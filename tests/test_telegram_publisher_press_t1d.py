"""
T.1 (d) — press-review publisher: one morning digest/day of NewsKeeper's top
relevant articles, clickable links. No pin.

Guards: relevance high>medium (discard dropped), confidence tiebreak, dedup by
event_key (same story across outlets), cap PRESS_MAX, hour gate + once/day.

Run:
    python tests/test_telegram_publisher_press_t1d.py
    # or: pytest tests/test_telegram_publisher_press_t1d.py
"""

import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import telegram_publisher as tp


class FakeQuery:
    def __init__(self, table_name, store):
        self._name = table_name
        self._store = store
        self._rows = list(store.get(table_name, []))
        self._eq = {}
        self._in = {}
        self._limit = None

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self  # time window is not exercised by the fake

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def in_(self, col, vals):
        self._in[col] = set(vals)
        return self

    def execute(self):
        out = []
        for r in self._rows:
            if any(r.get(k) != v for k, v in self._eq.items()):
                continue
            if any(r.get(k) not in vals for k, vals in self._in.items()):
                continue
            out.append(r)
        if self._limit is not None:
            out = out[: self._limit]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self, tables):
        self._store = {k: list(v) for k, v in tables.items()}

    def table(self, name):
        return FakeQuery(name, self._store)


def _row(relevance, conf, key, title, link, polarity=1):
    return {"relevance": relevance, "confidence": conf, "event_key": key,
            "summary": title, "raw_data": {"link": link}, "polarity": polarity}


# ---------------- rank_press ----------------

def test_rank_excludes_discard_dedups_and_orders():
    rows = [
        _row("medium", 0.9, "e1", "Med high-conf", "http://a"),
        _row("high", 0.5, "e2", "High low-conf", "http://b", polarity=-1),
        _row("discard", 0.99, "e3", "Discarded noise", "http://c"),
        _row("high", 0.8, "e2", "Dup of e2 (higher conf)", "http://b2"),
    ]
    ranked = tp.rank_press(rows, 5)
    titles = [x["title"] for x in ranked]
    assert "Discarded noise" not in titles                 # discard dropped
    assert titles == ["Dup of e2 (higher conf)", "Med high-conf"]  # high>med, e2 deduped to best
    assert len(ranked) == 2


def test_rank_caps_to_max():
    rows = [_row("high", 0.9 - i / 100, f"e{i}", f"t{i}", f"http://{i}") for i in range(10)]
    assert len(tp.rank_press(rows, 5)) == 5


def test_rank_skips_rows_without_link_or_title():
    rows = [
        {"relevance": "high", "confidence": 0.9, "event_key": "e1", "summary": "no link", "raw_data": {}},
        {"relevance": "high", "confidence": 0.9, "event_key": "e2", "summary": "  ", "raw_data": {"link": "http://x"}},
        _row("high", 0.9, "e3", "ok", "http://ok"),
    ]
    ranked = tp.rank_press(rows, 5)
    assert [x["title"] for x in ranked] == ["ok"]


# ---------------- build_press_post ----------------

def test_build_escapes_and_marks_polarity():
    items = [
        {"title": "US & UK align rules", "link": "http://x?a=1&b=2", "polarity": 1},
        {"title": "Hack drains funds", "link": "http://y", "polarity": -1},
    ]
    text = tp.build_press_post(items, "2026-07-18")
    assert "Daily crypto press review" in text
    assert "US &amp; UK align rules" in text          # title & escaped
    assert "a=1&amp;b=2" in text                       # url & escaped
    assert "📈" in text and "📉" in text                # polarity markers
    assert 'href="http://x?a=1&amp;b=2"' in text


# ---------------- publish_press_review paths ----------------

def test_before_hour_gate():
    sb = FakeSupabase({"newskeeper_signals": [_row("high", 0.9, "e", "t", "http://a")],
                       "telegram_publish_state": []})
    res = tp.publish_press_review(sb=sb, dry_run=True, now=datetime(2026, 7, 18, 7, 0))
    assert res["posted"] is False and "before" in res["reason"]


def test_already_posted_today():
    sb = FakeSupabase({
        "newskeeper_signals": [_row("high", 0.9, "e", "t", "http://a")],
        "telegram_publish_state": [{"key": tp.PRESS_MARKER, "value": "2026-07-18"}],
    })
    res = tp.publish_press_review(sb=sb, dry_run=True, now=datetime(2026, 7, 18, 10, 0))
    assert res["posted"] is False and res["reason"] == "already posted today"


def test_no_relevant_articles():
    sb = FakeSupabase({
        "newskeeper_signals": [_row("discard", 0.99, "e", "noise", "http://a")],
        "telegram_publish_state": [],
    })
    res = tp.publish_press_review(sb=sb, dry_run=True, now=datetime(2026, 7, 18, 10, 0))
    assert res["posted"] is False and res["reason"] == "no relevant articles"


def test_dry_run_builds_digest():
    sb = FakeSupabase({
        "newskeeper_signals": [
            _row("high", 0.9, "e1", "Big BTC news", "http://a"),
            _row("medium", 0.7, "e2", "Some altcoin thing", "http://b"),
        ],
        "telegram_publish_state": [],
    })
    res = tp.publish_press_review(sb=sb, dry_run=True, now=datetime(2026, 7, 18, 10, 0))
    assert res["posted"] is False and res["reason"] == "dry-run"
    assert res["count"] == 2
    assert "Big BTC news" in res["text"]


if __name__ == "__main__":
    test_rank_excludes_discard_dedups_and_orders()
    test_rank_caps_to_max()
    test_rank_skips_rows_without_link_or_title()
    test_build_escapes_and_marks_polarity()
    test_before_hour_gate()
    test_already_posted_today()
    test_no_relevant_articles()
    test_dry_run_builds_digest()
    print("PASS — T.1(d): press-review publisher (rank/dedup/cap/escape/hour-gate/once-a-day) verified.")
