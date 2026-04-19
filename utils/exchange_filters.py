"""
BagHolderAI - Exchange Filter Validation
Fetches and caches Binance exchange filters (MIN_NOTIONAL, LOT_SIZE).
Used by grid bots and (future) Trend Follower to validate orders
before execution, preventing ghost trades and API rejections.
"""

import math
import logging

logger = logging.getLogger("bagholderai.filters")


def fetch_filters(exchange, symbol: str) -> dict:
    """
    Fetch exchange filters for a symbol from ccxt market info.
    Returns dict with min_notional, lot_step_size, min_qty.
    """
    exchange.load_markets()
    market = exchange.markets.get(symbol)
    if not market:
        logger.warning(f"[exchange_filters] Market not found for {symbol}")
        return {"min_notional": 0.0, "lot_step_size": 0.0, "min_qty": 0.0}

    limits = market.get("limits", {})
    cost_limits = limits.get("cost", {})
    amount_limits = limits.get("amount", {})

    min_notional = float(cost_limits.get("min") or 0)
    min_qty = float(amount_limits.get("min") or 0)

    # lot_step_size: for Binance, ccxt precision.amount IS the step size directly
    precision = market.get("precision", {})
    amount_precision = precision.get("amount")
    if amount_precision is not None and float(amount_precision) > 0:
        lot_step_size = float(amount_precision)
    else:
        lot_step_size = 0.0

    filters = {
        "min_notional": min_notional,
        "lot_step_size": lot_step_size,
        "min_qty": min_qty,
    }
    logger.info(
        f"[exchange_filters] {symbol}: min_notional=${min_notional}, "
        f"min_qty={min_qty}, lot_step_size={lot_step_size}"
    )
    return filters


def fetch_and_cache_filters(exchange, symbols: list, supabase_client=None) -> dict:
    """
    Fetch filters for all symbols and optionally cache to Supabase.
    Returns dict of symbol -> filters.
    """
    exchange.load_markets()
    all_filters = {}
    for symbol in symbols:
        all_filters[symbol] = fetch_filters(exchange, symbol)

    if supabase_client:
        for symbol, f in all_filters.items():
            try:
                supabase_client.table("exchange_filters").upsert({
                    "symbol": symbol,
                    "min_notional": f["min_notional"],
                    "lot_step_size": f["lot_step_size"],
                    "min_qty": f["min_qty"],
                }, on_conflict="symbol").execute()
            except Exception as e:
                logger.warning(f"[exchange_filters] Failed to cache {symbol}: {e}")
        logger.info(f"[exchange_filters] Cached filters for {len(all_filters)} symbols")

    return all_filters


def validate_order(symbol: str, amount: float, price: float, filters: dict) -> tuple:
    """
    Validate an order against exchange filters.
    Returns (True, "OK") or (False, "reason").
    """
    if not filters:
        return (True, "OK")  # no filters loaded, skip validation

    if amount <= 0:
        return (False, f"amount={amount} <= 0")

    min_qty = filters.get("min_qty", 0)
    if min_qty > 0 and amount < min_qty:
        return (False, f"amount {amount} < min_qty {min_qty}")

    min_notional = filters.get("min_notional", 0)
    notional = amount * price
    if min_notional > 0 and notional < min_notional:
        return (False, f"MIN_NOTIONAL not met: ${notional:.2f} < ${min_notional:.2f}")

    lot_step_size = filters.get("lot_step_size", 0)
    if lot_step_size > 0:
        from decimal import Decimal
        d_amount = Decimal(str(amount))
        d_step = Decimal(str(lot_step_size))
        remainder = d_amount % d_step
        if remainder != 0:
            return (False, f"amount {amount} not aligned to step_size {lot_step_size}")

    return (True, "OK")


def round_to_step(amount: float, step_size: float) -> float:
    """
    Round amount DOWN to nearest valid step size.
    Uses Decimal to avoid floating-point artifacts (e.g. 3878984.8000000003).

    39h: naive `Decimal(str(amount))` inherits float imprecision — e.g.
    an amount that should be exactly 807.4 can arrive as
    807.39999999999... via an earlier `x * 10 / 10` roundtrip. A plain
    ROUND_DOWN then snaps it to 807.3, leaking 0.1 of dust. Fix: before
    the ROUND_DOWN, nudge the amount by a tiny ABSOLUTE epsilon
    (1e-9 units) so float-repr artifacts snap to the right step-boundary
    without perturbing real sub-step values (e.g. 24231428.99 BONK with
    step=1 must stay 24231428, not round up to 24231429).
    """
    if step_size <= 0:
        return amount
    from decimal import Decimal, ROUND_DOWN

    d_step = Decimal(str(step_size))
    # 1e-9 absolute: smaller than any real Binance step (BTC step is
    # 1e-5, BONK step is 1), big enough to swallow the ~1e-12 epsilon
    # that Decimal(str(float)) can carry from earlier arithmetic.
    d_amount = Decimal(str(amount)) + Decimal("1e-9")
    result = (d_amount / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step
    return float(result)
