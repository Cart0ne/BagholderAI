"""
BagHolderAI - 57a verify_fifo_queue() unit test

Validates that the bot's in-memory _pct_open_positions queue is checked
against a fresh DB replay before every sell decision, and corrected
in-place if it has drifted.

Drift sources covered by this test:
  T1) corrupted lot price in memory
  T2) corrupted lot amount in memory
  T3) extra ghost lot in memory (one too many)
  T4) missing lot in memory (one too few)
  T5) empty memory queue with non-empty DB queue
  T6) non-empty memory queue with empty DB queue
  T7) no drift — happy path, no rebuild, returns True

Also validates that on drift correction:
  - state.holdings and state.avg_buy_price are recomputed from DB queue
  - return value is False (drift was found and corrected)

Usage:
    python tests/test_verify_fifo_queue.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------------
# Mocks
# ----------------------------------------------------------------------

class MockSupabaseQuery:
    """Chainable mock of supabase-py's PostgrestFilterBuilder."""
    def __init__(self, rows):
        self._rows = rows

    def select(self, *args, **kwargs):
        return self
    def eq(self, *args, **kwargs):
        return self
    def order(self, *args, **kwargs):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        r.data = self._rows
        return r


class MockSupabaseClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return MockSupabaseQuery(self._rows)


class MockTradeLogger:
    """Holds a Supabase-shaped client + a no-op log_trade."""
    def __init__(self, db_trades):
        self.client = MockSupabaseClient(db_trades)
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


def make_bot(db_trades):
    from bot.strategies.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(db_trades),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="TEST/USDT",
        capital=100.0,
        num_levels=10,
        range_percent=0.04,
        grid_mode="percentage",
        buy_pct=1.0,
        sell_pct=1.0,
        strategy="A",
    )
    bot._exchange_filters = None
    bot.setup_grid(current_price=10.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.realized_pnl = 0.0
    bot._pct_open_positions = []
    return bot


def assert_close(actual, expected, tol=1e-6, label=""):
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_no_drift_returns_true():
    """Happy path: in-memory queue matches DB queue exactly. No rebuild."""
    print("=" * 60)
    print("TEST 1: no drift — verify returns True without rebuild")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
        {"side": "buy", "amount": 100.0, "price": 1.50, "cost": 150.0,
         "created_at": "2026-05-01T11:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [
        {"amount": 100.0, "price": 1.00},
        {"amount": 100.0, "price": 1.50},
    ]
    bot.state.holdings = 200.0
    bot.state.avg_buy_price = 1.25

    result = bot.verify_fifo_queue()
    assert result is True, "Expected True (no drift)"
    assert len(bot._pct_open_positions) == 2, "Queue must not have been rewritten"
    assert_close(bot.state.holdings, 200.0, label="holdings unchanged")
    print(f"  ✓ no drift detected, queue intact, returned True")


def test_drift_corrupted_price():
    """Memory queue has wrong price on lot 1 → drift detected, queue rebuilt."""
    print("=" * 60)
    print("TEST 2: drift — corrupted lot price in memory")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
        {"side": "buy", "amount": 100.0, "price": 1.50, "cost": 150.0,
         "created_at": "2026-05-01T11:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [
        {"amount": 100.0, "price": 1.00},
        {"amount": 100.0, "price": 1.99},  # drift!
    ]
    bot.state.holdings = 200.0
    bot.state.avg_buy_price = 1.495  # what mem queue would imply

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert len(bot._pct_open_positions) == 2, "Should still be 2 lots after rebuild"
    assert_close(bot._pct_open_positions[1]["price"], 1.50,
                 label="lot 1 price corrected from DB")
    assert_close(bot.state.holdings, 200.0, label="holdings recomputed")
    assert_close(bot.state.avg_buy_price, 1.25, label="avg_buy_price recomputed")
    print(f"  ✓ drift detected and corrected (price 1.99 → 1.50), avg recomputed")


def test_drift_corrupted_amount():
    """Memory queue has wrong amount on lot 1 → drift detected, queue rebuilt."""
    print("=" * 60)
    print("TEST 3: drift — corrupted lot amount in memory")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [{"amount": 50.0, "price": 1.00}]  # drift!
    bot.state.holdings = 50.0
    bot.state.avg_buy_price = 1.00

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert_close(bot._pct_open_positions[0]["amount"], 100.0,
                 label="lot amount corrected")
    assert_close(bot.state.holdings, 100.0, label="holdings re-derived")
    print(f"  ✓ amount drift (50 → 100) corrected from DB")


def test_drift_ghost_lot():
    """Memory has one extra lot the DB doesn't know about."""
    print("=" * 60)
    print("TEST 4: drift — ghost lot in memory")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [
        {"amount": 100.0, "price": 1.00},
        {"amount": 50.0, "price": 2.00},  # ghost!
    ]
    bot.state.holdings = 150.0
    bot.state.avg_buy_price = (100.0 + 100.0) / 150.0

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert len(bot._pct_open_positions) == 1, "Ghost lot should have been removed"
    assert_close(bot.state.holdings, 100.0, label="holdings reduced")
    assert_close(bot.state.avg_buy_price, 1.00, label="avg recomputed without ghost")
    print(f"  ✓ ghost lot removed, holdings 150→100")


def test_drift_missing_lot():
    """Memory has one fewer lot than DB (e.g. accidental pop)."""
    print("=" * 60)
    print("TEST 5: drift — missing lot in memory")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
        {"side": "buy", "amount": 100.0, "price": 1.50, "cost": 150.0,
         "created_at": "2026-05-01T11:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [{"amount": 100.0, "price": 1.50}]  # lot 0 missing
    bot.state.holdings = 100.0
    bot.state.avg_buy_price = 1.50

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert len(bot._pct_open_positions) == 2, "Missing lot should have been restored"
    assert_close(bot._pct_open_positions[0]["price"], 1.00,
                 label="lot 0 restored at price 1.00")
    assert_close(bot.state.holdings, 200.0, label="holdings restored to 200")
    assert_close(bot.state.avg_buy_price, 1.25, label="avg recomputed")
    print(f"  ✓ missing lot recovered from DB, holdings 100→200")


def test_empty_memory_with_db_lots():
    """Memory queue empty, DB has open lots → rebuild from DB."""
    print("=" * 60)
    print("TEST 6: drift — empty memory queue, non-empty DB")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = []
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert len(bot._pct_open_positions) == 1, "Should have rebuilt 1 lot from DB"
    assert_close(bot.state.holdings, 100.0, label="holdings rebuilt")
    print(f"  ✓ empty memory rebuilt to 1 lot, holdings 0→100")


def test_non_empty_memory_with_empty_db():
    """Memory has lots, DB has none (e.g. trades wiped) → memory wiped to match."""
    print("=" * 60)
    print("TEST 7: drift — non-empty memory, empty DB (sells consumed all)")
    print("=" * 60)
    # Equal buy + sell amounts → DB queue ends empty after replay
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
        {"side": "sell", "amount": 100.0, "price": 1.20, "cost": 120.0,
         "created_at": "2026-05-01T11:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [{"amount": 100.0, "price": 1.00}]  # stale
    bot.state.holdings = 100.0
    bot.state.avg_buy_price = 1.00

    result = bot.verify_fifo_queue()
    assert result is False, "Expected False (drift)"
    assert len(bot._pct_open_positions) == 0, "Should have wiped queue"
    assert_close(bot.state.holdings, 0.0, label="holdings wiped")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg wiped")
    print(f"  ✓ stale memory wiped to match empty DB queue")


def test_idempotent_after_rebuild():
    """Calling verify_fifo_queue twice in a row → first rebuilds, second is no-op."""
    print("=" * 60)
    print("TEST 8: idempotent — second call after rebuild returns True")
    print("=" * 60)
    db_trades = [
        {"side": "buy", "amount": 100.0, "price": 1.00, "cost": 100.0,
         "created_at": "2026-05-01T10:00:00+00:00"},
    ]
    bot = make_bot(db_trades)
    bot._pct_open_positions = [{"amount": 100.0, "price": 1.99}]  # drift
    bot.state.holdings = 100.0
    bot.state.avg_buy_price = 1.99

    first = bot.verify_fifo_queue()
    assert first is False, "First call must detect drift"

    second = bot.verify_fifo_queue()
    assert second is True, "Second call must report no drift (already corrected)"
    print(f"  ✓ first=False (corrected), second=True (idempotent)")


def test_db_error_returns_true_safely():
    """If the DB query raises, verify must NOT crash and must return True
    (degrade gracefully — a transient Supabase blip can't take the bot down)."""
    print("=" * 60)
    print("TEST 9: DB error — degrades to True without crashing")
    print("=" * 60)

    class CrashingClient:
        def table(self, *a, **kw):
            raise RuntimeError("simulated supabase outage")

    class CrashingLogger:
        client = CrashingClient()

    from bot.strategies.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=CrashingLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="TEST/USDT",
        capital=100.0, num_levels=10, range_percent=0.04,
        grid_mode="percentage", buy_pct=1.0, sell_pct=1.0, strategy="A",
    )
    bot._exchange_filters = None
    bot.setup_grid(current_price=10.0)
    bot._pct_open_positions = [{"amount": 100.0, "price": 1.00}]
    bot.state.holdings = 100.0

    result = bot.verify_fifo_queue()
    assert result is True, "DB error must degrade to True"
    # Memory queue must be untouched
    assert len(bot._pct_open_positions) == 1, "Memory must not have been wiped"
    print(f"  ✓ DB error handled, returned True, memory queue preserved")


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # suppress drift WARN noise

    tests = [
        test_no_drift_returns_true,
        test_drift_corrupted_price,
        test_drift_corrupted_amount,
        test_drift_ghost_lot,
        test_drift_missing_lot,
        test_empty_memory_with_db_lots,
        test_non_empty_memory_with_empty_db,
        test_idempotent_after_rebuild,
        test_db_error_returns_true_safely,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print()
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ CRASHED: {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"  ALL {len(tests)} TESTS PASSED ✓")
        sys.exit(0)
    else:
        print(f"  {failed}/{len(tests)} TESTS FAILED ✗")
        sys.exit(1)
