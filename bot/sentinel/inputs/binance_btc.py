"""Binance public-API wrappers for BTC price (Sentinel Sprint 1).

Two endpoints:
    fetch_ticker_24hr()  -> last price, 24h change %
    fetch_klines_1m()    -> last N 1-minute klines for warm-up

Both call api.binance.com (spot). No API key required. Network errors
are surfaced as exceptions; the caller decides how to react.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger("bagholderai.sentinel.binance_btc")

_BASE = "https://api.binance.com"
_TIMEOUT = 10  # seconds


def to_binance_symbol(symbol: str) -> str:
    """Normalize a bot_config symbol to a Binance spot symbol.

    'BONK/USDT' -> 'BONKUSDT'. Kraken /USD pairs have no Binance twin, so
    they map to their /USDT twin as a volatility/price PROXY (S122,
    sherpa-on-kraken): 'BTC/USD' -> 'BTCUSDT'. Rationale: BTC/USDT and
    BTC/USD realized volatility are effectively identical, and Sherpa already
    reads Binance public data for regime/funding (decision S112, EU-ok).
    Only /USD is remapped → the /USDT path is BYTE-IDENTICAL to before.

    KNOWN LIMIT (not resolved, do not treat as fixed): the proxy holds
    tightly on BTC; on SOL and especially BONK (Fase 3) the cross-venue
    volatility divergence can be larger. Revisit when Kraken goes multi-coin.
    """
    if symbol.endswith("/USD"):
        symbol = symbol[: -len("/USD")] + "/USDT"
    return symbol.replace("/", "")


def fetch_ticker_24hr(symbol: str = "BTCUSDT") -> dict:
    """GET /api/v3/ticker/24hr — last price, 24h change %.

    Returns dict with keys: lastPrice (float), priceChangePercent (float),
    highPrice (float), lowPrice (float). Raises requests.RequestException
    on network/HTTP error.
    """
    r = requests.get(
        f"{_BASE}/api/v3/ticker/24hr",
        params={"symbol": symbol},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    raw = r.json()
    return {
        "lastPrice": float(raw["lastPrice"]),
        "priceChangePercent": float(raw["priceChangePercent"]),
        "highPrice": float(raw["highPrice"]),
        "lowPrice": float(raw["lowPrice"]),
    }


def fetch_price(symbol: str) -> float:
    """GET /api/v3/ticker/price — single price quote. Light endpoint
    used by Sherpa to record symbol_price on each proposal.
    """
    r = requests.get(
        f"{_BASE}/api/v3/ticker/price",
        params={"symbol": symbol},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    raw = r.json()
    return float(raw["price"])


def fetch_klines_1m(symbol: str = "BTCUSDT", limit: int = 60) -> list[tuple[int, float]]:
    """GET /api/v3/klines?interval=1m — used at startup to warm the
    rolling-price buffer instead of waiting an hour. Returns a list of
    (close_time_ms, close_price) tuples in chronological order.
    """
    r = requests.get(
        f"{_BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1m", "limit": limit},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    raw = r.json()
    # Each kline is [openTime, open, high, low, close, volume, closeTime, ...].
    return [(int(k[6]), float(k[4])) for k in raw]


def fetch_klines_1h(symbol: str, limit: int = 168) -> list[tuple[int, float]]:
    """GET /api/v3/klines?interval=1h — used by Sherpa volatility module
    to compute per-coin rolling stdev over N days (default 168 = 7 days).
    Returns a list of (close_time_ms, close_price) tuples in chronological
    order. Symbol must be Binance format (e.g. 'BTCUSDT', 'BONKUSDT').
    """
    r = requests.get(
        f"{_BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": "1h", "limit": limit},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    raw = r.json()
    return [(int(k[6]), float(k[4])) for k in raw]
