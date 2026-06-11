"""Sherpa entry point (Sprint 2, Brief 81a).

Loop:
    every 120s:
        1. read latest sentinel_scores row with score_type='slow'
           (4h cadence; falls back to defaults if no row yet)
        2. read regime via regime_reader (slow-loop derived)
        3. compute per-coin volatility multipliers (cached 1h)
        4. for each Grid bot active+manual in bot_config:
             a. read current parameters
             b. compute proposed parameters (parameter_rules):
                base(regime) × volatility_multiplier, clamped, capped vs current
             c. compute proposed_stop_buy_active = (regime == "extreme_fear")
             d. check cooldown (cooldown_manager)
             e. if SHERPA_MODE=dry_run (default):
                   INSERT sherpa_proposals (with on-change + heartbeat filter)
             f. if SHERPA_MODE=live:
                   for each non-cooldown changed param: config_writer.write_parameter

Brief 81a explicit changes vs Sprint 1:
- Fast-loop signals removed (449 flips in 16d caused 6-minute flicker).
- Per-coin volatility scaling (BONK no longer gets BTC's sell_pct=1.5).
- Amplitude cap |Δ|/current ≤ MAX_DELTA_PCT (configurable).

Sentinel is NOT modified by this brief; the decoupling is implemented
via query filter (score_type='slow') on Sherpa's side only.

Communication is via Supabase only. If Sentinel is down, Sherpa keeps
reading the last available slow score — Grid keeps trading on the
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
from bot.sherpa.regime_reader import get_current_regime
from bot.sherpa.volatility import get_volatility_multipliers

logger = logging.getLogger("bagholderai.sherpa")

LOOP_INTERVAL_S = 120

# Brief 79c (S79 2026-05-18): even when the on-change filter skips an
# insert, write at least one row per symbol per SHERPA_HEARTBEAT_S so
# dashboards know Sherpa is alive.
# Brief S102 (2026-06-11): 600s -> 4h, aligned with the Sentinel slow
# loop — the regime (the only dynamic input) can't move faster than
# that, so a denser heartbeat adds rows without information. Floor in
# a stable market: 3 coins × 6/day = 18 rows/day.
SHERPA_HEARTBEAT_S = 4 * 60 * 60  # 4h
# Brief 81a (Sprint 2): Sherpa now reads slow-loop rows, emitted every 4h.
# Stale window is 6h = 4h cadence + 2h slack for backend hiccups.
STALE_SCORE_S = 6 * 60 * 60
TELEGRAM_THROTTLE_S = 10 * 60   # 1 message per kind per bot per 10 min
PROPOSED_PARAMS = ("buy_pct", "sell_pct", "idle_reentry_hours")
# Brief 81a Block 2: stop_buy is now derived from the slow-loop regime
# (decision Board 2026-05-22: extreme_fear → stop_buy lamp ON), replacing
# the Sprint-1 fast-loop threshold risk_score > 90.
STOP_BUY_REGIME = "extreme_fear"

# Brief 70b (S70 2026-05-10): default OFF al riavvio post-DRY_RUN per
# evitare spam Telegram durante calibrazione. Max abilita via env quando
# vuole. Memoria `feedback_no_telegram_alerts`.
TELEGRAM_ENABLED = os.getenv("SHERPA_TELEGRAM_ENABLED", "false").lower() == "true"


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
    # proposed_stop_buy_active flag — only alert/write when it flips.
    # S102: seeded from the same bootstrap, otherwise every restart in a
    # persistent extreme_fear regime would write/alert one spurious
    # "flip" per symbol.
    last_stop_buy_active: dict[str, bool] = {
        s: v["stop_buy_active"]
        for s, v in last_proposed.items()
        if v.get("stop_buy_active") is not None
    }
    # Brief 79c (S79): per-symbol heartbeat — write a row at least every
    # SHERPA_HEARTBEAT_S even when the existing on-change filter skips it.
    # First tick post-restart always writes (default 0.0).
    last_write_ts_per_symbol: dict[str, float] = {}
    # S102: skipped-write counter per symbol, surfaced in the heartbeat
    # log line so the console stays quiet between heartbeats.
    skips_since_write: dict[str, int] = {}

    while not shutting_down["v"]:
        try:
            # Brief 81a Block 2: read slow-loop row only (4h cadence).
            # If no slow row yet, fall back to defaults — the loop still
            # proposes neutral params so dashboards stay alive.
            score = _fetch_latest_slow_score(supabase)
            if score is None:
                logger.info("No slow sentinel_scores row yet; using defaults.")
                risk = 50
                opp = 50
                btc_price = None
            else:
                score_age_s = _score_age_seconds(score)
                if score_age_s is not None and score_age_s > STALE_SCORE_S:
                    logger.warning(
                        f"Slow sentinel score is {score_age_s:.0f}s old (stale)."
                    )
                    log_event(
                        severity="warn",
                        category="safety",
                        event="SHERPA_STALE_SCORE",
                        message=f"Slow score age {score_age_s:.0f}s",
                        details={
                            "score_age_seconds": score_age_s,
                            "last_score_at": score.get("created_at"),
                            "score_type": "slow",
                        },
                    )
                risk = int(score.get("risk_score") or 50)
                opp = int(score.get("opportunity_score") or 50)
                btc_price = score.get("btc_price")

            current_regime = get_current_regime(supabase)
            proposed_stop_buy_active = (current_regime == STOP_BUY_REGIME)

            bots = _fetch_active_manual_bots(supabase)
            # Brief 81a Block 1: per-coin volatility multipliers, computed
            # once per cycle and cached 1h inside volatility module.
            symbols = [b["symbol"] for b in bots]
            multipliers = get_volatility_multipliers(symbols)

            for bot in bots:
                symbol = bot["symbol"]
                current_params = {
                    "buy_pct": _f(bot.get("buy_pct")),
                    "sell_pct": _f(bot.get("sell_pct")),
                    "idle_reentry_hours": _f(bot.get("idle_reentry_hours")),
                }
                vol_mult = multipliers.get(symbol, 1.0)
                proposed_params, breakdown = calculate_parameters(
                    regime=current_regime,
                    current_params=current_params,
                    volatility_multiplier=vol_mult,
                )
                proposed_regime = breakdown.get("regime", current_regime)

                # symbol_price is fetched per-bot from Binance spot. Best-
                # effort: a fetch failure logs and stores None — the row
                # still gets written, replay can fall back to klines for
                # that timestamp.
                symbol_price = _fetch_symbol_price(symbol)
                _handle_bot(
                    supabase=supabase,
                    notifier=notifier,
                    bot=bot,
                    risk=risk,
                    opp=opp,
                    current=current_params,
                    proposed=proposed_params,
                    proposed_regime=proposed_regime,
                    proposed_stop_buy_active=proposed_stop_buy_active,
                    volatility_multiplier=vol_mult,
                    btc_price=btc_price,
                    symbol_price=symbol_price,
                    dry_run=dry_run,
                    last_alert_ts=last_alert_ts,
                    last_proposed=last_proposed,
                    last_stop_buy_active=last_stop_buy_active,
                    last_write_ts_per_symbol=last_write_ts_per_symbol,
                    skips_since_write=skips_since_write,
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
    restart doesn't trigger a fresh Telegram wave (or a spurious write)
    for proposals that haven't actually changed.

    Returns a dict {symbol: {buy_pct, sell_pct, idle_reentry_hours,
    regime, stop_buy_active, cooldown_active}} — S102 extended the
    on-change comparison beyond the 3 numeric params, so the bootstrap
    must carry the full proposal identity.

    Symbols with no prior proposal are simply absent — first cycle after
    boot will write/alert as a 'first proposal' for them, which is correct.
    """
    out: dict[str, dict] = {}
    try:
        # Pull a window slightly wider than the heartbeat (4h) and pick
        # the most recent row per symbol. PostgREST doesn't expose
        # DISTINCT ON via the JS client; client-side is fine for 6 symbols.
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
        rows = (
            supabase.table("sherpa_proposals")
            .select("symbol, proposed_buy_pct, proposed_sell_pct, "
                    "proposed_idle_reentry_hours, proposed_regime, "
                    "proposed_stop_buy_active, cooldown_active, created_at")
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
                "regime": row.get("proposed_regime"),
                "stop_buy_active": row.get("proposed_stop_buy_active"),
                "cooldown_active": row.get("cooldown_active"),
            }
        logger.info(f"Bootstrapped last_proposed for {len(out)} symbols")
    except Exception as e:
        logger.warning(f"last_proposed bootstrap failed: {e}")
    return out


def _fetch_latest_slow_score(supabase) -> Optional[dict]:
    """Read the most recent score_type='slow' row from sentinel_scores.

    Brief 81a Block 2: Sherpa no longer reads fast-loop rows. The slow
    loop emits every 4h, so risk_score / opportunity_score / btc_price
    move at most every 4h — proposals stay stable between emissions.
    """
    res = (
        supabase.table("sentinel_scores")
        .select("*")
        .eq("score_type", "slow")
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


def _fetch_active_manual_bots(supabase) -> list[dict]:
    res = (
        supabase.table("bot_config")
        .select(
            "symbol, is_active, managed_by, buy_pct, sell_pct, "
            "idle_reentry_hours, stop_buy_drawdown_pct"
        )
        .eq("is_active", True)
        .eq("managed_by", "grid")
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
    current: dict,
    proposed: dict,
    proposed_regime: str,
    proposed_stop_buy_active: bool,
    volatility_multiplier: float,
    btc_price,
    symbol_price,
    dry_run: bool,
    last_alert_ts: dict,
    last_proposed: dict,
    last_stop_buy_active: dict,
    last_write_ts_per_symbol: dict,
    skips_since_write: dict,
) -> None:
    symbol = bot["symbol"]

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
    params_changed = (prev is None) or any(
        is_changed(prev.get(p), proposed[p]) for p in PROPOSED_PARAMS
    )
    # Brief S102: the on-change identity of a proposal covers regime and
    # the cooldown window too, compared as transitions (flips), so a
    # regime change that leaves the numerics identical (the ±30% cap can
    # saturate two regimes onto the same values) still gets recorded,
    # and the open/close of a Board-override window leaves exactly two
    # rows instead of 720/day. None-aware: a missing prev field (pre-S102
    # bootstrap row) never counts as a flip.
    regime_changed = prev is not None and prev.get("regime") not in (None, proposed_regime)
    cooldown_flipped = (
        prev is not None
        and prev.get("cooldown_active") is not None
        and bool(prev.get("cooldown_active")) != cooldown_active
    )
    last_proposed[symbol] = {
        **proposed,
        "regime": proposed_regime,
        "stop_buy_active": proposed_stop_buy_active,
        "cooldown_active": cooldown_active,
    }

    prev_stop_buy = last_stop_buy_active.get(symbol)
    stop_buy_flipped = (prev_stop_buy is None and proposed_stop_buy_active) \
        or (prev_stop_buy is not None and prev_stop_buy != proposed_stop_buy_active)
    last_stop_buy_active[symbol] = proposed_stop_buy_active

    if dry_run:
        # Write to sherpa_proposals only when the proposal identity moved
        # since the previous cycle. No-op cycles are pure noise for replay
        # analysis. History of this gate:
        # - Brief 79c S79.1 (2026-05-18): guard switched from
        #   `would_have_changed` (proposed != current bot_config — in
        #   DRY_RUN current never moves, so it was true cronicamente) to
        #   proposal-vs-previous-cycle.
        # - Brief S102 (2026-06-11): `proposed_stop_buy_active` and
        #   `cooldown_active` were level-based passes ("write while
        #   true"), which bypassed the filter on EVERY tick during the
        #   persistent extreme_fear regime from May 29 (~2,100 rows/day,
        #   stop_buy true on 100% of them). Now both are flip-based:
        #   write the transition, skip the steady state. The regime is
        #   part of the comparison too. Expected stable-market volume:
        #   heartbeat only, 3 coins × 6/day = 18 rows/day.
        now_ts = time.time()
        heartbeat_due = (
            now_ts - last_write_ts_per_symbol.get(symbol, 0.0)
        ) >= SHERPA_HEARTBEAT_S
        change_due = params_changed or regime_changed or stop_buy_flipped or cooldown_flipped
        if change_due or heartbeat_due:
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
            last_write_ts_per_symbol[symbol] = now_ts
            n_skips = skips_since_write.pop(symbol, 0)
            if change_due:
                reasons = [r for r, flag in (
                    ("params", params_changed),
                    ("regime", regime_changed),
                    ("stop_buy_flip", stop_buy_flipped),
                    ("cooldown_flip", cooldown_flipped),
                ) if flag]
                logger.info(
                    "Sherpa proposal written for %s: %s", symbol, "+".join(reasons)
                )
            else:
                # S102 decision (Max 2026-06-11): the per-skip console
                # line the brief asked for would be ~2,000 lines/day;
                # the count inside the heartbeat carries the same
                # information at 18 lines/day.
                logger.info(
                    "Sherpa heartbeat %s: proposal unchanged (%d skips since last write)",
                    symbol, n_skips,
                )
        else:
            skips_since_write[symbol] = skips_since_write.get(symbol, 0) + 1
            logger.debug("sherpa write skipped for %s: no change", symbol)
        # Alert gate: would_have_changed is the precondition (no point
        # telling Max "I'd adjust" when proposed == current), AND the
        # numeric proposal must have moved since last cycle (regime/
        # cooldown flips with identical numbers would make a confusing
        # "0.65→0.65" message). Stop-buy flip is its own alert reason —
        # even if params didn't move, the lamp flipping is news.
        if (would_have_changed and params_changed) or stop_buy_flipped:
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
                    "regime": proposed_regime,
                    "volatility_multiplier": volatility_multiplier,
                },
            )
    if (would_have_changed and params_changed
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
    if not TELEGRAM_ENABLED:
        return  # Brief 70b: silenzioso al riavvio post-DRY_RUN
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
    if not TELEGRAM_ENABLED:
        return  # Brief 70b: silenzioso al riavvio post-DRY_RUN
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
    if not TELEGRAM_ENABLED:
        return  # Brief 70b: silenzioso al riavvio post-DRY_RUN
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
