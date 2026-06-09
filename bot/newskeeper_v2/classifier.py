"""NewsKeeper v2 Haiku classifier — architecture "C".

One Haiku call per article returns the four fields the barometer needs:
  - relevance  : high | medium | discard   (how much it moves the climate)
  - polarity   : -1 | 0 | +1               (Haiku READS the meaning — no veto)
  - event_key  : ENTITY|EVENT_TYPE          (for event-level dedup)
  - confidence : 0.0-1.0                    (drives the abstain safety net)

Architecture C (the fix to the S100 review's #1 finding): the Python lexicon
NO LONGER decides direction. Haiku reads "inflation jumps 6%" and knows it's
bearish for risk assets, where the lexicon mislabeled it bullish ("jumps"=up).
The preprocessor's direction survives ONLY as a logged `direction_conflict`
audit sensor — it cannot override Haiku.

Fail-safe, not fail-loud-with-a-guess: if Haiku is unavailable the item is
written as an ABSTENTION (polarity 0, confidence 0) plus a NEWSKEEPER_V2_
FALLBACK event — a degraded barometer must NOT move the state with regex
guesses. The Anthropic call pattern is copied from v1 (same model, same key).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from db.event_logger import log_event
from bot.newskeeper import preprocessor as pp

logger = logging.getLogger("bagholderai.newskeeper_v2.classifier")

HAIKU_MODEL = "claude-haiku-4-5-20251001"  # same as v1 / commentary.py

CLASSIFIER_VERSION = "barometro_v1"
FALLBACK_VERSION = "barometro_fallback"

# Controlled vocabulary for event_key = "ENTITY|EVENT_TYPE". Haiku picks the
# closest; the sanitizer falls back to MISC|<entity> for anything off-list so
# dedup still groups same-topic stories. Initial set (brief §5) — revise on data.
_ENTITIES = {"BTC", "ETH", "SOL", "BONK", "MACRO", "FED", "REG", "EXCH", "MISC"}
_EVENT_TYPES = {
    "etf_flow", "price_move", "rate_signal", "inflation_print", "exploit_hack",
    "regulation", "adoption", "liquidation", "geopolitics", "misc",
}

CLASSIFIER_SYSTEM_PROMPT = """You classify ONE crypto/macro news item for a market-climate barometer.
You read the MEANING of the headline. You never do arithmetic.

Return JSON only, exact keys:
{"relevance": "high|medium|discard",
 "polarity": -1 | 0 | 1,
 "event_key": "ENTITY|EVENT_TYPE",
 "confidence": 0.0-1.0,
 "reasoning": "1 short sentence"}

POLARITY — from the viewpoint of someone HOLDING crypto (a risk asset):
  +1  bullish for crypto price
   0  no clear directional impact / genuinely two-sided
  -1  bearish for crypto price
  CRITICAL: judge the EFFECT ON PRICE, not whether a number rises. Rising
  inflation, a hawkish Fed, a rate HIKE, surging yields, ETF OUTFLOWS, and
  "Bitcoin dumped all its gains" are all -1 (bearish for risk assets) even
  though a number is going up. A rate CUT, falling inflation, ETF inflows,
  and a rebound are +1.

RELEVANCE — how much this single item should move an AGGREGATE climate gauge:
  high     major catalyst: Fed/CPI/jobs prints, big exploit/hack, large ETF
           flows, a major BTC/ETH price move, systemic regulation.
  medium   real but secondary: a single project, a mid-size move, a notable
           opinion from a market mover.
  discard  does NOT move the climate: explainers, price-prediction clickbait,
           recaps, gossip, generic tech, single-altcoin trivia.

EVENT_KEY — group same-story coverage so it counts once. Format ENTITY|TYPE.
  ENTITY in: BTC ETH SOL BONK MACRO FED REG EXCH MISC
  TYPE in: etf_flow price_move rate_signal inflation_print exploit_hack
           regulation adoption liquidation geopolitics misc
  Examples: "FED|rate_signal", "BTC|etf_flow", "MACRO|inflation_print",
            "ETH|exploit_hack". Same real-world event -> same key.

CONFIDENCE: your certainty about polarity AND relevance. If the crypto impact
is ambiguous, be honest and go low — a low-confidence read abstains downstream."""

# Fields handed to Haiku (the envelope minus internal plumbing).
_PAYLOAD_KEYS = ("title", "description", "numbers", "entities", "content_type", "feed_source")


def _parse_json(raw: str) -> Optional[dict]:
    """Parse Haiku's reply. Tolerates ```json fences and surrounding prose."""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(s[start:end + 1])
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def _clean_event_key(value) -> str:
    """Validate ENTITY|EVENT_TYPE against the controlled vocab; fix or fall back."""
    if not isinstance(value, str) or "|" not in value:
        return "MISC|misc"
    ent, _, typ = value.partition("|")
    ent = ent.strip().upper()
    typ = typ.strip().lower()
    ent = ent if ent in _ENTITIES else "MISC"
    typ = typ if typ in _EVENT_TYPES else "misc"
    return f"{ent}|{typ}"


def sanitize(env: dict, haiku: dict) -> dict:
    """Validate + normalize Haiku's answer. PURE (no I/O), so unit-testable.

    Architecture C: Haiku's polarity is taken as-is (only range-validated). The
    Python lexicon direction is NOT applied — it is compared and recorded as
    `direction_conflict` for audit only. The one Python guardrail that remains
    is structural, not directional: video/recap content is forced to
    relevance=discard (it never moves the climate), which never touches polarity.
    """
    relevance = haiku.get("relevance")
    if relevance not in ("high", "medium", "discard"):
        relevance = "discard"

    try:
        polarity = int(haiku.get("polarity"))
    except (TypeError, ValueError):
        polarity = 0
    if polarity not in (-1, 0, 1):
        polarity = 0

    try:
        confidence = float(haiku.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = round(min(1.0, max(0.0, confidence)), 2)

    event_key = _clean_event_key(haiku.get("event_key"))
    reasoning = (haiku.get("reasoning") or "")[:200]

    # Structural guardrail (NOT directional): clickbait formats never vote.
    content_type = env.get("content_type")
    if content_type in ("video", "recap") and relevance != "discard":
        relevance = "discard"

    # Audit sensor only — Python direction vs Haiku polarity. No override (C).
    py_dir = env.get("direction")  # up | down | flat | mixed
    direction_conflict = (
        (py_dir == "up" and polarity == -1) or (py_dir == "down" and polarity == 1)
    )

    return {
        "relevance": relevance,
        "polarity": polarity,
        "event_key": event_key,
        "confidence": confidence,
        "reasoning": reasoning,
        "direction_conflict": direction_conflict,
        "classifier_version": CLASSIFIER_VERSION,
    }


def _fallback(env: dict, reason: str) -> dict:
    """Degraded path: ABSTAIN (do not guess with regex). Loud + tagged.

    A barometer in shadow must never move on a degraded read. So the fallback
    writes a non-voting row (polarity 0, confidence 0) and emits a loud event,
    exactly so the T+1 check can prove Haiku is really answering.
    """
    logger.warning("Haiku unavailable -> abstain (%s)", reason)
    log_event(
        severity="warn",
        category="error",
        event="NEWSKEEPER_V2_FALLBACK",
        message=f"barometer abstain: {reason}"[:300],
        details={"title": (env.get("title") or "")[:160], "reason": reason},
    )
    ents = env.get("entities") or []
    ent = (ents[0].upper() if ents and ents[0].upper() in _ENTITIES else "MISC")
    return {
        "relevance": "discard",      # abstains: weight 0
        "polarity": 0,
        "event_key": f"{ent}|misc",
        "confidence": 0.0,
        "reasoning": "fallback (Haiku unavailable) — abstained",
        "direction_conflict": False,
        "classifier_version": FALLBACK_VERSION,
    }


def classify(env: dict) -> dict:
    """Classify one preprocessed envelope. Never raises. Always returns a dict
    (an abstention on any failure)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback(env, "ANTHROPIC_API_KEY not set")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        payload = {k: env.get(k) for k in _PAYLOAD_KEYS}
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw = response.content[0].text
    except Exception as e:  # network, auth, SDK — degrade to abstain
        return _fallback(env, f"haiku error: {type(e).__name__}")

    parsed = _parse_json(raw)
    if parsed is None:
        return _fallback(env, "unparseable Haiku JSON")

    return sanitize(env, parsed)
