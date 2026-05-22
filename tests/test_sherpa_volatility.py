"""Unit tests for bot.sherpa.volatility (Brief 81a Block 1).

Covers:
- log-return stdev arithmetic on toy series
- BTC anchor → multiplier 1.0
- Higher-volatility coin → multiplier > 1
- Lower-volatility coin → multiplier < 1
- Per-coin divergence: BTC, SOL, BONK all get different multipliers
- Dynamic coin discovery: works for any symbol the caller passes
- Fallback to 1.0 on fetch failure
- Fallback to 1.0 across the board when BTC itself fails
- Cache TTL behavior
- Degenerate inputs (empty closes, identical closes, negative prices)

Run:
    python -m pytest tests/test_sherpa_volatility.py -v
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sherpa import volatility as vol_mod


# ----------------------------------------------------------------------
# Stdev helper unit tests (private function but worth pinning)
# ----------------------------------------------------------------------

def test_stdev_returns_zero_for_short_series():
    assert vol_mod._log_returns_stdev([100.0]) == 0.0
    assert vol_mod._log_returns_stdev([]) == 0.0


def test_stdev_returns_zero_for_negative_or_zero_prices():
    assert vol_mod._log_returns_stdev([100.0, 0.0, 50.0]) == 0.0
    assert vol_mod._log_returns_stdev([100.0, -50.0, 50.0]) == 0.0


def test_stdev_returns_zero_for_constant_series():
    """Constant prices → zero log returns → zero stdev."""
    assert vol_mod._log_returns_stdev([100.0] * 10) == 0.0


def test_stdev_positive_for_varying_series():
    # Alternating +1% / -1% returns: stdev must be > 0
    closes = [100.0]
    for i in range(20):
        prev = closes[-1]
        closes.append(prev * (1.01 if i % 2 == 0 else 0.99))
    s = vol_mod._log_returns_stdev(closes)
    assert s > 0
    # Roughly equal to log(1.01) ≈ 0.00995 in magnitude
    assert 0.005 < s < 0.02


# ----------------------------------------------------------------------
# get_volatility_multipliers — with fake fetch
# ----------------------------------------------------------------------

class FakeKlines:
    """Replace fetch_klines_1h with a deterministic per-symbol response."""

    def __init__(self, series_by_symbol: dict[str, list[float]], fail: set[str] = None):
        self.series = series_by_symbol
        self.fail = fail or set()
        self.calls: list[str] = []

    def __call__(self, symbol: str, limit: int = 168):
        self.calls.append(symbol)
        if symbol in self.fail:
            raise RuntimeError(f"simulated fetch failure for {symbol}")
        prices = self.series.get(symbol)
        if prices is None:
            raise RuntimeError(f"no fake series configured for {symbol}")
        # Mimic real fetch_klines_1h shape: list of (close_time_ms, close).
        return [(i * 3600_000, p) for i, p in enumerate(prices)]


def _alternating_series(amplitude: float, n: int = 200) -> list[float]:
    """Geometric series alternating ± amplitude per step. Larger amplitude
    → larger stdev of log returns."""
    out = [100.0]
    for i in range(n):
        prev = out[-1]
        out.append(prev * (1 + amplitude if i % 2 == 0 else 1 - amplitude))
    return out


def test_btc_anchor_multiplier_is_exactly_one(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines({"BTCUSDT": _alternating_series(0.005)})
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT"])
    assert out == {"BTC/USDT": 1.0}


def test_high_volatility_coin_gets_multiplier_above_one(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.005),     # 0.5% swings
        "BONKUSDT": _alternating_series(0.020),    # 2% swings → ~4x BTC stdev
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT", "BONK/USDT"])
    assert out["BTC/USDT"] == 1.0
    assert out["BONK/USDT"] > 2.0  # should be roughly 4x


def test_low_volatility_coin_gets_multiplier_below_one(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.010),
        "SOLUSDT": _alternating_series(0.003),     # quieter than BTC
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    assert out["SOL/USDT"] < 1.0


def test_three_coins_get_three_distinct_multipliers(monkeypatch):
    """Critical regression test for Brief 81a Block 1: Brain Analysis
    2026-05-22 found Sherpa was emitting identical params for BTC/SOL/BONK.
    Verify that with three coins of different volatility, the multipliers
    are all distinct."""
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.005),
        "SOLUSDT": _alternating_series(0.008),
        "BONKUSDT": _alternating_series(0.020),
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT", "BONK/USDT"])
    values = {out["BTC/USDT"], out["SOL/USDT"], out["BONK/USDT"]}
    assert len(values) == 3, f"expected 3 distinct multipliers, got {values}"
    # Ordering must respect input volatility
    assert out["BTC/USDT"] < out["SOL/USDT"] < out["BONK/USDT"]


def test_dynamic_coin_discovery_works_for_any_symbol(monkeypatch):
    """Brief 81a explicit constraint: NO hardcoded coin list. The caller
    passes whatever symbols are active in bot_config — today BTC/SOL/BONK,
    tomorrow ETH/XLM/DOGE. The volatility module must not care."""
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.005),
        "ETHUSDT": _alternating_series(0.007),
        "XLMUSDT": _alternating_series(0.012),
        "DOGEUSDT": _alternating_series(0.015),
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(
        ["BTC/USDT", "ETH/USDT", "XLM/USDT", "DOGE/USDT"]
    )
    assert set(out.keys()) == {"BTC/USDT", "ETH/USDT", "XLM/USDT", "DOGE/USDT"}
    assert out["BTC/USDT"] == 1.0
    assert all(v > 0 for v in out.values())


def test_failed_fetch_falls_back_to_one(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines(
        series_by_symbol={"BTCUSDT": _alternating_series(0.005)},
        fail={"BONKUSDT"},
    )
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT", "BONK/USDT"])
    assert out["BONK/USDT"] == 1.0


def test_btc_fetch_failure_degrades_all_to_one(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines(
        series_by_symbol={"SOLUSDT": _alternating_series(0.020)},
        fail={"BTCUSDT"},
    )
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    out = vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    assert out == {"BTC/USDT": 1.0, "SOL/USDT": 1.0}


def test_cache_avoids_repeated_fetches_within_ttl(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.005),
        "SOLUSDT": _alternating_series(0.008),
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    n_after_first = len(fake.calls)
    # Second call within TTL: should not refetch
    vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    assert len(fake.calls) == n_after_first


def test_cache_refetches_after_ttl_expiry(monkeypatch):
    vol_mod.reset_cache()
    fake = FakeKlines({
        "BTCUSDT": _alternating_series(0.005),
        "SOLUSDT": _alternating_series(0.008),
    })
    monkeypatch.setattr(vol_mod, "fetch_klines_1h", fake)
    vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    n_after_first = len(fake.calls)
    # Force expiry by patching time
    real_time = time.time
    monkeypatch.setattr(
        vol_mod.time, "time",
        lambda: real_time() + vol_mod.CACHE_TTL_S + 1
    )
    vol_mod.get_volatility_multipliers(["BTC/USDT", "SOL/USDT"])
    assert len(fake.calls) > n_after_first


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
