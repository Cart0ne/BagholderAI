"""
T.1 (a) — status-line publisher: post + pin the site status line on change.

Pins only the status line; posts once per change (idempotent via the
telegram_publish_state marker). This test pins the pure logic + the no-send
paths (dry-run / unchanged / missing row) with a fake Supabase — no telegram
SDK needed (the module imports it lazily, inside the IO functions, so the real
send/pin is exercised on the Mac Mini).

Run:
    python tests/test_telegram_publisher_status_t1a.py
    # or: pytest tests/test_telegram_publisher_status_t1a.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import telegram_publisher as tp


# ----------------------------------------------------------------------
# Fake Supabase honouring select/eq/order/limit/upsert/execute.
# ----------------------------------------------------------------------

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

    def upsert(self, row, on_conflict=None):
        # emulate on_conflict=key upsert into the backing store
        rows = self._store.setdefault(self._name, [])
        key = row.get(on_conflict) if on_conflict else None
        if key is not None:
            for i, r in enumerate(rows):
                if r.get(on_conflict) == key:
                    rows[i] = {**r, **row}
                    break
            else:
                rows.append(dict(row))
        else:
            rows.append(dict(row))
        return self

    def execute(self):
        out = [
            r for r in self._rows
            if all(r.get(k) == v for k, v in self._filters.items())
        ]
        if self._limit is not None:
            out = out[: self._limit]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self, tables):
        self._store = {k: list(v) for k, v in tables.items()}

    def table(self, name):
        return FakeQuery(name, self._store)


ROW = {
    "status_text": "One supervised $25 order on Kraken · real money, real fill",
    "status_emoji": "🔬",
    "updated_at": "2026-07-17 18:29:19.72329+00",
}


# ----------------------------------------------------------------------
# Pure logic
# ----------------------------------------------------------------------

def test_build_status_post():
    text = tp.build_status_post(ROW)
    assert "🔬" in text
    assert "Status update" in text
    assert ROW["status_text"] in text
    assert "bagholderai.lol" in text


def test_status_changed():
    assert tp.status_changed(ROW, None) is True            # no marker yet
    assert tp.status_changed(ROW, "2026-01-01") is True    # different marker
    assert tp.status_changed(ROW, ROW["updated_at"]) is False  # same → no repost
    assert tp.status_changed(None, "whatever") is False    # no row → nothing


# ----------------------------------------------------------------------
# publish_status_line — no-send paths (dry-run / unchanged / missing)
# ----------------------------------------------------------------------

def test_publish_dry_run_renders_without_sending():
    sb = FakeSupabase({"project_status": [ROW], "telegram_publish_state": []})
    res = tp.publish_status_line(sb=sb, dry_run=True)
    assert res["posted"] is False
    assert res["reason"] == "dry-run"
    assert ROW["status_text"] in res["text"]


def test_publish_skips_when_unchanged():
    sb = FakeSupabase({
        "project_status": [ROW],
        "telegram_publish_state": [
            {"key": tp.STATUS_MARKER, "value": ROW["updated_at"]},
        ],
    })
    res = tp.publish_status_line(sb=sb, dry_run=False)
    assert res["posted"] is False
    assert res["reason"] == "unchanged"


def test_publish_handles_missing_row():
    sb = FakeSupabase({"project_status": [], "telegram_publish_state": []})
    res = tp.publish_status_line(sb=sb, dry_run=True)
    assert res["posted"] is False
    assert res["reason"] == "no project_status row"


if __name__ == "__main__":
    test_build_status_post()
    test_status_changed()
    test_publish_dry_run_renders_without_sending()
    test_publish_skips_when_unchanged()
    test_publish_handles_missing_row()
    print("PASS — T.1(a): status-line publisher logic (build/change-detect/dry-run/"
          "unchanged/missing) verified; send+pin exercised on the Mini.")
