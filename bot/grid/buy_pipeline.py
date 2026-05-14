"""
BagHolderAI - Buy pipeline (Phase 1 split from grid_bot.py).

Brief s70 FASE 2 (2026-05-09): rimossa la legacy fixed-mode `execute_buy`
+ helper `activate_sell_level`. Avg-cost trading usa solo
`execute_percentage_buy`.
"""

import time
import logging
from typing import Optional
from datetime import datetime
from utils.formatting import fmt_price
from config.settings import HardcodedRules, TradingMode

logger = logging.getLogger("bagholderai.grid")


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

    # Brief s70 FASE 2 (CEO + Max 2026-05-09): Strategy A symmetric buy guard.
    # As we never sell below avg (S68a guard in sell_pipeline), we never buy
    # above avg when we already have holdings (DCA only in basso). Prevents
    # the "media in salita" loop in lateral-up markets. First entry
    # (holdings=0) is always permitted because there is no avg to respect.
    # Applied only to manual bots (managed_by="grid"); TF rotator buys are
    # driven by external signals and bypass the guard. Strategy A only.
    if (bot.strategy == "A"
            and bot.managed_by == "grid"
            and bot.state.holdings > 0
            and bot.state.avg_buy_price > 0
            and price > bot.state.avg_buy_price):
        logger.info(
            f"[{bot.symbol}] BUY BLOCKED: price {fmt_price(price)} > avg cost "
            f"{fmt_price(bot.state.avg_buy_price)}. Strategy A never buys above avg "
            f"(holdings={bot.state.holdings:.6f})."
        )
        from db.event_logger import log_event
        try:
            log_event(
                severity="info",
                category="trade_audit",
                event="buy_blocked_above_avg",
                symbol=bot.symbol,
                message=(
                    f"Buy blocked: price {price} > avg {bot.state.avg_buy_price} "
                    f"(holdings={bot.state.holdings})"
                ),
                details={
                    "price": float(price),
                    "avg_buy_price": float(bot.state.avg_buy_price),
                    "holdings": float(bot.state.holdings),
                },
            )
        except Exception:
            pass
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
    # Brief 71a Task 5: preserve check_price (trigger reference) so the
    # reason string can show both the trigger and the realized fill.
    check_price = price
    slippage_pct = 0.0
    exchange_order_id = None
    fee_currency = "USDT"
    if TradingMode.is_live() and bot.exchange is not None:
        # Brief 73c (S73 2026-05-12): when lot_step_size is known, submit
        # `amount=base_rounded` (deterministic, lot-step compliant) via
        # place_market_buy_base. Avoids the BONK -2010 rejection loop
        # that hit testnet 6 times on 2026-05-12 10:30-10:32 UTC: the
        # quote-order path (quoteOrderQty=$25) let Binance compute the
        # base amount from the slipped fill price, which on a thin book
        # broke lot_step_size divisibility. Reference price = check_price
        # (last polled tick); real fill comes from Binance response.
        # Fallback to quote-order only if filters unavailable (boot edge).
        from bot.exchange_orders import place_market_buy, place_market_buy_base
        res = None
        if bot._exchange_filters and price > 0:
            from utils.exchange_filters import round_to_step
            base_est = cost / price
            base_rounded = round_to_step(
                base_est, bot._exchange_filters["lot_step_size"],
            )
            if base_rounded > 0:
                res = place_market_buy_base(bot.exchange, bot.symbol, base_rounded)
            else:
                logger.warning(
                    f"[{bot.symbol}] BUY skipped: base_rounded=0 from "
                    f"cost=${cost:.4f} / price={price} / step={bot._exchange_filters['lot_step_size']}"
                )
                return None
        else:
            # No filters → fallback to quote-order (still better than skipping)
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
        # Brief 72a (S72): fee scaled from the base coin balance by Binance.
        # Subtracted from `state.holdings` so it mirrors the real wallet.
        # Paper mode keeps fee_base=0 because the simulated fill doesn't
        # touch base balance — paper fee is informational, USDT-equivalent.
        fee_base = float(res.get("fee_base", 0.0) or 0.0)
        if check_price > 0:
            slippage_pct = (price - check_price) / check_price * 100
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
        fee_base = 0.0  # 72a: paper has no base-coin commission

    old_last_buy = bot._pct_last_buy_price
    old_holdings = bot.state.holdings
    old_avg = bot.state.avg_buy_price

    # Brief 72a P1 (S72): state.holdings tracks the REAL wallet balance.
    # Binance scales fee from the base coin on market BUYs (e.g. you buy
    # 3.4M BONK, Binance keeps ~3.4K BONK as commission, your wallet
    # receives ~3.397M). Without subtracting fee_base, state.holdings
    # accumulates phantom qty and eventual sell-all gets InsufficientFunds
    # rejected (S71 BONK incident, 12.280 BONK observed drift over 9 buys).
    qty_acquired = amount - fee_base
    bot.state.total_invested += cost
    bot.state.total_fees += fee
    bot.state.holdings += qty_acquired

    # 75c (S76 2026-05-14): a successful BUY closes the drawdown cycle from
    # the bot's perspective (the position is being averaged down right now).
    # Clear any stop-buy baseline that a previous 75b unlock had registered,
    # so the next 39b check goes back to comparing against the real avg.
    bot._stop_buy_baseline_price = 0.0

    # Brief 72a P2 (S72): avg_buy_price = true USDT cost per coin held.
    # Numerator uses `cost` (USDT actually paid out of cash) and
    # denominator uses `qty_acquired` (coins that landed in the wallet).
    # Pre-72a we did (avg_old × old + price × amount) / (old + amount) —
    # numerically identical when fee_base=0 (paper) but ~0.1% low when
    # fee_base>0 (live market BUY). On mainnet this is the difference
    # between sell triggers that lock real profit vs ones that lock
    # losses after fee. Trade-off only visible at the boundary; corrected
    # by construction here.
    if bot.state.holdings > 0:
        bot.state.avg_buy_price = (
            (old_avg * old_holdings + cost) / bot.state.holdings
        )

    bot._pct_last_buy_price = price
    # Brief s70 FASE 2: avg-cost trading — no FIFO queue to populate.
    bot._daily_trade_count += 1
    bot._last_buy_time = time.time()
    bot._last_trade_time = datetime.utcnow()

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

    # Brief 71a Task 5: reason uses check_price (trigger) for the narrative
    # "dropped X% below ..." claim and appends fill + slippage as a tail
    # annotation. This makes the BUSINESS_STATE §27 case ("$0.00000735
    # dropped 1.5% below $0.00000731" — false on testnet) honest.
    slip_tail = (
        f" → fill {fmt_price(price)} (slippage {slippage_pct:+.2f}%)"
        if abs(slippage_pct) >= 0.05 else ""
    )
    if old_last_buy == 0:
        reason = (
            f"Pct buy: first buy at market {fmt_price(check_price)} "
            f"(reference established){slip_tail}"
        )
    else:
        reason = (
            f"Pct buy: check {fmt_price(check_price)} dropped {bot.buy_pct}% "
            f"below last buy {fmt_price(old_last_buy)}{slip_tail}"
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

    # Brief 72a P1 (S72): optional post-fill safety check (OFF by default,
    # ENABLED by RECONCILE_AFTER_FILL=true env flag for mainnet).
    try:
        from bot.grid.state_manager import maybe_reconcile_after_fill
        maybe_reconcile_after_fill(bot)
    except Exception:
        pass  # never let reconcile errors break a successful trade

    return trade_data
