"""S94a — NewsKeeper Session 2 unit tests (offline, no network/DB).

Covers the two load-bearing pure layers:
  1. preprocessor.compute_direction — Python computes the AUTHORITATIVE
     direction (the lesson from Brief 81b: Python does the math, Haiku reads).
  2. haiku_classifier.apply_guardrails — Python overrides a Haiku answer that
     contradicts the known direction / inflates severity on video|recap|
     low-confidence items.

These never hit Anthropic or Supabase: compute_direction and apply_guardrails
are pure functions, and we feed apply_guardrails a fake Haiku dict directly.

Run:
    pytest tests/test_newskeeper.py
"""

from bot.newskeeper import preprocessor as pp
from bot.newskeeper.haiku_classifier import apply_guardrails


# ----------------------------------------------------------------------
# compute_direction — the exact examples spelled out in brief S94a
# ----------------------------------------------------------------------

def test_direction_losses_fall_is_up():
    # negative subject ("losses") + diminish verb ("fall") -> good news
    assert pp.compute_direction("Crypto exchange losses fall 90% this quarter") == "up"


def test_direction_outflows_is_down():
    # negative subject with no verb -> the deflow itself is bad
    assert pp.compute_direction("Bitcoin ETF sees outflows of $1.67B") == "down"


def test_direction_slides_is_down():
    assert pp.compute_direction("Bitcoin slides under $73K as selloff deepens") == "down"


def test_direction_surges_is_up():
    assert pp.compute_direction("BTC surges past $80K on ETF inflows") == "up"


def test_direction_no_clear_signal_is_mixed():
    assert pp.compute_direction("Ethereum developers discuss next protocol meeting") == "mixed"


def test_direction_outflows_surge_is_down():
    # inversion: negative subject + rise verb -> bad
    assert pp.compute_direction("Stablecoin redemptions surge amid panic") == "down"


def test_direction_both_sided_is_mixed():
    # the CEO objection case: collapse (down) + rebound (up) -> mixed
    assert pp.compute_direction("Bitcoin collapses below M2 supply, eyes sharp rebound") == "mixed"


def test_direction_flat():
    assert pp.compute_direction("Bitcoin holds steady, unchanged on the day") == "flat"


# ----------------------------------------------------------------------
# content_type + entities
# ----------------------------------------------------------------------

def test_content_type_video_from_link():
    item = {"title": "Saylor buys more BTC", "link": "https://decrypt.co/videos/xyz"}
    assert pp.detect_content_type(item) == "video"


def test_content_type_recap_from_title():
    item = {"title": "Crypto markets: here's what happened this week", "link": "https://x.co/a"}
    assert pp.detect_content_type(item) == "recap"


def test_content_type_default_article():
    item = {"title": "SEC charges crypto firm", "link": "https://x.co/a"}
    assert pp.detect_content_type(item) == "article"


def test_entities_detected():
    ents = pp.detect_entities("Bitcoin and Ethereum ETF approval by the SEC")
    assert "BTC" in ents and "ETH" in ents and "ETF" in ents and "SEC" in ents


# ----------------------------------------------------------------------
# apply_guardrails — Python wins over a contradicting Haiku answer
# ----------------------------------------------------------------------

def _env(direction="mixed", content_type="article", title="t"):
    return {"direction": direction, "content_type": content_type, "title": title}


def test_guardrail_down_cannot_be_positive():
    haiku = {"theme": "macro", "market_impact": "positive", "severity": "high",
             "confidence": 0.9, "reasoning": "x"}
    out = apply_guardrails(_env(direction="down"), haiku)
    assert out["market_impact"] == "negative"
    assert out["classifier_version"] == "haiku_s2"


def test_guardrail_up_cannot_be_negative():
    haiku = {"theme": "adoption", "market_impact": "negative", "severity": "high",
             "confidence": 0.9, "reasoning": "x"}
    out = apply_guardrails(_env(direction="up"), haiku)
    assert out["market_impact"] == "positive"


def test_guardrail_video_caps_severity_low():
    haiku = {"theme": "market_crash", "market_impact": "negative", "severity": "critical",
             "confidence": 0.9, "reasoning": "x"}
    out = apply_guardrails(_env(content_type="video"), haiku)
    assert out["severity"] == "low"


def test_guardrail_low_confidence_caps_severity_low():
    haiku = {"theme": "regulatory", "market_impact": "negative", "severity": "high",
             "confidence": 0.1, "reasoning": "x"}
    out = apply_guardrails(_env(), haiku)
    assert out["severity"] == "low"


def test_guardrail_invalid_theme_falls_to_irrelevant():
    haiku = {"theme": "banana", "market_impact": "neutral", "severity": "low",
             "confidence": 0.5, "reasoning": "x"}
    out = apply_guardrails(_env(), haiku)
    assert out["theme"] == "irrelevant"


def test_guardrail_garbage_confidence_does_not_crash():
    haiku = {"theme": "macro", "market_impact": "neutral", "severity": "medium",
             "confidence": "not-a-number", "reasoning": "x"}
    out = apply_guardrails(_env(), haiku)
    # unparseable confidence -> 0.0 -> severity de-rated to low
    assert out["confidence"] == 0.0
    assert out["severity"] == "low"


def test_guardrail_valid_answer_passes_through():
    haiku = {"theme": "regulatory", "market_impact": "negative", "severity": "high",
             "confidence": 0.8, "reasoning": "SEC lawsuit"}
    out = apply_guardrails(_env(direction="down"), haiku)
    assert out["theme"] == "regulatory"
    assert out["market_impact"] == "negative"
    assert out["severity"] == "high"
    assert out["confidence"] == 0.8
