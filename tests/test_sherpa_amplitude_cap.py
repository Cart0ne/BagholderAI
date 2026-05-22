"""Unit tests for bot.sherpa.parameter_rules amplitude cap
(Brief 81a Block 3).

Covers:
- Cap up: proposed > current * (1 + MAX_DELTA_PCT) → clamped down
- Cap down: proposed < current * (1 - MAX_DELTA_PCT) → clamped up
- Within band: proposed left alone
- current=None: cap skipped (first proposal can populate freely)
- current=0: cap skipped (degenerate formula)
- cap_applied flag in breakdown correctly tracks which params were capped
- Cap applies AFTER absolute clamps (so it can't push back into clamped range)
- Volatility scaling interacts correctly with cap

Run:
    python -m pytest tests/test_sherpa_amplitude_cap.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sherpa.parameter_rules import calculate_parameters
from config.settings import HardcodedRules


# ----------------------------------------------------------------------
# Cap up — proposed would jump > MAX_DELTA_PCT above current
# ----------------------------------------------------------------------

def test_cap_blocks_upward_jump_above_max_delta():
    """Neutral regime + 5x volatility on a low current sell_pct should
    be capped to current * (1 + MAX_DELTA_PCT)."""
    current = {"buy_pct": 1.0, "sell_pct": 1.0, "idle_reentry_hours": 1.0}
    # Base neutral sell_pct = 1.5; with mult=5.0 raw is 7.5, clamped to
    # 4.0 (RANGES ceiling), then cap kicks in: 1.0 * 1.3 = 1.3
    final, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=5.0
    )
    expected_max = 1.0 * (1.0 + HardcodedRules.MAX_DELTA_PCT)
    assert final["sell_pct"] == round(expected_max, 4)
    assert breakdown["cap_applied"]["sell_pct"] is True


def test_cap_blocks_downward_jump_below_max_delta():
    """A current well above the regime base should be capped down by
    MAX_DELTA_PCT, not yanked all the way to the base."""
    current = {"buy_pct": 1.0, "sell_pct": 4.0, "idle_reentry_hours": 1.0}
    # Neutral base sell_pct = 1.5 ; would propose 1.5 but cap floor is
    # 4.0 * 0.7 = 2.8
    final, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=1.0
    )
    expected_min = 4.0 * (1.0 - HardcodedRules.MAX_DELTA_PCT)
    assert final["sell_pct"] == round(expected_min, 4)
    assert breakdown["cap_applied"]["sell_pct"] is True


# ----------------------------------------------------------------------
# Within band — proposed left alone
# ----------------------------------------------------------------------

def test_cap_passes_through_when_within_band():
    """Small move (≤ MAX_DELTA_PCT) is not modified by the cap."""
    current = {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0}
    # Neutral proposes (1.0, 1.5, 1.0) — exactly matches current
    final, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=1.0
    )
    assert final == {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0}
    assert all(v is False for v in breakdown["cap_applied"].values())


# ----------------------------------------------------------------------
# Skip cap — current=None or 0
# ----------------------------------------------------------------------

def test_cap_skipped_when_current_is_none():
    """Missing current value (first run, brand-new bot) → cap not applied,
    so the regime base flows through directly."""
    current = {"buy_pct": None, "sell_pct": None, "idle_reentry_hours": None}
    final, breakdown = calculate_parameters(
        regime="fear", current_params=current, volatility_multiplier=2.0
    )
    # Fear base: buy=1.8, sell=1.2, idle=2.0 ; with mult 2.0 amplitude
    # scaled: buy=3.6→clamped 3.0, sell=2.4, idle=2.0
    assert final["buy_pct"] == 3.0
    assert final["sell_pct"] == 2.4
    assert final["idle_reentry_hours"] == 2.0
    assert all(v is False for v in breakdown["cap_applied"].values())


def test_cap_skipped_when_current_is_zero():
    """Zero current → cap formula degenerate → skipped."""
    current = {"buy_pct": 0.0, "sell_pct": 0.0, "idle_reentry_hours": 0.0}
    final, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=1.0
    )
    # No cap interference: clamped values come through.
    assert final["sell_pct"] == 1.5
    assert all(v is False for v in breakdown["cap_applied"].values())


# ----------------------------------------------------------------------
# Cap is configurable via HardcodedRules
# ----------------------------------------------------------------------

def test_max_delta_pct_is_documented_value():
    """Brief 81a default: 30%. If this changes, update the brief and the
    expected behavior in the other tests above."""
    assert HardcodedRules.MAX_DELTA_PCT == 0.30


# ----------------------------------------------------------------------
# Breakdown audit trail
# ----------------------------------------------------------------------

def test_breakdown_records_volatility_multiplier():
    current = {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0}
    _, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=2.5
    )
    assert breakdown["volatility_multiplier"] == 2.5


def test_breakdown_records_cap_flags_per_parameter():
    current = {"buy_pct": 1.0, "sell_pct": 1.0, "idle_reentry_hours": 1.0}
    _, breakdown = calculate_parameters(
        regime="extreme_greed", current_params=current, volatility_multiplier=3.0
    )
    # extreme_greed base: buy=0.5 sell=3.0 idle=0.5
    # buy raw = 0.5 * 3.0 = 1.5 → clamp OK → cap to 1.0 * 1.3 = 1.3 (capped)
    # sell raw = 3.0 * 3.0 = 9.0 → clamp 4.0 → cap to 1.0 * 1.3 = 1.3 (capped)
    # idle raw = 0.5 → cap floor 1.0 * 0.7 = 0.7 (capped UP)
    assert breakdown["cap_applied"]["buy_pct"] is True
    assert breakdown["cap_applied"]["sell_pct"] is True
    assert breakdown["cap_applied"]["idle_reentry_hours"] is True


# ----------------------------------------------------------------------
# Idle_reentry_hours is NOT volatility-scaled (it's time, not amplitude)
# ----------------------------------------------------------------------

def test_idle_reentry_hours_is_not_volatility_scaled():
    """A high volatility multiplier must not stretch idle_reentry_hours."""
    current = {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0}
    _, breakdown = calculate_parameters(
        regime="neutral", current_params=current, volatility_multiplier=3.0
    )
    # Raw should equal base (1.0), not base*mult (3.0)
    assert breakdown["raw"]["idle_reentry_hours"] == 1.0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
