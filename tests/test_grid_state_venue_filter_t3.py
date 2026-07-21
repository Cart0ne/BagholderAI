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


# ----------------------------------------------------------------------
# T.3 (fee half) — get_grid_state headline must be NET of fees, byte-identical
# to the site hero (pnl-canonical.ts). Fees are money already spent, not held.
# Canonical identity: total_value = budget − netInvested + holdings − fees.
# ----------------------------------------------------------------------

# One coin, one buy + one sell, real fees + skim + a live price. Clean scenario
# (no dust-reset drift) so the correction isolates the FEE term.
NET_OF_FEE_TRADES = [
    {"symbol": "BTC/USDT", "side": "buy",  "amount": 1.0, "price": 100.0, "cost": 100.0,
     "fee": 0.10, "fee_asset": "USDT", "realized_pnl": 0.0,  "created_at": "2026-07-01T00:00:00",
     "config_version": "v3", "cycle": "testnet_2", "managed_by": "grid"},
    {"symbol": "BTC/USDT", "side": "sell", "amount": 0.5, "price": 120.0, "cost": 60.0,
     "fee": 0.06, "fee_asset": "USDT", "realized_pnl": 9.94, "created_at": "2026-07-02T00:00:00",
     "config_version": "v3", "cycle": "testnet_2", "managed_by": "grid"},
]


def _run_with_trades():
    fake = FakeSupabase({
        "bot_config": BOT_CONFIG_ROWS,
        "trades": NET_OF_FEE_TRADES,
        "reserve_ledger": [
            {"symbol": "BTC/USDT", "amount": "2.0", "config_version": "v3", "cycle": "testnet_2"},
        ],
    })
    orig_cycle = commentary.get_current_cycle
    orig_prices = commentary.fetch_binance_prices
    commentary.get_current_cycle = lambda _c: "testnet_2"
    commentary.fetch_binance_prices = lambda _syms: {"BTC/USDT": 110.0}
    try:
        return commentary.get_grid_state(fake)
    finally:
        commentary.get_current_cycle = orig_cycle
        commentary.fetch_binance_prices = orig_prices


def test_total_value_is_net_of_fees():
    state = _run_with_trades()
    # net_invested = 100 − 60 = 40 · holdings = 0.5 × 110 = 55 · fees = 0.16 · skim = 2
    # total_value = 500 − 40 + 55 − 0.16 = 514.84  (NET of fees)
    # cash        = 500 − 40 − 2      = 458.00
    assert abs(state["total_value"] - 514.84) < 0.01, state["total_value"]
    assert abs(state["cash"] - 458.00) < 0.01, state["cash"]
    assert abs(state["total_pnl"] - 14.84) < 0.01, state["total_pnl"]
    # The pre-fix gross formula (budget + DB-realized + unrealized) would read
    # 500 + 9.94 + 5 = 514.94 → strictly higher by the (buy) fee. Guard against
    # a regression back to gross-of-fee.
    assert state["total_value"] < 514.94, (
        f"total_value {state['total_value']} looks gross-of-fee (>= 514.94)"
    )


if __name__ == "__main__":
    test_grid_budget_excludes_kraken_row()
    test_no_phantom_kraken_position()
    test_total_pnl_is_venue_invariant()
    test_total_value_is_net_of_fees()
    print("PASS — T.3: get_grid_state filters grid budget to venue=binance (500, no $25 phantom) + net-of-fee headline.")
