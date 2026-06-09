"""NewsKeeper v2 entry point — the barometer loop (S100, SHADOW mode).

    every 15 min:
        1. rss_feeds.fetch_candidates()      (reused from v1, same feeds)
        2. preprocessor.preprocess(item)     (reused from v1: content_type,
                                              entities, Python direction-audit)
        3. classifier.classify(env)          (Haiku: relevance/polarity/
                                              event_key/confidence — architecture C)
        4. store.write_signal(...)           (enriched per-item row, kept raw)
        5. aggregator.compute(last 24h)      (dedup -> score -> hysteresis)
        6. store.write_regime(...)           (write-on-change + heartbeat)

Runs STANDALONE on the Mac Mini, ALONGSIDE v1 (`bot.newskeeper`), and NEVER
feeds Sentinel. Launch (Max runs it; v1 keeps running):
    nohup caffeinate -i -s -- venv/bin/python3.13 -m bot.newskeeper_v2.main \
        >> logs/newskeeper_v2.out 2>&1 < /dev/null & disown
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from db.client import get_client
from db.event_logger import log_event

from bot.newskeeper import preprocessor
from bot.newskeeper.readers import rss_feeds
from bot.newskeeper_v2 import aggregator, classifier, store

logger = logging.getLogger("bagholderai.newskeeper_v2")

INTERVAL_S = 15 * 60


def _silence_third_party_loggers() -> None:
    for name in ("httpx", "httpcore", "telegram", "telegram.ext", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _silence_third_party_loggers()

    supabase = get_client()
    params = aggregator.DEFAULT_PARAMS

    shutting_down = {"v": False}

    def shutdown(signum, frame):
        if shutting_down["v"]:
            sys.exit(1)
        shutting_down["v"] = True
        logger.info("NewsKeeper v2 shutting down...")
        log_event(
            severity="info", category="lifecycle", event="NEWSKEEPER_V2_STOP",
            message=f"NewsKeeper v2 stopped (signal={signum})",
            details={"signal": int(signum) if signum else None},
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Boot: resume the published state; pending is in-memory (restart-safe).
    current = store.load_state(supabase)
    pending = None
    pending_since = None
    haiku_ready = bool(os.getenv("ANTHROPIC_API_KEY"))

    logger.info(
        "NewsKeeper v2 (barometer) starting — state=%s, interval=%ds, haiku=%s",
        current, INTERVAL_S, "ready" if haiku_ready else "MISSING-KEY(abstain)",
    )
    log_event(
        severity="info", category="lifecycle", event="NEWSKEEPER_V2_START",
        message="NewsKeeper v2 barometer started (shadow)",
        details={"state": current, "haiku_key_present": haiku_ready},
    )

    while not shutting_down["v"]:
        try:
            # 1-4. classify + persist this tick's articles
            candidates = rss_feeds.fetch_candidates()
            written = 0
            for item in candidates:
                env = preprocessor.preprocess(item)
                cls = classifier.classify(env)
                if store.write_signal(supabase, item, cls):
                    written += 1

            # 5. recompute the barometer over the last 24h
            votes = store.fetch_votes_24h(supabase, params.window_h)
            now = datetime.now(timezone.utc)
            result = aggregator.compute(
                votes, now, current, pending, pending_since, params
            )
            score = result.score
            decision = result.decision
            pending, pending_since = decision.pending, decision.pending_since

            # 6. write-on-change + heartbeat
            if decision.flipped:
                store.write_regime(
                    supabase, decision.state, current, score.raw_score,
                    score.abstain_frac, score.vote_count, is_flip=True,
                )
                logger.info(
                    "BAROMETER FLIP %s -> %s (score=%.3f, votes=%d, abstain=%.0f%%)",
                    current, decision.state, score.raw_score,
                    score.vote_count, score.abstain_frac * 100,
                )
                log_event(
                    severity="info", category="lifecycle",
                    event="NEWSKEEPER_V2_STATE_CHANGE",
                    message=f"barometer {current} -> {decision.state}",
                    details={
                        "from": current, "to": decision.state,
                        "raw_score": score.raw_score, "votes": score.vote_count,
                        "abstain_frac": score.abstain_frac,
                    },
                )
                current = decision.state
            else:
                age = store.last_regime_age_seconds(supabase)
                if age is None or age >= store.HEARTBEAT_H * 3600:
                    store.write_regime(
                        supabase, current, current, score.raw_score,
                        score.abstain_frac, score.vote_count, is_flip=False,
                    )

            logger.info(
                "v2 tick: %d candidate(s) -> %d written | state=%s score=%.3f "
                "votes=%d abstain=%.0f%% pending=%s",
                len(candidates), written, current, score.raw_score,
                score.vote_count, score.abstain_frac * 100, pending,
            )
        except Exception as e:
            logger.error("NewsKeeper v2 loop error: %s", e, exc_info=True)
            log_event(
                severity="error", category="error", event="NEWSKEEPER_V2_ERROR",
                message=str(e)[:300], details={"source": "main_loop"},
            )

        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    run()
