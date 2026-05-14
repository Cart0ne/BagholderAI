"""Forced liquidation paths + TF multi-lot entry.

Three orchestrated mutations of bot/DB state live here:

- `_deactivate_if_fully_liquidated`: gate that writes is_active=False only
  if DB contabilità confirms holdings=0. Avoids minting orphans when the
  last sell INSERT timed out.
- `_consume_initial_lots`: TF multi-lot market entry, fired once on the
  first cycle after an ALLOCATE.
- `_force_liquidate`: market sell-all path used by BEARISH rotation,
  stop-loss, take-profit, profit-lock, trailing-stop, gain-saturation.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
"""

import logging

from utils.formatting import fmt_price
from db.event_logger import log_event

from bot.grid_runner.lifecycle import fetch_price
from bot.grid_runner.telegram_dispatcher import (
    _build_cycle_summary,
    _format_cycle_summary,
)

logger = logging.getLogger("bagholderai.runner")


def _deactivate_if_fully_liquidated(symbol: str, event_label: str) -> bool:
    """45: after a TF bot's liquidation branch, verify DB contabilità shows
    zero holdings before writing is_active=False. If the last sell INSERT
    timed out on Supabase, bot memory may say 0 but DB still says
    bought > sold — writing is_active=False there would mint an orphan
    that the boot reconciler then has to clean up. Keep is_active=True +
    pending_liquidation=True in that case so the next spawn retries.

    Returns True if the row was deactivated, False if held active for retry.
    """
    try:
        from db.client import get_client
        sb = get_client()
        trades_res = sb.table("trades").select(
            "side, amount"
        ).eq("symbol", symbol).eq("config_version", "v3").execute()
        bought = 0.0
        sold = 0.0
        for t in trades_res.data or []:
            amt = float(t.get("amount") or 0)
            if t.get("side") == "buy":
                bought += amt
            elif t.get("side") == "sell":
                sold += amt
        holdings_db = bought - sold
    except Exception as e:
        # If we can't verify (Supabase unreachable), err on the side of
        # NOT deactivating — worst case the bot stays alive one more
        # iteration; orphan reconciler at next boot will pick up any
        # mistake. Safer than minting an orphan with half-confidence.
        logger.warning(
            f"[{symbol}] Could not verify holdings_db for deactivation gate: {e}. "
            f"Holding is_active=True, pending_liquidation=True for next retry."
        )
        return False

    if holdings_db > 1e-6:
        logger.warning(
            f"[{symbol}] Post-{event_label.lower()} residual holdings_db={holdings_db:.6f} — "
            f"holding is_active=True + pending_liquidation=True so orchestrator "
            f"rispawns and retries the liquidation (likely a log_trade timed out)."
        )
        try:
            sb.table("bot_config").update({
                "is_active": True,
                "pending_liquidation": True,
            }).eq("symbol", symbol).execute()
        except Exception as e:
            logger.error(f"[{symbol}] Failed to hold is_active=True: {e}")
        return False

    # Clean liquidation — deactivate as before.
    try:
        sb.table("bot_config").update({
            "is_active": False,
            "pending_liquidation": False,
        }).eq("symbol", symbol).execute()
        return True
    except Exception as e:
        logger.error(f"[{symbol}] Failed to clear bot_config after {event_label.lower()}: {e}")
        return False


def _consume_initial_lots(reader, bot, symbol: str, price: float, notifier) -> int:
    """42a: Multi-lot entry — a SINGLE market buy sized N×capital_per_trade.

    On the first cycle after a TF ALLOCATE, fire one aggregated market buy
    equivalent to N lots, where N = bot_config.initial_lots (written by the
    allocator). This produces exactly 1 Binance order, 1 DB INSERT and 1
    Telegram alert (unlike the earlier per-lot loop which caused duplicate
    inserts to be rejected by the DB dedup trigger on ravvicinate calls).

    Idempotency: a bot-level latch (`bot._initial_lots_done`) prevents
    re-firing during the same process lifetime regardless of when the DB
    UPDATE propagates back through the 300s config-reader cache.

    Returns the number of logical lots bought (0 if not applicable).
    """
    if bot.managed_by not in ("tf", "tf_grid"):
        return 0
    # In-memory latch: once we've handled the entry for this bot instance,
    # don't even look at the cached initial_lots again — the 300s reader
    # refresh would otherwise keep returning the stale "3" for minutes
    # after we've already UPDATEd the DB row to 0.
    if getattr(bot, "_initial_lots_done", False):
        return 0

    sb_cfg = reader.get_config(symbol)
    raw = sb_cfg.get("initial_lots") if sb_cfg else None
    try:
        lots = int(raw) if raw is not None else 0
    except Exception:
        lots = 0
    if lots <= 0:
        # Mark done so subsequent ticks skip the cache lookup. DB is already
        # 0 (or the allocator never set it); nothing to do.
        bot._initial_lots_done = True
        return 0

    # Single aggregated buy: temporarily scale capital_per_trade so the
    # existing _execute_percentage_buy path emits ONE trade for N lots
    # worth of capital. Grid sell-per-lot semantics are preserved because
    # the resulting position is one big avg-cost entry on state, and
    # greed decay evaluates each lot independently against its own buy
    # price (all lots after this carry their own price).
    per_trade_before = bot.capital_per_trade
    aggregate = per_trade_before * lots
    bot.capital_per_trade = aggregate
    logger.info(
        f"[{symbol}] Multi-lot entry: firing 1 aggregated market buy of "
        f"{lots} lots (~${aggregate:.2f} @ {fmt_price(price)})"
    )
    try:
        trade = bot._execute_percentage_buy(price)
    finally:
        bot.capital_per_trade = per_trade_before

    # Clear DB flag + set latch regardless of buy success — the entry window
    # is one-shot. If the single buy failed (e.g. cash insufficient), the
    # TF bot falls through to normal grid logic on subsequent ticks.
    bot._initial_lots_done = True
    try:
        from db.client import get_client
        get_client().table("bot_config").update(
            {"initial_lots": 0}
        ).eq("symbol", symbol).execute()
    except Exception as e:
        logger.error(f"[{symbol}] Failed to reset initial_lots to 0: {e}")

    if trade is None:
        logger.warning(
            f"[{symbol}] Multi-lot entry skipped — aggregated buy returned "
            f"None (likely insufficient cash)."
        )
        return 0

    cost = float(trade.get("cost", 0.0))
    # Annotate the trade for Telegram + log — reason override so the CEO
    # sees it framed as a multi-lot entry, not a plain "first buy".
    trade["reason"] = (
        f"Multi-lot entry: {lots} lots at market "
        f"({fmt_price(price)}, total ${cost:.2f})"
    )
    try:
        notifier.send_trade_alert(trade)
    except Exception as e:
        logger.warning(f"[{symbol}] multi-lot entry alert failed: {e}")
    try:
        notifier.send_message(
            f"🚀 <b>{symbol} Multi-lot entry</b>\n"
            f"Bought {lots} lots at market (${cost:.2f} total)"
        )
    except Exception as e:
        logger.warning(f"[{symbol}] multi-lot entry summary alert failed: {e}")
    log_event(
        severity="info",
        category="tf",
        event="multi_lot_entry_fired",
        symbol=symbol,
        message=f"Multi-lot entry: {lots} lots at ${price:.6f} (total ${cost:.2f})",
        details={"lots": lots, "price": price, "total_cost": cost},
    )
    return lots


def _force_liquidate(bot, exchange, trade_logger, notifier, symbol: str,
                     reason: str = "TF rotation"):
    """Force-sell all holdings at market price.

    reason is used in the Telegram message + DB trade.reason so it's clear
    WHY the bot is being drained ("STOP-LOSS", "BEARISH EXIT", "TF rotation").

    Holdings below 1e-6 are treated as "already empty" — avoids firing a
    noisy Telegram with floating-point dust after a stop-loss has already
    liquidated (the meaningful PnL is in the individual sell notifications).

    39e: realized_pnl is computed as revenue − Σ(lot cost bases) − fees,
    not against a single avg_buy_price. The old formula was approximately
    equivalent when avg_buy_price was perfectly weighted — but after
    partial sells, dust rounding, or FIFO consumption the two diverge
    and the liquidation's PnL diverges from reality (today's API3 case:
    recorded +$0.18 vs actual −$1.21). Also routes skim on positive PnL,
    which the old flow bypassed unconditionally.
    """
    holdings = bot.state.holdings if bot.state else 0
    managed_by = getattr(bot, "managed_by", "grid")

    if holdings <= 1e-6:
        # 39f Section B: the stop-loss / take-profit paths already
        # liquidated every lot per-lot via _execute_percentage_sell. So
        # this branch is "no sell to execute, but still a real cycle
        # close". For TF bots emit the unified dealloc + cycle summary
        # Telegram so the CEO gets one consistent message regardless of
        # which exit trigger fired. For manual bots (or orchestrator
        # shutdown) keep the silent return — there's no TF cycle to
        # summarize.
        logger.info(f"[{symbol}] No holdings to liquidate (reason: {reason})")
        if managed_by in ("tf", "tf_grid") and trade_logger is not None:
            try:
                summary = _build_cycle_summary(trade_logger.client, symbol, None)
                if summary:
                    # The cycle summary block already reports Realized P&L,
                    # skim, net, and allocated→returned. The header just
                    # states WHICH trigger closed the cycle — no duplicate
                    # PnL line.
                    msg = (
                        f"🔴 <b>{symbol} DEALLOCATED</b> ({reason})\n"
                        f"Cycle closed — all lots exited via per-lot sells\n"
                        + _format_cycle_summary(summary)
                    )
                    notifier.send_message(msg)
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to emit cycle summary on empty-liquidation: {e}")
        return

    try:
        price = fetch_price(exchange, symbol)

        # Brief s70 FASE 2: avg-cost forced liquidation.
        # cost basis = avg_buy_price × holdings. The legacy FIFO queue
        # path è stato rimosso (no più _pct_open_positions in stato bot).
        avg_buy = bot.state.avg_buy_price if bot.state and bot.state.avg_buy_price else 0
        lot_cost_basis = avg_buy * holdings
        sell_amount = holdings

        proceeds = price * sell_amount
        # Fees: same rate as GridBot._execute_percentage_sell — charged on
        # BOTH the buy legs (reconstructed from cost basis) and the sell.
        # 52a: paper-mode realized_pnl excludes fees — see grid_bot.py
        # _execute_sell comment for the full rationale.
        from bot.grid.grid_bot import GridBot
        fee_rate = GridBot.FEE_RATE
        sell_fee = proceeds * fee_rate
        buy_fees = lot_cost_basis * fee_rate
        realized_pnl = proceeds - lot_cost_basis

        trade_db_row: dict = {}

        if trade_logger:
            try:
                trade_db_row = trade_logger.log_trade(
                    symbol=symbol,
                    side="sell",
                    amount=sell_amount,
                    price=price,
                    cost=proceeds,
                    fee=sell_fee,
                    strategy="A",
                    brain="grid",
                    mode="paper",
                    reason=f"FORCED_LIQUIDATION ({reason})",
                    realized_pnl=realized_pnl,
                    config_version="v3",
                    managed_by=managed_by,
                ) or {}
            except Exception as e:
                logger.error(f"[{symbol}] Failed to log liquidation trade: {e}")

        # 39e Fix 2: skim 30% (skim_pct) to reserve_ledger when the
        # liquidation PnL is positive. Previously bypassed entirely —
        # today's API3 missed a $0.054 skim because of this path.
        skim_amount = 0.0
        reserve_total = 0.0
        skim_pct = float(getattr(bot, "skim_pct", 0) or 0)
        reserve_ledger = getattr(bot, "reserve_ledger", None)
        if realized_pnl > 0 and skim_pct > 0 and reserve_ledger is not None:
            skim_amount = realized_pnl * (skim_pct / 100)
            try:
                trade_id = trade_db_row.get("id") if isinstance(trade_db_row, dict) else None
                reserve_ledger.log_skim(symbol, skim_amount, trade_id=trade_id,
                                         managed_by=getattr(bot, "managed_by", None))
                reserve_total = reserve_ledger.get_reserve_total(symbol, force_refresh=True)
                logger.info(
                    f"[{symbol}] SKIM ${skim_amount:.4f} → reserve total ${reserve_total:.2f} (liquidation)"
                )
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to log liquidation skim: {e}")
                skim_amount = 0.0  # don't claim a skim that failed

        # Reflect the sell in the in-memory bot state so get_status() and the
        # final stop notification don't report stale holdings. Mirrors the
        # state updates in GridBot._execute_sell.
        if bot.state:
            bot.state.total_received += proceeds
            bot.state.total_fees += sell_fee + buy_fees
            bot.state.realized_pnl += realized_pnl
            bot.state.daily_realized_pnl += realized_pnl
            bot.state.holdings = 0
            bot.state.avg_buy_price = 0

        pnl_emoji = "📈" if realized_pnl >= 0 else "📉"
        pnl_sign = "+" if realized_pnl >= 0 else ""
        msg = (
            f"🔴 <b>{symbol} LIQUIDATED</b> ({reason})\n"
            f"Sold {sell_amount:.6f} at ${price:.4f}\n"
            f"Proceeds: ${proceeds:.2f}\n"
            f"{pnl_emoji} PnL: {pnl_sign}${realized_pnl:.2f}"
        )
        if skim_amount > 0:
            msg += f"\n💰 Reserve: +${skim_amount:.2f} → total ${reserve_total:.2f}"

        # 39e Fix 3: append cycle summary for TF bots. Manual bots don't
        # have a TF "cycle" concept, so skip for them. The summary queries
        # trend_decisions_log for the last ALLOCATE and aggregates all
        # trades since then — including the liquidation sell we just wrote.
        if managed_by in ("tf", "tf_grid") and trade_logger is not None:
            try:
                liquidation_id = trade_db_row.get("id") if isinstance(trade_db_row, dict) else None
                summary = _build_cycle_summary(trade_logger.client, symbol, liquidation_id)
                if summary:
                    msg += "\n" + _format_cycle_summary(summary)
            except Exception as e:
                logger.warning(f"[{symbol}] cycle summary append failed: {e}")

        notifier.send_message(msg)
        logger.info(
            f"[{symbol}] Liquidation complete ({reason}): sold {sell_amount} at {price}, "
            f"PnL: ${realized_pnl:.2f}, skim: ${skim_amount:.4f}"
        )
    except Exception as e:
        logger.error(f"[{symbol}] Liquidation FAILED: {e}")
        notifier.send_message(
            f"🚨 <b>{symbol} LIQUIDATION FAILED</b>\n"
            f"<code>{str(e)[:300]}</code>\n"
            f"Manual intervention needed!"
        )
