"""Unit tests for the Sherpa write-on-change gate (Brief S102).

Covers:
- heartbeat constant moved to 4h (was 600s, brief 79c)
- stable proposal → no write between heartbeats (skip counter grows)
- heartbeat writes even when nothing changed
- numeric param change → write
- regime change with IDENTICAL numerics → write (cap saturation case)
- stop_buy: write on flip, NOT on persistent level (the S102 root cause:
  level-based pass wrote every tick during the May-29+ extreme_fear)
- cooldown: write on window open/close flip, not while persistently locked
- bootstrap carries regime/stop_buy/cooldown so a restart in a persistent
  extreme_fear regime doesn't produce a spurious write

Run:
    python -m pytest tests/test_sherpa_write_gate.py -v
"""

import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Same telegram stub as test_sherpa_slow_loop_gate.py — the telegram lib
# is broken on Python 3.13 and would block the bot.sherpa.main import.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from bot.sherpa import main as sherpa_main


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class FakeTable:
    """Generic chainable PostgREST stub: select/eq/gte/neq/order/limit
    return self; execute() returns the canned rows; insert() captures."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.inserts = []

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self.inserts.append(payload)
        return self

    def execute(self):
        return type("Result", (), {"data": self._rows})()


class FakeSupabase:
    def __init__(self, cooldown_rows=None, proposal_rows=None):
        self.proposals = FakeTable(rows=proposal_rows)
        self.changes = FakeTable(rows=cooldown_rows)

    def table(self, name):
        return {
            "sherpa_proposals": self.proposals,
            "config_changes_log": self.changes,
        }[name]


def _notifier():
    return types.SimpleNamespace(send_message=lambda *a, **k: None)


def _state():
    return {
        "alerts": {},
        "proposed": {},
        "stop_buy": {},
        "ts": {},
        "skips": {},
    }


PROPOSED = {"buy_pct": 0.65, "sell_pct": 1.05, "idle_reentry_hours": 5.6}
CURRENT = {"buy_pct": 0.5, "sell_pct": 1.5, "idle_reentry_hours": 8.0}


def _tick(supabase, state, proposed=None, regime="extreme_fear",
          stop_buy=True):
    sherpa_main._handle_bot(
        supabase=supabase,
        notifier=_notifier(),
        bot={"symbol": "BTC/USDT", "stop_buy_drawdown_pct": 2},
        risk=85,
        opp=15,
        current=dict(CURRENT),
        proposed=dict(proposed or PROPOSED),
        proposed_regime=regime,
        proposed_stop_buy_active=stop_buy,
        volatility_multiplier=1.0,
        btc_price=None,
        symbol_price=None,
        dry_run=True,
        last_alert_ts=state["alerts"],
        last_proposed=state["proposed"],
        last_stop_buy_active=state["stop_buy"],
        last_write_ts_per_symbol=state["ts"],
        skips_since_write=state["skips"],
    )


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

def test_heartbeat_is_4h():
    """Brief S102 (decision Max 2026-06-11): heartbeat aligned with the
    Sentinel slow-loop cadence. 600s was the 79c value."""
    assert sherpa_main.SHERPA_HEARTBEAT_S == 4 * 60 * 60


# ----------------------------------------------------------------------
# Stable proposal — the S102 regression scenario
# ----------------------------------------------------------------------

def test_persistent_stop_buy_level_does_not_write():
    """THE root cause of the 2,100 rows/day: regime stuck on extreme_fear
    → proposed_stop_buy_active true on every tick used to bypass the
    filter. After S102 only the FLIP writes; the steady state skips."""
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state)                      # first proposal → writes
    assert len(sb.proposals.inserts) == 1
    for _ in range(5):                    # extreme_fear persists
        _tick(sb, state)
    assert len(sb.proposals.inserts) == 1, "steady extreme_fear must not write"
    assert state["skips"]["BTC/USDT"] == 5


def test_stop_buy_flip_writes_once():
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state, regime="fear", stop_buy=False)   # seed (writes: first)
    _tick(sb, state, regime="fear", stop_buy=False)   # stable → skip
    assert len(sb.proposals.inserts) == 1
    _tick(sb, state, regime="fear", stop_buy=True)    # flip ON → write
    assert len(sb.proposals.inserts) == 2
    _tick(sb, state, regime="fear", stop_buy=True)    # persistent → skip
    assert len(sb.proposals.inserts) == 2


def test_regime_change_with_identical_numerics_writes():
    """The ±30% cap can saturate two regimes onto the same numbers (e.g.
    BTC buy 0.65 in both fear and extreme_fear). The regime is part of
    the proposal identity, so the transition must still be recorded."""
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state, regime="fear", stop_buy=False)
    _tick(sb, state, regime="neutral", stop_buy=False)  # same numerics
    assert len(sb.proposals.inserts) == 2
    assert sb.proposals.inserts[1]["proposed_regime"] == "neutral"


def test_numeric_change_writes():
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state)
    moved = dict(PROPOSED, sell_pct=1.30)
    _tick(sb, state, proposed=moved)
    assert len(sb.proposals.inserts) == 2


def test_cooldown_flip_writes_open_and_close_only():
    """Board override arms a 24h cooldown. Pre-S102 the level-based pass
    wrote every tick for the whole window (~720 rows/day); now exactly
    two rows bracket it: window open and window close."""
    state = _state()
    sb_free = FakeSupabase(cooldown_rows=[])
    _tick(sb_free, state)                 # seed, no cooldown
    inserts = sb_free.proposals.inserts
    assert len(inserts) == 1

    locked_rows = [{"parameter": "sell_pct", "changed_by": "manual-ceo",
                    "created_at": "2026-06-11T10:00:00+00:00"}]
    sb_locked = FakeSupabase(cooldown_rows=locked_rows)
    sb_locked.proposals.inserts = inserts          # share the capture list
    _tick(sb_locked, state)               # window opens → write
    assert len(inserts) == 2
    assert inserts[1]["cooldown_active"] is True
    _tick(sb_locked, state)               # still locked → skip
    _tick(sb_locked, state)
    assert len(inserts) == 2

    sb_free2 = FakeSupabase(cooldown_rows=[])
    sb_free2.proposals.inserts = inserts
    _tick(sb_free2, state)                # window closes → write
    assert len(inserts) == 3
    assert inserts[2]["cooldown_active"] is False


# ----------------------------------------------------------------------
# Heartbeat
# ----------------------------------------------------------------------

def test_heartbeat_writes_when_nothing_changed():
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state)
    _tick(sb, state)                      # stable → skip
    assert len(sb.proposals.inserts) == 1
    # age the last write beyond the heartbeat window
    state["ts"]["BTC/USDT"] = time.time() - sherpa_main.SHERPA_HEARTBEAT_S - 1
    _tick(sb, state)
    assert len(sb.proposals.inserts) == 2


def test_heartbeat_resets_skip_counter():
    sb = FakeSupabase()
    state = _state()
    _tick(sb, state)
    for _ in range(3):
        _tick(sb, state)
    assert state["skips"]["BTC/USDT"] == 3
    state["ts"]["BTC/USDT"] = time.time() - sherpa_main.SHERPA_HEARTBEAT_S - 1
    _tick(sb, state)                      # heartbeat → counter consumed
    assert state["skips"].get("BTC/USDT", 0) == 0


# ----------------------------------------------------------------------
# Bootstrap — restart must not produce a spurious write
# ----------------------------------------------------------------------

def test_bootstrap_carries_full_proposal_identity():
    rows = [{
        "symbol": "BTC/USDT",
        "proposed_buy_pct": "0.65",
        "proposed_sell_pct": "1.05",
        "proposed_idle_reentry_hours": "5.6",
        "proposed_regime": "extreme_fear",
        "proposed_stop_buy_active": True,
        "cooldown_active": False,
        "created_at": "2026-06-11T10:00:00+00:00",
    }]
    sb = FakeSupabase(proposal_rows=rows)
    out = sherpa_main._bootstrap_last_proposed(sb)
    entry = out["BTC/USDT"]
    assert entry["buy_pct"] == 0.65
    assert entry["regime"] == "extreme_fear"
    assert entry["stop_buy_active"] is True
    assert entry["cooldown_active"] is False


def test_restart_in_persistent_extreme_fear_does_not_write():
    """Simulate a restart: state seeded from bootstrap (as run_sherpa
    does), then the first tick re-proposes the same thing in the same
    persistent extreme_fear regime → no write, no flip."""
    rows = [{
        "symbol": "BTC/USDT",
        "proposed_buy_pct": "0.65",
        "proposed_sell_pct": "1.05",
        "proposed_idle_reentry_hours": "5.6",
        "proposed_regime": "extreme_fear",
        "proposed_stop_buy_active": True,
        "cooldown_active": False,
        "created_at": "2026-06-11T10:00:00+00:00",
    }]
    sb = FakeSupabase(proposal_rows=rows)
    state = _state()
    state["proposed"] = sherpa_main._bootstrap_last_proposed(sb)
    state["stop_buy"] = {
        s: v["stop_buy_active"] for s, v in state["proposed"].items()
        if v.get("stop_buy_active") is not None
    }
    state["ts"]["BTC/USDT"] = time.time()  # heartbeat not due
    _tick(sb, state)
    assert len(sb.proposals.inserts) == 0, "restart must not write spuriously"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
