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
from datetime import datetime, date
from utils.formatting import fmt_price

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
        min_profit_pct: float = 0.0,    # Task 10: min gross margin to allow a sell (e.g. 0.01 = 1%)
        grid_mode: str = "fixed",       # "fixed" or "percentage"
        buy_pct: float = 0.0,           # % drop from last buy to trigger next buy
        sell_pct: float = 0.0,          # % rise from avg buy to trigger sell
        capital_per_trade: float = 0.0, # USDT to spend per buy in percentage mode
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
        self.state: Optional[GridState] = None
        self._daily_trade_count = 0
        self._daily_date = datetime.utcnow().date()
        self._daily_pnl_date = datetime.utcnow().date()
        self._last_buy_time: float = 0.0  # Task 5: timestamp of last buy
        self.skipped_buys: list = []     # filled each cycle with insufficient-cash skips
        self.skipped_sells: list = []    # filled each cycle with insufficient-holdings skips
        # Percentage mode state
        self._pct_last_buy_price: float = 0.0
        self._pct_open_positions: list = []  # FIFO: [{"amount": float, "price": float}, ...]

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
        logger.info(
            f"Grid {is_reset}: {self.symbol} | "
            f"Center: {fmt_price(current_price)} | "
            f"Range: {fmt_price(lower)} - {fmt_price(upper)} | "
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
        Reconstructs the FIFO open-positions queue and last buy price
        by replaying all v3 trades for this symbol chronologically.
        """
        if not self.trade_logger:
            return
        try:
            result = (
                self.trade_logger.client.table("trades")
                .select("side,amount,price,created_at")
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

        for t in trades:
            side = t.get("side")
            amount = float(t.get("amount", 0))
            price = float(t.get("price", 0))
            if side == "buy":
                open_positions.append({"amount": amount, "price": price})
                last_buy_price = price
            elif side == "sell" and open_positions:
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

        if last_buy_price > 0:
            logger.info(
                f"[{self.symbol}] Pct mode restored: {len(open_positions)} open lots, "
                f"last buy {fmt_price(last_buy_price)}"
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
        amount = level.order_amount
        cost = amount * price
        fee = cost * self.FEE_RATE

        # Snapshot for Telegram verification
        cash_before = max(0.0, self.capital - self.state.total_invested + self.state.total_received)

        # Guard: skip buy if insufficient cash
        if cash_before < cost:
            logger.warning(
                f"Insufficient cash for BUY {self.symbol}: "
                f"need ${cost:.2f}, have ${cash_before:.2f}. Skipping level {fmt_price(level.price)}."
            )
            self.skipped_buys.append({
                "symbol": self.symbol,
                "level_price": level.price,
                "cost": cost,
                "cash_before": cash_before,
            })
            return None

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

        trade_data = {
            "symbol": self.symbol,
            "side": "buy",
            "amount": amount,
            "price": price,
            "cost": cost,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": f"Grid buy at level {fmt_price(level.price)} (price dropped to {fmt_price(price)})",
            "mode": self.mode,
            "cash_before": cash_before,
            "capital_allocated": self.capital,
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
        # Task 10: enforce minimum profit target before selling
        if self.min_profit_pct > 0 and self.state.avg_buy_price > 0:
            min_price = self.state.avg_buy_price * (1 + self.min_profit_pct)
            if price < min_price:
                logger.info(
                    f"SKIP: sell at {fmt_price(price)} below min profit target "
                    f"(need {fmt_price(min_price)}, {self.min_profit_pct * 100:.1f}% above avg buy)"
                )
                return None

        if self.strategy == "A" and price < self.state.avg_buy_price:
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
        self.state.last_price = current_price

        if self._daily_trade_count >= 50:
            logger.warning("Daily operation limit reached (50). Stopping.")
            return trades

        # --- SELL CHECK ---
        if (
            self.state.holdings > 0
            and self.state.avg_buy_price > 0
            and self._pct_open_positions
        ):
            sell_trigger = self.state.avg_buy_price * (1 + self.sell_pct / 100)
            if current_price >= sell_trigger:
                trade = self._execute_percentage_sell(current_price)
                if trade:
                    trades.append(trade)

        # --- BUY CHECK ---
        now = time.time()
        buy_cooldown_active = (
            self.buy_cooldown_seconds > 0
            and self._pct_last_buy_price != 0  # cooldown doesn't block the very first buy
            and (now - self._last_buy_time) < self.buy_cooldown_seconds
        )

        if not buy_cooldown_active:
            if self._pct_last_buy_price == 0:
                # No previous buy — establish reference immediately
                trade = self._execute_percentage_buy(current_price)
                if trade:
                    trades.append(trade)
            else:
                buy_trigger = self._pct_last_buy_price * (1 - self.buy_pct / 100)
                if current_price <= buy_trigger:
                    trade = self._execute_percentage_buy(current_price)
                    if trade:
                        trades.append(trade)

        return trades

    def _execute_percentage_buy(self, price: float) -> Optional[dict]:
        """Execute a percentage-mode buy: spend capital_per_trade USDT at current price."""
        if price <= 0:
            logger.error(f"Invalid price {price} for {self.symbol}, skipping pct buy")
            return None
        cost = self.capital_per_trade
        amount = cost / price
        fee = cost * self.FEE_RATE

        cash_before = max(0.0, self.capital - self.state.total_invested + self.state.total_received)

        if cash_before < cost:
            logger.warning(
                f"Insufficient cash for BUY {self.symbol}: "
                f"need ${cost:.2f}, have ${cash_before:.2f}. Skipping pct buy."
            )
            self.skipped_buys.append({
                "symbol": self.symbol,
                "level_price": price,
                "cost": cost,
                "cash_before": cash_before,
            })
            return None

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

        if old_last_buy == 0:
            reason = f"Pct buy: first buy at market {fmt_price(price)} (reference established)"
        else:
            reason = (
                f"Pct buy: price {fmt_price(price)} dropped {self.buy_pct}% "
                f"below last buy {fmt_price(old_last_buy)}"
            )

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

        # Mirror the same guards as _execute_sell
        if self.min_profit_pct > 0 and self.state.avg_buy_price > 0:
            min_price = self.state.avg_buy_price * (1 + self.min_profit_pct)
            if price < min_price:
                logger.info(
                    f"SKIP: pct sell at {fmt_price(price)} below min profit target "
                    f"(need {fmt_price(min_price)}, {self.min_profit_pct * 100:.1f}% above avg buy)"
                )
                return None

        if self.strategy == "A" and price < self.state.avg_buy_price:
            logger.info(
                f"BLOCKED: Pct sell at {fmt_price(price)} < avg buy {fmt_price(self.state.avg_buy_price)}. "
                f"Strategy A never sells at loss."
            )
            return None

        lot = self._pct_open_positions[0]
        amount = lot["amount"]

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

        avg_buy_snapshot = self.state.avg_buy_price
        revenue = amount * price
        fee = revenue * self.FEE_RATE
        holdings_value_before = self.state.holdings * price
        cost_basis = amount * avg_buy_snapshot
        buy_fee = cost_basis * self.FEE_RATE
        realized_pnl = revenue - cost_basis - fee - buy_fee

        self._pct_open_positions.pop(0)
        self.state.total_received += revenue
        self.state.total_fees += fee + buy_fee
        self.state.holdings -= amount
        self.state.realized_pnl += realized_pnl
        self.state.daily_realized_pnl += realized_pnl

        if self.state.holdings <= 0:
            self.state.holdings = 0
            self.state.avg_buy_price = 0

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
            "reason": (
                f"Pct sell: price {fmt_price(price)} is {self.sell_pct}% "
                f"above avg buy {fmt_price(avg_buy_snapshot)}"
            ),
            "mode": self.mode,
            "realized_pnl": realized_pnl,
            "holdings_value_before": holdings_value_before,
        }

        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

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

        # Task 3: available_capital = allocated - invested + received
        available_capital = max(0.0, self.capital - self.state.total_invested + self.state.total_received)

        return {
            "symbol": self.symbol,
            "strategy": self.strategy,
            "mode": self.mode,
            "center_price": self.state.center_price,
            "range": f"${self.state.lower_bound:.{self._price_decimals(self.state.center_price)}f} - ${self.state.upper_bound:.{self._price_decimals(self.state.center_price)}f}",
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
