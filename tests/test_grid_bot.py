"""
BagHolderAI - Grid Bot Test
Simulates price movement to validate the grid logic works correctly.
No exchange connection needed — pure logic test.

Usage:
    python tests/test_grid_bot.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockTradeLogger:
    """Fake trade logger that just collects trades."""
    def __init__(self):
        self.trades = []
    
    def log_trade(self, **kwargs):
        self.trades.append(kwargs)
        return kwargs


class MockPortfolioManager:
    def update_position(self, **kwargs):
        return kwargs
    def get_portfolio(self):
        return []
    def get_total_allocation(self):
        return 0


class MockPnLTracker:
    def record_daily(self, **kwargs):
        return kwargs
    def get_daily_pnl_today(self):
        return 0


def test_grid_setup():
    """Test that grid creates correct levels around price."""
    from bot.strategies.grid_bot import GridBot
    
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,  # 4%
    )
    
    # Setup grid at $84,000
    state = bot.setup_grid(84000.0)
    
    print("=" * 60)
    print("TEST 1: Grid Setup")
    print("=" * 60)
    print(f"Center: ${state.center_price:,.2f}")
    print(f"Range: ${state.lower_bound:,.2f} - ${state.upper_bound:,.2f}")
    print(f"Levels: {len(state.levels)}")
    print()
    
    for level in state.levels:
        marker = "BUY ↓" if level.side == "buy" else "SELL ↑"
        amt = f"({level.order_amount:.8f} BTC)" if level.order_amount > 0 else "(waiting)"
        print(f"  ${level.price:>10,.2f}  {marker}  {amt}")
    
    buy_levels = [l for l in state.levels if l.side == "buy"]
    sell_levels = [l for l in state.levels if l.side == "sell"]
    print(f"\nBuy levels: {len(buy_levels)}, Sell levels: {len(sell_levels)}")
    
    assert len(state.levels) == 10, "Should have 10 levels"
    assert state.lower_bound < 84000 < state.upper_bound, "Price should be inside range"
    assert len(buy_levels) > 0, "Should have buy levels"
    assert len(sell_levels) > 0, "Should have sell levels"
    print("✅ Grid setup OK\n")


def test_buy_execution():
    """Test that bot buys when price drops to a level."""
    from bot.strategies.grid_bot import GridBot
    
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )
    
    bot.setup_grid(84000.0)
    
    print("=" * 60)
    print("TEST 2: Buy Execution")
    print("=" * 60)
    
    # Price drops to first buy level
    first_buy = [l for l in bot.state.levels if l.side == "buy"][-1]  # highest buy
    print(f"Dropping price to first buy level: ${first_buy.price:,.2f}")
    
    trades = bot.check_price_and_execute(first_buy.price)
    
    print(f"Trades executed: {len(trades)}")
    for t in trades:
        print(f"  {t['side'].upper()} {t['amount']:.8f} @ ${t['price']:,.2f}")
    
    assert len(trades) >= 1, "Should execute at least one buy"
    assert trades[0]["side"] == "buy", "Should be a buy"
    assert bot.state.holdings > 0, "Should have holdings after buy"
    print(f"Holdings: {bot.state.holdings:.8f} BTC")
    print(f"Invested: ${bot.state.total_invested:.2f}")
    print("✅ Buy execution OK\n")


def test_sell_execution():
    """Test that bot sells when price rises after buying."""
    from bot.strategies.grid_bot import GridBot
    
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )
    
    bot.setup_grid(84000.0)
    
    print("=" * 60)
    print("TEST 3: Buy → Sell Cycle")
    print("=" * 60)
    
    # Step 1: Price drops — trigger buys
    low_price = bot.state.lower_bound + 50
    print(f"Step 1: Price drops to ${low_price:,.2f}")
    buy_trades = bot.check_price_and_execute(low_price)
    print(f"  Buys: {len(buy_trades)}")
    print(f"  Holdings: {bot.state.holdings:.8f} BTC")
    print(f"  Invested: ${bot.state.total_invested:.2f}")
    
    # Step 2: Price rises — trigger sells
    high_price = bot.state.upper_bound - 50
    print(f"\nStep 2: Price rises to ${high_price:,.2f}")
    sell_trades = bot.check_price_and_execute(high_price)
    print(f"  Sells: {len(sell_trades)}")
    print(f"  Holdings: {bot.state.holdings:.8f} BTC")
    print(f"  Received: ${bot.state.total_received:.2f}")
    print(f"  Realized P&L: ${bot.state.realized_pnl:.4f}")
    
    assert len(buy_trades) > 0, "Should have buys"
    assert len(sell_trades) > 0, "Should have sells"
    
    total_trades = len(mock_logger.trades)
    print(f"\nTotal trades logged: {total_trades}")
    print("✅ Buy → Sell cycle OK\n")


def test_never_sell_at_loss():
    """Test the HARDCODED rule: Strategy A never sells at loss."""
    from bot.strategies.grid_bot import GridBot
    
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        strategy="A",  # Strategy A = never sell at loss
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )
    
    bot.setup_grid(84000.0)
    
    print("=" * 60)
    print("TEST 4: Never Sell at Loss (Strategy A)")
    print("=" * 60)
    
    # Buy at a level
    first_buy = [l for l in bot.state.levels if l.side == "buy"][-1]
    bot.check_price_and_execute(first_buy.price)
    print(f"Bought at: ${first_buy.price:,.2f}")
    print(f"Avg buy price: ${bot.state.avg_buy_price:,.2f}")
    
    # Try to trigger a sell at a lower price (should be blocked!)
    loss_price = first_buy.price - 500
    pre_trades = len(mock_logger.trades)
    
    # Manually force a sell level to be active at this lower price
    for level in bot.state.levels:
        if level.side == "sell" and not level.filled:
            level.price = loss_price  # force sell level below buy price
            level.order_amount = bot.state.holdings
            break
    
    sells = bot.check_price_and_execute(loss_price)
    post_trades = len(mock_logger.trades)
    
    sell_count = sum(1 for t in sells if t and t.get("side") == "sell")
    print(f"Attempted sell at ${loss_price:,.2f} (below avg buy)")
    print(f"Sells executed: {sell_count}")
    
    assert sell_count == 0, "Strategy A should NEVER sell at loss"
    print("✅ Never-sell-at-loss rule working correctly\n")


def test_price_simulation():
    """Simulate realistic price movement over time."""
    from bot.strategies.grid_bot import GridBot
    import math
    
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )
    
    start_price = 84000.0
    bot.setup_grid(start_price)
    
    print("=" * 60)
    print("TEST 5: Price Simulation (60 cycles)")
    print("=" * 60)
    
    # Simulate 60 price ticks (oscillating within range)
    total_buys = 0
    total_sells = 0
    
    for i in range(60):
        # Oscillating price: sine wave within the grid range
        oscillation = math.sin(i * 0.3) * (start_price * 0.018)
        price = start_price + oscillation
        
        trades = bot.check_price_and_execute(price)
        
        buys = sum(1 for t in trades if t and t.get("side") == "buy")
        sells = sum(1 for t in trades if t and t.get("side") == "sell")
        total_buys += buys
        total_sells += sells
        
        if trades:
            for t in trades:
                if t:
                    emoji = "🟢" if t["side"] == "buy" else "🔴"
                    print(f"  Tick {i:3d}: {emoji} {t['side'].upper()} @ ${t['price']:,.2f}")
    
    status = bot.get_status()
    print(f"\n--- Simulation Results ---")
    print(f"Total buys:     {total_buys}")
    print(f"Total sells:    {total_sells}")
    print(f"Holdings:       {status['holdings']:.8f} BTC")
    print(f"Invested:       ${status['invested']:,.2f}")
    print(f"Received:       ${status['received']:,.2f}")
    print(f"Fees:           ${status['fees']:.4f}")
    print(f"Realized P&L:   ${status['realized_pnl']:.4f}")
    print(f"Unrealized P&L: ${status['unrealized_pnl']:.4f}")
    
    assert total_buys > 0, "Should have some buys in simulation"
    print("✅ Price simulation OK\n")


if __name__ == "__main__":
    print("\n🎒 BagHolderAI Grid Bot — Test Suite\n")
    
    test_grid_setup()
    test_buy_execution()
    test_sell_execution()
    test_never_sell_at_loss()
    test_price_simulation()
    
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
