"""
BagHolderAI — Exchange abstraction (S112, 2026-06-29).

Single seam between the trading logic and the venue. Two implementations:
  - BinanceClient: delegates VERBATIM to the existing bot.exchange /
    bot.exchange_orders / utils.exchange_filters functions. With
    EXCHANGE=binance the bot runs the exact same code as before S112
    (invariant: zero behavioural diff on the live testnet).
  - KrakenClient: native ccxt.kraken implementation for the Kraken cutover.

Approccio A (S112b): this seam is built and tested in isolation. The live
hot-path (grid pipelines, state_manager, reconcile) is NOT yet rewired through
it — that wiring is the cutover brief, where it is verified against a real
order. Nothing here is consumed by the running testnet bot, so importing this
package cannot affect the live process.

Normalized order dict — every place_* returns EXACTLY the shape that
bot.exchange_orders._normalize_order_response already produces, so the future
wiring is a drop-in:
    {order_id, filled_amount, avg_price, cost, fee_cost, fee_currency,
     fee_native_amount, fee_base, status, raw}

Note on quote currency: the *effective* quote is always derived per-pair from
the symbol string (e.g. "BTC/USDC" -> USDC). `quote_currency` below is only the
venue default / funding currency, used for labels and balance lookups.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class OrderFillUnconfirmed(Exception):
    """A real order was placed but its fill could NOT be confirmed within the
    poll budget (in-flight / unreadable). The one case a caller must NEVER
    retry (Max, S119): retrying re-orders and double-spends real money. Raised
    only by venues that must poll for the fill after placing (Kraken — its
    AddOrder response carries no fill). BinanceClient never raises it → the
    binance path is unaffected (invariant §3). Callers HALT and reconcile by
    hand instead of re-ordering.
    """

    def __init__(self, symbol: str, side: str, order_id: str, detail: str = ""):
        self.symbol = symbol
        self.side = side
        self.order_id = order_id
        self.detail = detail
        super().__init__(
            f"{side.upper()} {symbol}: fill unconfirmed "
            f"(order_id={order_id or 'n/a'}; {detail})"
        )


class ExchangeClient(ABC):
    """Venue-agnostic trading surface. Subclasses: BinanceClient, KrakenClient."""

    name: str = "base"
    quote_currency: str = ""

    # --- connection / pricing ---
    @abstractmethod
    def test_connection(self) -> dict:
        ...

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> dict:
        ...

    def fetch_price(self, symbol: str) -> float:
        """Convenience: last traded price. Default reads ticker['last']."""
        return float((self.fetch_ticker(symbol) or {}).get("last") or 0)

    # --- market orders (the surface the grid uses today) ---
    # `params` (S118): optional venue-specific order params. The binance path
    # never passes it (invariant §3: BinanceClient ignores it); KrakenClient
    # forwards it to ccxt — used by the Fase 1 "prova generale" to send
    # validate=true orders through the SAME code path the grid uses live.
    @abstractmethod
    def place_market_buy(self, symbol: str, quote_amount: float,
                         params: Optional[dict] = None) -> Optional[dict]:
        """Market BUY for `quote_amount` of quote currency worth of `symbol`."""
        ...

    @abstractmethod
    def place_market_buy_base(self, symbol: str, base_amount: float,
                              params: Optional[dict] = None) -> Optional[dict]:
        """Market BUY for a base-asset `base_amount` (lot-step rounded by caller)."""
        ...

    @abstractmethod
    def place_market_sell(self, symbol: str, base_amount: float,
                          params: Optional[dict] = None) -> Optional[dict]:
        """Market SELL of `base_amount` base asset (lot-step rounded by caller)."""
        ...

    # --- account / reconcile ---
    @abstractmethod
    def fetch_balance(self) -> dict:
        ...

    @abstractmethod
    def fetch_my_trades(self, symbol: str, limit: int = 50) -> list:
        ...

    # --- market info ---
    @abstractmethod
    def fetch_filters(self, symbol: str) -> dict:
        """{min_notional, lot_step_size, min_qty} for `symbol`."""
        ...

    @abstractmethod
    def get_all_symbols(self, quote_suffix: Optional[str] = None) -> list:
        """Tradeable symbols on the venue, optionally filtered by quote suffix
        (e.g. "/USDC"). Defaults to the venue's own quote when None."""
        ...

    # --- advanced order primitives ---
    # Kraken cutover surface (AddOrderBatch / EditOrder / cancel_all_after /
    # fee-tier). Binance's grid never needs these (market-order-on-trigger), so
    # the base raises loudly rather than silently no-op'ing. KrakenClient
    # overrides them.
    def place_limit_order(
        self, symbol: str, side: str, base_amount: float, price: float, **kw
    ) -> Optional[dict]:
        raise NotImplementedError(f"{self.name}: place_limit_order not supported")

    def place_order_batch(self, symbol: str, orders: list) -> Optional[list]:
        raise NotImplementedError(f"{self.name}: place_order_batch not supported")

    def edit_order(self, order_id: str, symbol: Optional[str] = None, **changes) -> Optional[dict]:
        raise NotImplementedError(f"{self.name}: edit_order not supported")

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Optional[dict]:
        raise NotImplementedError(f"{self.name}: cancel_order not supported")

    def cancel_all(self, symbol: Optional[str] = None) -> Optional[dict]:
        raise NotImplementedError(f"{self.name}: cancel_all not supported")

    def cancel_all_after(self, timeout_seconds: int) -> Optional[dict]:
        """Dead-man's switch: exchange auto-cancels resting orders if not
        refreshed within `timeout_seconds`. Built but DISARMED (D3, S112b):
        home for the future anti-blackout guard."""
        raise NotImplementedError(f"{self.name}: cancel_all_after not supported")

    def fee_tier(self, symbol: Optional[str] = None) -> dict:
        """Current maker/taker fee + 30d volume."""
        raise NotImplementedError(f"{self.name}: fee_tier not supported")

    def taker_fee_rate(self, symbol: Optional[str] = None) -> float:
        """Current taker fee as a FRACTION (0.008 = 0.80%), for the grid's
        dynamic fee_rate (S118, K.1 Fase 1). Only venues with real, tiered
        fees implement this (Kraken); the binance path keeps GridBot's
        FEE_RATE constant and never calls it."""
        raise NotImplementedError(f"{self.name}: taker_fee_rate not supported")
