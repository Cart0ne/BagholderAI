"""NewsKeeper preprocessor (S94a — Brain #5 Session 2).

Pure functions, NO network / NO DB. Takes a raw RSS item dict (as produced
by readers.rss_feeds._fetch_feed) and returns a structured "envelope" for the
Haiku classifier.

Golden rule (lesson from Brief 81b commentary): **Python computes the
direction, the LLM only reads it.** Haiku must never do math — it receives a
pre-computed, authoritative `direction` field and classifies around it.

The envelope shape:
    {
        "title": str,
        "description": str | None,
        "numbers": [{"value": float, "unit": str|None,
                     "currency": str|None, "context": str|None}, ...],
        "direction": "up" | "down" | "flat" | "mixed",
        "content_type": "article" | "video" | "recap" | "opinion",
        "entities": [str, ...],
        "feed_source": str,        # coindesk | cointelegraph | bbc | ...
    }
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Direction lexicons. The heuristic is deliberately conservative: a clear
# single-sided signal returns up/down, anything ambiguous returns "mixed" so
# Haiku decides (and `confidence` lets us discount it). See the CEO objection
# in brief S94a: "collapse ... rebound" in one title -> mixed by design.
# --------------------------------------------------------------------------

# Nouns whose VALUE going down is GOOD and going up is BAD (inversion subjects).
_NEG_SUBJECTS = {
    "outflow", "outflows", "loss", "losses", "deficit", "selloff",
    "liquidation", "liquidations", "redemption", "redemptions", "debt",
    "fear", "risk", "drawdown",
}

# Verbs/words meaning "decreasing" — invert a negative subject (losses fall=up).
_DIMINISH = {
    "fall", "falls", "fell", "drop", "drops", "dropped", "decline",
    "declines", "declined", "ease", "eases", "eased", "shrink", "shrinks",
    "slow", "slows", "slowed", "narrow", "narrows", "cool", "cools",
    "recede", "recedes", "abate", "abates",
}

# Verbs meaning "increasing" — with a negative subject this is BAD (outflows surge=down).
_RISE_VERBS = {
    "rise", "rises", "rose", "surge", "surges", "surged", "jump", "jumps",
    "jumped", "climb", "climbs", "climbed", "soar", "soars", "soared",
    "grow", "grows", "spike", "spikes", "spiked", "balloon", "balloons",
    "mount", "mounts", "swell", "swells",
}

# Generic bullish price words. NOTE: bare ambiguous verbs ("breaks",
# "tops") are deliberately excluded — "breaks silence" / "tops the agenda"
# would mis-fire to "up", and a WRONG direction is worse than "mixed" here
# because the guardrail uses direction to override Haiku's impact. When
# unsure, return "mixed" and let Haiku + confidence decide (CEO objection).
_UP_WORDS = {
    "surge", "surges", "rally", "rallies", "rallied", "soar", "soars",
    "jump", "jumps", "gain", "gains", "inflow", "inflows", "climb", "climbs",
    "rebound", "rebounds", "breakout", "ath", "approval", "approved",
    "adopts", "adoption", "upgrade", "upgraded", "bullish",
}

# Generic bearish price words.
_DOWN_WORDS = {
    "crash", "crashes", "plunge", "plunges", "collapse", "collapses",
    "slump", "slumps", "selloff", "outflow", "outflows", "liquidation",
    "exploit", "hack", "hacked", "plummet", "plummets", "tumble", "tumbles",
    "sink", "sinks", "slide", "slides", "slid", "dump", "dumps", "downgrade",
    "ban", "lawsuit", "bearish", "drops", "drop", "falls", "fell", "sell-off",
    "dips", "dip", "retreat", "retreats", "loses", "lost", "fear",
}

# Explicitly flat.
_FLAT_WORDS = {
    "flat", "steady", "unchanged", "holds", "hovers", "consolidates",
    "consolidate", "sideways", "stable", "range-bound", "rangebound",
}

_TOKEN_RE = re.compile(r"[a-z][a-z\-']*")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def compute_direction(title: str) -> str:
    """Pre-compute market direction from the headline. AUTHORITATIVE for Haiku.

    Order of precedence:
      1. inversion subjects (losses/outflows) combined with diminish/rise verbs
      2. explicit flat words
      3. generic up/down word presence (single-sided -> up/down, both -> mixed)
    """
    toks = _tokens(title or "")
    has_neg_subject = bool(toks & _NEG_SUBJECTS)
    has_diminish = bool(toks & _DIMINISH)
    has_rise = bool(toks & _RISE_VERBS)

    # 1. inversion logic on negative subjects
    if has_neg_subject and has_diminish and not has_rise:
        return "up"          # "losses fall 90%" -> good
    if has_neg_subject and has_rise and not has_diminish:
        return "down"        # "outflows surge" -> bad
    if has_neg_subject and not has_diminish and not has_rise:
        return "down"        # "outflows of $1.67B" -> bad (deflow, no verb)

    # 2. explicit flat
    if toks & _FLAT_WORDS and not (toks & _UP_WORDS) and not (toks & _DOWN_WORDS):
        return "flat"

    # 3. generic single-sided
    up = bool(toks & _UP_WORDS)
    down = bool(toks & _DOWN_WORDS)
    if up and not down:
        return "up"
    if down and not up:
        return "down"
    return "mixed"           # both or neither -> Haiku decides


# --------------------------------------------------------------------------
# Number extraction. Informational context for Haiku (NOT load-bearing — the
# load-bearing field is `direction`). Best-effort; never raises.
# --------------------------------------------------------------------------

_UNIT_MAP = {
    "%": "%", "percent": "%",
    "k": "K", "thousand": "K",
    "m": "M", "mn": "M", "million": "M",
    "b": "B", "bn": "B", "billion": "B",
    "t": "T", "tn": "T", "trillion": "T",
}

# money: optional $, number, optional scale word
_MONEY_RE = re.compile(
    r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(k|m|mn|b|bn|t|tn|million|billion|trillion|thousand)?",
    re.IGNORECASE,
)
# percent: optional sign, number, %
_PCT_RE = re.compile(r"([-+]?)(\d[\d,]*(?:\.\d+)?)\s?%")

_CONTEXT_WORDS = (
    "outflow", "inflow", "loss", "gain", "drop", "surge", "rally", "crash",
    "plunge", "rate", "inflation", "gdp", "yield", "volume", "marketcap",
)


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return 0.0


def _context_for(title: str) -> str | None:
    low = title.lower()
    for w in _CONTEXT_WORDS:
        if w in low:
            return w
    return None


def extract_numbers(title: str, description: str | None = None) -> list[dict]:
    text = f"{title or ''} {description or ''}"
    ctx = _context_for(title or "")
    out: list[dict] = []
    for m in _MONEY_RE.finditer(text):
        unit = _UNIT_MAP.get((m.group(2) or "").lower()) if m.group(2) else None
        out.append({
            "value": _to_float(m.group(1)),
            "unit": unit,
            "currency": "USD",
            "context": ctx,
        })
    for m in _PCT_RE.finditer(text):
        sign = -1.0 if m.group(1) == "-" else 1.0
        out.append({
            "value": sign * _to_float(m.group(2)),
            "unit": "%",
            "currency": None,
            "context": ctx or "price change",
        })
    return out[:8]  # cap — headlines never carry more than a handful


# --------------------------------------------------------------------------
# content_type + entities
# --------------------------------------------------------------------------

_RECAP_RE = re.compile(
    r"here'?s what happened|what to know|recap|in review|week in|"
    r"daily (roundup|wrap)|markets? wrap|weekly|roundup",
    re.IGNORECASE,
)
_OPINION_RE = re.compile(
    r"\bopinion\b|op-ed|\bcolumn\b|why .+ matters|here'?s why",
    re.IGNORECASE,
)


def detect_content_type(item: dict) -> str:
    link = (item.get("link") or "").lower()
    title = item.get("title") or ""
    if "/videos/" in link or "/video/" in link:
        return "video"
    if _RECAP_RE.search(title):
        return "recap"
    if _OPINION_RE.search(title):
        return "opinion"
    return "article"


_ENTITY_PATTERNS = {
    "BTC": r"\b(bitcoin|btc)\b",
    "ETH": r"\b(ethereum|eth|ether)\b",
    "SOL": r"\b(solana|sol)\b",
    "BONK": r"\bbonk\b",
    "XRP": r"\b(xrp|ripple)\b",
    "ETF": r"\betf\b",
    "SEC": r"\bsec\b",
    "Fed": r"\b(fed|federal reserve|fomc)\b",
    "ECB": r"\becb\b",
    "Treasury": r"\btreasury\b",
    "stablecoin": r"\b(stablecoin|usdt|usdc|tether)\b",
    "DeFi": r"\bdefi\b",
    "tariff": r"\btariffs?\b",
    "inflation": r"\b(inflation|cpi)\b",
}
_ENTITY_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in _ENTITY_PATTERNS.items()}


def detect_entities(title: str, description: str | None = None) -> list[str]:
    text = f"{title or ''} {description or ''}"
    return [name for name, rx in _ENTITY_COMPILED.items() if rx.search(text)]


def preprocess(item: dict) -> dict:
    """Build the structured envelope from a raw RSS item dict. Never raises."""
    title = item.get("title") or ""
    description = item.get("description") or None
    return {
        "title": title,
        "description": description,
        "numbers": extract_numbers(title, description),
        "direction": compute_direction(title),
        "content_type": detect_content_type(item),
        "entities": detect_entities(title, description),
        "feed_source": item.get("feed"),
    }
