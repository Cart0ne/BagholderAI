"""Unit tests for bot.sherpa.board_parameter_rules (Brief S103a).

Covers:
- BOARD_TABLE has all 5 regimes x 3 tiers, each with the 4 param keys
- classify_tier boundaries (LOW/MID/HIGH) incl. the exact edges 1.30 / 1.65
- the three live coins land in their documented tiers (BTC LOW, SOL MID, BONK HIGH)
- calculate_board_parameters returns (values, tier) from the live multiplier
- profit_target_pct is 0 in every cell (scaffolding)
- board_values_for fallbacks (unknown regime -> neutral, unknown tier -> MID)
  and returns a copy (mutating the result must not corrupt the table)

Run:
    python -m pytest tests/test_sherpa_board_params.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sherpa.board_parameter_rules import (
    BOARD_PARAM_KEYS,
    BOARD_TABLE,
    TIERS,
    board_values_for,
    calculate_board_parameters,
    classify_tier,
)
from config.settings import HardcodedRules

REGIMES = ("extreme_fear", "fear", "neutral", "greed", "extreme_greed")


def test_table_covers_all_regimes_and_tiers():
    assert set(BOARD_TABLE) == set(REGIMES)
    for regime in REGIMES:
        assert set(BOARD_TABLE[regime]) == set(TIERS)
        for tier in TIERS:
            assert set(BOARD_TABLE[regime][tier]) == set(BOARD_PARAM_KEYS)


def test_classify_tier_boundaries():
    lo = HardcodedRules.BOARD_TIER_LOW_MAX   # 1.30
    hi = HardcodedRules.BOARD_TIER_HIGH_MIN  # 1.65
    assert classify_tier(1.0) == "LOW"
    assert classify_tier(lo - 0.001) == "LOW"
    assert classify_tier(lo) == "MID"            # boundary belongs to MID
    assert classify_tier(1.5) == "MID"
    assert classify_tier(hi - 0.001) == "MID"
    assert classify_tier(hi) == "HIGH"           # boundary belongs to HIGH
    assert classify_tier(2.0) == "HIGH"


def test_live_coins_land_in_documented_tiers():
    """BTC ~1.0 LOW, SOL ~1.53 MID, BONK ~1.75 HIGH (brief)."""
    assert classify_tier(1.0) == "LOW"
    assert classify_tier(1.53) == "MID"
    assert classify_tier(1.75) == "HIGH"


def test_calculate_returns_values_and_tier():
    values, tier = calculate_board_parameters("extreme_fear", 1.53)
    assert tier == "MID"
    assert values == {
        "stop_buy_drawdown_pct": 4,
        "stop_buy_unlock_hours": 12,
        "dead_zone_hours": 2,
        "profit_target_pct": 0,
    }


def test_profit_target_is_zero_everywhere():
    for regime in REGIMES:
        for tier in TIERS:
            assert BOARD_TABLE[regime][tier]["profit_target_pct"] == 0


def test_extreme_fear_widens_stop_buy_dd_by_tier():
    """The one genuinely strategic axis: in panic, more volatile coins get a
    wider drawdown tolerance (3/4/5 for LOW/MID/HIGH)."""
    row = BOARD_TABLE["extreme_fear"]
    assert row["LOW"]["stop_buy_drawdown_pct"] == 3
    assert row["MID"]["stop_buy_drawdown_pct"] == 4
    assert row["HIGH"]["stop_buy_drawdown_pct"] == 5


def test_board_values_for_fallbacks():
    assert board_values_for("nonsense", "LOW") == BOARD_TABLE["neutral"]["LOW"]
    assert board_values_for("fear", "WAT") == BOARD_TABLE["fear"]["MID"]


def test_board_values_for_returns_copy():
    """Mutating the returned dict must not corrupt the table."""
    v = board_values_for("neutral", "LOW")
    v["stop_buy_drawdown_pct"] = 999
    assert BOARD_TABLE["neutral"]["LOW"]["stop_buy_drawdown_pct"] == 1


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
