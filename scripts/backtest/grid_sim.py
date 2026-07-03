"""
Grid-regime-backtest — faithful grid-bot simulator (read-only).

Brief: config/2026-06-28_S110_brief_grid-regime-backtest.md

Replica il loop decisionale REALE di bot/grid/grid_bot.py:check_price_and_execute
nello stesso ordine, con i parametri congelati (vedi params.py):

  daily-reset -> daily-limit -> [skip post-recalibrate] -> stop-buy arm ->
  stop-buy unlock -> dead-zone recalibrate -> SELL -> BUY -> IDLE re-entry

Decisioni di modellazione (documentate nel report):
 1. FILL = close della candela 1m. Il bot live fa polling ogni 60s e reagisce a
    un PREZZO ISTANTANEO, non a high/low del minuto: il close è il proxy fedele
    (e conservativo: non assume di aver preso ogni wick). [conferma Max]
 2. FEE = Kraken taker (0.40%), pagata in QUOTE (USD) su buy e sell (KrakenClient
    fee_base=0). Sul buy la fee è inglobata nel cost-basis dell'avg (come il
    ramo synth_fee del bot, pensato proprio per simulare una fee mainnet-like).
    Il trigger di SELL usa FEE dentro la formula -> alzando la fee i trigger di
    vendita si allargano da soli (il sell_pct resta NETTO post-fee). [Max]
 3. CASH = USD liquidi totali (riserva inclusa). available_cash = cash - reserve
    (lo skim non è reinvestibile). equity = cash + holdings*price.
 4. Nessun TF/Sentinel/Sherpa: parametri congelati = nessun force-liquidate,
    nessun trailing/stop-loss/take-profit (quelli sono TF-only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class GridSim:
    # --- frozen params ---
    capital: float
    capital_per_trade: float
    buy_pct: float
    sell_pct: float
    skim_pct: float
    min_profit_pct: float
    idle_reentry_hours: float
    dead_zone_hours: float
    stop_buy_drawdown_pct: float
    stop_buy_unlock_hours: float
    buy_cooldown_seconds: float
    slippage_buffer_pct: float
    fee_rate: float
    min_last_shot_usd: float = 5.0
    daily_trade_limit: int = 50
    min_notional_usd: float = 5.0
    strategy: str = "A"
    # repaired=False -> bot ATTUALE: avg azzerato sulla svendita-a-polvere
    #   (sell_pipeline.py:696) -> la polvere tenuta diluisce l'avg al re-entry
    #   -> vendita istantanea allo stesso prezzo -> churn da fee.
    # repaired=True  -> bot RIPARATO: l'avg "operativo" NON si azzera sulla
    #   polvere (la trattiene al costo vero). Niente diluizione -> il trigger
    #   di sell richiede un movimento reale -> niente churn. La guard Strategy A
    #   resta esente sulla polvere (S105b), quindi niente dust-trap dei buy.
    repaired: bool = False
    # trend_gate=True: in uptrend confermato (regime_up passato da run()) il grid
    #   NON fa la vendita fissa a +sell_pct — invece "cavalca" con un trailing
    #   stop (esce a -trail_pct dal picco). Fuori dall'uptrend torna grid normale.
    #   Default off -> comportamento identico al grid puro validato.
    trend_gate: bool = False
    trail_pct: float = 4.0

    # --- state ---
    cash: float = 0.0
    holdings: float = 0.0
    avg: float = 0.0
    last_buy_price: float = 0.0       # _pct_last_buy_price
    last_sell_price: float = 0.0
    reserve: float = 0.0              # cumulative skim
    realized: float = 0.0
    total_fees: float = 0.0
    stop_buy_active: bool = False
    stop_buy_activated_at: Optional[pd.Timestamp] = None
    stop_buy_baseline: float = 0.0
    last_trade_time: Optional[pd.Timestamp] = None
    last_buy_time: Optional[pd.Timestamp] = None
    skip_next_decision: bool = False
    daily_trade_count: int = 0
    daily_date: object = None
    peak_price: float = 0.0           # max prezzo mentre tiene posizione (trailing)

    # --- records ---
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)

    def __post_init__(self):
        self.cash = float(self.capital)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _available_cash(self) -> float:
        return max(0.0, self.cash - self.reserve)

    def _is_dust(self, price: float) -> bool:
        """No real (sellable) position. Mirrors is_dust(holdings*price < min_notional)."""
        return self.holdings * price < self.min_notional_usd

    def equity(self, price: float) -> float:
        return self.cash + self.holdings * price

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------
    def _execute_buy(self, price: float, dt: pd.Timestamp) -> bool:
        if self.stop_buy_active:
            return False
        # Strategy A symmetric guard: never buy above avg when holding a real
        # position (buy_pipeline.py). First entry (dust/flat) always allowed.
        if (self.strategy == "A"
                and not self._is_dust(price)
                and self.avg > 0
                and price > self.avg):
            return False

        standard_cost = self.capital_per_trade
        cash_b = self._available_cash()
        if cash_b >= standard_cost:
            remaining = cash_b - standard_cost
            if 0 < remaining < standard_cost:          # SWEEP
                cost = cash_b * (1 - self.slippage_buffer_pct)
                last_shot = True
            else:
                cost = standard_cost
                last_shot = False
        elif cash_b >= self.min_last_shot_usd:          # LAST SHOT
            cost = cash_b * (1 - self.slippage_buffer_pct)
            last_shot = True
        else:
            return False                                # insufficient cash

        qty = cost / price
        fee = cost * self.fee_rate                       # Kraken: fee in quote
        # avg includes the buy fee (cost_for_avg = cost + fee), like synth_fee.
        new_holdings = self.holdings + qty
        self.avg = (self.avg * self.holdings + (cost + fee)) / new_holdings
        self.holdings = new_holdings
        self.cash -= (cost + fee)
        self.total_fees += fee
        self.last_buy_price = price
        self.last_buy_time = dt
        self.last_trade_time = dt
        self.stop_buy_baseline = 0.0
        self.daily_trade_count += 1
        self.trades.append({
            "dt": dt, "side": "buy", "price": price, "qty": qty,
            "value": cost, "fee": fee, "realized": 0.0,
            "reason": ("first/re-entry" if last_shot is False and self.avg else "buy")
                      + (" LAST_SHOT" if last_shot else ""),
        })
        return True

    def _execute_sell(self, price: float, dt: pd.Timestamp) -> bool:
        if self.avg <= 0:
            return False
        # min profit floor (disabled when min_profit_pct == 0)
        if self.min_profit_pct > 0 and price < self.avg * (1 + self.min_profit_pct / 100):
            return False
        # Strategy A: never sell below avg (redundant with trigger gate).
        if self.strategy == "A" and price < self.avg:
            return False

        qty = min(self.holdings, self.capital_per_trade / price)
        if qty <= 0:
            return False
        revenue = qty * price
        fee = revenue * self.fee_rate
        cost_basis = qty * self.avg
        realized = revenue - cost_basis - fee
        self.cash += (revenue - fee)
        self.holdings -= qty
        self.realized += realized
        self.total_fees += fee
        # profit skim -> reserve (not reinvestable)
        if self.skim_pct > 0 and realized > 0:
            self.reserve += realized * (self.skim_pct / 100)
        # profitable sell releases the stop-buy gate (event hysteresis)
        if self.stop_buy_active and realized > 0:
            self.stop_buy_active = False
            self.stop_buy_activated_at = None
            self.stop_buy_baseline = 0.0
        # fully sold out (residual below min sellable = "dust")?
        if self.holdings * price < self.min_notional_usd or self.holdings <= 1e-12:
            if not self.repaired:
                self.avg = 0.0           # bot attuale: dimentica il costo della polvere
            # repaired: l'avg resta onesto (la polvere è valorizzata al costo vero)
            self.last_sell_price = 0.0
            self.last_buy_price = price
        else:
            self.last_sell_price = price
        self.last_trade_time = dt
        self.daily_trade_count += 1
        self.trades.append({
            "dt": dt, "side": "sell", "price": price, "qty": qty,
            "value": revenue, "fee": fee, "realized": realized, "reason": "pct sell",
        })
        return True

    # ------------------------------------------------------------------
    # one tick (candle close)
    # ------------------------------------------------------------------
    def step(self, price: float, dt: pd.Timestamp, regime_up: bool = False):
        d = dt.date()
        if d != self.daily_date:
            self.daily_trade_count = 0
            self.daily_date = d

        if self.daily_trade_count >= self.daily_trade_limit:
            return self._record(price, dt)

        if self.skip_next_decision:
            self.skip_next_decision = False
            return self._record(price, dt)

        # --- stop-buy arm (39b) ---
        if (not self._is_dust(price) and self.avg > 0 and not self.stop_buy_active):
            ref = self.stop_buy_baseline if self.stop_buy_baseline > 0 else self.avg
            unreal = (price - ref) * self.holdings
            if unreal <= -(self.capital * self.stop_buy_drawdown_pct / 100):
                self.stop_buy_active = True
                self.stop_buy_activated_at = dt

        # --- stop-buy unlock (75b/75c) ---
        if (self.stop_buy_active and self.stop_buy_unlock_hours > 0
                and self.stop_buy_activated_at is not None):
            elapsed_sb = (dt - self.stop_buy_activated_at).total_seconds() / 3600
            if elapsed_sb >= self.stop_buy_unlock_hours:
                self.stop_buy_baseline = price
                self.stop_buy_active = False
                self.stop_buy_activated_at = None

        # --- dead-zone recalibrate (73a/74b) ---
        if (not self._is_dust(price) and self.last_sell_price > 0 and self.avg > 0
                and price > self.avg and self.last_trade_time is not None):
            elapsed_dz = (dt - self.last_trade_time).total_seconds() / 3600
            if elapsed_dz >= self.dead_zone_hours:
                self.last_sell_price = 0.0
                self.last_buy_price = price
                self.last_trade_time = dt
                self.skip_next_decision = True
                return self._record(price, dt)

        # --- track peak while holding (per il trailing del trend-gate) ---
        if not self._is_dust(price):
            self.peak_price = max(self.peak_price, price)
        else:
            self.peak_price = 0.0

        # --- SELL ---
        if not self._is_dust(price):
            if self.trend_gate and regime_up:
                # RIDE MODE: uptrend confermato -> niente vendita fissa, si cavalca.
                # Esce solo se il prezzo cala di trail_pct dal picco (trend rotto)
                # e resta sopra l'avg (Strategy A: mai vendere in perdita).
                trail_stop = self.peak_price * (1 - self.trail_pct / 100)
                if self.avg > 0 and price <= trail_stop and price > self.avg:
                    self._execute_sell(price, dt)
            else:
                ref = self.last_sell_price if self.last_sell_price > 0 else self.avg
                sell_trigger = ref * (1 + self.sell_pct / 100 + self.fee_rate) / (1 - self.fee_rate)
                if self.avg > 0 and price >= sell_trigger:
                    self._execute_sell(price, dt)

        # --- BUY ---
        cooldown = (self.buy_cooldown_seconds > 0
                    and self.last_buy_price != 0
                    and self.last_buy_time is not None
                    and (dt - self.last_buy_time).total_seconds() < self.buy_cooldown_seconds)
        if not cooldown and not self.stop_buy_active:
            if self.last_buy_price == 0:
                if self._is_dust(price):
                    self._execute_buy(price, dt)            # first buy at market
                else:
                    self.last_buy_price = self.avg          # existing holdings -> ref=avg
            else:
                buy_trigger = self.last_buy_price * (1 - self.buy_pct / 100)
                if price <= buy_trigger:
                    self._execute_buy(price, dt)

        # --- IDLE re-entry / recalibrate ---
        if (self.last_buy_price > 0 and self.last_trade_time is not None
                and self.idle_reentry_hours > 0):
            elapsed = (dt - self.last_trade_time).total_seconds() / 3600
            if elapsed >= self.idle_reentry_hours:
                available = self._available_cash()
                if available < self.min_last_shot_usd:
                    self.last_trade_time = dt               # suppressed, advance window
                elif self._is_dust(price):
                    self.last_buy_price = 0
                    self._execute_buy(price, dt)            # Path A: force re-entry
                else:
                    if not (self.avg > 0 and price > self.avg):
                        self.last_buy_price = price          # Path B: recalibrate
                    self.last_trade_time = dt

        return self._record(price, dt)

    def _record(self, price: float, dt: pd.Timestamp):
        self.equity_curve.append({
            "dt": dt,
            "price": price,
            "equity": self.equity(price),
            "available_cash": self._available_cash(),
            "reserve": self.reserve,
            "holdings": self.holdings,
            "position_value": self.holdings * price,
            "avg": self.avg,
            "realized": self.realized,
            "stop_buy": self.stop_buy_active,
            "active": not self._is_dust(price),   # holds a real position
            "n_trades": len(self.trades),
        })

    # ------------------------------------------------------------------
    def run(self, df: pd.DataFrame) -> "GridSim":
        has_regime = "regime_up" in df.columns
        for row in df.itertuples(index=False):
            ru = bool(getattr(row, "regime_up")) if has_regime else False
            self.step(float(row.close), row.dt, regime_up=ru)
        return self

    # ------------------------------------------------------------------
    def trades_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.trades)

    def equity_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.equity_curve)
