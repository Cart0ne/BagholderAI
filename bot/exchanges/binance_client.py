"""
BinanceClient — delegates VERBATIM to the existing Binance code path (S112).

With EXCHANGE=binance the factory returns this. Every method forwards to the
pre-S112 functions in bot.exchange / bot.exchange_orders / utils.exchange_filters,
so behaviour is byte-identical to before this brief (the §3 invariant). This
wrapper is the seam the cutover will rewire the grid through; it is NOT yet
consumed by the live hot-path (Approccio A, S112b).
"""

from __future__ import annotations

from typing import Optional

from bot.exchange import create_exchange, test_connection, fetch_ticker
from bot import exchange_orders
from utils import exchange_filters

from .base import ExchangeClient


class BinanceClient(ExchangeClient):
    name = "binance"
    quote_currency = "USDT"

    def __init__(self, exchange=None):
        # Reuse the EXACT same ccxt instance construction as before S112.
        # Passing `exchange` is for tests (inject a mock); production builds
        # it via create_exchange() identically to the legacy path.
        self._exchange = exchange if exchange is not None else create_exchange()

    @property
    def raw(self):
        """Underlying ccxt instance — for cutover call-sites that still need it."""
        return self._exchange

    # --- connection / pricing ---
    def test_connection(self) -> dict:
        return test_connection(self._exchange)

    def fetch_ticker(self, symbol: str) -> dict:
        return fetch_ticker(self._exchange, symbol)

    # --- market orders ---
    # `params` (S118) is accepted for interface parity but IGNORED here: the
    # binance path must stay byte-identical to pre-S112 (§3 invariant), and
    # nothing on it ever passes params. validate=true is a Kraken-only need.
    def place_market_buy(self, symbol: str, quote_amount: float,
                         params: Optional[dict] = None) -> Optional[dict]:
        return exchange_orders.place_market_buy(self._exchange, symbol, quote_amount)

    def place_market_buy_base(self, symbol: str, base_amount: float,
                              params: Optional[dict] = None) -> Optional[dict]:
        return exchange_orders.place_market_buy_base(self._exchange, symbol, base_amount)

    def place_market_sell(self, symbol: str, base_amount: float,
                          params: Optional[dict] = None) -> Optional[dict]:
        return exchange_orders.place_market_sell(self._exchange, symbol, base_amount)

    # --- account / reconcile ---
    def fetch_balance(self) -> dict:
        return self._exchange.fetch_balance()

    def fetch_my_trades(self, symbol: str, limit: int = 50) -> list:
        return self._exchange.fetch_my_trades(symbol, limit=limit)

    # --- market info ---
    def fetch_filters(self, symbol: str) -> dict:
        return exchange_filters.fetch_filters(self._exchange, symbol)

    def get_all_symbols(self, quote_suffix: Optional[str] = None) -> list:
        self._exchange.load_markets()
        suffix = quote_suffix or "/USDT"
        return [s for s in self._exchange.markets if s.endswith(suffix)]
