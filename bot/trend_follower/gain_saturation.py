"""
45g — Gain Saturation Circuit Breaker

Helpers for the "exit-after-N-positive-sells" filter. The check itself lives
in grid_bot.py alongside 39a/39c/45f; this module isolates the stateless
counter and the period-start lookup so they can be unit-tested in isolation.

Backtest rationale: see scripts/backtest_exit_after_n_positive_sells.py and
report_for_CEO/exit_after_n_positive_sells_proposal.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def get_period_start(supabase, symbol: str) -> Optional[datetime]:
    """
    Returns the scan_timestamp of the first ALLOCATE that opened the current
    TF management period for `symbol` — i.e. the first ALLOCATE strictly
    after the most recent DEALLOCATE on that symbol. If no DEALLOCATE
    exists, returns the first ALLOCATE ever for the symbol.

    Returns None if no ALLOCATE has been logged for this symbol — caller
    should treat this as "no period started, counter is 0".

    ALLOCATE-update events do NOT shift the period start: only the *first*
    ALLOCATE post-DEALLOCATE counts. This matches Max's intent: a rinforzo
    of an existing allocation must not reset the saturation counter.
    """
    try:
        last_dealloc = (
            supabase.table("trend_decisions_log")
            .select("scan_timestamp")
            .eq("symbol", symbol)
            .eq("action_taken", "DEALLOCATE")
            .order("scan_timestamp", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    q = (
        supabase.table("trend_decisions_log")
        .select("scan_timestamp")
        .eq("symbol", symbol)
        .eq("action_taken", "ALLOCATE")
        .order("scan_timestamp")
        .limit(1)
    )
    if last_dealloc.data:
        q = q.gt("scan_timestamp", last_dealloc.data[0]["scan_timestamp"])

    try:
        res = q.execute()
    except Exception:
        return None

    if not res.data:
        return None

    ts = res.data[0]["scan_timestamp"]
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def count_positive_sells_since(supabase, symbol: str, since: datetime) -> int:
    """
    Count TF-managed sells with realized_pnl > 0 on `symbol` since `since`.
    Stateless — the source of truth is the trades table.
    """
    try:
        res = (
            supabase.table("trades")
            .select("id", count="exact")
            .eq("symbol", symbol)
            .eq("managed_by", "trend_follower")
            .eq("side", "sell")
            .gt("realized_pnl", 0)
            .gte("created_at", since.isoformat())
            .execute()
        )
        return int(res.count or 0)
    except Exception:
        return 0


def resolve_effective_n(global_default: int, per_coin_override: Optional[int]) -> int:
    """
    Per-coin override wins; otherwise the global trend_config default.
    Documented here so the precedence is visible in one place.
    """
    if per_coin_override is not None:
        return int(per_coin_override)
    return int(global_default)


