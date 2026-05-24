"""NewsKeeper entry point (5th brain, S83 Session 1 — RSS feeds only).

Loop:
    every NEWSKEEPER_INTERVAL_S (15 min):
        1. rss_feeds.fetch_signals() -> list of candidates
        2. signal_writer.write_if_changed for each
        (future S2: etf_flows.fetch_signals + macro_calendar.fetch_signals)

Comm with Sherpa/Sentinel is via Supabase only — NewsKeeper never imports
the other brains and vice versa. If NewsKeeper crashes the orchestrator
will own restart (wired in S2); for S1 the process is launched manually
for stand-alone tests, no orchestrator wiring yet.

Source choice S83 pivot 2026-05-24: brief originally specified CryptoPanic
free Developer API, but that tier was discontinued 2026-04-01. RSS feeds
(CoinDesk + CoinTelegraph + Decrypt) are the Board-approved substitute —
zero auth, zero paywall risk, keyword-classified for now (Haiku
classification arrives in S3-4 with the Strategist).

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

from bot.newskeeper import signal_writer
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

    logger.info(
        "NewsKeeper starting (S1 — RSS feeds only, interval=%ds)",
        NEWSKEEPER_INTERVAL_S,
    )
    log_event(
        severity="info",
        category="lifecycle",
        event="NEWSKEEPER_START",
        message="NewsKeeper started",
        details={"version": "s1", "interval_s": NEWSKEEPER_INTERVAL_S},
    )

    while not shutting_down["v"]:
        try:
            candidates = rss_feeds.fetch_signals()
            for c in candidates:
                signal_writer.write_if_changed(
                    supabase,
                    source=c["source"],
                    signal_type=c["signal_type"],
                    severity=c["severity"],
                    summary=c["summary"],
                    raw_data=c.get("raw_data"),
                    expires_at_minutes=c.get("expires_at_minutes"),
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
