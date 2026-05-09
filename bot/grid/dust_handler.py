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
"""

import logging

logger = logging.getLogger("bagholderai.grid")


def _writeoff_dust(bot, reason: str):
    """Zero out residual holdings + avg when the position is unsellable."""
    dust_amount = float(bot.state.holdings or 0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    logger.info(
        f"[{bot.symbol}] Dust write-off: {dust_amount:.8f} units removed from state "
        f"({reason})."
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
    _writeoff_dust(bot, f"economic dust ({reason_reject})")
    return True
