"""
T.2 — the private daily report must show the day's real equity move
(realized + paper), not only realized-from-sells.

Symptom: on a no-sell day the report showed "Today · Realized 🟢 $+0.00" even
when open positions dropped several dollars, looking falsely flat. Fix: add a
"Day P&L (Grid)" line = today's Grid total_pnl − yesterday's snapshot total_pnl
(= realized + change in paper P&L). Falls back to the old realized-only line
when there is no yesterday baseline.

T.4 (2026-08-06) — the decomposition of that move was itself misleading. It
showed "sells $X · paper $Y" with paper deduced as (move − realized), so every
profitable sell landed twice: as a gain in sells and as an equal loss in paper,
making paper read like a market drop that never happened. Real case 06/08:
move −1.50 rendered as "sells +1.53 · paper −3.03" while the market had only
taken −2.13 and the bot had actually *added* +0.63. Fix: measure the market leg
from yesterday's closing prices × yesterday's quantities, and leave trading as
the residual.

This test pins four things:
  1. get_yesterday_grid_pnl reads total_pnl (NOT total_value) → the number is
     invariant to the $25 Kraken phantom, so it stays honest across the restart
     that removes the phantom.
  2. compute_market_move measures the do-nothing baseline, and refuses to
     invent a $0.00 market when yesterday's positions are unknown.
  3. The private renderer emits "Day P&L (Grid)" + the market/trading split
     with the right signs, and never resurrects the double-counted paper line.
  4. Fallbacks survive: no baseline → old realized-only line; baseline but no
     yesterday positions → total move with no split.

Run:
    python tests/test_daily_report_day_move_t2.py
    # or: pytest tests/test_daily_report_day_move_t2.py
"""

import asyncio
import os
import sys
import types
from datetime import date, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commentary

# The MacBook dev venv has a broken python-telegram-bot install (the bot only
# runs on the Mac Mini). Prefer the real package (so on the Mini/CI this is a
# genuine end-to-end render test); fall back to a minimal stub so the renderer
# logic is still testable locally. The stub does not affect the rendered text
# (ParseMode is only ever passed as a parameter, never embedded), and Bot is
# never instantiated here — the renderer is exercised via __new__.
try:
    import telegram  # noqa: F401
    import telegram.constants  # noqa: F401
except Exception:
    _tg = types.ModuleType("telegram")

    class _Bot:  # pragma: no cover - never instantiated in this test
        def __init__(self, *a, **k):
            pass

    _tg.Bot = _Bot
    _constants = types.ModuleType("telegram.constants")

    class _ParseMode:
        HTML = "HTML"

    _constants.ParseMode = _ParseMode
    _tg.constants = _constants
    sys.modules["telegram"] = _tg
    sys.modules["telegram.constants"] = _constants

from utils.telegram_notifier import TelegramNotifier


# ----------------------------------------------------------------------
# Fake Supabase honouring .eq()/.limit() (same idiom as the T.3 test).
# ----------------------------------------------------------------------

class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}
        self._limit = None

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def execute(self):
        out = [
            r for r in self._rows
            if all(r.get(k) == v for k, v in self._filters.items())
        ]
        if self._limit is not None:
            out = out[: self._limit]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(list(self._tables.get(name, [])))


YESTERDAY = str(date.today() - timedelta(days=1))


# ----------------------------------------------------------------------
# 1. get_yesterday_grid_pnl: reads total_pnl, phantom-invariant.
# ----------------------------------------------------------------------

def test_yesterday_grid_pnl_reads_total_pnl_not_value():
    # total_value is phantom-inflated (525-based) but total_pnl is clean.
    fake = FakeSupabase({"daily_pnl": [
        {"date": YESTERDAY, "cycle": "testnet_2", "total_pnl": "-2.66", "total_value": "522.34"},
    ]})
    val = commentary.get_yesterday_grid_pnl(fake, "testnet_2")
    assert val == -2.66, f"expected -2.66 (total_pnl), got {val}"


def test_yesterday_grid_pnl_none_when_missing():
    fake = FakeSupabase({"daily_pnl": []})
    assert commentary.get_yesterday_grid_pnl(fake, "testnet_2") is None
    # Also None when only an older date exists (strict yesterday).
    fake2 = FakeSupabase({"daily_pnl": [
        {"date": "2020-01-01", "cycle": "testnet_2", "total_pnl": "5.0"},
    ]})
    assert commentary.get_yesterday_grid_pnl(fake2, "testnet_2") is None


def test_yesterday_snapshot_parses_positions_json():
    # db/client.py stores positions as a json.dumps'd string.
    fake = FakeSupabase({"daily_pnl": [{
        "date": YESTERDAY, "cycle": "testnet_2", "total_pnl": "-27.34",
        "positions": '[{"symbol": "SOL/USDT", "holdings": 0.812187, "value": 60.5729}]',
    }]})
    snap = commentary.get_yesterday_grid_snapshot(fake, "testnet_2")
    assert snap["total_pnl"] == -27.34, snap
    assert snap["positions"][0]["symbol"] == "SOL/USDT", snap


def test_yesterday_snapshot_positions_none_when_unparseable():
    # Old rows / corrupt JSON must yield None (→ no split), never [] (→ $0.00
    # market, which would be a lie).
    for bad in (None, "not json", '{"not": "a list"}'):
        fake = FakeSupabase({"daily_pnl": [
            {"date": YESTERDAY, "cycle": "testnet_2", "total_pnl": "-27.34", "positions": bad},
        ]})
        snap = commentary.get_yesterday_grid_snapshot(fake, "testnet_2")
        assert snap["positions"] is None, f"{bad!r} → {snap}"


# ----------------------------------------------------------------------
# 1b. T.4 compute_market_move: measured, not deduced.
# ----------------------------------------------------------------------

def test_market_move_matches_the_06_08_incident():
    """The day that exposed the bug. Grid move −1.50 was rendered as
    'sells +1.53 · paper −3.03'; the market had actually taken −2.13 and the
    bot had added +0.63 (BTC: 67% of the position sold during the day)."""
    yesterday = [
        {"symbol": "BTC/USDT", "holdings": 0.00233766, "value": 151.4056},
        {"symbol": "SOL/USDT", "holdings": 0.812187, "value": 60.5729},
        {"symbol": "BONK/USDT", "holdings": 33137599.0203857, "value": 93.1167},
    ]
    today = [
        {"symbol": "BTC/USDT", "holdings": 0.00077689, "value": 50.2039},
        {"symbol": "SOL/USDT", "holdings": 0.812187, "value": 59.444},
        {"symbol": "BONK/USDT", "holdings": 33137599.0203857, "value": 92.4539},
    ]
    market = commentary.compute_market_move(yesterday, today)
    assert market == -2.13, f"expected -2.13, got {market}"
    # Trading is the residual the renderer computes.
    assert round(-1.50 - market, 2) == 0.63


def test_market_move_ignores_quantity_bought_today():
    """A position opened today has no yesterday quantity → contributes 0 to
    the market leg (opening-balance baseline)."""
    yesterday = []
    today = [{"symbol": "ETH/USDT", "holdings": 0.5, "value": 1000.0}]
    assert commentary.compute_market_move(yesterday, today) == 0.0


def test_market_move_prefers_live_price_over_value_ratio():
    # Live state carries live_price; a fully-sold position has value 0 but a
    # valid price, so the market leg must still be measurable.
    yesterday = [{"symbol": "SOL/USDT", "holdings": 2.0, "value": 200.0}]
    today = [{"symbol": "SOL/USDT", "holdings": 0.0, "value": 0.0, "live_price": 90.0}]
    # Price went 100 → 90 on 2 SOL held at yesterday's close.
    assert commentary.compute_market_move(yesterday, today) == -20.0


def test_market_move_none_when_yesterday_positions_unknown():
    assert commentary.compute_market_move(None, [{"symbol": "BTC/USDT"}]) is None


def test_market_move_skips_symbol_missing_today():
    """Coin dropped from bot_config mid-day: skipped, its move falls into the
    residual — but the other symbols are still measured."""
    yesterday = [
        {"symbol": "SOL/USDT", "holdings": 2.0, "value": 200.0},
        {"symbol": "GONE/USDT", "holdings": 5.0, "value": 50.0},
    ]
    today = [{"symbol": "SOL/USDT", "holdings": 2.0, "value": 180.0}]
    assert commentary.compute_market_move(yesterday, today) == -20.0


# ----------------------------------------------------------------------
# 2. Private renderer: honest "Day P&L (Grid)" line + fallback.
# ----------------------------------------------------------------------

def _render_private(data):
    """Run the real renderer, capturing the text instead of sending it."""
    n = TelegramNotifier.__new__(TelegramNotifier)  # skip __init__ → no Bot/network
    captured = {}

    async def fake_send(text, *a, **k):
        captured["text"] = text
        return True

    n.send_message = fake_send
    asyncio.run(n.send_private_daily_report(data))
    return captured["text"]


_BASE = {
    "day_number": 44,
    "mode": "LIVE TESTNET",
    "total_value": 482.94,
    "initial_capital": 500,
    "total_pnl": -17.06,
    "cash": 308.10,
    "holdings_value": 157.25,
    "today_trades_count": 0,
    "today_buys": 0,
    "today_sells": 0,
    "today_realized": 0.0,
    "today_fees": 0.12,
    "positions": [],
    "tf": {},
    "skim_by_sym": {},
}


def test_renderer_shows_day_move_on_nosell_loss():
    # The real T.2 scenario: 0 sells, portfolio down $14.40 on paper — which
    # is all market, no trading.
    data = {
        **_BASE,
        "today_grid_move": -14.40,
        "today_grid_realized": 0.0,
        "today_market_move": -14.40,
    }
    text = _render_private(data)
    assert "Day P&L (Grid): 🔴 $-14.40" in text, text
    assert "Market (open positions): 🔴 $-14.40" in text, text
    assert "Trading (net of fees): 🟢 $+0.00" in text, text
    # The misleading realized-only headline must be gone in this branch.
    assert "Today (combined)" not in text, text


def test_renderer_splits_move_into_market_and_trading():
    """T.4 on the 06/08 numbers: the day the old split lied."""
    data = {
        **_BASE,
        "today_grid_move": -1.50,
        "today_grid_realized": 1.53,
        "today_market_move": -2.13,
    }
    text = _render_private(data)
    assert "Day P&L (Grid): 🔴 $-1.50" in text, text
    assert "Market (open positions): 🔴 $-2.13" in text, text
    assert "Trading (net of fees): 🟢 $+0.63" in text, text
    # Realized survives as cash secured, not as P&L earned today.
    assert "Locked in: $+1.53" in text, text
    # The double-counted decomposition must never come back.
    assert "paper $" not in text, text
    assert "sells $" not in text, text


def test_renderer_omits_split_when_market_unknown():
    """Baseline present but yesterday's positions unknown (pre-T.4 snapshot):
    show the total move, claim nothing about its composition."""
    data = {
        **_BASE,
        "today_grid_move": 5.00,
        "today_grid_realized": 2.00,
        "today_market_move": None,
    }
    text = _render_private(data)
    assert "Day P&L (Grid): 🟢 $+5.00" in text, text
    assert "Market (open positions)" not in text, text
    assert "Trading (net of fees)" not in text, text


def test_renderer_falls_back_when_no_baseline():
    data = {**_BASE, "today_grid_move": None}
    text = _render_private(data)
    assert "Today (combined)" in text, text
    assert "Realized: 🟢 $+0.00" in text, text
    assert "Day P&L (Grid)" not in text, text


if __name__ == "__main__":
    test_yesterday_grid_pnl_reads_total_pnl_not_value()
    test_yesterday_grid_pnl_none_when_missing()
    test_yesterday_snapshot_parses_positions_json()
    test_yesterday_snapshot_positions_none_when_unparseable()
    test_market_move_matches_the_06_08_incident()
    test_market_move_ignores_quantity_bought_today()
    test_market_move_prefers_live_price_over_value_ratio()
    test_market_move_none_when_yesterday_positions_unknown()
    test_market_move_skips_symbol_missing_today()
    test_renderer_shows_day_move_on_nosell_loss()
    test_renderer_splits_move_into_market_and_trading()
    test_renderer_omits_split_when_market_unknown()
    test_renderer_falls_back_when_no_baseline()
    print("PASS — T.2/T.4: private report shows the honest day equity move split into "
          "measured market + trading residual, helper is phantom-invariant, "
          "both fallbacks preserved.")
