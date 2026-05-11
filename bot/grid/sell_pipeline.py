"""
BagHolderAI - Sell pipeline (Phase 1 split from grid_bot.py).

Contains:
- _execute_sell: fixed-mode sell at a grid level (legacy v1).
- _execute_percentage_sell: percentage-mode FIFO sell (v3, hot path).
- evaluate_gain_saturation: 45g circuit breaker.
- get_effective_tp: 42a greed-decay tier resolution.

KNOWN BUGS (kept intact for Phase 1 — fix in Phase 2):
- 60c: _execute_percentage_sell can be called twice in <1s for the same
  symbol; the DB safety trigger "Duplicate trade rejected within 5s"
  blocks the 2nd INSERT, but state.holdings/_pct_open_positions/audit
  have already been mutated for both calls. Result: state.realized_pnl
  inflated, mem_queue desynced from DB, drift detection rebuilds, loop.
  See project_60c_fifo_init_bug memory for full diagnosis.
- The audit `sell_fifo_detail` is written BEFORE log_trade. If log_trade
  fails (Duplicate trade rejected, or anything else), the audit becomes
  orphaned (written, no matching trade in `trades`).
- Dust pop in `handle_step_size_dust` / `handle_economic_dust` mutates
  state without writing any DB event — sole queue desync source.

# TODO 62a (Phase 2): make _execute_percentage_sell atomic — state changes
# AFTER log_trade succeeds, with rollback on failure. Move audit AFTER trade.
# Add client-side idempotency key to short-circuit double-calls before they
# touch state. See dust_handler.py for the dust event TODO.
"""

import time
import logging
from typing import Optional
from datetime import datetime, timezone
from utils.formatting import fmt_price
from db.event_logger import log_event
from config.settings import TradingMode

# These imports are inside functions where used (kept identical to original).

logger = logging.getLogger("bagholderai.grid")


# ----------------------------------------------------------------------
# 42a: Greed decay TP resolver. Pure-ish (only reads bot state + clock).
# ----------------------------------------------------------------------

def get_effective_tp(bot) -> tuple:
    """42a: Greed decay for TF bots. Returns (threshold_pct, age_minutes, tier_used).

    For TF bots with a valid allocated_at + greed_decay_tiers, returns the
    tp_pct of the highest-minutes tier whose threshold is <= age. When
    age is below the lowest tier's minutes (pre-first-tier window), the
    first tier's tp_pct is used — greed decay is authoritative from t=0,
    not a gradual override that kicks in after N minutes.

    Post-last-tier salvage (CEO decision 2026-04-20 evening): once the
    bot outlives the highest-minutes tier, fall back to bot.sell_pct
    as a final safety threshold (if sell_pct > 0). This replaces the
    awkward 999999-minutes placeholder tier with an actual editable
    per-coin parameter. Setting sell_pct=0 on a TF coin disables the
    salvage (bot stays on the last tier's tp_pct forever).

    For anything else (manual bots, missing allocated_at, empty/bad
    tiers), returns (bot.sell_pct, None, None) — the legacy behavior.
    """
    if bot.managed_by not in ("tf", "tf_grid"):
        return (bot.sell_pct, None, None)
    if bot.allocated_at is None or not bot.greed_decay_tiers:
        return (bot.sell_pct, None, None)

    now = datetime.now(timezone.utc)
    alloc = bot.allocated_at
    if alloc.tzinfo is None:
        alloc = alloc.replace(tzinfo=timezone.utc)
    age_minutes = (now - alloc).total_seconds() / 60.0

    tier_used = None
    try:
        tiers = sorted(
            (t for t in bot.greed_decay_tiers
             if isinstance(t, dict) and "minutes" in t and "tp_pct" in t),
            key=lambda t: float(t["minutes"]),
        )
    except Exception:
        return (bot.sell_pct, age_minutes, None)
    if not tiers:
        return (bot.sell_pct, age_minutes, None)
    for tier in tiers:
        try:
            if age_minutes >= float(tier["minutes"]):
                tier_used = tier
            else:
                break
        except Exception:
            continue

    if tier_used is None:
        tier_used = tiers[0]

    last_tier_minutes = float(tiers[-1]["minutes"])
    if age_minutes >= last_tier_minutes and bot.sell_pct > 0:
        return (
            float(bot.sell_pct),
            age_minutes,
            {"minutes": last_tier_minutes, "tp_pct": float(bot.sell_pct), "source": "sell_pct"},
        )

    try:
        return (float(tier_used["tp_pct"]), age_minutes, tier_used)
    except Exception:
        return (bot.sell_pct, age_minutes, None)


# ----------------------------------------------------------------------
# 45g: Gain-saturation circuit breaker.
# ----------------------------------------------------------------------

def evaluate_gain_saturation(bot, current_price: float, trigger_source: str) -> bool:
    """45g — evaluate the gain-saturation breaker for this coin.

    Counts positive-PnL sells inside the current management period
    (= since the first ALLOCATE after the last DEALLOCATE on this
    symbol; ALLOCATE-update does NOT shift the start). When the count
    reaches the effective N (per-coin override > global default), arms
    the breaker: sets `_gain_saturation_triggered`, emits the
    `tf_exit_saturated` event, and lets the existing pending_liquidation
    pipeline in grid_runner do the actual force-sell + DEALLOCATE row.

    trigger_source: "post_sell" (called from check_price_and_execute
    after a positive sell) or "proactive_tick" (called from the main
    loop in grid_runner, covers coins that already have counter>=N at
    deploy time or whose holdings hit 0 with no pending sells).

    Returns True if the breaker fired this call, False otherwise.
    Idempotent: a second call after the first trigger is a no-op.
    """
    if bot.managed_by != "tf":
        return False
    if not bot.tf_exit_after_n_enabled:
        return False
    if bot._gain_saturation_triggered:
        return False
    # Mutually exclusive with the other latched exits (priority order
    # mirrors check_price_and_execute).
    if (bot._stop_loss_triggered
            or bot._trailing_stop_triggered
            or bot._take_profit_triggered
            or bot._profit_lock_triggered):
        return False
    if bot.trade_logger is None:
        return False

    from bot.trend_follower.gain_saturation import (
        count_positive_sells_since,
        get_period_start,
        resolve_effective_n,
    )

    effective_n = resolve_effective_n(
        bot.tf_exit_after_n_default,
        bot.tf_exit_after_n_override,
    )
    if effective_n <= 0:
        return False

    period_start = get_period_start(bot.trade_logger.client, bot.symbol)
    if period_start is None:
        return False

    pos_count = count_positive_sells_since(
        bot.trade_logger.client, bot.symbol, period_start
    )
    if pos_count < effective_n:
        return False

    unrealized = (
        (current_price - bot.state.avg_buy_price) * bot.state.holdings
        if bot.state.avg_buy_price > 0 and bot.state.holdings > 0
        else 0.0
    )
    was_override = bot.tf_exit_after_n_override is not None
    logger.warning(
        f"[{bot.symbol}] GAIN-SATURATION TRIGGERED ({trigger_source}): "
        f"{pos_count} positive sells ≥ N={effective_n} "
        f"({'override' if was_override else 'default'}). "
        f"Holdings={bot.state.holdings:.6f}, unrealized ${unrealized:.2f}."
    )
    # Set the flag BEFORE any side effects so a concurrent buy decision
    # sees the breaker as already armed (race protection from §3.5 of
    # the brief). The DEALLOCATE row to trend_decisions_log is emitted
    # by grid_runner when pending_liquidation fires.
    bot._gain_saturation_triggered = True
    log_event(
        severity="info",
        category="safety",
        event="tf_exit_saturated",
        symbol=bot.symbol,
        message=f"TF exit after N={effective_n} positive sells",
        details={
            "n_threshold": effective_n,
            "was_override": was_override,
            "positive_sells_count": pos_count,
            "period_started_at": period_start.isoformat(),
            "residual_holdings": float(bot.state.holdings or 0),
            "residual_avg_buy_price": float(bot.state.avg_buy_price or 0),
            "exit_price": float(current_price),
            "liq_value_usd": float(bot.state.holdings or 0) * float(current_price),
            "liq_pnl_usd": unrealized,
            "total_period_realized_pnl_usd": float(bot.state.realized_pnl or 0),
            "trigger_source": trigger_source,
        },
    )
    # holdings=0 case (49b ALGO scenario): no sell to ride, so flag
    # pending_liquidation directly here. grid_runner picks it up next
    # tick → _force_liquidate sees no holdings → emits the DEALLOCATE
    # row + Telegram cycle-close summary → bot exits gracefully.
    # holdings>0 case: pending_liquidation will be set by the existing
    # cycle_closed path in _check_percentage_and_execute once the
    # forced sells empty the queue. Either way we converge.
    if bot.state.holdings <= 1e-9:
        bot.pending_liquidation = True
    return True


# ----------------------------------------------------------------------
# Brief s70 FASE 2 (2026-05-09): rimossa la legacy `execute_sell`
# (fixed-mode v1) + helper `activate_buy_level`. Avg-cost trading usa
# solo `execute_percentage_sell`.
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Percentage-mode sell (HOT PATH — used by all v3 bots).
# ----------------------------------------------------------------------

def execute_percentage_sell(
    bot,
    price: float,
    sell_amount: Optional[float] = None,
    force_all: bool = False,
) -> Optional[dict]:
    """Execute a percentage-mode sell on avg-cost (brief s70 FASE 1).

    Caller (grid_bot.check_price_and_execute) computes sell_amount from
    capital_per_trade / current_price. If force_all=True (TF stop-loss /
    trailing / take-profit / profit-lock / gain-saturation / bearish
    rotation), sells the full state.holdings in one trade.
    """
    from bot.grid.dust_handler import handle_step_size_dust, handle_economic_dust

    if bot.state.holdings <= 0:
        logger.info(f"No holdings left to sell {bot.symbol}, skipping pct sell.")
        return None

    # Determine sell amount. force_all (TF override) wins; otherwise the
    # caller-provided amount (default capital_per_trade / price); fallback
    # to all holdings if no per-trade size configured. Always clamp to
    # current holdings so we never oversell.
    if force_all:
        amount = bot.state.holdings
    elif sell_amount is not None and sell_amount > 0:
        amount = min(sell_amount, bot.state.holdings)
    elif bot.capital_per_trade > 0 and price > 0:
        amount = min(bot.capital_per_trade / price, bot.state.holdings)
    else:
        amount = bot.state.holdings

    # Mirror the same guards as _execute_sell
    if bot.min_profit_pct > 0 and bot.state.avg_buy_price > 0:
        min_price = bot.state.avg_buy_price * (1 + bot.min_profit_pct / 100)
        if price < min_price:
            logger.info(
                f"SKIP: pct sell at {fmt_price(price)} below min profit target "
                f"(need {fmt_price(min_price)}, {bot.min_profit_pct:.1f}% above avg buy)"
            )
            return None

    # 68a: Strategy A guard checks avg_buy_price (canonical avg-cost).
    # Brief s70 FASE 1: redundant safety net — the new trigger in
    # check_price_and_execute already gates on price >= avg×(1+sell_pct/100),
    # so price < avg can only reach here via TF force-liquidate path.
    # Kept anyway: cheap, preserves invariant for any future caller.
    if bot.strategy == "A" and price < bot.state.avg_buy_price:
        tf_override = (
            bot.managed_by in ("tf", "tf_grid")
            and (bot._stop_loss_triggered
                 or bot._trailing_stop_triggered
                 or bot._take_profit_triggered
                 or bot._profit_lock_triggered
                 or bot._gain_saturation_triggered
                 or bot.pending_liquidation)
        )
        if tf_override:
            if bot._stop_loss_triggered:
                reason = "STOP-LOSS"
            elif bot._trailing_stop_triggered:
                reason = "TRAILING-STOP"
            elif bot._take_profit_triggered:
                reason = "TAKE-PROFIT"
            elif bot._profit_lock_triggered:
                reason = "PROFIT-LOCK"
            elif bot._gain_saturation_triggered:
                reason = "GAIN-SATURATION"
            else:
                reason = "BEARISH EXIT"
            logger.warning(
                f"{reason} OVERRIDE: Pct sell at {fmt_price(price)} < "
                f"avg cost {fmt_price(bot.state.avg_buy_price)} ({bot.symbol})."
            )
        else:
            logger.info(
                f"BLOCKED: Pct sell at {fmt_price(price)} < avg cost {fmt_price(bot.state.avg_buy_price)}. "
                f"Strategy A never sells at loss."
            )
            return None

    # Round to valid step size and validate against exchange filters
    if bot._exchange_filters:
        # 66a Step 2 — dust prevention at the source.
        # If selling `amount` would leave a residual below the exchange's
        # min sellable size, sell-all instead. Prevents dust creation
        # upstream — no more silent queue desync via the pop paths in
        # dust_handler.py (which were one of the 4 sources of the +29%
        # bias certified in formula_verification_s66.md). The dust
        # handlers below remain as a safety net for legacy/multi-lot
        # dust still in the queue at restart.
        step_size = float(bot._exchange_filters.get("lot_step_size") or 0)
        min_qty = float(bot._exchange_filters.get("min_qty") or 0)
        min_notional = float(bot._exchange_filters.get("min_notional") or 0)
        min_sellable = max(
            step_size,
            min_qty,
            min_notional / price if price > 0 else 0,
        )
        if min_sellable > 0:
            residual = bot.state.holdings - amount
            if 0 < residual < min_sellable * 1.5:
                logger.info(
                    f"[{bot.symbol}] DUST PREVENTION: residual {residual:.8f} < "
                    f"1.5x min_sellable ({min_sellable * 1.5:.8f}). "
                    f"Selling all {bot.state.holdings:.8f} instead of {amount:.8f}."
                )
                amount = bot.state.holdings

        from utils.exchange_filters import round_to_step, validate_order
        amount = round_to_step(amount, bot._exchange_filters["lot_step_size"])
        if handle_step_size_dust(bot, amount, price):
            return None
        valid, reason_reject = validate_order(bot.symbol, amount, price, bot._exchange_filters)
        if not valid:
            if handle_economic_dust(bot, price, reason_reject):
                return None
            logger.warning(f"[{bot.symbol}] SELL order rejected: {reason_reject}")
            return None

    # 66a Step 3: live mode (testnet or mainnet) sends a real market SELL
    # to Binance. Fill price, revenue, and fee come from the exchange
    # response. Paper mode keeps the legacy simulated path unchanged.
    # Brief 71a Task 5: freeze check_price (trigger reference) for reason
    # string — fill_price post-slippage can sit on the opposite side of
    # the trigger threshold and used to make `reason` lie.
    check_price = price
    slippage_pct = 0.0
    exchange_order_id = None
    fee_currency = "USDT"
    if TradingMode.is_live() and bot.exchange is not None:
        from bot.exchange_orders import place_market_sell
        res = place_market_sell(bot.exchange, bot.symbol, amount)
        if res is None:
            # Order failed or did not fill — no state change. Retry on next tick.
            return None
        amount = res["filled_amount"]
        price = res["avg_price"]
        revenue = res["cost"]
        fee = res["fee_cost"]
        fee_currency = res["fee_currency"] or "USDT"
        exchange_order_id = res["order_id"]
        if check_price > 0:
            slippage_pct = (price - check_price) / check_price * 100
    else:
        revenue = amount * price
        fee = revenue * bot.FEE_RATE
    holdings_value_before = bot.state.holdings * price

    # 66a (Operation Clean Slate): canonical avg-cost.
    #   cost_basis = avg_buy_price × sell_qty
    #   avg_buy_price does NOT change on sell.
    # The accounting identity (Realized + Unrealized = Total P&L) closes
    # by construction. Replaces 53a (queue walk-and-sum) which produced
    # +29% cumulative bias on the v3 dataset because the in-RAM
    # _pct_open_positions queue silently desynced from the DB-rebuildable
    # FIFO replay (dust pop without log, 60c double-call, 53a fossil,
    # Strategy A skip-then-walk). Avg-cost is robust to all four sources
    # because it depends only on (avg_buy_price, holdings) — two scalars
    # the bot already maintains correctly on every buy. See
    # audits/2026-05-08_pre-clean-slate/formula_verification_s66.md.
    # 68a: snapshot avg_buy_price before any state mutation so the reason
    # string can reference it accurately. Without this, after a full-empty
    # sell the avg gets reset to 0 below and the reason would log a wrong
    # value.
    sell_avg_cost = bot.state.avg_buy_price
    cost_basis = amount * sell_avg_cost
    buy_fee = cost_basis * bot.FEE_RATE  # backward-compat for state.total_fees
    # 52a: paper-mode realized_pnl excludes fees (see _execute_sell comment).
    realized_pnl = revenue - cost_basis

    # Brief s70 FASE 1: forensic audit trail on avg-cost.
    # ~20 sells/day cluster-wide; cheap. If a future report disagrees
    # with the broker, we can replay these events to find which trade
    # introduced drift. Best-effort — log_event swallows DB errors.
    #
    # TODO 62a (Phase 2): this audit is written before log_trade. If
    # log_trade fails (60c double-call → DB safety trigger), the audit
    # becomes orphaned. Move audit AFTER log_trade success in Phase 2.
    try:
        log_event(
            severity="info",
            category="trade_audit",
            event="sell_avg_cost_detail",
            symbol=bot.symbol,
            message=(
                f"Sell @ avg cost {fmt_price(sell_avg_cost)}, "
                f"amount={amount}, pnl=${realized_pnl:.4f}"
            ),
            details={
                "avg_buy_price": float(sell_avg_cost),
                "sell_price": float(price),
                "amount": float(amount),
                "cost_basis": float(cost_basis),
                "revenue": float(revenue),
                "realized_pnl": float(realized_pnl),
                "managed_by": getattr(bot, "managed_by", "grid"),
            },
        )
    except Exception:
        pass

    # Brief 70a Parte 4 (S70 2026-05-10): post-fill warning su slippage che
    # porta il fill sotto avg_buy_price. Il trigger pre-trade ha visto
    # check_price >= avg × (1+sell_pct/100+FEE)/(1-FEE) e ha lasciato
    # passare; lo slippage sul market order può comunque portare il fill
    # sotto avg (book sottile, flash event). Non blocca il trade (ordine
    # già eseguito su exchange), solo loggato in bot_events_log per
    # visibility post-hoc. No Telegram. Esclude TF force-liquidate path
    # (sell sotto avg è atteso per design su stop-loss / trailing / etc.).
    if price < sell_avg_cost and sell_avg_cost > 0:
        tf_force_path = (
            getattr(bot, "managed_by", "grid") in ("tf", "tf_grid")
            and (bot._stop_loss_triggered or bot._trailing_stop_triggered
                 or bot._take_profit_triggered or bot._profit_lock_triggered
                 or bot._gain_saturation_triggered or bot.pending_liquidation)
        )
        if not tf_force_path:
            gap_pct = (price - sell_avg_cost) / sell_avg_cost * 100
            try:
                log_event(
                    severity="warn",
                    category="trade_audit",
                    event="slippage_below_avg",
                    symbol=bot.symbol,
                    message=(
                        f"Slippage exceeded: fill {fmt_price(price)} below avg cost "
                        f"{fmt_price(sell_avg_cost)} ({gap_pct:+.2f}%)"
                    ),
                    details={
                        "fill_price": float(price),
                        "avg_buy_price": float(sell_avg_cost),
                        "gap_pct": float(gap_pct),
                        "sell_pct_config": float(getattr(bot, "sell_pct", 0) or 0),
                        "implied_slippage_pct": float(
                            (getattr(bot, "sell_pct", 0) or 0) - gap_pct
                        ),
                        "managed_by": getattr(bot, "managed_by", "grid"),
                        "realized_pnl": float(realized_pnl),
                    },
                )
            except Exception:
                pass

    # Brief s70 FASE 1: avg-cost trading — no FIFO queue to consume.
    # TODO 62a (Phase 2): these state mutations happen BEFORE log_trade.
    # If log_trade fails (60c), state is desynced from DB. Make atomic.
    bot.state.total_received += revenue
    bot.state.total_fees += fee + buy_fee
    bot.state.holdings -= amount
    bot.state.realized_pnl += realized_pnl
    bot.state.daily_realized_pnl += realized_pnl

    # 39b: a profitable sell releases the stop-buy gate (event-based
    # hysteresis). A rebound in price alone does NOT re-enable buys —
    # we wait for a real profit event to confirm the cycle is digested.
    if bot._stop_buy_active and realized_pnl > 0:
        bot._stop_buy_active = False
        logger.info(
            f"[{bot.symbol}] STOP-BUY RESET: profitable sell ${realized_pnl:.2f} "
            f"cleared the block. Buys re-enabled."
        )
        log_event(
            severity="info",
            category="safety",
            event="stop_buy_cleared",
            symbol=bot.symbol,
            message=f"Manual stop-buy reset after profitable sell ${realized_pnl:.2f}",
            details={"realized_pnl": realized_pnl},
        )

    # Brief s70 FASE 1: reset state when fully sold out. Single
    # condition: holdings → 0. _pct_last_buy_price reset only fires on
    # full exit (was tied to empty queue pre-fix; now tied to scalar
    # holdings). After a partial avg-cost sell holdings stay positive
    # and the buy reference is preserved.
    if bot.state.holdings <= 0:
        bot.state.holdings = 0
        bot.state.avg_buy_price = 0
        bot._pct_last_buy_price = price
        # Brief 70a Parte 3 (S70): reset sell ladder reference on full
        # sell-out. Next cycle's first sell will use avg_cost as reference.
        bot._last_sell_price = 0.0
        logger.info(
            f"[{bot.symbol}] Fully sold out. Buy reference reset to {fmt_price(price)}"
        )
    else:
        # Brief 70a Parte 3: partial sell — track for next ladder step.
        # Grid manual reads this in check_price_and_execute; TF/tf_grid
        # ignore _last_sell_price (their trigger formula is unchanged).
        bot._last_sell_price = price

    bot._daily_trade_count += 1
    bot._last_trade_time = datetime.utcnow()

    trade_pnl_pct = (realized_pnl / cost_basis * 100) if cost_basis > 0 else 0

    # 39a/39c/45f/45g: tag the reason so the trade log + Haiku commentary
    # can distinguish forced exits from normal pct sells.
    # Brief 71a Task 5: append check + slippage tail whenever slippage is
    # non-trivial (≥0.05%). Pct/Greed reasons use check_price in the
    # narrative since they reference the trigger threshold, not the fill.
    slip_tail = (
        f" → fill {fmt_price(price)} (slippage {slippage_pct:+.2f}%)"
        if abs(slippage_pct) >= 0.05 else ""
    )
    if bot._stop_loss_triggered:
        reason = (
            f"STOP-LOSS: price {fmt_price(price)} forces liquidation "
            f"(avg cost {fmt_price(sell_avg_cost)}, threshold {bot.tf_stop_loss_pct:.0f}% of open value)"
        )
    elif bot._trailing_stop_triggered:
        reason = (
            f"TRAILING-STOP: price {fmt_price(price)} dropped {bot.tf_trailing_stop_pct:.1f}% from "
            f"peak {fmt_price(bot._trailing_peak_price)} (avg cost {fmt_price(sell_avg_cost)})"
        )
    elif bot._take_profit_triggered:
        reason = (
            f"TAKE-PROFIT: price {fmt_price(price)} crystallizes gains "
            f"(avg cost {fmt_price(sell_avg_cost)}, threshold {bot.tf_take_profit_pct:.0f}% of open value)"
        )
    elif bot._profit_lock_triggered:
        reason = (
            f"PROFIT-LOCK: price {fmt_price(price)} locks net gain "
            f"(avg cost {fmt_price(sell_avg_cost)}, threshold {bot.tf_profit_lock_pct:.1f}% of alloc on net PnL)"
        )
    elif bot._gain_saturation_triggered:
        reason = (
            f"GAIN-SATURATION: N positive sells reached, exit at {fmt_price(price)} "
            f"(avg cost {fmt_price(sell_avg_cost)})"
        )
    elif bot.pending_liquidation and bot.managed_by == "tf":
        reason = (
            f"BEARISH EXIT: TF rotation, sell at {fmt_price(price)} "
            f"(avg cost {fmt_price(sell_avg_cost)})"
        )
    elif bot.pending_liquidation and bot.managed_by == "tf_grid":
        reason = (
            f"MANUAL EXIT (tf_grid): sell at {fmt_price(price)} "
            f"(avg cost {fmt_price(sell_avg_cost)})"
        )
    else:
        tp_pct, age_min, tier = get_effective_tp(bot)
        if bot.managed_by in ("tf", "tf_grid") and age_min is not None:
            reason = (
                f"Greed decay sell: check {fmt_price(check_price)} >= avg cost "
                f"{fmt_price(sell_avg_cost)} * (1 + {tp_pct}%) "
                f"(age {age_min:.0f}min, tier {tp_pct}%)"
            )
        else:
            reason = (
                f"Pct sell: check {fmt_price(check_price)} is {bot.sell_pct}% "
                f"above avg cost {fmt_price(sell_avg_cost)}"
            )
    reason = f"{reason}{slip_tail}"

    trade_data = {
        "symbol": bot.symbol,
        "side": "sell",
        "amount": amount,
        "price": price,
        "cost": revenue,
        "fee": fee,
        "strategy": bot.strategy,
        "brain": "grid",
        "reason": reason,
        "mode": bot.mode,
        "realized_pnl": realized_pnl,
        "trade_pnl_pct": trade_pnl_pct,  # for Telegram only, filtered before DB log
        "capital_allocated": bot.capital,
        "holdings_value_before": holdings_value_before,
        "managed_by": getattr(bot, "managed_by", "grid"),
    }
    # 67a: fee_asset only written for real exchange fills (defensive against
    # pre-migration deploys — see buy_pipeline.py for rationale).
    if exchange_order_id:
        trade_data["exchange_order_id"] = exchange_order_id
        trade_data["fee_asset"] = fee_currency

    # 42a: expose greed-decay tier info for Telegram alert. Skip when the
    # sell was forced (stop-loss / take-profit / profit-lock / gain-
    # saturation / bearish) — those have their own reason tags that
    # already dominate the message.
    if (bot.managed_by in ("tf", "tf_grid")
            and not bot._stop_loss_triggered
            and not bot._trailing_stop_triggered
            and not bot._take_profit_triggered
            and not bot._profit_lock_triggered
            and not bot._gain_saturation_triggered
            and not bot.pending_liquidation):
        tp_pct, age_min, _ = get_effective_tp(bot)
        if age_min is not None:
            trade_data["greed_tier_age_min"] = age_min
            trade_data["greed_tier_tp_pct"] = tp_pct

    _LOG_TRADE_KEYS = {
        "symbol", "side", "amount", "price", "fee", "fee_asset", "strategy",
        "brain", "reason", "mode", "exchange_order_id", "realized_pnl",
        "buy_trade_id", "cost", "config_version", "cash_before",
        "capital_allocated", "holdings_value_before", "managed_by",
    }
    trade_db_row = {}
    try:
        trade_db_row = bot.trade_logger.log_trade(
            **{k: v for k, v in trade_data.items() if k in _LOG_TRADE_KEYS}
        )
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

    # Profit skimming: set aside skim_pct% of positive profit into reserve
    if bot.skim_pct > 0 and realized_pnl > 0 and bot.reserve_ledger:
        skim_amount = realized_pnl * (bot.skim_pct / 100)
        try:
            trade_id = trade_db_row.get("id")
            bot.reserve_ledger.log_skim(bot.symbol, skim_amount, trade_id=trade_id,
                                          managed_by=bot.managed_by)
            reserve_total = bot.reserve_ledger.get_reserve_total(
                bot.symbol, force_refresh=True
            )
            trade_data["skim_amount"] = skim_amount
            trade_data["reserve_total"] = reserve_total
            logger.info(
                f"SKIM ${skim_amount:.4f} → reserve total ${reserve_total:.2f} [{bot.symbol}]"
            )
        except Exception as e:
            logger.warning(f"Failed to log skim for {bot.symbol}: {e}")

    logger.info(
        f"SELL {amount:.6f} {bot.symbol} @ {fmt_price(price)} "
        f"(revenue: ${revenue:.2f}, fee: ${fee:.4f}, pnl: ${realized_pnl:.4f}) [pct mode]"
    )
    return trade_data
