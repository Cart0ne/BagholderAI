"""
BagHolderAI - FIFO Queue helpers (Phase 1 split from grid_bot.py).

Phase 1 deviation note (62a):
The brief §3.1 proposed a `FIFOQueue` class wrapping `_pct_open_positions`.
For Phase 1 we only extract the verify/replay logic as functions and keep
`_pct_open_positions` as a plain list on `GridBot` — a class wrapper would
require touching 30+ read sites in the same commit, raising regression risk
beyond the Phase 1 mandate ("ZERO behaviour change"). The class will land in
Phase 2 alongside the dust + 60c fixes.

# TODO 62a (Phase 2): introduce FIFOQueue class wrapping _pct_open_positions.
"""

import logging
from typing import Optional
from db.event_logger import log_event

logger = logging.getLogger("bagholderai.grid")


def replay_trades_to_queue(trades: list) -> list:
    """Replay v3 trades into a fresh FIFO queue (no dust filter).

    Same logic used by both init_percentage_state_from_db (state_manager)
    and verify_fifo_queue (here) so the two are guaranteed to agree under
    no-drift conditions.

    Returns a new list of {"amount": float, "price": float} lots.
    """
    queue: list = []
    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        if side == "buy":
            queue.append({"amount": amount, "price": price})
        elif side == "sell":
            remaining = amount
            while remaining > 1e-12 and queue:
                oldest = queue[0]
                if oldest["amount"] <= remaining + 1e-12:
                    remaining -= oldest["amount"]
                    queue.pop(0)
                else:
                    oldest["amount"] -= remaining
                    remaining = 0
    return queue


def verify_fifo_queue(bot) -> bool:
    """Check the in-memory FIFO queue against DB truth and rebuild on drift.

    Re-runs the same replay as init_percentage_state_from_db (filter on
    symbol + config_version='v3') and compares lot-by-lot with
    bot._pct_open_positions. On mismatch: log to bot_events_log, send a
    Telegram alert, replace the queue with the DB-derived one, recalc
    holdings + avg_buy_price, return False. On match: return True.

    Never raises — DB errors degrade to "no verify" and return True so
    a transient Supabase blip can't take the bot down.
    """
    if not bot.trade_logger:
        return True

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
        logger.warning(f"[{bot.symbol}] FIFO verify failed (DB error): {e}")
        return True

    db_queue = replay_trades_to_queue(trades)

    # 57a hotfix v2: drop dust lots that would never be sellable on
    # the exchange. The runtime path already pops these in
    # _execute_percentage_sell after a step_size + MIN_NOTIONAL
    # rejection, but the DB still has the buy → replay rebuilds them.
    # Without this filter, verify_fifo_queue flags a permanent drift
    # on any symbol that ever had a partial-sell residual, looping
    # forever (Telegram spam every cycle).
    #
    # Use the symbol's actual MIN_NOTIONAL from exchange filters when
    # available (typically $5). Static $1 fallback only when filters
    # haven't loaded yet, never as the long-term value: a $3.79
    # SOL dust lot is sub-MIN_NOTIONAL ($5) but above $1, so the
    # static threshold misses it and the loop reappears.
    #
    # TODO 62a (Phase 2): mem_queue is NOT filtered for dust here, only
    # db_queue is — this is the spurious-drift source noted in the 60c
    # diagnosis. Filter both sides symmetrically in Phase 2.
    min_notional = float(
        (bot._exchange_filters or {}).get("min_notional") or 0
    )
    dust_threshold = min_notional if min_notional > 0 else 1.0
    db_queue = [
        lot for lot in db_queue
        if lot["amount"] * lot["price"] >= dust_threshold
    ]

    mem_queue = bot._pct_open_positions or []

    drift = len(db_queue) != len(mem_queue)
    if not drift:
        for db_lot, mem_lot in zip(db_queue, mem_queue):
            if (abs(db_lot["amount"] - mem_lot["amount"]) > 1e-6
                    or abs(db_lot["price"] - mem_lot["price"]) > 1e-6):
                drift = True
                break

    if not drift:
        return True

    logger.warning(
        f"[{bot.symbol}] FIFO DRIFT DETECTED — "
        f"memory queue: {len(mem_queue)} lots, DB queue: {len(db_queue)} lots. "
        f"Rebuilding from DB."
    )

    log_event(
        severity="warn",
        category="integrity",
        event="fifo_drift_detected",
        symbol=bot.symbol,
        message=f"FIFO queue drift: mem={len(mem_queue)} lots, db={len(db_queue)} lots",
        details={
            "mem_queue_summary": [
                {"amount": round(float(l["amount"]), 8),
                 "price": round(float(l["price"]), 8)}
                for l in mem_queue[:5]
            ],
            "db_queue_summary": [
                {"amount": round(float(l["amount"]), 8),
                 "price": round(float(l["price"]), 8)}
                for l in db_queue[:5]
            ],
        },
    )

    # Replace queue and recalc dependent state from the corrected lots.
    bot._pct_open_positions = db_queue
    if db_queue:
        total_amount = sum(lot["amount"] for lot in db_queue)
        weighted_cost = sum(lot["amount"] * lot["price"] for lot in db_queue)
        bot.state.holdings = total_amount
        bot.state.avg_buy_price = (
            weighted_cost / total_amount if total_amount > 0 else 0.0
        )
    else:
        bot.state.holdings = 0.0
        bot.state.avg_buy_price = 0.0

    # Best-effort Telegram alert. A failed send must never bubble out
    # of a sell-path verify call.
    try:
        from utils.telegram_notifier import SyncTelegramNotifier
        SyncTelegramNotifier().send_message(
            f"⚠️ <b>FIFO DRIFT — {bot.symbol}</b>\n"
            f"Queue corrected from DB.\n"
            f"Memory had {len(mem_queue)} lots → DB has {len(db_queue)} lots.\n"
            f"Holdings: {bot.state.holdings:.6f}"
        )
    except Exception:
        pass

    return False
