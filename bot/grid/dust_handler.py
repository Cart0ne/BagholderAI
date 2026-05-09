"""
BagHolderAI - Dust handler (Phase 1 split from grid_bot.py).

Identifies and removes lots that are too small to be sold on the exchange:
- "Dust" = lot size below step_size after rounding (round_to_step → 0).
- "Economic dust" = lot above step_size but below MIN_NOTIONAL/min_qty.

KNOWN BUG (kept intact for Phase 1 — fix in Phase 2):
The two pop paths below mutate `bot._pct_open_positions` and `bot.state`
WITHOUT writing any event to bot_events_log nor any trade to `trades`.
This is the root of the 60c "phantom audit + drift" pattern: when
_execute_percentage_sell calls these and returns None, the queue has
silently lost a lot, the next verify_fifo_queue rebuilds from DB and
flags a spurious drift, and the audit `sell_fifo_detail` written
upstream becomes orphaned (no matching trade).

# TODO 62a (Phase 2): emit `dust_lot_removed` events to bot_events_log
# so verify_fifo_queue can reconcile, and move the dust check BEFORE
# the audit write in _execute_percentage_sell to avoid orphans.
"""

import logging

logger = logging.getLogger("bagholderai.grid")


def _sync_holdings_after_dust_pop(bot, dust_amount: float):
    """39h: keep state.holdings in sync with the queue after a dust pop.

    Without this, the self-heal path (holdings>0 + queue empty) keeps
    resurrecting the dust lot forever and the post-stop-loss cleanup
    never sees holdings=0.
    """
    bot.state.holdings = max(0.0, bot.state.holdings - dust_amount)
    if bot.state.holdings <= 1e-10:
        bot.state.holdings = 0.0
        bot.state.avg_buy_price = 0.0


def handle_step_size_dust(bot, amount: float, price: float) -> bool:
    """Pop the head lot if it's below step_size after rounding.

    Called when round_to_step returned 0 for the head-lot amount —
    the exchange would reject the order outright.

    Returns True if a lot was popped (caller should `return None`).
    Returns False if no action needed.
    """
    if amount > 0:
        return False
    popped = bot._pct_open_positions.pop(0)
    dust_amount = float(popped.get("amount", 0))
    dust_value = dust_amount * price
    logger.info(
        f"[{bot.symbol}] Dust lot removed: {dust_amount:.6f} units "
        f"(${dust_value:.4f}) too small for step_size {bot._exchange_filters['lot_step_size']}"
    )
    _sync_holdings_after_dust_pop(bot, dust_amount)
    return True


def handle_economic_dust(bot, price: float, reason_reject: str) -> bool:
    """Pop the head lot if validate_order failed on MIN_NOTIONAL/min_qty.

    Lot is above step_size but below the exchange's economic minimum —
    it will never be sellable. Remove from queue to stop retry spam.

    Returns True if a lot was popped (caller should `return None`).
    Returns False if the rejection reason is something else (caller
    handles its own logging + return).
    """
    if "MIN_NOTIONAL" not in reason_reject and "min_qty" not in reason_reject:
        return False
    popped = bot._pct_open_positions.pop(0)
    dust_amount = float(popped.get("amount", 0))
    logger.info(
        f"[{bot.symbol}] Economic dust lot removed: {dust_amount:.8f} units "
        f"(${dust_amount * price:.4f}) — {reason_reject}"
    )
    _sync_holdings_after_dust_pop(bot, dust_amount)
    return True
