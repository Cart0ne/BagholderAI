"""RSS feeds news input (NewsKeeper Module 1, S83 — pivot from CryptoPanic).

Aggregates RSS feeds from CoinDesk + CoinTelegraph + Decrypt. Standard
RSS 2.0, zero auth, zero paywall risk. Brief originally specified
CryptoPanic but its free Developer tier was discontinued on 2026-04-01;
RSS is the Board-approved substitute (S83 addendum 2026-05-24, CEO note).

Classification is keyword-driven for now (no native sentiment/votes in
RSS). S3-4 Strategist + Haiku will likely upgrade this to LLM
classification, but the keyword pre-filter stays as cheap noise reduction
ahead of any LLM call.

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

# Feeds active in S1. Add a new source by appending a tuple — no other code
# changes needed. URLs verified live 2026-05-24 (HTTP 200 + valid RSS 2.0).
_FEEDS = [
    ("coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss"),
    ("cointelegraph", "https://cointelegraph.com/rss"),
    ("decrypt", "https://decrypt.co/feed"),
]

# Relevance gate: an item must mention at least one crypto keyword to count
# at all. Decrypt's feed mixes in general-tech ("Firefox kill AI" etc.) and
# we skip those before any classification.
_CRYPTO_KEYWORDS = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|solana|sol|crypto|cryptocurr\w*|"
    r"blockchain|stablecoin|defi|etf|altcoin|memecoin|bonk)\b",
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


def fetch_signals() -> list[dict]:
    """Return signal-candidate dicts ready for signal_writer.write_if_changed.

    Shape per candidate:
        {
            "source": "rss_feeds",
            "signal_type": "bearish_news" | "bullish_news",
            "severity": "high" | "critical",
            "summary": str,                  # article title (truncated 280)
            "raw_data": {feed, title, link, guid, description, pub_date},
            "expires_at_minutes": 24 * 60,
        }
    Empty list on any failure. Never raises.
    """
    _prune_dedupe_cache()
    now = time.time()
    out: list[dict] = []
    feed_stats: dict[str, int] = {}

    for name, url in _FEEDS:
        items = _fetch_feed(name, url)
        feed_stats[name] = len(items)
        for it in items:
            guid = it["guid"]
            if guid in _seen_guids:
                continue
            text = f"{it['title']} {it['description']}"
            if not _CRYPTO_KEYWORDS.search(text):
                continue
            classified = _classify(text)
            if classified is None:
                continue
            signal_type, severity = classified
            out.append({
                "source": "rss_feeds",
                "signal_type": signal_type,
                "severity": severity,
                "summary": it["title"][:280],
                "raw_data": it,
                "expires_at_minutes": 24 * 60,
            })
            _seen_guids[guid] = now

    summary = " ".join(f"{n}={c}" for n, c in feed_stats.items())
    if out:
        logger.info(
            "RSS: %d signal(s) from %s — sample: %s",
            len(out), summary,
            "; ".join(
                f"{s['signal_type']}={s['severity']} {s['summary'][:60]}"
                for s in out[:3]
            ),
        )
    else:
        logger.info("RSS: 0 signals from %s (all filtered out)", summary)
    return out
