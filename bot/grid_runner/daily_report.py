"""Daily 20:00 Telegram report builder + sender.

Triggered once per day per orchestrator. The atomic INSERT on
`daily_pnl_snapshots` decides who wins: the first bot to insert sends the
Telegram report (private + public + Haiku commentary), the others skip.

Refactor S76 (2026-05-14): extracted from grid_runner.py main loop.
"""

import logging
from datetime import datetime, date

from commentary import generate_daily_commentary, get_tf_state
from config.settings import GRID_INSTANCES

logger = logging.getLogger("bagholderai.runner")


def maybe_send_daily_report(
    bot,
    cfg,
    trade_logger,
    exchange,
    reserve_ledger,
    pnl_tracker,
    notifier,
    daily_report_sent,
    report_hour: int,
    build_portfolio_summary,
):
    """If the local clock has crossed `report_hour` and today's report
    hasn't been sent yet, build and dispatch the daily Telegram report.

    Returns the new `daily_report_sent` (today's date) on attempt, or the
    original value when the hour gate is not yet open.

    `build_portfolio_summary` is injected (rather than imported) to avoid
    circular dependency with the legacy `_build_portfolio_summary` still
    living in grid_runner's main loop module.
    """
    now = datetime.now()
    if not (now.hour >= report_hour and daily_report_sent != date.today()):
        return daily_report_sent

    # Set flag immediately so even if the send fails we don't send twice
    daily_report_sent = date.today()
    try:
        # Build consolidated portfolio from DB + live prices
        portfolio_summary = build_portfolio_summary(
            trade_logger, exchange, bot, cfg.symbol
        )

        # Get today's trades for ALL symbols
        today_all_trades = trade_logger.get_today_trades(config_version="v3") if trade_logger else []
        today_buys = sum(1 for t in today_all_trades if t.get("side") == "buy")
        today_sells = sum(1 for t in today_all_trades if t.get("side") == "sell")
        day_fees = sum(float(t.get("fee", 0)) for t in today_all_trades)
        day_realized = sum(
            float(t.get("realized_pnl", 0))
            for t in today_all_trades if t.get("realized_pnl")
        )

        # Enrich positions with today's trade counts + grid info
        for p in portfolio_summary.get("positions", []):
            sym_trades = [t for t in today_all_trades if t.get("symbol") == p["symbol"]]
            p["trades_today"] = len(sym_trades)
            p["buys_today"] = sum(1 for t in sym_trades if t.get("side") == "buy")
            p["sells_today"] = sum(1 for t in sym_trades if t.get("side") == "sell")
            # Grid info only available for this bot's symbol
            if p["symbol"] == cfg.symbol:
                status = bot.get_status()
                p["grid_range"] = status.get("range", "N/A")
                p["grid_active_buys"] = status.get("levels", {}).get("active_buys", 0)
                p["grid_active_sells"] = status.get("levels", {}).get("active_sells", 0)

        # Calculate trading day number
        day_number = 1
        try:
            first_trade_result = trade_logger.client.table("trades").select("created_at").order("created_at", desc=False).limit(1).execute()
            if first_trade_result.data:
                first_date_str = first_trade_result.data[0]["created_at"]
                first_date = datetime.fromisoformat(first_date_str.replace("Z", "+00:00")).date()
                day_number = (date.today() - first_date).days + 1
        except Exception:
            pass

        # Fetch reserve totals for all symbols (fresh for daily report)
        reserves = {}
        if reserve_ledger:
            for inst in GRID_INSTANCES:
                try:
                    reserves[inst.symbol] = reserve_ledger.get_reserve_total(
                        inst.symbol, force_refresh=True
                    )
                except Exception:
                    reserves[inst.symbol] = 0.0

        # Fetch TF state for inclusion in the daily reports.
        # Same source-of-truth used by Haiku commentary + tf.html
        # so private/public report numbers stay coherent with the
        # web dashboard. Never raises — returns safe_default on
        # any DB error.
        tf_state = get_tf_state(trade_logger.client)

        # Bundle all report data
        report_data = {
            **portfolio_summary,
            "day_number": day_number,
            "today_trades_count": len(today_all_trades),
            "today_buys": today_buys,
            "today_sells": today_sells,
            "today_fees": day_fees,
            "today_realized": day_realized,
            "reserves": reserves,
            "tf": tf_state,  # 47e: TF section in daily reports
        }

        # Atomic write: INSERT ON CONFLICT DO NOTHING.
        # Only the first bot to insert wins (returns True). The second gets False → skip.
        snapshot_written = False
        if pnl_tracker:
            snapshot_positions = []
            for p in portfolio_summary.get("positions", []):
                snapshot_positions.append({
                    "symbol": p["symbol"],
                    "holdings": p["holdings"],
                    "value": round(p["value"], 4),
                    "avg_buy_price": p["avg_buy_price"],
                    "unrealized_pnl": round(p["unrealized_pnl"], 4),
                    "unrealized_pnl_pct": round(p.get("unrealized_pnl_pct", 0), 2),
                })
            snapshot_written = pnl_tracker.record_daily(
                total_value=portfolio_summary["total_value"],
                cash_remaining=portfolio_summary["cash"],
                holdings_value=portfolio_summary["holdings_value"],
                initial_capital=portfolio_summary["initial_capital"],
                total_pnl=portfolio_summary["total_pnl"],
                realized_pnl_today=day_realized,
                total_fees_today=day_fees,
                trades_count=len(today_all_trades),
                buys_count=today_buys,
                sells_count=today_sells,
                positions=snapshot_positions,
            )

        if not pnl_tracker or snapshot_written:
            # Send reports only if we were first to write (or no tracker)
            notifier.send_private_daily_report(report_data)
            notifier.send_public_daily_report(report_data)
            # Generate Haiku commentary; capture the text so we can
            # echo it on the public channel as a CEO's-Log follow-up
            # (same content that lands on bagholderai.lol/dashboard).
            commentary_text = generate_daily_commentary(report_data, trade_logger.client)
            if commentary_text:
                notifier.send_public_commentary(commentary_text)
            logger.info("Daily P&L snapshot saved + report sent via Telegram.")
        else:
            logger.info("Daily snapshot already written by another bot. Skipping report.")
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")

    return daily_report_sent
