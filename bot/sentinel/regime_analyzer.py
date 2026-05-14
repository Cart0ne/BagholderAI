"""Regime detection from F&G + CMC data (Sentinel Sprint 2 MVP).

In Sprint 2 the regime is derived from the Fear & Greed Index alone.
CMC global metrics are logged for future analysis (Sprint 2.5) but do
not influence the regime call yet — we have no validated theory on how
BTC dominance should reweight a F&G read.

Output: one of 5 regime strings expected by Sherpa parameter_rules.py
BASE_TABLE: extreme_fear | fear | neutral | greed | extreme_greed.

Boundaries (inclusive low, exclusive high of the next bucket):
    F&G 0–20   → extreme_fear
    F&G 21–40  → fear
    F&G 41–60  → neutral
    F&G 61–80  → greed
    F&G 81–100 → extreme_greed

So F&G=20 is extreme_fear, F&G=21 is fear. Documented here so future
edits don't drift.

Trading-sense mapping for the slow score (consumed by slow_loop.py):
    extreme_fear  → risk 20 / opp 80  (capitulation = buy zone)
    fear          → risk 30 / opp 65
    neutral       → risk 40 / opp 40
    greed         → risk 65 / opp 30
    extreme_greed → risk 80 / opp 20  (euphoria = sell zone, dangerous to add)

Fallback policy:
    F&G None                          → neutral (warning)
    F&G stale (> FNG_MAX_AGE_S)       → neutral (warning)
    F&G valid, CMC None               → regime from F&G (no warning, CMC is bonus)
    Both None                         → neutral (warning)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("bagholderai.sentinel.regime_analyzer")

# 36h = a F&G value older than this triggers fallback to neutral.
# alternative.me updates ~1x/day; 36h covers worst-case 24h cycle +
# margin without being too lax.
FNG_MAX_AGE_S = 36 * 3600

# Regime → (risk_slow, opp_slow). Public so slow_loop can import.
REGIME_SCORE_MAP = {
    "extreme_fear":  (20, 80),
    "fear":          (30, 65),
    "neutral":       (40, 40),
    "greed":         (65, 30),
    "extreme_greed": (80, 20),
}


def _fng_to_regime(fng_value: int) -> str:
    """Map a 0-100 F&G integer to one of the 5 regime buckets."""
    if fng_value <= 20:
        return "extreme_fear"
    if fng_value <= 40:
        return "fear"
    if fng_value <= 60:
        return "neutral"
    if fng_value <= 80:
        return "greed"
    return "extreme_greed"


def determine_regime(
    fng_data: Optional[dict],
    cmc_data: Optional[dict],
    fng_max_age_s: int = FNG_MAX_AGE_S,
    now_unix: Optional[int] = None,
) -> tuple[str, dict]:
    """Decide the current macro regime.

    Args:
        fng_data: dict from alternative_fng.fetch(), or None.
        cmc_data: dict from cmc_global.fetch(), or None. Sprint 2 logs
            only; does not affect the regime.
        fng_max_age_s: how stale F&G can be before we fall back. Default
            36h; override for tests.
        now_unix: current unix time; default time.time(). Override for
            deterministic tests.

    Returns:
        (regime_string, decision_log_dict). The dict is meant to be
        embedded into sentinel_scores.raw_signals for auditability.
    """
    now = now_unix if now_unix is not None else int(time.time())
    log: dict = {
        "fng_used": False,
        "cmc_seen": cmc_data is not None,
        "fallback_reason": None,
    }

    if fng_data is None:
        log["fallback_reason"] = "fng_unavailable"
        logger.warning("F&G data unavailable; regime falls back to neutral")
        return "neutral", log

    fng_value = fng_data.get("fng_value")
    fng_timestamp = fng_data.get("fng_timestamp")
    log["fng_value"] = fng_value
    log["fng_label"] = fng_data.get("fng_label")
    log["fng_timestamp"] = fng_timestamp

    if fng_value is None or fng_timestamp is None:
        log["fallback_reason"] = "fng_malformed"
        logger.warning(f"F&G data malformed: {fng_data}; fallback neutral")
        return "neutral", log

    age_s = now - int(fng_timestamp)
    log["fng_age_s"] = age_s
    if age_s > fng_max_age_s:
        log["fallback_reason"] = "fng_stale"
        logger.warning(
            f"F&G stale (age {age_s}s > {fng_max_age_s}s); fallback neutral"
        )
        return "neutral", log

    regime = _fng_to_regime(int(fng_value))
    log["fng_used"] = True
    log["regime_source"] = "fng"
    return regime, log


def regime_to_slow_score(regime: str) -> tuple[int, int]:
    """Return (risk_slow, opp_slow) for a given regime string.

    Unknown regime → (40, 40) defensive neutral. Slow_loop uses this to
    fill sentinel_scores.risk_score / opportunity_score for the slow row.
    """
    return REGIME_SCORE_MAP.get(regime, (40, 40))
