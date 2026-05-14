"""Read the current macro regime from Sentinel's slow scores (Sprint 2).

Sentinel writes one sentinel_scores row with score_type='slow' every 4h.
Sherpa needs to know the current regime to pick the right BASE_TABLE
row in parameter_rules. This module isolates the query so sherpa/main.py
stays a thin orchestrator and so we can unit-test the fallback logic
without spinning up a Supabase mock inside that 535-line file.

Contract: never raise. On any failure (no row yet, DB error, malformed
raw_signals) return "neutral" and log a warning. Sherpa continues
unaffected — it just behaves as it did before Sprint 2.

Valid regimes match Sherpa's parameter_rules.py BASE_TABLE:
    extreme_fear | fear | neutral | greed | extreme_greed
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("bagholderai.sherpa.regime_reader")

VALID_REGIMES = frozenset(
    ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]
)
DEFAULT_REGIME = "neutral"


def get_current_regime(supabase) -> str:
    """Return the regime from the most recent slow sentinel score.

    Returns DEFAULT_REGIME ("neutral") on any failure or absence of a
    slow row. Logs a warning on unexpected paths so we can audit them
    in bot_events_log, but never raises.
    """
    try:
        res = (
            supabase.table("sentinel_scores")
            .select("raw_signals, created_at")
            .eq("score_type", "slow")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning(f"Slow score query failed: {e}; using {DEFAULT_REGIME}")
        return DEFAULT_REGIME

    rows = res.data or []
    if not rows:
        logger.info(
            f"No slow sentinel_scores row yet; using {DEFAULT_REGIME} regime"
        )
        return DEFAULT_REGIME

    raw = rows[0].get("raw_signals") or {}
    regime = raw.get("regime")
    if regime not in VALID_REGIMES:
        logger.warning(
            f"Unknown regime '{regime}' in latest slow score; "
            f"falling back to {DEFAULT_REGIME}"
        )
        return DEFAULT_REGIME

    return regime
