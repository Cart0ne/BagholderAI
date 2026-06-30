"""
KrakenClient — native ccxt.kraken implementation (S112, dormant until cutover).

Venue we migrate to after Binance lost MiCA. Quote = USD for everything
(Board-ratified S112b): BTC/USD, SOL/USD, BONK/USD for the grid; TF picks from
the deep /USD universe. USD is fiat (no MiCA stablecoin restriction); USDC on
Kraken is thin / partly synthetic (see config.settings.KrakenConfig).

ccxt 4.5.50 exposes full unified support for every primitive we need
(createMarketBuyOrderWithCost, createOrders, editOrder, cancelAllOrdersAfter,
fetchTradingFee), so this is pure ccxt — no raw REST.

KEY DIFFERENCES vs Binance (the §5 behavioural divergences):
  - FEES ARE REAL from the first order (no testnet, no synth_fee). The fee is
    charged in the QUOTE currency (USD) for both buy and sell — never in the
    base coin. So `fee_base` is always 0.0 (nothing to subtract from holdings),
    unlike Binance market BUY which takes the fee from the base coin (72a).
  - Market BUY by quote amount uses Kraken's native cost order, not Binance's
    `quoteOrderQty`.

Returns the SAME normalized dict shape as bot.exchange_orders so the cutover
wiring is a drop-in:
    {order_id, filled_amount, avg_price, cost, fee_cost, fee_currency,
     fee_native_amount, fee_base, status, raw}

NOT YET CONSUMED by the live hot-path (Approccio A). Authenticated calls need
the Kraken API key in config/.env (Withdraw OFF); public calls work without it.
The order layer is verified against a real order only at cutover (Kraken has no
testnet) — methods are mock-tested here.
"""

from __future__ import annotations

import logging
from typing import Optional

import ccxt

from config.settings import KrakenConfig
from utils import exchange_filters
from bot.exchange_orders import _alert_rejection  # reuse venue-agnostic ORDER_REJECTED alert

from .base import ExchangeClient

logger = logging.getLogger("bagholderai.exchanges.kraken")


class KrakenClient(ExchangeClient):
    name = "kraken"
    quote_currency = "USD"

    def __init__(self, exchange=None):
        if exchange is not None:
            self._exchange = exchange  # tests inject a mock
            return
        cfg = {
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        if KrakenConfig.API_KEY and KrakenConfig.SECRET:
            cfg["apiKey"] = KrakenConfig.API_KEY
            cfg["secret"] = KrakenConfig.SECRET
        ex = ccxt.kraken(cfg)
        # Microsecond nonce: the grid spawns one process per coin, all sharing
        # one API key. Kraken nonce is per-key, so ms-resolution nonces can
        # collide across processes → "Invalid nonce". Microseconds widen the
        # gap; the Kraken account "Nonce Window" setting should ALSO be raised
        # (account-side, not code). Revisit at cutover (per-coin subaccounts?).
        ex.nonce = ex.microseconds
        self._exchange = ex

    @property
    def raw(self):
        """Underlying ccxt instance — for cutover call-sites that need it."""
        return self._exchange

    # --- connection / pricing ---
    def test_connection(self) -> dict:
        try:
            ticker = self._exchange.fetch_ticker("BTC/USD")
            result = {
                "status": "connected",
                "mode": "KRAKEN LIVE (USD)",
                "btc_price": ticker.get("last"),
            }
            if KrakenConfig.API_KEY:
                balance = self._exchange.fetch_balance()
                result["total_usd"] = balance.get("USD", {}).get("total", 0)
            return result
        except ccxt.AuthenticationError:
            return {"status": "auth_error",
                    "message": "Kraken API key invalid or missing. Check .env."}
        except ccxt.NetworkError as e:
            return {"status": "network_error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def fetch_ticker(self, symbol: str) -> dict:
        return self._exchange.fetch_ticker(symbol)

    # --- market orders ---
    def place_market_buy(self, symbol: str, quote_amount: float) -> Optional[dict]:
        """Market BUY for `quote_amount` USD worth of `symbol` (native cost order)."""
        if quote_amount <= 0:
            logger.error(f"[kraken] BUY {symbol}: invalid quote_amount={quote_amount}")
            _alert_rejection(symbol, "buy", "invalid quote_amount",
                             {"quote_amount": quote_amount})
            return None
        try:
            order = self._exchange.create_market_buy_order_with_cost(symbol, quote_amount)
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            logger.error(f"[kraken] BUY {symbol} ${quote_amount:.2f} FAILED: {reason}")
            _alert_rejection(symbol, "buy", reason,
                             {"quote_amount": quote_amount, "exception_type": type(e).__name__})
            return None
        return self._normalize_order_response(order, symbol, "buy")

    def place_market_buy_base(self, symbol: str, base_amount: float) -> Optional[dict]:
        """Market BUY for a base-asset `base_amount` (lot-step rounded by caller)."""
        if base_amount <= 0:
            logger.error(f"[kraken] BUY {symbol}: invalid base_amount={base_amount}")
            _alert_rejection(symbol, "buy", "invalid base_amount", {"base_amount": base_amount})
            return None
        try:
            order = self._exchange.create_order(symbol, "market", "buy", base_amount)
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            logger.error(f"[kraken] BUY {symbol} base={base_amount} FAILED: {reason}")
            _alert_rejection(symbol, "buy", reason,
                             {"base_amount": base_amount, "exception_type": type(e).__name__})
            return None
        return self._normalize_order_response(order, symbol, "buy")

    def place_market_sell(self, symbol: str, base_amount: float) -> Optional[dict]:
        """Market SELL of `base_amount` base asset (lot-step rounded by caller)."""
        if base_amount <= 0:
            logger.error(f"[kraken] SELL {symbol}: invalid base_amount={base_amount}")
            _alert_rejection(symbol, "sell", "invalid base_amount", {"base_amount": base_amount})
            return None
        try:
            order = self._exchange.create_order(symbol, "market", "sell", base_amount)
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            logger.error(f"[kraken] SELL {symbol} {base_amount} FAILED: {reason}")
            _alert_rejection(symbol, "sell", reason,
                             {"base_amount": base_amount, "exception_type": type(e).__name__})
            return None
        return self._normalize_order_response(order, symbol, "sell")

    # --- account / reconcile ---
    def fetch_balance(self) -> dict:
        return self._exchange.fetch_balance()

    def fetch_my_trades(self, symbol: str, limit: int = 50) -> list:
        return self._exchange.fetch_my_trades(symbol, limit=limit)

    # --- market info ---
    def fetch_filters(self, symbol: str) -> dict:
        # ccxt normalizes Kraken precision to TICK_SIZE mode (verified S112b:
        # precisionMode=4), so the Binance helper reads min_notional / min_qty /
        # lot_step_size identically. One source of truth, no Kraken-specific copy.
        return exchange_filters.fetch_filters(self._exchange, symbol)

    def get_all_symbols(self, quote_suffix: Optional[str] = None) -> list:
        self._exchange.load_markets()
        suffix = quote_suffix or f"/{self.quote_currency}"   # default "/USD"
        return [
            s for s, mk in self._exchange.markets.items()
            if s.endswith(suffix) and mk.get("spot", True)
        ]

    # --- advanced order primitives (the Kraken order toolbox, brief §4) ---
    def place_limit_order(self, symbol, side, base_amount, price, **kw) -> Optional[dict]:
        try:
            return self._exchange.create_order(symbol, "limit", side, base_amount, price, kw or {})
        except Exception as e:
            logger.error(f"[kraken] LIMIT {side} {symbol} {base_amount}@{price} FAILED: {e}")
            return None

    def place_order_batch(self, symbol, orders: list) -> Optional[list]:
        """AddOrderBatch via ccxt unified create_orders (≤15 per pair).

        `orders` is a list of ccxt order dicts; symbol is injected when absent.
        """
        prepared = [{**o, "symbol": o.get("symbol", symbol)} for o in orders]
        try:
            return self._exchange.create_orders(prepared)
        except Exception as e:
            logger.error(f"[kraken] BATCH {symbol} ({len(prepared)} orders) FAILED: {e}")
            return None

    def edit_order(self, order_id, symbol=None, **changes) -> Optional[dict]:
        try:
            return self._exchange.edit_order(
                order_id, symbol,
                changes.get("type", "limit"), changes.get("side"),
                changes.get("amount"), changes.get("price"),
                changes.get("params", {}),
            )
        except Exception as e:
            logger.error(f"[kraken] EDIT {order_id} ({symbol}) FAILED: {e}")
            return None

    def cancel_order(self, order_id, symbol=None) -> Optional[dict]:
        try:
            return self._exchange.cancel_order(order_id, symbol)
        except Exception as e:
            logger.error(f"[kraken] CANCEL {order_id} ({symbol}) FAILED: {e}")
            return None

    def cancel_all(self, symbol=None) -> Optional[dict]:
        try:
            return self._exchange.cancel_all_orders(symbol)
        except Exception as e:
            logger.error(f"[kraken] CANCEL_ALL ({symbol}) FAILED: {e}")
            return None

    def cancel_all_after(self, timeout_seconds: int) -> Optional[dict]:
        """Dead-man's switch (Kraken CancelAllOrdersAfter). Built but DISARMED
        (D3, S112b): home for the future anti-blackout guard. `timeout_seconds=0`
        disables a previously-armed switch."""
        try:
            return self._exchange.cancel_all_orders_after(timeout_seconds)
        except Exception as e:
            logger.error(f"[kraken] CANCEL_ALL_AFTER({timeout_seconds}) FAILED: {e}")
            return None

    def fee_tier(self, symbol: Optional[str] = None) -> dict:
        """Current maker/taker fee + 30d volume for `symbol` (defaults BTC/USD)."""
        try:
            return self._exchange.fetch_trading_fee(symbol or "BTC/USD")
        except Exception as e:
            logger.error(f"[kraken] fee_tier({symbol}) FAILED: {e}")
            return {}

    # --- normalization ---
    def _normalize_order_response(self, order: dict, symbol: str, side: str) -> Optional[dict]:
        """Same output shape as bot.exchange_orders._normalize_order_response,
        but for Kraken's fee model: real fee in QUOTE currency (USD), fee_base
        always 0.0 (Kraken never deducts the fee from the base coin), no synth."""
        if not order:
            return None
        status = (order.get("status") or "").lower()
        filled = float(order.get("filled") or 0)
        if filled <= 0:
            logger.warning(
                f"[kraken] {side.upper()} {symbol}: order not filled "
                f"(status={status!r}, filled={filled}). No-op. id={order.get('id')}."
            )
            _alert_rejection(symbol, side,
                             f"order not filled (status={status}, filled={filled})",
                             {"order_id": order.get("id"), "status": status, "filled": filled})
            return None

        avg_price = float(order.get("average") or 0)
        cost = float(order.get("cost") or 0)
        if avg_price <= 0 and cost > 0 and filled > 0:
            avg_price = cost / filled

        fee_native = 0.0
        fee_currency = ""
        fee_obj = order.get("fee") or {}
        if fee_obj:
            fee_native = float(fee_obj.get("cost") or 0)
            fee_currency = (fee_obj.get("currency") or "").upper()
        else:
            fees = order.get("fees") or []
            if fees:
                fee_currency = (fees[0].get("currency") or "").upper()
                fee_native = sum(
                    float(f.get("cost") or 0)
                    for f in fees if (f.get("currency") or "").upper() == fee_currency
                )

        # Kraken charges the fee in the QUOTE currency (USD) for both sides.
        # No base-coin commission → fee_base = 0.0 (nothing to subtract from
        # holdings, unlike Binance market BUY). If the broker ever reports a fee
        # in some other currency, keep the native value as fee_cost and warn.
        quote_coin = symbol.split("/")[1].upper() if "/" in symbol else self.quote_currency
        if fee_native > 0 and fee_currency and fee_currency != quote_coin:
            logger.warning(
                f"[kraken] {side.upper()} {symbol}: fee in {fee_currency} "
                f"(expected {quote_coin}); recording native value as fee_cost."
            )
        fee_cost = fee_native

        logger.info(
            f"[kraken] {side.upper()} {symbol} FILLED: amount={filled} "
            f"avg=${avg_price:.6f} cost=${cost:.4f} fee={fee_native} {fee_currency} "
            f"id={order.get('id')}"
        )

        order_id = str(order.get("id") or (order.get("info") or {}).get("txid") or "")
        if not order_id:
            logger.warning(
                f"[kraken] {side.upper()} {symbol}: response carries no order id; "
                f"DB exchange_order_id will be null."
            )

        return {
            "order_id": order_id,
            "filled_amount": filled,
            "avg_price": avg_price,
            "cost": cost,
            "fee_cost": fee_cost,            # USD — what trades.fee gets
            "fee_currency": fee_currency,    # broker's original ticker (audit)
            "fee_native_amount": fee_native,
            "fee_base": 0.0,                 # Kraken never deducts fee from base coin
            "status": status,
            "raw": order,
        }
