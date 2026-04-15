# INTERN BRIEF — Session 35b: Orchestrator

**Date:** April 14, 2026
**Priority:** CRITICAL — TF autonomy depends on this
**Prerequisite:** Brief 35a (tiered scanning) should be deployed first, but this brief can be implemented independently

---

## Context

Today every grid bot is launched manually from the terminal:
```bash
python3.13 -m bot.grid_runner --symbol BTC/USDT
python3.13 -m bot.grid_runner --symbol SOL/USDT
python3.13 -m bot.grid_runner --symbol BONK/USDT
python3.13 -m bot.trend_follower.trend_follower
```

This means:
- If the Mac Mini restarts, everything is dead until Max re-launches
- If the Trend Follower writes a new coin to `bot_config`, nobody starts a grid bot for it
- If a grid bot crashes, nobody restarts it

The orchestrator fixes all three: **one process to rule them all**.

---

## Architecture

```
bot/orchestrator.py          ← NEW: this brief
├── reads bot_config         ← which symbols need grid bots
├── reads trend_config       ← is trend_follower enabled
├── spawns grid_runner       ← one subprocess per active symbol
├── spawns trend_follower    ← one subprocess
├── monitors all processes   ← restart on crash, stop on deactivation
└── sends Telegram alerts    ← key lifecycle events
```

---

## 1. Orchestrator (`bot/orchestrator.py`)

### Main loop

```python
"""
BagHolderAI - Orchestrator
Single entry point that manages all grid bots and the trend follower.

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

POLL_INTERVAL = 30          # seconds between bot_config checks
MAX_RESTART_ATTEMPTS = 5    # max consecutive restarts before giving up on a symbol
RESTART_COOLDOWN = 60       # seconds to wait before restarting a crashed process
LOG_DIR = Path("logs")


class ProcessInfo:
    """Tracks a managed subprocess."""
    def __init__(self, symbol: str, process: subprocess.Popen, managed_by: str):
        self.symbol = symbol
        self.process = process
        self.managed_by = managed_by
        self.restart_count = 0
        self.started_at = datetime.now(timezone.utc)
        self.last_crash = None


def run_orchestrator():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Create log directory
    LOG_DIR.mkdir(exist_ok=True)
    
    supabase = get_client()
    notifier = SyncTelegramNotifier()
    
    # Track running processes: symbol -> ProcessInfo
    grid_processes: dict[str, ProcessInfo] = {}
    tf_process: subprocess.Popen | None = None
    
    # Graceful shutdown on Ctrl+C
    shutting_down = False
    
    def shutdown_handler(signum, frame):
        nonlocal shutting_down
        if shutting_down:
            logger.info("Force exit.")
            sys.exit(1)
        shutting_down = True
        logger.info("Shutting down all processes...")
        notifier.send_message("🛑 <b>Orchestrator shutting down</b> — stopping all bots")
        
        # Terminate all grid bots
        for sym, info in grid_processes.items():
            logger.info(f"Stopping {sym}...")
            info.process.terminate()
        
        # Terminate trend follower
        if tf_process and tf_process.poll() is None:
            logger.info("Stopping Trend Follower...")
            tf_process.terminate()
        
        # Wait for all to exit (max 10s each)
        for sym, info in grid_processes.items():
            try:
                info.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                info.process.kill()
        
        if tf_process:
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
    
    # === MAIN LOOP ===
    first_run = True
    while not shutting_down:
        try:
            # 1. Read desired state from bot_config
            result = supabase.table("bot_config").select(
                "symbol, is_active, managed_by, pending_liquidation"
            ).execute()
            desired = {r["symbol"]: r for r in result.data} if result.data else {}
            
            # 2. Read trend_config
            tf_result = supabase.table("trend_config").select(
                "trend_follower_enabled"
            ).limit(1).execute()
            tf_enabled = tf_result.data[0]["trend_follower_enabled"] if tf_result.data else False
            
            # 3. Reconcile grid bots
            
            # 3a. Find symbols that SHOULD be running
            should_run = {
                sym for sym, cfg in desired.items()
                if cfg.get("is_active") and not cfg.get("pending_liquidation")
            }
            
            # 3b. Find symbols currently running
            currently_running = set()
            for sym, info in list(grid_processes.items()):
                if info.process.poll() is None:
                    currently_running.add(sym)
                else:
                    # Process has exited
                    exit_code = info.process.returncode
                    logger.info(f"[{sym}] Grid bot exited with code {exit_code}")
                    del grid_processes[sym]
            
            # 3c. START new symbols
            for sym in should_run - currently_running:
                if sym in grid_processes:
                    # Was running but crashed — check restart limits
                    info = grid_processes[sym]
                    if info.restart_count >= MAX_RESTART_ATTEMPTS:
                        logger.error(f"[{sym}] Max restarts reached ({MAX_RESTART_ATTEMPTS}). Giving up.")
                        if first_run or info.restart_count == MAX_RESTART_ATTEMPTS:
                            notifier.send_message(
                                f"🚨 <b>{sym} grid bot crashed {MAX_RESTART_ATTEMPTS} times</b>\n"
                                f"Giving up. Manual intervention needed."
                            )
                        continue
                
                # Spawn new process
                managed_by = desired[sym].get("managed_by", "manual")
                proc = _spawn_grid_bot(sym)
                grid_processes[sym] = ProcessInfo(sym, proc, managed_by)
                
                emoji = "🟢" if first_run else "🔄" if sym in grid_processes else "🆕"
                source = "TF" if managed_by == "trend_follower" else "manual"
                logger.info(f"[{sym}] Grid bot spawned (pid={proc.pid}, {source})")
                
                if not first_run:
                    notifier.send_message(
                        f"{emoji} <b>{sym} grid bot started</b> ({source})"
                    )
            
            # 3d. STOP symbols that should NOT be running
            for sym in currently_running - should_run:
                info = grid_processes[sym]
                logger.info(f"[{sym}] No longer active — sending SIGTERM")
                info.process.terminate()
                notifier.send_message(f"🔴 <b>{sym} grid bot stopping</b>")
                # Don't delete from grid_processes yet — let the poll loop clean it up
            
            # 3e. Handle crashed processes (in should_run but not currently_running and not in grid_processes)
            for sym in should_run - currently_running:
                if sym not in grid_processes:
                    # New symbol, already handled in 3c
                    continue
                # Crashed process that was cleaned up above
                info = grid_processes.get(sym)
                if info:
                    info.restart_count += 1
                    info.last_crash = datetime.now(timezone.utc)
                    logger.warning(f"[{sym}] Restarting (attempt {info.restart_count}/{MAX_RESTART_ATTEMPTS})")
                    
                    proc = _spawn_grid_bot(sym)
                    info.process = proc
                    info.started_at = datetime.now(timezone.utc)
                    
                    notifier.send_message(
                        f"🔄 <b>{sym} grid bot restarted</b> "
                        f"(attempt {info.restart_count}/{MAX_RESTART_ATTEMPTS})"
                    )
            
            # 4. Reconcile Trend Follower
            if tf_enabled:
                if tf_process is None or tf_process.poll() is not None:
                    if tf_process and tf_process.poll() is not None:
                        logger.warning("Trend Follower crashed — restarting")
                        notifier.send_message("🔄 <b>Trend Follower restarted</b> (crashed)")
                    tf_process = _spawn_trend_follower()
                    logger.info(f"Trend Follower spawned (pid={tf_process.pid})")
            else:
                if tf_process and tf_process.poll() is None:
                    logger.info("Trend Follower disabled — stopping")
                    tf_process.terminate()
                    notifier.send_message("🛑 <b>Trend Follower stopped</b> (disabled)")
                    tf_process = None
            
            # 5. First-run summary on Telegram
            if first_run:
                grid_count = len(grid_processes)
                tf_status = "on" if tf_enabled else "off"
                symbols_list = ", ".join(sorted(grid_processes.keys()))
                notifier.send_message(
                    f"🚀 <b>Orchestrator started</b>\n"
                    f"Grid bots: {grid_count} ({symbols_list})\n"
                    f"Trend Follower: {tf_status}\n"
                    f"Poll interval: {POLL_INTERVAL}s"
                )
                first_run = False
            
            time.sleep(POLL_INTERVAL)
        
        except KeyboardInterrupt:
            shutdown_handler(None, None)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            try:
                notifier.send_message(f"🚨 <b>Orchestrator error</b>\n<code>{str(e)[:300]}</code>")
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)


def _spawn_grid_bot(symbol: str) -> subprocess.Popen:
    """Spawn a grid bot subprocess for the given symbol."""
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
    log_file = LOG_DIR / f"trend_follower.log"
    f = open(log_file, "a")
    
    return subprocess.Popen(
        [sys.executable, "-m", "bot.trend_follower.trend_follower"],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=str(Path.cwd()),
    )


if __name__ == "__main__":
    run_orchestrator()
```

**Important**: The `sys.executable` ensures we use the same Python that launched the orchestrator (python3.13), not whatever `python3` resolves to.

---

## 2. Grid bot changes (`bot/grid_runner.py`)

### 2a. Handle `pending_liquidation` flag

In the main loop, after syncing config and checking `is_active`, add a check for `pending_liquidation`. This goes RIGHT AFTER the existing `is_active` check:

```python
# Graceful shutdown if is_active=false in Supabase
if not bot.is_active:
    logger.info(f"[{cfg.symbol}] is_active=false — shutting down gracefully")
    notifier.send_message(f"🛑 <b>{cfg.symbol} grid bot stopped</b> (is_active=false)")
    break

# === NEW: forced liquidation ===
if getattr(bot, 'pending_liquidation', False):
    logger.info(f"[{cfg.symbol}] pending_liquidation=true — force-selling all positions")
    _force_liquidate(bot, exchange, trade_logger, notifier, cfg.symbol)
    # Mark as inactive in Supabase
    try:
        from db.client import get_client
        sb = get_client()
        sb.table("bot_config").update({
            "is_active": False,
            "pending_liquidation": False,
        }).eq("symbol", cfg.symbol).execute()
    except Exception as e:
        logger.error(f"[{cfg.symbol}] Failed to update bot_config after liquidation: {e}")
    break
```

### 2b. Sync `pending_liquidation` in `_sync_config_to_bot`

Add to the existing `_sync_config_to_bot` function:

```python
if "pending_liquidation" in sb_cfg:
    bot.pending_liquidation = bool(sb_cfg.get("pending_liquidation", False))
```

And add `pending_liquidation` to the list of fields fetched by `SupabaseConfigReader`. Find the `_CONFIG_FIELDS` list in `config/supabase_config.py` and add `"pending_liquidation"` to it.

### 2c. Force liquidation function

Add this function to `grid_runner.py`:

```python
def _force_liquidate(bot, exchange, trade_logger, notifier, symbol: str):
    """
    Force-sell ALL open positions at current market price.
    Used when Trend Follower rotates to a different coin.
    """
    holdings = bot.state.holdings if hasattr(bot.state, 'holdings') else 0
    
    if holdings <= 0:
        logger.info(f"[{symbol}] No holdings to liquidate")
        notifier.send_message(f"🔴 <b>{symbol} liquidation</b>: no holdings, clean exit")
        return
    
    try:
        price = fetch_price(exchange, symbol)
        
        # Calculate cost basis for PnL
        avg_buy = bot.state.avg_buy_price if hasattr(bot.state, 'avg_buy_price') else 0
        cost_basis = avg_buy * holdings
        proceeds = price * holdings
        realized_pnl = proceeds - cost_basis
        
        # Determine managed_by from bot_config
        managed_by = "manual"
        try:
            from db.client import get_client
            sb = get_client()
            cfg_result = sb.table("bot_config").select("managed_by").eq("symbol", symbol).execute()
            if cfg_result.data:
                managed_by = cfg_result.data[0].get("managed_by", "manual")
        except Exception:
            pass
        
        # Log the liquidation sell trade
        if trade_logger:
            trade_logger.log_trade({
                "symbol": symbol,
                "side": "sell",
                "amount": holdings,
                "price": price,
                "cost": proceeds,
                "fee": 0,
                "strategy": "A",
                "brain": "grid",
                "mode": "paper",
                "reason": "FORCED_LIQUIDATION (TF rotation)",
                "realized_pnl": realized_pnl,
                "config_version": "v3",
                "managed_by": managed_by,
            })
        
        pnl_emoji = "📈" if realized_pnl >= 0 else "📉"
        notifier.send_message(
            f"🔴 <b>{symbol} LIQUIDATED</b>\n"
            f"Sold {holdings:.6f} at ${price:.4f}\n"
            f"Proceeds: ${proceeds:.2f}\n"
            f"{pnl_emoji} PnL: ${realized_pnl:.2f}"
        )
        
        logger.info(
            f"[{symbol}] Liquidation complete: sold {holdings} at {price}, "
            f"PnL: ${realized_pnl:.2f}"
        )
        
    except Exception as e:
        logger.error(f"[{symbol}] Liquidation FAILED: {e}")
        notifier.send_message(
            f"🚨 <b>{symbol} LIQUIDATION FAILED</b>\n"
            f"<code>{str(e)[:300]}</code>\n"
            f"Manual intervention needed!"
        )
```

### 2d. Write `managed_by` on trades

In the grid bot's trade logging, the `managed_by` value needs to be included. The grid bot reads its config from `bot_config` which has `managed_by`. 

In `bot/grid_runner.py`, find where trades are logged (the `trade_logger.log_trade(...)` calls). The bot itself doesn't call `log_trade` directly — it goes through `GridBot.check_price_and_execute()` which calls `self.trade_logger.log_trade(...)` in `bot/strategies/grid_bot.py`.

**In `bot/strategies/grid_bot.py`**, find ALL `self.trade_logger.log_trade(...)` calls. Each one builds a dict with fields like `symbol`, `side`, `amount`, `price`, etc. Add `"managed_by"` to each:

```python
"managed_by": getattr(self, 'managed_by', 'manual'),
```

And set `self.managed_by` during config sync — add to `_sync_config_to_bot`:

```python
if "managed_by" in sb_cfg:
    bot.managed_by = sb_cfg.get("managed_by", "manual")
```

Also set it at bot initialization in `run_grid_bot`:

```python
bot.managed_by = sb_cfg.get("managed_by", "manual") if sb_cfg else "manual"
```

### 2e. Support unknown symbols (TF-created)

Currently `get_grid_config(symbol)` falls back to BTC config for unknown symbols. For TF-created symbols, ALL config comes from `bot_config` table.

The existing code in `run_grid_bot` already reads from Supabase and overrides the local config. This works — the fallback config provides sane defaults (check_interval, etc.) and Supabase overrides the trading params.

**BUT**: TF-created symbols won't have an entry in `GRID_INSTANCES`. The fallback to BTC config is fine for non-critical defaults (check_interval_seconds, buy_cooldown_seconds). The important fields (symbol, capital_allocation, buy_pct, sell_pct, grid_mode, capital_per_trade) all come from Supabase.

One change needed: in `run_grid_bot`, the `cfg.symbol` is set from `get_grid_config(symbol)`. But if the symbol is unknown, it returns BTC config — meaning `cfg.symbol` would be "BTC/USDT" instead of the requested symbol. Fix this:

```python
cfg = get_grid_config(symbol)
cfg.symbol = symbol  # Always use the requested symbol, even if config was a fallback
```

This line should go right after `cfg = get_grid_config(symbol)`, before anything else.

---

## 3. Supabase config reader changes (`config/supabase_config.py`)

Add `"pending_liquidation"` and `"managed_by"` to the list of fields fetched from `bot_config`.

Find `_CONFIG_FIELDS` (or the equivalent SELECT statement) and add both fields.

---

## 4. Log file management

The orchestrator writes logs to `logs/` directory. Each subprocess writes to its own file.

Create a `.gitignore` entry if not present:
```
logs/
```

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/orchestrator.py` | CREATE | Main orchestrator script |
| `bot/grid_runner.py` | MODIFY | Add `pending_liquidation` handling, `_force_liquidate`, symbol override |
| `bot/strategies/grid_bot.py` | MODIFY | Add `managed_by` to all `log_trade` calls |
| `config/supabase_config.py` | MODIFY | Add `pending_liquidation`, `managed_by` to fetched fields |
| `.gitignore` | MODIFY | Add `logs/` |

---

## Test

### Test 1: Basic orchestrator start
```bash
python3.13 -m bot.orchestrator
```
- [ ] Telegram receives: "🚀 Orchestrator started — Grid bots: 3 (BTC/USDT, BONK/USDT, SOL/USDT) — TF: on"
- [ ] `logs/` directory created with log files for each bot + TF
- [ ] All 3 grid bots running (check with `ps aux | grep grid_runner`)
- [ ] Trend follower running (check with `ps aux | grep trend_follower`)

### Test 2: Crash recovery
```bash
# Find a grid bot PID and kill it
kill -9 $(pgrep -f "grid_runner.*BTC")
```
- [ ] Within 30s, orchestrator detects the crash
- [ ] Telegram receives: "🔄 BTC/USDT grid bot restarted (attempt 1/5)"
- [ ] BTC grid bot is running again

### Test 3: Deactivation via admin
Set `is_active = false` for BONK/USDT in Supabase admin dashboard.
- [ ] Grid bot for BONK stops gracefully (existing behavior)
- [ ] Orchestrator does NOT restart it
- [ ] Set `is_active = true` again → orchestrator starts it within 30s

### Test 4: Graceful shutdown
Press Ctrl+C on the orchestrator terminal.
- [ ] Telegram receives: "🛑 Orchestrator shutting down"
- [ ] All processes terminated cleanly
- [ ] No zombie processes

### Test 5: Trades have managed_by
After running for a few minutes with trades:
```sql
SELECT symbol, side, managed_by FROM trades ORDER BY created_at DESC LIMIT 5;
```
- [ ] All trades have `managed_by = 'manual'` (since all current grids are manual)

---

## Scope rules

- **DO NOT** modify the Trend Follower allocator or scanner
- **DO NOT** modify bot_config data for existing symbols
- **DO NOT** change any trading logic in grid_bot.py (only add managed_by to log_trade calls)
- **DO NOT** implement TF writing to bot_config yet (that's the next brief)
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(orchestrator): single process manages all grid bots + trend follower
```
