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
from utils.telegram_notifier import SyncTelegramNotifier

logger = logging.getLogger("bagholderai.orchestrator")

POLL_INTERVAL = 30          # seconds between bot_config reconciliations
MAX_RESTART_ATTEMPTS = 5    # consecutive crash restarts before giving up on a symbol
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
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("=" * 50)
    logger.info("BagHolderAI Orchestrator starting...")
    logger.info("=" * 50)

    first_run = True
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

            should_run = {
                sym for sym, cfg in desired.items()
                if cfg.get("is_active") and not cfg.get("pending_liquidation")
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
                if not first_run:
                    try:
                        notifier.send_message(
                            f"🆕 <b>{sym} grid bot started</b> ({source})"
                        )
                    except Exception:
                        pass

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
                first_run = False

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            shutdown_handler(signal.SIGINT, None)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            try:
                notifier.send_message(
                    f"🚨 <b>Orchestrator error</b>\n<code>{str(e)[:300]}</code>"
                )
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_orchestrator()
