"""Sentinel entry point (Sprint 1).

Loop:
    every 60s:
        1. fetch BTC ticker, append to rolling buffer
        2. compute window deltas + speed_of_fall flag
        3. read funding rate (cached 8h)
        4. score_engine -> (risk, opportunity, breakdown)
        5. INSERT sentinel_scores
        6. log SENTINEL_SCAN in bot_events_log

Comm with Sherpa is via Supabase only — Sentinel never imports Sherpa
and vice versa. If Sentinel crashes, the orchestrator restarts it; in
the gap, Sherpa keeps using the last score it can read from the DB.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

from db.client import get_client
from db.event_logger import log_event
from utils.telegram_notifier import SyncTelegramNotifier

from bot.sentinel import slow_loop
from bot.sentinel.funding_monitor import FundingMonitor
from bot.sentinel.price_monitor import PriceMonitor
from bot.sentinel.score_engine import score

logger = logging.getLogger("bagholderai.sentinel")

SCAN_INTERVAL_S = 60
TELEGRAM_THROTTLE_S = 10 * 60  # max 1 alert of each type per 10 min
RISK_ALERT_THRESHOLD = 70
RISK_CRITICAL_THRESHOLD = 90

# Sprint 2 (S78): slow loop cadence. Every SLOW_LOOP_INTERVAL_S the
# Sentinel pulls F&G + CMC, decides a regime, and writes a
# score_type='slow' row. Sherpa reads the latest slow row to pick the
# BASE_TABLE regime to start from.
SLOW_LOOP_INTERVAL_S = 4 * 60 * 60  # 4 hours
SLOW_LOOP_EVERY_N_TICKS = SLOW_LOOP_INTERVAL_S // SCAN_INTERVAL_S  # 240

# Brief 70b (S70 2026-05-10): default OFF al riavvio post-DRY_RUN per
# evitare spam Telegram durante calibrazione. Max abilita via env quando
# vuole. Memoria `feedback_no_telegram_alerts`: feature di monitoring
# vanno in /admin, non Telegram.
TELEGRAM_ENABLED = os.getenv("SENTINEL_TELEGRAM_ENABLED", "false").lower() == "true"


def _silence_third_party_loggers() -> None:
    """Stop httpx/telegram from leaking tokens via INFO logs (cf. 8.x)."""
    for name in ("httpx", "httpcore", "telegram", "telegram.ext"):
        logging.getLogger(name).setLevel(logging.WARNING)


def run_sentinel() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _silence_third_party_loggers()

    supabase = get_client()
    notifier = SyncTelegramNotifier()
    price = PriceMonitor()
    funding = FundingMonitor()

    shutting_down = {"v": False}

    def shutdown(signum, frame):
        if shutting_down["v"]:
            sys.exit(1)
        shutting_down["v"] = True
        logger.info("Sentinel shutting down...")
        log_event(
            severity="info",
            category="lifecycle",
            event="SENTINEL_STOP",
            message=f"Sentinel stopped (signal={signum})",
            details={"signal": int(signum) if signum else None},
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Sentinel starting (Sprint 1, fast loop)...")
    log_event(
        severity="info",
        category="lifecycle",
        event="SENTINEL_START",
        message="Sentinel started",
        details={"version": "sprint1"},
    )

    # Best-effort: warm the price buffer with the last 60 minutes of
    # 1m klines so the 1h window is usable from the first scan.
    price.warm_up_from_klines()

    last_alert_ts: dict[str, float] = {}
    # Sprint 2: start the counter AT the threshold so the very first
    # iteration fires a slow tick. After that, every SLOW_LOOP_EVERY_N_TICKS
    # ticks (=240 ticks = 4h) it fires again.
    slow_tick_counter = SLOW_LOOP_EVERY_N_TICKS

    while not shutting_down["v"]:
        try:
            snapshot = price.tick()
            funding_rate = funding.get_rate()
            signals = {
                "btc_change_1h": snapshot.get("btc_change_1h"),
                "speed_of_fall_accelerating": snapshot.get(
                    "speed_of_fall_accelerating", False
                ),
                "funding_rate": funding_rate,
            }
            risk, opp, breakdown = score(signals)

            raw_signals = {
                "btc_change_5m": snapshot.get("btc_change_5m"),
                "btc_change_15m": snapshot.get("btc_change_15m"),
                "btc_change_1h": snapshot.get("btc_change_1h"),
                "btc_change_4h": snapshot.get("btc_change_4h"),
                "speed_of_fall_accelerating": snapshot.get(
                    "speed_of_fall_accelerating", False
                ),
                "samples": snapshot.get("samples", 0),
                "breakdown": breakdown,
            }

            try:
                supabase.table("sentinel_scores").insert({
                    "score_type": "fast",
                    "risk_score": risk,
                    "opportunity_score": opp,
                    "btc_price": snapshot.get("btc_price"),
                    "btc_change_1h": snapshot.get("btc_change_1h"),
                    "btc_change_24h": snapshot.get("btc_change_24h"),
                    "funding_rate": funding_rate,
                    "raw_signals": raw_signals,
                }).execute()
            except Exception as e:
                logger.error(f"sentinel_scores insert failed: {e}")
                log_event(
                    severity="error",
                    category="error",
                    event="SENTINEL_ERROR",
                    message=f"sentinel_scores insert failed: {e}",
                    details={"source": "supabase_insert"},
                )

            # Per-scan event logging removed: every scan already lands as
            # a sentinel_scores row; duplicating it in bot_events_log
            # doubled the write volume for no gain. Errors and lifecycle
            # events still go through log_event below.

            _maybe_alert(notifier, last_alert_ts, risk, snapshot)

            # Sprint 2: slow tick (regime detection) every 4h, plus
            # once at boot. Wrapped so any failure here cannot crash
            # the fast loop; slow_loop.tick() itself also swallows
            # internal errors and just logs them.
            slow_tick_counter += 1
            if slow_tick_counter >= SLOW_LOOP_EVERY_N_TICKS:
                slow_tick_counter = 0
                try:
                    slow_loop.tick(supabase)
                except Exception as e:
                    logger.error(f"Slow tick failed: {e}", exc_info=True)
                    log_event(
                        severity="error",
                        category="error",
                        event="SENTINEL_SLOW_ERROR",
                        message=str(e)[:300],
                        details={"source": "slow_loop"},
                    )

        except Exception as e:
            logger.error(f"Sentinel loop error: {e}", exc_info=True)
            log_event(
                severity="error",
                category="error",
                event="SENTINEL_ERROR",
                message=str(e)[:300],
                details={"source": "main_loop"},
            )

        time.sleep(SCAN_INTERVAL_S)


def _maybe_alert(
    notifier: SyncTelegramNotifier,
    last_alert_ts: dict[str, float],
    risk: int,
    snapshot: dict,
) -> None:
    """Throttled Telegram alert when risk crosses warn/critical thresholds.

    Brief 70b: silenzioso se SENTINEL_TELEGRAM_ENABLED=false (default).
    """
    if not TELEGRAM_ENABLED:
        return
    now = time.time()
    change_1h = snapshot.get("btc_change_1h")
    change_str = f"{change_1h:+.2f}%" if change_1h is not None else "n/a"

    if risk >= RISK_CRITICAL_THRESHOLD:
        key = "risk_critical"
        if now - last_alert_ts.get(key, 0) >= TELEGRAM_THROTTLE_S:
            try:
                notifier.send_message(
                    f"🚨 <b>SENTINEL ALERT</b>: risk {risk}/100 — "
                    f"BTC {change_str} in 1h. Full defensive."
                )
                last_alert_ts[key] = now
            except Exception as e:
                logger.warning(f"Telegram alert failed: {e}")
    elif risk >= RISK_ALERT_THRESHOLD:
        key = "risk_warn"
        if now - last_alert_ts.get(key, 0) >= TELEGRAM_THROTTLE_S:
            try:
                notifier.send_message(
                    f"🛡️ <b>Sentinel</b>: risk {risk}/100 — "
                    f"BTC {change_str} in 1h. Sherpa switching to defensive."
                )
                last_alert_ts[key] = now
            except Exception as e:
                logger.warning(f"Telegram alert failed: {e}")


if __name__ == "__main__":
    run_sentinel()
