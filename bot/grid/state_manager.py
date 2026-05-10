"""
BagHolderAI - State manager (Phase 1 split from grid_bot.py).

Boot-time state restoration from DB.

Brief s70 FASE 2 (2026-05-09): la legacy FIFO queue replay è stata
rimossa, e la legacy `restore_state_from_db` (fixed-mode v1) è stata
rimossa insieme al cleanup completo del fixed-mode (vedi commit 9).
Avg-cost trading consulta solo state.avg_buy_price e state.holdings.
"""

import logging
from datetime import datetime, timezone
from utils.formatting import fmt_price

logger = logging.getLogger("bagholderai.grid")


def init_avg_cost_state_from_db(bot):
    """
    Restore avg-cost percentage-mode state from DB on startup.

    Replays all v3 trades for this symbol chronologically and recomputes:
    - state.holdings (qty_canonical)
    - state.avg_buy_price (running weighted average; reset to 0 on full sell)
    - state.realized_pnl (sum of (sell_price - avg_at_sell) × sell_qty)
    - state.total_invested, state.total_received
    - bot._pct_last_buy_price (price del trade buy più recente)
    - bot._last_trade_time (timestamp del trade più recente, per idle path)

    Brief s70 FASE 2: niente più FIFO queue replay. La queue era usata
    per guidare il Strategy A trigger per-lot pre-S70; con avg-cost
    trading il trigger guarda solo state.avg_buy_price.
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
        logger.warning(f"[{bot.symbol}] Could not load avg-cost state from DB: {e}")
        return

    last_buy_price = 0.0
    last_sell_price = 0.0  # Brief 70a Parte 3: sell ladder reference (Grid manual)
    total_invested = 0.0
    total_received = 0.0
    avg = 0.0
    qty = 0.0
    realized = 0.0

    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        cost = float(t.get("cost") or (amount * price))
        if side == "buy":
            total_invested += cost
            last_buy_price = price
            new_qty = qty + amount
            if new_qty > 0:
                avg = (avg * qty + price * amount) / new_qty
            qty = new_qty
        elif side == "sell":
            revenue = amount * price
            total_received += revenue
            if qty > 1e-12:
                realized += (price - avg) * amount
                qty -= amount
                if qty <= 1e-9:
                    qty = 0.0
                    avg = 0.0  # reset on full sell-out
                    last_sell_price = 0.0  # 70a: reset ladder on full exit
                else:
                    last_sell_price = price  # 70a: partial sell → next ladder step

    bot._pct_last_buy_price = last_buy_price
    bot._last_sell_price = last_sell_price

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
                # writing to DB; this re-init must not clobber that.
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
        bot.state.holdings = qty
        bot.state.avg_buy_price = avg
        bot.state.realized_pnl = realized

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

    last_sell_log = (
        f", last sell {fmt_price(last_sell_price)} (ladder active)"
        if last_sell_price > 0 else ""
    )
    logger.info(
        f"[{bot.symbol}] Avg-cost state restored: holdings={bot.state.holdings:.6f}, "
        f"avg_buy={fmt_price(bot.state.avg_buy_price)}, "
        f"realized=${bot.state.realized_pnl:.4f}, "
        f"last buy {fmt_price(last_buy_price)}{last_sell_log}"
    )
    logger.info(
        f"[{bot.symbol}] Cash restored: ${bot.capital:.2f} allocated"
        f" - ${total_invested:.2f} invested"
        f" + ${total_received:.2f} sold"
        f"{reserve_str}"
        f" = ${available:.2f} available"
    )
