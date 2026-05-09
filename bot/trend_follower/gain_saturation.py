"""
45g — Gain Saturation Circuit Breaker

Helpers for the "exit-after-N-positive-sells" filter. Two checks exist:
- Post-sell: inside grid_bot.check_price_and_execute, fires after a positive
  sell pushes the counter to N. Covers the "organic" trigger path.
- Proactive (49b): runs at tick start in grid_runner. Covers coins that
  already have counter >= N at deploy time, or whose holdings hit 0 before
  the post-sell check could fire (the "ALGO scenario": closed cycle, no
  pending sells, but counter pre-existing).

Both check paths are guarded by the in-memory `_gain_saturation_triggered`
flag so they're idempotent.

Backtest rationale: see scripts/backtest_exit_after_n_positive_sells.py and
report_for_CEO/exit_after_n_positive_sells_proposal.md.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
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
            .eq("managed_by", "tf")
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


# Proactive check cooldown — see brief 49b §3.3. The proactive check could
# in principle run every tick (~60s), which on 30 TF bots would be 30
# unnecessary count queries/min. 5 min is plenty: TF management decisions
# do not have second-level urgency. Cleared on bot restart by design (the
# first post-restart tick re-runs the check, see brief §3.6).
PROACTIVE_CHECK_INTERVAL_S = 300

_last_proactive_check: dict = {}  # symbol -> epoch seconds


def should_run_proactive_check(symbol: str, interval_s: int = PROACTIVE_CHECK_INTERVAL_S) -> bool:
    """
    Rate-limit the proactive saturation check per symbol. Returns True the
    first time it's called for a symbol within `interval_s` seconds, then
    False until the cooldown elapses. Updates the timestamp on the True
    branch so subsequent calls in the same window return False.
    """
    now = time.time()
    last = _last_proactive_check.get(symbol, 0.0)
    if now - last >= interval_s:
        _last_proactive_check[symbol] = now
        return True
    return False
