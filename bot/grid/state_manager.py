"""
BagHolderAI - State manager (Phase 1 split from grid_bot.py).

Boot-time state restoration from DB:
- restore_state_from_db: fixed-mode legacy path (v1).
- init_percentage_state_from_db: percentage-mode FIFO replay (v3).

Both functions mutate `bot.state` and `bot._pct_open_positions` /
`bot._pct_last_buy_price` in place. They preserve identical behaviour to
the original methods on GridBot.
"""

import logging
from datetime import datetime, timezone
from utils.formatting import fmt_price

logger = logging.getLogger("bagholderai.grid")


def restore_state_from_db(bot):
    """
    Restore holdings, avg_buy_price, and P&L from historical trades in DB.
    Call after setup_grid() on startup to recover v1 positions.
    """
    if not bot.trade_logger or not bot.state:
        return

    pos = bot.trade_logger.get_open_position(bot.symbol)
    if pos["holdings"] <= 0:
        logger.info(f"No open position found in DB for {bot.symbol}.")
        return

    bot.state.holdings = pos["holdings"]
    bot.state.avg_buy_price = pos["avg_buy_price"]
    bot.state.realized_pnl = pos["realized_pnl"]
    bot.state.total_fees = pos["total_fees"]
    bot.state.total_invested = pos["total_invested"]
    bot.state.total_received = pos["total_received"]

    # Distribute recovered holdings across sell levels
    sell_levels = [l for l in bot.state.levels if l.side == "sell"]
    if sell_levels:
        amount_per_level = bot.state.holdings / len(sell_levels)
        for sl in sell_levels:
            sl.order_amount = round(amount_per_level, 8)

    logger.info(
        f"Restored from DB: {pos['holdings']:.6f} {bot.symbol} "
        f"@ avg {fmt_price(pos['avg_buy_price'])} | "
        f"Realized P&L: ${pos['realized_pnl']:.4f}"
    )


def init_percentage_state_from_db(bot):
    """
    Restore percentage mode state from DB on startup.
    Reconstructs the FIFO open-positions queue, last buy price,
    and cash accounting (total_invested / total_received) by replaying
    all v3 trades for this symbol chronologically.
    """
    if not bot.trade_logger:
        return
    try:
        result = (
            bot.trade_logger.client.table("trades")
            .select("side,amount,price,cost,created_at")
            .eq("symbol", bot.symbol)
            .eq("config_version", "v3")
            .order("created_at", desc=False)
            .execute()
        )
        trades = result.data or []
    except Exception as e:
        logger.warning(f"[{bot.symbol}] Could not load pct state from DB: {e}")
        return

    # 66a (Operation Clean Slate): two parallel replay tracks.
    #   1. FIFO queue       → drives Strategy A trigger (lot_buy_price)
    #   2. Canonical avg    → drives state.avg_buy_price + state.realized_pnl
    # Both must be aligned with what the bot would have at runtime if it
    # had never restarted. Pre-66a code derived avg from the FIFO residual
    # queue, which after multi-lot sells produced a different avg from the
    # one the bot mantained at runtime — feeding the +29% bias documented
    # in audits/2026-05-08_pre-clean-slate/formula_verification_s66.md.
    open_positions = []
    last_buy_price = 0.0
    total_invested = 0.0
    total_received = 0.0
    avg_canonical = 0.0
    qty_canonical = 0.0
    realized_pnl_replay = 0.0

    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        cost = float(t.get("cost") or (amount * price))
        if side == "buy":
            total_invested += cost
            open_positions.append({"amount": amount, "price": price})
            last_buy_price = price
            # Canonical avg update on buy (weighted average).
            new_qty = qty_canonical + amount
            if new_qty > 0:
                avg_canonical = (
                    (avg_canonical * qty_canonical + price * amount) / new_qty
                )
            qty_canonical = new_qty
        elif side == "sell":
            revenue = amount * price
            total_received += revenue
            # Canonical realized: (sell_price - avg) × sell_qty.
            # avg does NOT change on sell.
            if qty_canonical > 1e-12:
                realized_pnl_replay += (price - avg_canonical) * amount
                qty_canonical -= amount
                if qty_canonical <= 1e-9:
                    qty_canonical = 0.0
                    avg_canonical = 0.0  # reset on full sell-out
            # FIFO queue consume (oldest first) — for Strategy A trigger.
            if open_positions:
                remaining = amount
                while remaining > 1e-12 and open_positions:
                    oldest = open_positions[0]
                    if oldest["amount"] <= remaining + 1e-12:
                        remaining -= oldest["amount"]
                        open_positions.pop(0)
                    else:
                        oldest["amount"] -= remaining
                        remaining = 0

    bot._pct_open_positions = open_positions
    bot._pct_last_buy_price = last_buy_price

    # Restore last trade time so idle re-entry countdown is correct.
    # Convert to UTC-naive so comparison with datetime.utcnow() is always correct
    # regardless of the timezone offset stored in the DB timestamp.
    if trades:
        try:
            dt_str = trades[-1].get("created_at", "")
            if dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                # Only overwrite if DB value is newer than in-memory value.
                # The idle-recalibrate path sets _last_trade_time = utcnow() without
                # writing to DB; the self-heal re-init must not clobber that.
                if bot._last_trade_time is None or dt > bot._last_trade_time:
                    bot._last_trade_time = dt
                    bot._idle_logged_hour = -1  # reset so first eval logs immediately
                    logger.info(f"[{bot.symbol}] Restored _last_trade_time = {dt:%Y-%m-%d %H:%M:%S} UTC")
                else:
                    logger.info(
                        f"[{bot.symbol}] DB _last_trade_time ({dt:%Y-%m-%d %H:%M:%S}) "
                        f"older than in-memory ({bot._last_trade_time:%Y-%m-%d %H:%M:%S}), keeping in-memory"
                    )
        except Exception:
            pass
    else:
        logger.info(f"[{bot.symbol}] No v3 trades found — _last_trade_time stays None")

    # Reconstruct cash accounting + holdings so sell logic fires correctly
    if bot.state:
        bot.state.total_invested = total_invested
        bot.state.total_received = total_received

        # 66a: holdings + avg_buy_price come from canonical replay (not
        # from the FIFO residual queue). Sanity-check the two should
        # match within tolerance — if not, log a warning (data drift).
        bot.state.holdings = qty_canonical
        bot.state.avg_buy_price = avg_canonical
        bot.state.realized_pnl = realized_pnl_replay

        if open_positions:
            queue_total = sum(lot["amount"] for lot in open_positions)
            if abs(queue_total - qty_canonical) > 1e-6:
                logger.warning(
                    f"[{bot.symbol}] FIFO queue / canonical qty desync: "
                    f"queue_total={queue_total:.8f} vs canonical={qty_canonical:.8f} "
                    f"(diff={queue_total - qty_canonical:+.8f}). "
                    f"Trusting canonical for state.holdings."
                )

    available = bot.capital - total_invested + total_received
    reserve_str = ""
    if bot.reserve_ledger:
        try:
            reserve = bot.reserve_ledger.get_reserve_total(bot.symbol)
            if reserve > 0:
                available -= reserve
                reserve_str = f" - ${reserve:.2f} reserve"
        except Exception as e:
            logger.warning(f"[{bot.symbol}] Could not fetch reserve total for cash log: {e}")

    logger.info(
        f"[{bot.symbol}] Pct mode restored: {len(open_positions)} open lots, "
        f"holdings={bot.state.holdings:.6f}, "
        f"avg_buy={fmt_price(bot.state.avg_buy_price)}, "
        f"last buy {fmt_price(last_buy_price)}"
    )
    logger.info(
        f"[{bot.symbol}] Cash restored: ${bot.capital:.2f} allocated"
        f" - ${total_invested:.2f} invested"
        f" + ${total_received:.2f} sold"
        f"{reserve_str}"
        f" = ${available:.2f} available"
    )
