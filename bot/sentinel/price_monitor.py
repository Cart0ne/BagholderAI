"""Rolling-window BTC price monitor (Sentinel Sprint 1).

Maintains an in-memory deque of recent price observations and computes
percentage changes over fixed windows (5m, 15m, 1h, 4h, 24h) plus the
"speed_of_fall" accelerating flag.

`speed_of_fall accelerating` definition (per CEO brief):
    The drop in the last third of the 1h window (= last 20 minutes) is
    >= 1.5x the average drop across the full window. Formally:
        abs(change_last_20m) >= 1.5 * abs(change_1h / 3)
    Only true when the move is downward (change_last_20m < 0).
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Optional

from bot.sentinel.inputs.binance_btc import fetch_klines_1m, fetch_ticker_24hr

logger = logging.getLogger("bagholderai.sentinel.price_monitor")

# 24h of 1m ticks plus a margin so 24h change is always available once
# the buffer is warm.
_BUFFER_MAX = 24 * 60 + 10
# Windows in seconds.
_WINDOWS = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "24h": 24 * 60 * 60,
}
# Sub-window used by speed_of_fall: last 20 minutes of the 1h window.
_SOF_SUBWINDOW_S = 20 * 60
# Brief 70b (S70 2026-05-10): floor sul change_1h per evitare falsi
# positivi su mercato laterale. Su 2,827 tick raccolti 6-8 maggio la
# vecchia formula scattava 30% delle volte per pure micro-oscillazioni
# (BTC range ±1%). Solo se l'ora intera è in vero calo (≤ floor)
# valutiamo l'accelerazione della caduta.
_SOF_MIN_DROP_1H_PCT = -0.5


class PriceMonitor:
    """Rolling buffer of (epoch_seconds, price) samples."""

    def __init__(self) -> None:
        self._buf: deque[tuple[float, float]] = deque(maxlen=_BUFFER_MAX)
        self._last_ticker: Optional[dict] = None

    def warm_up_from_klines(self) -> None:
        """Pre-fill the buffer with the last 60 minutes of 1m klines so
        the 1h window is usable from tick 1. Best-effort: a failure
        here is logged but not fatal — the buffer simply starts empty.
        """
        try:
            klines = fetch_klines_1m(limit=60)
        except Exception as e:
            logger.warning(f"Klines warm-up failed: {e}")
            return
        for close_time_ms, close_price in klines:
            self._buf.append((close_time_ms / 1000.0, close_price))
        logger.info(f"Warmed price buffer with {len(klines)} klines")

    def tick(self) -> dict:
        """Fetch the current ticker, append to the buffer, and return a
        dict with the latest price and rolling-window deltas. Raises on
        network/HTTP error so the caller can decide what to do.
        """
        ticker = fetch_ticker_24hr()
        self._last_ticker = ticker
        now = time.time()
        self._buf.append((now, ticker["lastPrice"]))
        return self.snapshot()

    def snapshot(self) -> dict:
        """Compute deltas without hitting the network. Returns a dict
        with btc_price, btc_change_*m, btc_change_*h, btc_change_24h,
        speed_of_fall_accelerating, and samples (count for diagnostics).
        """
        if not self._buf:
            return {"btc_price": None, "samples": 0}

        latest_ts, latest_price = self._buf[-1]
        out: dict = {
            "btc_price": latest_price,
            "samples": len(self._buf),
        }

        for label, seconds in _WINDOWS.items():
            ref = self._price_at_or_before(latest_ts - seconds)
            if ref is None:
                out[f"btc_change_{label}"] = None
            else:
                out[f"btc_change_{label}"] = _pct_change(ref, latest_price)

        # 24h delta from the API ticker is authoritative when available
        # (covers the cold-start case before the buffer has 24h depth).
        if self._last_ticker is not None:
            out["btc_change_24h"] = self._last_ticker.get("priceChangePercent")

        out["speed_of_fall_accelerating"] = self._speed_of_fall_accelerating(
            latest_ts, latest_price
        )
        return out

    def _price_at_or_before(self, target_ts: float) -> Optional[float]:
        """Return the most recent buffered price with timestamp <= target_ts,
        or None if the buffer doesn't extend that far back.
        """
        # Linear scan from the right is fine: buffer is at most ~1500 entries
        # and tick() runs once per minute.
        candidate = None
        for ts, price in self._buf:
            if ts <= target_ts:
                candidate = price
            else:
                break
        return candidate

    def _speed_of_fall_accelerating(
        self, latest_ts: float, latest_price: float
    ) -> bool:
        """True when the drop in the last 20 minutes is >= 1.5x the
        average drop across the full hour, AND the 20m move is negative,
        AND the 1h move itself is a vero calo (<= _SOF_MIN_DROP_1H_PCT).

        Brief 70b: floor su change_1h aggiunto per evitare falsi positivi
        su mercato laterale (vecchio scatto 30% su rumore ±1%).
        """
        ref_1h = self._price_at_or_before(latest_ts - _WINDOWS["1h"])
        ref_20m = self._price_at_or_before(latest_ts - _SOF_SUBWINDOW_S)
        if ref_1h is None or ref_20m is None:
            return False
        change_1h = _pct_change(ref_1h, latest_price)
        change_20m = _pct_change(ref_20m, latest_price)
        if change_20m >= 0:
            return False
        if change_1h > _SOF_MIN_DROP_1H_PCT:
            return False  # 70b: ignora accelerazione su mercato sostanzialmente piatto/up
        # change_1h / 3 = average drop per 20m segment of the hour.
        return abs(change_20m) >= 1.5 * abs(change_1h / 3.0)


def _pct_change(reference: float, current: float) -> float:
    if reference == 0:
        return 0.0
    return (current - reference) / reference * 100.0
