"""
T.1 (b) — diary publisher: post the CEO's session summary on a new COMPLETE entry.

Pins nothing. Idempotent via the diary:last_posted_session marker. Latest-only
(a burst of back-written sessions announces just the newest). Gated on
status='COMPLETE' so a half-written draft is never posted.

Run:
    python tests/test_telegram_publisher_diary_t1b.py
    # or: pytest tests/test_telegram_publisher_diary_t1b.py
"""

import os
import sys
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
        return self

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


COMPLETE = {
    "session": 119, "title": "The One Where Everyone's Numbers Were Wrong",
    "summary": "The project spent real money for the first time: $25 of BTC on Kraken.",
    "date": "July 13-17, 2026", "status": "COMPLETE",
}


def test_build_diary_post():
    text = tp.build_diary_post(COMPLETE)
    assert "Session 119" in text
    assert COMPLETE["title"] in text
    assert COMPLETE["summary"] in text
    assert "July 13-17, 2026" in text
    assert "bagholderai.lol" in text


def test_diary_is_new():
    assert tp.diary_is_new(COMPLETE, None) is True          # first run
    assert tp.diary_is_new(COMPLETE, "118") is True         # newer session
    assert tp.diary_is_new(COMPLETE, "119") is False        # already posted
    assert tp.diary_is_new(COMPLETE, "120") is False        # marker ahead (no downgrade)
    # draft never posts
    assert tp.diary_is_new({**COMPLETE, "status": "DRAFT"}, None) is False
    # empty summary never posts
    assert tp.diary_is_new({**COMPLETE, "summary": "  "}, None) is False


def test_publish_dry_run_and_skip():
    sb = FakeSupabase({"diary_entries": [COMPLETE], "telegram_publish_state": []})
    res = tp.publish_diary(sb=sb, dry_run=True)
    assert res["posted"] is False and res["reason"] == "dry-run"
    assert COMPLETE["summary"] in res["text"]

    # already posted → skip
    sb2 = FakeSupabase({
        "diary_entries": [COMPLETE],
        "telegram_publish_state": [{"key": tp.DIARY_MARKER, "value": "119"}],
    })
    res2 = tp.publish_diary(sb=sb2, dry_run=False)
    assert res2["posted"] is False and res2["reason"] == "no new session"


def test_publish_ignores_draft_latest():
    # Latest by session is a DRAFT → read_latest_diary filters to COMPLETE only,
    # so it returns the older COMPLETE one (not the draft).
    draft = {**COMPLETE, "session": 120, "status": "DRAFT", "summary": "wip"}
    sb = FakeSupabase({
        "diary_entries": [draft, COMPLETE],
        "telegram_publish_state": [],
    })
    res = tp.publish_diary(sb=sb, dry_run=True)
    assert res["posted"] is False and res["reason"] == "dry-run"
    assert "Session 119" in res["text"]  # the COMPLETE one, not the draft 120


if __name__ == "__main__":
    test_build_diary_post()
    test_diary_is_new()
    test_publish_dry_run_and_skip()
    test_publish_ignores_draft_latest()
    print("PASS — T.1(b): diary publisher (build/new-detect/draft-gate/dry-run/skip) verified.")
