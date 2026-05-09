"""
BagHolderAI - Grid Bot (Brain #1)
The soldier. Buys low, sells high, no prediction needed.
Profits from volatility by placing orders at regular intervals within a range.

Paper trading mode: uses real market prices, simulates fills.

Phase 1 refactor (2026-05-07, brief 62a):
This file used to be a 2200-line monolith. It now coordinates calls into
focused modules:
- fifo_queue.py: FIFO queue replay + drift verify.
- state_manager.py: boot-time state restoration from DB.
- buy_pipeline.py: buy execution (fixed + pct).
- sell_pipeline.py: sell execution + greed-decay TP + gain-saturation.
- dust_handler.py: dust-lot pop helpers (with documented bug intact).
GridBot's public API is unchanged — every method that grid_runner or tests
call still exists and behaves identically. Internals are wrappers that
delegate to the modules above.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from utils.formatting import fmt_price
from db.event_logger import log_event

from bot.grid import (
    fifo_queue,
    state_manager,
    buy_pipeline,
    sell_pipeline,
)

logger = logging.getLogger("bagholderai.grid")


@dataclass
class GridLevel:
    """A single level in the grid."""
    price: float
    side: str  # "buy" or "sell"
    filled: bool = False
    filled_at: Optional[float] = None  # timestamp when filled
    order_amount: float = 0.0  # amount in base currency (e.g., BTC)


@dataclass
class GridState:
    """Current state of the grid bot for one symbol."""
    symbol: str
    strategy: str  # "A" or "B"
    center_price: float
    lower_bound: float
    upper_bound: float
    levels: list = field(default_factory=list)
    total_invested: float = 0.0  # total USDT spent on buys
    total_received: float = 0.0  # total USDT received from sells
    total_fees: float = 0.0
    holdings: float = 0.0  # current holdings in base currency
    avg_buy_price: float = 0.0
    trades_today: int = 0
    last_price: float = 0.0
    created_at: str = ""

    realized_pnl: float = 0.0
    daily_realized_pnl: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if self.holdings > 0 and self.last_price > 0 and self.avg_buy_price > 0:
            return (self.last_price - self.avg_buy_price) * self.holdings
        return 0.0


class GridBot:
    """
    Grid trading bot. Places buy and sell orders at regular intervals
    within a price range. Profits from oscillations.

    In paper mode: reads real prices, simulates order fills.
    In live mode: places real orders via exchange API (future).
    """

    # Fee rate for Binance spot with BNB discount
    FEE_RATE = 0.00075  # 0.075%

    def __init__(
        self,
        exchange,
        trade_logger,
        portfolio_manager,
        pnl_tracker,
        symbol: str = "BTC/USDT",
        strategy: str = "A",
        capital: float = 100.0,  # USDT allocated to this grid
        num_levels: int = 10,
        range_percent: float = 0.04,  # 4% range (2% above and below)
        mode: str = "paper",
        buy_cooldown_seconds: int = 0,  # Task 5: min seconds between buys
        min_profit_pct: float = 0.0,    # Task 10: min gross margin % to allow a sell (e.g. 1.0 = 1%)
        grid_mode: str = "fixed",       # "fixed" or "percentage"
        buy_pct: float = 0.0,           # % drop from last buy to trigger next buy
        sell_pct: float = 0.0,          # % rise from avg buy to trigger sell
        capital_per_trade: float = 0.0, # USDT to spend per buy in percentage mode
        reserve_ledger=None,            # ReserveLedger instance (Session 20b)
        skim_pct: float = 0.0,          # % of sell profit to skim into reserve
        idle_reentry_hours: float = 24.0,  # hours idle (holdings=0) before forced re-entry
        tf_stop_loss_pct: float = 0.0,  # 39a: TF stop-loss threshold as % of open value (0 = disabled)
        stop_buy_drawdown_pct: float = 0.0,  # 39b: manual stop-buy threshold as % of allocation (0 = disabled)
        tf_take_profit_pct: float = 0.0,  # 39c: TF take-profit threshold as % of open value (0 = disabled)
        tf_profit_lock_enabled: bool = False,  # 45f: opt-in switch for proactive Profit Lock exit
        tf_profit_lock_pct: float = 0.0,       # 45f: net PnL threshold (% of alloc) that triggers Profit Lock
        tf_exit_after_n_enabled: bool = True,   # 45g: kill-switch for the gain-saturation breaker
        tf_exit_after_n_default: int = 4,       # 45g: global default N; per-coin override on bot_config
        tf_exit_after_n_override: Optional[int] = None,  # 45g: per-coin override (NULL = use default)
        tf_trailing_stop_activation_pct: float = 0.0,  # 51b: minimum profit (% of avg_buy) the peak must reach before trailing engages
        tf_trailing_stop_pct: float = 0.0,             # 51b: drop from peak (%) that triggers exit; 0 = disabled
        allocated_at: Optional[datetime] = None,  # 42a: TF allocation timestamp (anchors greed decay)
        greed_decay_tiers: Optional[list] = None, # 42a: [{minutes, tp_pct}, ...] — None for manual bots
    ):
        self.exchange = exchange
        self.trade_logger = trade_logger
        self.portfolio_manager = portfolio_manager
        self.pnl_tracker = pnl_tracker
        self.symbol = symbol
        self.strategy = strategy
        self.capital = capital
        self.num_levels = num_levels
        self.range_percent = range_percent
        self.mode = mode
        self.buy_cooldown_seconds = buy_cooldown_seconds
        self.min_profit_pct = min_profit_pct
        self.grid_mode = grid_mode
        self.buy_pct = buy_pct
        self.sell_pct = sell_pct
        self.capital_per_trade = capital_per_trade
        self.reserve_ledger = reserve_ledger
        self.skim_pct = skim_pct
        self.idle_reentry_hours = idle_reentry_hours
        self.tf_stop_loss_pct = tf_stop_loss_pct
        self.stop_buy_drawdown_pct = stop_buy_drawdown_pct
        self.tf_take_profit_pct = tf_take_profit_pct
        self.tf_profit_lock_enabled = tf_profit_lock_enabled
        self.tf_profit_lock_pct = tf_profit_lock_pct
        self.tf_exit_after_n_enabled = tf_exit_after_n_enabled
        self.tf_exit_after_n_default = tf_exit_after_n_default
        self.tf_exit_after_n_override = tf_exit_after_n_override
        self.tf_trailing_stop_activation_pct = tf_trailing_stop_activation_pct  # 51b
        self.tf_trailing_stop_pct = tf_trailing_stop_pct                        # 51b
        self.allocated_at: Optional[datetime] = allocated_at
        self.greed_decay_tiers: Optional[list] = greed_decay_tiers
        self.is_active: bool = True  # controlled via Supabase bot_config
        self.pending_liquidation: bool = False  # TF rotation trigger
        self.managed_by: str = "grid"  # "grid", "tf", or "tf_grid" (68b)
        self._stop_loss_triggered: bool = False  # 39a: latched once threshold is breached
        self._stop_buy_active: bool = False  # 39b: latched once drawdown breached, resets on profitable sell
        self._take_profit_triggered: bool = False  # 39c: latched once +pct threshold reached
        self._profit_lock_triggered: bool = False  # 45f: latched once net-PnL threshold breached
        self._gain_saturation_triggered: bool = False  # 45g: latched once N positive sells in current period
        self._trailing_peak_price: float = 0.0          # 51b: highest price seen since bot start (in-memory only)
        self._trailing_stop_triggered: bool = False     # 51b: latched once trailing stop fires
        self._exchange_filters: dict = {}  # populated at startup via set_exchange_filters()
        self.state: Optional[GridState] = None
        self._daily_trade_count = 0
        self._daily_date = datetime.utcnow().date()
        self._daily_pnl_date = datetime.utcnow().date()
        self._last_buy_time: float = 0.0  # Task 5: timestamp of last buy
        self._last_trade_time: Optional[datetime] = None  # UTC datetime of last executed trade
        self.skipped_buys: list = []     # filled each cycle with insufficient-cash skips
        self.skipped_sells: list = []    # filled each cycle with insufficient-holdings skips
        self.idle_reentry_alerts: list = []  # filled each cycle when idle re-entry fires
        self._idle_logged_hour: int = -1     # last elapsed-hour mark already logged (avoids spam)
        # Percentage mode state
        self._pct_last_buy_price: float = 0.0
        self._pct_open_positions: list = []  # FIFO: [{"amount": float, "price": float}, ...]
        self._self_heal_attempted: bool = False  # prevents repeated futile self-heal calls

    # ------------------------------------------------------------------
    # Helpers (kept on GridBot — small + heavily used internally).
    # ------------------------------------------------------------------

    def _available_cash(self) -> float:
        """
        Available cash = capital - invested + received - reserve.
        The reserve is subtracted so the bot never buys with skimmed profit.
        """
        if not self.state:
            return self.capital
        base = max(0.0, self.capital - self.state.total_invested + self.state.total_received)
        if self.reserve_ledger:
            try:
                reserve = self.reserve_ledger.get_reserve_total(self.symbol)
                base = max(0.0, base - reserve)
            except Exception as e:
                logger.warning(f"[{self.symbol}] Could not fetch reserve total: {e}")
        return base

    @staticmethod
    def _price_decimals(price: float) -> int:
        """Determine the number of decimals to use for rounding based on price magnitude."""
        if price >= 1:
            return 2
        if price >= 0.01:
            return 4
        if price >= 0.0001:
            return 6
        return 8

    def set_exchange_filters(self, filters: dict):
        """Store exchange filters for order validation."""
        self._exchange_filters = filters

    # ------------------------------------------------------------------
    # Grid setup (kept here — tightly coupled to GridState construction).
    # ------------------------------------------------------------------

    def setup_grid(self, current_price: float) -> GridState:
        """
        Create a new grid centered on the current price.

        Buy levels below current price, sell levels above.
        Each level gets an equal share of the available capital.

        On reset (self.state already exists): preserves accounting
        (holdings, avg_buy_price, realized_pnl, etc.) and distributes
        existing holdings across the new sell levels. Buy level sizes
        are calculated from available_capital (Task 7), not total capital.
        """
        # Save old accounting before overwriting state
        old_state = self.state

        # Task 7: use available capital on reset, full capital on first setup
        if old_state is not None:
            available_capital = max(0.0, self.capital - old_state.total_invested + old_state.total_received)
        else:
            available_capital = self.capital

        half_range = current_price * (self.range_percent / 2)
        lower = current_price - half_range
        upper = current_price + half_range

        # Calculate step size between levels
        step = (upper - lower) / (self.num_levels - 1)

        # Determine rounding precision based on price
        decimals = self._price_decimals(current_price)

        # Capital per level (only buy levels use capital)
        num_buy_levels = self.num_levels // 2
        capital_per_level = available_capital / num_buy_levels

        levels = []
        for i in range(self.num_levels):
            level_price = lower + (step * i)

            if level_price < current_price:
                # Buy level — below current price
                amount = capital_per_level / level_price
                if self._exchange_filters:
                    from utils.exchange_filters import round_to_step
                    amount = round_to_step(amount, self._exchange_filters["lot_step_size"])
                levels.append(GridLevel(
                    price=round(level_price, decimals),
                    side="buy",
                    order_amount=round(amount, 8),
                ))
            else:
                # Sell level — above current price
                # Sell levels start empty (nothing to sell until we buy)
                levels.append(GridLevel(
                    price=round(level_price, decimals),
                    side="sell",
                    order_amount=0.0,
                ))

        self.state = GridState(
            symbol=self.symbol,
            strategy=self.strategy,
            center_price=round(current_price, decimals),
            lower_bound=round(lower, decimals),
            upper_bound=round(upper, decimals),
            levels=levels,
            last_price=current_price,
            created_at=datetime.utcnow().isoformat(),
        )

        # On reset: restore accounting from old state
        if old_state is not None:
            self.state.holdings = old_state.holdings
            self.state.avg_buy_price = old_state.avg_buy_price
            self.state.total_invested = old_state.total_invested
            self.state.total_received = old_state.total_received
            self.state.total_fees = old_state.total_fees
            self.state.realized_pnl = old_state.realized_pnl
            self.state.daily_realized_pnl = old_state.daily_realized_pnl
            self.state.trades_today = old_state.trades_today

            # Distribute existing holdings across sell levels
            if self.state.holdings > 0:
                sell_levels = [l for l in levels if l.side == "sell"]
                if sell_levels:
                    amount_per_level = self.state.holdings / len(sell_levels)
                    for sl in sell_levels:
                        sl.order_amount = round(amount_per_level, 8)

        is_reset = "RESET" if old_state is not None else "NEW"
        if self.grid_mode == "percentage":
            buy_trigger = current_price * (1 - self.buy_pct / 100)
            sell_trigger = current_price * (1 + self.sell_pct / 100)
            range_str = (
                f"Range: {fmt_price(buy_trigger)} (-{self.buy_pct}%) - "
                f"{fmt_price(sell_trigger)} (+{self.sell_pct}%)"
            )
        else:
            range_str = f"Range Fixed: {fmt_price(lower)} - {fmt_price(upper)}"
        logger.info(
            f"Grid {is_reset}: {self.symbol} | "
            f"Center: {fmt_price(current_price)} | "
            f"{range_str} | "
            f"Levels: {self.num_levels} | "
            f"Available capital: ${available_capital:.2f}"
        )

        return self.state

    # ------------------------------------------------------------------
    # State restoration — wrappers around state_manager / fifo_queue.
    # ------------------------------------------------------------------

    def restore_state_from_db(self):
        """v1 fixed-mode position restore. Delegates to state_manager."""
        return state_manager.restore_state_from_db(self)

    def init_percentage_state_from_db(self):
        """v3 pct-mode FIFO replay from DB. Delegates to state_manager."""
        return state_manager.init_percentage_state_from_db(self)

    def verify_fifo_queue(self) -> bool:
        """57a integrity gate. Delegates to fifo_queue.verify_fifo_queue."""
        return fifo_queue.verify_fifo_queue(self)

    # ------------------------------------------------------------------
    # Main dispatcher — kept here, the central decision flow.
    # ------------------------------------------------------------------

    def check_price_and_execute(self, current_price: float) -> list:
        """
        Check current price against grid levels and execute fills.
        Returns list of trades executed.

        Logic:
        - Price drops to/below a buy level → fill the buy (if cooldown elapsed)
        - Price rises to/above a sell level → fill the sell (no cooldown on sells)
        """
        if not self.state:
            raise RuntimeError("Grid not initialized. Call setup_grid() first.")

        if self.grid_mode == "percentage":
            return self._check_percentage_and_execute(current_price)

        # Reset daily counters if new day
        today = datetime.utcnow().date()
        if today != self._daily_date:
            self._daily_trade_count = 0
            self._daily_date = today
        if today != self._daily_pnl_date:
            self.state.daily_realized_pnl = 0.0
            self._daily_pnl_date = today

        trades = []
        self.skipped_buys = []
        self.skipped_sells = []
        self.state.last_price = current_price

        # Task 5: check if buy cooldown is active
        now = time.time()
        buy_cooldown_active = (
            self.buy_cooldown_seconds > 0
            and (now - self._last_buy_time) < self.buy_cooldown_seconds
        )
        if buy_cooldown_active:
            remaining = self.buy_cooldown_seconds - (now - self._last_buy_time)
            logger.debug(f"Buy cooldown active, {remaining:.0f}s remaining. Skipping buy levels.")

        for level in self.state.levels:
            if level.filled:
                continue

            # Check daily operation limit (hardcoded rule)
            if self._daily_trade_count >= 50:
                logger.warning("Daily operation limit reached (50). Stopping.")
                break

            if level.side == "buy" and current_price <= level.price:
                if buy_cooldown_active:
                    continue  # skip all buys while cooldown is active
                trade = self._execute_buy(level, current_price)
                if trade:
                    trades.append(trade)
                    buy_cooldown_active = True  # block further buys this cycle regardless of cooldown setting

            elif level.side == "sell" and current_price >= level.price:
                if self.state.holdings > 0:
                    trade = self._execute_sell(level, current_price)
                    if trade:
                        trades.append(trade)

        return trades

    def _check_percentage_and_execute(self, current_price: float) -> list:
        """
        Percentage-based buy/sell logic (grid_mode = 'percentage').

        BUY:  price dropped buy_pct% below last buy price → buy capital_per_trade USDT
              If no previous buys, buy immediately to establish reference.
        SELL: price rose sell_pct% above avg buy price → sell oldest open lot (FIFO).
        """
        today = datetime.utcnow().date()
        if today != self._daily_date:
            self._daily_trade_count = 0
            self._daily_date = today
        if today != self._daily_pnl_date:
            self.state.daily_realized_pnl = 0.0
            self._daily_pnl_date = today

        trades = []
        self.skipped_buys = []
        self.skipped_sells = []
        self.idle_reentry_alerts = []
        self.state.last_price = current_price

        if self._daily_trade_count >= 50:
            logger.warning("Daily operation limit reached (50). Stopping.")
            return trades

        # --- 51b: trailing stop — peak tracking ---
        # Track highest price seen each tick while we have holdings on a TF
        # bot. Manual bots and TF bots with the feature disabled skip it
        # entirely (no peak persisted, no API cost). In-memory only by design
        # (see brief: a restart "forgets" the peak which is conservative).
        if (self.managed_by == "tf"
                and self.tf_trailing_stop_pct > 0
                and self.state.holdings > 0
                and current_price > self._trailing_peak_price):
            self._trailing_peak_price = current_price

        # --- 39a: TF stop-loss check ---
        # Evaluated on the entire position (not per-lot) so a partial rebound
        # on one lot doesn't mask the overall bleed. Only armed for TF bots
        # (manual bots keep Strategy A's unconditional "never sell at loss").
        if (self.managed_by == "tf"
                and self.tf_stop_loss_pct > 0
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and not self._stop_loss_triggered):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            open_value = self.state.avg_buy_price * self.state.holdings
            loss_threshold = -(open_value * self.tf_stop_loss_pct / 100)
            if unrealized <= loss_threshold:
                logger.warning(
                    f"[{self.symbol}] STOP-LOSS TRIGGERED: unrealized ${unrealized:.2f} "
                    f"<= threshold ${loss_threshold:.2f} "
                    f"({self.tf_stop_loss_pct:.0f}% of open value ${open_value:.2f}). "
                    f"Liquidating all {len(self._pct_open_positions)} lots."
                )
                self._stop_loss_triggered = True
                # 45a v2: record SL timestamp in bot_config for the TF cooldown.
                # Always written (even when cooldown is disabled / 0h) so the
                # history is available if Max later raises the value.
                if self.trade_logger is not None:
                    try:
                        self.trade_logger.client.table("bot_config").update(
                            {"last_stop_loss_at": datetime.now(timezone.utc).isoformat()}
                        ).eq("symbol", self.symbol).execute()
                    except Exception as e:
                        logger.error(
                            f"[{self.symbol}] Failed to write last_stop_loss_at: {e}"
                        )
                log_event(
                    severity="warn",
                    category="safety",
                    event="stop_loss_triggered",
                    symbol=self.symbol,
                    message=f"TF stop-loss: unrealized ${unrealized:.2f} ≤ ${loss_threshold:.2f}",
                    details={
                        "unrealized": unrealized,
                        "threshold": loss_threshold,
                        "pct": self.tf_stop_loss_pct,
                        "lots": len(self._pct_open_positions),
                    },
                )

        # --- 51b: trailing stop trigger ---
        # Order: stop-loss → trailing stop → take-profit → profit-lock → 45g.
        # Trailing protects unrealized gains: once the peak has cleared
        # avg_buy × (1 + activation_pct%), a drop of trailing_pct% from peak
        # forces a full liquidation. Doesn't fire if SL/TP/PL/45g already
        # latched, or when the feature is disabled (tf_trailing_stop_pct=0).
        if (self.managed_by == "tf"
                and self.tf_trailing_stop_pct > 0
                and not self._stop_loss_triggered
                and not self._trailing_stop_triggered
                and not self._take_profit_triggered
                and not self._profit_lock_triggered
                and not self._gain_saturation_triggered
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and self._trailing_peak_price > 0):
            activation_price = self.state.avg_buy_price * (1 + self.tf_trailing_stop_activation_pct / 100)
            if self._trailing_peak_price >= activation_price:
                trailing_trigger = self._trailing_peak_price * (1 - self.tf_trailing_stop_pct / 100)
                if current_price <= trailing_trigger:
                    drop_from_peak_pct = ((self._trailing_peak_price - current_price) / self._trailing_peak_price) * 100
                    unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
                    logger.warning(
                        f"[{self.symbol}] TRAILING-STOP TRIGGERED: price {fmt_price(current_price)} "
                        f"dropped {drop_from_peak_pct:.1f}% from peak {fmt_price(self._trailing_peak_price)} "
                        f"(trigger: {fmt_price(trailing_trigger)}). "
                        f"Unrealized: ${unrealized:+.2f}. "
                        f"Liquidating all {len(self._pct_open_positions)} lots."
                    )
                    self._trailing_stop_triggered = True
                    # Re-use the SL cooldown clock so the TF can't immediately
                    # re-allocate the same coin after a trailing stop exit.
                    if self.trade_logger is not None:
                        try:
                            self.trade_logger.client.table("bot_config").update(
                                {"last_stop_loss_at": datetime.now(timezone.utc).isoformat()}
                            ).eq("symbol", self.symbol).execute()
                        except Exception as e:
                            logger.error(
                                f"[{self.symbol}] Failed to write last_stop_loss_at "
                                f"(trailing stop): {e}"
                            )
                    log_event(
                        severity="warn",
                        category="safety",
                        event="trailing_stop_triggered",
                        symbol=self.symbol,
                        message=(
                            f"TF trailing stop: price dropped {drop_from_peak_pct:.1f}% from "
                            f"peak {fmt_price(self._trailing_peak_price)}"
                        ),
                        details={
                            "peak_price": float(self._trailing_peak_price),
                            "trigger_price": float(trailing_trigger),
                            "current_price": float(current_price),
                            "avg_buy_price": float(self.state.avg_buy_price),
                            "drop_from_peak_pct": round(drop_from_peak_pct, 2),
                            "unrealized": unrealized,
                            "activation_pct": float(self.tf_trailing_stop_activation_pct),
                            "trailing_pct": float(self.tf_trailing_stop_pct),
                            "lots": len(self._pct_open_positions),
                        },
                    )

        # --- 39c: TF take-profit check ---
        # Speculare perfetto al 39a: stessa base di calcolo (unrealized vs
        # capital × pct), segno opposto. Cristallizza il profit quando
        # supera la soglia, indipendentemente dal signal TF. Mutuamente
        # esclusivo con stop-loss per costruzione (unrealized non può
        # essere contemporaneamente <= -X e >= +X).
        if (self.managed_by == "tf"
                and self.tf_take_profit_pct > 0
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and not self._take_profit_triggered
                and not self._stop_loss_triggered):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            open_value = self.state.avg_buy_price * self.state.holdings
            profit_threshold = open_value * self.tf_take_profit_pct / 100
            if unrealized >= profit_threshold:
                logger.warning(
                    f"[{self.symbol}] TAKE-PROFIT TRIGGERED: unrealized ${unrealized:.2f} "
                    f">= threshold ${profit_threshold:.2f} "
                    f"({self.tf_take_profit_pct:.0f}% of open value ${open_value:.2f}). "
                    f"Liquidating all {len(self._pct_open_positions)} lots."
                )
                self._take_profit_triggered = True
                log_event(
                    severity="info",
                    category="safety",
                    event="take_profit_triggered",
                    symbol=self.symbol,
                    message=f"TF take-profit: unrealized ${unrealized:.2f} ≥ ${profit_threshold:.2f}",
                    details={
                        "unrealized": unrealized,
                        "threshold": profit_threshold,
                        "pct": self.tf_take_profit_pct,
                        "lots": len(self._pct_open_positions),
                    },
                )

        # --- 45f: TF Profit Lock Exit ---
        # Proactive exit: when NET PnL (realized + unrealized) crosses the
        # threshold, liquidate before the market retraces. Unlike 39a/39c
        # which only see unrealized, Profit Lock includes realized_pnl — so
        # a grid that has already cashed cycles can trigger even with a
        # slightly negative unrealized. Opt-in (tf_profit_lock_enabled).
        #
        # Phase 2 hook (~2 weeks after deploy): if/when 36f Trailing Stop
        # lands, it takes priority over Profit Lock. Add the armed-check
        # right here (e.g. `and not self._trailing_stop_armed`).
        if (self.managed_by in ("tf", "tf_grid")
                and (self.tf_profit_lock_enabled or self.managed_by == "tf_grid")
                and self.tf_profit_lock_pct > 0
                and self.state.holdings > 0
                and self.capital > 0
                and not self._profit_lock_triggered
                and not self._stop_loss_triggered
                and not self._take_profit_triggered):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            net_pnl = float(self.state.realized_pnl or 0) + unrealized
            net_pnl_pct = (net_pnl / self.capital) * 100
            if net_pnl_pct >= self.tf_profit_lock_pct:
                logger.warning(
                    f"[{self.symbol}] PROFIT-LOCK TRIGGERED: net PnL ${net_pnl:.2f} "
                    f"({net_pnl_pct:.1f}%) >= {self.tf_profit_lock_pct:.1f}% of alloc "
                    f"${self.capital:.2f}. Liquidating all {len(self._pct_open_positions)} lots "
                    f"(realized ${self.state.realized_pnl:.2f} + unrealized ${unrealized:.2f})."
                )
                self._profit_lock_triggered = True
                # 45f: reuse the SL cooldown timestamp (Option A — KISS).
                # tf_stop_loss_cooldown_hours applies identically post-lock,
                # so the same coin isn't re-allocated immediately if the
                # cooldown is set. With cooldown=0 (current default), the
                # allocator is free to re-pick the coin next scan.
                if self.trade_logger is not None:
                    try:
                        self.trade_logger.client.table("bot_config").update(
                            {"last_stop_loss_at": datetime.now(timezone.utc).isoformat()}
                        ).eq("symbol", self.symbol).execute()
                    except Exception as e:
                        logger.error(
                            f"[{self.symbol}] Failed to write last_stop_loss_at (profit lock): {e}"
                        )
                log_event(
                    severity="info",
                    category="safety",
                    event="profit_lock_triggered",
                    symbol=self.symbol,
                    message=f"TF profit lock: net PnL {net_pnl_pct:.1f}% ≥ {self.tf_profit_lock_pct:.1f}%",
                    details={
                        "realized": float(self.state.realized_pnl or 0),
                        "unrealized": unrealized,
                        "net_pnl": net_pnl,
                        "net_pnl_pct": net_pnl_pct,
                        "threshold_pct": self.tf_profit_lock_pct,
                        "capital_allocation": self.capital,
                        "lots": len(self._pct_open_positions),
                    },
                )

        # --- 45g: TF Gain-Saturation Circuit Breaker (post-sell path) ---
        # See evaluate_gain_saturation() docstring for the full logic.
        # 49b: a second, proactive entry point lives in grid_runner main loop
        # to cover coins that already have counter>=N at deploy time, or
        # whose holdings hit 0 before any post-sell check could fire.
        self.evaluate_gain_saturation(current_price, trigger_source="post_sell")

        # --- 39b: manual stop-buy check ---
        # Speculare al 39a ma per i bot manuali (BTC/SOL/BONK): quando il
        # drawdown totale eccede la soglia, blocca NUOVE buy — i lot esistenti
        # restano sotto Strategy A (mai sell in perdita). Il flag è latched
        # finché una sell in profit lo resetta (isteresi event-based).
        if (self.managed_by != "tf"
                and self.stop_buy_drawdown_pct > 0
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and not self._stop_buy_active):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            buy_block_threshold = -(self.capital * self.stop_buy_drawdown_pct / 100)
            if unrealized <= buy_block_threshold:
                logger.warning(
                    f"[{self.symbol}] STOP-BUY TRIGGERED: unrealized ${unrealized:.2f} "
                    f"<= threshold ${buy_block_threshold:.2f} "
                    f"({self.stop_buy_drawdown_pct:.0f}% of allocation ${self.capital:.2f}). "
                    f"New buys blocked until profitable sell."
                )
                self._stop_buy_active = True
                log_event(
                    severity="warn",
                    category="safety",
                    event="stop_buy_activated",
                    symbol=self.symbol,
                    message=f"Manual stop-buy: unrealized ${unrealized:.2f} ≤ ${buy_block_threshold:.2f}",
                    details={
                        "unrealized": unrealized,
                        "threshold": buy_block_threshold,
                        "pct": self.stop_buy_drawdown_pct,
                    },
                )

        # --- SELL CHECK (avg-cost trading, brief s70 FASE 1) ---
        # Single decision on state.avg_buy_price: if current_price >=
        # avg_buy_price × (1 + threshold_pct/100), sell one lot of
        # capital_per_trade / current_price (rounded to exchange step).
        # Force-liquidate paths (TF stop-loss / trailing / take-profit /
        # profit-lock / gain-saturation / pending_liquidation) sell
        # everything in one trade.
        if self.state.holdings > 0:
            # 39a/39c/45f/45g/51b: TF override paths still fire on
            # avg-cost, but bypass the "no sell at loss" guard via
            # bot.strategy override in sell_pipeline.
            force_liquidate = (
                self.managed_by in ("tf", "tf_grid")
                and (self._stop_loss_triggered
                     or self._trailing_stop_triggered
                     or self._take_profit_triggered
                     or self._profit_lock_triggered
                     or self._gain_saturation_triggered
                     or self.pending_liquidation)
            )

            # 42a: for TF bots the sell threshold is the greed-decay TP
            # of the current age tier (replaces sell_pct). Manual bots
            # keep sell_pct unchanged. See get_effective_tp() docstring.
            threshold_pct, _age_min, _tier = self.get_effective_tp()
            avg_cost = self.state.avg_buy_price
            sell_trigger = (
                avg_cost * (1 + threshold_pct / 100) if avg_cost > 0 else 0.0
            )

            should_sell = force_liquidate or (
                avg_cost > 0 and current_price >= sell_trigger
            )

            if should_sell:
                if force_liquidate:
                    sell_amount = self.state.holdings
                else:
                    sell_amount = (
                        self.capital_per_trade / current_price
                        if self.capital_per_trade > 0 and current_price > 0
                        else self.state.holdings
                    )
                    sell_amount = min(sell_amount, self.state.holdings)

                trade = self._execute_percentage_sell(
                    current_price,
                    sell_amount=sell_amount,
                    force_all=force_liquidate,
                )
                if trade:
                    trades.append(trade)

                # 39a/39c/39h: after a forced liquidation, flag for
                # cleanup so the grid_runner closes the bot and the TF
                # deallocates next scan. Cycle closed when holdings drop
                # below 1e-10 OR residual notional below MIN_NOTIONAL
                # (economic dust, not sellable on Binance).
                cycle_closed = False
                if self.state.holdings <= 1e-10:
                    cycle_closed = True
                elif self._exchange_filters:
                    residual_notional = self.state.holdings * current_price
                    min_notional = float(self._exchange_filters.get("min_notional", 0) or 0)
                    if min_notional > 0 and residual_notional < min_notional:
                        cycle_closed = True

                if ((self._stop_loss_triggered
                     or self._trailing_stop_triggered
                     or self._take_profit_triggered
                     or self._profit_lock_triggered
                     or self._gain_saturation_triggered)
                        and cycle_closed
                        and not self.pending_liquidation):
                    if self._stop_loss_triggered:
                        trigger = "Stop-loss"
                    elif self._trailing_stop_triggered:
                        trigger = "Trailing-stop"
                    elif self._take_profit_triggered:
                        trigger = "Take-profit"
                    elif self._profit_lock_triggered:
                        trigger = "Profit-lock"
                    else:
                        trigger = "Gain-saturation"
                    logger.warning(
                        f"[{self.symbol}] {trigger} liquidation complete "
                        f"(holdings={self.state.holdings:.6f}). "
                        f"Flagging pending_liquidation for TF cleanup."
                    )
                    self.pending_liquidation = True
            else:
                age_str = f", age={_age_min:.0f}min" if _age_min is not None else ""
                logger.debug(
                    f"[{self.symbol}] Nessuna sell: prezzo {fmt_price(current_price)} < "
                    f"trigger {fmt_price(sell_trigger)} "
                    f"(avg cost {fmt_price(avg_cost)}, threshold={threshold_pct}%{age_str})"
                )

        # --- BUY CHECK ---
        now = time.time()
        buy_cooldown_active = (
            self.buy_cooldown_seconds > 0
            and self._pct_last_buy_price != 0  # cooldown doesn't block the very first buy
            and (now - self._last_buy_time) < self.buy_cooldown_seconds
        )

        if not buy_cooldown_active:
            if self._pct_last_buy_price == 0:
                if self.state.holdings > 0:
                    # Already have positions (e.g. switched from fixed mode mid-run).
                    # Skip the first buy and use avg_buy_price as the reference.
                    self._pct_last_buy_price = self.state.avg_buy_price
                    if not self._pct_open_positions:
                        self._pct_open_positions.append({
                            "amount": self.state.holdings,
                            "price": self.state.avg_buy_price,
                        })
                    logger.info(
                        f"[{self.symbol}] Pct mode: existing holdings found, skipping first buy. "
                        f"Ref price set to avg buy {fmt_price(self.state.avg_buy_price)}"
                    )
                else:
                    # No holdings — establish reference with first buy
                    trade = self._execute_percentage_buy(current_price)
                    if trade:
                        trades.append(trade)
            else:
                buy_trigger = self._pct_last_buy_price * (1 - self.buy_pct / 100)
                if current_price <= buy_trigger:
                    trade = self._execute_percentage_buy(current_price)
                    if trade:
                        trades.append(trade)

        # --- IDLE RE-ENTRY / RECALIBRATE CHECK ---
        # After idle_reentry_hours of inactivity:
        #   holdings <= 0 → force a re-entry buy at market (existing behaviour)
        #   holdings >  0 → recalibrate: reset buy reference to current price
        #                   so the next cycle can evaluate a normal buy.
        #                   This unsticks bots with dust residuals that keep
        #                   holdings > 0 forever, blocking the original idle path.
        # Guard: do NOT act if bot has been deactivated via is_active=false.
        if (self.is_active
                and self._pct_last_buy_price > 0
                and self._last_trade_time is not None
                and self.idle_reentry_hours > 0):
            elapsed = (datetime.utcnow() - self._last_trade_time).total_seconds() / 3600
            # Log once per elapsed-hour boundary so progress is always visible in logs
            elapsed_h = int(elapsed)
            if elapsed_h != self._idle_logged_hour:
                self._idle_logged_hour = elapsed_h
                mode = "RE-ENTRY" if self.state.holdings <= 0 else "RECALIBRATE"
                logger.info(
                    f"[{self.symbol}] IDLE {mode} CHECK: "
                    f"elapsed={elapsed:.2f}h / threshold={self.idle_reentry_hours}h "
                    f"| last_trade={self._last_trade_time:%Y-%m-%d %H:%M:%S} UTC "
                    f"| ref_price={fmt_price(self._pct_last_buy_price)} "
                    f"| holdings={self.state.holdings:.6f} "
                    f"| will_fire={'YES' if elapsed >= self.idle_reentry_hours else 'NOT YET'}"
                )
            if elapsed >= self.idle_reentry_hours:
                if self.state.holdings <= 0:
                    # --- Path A: no holdings → force re-entry buy ---
                    logger.info(
                        f"[{self.symbol}] Idle re-entry after {elapsed:.1f}h: "
                        f"resetting reference from {fmt_price(self._pct_last_buy_price)} "
                        f"to {fmt_price(current_price)}"
                    )
                    self.idle_reentry_alerts.append({
                        "symbol": self.symbol,
                        "elapsed_hours": elapsed,
                        "reference_price": current_price,
                    })
                    self._pct_last_buy_price = 0  # triggers "first buy at market" reason in execute_buy
                    trade = self._execute_percentage_buy(current_price)
                    if trade:
                        trades.append(trade)
                else:
                    # --- Path B: holdings > 0 → recalibrate buy reference ---
                    # Brief s70 FASE 2 (CEO + Max 2026-05-09): skip recalibrate
                    # if current_price > avg_buy_price. Prevents the
                    # Scenario 4 loop (lateral-up market) where the bot would
                    # mediate up — buying progressively above avg, gonfiando
                    # il cost basis. Coerente con Strategy A "no sell at loss":
                    # specularmente "no buy reference reset above avg".
                    avg = self.state.avg_buy_price
                    if avg > 0 and current_price > avg:
                        logger.info(
                            f"[{self.symbol}] Idle recalibrate skipped after {elapsed:.1f}h: "
                            f"price {fmt_price(current_price)} > avg cost {fmt_price(avg)}. "
                            f"Reference unchanged at {fmt_price(self._pct_last_buy_price)}."
                        )
                        self.idle_reentry_alerts.append({
                            "symbol": self.symbol,
                            "elapsed_hours": elapsed,
                            "reference_price": self._pct_last_buy_price,
                            "recalibrate": False,
                            "skipped_above_avg": True,
                        })
                        log_event(
                            severity="info",
                            category="trade_audit",
                            event="idle_recalibrate_skipped",
                            symbol=self.symbol,
                            message=(
                                f"Skipped recalibrate: price {current_price} > avg {avg}"
                            ),
                            details={
                                "current_price": float(current_price),
                                "avg_buy_price": float(avg),
                                "elapsed_hours": float(elapsed),
                                "last_buy_ref": float(self._pct_last_buy_price),
                            },
                        )
                    else:
                        logger.info(
                            f"[{self.symbol}] Idle recalibrate after {elapsed:.1f}h: "
                            f"resetting buy reference from {fmt_price(self._pct_last_buy_price)} "
                            f"to {fmt_price(current_price)} (holdings={self.state.holdings:.6f})"
                        )
                        self.idle_reentry_alerts.append({
                            "symbol": self.symbol,
                            "elapsed_hours": elapsed,
                            "reference_price": current_price,
                            "recalibrate": True,
                        })
                        self._pct_last_buy_price = current_price
                    # Always advance _last_trade_time so the next idle check
                    # fires after another window (avoids per-cycle log spam).
                    self._last_trade_time = datetime.utcnow()
                    self._idle_logged_hour = -1

        return trades

    # ------------------------------------------------------------------
    # Pipeline wrappers — delegate to buy_pipeline / sell_pipeline.
    # Kept as methods so existing callers (grid_runner, tests) work unchanged.
    # ------------------------------------------------------------------

    def _execute_buy(self, level: GridLevel, price: float) -> Optional[dict]:
        return buy_pipeline.execute_buy(self, level, price)

    def _execute_percentage_buy(self, price: float) -> Optional[dict]:
        return buy_pipeline.execute_percentage_buy(self, price)

    def _execute_sell(self, level: GridLevel, price: float) -> Optional[dict]:
        return sell_pipeline.execute_sell(self, level, price)

    def _execute_percentage_sell(
        self,
        price: float,
        sell_amount: Optional[float] = None,
        force_all: bool = False,
    ) -> Optional[dict]:
        return sell_pipeline.execute_percentage_sell(
            self, price, sell_amount=sell_amount, force_all=force_all
        )

    def _activate_sell_level(self, buy_level: GridLevel, amount: float):
        return buy_pipeline.activate_sell_level(self, buy_level, amount)

    def _activate_buy_level(self, sell_level: GridLevel):
        return sell_pipeline.activate_buy_level(self, sell_level)

    def evaluate_gain_saturation(self, current_price: float, trigger_source: str) -> bool:
        return sell_pipeline.evaluate_gain_saturation(self, current_price, trigger_source)

    def get_effective_tp(self) -> tuple:
        return sell_pipeline.get_effective_tp(self)

    # ------------------------------------------------------------------
    # Read-only utility methods (kept here — small, no extraction value).
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return current grid status for dashboard/Telegram."""
        if not self.state:
            return {"status": "not_initialized"}

        filled_buys = sum(1 for l in self.state.levels if l.side == "buy" and l.filled)
        filled_sells = sum(1 for l in self.state.levels if l.side == "sell" and l.filled)
        active_buys = sum(1 for l in self.state.levels if l.side == "buy" and not l.filled)
        active_sells = sum(1 for l in self.state.levels if l.side == "sell" and not l.filled and l.order_amount > 0)

        # available_capital = allocated - invested + received - reserve
        available_capital = self._available_cash()

        return {
            "symbol": self.symbol,
            "strategy": self.strategy,
            "mode": self.mode,
            "center_price": self.state.center_price,
            "range": (
                f"${self.state.last_price * (1 - self.buy_pct / 100):.{self._price_decimals(self.state.center_price)}f} (-{self.buy_pct}%) - "
                f"${self.state.last_price * (1 + self.sell_pct / 100):.{self._price_decimals(self.state.center_price)}f} (+{self.sell_pct}%)"
                if self.grid_mode == "percentage" else
                f"${self.state.lower_bound:.{self._price_decimals(self.state.center_price)}f} - ${self.state.upper_bound:.{self._price_decimals(self.state.center_price)}f}"
            ),
            "last_price": self.state.last_price,
            "levels": {
                "total": self.num_levels,
                "active_buys": active_buys,
                "active_sells": active_sells,
                "filled_buys": filled_buys,
                "filled_sells": filled_sells,
            },
            "holdings": self.state.holdings,
            "avg_buy_price": self.state.avg_buy_price,
            "capital": self.capital,
            "available_capital": available_capital,
            "invested": self.state.total_invested,
            "received": self.state.total_received,
            "fees": self.state.total_fees,
            "realized_pnl": self.state.realized_pnl,
            "unrealized_pnl": self.state.unrealized_pnl,
            "trades_today": self._daily_trade_count,
        }

    def should_reset_grid(self, current_price: float) -> bool:
        """
        Check if the price has moved too far from the grid center.
        If price is outside the grid range, we should create a new grid.
        In percentage mode there is no fixed range, so never reset.
        """
        if not self.state:
            return True

        if self.grid_mode == "percentage":
            return False

        margin = (self.state.upper_bound - self.state.lower_bound) * 0.1
        return (
            current_price < self.state.lower_bound - margin
            or current_price > self.state.upper_bound + margin
        )
