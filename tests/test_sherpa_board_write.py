"""Unit tests for the LIVE Board-param write path in
bot.sherpa.main._handle_bot (Brief S103a).

Covers:
- LIVE: board params differing from current are written to bot_config +
  config_changes_log (via config_writer); equal ones are skipped
- LIVE: a board param under Board cooldown is skipped (no write)
- the proposal heartbeat row carries the new board columns + volatility_tier
- dry_run: no bot_config writes for board params; the proposal row still
  logs them (instantaneous lookup)

Run:
    python -m pytest tests/test_sherpa_board_write.py -v
"""

import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# telegram lib is broken on Python 3.13; stub before importing bot.sherpa.main.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from bot.sherpa import main as sherpa_main

# log_event makes its own real client — stub it so tests stay hermetic.
sherpa_main.log_event = lambda *a, **k: None


class FakeTable:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.inserts = []
        self.updates = []

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def insert(self, payload): self.inserts.append(payload); return self
    def update(self, payload): self.updates.append(payload); return self
    def execute(self): return type("Result", (), {"data": self._rows})()


class FakeSupabase:
    def __init__(self, cooldown_rows=None):
        self.proposals = FakeTable()
        self.changes = FakeTable(rows=cooldown_rows)
        self.config = FakeTable()

    def table(self, name):
        return {
            "sherpa_proposals": self.proposals,
            "config_changes_log": self.changes,
            "bot_config": self.config,
        }[name]


def _notifier():
    return types.SimpleNamespace(send_message=lambda *a, **k: None)


def _state():
    return {"alerts": {}, "proposed": {}, "stop_buy": {}, "ts": {}, "skips": {}}


# Strategy params: proposed == current so they trigger no writes — isolates
# the board-param behavior under test.
STRAT = {"buy_pct": 0.65, "sell_pct": 1.05, "idle_reentry_hours": 5.6}

BOARD_CURRENT = {
    "stop_buy_drawdown_pct": 2.0,
    "stop_buy_unlock_hours": 1.0,
    "dead_zone_hours": 4.0,
    "profit_target_pct": 0.0,
}
# extreme_fear / HIGH target: 5 / 12 / 2 / 0 -> dd, unlock, dead_zone move;
# profit_target stays 0.
BOARD_TARGET = {
    "stop_buy_drawdown_pct": 5.0,
    "stop_buy_unlock_hours": 12.0,
    "dead_zone_hours": 2.0,
    "profit_target_pct": 0.0,
}


def _tick(sb, state, dry_run=False, board_cooldown=None, heartbeat_due=False):
    state["ts"]["BONK/USDT"] = 0.0 if heartbeat_due else time.time()
    sherpa_main._handle_bot(
        supabase=sb,
        notifier=_notifier(),
        bot={
            "symbol": "BONK/USDT",
            "stop_buy_drawdown_pct": 2.0,
            "stop_buy_unlock_hours": 1.0,
            "dead_zone_hours": 4.0,
            "profit_target_pct": 0.0,
        },
        risk=85, opp=15,
        current=dict(STRAT), proposed=dict(STRAT),
        proposed_regime="extreme_fear",
        proposed_stop_buy_active=True,
        volatility_multiplier=1.75,
        btc_price=None, symbol_price=None,
        dry_run=dry_run,
        last_alert_ts=state["alerts"],
        last_proposed=state["proposed"],
        last_stop_buy_active=state["stop_buy"],
        last_write_ts_per_symbol=state["ts"],
        skips_since_write=state["skips"],
        board_current=dict(BOARD_CURRENT),
        board_target=dict(BOARD_TARGET),
        board_tier="HIGH",
        board_cooldown_locked=board_cooldown or [],
    )


def _written_params(sb):
    return {k for upd in sb.config.updates for k in upd}


def test_live_writes_changed_board_params():
    sb = FakeSupabase(cooldown_rows=[])
    _tick(sb, _state())
    written = _written_params(sb)
    assert "stop_buy_drawdown_pct" in written
    assert "stop_buy_unlock_hours" in written
    assert "dead_zone_hours" in written
    assert "profit_target_pct" not in written          # 0 == 0, unchanged
    logged = {c["parameter"] for c in sb.changes.inserts}
    assert logged == {"stop_buy_drawdown_pct", "stop_buy_unlock_hours", "dead_zone_hours"}


def test_live_skips_board_param_in_cooldown():
    sb = FakeSupabase(cooldown_rows=[])
    _tick(sb, _state(), board_cooldown=["stop_buy_drawdown_pct"])
    written = _written_params(sb)
    assert "stop_buy_drawdown_pct" not in written       # locked by Board override
    assert "stop_buy_unlock_hours" in written           # others still move


def test_dry_run_does_not_write_board_to_bot_config():
    sb = FakeSupabase(cooldown_rows=[])
    _tick(sb, _state(), dry_run=True)
    assert sb.config.updates == []                      # never writes bot_config
    assert len(sb.proposals.inserts) == 1
    row = sb.proposals.inserts[0]
    assert row["proposed_stop_buy_dd"] == 5.0
    assert row["volatility_tier"] == "HIGH"


def test_live_heartbeat_row_carries_board_columns():
    sb = FakeSupabase(cooldown_rows=[])
    _tick(sb, _state(), heartbeat_due=True)
    assert len(sb.proposals.inserts) == 1
    row = sb.proposals.inserts[0]
    assert row["proposed_stop_buy_unlock_h"] == 12.0
    assert row["current_dead_zone_h"] == 4.0
    assert row["volatility_tier"] == "HIGH"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
