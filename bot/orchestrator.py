"""
BagHolderAI - Orchestrator
Single entry point that manages all grid bots and the trend follower.

Responsibilities:
  - Spawn a grid_runner subprocess for every active bot_config symbol
  - Spawn the trend_follower subprocess when trend_config.trend_follower_enabled
  - Restart crashed subprocesses (up to MAX_RESTART_ATTEMPTS)
  - Pick up new symbols written to bot_config by the Trend Follower
  - Let subprocesses self-shutdown on is_active=false / pending_liquidation

Usage:
    python3.13 -m bot.orchestrator
"""

import subprocess
import time
import signal
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

from db.client import get_client
from db.event_logger import log_event
from utils.telegram_notifier import SyncTelegramNotifier
from bot.health_check import run_health_check
from bot.db_maintenance import maybe_run_maintenance

logger = logging.getLogger("bagholderai.orchestrator")

POLL_INTERVAL = 30          # seconds between bot_config reconciliations
MAX_RESTART_ATTEMPTS = 5    # consecutive crash restarts before giving up on a symbol
HEALTH_CHECK_INTERVAL = 30 * 60  # 57a: periodic FIFO/holdings/cash integrity check
# 44a: cap Telegram spam from the main-loop exception handler. Network
# blackouts (httpx ConnectTimeout, etc.) can raise the same exception
# every POLL_INTERVAL for tens of minutes; without a cooldown that
# produces 20-25 identical Telegram alerts per incident. Logging is
# not rate-limited — the local log file keeps every occurrence.
ORCHESTRATOR_ALERT_COOLDOWN = 15 * 60  # seconds
LOG_DIR = Path("logs")


class ProcessInfo:
    """Tracks a managed grid_runner subprocess."""

    def __init__(self, symbol: str, process: subprocess.Popen, managed_by: str):
        self.symbol = symbol
        self.process = process
        self.managed_by = managed_by
        self.restart_count = 0
        self.started_at = datetime.now(timezone.utc)
        self.gave_up = False


def _spawn_grid_bot(symbol: str) -> subprocess.Popen:
    """Spawn a grid bot subprocess for the given symbol. Stdout/stderr tee to a log file."""
    log_file = LOG_DIR / f"grid_{symbol.replace('/', '_')}.log"
    f = open(log_file, "a")
    return subprocess.Popen(
        [sys.executable, "-m", "bot.grid_runner", "--symbol", symbol],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=str(Path.cwd()),
    )


def _spawn_trend_follower() -> subprocess.Popen:
    """Spawn the trend follower subprocess."""
    log_file = LOG_DIR / "trend_follower.log"
    f = open(log_file, "a")
    return subprocess.Popen(
        [sys.executable, "-m", "bot.trend_follower.trend_follower"],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=str(Path.cwd()),
    )


def _reconcile_orphan_tf_bots(supabase, notifier) -> None:
    """45: Rescue TF bots whose bot_config says is_active=False but whose
    DB-replayed holdings are non-zero. Typical cause: a liquidation sell
    was executed by the bot but the trades INSERT timed out on Supabase
    during a network blackout, leaving the DB with buys > sells and no
    way for the bot to re-enter the liquidation path on its own.

    Strategy: flip is_active=True + pending_liquidation=True on each
    orphan row. The standard poll loop will spawn the grid_runner at
    the next tick; its init_percentage_state_from_db will rebuild the
    FIFO queue, see pending_liquidation, run the force-liquidate branch,
    and close the cycle normally.

    Skips manual bots (managed_by != 'trend_follower') — those are under
    user control, auto-rianimation would be invasive. No price check
    here; grid_bot's dust-handling will close sub-min_notional residuals
    on the first tick after spawn.
    """
    try:
        rows = supabase.table("bot_config").select(
            "symbol, is_active, managed_by, pending_liquidation"
        ).eq("managed_by", "trend_follower").eq("is_active", False).execute()
    except Exception as e:
        logger.warning(f"[RECONCILER] Could not query bot_config: {e}")
        return

    # Minimum notional estimate: below this, an orphan is sub-Binance-
    # min_notional and would just spin (spawn → dust removal → shut down
    # → reconciler re-flips at next boot). Skip those to break the loop.
    # $5 is the typical Binance MIN_NOTIONAL across pairs.
    MIN_ORPHAN_USD = 5.0

    orphans_found = []
    orphans_skipped_dust = []
    for row in rows.data or []:
        symbol = row["symbol"]
        try:
            trades_res = supabase.table("trades").select(
                "side, amount, price, created_at"
            ).eq("symbol", symbol).eq("config_version", "v3").order(
                "created_at", desc=True
            ).execute()
        except Exception as e:
            logger.warning(f"[RECONCILER] Could not query trades for {symbol}: {e}")
            continue

        bought = 0.0
        sold = 0.0
        last_price = 0.0
        for t in trades_res.data or []:
            amt = float(t.get("amount") or 0)
            if last_price == 0 and t.get("price"):
                last_price = float(t["price"])  # most-recent price (desc order)
            if t.get("side") == "buy":
                bought += amt
            elif t.get("side") == "sell":
                sold += amt
        holdings = bought - sold
        # Guard against tiny float imprecision (10^-8 residuals from
        # float sums) — anything below 1e-6 is not a real position.
        if holdings <= 1e-6:
            continue

        # Estimated notional using the last traded price (stale but adequate
        # for deciding "is this dust or sellable"). A full Binance ticker
        # fetch would be more accurate but the reconciler runs offline-
        # friendly at boot; stale price is safer than skipping entirely.
        est_usd = holdings * last_price if last_price > 0 else 0.0
        if est_usd < MIN_ORPHAN_USD:
            logger.info(
                f"[RECONCILER] Sub-min_notional residual: {symbol} "
                f"holdings={holdings:.6f} × ${last_price} ≈ ${est_usd:.2f} "
                f"— economic dust, skipping (stays is_active=False)."
            )
            orphans_skipped_dust.append((symbol, holdings, est_usd))
            continue

        logger.warning(
            f"[RECONCILER] Orphan detected: {symbol} holdings={holdings:.6f} "
            f"(~${est_usd:.2f}). Flipping to is_active=True + "
            f"pending_liquidation=True."
        )
        try:
            supabase.table("bot_config").update({
                "is_active": True,
                "pending_liquidation": True,
            }).eq("symbol", symbol).execute()
            orphans_found.append((symbol, holdings, est_usd))
        except Exception as e:
            logger.error(f"[RECONCILER] Failed to flip {symbol}: {e}")

    if orphans_found:
        lines = "\n".join(
            f"  {sym}: {qty:.6f} units (~${usd:.2f})"
            for sym, qty, usd in orphans_found
        )
        try:
            notifier.send_message(
                f"🔧 <b>Orphan reconciler</b>\n"
                f"Detected {len(orphans_found)} TF bot(s) with residual "
                f"holdings after deallocate. Re-activating for liquidation:\n"
                f"{lines}"
            )
        except Exception as e:
            logger.warning(f"[RECONCILER] Telegram alert failed: {e}")
    if not orphans_found and not orphans_skipped_dust:
        logger.info("[RECONCILER] No TF orphans detected.")
    elif not orphans_found:
        logger.info(
            f"[RECONCILER] {len(orphans_skipped_dust)} sub-min_notional "
            f"residual(s) skipped, no actionable orphan."
        )


def run_orchestrator():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    LOG_DIR.mkdir(exist_ok=True)

    supabase = get_client()
    notifier = SyncTelegramNotifier()

    grid_processes: dict[str, ProcessInfo] = {}
    tf_process: subprocess.Popen | None = None

    shutting_down = {"v": False}

    def shutdown_handler(signum, frame):
        if shutting_down["v"]:
            logger.info("Force exit.")
            sys.exit(1)
        shutting_down["v"] = True
        logger.info("Shutting down all processes...")
        try:
            notifier.send_message("🛑 <b>Orchestrator shutting down</b> — stopping all bots")
        except Exception:
            pass

        # Send SIGINT (not SIGTERM) so each subprocess hits its
        # KeyboardInterrupt handler and gets to send a farewell Telegram.
        # External kill paths are still covered by the SIGTERM handler in
        # grid_runner / trend_follower (identical behavior, belt + suspenders).
        for sym, info in grid_processes.items():
            if info.process.poll() is None:
                logger.info(f"Stopping {sym}...")
                info.process.send_signal(signal.SIGINT)
        if tf_process is not None and tf_process.poll() is None:
            logger.info("Stopping Trend Follower...")
            tf_process.send_signal(signal.SIGINT)

        for sym, info in grid_processes.items():
            try:
                info.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                info.process.kill()
        if tf_process is not None:
            try:
                tf_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                tf_process.kill()

        logger.info("All processes stopped.")
        # 43a: structured event. Use critical severity if the shutdown was
        # triggered by an unexpected signal; SIGINT/SIGTERM from the user
        # is the normal path so severity is info.
        log_event(
            severity="info",
            category="lifecycle",
            event="orchestrator_stopped",
            message=f"Orchestrator shutdown complete (signal={signum})",
            details={"signal": int(signum) if signum else None},
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("=" * 50)
    logger.info("BagHolderAI Orchestrator starting...")
    logger.info("=" * 50)

    # 45: orphan-lot reconciler. Run once at boot to recover any TF bot
    # that was deallocated while still holding sellable coin (typically
    # because a liquidation sell's INSERT timed out on Supabase). Flips
    # is_active=True + pending_liquidation=True so the standard spawn +
    # BEARISH-EXIT flow liquidates them at the next poll iteration. No
    # price-check here — the grid_bot dust-handling logic will close
    # out sub-min_notional residuals cleanly at first tick.
    try:
        _reconcile_orphan_tf_bots(supabase, notifier)
    except Exception as e:
        logger.error(f"Orphan reconciler failed at boot: {e}", exc_info=True)
        # Not fatal — carry on; the orphans just stay parked until a
        # future boot retries.

    # 57a: integrity health check at boot. Catches DB-level discrepancies
    # (FIFO P&L drift, negative holdings, orphan lots, cash divergence)
    # before the bots start trading. Telegram alert is emitted if any
    # check fails; the run never raises (errors degrade to per-check
    # ERROR statuses inside the report).
    try:
        report = run_health_check(client=supabase)
        if report.get("all_ok"):
            try:
                notifier.send_message(
                    f"✅ <b>Health check passed at boot</b>\n"
                    f"{report.get('n_ok', 0)} checks OK"
                )
            except Exception:
                pass
        else:
            logger.warning(
                f"Boot health check FAILED: "
                f"{report.get('n_fail', 0)} fail, {report.get('n_error', 0)} error"
            )
    except Exception as e:
        logger.error(f"Health check at boot crashed: {e}", exc_info=True)

    first_run = True
    # 44a: timestamp of the last "🚨 Orchestrator error" Telegram. 0 means
    # "never sent" so the first error in a run still alerts immediately.
    _last_error_alert_ts = 0.0
    # 57a: timestamp of the last periodic health check.
    _last_health_check_ts = time.time()
    while not shutting_down["v"]:
        try:
            # 1. Desired state from bot_config
            result = supabase.table("bot_config").select(
                "symbol, is_active, managed_by, pending_liquidation"
            ).execute()
            desired = {r["symbol"]: r for r in (result.data or [])}

            # 2. Trend follower enable flag
            try:
                tf_result = supabase.table("trend_config").select(
                    "trend_follower_enabled"
                ).limit(1).execute()
                tf_enabled = bool(tf_result.data[0]["trend_follower_enabled"]) if tf_result.data else False
            except Exception as e:
                logger.warning(f"Could not read trend_config: {e}")
                tf_enabled = False

            # A row is "should run" when is_active=True. The historical
            # contract also required pending_liquidation=False, under the
            # assumption that pending_liquidation was only ever set on an
            # already-running bot (which would self-terminate after force
            # liquidation). The 45 orphan reconciler breaks that assumption:
            # it flips a non-running bot to is_active=True + pending_liquidation=True
            # precisely so the orchestrator spawns it, lets the standard
            # force-liquidate branch close out the residual holdings, and
            # the grid_runner writes is_active=False on its way out. So we
            # spawn on is_active=True regardless of pending_liquidation.
            should_run = {
                sym for sym, cfg in desired.items()
                if cfg.get("is_active")
            }

            # 3. Reconcile grid bots: detect crashes / clean exits first
            for sym in list(grid_processes.keys()):
                info = grid_processes[sym]
                if info.process.poll() is None:
                    continue  # still alive

                exit_code = info.process.returncode
                logger.info(f"[{sym}] Grid bot exited with code {exit_code}")

                if sym in should_run and not info.gave_up:
                    info.restart_count += 1
                    if info.restart_count > MAX_RESTART_ATTEMPTS:
                        logger.error(f"[{sym}] Max restarts reached ({MAX_RESTART_ATTEMPTS}). Giving up.")
                        info.gave_up = True
                        try:
                            notifier.send_message(
                                f"🚨 <b>{sym} grid bot crashed {MAX_RESTART_ATTEMPTS} times</b>\n"
                                f"Giving up. Manual intervention needed."
                            )
                        except Exception:
                            pass
                        continue

                    proc = _spawn_grid_bot(sym)
                    info.process = proc
                    info.started_at = datetime.now(timezone.utc)
                    logger.warning(
                        f"[{sym}] Restarting (attempt {info.restart_count}/{MAX_RESTART_ATTEMPTS})"
                    )
                    try:
                        notifier.send_message(
                            f"🔄 <b>{sym} grid bot restarted</b> "
                            f"(attempt {info.restart_count}/{MAX_RESTART_ATTEMPTS})"
                        )
                    except Exception:
                        pass
                else:
                    # Clean exit (is_active=false or liquidated) — drop tracking
                    del grid_processes[sym]

            # 4. Start symbols wanted but not tracked
            for sym in should_run:
                if sym in grid_processes:
                    continue
                managed_by = desired[sym].get("managed_by") or "manual"
                proc = _spawn_grid_bot(sym)
                grid_processes[sym] = ProcessInfo(sym, proc, managed_by)
                source = "TF" if managed_by == "trend_follower" else "manual"
                logger.info(f"[{sym}] Grid bot spawned (pid={proc.pid}, {source})")
                # Per-bot spawn notification suppressed — the orchestrator-level
                # summary message is enough; new TF allocations still surface via
                # the scan-report Telegram sent by the Trend Follower itself.

            # 5. Reconcile Trend Follower
            if tf_enabled:
                if tf_process is None:
                    tf_process = _spawn_trend_follower()
                    logger.info(f"Trend Follower spawned (pid={tf_process.pid})")
                elif tf_process.poll() is not None:
                    logger.warning("Trend Follower crashed — restarting")
                    try:
                        notifier.send_message("🔄 <b>Trend Follower restarted</b> (crashed)")
                    except Exception:
                        pass
                    tf_process = _spawn_trend_follower()
                    logger.info(f"Trend Follower respawned (pid={tf_process.pid})")
            else:
                if tf_process is not None:
                    if tf_process.poll() is None:
                        logger.info("Trend Follower disabled — stopping")
                        tf_process.terminate()
                        try:
                            notifier.send_message("🛑 <b>Trend Follower stopped</b> (disabled)")
                        except Exception:
                            pass
                    tf_process = None

            # 6. First-run summary
            if first_run:
                grid_count = len(grid_processes)
                tf_status = "on" if tf_enabled else "off"
                symbols_list = ", ".join(sorted(grid_processes.keys())) or "(none)"
                try:
                    notifier.send_message(
                        f"🚀 <b>Orchestrator started</b>\n"
                        f"Grid bots: {grid_count} ({symbols_list})\n"
                        f"Trend Follower: {tf_status}\n"
                        f"Poll interval: {POLL_INTERVAL}s"
                    )
                except Exception:
                    pass
                # 43a: structured event for queryable history.
                log_event(
                    severity="info",
                    category="lifecycle",
                    event="orchestrator_started",
                    message=f"Orchestrator started with {grid_count} grid bot(s), TF {tf_status}",
                    details={
                        "grid_count": grid_count,
                        "symbols": sorted(grid_processes.keys()),
                        "tf_enabled": tf_enabled,
                        "poll_interval_s": POLL_INTERVAL,
                    },
                )
                first_run = False

            # 57a: periodic integrity check. Fires every HEALTH_CHECK_INTERVAL
            # regardless of poll cadence — wraps in try/except so a failed
            # check (DB hiccup, etc.) cannot stop the orchestrator main loop.
            now_ts = time.time()
            if (now_ts - _last_health_check_ts) >= HEALTH_CHECK_INTERVAL:
                _last_health_check_ts = now_ts
                try:
                    run_health_check(client=supabase)
                except Exception as e:
                    logger.error(f"Periodic health check crashed: {e}", exc_info=True)

            # 59b: daily DB retention cleanup. The maybe_ wrapper is a no-op
            # except at MAINTENANCE_HOUR_UTC, and only runs once per UTC day
            # — calling it every poll is fine and cheap. Wrapped in try so
            # a transient Supabase failure cannot take the orchestrator down.
            try:
                maybe_run_maintenance(supabase, notifier)
            except Exception as e:
                logger.error(f"DB maintenance crashed: {e}", exc_info=True)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            shutdown_handler(signal.SIGINT, None)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            # 44a: only send a Telegram if enough time has passed since the
            # previous one. A network blackout that raises the same exception
            # every POLL_INTERVAL used to fire ~25 identical messages per
            # incident; now it fires at most one every ORCHESTRATOR_ALERT_COOLDOWN.
            now_ts = time.time()
            if (now_ts - _last_error_alert_ts) >= ORCHESTRATOR_ALERT_COOLDOWN:
                try:
                    notifier.send_message(
                        f"🚨 <b>Orchestrator error</b>\n<code>{str(e)[:300]}</code>"
                    )
                    _last_error_alert_ts = now_ts
                except Exception:
                    pass
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_orchestrator()
