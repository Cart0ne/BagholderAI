"""Fear & Greed Index input (Sentinel Sprint 2 slow loop).

Public wrapper around alternative.me's free F&G endpoint. The index
updates ~once per day and is the primary signal driving regime
detection (extreme_fear / fear / neutral / greed / extreme_greed).

Endpoint: https://api.alternative.me/fng/?limit=1
No authentication, generous rate limit.

Design rule for slow-loop inputs: NEVER raise. On any error (network,
HTTP non-200, malformed JSON, missing fields) return None and log a
warning. The slow loop falls back to "neutral" regime — the fast loop
keeps running undisturbed.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger("bagholderai.sentinel.alternative_fng")

_ENDPOINT = "https://api.alternative.me/fng/"
_TIMEOUT = 10  # seconds


def fetch() -> Optional[dict]:
    """Fetch the latest Fear & Greed Index value.

    Returns dict on success:
        {
            "fng_value": int (0-100),
            "fng_label": str ("Extreme Fear" | "Fear" | "Neutral" |
                              "Greed" | "Extreme Greed"),
            "fng_timestamp": int (unix epoch seconds, when the index
                                  was calculated by alternative.me),
        }

    Returns None on any failure. Never raises.
    """
    try:
        r = requests.get(_ENDPOINT, params={"limit": 1}, timeout=_TIMEOUT)
    except requests.RequestException as e:
        logger.warning(f"F&G fetch failed (network): {e}")
        return None

    if r.status_code != 200:
        logger.warning(f"F&G fetch failed (HTTP {r.status_code})")
        return None

    try:
        payload = r.json()
    except ValueError as e:
        logger.warning(f"F&G fetch failed (JSON parse): {e}")
        return None

    data = payload.get("data")
    if not data or not isinstance(data, list):
        logger.warning(f"F&G fetch failed (missing 'data' list): {payload}")
        return None

    row = data[0]
    try:
        return {
            "fng_value": int(row["value"]),
            "fng_label": str(row["value_classification"]),
            "fng_timestamp": int(row["timestamp"]),
        }
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"F&G fetch failed (malformed row {row}): {e}")
        return None
