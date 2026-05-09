"""
BagHolderAI - Buy pipeline (Phase 1 split from grid_bot.py).

Contains:
- execute_buy: fixed-mode buy at a grid level (legacy v1).
- execute_percentage_buy: percentage-mode buy (v3, hot path).

Helpers in this file:
- activate_sell_level: when a buy fills, arm the nearest unfilled sell.
"""

import time
import logging
from typing import Optional
from datetime import datetime
from utils.formatting import fmt_price
from config.settings import HardcodedRules, TradingMode

logger = logging.getLogger("bagholderai.grid")


# ----------------------------------------------------------------------
# Fixed-mode helpers.
# ----------------------------------------------------------------------

def activate_sell_level(bot, buy_level, amount: float):
    """When a buy fills, activate the nearest unfilled sell level above it.

    This is what makes the grid cycle: buy low → sell high → repeat.
    """
    for level in bot.state.levels:
        if level.side == "sell" and not level.filled and level.price > buy_level.price:
            level.order_amount = amount
            return


# ----------------------------------------------------------------------
# Fixed-mode buy.
# ----------------------------------------------------------------------

def execute_buy(bot, level, price: float) -> Optional[dict]:
    """Execute a buy at a grid level (fixed mode)."""
    # 39b: manual stop-buy gate also for fixed-grid mode (for parity,
    # even if manual bots run percentage today).
    if bot._stop_buy_active:
        logger.info(
            f"[{bot.symbol}] BUY BLOCKED: stop-buy active "
            f"(drawdown > {bot.stop_buy_drawdown_pct}% of allocation)."
        )
        return None
    # 45g: gain-saturation latched → no new entries until next ALLOCATE.
    if bot._gain_saturation_triggered:
        logger.info(
            f"[{bot.symbol}] BUY SKIPPED: gain-saturation latched, "
            f"waiting for next ALLOCATE."
        )
        return None
    # 51b: trailing-stop latched → no new entries during liquidation.
    if bot._trailing_stop_triggered:
        logger.info(
            f"[{bot.symbol}] BUY SKIPPED: trailing-stop latched, "
            f"waiting for next ALLOCATE."
        )
        return None

    standard_cost = level.order_amount * price

    # Snapshot for Telegram verification (reserve-aware)
    cash_before = bot._available_cash()

    # Last-shot logic: use remaining cash if below standard cost but above minimum
    if cash_before >= standard_cost:
        actual_cost = standard_cost
        last_shot = False
    elif cash_before >= HardcodedRules.MIN_LAST_SHOT_USD:
        actual_cost = cash_before
        last_shot = True
        logger.info(
            f"LAST SHOT: buying with remaining ${cash_before:.2f} "
            f"(reduced from standard ${standard_cost:.2f}) for {bot.symbol}"
        )
    else:
        logger.warning(
            f"Insufficient cash for BUY {bot.symbol}: "
            f"need ${standard_cost:.2f}, have ${cash_before:.2f}. Skipping level {fmt_price(level.price)}."
        )
        bot.skipped_buys.append({
            "symbol": bot.symbol,
            "level_price": level.price,
            "cost": standard_cost,
            "cash_before": cash_before,
        })
        return None

    amount = actual_cost / price
    if bot._exchange_filters:
        from utils.exchange_filters import round_to_step
        amount = round_to_step(amount, bot._exchange_filters["lot_step_size"])
        cost = amount * price  # recalculate cost after rounding
    else:
        cost = actual_cost
    fee = cost * bot.FEE_RATE

    # Mark level as filled
    level.filled = True
    level.filled_at = time.time()

    # Update state — weighted average buy price
    old_holdings = bot.state.holdings
    old_avg = bot.state.avg_buy_price
    bot.state.total_invested += cost
    bot.state.total_fees += fee
    bot.state.holdings += amount

    # Recalculate average buy price (weighted average on buys only)
    if bot.state.holdings > 0:
        bot.state.avg_buy_price = (old_avg * old_holdings + price * amount) / bot.state.holdings

    # Activate the corresponding sell level above
    activate_sell_level(bot, level, amount)

    bot._daily_trade_count += 1
    bot._last_buy_time = time.time()  # Task 5: record buy timestamp

    reason = f"Grid buy at level {fmt_price(level.price)} (price dropped to {fmt_price(price)})"
    if last_shot:
        reason = f"LAST SHOT: {reason} — spent remaining ${cost:.2f}"

    trade_data = {
        "symbol": bot.symbol,
        "side": "buy",
        "amount": amount,
        "price": price,
        "cost": cost,
        "fee": fee,
        "strategy": bot.strategy,
        "brain": "grid",
        "reason": reason,
        "mode": bot.mode,
        "cash_before": cash_before,
        "capital_allocated": bot.capital,
        "managed_by": getattr(bot, "managed_by", "grid"),
    }

    # Log to database
    try:
        bot.trade_logger.log_trade(**trade_data)
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

    logger.info(
        f"BUY {amount:.6f} {bot.symbol} @ {fmt_price(price)} "
        f"(cost: ${cost:.2f}, fee: ${fee:.4f})"
    )

    return trade_data


# ----------------------------------------------------------------------
# Percentage-mode buy (HOT PATH — used by all v3 bots).
# ----------------------------------------------------------------------

def execute_percentage_buy(bot, price: float) -> Optional[dict]:
    """Execute a percentage-mode buy: spend capital_per_trade USDT at current price."""
    if price <= 0:
        logger.error(f"Invalid price {price} for {bot.symbol}, skipping pct buy")
        return None

    # 39b: manual stop-buy gate. When drawdown threshold has been breached
    # on this manual bot, reject any new buy until a profitable sell
    # resets the flag. Existing lots continue to follow Strategy A.
    if bot._stop_buy_active:
        logger.info(
            f"[{bot.symbol}] BUY BLOCKED: stop-buy active "
            f"(drawdown > {bot.stop_buy_drawdown_pct}% of allocation). "
            f"Waiting for profitable sell to reset."
        )
        return None
    # 45g: gain-saturation latched → no new entries until next ALLOCATE.
    if bot._gain_saturation_triggered:
        logger.info(
            f"[{bot.symbol}] BUY SKIPPED: gain-saturation latched, "
            f"waiting for next ALLOCATE."
        )
        return None
    # 51b: trailing-stop latched → no new entries during liquidation.
    if bot._trailing_stop_triggered:
        logger.info(
            f"[{bot.symbol}] BUY SKIPPED: trailing-stop latched, "
            f"waiting for next ALLOCATE."
        )
        return None

    standard_cost = bot.capital_per_trade
    cash_before = bot._available_cash()

    # Last-shot logic: use remaining cash if below standard cost but above minimum.
    # Sweep logic: if remaining cash after this buy < one trade size, spend it all now.
    if cash_before >= standard_cost:
        remaining_after = cash_before - standard_cost
        if 0 < remaining_after < standard_cost:
            cost = cash_before  # sweep stranded remainder into this trade
            last_shot = True
            logger.info(
                f"SWEEP BUY: spending ${cash_before:.2f} (remaining ${remaining_after:.2f} "
                f"< trade size ${standard_cost:.2f}) for {bot.symbol}"
            )
        else:
            cost = standard_cost
            last_shot = False
    elif cash_before >= HardcodedRules.MIN_LAST_SHOT_USD:
        cost = cash_before
        last_shot = True
        logger.info(
            f"LAST SHOT: buying with remaining ${cash_before:.2f} "
            f"(reduced from standard ${standard_cost:.2f}) for {bot.symbol}"
        )
    else:
        logger.warning(
            f"Insufficient cash for BUY {bot.symbol}: "
            f"need ${standard_cost:.2f}, have ${cash_before:.2f}. Skipping pct buy."
        )
        bot.skipped_buys.append({
            "symbol": bot.symbol,
            "level_price": price,
            "cost": standard_cost,
            "cash_before": cash_before,
        })
        return None

    # 66a Step 3: live mode (testnet or mainnet) sends a real market BUY
    # to Binance. The fill price, cost, and fee come from the exchange
    # response — NOT from the local FEE_RATE constant. Paper mode keeps
    # the legacy simulated path unchanged.
    exchange_order_id = None
    fee_currency = "USDT"
    if TradingMode.is_live() and bot.exchange is not None:
        from bot.exchange_orders import place_market_buy
        res = place_market_buy(bot.exchange, bot.symbol, cost)
        if res is None:
            # Order failed or did not fill — no state change. Retry on next tick.
            return None
        amount = res["filled_amount"]
        price = res["avg_price"]
        cost = res["cost"]
        fee = res["fee_cost"]
        fee_currency = res["fee_currency"] or "USDT"
        exchange_order_id = res["order_id"]
    else:
        # Paper path: simulated fill at the requested price.
        amount = cost / price

        # Round to valid step size and validate against exchange filters
        if bot._exchange_filters:
            from utils.exchange_filters import round_to_step, validate_order
            amount = round_to_step(amount, bot._exchange_filters["lot_step_size"])
            valid, reason_reject = validate_order(bot.symbol, amount, price, bot._exchange_filters)
            if not valid:
                logger.warning(f"[{bot.symbol}] BUY order rejected: {reason_reject}")
                return None
            cost = amount * price  # recalculate cost after rounding

        fee = cost * bot.FEE_RATE

    old_last_buy = bot._pct_last_buy_price
    old_holdings = bot.state.holdings
    old_avg = bot.state.avg_buy_price

    bot.state.total_invested += cost
    bot.state.total_fees += fee
    bot.state.holdings += amount

    if bot.state.holdings > 0:
        bot.state.avg_buy_price = (old_avg * old_holdings + price * amount) / bot.state.holdings

    bot._pct_last_buy_price = price
    bot._pct_open_positions.append({"amount": amount, "price": price})
    bot._daily_trade_count += 1
    bot._last_buy_time = time.time()
    bot._last_trade_time = datetime.utcnow()
    bot._self_heal_attempted = False  # real trade happened, allow self-heal again if needed

    # 51b fix (2026-05-04): reset trailing peak on every confirmed TF buy.
    # Without this, a peak from an earlier lot survives a last-shot buy at a
    # lower price and arms the trailing stop on a fresh lot that never had a
    # gain (DOGE 2026-05-04: lot A buy $0.1124 → peak $0.1136 → last-shot
    # lot B $0.1095 → trailing fired 1 min later, sold both at -2% from
    # stale peak). Reset only when the trailing feature is enabled on a TF
    # bot; manual bots and disabled-trailing TF bots are unaffected.
    if (bot.managed_by == "tf"
            and bot.tf_trailing_stop_pct > 0):
        bot._trailing_peak_price = price

    if old_last_buy == 0:
        reason = f"Pct buy: first buy at market {fmt_price(price)} (reference established)"
    else:
        reason = (
            f"Pct buy: price {fmt_price(price)} dropped {bot.buy_pct}% "
            f"below last buy {fmt_price(old_last_buy)}"
        )
    if last_shot:
        reason = f"LAST SHOT: {reason} — spent remaining ${cost:.2f}"

    trade_data = {
        "symbol": bot.symbol,
        "side": "buy",
        "amount": amount,
        "price": price,
        "cost": cost,
        "fee": fee,
        "strategy": bot.strategy,
        "brain": "grid",
        "reason": reason,
        "mode": bot.mode,
        "cash_before": cash_before,
        "capital_allocated": bot.capital,
        "managed_by": getattr(bot, "managed_by", "grid"),
    }
    # 67a: fee_asset only written for real exchange fills. Paper trades
    # omit the field to avoid INSERT failures on schemas that haven't
    # received the brief 67a migration yet (defensive against partial deploys).
    if exchange_order_id:
        trade_data["exchange_order_id"] = exchange_order_id
        trade_data["fee_asset"] = fee_currency

    try:
        bot.trade_logger.log_trade(**trade_data)
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

    logger.info(
        f"BUY {amount:.6f} {bot.symbol} @ {fmt_price(price)} "
        f"(cost: ${cost:.2f}, fee: ${fee:.4f} {fee_currency}) [pct mode]"
        + (f" id={exchange_order_id}" if exchange_order_id else "")
    )
    return trade_data
