"""
S109 — order_id extraction in _normalize_order_response (MASTER bug: null
exchange_order_id on sell OP/USDT).

ccxt normalizes Binance's orderId into the unified `id` field, but some
responses (partial fills, testnet quirks — the historical OP/USDT sell)
arrive with `id` missing. Before S109 that produced order_id="" and a null
exchange_order_id in the DB, pushing reconciliation onto the weaker
timestamp heuristic. The fix falls back to the raw `info.orderId`.

These tests pin the three branches: normalized id present, fallback to raw
info, and the genuine empty case.

Run:
    python tests/test_order_id_fallback_s109.py
    # or: pytest tests/test_order_id_fallback_s109.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.exchange_orders import _normalize_order_response


def _filled_order(**overrides):
    """Minimal ccxt-style FILLED order response (status closed, filled > 0)."""
    order = {
        "id": "12345",
        "status": "closed",
        "filled": 2.0,
        "average": 1.5,
        "cost": 3.0,
        "fee": {"cost": 0.003, "currency": "USDT"},
        "info": {},
    }
    order.update(overrides)
    return order


def test_order_id_from_normalized_id():
    res = _normalize_order_response(_filled_order(id="999"), "OP/USDT", "sell")
    assert res is not None
    assert res["order_id"] == "999"


def test_order_id_falls_back_to_raw_info():
    # ccxt left `id` empty but Binance's raw payload still has orderId.
    res = _normalize_order_response(
        _filled_order(id=None, info={"orderId": 777}), "OP/USDT", "sell"
    )
    assert res is not None
    assert res["order_id"] == "777"


def test_order_id_empty_when_truly_absent():
    # Neither source available — stays "" (reconciliation uses timestamp).
    res = _normalize_order_response(
        _filled_order(id=None, info={}), "OP/USDT", "sell"
    )
    assert res is not None
    assert res["order_id"] == ""


def test_fill_fields_intact_with_fallback():
    # The fallback must not disturb the economic fields.
    res = _normalize_order_response(
        _filled_order(id=None, info={"orderId": 555}), "OP/USDT", "sell"
    )
    assert res["order_id"] == "555"
    assert res["filled_amount"] == 2.0
    assert res["avg_price"] == 1.5
    assert res["cost"] == 3.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
