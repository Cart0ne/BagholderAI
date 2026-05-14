"""Unit tests for bot.sentinel.regime_analyzer.

Covers all 5 regime buckets, both boundaries (20/21, 40/41, 60/61, 80/81),
every fallback path (None / malformed / stale), and the slow-score map.

Run:
    python -m pytest tests/test_regime_analyzer.py -v
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sentinel.regime_analyzer import (
    REGIME_SCORE_MAP,
    determine_regime,
    regime_to_slow_score,
)


_NOW = 1_715_700_000  # fixed unix time for determinism (2026-05-14 ~)


def _fng(value, age_s=0):
    """Build a fake F&G dict timestamped age_s seconds in the past."""
    return {
        "fng_value": value,
        "fng_label": "test",
        "fng_timestamp": _NOW - age_s,
    }


# ----- Happy path: 5 regime buckets -----

def test_extreme_fear_at_value_10():
    regime, log = determine_regime(_fng(10), None, now_unix=_NOW)
    assert regime == "extreme_fear"
    assert log["fng_used"] is True
    assert log["regime_source"] == "fng"


def test_fear_at_value_35():
    regime, _ = determine_regime(_fng(35), None, now_unix=_NOW)
    assert regime == "fear"


def test_neutral_at_value_50():
    regime, _ = determine_regime(_fng(50), None, now_unix=_NOW)
    assert regime == "neutral"


def test_greed_at_value_70():
    regime, _ = determine_regime(_fng(70), None, now_unix=_NOW)
    assert regime == "greed"


def test_extreme_greed_at_value_90():
    regime, _ = determine_regime(_fng(90), None, now_unix=_NOW)
    assert regime == "extreme_greed"


# ----- Boundary tests: 20/21, 40/41, 60/61, 80/81 -----

def test_boundary_20_is_extreme_fear():
    regime, _ = determine_regime(_fng(20), None, now_unix=_NOW)
    assert regime == "extreme_fear"


def test_boundary_21_is_fear():
    regime, _ = determine_regime(_fng(21), None, now_unix=_NOW)
    assert regime == "fear"


def test_boundary_40_is_fear():
    regime, _ = determine_regime(_fng(40), None, now_unix=_NOW)
    assert regime == "fear"


def test_boundary_41_is_neutral():
    regime, _ = determine_regime(_fng(41), None, now_unix=_NOW)
    assert regime == "neutral"


def test_boundary_60_is_neutral():
    regime, _ = determine_regime(_fng(60), None, now_unix=_NOW)
    assert regime == "neutral"


def test_boundary_61_is_greed():
    regime, _ = determine_regime(_fng(61), None, now_unix=_NOW)
    assert regime == "greed"


def test_boundary_80_is_greed():
    regime, _ = determine_regime(_fng(80), None, now_unix=_NOW)
    assert regime == "greed"


def test_boundary_81_is_extreme_greed():
    regime, _ = determine_regime(_fng(81), None, now_unix=_NOW)
    assert regime == "extreme_greed"


# ----- Fallbacks -----

def test_fng_none_falls_back_to_neutral():
    regime, log = determine_regime(None, None, now_unix=_NOW)
    assert regime == "neutral"
    assert log["fallback_reason"] == "fng_unavailable"
    assert log["fng_used"] is False


def test_fng_none_with_cmc_still_falls_back_to_neutral():
    cmc = {"btc_dominance": 57.0, "total_market_cap_usd": 1.0,
           "total_volume_24h_usd": 1.0, "active_cryptocurrencies": 1}
    regime, log = determine_regime(None, cmc, now_unix=_NOW)
    assert regime == "neutral"
    assert log["cmc_seen"] is True
    assert log["fallback_reason"] == "fng_unavailable"


def test_fng_malformed_value_falls_back_to_neutral():
    bad = {"fng_value": None, "fng_label": "x", "fng_timestamp": _NOW}
    regime, log = determine_regime(bad, None, now_unix=_NOW)
    assert regime == "neutral"
    assert log["fallback_reason"] == "fng_malformed"


def test_fng_stale_falls_back_to_neutral():
    # Age = 40h > 36h threshold
    stale = _fng(15, age_s=40 * 3600)
    regime, log = determine_regime(stale, None, now_unix=_NOW)
    assert regime == "neutral"
    assert log["fallback_reason"] == "fng_stale"
    assert log["fng_age_s"] > 36 * 3600


def test_fng_fresh_just_under_threshold_uses_value():
    # Age = 35h59m < 36h threshold → still used
    fresh = _fng(15, age_s=36 * 3600 - 60)
    regime, _ = determine_regime(fresh, None, now_unix=_NOW)
    assert regime == "extreme_fear"


# ----- Slow score map -----

def test_regime_to_slow_score_known():
    assert regime_to_slow_score("extreme_fear") == (20, 80)
    assert regime_to_slow_score("fear") == (30, 65)
    assert regime_to_slow_score("neutral") == (40, 40)
    assert regime_to_slow_score("greed") == (65, 30)
    assert regime_to_slow_score("extreme_greed") == (80, 20)


def test_regime_to_slow_score_unknown_defaults_to_neutral():
    assert regime_to_slow_score("garbage") == (40, 40)
    assert regime_to_slow_score("") == (40, 40)


def test_regime_score_map_is_complete():
    expected = {"extreme_fear", "fear", "neutral", "greed", "extreme_greed"}
    assert set(REGIME_SCORE_MAP.keys()) == expected


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
