"""
S133 — Telegram alert of the nightly Kraken reconciliation.

Max: a message in the trade-alert chat only when the reconciliation fails.
The 14-Oct SOL buy lost in a Supabase block sat in /admin as
DRIFT_EXCHANGE_ORPHAN for 4 nights before anyone saw it.
"""

import utils.telegram_notifier as tn
from scripts.reconcile_kraken import build_alert, fatal_alert, notify


def _ok(symbol):
    return {"symbol": symbol, "status": "OK", "balance_status": "OK",
            "balance_note": "gap +0.00000000 within tolerance", "drift_details": None}


def _sol_orphan():
    # The real 14-Oct case, as written in reconciliation_runs.drift_details
    return {
        "symbol": "SOL/USD", "status": "DRIFT_EXCHANGE_ORPHAN", "balance_status": "DRIFT_BALANCE",
        "balance_note": "gap +0.05309218 SOL (+3.96% of DB holdings)",
        "drift_details": {"drift": [], "in_db_not_on_kraken": [], "on_kraken_not_in_db": [{
            "at": "2026-10-14 13:26:02", "side": "buy", "qty": 0.05140078,
            "price": 104.97992442916235, "fee": 0.04317, "order_id": "OLSMHY-LEQKT-6D6UNK"}]},
    }


def test_clean_night_sends_nothing():
    assert build_alert([_ok("BTC/USD"), _ok("SOL/USD")]) is None


def test_lost_trade_names_order_and_symbol():
    text = build_alert([_ok("BTC/USD"), _sol_orphan()])
    assert "<b>SOL/USD</b> — DRIFT_EXCHANGE_ORPHAN" in text
    assert "On Kraken, not in DB: 2026-10-14 13:26:02 UTC BUY 0.05140078 @ $104.98 (OLSMHY-LEQKT-6D6UNK)" in text
    assert "Balance: gap +0.05309218 SOL" in text
    assert "<b>BTC/USD</b> — OK" in text
    assert "/admin" in text


def test_db_orphan_and_field_drift_listed():
    r = {"symbol": "BTC/USD", "status": "DRIFT_DB_ORPHAN", "balance_status": "OK", "balance_note": "",
         "drift_details": {
             "in_db_not_on_kraken": [{"created_at": "2026-10-01 10:00:00", "side": "sell", "qty": 0.0004,
                                      "price": 84000.0, "fee": 0.27, "order_id": "OAAAAA", "cycle": "kraken_2b"}],
             "drift": [{"order_id": "OBBBBB", "db_id": "x", "at": "2026-10-02 10:00:00",
                        "findings": [{"field": "fee", "db": 0.2, "kraken": 0.27}]}],
             "on_kraken_not_in_db": []}}
    text = build_alert([r])
    assert "In DB, not on Kraken: 2026-10-01 10:00:00 UTC SELL 0.00040000 @ $84,000.00 (OAAAAA)" in text
    assert "Different values on OBBBBB: fee DB 0.2 vs Kraken 0.27" in text


def test_long_list_is_capped():
    r = _sol_orphan()
    order = r["drift_details"]["on_kraken_not_in_db"][0]
    r["drift_details"]["on_kraken_not_in_db"] = [dict(order, order_id=f"O{i}") for i in range(8)]
    text = build_alert([r])
    assert text.count("On Kraken, not in DB") == 5
    assert "…and 4 more" in text  # 3 more orders + the balance line


def test_html_is_escaped():
    r = _sol_orphan()
    r["balance_note"] = "gap <weird> & odd"
    assert "gap &lt;weird&gt; &amp; odd" in build_alert([r])
    assert "&lt;html&gt;" in fatal_alert("DB read failed: <html> 504")


def test_fatal_alert_truncates_long_errors():
    text = fatal_alert("x" * 1000)
    assert "x" * 300 in text and "x" * 301 not in text
    assert "missing from /admin" in text


def test_notify_is_silent_and_never_raises(monkeypatch):
    calls = []

    class FakeNotifier:
        def send_message(self, text, disable_notification=False):
            calls.append(disable_notification)
            return True

    monkeypatch.setattr(tn, "SyncTelegramNotifier", FakeNotifier)
    notify("hello")
    assert calls == [True]

    class Broken:
        def __init__(self):
            raise RuntimeError("no token")

    monkeypatch.setattr(tn, "SyncTelegramNotifier", Broken)
    notify("hello")  # must not raise
