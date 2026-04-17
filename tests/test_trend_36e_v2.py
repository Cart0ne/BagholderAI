"""
BagHolderAI - Session 36e v2 tests
Exercises the hybrid rotation, on-demand rescan fallback, and ATR-adaptive
steps introduced by brief_36e_tf_rotation_atr_adaptive_v2.md.

Runs as a pure-Python script (no pytest), matching the existing tests/ style.
    python3.13 tests/test_trend_36e_v2.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.trend_follower.allocator import (
    _adaptive_steps,
    _hours_since,
    _fetch_unrealized_pnl,
    decide_allocations,
    SWAP_STRENGTH_DELTA,
    SWAP_COOLDOWN_HOURS,
    SWAP_MIN_PROFIT_PCT,
)


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

class MockSupabaseTable:
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        data = self._rows
        for k, v in self._filters.items():
            data = [r for r in data if r.get(k) == v]
        return type("R", (), {"data": data})()


class MockSupabase:
    def __init__(self, trades_rows=None):
        self._trades = trades_rows or []

    def table(self, name):
        if name == "trades":
            return MockSupabaseTable(self._trades)
        return MockSupabaseTable([])


class MockExchange:
    """Satisfies the exchange-not-None check; never actually called unless
    an active symbol is missing from coin_lookup."""
    def fetch_ticker(self, sym):
        raise RuntimeError("should not be called in these tests")

    def fetch_ohlcv(self, *_a, **_k):
        raise RuntimeError("should not be called in these tests")


class RaisingExchange:
    """Used to test on-demand rescan fallback."""
    def __init__(self, kind="timeout"):
        self.kind = kind

    def fetch_ticker(self, sym):
        if self.kind == "timeout":
            raise TimeoutError("simulated binance timeout")
        raise ValueError("simulated malformed response")

    def fetch_ohlcv(self, *_a, **_k):
        return self.fetch_ticker("x")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()


def make_coin(symbol, signal="BULLISH", strength=50.0, price=100.0, atr=3.0,
              rsi=60.0, ema_fast=105.0, ema_slow=100.0):
    return {
        "symbol": symbol,
        "price": price,
        "volume_24h": 1_000_000,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "rsi": rsi,
        "atr": atr,
        "atr_avg": atr / 1.1,
        "signal": signal,
        "signal_strength": strength,
    }


def make_alloc(symbol, capital=50.0, hours_ago=10.0):
    return {
        "symbol": symbol,
        "is_active": True,
        "capital_allocation": capital,
        "managed_by": "trend_follower",
        "updated_at": _iso_hours_ago(hours_ago),
        "created_at": _iso_hours_ago(hours_ago + 24),
    }


def _actions(decisions, symbol):
    return [d["action_taken"] for d in decisions if d["symbol"] == symbol]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

results = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append((status, name, detail))
    print(f"  [{status}] {name}{(' — ' + detail) if detail else ''}")


# --- ATR adaptive (Fix 2) -------------------------------------------------
print("\n=== ATR adaptive steps ===")

buy, sell = _adaptive_steps(make_coin("X", atr=6.0, price=100.0), "BULLISH")
check("ATR 6%: buy=4.8 sell=7.2", buy == 4.8 and sell == 7.2, f"buy={buy} sell={sell}")

buy, sell = _adaptive_steps(make_coin("X", atr=0.5, price=100.0), "BULLISH")
check("ATR 0.5% clamps to min 1.0/1.0", buy == 1.0 and sell == 1.0, f"buy={buy} sell={sell}")

buy, sell = _adaptive_steps(make_coin("X", atr=15.0, price=100.0), "BULLISH")
check("ATR 15%: sell clamps to 8.0 and buy stays <=10.0",
      sell == 8.0 and buy <= 10.0, f"buy={buy} sell={sell}")

buy, sell = _adaptive_steps(make_coin("X", atr=0, price=100.0), "BULLISH")
check("ATR=0 fallback BULLISH → 1.5/1.2", buy == 1.5 and sell == 1.2)

buy, sell = _adaptive_steps(make_coin("X", atr=0, price=100.0), "BEARISH")
check("ATR=0 fallback BEARISH → 2.0/0.8", buy == 2.0 and sell == 0.8)

buy, sell = _adaptive_steps(make_coin("X", atr=3.0, price=100.0), "BEARISH")
# buy = max(1.0, min(10.0, 3 * 0.8)) * 1.1 = 2.4 * 1.1 = 2.64
check("ATR 3% BEARISH: buy=2.64 sell=3.6", buy == 2.64 and sell == 3.6,
      f"buy={buy} sell={sell}")


# --- _hours_since sanity ---------------------------------------------------
print("\n=== _hours_since ===")
check("None → +inf", _hours_since(None) == float("inf"))
h = _hours_since(_iso_hours_ago(5))
check("ISO 5h ago ≈ 5", 4.9 < h < 5.1, f"got {h:.3f}")


# --- Rotation SWAP (Fix 1) -------------------------------------------------
print("\n=== Rotation SWAP gates ===")
config = {"tf_max_coins": 2}
filters = {}  # no filters required for SWAP logic itself
tiers = {}

# Boundary: delta = 20.0 exactly should SWAP (>= inclusive)
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0),
    make_coin("ORDI/USDT", "BULLISH", strength=50.0),
]
allocs = [make_alloc("AXL/USDT", 50.0, hours_ago=10.0)]
# Return 0 unrealized via an empty trades list → passes -1% of $50 = -$0.50 gate (0 > -0.5)
mock_sb = MockSupabase(trades_rows=[])
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb)
check("delta=+20 exact triggers SWAP (DEALLOCATE)",
      "DEALLOCATE" in _actions(decs, "AXL/USDT"),
      f"actions={_actions(decs, 'AXL/USDT')}")
check("replacement ORDI ALLOCATE in same scan",
      "ALLOCATE" in _actions(decs, "ORDI/USDT"))

# Below delta (15 < 20): HOLD, no SWAP
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0),
    make_coin("ORDI/USDT", "BULLISH", strength=45.0),
]
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb)
check("delta<20 → HOLD, no SWAP", _actions(decs, "AXL/USDT") == ["HOLD"],
      f"actions={_actions(decs, 'AXL/USDT')}")

# Cooldown: held only 6h (<8h) should NOT swap even with delta=+30
allocs = [make_alloc("AXL/USDT", 50.0, hours_ago=6.0)]
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0),
    make_coin("ORDI/USDT", "BULLISH", strength=60.0),
]
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb)
check("held 6h < cooldown 8h blocks SWAP",
      _actions(decs, "AXL/USDT") == ["HOLD"])

# Profit gate: allocation=$50, unrealized loss -$0.51 should block (threshold -$0.50)
# avg_buy 100, holdings 1, current 99.49 → unrealized = -0.51
allocs = [make_alloc("AXL/USDT", 50.0, hours_ago=10.0)]
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0, price=99.49),
    make_coin("ORDI/USDT", "BULLISH", strength=60.0),
]
mock_sb_loss = MockSupabase(trades_rows=[
    {"symbol": "AXL/USDT", "side": "buy", "amount": 1.0, "price": 100.0,
     "managed_by": "trend_follower", "config_version": "v3"},
])
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb_loss)
check("unrealized -$0.51 on $50 alloc blocks SWAP",
      _actions(decs, "AXL/USDT") == ["HOLD"])

# Profit gate: allocation=$50, unrealized loss -$0.49 allows SWAP (above -$0.50)
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0, price=99.51),
    make_coin("ORDI/USDT", "BULLISH", strength=60.0),
]
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb_loss)
check("unrealized -$0.49 on $50 alloc allows SWAP",
      "DEALLOCATE" in _actions(decs, "AXL/USDT"))

# Two active both above delta — only one SWAP, other HOLD
allocs = [
    make_alloc("AXL/USDT", 40.0, hours_ago=10.0),
    make_alloc("MBOX/USDT", 40.0, hours_ago=10.0),
]
coins = [
    make_coin("AXL/USDT", "BULLISH", strength=30.0),
    make_coin("MBOX/USDT", "BULLISH", strength=30.0),
    make_coin("ORDI/USDT", "BULLISH", strength=55.0),  # +25 over both
]
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=MockExchange(), supabase=mock_sb)
deallocated = [d["symbol"] for d in decs if d["action_taken"] == "DEALLOCATE"]
check("2 active meriting SWAP → only 1 swapped",
      len(deallocated) == 1, f"deallocated={deallocated}")


# --- On-demand rescan fallback (Problema 0) -------------------------------
print("\n=== On-demand rescan fallback ===")

# Active AXL is NOT in coin_lookup, exchange raises → legacy HOLD path
coins = [make_coin("ORDI/USDT", "BULLISH", strength=60.0)]  # AXL missing
allocs = [make_alloc("AXL/USDT", 50.0, hours_ago=10.0)]
decs = decide_allocations(coins, allocs, tiers, filters, config, 100.0,
                          exchange=RaisingExchange(), supabase=mock_sb)
check("Rescan failure → legacy HOLD for AXL",
      _actions(decs, "AXL/USDT") == ["HOLD"])


# --- Unrealized PnL helper ------------------------------------------------
print("\n=== _fetch_unrealized_pnl ===")
mock_sb_mix = MockSupabase(trades_rows=[
    {"symbol": "ANY/USDT", "side": "buy", "amount": 2.0, "price": 100.0,
     "managed_by": "trend_follower", "config_version": "v3"},
    {"symbol": "ANY/USDT", "side": "buy", "amount": 2.0, "price": 110.0,
     "managed_by": "trend_follower", "config_version": "v3"},
    {"symbol": "ANY/USDT", "side": "sell", "amount": 1.0, "price": 115.0,
     "managed_by": "trend_follower", "config_version": "v3"},
    # Manual trade must be excluded
    {"symbol": "ANY/USDT", "side": "buy", "amount": 10.0, "price": 1.0,
     "managed_by": "manual", "config_version": "v3"},
])
pnl = _fetch_unrealized_pnl(mock_sb_mix, "ANY/USDT", current_price=120.0)
# After replay: holdings=3, avg_buy_price = (100*2 + 110*2)/4 = 105 (sell doesn't touch avg)
# Unrealized = (120 - 105) * 3 = 45
check("PnL reconstruction excludes non-TF trades", abs(pnl - 45.0) < 1e-6,
      f"got {pnl}")

pnl_none = _fetch_unrealized_pnl(MockSupabase(trades_rows=[]), "X", 100.0)
check("No open position → 0.0", pnl_none == 0.0)


# --- Summary ---------------------------------------------------------------
print("\n=== Summary ===")
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print(f"  {passed}/{len(results)} passed, {failed} failed")
if failed:
    for r in results:
        if r[0] == "FAIL":
            print(f"    FAIL: {r[1]} — {r[2]}")
    sys.exit(1)
sys.exit(0)
