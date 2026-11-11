"""
BagHolderAI - Database Client
Handles all Supabase interactions: logging trades, updating portfolio, etc.
"""

import json
import logging
import os
import time
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional
from config.settings import DatabaseConfig

logger = logging.getLogger("bagholderai.db")


# --- S134 trade outbox --------------------------------------------------------
# A trade already filled on the exchange whose INSERT fails because Supabase is
# unreachable is parked in logs/trade_outbox_<SYMBOL>.jsonl (one file per grid
# process, no concurrent writers) and flushed in order once the DB answers.
# Permanent rejections (triggers, constraints) are NOT parked: they raise as
# before, so a real bug stays visible.
OUTBOX_RETRY_S = 600  # at most one flush attempt per 10 min during an outage
_OUTBOX_LAST_ATTEMPT: dict = {}
_TRANSIENT_CODES = {"PGRST002", "502", "503", "504", "520", "521", "522", "523", "524"}
_TRANSIENT_TEXT = ("timed out", "timeout", "upstream connect", "schema cache",
                   "JSON could not be generated", "Server disconnected",
                   "Connection refused", "connection reset", "Name or service not known",
                   "nodename nor servname")


def _outbox_dir() -> Path:
    override = os.getenv("BAGHOLDER_TRADE_OUTBOX_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "logs"


def _outbox_path(symbol: str, failed: bool = False) -> Path:
    name = symbol.replace("/", "_")
    suffix = "_failed" if failed else ""
    return _outbox_dir() / f"trade_outbox_{name}{suffix}.jsonl"


def _outbox_read(symbol: str) -> list:
    path = _outbox_path(symbol)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            logger.error(f"[{symbol}] Outbox: unreadable line skipped: {line[:200]}")
    return entries


def _outbox_write(symbol: str, entries: list) -> None:
    path = _outbox_path(symbol)
    if not entries:
        path.unlink(missing_ok=True)
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(e, default=str) + "\n" for e in entries))
    tmp.replace(path)


def _outbox_append(symbol: str, data: dict, fill_time: str) -> None:
    path = _outbox_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"fill_time": fill_time, "data": data, "skim": None}
    with path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _outbox_append_failed(symbol: str, entry: dict, error: str) -> None:
    path = _outbox_path(symbol, failed=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({**entry, "error": error[:500]}, default=str) + "\n")


def _is_transient_db_error(e: Exception) -> bool:
    """True when the DB/gateway is unreachable, False when it answered with a
    real rejection (trigger, constraint, bad request)."""
    code = str(getattr(e, "code", "") or "")
    msg = str(getattr(e, "message", "") or e)
    if code in _TRANSIENT_CODES:
        return True
    if code.startswith("P0") or code.startswith("23") or code.startswith("42"):
        return False  # raised by a trigger / constraint / SQL error
    try:
        import httpx
        if isinstance(e, (httpx.TimeoutException, httpx.TransportError)):
            return True
    except ImportError:
        pass
    if isinstance(e, (TimeoutError, ConnectionError, OSError)):
        return True
    low = msg.lower()
    return any(t.lower() in low for t in _TRANSIENT_TEXT)


def get_client():
    """
    Create and return a Supabase client.
    Lazy import to avoid errors when supabase isn't installed yet.
    """
    from supabase import create_client
    return create_client(DatabaseConfig.SUPABASE_URL, DatabaseConfig.SUPABASE_KEY)


# --- Testnet cycle (S96a clean slate) ---------------------------------------
# Current cycle label (e.g. 'testnet_2') lives in bot_config.cycle, set by
# migration_20260604_s96a_clean_slate_cycle.sql. All grid rows are uniform.
# Writers stamp it on new rows; readers (boot replay, reserve, dashboards)
# filter by it so a monthly Binance testnet reset is handled by tagging the
# closed cycle, never deleting data. Next reset = UPDATE bot_config.cycle.
import time as _time
_CYCLE_CACHE = {"val": None, "ts": 0.0}
_CYCLE_TTL = 300  # seconds


def get_current_cycle(client=None, symbol: Optional[str] = None) -> str:
    """Return the current testnet cycle label from bot_config.

    Cached for _CYCLE_TTL when read globally (symbol=None). Falls back to
    'testnet_1' on any DB error so a write/replay never crashes on this.

    S118 (global path): the current cycle is the one on the most recently
    updated ACTIVE row (fallback: most recently updated row of all). The old
    rule — lexicographic max() across every row — silently broke the moment
    two venues coexist with different cycle tags (the winner depended on the
    alphabet, so Kraken trades could get stamped with the dead testnet
    cycle). With today's uniform tags the result is identical.

    S119 (Fase 2a): the GLOBAL path is pinned to venue='binance' — the
    canonical public venue during the Kraken test/collaudo (Board decision
    S119). Without it, activating a Kraken row (newest updated_at) would make
    the global/public cycle jump onto the near-empty Kraken cycle, exactly the
    S118 rule's blind spot. The PER-SYMBOL path (symbol given) stays
    venue-agnostic: each bot keeps its own row's cycle so a Kraken runner tags
    its trades correctly. All rows are venue='binance' today → no-op.
    """
    now = _time.time()
    if symbol is None and _CYCLE_CACHE["val"] and (now - _CYCLE_CACHE["ts"]) < _CYCLE_TTL:
        return _CYCLE_CACHE["val"]
    try:
        c = client or get_client()
        if symbol:
            rows = (
                c.table("bot_config").select("cycle")
                .eq("symbol", symbol).execute().data or []
            )
            val = max((r["cycle"] for r in rows if r.get("cycle")), default="testnet_1")
            return val
        rows = (
            c.table("bot_config").select("cycle,is_active,updated_at,venue")
            .execute().data or []
        )
        tagged = [r for r in rows if r.get("cycle")]
        # S125: il pin venue='binance' e' RIMOSSO. Esisteva (S119) perche'
        # durante il collaudo Kraken il venue pubblico canonico era Binance, e
        # senza pin l'attivazione di una riga Kraken avrebbe fatto saltare
        # l'intero sistema su un ciclo quasi vuoto. Dal cutover del 07-ago quel
        # motivo e' capovolto: le righe binance sono is_active=false, quindi
        # `canonical = binance or tagged` sceglieva le 4 righe SPENTE e
        # `pool = active or canonical` ci ricadeva sopra, restituendo
        # 'testnet_2'. Conseguenza concreta: lo snapshot giornaliero di
        # denaro reale sarebbe stato archiviato sotto il ciclo morto —
        # invisibile al grafico e mescolato all'archivio testnet.
        # Regola nuova, venue-agnostica: il ciclo globale e' quello della riga
        # ATTIVA aggiornata piu' di recente, su qualunque venue.
        active = [r for r in tagged if r.get("is_active")]
        pool = active or tagged
        if pool:
            val = max(pool, key=lambda r: str(r.get("updated_at") or ""))["cycle"]
        else:
            val = "testnet_1"
        _CYCLE_CACHE["val"] = val
        _CYCLE_CACHE["ts"] = now
        return val
    except Exception:
        return _CYCLE_CACHE["val"] or "testnet_1"


class TradeLogger:
    """Logs every trade the bot makes."""
    
    def __init__(self):
        self.client = get_client()
    
    def log_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        fee: float,
        strategy: str,
        brain: str,
        reason: str,
        mode: str = "paper",
        exchange_order_id: Optional[str] = None,
        realized_pnl: Optional[float] = None,
        buy_trade_id: Optional[str] = None,
        cost: Optional[float] = None,
        config_version: str = "v3",
        cash_before: Optional[float] = None,
        capital_allocated: Optional[float] = None,
        holdings_value_before: Optional[float] = None,
        managed_by: Optional[str] = None,
        fee_asset: Optional[str] = None,
    ) -> dict:
        """Log a trade to the database."""
        # S134: taken first — get_current_cycle below can block for minutes
        # during an outage, and a parked trade must keep its real fill time.
        fill_time = datetime.now(timezone.utc).isoformat()
        data = {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "cost": round(cost, 8) if cost is not None else round(amount * price, 8),
            "fee": fee,
            "strategy": strategy,
            "brain": brain,
            "reason": reason,
            "mode": mode,
            "exchange_order_id": exchange_order_id,
            "realized_pnl": realized_pnl,
            "buy_trade_id": buy_trade_id,
            "config_version": config_version,
            "cycle": get_current_cycle(self.client, symbol),  # S96a clean slate
        }
        if managed_by is not None:
            data["managed_by"] = managed_by
        # 67a: fee_asset only written when known (live trades from
        # exchange_orders.py). Paper trades omit it — column has default
        # 'USDT' on the DB side after the brief 67a migration.
        if fee_asset is not None:
            data["fee_asset"] = fee_asset

        # S134 trade outbox: a fill that already happened on the exchange must
        # never be lost because Supabase is down (14-ott SOL, 08-nov BTC). The
        # happy path is unchanged; only a transient DB failure parks the row in
        # a local file, flushed in order as soon as the DB answers again.
        if _outbox_read(symbol):
            # Older trades still parked: they must land first (the short-sell
            # trigger sums buys/sells, order matters).
            self.flush_outbox(symbol)
            if _outbox_read(symbol):
                _outbox_append(symbol, data, fill_time)
                logger.error(
                    f"[{symbol}] Trade queued to outbox behind earlier unsent "
                    f"trades ({side} {amount} @ {price}, id={exchange_order_id})"
                )
                return {"_queued": True}

        try:
            result = self.client.table("trades").insert(data).execute()
        except Exception as e:
            if not _is_transient_db_error(e):
                raise
            _outbox_append(symbol, data, fill_time)
            logger.error(
                f"[{symbol}] Trade NOT logged, DB unreachable ({e}) — queued to "
                f"outbox, will retry ({side} {amount} @ {price}, id={exchange_order_id})"
            )
            return {"_queued": True}
        return result.data[0] if result.data else {}

    # --- S134 trade outbox ------------------------------------------------

    def attach_skim_to_queued(self, symbol: str, exchange_order_id: Optional[str],
                              amount: float, managed_by: Optional[str] = None,
                              config_version: str = "v3") -> bool:
        """Attach a profit skim to a SELL parked in the outbox, so it is
        written together with (and linked to) the trade when it lands."""
        entries = _outbox_read(symbol)
        for entry in reversed(entries):
            if entry["data"].get("exchange_order_id") == exchange_order_id:
                entry["skim"] = {
                    "amount": round(amount, 8),
                    "managed_by": managed_by,
                    "config_version": config_version,
                }
                _outbox_write(symbol, entries)
                return True
        return False

    def flush_outbox(self, symbol: str, force: bool = False) -> int:
        """Try to write parked trades (oldest first). Never raises.

        Rate-limited to one attempt every OUTBOX_RETRY_S per symbol (a DB call
        during an outage can block for minutes), unless force=True (boot).
        Returns how many entries are still parked.
        """
        entries = _outbox_read(symbol)
        if not entries:
            return 0
        now = time.time()
        last = _OUTBOX_LAST_ATTEMPT.get(symbol, 0.0)
        if not force and (now - last) < OUTBOX_RETRY_S:
            return len(entries)
        _OUTBOX_LAST_ATTEMPT[symbol] = now

        while entries:
            entry = entries[0]
            try:
                self._flush_one(symbol, entry)
            except Exception as e:
                if _is_transient_db_error(e):
                    logger.warning(
                        f"[{symbol}] Outbox flush: DB still unreachable ({e}); "
                        f"{len(entries)} trade(s) still parked"
                    )
                    break
                # Permanent rejection (e.g. trigger): park it aside so it
                # doesn't block the queue forever. The nightly reconciliation
                # flags the missing trade.
                logger.error(
                    f"[{symbol}] Outbox flush: trade REJECTED by DB ({e}); moved "
                    f"to {_outbox_path(symbol, failed=True).name}"
                )
                _outbox_append_failed(symbol, entry, str(e))
            entries.pop(0)
            _outbox_write(symbol, entries)
        return len(entries)

    def _flush_one(self, symbol: str, entry: dict) -> None:
        data = dict(entry["data"])
        data["created_at"] = entry["fill_time"]
        data["cycle"] = get_current_cycle(self.client, symbol)
        trade_id = None
        order_id = data.get("exchange_order_id")
        if order_id:
            # The first attempt may have landed even though the reply timed
            # out: never insert the same exchange order twice.
            found = (
                self.client.table("trades").select("id")
                .eq("exchange_order_id", order_id).limit(1).execute()
            )
            if found.data:
                trade_id = found.data[0]["id"]
        if trade_id is None:
            result = self.client.table("trades").insert(data).execute()
            trade_id = result.data[0]["id"] if result.data else None
            logger.info(
                f"[{symbol}] Outbox flush: trade written ({data.get('side')} "
                f"{data.get('amount')} @ {data.get('price')}, fill {entry['fill_time']}, "
                f"id={order_id})"
            )
        skim = entry.get("skim")
        if skim and trade_id:
            existing = (
                self.client.table("reserve_ledger").select("id")
                .eq("trade_id", trade_id).limit(1).execute()
            )
            if not existing.data:
                self.client.table("reserve_ledger").insert({
                    "symbol": symbol,
                    "amount": skim["amount"],
                    "trade_id": trade_id,
                    "config_version": skim.get("config_version", "v3"),
                    "managed_by": skim.get("managed_by"),
                    "cycle": data["cycle"],
                    "created_at": entry["fill_time"],
                }).execute()
                logger.info(f"[{symbol}] Outbox flush: skim ${skim['amount']} written")
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """Fetch recent trades with optional filters."""
        query = self.client.table("trades").select("*").order("created_at", desc=True).limit(limit)
        
        if symbol:
            query = query.eq("symbol", symbol)
        if strategy:
            query = query.eq("strategy", strategy)
        
        result = query.execute()
        return result.data or []
    
    def get_daily_trade_count(self) -> int:
        """Count today's trades (for daily limit check)."""
        today = date.today().isoformat()
        result = (
            self.client.table("trades")
            .select("id", count="exact")
            .gte("created_at", f"{today}T00:00:00")
            .execute()
        )
        return result.count or 0

    def get_today_trades(self, symbol: Optional[str] = None, config_version: Optional[str] = None) -> list:
        """Fetch all of today's trades, optionally filtered by symbol and config_version."""
        today = date.today().isoformat()
        query = (
            self.client.table("trades")
            .select("*")
            .gte("created_at", f"{today}T00:00:00")
            .order("created_at", desc=True)
        )
        if symbol:
            query = query.eq("symbol", symbol)
        if config_version:
            query = query.eq("config_version", config_version)
        result = query.execute()
        return result.data or []

    def get_open_position(self, symbol: str, config_version: str = "v3") -> dict:
        """
        Reconstruct net position for a symbol from trades in DB.
        Filters by config_version to avoid cross-contamination between v1/v2/v3.
        Returns dict with holdings, avg_buy_price, realized_pnl, total_fees.
        """
        query = (
            self.client.table("trades")
            .select("*")
            .eq("symbol", symbol)
            .order("created_at", desc=True)
        )
        if config_version:
            query = query.eq("config_version", config_version)
        result = query.execute()
        trades = result.data or []

        holdings = 0.0
        avg_buy_price = 0.0
        realized_pnl = 0.0
        total_fees = 0.0
        total_invested = 0.0
        total_received = 0.0

        # Process in chronological order
        for t in reversed(trades):
            side = t.get("side")
            amount = float(t.get("amount", 0))
            price = float(t.get("price", 0))
            fee = float(t.get("fee", 0))
            total_fees += fee

            if side == "buy":
                total_invested += amount * price
                old_holdings = holdings
                holdings += amount
                if holdings > 0:
                    avg_buy_price = (avg_buy_price * old_holdings + price * amount) / holdings
            elif side == "sell":
                total_received += amount * price
                rpnl = float(t.get("realized_pnl", 0) or 0)
                realized_pnl += rpnl
                holdings -= amount
                if holdings <= 0:
                    holdings = 0.0
                    avg_buy_price = 0.0

        return {
            "holdings": holdings,
            "avg_buy_price": avg_buy_price,
            "realized_pnl": realized_pnl,
            "total_fees": total_fees,
            "total_invested": total_invested,
            "total_received": total_received,
        }


class DailyPnLTracker:
    """Tracks daily performance snapshots for dashboard."""

    def __init__(self):
        self.client = get_client()

    def record_daily(
        self,
        total_value: float,
        cash_remaining: float,
        holdings_value: float,
        initial_capital: float,
        total_pnl: float,
        realized_pnl_today: float = 0,
        total_fees_today: float = 0,
        trades_count: int = 0,
        buys_count: int = 0,
        sells_count: int = 0,
        positions: list = None,
    ) -> dict:
        """Record end-of-day portfolio snapshot."""
        import json
        data = {
            "date": date.today().isoformat(),
            "total_value": round(total_value, 8),
            "cash_remaining": round(cash_remaining, 8),
            "holdings_value": round(holdings_value, 8),
            "initial_capital": round(initial_capital, 8),
            "total_pnl": round(total_pnl, 8),
            "realized_pnl_today": round(realized_pnl_today, 8),
            "total_fees_today": round(total_fees_today, 8),
            "trades_count": trades_count,
            "buys_count": buys_count,
            "sells_count": sells_count,
            "positions": json.dumps(positions or []),
            "cycle": get_current_cycle(self.client),  # S96a clean slate
        }

        # S125: la chiave di conflitto passa da "date" a "date,cycle".
        # Con UNIQUE(date) esisteva UNA riga al giorno per tutto il sistema: dal
        # 22-lug al 6-ago un grid Binance arrivava sempre primo e lo snapshot
        # del bot Kraken veniva scartato in silenzio — 63 giorni di testnet_2 e
        # ZERO righe Kraken, cioe' il grafico §2 della dashboard senza nulla da
        # disegnare. Per-ciclo, ogni era tiene la propria serie e due venue in
        # parallelo smettono di escludersi a vicenda.
        # ignore_duplicates resta: fra i bot dello STESSO ciclo il primo vince,
        # che e' il coordinamento voluto (un report al giorno, non tre).
        result = (
            self.client.table("daily_pnl")
            .upsert(data, on_conflict="date,cycle", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)  # True = newly inserted, False = already existed

    def has_today_snapshot(self) -> bool:
        """Check if today's snapshot already exists (for single-report coordination)."""
        today = date.today().isoformat()
        result = (
            self.client.table("daily_pnl")
            .select("id")
            .eq("date", today)
            .execute()
        )
        return bool(result.data)

    def get_daily_pnl_today(self) -> float:
        """Get today's P&L (for daily loss limit check)."""
        today = date.today().isoformat()
        result = (
            self.client.table("daily_pnl")
            .select("total_pnl")
            .eq("date", today)
            .execute()
        )
        if result.data:
            return float(result.data[0].get("total_pnl", 0))
        return 0.0


class ReserveLedger:
    """
    Tracks accumulated profit reserve (skimmed from sell profits).

    Each entry = one skim event from one sell trade.
    Cache TTL = 5 minutes — refreshed on config reload cycles.
    """

    # S134: 300 → 1800. The reserve only changes on a skim (sell), and the sell
    # path force-refreshes right after it; the TTL just bounded idle re-reads.
    CACHE_TTL = 1800  # seconds

    def __init__(self):
        self.client = get_client()
        self._cache: dict = {}  # symbol -> {"total": float, "ts": float}

    def log_skim(self, symbol: str, amount: float, trade_id: str = None,
                 config_version: str = "v3", managed_by: str = None) -> dict:
        """Insert one skim entry and invalidate the cache for this symbol."""
        data = {
            "symbol": symbol,
            "amount": round(amount, 8),
            "trade_id": trade_id,
            "config_version": config_version,
            "managed_by": managed_by,
            "cycle": get_current_cycle(self.client, symbol),  # S96a clean slate
        }
        result = self.client.table("reserve_ledger").insert(data).execute()
        # Invalidate so next call queries fresh
        self._cache.pop(symbol, None)
        return result.data[0] if result.data else {}

    def get_reserve_total(self, symbol: str, config_version: str = "v3",
                          force_refresh: bool = False) -> float:
        """Return total reserve for a symbol. Cached for CACHE_TTL seconds."""
        import time
        now = time.time()
        cached = self._cache.get(symbol)
        if not force_refresh and cached and (now - cached["ts"]) < self.CACHE_TTL:
            return cached["total"]

        result = (
            self.client.table("reserve_ledger")
            .select("amount")
            .eq("symbol", symbol)
            .eq("config_version", config_version)
            .eq("cycle", get_current_cycle(self.client, symbol))  # S96a: only current cycle
            .execute()
        )
        total = sum(float(r["amount"]) for r in (result.data or []))
        self._cache[symbol] = {"total": total, "ts": now}
        return total


class SentinelLogger:
    """Logs AI Sentinel analyses."""
    
    def __init__(self):
        self.client = get_client()
    
    # DEPRECATED — 'sentinel_logs' table does not exist, legacy from pre-S59
    def log_analysis(
        self,
        risk_score: int,
        opportunity_score: int,
        summary: str,
        action_taken: Optional[str] = None,
        news_sources: Optional[dict] = None,
        llm_model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0,
    ) -> dict:
        """Log a Sentinel analysis."""
        return None  # DEPRECATED: 'sentinel_logs' table removed pre-S59 — no-op guard
        data = {
            "risk_score": risk_score,
            "opportunity_score": opportunity_score,
            "summary": summary,
            "action_taken": action_taken,
            "news_sources": news_sources,
            "llm_model": llm_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
        
        result = self.client.table("sentinel_logs").insert(data).execute()
        return result.data[0] if result.data else {}
