"""
S119 (K.1 Fase 2a) — Kraken order-proof readiness: unit tests.

Covers the review findings that only bite on a REAL order — validate=true
skipped them by construction, so Fase 1's "prova generale" (28/28) never
exercised these paths:

  1. Fill confirmation (CRITICAL): Kraken's AddOrder / AddOrderWithCost
     response carries ONLY {descr, txid} — no fill. KrakenClient now POLLS
     fetch_order(txid) and normalizes the QueryOrders response (which is the
     only one with vol_exec/price/fee). A test that mocks the REAL two-step
     shape (empty AddOrder → populated QueryOrders) must pass; the pre-fix code
     read `filled` off the empty AddOrder, saw 0, and returned None → the grid
     would re-order in a loop, spending real money and recording nothing.
  2. Halt-on-unconfirmed: if the fill never confirms within the poll budget the
     client raises OrderFillUnconfirmed so the caller HALTS — never retries
     (retrying re-orders and double-spends, Max S119).
  3. _alert_rejection gated on validate: a failed validate=true probe does NOT
     fire the prod Telegram alert / bot_events_log row; a real failure still does.

Run:  venv/bin/python3.13 -m pytest tests/test_kraken_fase2a_s119.py -q
"""

import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Telegram lib is broken on py3.13 (pre-existing env issue) — stub before any
# import chain that might touch it (mirrors tests/test_kraken_fase1_s118.py).
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from bot.exchanges.kraken_client import KrakenClient
from bot.exchanges.base import OrderFillUnconfirmed


# Kraken's real AddOrder / AddOrderWithCost ack: a txid, no fill data.
def _add_order_ack(txid="OABC-1"):
    return {"id": txid, "info": {"txid": [txid]}}


# QueryOrders (fetch_order) — the ONLY response that carries the executed fill.
def _query_order_filled(txid="OABC-1", filled=0.001, avg=25000.0, cost=25.0,
                        fee=0.20, currency="USD", status="closed"):
    return {"id": txid, "status": status, "filled": filled,
            "average": avg, "cost": cost,
            "fee": {"cost": fee, "currency": currency}}


# ----------------------------------------------------------------------
# 1. CRITICAL — confirm the real fill via a follow-up QueryOrders
# ----------------------------------------------------------------------

@patch("bot.exchanges.kraken_client.time.sleep", lambda *_: None)
def test_fill_confirmed_via_query_order_sell():
    ex = MagicMock()
    ex.create_order.return_value = _add_order_ack("OS-9")            # empty ack
    ex.fetch_order.return_value = _query_order_filled(
        "OS-9", filled=0.5, avg=103.0, cost=51.5, fee=0.41)         # real fill
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_sell("BTC/USD", 0.5)
    # Pre-fix regression guard: the empty ack → filled 0 → used to return None.
    assert out is not None
    ex.fetch_order.assert_called_with("OS-9", "BTC/USD")
    assert out["filled_amount"] == 0.5
    assert out["avg_price"] == 103.0
    assert out["cost"] == 51.5
    assert out["fee_cost"] == 0.41
    assert out["fee_base"] == 0.0        # Kraken fee in quote (USD), never base
    assert out["order_id"] == "OS-9"


@patch("bot.exchanges.kraken_client.time.sleep", lambda *_: None)
def test_fill_confirmed_via_query_order_cost_buy():
    ex = MagicMock()
    ex.create_market_buy_order_with_cost.return_value = _add_order_ack("OB-3")
    ex.fetch_order.return_value = _query_order_filled(
        "OB-3", filled=0.001, avg=25000.0, cost=25.0, fee=0.20)
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_buy("BTC/USD", 25.0)
    assert out is not None
    assert out["filled_amount"] == 0.001
    assert out["fee_cost"] == 0.20
    assert out["order_id"] == "OB-3"


@patch("bot.exchanges.kraken_client.time.sleep", lambda *_: None)
def test_fill_present_inline_skips_poll():
    # A response already carrying the fill (a mock or an inline-fill venue) is
    # normalized directly — no fetch_order round-trip.
    ex = MagicMock()
    ex.create_order.return_value = _query_order_filled(
        "OINLINE", filled=0.5, avg=103.0, cost=51.5, fee=0.41)
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_sell("BTC/USD", 0.5)
    assert out is not None and out["filled_amount"] == 0.5
    ex.fetch_order.assert_not_called()


# ----------------------------------------------------------------------
# 2. Halt-on-unconfirmed — raise, never return None (which would re-order)
# ----------------------------------------------------------------------

@patch("bot.exchanges.kraken_client.time.sleep", lambda *_: None)
def test_fill_never_confirms_raises_halt():
    ex = MagicMock()
    ex.create_order.return_value = _add_order_ack("OS-x")
    ex.fetch_order.return_value = {"id": "OS-x", "status": "open", "filled": 0.0}
    kc = KrakenClient(exchange=ex)
    with pytest.raises(OrderFillUnconfirmed) as exc:
        kc.place_market_sell("BTC/USD", 0.5)
    assert exc.value.order_id == "OS-x"
    # Really polled to the budget — did not give up after one read.
    assert ex.fetch_order.call_count >= 2


@patch("bot.exchanges.kraken_client.time.sleep", lambda *_: None)
def test_fill_unconfirmed_when_no_txid_raises_halt():
    ex = MagicMock()
    ex.create_order.return_value = {"info": {}}     # no id, no txid, no fill
    kc = KrakenClient(exchange=ex)
    with pytest.raises(OrderFillUnconfirmed):
        kc.place_market_sell("BTC/USD", 0.5)
    ex.fetch_order.assert_not_called()              # nothing to poll


# ----------------------------------------------------------------------
# 3. _alert_rejection gated on validate probes
# ----------------------------------------------------------------------

def test_alert_rejection_skipped_on_validate_failure():
    ex = MagicMock()
    ex.create_order.side_effect = RuntimeError("EOrder:Insufficient funds")
    kc = KrakenClient(exchange=ex)
    with patch("bot.exchanges.kraken_client._alert_rejection") as alert:
        out = kc.place_market_buy_base("BTC/USD", 0.00005, params={"validate": True})
    assert out is None
    alert.assert_not_called()                        # validate probe → no prod alert


def test_alert_rejection_fires_on_real_failure():
    ex = MagicMock()
    ex.create_order.side_effect = RuntimeError("EOrder:Insufficient funds")
    kc = KrakenClient(exchange=ex)
    with patch("bot.exchanges.kraken_client._alert_rejection") as alert:
        out = kc.place_market_buy_base("BTC/USD", 0.5)   # no validate → real order
    assert out is None
    alert.assert_called_once()                       # real rejection → alert fires
