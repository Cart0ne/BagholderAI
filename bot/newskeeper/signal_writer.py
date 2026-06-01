"""NewsKeeper signal writer with write-on-change + heartbeat (S79c pattern).

Avoids redundant rows: if the latest DB row for (source, signal_type)
has the same severity + summary AND its age < HEARTBEAT_S, skip INSERT.

Heartbeat semantics: a "still bearish" state is re-confirmed periodically
so that a missing recent row means either the brain is silent (likely
crashed) or the signal genuinely cleared. Both are distinguishable from
lifecycle events in bot_events_log.

S94a (Session 2): the writer is unchanged structurally — the new Haiku
fields ride inside the `raw_data` JSONB (market_impact, confidence,
reasoning, direction, classifier_version, entities, numbers, feed_source).
The caller now passes signal_type = Haiku `theme` (market_crash | regulatory
| adoption | exploit | macro) instead of bearish_news/bullish_news, and
keeps source="rss_feeds" (the `source` CHECK constraint forbids new values).
`signal_type` has no CHECK constraint, so the new vocabulary needs no
migration.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from db.event_logger import log_event

logger = logging.getLogger("bagholderai.newskeeper.signal_writer")

# Min seconds between rows for the same (source, signal_type) when nothing
# changed. Sentinel fast loop uses 600s; NewsKeeper signals evolve slower
# (news cycle), so 1800s (30 min) is comfortable. Tunable post-S1.
HEARTBEAT_S = 30 * 60


def write_if_changed(
    supabase,
    source: str,
    signal_type: str,
    severity: str,
    summary: str,
    raw_data: Optional[dict] = None,
    expires_at_minutes: Optional[int] = None,
) -> bool:
    """INSERT into newskeeper_signals only if signal changed or heartbeat due.

    Returns True if a row was inserted, False if skipped.
    Never raises — DB errors land in bot_events_log + return False.
    """
    try:
        res = supabase.table("newskeeper_signals").select(
            "severity, summary, created_at"
        ).eq("source", source).eq("signal_type", signal_type).order(
            "created_at", desc=True
        ).limit(1).execute()
        last = (res.data or [None])[0]
    except Exception as e:
        logger.error(f"newskeeper_signals select failed: {e}")
        # Fail-open: try to insert anyway so a signal is never lost just
        # because the dedupe check itself failed.
        last = None

    should_write = True
    reason = "first row"
    if last:
        same = (last.get("severity") == severity) and (
            (last.get("summary") or "").strip() == (summary or "").strip()
        )
        try:
            last_ts = datetime.fromisoformat(
                last["created_at"].replace("Z", "+00:00")
            ).timestamp()
        except (KeyError, ValueError, AttributeError):
            last_ts = 0.0
        age_s = time.time() - last_ts
        if same and age_s < HEARTBEAT_S:
            should_write = False
            reason = f"unchanged ({int(age_s)}s < {HEARTBEAT_S}s)"
        elif same:
            reason = f"heartbeat ({int(age_s)}s >= {HEARTBEAT_S}s)"
        else:
            reason = "changed"

    if not should_write:
        logger.debug(
            "skip insert source=%s type=%s sev=%s: %s",
            source, signal_type, severity, reason,
        )
        return False

    row = {
        "source": source,
        "signal_type": signal_type,
        "severity": severity,
        "summary": summary,
        "raw_data": raw_data,
    }
    if expires_at_minutes is not None:
        expires = datetime.now(timezone.utc) + timedelta(minutes=expires_at_minutes)
        row["expires_at"] = expires.isoformat()

    try:
        supabase.table("newskeeper_signals").insert(row).execute()
    except Exception as e:
        logger.error(f"newskeeper_signals insert failed: {e}")
        log_event(
            severity="error",
            category="error",
            event="NEWSKEEPER_ERROR",
            message=f"signal insert failed: {e}",
            details={"source": source, "signal_type": signal_type},
        )
        return False

    logger.info(
        "insert source=%s type=%s sev=%s reason=%s",
        source, signal_type, severity, reason,
    )
    return True
