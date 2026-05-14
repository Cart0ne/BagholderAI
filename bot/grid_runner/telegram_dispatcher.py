"""Telegram message builders for grid lifecycle events.

Currently hosts the TF DEALLOCATE cycle summary (39e Fix 3). The summary
queries `trend_decisions_log` for the most recent ALLOCATE and aggregates
all trades in that window — split into grid PnL vs exit-liquidation PnL,
with skim totals from `reserve_ledger`.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
These helpers are pure renderers/builders — they don't decide *whether*
to send; that policy lives at the call site (typically `liquidation.py`).
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("bagholderai.runner")


def _build_cycle_summary(supabase, symbol: str, liquidation_trade_id: str | None) -> dict | None:
    """Build a per-cycle summary for the TF DEALLOCATE notification (39e Fix 3).

    A "cycle" is the window between the most recent ALLOCATE for this symbol
    in trend_decisions_log and NOW. Returns a dict with all fields needed to
    render the summary, or None if anything fails (caller falls back to the
    minimal LIQUIDATED message).

    liquidation_trade_id: id of the FORCED_LIQUIDATION sell row just written,
    used to split grid vs exit PnL and find the liquidation's skim row.
    """
    if supabase is None:
        return None
    try:
        last_alloc = (
            supabase.table("trend_decisions_log")
            .select("scan_timestamp,reason,config_written")
            .eq("symbol", symbol)
            .eq("action_taken", "ALLOCATE")
            .eq("is_shadow", False)
            .order("scan_timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not last_alloc.data:
            return None
        cycle_start = last_alloc.data[0]["scan_timestamp"]
        alloc_snapshot = last_alloc.data[0].get("config_written") or {}
        initial_capital = float(alloc_snapshot.get("capital_allocation") or 0)
        cycle_end_iso = datetime.now(timezone.utc).isoformat()

        trades_res = (
            supabase.table("trades")
            .select("id,side,amount,cost,realized_pnl,created_at,reason")
            .eq("symbol", symbol)
            .eq("config_version", "v3")
            .gte("created_at", cycle_start)
            .order("created_at", desc=False)
            .execute()
        )
        cycle_trades = trades_res.data or []
        buys = [t for t in cycle_trades if t.get("side") == "buy"]
        sells = [t for t in cycle_trades if t.get("side") == "sell"]

        realized_pnl_total = sum(float(t.get("realized_pnl") or 0) for t in sells)
        # Split: the liquidation row (matched by id) vs everything else.
        liquidation_pnl = 0.0
        grid_pnl = 0.0
        for t in sells:
            p = float(t.get("realized_pnl") or 0)
            if liquidation_trade_id and t.get("id") == liquidation_trade_id:
                liquidation_pnl += p
            else:
                grid_pnl += p

        sell_ids = [t["id"] for t in sells if t.get("id")]
        skim_total = 0.0
        if sell_ids:
            try:
                skim_res = (
                    supabase.table("reserve_ledger")
                    .select("amount,trade_id")
                    .in_("trade_id", sell_ids)
                    .execute()
                )
                skim_total = sum(float(r.get("amount") or 0) for r in (skim_res.data or []))
            except Exception as e:
                logger.warning(f"[{symbol}] cycle summary: skim query failed: {e}")

        return {
            "cycle_start": cycle_start,
            "cycle_end": cycle_end_iso,
            "initial_capital": initial_capital,
            "buys_count": len(buys),
            "sells_count": len(sells),
            "realized_pnl": realized_pnl_total,
            "grid_pnl": grid_pnl,
            "liquidation_pnl": liquidation_pnl,
            "skim_total": skim_total,
        }
    except Exception as e:
        logger.warning(f"[{symbol}] cycle summary build failed: {e}")
        return None


def _format_cycle_summary(s: dict) -> str:
    """Render a cycle summary dict into the Telegram message block (39e Fix 3)."""
    try:
        start = datetime.fromisoformat(s["cycle_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(s["cycle_end"].replace("Z", "+00:00"))
        duration = end - start
        total_minutes = int(duration.total_seconds() // 60)
        hours = total_minutes // 60
        mins = total_minutes % 60
        duration_str = f"{hours}h {mins}m" if hours else f"{mins}m"
        window = f"{start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({duration_str})"
    except Exception:
        window = "—"

    realized = s["realized_pnl"]
    grid = s["grid_pnl"]
    liq = s["liquidation_pnl"]
    skim = s["skim_total"]
    net = realized - skim
    alloc = s["initial_capital"]
    returned = alloc + realized

    def money(v: float) -> str:
        # Render as "+$1.21" / "-$1.21" (sign before $, standard accounting).
        return f"{'+' if v >= 0 else '-'}${abs(v):.2f}"

    def pct(v: float) -> str:
        return f"{'+' if v >= 0 else ''}{v:.1f}%"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"Cycle: {window}",
        f"Trades: {s['buys_count']} buys · {s['sells_count']} sells",
        f"Realized P&L: {money(realized)}",
    ]
    # Only show the split when both components are meaningful (avoid a
    # single-line breakdown that adds noise). grid_pnl and liquidation_pnl
    # are independent sums; we consider each "present" if its magnitude is
    # above a cent, to filter out rounding artefacts.
    if abs(grid) >= 0.01 and abs(liq) >= 0.01:
        lines.append(f"  ├─ Grid profits:     {money(grid)}")
        lines.append(f"  └─ Exit liquidation: {money(liq)}")
    lines.append(f"Skimmed to reserve: {money(skim)}")
    lines.append(f"Net to trading pool: {money(net)}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if alloc > 0:
        pct_val = (realized / alloc) * 100
        lines.append(
            f"Allocated: ${alloc:.2f} → Returned: ${returned:.2f} ({pct(pct_val)})"
        )
    return "\n".join(lines)
