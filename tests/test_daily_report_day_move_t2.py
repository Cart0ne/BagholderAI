"""
T.2 — the private daily report must show the day's real equity move
(realized + paper), not only realized-from-sells.

Symptom: on a no-sell day the report showed "Today · Realized 🟢 $+0.00" even
when open positions dropped several dollars, looking falsely flat. Fix: add a
"Day P&L (Grid)" line = today's Grid total_pnl − yesterday's snapshot total_pnl
(= realized + change in paper P&L), decomposed into sells vs paper. Falls back
to the old realized-only line when there is no yesterday baseline.

This test pins two things:
  1. get_yesterday_grid_pnl reads total_pnl (NOT total_value) → the number is
     invariant to the $25 Kraken phantom, so it stays honest across the restart
     that removes the phantom.
  2. The private renderer emits the honest "Day P&L (Grid)" line with the right
     sign/decomposition, and falls back to "Realized:" when the move is absent.

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
    # The real T.2 scenario: 0 sells, portfolio down $14.40 on paper.
    data = {**_BASE, "today_grid_move": -14.40, "today_grid_realized": 0.0}
    text = _render_private(data)
    assert "Day P&L (Grid): 🔴 $-14.40" in text, text
    assert "sells $+0.00 · paper $-14.40" in text, text
    # The misleading realized-only headline must be gone in this branch.
    assert "Today (combined)" not in text, text


def test_renderer_decomposes_move_into_sells_and_paper():
    data = {**_BASE, "today_grid_move": 5.00, "today_grid_realized": 2.00}
    text = _render_private(data)
    assert "Day P&L (Grid): 🟢 $+5.00" in text, text
    assert "sells $+2.00 · paper $+3.00" in text, text


def test_renderer_falls_back_when_no_baseline():
    data = {**_BASE, "today_grid_move": None}
    text = _render_private(data)
    assert "Today (combined)" in text, text
    assert "Realized: 🟢 $+0.00" in text, text
    assert "Day P&L (Grid)" not in text, text


if __name__ == "__main__":
    test_yesterday_grid_pnl_reads_total_pnl_not_value()
    test_yesterday_grid_pnl_none_when_missing()
    test_renderer_shows_day_move_on_nosell_loss()
    test_renderer_decomposes_move_into_sells_and_paper()
    test_renderer_falls_back_when_no_baseline()
    print("PASS — T.2: private report shows honest day equity move (realized + paper), "
          "helper is phantom-invariant, fallback preserved.")
