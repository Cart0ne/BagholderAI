"""NewsKeeper Haiku classifier (S94a — Brain #5 Session 2).

Replaces the regex severity/direction classifier with a narrow Haiku call.
The Anthropic call pattern is copied 1:1 from commentary.py (same model, same
ANTHROPIC_API_KEY env var, same client construction).

Two-layer safety:
  1. Python pre-computes `direction` (preprocessor) — AUTHORITATIVE.
  2. Python guardrails run AFTER Haiku answers, so a confident-but-wrong
     answer can't invert a Python-known direction or inflate severity on a
     video/recap/low-confidence item.

Fail-open, but LOUDLY: any failure (no API key, network, unparseable JSON)
falls back to the legacy regex classifier in rss_feeds AND emits a
NEWSKEEPER_HAIKU_FALLBACK event. A silent fallback would let us ship "Haiku"
while running regex in production (objection C, brief S94a) — the loud event
+ the classifier_version tag let the T+1 check prove Haiku actually answered.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from db.event_logger import log_event
from bot.newskeeper.readers import rss_feeds

logger = logging.getLogger("bagholderai.newskeeper.haiku_classifier")

HAIKU_MODEL = "claude-haiku-4-5-20251001"  # same as commentary.py

CLASSIFIER_SYSTEM_PROMPT = """You classify crypto/macro news for a trading system.
You receive pre-processed structured data. NEVER do math.
The `direction` field is pre-computed by Python and is AUTHORITATIVE.

Rules:
1. If direction="down", market_impact CANNOT be "positive"
2. If direction="up", market_impact CANNOT be "negative"
3. If content_type="video", severity is at most "low"
4. If content_type="recap", severity is at most "low"
5. theme="irrelevant" for news that don't affect crypto markets
6. Respond ONLY with JSON, no other text

Output JSON shape (exact keys):
{"theme": "market_crash|regulatory|adoption|exploit|macro|irrelevant",
 "market_impact": "positive|negative|neutral",
 "severity": "critical|high|medium|low",
 "confidence": 0.0-1.0,
 "reasoning": "1 sentence max"}"""

_VALID_THEMES = {
    "market_crash", "regulatory", "adoption", "exploit", "macro", "irrelevant",
}
_VALID_IMPACT = {"positive", "negative", "neutral"}
_SEVERITY_ORDER = ["low", "medium", "high", "critical"]

# Fields handed to Haiku (the envelope minus internal plumbing).
_PAYLOAD_KEYS = (
    "title", "description", "numbers", "direction", "content_type",
    "entities", "feed_source",
)


def _parse_json(raw: str) -> Optional[dict]:
    """Parse Haiku's reply. Tolerates ```json fences and surrounding prose."""
    if not raw:
        return None
    s = raw.strip()
    # strip code fences if present
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    # isolate the first {...} block
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        obj = json.loads(s[start:end + 1])
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def apply_guardrails(envelope: dict, haiku: dict) -> dict:
    """Validate + override Haiku's answer against Python-known facts.

    PURE function (no I/O) so it is unit-testable without the network.
    Returns the final classification dict written to newskeeper_signals.
    """
    direction = envelope.get("direction")
    content_type = envelope.get("content_type")

    theme = haiku.get("theme")
    theme = theme if theme in _VALID_THEMES else "irrelevant"

    impact = haiku.get("market_impact")
    impact = impact if impact in _VALID_IMPACT else "neutral"

    severity = haiku.get("severity")
    severity = severity if severity in _SEVERITY_ORDER else "low"

    try:
        confidence = float(haiku.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))

    reasoning = (haiku.get("reasoning") or "")[:200]

    overrides: list[str] = []

    # Rules 1/2 — direction is authoritative, impact can't contradict it.
    if direction == "down" and impact == "positive":
        impact = "negative"
        overrides.append("impact->negative (dir=down)")
    elif direction == "up" and impact == "negative":
        impact = "positive"
        overrides.append("impact->positive (dir=up)")

    # Rules 3/4 — video/recap can never be louder than "low".
    if content_type in ("video", "recap") and severity != "low":
        severity = "low"
        overrides.append(f"severity->low ({content_type})")

    # Low confidence -> de-rate severity (brief guardrail).
    if confidence < 0.3 and severity != "low":
        severity = "low"
        overrides.append("severity->low (confidence<0.3)")

    if overrides:
        logger.warning(
            "guardrail overrides on '%s': %s",
            (envelope.get("title") or "")[:60], "; ".join(overrides),
        )

    return {
        "theme": theme,
        "market_impact": impact,
        "severity": severity,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "direction": direction,
        "classifier_version": "haiku_s2",
    }


def _regex_fallback(envelope: dict, reason: str) -> Optional[dict]:
    """Degraded path: reuse the legacy regex classifier. Loud + tagged.

    Returns None if even the regex finds nothing signal-worthy (so the caller
    skips the item), else a classification dict tagged classifier_version=
    'regex_fallback' so it is distinguishable from real Haiku output.
    """
    text = f"{envelope.get('title', '')} {envelope.get('description') or ''}"
    classified = rss_feeds._classify(text)  # (signal_type, severity) | None

    logger.warning("Haiku unavailable -> regex fallback (%s)", reason)
    log_event(
        severity="warn",
        category="error",
        event="NEWSKEEPER_HAIKU_FALLBACK",
        message=f"regex fallback: {reason}"[:300],
        details={"title": (envelope.get("title") or "")[:160], "reason": reason},
    )

    if classified is None:
        return None
    signal_type, severity = classified  # 'bearish_news'|'bullish_news', sev
    impact = "negative" if signal_type == "bearish_news" else "positive"
    theme = "market_crash" if severity == "critical" else "macro"
    return {
        "theme": theme,
        "market_impact": impact,
        "severity": severity,
        "confidence": 0.3,  # explicitly uncertain — it's a degraded path
        "reasoning": "regex fallback (Haiku unavailable)",
        "direction": envelope.get("direction"),
        "classifier_version": "regex_fallback",
    }


def classify(envelope: dict) -> Optional[dict]:
    """Classify one preprocessed envelope. Never raises.

    Returns the classification dict, or None when the item is not
    signal-worthy (only possible on the regex fallback path — Haiku itself
    always returns a theme, and theme=='irrelevant' is filtered by the caller).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _regex_fallback(envelope, "ANTHROPIC_API_KEY not set")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        payload = {k: envelope.get(k) for k in _PAYLOAD_KEYS}
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw = response.content[0].text
    except Exception as e:  # network, auth, SDK — degrade loudly
        return _regex_fallback(envelope, f"haiku error: {type(e).__name__}")

    parsed = _parse_json(raw)
    if parsed is None:
        return _regex_fallback(envelope, "unparseable Haiku JSON")

    return apply_guardrails(envelope, parsed)
