"""
BagHolderAI - Force Daily Report (test script)
Triggers the private daily report immediately, without waiting for 20:00.
Also prints what the public report would look like.

Usage:
    cd /Volumes/Archivio/bagholderai && source venv/bin/activate
    python test_report.py
"""

import logging
from datetime import date, datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.test_report")

from config.settings import (
    HardcodedRules, GRID_INSTANCES,
)
from bot.exchange import create_exchange
from db.client import TradeLogger
from utils.telegram_notifier import SyncTelegramNotifier
from utils.formatting import fmt_price


def build_portfolio_summary(trade_logger, exchange) -> dict:
    """
    Build consolidated portfolio summary from DB + live prices.
    Same logic as grid_runner._build_portfolio_summary() after Session 12 fix.
    """
    initial_capital = HardcodedRules.MAX_CAPITAL

    total_invested_all = 0.0
    total_received_all = 0.0
    holdings_value = 0.0
    positions = []

    for inst in GRID_INSTANCES:
        pos = trade_logger.get_open_position(inst.symbol)
        h = pos["holdings"]
        total_invested_all += pos["total_invested"]
        total_received_all += pos["total_received"]

        if h > 0:
            try:
                ticker = exchange.fetch_ticker(inst.symbol)
                live_price = ticker["last"]
            except Exception as e:
                logger.warning(f"Failed to fetch price for {inst.symbol}: {e}")
                live_price = pos["avg_buy_price"]

            value = h * live_price
            unrealized = (live_price - pos["avg_buy_price"]) * h if pos["avg_buy_price"] > 0 else 0
            unrealized_pct = ((live_price / pos["avg_buy_price"]) - 1) * 100 if pos["avg_buy_price"] > 0 else 0
            holdings_value += value
            positions.append({
                "symbol": inst.symbol,
                "holdings": h,
                "value": value,
                "avg_buy_price": pos["avg_buy_price"],
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
                "realized_pnl": pos["realized_pnl"],
                "live_price": live_price,
            })

    cash = max(0.0, initial_capital - total_invested_all + total_received_all)
    total_value = cash + holdings_value
    total_pnl = total_value - initial_capital

    return {
        "total_value": total_value,
        "cash": cash,
        "holdings_value": holdings_value,
        "initial_capital": initial_capital,
        "total_pnl": total_pnl,
        "positions": positions,
    }


def main():
    logger.info("=" * 50)
    logger.info("BagHolderAI — Force Daily Report Test")
    logger.info("=" * 50)

    exchange = create_exchange()
    trade_logger = TradeLogger()
    notifier = SyncTelegramNotifier()

    # Build portfolio summary
    logger.info("Building portfolio summary from DB + live prices...")
    portfolio = build_portfolio_summary(trade_logger, exchange)

    # Get today's trades
    today_all_trades = trade_logger.get_today_trades()
    today_buys = sum(1 for t in today_all_trades if t.get("side") == "buy")
    today_sells = sum(1 for t in today_all_trades if t.get("side") == "sell")
    day_fees = sum(float(t.get("fee", 0)) for t in today_all_trades)
    day_realized = sum(
        float(t.get("realized_pnl", 0))
        for t in today_all_trades if t.get("realized_pnl")
    )

    # Enrich positions with today's trades
    for p in portfolio.get("positions", []):
        sym_trades = [t for t in today_all_trades if t.get("symbol") == p["symbol"]]
        p["trades_today"] = len(sym_trades)
        p["buys_today"] = sum(1 for t in sym_trades if t.get("side") == "buy")
        p["sells_today"] = sum(1 for t in sym_trades if t.get("side") == "sell")

    # Calculate day number
    day_number = 1
    try:
        first_trade_result = trade_logger.client.table("trades").select("created_at").order("created_at", desc=False).limit(1).execute()
        if first_trade_result.data:
            first_date_str = first_trade_result.data[0]["created_at"]
            first_date = datetime.fromisoformat(first_date_str.replace("Z", "+00:00")).date()
            day_number = (date.today() - first_date).days + 1
    except Exception:
        pass

    # 47e: include TF state so test_report mirrors what grid_runner sends.
    try:
        from commentary import get_tf_state
        tf_state = get_tf_state(trade_logger.client)
    except Exception as e:
        logger.warning(f"Could not fetch TF state: {e}")
        tf_state = None

    report_data = {
        **portfolio,
        "day_number": day_number,
        "today_trades_count": len(today_all_trades),
        "today_buys": today_buys,
        "today_sells": today_sells,
        "today_fees": day_fees,
        "today_realized": day_realized,
        "tf": tf_state,
    }

    # Print summary to console
    logger.info(f"\n{'=' * 40}")
    logger.info(f"Portfolio: ${portfolio['total_value']:.2f}")
    logger.info(f"Invested:  ${portfolio['initial_capital']:.2f}")
    logger.info(f"P&L:       ${portfolio['total_pnl']:+.2f}")
    logger.info(f"Cash:      ${portfolio['cash']:.2f}")
    logger.info(f"Holdings:  ${portfolio['holdings_value']:.2f}")
    logger.info(f"Day:       {day_number}")
    logger.info(f"Today:     {len(today_all_trades)} trades ({today_buys}B {today_sells}S)")
    for p in portfolio["positions"]:
        logger.info(f"  {p['symbol']}: ${p['value']:.2f} ({p['unrealized_pnl_pct']:+.1f}%)")
    logger.info(f"{'=' * 40}\n")

    # Verify numbers before sending
    if portfolio["initial_capital"] < 400:
        logger.error(f"SANITY CHECK FAILED: initial_capital is ${portfolio['initial_capital']:.2f} — expected ~$500")
        logger.error("The grid_runner._build_portfolio_summary() fix may not be applied yet.")
        return

    if portfolio["total_pnl"] > 100:
        logger.error(f"SANITY CHECK FAILED: total_pnl is ${portfolio['total_pnl']:+.2f} — we should be slightly negative")
        logger.error("Something is still wrong with the P&L calculation.")
        return

    logger.info("Sanity checks passed. Sending private report to Telegram...")

    # Send private report
    try:
        notifier.send_private_daily_report(report_data)
        logger.info("✅ Private report sent!")
    except Exception as e:
        logger.error(f"❌ Failed to send private report: {e}")

    # Send public report — same flow as 20:00 production
    logger.info("\n--- PUBLIC REPORT ---")
    try:
        result = notifier.send_public_daily_report(report_data)
        logger.info(f"Public report sent: {result}")
    except Exception as e:
        logger.warning(f"Public report failed: {e}")

    # 47e: public commentary follow-up — mirrors the full 20:00 production flow
    # (private → public → commentary echo). generate_daily_commentary returns
    # the text it just wrote; we forward that to send_public_commentary.
    try:
        from commentary import generate_daily_commentary
        commentary_text = generate_daily_commentary(report_data, trade_logger.client)
        if commentary_text:
            sent = notifier.send_public_commentary(commentary_text)
            logger.info(f"✅ Public commentary echoed: {sent}")
        else:
            logger.info("Commentary generation returned None — skipping public echo")
    except Exception as e:
        logger.warning(f"Public commentary echo failed: {e}")


if __name__ == "__main__":
    main()
