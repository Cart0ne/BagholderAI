"""
BagHolderAI - Dust handler (Phase 1 split from grid_bot.py; rewritten S70 FASE 2).

Identifies dust state and zeroes out holdings to prevent retry spam:
- "Dust" = sell amount below step_size after rounding (round_to_step → 0).
- "Economic dust" = above step_size but below MIN_NOTIONAL/min_qty.

Brief s70 FASE 2 (avg-cost trading): the legacy pop-from-queue path is
gone. With queue-less Strategy A, "dust" simply means the residual
holdings can no longer produce a valid sell order on the exchange. We
zero state.holdings + state.avg_buy_price (write-off) and signal the
caller to abort the current sell — preventing the retry storm that the
old pop-no-event paths used to cause.

S109 (brief DUST, "evento + stub"): the write-off is now a persisted event
(bot_events_log: DUST_WRITEOFF) carrying `written_off_at`, not just a log
line. This is the durable record the brief asked for (Option 3) — on
mainnet it pairs with bot/dust_converter.py to explain the wallet residue
that stays put after the books are zeroed.
"""

import logging

from db.event_logger import log_event
from utils.timeutils import utcnow

logger = logging.getLogger("bagholderai.grid")


def _writeoff_dust(bot, reason: str, price: float | None = None):
    """Zero out residual holdings + avg when the position is unsellable, and
    record a durable DUST_WRITEOFF event (with written_off_at)."""
    dust_amount = float(bot.managed_holdings or 0)  # S97a: report the managed dust, not wallet+phantom
    est_value = round(dust_amount * price, 8) if price else None
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    written_off_at = utcnow().isoformat()
    value_str = f"~${est_value:.4f}" if est_value is not None else "value n/a"
    logger.info(
        f"[{bot.symbol}] Dust write-off: {dust_amount:.8f} units removed from state "
        f"({value_str}, {reason})."
    )
    # S109: persist the write-off so it isn't just a log line. On mainnet this
    # is the record reconciliation reads to tell "abandoned dust" apart from a
    # wallet↔DB drift bug (brief DUST point 3, go-live).
    log_event(
        severity="warn",
        category="trade",
        event="DUST_WRITEOFF",
        symbol=bot.symbol,
        message=f"Dust write-off: {dust_amount:.8f} units ({value_str}) — {reason}",
        details={
            "amount": dust_amount,
            "est_value_usdt": est_value,
            "price": price,
            "reason": reason,
            "written_off_at": written_off_at,
        },
    )


def handle_step_size_dust(bot, amount: float, price: float) -> bool:
    """Write-off if amount post-round is 0.

    Called when round_to_step returned 0 for the requested sell amount —
    the exchange would reject the order outright. Returns True so the
    caller bails out (return None).
    """
    if amount > 0:
        return False
    _writeoff_dust(
        bot,
        f"step_size {bot._exchange_filters.get('lot_step_size', '?')} > sell amount",
        price=price,
    )
    return True


def handle_economic_dust(bot, price: float, reason_reject: str) -> bool:
    """Write-off if validate_order rejected for MIN_NOTIONAL / min_qty.

    Means the residual holdings × price is below Binance's economic
    minimum — sellable in theory but the exchange refuses. Returns True
    so the caller bails out.
    """
    if "MIN_NOTIONAL" not in reason_reject and "min_qty" not in reason_reject:
        return False
    _writeoff_dust(bot, f"economic dust ({reason_reject})", price=price)
    return True
