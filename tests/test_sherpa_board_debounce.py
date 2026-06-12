"""Unit tests for bot.sherpa.board_debounce.decide (Board decision 2026-06-12).

The debounce stops a coin hugging a tier/regime boundary from rewriting its
safety params on every wiggle: a newly observed (regime, tier) must hold
continuously for BOARD_DEBOUNCE_HOURS before Sherpa adopts it. A coin's first
classification is immediate.

Covers:
- first classification (no state) -> adopt immediately
- observed == effective -> no change
- a fresh divergence -> candidate armed, effective unchanged
- candidate that returns home before maturing -> candidate cleared, no flip
- candidate that persists >= debounce -> promoted
- candidate not yet mature -> still held
- a different divergence resets the candidate timer (anti-flap core)
- an oscillating coin never promotes inside the window

Run:
    python -m pytest tests/test_sherpa_board_debounce.py -v
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sherpa import board_debounce

DEBOUNCE_H = 24
T0 = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)


def _state(eff_r, eff_t, cand_r=None, cand_t=None, since=None):
    return {
        "effective_regime": eff_r,
        "effective_tier": eff_t,
        "candidate_regime": cand_r,
        "candidate_tier": cand_t,
        "candidate_since": since.isoformat() if since else None,
    }


def test_first_classification_adopts_immediately():
    d = board_debounce.decide(None, "extreme_fear", "MID", T0, DEBOUNCE_H)
    assert d.adopted_now is True
    assert d.state_changed is True
    assert (d.effective_regime, d.effective_tier) == ("extreme_fear", "MID")
    assert d.new_state["candidate_regime"] is None


def test_empty_state_row_also_adopts():
    """A row missing effective_regime (defensive) is treated as first run."""
    d = board_debounce.decide({}, "fear", "LOW", T0, DEBOUNCE_H)
    assert d.adopted_now is True
    assert (d.effective_regime, d.effective_tier) == ("fear", "LOW")


def test_observed_equals_effective_no_change():
    st = _state("fear", "LOW")
    d = board_debounce.decide(st, "fear", "LOW", T0, DEBOUNCE_H)
    assert d.state_changed is False
    assert d.new_state is None
    assert (d.effective_regime, d.effective_tier) == ("fear", "LOW")


def test_fresh_divergence_arms_candidate_without_flip():
    st = _state("neutral", "MID")
    d = board_debounce.decide(st, "fear", "MID", T0, DEBOUNCE_H)
    assert (d.effective_regime, d.effective_tier) == ("neutral", "MID")
    assert d.adopted_now is False
    assert d.state_changed is True
    assert d.new_state["candidate_regime"] == "fear"
    assert d.new_state["candidate_since"] is not None


def test_candidate_returns_home_before_maturing_clears():
    """Anti-flap: regime flickered to fear then back to neutral before 24h
    -> candidate cleared, no safety-param change ever."""
    st = _state("neutral", "MID", cand_r="fear", cand_t="MID", since=T0)
    d = board_debounce.decide(st, "neutral", "MID", T0 + timedelta(hours=1), DEBOUNCE_H)
    assert (d.effective_regime, d.effective_tier) == ("neutral", "MID")
    assert d.state_changed is True            # candidate cleared
    assert d.new_state["candidate_regime"] is None


def test_candidate_matures_promotes():
    st = _state("neutral", "MID", cand_r="fear", cand_t="MID", since=T0)
    d = board_debounce.decide(
        st, "fear", "MID", T0 + timedelta(hours=DEBOUNCE_H), DEBOUNCE_H
    )
    assert d.adopted_now is True
    assert (d.effective_regime, d.effective_tier) == ("fear", "MID")
    assert d.new_state["candidate_regime"] is None


def test_candidate_not_yet_mature_holds():
    st = _state("neutral", "MID", cand_r="fear", cand_t="MID", since=T0)
    d = board_debounce.decide(
        st, "fear", "MID", T0 + timedelta(hours=DEBOUNCE_H - 1), DEBOUNCE_H
    )
    assert d.adopted_now is False
    assert (d.effective_regime, d.effective_tier) == ("neutral", "MID")
    assert d.state_changed is False          # timer keeps running, no write


def test_different_divergence_resets_timer():
    """A coin oscillating across two boundaries never matures: each new
    divergence restarts the candidate clock."""
    st = _state("neutral", "MID", cand_r="fear", cand_t="MID", since=T0)
    later = T0 + timedelta(hours=23)
    d = board_debounce.decide(st, "neutral", "HIGH", later, DEBOUNCE_H)
    assert (d.effective_regime, d.effective_tier) == ("neutral", "MID")
    assert d.new_state["candidate_regime"] == "neutral"
    assert d.new_state["candidate_tier"] == "HIGH"
    assert d.new_state["candidate_since"] == later.isoformat()  # reset, not T0


def test_tier_flap_never_promotes_within_window():
    """End-to-end anti-flap: a SOL-like coin bouncing MID<->HIGH hourly for
    23h never promotes (each bounce resets the clock), so the effective tier
    — and therefore the safety params — stays put."""
    st = _state("neutral", "MID")
    now = T0
    for i in range(23):
        obs_tier = "HIGH" if i % 2 == 0 else "MID"
        d = board_debounce.decide(st, "neutral", obs_tier, now, DEBOUNCE_H)
        st = d.new_state if d.new_state is not None else st
        now += timedelta(hours=1)
        assert d.effective_tier == "MID"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
