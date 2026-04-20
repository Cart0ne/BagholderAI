"""
BagHolderAI - Grid Bot (Brain #1)
The soldier. Buys low, sells high, no prediction needed.
Profits from volatility by placing orders at regular intervals within a range.

Paper trading mode: uses real market prices, simulates fills.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from utils.formatting import fmt_price
from config.settings import HardcodedRules

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
        tf_stop_loss_pct: float = 0.0,  # 39a: TF stop-loss threshold as % of allocation (0 = disabled)
        stop_buy_drawdown_pct: float = 0.0,  # 39b: manual stop-buy threshold as % of allocation (0 = disabled)
        tf_take_profit_pct: float = 0.0,  # 39c: TF take-profit threshold as % of allocation (0 = disabled)
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
        self.allocated_at: Optional[datetime] = allocated_at
        self.greed_decay_tiers: Optional[list] = greed_decay_tiers
        self.is_active: bool = True  # controlled via Supabase bot_config
        self.pending_liquidation: bool = False  # TF rotation trigger
        self.managed_by: str = "manual"  # "manual" or "trend_follower"
        self._stop_loss_triggered: bool = False  # 39a: latched once threshold is breached
        self._stop_buy_active: bool = False  # 39b: latched once drawdown breached, resets on profitable sell
        self._take_profit_triggered: bool = False  # 39c: latched once +pct threshold reached
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

    def restore_state_from_db(self):
        """
        Restore holdings, avg_buy_price, and P&L from historical trades in DB.
        Call after setup_grid() on startup to recover v1 positions.
        """
        if not self.trade_logger or not self.state:
            return

        pos = self.trade_logger.get_open_position(self.symbol)
        if pos["holdings"] <= 0:
            logger.info(f"No open position found in DB for {self.symbol}.")
            return

        self.state.holdings = pos["holdings"]
        self.state.avg_buy_price = pos["avg_buy_price"]
        self.state.realized_pnl = pos["realized_pnl"]
        self.state.total_fees = pos["total_fees"]
        self.state.total_invested = pos["total_invested"]
        self.state.total_received = pos["total_received"]

        # Distribute recovered holdings across sell levels
        sell_levels = [l for l in self.state.levels if l.side == "sell"]
        if sell_levels:
            amount_per_level = self.state.holdings / len(sell_levels)
            for sl in sell_levels:
                sl.order_amount = round(amount_per_level, 8)

        logger.info(
            f"Restored from DB: {pos['holdings']:.6f} {self.symbol} "
            f"@ avg {fmt_price(pos['avg_buy_price'])} | "
            f"Realized P&L: ${pos['realized_pnl']:.4f}"
        )

    def init_percentage_state_from_db(self):
        """
        Restore percentage mode state from DB on startup.
        Reconstructs the FIFO open-positions queue, last buy price,
        and cash accounting (total_invested / total_received) by replaying
        all v3 trades for this symbol chronologically.
        """
        if not self.trade_logger:
            return
        try:
            result = (
                self.trade_logger.client.table("trades")
                .select("side,amount,price,cost,created_at")
                .eq("symbol", self.symbol)
                .eq("config_version", "v3")
                .order("created_at", desc=False)
                .execute()
            )
            trades = result.data or []
        except Exception as e:
            logger.warning(f"[{self.symbol}] Could not load pct state from DB: {e}")
            return

        open_positions = []
        last_buy_price = 0.0
        total_invested = 0.0
        total_received = 0.0

        for t in trades:
            side = t.get("side")
            amount = float(t.get("amount", 0))
            price = float(t.get("price", 0))
            cost = float(t.get("cost") or (amount * price))
            if side == "buy":
                total_invested += cost
                open_positions.append({"amount": amount, "price": price})
                last_buy_price = price
            elif side == "sell":
                revenue = amount * price
                total_received += revenue
                if open_positions:
                    # FIFO: consume oldest lot(s) to match sell amount
                    remaining = amount
                    while remaining > 1e-12 and open_positions:
                        oldest = open_positions[0]
                        if oldest["amount"] <= remaining + 1e-12:
                            remaining -= oldest["amount"]
                            open_positions.pop(0)
                        else:
                            oldest["amount"] -= remaining
                            remaining = 0

        self._pct_open_positions = open_positions
        self._pct_last_buy_price = last_buy_price

        # Restore last trade time so idle re-entry countdown is correct.
        # Convert to UTC-naive so comparison with datetime.utcnow() is always correct
        # regardless of the timezone offset stored in the DB timestamp.
        if trades:
            try:
                dt_str = trades[-1].get("created_at", "")
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                    # Only overwrite if DB value is newer than in-memory value.
                    # The idle-recalibrate path sets _last_trade_time = utcnow() without
                    # writing to DB; the self-heal re-init must not clobber that.
                    if self._last_trade_time is None or dt > self._last_trade_time:
                        self._last_trade_time = dt
                        self._idle_logged_hour = -1  # reset so first eval logs immediately
                        logger.info(f"[{self.symbol}] Restored _last_trade_time = {dt:%Y-%m-%d %H:%M:%S} UTC")
                    else:
                        logger.info(
                            f"[{self.symbol}] DB _last_trade_time ({dt:%Y-%m-%d %H:%M:%S}) "
                            f"older than in-memory ({self._last_trade_time:%Y-%m-%d %H:%M:%S}), keeping in-memory"
                        )
            except Exception:
                pass
        else:
            logger.info(f"[{self.symbol}] No v3 trades found — _last_trade_time stays None")

        # Reconstruct cash accounting + holdings so sell logic fires correctly
        if self.state:
            self.state.total_invested = total_invested
            self.state.total_received = total_received

            # Rebuild state.holdings and state.avg_buy_price from open lots.
            # Without this, _check_percentage_and_execute() sees holdings=0
            # and never triggers sells even when _pct_open_positions is populated.
            if open_positions:
                total_amount = sum(lot["amount"] for lot in open_positions)
                weighted_cost = sum(lot["amount"] * lot["price"] for lot in open_positions)
                self.state.holdings = total_amount
                self.state.avg_buy_price = weighted_cost / total_amount if total_amount > 0 else 0.0
            else:
                self.state.holdings = 0.0
                self.state.avg_buy_price = 0.0

        available = self.capital - total_invested + total_received
        reserve_str = ""
        if self.reserve_ledger:
            try:
                reserve = self.reserve_ledger.get_reserve_total(self.symbol)
                if reserve > 0:
                    available -= reserve
                    reserve_str = f" - ${reserve:.2f} reserve"
            except Exception as e:
                logger.warning(f"[{self.symbol}] Could not fetch reserve total for cash log: {e}")

        logger.info(
            f"[{self.symbol}] Pct mode restored: {len(open_positions)} open lots, "
            f"holdings={self.state.holdings:.6f}, "
            f"avg_buy={fmt_price(self.state.avg_buy_price)}, "
            f"last buy {fmt_price(last_buy_price)}"
        )
        logger.info(
            f"[{self.symbol}] Cash restored: ${self.capital:.2f} allocated"
            f" - ${total_invested:.2f} invested"
            f" + ${total_received:.2f} sold"
            f"{reserve_str}"
            f" = ${available:.2f} available"
        )

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

    def _execute_buy(self, level: GridLevel, price: float) -> Optional[dict]:
        """Execute a buy at a grid level."""
        # 39b: manual stop-buy gate also for fixed-grid mode (for parity,
        # even if manual bots run percentage today).
        if self._stop_buy_active:
            logger.info(
                f"[{self.symbol}] BUY BLOCKED: stop-buy active "
                f"(drawdown > {self.stop_buy_drawdown_pct}% of allocation)."
            )
            return None

        standard_cost = level.order_amount * price

        # Snapshot for Telegram verification (reserve-aware)
        cash_before = self._available_cash()

        # Last-shot logic: use remaining cash if below standard cost but above minimum
        if cash_before >= standard_cost:
            actual_cost = standard_cost
            last_shot = False
        elif cash_before >= HardcodedRules.MIN_LAST_SHOT_USD:
            actual_cost = cash_before
            last_shot = True
            logger.info(
                f"LAST SHOT: buying with remaining ${cash_before:.2f} "
                f"(reduced from standard ${standard_cost:.2f}) for {self.symbol}"
            )
        else:
            logger.warning(
                f"Insufficient cash for BUY {self.symbol}: "
                f"need ${standard_cost:.2f}, have ${cash_before:.2f}. Skipping level {fmt_price(level.price)}."
            )
            self.skipped_buys.append({
                "symbol": self.symbol,
                "level_price": level.price,
                "cost": standard_cost,
                "cash_before": cash_before,
            })
            return None

        amount = actual_cost / price
        if self._exchange_filters:
            from utils.exchange_filters import round_to_step
            amount = round_to_step(amount, self._exchange_filters["lot_step_size"])
            cost = amount * price  # recalculate cost after rounding
        else:
            cost = actual_cost
        fee = cost * self.FEE_RATE

        # Mark level as filled
        level.filled = True
        level.filled_at = time.time()

        # Update state — weighted average buy price
        old_holdings = self.state.holdings
        old_avg = self.state.avg_buy_price
        self.state.total_invested += cost
        self.state.total_fees += fee
        self.state.holdings += amount

        # Recalculate average buy price (weighted average on buys only)
        if self.state.holdings > 0:
            self.state.avg_buy_price = (old_avg * old_holdings + price * amount) / self.state.holdings

        # Activate the corresponding sell level above
        self._activate_sell_level(level, amount)

        self._daily_trade_count += 1
        self._last_buy_time = time.time()  # Task 5: record buy timestamp

        reason = f"Grid buy at level {fmt_price(level.price)} (price dropped to {fmt_price(price)})"
        if last_shot:
            reason = f"LAST SHOT: {reason} — spent remaining ${cost:.2f}"

        trade_data = {
            "symbol": self.symbol,
            "side": "buy",
            "amount": amount,
            "price": price,
            "cost": cost,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": reason,
            "mode": self.mode,
            "cash_before": cash_before,
            "capital_allocated": self.capital,
            "managed_by": getattr(self, "managed_by", "manual"),
        }

        # Log to database
        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

        logger.info(
            f"BUY {amount:.6f} {self.symbol} @ {fmt_price(price)} "
            f"(cost: ${cost:.2f}, fee: ${fee:.4f})"
        )

        return trade_data

    def _execute_sell(self, level: GridLevel, price: float) -> Optional[dict]:
        """
        Execute a sell at a grid level.

        HARDCODED RULE: Strategy A NEVER sells at a loss.
        """
        # Task 10: enforce minimum profit target before selling.
        # min_profit_pct is a percentage (e.g. 1.0 = 1%), aligned with buy_pct / sell_pct.
        if self.min_profit_pct > 0 and self.state.avg_buy_price > 0:
            min_price = self.state.avg_buy_price * (1 + self.min_profit_pct / 100)
            if price < min_price:
                logger.info(
                    f"SKIP: sell at {fmt_price(price)} below min profit target "
                    f"(need {fmt_price(min_price)}, {self.min_profit_pct:.1f}% above avg buy)"
                )
                return None

        if self.strategy == "A" and price < self.state.avg_buy_price:
            # 39a/39c: TF bots can override Strategy A on stop-loss,
            # bearish exit, or take-profit (mixed-lots liquidation).
            tf_override = (
                self.managed_by == "trend_follower"
                and (self._stop_loss_triggered
                     or self._take_profit_triggered
                     or self.pending_liquidation)
            )
            if tf_override:
                if self._stop_loss_triggered:
                    reason = "STOP-LOSS"
                elif self._take_profit_triggered:
                    reason = "TAKE-PROFIT"
                else:
                    reason = "BEARISH EXIT"
                logger.warning(
                    f"{reason} OVERRIDE: Sell at {fmt_price(price)} < "
                    f"avg buy {fmt_price(self.state.avg_buy_price)} ({self.symbol})."
                )
            else:
                logger.info(
                    f"BLOCKED: Sell at {fmt_price(price)} < avg buy {fmt_price(self.state.avg_buy_price)}. "
                    f"Strategy A never sells at loss."
                )
                return None

        # Sell the amount that was bought at the corresponding buy level
        amount = level.order_amount

        if amount <= 0:
            return None

        # Guard: skip sell if insufficient holdings (1e-10 tolerance for floating-point accumulation)
        if amount > self.state.holdings + 1e-10:
            logger.warning(
                f"Insufficient holdings for SELL {self.symbol}: "
                f"need {amount:.6f}, have {self.state.holdings:.6f}. Skipping level {fmt_price(level.price)}."
            )
            self.skipped_sells.append({
                "symbol": self.symbol,
                "level_price": level.price,
                "amount_needed": amount,
                "holdings": self.state.holdings,
            })
            return None

        revenue = amount * price
        fee = revenue * self.FEE_RATE

        # Snapshot for Telegram verification
        holdings_value_before = self.state.holdings * price

        # Calculate realized P&L for this trade
        cost_basis = amount * self.state.avg_buy_price
        buy_fee = cost_basis * self.FEE_RATE
        realized_pnl = revenue - cost_basis - fee - buy_fee

        # Mark level as filled
        level.filled = True
        level.filled_at = time.time()

        # Update state — do NOT touch avg_buy_price on sells
        self.state.total_received += revenue
        self.state.total_fees += fee + buy_fee
        self.state.holdings -= amount
        self.state.realized_pnl += realized_pnl
        self.state.daily_realized_pnl += realized_pnl

        # 39b: profitable sell releases the manual stop-buy gate.
        if self._stop_buy_active and realized_pnl > 0:
            self._stop_buy_active = False
            logger.info(
                f"[{self.symbol}] STOP-BUY RESET: profitable sell ${realized_pnl:.2f} "
                f"cleared the block. Buys re-enabled."
            )

        # Reset avg_buy_price when fully sold out
        if self.state.holdings <= 0:
            self.state.holdings = 0
            self.state.avg_buy_price = 0

        # Reactivate the corresponding buy level below
        self._activate_buy_level(level)

        self._daily_trade_count += 1

        trade_data = {
            "symbol": self.symbol,
            "side": "sell",
            "amount": amount,
            "price": price,
            "cost": revenue,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": f"Grid sell at level {fmt_price(level.price)} (price rose to {fmt_price(price)})",
            "mode": self.mode,
            "realized_pnl": realized_pnl,
            "holdings_value_before": holdings_value_before,
            "managed_by": getattr(self, "managed_by", "manual"),
        }

        # Log to database
        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

        logger.info(
            f"SELL {amount:.6f} {self.symbol} @ {fmt_price(price)} "
            f"(revenue: ${revenue:.2f}, fee: ${fee:.4f}, pnl: ${realized_pnl:.4f})"
        )

        return trade_data

    # ------------------------------------------------------------------
    # Percentage mode methods
    # ------------------------------------------------------------------

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

        # --- 39a: TF stop-loss check ---
        # Evaluated on the entire position (not per-lot) so a partial rebound
        # on one lot doesn't mask the overall bleed. Only armed for TF bots
        # (manual bots keep Strategy A's unconditional "never sell at loss").
        if (self.managed_by == "trend_follower"
                and self.tf_stop_loss_pct > 0
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and not self._stop_loss_triggered):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            loss_threshold = -(self.capital * self.tf_stop_loss_pct / 100)
            if unrealized <= loss_threshold:
                logger.warning(
                    f"[{self.symbol}] STOP-LOSS TRIGGERED: unrealized ${unrealized:.2f} "
                    f"<= threshold ${loss_threshold:.2f} "
                    f"({self.tf_stop_loss_pct:.0f}% of allocation ${self.capital:.2f}). "
                    f"Liquidating all {len(self._pct_open_positions)} lots."
                )
                self._stop_loss_triggered = True

        # --- 39c: TF take-profit check ---
        # Speculare perfetto al 39a: stessa base di calcolo (unrealized vs
        # capital × pct), segno opposto. Cristallizza il profit quando
        # supera la soglia, indipendentemente dal signal TF. Mutuamente
        # esclusivo con stop-loss per costruzione (unrealized non può
        # essere contemporaneamente <= -X e >= +X).
        if (self.managed_by == "trend_follower"
                and self.tf_take_profit_pct > 0
                and self.state.holdings > 0
                and self.state.avg_buy_price > 0
                and not self._take_profit_triggered
                and not self._stop_loss_triggered):
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
            profit_threshold = self.capital * self.tf_take_profit_pct / 100
            if unrealized >= profit_threshold:
                logger.warning(
                    f"[{self.symbol}] TAKE-PROFIT TRIGGERED: unrealized ${unrealized:.2f} "
                    f">= threshold ${profit_threshold:.2f} "
                    f"({self.tf_take_profit_pct:.0f}% of allocation ${self.capital:.2f}). "
                    f"Liquidating all {len(self._pct_open_positions)} lots."
                )
                self._take_profit_triggered = True

        # --- 39b: manual stop-buy check ---
        # Speculare al 39a ma per i bot manuali (BTC/SOL/BONK): quando il
        # drawdown totale eccede la soglia, blocca NUOVE buy — i lot esistenti
        # restano sotto Strategy A (mai sell in perdita). Il flag è latched
        # finché una sell in profit lo resetta (isteresi event-based).
        if (self.managed_by != "trend_follower"
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

        # --- SELL CHECK ---
        # Iterate ALL open lots; sell any whose trigger is hit.
        # FIFO order: among triggered lots, sell oldest first.
        # A lot can sell even if an older lot hasn't triggered yet.
        if self.state.holdings > 0 and not self._pct_open_positions and not self._self_heal_attempted:
            # Self-heal: holdings exist but open-positions queue is empty → state diverged.
            # Re-init from DB so the sell check can fire correctly.
            # Only attempt once: if DB replay still yields no positions (e.g. dust residual),
            # retrying every cycle is futile and clobbers in-memory state set by idle recalibrate.
            self._self_heal_attempted = True
            logger.warning(
                f"[{self.symbol}] WARN: holdings={self.state.holdings:.6f} ma _pct_open_positions è vuota. "
                f"Re-init dal DB..."
            )
            self.init_percentage_state_from_db()
            if not self._pct_open_positions:
                logger.warning(
                    f"[{self.symbol}] Self-heal: DB replay still yielded no open positions (dust residual). "
                    f"Will not retry until next real trade."
                )

        if self.state.holdings > 0 and self._pct_open_positions:
            # 39a/39c: stop-loss, take-profit, or pending-liquidation
            # overrides the per-lot trigger — sell every open lot in one
            # pass. For stop-loss/bearish this includes underwater lots;
            # for take-profit it includes lots that haven't individually
            # hit their sell_pct yet.
            force_liquidate = (
                self.managed_by == "trend_follower"
                and (self._stop_loss_triggered
                     or self._take_profit_triggered
                     or self.pending_liquidation)
            )
            if force_liquidate:
                lots_to_sell = list(self._pct_open_positions)
            else:
                # 42a: for TF bots the sell threshold is the greed-decay TP of
                # the current age tier (replaces sell_pct). Manual bots keep
                # sell_pct unchanged. See get_effective_tp() docstring.
                threshold_pct, _age_min, _tier = self.get_effective_tp()
                lots_to_sell = [
                    lot for lot in self._pct_open_positions
                    if current_price >= lot["price"] * (1 + threshold_pct / 100)
                ]
            if lots_to_sell:
                # Reorder queue: triggered lots first (FIFO), then untriggered (FIFO)
                sell_ids = {id(lot) for lot in lots_to_sell}
                untriggered = [l for l in self._pct_open_positions if id(l) not in sell_ids]
                self._pct_open_positions = lots_to_sell + untriggered
                for _ in lots_to_sell:
                    trade = self._execute_percentage_sell(current_price)
                    if trade:
                        trades.append(trade)
                # 39a/39c/39h: after a forced liquidation (stop-loss or
                # take-profit), flag for cleanup so the grid_runner closes
                # the bot and the TF deallocates next scan.
                #
                # 39h: the old check was holdings <= 1e-10, which missed the
                # common case where a sub-step dust residual remains
                # (e.g. 0.1 TST stuck because Binance step_size=0.1 but the
                # lot's float holdings drift to 0.1 via round_to_step).
                # Without this flag, the bot would re-buy on the next tick
                # and thrash through more stop-losses in the same cycle
                # (PHB/TST observed before 39f/39h).
                #
                # New condition: queue empty after the cascade OR residual
                # holdings below Binance MIN_NOTIONAL (economic dust, not
                # sellable anyway). Either way the cycle is over.
                cycle_closed = False
                if not self._pct_open_positions:
                    cycle_closed = True
                elif self._exchange_filters and self.state.holdings > 0:
                    residual_notional = self.state.holdings * current_price
                    min_notional = float(self._exchange_filters.get("min_notional", 0) or 0)
                    if min_notional > 0 and residual_notional < min_notional:
                        cycle_closed = True
                elif self.state.holdings <= 1e-10:
                    cycle_closed = True

                if ((self._stop_loss_triggered or self._take_profit_triggered)
                        and cycle_closed
                        and not self.pending_liquidation):
                    trigger = "Stop-loss" if self._stop_loss_triggered else "Take-profit"
                    logger.warning(
                        f"[{self.symbol}] {trigger} liquidation complete "
                        f"(holdings={self.state.holdings:.6f}, queue={len(self._pct_open_positions)} lots). "
                        f"Flagging pending_liquidation for TF cleanup."
                    )
                    self.pending_liquidation = True
            else:
                # 42a: same threshold used above for the sell decision
                log_threshold, log_age, _ = self.get_effective_tp()
                nearest_trigger = min(
                    lot["price"] * (1 + log_threshold / 100)
                    for lot in self._pct_open_positions
                )
                age_str = f", age={log_age:.0f}min" if log_age is not None else ""
                logger.debug(
                    f"[{self.symbol}] Nessuna sell: prezzo {fmt_price(current_price)} < "
                    f"trigger più vicino {fmt_price(nearest_trigger)} "
                    f"(threshold={log_threshold}%{age_str}, {len(self._pct_open_positions)} lotti)"
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
                    self._last_trade_time = datetime.utcnow()
                    self._idle_logged_hour = -1

        return trades

    def get_effective_tp(self) -> tuple:
        """42a: Greed decay for TF bots. Returns (threshold_pct, age_minutes, tier_used).

        For TF bots with a valid allocated_at + greed_decay_tiers, returns the
        tp_pct of the highest-minutes tier whose threshold is <= age. When
        age is below the lowest tier's minutes (pre-first-tier window), the
        first tier's tp_pct is used — greed decay is authoritative from t=0,
        not a gradual override that kicks in after N minutes.

        For anything else (manual bots, missing allocated_at, empty/bad
        tiers), returns (self.sell_pct, None, None) — the legacy behavior.

        CEO design (2026-04-20): greed decay IS the sell threshold for TF
        bots; sell_pct is ignored. Manual bots keep sell_pct unchanged.
        """
        if self.managed_by != "trend_follower":
            return (self.sell_pct, None, None)
        if self.allocated_at is None or not self.greed_decay_tiers:
            return (self.sell_pct, None, None)

        now = datetime.now(timezone.utc)
        alloc = self.allocated_at
        if alloc.tzinfo is None:
            alloc = alloc.replace(tzinfo=timezone.utc)
        age_minutes = (now - alloc).total_seconds() / 60.0

        # Pick highest-minutes tier whose threshold <= age. Sort ascending so
        # we can walk until we overshoot. Skip malformed tiers defensively —
        # the UI editor is user-facing and could write garbage.
        tier_used = None
        try:
            tiers = sorted(
                (t for t in self.greed_decay_tiers
                 if isinstance(t, dict) and "minutes" in t and "tp_pct" in t),
                key=lambda t: float(t["minutes"]),
            )
        except Exception:
            return (self.sell_pct, age_minutes, None)
        if not tiers:
            return (self.sell_pct, age_minutes, None)
        for tier in tiers:
            try:
                if age_minutes >= float(tier["minutes"]):
                    tier_used = tier
                else:
                    break
            except Exception:
                continue

        # Pre-first-tier window: use the first tier's tp_pct. This is the
        # "lock-in high threshold from t=0" behavior the CEO wants — no
        # sell_pct fallback leaking micro-trades before greed decay starts.
        if tier_used is None:
            tier_used = tiers[0]

        try:
            return (float(tier_used["tp_pct"]), age_minutes, tier_used)
        except Exception:
            return (self.sell_pct, age_minutes, None)

    def _execute_percentage_buy(self, price: float) -> Optional[dict]:
        """Execute a percentage-mode buy: spend capital_per_trade USDT at current price."""
        if price <= 0:
            logger.error(f"Invalid price {price} for {self.symbol}, skipping pct buy")
            return None

        # 39b: manual stop-buy gate. When drawdown threshold has been breached
        # on this manual bot, reject any new buy until a profitable sell
        # resets the flag. Existing lots continue to follow Strategy A.
        if self._stop_buy_active:
            logger.info(
                f"[{self.symbol}] BUY BLOCKED: stop-buy active "
                f"(drawdown > {self.stop_buy_drawdown_pct}% of allocation). "
                f"Waiting for profitable sell to reset."
            )
            return None

        standard_cost = self.capital_per_trade
        cash_before = self._available_cash()

        # Last-shot logic: use remaining cash if below standard cost but above minimum.
        # Sweep logic: if remaining cash after this buy < one trade size, spend it all now.
        if cash_before >= standard_cost:
            remaining_after = cash_before - standard_cost
            if 0 < remaining_after < standard_cost:
                cost = cash_before  # sweep stranded remainder into this trade
                last_shot = True
                logger.info(
                    f"SWEEP BUY: spending ${cash_before:.2f} (remaining ${remaining_after:.2f} "
                    f"< trade size ${standard_cost:.2f}) for {self.symbol}"
                )
            else:
                cost = standard_cost
                last_shot = False
        elif cash_before >= HardcodedRules.MIN_LAST_SHOT_USD:
            cost = cash_before
            last_shot = True
            logger.info(
                f"LAST SHOT: buying with remaining ${cash_before:.2f} "
                f"(reduced from standard ${standard_cost:.2f}) for {self.symbol}"
            )
        else:
            logger.warning(
                f"Insufficient cash for BUY {self.symbol}: "
                f"need ${standard_cost:.2f}, have ${cash_before:.2f}. Skipping pct buy."
            )
            self.skipped_buys.append({
                "symbol": self.symbol,
                "level_price": price,
                "cost": standard_cost,
                "cash_before": cash_before,
            })
            return None

        amount = cost / price

        # Round to valid step size and validate against exchange filters
        if self._exchange_filters:
            from utils.exchange_filters import round_to_step, validate_order
            amount = round_to_step(amount, self._exchange_filters["lot_step_size"])
            valid, reason_reject = validate_order(self.symbol, amount, price, self._exchange_filters)
            if not valid:
                logger.warning(f"[{self.symbol}] BUY order rejected: {reason_reject}")
                return None
            cost = amount * price  # recalculate cost after rounding

        fee = cost * self.FEE_RATE

        old_last_buy = self._pct_last_buy_price
        old_holdings = self.state.holdings
        old_avg = self.state.avg_buy_price

        self.state.total_invested += cost
        self.state.total_fees += fee
        self.state.holdings += amount

        if self.state.holdings > 0:
            self.state.avg_buy_price = (old_avg * old_holdings + price * amount) / self.state.holdings

        self._pct_last_buy_price = price
        self._pct_open_positions.append({"amount": amount, "price": price})
        self._daily_trade_count += 1
        self._last_buy_time = time.time()
        self._last_trade_time = datetime.utcnow()
        self._self_heal_attempted = False  # real trade happened, allow self-heal again if needed

        if old_last_buy == 0:
            reason = f"Pct buy: first buy at market {fmt_price(price)} (reference established)"
        else:
            reason = (
                f"Pct buy: price {fmt_price(price)} dropped {self.buy_pct}% "
                f"below last buy {fmt_price(old_last_buy)}"
            )
        if last_shot:
            reason = f"LAST SHOT: {reason} — spent remaining ${cost:.2f}"

        trade_data = {
            "symbol": self.symbol,
            "side": "buy",
            "amount": amount,
            "price": price,
            "cost": cost,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": reason,
            "mode": self.mode,
            "cash_before": cash_before,
            "capital_allocated": self.capital,
            "managed_by": getattr(self, "managed_by", "manual"),
        }

        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

        logger.info(
            f"BUY {amount:.6f} {self.symbol} @ {fmt_price(price)} "
            f"(cost: ${cost:.2f}, fee: ${fee:.4f}) [pct mode]"
        )
        return trade_data

    def _execute_percentage_sell(self, price: float) -> Optional[dict]:
        """Execute a percentage-mode sell: sell oldest open lot (FIFO)."""
        if not self._pct_open_positions:
            return None

        if self.state.holdings <= 0:
            logger.info(f"No holdings left to sell {self.symbol}, skipping pct sell.")
            return None

        # Resolve the lot first so guards can reference the actual lot price
        lot = self._pct_open_positions[0]
        lot_buy_price = lot["price"]

        # Last-lot logic: if holdings are <= lot size, sell everything in one trade
        if self.state.holdings <= lot["amount"] + 1e-10:
            amount = self.state.holdings
        else:
            amount = lot["amount"]

        # Mirror the same guards as _execute_sell
        if self.min_profit_pct > 0 and self.state.avg_buy_price > 0:
            min_price = self.state.avg_buy_price * (1 + self.min_profit_pct / 100)
            if price < min_price:
                logger.info(
                    f"SKIP: pct sell at {fmt_price(price)} below min profit target "
                    f"(need {fmt_price(min_price)}, {self.min_profit_pct:.1f}% above avg buy)"
                )
                return None

        # Strategy A never sells at a loss on the specific lot being sold —
        # UNLESS this is a TF-managed bot under stop-loss, bearish exit, or
        # take-profit (39a/39c: override so all lots liquidate in one pass
        # even when some are locally underwater).
        if self.strategy == "A" and price < lot_buy_price:
            tf_override = (
                self.managed_by == "trend_follower"
                and (self._stop_loss_triggered
                     or self._take_profit_triggered
                     or self.pending_liquidation)
            )
            if tf_override:
                if self._stop_loss_triggered:
                    reason = "STOP-LOSS"
                elif self._take_profit_triggered:
                    reason = "TAKE-PROFIT"
                else:
                    reason = "BEARISH EXIT"
                logger.warning(
                    f"{reason} OVERRIDE: Pct sell at {fmt_price(price)} < "
                    f"lot buy {fmt_price(lot_buy_price)} ({self.symbol})."
                )
            else:
                logger.info(
                    f"BLOCKED: Pct sell at {fmt_price(price)} < lot buy {fmt_price(lot_buy_price)}. "
                    f"Strategy A never sells at loss."
                )
                return None

        if amount > self.state.holdings + 1e-10:
            logger.warning(
                f"Insufficient holdings for SELL {self.symbol}: "
                f"need {amount:.6f}, have {self.state.holdings:.6f}. Skipping pct sell."
            )
            self.skipped_sells.append({
                "symbol": self.symbol,
                "level_price": price,
                "amount_needed": amount,
                "holdings": self.state.holdings,
            })
            return None

        # Round to valid step size and validate against exchange filters
        if self._exchange_filters:
            from utils.exchange_filters import round_to_step, validate_order
            amount = round_to_step(amount, self._exchange_filters["lot_step_size"])
            if amount <= 0:
                # Dust amount — too small to sell after rounding. Remove lot from queue.
                # 39h: also decrement state.holdings by the popped lot so the
                # in-memory state stays consistent with the queue. Without
                # this, the self-heal path (holdings>0 + queue empty) keeps
                # resurrecting the dust lot forever and the post-stop-loss
                # cleanup never sees holdings=0.
                popped = self._pct_open_positions.pop(0)
                dust_amount = float(popped.get("amount", 0))
                dust_value = dust_amount * price
                logger.info(
                    f"[{self.symbol}] Dust lot removed: {dust_amount:.6f} units "
                    f"(${dust_value:.4f}) too small for step_size {self._exchange_filters['lot_step_size']}"
                )
                self.state.holdings = max(0.0, self.state.holdings - dust_amount)
                if self.state.holdings <= 1e-10:
                    self.state.holdings = 0.0
                    self.state.avg_buy_price = 0.0
                return None
            valid, reason_reject = validate_order(self.symbol, amount, price, self._exchange_filters)
            if not valid:
                # Economic dust: lot above step_size but below exchange min_notional/min_qty.
                # It will never be sellable — remove from queue to stop retry spam.
                if "MIN_NOTIONAL" in reason_reject or "min_qty" in reason_reject:
                    popped = self._pct_open_positions.pop(0)
                    dust_amount = float(popped.get("amount", 0))
                    logger.info(
                        f"[{self.symbol}] Economic dust lot removed: {dust_amount:.8f} units "
                        f"(${dust_amount * price:.4f}) — {reason_reject}"
                    )
                    # 39h: same state.holdings sync as above.
                    self.state.holdings = max(0.0, self.state.holdings - dust_amount)
                    if self.state.holdings <= 1e-10:
                        self.state.holdings = 0.0
                        self.state.avg_buy_price = 0.0
                    return None
                logger.warning(f"[{self.symbol}] SELL order rejected: {reason_reject}")
                return None

        revenue = amount * price
        fee = revenue * self.FEE_RATE
        holdings_value_before = self.state.holdings * price
        # Use the specific lot's buy price for cost basis — gives correct per-trade P&L
        cost_basis = amount * lot_buy_price
        buy_fee = cost_basis * self.FEE_RATE
        realized_pnl = revenue - cost_basis - fee - buy_fee

        self._pct_open_positions.pop(0)
        self.state.total_received += revenue
        self.state.total_fees += fee + buy_fee
        self.state.holdings -= amount
        self.state.realized_pnl += realized_pnl
        self.state.daily_realized_pnl += realized_pnl

        # 39b: a profitable sell releases the stop-buy gate (event-based
        # hysteresis). A rebound in price alone does NOT re-enable buys —
        # we wait for a real profit event to confirm the cycle is digested.
        if self._stop_buy_active and realized_pnl > 0:
            self._stop_buy_active = False
            logger.info(
                f"[{self.symbol}] STOP-BUY RESET: profitable sell ${realized_pnl:.2f} "
                f"cleared the block. Buys re-enabled."
            )

        if self.state.holdings <= 0:
            self.state.holdings = 0
            self.state.avg_buy_price = 0

        # After selling all lots, reset buy reference to sell price so next
        # buy triggers correctly (buy_pct% drop from here, not from old buy price)
        if not self._pct_open_positions:
            self._pct_last_buy_price = price
            logger.info(
                f"[{self.symbol}] All lots sold. Buy reference reset to {fmt_price(price)}"
            )

        self._daily_trade_count += 1
        self._last_trade_time = datetime.utcnow()
        self._self_heal_attempted = False  # real trade happened, allow self-heal again if needed

        trade_pnl_pct = (realized_pnl / cost_basis * 100) if cost_basis > 0 else 0

        # 39a/39c: tag the reason so the trade log + Haiku commentary can
        # distinguish forced exits from normal pct sells.
        if self._stop_loss_triggered:
            reason = (
                f"STOP-LOSS: price {fmt_price(price)} forces liquidation "
                f"(lot buy {fmt_price(lot_buy_price)}, threshold {self.tf_stop_loss_pct:.0f}% of alloc)"
            )
        elif self._take_profit_triggered:
            reason = (
                f"TAKE-PROFIT: price {fmt_price(price)} crystallizes gains "
                f"(lot buy {fmt_price(lot_buy_price)}, threshold {self.tf_take_profit_pct:.0f}% of alloc)"
            )
        elif self.pending_liquidation and self.managed_by == "trend_follower":
            reason = (
                f"BEARISH EXIT: TF rotation, sell at {fmt_price(price)} "
                f"(lot buy {fmt_price(lot_buy_price)})"
            )
        else:
            # 42a: for TF bots, the sell threshold was the greed-decay TP;
            # include tier info in the reason so it shows up in logs and
            # Telegram. Manual bots keep the legacy sell_pct wording.
            tp_pct, age_min, tier = self.get_effective_tp()
            if self.managed_by == "trend_follower" and age_min is not None:
                reason = (
                    f"Greed decay sell: price {fmt_price(price)} >= lot buy "
                    f"{fmt_price(lot_buy_price)} * (1 + {tp_pct}%) "
                    f"(age {age_min:.0f}min, tier {tp_pct}%)"
                )
            else:
                reason = (
                    f"Pct sell: price {fmt_price(price)} is {self.sell_pct}% "
                    f"above lot buy {fmt_price(lot_buy_price)}"
                )

        trade_data = {
            "symbol": self.symbol,
            "side": "sell",
            "amount": amount,
            "price": price,
            "cost": revenue,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": reason,
            "mode": self.mode,
            "realized_pnl": realized_pnl,
            "trade_pnl_pct": trade_pnl_pct,  # for Telegram only, filtered before DB log
            "capital_allocated": self.capital,
            "holdings_value_before": holdings_value_before,
            "managed_by": getattr(self, "managed_by", "manual"),
        }

        # 42a: expose greed-decay tier info for Telegram alert. Skip when the
        # sell was forced (stop-loss / take-profit / bearish) — those have
        # their own reason tags that already dominate the message.
        if (self.managed_by == "trend_follower"
                and not self._stop_loss_triggered
                and not self._take_profit_triggered
                and not self.pending_liquidation):
            tp_pct, age_min, _ = self.get_effective_tp()
            if age_min is not None:
                trade_data["greed_tier_age_min"] = age_min
                trade_data["greed_tier_tp_pct"] = tp_pct

        _LOG_TRADE_KEYS = {
            "symbol", "side", "amount", "price", "fee", "strategy", "brain", "reason",
            "mode", "exchange_order_id", "realized_pnl", "buy_trade_id", "cost",
            "config_version", "cash_before", "capital_allocated", "holdings_value_before",
            "managed_by",
        }
        trade_db_row = {}
        try:
            trade_db_row = self.trade_logger.log_trade(
                **{k: v for k, v in trade_data.items() if k in _LOG_TRADE_KEYS}
            )
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

        # Profit skimming: set aside skim_pct% of positive profit into reserve
        if self.skim_pct > 0 and realized_pnl > 0 and self.reserve_ledger:
            skim_amount = realized_pnl * (self.skim_pct / 100)
            try:
                trade_id = trade_db_row.get("id")
                self.reserve_ledger.log_skim(self.symbol, skim_amount, trade_id=trade_id)
                reserve_total = self.reserve_ledger.get_reserve_total(
                    self.symbol, force_refresh=True
                )
                trade_data["skim_amount"] = skim_amount
                trade_data["reserve_total"] = reserve_total
                logger.info(
                    f"SKIM ${skim_amount:.4f} → reserve total ${reserve_total:.2f} [{self.symbol}]"
                )
            except Exception as e:
                logger.warning(f"Failed to log skim for {self.symbol}: {e}")

        logger.info(
            f"SELL {amount:.6f} {self.symbol} @ {fmt_price(price)} "
            f"(revenue: ${revenue:.2f}, fee: ${fee:.4f}, pnl: ${realized_pnl:.4f}) [pct mode]"
        )
        return trade_data

    def _activate_sell_level(self, buy_level: GridLevel, amount: float):
        """
        When a buy fills, activate the nearest unfilled sell level above it.
        This is what makes the grid cycle: buy low → sell high → repeat.
        """
        for level in self.state.levels:
            if level.side == "sell" and not level.filled and level.price > buy_level.price:
                level.order_amount = amount
                return

    def _activate_buy_level(self, sell_level: GridLevel):
        """
        When a sell fills, reactivate the nearest filled buy level below it.
        This lets the grid buy again if price drops back down.
        """
        for level in reversed(self.state.levels):
            if level.side == "buy" and level.filled and level.price < sell_level.price:
                level.filled = False
                level.filled_at = None
                return

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
