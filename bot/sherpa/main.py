"""Sherpa entry point (Sprint 1).

Loop:
    every 120s:
        1. read latest sentinel_scores row (score_type='fast')
        2. if no score yet -> log + sleep
        3. for each Grid bot active+manual in bot_config:
             a. read current parameters
             b. compute proposed parameters (parameter_rules)
             c. compute proposed_stop_buy_active = (risk > 90)
             d. check cooldown (cooldown_manager)
             e. if SHERPA_MODE=dry_run (default):
                   INSERT sherpa_proposals + log SHERPA_PROPOSAL
             f. if SHERPA_MODE=live:
                   for each non-cooldown changed param: config_writer.write_parameter
                   log SHERPA_ADJUSTMENT (or SHERPA_COOLDOWN per skipped param)

Communication is via Supabase only. If Sentinel is down, Sherpa just
keeps reading the last score it can find — Grid keeps trading on the
parameters bot_config currently holds.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from db.client import get_client
from db.event_logger import log_event
from utils.telegram_notifier import SyncTelegramNotifier

from bot.sentinel.inputs.binance_btc import fetch_price
from bot.sherpa.config_writer import write_parameter
from bot.sherpa.cooldown_manager import latest_manual_change, parameters_in_cooldown
from bot.sherpa.parameter_rules import calculate_parameters, is_changed

logger = logging.getLogger("bagholderai.sherpa")

LOOP_INTERVAL_S = 120
STALE_SCORE_S = 5 * 60          # >5 min old triggers a stale warning
TELEGRAM_THROTTLE_S = 10 * 60   # 1 message per kind per bot per 10 min
PROPOSED_PARAMS = ("buy_pct", "sell_pct", "idle_reentry_hours")
RISK_STOP_BUY_THRESHOLD = 90    # would-have-activated stop_buy on Grid


def _silence_third_party_loggers() -> None:
    for name in ("httpx", "httpcore", "telegram", "telegram.ext"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _is_dry_run() -> bool:
    """SHERPA_MODE controls dry-run vs live. Default = dry_run (any value
    other than the literal 'live' is treated as dry-run for safety)."""
    mode = os.environ.get("SHERPA_MODE", "dry_run").strip().lower()
    return mode != "live"


def run_sherpa() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _silence_third_party_loggers()

    supabase = get_client()
    notifier = SyncTelegramNotifier()
    dry_run = _is_dry_run()
    mode_str = "dry_run" if dry_run else "live"

    shutting_down = {"v": False}

    def shutdown(signum, frame):
        if shutting_down["v"]:
            sys.exit(1)
        shutting_down["v"] = True
        logger.info(f"Sherpa shutting down (mode={mode_str})...")
        log_event(
            severity="info",
            category="lifecycle",
            event="SHERPA_STOP",
            message=f"Sherpa stopped (signal={signum})",
            details={"signal": int(signum) if signum else None, "mode": mode_str},
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(f"Sherpa starting (Sprint 1, mode={mode_str})...")
    log_event(
        severity="info",
        category="lifecycle",
        event="SHERPA_START",
        message=f"Sherpa started (mode={mode_str})",
        details={"version": "sprint1", "mode": mode_str},
    )

    last_alert_ts: dict[str, float] = {}
    # Telegram now alerts only when Sherpa's PROPOSAL changes between
    # cycles (not when it differs from current bot_config). last_proposed
    # holds the most recent proposed-params per symbol so we can compare.
    # Bootstrapped from sherpa_proposals so a restart doesn't generate a
    # spurious "first message" wave for proposals that haven't changed.
    last_proposed: dict[str, dict] = _bootstrap_last_proposed(supabase)
    # last_stop_buy_active mirrors the same logic for the boolean
    # proposed_stop_buy_active flag — only alert when it flips.
    last_stop_buy_active: dict[str, bool] = {}

    while not shutting_down["v"]:
        try:
            score = _fetch_latest_score(supabase)
            if score is None:
                logger.info("No sentinel_scores yet; sleeping.")
                time.sleep(LOOP_INTERVAL_S)
                continue

            score_age_s = _score_age_seconds(score)
            if score_age_s is not None and score_age_s > STALE_SCORE_S:
                logger.warning(f"Sentinel score is {score_age_s:.0f}s old (stale).")
                log_event(
                    severity="warn",
                    category="safety",
                    event="SHERPA_STALE_SCORE",
                    message=f"Score age {score_age_s:.0f}s",
                    details={"score_age_seconds": score_age_s, "last_score_at": score.get("created_at")},
                )

            risk = int(score.get("risk_score", 50))
            opp = int(score.get("opportunity_score", 50))
            fast_signals = _signals_from_score(score)
            proposed_params, breakdown = calculate_parameters(
                regime="neutral", fast_signals=fast_signals
            )
            proposed_stop_buy_active = risk > RISK_STOP_BUY_THRESHOLD
            proposed_regime = breakdown.get("regime", "neutral")

            bots = _fetch_active_manual_bots(supabase)
            for bot in bots:
                # symbol_price is fetched per-bot from Binance spot. Best-
                # effort: a fetch failure logs and stores None — the row
                # still gets written, replay can fall back to klines for
                # that timestamp.
                symbol_price = _fetch_symbol_price(bot["symbol"])
                _handle_bot(
                    supabase=supabase,
                    notifier=notifier,
                    bot=bot,
                    risk=risk,
                    opp=opp,
                    proposed=proposed_params,
                    proposed_regime=proposed_regime,
                    proposed_stop_buy_active=proposed_stop_buy_active,
                    btc_price=score.get("btc_price"),
                    symbol_price=symbol_price,
                    dry_run=dry_run,
                    last_alert_ts=last_alert_ts,
                    last_proposed=last_proposed,
                    last_stop_buy_active=last_stop_buy_active,
                )

        except Exception as e:
            logger.error(f"Sherpa loop error: {e}", exc_info=True)
            log_event(
                severity="error",
                category="error",
                event="SHERPA_ERROR",
                message=str(e)[:300],
                details={"source": "main_loop"},
            )

        time.sleep(LOOP_INTERVAL_S)


def _bootstrap_last_proposed(supabase) -> dict[str, dict]:
    """Read the latest sherpa_proposals row per active manual symbol so a
    restart doesn't trigger a fresh Telegram wave for proposals that
    haven't actually changed.

    Returns a dict {symbol: {buy_pct, sell_pct, idle_reentry_hours}}.
    Symbols with no prior proposal are simply absent — first cycle after
    boot will alert as a 'first proposal' for them, which is correct.
    """
    out: dict[str, dict] = {}
    try:
        # Pull a generous window (last 6 hours, ~180 rows) and pick the
        # most recent row per symbol. PostgREST doesn't expose DISTINCT ON
        # via the JS client; doing it client-side is fine for 6 symbols.
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        rows = (
            supabase.table("sherpa_proposals")
            .select("symbol, proposed_buy_pct, proposed_sell_pct, "
                    "proposed_idle_reentry_hours, created_at")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .execute()
        )
        for row in (rows.data or []):
            symbol = row["symbol"]
            if symbol in out:
                continue  # already have the most recent for this symbol
            out[symbol] = {
                "buy_pct": _f(row.get("proposed_buy_pct")),
                "sell_pct": _f(row.get("proposed_sell_pct")),
                "idle_reentry_hours": _f(row.get("proposed_idle_reentry_hours")),
            }
        logger.info(f"Bootstrapped last_proposed for {len(out)} symbols")
    except Exception as e:
        logger.warning(f"last_proposed bootstrap failed: {e}")
    return out


def _fetch_latest_score(supabase) -> Optional[dict]:
    res = (
        supabase.table("sentinel_scores")
        .select("*")
        .eq("score_type", "fast")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def _score_age_seconds(score: dict) -> Optional[float]:
    created_at = score.get("created_at")
    if not created_at:
        return None
    try:
        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except Exception:
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds()


def _signals_from_score(score: dict) -> dict:
    """Sentinel writes the raw signals back into sentinel_scores.raw_signals;
    fall back to the top-level columns when raw_signals is missing.
    """
    raw = score.get("raw_signals") or {}
    return {
        "btc_change_1h": raw.get("btc_change_1h", score.get("btc_change_1h")),
        "speed_of_fall_accelerating": raw.get("speed_of_fall_accelerating", False),
        "funding_rate": score.get("funding_rate"),
    }


def _fetch_active_manual_bots(supabase) -> list[dict]:
    res = (
        supabase.table("bot_config")
        .select(
            "symbol, is_active, managed_by, buy_pct, sell_pct, "
            "idle_reentry_hours, stop_buy_drawdown_pct"
        )
        .eq("is_active", True)
        .eq("managed_by", "manual")
        .execute()
    )
    return res.data or []


def _fetch_symbol_price(symbol: str) -> Optional[float]:
    """Convert 'BONK/USDT' -> 'BONKUSDT' and fetch the spot price.
    Returns None on any error (network, unknown symbol). Sherpa never
    blocks on a missing price.
    """
    binance_symbol = symbol.replace("/", "")
    try:
        return fetch_price(binance_symbol)
    except Exception as e:
        logger.warning(f"symbol_price fetch failed for {symbol}: {e}")
        return None


def _handle_bot(
    supabase,
    notifier: SyncTelegramNotifier,
    bot: dict,
    risk: int,
    opp: int,
    proposed: dict,
    proposed_regime: str,
    proposed_stop_buy_active: bool,
    btc_price,
    symbol_price,
    dry_run: bool,
    last_alert_ts: dict,
    last_proposed: dict,
    last_stop_buy_active: dict,
) -> None:
    symbol = bot["symbol"]
    current = {
        "buy_pct": _f(bot.get("buy_pct")),
        "sell_pct": _f(bot.get("sell_pct")),
        "idle_reentry_hours": _f(bot.get("idle_reentry_hours")),
    }

    cooldown_locked = parameters_in_cooldown(supabase, symbol, PROPOSED_PARAMS)
    cooldown_active = bool(cooldown_locked)

    changed_params = [p for p in PROPOSED_PARAMS if is_changed(current[p], proposed[p])]
    would_have_changed = bool(changed_params)

    # Per-bot alert gating: emit a Telegram only when Sherpa's PROPOSAL
    # changes between cycles (not when it merely differs from current).
    # The previous behavior would fire one message every TELEGRAM_THROTTLE_S
    # for as long as proposed != current — even if Sherpa kept proposing
    # the same exact thing. The new rule: alert only on a fresh proposal,
    # then stay silent until the proposal *itself* changes again.
    prev = last_proposed.get(symbol)
    proposal_changed = (prev is None) or any(
        is_changed(prev.get(p), proposed[p]) for p in PROPOSED_PARAMS
    )
    last_proposed[symbol] = dict(proposed)

    prev_stop_buy = last_stop_buy_active.get(symbol)
    stop_buy_flipped = (prev_stop_buy is None and proposed_stop_buy_active) \
        or (prev_stop_buy is not None and prev_stop_buy != proposed_stop_buy_active)
    last_stop_buy_active[symbol] = proposed_stop_buy_active

    if dry_run:
        # Write to sherpa_proposals only when there's a counterfactual
        # signal to record: would_have_changed=true OR a stop_buy
        # would-have-activated event OR a cooldown skip. No-op cycles
        # (proposed == current, no cooldown, no stop_buy) are pure
        # noise for replay analysis and would 3x the write volume.
        # Per-proposal SHERPA_PROPOSAL events also dropped — sherpa_proposals
        # already captures the row; doubling it in bot_events_log added
        # ~2,400 rows/day with no information gain. Lifecycle/cooldown/
        # error events still go through log_event below.
        if would_have_changed or proposed_stop_buy_active or cooldown_active:
            _insert_proposal(
                supabase=supabase,
                symbol=symbol,
                risk=risk,
                opp=opp,
                current=current,
                proposed=proposed,
                proposed_regime=proposed_regime,
                current_stop_buy_drawdown_pct=_f(bot.get("stop_buy_drawdown_pct")),
                proposed_stop_buy_active=proposed_stop_buy_active,
                cooldown_active=cooldown_active,
                cooldown_parameters=cooldown_locked,
                would_have_changed=would_have_changed,
                btc_price=btc_price,
                symbol_price=symbol_price,
            )
        # Alert gate: would_have_changed is the precondition (no point
        # telling Max "I'd adjust" when proposed == current), AND the
        # proposal must have moved since last cycle. Stop-buy flip is
        # treated as its own alert reason — even if params didn't move,
        # the risk crossing 90 is news worth surfacing.
        if (would_have_changed and proposal_changed) or stop_buy_flipped:
            _alert_dry_run(notifier, last_alert_ts, symbol, current, proposed)
        return

    # LIVE mode.
    for parameter in changed_params:
        if parameter in cooldown_locked:
            mc = latest_manual_change(supabase, symbol, parameter)
            log_event(
                severity="info",
                category="config",
                event="SHERPA_COOLDOWN",
                message=f"Skip {symbol}.{parameter}: cooldown",
                symbol=symbol,
                details={
                    "parameter": parameter,
                    "manual_change_at": (mc or {}).get("created_at"),
                    "manual_changed_by": (mc or {}).get("changed_by"),
                },
            )
            _alert_cooldown(notifier, last_alert_ts, symbol, parameter, mc)
            continue

        ok = write_parameter(
            supabase,
            symbol=symbol,
            parameter=parameter,
            new_value=proposed[parameter],
            old_value=current[parameter],
        )
        if ok:
            log_event(
                severity="info",
                category="config",
                event="SHERPA_ADJUSTMENT",
                message=f"{symbol}.{parameter} {current[parameter]} -> {proposed[parameter]}",
                symbol=symbol,
                details={
                    "parameter": parameter,
                    "old": current[parameter],
                    "new": proposed[parameter],
                    "risk_score": risk,
                },
            )
    if (would_have_changed and proposal_changed
            and any(p not in cooldown_locked for p in changed_params)):
        _alert_live(notifier, last_alert_ts, symbol, current, proposed)


def _insert_proposal(
    supabase,
    symbol: str,
    risk: int,
    opp: int,
    current: dict,
    proposed: dict,
    proposed_regime: str,
    current_stop_buy_drawdown_pct: Optional[float],
    proposed_stop_buy_active: bool,
    cooldown_active: bool,
    cooldown_parameters: list[str],
    would_have_changed: bool,
    btc_price,
    symbol_price,
) -> None:
    try:
        supabase.table("sherpa_proposals").insert({
            "symbol": symbol,
            "risk_score": risk,
            "opportunity_score": opp,
            "current_buy_pct": current["buy_pct"],
            "current_sell_pct": current["sell_pct"],
            "current_idle_reentry_hours": current["idle_reentry_hours"],
            "proposed_buy_pct": proposed["buy_pct"],
            "proposed_sell_pct": proposed["sell_pct"],
            "proposed_idle_reentry_hours": proposed["idle_reentry_hours"],
            "proposed_regime": proposed_regime,
            "current_stop_buy_drawdown_pct": current_stop_buy_drawdown_pct,
            "proposed_stop_buy_active": proposed_stop_buy_active,
            "cooldown_active": cooldown_active,
            "cooldown_parameters": cooldown_parameters,
            "would_have_changed": would_have_changed,
            "btc_price": btc_price,
            "symbol_price": symbol_price,
        }).execute()
    except Exception as e:
        logger.error(f"sherpa_proposals insert failed for {symbol}: {e}")


def _alert_dry_run(
    notifier: SyncTelegramNotifier,
    last_alert_ts: dict,
    symbol: str,
    current: dict,
    proposed: dict,
) -> None:
    key = f"dry_run:{symbol}"
    now = time.time()
    if now - last_alert_ts.get(key, 0) < TELEGRAM_THROTTLE_S:
        return
    try:
        notifier.send_message(
            f"🏔️ <b>Sherpa [DRY_RUN]</b>: would adjust {symbol} — "
            f"buy_pct {_fmt(current['buy_pct'])}→{_fmt(proposed['buy_pct'])}, "
            f"sell_pct {_fmt(current['sell_pct'])}→{_fmt(proposed['sell_pct'])}"
        )
        last_alert_ts[key] = now
    except Exception as e:
        logger.warning(f"Telegram dry_run alert failed: {e}")


def _alert_live(
    notifier: SyncTelegramNotifier,
    last_alert_ts: dict,
    symbol: str,
    current: dict,
    proposed: dict,
) -> None:
    key = f"live:{symbol}"
    now = time.time()
    if now - last_alert_ts.get(key, 0) < TELEGRAM_THROTTLE_S:
        return
    try:
        notifier.send_message(
            f"🏔️ <b>Sherpa</b>: adjusted {symbol} — "
            f"buy_pct {_fmt(current['buy_pct'])}→{_fmt(proposed['buy_pct'])}, "
            f"sell_pct {_fmt(current['sell_pct'])}→{_fmt(proposed['sell_pct'])}"
        )
        last_alert_ts[key] = now
    except Exception as e:
        logger.warning(f"Telegram live alert failed: {e}")


def _alert_cooldown(
    notifier: SyncTelegramNotifier,
    last_alert_ts: dict,
    symbol: str,
    parameter: str,
    manual_change: Optional[dict],
) -> None:
    key = f"cooldown:{symbol}:{parameter}"
    now = time.time()
    if now - last_alert_ts.get(key, 0) < TELEGRAM_THROTTLE_S:
        return
    when = (manual_change or {}).get("created_at", "")
    try:
        notifier.send_message(
            f"⏸️ <b>Sherpa</b>: skipping {parameter} on {symbol} — "
            f"Board override active (since {when})"
        )
        last_alert_ts[key] = now
    except Exception as e:
        logger.warning(f"Telegram cooldown alert failed: {e}")


def _f(v) -> Optional[float]:
    return None if v is None else float(v)


def _fmt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.2f}"


if __name__ == "__main__":
    run_sherpa()
