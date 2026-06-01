"""RSS feeds news input (NewsKeeper Module 1, S83 — pivot from CryptoPanic).

Aggregates crypto feeds (CoinDesk + CoinTelegraph + Decrypt) plus macro feeds
(CNBC Economy + MarketWatch, added S94a). Standard RSS 2.0, zero auth, zero
paywall risk. Brief originally specified CryptoPanic but its free Developer
tier was discontinued 2026-04-01; RSS is the Board-approved substitute (S83
addendum 2026-05-24, CEO note).

S94a (Session 2): this module no longer classifies. `fetch_candidates()`
returns RAW items that pass a cheap keyword gate (crypto OR macro, per feed
type) and a video skip; the downstream preprocessor + Haiku classifier do the
actual classification. The legacy regex `_classify` stays as the Haiku
fallback only.

Design rule (same as Sentinel inputs): NEVER raise. On any error,
including network or parse failure, return [] and log a warning.
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

import requests

logger = logging.getLogger("bagholderai.newskeeper.rss_feeds")

_TIMEOUT = 15
_USER_AGENT = "BagHolderAI-NewsKeeper/1.0"

# Feeds active. Tuple is (source_name, url, feed_type). feed_type routes the
# relevance gate: "crypto" -> _CRYPTO_KEYWORDS, "macro" -> _MACRO_KEYWORDS.
# Crypto URLs verified live 2026-05-24; macro URLs verified live 2026-06-01
# (Reuters/AP from the brief were dead — HTTP 000/403. First wired
# BBC Business + MarketWatch, then BBC swapped for CNBC Economy — far better
# macro targeting: 22/30 items pass the macro gate vs BBC's general business
# noise, Max/CEO decision S94a correction. MarketWatch kept, re-evaluated T+7.)
# NOTE: every feed writes DB source="rss_feeds" (CHECK constraint on the
# `source` column only allows cryptopanic/rss_feeds/etf_flows/macro_calendar);
# the per-feed identity lives in raw_data.feed_source, never in `source`.
_FEEDS = [
    # Crypto
    ("coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss", "crypto"),
    ("cointelegraph", "https://cointelegraph.com/rss", "crypto"),
    ("decrypt", "https://decrypt.co/feed", "crypto"),
    # Macro (S94a)
    ("cnbc_economy", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", "macro"),
    ("marketwatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "macro"),
]

# Cold-start / burst guard (objection B, brief S94a): the in-memory dedupe
# cache is empty after every restart, so the first tick would otherwise hand
# every live article to Haiku at once (~3-5 min blocking + cost spike). Cap
# Haiku calls per tick; the overflow stays un-seen and is picked up next tick.
_MAX_CANDIDATES_PER_TICK = 25

# Relevance gate: a crypto-feed item must mention at least one crypto keyword.
# Decrypt's feed mixes in general-tech ("Firefox kill AI" etc.) and we skip
# those before any classification.
_CRYPTO_KEYWORDS = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|solana|sol|crypto|cryptocurr\w*|"
    r"blockchain|stablecoin|defi|etf|altcoin|memecoin|bonk)\b",
    re.IGNORECASE,
)

# Macro feeds (BBC/MarketWatch) carry mostly off-topic business news; the
# macro gate keeps only items that can move crypto via the macro channel
# (Fed/rates/inflation/tariffs/geopolitics/dollar/yields).
_MACRO_KEYWORDS = re.compile(
    r"\b(fed|fomc|rate hike|rate cut|interest rate|tariff|tariffs|"
    r"gdp|inflation|recession|employment|unemployment|jobs report|"
    r"sanctions|treasury|geopolitical|war|trade war|"
    r"oil price|commodities|dollar|dxy|bond yield|yields)\b",
    re.IGNORECASE,
)

# Severity classification. Title + description searched together.
# Critical wins over high; high-bearish wins over high-bullish (when both
# match the prudent fallback is "be defensive" per brief Haiku rules).
_CRITICAL_BEARISH = re.compile(
    r"\b(crash|plunge|collapses?|liquidation|exploit|hack(?:ed)?|stolen|"
    r"rug ?pull|fraud|insolven\w*|bankrupt\w*|seized|drained|depeg)\b",
    re.IGNORECASE,
)
_HIGH_BEARISH = re.compile(
    r"\b(sec|lawsuit|charged|ban|crackdown|regulation|outflow|sell-off|"
    r"selloff|fed|fomc|cpi|rate hike|hawkish|tariff|recession|downgrade|"
    r"warning|risk-off)\b",
    re.IGNORECASE,
)
_HIGH_BULLISH = re.compile(
    r"\b(rally|surge|all-time high|new high|ath|inflow|approval|approved|"
    r"breakthrough|adopts?|adoption|integration|partnership|dovish|rate cut)\b",
    re.IGNORECASE,
)

# Dedupe by guid (RSS standard identifier) across ticks. TTL 24h matches
# expires_at — a long-lived article re-emits to refresh signal heartbeat.
_DEDUPE_TTL_S = 24 * 60 * 60
_seen_guids: dict[str, float] = {}


def _prune_dedupe_cache() -> None:
    now = time.time()
    stale = [g for g, ts in _seen_guids.items() if (now - ts) > _DEDUPE_TTL_S]
    for g in stale:
        del _seen_guids[g]


def _classify(text: str) -> Optional[tuple[str, str]]:
    """Return (signal_type, severity) or None if not signal-worthy."""
    if _CRITICAL_BEARISH.search(text):
        return ("bearish_news", "critical")
    if _HIGH_BEARISH.search(text):
        return ("bearish_news", "high")
    if _HIGH_BULLISH.search(text):
        return ("bullish_news", "high")
    return None


def _strip_html(s: str) -> str:
    """Crude HTML strip — RSS descriptions often have inline <p>, <img>."""
    return re.sub(r"<[^>]+>", " ", s or "")


def _fetch_feed(name: str, url: str) -> list[dict]:
    """Fetch + parse one feed. Returns list of raw item dicts; empty on error."""
    try:
        r = requests.get(
            url, timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
    except requests.RequestException as e:
        logger.warning(f"RSS {name}: fetch failed (network): {e}")
        return []
    if r.status_code != 200:
        logger.warning(f"RSS {name}: HTTP {r.status_code}")
        return []

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        logger.warning(f"RSS {name}: parse error: {e}")
        return []

    items_out: list[dict] = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link or title).strip()
        desc = _strip_html(it.findtext("description") or "")
        pub = (it.findtext("pubDate") or "").strip()
        if not guid:
            continue
        items_out.append({
            "feed": name,
            "title": title,
            "link": link,
            "guid": guid,
            "description": desc[:500],
            "pub_date": pub,
        })
    return items_out


def _is_video(link: str) -> bool:
    low = (link or "").lower()
    return "/videos/" in low or "/video/" in low


def fetch_candidates() -> list[dict]:
    """Return RAW item dicts (filtered + deduped, NOT classified).

    S94a: classification moved downstream to preprocessor + Haiku. Here we
    only apply cheap noise reduction before any LLM call:
      - per-feed keyword gate (crypto OR macro, by feed_type)
      - video skip (Decrypt clickbait videos linger for weeks — brief fix #4)
      - dedupe by guid across ticks (in-memory, 24h TTL)
      - per-tick cap (objection B cold-start guard)

    Shape per item:
        {feed, feed_type, title, link, guid, description, pub_date}

    Empty list on any failure. Never raises. The guid is marked "seen" only
    for the items actually returned, so capped overflow is retried next tick.
    """
    _prune_dedupe_cache()
    now = time.time()
    feed_stats: dict[str, int] = {}
    buckets: list[list[dict]] = []  # one kept-list per feed, feed order

    for name, url, feed_type in _FEEDS:
        items = _fetch_feed(name, url)
        feed_stats[name] = len(items)
        keyword_filter = _CRYPTO_KEYWORDS if feed_type == "crypto" else _MACRO_KEYWORDS
        kept: list[dict] = []
        for it in items:
            guid = it["guid"]
            if guid in _seen_guids:
                continue
            if _is_video(it.get("link", "")):
                continue
            text = f"{it['title']} {it['description']}"
            if not keyword_filter.search(text):
                continue
            it["feed_type"] = feed_type
            kept.append(it)
        buckets.append(kept)

    # Round-robin across feeds before the cap, so one busy feed (CoinDesk on a
    # news day) can't monopolize all 25 slots and starve the macro feeds that
    # come last in _FEEDS order (bug found in S94a smoke test).
    total_kept = sum(len(b) for b in buckets)
    out: list[dict] = []
    round_idx = 0
    while len(out) < _MAX_CANDIDATES_PER_TICK:
        progressed = False
        for b in buckets:
            if round_idx < len(b):
                out.append(b[round_idx])
                progressed = True
                if len(out) >= _MAX_CANDIDATES_PER_TICK:
                    break
        if not progressed:
            break
        round_idx += 1

    truncated = max(0, total_kept - len(out))
    # Mark seen ONLY what we return — overflow stays un-seen for next tick.
    for it in out:
        _seen_guids[it["guid"]] = now

    summary = " ".join(f"{n}={c}" for n, c in feed_stats.items())
    if truncated:
        logger.info(
            "RSS: %d candidate(s) from %s (capped — %d held for next tick)",
            len(out), summary, truncated,
        )
    elif out:
        logger.info(
            "RSS: %d candidate(s) from %s — sample: %s",
            len(out), summary,
            "; ".join(f"[{c['feed']}] {c['title'][:50]}" for c in out[:3]),
        )
    else:
        logger.info("RSS: 0 candidates from %s (all filtered out)", summary)
    return out
