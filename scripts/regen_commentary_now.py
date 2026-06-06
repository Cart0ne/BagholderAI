"""
One-shot manual trigger for the daily Haiku commentary ONLY (no Telegram).

Use case (S97b): after fixing the cycle filter / day-count, regenerate today's
commentary so the dashboard CEO-log shows clean-slate-correct numbers. Inserts
a fresh row into daily_commentary; the dashboard dedupes per date keeping the
latest created_at, so this overwrites today's stale entry on the public page
WITHOUT re-sending the daily report to the Telegram channels.

Mirrors the report_data shape that bot/grid_runner/daily_report.py builds, but
calls generate_daily_commentary instead of the notifier.

Usage (from repo root, Mac Mini):
    ./venv/bin/python3.13 scripts/regen_commentary_now.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.client import get_client, get_current_cycle
from commentary import (
    generate_daily_commentary,
    get_grid_state,
    get_cycle_start_date,
)


def main():
    sb = get_client()
    cycle = get_current_cycle(sb)
    cycle_start = get_cycle_start_date(sb, cycle)

    # === Grid state (cycle-filtered, single source of truth) ===
    grid_state = get_grid_state(sb)

    # === Today's Grid activity (current cycle only) ===
    today_iso = date.today().isoformat()
    today_all = (
        sb.table("trades")
        .select("symbol, side, realized_pnl, fee, created_at, managed_by, cycle")
        .gte("created_at", f"{today_iso}T00:00:00")
        .eq("cycle", cycle)
        .execute()
        .data or []
    )
    grid_today = [t for t in today_all if t.get("managed_by") == "grid"]
    today_buys = sum(1 for t in grid_today if t.get("side") == "buy")
    today_sells = sum(1 for t in grid_today if t.get("side") == "sell")
    day_realized = sum(float(t.get("realized_pnl") or 0) for t in grid_today)
    day_fees = sum(float(t.get("fee") or 0) for t in grid_today)

    day_number = (date.today() - cycle_start).days + 1

    # Per-coin today counts (mirror daily_report enrichment)
    for p in grid_state.get("positions", []):
        sym = p["symbol"]
        sym_today = [t for t in grid_today if t.get("symbol") == sym]
        p["trades_today"] = len(sym_today)
        p["buys_today"] = sum(1 for t in sym_today if t.get("side") == "buy")
        p["sells_today"] = sum(1 for t in sym_today if t.get("side") == "sell")

    report_data = {
        **grid_state,
        "day_number": day_number,
        "today_trades_count": len(grid_today),
        "today_buys": today_buys,
        "today_sells": today_sells,
        "today_fees": day_fees,
        "today_realized": day_realized,
    }

    print(f"Cycle={cycle} · start={cycle_start} · Day {day_number}")
    print(f"Grid net worth ${grid_state.get('total_value')} · "
          f"P&L ${grid_state.get('total_pnl')}")
    print("Generating Haiku commentary (no Telegram)...")
    text = generate_daily_commentary(report_data, sb)
    if text:
        print("\n--- COMMENTARY ---")
        print(text)
        print("------------------")
        print("Saved to daily_commentary. Dashboard will show it on next load.")
    else:
        print("FAILED — generate_daily_commentary returned None (check API key / logs).")


if __name__ == "__main__":
    main()
