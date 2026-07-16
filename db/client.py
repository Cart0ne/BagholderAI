"""
BagHolderAI - Database Client
Handles all Supabase interactions: logging trades, updating portfolio, etc.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from config.settings import DatabaseConfig


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
        # S119: public/global cycle = venue='binance' canonical (fallback: all
        # tagged rows, so a hypothetical binance-less DB still resolves).
        binance = [r for r in tagged if (r.get("venue") or "binance") == "binance"]
        canonical = binance or tagged
        active = [r for r in canonical if r.get("is_active")]
        pool = active or canonical
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

        result = self.client.table("trades").insert(data).execute()
        return result.data[0] if result.data else {}
    
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

        # Use ignore_duplicates=True so only the first bot to insert wins.
        # If the row already exists (another bot beat us), result.data is empty → return False.
        result = (
            self.client.table("daily_pnl")
            .upsert(data, on_conflict="date", ignore_duplicates=True)
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

    CACHE_TTL = 300  # seconds

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
