"""
T.1 (c) — regime publisher: post on a CONFIRMED + CHANGED + past-min-hold
Fear & Greed regime shift. No pin.

The three anti-chatter guards (Max's "freno anti-tremolio"):
  1. confirmed: latest K slow scans agree on the bucket,
  2. changed: bucket differs from the last one announced,
  3. min-hold: >= REGIME_MIN_HOLD_HOURS since the last regime post.

Reads the regime the system already computed (sentinel_scores.raw_signals.regime),
so no threshold re-derivation.

Run:
    python tests/test_telegram_publisher_regime_t1c.py
    # or: pytest tests/test_telegram_publisher_regime_t1c.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import telegram_publisher as tp


class FakeQuery:
    def __init__(self, table_name, store):
        self._name = table_name
        self._store = store
        self._rows = list(store.get(table_name, []))
        self._filters = {}
        self._limit = None

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self  # rows are seeded newest-first

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def execute(self):
        out = [r for r in self._rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._limit is not None:
            out = out[: self._limit]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self, tables):
        self._store = {k: list(v) for k, v in tables.items()}

    def table(self, name):
        return FakeQuery(name, self._store)


def _slow_row(regime, fng_value=25, label="Extreme Fear"):
    return {"score_type": "slow", "created_at": "2026-07-18T17:00:00+00:00",
            "raw_signals": {"regime": regime, "fng_value": fng_value, "fng_label": label}}


NOW = datetime(2026, 7, 18, 20, 0, 0, tzinfo=timezone.utc)


# ---------------- pure logic ----------------

def test_confirmed_regime():
    assert tp.confirmed_regime([_slow_row("fear"), _slow_row("fear")], 2) == "fear"
    # disagreement in the top-2 → not confirmed (boundary flicker)
    assert tp.confirmed_regime([_slow_row("neutral"), _slow_row("fear")], 2) is None
    # not enough history
    assert tp.confirmed_regime([_slow_row("fear")], 2) is None


def test_build_regime_post():
    first = tp.build_regime_post("extreme_fear", 25, "Extreme Fear", prev_bucket=None)
    assert "Extreme Fear" in first and "😱" in first and "F&amp;G 25" in first
    shift = tp.build_regime_post("fear", 32, "Fear", prev_bucket="neutral")
    assert "from Neutral to" in shift and "Fear" in shift


# ---------------- publish_regime paths ----------------

def _state(rows):
    return {"sentinel_scores": rows, "telegram_publish_state": []}


def test_posts_on_confirmed_change():
    sb = FakeSupabase(_state([_slow_row("extreme_fear"), _slow_row("extreme_fear")]))
    res = tp.publish_regime(sb=sb, dry_run=True, now=NOW)
    assert res["posted"] is False and res["reason"] == "dry-run"
    assert res["bucket"] == "extreme_fear"
    assert "Extreme Fear" in res["text"]


def test_skips_when_not_confirmed():
    sb = FakeSupabase(_state([_slow_row("greed"), _slow_row("fear")]))
    res = tp.publish_regime(sb=sb, dry_run=True, now=NOW)
    assert res["posted"] is False and "not confirmed" in res["reason"]


def test_skips_when_unchanged():
    tables = _state([_slow_row("fear"), _slow_row("fear")])
    tables["telegram_publish_state"] = [{"key": tp.REGIME_MARKER, "value": "fear"}]
    sb = FakeSupabase(tables)
    res = tp.publish_regime(sb=sb, dry_run=True, now=NOW)
    assert res["posted"] is False and res["reason"] == "unchanged"


def test_debounced_by_min_hold():
    # confirmed + changed, but we posted a different regime only 3h ago → hold.
    recent = (NOW - timedelta(hours=3)).isoformat()
    tables = _state([_slow_row("fear"), _slow_row("fear")])
    tables["telegram_publish_state"] = [
        {"key": tp.REGIME_MARKER, "value": "neutral"},
        {"key": tp.REGIME_POSTED_AT, "value": recent},
    ]
    sb = FakeSupabase(tables)
    res = tp.publish_regime(sb=sb, dry_run=True, now=NOW)
    assert res["posted"] is False and "min-hold" in res["reason"]


def test_posts_after_min_hold_elapsed():
    old = (NOW - timedelta(hours=30)).isoformat()
    tables = _state([_slow_row("fear"), _slow_row("fear")])
    tables["telegram_publish_state"] = [
        {"key": tp.REGIME_MARKER, "value": "neutral"},
        {"key": tp.REGIME_POSTED_AT, "value": old},
    ]
    sb = FakeSupabase(tables)
    res = tp.publish_regime(sb=sb, dry_run=True, now=NOW)
    assert res["posted"] is False and res["reason"] == "dry-run"  # would post
    assert res["bucket"] == "fear"
    assert "from Neutral to" in res["text"]


if __name__ == "__main__":
    test_confirmed_regime()
    test_build_regime_post()
    test_posts_on_confirmed_change()
    test_skips_when_not_confirmed()
    test_skips_when_unchanged()
    test_debounced_by_min_hold()
    test_posts_after_min_hold_elapsed()
    print("PASS — T.1(c): regime publisher (confirm + change + min-hold debounce) verified.")
