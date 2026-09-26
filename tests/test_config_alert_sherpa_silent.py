"""Sherpa-tuned params must not produce CONFIG CHANGE Telegram alerts
(Max, S127: "togliamo i messaggi di sherpa"); other fields still alert and
every change is still logged as an event."""

import config.supabase_config as sc
from config.supabase_config import SupabaseConfigReader


def _run_refresh(monkeypatch, old_row, new_row):
    reader = SupabaseConfigReader(own_symbol="SOL/USD")
    reader._configs = {"SOL/USD": old_row}
    monkeypatch.setattr(reader, "_fetch_from_supabase", lambda: [new_row])
    monkeypatch.setattr(reader, "_fetch_trend_config", lambda: {})

    alerts, events = [], []
    monkeypatch.setattr(
        reader, "_send_config_changes", lambda sym, ch: alerts.append((sym, ch))
    )
    monkeypatch.setattr(sc, "log_event", lambda **kw: events.append(kw))
    reader.refresh()
    return alerts, events


def test_sherpa_params_only_no_alert_but_event(monkeypatch):
    old = {"symbol": "SOL/USD", "sell_pct": 3.0, "buy_pct": 1.5, "idle_reentry_hours": 1.0}
    new = {"symbol": "SOL/USD", "sell_pct": 3.02, "buy_pct": 1.6, "idle_reentry_hours": 0.8}
    alerts, events = _run_refresh(monkeypatch, old, new)
    assert alerts == []
    assert len(events) == 1
    assert len(events[0]["details"]["changes"]) == 3


def test_non_sherpa_field_still_alerts(monkeypatch):
    old = {"symbol": "SOL/USD", "sell_pct": 3.0, "capital_allocation": 150}
    new = {"symbol": "SOL/USD", "sell_pct": 3.02, "capital_allocation": 200}
    alerts, events = _run_refresh(monkeypatch, old, new)
    assert alerts == [("SOL/USD", [("capital_allocation", 150, 200)])]
    assert len(events[0]["details"]["changes"]) == 2
