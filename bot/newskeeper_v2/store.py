"""NewsKeeper v2 Supabase I/O — the only module here that touches the DB.

Three jobs:
  - write_signal()        : append one enriched per-item row to
                            `newskeeper_signals` (kept raw for audit / digest /
                            param re-tuning; brief §4). v2 rows are the ones
                            with event_key NOT NULL — that is the clean
                            discriminator from v1's rows.
  - fetch_votes_24h()     : pull the last 24h of v2 votes for the aggregator.
  - load_state() / write_regime() : the slow barometer state in
                            `newskeeper_regime`, written on-change + heartbeat.

Never raises on DB failure — errors land in bot_events_log and the loop
continues (a barometer that crashes on a transient DB blip is worse than one
that skips a tick).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from db.event_logger import log_event

logger = logging.getLogger("bagholderai.newskeeper_v2.store")

# relevance bucket -> the legacy NOT-NULL `severity` column (CHECK-constrained
# to low/medium/high/critical). severity is no longer a barometer driver
# (brief §4); we only need a valid value so the insert passes the constraint.
_REL_TO_SEVERITY = {"high": "high", "medium": "medium", "discard": "low"}

EXPIRES_MINUTES = 24 * 60
HEARTBEAT_H = 6  # write a non-flip regime row at least this often (liveness)


def write_signal(supabase, item: dict, cls: dict) -> bool:
    """Append one enriched per-item row. Returns True on insert, else False."""
    title = (item.get("title") or "")[:280]
    relevance = cls.get("relevance") or "discard"
    expires = datetime.now(timezone.utc) + timedelta(minutes=EXPIRES_MINUTES)
    row = {
        "source": "rss_feeds",                       # CHECK-constrained value
        "signal_type": cls.get("event_key") or "MISC|misc",
        "severity": _REL_TO_SEVERITY.get(relevance, "low"),
        "summary": title,
        "relevance": relevance,
        "polarity": cls.get("polarity", 0),
        "event_key": cls.get("event_key"),
        "confidence": cls.get("confidence", 0.0),
        "expires_at": expires.isoformat(),
        "raw_data": {
            "feed_source": item.get("feed"),
            "guid": item.get("guid"),
            "link": item.get("link"),
            "reasoning": cls.get("reasoning"),
            "direction_conflict": cls.get("direction_conflict", False),
            "classifier_version": cls.get("classifier_version"),
        },
    }
    try:
        supabase.table("newskeeper_signals").insert(row).execute()
        return True
    except Exception as e:
        logger.error("newskeeper_signals (v2) insert failed: %s", e)
        log_event(
            severity="error", category="error", event="NEWSKEEPER_V2_ERROR",
            message=f"signal insert failed: {e}"[:300],
            details={"event_key": cls.get("event_key")},
        )
        return False


def fetch_votes_24h(supabase, window_h: float = 24.0) -> list[dict]:
    """Pull the last `window_h` hours of v2 votes (event_key NOT NULL)."""
    since = (datetime.now(timezone.utc) - timedelta(hours=window_h)).isoformat()
    try:
        res = (
            supabase.table("newskeeper_signals")
            .select("created_at, relevance, polarity, confidence, event_key")
            .not_.is_("event_key", "null")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("fetch_votes_24h failed: %s", e)
        return []


def load_state(supabase) -> str:
    """Current published barometer state from the latest regime row.

    Only the committed state is persisted across restarts; the in-flight
    `pending`/`pending_since` are in-memory (a restart restarts the persistence
    clock — at most a `persist_h` delay, acceptable in shadow).
    """
    try:
        res = (
            supabase.table("newskeeper_regime")
            .select("state, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows and rows[0].get("state") in ("bearish", "neutral", "bullish"):
            return rows[0]["state"]
    except Exception as e:
        logger.error("load_state failed: %s", e)
    return "neutral"


def last_regime_age_seconds(supabase) -> Optional[float]:
    """Seconds since the last regime row (for the heartbeat cadence)."""
    try:
        res = (
            supabase.table("newskeeper_regime")
            .select("created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        ts = datetime.fromisoformat(rows[0]["created_at"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception as e:
        logger.error("last_regime_age failed: %s", e)
        return None


def latest_btc_price(supabase) -> Optional[float]:
    """Latest BTC price Sentinel logged — the anchor for the 24h forward-return
    validation (read-only; we never write to sentinel_scores)."""
    try:
        res = (
            supabase.table("sentinel_scores")
            .select("btc_price")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows and rows[0].get("btc_price") is not None:
            return float(rows[0]["btc_price"])
    except Exception as e:
        logger.error("latest_btc_price failed: %s", e)
    return None


def fetch_fear_greed() -> Optional[int]:
    """Best-effort Fear & Greed index (downstream confirmation, NOT the
    validation metric). Never raises; None on any failure."""
    try:
        import requests

        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        if r.status_code != 200:
            return None
        return int(r.json()["data"][0]["value"])
    except Exception:
        return None


def write_regime(
    supabase,
    state: str,
    prev_state: str,
    net_score: float,
    abstain_frac: float,
    vote_count: int,
    is_flip: bool,
) -> bool:
    """Write one regime row (a flip, or a periodic heartbeat). Snapshots BTC
    price + F&G at write time so the T+14 forward-return validation can join
    against sentinel_scores. Never raises."""
    row = {
        "state": state,
        "prev_state": prev_state,
        "net_score": round(float(net_score), 4),
        "abstain_frac": round(float(abstain_frac), 3),
        "vote_count": int(vote_count),
        "btc_price_at_flip": latest_btc_price(supabase),
        "fg_at_flip": fetch_fear_greed(),
        "raw_data": {"kind": "flip" if is_flip else "heartbeat"},
    }
    try:
        supabase.table("newskeeper_regime").insert(row).execute()
        return True
    except Exception as e:
        logger.error("newskeeper_regime insert failed: %s", e)
        log_event(
            severity="error", category="error", event="NEWSKEEPER_V2_ERROR",
            message=f"regime insert failed: {e}"[:300],
            details={"state": state, "is_flip": is_flip},
        )
        return False
