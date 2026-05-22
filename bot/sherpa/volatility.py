"""Per-coin volatility multipliers (Sherpa Sprint 2, Brief 81a Block 1).

Computes a per-symbol multiplier so Sherpa proposes different parameters
for different coins. BTC is the anchor (multiplier = 1.0). A coin with
twice BTC's rolling stdev gets multiplier = 2.0 → its sell_pct and
buy_pct widths are doubled relative to BTC.

Metric: standard deviation of log returns over the last 7 days of 1h
klines (168 candles). Chosen over ATR for simplicity (one Binance
endpoint, no high/low extraction) and over raw pct stdev for additivity
across timeframes. The exact metric is interchangeable — the contract
is "BTC anchor, scalar > 0, fallback 1.0 on failure".

Cache: 1h TTL per symbol. The slow loop runs every 4h, so refreshing
volatility every hour is more frequent than the regime — rationale:
volatility is independent of regime and we want the multiplier to
catch up promptly when a coin rotates from quiet to choppy. Still
~24× cheaper than fetching at every Sherpa tick (120s).

Contract: never raises. On any failure returns multiplier 1.0 for the
affected symbol (degrades to "all coins look like BTC"). Logs warn so
the operator can see it in bot_events_log if needed.

Brief 81a explicit constraint: NO hardcoded coin list. The caller
passes the set of active symbols read from bot_config at runtime.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Iterable

from bot.sentinel.inputs.binance_btc import fetch_klines_1h

logger = logging.getLogger("bagholderai.sherpa.volatility")

ANCHOR_SYMBOL = "BTC/USDT"
KLINES_WINDOW_HOURS = 168  # 7 days × 24h
CACHE_TTL_S = 3600          # 1h
DEFAULT_MULTIPLIER = 1.0    # fallback when stdev is unavailable

# Module-level cache: {binance_symbol: (timestamp_s, stdev_value)}
_stdev_cache: dict[str, tuple[float, float]] = {}


def _to_binance_symbol(symbol: str) -> str:
    """'BONK/USDT' -> 'BONKUSDT'. Sherpa stores Grid symbols with the
    slash; Binance REST wants them concatenated."""
    return symbol.replace("/", "")


def _log_returns_stdev(closes: list[float]) -> float:
    """Sample stdev of log returns. Returns 0.0 if fewer than 2 closes
    or if any close is non-positive (corrupt data)."""
    if len(closes) < 2:
        return 0.0
    if any(c <= 0 for c in closes):
        return 0.0
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    n = len(rets)
    if n < 2:
        return 0.0
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    return math.sqrt(var)


def _fetch_stdev(symbol: str) -> float:
    """Fetch 7-day 1h klines and return log-return stdev. Cached for
    CACHE_TTL_S per symbol. Returns 0.0 on any failure (caller decides
    the fallback)."""
    binance_symbol = _to_binance_symbol(symbol)
    now = time.time()
    cached = _stdev_cache.get(binance_symbol)
    if cached is not None and (now - cached[0]) < CACHE_TTL_S:
        return cached[1]
    try:
        klines = fetch_klines_1h(binance_symbol, limit=KLINES_WINDOW_HOURS)
    except Exception as e:
        logger.warning(f"fetch_klines_1h failed for {symbol}: {e}")
        return 0.0
    closes = [c for _, c in klines]
    stdev = _log_returns_stdev(closes)
    if stdev <= 0:
        logger.warning(f"degenerate stdev for {symbol} (got {stdev})")
        return 0.0
    _stdev_cache[binance_symbol] = (now, stdev)
    return stdev


def get_volatility_multipliers(symbols: Iterable[str]) -> dict[str, float]:
    """Return {symbol: multiplier} keyed by the Grid-format symbol
    (e.g. 'BTC/USDT'). BTC is forced to 1.0 (anchor). Others are
    stdev(symbol) / stdev(BTC). On any failure the affected symbol
    gets DEFAULT_MULTIPLIER. If BTC itself can't be fetched, all
    multipliers fall back to 1.0 (no per-coin signal that cycle).
    """
    symbols = list(symbols)
    out: dict[str, float] = {}
    btc_stdev = _fetch_stdev(ANCHOR_SYMBOL)
    if btc_stdev <= 0:
        logger.warning(
            "BTC stdev unavailable; volatility multipliers degraded to 1.0"
        )
        for s in symbols:
            out[s] = DEFAULT_MULTIPLIER
        return out

    for s in symbols:
        if s == ANCHOR_SYMBOL:
            out[s] = 1.0
            continue
        sym_stdev = _fetch_stdev(s)
        if sym_stdev <= 0:
            out[s] = DEFAULT_MULTIPLIER
            continue
        out[s] = round(sym_stdev / btc_stdev, 4)
    return out


def reset_cache() -> None:
    """Test helper — clear the module-level cache between tests."""
    _stdev_cache.clear()
