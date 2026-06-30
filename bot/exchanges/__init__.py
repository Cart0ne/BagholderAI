"""
Exchange factory (S112) — selects the venue client from the EXCHANGE flag.

    from bot.exchanges import create_client
    client = create_client()            # default: reads config.settings.EXCHANGE
    client = create_client("kraken")    # explicit override (tests / cutover)

KrakenClient is imported lazily so the binance path never pulls in any
kraken-specific code (keeps the §3 invariant: EXCHANGE=binance unchanged).
"""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import EXCHANGE

from .base import ExchangeClient
from .binance_client import BinanceClient

logger = logging.getLogger("bagholderai.exchanges")


def create_client(exchange_name: Optional[str] = None) -> ExchangeClient:
    name = (exchange_name or EXCHANGE or "binance").lower()
    if name == "binance":
        return BinanceClient()
    if name == "kraken":
        # Lazy: avoid importing the Kraken implementation on the binance path.
        from .kraken_client import KrakenClient
        return KrakenClient()
    raise ValueError(
        f"Unknown EXCHANGE={name!r} (expected 'binance' or 'kraken')"
    )


__all__ = ["ExchangeClient", "BinanceClient", "create_client"]
