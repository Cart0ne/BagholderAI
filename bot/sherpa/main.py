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

from config.settings import HardcodedRules

from bot.sentinel.inputs.binance_btc import fetch_price, to_binance_symbol
from bot.sherpa import board_debounce
from bot.sherpa.board_parameter_rules import (
    BOARD_PARAM_KEYS,
    board_values_for,
    calculate_board_parameters,
    classify_tier,
)
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
            # Brief S103a: debounce state for the 4 protective Board params.
            # Only read in LIVE (the dry_run path logs the instantaneous
            # lookup and never touches the state table).
            board_states = {} if dry_run else _fetch_board_states(supabase)
            now_dt = datetime.now(timezone.utc)

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

                # Brief S103a: resolve the 4 protective Board params on the
                # discrete (regime x volatility-tier) table. dry_run logs the
                # instantaneous lookup; LIVE runs the 24h debounce (so a coin
                # hugging a tier/regime boundary doesn't rewrite its safety
                # params on every wiggle) and writes the survivors.
                board_current = {
                    "stop_buy_drawdown_pct": _f(bot.get("stop_buy_drawdown_pct")),
                    "stop_buy_unlock_hours": _f(bot.get("stop_buy_unlock_hours")),
                    "dead_zone_hours": _f(bot.get("dead_zone_hours")),
                    "profit_target_pct": _f(bot.get("profit_target_pct")),
                }
                if dry_run:
                    board_target, board_tier = calculate_board_parameters(
                        current_regime, vol_mult
                    )
                    board_cooldown_locked: list[str] = []
                else:
                    decision = board_debounce.decide(
                        board_states.get(symbol),
                        current_regime,
                        classify_tier(vol_mult),
                        now_dt,
                        HardcodedRules.BOARD_DEBOUNCE_HOURS,
                    )
                    if decision.state_changed:
                        _upsert_board_state(supabase, symbol, decision.new_state)
                    board_target = board_values_for(
                        decision.effective_regime, decision.effective_tier
                    )
                    board_tier = decision.effective_tier
                    board_cooldown_locked = parameters_in_cooldown(
                        supabase, symbol, BOARD_PARAM_KEYS
                    )

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
                    board_current=board_current,
                    board_target=board_target,
                    board_tier=board_tier,
                    board_cooldown_locked=board_cooldown_locked,
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
            "idle_reentry_hours, stop_buy_drawdown_pct, "
            "stop_buy_unlock_hours, dead_zone_hours, profit_target_pct, venue"
        )
        .eq("is_active", True)
        .eq("managed_by", "grid")
        .execute()
    )
    rows = res.data or []
    # S122 (sherpa-on-kraken) — Sherpa ora GUIDA anche le righe venue='kraken'
    # (decisione Board Opzione B, 2026-07-21). Il filtro hands-off della Fase 1
    # (S118) è RIMOSSO perché entrambe le sue ragioni sono risolte:
    #   (a) il floor NON si azzera più: il fee-fix S121 (ed1933d) fa sì che
    #       profit_target_pct=0 significhi "floor al break-even net-of-fee",
    #       non "floor spento" (il trigger fee-buffered protegge ogni vendita);
    #   (b) la volatilità NON è più rotta su /USD: to_binance_symbol() mappa
    #       'BTC/USD'→'BTCUSDT' (proxy Binance, decisione S112/CEO S122) →
    #       _fetch_stdev restituisce un valore reale, non 0.0/fallback.
    # `venue` resta nel select solo per telemetria/eventuale uso futuro; Sherpa
    # non ne ha bisogno per la propria matematica (il fee-buffer vive nel grid).
    return rows


def _fetch_board_states(supabase) -> dict[str, dict]:
    """Read all sherpa_board_state rows once per cycle, keyed by symbol.
    Brief S103a: holds the debounce state (effective + candidate (regime,
    tier) + candidate_since) for the 4 protective params. Empty on any
    failure — decide() then treats every coin as a first classification."""
    try:
        res = supabase.table("sherpa_board_state").select("*").execute()
        return {r["symbol"]: r for r in (res.data or [])}
    except Exception as e:
        logger.warning(f"sherpa_board_state fetch failed: {e}")
        return {}


def _upsert_board_state(supabase, symbol: str, new_state: dict) -> None:
    try:
        supabase.table("sherpa_board_state").upsert(
            {
                "symbol": symbol,
                "effective_regime": new_state.get("effective_regime"),
                "effective_tier": new_state.get("effective_tier"),
                "candidate_regime": new_state.get("candidate_regime"),
                "candidate_tier": new_state.get("candidate_tier"),
                "candidate_since": new_state.get("candidate_since"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="symbol",
        ).execute()
    except Exception as e:
        logger.error(f"sherpa_board_state upsert failed for {symbol}: {e}")


def _fetch_symbol_price(symbol: str) -> Optional[float]:
    """Convert 'BONK/USDT' -> 'BONKUSDT' and fetch the spot price. Kraken
    '/USD' rows map to their '/USDT' twin (S122, shared normalizer). Returns
    None on any error (network, unknown symbol). Sherpa never blocks on a
    missing price.
    """
    binance_symbol = to_binance_symbol(symbol)
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
    board_current: Optional[dict] = None,
    board_target: Optional[dict] = None,
    board_tier: Optional[str] = None,
    board_cooldown_locked: Optional[list] = None,
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

    # S102b: heartbeat is computed for BOTH modes. last_write_ts_per_symbol
    # tracks the last sherpa_proposals row for this symbol (in either mode),
    # so heartbeat_due == "the proposals table has been silent for this
    # symbol for SHERPA_HEARTBEAT_S". DRY_RUN joins it to the change gate;
    # LIVE uses it for a periodic liveness row (see the LIVE branch).
    now_ts = time.time()
    heartbeat_due = (
        now_ts - last_write_ts_per_symbol.get(symbol, 0.0)
    ) >= SHERPA_HEARTBEAT_S

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
                board_current=board_current,
                board_target=board_target,
                volatility_tier=board_tier,
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

    # Brief S103a: write the 4 protective Board params (debounced upstream in
    # the loop, so board_target is the *effective* target — a tier/regime that
    # just flipped is still being held). Same write path as the 3 strategy
    # params: skip a param locked by a Board override (cooldown), write the
    # rest where they differ from bot_config. No Telegram alert for these
    # (config_changes_log + SHERPA_ADJUSTMENT carry the audit; the channel
    # stays for trade events — memory feedback_no_telegram_alerts).
    if board_target is not None:
        board_locked = set(board_cooldown_locked or [])
        for parameter in BOARD_PARAM_KEYS:
            new_value = board_target.get(parameter)
            old_value = (board_current or {}).get(parameter)
            if new_value is None or not is_changed(old_value, new_value):
                continue
            if parameter in board_locked:
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
                continue
            ok = write_parameter(
                supabase,
                symbol=symbol,
                parameter=parameter,
                new_value=new_value,
                old_value=old_value,
            )
            if ok:
                log_event(
                    severity="info",
                    category="config",
                    event="SHERPA_ADJUSTMENT",
                    message=f"{symbol}.{parameter} {old_value} -> {new_value}",
                    symbol=symbol,
                    details={
                        "parameter": parameter,
                        "old": old_value,
                        "new": new_value,
                        "regime": proposed_regime,
                        "volatility_tier": board_tier,
                        "board_param": True,
                    },
                )

    # S102b liveness heartbeat (LIVE mode). In LIVE Sherpa writes parameters
    # straight to bot_config (audit trail in config_changes_log) and never
    # touches sherpa_proposals — so in a stable regime that table goes silent
    # and we can't distinguish "alive, nothing to change" from "stuck", and
    # the admin STOP BUY lamp (which reads sherpa_proposals) freezes on a
    # weeks-old value. Write one row per symbol per SHERPA_HEARTBEAT_S
    # carrying the current regime / stop_buy. This is the heartbeat ONLY —
    # real parameter changes stay in config_changes_log (decision D2: no
    # full shadow-write of every proposal). First tick post-restart always
    # fires (last_write_ts default 0.0), confirming Sherpa is up.
    if heartbeat_due:
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
            board_current=board_current,
            board_target=board_target,
            volatility_tier=board_tier,
        )
        last_write_ts_per_symbol[symbol] = now_ts
        logger.info(
            "Sherpa LIVE heartbeat %s: alive, regime=%s, stop_buy=%s, tier=%s",
            symbol, proposed_regime, proposed_stop_buy_active, board_tier,
        )


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
    board_current: Optional[dict] = None,
    board_target: Optional[dict] = None,
    volatility_tier: Optional[str] = None,
) -> None:
    payload = {
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
    }
    # Brief S103a: the 4 protective Board params on the same row (the admin
    # "Last proposals" table renders them as a second row under the strategy
    # params). current_stop_buy_drawdown_pct is already set above; board_current
    # fills the other three current_* columns.
    if board_target is not None:
        payload.update({
            "proposed_stop_buy_dd": board_target.get("stop_buy_drawdown_pct"),
            "proposed_stop_buy_unlock_h": board_target.get("stop_buy_unlock_hours"),
            "proposed_dead_zone_h": board_target.get("dead_zone_hours"),
            "proposed_profit_target": board_target.get("profit_target_pct"),
        })
    if board_current is not None:
        payload.update({
            "current_stop_buy_unlock_h": board_current.get("stop_buy_unlock_hours"),
            "current_dead_zone_h": board_current.get("dead_zone_hours"),
            "current_profit_target": board_current.get("profit_target_pct"),
        })
    if volatility_tier is not None:
        payload["volatility_tier"] = volatility_tier
    try:
        supabase.table("sherpa_proposals").insert(payload).execute()
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
