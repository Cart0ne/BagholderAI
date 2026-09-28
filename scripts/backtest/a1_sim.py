"""
A.1 (S130, 2026-09-28) — simulatore fedele al grid LIVE su Kraken.

Piano: config/2026-09-26_S129_piano_A1_analisi-strategia.md

Rispetto a grid_sim.py (S110, parametri congelati) qui cambia:
 - parametri che cambiano nel tempo (config_changes_log: Sherpa + manuali)
 - trigger di vendita S121: ref x (1 + sell_pct) / (1 - fee)  (grid_sim usa
   ancora la formula pre-S121 con la fee contata due volte)
 - vendita del residuo col lotto se resterebbe < 1,5x il minimo vendibile
   (dust prevention 66a, sell_pipeline.py:364)
 - finestre di fermo (nessun tick) e riavvii (stato ricostruito come
   state_manager.py: riferimento d'acquisto = ultimo acquisto vero, cronometro
   = ultima operazione, blocco perdita e attesa tra acquisti azzerati)
 - capitale che cambia nel tempo (BTC 100 -> 250 il 7-ago)
 - varianti del piano §4: dz_fix (D), dz_keep_buy_ref (D2), dz_hours_by_regime
   (E), fee (F), sell_pct_add (G), params fissi (C)

Ordine del tick = grid_bot.check_price_and_execute:
  skip post-reset -> blocco perdita (arma/sblocca) -> zona morta -> SELL -> BUY
  -> idle (re-entry / ricalcolo)
Fill = close della candela 1m (il bot fa polling ogni 60 s).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

MIN_LAST_SHOT_USD = 5.0        # config/settings.py
SLIPPAGE_BUFFER_PCT = 0.03     # config/settings.py (SWEEP / LAST SHOT)
MIN_NOTIONAL_USD = 0.5         # Kraken filters (log grid runner)


@dataclass
class A1Grid:
    symbol: str
    capital_per_trade: float
    skim_pct: float
    buy_cooldown_seconds: float
    min_qty: float
    fee_rate: float = 0.008
    # --- varianti ---
    dz_fix: bool = False              # D: la zona morta ha il SUO cronometro (non azzerato dall'idle)
    dz_keep_buy_ref: bool = False     # D2: il reset non tocca il riferimento d'acquisto
    dz_hours_fn: Optional[Callable[[str], float]] = None  # E: ore zona morta per regime
    sell_pct_add: float = 0.0         # G: + punti su sell_pct
    dz_off_regimes: tuple = ()        # S131a (R): zona morta spenta per scelta in questi regimi
    dz_resets_by_regime: dict = field(default_factory=dict)
    strategy: str = "A"

    # --- stato ---
    capital: float = 0.0
    cash: float = 0.0
    holdings: float = 0.0
    avg: float = 0.0
    last_buy_price: float = 0.0
    last_sell_price: float = 0.0
    reserve: float = 0.0
    realized: float = 0.0
    total_fees: float = 0.0
    injected: float = 0.0
    stop_buy_active: bool = False
    stop_buy_activated_at: Optional[pd.Timestamp] = None
    stop_buy_baseline: float = 0.0
    last_trade_time: Optional[pd.Timestamp] = None
    dz_clock: Optional[pd.Timestamp] = None   # solo dz_fix
    last_buy_time: Optional[pd.Timestamp] = None
    skip_next_decision: bool = False
    dz_resets: int = 0

    trades: list = field(default_factory=list)
    equity_rows: list = field(default_factory=list)

    # ------------------------------------------------------------------
    def set_capital(self, capital: float):
        """Carica/aumenta il capitale (BTC 100 -> 250 il 7-ago)."""
        delta = capital - self.capital
        self.capital = capital
        self.cash += delta
        self.injected += delta

    def _available_cash(self) -> float:
        return max(0.0, self.cash - self.reserve)

    def _min_sellable(self, price: float) -> float:
        return max(self.min_qty, MIN_NOTIONAL_USD / price if price > 0 else 0.0)

    def _is_dust(self, price: float) -> bool:
        return self.holdings <= 0 or self.holdings < self._min_sellable(price)

    def equity(self, price: float) -> float:
        return self.cash + self.holdings * price

    # ------------------------------------------------------------------
    def restart(self, dt: pd.Timestamp):
        """Riavvio del bot: state_manager ricostruisce dallo storico operazioni."""
        buys = [t for t in self.trades if t["side"] == "buy"]
        self.last_buy_price = buys[-1]["price"] if buys else 0.0
        self.last_trade_time = self.trades[-1]["dt"] if self.trades else None
        self.dz_clock = self.last_trade_time
        self.stop_buy_active = False
        self.stop_buy_activated_at = None
        self.stop_buy_baseline = 0.0
        self.last_buy_time = None
        self.skip_next_decision = False
        # last_sell_price (scala) e avg: il replay li ricostruisce uguali a quelli
        # tenuti in memoria (stesse regole), quindi restano.

    # ------------------------------------------------------------------
    def _buy(self, price: float, dt: pd.Timestamp, reason: str) -> bool:
        if self.stop_buy_active:
            return False
        if (self.strategy == "A" and not self._is_dust(price)
                and self.avg > 0 and price > self.avg):
            return False
        cash_b = self._available_cash()
        std = self.capital_per_trade
        if cash_b >= std:
            rem = cash_b - std
            cost = cash_b * (1 - SLIPPAGE_BUFFER_PCT) if 0 < rem < std else std
        elif cash_b >= MIN_LAST_SHOT_USD:
            cost = cash_b * (1 - SLIPPAGE_BUFFER_PCT)
        else:
            return False
        qty = cost / price
        if qty < self.min_qty:
            return False
        fee = cost * self.fee_rate
        new_h = self.holdings + qty
        self.avg = (self.avg * self.holdings + cost + fee) / new_h
        self.holdings = new_h
        self.cash -= cost + fee
        self.total_fees += fee
        self.last_buy_price = price
        self.last_buy_time = dt
        self.last_trade_time = dt
        self.dz_clock = dt
        self.stop_buy_baseline = 0.0
        self.trades.append({"dt": dt, "side": "buy", "price": price, "qty": qty,
                            "value": cost, "fee": fee, "realized": 0.0, "reason": reason})
        return True

    def _sell(self, price: float, dt: pd.Timestamp, reason: str) -> bool:
        if self.avg <= 0 or (self.strategy == "A" and price < self.avg):
            return False
        qty = min(self.capital_per_trade / price, self.holdings)
        residual = self.holdings - qty
        if 0 < residual < self._min_sellable(price) * 1.5:
            qty = self.holdings
        revenue = qty * price
        fee = revenue * self.fee_rate
        realized = revenue - qty * self.avg - fee
        self.cash += revenue - fee
        self.holdings -= qty
        self.realized += realized
        self.total_fees += fee
        if self.skim_pct > 0 and realized > 0:
            self.reserve += realized * self.skim_pct / 100
        if self.stop_buy_active and realized > 0:
            self.stop_buy_active = False
            self.stop_buy_activated_at = None
            self.stop_buy_baseline = 0.0
        if self.holdings <= 1e-10 or self.holdings * price < MIN_NOTIONAL_USD:
            if self.holdings <= 1e-10:
                self.holdings = 0.0
                self.avg = 0.0
            self.last_buy_price = price
            self.last_sell_price = 0.0
        else:
            self.last_sell_price = price
        self.last_trade_time = dt
        self.dz_clock = dt
        self.trades.append({"dt": dt, "side": "sell", "price": price, "qty": qty,
                            "value": revenue, "fee": fee, "realized": realized, "reason": reason})
        return True

    # ------------------------------------------------------------------
    def step(self, price: float, dt: pd.Timestamp, p) -> None:
        """p: riga con buy_pct, sell_pct, idle_h, dz_h, sb_dd, sb_unlock, regime."""
        if self.skip_next_decision:
            self.skip_next_decision = False
            return

        # --- blocco perdita: arma ---
        if (p.sb_dd > 0 and self.holdings > 0 and self.avg > 0
                and not self.stop_buy_active):
            ref = self.stop_buy_baseline if self.stop_buy_baseline > 0 else self.avg
            if (price - ref) * self.holdings <= -(self.capital * p.sb_dd / 100):
                self.stop_buy_active = True
                self.stop_buy_activated_at = dt
        # --- blocco perdita: sblocco a tempo ---
        if (self.stop_buy_active and p.sb_unlock > 0
                and self.stop_buy_activated_at is not None
                and (dt - self.stop_buy_activated_at).total_seconds() / 3600 >= p.sb_unlock):
            self.stop_buy_baseline = price
            self.stop_buy_active = False
            self.stop_buy_activated_at = None

        # --- zona morta ---
        dz_h = self.dz_hours_fn(p.regime) if self.dz_hours_fn else p.dz_h
        if p.regime in self.dz_off_regimes:
            dz_h = 0.0                        # S131a: 0 = zona morta disattivata
        clock = self.dz_clock if self.dz_fix else self.last_trade_time
        if (dz_h > 0 and not self._is_dust(price) and self.last_sell_price > 0 and self.avg > 0
                and price > self.avg and clock is not None
                and (dt - clock).total_seconds() / 3600 >= dz_h):
            self.last_sell_price = 0.0
            if not self.dz_keep_buy_ref:
                self.last_buy_price = price
            self.last_trade_time = dt
            self.dz_clock = dt
            self.skip_next_decision = True
            self.dz_resets += 1
            self.dz_resets_by_regime[p.regime] = self.dz_resets_by_regime.get(p.regime, 0) + 1
            return

        # --- SELL ---
        if not self._is_dust(price):
            ref = self.last_sell_price if self.last_sell_price > 0 else self.avg
            sp = p.sell_pct + self.sell_pct_add
            trig = ref * (1 + sp / 100) / (1 - self.fee_rate)
            if self.avg > 0 and price >= trig:
                self._sell(price, dt, "ladder" if self.last_sell_price > 0 else "avg")

        # --- BUY ---
        cooldown = (self.buy_cooldown_seconds > 0 and self.last_buy_price != 0
                    and self.last_buy_time is not None
                    and (dt - self.last_buy_time).total_seconds() < self.buy_cooldown_seconds)
        if not cooldown:
            if self.last_buy_price == 0:
                if not self._is_dust(price):
                    self.last_buy_price = self.avg
                else:
                    self._buy(price, dt, "first")
            elif price <= self.last_buy_price * (1 - p.buy_pct / 100):
                self._buy(price, dt, "pct")

        # --- idle: re-entry (senza posizione) / ricalcolo (con posizione) ---
        if (self.last_buy_price > 0 and self.last_trade_time is not None and p.idle_h > 0
                and (dt - self.last_trade_time).total_seconds() / 3600 >= p.idle_h):
            if self._available_cash() < MIN_LAST_SHOT_USD:
                self.last_trade_time = dt
            elif self._is_dust(price):
                self.last_buy_price = 0
                self._buy(price, dt, "re-entry")
            else:
                if not (self.avg > 0 and price > self.avg):
                    self.last_buy_price = price
                self.last_trade_time = dt   # <- il bug S129: azzera anche il cronometro della zona morta


def run_sim(grid: A1Grid, prices: pd.DataFrame, params: pd.DataFrame,
            capital_events: list, restarts: list, downtime: list) -> A1Grid:
    """prices: dt, close (1m). params: stesso indice di prices, colonne dei parametri.

    capital_events: [(ts, capital)] ; restarts: [ts] ; downtime: [(start, end)].
    Ogni minuto registra equity e stato (anche nei fermi, marcati `down`).
    """
    cap_ev = sorted(capital_events)
    rst = sorted(restarts)
    ci = ri = 0
    down_iv = sorted(downtime)
    di = 0
    for row, p in zip(prices.itertuples(index=False), params.itertuples(index=False)):
        dt = row.dt
        price = float(row.close)
        while ci < len(cap_ev) and cap_ev[ci][0] <= dt:
            grid.set_capital(cap_ev[ci][1]); ci += 1
        while di < len(down_iv) and down_iv[di][1] <= dt:
            di += 1
        down = di < len(down_iv) and down_iv[di][0] <= dt < down_iv[di][1]
        if not down:
            while ri < len(rst) and rst[ri] <= dt:
                grid.restart(dt); ri += 1
            grid.step(price, dt, p)
        grid.equity_rows.append((dt, price, grid.equity(price), grid.injected,
                                 grid.holdings, grid.avg, grid.reserve, p.regime, down))
    return grid


def equity_df(grid: A1Grid) -> pd.DataFrame:
    return pd.DataFrame(grid.equity_rows, columns=[
        "dt", "price", "equity", "injected", "holdings", "avg", "reserve", "regime", "down"])


def trades_df(grid: A1Grid) -> pd.DataFrame:
    return pd.DataFrame(grid.trades)
