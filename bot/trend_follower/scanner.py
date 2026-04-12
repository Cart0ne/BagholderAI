"""
BagHolderAI - Trend Follower Scanner
Fetches market data from Binance and calculates technical indicators.
"""

import time
import logging
import pandas as pd

logger = logging.getLogger("bagholderai.trend.scanner")


# ---------------------------------------------------------------------------
# Technical indicator helpers
# ---------------------------------------------------------------------------

def calc_ema(closes: list[float], period: int) -> float:
    """Standard EMA calculation using pandas."""
    series = pd.Series(closes)
    return series.ewm(span=period, adjust=False).mean().iloc[-1]


def calc_rsi(closes: list[float], period: int = 14) -> float:
    """Wilder's RSI."""
    series = pd.Series(closes)
    delta = series.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])


def calc_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> tuple[float, float]:
    """
    Standard ATR: EMA of true range.
    Returns (current_atr, average_atr) where average is the mean of all ATR values.
    """
    h, l, c = pd.Series(highs), pd.Series(lows), pd.Series(closes)
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    atr_series = tr.ewm(span=period, adjust=False).mean()
    current_atr = float(atr_series.iloc[-1])
    avg_atr = float(atr_series.mean())
    return current_atr, avg_atr


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_top_coins(exchange, top_n: int = 50) -> list[dict]:
    """
    1. Fetch all USDT tickers from Binance
    2. Sort by 24h quoteVolume (USDT volume), take top N
    3. For each coin, fetch 4h klines (minimum 50 candles)
    4. Calculate indicators: EMA 20, EMA 50, RSI 14, ATR 14
    5. Return list of dicts with all data
    """
    logger.info(f"Scanning top {top_n} coins by 24h USDT volume...")

    # 1. Fetch all tickers
    tickers = exchange.fetch_tickers()
    usdt_tickers = {
        k: v for k, v in tickers.items()
        if k.endswith("/USDT") and v.get("quoteVolume") and v.get("last")
    }

    # 2. Sort by volume, take top N
    sorted_tickers = sorted(
        usdt_tickers.items(),
        key=lambda x: x[1].get("quoteVolume", 0),
        reverse=True,
    )[:top_n]

    logger.info(f"Found {len(usdt_tickers)} USDT pairs, scanning top {len(sorted_tickers)}")

    # 3+4. Fetch klines and calculate indicators
    coins = []
    for symbol, ticker in sorted_tickers:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe="4h", limit=100)
            if len(ohlcv) < 50:
                logger.warning(f"[{symbol}] Only {len(ohlcv)} candles, need >=50. Skipping.")
                continue

            closes = [c[4] for c in ohlcv]
            highs = [c[2] for c in ohlcv]
            lows = [c[3] for c in ohlcv]

            ema_fast = calc_ema(closes, 20)
            ema_slow = calc_ema(closes, 50)
            rsi = calc_rsi(closes, 14)
            atr, atr_avg = calc_atr(highs, lows, closes, 14)

            coins.append({
                "symbol": symbol,
                "price": ticker["last"],
                "volume_24h": ticker.get("quoteVolume", 0),
                "ema_fast": round(ema_fast, 6),
                "ema_slow": round(ema_slow, 6),
                "rsi": round(rsi, 2),
                "atr": round(atr, 6),
                "atr_avg": round(atr_avg, 6),
            })

            time.sleep(0.2)  # rate limit: 200ms between kline requests

        except Exception as e:
            logger.warning(f"[{symbol}] Failed to scan: {e}")
            continue

    logger.info(f"Scan complete: {len(coins)} coins with indicators")
    return coins
