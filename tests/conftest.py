"""
Suite-wide isolation: tests never write to production (S132, brief S131c).

Until S132 there was no conftest, and every module that calls
`db.client.get_client()` talked to the real Supabase with the keys in
config/.env: each full run left ~70 fake rows (TEST/USDT, TEST/USD, BTC/USDT)
in the production bot_events_log.

Two layers, both active by default:
1. `db.client.get_client` is replaced by an in-memory fake BEFORE any test
   module imports bot code. That matters: ~20 modules do
   `from db.event_logger import log_event` / `from db.client import get_client`
   at import time, so a patch applied later would not reach their bindings.
   Writes are recorded on the fake (`_FakeSupabase.writes`), reads return [].
2. Outbound network is blocked (anything that is not loopback or a Unix
   socket): Supabase, Telegram, Kraken, Binance, Anthropic. A test that
   reaches the internet fails loudly instead of touching production.

Tests that patch get_client themselves (monkeypatch/patch) still win: they
replace the attribute on their own module, after this file has run.

Opt-out, for a deliberate integration run only:
    BAGHOLDER_TESTS_ALLOW_REMOTE=1 pytest ...
"""

import os
import socket

_ALLOW_REMOTE = os.getenv("BAGHOLDER_TESTS_ALLOW_REMOTE") == "1"


class _FakeResult:
    def __init__(self):
        self.data = []
        self.count = 0


class _FakeQuery:
    """Chainable stand-in for a supabase-py query builder: every method
    (select/insert/eq/order/limit/...) returns the builder, execute() returns
    an empty result. Insert/update/upsert/delete payloads are recorded."""

    _WRITES = {"insert", "update", "upsert", "delete"}

    def __init__(self, client, table):
        self._client = client
        self._table = table

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            if name in self._WRITES:
                self._client.writes.append((self._table, name, args, kwargs))
            return self
        return _method

    def execute(self):
        return _FakeResult()


class _FakeSupabase:
    def __init__(self):
        self.writes = []

    def table(self, name):
        return _FakeQuery(self, name)

    from_ = table

    def rpc(self, name, *args, **kwargs):
        return _FakeQuery(self, f"rpc:{name}")


FAKE_SUPABASE = _FakeSupabase()


def _fake_get_client():
    return FAKE_SUPABASE


def _guard_network():
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _is_local(sock, address):
        if sock.family == getattr(socket, "AF_UNIX", None):
            return True
        host = address[0] if isinstance(address, tuple) else address
        return host in ("127.0.0.1", "::1", "localhost")

    def connect(self, address):
        if not _is_local(self, address):
            raise RuntimeError(
                f"Network blocked in tests (tried {address!r}). "
                "Mock the call, or run with BAGHOLDER_TESTS_ALLOW_REMOTE=1."
            )
        return real_connect(self, address)

    def connect_ex(self, address):
        if not _is_local(self, address):
            raise RuntimeError(f"Network blocked in tests (tried {address!r}).")
        return real_connect_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


if not _ALLOW_REMOTE:
    import db.client as _db_client

    _db_client.get_client = _fake_get_client
    _guard_network()
