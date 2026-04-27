"""
BagHolderAI - 45g Gain Saturation tests

Exercises the helper functions in bot/trend_follower/gain_saturation.py:
period-start lookup vs ALLOCATE/DEALLOCATE history, positive-sells counter
on a real-shape trades query, override resolution.

    python3.13 tests/test_gain_saturation.py
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.trend_follower.gain_saturation import (
    count_positive_sells_since,
    get_period_start,
    resolve_effective_n,
)


# ---------------------------------------------------------------------------
# Minimal Supabase mock — supports the chained-call shape used in production.
# ---------------------------------------------------------------------------

class MockResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class MockQuery:
    """
    A query object that records filters and returns a pre-canned result based
    on which table+filters were applied.
    """
    def __init__(self, table_name, store):
        self.table_name = table_name
        self.store = store
        self.filters = {"eq": {}, "gt": {}, "gte": {}}
        self.order_field = None
        self.order_desc = False
        self.limit_n = None
        self.count_mode = None

    def select(self, _cols, count=None):
        if count == "exact":
            self.count_mode = "exact"
        return self

    def eq(self, k, v):
        self.filters["eq"][k] = v
        return self

    def gt(self, k, v):
        self.filters["gt"][k] = v
        return self

    def gte(self, k, v):
        self.filters["gte"][k] = v
        return self

    def order(self, f, desc=False):
        self.order_field = f
        self.order_desc = desc
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def execute(self):
        rows = self.store.get(self.table_name, [])

        def matches(row):
            for k, v in self.filters["eq"].items():
                if row.get(k) != v:
                    return False
            for k, v in self.filters["gt"].items():
                if not (str(row.get(k)) > str(v)):
                    return False
            for k, v in self.filters["gte"].items():
                if not (str(row.get(k)) >= str(v)):
                    return False
            return True

        filtered = [r for r in rows if matches(r)]
        if self.order_field:
            filtered.sort(
                key=lambda r: r.get(self.order_field, ""),
                reverse=self.order_desc,
            )
        if self.limit_n is not None:
            filtered = filtered[: self.limit_n]
        if self.count_mode == "exact":
            return MockResult(filtered, count=len(filtered))
        return MockResult(filtered)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockQuery(name, self.store)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_period_start_no_history():
    sb = MockSupabase({"trend_decisions_log": []})
    assert get_period_start(sb, "MOVR/USDT") is None
    print("  [ok] no history → None")


def test_period_start_first_allocate_no_dealloc():
    sb = MockSupabase({
        "trend_decisions_log": [
            {"symbol": "MOVR/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-25T10:00:00+00:00"},
        ],
    })
    ps = get_period_start(sb, "MOVR/USDT")
    assert ps is not None
    assert ps.isoformat() == "2026-04-25T10:00:00+00:00"
    print("  [ok] first ALLOCATE, no DEALLOCATE → that ALLOCATE")


def test_period_start_after_dealloc():
    sb = MockSupabase({
        "trend_decisions_log": [
            {"symbol": "MOVR/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-20T10:00:00+00:00"},
            {"symbol": "MOVR/USDT", "action_taken": "DEALLOCATE",
             "scan_timestamp": "2026-04-22T10:00:00+00:00"},
            {"symbol": "MOVR/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-25T10:00:00+00:00"},
            {"symbol": "MOVR/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-25T11:00:00+00:00"},  # update
        ],
    })
    ps = get_period_start(sb, "MOVR/USDT")
    assert ps.isoformat() == "2026-04-25T10:00:00+00:00", (
        f"expected 2026-04-25T10:00:00+00:00, got {ps.isoformat()}"
    )
    print("  [ok] post-DEALLOCATE → first ALLOCATE after dealloc, NOT update at 11:00")


def test_period_start_ignores_other_symbols():
    sb = MockSupabase({
        "trend_decisions_log": [
            {"symbol": "MBOX/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-20T10:00:00+00:00"},
            {"symbol": "MBOX/USDT", "action_taken": "DEALLOCATE",
             "scan_timestamp": "2026-04-26T10:00:00+00:00"},
            {"symbol": "MOVR/USDT", "action_taken": "ALLOCATE",
             "scan_timestamp": "2026-04-25T10:00:00+00:00"},
        ],
    })
    ps = get_period_start(sb, "MOVR/USDT")
    assert ps.isoformat() == "2026-04-25T10:00:00+00:00"
    print("  [ok] other symbols' DEALLOCATE rows ignored")


def test_count_positive_sells_basic():
    since = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)
    sb = MockSupabase({
        "trades": [
            # In-period positive sells (count = 4)
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 1.0,
             "created_at": "2026-04-25T11:00:00+00:00", "id": 1},
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 0.5,
             "created_at": "2026-04-25T12:00:00+00:00", "id": 2},
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 2.0,
             "created_at": "2026-04-25T13:00:00+00:00", "id": 3},
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 0.1,
             "created_at": "2026-04-25T14:00:00+00:00", "id": 4},
            # In-period but negative — must NOT count
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": -3.0,
             "created_at": "2026-04-25T15:00:00+00:00", "id": 5},
            # In-period buy — must NOT count
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "buy", "realized_pnl": None,
             "created_at": "2026-04-25T11:30:00+00:00", "id": 6},
            # Pre-period positive sell — must NOT count
            {"symbol": "MOVR/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 5.0,
             "created_at": "2026-04-20T10:00:00+00:00", "id": 7},
            # In-period positive sell on different coin — must NOT count
            {"symbol": "MBOX/USDT", "managed_by": "trend_follower",
             "side": "sell", "realized_pnl": 5.0,
             "created_at": "2026-04-25T13:00:00+00:00", "id": 8},
            # In-period positive sell but managed_by=manual — must NOT count
            {"symbol": "MOVR/USDT", "managed_by": "manual",
             "side": "sell", "realized_pnl": 5.0,
             "created_at": "2026-04-25T13:00:00+00:00", "id": 9},
        ],
    })
    n = count_positive_sells_since(sb, "MOVR/USDT", since)
    assert n == 4, f"expected 4, got {n}"
    print(f"  [ok] counted {n} positive TF sells (excluded buys/losses/pre-period/other-coin/manual)")


def test_resolve_effective_n_default():
    assert resolve_effective_n(4, None) == 4
    assert resolve_effective_n(4, 0) == 0  # 0 = "disabled per coin" — caller handles
    assert resolve_effective_n(4, 3) == 3
    assert resolve_effective_n(4, 6) == 6
    print("  [ok] override precedence resolves correctly")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    tests = [
        ("get_period_start no history", test_period_start_no_history),
        ("get_period_start first ALLOCATE", test_period_start_first_allocate_no_dealloc),
        ("get_period_start ignores ALLOCATE-update", test_period_start_after_dealloc),
        ("get_period_start scoped per symbol", test_period_start_ignores_other_symbols),
        ("count_positive_sells filters correctly", test_count_positive_sells_basic),
        ("resolve_effective_n", test_resolve_effective_n_default),
    ]
    failures = 0
    for name, fn in tests:
        print(f"[test] {name}")
        try:
            fn()
        except Exception as e:
            print(f"  [FAIL] {e}")
            failures += 1
    if failures:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
