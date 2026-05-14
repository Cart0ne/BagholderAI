"""Unit tests for bot.sherpa.regime_reader.get_current_regime().

Covers: happy path / no slow row yet / DB error / malformed raw_signals
/ unknown regime string. All fallback paths return "neutral".

Run:
    python -m pytest tests/test_regime_reader.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sherpa import regime_reader


class FakeQuery:
    def __init__(self, rows=None, raise_exc=None):
        self._rows = rows or []
        self._raise = raise_exc

    def select(self, *args, **kw): return self
    def eq(self, *args, **kw): return self
    def order(self, *args, **kw): return self
    def limit(self, *args, **kw): return self

    def execute(self):
        if self._raise:
            raise self._raise
        result = type("Result", (), {"data": self._rows})()
        return result


class FakeSupabase:
    def __init__(self, rows=None, raise_exc=None):
        self._q = FakeQuery(rows=rows, raise_exc=raise_exc)

    def table(self, name):
        assert name == "sentinel_scores"
        return self._q


def test_returns_regime_from_latest_slow_row():
    sb = FakeSupabase(rows=[{"raw_signals": {"regime": "fear"}, "created_at": "x"}])
    assert regime_reader.get_current_regime(sb) == "fear"


def test_all_five_valid_regimes_are_returned():
    for r in ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]:
        sb = FakeSupabase(rows=[{"raw_signals": {"regime": r}}])
        assert regime_reader.get_current_regime(sb) == r


def test_no_slow_row_falls_back_to_neutral():
    sb = FakeSupabase(rows=[])
    assert regime_reader.get_current_regime(sb) == "neutral"


def test_db_error_falls_back_to_neutral():
    sb = FakeSupabase(raise_exc=RuntimeError("supabase down"))
    assert regime_reader.get_current_regime(sb) == "neutral"


def test_unknown_regime_string_falls_back_to_neutral():
    sb = FakeSupabase(rows=[{"raw_signals": {"regime": "panic"}}])
    assert regime_reader.get_current_regime(sb) == "neutral"


def test_missing_regime_key_falls_back_to_neutral():
    sb = FakeSupabase(rows=[{"raw_signals": {"fng_value": 50}}])
    assert regime_reader.get_current_regime(sb) == "neutral"


def test_null_raw_signals_falls_back_to_neutral():
    sb = FakeSupabase(rows=[{"raw_signals": None}])
    assert regime_reader.get_current_regime(sb) == "neutral"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
