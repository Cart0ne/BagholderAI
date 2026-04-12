"""
BagHolderAI - Trend Follower Classifier
Classifies each coin's trend signal based on indicator values.
"""

import logging

logger = logging.getLogger("bagholderai.trend.classifier")


def classify_signal(coin: dict, config: dict) -> dict:
    """
    Classify a coin's trend based on indicator values.
    Mutates the coin dict in-place, adding 'signal' and 'signal_strength' fields.
    Returns the coin dict for convenience.

    Rules:
        BULLISH:   EMA fast > EMA slow AND RSI > 50 AND ATR > ATR average
        BEARISH:   EMA fast < EMA slow AND RSI < 50 AND ATR > ATR average
        SIDEWAYS:  ATR > ATR average BUT EMAs close together OR RSI 45-55
        NO_SIGNAL: ATR <= ATR average (market too flat to trade)
    """
    ema_fast = coin["ema_fast"]
    ema_slow = coin["ema_slow"]
    rsi = coin["rsi"]
    atr = coin["atr"]
    atr_avg = coin["atr_avg"]

    # Signal strength: used for ranking bullish candidates
    signal_strength = abs(rsi - 50) + (atr / atr_avg if atr_avg > 0 else 0)

    # Classification
    if atr <= atr_avg:
        signal = "NO_SIGNAL"
    else:
        ema_diff_pct = abs(ema_fast - ema_slow) / ema_slow * 100 if ema_slow > 0 else 0
        emas_close = ema_diff_pct < 0.5
        rsi_neutral = 45 <= rsi <= 55

        if emas_close or rsi_neutral:
            signal = "SIDEWAYS"
        elif ema_fast > ema_slow and rsi > 50:
            signal = "BULLISH"
        elif ema_fast < ema_slow and rsi < 50:
            signal = "BEARISH"
        else:
            signal = "SIDEWAYS"

    coin["signal"] = signal
    coin["signal_strength"] = round(signal_strength, 2)
    return coin
