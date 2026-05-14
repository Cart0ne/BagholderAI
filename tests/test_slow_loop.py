"""Unit tests for bot.sentinel.slow_loop.tick().

Uses dependency-injected fetchers + a fake Supabase to verify:
    - happy path (both inputs OK)
    - F&G only (CMC absent → still works)
    - both None (neutral fallback)
    - DB error (tick returns inserted=False, no raise)
    - raw_signals structure matches the documented contract

Run:
    python -m pytest tests/test_slow_loop.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sentinel import slow_loop


# ---------- Test doubles ----------

class FakeTable:
    def __init__(self, fail_insert=False):
        self.fail_insert = fail_insert
        self.inserted_payload = None

    def insert(self, payload):
        self.inserted_payload = payload
        return self

    def execute(self):
        if self.fail_insert:
            raise RuntimeError("simulated supabase error")
        return self


class FakeSupabase:
    def __init__(self, fail_insert=False):
        self._table = FakeTable(fail_insert=fail_insert)

    def table(self, name):
        assert name == "sentinel_scores"
        return self._table


import time as _time


def _fng_dict(value=32, label="Fear", age_s=3600):
    # Use real time so determine_regime's internal time.time() check passes.
    return {
        "fng_value": value,
        "fng_label": label,
        "fng_timestamp": int(_time.time()) - age_s,
    }


def _cmc_dict():
    return {
        "btc_dominance": 57.3,
        "total_market_cap_usd": 2.3e12,
        "total_volume_24h_usd": 8.5e10,
        "active_cryptocurrencies": 9712,
    }


# ---------- Tests ----------

def test_tick_happy_path_both_inputs():
    sb = FakeSupabase()
    result = slow_loop.tick(
        sb,
        fng_fetcher=lambda: _fng_dict(value=32),  # → "fear"
        cmc_fetcher=_cmc_dict,
    )
    assert result["regime"] == "fear"
    assert result["risk_slow"] == 30
    assert result["opp_slow"] == 65
    assert result["fng_value"] == 32
    assert result["cmc_seen"] is True
    assert result["inserted"] is True

    payload = sb._table.inserted_payload
    assert payload["score_type"] == "slow"
    assert payload["risk_score"] == 30
    assert payload["opportunity_score"] == 65
    raw = payload["raw_signals"]
    assert raw["regime"] == "fear"
    assert raw["fng_value"] == 32
    assert raw["btc_dominance"] == 57.3
    assert raw["decision_log"]["regime_source"] == "fng"


def test_tick_fng_only_no_cmc():
    sb = FakeSupabase()
    result = slow_loop.tick(
        sb,
        fng_fetcher=lambda: _fng_dict(value=85),  # → "extreme_greed"
        cmc_fetcher=lambda: None,
    )
    assert result["regime"] == "extreme_greed"
    assert result["cmc_seen"] is False
    raw = sb._table.inserted_payload["raw_signals"]
    assert "btc_dominance" not in raw  # CMC keys absent, not None
    assert raw["fng_value"] == 85


def test_tick_both_inputs_none_falls_back_to_neutral():
    sb = FakeSupabase()
    result = slow_loop.tick(
        sb,
        fng_fetcher=lambda: None,
        cmc_fetcher=lambda: None,
    )
    assert result["regime"] == "neutral"
    assert result["risk_slow"] == 40
    assert result["opp_slow"] == 40
    assert result["fng_value"] is None
    assert result["cmc_seen"] is False
    assert result["inserted"] is True
    raw = sb._table.inserted_payload["raw_signals"]
    assert raw["decision_log"]["fallback_reason"] == "fng_unavailable"


def test_tick_db_failure_returns_inserted_false():
    sb = FakeSupabase(fail_insert=True)
    result = slow_loop.tick(
        sb,
        fng_fetcher=lambda: _fng_dict(value=50),
        cmc_fetcher=_cmc_dict,
    )
    assert result["regime"] == "neutral"
    assert result["inserted"] is False  # DB failed, but tick did not raise


def test_tick_fetcher_raises_unexpectedly_is_swallowed():
    """Inputs follow NEVER-raise contracts, but slow_loop defends anyway."""
    sb = FakeSupabase()

    def buggy_fetcher():
        raise RuntimeError("bug in F&G input")

    result = slow_loop.tick(
        sb,
        fng_fetcher=buggy_fetcher,
        cmc_fetcher=lambda: None,
    )
    assert result["regime"] == "neutral"
    assert result["inserted"] is True


def test_tick_extreme_fear_maps_to_high_opp_low_risk():
    """Sanity check on the trading-sense inversion: panic = buy zone."""
    sb = FakeSupabase()
    result = slow_loop.tick(
        sb,
        fng_fetcher=lambda: _fng_dict(value=10),  # extreme_fear
        cmc_fetcher=lambda: None,
    )
    assert result["regime"] == "extreme_fear"
    assert result["risk_slow"] == 20
    assert result["opp_slow"] == 80


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
