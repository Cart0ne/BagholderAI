"""
BagHolderAI - Real exchange order placement (66a Step 3 / brief 67a).

Thin wrapper around ccxt market orders, used in live mode (testnet or
mainnet). Returns a normalized dict that buy_pipeline / sell_pipeline
plug into the existing state-update + log_trade flow.

Paper mode does NOT call this module — _execute_percentage_buy/sell
still simulate fills internally when TradingMode.is_paper().

Design choices (Phase 1, S67):
- Market orders only. Limit orders + async fill tracking postponed —
  market on Binance spot is synchronous fill, simplest path to "Binance
  writes its own realized_pnl on each sell" for accounting verification.
- Buy uses quoteOrderQty (USDT amount). Binance rounds to lot_step_size
  internally. No need to pre-round on our side for buys.
- Sell uses base-coin amount (already rounded by sell_pipeline's
  round_to_step + dust prevention logic).
- Fee read from the ccxt response. If Binance charges fee in BNB
  (when BNB-discount is enabled and user has BNB), we record the
  amount + currency; USDT-equivalent conversion is a Step 5 task.
- Errors → None → caller treats as no-op (no state change, no DB row).
  The bot retries naturally on next tick. Idempotency is not a hard
  guarantee here — if a network error eats the response after the
  exchange filled, we'll have an orphan fill on Binance and no row
  in `trades`. Reconciliation (Step 5) is the safety net.
- On rejection: `log_event(event="ORDER_REJECTED")` to bot_events_log
  + Telegram alert on the private channel (best-effort, both swallow
  errors). Brief 67a mandates these for forensic visibility.

Library choice: ccxt (already used by TF/scanner/exchange_filters), NOT
python-binance. ccxt's sandbox=True is functionally identical to
python-binance's testnet=True (HMAC-SHA256 auth, URL rewriting to
testnet.binance.vision, rate limiting). Coherence with the existing
codebase outweighs literal compliance with brief 67a's library hint.
"""

import logging
from typing import Optional

logger = logging.getLogger("bagholderai.orders")


def _alert_rejection(symbol: str, side: str, reason: str, details: dict) -> None:
    """Best-effort: log ORDER_REJECTED to bot_events_log + Telegram alert.

    Both writes swallow exceptions — order rejection is operational noise,
    must never break the trade flow on top of itself. Lazy imports keep
    this module decoupled from db.* and utils.* unless actually invoked
    (paper-mode tests don't pull these in).
    """
    try:
        from db.event_logger import log_event
        log_event(
            severity="warn",
            category="trade",
            event="ORDER_REJECTED",
            symbol=symbol,
            message=f"{side.upper()} {symbol} rejected: {reason}",
            details=details,
        )
    except Exception as e:
        logger.debug(f"[orders] log_event ORDER_REJECTED failed: {e}")

    try:
        from utils.telegram_notifier import SyncTelegramNotifier
        SyncTelegramNotifier().send_message(
            f"⚠️ <b>{side.upper()} {symbol} rejected</b>\n"
            f"<i>{reason}</i>"
        )
    except Exception as e:
        logger.debug(f"[orders] telegram alert ORDER_REJECTED failed: {e}")


def place_market_buy(exchange, symbol: str, quote_amount_usdt: float) -> Optional[dict]:
    """Place a market BUY for `quote_amount_usdt` USDT worth of `symbol`.

    Returns normalized dict on success, None on failure (logged).
    """
    if quote_amount_usdt <= 0:
        logger.error(f"[orders] BUY {symbol}: invalid quote_amount={quote_amount_usdt}")
        _alert_rejection(symbol, "buy", "invalid quote_amount",
                         {"quote_amount_usdt": quote_amount_usdt})
        return None
    try:
        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side="buy",
            amount=None,
            price=None,
            params={"quoteOrderQty": quote_amount_usdt},
        )
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        logger.error(
            f"[orders] BUY {symbol} ${quote_amount_usdt:.2f} FAILED: {reason}"
        )
        _alert_rejection(symbol, "buy", reason,
                         {"quote_amount_usdt": quote_amount_usdt,
                          "exception_type": type(e).__name__})
        return None

    return _normalize_order_response(order, symbol, "buy")


def place_market_buy_base(exchange, symbol: str, base_amount: float) -> Optional[dict]:
    """Brief 73c (S73 2026-05-12): mainnet-safe BUY using base amount.

    Unlike `place_market_buy` (which uses Binance's `quoteOrderQty` and
    lets Binance derive the base amount from the fill price), this path
    submits `amount=base_amount` directly. The caller MUST round
    `base_amount` to `lot_step_size` before calling. Use this whenever
    `bot._exchange_filters['lot_step_size']` is known.

    Why this exists: on thin testnet books (e.g. BONK lot_step=1, book
    depth $50), `quoteOrderQty=$25` causes Binance to compute amount
    via slipped fill price → not lot-step-divisible → InvalidOrder
    -2010 "Order book liquidity is less than LOT_SIZE filter minimum
    quantity". 6 attempts rejected before LAST SHOT retry succeeded
    (BONK 2026-05-12 10:30-10:32 UTC). With amount-based the order is
    deterministic. Coverage works on mainnet too (mainnet has filters
    populated, so this path is always preferred when filters known).

    Returns normalized dict on success, None on failure.
    """
    if base_amount <= 0:
        logger.error(f"[orders] BUY {symbol}: invalid base_amount={base_amount}")
        _alert_rejection(symbol, "buy", "invalid base_amount",
                         {"base_amount": base_amount})
        return None
    try:
        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side="buy",
            amount=base_amount,
        )
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        logger.error(
            f"[orders] BUY {symbol} base={base_amount} FAILED: {reason}"
        )
        _alert_rejection(symbol, "buy", reason,
                         {"base_amount": base_amount,
                          "exception_type": type(e).__name__})
        return None

    return _normalize_order_response(order, symbol, "buy")


def place_market_sell(exchange, symbol: str, base_amount: float) -> Optional[dict]:
    """Place a market SELL for `base_amount` of base coin in `symbol`.

    `base_amount` must already be rounded to lot_step_size by the caller.
    Returns normalized dict on success, None on failure (logged).
    """
    if base_amount <= 0:
        logger.error(f"[orders] SELL {symbol}: invalid base_amount={base_amount}")
        _alert_rejection(symbol, "sell", "invalid base_amount",
                         {"base_amount": base_amount})
        return None
    try:
        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side="sell",
            amount=base_amount,
        )
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        logger.error(
            f"[orders] SELL {symbol} {base_amount} FAILED: {reason}"
        )
        _alert_rejection(symbol, "sell", reason,
                         {"base_amount": base_amount,
                          "exception_type": type(e).__name__})
        return None

    return _normalize_order_response(order, symbol, "sell")


def _normalize_order_response(order: dict, symbol: str, side: str) -> Optional[dict]:
    """Extract the fields we care about from a ccxt order response.

    Returns None ONLY for a real no-op (filled <= 0). A response with
    status != 'closed' but filled > 0 is a partial fill: the base coin
    IS in the account (Binance has already settled it), so we MUST
    normalize and record it as a real trade. Treating the partial fill
    as a no-op would lose a true position and desync DB from broker
    (brief 74c, BONK orphan 21190 incident 2026-05-12).
    """
    status = (order.get("status") or "").lower()
    filled = float(order.get("filled") or 0)
    if filled <= 0:
        logger.warning(
            f"[orders] {side.upper()} {symbol}: order not filled "
            f"(status={status!r}, filled={filled}). Treating as no-op. "
            f"Order id={order.get('id')}."
        )
        _alert_rejection(
            symbol, side,
            f"order not filled (status={status}, filled={filled})",
            {"order_id": order.get("id"), "status": status, "filled": filled},
        )
        return None

    if status != "closed":
        # Brief 74c (S74 2026-05-12): partial fill. Binance returned
        # status='expired'/'canceled' but filled > 0 — the coins are
        # already in the wallet. Common on thin testnet books (BONK).
        # Log and emit a forensic event, but proceed with normalize:
        # buy_pipeline / sell_pipeline will record it as a real trade.
        amount = order.get("amount")
        logger.warning(
            f"[orders] {side.upper()} {symbol}: PARTIAL FILL "
            f"(status={status!r}, filled={filled}/{amount}). "
            f"Recording as real trade. Order id={order.get('id')}."
        )
        try:
            from db.event_logger import log_event
            log_event(
                severity="warn",
                category="trade",
                event="ORDER_PARTIAL_FILL",
                symbol=symbol,
                message=f"{side.upper()} {symbol} partial fill: {filled}/{amount}",
                details={
                    "order_id": order.get("id"),
                    "status": status,
                    "filled": filled,
                    "amount": amount,
                },
            )
        except Exception as e:
            logger.debug(f"[orders] log_event ORDER_PARTIAL_FILL failed: {e}")

    avg_price = float(order.get("average") or 0)
    cost = float(order.get("cost") or 0)
    if avg_price <= 0 and cost > 0 and filled > 0:
        avg_price = cost / filled  # derive if missing

    fee_native = 0.0
    fee_currency = ""
    fee_obj = order.get("fee") or {}
    if fee_obj:
        fee_native = float(fee_obj.get("cost") or 0)
        fee_currency = (fee_obj.get("currency") or "").upper()
    else:
        # Some Binance responses split fees per fill (fees: [...])
        fees = order.get("fees") or []
        if fees:
            fee_currency = (fees[0].get("currency") or "").upper()
            fee_native = sum(
                float(f.get("cost") or 0)
                for f in fees if (f.get("currency") or "").upper() == fee_currency
            )

    # 67a (CEO verdict 2026-05-08, option A): convert fee to USDT-equivalent
    # before returning. Binance market BUY scales fee from the base coin
    # (BTC/SOL/BONK/...), market SELL scales from USDT, BNB-discount mode
    # scales from BNB. The dashboard, daily report, P&L and reconciliation
    # gate all read `trades.fee` as USDT — keeping the raw value would
    # break every consumer (the BONK trade on 2026-05-08 21:00 showed up
    # as -$3,419 P&L in the private grid dashboard before this fix).
    # `fee_currency` stays as the broker's original ticker for audit.
    #
    # Brief 72a (Fee Unification, S72 2026-05-11): also return `fee_base`,
    # the amount of base coin scaled by Binance as commission. Only > 0
    # when fee_currency == base_coin (typical market BUY). This is what
    # buy_pipeline subtracts from `state.holdings` so it matches the
    # actual wallet balance on Binance. BNB-discount path: fee_base = 0
    # because the BNB commission does NOT touch the symbol's base coin
    # balance (it's paid out of the user's BNB wallet, separate asset).
    base_coin = symbol.split("/")[0].upper() if "/" in symbol else ""
    quote_coin = symbol.split("/")[1].upper() if "/" in symbol else "USDT"
    fee_base = 0.0
    if fee_native <= 0 or not fee_currency:
        fee_usdt = 0.0
    elif fee_currency == quote_coin:
        # Fee already in USDT (typical: market SELL on /USDT pair)
        fee_usdt = fee_native
    elif fee_currency == base_coin and avg_price > 0:
        # Fee in base coin (typical: market BUY on /USDT pair)
        fee_usdt = fee_native * avg_price
        fee_base = fee_native  # 72a: scaled from wallet base balance
    else:
        # BNB-discount path (or other unrelated currency). fee_base stays 0
        # because BNB commission doesn't touch this symbol's base balance.
        # fee_usdt cross-rate lookup is deferred (Step 5); for now record 0
        # so dashboards don't show garbage and log a warning.
        fee_usdt = 0.0
        logger.warning(
            f"[orders] {side.upper()} {symbol}: fee in {fee_currency} "
            f"({fee_native}) cannot be auto-converted to USDT (base={base_coin}, "
            f"quote={quote_coin}). Leaving fee_usdt=0; native amount preserved "
            f"in fee_native_amount key."
        )

    logger.info(
        f"[orders] {side.upper()} {symbol} FILLED: "
        f"amount={filled} avg=${avg_price:.6f} cost=${cost:.4f} "
        f"fee={fee_native} {fee_currency} (~${fee_usdt:.6f}, "
        f"fee_base={fee_base}) id={order.get('id')}"
    )

    return {
        "order_id": str(order.get("id") or ""),
        "filled_amount": filled,
        "avg_price": avg_price,
        "cost": cost,
        "fee_cost": fee_usdt,            # USDT-equivalent — what trades.fee gets
        "fee_currency": fee_currency,    # broker's original ticker (audit)
        "fee_native_amount": fee_native, # raw value, available for future audit cols
        "fee_base": fee_base,            # 72a: base-coin commission (>0 only when
                                          # fee_currency==base_coin); used by
                                          # buy_pipeline to keep state.holdings in
                                          # sync with the real Binance wallet
        "status": status,
        "raw": order,
    }
