"""NewsKeeper entry point (5th brain, S83 Session 1 → S94a Session 2).

Loop:
    every NEWSKEEPER_INTERVAL_S (15 min):
        1. rss_feeds.fetch_candidates()   -> raw items (filtered, deduped)
        2. preprocessor.preprocess(item)  -> structured envelope
        3. haiku_classifier.classify()    -> theme/impact/severity + guardrails
        4. signal_writer.write_if_changed  for each signal-worthy item

Comm with Sherpa/Sentinel is via Supabase only — NewsKeeper never imports
the other brains and vice versa. NewsKeeper runs STANDALONE (not orchestrator-
managed): launched manually on the Mac Mini (memoria
reference_newskeeper_standalone_launch).

S94a (Session 2): the keyword regex no longer classifies — it only gates
crypto/macro relevance. Haiku (claude-haiku-4-5) classifies, with Python
pre-computing the authoritative `direction` and running post-call guardrails.
Macro feeds (BBC Business + MarketWatch) added. Requires ANTHROPIC_API_KEY in
the environment; without it every item degrades LOUDLY to the regex fallback.

Telegram: silenced by default (memoria feedback_no_telegram_alerts) — set
NEWSKEEPER_TELEGRAM_ENABLED=true to enable.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

from db.client import get_client
from db.event_logger import log_event

from bot.newskeeper import haiku_classifier, preprocessor, signal_writer
from bot.newskeeper.readers import rss_feeds

logger = logging.getLogger("bagholderai.newskeeper")

NEWSKEEPER_INTERVAL_S = 15 * 60  # brief §Sessions 1-2 default

TELEGRAM_ENABLED = (
    os.getenv("NEWSKEEPER_TELEGRAM_ENABLED", "false").lower() == "true"
)


def _silence_third_party_loggers() -> None:
    """Stop httpx/telegram/urllib3 from leaking tokens via INFO logs."""
    for name in ("httpx", "httpcore", "telegram", "telegram.ext", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def run_newskeeper() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _silence_third_party_loggers()

    supabase = get_client()

    shutting_down = {"v": False}

    def shutdown(signum, frame):
        if shutting_down["v"]:
            sys.exit(1)
        shutting_down["v"] = True
        logger.info("NewsKeeper shutting down...")
        log_event(
            severity="info",
            category="lifecycle",
            event="NEWSKEEPER_STOP",
            message=f"NewsKeeper stopped (signal={signum})",
            details={"signal": int(signum) if signum else None},
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    haiku_ready = bool(os.getenv("ANTHROPIC_API_KEY"))
    logger.info(
        "NewsKeeper starting (S2 — Haiku classifier, interval=%ds, haiku=%s)",
        NEWSKEEPER_INTERVAL_S, "ready" if haiku_ready else "MISSING-KEY(regex fallback)",
    )
    log_event(
        severity="info",
        category="lifecycle",
        event="NEWSKEEPER_START",
        message="NewsKeeper started",
        details={
            "version": "s2",
            "interval_s": NEWSKEEPER_INTERVAL_S,
            "haiku_key_present": haiku_ready,
        },
    )

    while not shutting_down["v"]:
        try:
            candidates = rss_feeds.fetch_candidates()
            written = 0
            for item in candidates:
                envelope = preprocessor.preprocess(item)
                cls = haiku_classifier.classify(envelope)
                # None = not signal-worthy (regex fallback path); irrelevant =
                # Haiku says no crypto-market impact. Both are dropped — that
                # filtering IS the S2 noise reduction.
                if cls is None or cls.get("theme") == "irrelevant":
                    continue
                raw_data = dict(item)
                raw_data.update({
                    "feed_source": envelope.get("feed_source"),
                    "entities": envelope.get("entities"),
                    "numbers": envelope.get("numbers"),
                    "direction": cls.get("direction"),
                    "market_impact": cls.get("market_impact"),
                    "confidence": cls.get("confidence"),
                    "reasoning": cls.get("reasoning"),
                    "classifier_version": cls.get("classifier_version"),
                })
                if signal_writer.write_if_changed(
                    supabase,
                    source="rss_feeds",
                    signal_type=cls["theme"],
                    severity=cls["severity"],
                    summary=item["title"][:280],
                    raw_data=raw_data,
                    expires_at_minutes=24 * 60,
                ):
                    written += 1
            if candidates:
                logger.info(
                    "NewsKeeper: %d candidate(s) -> %d signal(s) written",
                    len(candidates), written,
                )
        except Exception as e:
            logger.error(f"NewsKeeper loop error: {e}", exc_info=True)
            log_event(
                severity="error",
                category="error",
                event="NEWSKEEPER_ERROR",
                message=str(e)[:300],
                details={"source": "main_loop"},
            )

        time.sleep(NEWSKEEPER_INTERVAL_S)


if __name__ == "__main__":
    run_newskeeper()
