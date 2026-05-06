"""Binance futures funding-rate wrapper (Sentinel Sprint 1).

Funding rate updates every 8h (00:00, 08:00, 16:00 UTC). The caller is
expected to cache the value and only refresh past the next funding
window — see funding_monitor.py.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("bagholderai.sentinel.binance_funding")

_BASE = "https://fapi.binance.com"
_TIMEOUT = 10


def fetch_funding_rate(symbol: str = "BTCUSDT") -> dict:
    """GET /fapi/v1/fundingRate — most recent funding rate.

    Returns dict with keys: fundingRate (float, e.g. 0.0001 = 0.01%),
    fundingTime (int, ms epoch). Raises on network/HTTP error.
    """
    r = requests.get(
        f"{_BASE}/fapi/v1/fundingRate",
        params={"symbol": symbol, "limit": 1},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        raise RuntimeError(f"Empty fundingRate response for {symbol}")
    row = rows[0]
    return {
        "fundingRate": float(row["fundingRate"]),
        "fundingTime": int(row["fundingTime"]),
    }
