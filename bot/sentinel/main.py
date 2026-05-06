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
import signal
import sys
import time

from db.client import get_client
from db.event_logger import log_event
from utils.telegram_notifier import SyncTelegramNotifier

from bot.sentinel.funding_monitor import FundingMonitor
from bot.sentinel.price_monitor import PriceMonitor
from bot.sentinel.score_engine import score

logger = logging.getLogger("bagholderai.sentinel")

SCAN_INTERVAL_S = 60
TELEGRAM_THROTTLE_S = 10 * 60  # max 1 alert of each type per 10 min
RISK_ALERT_THRESHOLD = 70
RISK_CRITICAL_THRESHOLD = 90


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

            log_event(
                severity="info",
                category="safety",
                event="SENTINEL_SCAN",
                message=f"risk={risk} opp={opp}",
                details={
                    "risk_score": risk,
                    "opportunity_score": opp,
                    "btc_price": snapshot.get("btc_price"),
                    "btc_change_1h": snapshot.get("btc_change_1h"),
                    "funding_rate": funding_rate,
                },
            )

            _maybe_alert(notifier, last_alert_ts, risk, snapshot)

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
    """Throttled Telegram alert when risk crosses warn/critical thresholds."""
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
