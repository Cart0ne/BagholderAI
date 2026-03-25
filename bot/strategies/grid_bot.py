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

    @property
    def unrealized_pnl(self) -> float:
        if self.holdings > 0 and self.last_price > 0:
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
        self.state: Optional[GridState] = None
        self._daily_trade_count = 0
        self._daily_date = date.today()
    
    def setup_grid(self, current_price: float) -> GridState:
        """
        Create a new grid centered on the current price.
        
        Buy levels below current price, sell levels above.
        Each level gets an equal share of the allocated capital.
        """
        half_range = current_price * (self.range_percent / 2)
        lower = current_price - half_range
        upper = current_price + half_range
        
        # Calculate step size between levels
        step = (upper - lower) / (self.num_levels - 1)
        
        # Capital per level (only buy levels use capital)
        num_buy_levels = self.num_levels // 2
        capital_per_level = self.capital / num_buy_levels
        
        levels = []
        for i in range(self.num_levels):
            level_price = lower + (step * i)
            
            if level_price < current_price:
                # Buy level — below current price
                amount = capital_per_level / level_price  # how much BTC we'd buy
                levels.append(GridLevel(
                    price=round(level_price, 2),
                    side="buy",
                    order_amount=round(amount, 8),
                ))
            else:
                # Sell level — above current price
                # Sell levels start empty (nothing to sell until we buy)
                levels.append(GridLevel(
                    price=round(level_price, 2),
                    side="sell",
                    order_amount=0.0,
                ))
        
        self.state = GridState(
            symbol=self.symbol,
            strategy=self.strategy,
            center_price=round(current_price, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            levels=levels,
            last_price=current_price,
            created_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(
            f"Grid created: {self.symbol} | "
            f"Center: ${current_price:.2f} | "
            f"Range: ${lower:.2f} - ${upper:.2f} | "
            f"Levels: {self.num_levels} | "
            f"Capital: ${self.capital}"
        )
        
        return self.state
    
    def check_price_and_execute(self, current_price: float) -> list:
        """
        Check current price against grid levels and execute fills.
        Returns list of trades executed.
        
        Logic:
        - Price drops to/below a buy level → fill the buy
        - Price rises to/above a sell level → fill the sell (if we have holdings)
        """
        if not self.state:
            raise RuntimeError("Grid not initialized. Call setup_grid() first.")
        
        # Reset daily counter if new day
        today = date.today()
        if today != self._daily_date:
            self._daily_trade_count = 0
            self._daily_date = today
        
        trades = []
        self.state.last_price = current_price
        
        for level in self.state.levels:
            if level.filled:
                continue
            
            # Check daily operation limit (hardcoded rule)
            if self._daily_trade_count >= 50:
                logger.warning("Daily operation limit reached (50). Stopping.")
                break
            
            if level.side == "buy" and current_price <= level.price:
                trade = self._execute_buy(level, current_price)
                if trade:
                    trades.append(trade)
            
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
        
        # Mark level as filled
        level.filled = True
        level.filled_at = time.time()
        
        # Update state
        self.state.total_invested += cost
        self.state.total_fees += fee
        self.state.holdings += amount
        
        # Recalculate average buy price
        if self.state.holdings > 0:
            self.state.avg_buy_price = self.state.total_invested / self.state.holdings
        
        # Activate the corresponding sell level above
        self._activate_sell_level(level, amount)
        
        self._daily_trade_count += 1
        
        trade_data = {
            "symbol": self.symbol,
            "side": "buy",
            "amount": amount,
            "price": price,
            "cost": cost,
            "fee": fee,
            "strategy": self.strategy,
            "brain": "grid",
            "reason": f"Grid buy at level ${level.price:.2f} (price dropped to ${price:.2f})",
            "mode": self.mode,
        }
        
        # Log to database
        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
        
        logger.info(
            f"BUY {amount:.6f} {self.symbol} @ ${price:.2f} "
            f"(cost: ${cost:.2f}, fee: ${fee:.4f})"
        )
        
        return trade_data
    
    def _execute_sell(self, level: GridLevel, price: float) -> Optional[dict]:
        """
        Execute a sell at a grid level.
        
        HARDCODED RULE: Strategy A NEVER sells at a loss.
        """
        if self.strategy == "A" and price < self.state.avg_buy_price:
            logger.info(
                f"BLOCKED: Sell at ${price:.2f} < avg buy ${self.state.avg_buy_price:.2f}. "
                f"Strategy A never sells at loss."
            )
            return None
        
        # Sell the amount that was bought at the corresponding buy level
        amount = level.order_amount
        if amount <= 0 or amount > self.state.holdings:
            amount = self.state.holdings  # sell what we have
        
        if amount <= 0:
            return None
        
        revenue = amount * price
        fee = revenue * self.FEE_RATE
        
        # Calculate realized P&L for this trade
        cost_basis = amount * self.state.avg_buy_price
        buy_fee = cost_basis * self.FEE_RATE
        realized_pnl = revenue - cost_basis - fee - buy_fee
        
        # Mark level as filled
        level.filled = True
        level.filled_at = time.time()
        
        # Update state
        self.state.total_received += revenue
        self.state.total_fees += fee
        self.state.holdings -= amount
        self.state.realized_pnl += realized_pnl

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
            "reason": f"Grid sell at level ${level.price:.2f} (price rose to ${price:.2f})",
            "mode": self.mode,
            "realized_pnl": realized_pnl,
        }
        
        # Log to database
        try:
            self.trade_logger.log_trade(**trade_data)
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
        
        logger.info(
            f"SELL {amount:.6f} {self.symbol} @ ${price:.2f} "
            f"(revenue: ${revenue:.2f}, fee: ${fee:.4f}, pnl: ${realized_pnl:.4f})"
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
        
        return {
            "symbol": self.symbol,
            "strategy": self.strategy,
            "mode": self.mode,
            "center_price": self.state.center_price,
            "range": f"${self.state.lower_bound:.2f} - ${self.state.upper_bound:.2f}",
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
        """
        if not self.state:
            return True
        
        margin = (self.state.upper_bound - self.state.lower_bound) * 0.1
        return (
            current_price < self.state.lower_bound - margin
            or current_price > self.state.upper_bound + margin
        )
