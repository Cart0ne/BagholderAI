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


def test_avg_buy_price_accounting():
    """Test that avg_buy_price is a correct weighted average, survives sells, and resets to 0."""
    from bot.strategies.grid_bot import GridBot

    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        strategy="A",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )

    bot.setup_grid(84000.0)

    print("=" * 60)
    print("TEST 5: avg_buy_price Accounting")
    print("=" * 60)

    # --- (a) Multiple buys at different prices → weighted average ---
    buy_levels = [l for l in bot.state.levels if l.side == "buy"]

    # Fill only the highest buy level first
    highest_buy = buy_levels[-1]
    bot.check_price_and_execute(highest_buy.price)
    avg_after_first = bot.state.avg_buy_price
    holdings_after_first = bot.state.holdings
    print(f"  After buy #1 @ ${highest_buy.price:,.2f}: avg=${avg_after_first:,.2f}, holdings={holdings_after_first:.8f}")
    assert abs(avg_after_first - highest_buy.price) < 1.0, "After single buy, avg should equal buy price"

    # Drop price further — fills remaining buy levels. Track weighted average manually.
    second_lowest = buy_levels[1]
    # This will fill buy_levels[1], [2], [3] (indices with price >= second_lowest.price and not yet filled)
    trades = bot.check_price_and_execute(second_lowest.price)
    filled_in_round = [t for t in trades if t and t["side"] == "buy"]

    # Compute expected weighted average: start from first buy, then add each new fill
    weighted_sum = highest_buy.price * highest_buy.order_amount
    total_qty = highest_buy.order_amount
    for t in filled_in_round:
        weighted_sum += t["price"] * t["amount"]
        total_qty += t["amount"]
    expected_avg = weighted_sum / total_qty

    avg_after_multi = bot.state.avg_buy_price
    print(f"  After {1 + len(filled_in_round)} buys: avg=${avg_after_multi:,.2f} (expected ${expected_avg:,.2f})")
    assert abs(avg_after_multi - expected_avg) < 1.0, f"Weighted avg wrong: got {avg_after_multi}, expected {expected_avg}"
    print("  ✅ (a) Weighted average correct after multiple buys")

    # --- (b) avg_buy_price unchanged after a sell ---
    avg_before_sell = bot.state.avg_buy_price
    holdings_before_sell = bot.state.holdings
    # Price rises above grid → trigger sells
    sell_levels = [l for l in bot.state.levels if l.side == "sell" and l.order_amount > 0]
    if sell_levels:
        # Sell just one level (the lowest active sell)
        high_price = sell_levels[0].price
        bot.check_price_and_execute(high_price)
        avg_after_sell = bot.state.avg_buy_price
        print(f"  After sell: avg=${avg_after_sell:,.2f} (was ${avg_before_sell:,.2f}), holdings={bot.state.holdings:.8f}")
        if bot.state.holdings > 0:
            assert abs(avg_after_sell - avg_before_sell) < 0.01, "avg_buy_price must NOT change on sell"
            print("  ✅ (b) avg_buy_price unchanged after sell (partial)")
        else:
            assert avg_after_sell == 0, "avg_buy_price should be 0 when holdings is 0"
            print("  ✅ (b) avg_buy_price reset to 0 (all sold)")

    # --- (c) avg_buy_price → 0 when holdings → 0 ---
    # Sell everything remaining
    while bot.state.holdings > 0:
        # Force a sell level active above current avg
        found = False
        for level in bot.state.levels:
            if level.side == "sell" and not level.filled:
                level.order_amount = bot.state.holdings
                level.price = bot.state.avg_buy_price + 500
                found = True
                break
        if not found:
            break
        sell_price = bot.state.avg_buy_price + 500
        trades = bot.check_price_and_execute(sell_price)
        if not trades:
            break

    print(f"  After selling all: avg=${bot.state.avg_buy_price:,.2f}, holdings={bot.state.holdings:.8f}")
    assert bot.state.holdings == 0, "Holdings should be 0"
    assert bot.state.avg_buy_price == 0, "avg_buy_price should be 0 when no holdings"
    print("  ✅ (c) avg_buy_price is 0 when holdings is 0")

    # --- (d) unrealized P&L correct ---
    # Reset and do a fresh test
    bot.setup_grid(84000.0)
    buy_levels_new = [l for l in bot.state.levels if l.side == "buy"]
    bot.check_price_and_execute(buy_levels_new[-1].price)

    # Check unrealized at a known price
    test_price = 85000.0
    bot.state.last_price = test_price
    expected_unrealized = (test_price - bot.state.avg_buy_price) * bot.state.holdings
    actual_unrealized = bot.state.unrealized_pnl
    print(f"  Unrealized @ ${test_price:,.2f}: ${actual_unrealized:.4f} (expected ${expected_unrealized:.4f})")
    assert abs(actual_unrealized - expected_unrealized) < 0.0001, "Unrealized P&L mismatch"

    # Unrealized should be 0 when holdings is 0
    bot.state.holdings = 0
    bot.state.avg_buy_price = 0
    bot.state.last_price = 85000.0
    assert bot.state.unrealized_pnl == 0, "Unrealized should be 0 with no holdings"
    print("  ✅ (d) Unrealized P&L correct in all scenarios")

    print("✅ avg_buy_price accounting OK\n")


def test_grid_reset_preserves_state():
    """BUG 2: Grid reset must preserve accounting and activate sell levels for existing holdings."""
    from bot.strategies.grid_bot import GridBot

    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        strategy="A",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )

    print("=" * 60)
    print("TEST 6: Grid Reset Preserves State")
    print("=" * 60)

    # Setup grid and execute a buy
    bot.setup_grid(84000.0)
    buy_levels = [l for l in bot.state.levels if l.side == "buy"]
    bot.check_price_and_execute(buy_levels[-1].price)

    # Record accounting before reset
    holdings_before = bot.state.holdings
    avg_buy_before = bot.state.avg_buy_price
    invested_before = bot.state.total_invested
    fees_before = bot.state.total_fees
    realized_before = bot.state.realized_pnl
    daily_pnl_before = bot.state.daily_realized_pnl
    print(f"  Before reset: holdings={holdings_before:.8f}, avg=${avg_buy_before:,.2f}, invested=${invested_before:.2f}")

    assert holdings_before > 0, "Should have holdings before reset"

    # Simulate price moving far away — trigger reset
    new_price = 90000.0
    assert bot.should_reset_grid(new_price), "Price should be outside grid range"
    bot.setup_grid(new_price)

    print(f"  After reset:  holdings={bot.state.holdings:.8f}, avg=${bot.state.avg_buy_price:,.2f}, invested=${bot.state.total_invested:.2f}")

    # Verify accounting preserved
    assert bot.state.holdings == holdings_before, f"Holdings lost: {bot.state.holdings} != {holdings_before}"
    assert bot.state.avg_buy_price == avg_buy_before, f"avg_buy_price lost: {bot.state.avg_buy_price} != {avg_buy_before}"
    assert bot.state.total_invested == invested_before, f"total_invested lost"
    assert bot.state.total_fees == fees_before, f"total_fees lost"
    assert bot.state.realized_pnl == realized_before, f"realized_pnl lost"
    assert bot.state.daily_realized_pnl == daily_pnl_before, f"daily_realized_pnl lost"
    print("  ✅ Accounting preserved after reset")

    # Verify sell levels have order_amount (holdings distributed)
    sell_levels_with_amount = [l for l in bot.state.levels if l.side == "sell" and l.order_amount > 0]
    assert len(sell_levels_with_amount) > 0, "Sell levels should have order_amount after reset with holdings"
    total_sell_amount = sum(l.order_amount for l in sell_levels_with_amount)
    assert abs(total_sell_amount - holdings_before) < 1e-6, f"Sell amounts ({total_sell_amount}) should equal holdings ({holdings_before})"
    print(f"  ✅ {len(sell_levels_with_amount)} sell levels activated with total amount={total_sell_amount:.8f}")

    # Verify new grid is centered on new price
    assert bot.state.lower_bound < new_price < bot.state.upper_bound, "New grid should be centered on new price"
    print(f"  ✅ New grid range: ${bot.state.lower_bound:,.2f} - ${bot.state.upper_bound:,.2f}")

    print("✅ Grid reset preserves state OK\n")


def test_daily_pnl_resets():
    """BUG 3: daily_realized_pnl resets at day change, realized_pnl stays cumulative."""
    from datetime import date
    from bot.strategies.grid_bot import GridBot
    from unittest.mock import patch

    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        strategy="A",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
    )

    print("=" * 60)
    print("TEST 7: Daily P&L Resets")
    print("=" * 60)

    # Day 1: setup, buy, then sell for profit
    day1 = date(2026, 3, 26)
    with patch("bot.strategies.grid_bot.date") as mock_date:
        mock_date.today.return_value = day1
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        bot._daily_date = day1
        bot._daily_pnl_date = day1

        bot.setup_grid(84000.0)

        # Buy: drop price to fill lowest buy levels
        bot.check_price_and_execute(82400.0)
        assert bot.state.holdings > 0, "Should have holdings after buy"
        print(f"  Day 1 after buys: holdings={bot.state.holdings:.8f}")

        # Sell: price rises above grid
        sell_levels = [l for l in bot.state.levels if l.side == "sell" and l.order_amount > 0]
        if sell_levels:
            bot.check_price_and_execute(sell_levels[-1].price + 100)

    day1_daily = bot.state.daily_realized_pnl
    day1_cumulative = bot.state.realized_pnl
    print(f"  Day 1: daily_pnl=${day1_daily:.4f}, cumulative=${day1_cumulative:.4f}")
    assert day1_daily != 0, "Should have some realized P&L on day 1"
    assert day1_daily == day1_cumulative, "On day 1, daily should equal cumulative"

    # Day 2: date changes — daily_realized_pnl should reset
    day2 = date(2026, 3, 27)
    with patch("bot.strategies.grid_bot.date") as mock_date:
        mock_date.today.return_value = day2
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # This call triggers the daily reset inside check_price_and_execute
        bot.check_price_and_execute(84000.0)

    print(f"  Day 2 after reset: daily_pnl=${bot.state.daily_realized_pnl:.4f}, cumulative=${bot.state.realized_pnl:.4f}")
    assert bot.state.daily_realized_pnl == 0.0 or bot.state.daily_realized_pnl != day1_daily, \
        "daily_realized_pnl should have been reset on day change"
    assert bot.state.realized_pnl == day1_cumulative or bot.state.realized_pnl > day1_cumulative, \
        "Cumulative realized_pnl should NOT be reset"
    print("  ✅ daily_realized_pnl resets on new day")
    print("  ✅ realized_pnl (cumulative) preserved")

    print("✅ Daily P&L resets OK\n")


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
    test_avg_buy_price_accounting()
    test_grid_reset_preserves_state()
    test_daily_pnl_resets()
    test_price_simulation()
    
    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
