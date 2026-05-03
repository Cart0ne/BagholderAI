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

import ccxt

from db.client import TradeLogger, ReserveLedger, get_client
from utils.telegram_notifier import SyncTelegramNotifier
from commentary import get_tf_state


def main():
    sb = get_client()
    trade_logger = TradeLogger()
    reserve_ledger = ReserveLedger()
    notifier = SyncTelegramNotifier()

    # === Pull live state ===
    # Today's Grid trades (manual bots only — exclude TF + tf_grid since
    # the report bundle keeps them separate via the `tf` block).
    # Brief 46b: tf_grid coins are TF-funded, so they belong in the TF
    # totals, NOT in the Grid totals — filter them out here.
    today_iso = date.today().isoformat()
    grid_trades_today = (
        sb.table("trades")
        .select("symbol, side, realized_pnl, fee, created_at, managed_by")
        .gte("created_at", f"{today_iso}T00:00:00")
        .execute()
        .data or []
    )
    grid_today = [t for t in grid_trades_today if t.get("managed_by") == "manual"]

    today_buys = sum(1 for t in grid_today if t.get("side") == "buy")
    today_sells = sum(1 for t in grid_today if t.get("side") == "sell")
    day_realized = sum(float(t.get("realized_pnl") or 0) for t in grid_today)
    day_fees = sum(float(t.get("fee") or 0) for t in grid_today)

    # === Build per-coin Grid positions from bot_config (manual bots only) ===
    # Brief 46b: tf_grid coins are TF-funded → must NOT show up in Grid
    # totals. Strict equality on 'manual' (the prior !=trend_follower
    # filter incorrectly included tf_grid).
    manual_cfgs = (
        sb.table("bot_config")
        .select("*")
        .eq("managed_by", "manual")
        .eq("is_active", True)
        .execute()
        .data or []
    )

    # Live prices via ccxt (binance public)
    exchange = ccxt.binance()
    exchange.set_sandbox_mode(False)

    positions = []
    holdings_value = 0.0
    cash_used_in_holdings = 0.0
    for cfg in manual_cfgs:
        sym = cfg["symbol"]
        try:
            ticker = exchange.fetch_ticker(sym)
            live_price = float(ticker["last"])
        except Exception as e:
            print(f"  [warn] could not fetch {sym} live price: {e}")
            live_price = 0.0

        pos = trade_logger.get_open_position(sym, config_version="v3")
        holdings = pos["holdings"]
        avg_buy = pos["avg_buy_price"]
        realized_pnl = pos["realized_pnl"]
        value = holdings * live_price
        unrealized = (live_price - avg_buy) * holdings if avg_buy > 0 else 0.0
        unrealized_pct = ((live_price / avg_buy - 1) * 100) if avg_buy > 0 else 0.0

        coin_today = [t for t in grid_today if t.get("symbol") == sym]
        coin_buys_today = sum(1 for t in coin_today if t.get("side") == "buy")
        coin_sells_today = sum(1 for t in coin_today if t.get("side") == "sell")

        positions.append({
            "symbol": sym,
            "holdings": round(holdings, 8),
            "avg_buy_price": round(avg_buy, 8),
            "value": round(value, 4),
            "unrealized_pnl": round(unrealized, 4),
            "unrealized_pnl_pct": round(unrealized_pct, 2),
            "realized_pnl": round(realized_pnl, 4),
            "trades_today": len(coin_today),
            "buys_today": coin_buys_today,
            "sells_today": coin_sells_today,
        })
        holdings_value += value
        cash_used_in_holdings += holdings * avg_buy

    # === Aggregate cash + totals ===
    grid_initial = sum(float(c.get("capital_allocation") or 0) for c in manual_cfgs)
    # cash = capital_allocation totals - cost basis of currently held positions
    # + net realized (rough — same shape as orchestrator does it)
    total_realized_grid = sum(p["realized_pnl"] for p in positions)
    cash = grid_initial - cash_used_in_holdings + total_realized_grid
    total_value_grid = cash + holdings_value
    total_pnl_grid = total_value_grid - grid_initial

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

    # === Reserves ===
    reserves = {}
    for cfg in manual_cfgs:
        sym = cfg["symbol"]
        try:
            reserves[sym] = reserve_ledger.get_reserve_total(sym, force_refresh=True)
        except Exception:
            reserves[sym] = 0.0

    report_data = {
        "total_value": total_value_grid,
        "initial_capital": grid_initial,
        "total_pnl": total_pnl_grid,
        "cash": cash,
        "holdings_value": holdings_value,
        "positions": positions,
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
