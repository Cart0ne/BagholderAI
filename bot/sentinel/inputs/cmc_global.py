"""CoinMarketCap global metrics input (Sentinel Sprint 2 slow loop).

Wrapper around CMC Pro API endpoint /v1/global-metrics/quotes/latest.
Returns BTC dominance + total market cap + total volume — context
metrics that Sprint 2 logs but does NOT (yet) feed into regime
detection. A future Sprint 2.5 may use them to refine the F&G-driven
regime call.

Authentication: header X-CMC_PRO_API_KEY, value read from env var
CMC_API_KEY. Free tier: 10,000 credits/month, 1 credit per call. At
6 calls/day (every 4h) that's 180/month — comfortable margin.

Design rule for slow-loop inputs (same as F&G): NEVER raise. On any
error, including missing API key, return None and log a warning. The
slow loop tolerates a missing CMC just fine — regime falls back to F&G
alone, and if both are missing the regime stays "neutral".
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger("bagholderai.sentinel.cmc_global")

_ENDPOINT = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
_TIMEOUT = 10  # seconds
_ENV_KEY = "CMC_API_KEY"


def fetch() -> Optional[dict]:
    """Fetch the latest CMC global metrics.

    Returns dict on success:
        {
            "btc_dominance": float (e.g. 57.3 = 57.3%),
            "total_market_cap_usd": float,
            "total_volume_24h_usd": float,
            "active_cryptocurrencies": int,
        }

    Returns None on any failure. Never raises.
    """
    api_key = os.environ.get(_ENV_KEY)
    if not api_key:
        logger.warning(
            f"{_ENV_KEY} not set — CMC global metrics unavailable. "
            "Slow loop will proceed with F&G only."
        )
        return None

    headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
    try:
        r = requests.get(_ENDPOINT, headers=headers, timeout=_TIMEOUT)
    except requests.RequestException as e:
        logger.warning(f"CMC fetch failed (network): {e}")
        return None

    if r.status_code != 200:
        logger.warning(f"CMC fetch failed (HTTP {r.status_code})")
        return None

    try:
        payload = r.json()
    except ValueError as e:
        logger.warning(f"CMC fetch failed (JSON parse): {e}")
        return None

    data = payload.get("data")
    if not data or not isinstance(data, dict):
        logger.warning(f"CMC fetch failed (missing 'data' dict): {payload}")
        return None

    try:
        usd = data["quote"]["USD"]
        return {
            "btc_dominance": float(data["btc_dominance"]),
            "total_market_cap_usd": float(usd["total_market_cap"]),
            "total_volume_24h_usd": float(usd["total_volume_24h"]),
            "active_cryptocurrencies": int(data["active_cryptocurrencies"]),
        }
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"CMC fetch failed (malformed payload): {e}")
        return None
