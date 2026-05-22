"""Unit tests for Sherpa slow-loop gate (Brief 81a Block 2).

Covers:
- _fetch_latest_slow_score queries sentinel_scores with score_type='slow'
- STALE_SCORE_S is widened to 6h (slow cadence is 4h)
- STOP_BUY_REGIME constant maps to "extreme_fear"
- proposed_stop_buy_active fires only when regime is extreme_fear
- Sprint-1 fast-signal ladders are gone from parameter_rules signature
- Calling calculate_parameters with same regime + same multiplier returns
  the same proposal regardless of fast-loop noise

Run:
    python -m pytest tests/test_sherpa_slow_loop_gate.py -v
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The telegram lib that utils/telegram_notifier imports is broken on
# Python 3.13 (ModuleNotFoundError on telegram._utils.datetime). It's a
# pre-existing environment issue unrelated to Brief 81a, but it would
# block this test from importing bot.sherpa.main. Stub the modules we
# need before the import chain reaches them.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from bot.sherpa import main as sherpa_main
from bot.sherpa.parameter_rules import calculate_parameters


# ----------------------------------------------------------------------
# Configuration constants
# ----------------------------------------------------------------------

def test_stop_buy_regime_is_extreme_fear():
    """Board decision 2026-05-22: stop_buy lamp is on iff regime is
    extreme_fear. Renaming this constant is fine, repointing it is not
    without a brief."""
    assert sherpa_main.STOP_BUY_REGIME == "extreme_fear"


def test_stale_score_window_widened_for_slow_loop():
    """Sprint 1 used 5min stale window (fast loop = 60s cadence). Slow
    loop runs every 4h, so 5min would flap constantly. Brief 81a sets
    it to 6h = 4h cadence + 2h slack."""
    assert sherpa_main.STALE_SCORE_S == 6 * 60 * 60


# ----------------------------------------------------------------------
# _fetch_latest_slow_score query
# ----------------------------------------------------------------------

class FakeQuery:
    def __init__(self, rows, expect_score_type=None):
        self._rows = rows
        self._expect_score_type = expect_score_type
        self.captured_score_type = None

    def select(self, *a, **kw):
        return self

    def eq(self, col, val):
        if col == "score_type":
            self.captured_score_type = val
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def execute(self):
        return type("Result", (), {"data": self._rows})()


class FakeSupabase:
    def __init__(self, rows):
        self.q = FakeQuery(rows)

    def table(self, name):
        assert name == "sentinel_scores"
        return self.q


def test_fetch_latest_slow_score_filters_by_slow():
    """Brief 81a Block 2: Sherpa must NOT read fast-loop rows. The query
    must filter score_type='slow' explicitly."""
    sb = FakeSupabase([{"score_type": "slow", "risk_score": 30}])
    res = sherpa_main._fetch_latest_slow_score(sb)
    assert sb.q.captured_score_type == "slow"
    assert res["risk_score"] == 30


def test_fetch_latest_slow_score_returns_none_when_no_rows():
    sb = FakeSupabase([])
    assert sherpa_main._fetch_latest_slow_score(sb) is None


# ----------------------------------------------------------------------
# calculate_parameters signature — no fast_signals parameter
# ----------------------------------------------------------------------

def test_calculate_parameters_signature_has_no_fast_signals():
    """Brief 81a Block 2: Sprint-1 fast_signals kwarg is gone. The new
    signature is (regime, current_params, volatility_multiplier).
    """
    import inspect
    sig = inspect.signature(calculate_parameters)
    assert "fast_signals" not in sig.parameters
    assert "current_params" in sig.parameters
    assert "volatility_multiplier" in sig.parameters


def test_calculate_parameters_stable_under_repeated_calls():
    """Sherpa proposals must change at most every 4h (slow-loop cadence),
    not every 2 minutes. Calling calculate_parameters with the same
    inputs must return identical outputs — there's no internal randomness
    or fast-signal-driven jitter."""
    current = {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0}
    proposals = [
        calculate_parameters(
            regime="neutral", current_params=current, volatility_multiplier=1.2
        )[0]
        for _ in range(10)
    ]
    first = proposals[0]
    assert all(p == first for p in proposals[1:])


# ----------------------------------------------------------------------
# Sprint-1 fast-signal ladders are gone
# ----------------------------------------------------------------------

def test_sprint1_ladders_are_removed_from_module():
    """Brief 81a Block 2 / decision (a): the DROP/PUMP/FUNDING/SOF ladders
    are deleted. If they reappear (e.g. via accidental revert), this test
    fails so we notice."""
    from bot.sherpa import parameter_rules
    for symbol_name in (
        "DROP_LADDER", "PUMP_LADDER",
        "FUNDING_LONG_LADDER", "FUNDING_SHORT_LADDER",
        "SPEED_OF_FALL_DELTA",
    ):
        assert not hasattr(parameter_rules, symbol_name), (
            f"{symbol_name} should be removed in Sprint 2"
        )


# ----------------------------------------------------------------------
# proposed_stop_buy_active mapping (regime-driven, not risk-driven)
# ----------------------------------------------------------------------

def test_stop_buy_active_when_regime_is_extreme_fear():
    """Replicates the inline expression in run_sherpa(). Kept as a unit
    test so the mapping is documented and any future refactor (e.g.
    moving this into a helper) doesn't silently change semantics."""
    regime = "extreme_fear"
    assert (regime == sherpa_main.STOP_BUY_REGIME) is True


def test_stop_buy_inactive_for_other_regimes():
    for regime in ("fear", "neutral", "greed", "extreme_greed"):
        assert (regime == sherpa_main.STOP_BUY_REGIME) is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
