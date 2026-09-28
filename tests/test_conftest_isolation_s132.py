"""S132 (brief S131c): the suite must never write to production.

Guards the two layers set up in tests/conftest.py.
"""

import os
import socket

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("BAGHOLDER_TESTS_ALLOW_REMOTE") == "1",
    reason="integration run: isolation deliberately off",
)


def test_get_client_is_the_in_memory_fake():
    import db.client
    from tests.conftest import FAKE_SUPABASE

    assert db.client.get_client() is FAKE_SUPABASE


def test_log_event_is_recorded_not_sent():
    from db.event_logger import log_event
    from tests.conftest import FAKE_SUPABASE

    before = len(FAKE_SUPABASE.writes)
    log_event(severity="info", category="lifecycle", event="isolation_probe",
              message="must stay in memory", symbol="TEST/USDT")
    table, op, args, _ = FAKE_SUPABASE.writes[-1]
    assert len(FAKE_SUPABASE.writes) == before + 1
    assert (table, op) == ("bot_events_log", "insert")
    assert args[0]["event"] == "isolation_probe"


def test_outbound_network_is_blocked():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="Network blocked"):
            s.connect(("1.1.1.1", 443))
    finally:
        s.close()
