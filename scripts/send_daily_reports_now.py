"""
One-shot manual trigger for the private + public daily reports.

Use case: after a UI/format change to telegram_notifier.py, fire the reports
on demand without waiting for the next 20:00 cycle. Skips the daily_pnl
snapshot write (already done today by the orchestrator's regular run).

Usage (from repo root):
    venv/bin/python3.13 scripts/send_daily_reports_now.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.client import ReserveLedger, get_client
from utils.telegram_notifier import SyncTelegramNotifier
from commentary import get_tf_state, get_grid_state


def main():
    sb = get_client()
    reserve_ledger = ReserveLedger()
    notifier = SyncTelegramNotifier()

    # === Grid state (single source of truth, identical to dashboard) ===
    # commentary.get_grid_state runs FIFO replay over Grid trades and returns
    # the same fields the legacy inline calc produced (plus realized/fees/
    # skim/unrealized aggregates) — see commentary.py for the formula.
    grid_state = get_grid_state(sb)

    # === Today's Grid activity (intra-day stats for the report header) ===
    today_iso = date.today().isoformat()
    grid_trades_today_all = (
        sb.table("trades")
        .select("symbol, side, realized_pnl, fee, created_at, managed_by")
        .gte("created_at", f"{today_iso}T00:00:00")
        .execute()
        .data or []
    )
    grid_today = [t for t in grid_trades_today_all if t.get("managed_by") == "grid"]
    today_buys = sum(1 for t in grid_today if t.get("side") == "buy")
    today_sells = sum(1 for t in grid_today if t.get("side") == "sell")
    day_realized = sum(float(t.get("realized_pnl") or 0) for t in grid_today)
    day_fees = sum(float(t.get("fee") or 0) for t in grid_today)

    # === TF state ===
    tf_state = get_tf_state(sb)

    # === Day number ===
    day_number = 1
    try:
        first_trade = (
            sb.table("trades")
            .select("created_at")
            .order("created_at")
            .limit(1)
            .execute()
            .data
        )
        if first_trade:
            first_dt = datetime.fromisoformat(
                first_trade[0]["created_at"].replace("Z", "+00:00")
            ).date()
            day_number = (date.today() - first_dt).days + 1
    except Exception:
        pass

    # === Reserves (per-coin breakdown for the "🏦 Grid Reserve" footer) ===
    reserves = {}
    for p in grid_state.get("positions", []):
        sym = p["symbol"]
        try:
            reserves[sym] = reserve_ledger.get_reserve_total(sym, force_refresh=True)
        except Exception:
            reserves[sym] = 0.0

    # Enrich positions with today's trade counts (per-coin) — get_grid_state
    # already includes them, but we re-merge here in case the day boundary
    # crossed between the two queries.
    for p in grid_state["positions"]:
        sym = p["symbol"]
        sym_today = [t for t in grid_today if t.get("symbol") == sym]
        p["trades_today"] = len(sym_today)
        p["buys_today"] = sum(1 for t in sym_today if t.get("side") == "buy")
        p["sells_today"] = sum(1 for t in sym_today if t.get("side") == "sell")

    report_data = {
        **grid_state,  # total_value, cash, holdings_value, initial_capital,
                       # total_pnl, realized_total, unrealized_total,
                       # fees_total, skim_total, positions
        "day_number": day_number,
        "today_trades_count": len(grid_today),
        "today_buys": today_buys,
        "today_sells": today_sells,
        "today_fees": day_fees,
        "today_realized": day_realized,
        "reserves": reserves,
        "tf": tf_state,
    }

    # === Fire ===
    print("Sending PRIVATE daily report...")
    ok_priv = notifier.send_private_daily_report(report_data)
    print(f"  → {'OK' if ok_priv else 'FAILED'}")

    print("Sending PUBLIC daily report...")
    ok_pub = notifier.send_public_daily_report(report_data)
    print(f"  → {'OK' if ok_pub else 'FAILED'}")


if __name__ == "__main__":
    main()
