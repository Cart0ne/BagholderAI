"""Slow loop orchestration (Sentinel Sprint 2).

One slow tick:
    1. Fetch Fear & Greed Index (alternative.me, free)
    2. Fetch CMC global metrics (paid, optional — needs CMC_API_KEY)
    3. Determine regime (extreme_fear / fear / neutral / greed / extreme_greed)
    4. Map regime → slow risk/opp score
    5. INSERT sentinel_scores row with score_type='slow'

Sentinel main loop runs this at boot and every SLOW_LOOP_INTERVAL_S
seconds thereafter. Errors here MUST NOT crash the fast loop — callers
wrap tick() in try/except, but tick() itself also swallows DB errors
internally and just logs them.

Sprint 2 CMC scope: log only. cmc_data is embedded into raw_signals for
future analysis but does NOT affect the regime call. regime_analyzer.py
will refine this in a future sprint if data justifies it.
"""

from __future__ import annotations

import logging
from typing import Optional

from bot.sentinel.inputs import alternative_fng, cmc_global
from bot.sentinel.regime_analyzer import determine_regime, regime_to_slow_score

logger = logging.getLogger("bagholderai.sentinel.slow_loop")


def tick(
    supabase,
    fng_fetcher=alternative_fng.fetch,
    cmc_fetcher=cmc_global.fetch,
) -> dict:
    """Execute one slow tick. Returns a dict describing what happened.

    Args:
        supabase: Supabase client (from db.client.get_client()).
        fng_fetcher: callable returning the F&G dict or None. Injected
            for testability; defaults to the real fetcher.
        cmc_fetcher: callable returning the CMC dict or None. Same.

    Returns:
        dict with keys: regime, risk_slow, opp_slow, fng_value (or None),
        cmc_seen (bool), inserted (bool). Useful for logging from main.
    """
    fng = _safe_call(fng_fetcher, "F&G")
    cmc = _safe_call(cmc_fetcher, "CMC")

    regime, decision_log = determine_regime(fng, cmc)
    risk_slow, opp_slow = regime_to_slow_score(regime)

    raw_signals = _build_raw_signals(regime, fng, cmc, decision_log)
    inserted = _insert_slow_score(supabase, regime, risk_slow, opp_slow, raw_signals)

    out = {
        "regime": regime,
        "risk_slow": risk_slow,
        "opp_slow": opp_slow,
        "fng_value": (fng or {}).get("fng_value"),
        "cmc_seen": cmc is not None,
        "inserted": inserted,
    }
    logger.info(
        f"Slow tick: regime={regime}, risk={risk_slow}, opp={opp_slow}, "
        f"fng={out['fng_value']}, cmc={'yes' if cmc else 'no'}, "
        f"inserted={'yes' if inserted else 'no'}"
    )
    return out


def _safe_call(fetcher, name: str) -> Optional[dict]:
    """Wrap fetcher in try/except so a bug in input code can't crash the tick.
    Input modules already follow NEVER-raise contracts, but defense in
    depth is cheap here.
    """
    try:
        return fetcher()
    except Exception as e:
        logger.warning(f"{name} fetcher raised unexpectedly: {e}")
        return None


def _build_raw_signals(
    regime: str,
    fng: Optional[dict],
    cmc: Optional[dict],
    decision_log: dict,
) -> dict:
    """Build the raw_signals jsonb embedded in sentinel_scores.

    The shape mirrors what Sherpa and audit queries will look for —
    keep keys stable. Missing inputs leave their keys absent (not None)
    so jsonb_each in audit queries doesn't enumerate empty noise.
    """
    raw: dict = {"regime": regime, "decision_log": decision_log}

    if fng is not None:
        raw["fng_value"] = fng.get("fng_value")
        raw["fng_label"] = fng.get("fng_label")
        raw["fng_timestamp"] = fng.get("fng_timestamp")

    if cmc is not None:
        raw["btc_dominance"] = cmc.get("btc_dominance")
        raw["total_market_cap_usd"] = cmc.get("total_market_cap_usd")
        raw["total_volume_24h_usd"] = cmc.get("total_volume_24h_usd")
        raw["active_cryptocurrencies"] = cmc.get("active_cryptocurrencies")

    return raw


def _insert_slow_score(
    supabase,
    regime: str,
    risk_slow: int,
    opp_slow: int,
    raw_signals: dict,
) -> bool:
    """Insert one row with score_type='slow'. Returns True on success.

    Errors are logged + swallowed: a transient DB hiccup must not crash
    the Sentinel process. The next slow tick (4h later) will retry; in
    the meantime Sherpa reads the last available slow score, falling
    back to "neutral" if none exists.
    """
    try:
        supabase.table("sentinel_scores").insert({
            "score_type": "slow",
            "risk_score": risk_slow,
            "opportunity_score": opp_slow,
            "raw_signals": raw_signals,
        }).execute()
        return True
    except Exception as e:
        logger.error(f"sentinel_scores slow insert failed: {e}")
        return False
