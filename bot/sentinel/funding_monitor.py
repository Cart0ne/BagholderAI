"""Funding-rate monitor with 8h cache (Sentinel Sprint 1).

Binance updates the funding rate at 00:00, 08:00, 16:00 UTC. Polling
every minute is wasteful — we cache the value and refresh only after
the next funding window has likely closed. Cache is in-memory: a
restart costs one extra fetch, which is fine.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from bot.sentinel.inputs.binance_funding import fetch_funding_rate

logger = logging.getLogger("bagholderai.sentinel.funding_monitor")

_REFRESH_AFTER_S = 8 * 60 * 60  # re-fetch at most once per 8h window


class FundingMonitor:
    def __init__(self) -> None:
        self._last_value: Optional[float] = None
        self._last_funding_time_ms: Optional[int] = None
        self._last_fetch_ts: float = 0.0

    def get_rate(self) -> Optional[float]:
        """Return the most recent funding rate as a decimal (e.g. 0.0001
        = 0.01%). None if every fetch attempt has failed so far. Refreshes
        from the API at most once per 8h window.
        """
        now = time.time()
        if (
            self._last_value is not None
            and (now - self._last_fetch_ts) < _REFRESH_AFTER_S
        ):
            return self._last_value
        try:
            data = fetch_funding_rate()
            self._last_value = data["fundingRate"]
            self._last_funding_time_ms = data["fundingTime"]
            self._last_fetch_ts = now
            logger.info(f"Funding rate refreshed: {self._last_value}")
        except Exception as e:
            logger.warning(f"Funding rate fetch failed: {e}")
        return self._last_value
