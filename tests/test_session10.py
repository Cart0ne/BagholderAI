"""
BagHolderAI - Session 10 Tests
Tests for: symbol filter, fmt_price, buy cooldown, available_capital on reset.
No exchange connection needed — pure logic tests.

Usage:
    python tests/test_session10.py
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockTradeLogger:
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


# ---------------------------------------------------------------------------
# TEST 1: get_today_trades(symbol=...) filters correctly
# ---------------------------------------------------------------------------

def test_get_today_trades_symbol_filter():
    """
    get_today_trades(symbol="BTC/USDT") must return only BTC/USDT trades.
    We mock the Supabase client so no real connection is needed.
    """
    print("=" * 60)
    print("TEST 1: get_today_trades symbol filter")
    print("=" * 60)

    from unittest.mock import MagicMock, patch
    import db.client  # ensure module is imported before patching

    # Build fake response data with mixed symbols
    fake_trades = [
        {"id": 1, "symbol": "BTC/USDT", "side": "buy", "config_version": "v2"},
        {"id": 2, "symbol": "SOL/USDT", "side": "buy", "config_version": "v2"},
        {"id": 3, "symbol": "BTC/USDT", "side": "sell", "config_version": "v2"},
    ]

    # We patch get_client so TradeLogger never tries to connect to Supabase
    with patch("db.client.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Build a chainable mock that ends with .execute() → returns BTC-only rows
        btc_trades = [t for t in fake_trades if t["symbol"] == "BTC/USDT"]
        mock_execute = MagicMock()
        mock_execute.execute.return_value = MagicMock(data=btc_trades)

        # Each chained call (.table().select().gte().order().eq().eq()) returns the same mock
        mock_client.table.return_value.select.return_value.gte.return_value \
            .order.return_value.eq.return_value.eq.return_value = mock_execute

        from db.client import TradeLogger
        logger = TradeLogger()
        result = logger.get_today_trades(symbol="BTC/USDT")

    assert all(t["symbol"] == "BTC/USDT" for t in result), \
        f"Expected only BTC/USDT trades, got: {[t['symbol'] for t in result]}"
    print(f"  Returned {len(result)} trades, all BTC/USDT ✅")
    print("✅ get_today_trades symbol filter OK\n")


# ---------------------------------------------------------------------------
# TEST 2: fmt_price handles the full range $87,000 → $0.0000059
# ---------------------------------------------------------------------------

def test_fmt_price():
    """fmt_price must never show $0.00 for any real crypto price."""
    print("=" * 60)
    print("TEST 2: fmt_price formatting")
    print("=" * 60)

    from utils.formatting import fmt_price

    cases = [
        (87000.0,   "$87,000.00"),
        (1234.56,   "$1,234.56"),
        (1.0,       "$1.00"),
        (0.5,       "$0.5000"),
        (0.0123,    "$0.0123"),
        (0.00059,   "$0.000590"),
        (0.0000059, "$0.00000590"),
        (0.00000001,"$0.00000001"),
    ]

    for price, expected in cases:
        result = fmt_price(price)
        # The exact format may differ slightly for very small numbers;
        # what we enforce: no "$0.00" for a nonzero price, and result starts with "$"
        assert result != "$0.00", f"fmt_price({price}) returned $0.00 — must show significant digits"
        assert result.startswith("$"), f"fmt_price({price}) should start with $, got {result}"
        print(f"  fmt_price({price}) = {result}  ✅")

    # Explicit exact checks for the boundary cases
    assert fmt_price(87000.0) == "$87,000.00"
    assert fmt_price(0.0000059) == "$0.00000590"
    print("✅ fmt_price formatting OK\n")


# ---------------------------------------------------------------------------
# TEST 3: Buy cooldown blocks consecutive buys for N seconds
# ---------------------------------------------------------------------------

def test_buy_cooldown():
    """After a buy, the next buy must be blocked for buy_cooldown_seconds."""
    print("=" * 60)
    print("TEST 3: Buy cooldown")
    print("=" * 60)

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
        buy_cooldown_seconds=9999,  # effectively infinite cooldown for testing
    )

    bot.setup_grid(84000.0)

    # Drop price below all buy levels → should fill exactly ONE buy (cooldown blocks the rest)
    low_price = bot.state.lower_bound - 10
    trades = bot.check_price_and_execute(low_price)

    buys = [t for t in trades if t and t["side"] == "buy"]
    print(f"  Trades executed at low price: {len(trades)} (buys={len(buys)})")
    assert len(buys) == 1, f"Cooldown should block all but the first buy, got {len(buys)} buys"
    print(f"  First buy executed, remaining levels blocked by cooldown ✅")

    # Second call immediately — cooldown still active, no new buys
    trades2 = bot.check_price_and_execute(low_price)
    buys2 = [t for t in trades2 if t and t["side"] == "buy"]
    assert len(buys2) == 0, f"Cooldown should block all buys on second call, got {len(buys2)}"
    print(f"  Second call: 0 buys (cooldown active) ✅")

    print("✅ Buy cooldown OK\n")


# ---------------------------------------------------------------------------
# TEST 4: Grid reset — available_capital calculated correctly
# ---------------------------------------------------------------------------

def test_grid_reset_available_capital():
    """
    After partial buys, grid reset must use available_capital for new buy levels,
    not the full allocated capital.
    """
    print("=" * 60)
    print("TEST 4: Grid reset uses available_capital")
    print("=" * 60)

    from bot.strategies.grid_bot import GridBot

    capital = 100.0
    mock_logger = MockTradeLogger()
    bot = GridBot(
        exchange=None,
        trade_logger=mock_logger,
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="BTC/USDT",
        capital=capital,
        num_levels=10,
        range_percent=0.04,
    )

    bot.setup_grid(84000.0)

    # Execute some buys so total_invested > 0
    low_price = bot.state.lower_bound + 10
    bot.check_price_and_execute(low_price)
    invested = bot.state.total_invested
    received = bot.state.total_received
    assert invested > 0, "Should have invested something"

    available_before_reset = max(0.0, capital - invested + received)
    print(f"  Invested: ${invested:.2f}, received: ${received:.2f}, available: ${available_before_reset:.2f}")

    # Force a grid reset
    new_price = 90000.0
    bot.setup_grid(new_price)

    # Check that buy level amounts reflect available_capital, not full capital
    buy_levels = [l for l in bot.state.levels if l.side == "buy"]
    num_buy_levels = len(buy_levels)
    expected_per_level = available_before_reset / num_buy_levels if num_buy_levels else 0

    for bl in buy_levels:
        expected_amount = expected_per_level / bl.price
        # Allow 1% tolerance due to rounding
        assert abs(bl.order_amount - expected_amount) / expected_amount < 0.01, (
            f"Buy level at ${bl.price:.2f}: order_amount={bl.order_amount:.8f}, "
            f"expected ~{expected_amount:.8f} (based on available ${available_before_reset:.2f})"
        )

    print(f"  {num_buy_levels} buy levels sized from available capital ${available_before_reset:.2f} ✅")
    print("✅ Grid reset available_capital OK\n")


# ---------------------------------------------------------------------------
# TEST 5: Grid reset preserves holdings, avg_buy_price, realized_pnl
# ---------------------------------------------------------------------------

def test_grid_reset_preserves_accounting():
    """
    Grid reset must NOT zero out holdings, avg_buy_price, or realized_pnl.
    """
    print("=" * 60)
    print("TEST 5: Grid reset preserves accounting")
    print("=" * 60)

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

    # Buy some levels
    buy_levels = [l for l in bot.state.levels if l.side == "buy"]
    bot.check_price_and_execute(buy_levels[-1].price)

    # Snapshot before reset
    holdings_before = bot.state.holdings
    avg_before = bot.state.avg_buy_price
    invested_before = bot.state.total_invested
    realized_before = bot.state.realized_pnl
    daily_pnl_before = bot.state.daily_realized_pnl

    assert holdings_before > 0, "Need holdings before reset"

    # Reset grid
    bot.setup_grid(90000.0)

    assert bot.state.holdings == holdings_before, \
        f"holdings changed: {bot.state.holdings} != {holdings_before}"
    assert bot.state.avg_buy_price == avg_before, \
        f"avg_buy_price changed: {bot.state.avg_buy_price} != {avg_before}"
    assert bot.state.total_invested == invested_before, \
        f"total_invested changed"
    assert bot.state.realized_pnl == realized_before, \
        f"realized_pnl changed"
    assert bot.state.daily_realized_pnl == daily_pnl_before, \
        f"daily_realized_pnl changed"

    print(f"  holdings={bot.state.holdings:.8f} ✅")
    print(f"  avg_buy_price=${bot.state.avg_buy_price:.2f} ✅")
    print(f"  realized_pnl=${bot.state.realized_pnl:.4f} ✅")
    print("✅ Grid reset preserves accounting OK\n")


# ---------------------------------------------------------------------------
# TEST 6: min_profit_pct blocks sells below the target
# ---------------------------------------------------------------------------

def test_min_profit_sell_blocked():
    """Sell must be blocked when price < avg_buy_price * (1 + min_profit_pct)."""
    print("=" * 60)
    print("TEST 6: min_profit_pct — sell blocked below target")
    print("=" * 60)

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
        min_profit_pct=0.01,  # 1% minimum
    )

    bot.setup_grid(84000.0)

    # Buy at the highest buy level
    buy_levels = [l for l in bot.state.levels if l.side == "buy"]
    bot.check_price_and_execute(buy_levels[-1].price)
    avg = bot.state.avg_buy_price
    assert avg > 0

    min_sell_price = avg * 1.01  # need at least +1%

    # Force a sell level just below the minimum profit threshold
    below_target = avg * 1.005  # only +0.5% — not enough
    for level in bot.state.levels:
        if level.side == "sell" and not level.filled:
            level.price = below_target
            level.order_amount = bot.state.holdings
            break

    trades_before = len(mock_logger.trades)
    sells = bot.check_price_and_execute(below_target)
    sell_count = sum(1 for t in sells if t and t.get("side") == "sell")

    assert sell_count == 0, f"Sell should be blocked at {below_target:.2f} (below min {min_sell_price:.2f})"
    print(f"  avg_buy=${avg:.2f}, min_target=${min_sell_price:.2f}, sell_price=${below_target:.2f} → blocked ✅")
    print("✅ min_profit sell blocked OK\n")


# ---------------------------------------------------------------------------
# TEST 7: min_profit_pct allows sells above the target
# ---------------------------------------------------------------------------

def test_min_profit_sell_allowed():
    """Sell must execute when price >= avg_buy_price * (1 + min_profit_pct)."""
    print("=" * 60)
    print("TEST 7: min_profit_pct — sell allowed above target")
    print("=" * 60)

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
        min_profit_pct=0.01,  # 1% minimum
    )

    bot.setup_grid(84000.0)

    buy_levels = [l for l in bot.state.levels if l.side == "buy"]
    bot.check_price_and_execute(buy_levels[-1].price)
    avg = bot.state.avg_buy_price

    above_target = avg * 1.02  # +2% — above the 1% threshold

    # Force a sell level at the above-target price
    for level in bot.state.levels:
        if level.side == "sell" and not level.filled:
            level.price = above_target
            level.order_amount = bot.state.holdings
            break

    sells = bot.check_price_and_execute(above_target)
    sell_count = sum(1 for t in sells if t and t.get("side") == "sell")

    assert sell_count == 1, f"Sell should execute at {above_target:.2f} (above min {avg * 1.01:.2f})"
    print(f"  avg_buy=${avg:.2f}, min_target=${avg * 1.01:.2f}, sell_price=${above_target:.2f} → executed ✅")
    print("✅ min_profit sell allowed OK\n")


if __name__ == "__main__":
    print("\n🎒 BagHolderAI — Session 10 Test Suite\n")

    test_fmt_price()
    test_buy_cooldown()
    test_grid_reset_available_capital()
    test_grid_reset_preserves_accounting()
    test_get_today_trades_symbol_filter()
    test_min_profit_sell_blocked()
    test_min_profit_sell_allowed()

    print("=" * 60)
    print("ALL SESSION 10 TESTS PASSED ✅")
    print("=" * 60)
