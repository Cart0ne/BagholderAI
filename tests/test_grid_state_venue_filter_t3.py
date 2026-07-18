"""
T.3 — get_grid_state must filter the Grid budget to venue=binance.

Root cause (verified 2026-07-18): `commentary.get_grid_state` summed
`capital_allocation` over ALL managed_by=grid rows with no venue filter. The
Kraken collaudo row (BTC/USD, $25, venue=kraken, is_active=false,
cycle=kraken_test) leaked its $25 into `grid_budget` → "Started with $525",
net worth +$25, cash +$25, and inflated the P&L % denominator (the $ P&L
itself cancels, since total_pnl = total_value - grid_budget). Same phantom the
public site had (fixed web-side in f6388b6, S119b); this is the bot-side twin
that feeds both the Telegram daily report and the daily_pnl snapshot.

Fix = one line: `.eq("venue", "binance")` on the bot_config query.

This test seeds the REAL four bot_config rows (3 binance + 1 kraken) into a
fake Supabase client that faithfully applies `.eq()` filters. If the venue
filter is ever removed, the fake returns all four rows → budget 525 → the
assertions fail. So the test pins behaviour, not the implementation string.

Run:
    python tests/test_grid_state_venue_filter_t3.py
    # or: pytest tests/test_grid_state_venue_filter_t3.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commentary


# ----------------------------------------------------------------------
# Fake Supabase client that honours .eq() filters (so the venue filter is
# genuinely exercised, not stubbed away).
# ----------------------------------------------------------------------

class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def execute(self):
        out = [
            r for r in self._rows
            if all(r.get(k) == v for k, v in self._filters.items())
        ]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables  # name -> list[dict]

    def table(self, name):
        return FakeQuery(list(self._tables.get(name, [])))


# Real bot_config rows as of 2026-07-18 (capital_allocation as strings, like
# PostgREST returns numeric columns over JSON).
BOT_CONFIG_ROWS = [
    {"symbol": "BTC/USDT",  "managed_by": "grid", "is_active": True,  "venue": "binance", "cycle": "testnet_2",   "capital_allocation": "200"},
    {"symbol": "SOL/USDT",  "managed_by": "grid", "is_active": True,  "venue": "binance", "cycle": "testnet_2",   "capital_allocation": "150"},
    {"symbol": "BONK/USDT", "managed_by": "grid", "is_active": True,  "venue": "binance", "cycle": "testnet_2",   "capital_allocation": "150"},
    {"symbol": "BTC/USD",   "managed_by": "grid", "is_active": False, "venue": "kraken",  "cycle": "kraken_test", "capital_allocation": "25"},
]


def _run_get_grid_state(monkeypatch=None):
    fake = FakeSupabase({
        "bot_config": BOT_CONFIG_ROWS,
        "trades": [],
        "reserve_ledger": [],
    })

    # Neutralise external calls: current cycle + live prices.
    orig_cycle = commentary.get_current_cycle
    orig_prices = commentary.fetch_binance_prices
    commentary.get_current_cycle = lambda _c: "testnet_2"
    commentary.fetch_binance_prices = lambda _syms: {}
    try:
        return commentary.get_grid_state(fake)
    finally:
        commentary.get_current_cycle = orig_cycle
        commentary.fetch_binance_prices = orig_prices


def test_grid_budget_excludes_kraken_row():
    state = _run_get_grid_state()
    # 200 + 150 + 150 = 500 (Kraken $25 row excluded).
    assert state["initial_capital"] == 500.0, (
        f"grid budget should be 500 (venue=binance only), got {state['initial_capital']}. "
        "Did the .eq('venue','binance') filter get dropped?"
    )


def test_no_phantom_kraken_position():
    state = _run_get_grid_state()
    syms = [p["symbol"] for p in state["positions"]]
    assert "BTC/USD" not in syms, (
        f"Kraken BTC/USD must not appear as a (zero) Grid position, got {syms}"
    )
    assert set(syms) == {"BTC/USDT", "SOL/USDT", "BONK/USDT"}, syms


def test_total_pnl_is_venue_invariant():
    # With no trades: realized=0, unrealized=0 → total_value == budget → pnl 0.
    # The point: total_pnl = total_value - grid_budget cancels the $25 either
    # way; the fix moves initial_capital/cash/%, never the $ P&L.
    state = _run_get_grid_state()
    assert state["total_pnl"] == 0.0, state["total_pnl"]
    assert state["total_value"] == 500.0, state["total_value"]


if __name__ == "__main__":
    test_grid_budget_excludes_kraken_row()
    test_no_phantom_kraken_position()
    test_total_pnl_is_venue_invariant()
    print("PASS — T.3: get_grid_state filters grid budget to venue=binance (500, no $25 phantom).")
