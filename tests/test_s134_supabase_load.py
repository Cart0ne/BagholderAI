"""S134 — alleggerire Supabase + trade outbox.

Pins:
1. TradeLogger.log_trade: happy path unchanged; a transient DB failure parks
   the trade in a local outbox (never lost); a real rejection still raises.
2. flush_outbox: writes parked trades in order with their real fill time,
   never twice (exchange_order_id check), skim linked to the trade.
3. _upsert_runtime_state: no rewrite of an unchanged mirror, heartbeat every
   10 min, rewrite on change.
4. Load-reduction constants (orchestrator config poll, Sherpa loop, grid
   config refresh, reserve cache, Sentinel heartbeat).
"""

import json

import pytest

import db.client as dbc
from bot.grid_runner import runtime_state as rs


# --- a tiny controllable Supabase fake ---------------------------------------

class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.op = "select"
        self.payload = None
        self.filters = {}

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, **k):
        self.op = "upsert"
        self.payload = payload
        return self

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def limit(self, *a):
        return self

    def execute(self):
        if self.db.down:
            raise self.db.down
        self.db.calls.append((self.table, self.op, self.payload, dict(self.filters)))
        rows = self.db.rows.setdefault(self.table, [])
        if self.op in ("insert", "upsert"):
            if self.db.reject:
                raise self.db.reject
            row = dict(self.payload)
            row.setdefault("id", f"{self.table}-{len(rows) + 1}")
            rows.append(row)
            return _Res([row])
        hits = [r for r in rows if all(r.get(c) == v for c, v in self.filters.items())]
        return _Res(hits)


class _DB:
    def __init__(self):
        self.down = None
        self.reject = None
        self.calls = []
        self.rows = {}

    def table(self, name):
        return _Q(self, name)


class _APIError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.message = message
        self.code = code


@pytest.fixture
def tl(tmp_path, monkeypatch):
    monkeypatch.setenv("BAGHOLDER_TRADE_OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(dbc, "get_current_cycle", lambda c=None, s=None: "kraken_2b")
    dbc._OUTBOX_LAST_ATTEMPT.clear()
    logger = dbc.TradeLogger()
    logger.client = _DB()
    return logger


def _buy(tl, order_id="OAAAAA-1", amount=0.0004, price=74000.0):
    return tl.log_trade(
        symbol="BTC/USD", side="buy", amount=amount, price=price, fee=0.26,
        strategy="A", brain="grid", reason="Pct buy: test", mode="live",
        exchange_order_id=order_id, managed_by="grid", fee_asset="USD",
    )


def _outbox(tmp_path, failed=False):
    name = "trade_outbox_BTC_USD" + ("_failed" if failed else "") + ".jsonl"
    p = tmp_path / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


# --- 1. log_trade -------------------------------------------------------------

def test_happy_path_unchanged(tl, tmp_path):
    row = _buy(tl)
    assert row["exchange_order_id"] == "OAAAAA-1"
    assert "_queued" not in row
    assert "created_at" not in tl.client.rows["trades"][0]  # DB default now()
    assert _outbox(tmp_path) == []


def test_timeout_parks_trade_instead_of_losing_it(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("The read operation timed out")
    row = _buy(tl)
    assert row == {"_queued": True}
    parked = _outbox(tmp_path)
    assert len(parked) == 1
    assert parked[0]["data"]["exchange_order_id"] == "OAAAAA-1"
    assert parked[0]["fill_time"]


def test_real_rejection_still_raises(tl, tmp_path):
    tl.client.reject = _APIError(
        "Short sell rejected: would sell 0.00045031 total", "P0001"
    )
    with pytest.raises(_APIError):
        _buy(tl)
    assert _outbox(tmp_path) == []


@pytest.mark.parametrize("err,expected", [
    (_APIError("JSON could not be generated", 521), True),
    (_APIError("JSON could not be generated", 503), True),
    (_APIError("Could not query the database for the schema cache.", "PGRST002"), True),
    (_APIError("Short sell rejected: 0.0005031 total", "P0001"), False),
    (_APIError("Duplicate trade rejected", "P0001"), False),
    (_APIError("duplicate key value violates unique constraint", "23505"), False),
    (TimeoutError("timed out"), True),
])
def test_transient_classification(err, expected):
    assert dbc._is_transient_db_error(err) is expected


def test_new_trade_queues_behind_parked_ones(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    _buy(tl, order_id="O-FIRST")
    dbc._OUTBOX_LAST_ATTEMPT.clear()
    _buy(tl, order_id="O-SECOND")
    ids = [e["data"]["exchange_order_id"] for e in _outbox(tmp_path)]
    assert ids == ["O-FIRST", "O-SECOND"]


# --- 2. flush_outbox ----------------------------------------------------------

def test_flush_writes_in_order_with_fill_time(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    _buy(tl, order_id="O-1")
    _buy(tl, order_id="O-2")
    fill_times = [e["fill_time"] for e in _outbox(tmp_path)]

    tl.client.down = None
    left = tl.flush_outbox("BTC/USD", force=True)
    assert left == 0
    rows = tl.client.rows["trades"]
    assert [r["exchange_order_id"] for r in rows] == ["O-1", "O-2"]
    assert [r["created_at"] for r in rows] == fill_times
    assert all(r["cycle"] == "kraken_2b" for r in rows)
    assert not (tmp_path / "trade_outbox_BTC_USD.jsonl").exists()


def test_flush_never_inserts_the_same_order_twice(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    _buy(tl, order_id="O-LANDED")
    # The first attempt actually landed (reply timed out):
    tl.client.down = None
    tl.client.rows["trades"] = [{"id": "t-1", "exchange_order_id": "O-LANDED"}]
    tl.flush_outbox("BTC/USD", force=True)
    assert len(tl.client.rows["trades"]) == 1


def test_flush_is_rate_limited_during_outage(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    _buy(tl)
    assert tl.flush_outbox("BTC/USD", force=True) == 1
    tl.client.down = None
    calls_before = len(tl.client.calls)
    assert tl.flush_outbox("BTC/USD") == 1  # within 10 min: no DB call
    assert len(tl.client.calls) == calls_before


def test_flush_moves_rejected_trade_aside(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    _buy(tl, order_id="O-BAD")
    tl.client.down = None
    tl.client.reject = _APIError("Short sell rejected", "P0001")
    assert tl.flush_outbox("BTC/USD", force=True) == 0
    assert [e["data"]["exchange_order_id"] for e in _outbox(tmp_path, failed=True)] == ["O-BAD"]


def test_skim_parked_with_sell_and_linked_on_flush(tl, tmp_path):
    import httpx
    tl.client.down = httpx.ReadTimeout("timed out")
    tl.log_trade(
        symbol="BTC/USD", side="sell", amount=0.0004, price=80000.0, fee=0.26,
        strategy="A", brain="grid", reason="Pct sell: test", mode="live",
        exchange_order_id="O-SELL", realized_pnl=1.5, managed_by="grid",
        fee_asset="USD",
    )
    assert tl.attach_skim_to_queued("BTC/USD", "O-SELL", 0.45, managed_by="grid")
    tl.client.down = None
    tl.flush_outbox("BTC/USD", force=True)
    trade = tl.client.rows["trades"][0]
    skim = tl.client.rows["reserve_ledger"][0]
    assert skim["trade_id"] == trade["id"]
    assert skim["amount"] == 0.45
    assert skim["created_at"] == trade["created_at"]


# --- 3. runtime state mirror --------------------------------------------------

class _Bot:
    _pct_last_buy_price = 75000.0
    _last_sell_price = 0.0
    _stop_buy_active = False
    _stop_buy_activated_at = None
    _stop_buy_baseline_price = 0.0
    _sell_pct_penalty = 0.0
    _phantom_holdings = 0.0
    managed_holdings = 0.002
    _last_trade_time = None


class _TL:
    def __init__(self):
        self.client = _DB()


def test_runtime_state_not_rewritten_when_unchanged(monkeypatch):
    rs._LAST_WRITE.clear()
    clock = {"t": 1000.0}
    monkeypatch.setattr(rs.time, "time", lambda: clock["t"])
    tl, bot = _TL(), _Bot()

    rs._upsert_runtime_state(tl, bot, "BTC/USD")
    clock["t"] += 60
    rs._upsert_runtime_state(tl, bot, "BTC/USD")
    assert len(tl.client.calls) == 1  # unchanged → skipped

    bot._pct_last_buy_price = 74000.0
    rs._upsert_runtime_state(tl, bot, "BTC/USD")
    assert len(tl.client.calls) == 2  # changed → written

    clock["t"] += rs.RUNTIME_STATE_HEARTBEAT_S
    rs._upsert_runtime_state(tl, bot, "BTC/USD")
    assert len(tl.client.calls) == 3  # heartbeat


def test_runtime_state_backs_off_after_failure(monkeypatch):
    import httpx
    rs._LAST_WRITE.clear()
    clock = {"t": 1000.0}
    monkeypatch.setattr(rs.time, "time", lambda: clock["t"])
    tl, bot = _TL(), _Bot()
    tl.client.down = httpx.ReadTimeout("timed out")
    rs._upsert_runtime_state(tl, bot, "SOL/USD")
    tl.client.down = None
    clock["t"] += 60
    bot._pct_last_buy_price = 1.0
    rs._upsert_runtime_state(tl, bot, "SOL/USD")
    assert tl.client.calls == []  # still backing off
    clock["t"] += rs.RUNTIME_STATE_HEARTBEAT_S
    rs._upsert_runtime_state(tl, bot, "SOL/USD")
    assert len(tl.client.calls) == 1


# --- 4. cadences ---------------------------------------------------------------

def test_load_reduction_cadences():
    from bot import orchestrator
    from bot.sentinel import main as sentinel_main
    from bot.sherpa import main as sherpa_main
    from config import supabase_config

    assert orchestrator.POLL_INTERVAL == 30          # process supervision unchanged
    assert orchestrator.CONFIG_POLL_INTERVAL == 300
    assert sherpa_main.LOOP_INTERVAL_S == 1800
    assert supabase_config.CONFIG_REFRESH_INTERVAL == 1800
    assert dbc.ReserveLedger.CACHE_TTL == 1800
    assert sentinel_main.SCAN_INTERVAL_S == 60       # 1-minute samples kept
    assert sentinel_main.SENTINEL_HEARTBEAT_S == 3600
    # slow loop still every 4h whatever the scan interval
    assert sentinel_main.SLOW_LOOP_EVERY_N_TICKS * sentinel_main.SCAN_INTERVAL_S == 4 * 3600
