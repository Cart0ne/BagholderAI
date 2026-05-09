"""
BagHolderAI - Grid Bot Runner
Main loop: fetches real prices, runs the grid, logs results.
Designed for paper trading first, live trading later.

Usage:
    python -m bot.grid_runner              # Run with default settings
    python -m bot.grid_runner --once       # Run one cycle only (for testing)
    python -m bot.grid_runner --dry-run    # Show what would happen, don't log
"""

import sys
import signal
import time
import logging
import argparse
from datetime import datetime, date, timezone
from utils.telegram_notifier import SyncTelegramNotifier
from utils.formatting import fmt_price
from commentary import generate_daily_commentary, get_tf_state


def _sigterm_to_keyboard_interrupt(signum, frame):
    """Map SIGTERM to KeyboardInterrupt so the shutdown path (farewell
    Telegram + final status log) runs when the orchestrator or any
    external supervisor terminates us."""
    raise KeyboardInterrupt()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Silence chatty third-party loggers (httpx logs every Supabase/Binance
# request with the URL; on busy grid bots like BONK ~16% of the log was
# pure HTTP noise). Our own bagholderai.* loggers stay at INFO.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger("bagholderai.runner")

# Imports from project
from config.settings import (
    TradingMode, HardcodedRules, GridConfig, ExchangeConfig, get_grid_config,
    GRID_INSTANCES,
)
from config.supabase_config import SupabaseConfigReader
from bot.exchange import create_exchange
from bot.grid.grid_bot import GridBot
from db.client import TradeLogger, PortfolioManager, DailyPnLTracker, ReserveLedger
from db.event_logger import log_event
from db.snapshot_writer import write_state_snapshot


STRATEGY = "A"


def fetch_price(exchange, symbol: str, max_retries: int = 3) -> float:
    """Fetch current price with retry logic for transient Binance errors."""
    for attempt in range(max_retries):
        try:
            ticker = exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                logger.warning(
                    f"Price fetch failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                raise


def _deactivate_if_fully_liquidated(symbol: str, event_label: str) -> bool:
    """45: after a TF bot's liquidation branch, verify DB contabilità shows
    zero holdings before writing is_active=False. If the last sell INSERT
    timed out on Supabase, bot memory may say 0 but DB still says
    bought > sold — writing is_active=False there would mint an orphan
    that the boot reconciler then has to clean up. Keep is_active=True +
    pending_liquidation=True in that case so the next spawn retries.

    Returns True if the row was deactivated, False if held active for retry.
    """
    try:
        from db.client import get_client
        sb = get_client()
        trades_res = sb.table("trades").select(
            "side, amount"
        ).eq("symbol", symbol).eq("config_version", "v3").execute()
        bought = 0.0
        sold = 0.0
        for t in trades_res.data or []:
            amt = float(t.get("amount") or 0)
            if t.get("side") == "buy":
                bought += amt
            elif t.get("side") == "sell":
                sold += amt
        holdings_db = bought - sold
    except Exception as e:
        # If we can't verify (Supabase unreachable), err on the side of
        # NOT deactivating — worst case the bot stays alive one more
        # iteration; orphan reconciler at next boot will pick up any
        # mistake. Safer than minting an orphan with half-confidence.
        logger.warning(
            f"[{symbol}] Could not verify holdings_db for deactivation gate: {e}. "
            f"Holding is_active=True, pending_liquidation=True for next retry."
        )
        return False

    if holdings_db > 1e-6:
        logger.warning(
            f"[{symbol}] Post-{event_label.lower()} residual holdings_db={holdings_db:.6f} — "
            f"holding is_active=True + pending_liquidation=True so orchestrator "
            f"rispawns and retries the liquidation (likely a log_trade timed out)."
        )
        try:
            sb.table("bot_config").update({
                "is_active": True,
                "pending_liquidation": True,
            }).eq("symbol", symbol).execute()
        except Exception as e:
            logger.error(f"[{symbol}] Failed to hold is_active=True: {e}")
        return False

    # Clean liquidation — deactivate as before.
    try:
        sb.table("bot_config").update({
            "is_active": False,
            "pending_liquidation": False,
        }).eq("symbol", symbol).execute()
        return True
    except Exception as e:
        logger.error(f"[{symbol}] Failed to clear bot_config after {event_label.lower()}: {e}")
        return False


def _sync_config_to_bot(reader: "SupabaseConfigReader", bot: "GridBot", symbol: str):
    """
    Apply the latest Supabase config values to the running bot.
    Only updates fields that are safe to change mid-run without a restart.
    """
    sb_cfg = reader.get_config(symbol)
    if not sb_cfg:
        return
    if "buy_pct" in sb_cfg and sb_cfg["buy_pct"] is not None:
        bot.buy_pct = float(sb_cfg["buy_pct"])
    if "sell_pct" in sb_cfg and sb_cfg["sell_pct"] is not None:
        bot.sell_pct = float(sb_cfg["sell_pct"])
    if "capital_per_trade" in sb_cfg and sb_cfg["capital_per_trade"] is not None:
        bot.capital_per_trade = float(sb_cfg["capital_per_trade"])
    if "grid_mode" in sb_cfg and sb_cfg["grid_mode"] is not None:
        new_mode = sb_cfg["grid_mode"]
        if new_mode != bot.grid_mode:
            logger.info(f"[{symbol}] Grid mode changed: {bot.grid_mode} → {new_mode}")
            bot.grid_mode = new_mode
            if new_mode == "percentage":
                bot.init_percentage_state_from_db()
            logger.info(f"[{symbol}] Strategy re-initialized for {new_mode} mode")
        else:
            bot.grid_mode = new_mode
    if "skim_pct" in sb_cfg and sb_cfg["skim_pct"] is not None:
        bot.skim_pct = float(sb_cfg["skim_pct"])
    if "idle_reentry_hours" in sb_cfg and sb_cfg["idle_reentry_hours"] is not None:
        bot.idle_reentry_hours = float(sb_cfg["idle_reentry_hours"])
    if "profit_target_pct" in sb_cfg and sb_cfg["profit_target_pct"] is not None:
        bot.min_profit_pct = float(sb_cfg["profit_target_pct"])
    if "stop_buy_drawdown_pct" in sb_cfg and sb_cfg["stop_buy_drawdown_pct"] is not None:
        # 39b: per-coin manual stop-buy threshold (hot-reload via config refresh).
        # Changing the value does NOT reset _stop_buy_active — the flag clears
        # only on a profitable sell (event-based hysteresis).
        bot.stop_buy_drawdown_pct = float(sb_cfg["stop_buy_drawdown_pct"])
    if "is_active" in sb_cfg:
        bot.is_active = bool(sb_cfg["is_active"])
    if "pending_liquidation" in sb_cfg:
        # pending_liquidation is monotonic-sticky: once the bot flags itself
        # for cleanup (e.g. 39a stop-loss), don't let a DB poll overwrite it
        # back to False. Clearing happens via the grid_runner UPDATE after the
        # liquidation branch runs + bot exit + fresh start.
        db_flag = bool(sb_cfg.get("pending_liquidation", False))
        if db_flag and not bot.pending_liquidation:
            bot.pending_liquidation = True
    if "managed_by" in sb_cfg and sb_cfg.get("managed_by"):
        bot.managed_by = sb_cfg["managed_by"]

    # 39j: hot-reload of TF safety params from trend_config. Only TF bots use
    # these thresholds (grid_bot gates the checks on managed_by); manual bots
    # keep their own stop_buy_drawdown_pct (39b). Log at INFO on change —
    # Telegram notification is owned by the TF scan loop (39g), not here.
    if bot.managed_by in ("tf", "tf_grid"):
        tf_slp = reader.get_trend_config_value("tf_stop_loss_pct")
        if tf_slp is not None:
            new_slp = float(tf_slp)
            if new_slp != bot.tf_stop_loss_pct:
                logger.info(
                    f"[{symbol}] tf_stop_loss_pct updated: "
                    f"{bot.tf_stop_loss_pct} → {new_slp}"
                )
                bot.tf_stop_loss_pct = new_slp

        tf_tpp = reader.get_trend_config_value("tf_take_profit_pct")
        if tf_tpp is not None:
            new_tpp = float(tf_tpp)
            if new_tpp != bot.tf_take_profit_pct:
                logger.info(
                    f"[{symbol}] tf_take_profit_pct updated: "
                    f"{bot.tf_take_profit_pct} → {new_tpp}"
                )
                bot.tf_take_profit_pct = new_tpp

        # 45f: profit lock enable + threshold — hot-reloaded so the CEO can
        # flip the switch from the dashboard without restarting the bot.
        tf_ple = reader.get_trend_config_value("tf_profit_lock_enabled")
        if tf_ple is not None:
            new_ple = bool(tf_ple)
            if new_ple != bot.tf_profit_lock_enabled:
                logger.info(
                    f"[{symbol}] tf_profit_lock_enabled updated: "
                    f"{bot.tf_profit_lock_enabled} → {new_ple}"
                )
                bot.tf_profit_lock_enabled = new_ple

        tf_plp = reader.get_trend_config_value("tf_profit_lock_pct")
        if tf_plp is not None:
            new_plp = float(tf_plp)
            if new_plp != bot.tf_profit_lock_pct:
                logger.info(
                    f"[{symbol}] tf_profit_lock_pct updated: "
                    f"{bot.tf_profit_lock_pct} → {new_plp}"
                )
                bot.tf_profit_lock_pct = new_plp

        # 45g: hot-reload kill-switch and global N (so CEO can change either
        # from the dashboard / SQL without restarting the orchestrator).
        tf_xen = reader.get_trend_config_value("tf_exit_after_n_enabled")
        if tf_xen is not None:
            new_xen = bool(tf_xen)
            if new_xen != bot.tf_exit_after_n_enabled:
                logger.info(
                    f"[{symbol}] tf_exit_after_n_enabled updated: "
                    f"{bot.tf_exit_after_n_enabled} → {new_xen}"
                )
                bot.tf_exit_after_n_enabled = new_xen

        tf_xn = reader.get_trend_config_value("tf_exit_after_n_positive_sells")
        if tf_xn is not None:
            new_xn = int(tf_xn)
            if new_xn != bot.tf_exit_after_n_default:
                logger.info(
                    f"[{symbol}] tf_exit_after_n_positive_sells updated: "
                    f"{bot.tf_exit_after_n_default} → {new_xn}"
                )
                bot.tf_exit_after_n_default = new_xn

        # 45g: per-coin override lives on bot_config — re-read each tick so
        # CEO's SQL UPDATEs propagate without restart.
        new_override = sb_cfg.get("tf_exit_after_n_override")
        new_override_int = int(new_override) if new_override is not None else None
        if new_override_int != bot.tf_exit_after_n_override:
            logger.info(
                f"[{symbol}] tf_exit_after_n_override updated: "
                f"{bot.tf_exit_after_n_override} → {new_override_int}"
            )
            bot.tf_exit_after_n_override = new_override_int

        # 51b: hot-reload trailing-stop knobs (activation + trailing pct).
        # Same pattern as the other safety params — CEO changes the DB
        # value, the next tick picks it up. 0 disables the feature
        # immediately (peak tracking branch in grid_bot keys off it).
        tf_tsa = reader.get_trend_config_value("tf_trailing_stop_activation_pct")
        if tf_tsa is not None:
            new_tsa = float(tf_tsa)
            if new_tsa != bot.tf_trailing_stop_activation_pct:
                logger.info(
                    f"[{symbol}] tf_trailing_stop_activation_pct updated: "
                    f"{bot.tf_trailing_stop_activation_pct} → {new_tsa}"
                )
                bot.tf_trailing_stop_activation_pct = new_tsa

        tf_tsp = reader.get_trend_config_value("tf_trailing_stop_pct")
        if tf_tsp is not None:
            new_tsp = float(tf_tsp)
            if new_tsp != bot.tf_trailing_stop_pct:
                logger.info(
                    f"[{symbol}] tf_trailing_stop_pct updated: "
                    f"{bot.tf_trailing_stop_pct} → {new_tsp}"
                )
                bot.tf_trailing_stop_pct = new_tsp

        # 42a: greed_decay_tiers is global (trend_config); allocated_at is
        # per-bot (bot_config). Both are re-read each tick so UI edits and
        # SWAP re-allocations propagate without restart.
        new_tiers = reader.get_trend_config_value("greed_decay_tiers")
        if new_tiers is not None and new_tiers != bot.greed_decay_tiers:
            logger.info(
                f"[{symbol}] greed_decay_tiers updated: "
                f"{bot.greed_decay_tiers} → {new_tiers}"
            )
            bot.greed_decay_tiers = new_tiers

        raw_alloc = sb_cfg.get("allocated_at")
        if raw_alloc:
            try:
                new_alloc = datetime.fromisoformat(str(raw_alloc).replace("Z", "+00:00"))
                if new_alloc != bot.allocated_at:
                    logger.info(
                        f"[{symbol}] allocated_at updated: "
                        f"{bot.allocated_at} → {new_alloc}"
                    )
                    bot.allocated_at = new_alloc
            except Exception as e:
                logger.warning(f"[{symbol}] allocated_at parse error: {e}")


def _consume_initial_lots(reader, bot, symbol: str, price: float, notifier) -> int:
    """42a: Multi-lot entry — a SINGLE market buy sized N×capital_per_trade.

    On the first cycle after a TF ALLOCATE, fire one aggregated market buy
    equivalent to N lots, where N = bot_config.initial_lots (written by the
    allocator). This produces exactly 1 Binance order, 1 DB INSERT and 1
    Telegram alert (unlike the earlier per-lot loop which caused duplicate
    inserts to be rejected by the DB dedup trigger on ravvicinate calls).

    Idempotency: a bot-level latch (`bot._initial_lots_done`) prevents
    re-firing during the same process lifetime regardless of when the DB
    UPDATE propagates back through the 300s config-reader cache.

    Returns the number of logical lots bought (0 if not applicable).
    """
    if bot.managed_by not in ("tf", "tf_grid"):
        return 0
    # In-memory latch: once we've handled the entry for this bot instance,
    # don't even look at the cached initial_lots again — the 300s reader
    # refresh would otherwise keep returning the stale "3" for minutes
    # after we've already UPDATEd the DB row to 0.
    if getattr(bot, "_initial_lots_done", False):
        return 0

    sb_cfg = reader.get_config(symbol)
    raw = sb_cfg.get("initial_lots") if sb_cfg else None
    try:
        lots = int(raw) if raw is not None else 0
    except Exception:
        lots = 0
    if lots <= 0:
        # Mark done so subsequent ticks skip the cache lookup. DB is already
        # 0 (or the allocator never set it); nothing to do.
        bot._initial_lots_done = True
        return 0

    # Single aggregated buy: temporarily scale capital_per_trade so the
    # existing _execute_percentage_buy path emits ONE trade for N lots
    # worth of capital. Grid sell-per-lot semantics are preserved because
    # the resulting position is one big lot in _pct_open_positions, and
    # greed decay evaluates each lot independently against its own buy
    # price (all lots after this carry their own price).
    per_trade_before = bot.capital_per_trade
    aggregate = per_trade_before * lots
    bot.capital_per_trade = aggregate
    logger.info(
        f"[{symbol}] Multi-lot entry: firing 1 aggregated market buy of "
        f"{lots} lots (~${aggregate:.2f} @ {fmt_price(price)})"
    )
    try:
        trade = bot._execute_percentage_buy(price)
    finally:
        bot.capital_per_trade = per_trade_before

    # Clear DB flag + set latch regardless of buy success — the entry window
    # is one-shot. If the single buy failed (e.g. cash insufficient), the
    # TF bot falls through to normal grid logic on subsequent ticks.
    bot._initial_lots_done = True
    try:
        from db.client import get_client
        get_client().table("bot_config").update(
            {"initial_lots": 0}
        ).eq("symbol", symbol).execute()
    except Exception as e:
        logger.error(f"[{symbol}] Failed to reset initial_lots to 0: {e}")

    if trade is None:
        logger.warning(
            f"[{symbol}] Multi-lot entry skipped — aggregated buy returned "
            f"None (likely insufficient cash)."
        )
        return 0

    cost = float(trade.get("cost", 0.0))
    # Annotate the trade for Telegram + log — reason override so the CEO
    # sees it framed as a multi-lot entry, not a plain "first buy".
    trade["reason"] = (
        f"Multi-lot entry: {lots} lots at market "
        f"({fmt_price(price)}, total ${cost:.2f})"
    )
    try:
        notifier.send_trade_alert(trade)
    except Exception as e:
        logger.warning(f"[{symbol}] multi-lot entry alert failed: {e}")
    try:
        notifier.send_message(
            f"🚀 <b>{symbol} Multi-lot entry</b>\n"
            f"Bought {lots} lots at market (${cost:.2f} total)"
        )
    except Exception as e:
        logger.warning(f"[{symbol}] multi-lot entry summary alert failed: {e}")
    log_event(
        severity="info",
        category="tf",
        event="multi_lot_entry_fired",
        symbol=symbol,
        message=f"Multi-lot entry: {lots} lots at ${price:.6f} (total ${cost:.2f})",
        details={"lots": lots, "price": price, "total_cost": cost},
    )
    return lots


def run_grid_bot(symbol: str = "BTC/USDT", once: bool = False, dry_run: bool = False):
    """Main loop."""

    # Ensure SIGTERM drops into the farewell path (see _sigterm handler above).
    signal.signal(signal.SIGTERM, _sigterm_to_keyboard_interrupt)

    # Load local config for this symbol (fallback / initial values)
    cfg = get_grid_config(symbol)
    # Unknown symbols fall back to BTC config; force the requested symbol so
    # TF-created grids don't accidentally trade BTC.
    cfg.symbol = symbol

    # --- Read config from Supabase (Task 2) ---
    config_reader = SupabaseConfigReader(own_symbol=cfg.symbol)
    try:
        config_reader.load_initial()
        sb_cfg = config_reader.get_config(symbol)
        if sb_cfg:
            # Override local config with Supabase values
            # S69: rimosso sync di grid_mode/grid_levels/grid_lower/grid_upper —
            # fixed mode è codice morto (tutti i bot_config hanno grid_mode='percentage').
            # Refactor completo + DROP COLUMN DB rinviato a BLOCCO 3 (TRUNCATE+restart).
            if sb_cfg.get("capital_allocation") is not None:
                cfg.capital = float(sb_cfg["capital_allocation"])
            if sb_cfg.get("capital_per_trade") is not None:
                cfg.capital_per_trade = float(sb_cfg["capital_per_trade"])
            if sb_cfg.get("buy_pct") is not None:
                cfg.buy_pct = float(sb_cfg["buy_pct"])
            if sb_cfg.get("sell_pct") is not None:
                cfg.sell_pct = float(sb_cfg["sell_pct"])
            if sb_cfg.get("profit_target_pct") is not None:
                cfg.min_profit_pct = float(sb_cfg["profit_target_pct"])
    except Exception as e:
        logger.warning(f"Could not load Supabase config, using local defaults: {e}")

    config_reader.start_refresh_loop()

    logger.info("=" * 50)
    logger.info("BagHolderAI Grid Bot starting...")
    logger.info(f"Mode: {'PAPER' if TradingMode.is_paper() else 'LIVE'}")
    logger.info(f"Symbol: {cfg.symbol}")
    logger.info(f"Capital: ${cfg.capital}")
    logger.info(f"Levels: {cfg.num_levels}")
    logger.info(f"Range: {cfg.grid_range_pct * 100:.1f}%")
    logger.info(f"Grid mode: {cfg.grid_mode}")
    if cfg.grid_mode == "percentage":
        logger.info(f"Capital per trade: ${cfg.capital_per_trade}")
        logger.info(f"Buy pct: {cfg.buy_pct}% / Sell pct: {cfg.sell_pct}%")
    else:
        per_level = cfg.capital / max(cfg.num_levels // 2, 1)
        logger.info(f"Capital per level: ${per_level:.2f} (={cfg.capital} / {cfg.num_levels // 2} buy levels)")
    logger.info(f"Check interval: {cfg.check_interval_seconds}s")
    logger.info(f"Buy cooldown: {cfg.buy_cooldown_seconds}s")
    logger.info("=" * 50)

    # Safety checks for live mode (testnet OR mainnet).
    # 66a Step 3: live trading path is now implemented via
    # bot/exchange_orders.py (market orders only).
    if TradingMode.is_live():
        if not ExchangeConfig.API_KEY or not ExchangeConfig.SECRET:
            logger.error(
                "Live mode requires BINANCE_API_KEY and BINANCE_SECRET in config/.env. Aborting."
            )
            return
        if ExchangeConfig.TESTNET:
            logger.warning(
                "LIVE MODE: TESTNET — orders route to testnet.binance.vision (fake money, real fills)"
            )
        else:
            # Mainnet authorization gate. Will be lifted in a future brief
            # once testnet shake-down + reconciliation gate (Step 5) are
            # green. Until then mainnet is hard-blocked from this entry point.
            logger.error(
                "LIVE MODE: MAINNET — not authorized in S67. "
                "Set BINANCE_TESTNET=true in config/.env to use testnet, "
                "or wait for the mainnet go-live brief. Aborting."
            )
            return

    # Initialize components
    exchange = create_exchange()

    if dry_run:
        trade_logger = None
        portfolio_manager = None
        pnl_tracker = None
        reserve_ledger = None
        logger.info("DRY RUN — trades will NOT be logged to database")
    else:
        trade_logger = TradeLogger()
        portfolio_manager = PortfolioManager()
        pnl_tracker = DailyPnLTracker()
        reserve_ledger = ReserveLedger()

    # Initialize Telegram
    notifier = SyncTelegramNotifier()

    # 39a/39c/45f: TF stop-loss + take-profit + profit-lock thresholds live
    # in trend_config (global policy, not per-bot). Read once at startup;
    # hot-reload is handled inside _sync_config_to_bot. Manual bots ignore
    # all three (only TF bots arm the checks inside grid_bot), so reading
    # them unconditionally is safe.
    tf_stop_loss_pct = 0.0
    tf_take_profit_pct = 0.0
    tf_profit_lock_enabled = False
    tf_profit_lock_pct = 0.0
    tf_exit_after_n_enabled = True
    tf_exit_after_n_default = 4
    tf_trailing_stop_activation_pct = 1.5  # 51b
    tf_trailing_stop_pct = 0.0             # 51b: 0 = disabled at startup until DB read
    try:
        from db.client import get_client
        _sb = get_client()
        _tc = _sb.table("trend_config").select(
            "tf_stop_loss_pct,tf_take_profit_pct,tf_profit_lock_enabled,"
            "tf_profit_lock_pct,tf_exit_after_n_enabled,tf_exit_after_n_positive_sells,"
            "tf_trailing_stop_activation_pct,tf_trailing_stop_pct"
        ).limit(1).execute()
        if _tc.data:
            row = _tc.data[0]
            if row.get("tf_stop_loss_pct") is not None:
                tf_stop_loss_pct = float(row["tf_stop_loss_pct"])
            if row.get("tf_take_profit_pct") is not None:
                tf_take_profit_pct = float(row["tf_take_profit_pct"])
            if row.get("tf_profit_lock_enabled") is not None:
                tf_profit_lock_enabled = bool(row["tf_profit_lock_enabled"])
            if row.get("tf_profit_lock_pct") is not None:
                tf_profit_lock_pct = float(row["tf_profit_lock_pct"])
            if row.get("tf_exit_after_n_enabled") is not None:
                tf_exit_after_n_enabled = bool(row["tf_exit_after_n_enabled"])
            if row.get("tf_exit_after_n_positive_sells") is not None:
                tf_exit_after_n_default = int(row["tf_exit_after_n_positive_sells"])
            if row.get("tf_trailing_stop_activation_pct") is not None:
                tf_trailing_stop_activation_pct = float(row["tf_trailing_stop_activation_pct"])
            if row.get("tf_trailing_stop_pct") is not None:
                tf_trailing_stop_pct = float(row["tf_trailing_stop_pct"])
    except Exception as e:
        logger.warning(f"Could not read trend_config safety params: {e}. Defaulting to 0.")

    # 45g: per-coin override lives in bot_config.tf_exit_after_n_override.
    # NULL = use the global default. CEO can SET this for individual coins.
    tf_exit_after_n_override = None
    try:
        if sb_cfg and sb_cfg.get("tf_exit_after_n_override") is not None:
            tf_exit_after_n_override = int(sb_cfg["tf_exit_after_n_override"])
    except Exception as e:
        logger.warning(f"Could not read bot_config.tf_exit_after_n_override for {cfg.symbol}: {e}.")

    # 39b: manual stop-buy threshold is per-coin (lives in bot_config).
    # TF bots ignore it (gated by managed_by != 'tf' in grid_bot).
    stop_buy_drawdown_pct = 0.0
    try:
        if sb_cfg and sb_cfg.get("stop_buy_drawdown_pct") is not None:
            stop_buy_drawdown_pct = float(sb_cfg["stop_buy_drawdown_pct"])
    except Exception as e:
        logger.warning(f"Could not read bot_config.stop_buy_drawdown_pct for {cfg.symbol}: {e}. Defaulting to 0.")

    # 42a: greed decay anchor (per-bot) + tiers (global, from trend_config).
    # allocated_at is the TF ALLOCATE moment; manual bots have NULL here and
    # fall back to sell_pct. greed_decay_tiers is the JSON array polled by
    # SupabaseConfigReader; exposed via get_trend_config_value. Both are
    # hot-reloaded every cycle in _sync_config_to_bot.
    allocated_at = None
    try:
        raw_alloc = sb_cfg.get("allocated_at") if sb_cfg else None
        if raw_alloc:
            allocated_at = datetime.fromisoformat(str(raw_alloc).replace("Z", "+00:00"))
    except Exception as e:
        logger.warning(f"Could not parse allocated_at for {cfg.symbol}: {e}. Defaulting to None.")
    greed_decay_tiers = config_reader.get_trend_config_value("greed_decay_tiers")

    # Create grid bot
    bot = GridBot(
        exchange=exchange,
        trade_logger=trade_logger,
        portfolio_manager=portfolio_manager,
        pnl_tracker=pnl_tracker,
        symbol=cfg.symbol,
        strategy=STRATEGY,
        capital=cfg.capital,
        num_levels=cfg.num_levels,
        range_percent=cfg.grid_range_pct,
        # 67a: read the trading mode dynamically. Hardcoding "paper" caused
        # all live testnet trades to be tagged as paper in the DB, breaking
        # downstream filters (dashboards, reconciliation, audit). The CHECK
        # constraint on trades.mode accepts only 'paper' | 'live', so any
        # live mode (testnet OR mainnet) maps to 'live' here.
        mode=TradingMode.MODE,
        buy_cooldown_seconds=cfg.buy_cooldown_seconds,
        min_profit_pct=cfg.min_profit_pct,
        grid_mode=cfg.grid_mode,
        buy_pct=cfg.buy_pct,
        sell_pct=cfg.sell_pct,
        capital_per_trade=cfg.capital_per_trade,
        reserve_ledger=reserve_ledger,
        skim_pct=cfg.skim_pct,
        tf_stop_loss_pct=tf_stop_loss_pct,
        stop_buy_drawdown_pct=stop_buy_drawdown_pct,
        tf_take_profit_pct=tf_take_profit_pct,
        tf_profit_lock_enabled=tf_profit_lock_enabled,
        tf_profit_lock_pct=tf_profit_lock_pct,
        tf_exit_after_n_enabled=tf_exit_after_n_enabled,
        tf_exit_after_n_default=tf_exit_after_n_default,
        tf_exit_after_n_override=tf_exit_after_n_override,
        tf_trailing_stop_activation_pct=tf_trailing_stop_activation_pct,
        tf_trailing_stop_pct=tf_trailing_stop_pct,
        allocated_at=allocated_at,
        greed_decay_tiers=greed_decay_tiers,
    )

    # Initial managed_by from Supabase (default "grid" — 68b)
    try:
        _initial_cfg = config_reader.get_config(cfg.symbol)
        bot.managed_by = (_initial_cfg.get("managed_by") or "grid") if _initial_cfg else "grid"
    except Exception:
        bot.managed_by = "grid"

    # Fetch initial price and setup grid
    try:
        price = fetch_price(exchange, cfg.symbol)
        logger.info(f"Current {cfg.symbol} price: {fmt_price(price)}")
    except Exception as e:
        logger.error(f"Failed to fetch price: {e}")
        return

    # Load exchange filters for order validation + cache to Supabase
    from utils.exchange_filters import fetch_filters, fetch_and_cache_filters
    try:
        filters = fetch_filters(exchange, cfg.symbol)
        bot.set_exchange_filters(filters)
        # Cache filters for all grid instances (first bot to start does this)
        all_symbols = [inst.symbol for inst in GRID_INSTANCES]
        fetch_and_cache_filters(exchange, all_symbols, supabase_client=trade_logger.client if trade_logger else None)
    except Exception as e:
        logger.warning(f"[{cfg.symbol}] Could not load exchange filters: {e}")

    bot.setup_grid(price)
    if cfg.grid_mode == "percentage":
        # Brief s70 FASE 1: boot replay populates state.holdings +
        # state.avg_buy_price from canonical avg-cost. The FIFO queue
        # field is also touched by the legacy replay but no longer
        # consulted in the hot path (avg-cost trading).
        bot.init_percentage_state_from_db()
    else:
        bot.restore_state_from_db()

    # Print initial grid
    if cfg.grid_mode == "percentage":
        logger.info("Grid triggers (percentage mode):")
        ref = bot._pct_last_buy_price
        if ref:
            buy_trigger = ref * (1 - bot.buy_pct / 100)
            logger.info(f"  Buy trigger:    {fmt_price(buy_trigger)}  (ref {fmt_price(ref)} -{bot.buy_pct}%)")
        else:
            logger.info(f"  Buy trigger:    immediate  (no reference — first entry)")
        if bot.state.holdings > 0 and bot.state.avg_buy_price > 0:
            sell_trigger = bot.state.avg_buy_price * (1 + bot.sell_pct / 100)
            logger.info(
                f"  Sell trigger:   {fmt_price(sell_trigger)}  "
                f"(avg cost {fmt_price(bot.state.avg_buy_price)} +{bot.sell_pct}%, "
                f"holdings {bot.state.holdings:.6f})"
            )
        else:
            logger.info(f"  Holdings:       none")
        logger.info(f"  Current price:  {fmt_price(price)}")
    else:
        logger.info("Grid levels (fixed mode):")
        for level in bot.state.levels:
            marker = "BUY ↓" if level.side == "buy" else "SELL ↑"
            base = cfg.symbol.split("/")[0] if "/" in cfg.symbol else cfg.symbol
            amount_str = f" ({level.order_amount:.6f} {base})" if level.order_amount > 0 else ""
            logger.info(f"  {fmt_price(level.price):>14}  {marker}{amount_str}")
        logger.info(f"  Current price:  {fmt_price(price)}")

    # Per-bot start notification suppressed: the orchestrator's single
    # "🚀 Orchestrator started" summary is enough — less Telegram noise.
    # Status is still logged to grid_<symbol>.log for audit.

    if once:
        logger.info("Single cycle mode — checking once and exiting.")
        trades = bot.check_price_and_execute(price)
        _print_status(bot)
        return

    # Main loop — Task 6: use per-asset check interval from config
    check_interval = cfg.check_interval_seconds
    logger.info(f"Starting main loop (checking every {check_interval}s)...")
    logger.info("Press Ctrl+C to stop.\n")

    # 43a: structured event for bot start. managed_by is the single most
    # useful piece of context here (tells TF vs manual at a glance).
    log_event(
        severity="info",
        category="lifecycle",
        event="bot_started",
        symbol=cfg.symbol,
        message=f"Grid bot entering main loop (interval {check_interval}s)",
        details={
            "managed_by": getattr(bot, "managed_by", "grid"),
            "check_interval_s": check_interval,
            "capital": cfg.capital,
        },
    )

    daily_report_sent = None  # Track which date we sent the report
    REPORT_HOUR = 20  # Send daily report at 20:00

    # Proactive alert state.
    # _capital_exhausted is seeded from the restored state: if the bot
    # restarts with cash already below the last-shot floor, treat it as
    # "already known to the user" so we don't re-notify on every restart.
    # Alerts fire only on state TRANSITIONS during the process lifetime
    # (exhausted → restored → exhausted again), which is what the user
    # actually cares about.
    try:
        _initial_cash = bot.get_status().get("available_capital", 0.0)
    except Exception:
        _initial_cash = 0.0
    _capital_exhausted = _initial_cash < HardcodedRules.MIN_LAST_SHOT_USD
    if _capital_exhausted:
        logger.info(
            f"[{cfg.symbol}] Boot with cash ${_initial_cash:.2f} below "
            f"${HardcodedRules.MIN_LAST_SHOT_USD:.2f} — capital-exhausted "
            f"state restored silently (no Telegram)."
        )
    _error_count = 0
    _error_last_alert = 0.0
    ERROR_ALERT_COOLDOWN = 30 * 60  # 30 minutes between repeated error alerts
    # Skip-notification dedup: symbol -> (level_price_rounded, cash_rounded)
    _last_skip_notification: dict = {}
    # Sell-skip dedup: symbol -> (level_price_rounded, holdings_rounded)
    _last_sell_skip_notification: dict = {}

    cycle = 0
    stop_reason = "manual"
    while True:
        try:
            cycle += 1

            # Sync dynamic config fields from Supabase reader to bot
            _sync_config_to_bot(config_reader, bot, cfg.symbol)

            # 49b: 45g proactive check. Covers TF coins whose counter has
            # already reached N before the post-sell check inside
            # check_price_and_execute can ever fire (e.g. holdings=0 with
            # closed cycle, or counter pre-existing at deploy time). Rate-
            # limited per-symbol to avoid hammering Supabase. The check
            # itself is idempotent against the post-sell path via the
            # _gain_saturation_triggered flag.
            if (bot.managed_by == "tf"
                    and bot.tf_exit_after_n_enabled
                    and not bot._gain_saturation_triggered):
                from bot.trend_follower.gain_saturation import should_run_proactive_check
                if should_run_proactive_check(cfg.symbol):
                    try:
                        live_price = fetch_price(exchange, cfg.symbol)
                        bot.evaluate_gain_saturation(live_price, trigger_source="proactive_tick")
                    except Exception as e:
                        logger.warning(
                            f"[{cfg.symbol}] proactive 45g check failed: {e}"
                        )

            # Graceful shutdown if is_active=false in Supabase
            if not bot.is_active:
                logger.info(f"[{cfg.symbol}] is_active=false — shutting down gracefully")
                notifier.send_message(
                    f"🛑 <b>{cfg.symbol} grid bot stopped</b> (is_active=false)"
                )
                stop_reason = "is_active=false"
                break

            # Forced liquidation (e.g., TF BEARISH rotation): pending_liquidation
            # set in DB by the allocator — dump all holdings at market and exit.
            # 49b: 45g proactive trigger also routes through here when
            # holdings=0 (no per-lot sell phase to ride), tagged with the
            # appropriate reason so the cycle-close Telegram is honest.
            if getattr(bot, "pending_liquidation", False):
                if getattr(bot, "_gain_saturation_triggered", False):
                    top_reason = "GAIN-SATURATION"
                elif getattr(bot, "_trailing_stop_triggered", False):  # 51b
                    top_reason = "TRAILING-STOP"
                else:
                    top_reason = "BEARISH EXIT"
                logger.info(
                    f"[{cfg.symbol}] pending_liquidation=true ({top_reason}) "
                    f"— force-selling all positions"
                )
                # 49b: 45g via top-of-loop (holdings=0) does NOT pass through
                # the mid-tick DEALLOCATE-writer below, so write the
                # DEALLOCATE row here. BEARISH path skips this write because
                # the allocator already wrote one when it set
                # pending_liquidation=True (see allocator.py:1138).
                if (top_reason == "GAIN-SATURATION"
                        and getattr(bot, "managed_by", "grid") == "tf"
                        and trade_logger is not None):
                    try:
                        trade_logger.client.table("trend_decisions_log").insert({
                            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
                            "symbol": cfg.symbol,
                            "ema_fast_value": 0, "ema_slow_value": 0,
                            "rsi_value": 0, "atr_value": 0,
                            "signal": "NO_SIGNAL", "signal_strength": 0,
                            "action_taken": "DEALLOCATE",
                            "is_shadow": False,
                            "reason": "GAIN_SATURATION (proactive trigger)",
                            "config_written": None,
                        }).execute()
                    except Exception as e:
                        logger.warning(
                            f"[{cfg.symbol}] Failed to log GAIN_SATURATION "
                            f"DEALLOCATE: {e}"
                        )
                _force_liquidate(bot, exchange, trade_logger, notifier, cfg.symbol,
                                 reason=top_reason)
                _deactivate_if_fully_liquidated(cfg.symbol, top_reason)
                # 50a: gain-saturation must surface as its own reason for
                # forensics/dashboard (was previously bucketed as
                # "liquidation"). BEARISH rotations keep "liquidation".
                if getattr(bot, "_gain_saturation_triggered", False):
                    stop_reason = "gain_saturation"
                elif getattr(bot, "_trailing_stop_triggered", False):  # 51b
                    stop_reason = "trailing_stop"
                else:
                    stop_reason = "liquidation"
                break

            price = fetch_price(exchange, cfg.symbol)

            # Check if grid needs reset (price moved too far)
            if bot.should_reset_grid(price):
                old_range = bot.get_status().get("range", "N/A")
                logger.info(f"Price {fmt_price(price)} outside grid range. Resetting grid...")
                bot.setup_grid(price)
                new_range = bot.get_status().get("range", "N/A")
                notifier.send_grid_reset(old_range, new_range, price)

            # 42a: fire multi-lot market entry on the first cycle after an
            # ALLOCATE. No-op for manual bots and for TF bots with
            # initial_lots=0. Must run BEFORE check_price_and_execute so the
            # new lots are visible to the sell-queue logic in the same tick.
            _consume_initial_lots(config_reader, bot, cfg.symbol, price, notifier)

            # Run grid logic
            trades = bot.check_price_and_execute(price)

            # 39a/39c: stop-loss or take-profit inside check_price_and_execute
            # may have flagged pending_liquidation. Handle it NOW (before the
            # daily-PnL guard can short-circuit to an is_active=True exit
            # that would trigger an orchestrator respawn). Mirrors the
            # top-of-loop branch.
            #
            # CEO preference: ONE summary Telegram per forced-exit event
            # (not one-per-sell). Build it from the `trades` list we just
            # got back — already has all lots + their PnL — then break
            # before the individual-trade alert loop below.
            if getattr(bot, "pending_liquidation", False):
                is_tp = getattr(bot, "_take_profit_triggered", False)
                is_pl = getattr(bot, "_profit_lock_triggered", False)
                is_gs = getattr(bot, "_gain_saturation_triggered", False)
                is_ts = getattr(bot, "_trailing_stop_triggered", False)  # 51b
                if is_gs:
                    event_label = "GAIN-SATURATION"
                    stop_reason_tag = "gain_saturation"
                elif is_pl:
                    event_label = "PROFIT-LOCK"
                    stop_reason_tag = "profit_lock"
                elif is_tp:
                    event_label = "TAKE-PROFIT"
                    stop_reason_tag = "take_profit"
                elif is_ts:
                    event_label = "TRAILING-STOP"
                    stop_reason_tag = "trailing_stop"
                else:
                    event_label = "STOP-LOSS"
                    stop_reason_tag = "stop_loss"

                logger.info(
                    f"[{cfg.symbol}] pending_liquidation triggered mid-tick ({event_label.lower()}) — closing bot"
                )

                # 39f Section B: close the TF cycle formally by writing a
                # DEALLOCATE row to trend_decisions_log. Without this row
                # the cycle never ends in TF's eyes and the next ALLOCATE
                # would attribute its trades to the wrong window. Mirrors
                # what the allocator does for SWAP / BEARISH dealloc paths.
                managed_by = getattr(bot, "managed_by", "grid")
                if managed_by in ("tf", "tf_grid") and trade_logger is not None:
                    forced_sells = [t for t in (trades or []) if t.get("side") == "sell"]
                    total_pnl = sum(float(t.get("realized_pnl", 0)) for t in forced_sells)
                    if managed_by == "tf_grid":
                        dealloc_reason = (
                            f"PROFIT-LOCK EXIT (tf_grid): {event_label} "
                            f"(cycle closed after {len(forced_sells)} sells, "
                            f"realized ${total_pnl:+.2f})"
                        )
                    else:
                        dealloc_reason = (
                            f"{event_label} exhausted (cycle closed after "
                            f"{len(forced_sells)} sells, realized ${total_pnl:+.2f})"
                        )
                    try:
                        trade_logger.client.table("trend_decisions_log").insert({
                            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
                            "symbol": cfg.symbol,
                            "ema_fast_value": 0, "ema_slow_value": 0,
                            "rsi_value": 0, "atr_value": 0,
                            "signal": "NO_SIGNAL", "signal_strength": 0,
                            "action_taken": "DEALLOCATE",
                            "is_shadow": False,
                            "reason": dealloc_reason,
                            "config_written": None,
                        }).execute()
                    except Exception as e:
                        logger.warning(
                            f"[{cfg.symbol}] Failed to log DEALLOCATE decision: {e}"
                        )

                # 39f Section B: no more per-event "X LIQUIDATED" Telegram
                # here — the unified dealloc + cycle summary message comes
                # from _force_liquidate. For stop-loss/TP, holdings is
                # already 0 (grid_bot sold per-lot), so _force_liquidate
                # takes the "no-sell cycle close" branch.
                _force_liquidate(bot, exchange, trade_logger, notifier, cfg.symbol,
                                 reason=event_label)
                _deactivate_if_fully_liquidated(cfg.symbol, event_label)
                stop_reason = stop_reason_tag
                break

            # Idle re-entry / recalibrate alert: send BEFORE trade alerts so context arrives first
            for alert in bot.idle_reentry_alerts:
                base = alert["symbol"].split("/")[0] if "/" in alert["symbol"] else alert["symbol"]
                if alert.get("recalibrate"):
                    notifier.send_message(
                        f"🔄 <b>IDLE RECALIBRATE: {base}</b>\n"
                        f"After {alert['elapsed_hours']:.1f}h idle, buy reference reset to "
                        f"{fmt_price(alert['reference_price'])}\n"
                        f"Holdings still open — waiting for next buy signal."
                    )
                else:
                    notifier.send_message(
                        f"⏰ <b>IDLE RE-ENTRY: {base}</b>\n"
                        f"After {alert['elapsed_hours']:.1f}h idle, new reference: "
                        f"{fmt_price(alert['reference_price'])}\n"
                        f"Buying at market..."
                    )

            # Log trades
            if trades:
                for t in trades:
                    emoji = "🟢" if t["side"] == "buy" else "🔴"
                    logger.info(
                        f"{emoji} {t['side'].upper()} {t['amount']:.6f} "
                        f"@ {fmt_price(t['price'])} | {t['reason']}"
                    )
                    notifier.send_trade_alert(t)

            # Alert for skipped buys (insufficient cash) — deduplicated
            # Se il capitale è già esaurito, non spammare: l'utente è già stato avvisato
            if not _capital_exhausted:
                for skip in bot.skipped_buys:
                    sym = skip['symbol']
                    dedup_key = (round(skip['level_price'], 8), round(skip['cash_before'], 2))
                    if _last_skip_notification.get(sym) == dedup_key:
                        continue  # same level + same cash balance — already notified
                    _last_skip_notification[sym] = dedup_key
                    base = sym.split("/")[0] if "/" in sym else sym
                    msg = (
                        f"⚠️ BUY SKIPPED {sym}\n"
                        f"Level: {fmt_price(skip['level_price'])}\n"
                        f"💵 Cash {base}: ${skip['cash_before']:.2f} → Servono ${skip['cost']:.2f} ❌ SKIPPED\n"
                        f"Motivo: capitale insufficiente"
                    )
                    notifier.send_message(msg)

            # Alert for skipped sells (insufficient holdings) — deduplicated
            for skip in bot.skipped_sells:
                sym = skip['symbol']
                sell_dedup_key = (round(skip['level_price'], 8), round(skip['holdings'], 6))
                if _last_sell_skip_notification.get(sym) == sell_dedup_key:
                    continue
                _last_sell_skip_notification[sym] = sell_dedup_key
                msg = (
                    f"⚠️ SELL SKIPPED {sym}\n"
                    f"Level: {fmt_price(skip['level_price'])}\n"
                    f"Need: {skip['amount_needed']:.6f} | Have: {skip['holdings']:.6f}\n"
                    f"Motivo: holdings insufficienti"
                )
                notifier.send_message(msg)

            # Alert: capital exhausted / recovered
            available = bot.get_status()["available_capital"]
            if available < HardcodedRules.MIN_LAST_SHOT_USD and not _capital_exhausted:
                _capital_exhausted = True
                notifier.send_message(
                    f"⚠️ <b>{cfg.symbol}: Capitale esaurito</b>\n"
                    f"Cash disponibile: ${available:.2f}\n"
                    f"Tutte le posizioni sono deployed.\n"
                    f"Il bot attende un sell per ricominciare a comprare."
                )
                log_event(
                    severity="warn",
                    category="safety",
                    event="capital_exhausted",
                    symbol=cfg.symbol,
                    message=f"Cash ${available:.2f} below last-shot floor ${HardcodedRules.MIN_LAST_SHOT_USD}",
                    details={"available": available, "floor": HardcodedRules.MIN_LAST_SHOT_USD},
                )
            elif available >= HardcodedRules.MIN_LAST_SHOT_USD and _capital_exhausted:
                _capital_exhausted = False
                notifier.send_message(
                    f"✅ <b>{cfg.symbol}: Capitale ripristinato</b>\n"
                    f"Cash disponibile: ${available:.2f}\n"
                    f"Il bot può tornare a comprare."
                )
                log_event(
                    severity="info",
                    category="safety",
                    event="capital_restored",
                    symbol=cfg.symbol,
                    message=f"Cash restored to ${available:.2f}",
                    details={"available": available},
                )

            # Error recovery: cycle succeeded after consecutive failures
            if _error_count > 0:
                notifier.send_message(
                    f"✅ <b>{cfg.symbol}: Loop ripristinato</b>\n"
                    f"Errori consecutivi risolti: {_error_count}\n"
                    f"Bot operativo."
                )
                _error_count = 0
                _error_last_alert = 0.0

            # Periodic status update (every 10 cycles)
            if cycle % 10 == 0:
                _print_status(bot)

            # 43b: write a bot_state_snapshot every ~15 cycles. With
            # check_interval=60s that's ~15 min per snapshot, giving the
            # CEO an equity-curve-grade timeline without replaying trades
            # from scratch. The writer swallows its own errors so a slow
            # Supabase round-trip never stalls the main loop.
            if cycle % 15 == 0:
                write_state_snapshot(bot, cfg.symbol)

            # Daily report at 20:00 — only first bot to trigger sends
            now = datetime.now()
            if now.hour >= REPORT_HOUR and daily_report_sent != date.today():
                # Set flag immediately so even if the send fails we don't send twice
                daily_report_sent = date.today()
                try:
                    # Build consolidated portfolio from DB + live prices
                    portfolio_summary = _build_portfolio_summary(
                        trade_logger, exchange, bot, cfg.symbol
                    )

                    # Get today's trades for ALL symbols
                    today_all_trades = trade_logger.get_today_trades(config_version="v3") if trade_logger else []
                    today_buys = sum(1 for t in today_all_trades if t.get("side") == "buy")
                    today_sells = sum(1 for t in today_all_trades if t.get("side") == "sell")
                    day_fees = sum(float(t.get("fee", 0)) for t in today_all_trades)
                    day_realized = sum(
                        float(t.get("realized_pnl", 0))
                        for t in today_all_trades if t.get("realized_pnl")
                    )

                    # Enrich positions with today's trade counts + grid info
                    for p in portfolio_summary.get("positions", []):
                        sym_trades = [t for t in today_all_trades if t.get("symbol") == p["symbol"]]
                        p["trades_today"] = len(sym_trades)
                        p["buys_today"] = sum(1 for t in sym_trades if t.get("side") == "buy")
                        p["sells_today"] = sum(1 for t in sym_trades if t.get("side") == "sell")
                        # Grid info only available for this bot's symbol
                        if p["symbol"] == cfg.symbol:
                            status = bot.get_status()
                            p["grid_range"] = status.get("range", "N/A")
                            p["grid_active_buys"] = status.get("levels", {}).get("active_buys", 0)
                            p["grid_active_sells"] = status.get("levels", {}).get("active_sells", 0)

                    # Calculate trading day number
                    day_number = 1
                    try:
                        first_trade_result = trade_logger.client.table("trades").select("created_at").order("created_at", desc=False).limit(1).execute()
                        if first_trade_result.data:
                            first_date_str = first_trade_result.data[0]["created_at"]
                            first_date = datetime.fromisoformat(first_date_str.replace("Z", "+00:00")).date()
                            day_number = (date.today() - first_date).days + 1
                    except Exception:
                        pass

                    # Fetch reserve totals for all symbols (fresh for daily report)
                    reserves = {}
                    if reserve_ledger:
                        for inst in GRID_INSTANCES:
                            try:
                                reserves[inst.symbol] = reserve_ledger.get_reserve_total(
                                    inst.symbol, force_refresh=True
                                )
                            except Exception:
                                reserves[inst.symbol] = 0.0

                    # Fetch TF state for inclusion in the daily reports.
                    # Same source-of-truth used by Haiku commentary + tf.html
                    # so private/public report numbers stay coherent with the
                    # web dashboard. Never raises — returns safe_default on
                    # any DB error.
                    tf_state = get_tf_state(trade_logger.client)

                    # Bundle all report data
                    report_data = {
                        **portfolio_summary,
                        "day_number": day_number,
                        "today_trades_count": len(today_all_trades),
                        "today_buys": today_buys,
                        "today_sells": today_sells,
                        "today_fees": day_fees,
                        "today_realized": day_realized,
                        "reserves": reserves,
                        "tf": tf_state,  # 47e: TF section in daily reports
                    }

                    # Atomic write: INSERT ON CONFLICT DO NOTHING.
                    # Only the first bot to insert wins (returns True). The second gets False → skip.
                    snapshot_written = False
                    if pnl_tracker:
                        snapshot_positions = []
                        for p in portfolio_summary.get("positions", []):
                            snapshot_positions.append({
                                "symbol": p["symbol"],
                                "holdings": p["holdings"],
                                "value": round(p["value"], 4),
                                "avg_buy_price": p["avg_buy_price"],
                                "unrealized_pnl": round(p["unrealized_pnl"], 4),
                                "unrealized_pnl_pct": round(p.get("unrealized_pnl_pct", 0), 2),
                            })
                        snapshot_written = pnl_tracker.record_daily(
                            total_value=portfolio_summary["total_value"],
                            cash_remaining=portfolio_summary["cash"],
                            holdings_value=portfolio_summary["holdings_value"],
                            initial_capital=portfolio_summary["initial_capital"],
                            total_pnl=portfolio_summary["total_pnl"],
                            realized_pnl_today=day_realized,
                            total_fees_today=day_fees,
                            trades_count=len(today_all_trades),
                            buys_count=today_buys,
                            sells_count=today_sells,
                            positions=snapshot_positions,
                        )

                    if not pnl_tracker or snapshot_written:
                        # Send reports only if we were first to write (or no tracker)
                        notifier.send_private_daily_report(report_data)
                        notifier.send_public_daily_report(report_data)
                        # Generate Haiku commentary; capture the text so we can
                        # echo it on the public channel as a CEO's-Log follow-up
                        # (same content that lands on bagholderai.lol/dashboard).
                        commentary_text = generate_daily_commentary(report_data, trade_logger.client)
                        if commentary_text:
                            notifier.send_public_commentary(commentary_text)
                        logger.info("Daily P&L snapshot saved + report sent via Telegram.")
                    else:
                        logger.info("Daily snapshot already written by another bot. Skipping report.")
                except Exception as e:
                    logger.error(f"Failed to send daily report: {e}")

            # Check daily P&L limit (hardcoded rule)
            if bot.state.daily_realized_pnl < HardcodedRules.STRATEGY_A_MIN_DAILY_PNL:
                logger.warning(
                    f"Daily P&L ${bot.state.daily_realized_pnl:.2f} below limit "
                    f"${HardcodedRules.STRATEGY_A_MIN_DAILY_PNL}. STOPPING."
                )
                break

            time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("\nStopping grid bot (Ctrl+C)...")
            break
        except Exception as e:
            _error_count += 1
            logger.error(f"Error in main loop: {e}")
            log_event(
                severity="error",
                category="error",
                event="error_loop",
                symbol=cfg.symbol,
                message=f"Main loop exception: {str(e)[:200]}",
                details={"error": str(e)[:500], "consecutive_errors": _error_count},
            )
            now_ts = time.time()
            if now_ts - _error_last_alert >= ERROR_ALERT_COOLDOWN:
                _error_last_alert = now_ts
                repeat_note = f"\nProssimo alert tra 30min se persiste." if _error_count > 1 else ""
                notifier.send_message(
                    f"🔴 <b>{cfg.symbol}: Errore nel loop</b>\n"
                    f"<code>{str(e)[:300]}</code>\n"
                    f"Errori consecutivi: {_error_count}"
                    f"{repeat_note}"
                )
            try:
                time.sleep(check_interval)  # wait and retry
            except KeyboardInterrupt:
                logger.info("\nStopping grid bot (Ctrl+C during error sleep)...")
                break

    # Per-bot farewell suppressed: the orchestrator's
    # "🛑 Orchestrator shutting down" covers the collective case,
    # and special events (liquidation, stop-loss, is_active=false)
    # still fire targeted notifications via their own paths.

    # Final status
    logger.info("\n" + "=" * 50)
    logger.info(f"FINAL STATUS (reason: {stop_reason})")
    _print_status(bot)
    logger.info("=" * 50)

    # 43a: structured event for bot stop with reason tag (manual,
    # is_active=false, liquidation, stop_loss, take_profit).
    log_event(
        severity="info",
        category="lifecycle",
        event="bot_stopped",
        symbol=cfg.symbol,
        message=f"Grid bot exited (reason: {stop_reason})",
        details={"stop_reason": stop_reason},
    )


def _build_cycle_summary(supabase, symbol: str, liquidation_trade_id: str | None) -> dict | None:
    """Build a per-cycle summary for the TF DEALLOCATE notification (39e Fix 3).

    A "cycle" is the window between the most recent ALLOCATE for this symbol
    in trend_decisions_log and NOW. Returns a dict with all fields needed to
    render the summary, or None if anything fails (caller falls back to the
    minimal LIQUIDATED message).

    liquidation_trade_id: id of the FORCED_LIQUIDATION sell row just written,
    used to split grid vs exit PnL and find the liquidation's skim row.
    """
    if supabase is None:
        return None
    try:
        last_alloc = (
            supabase.table("trend_decisions_log")
            .select("scan_timestamp,reason,config_written")
            .eq("symbol", symbol)
            .eq("action_taken", "ALLOCATE")
            .eq("is_shadow", False)
            .order("scan_timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not last_alloc.data:
            return None
        cycle_start = last_alloc.data[0]["scan_timestamp"]
        alloc_snapshot = last_alloc.data[0].get("config_written") or {}
        initial_capital = float(alloc_snapshot.get("capital_allocation") or 0)
        cycle_end_iso = datetime.now(timezone.utc).isoformat()

        trades_res = (
            supabase.table("trades")
            .select("id,side,amount,cost,realized_pnl,created_at,reason")
            .eq("symbol", symbol)
            .eq("config_version", "v3")
            .gte("created_at", cycle_start)
            .order("created_at", desc=False)
            .execute()
        )
        cycle_trades = trades_res.data or []
        buys = [t for t in cycle_trades if t.get("side") == "buy"]
        sells = [t for t in cycle_trades if t.get("side") == "sell"]

        realized_pnl_total = sum(float(t.get("realized_pnl") or 0) for t in sells)
        # Split: the liquidation row (matched by id) vs everything else.
        liquidation_pnl = 0.0
        grid_pnl = 0.0
        for t in sells:
            p = float(t.get("realized_pnl") or 0)
            if liquidation_trade_id and t.get("id") == liquidation_trade_id:
                liquidation_pnl += p
            else:
                grid_pnl += p

        sell_ids = [t["id"] for t in sells if t.get("id")]
        skim_total = 0.0
        if sell_ids:
            try:
                skim_res = (
                    supabase.table("reserve_ledger")
                    .select("amount,trade_id")
                    .in_("trade_id", sell_ids)
                    .execute()
                )
                skim_total = sum(float(r.get("amount") or 0) for r in (skim_res.data or []))
            except Exception as e:
                logger.warning(f"[{symbol}] cycle summary: skim query failed: {e}")

        return {
            "cycle_start": cycle_start,
            "cycle_end": cycle_end_iso,
            "initial_capital": initial_capital,
            "buys_count": len(buys),
            "sells_count": len(sells),
            "realized_pnl": realized_pnl_total,
            "grid_pnl": grid_pnl,
            "liquidation_pnl": liquidation_pnl,
            "skim_total": skim_total,
        }
    except Exception as e:
        logger.warning(f"[{symbol}] cycle summary build failed: {e}")
        return None


def _format_cycle_summary(s: dict) -> str:
    """Render a cycle summary dict into the Telegram message block (39e Fix 3)."""
    try:
        start = datetime.fromisoformat(s["cycle_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(s["cycle_end"].replace("Z", "+00:00"))
        duration = end - start
        total_minutes = int(duration.total_seconds() // 60)
        hours = total_minutes // 60
        mins = total_minutes % 60
        duration_str = f"{hours}h {mins}m" if hours else f"{mins}m"
        window = f"{start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({duration_str})"
    except Exception:
        window = "—"

    realized = s["realized_pnl"]
    grid = s["grid_pnl"]
    liq = s["liquidation_pnl"]
    skim = s["skim_total"]
    net = realized - skim
    alloc = s["initial_capital"]
    returned = alloc + realized

    def money(v: float) -> str:
        # Render as "+$1.21" / "-$1.21" (sign before $, standard accounting).
        return f"{'+' if v >= 0 else '-'}${abs(v):.2f}"

    def pct(v: float) -> str:
        return f"{'+' if v >= 0 else ''}{v:.1f}%"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"Cycle: {window}",
        f"Trades: {s['buys_count']} buys · {s['sells_count']} sells",
        f"Realized P&L: {money(realized)}",
    ]
    # Only show the split when both components are meaningful (avoid a
    # single-line breakdown that adds noise). grid_pnl and liquidation_pnl
    # are independent sums; we consider each "present" if its magnitude is
    # above a cent, to filter out rounding artefacts.
    if abs(grid) >= 0.01 and abs(liq) >= 0.01:
        lines.append(f"  ├─ Grid profits:     {money(grid)}")
        lines.append(f"  └─ Exit liquidation: {money(liq)}")
    lines.append(f"Skimmed to reserve: {money(skim)}")
    lines.append(f"Net to trading pool: {money(net)}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if alloc > 0:
        pct_val = (realized / alloc) * 100
        lines.append(
            f"Allocated: ${alloc:.2f} → Returned: ${returned:.2f} ({pct(pct_val)})"
        )
    return "\n".join(lines)


def _force_liquidate(bot, exchange, trade_logger, notifier, symbol: str,
                     reason: str = "TF rotation"):
    """Force-sell all holdings at market price.

    reason is used in the Telegram message + DB trade.reason so it's clear
    WHY the bot is being drained ("STOP-LOSS", "BEARISH EXIT", "TF rotation").

    Holdings below 1e-6 are treated as "already empty" — avoids firing a
    noisy Telegram with floating-point dust after a stop-loss has already
    liquidated (the meaningful PnL is in the individual sell notifications).

    39e: realized_pnl is computed as revenue − Σ(lot cost bases) − fees,
    not against a single avg_buy_price. The old formula was approximately
    equivalent when avg_buy_price was perfectly weighted — but after
    partial sells, dust rounding, or FIFO consumption the two diverge
    and the liquidation's PnL diverges from reality (today's API3 case:
    recorded +$0.18 vs actual −$1.21). Also routes skim on positive PnL,
    which the old flow bypassed unconditionally.
    """
    holdings = bot.state.holdings if bot.state else 0
    managed_by = getattr(bot, "managed_by", "grid")

    if holdings <= 1e-6:
        # 39f Section B: the stop-loss / take-profit paths already
        # liquidated every lot per-lot via _execute_percentage_sell. So
        # this branch is "no sell to execute, but still a real cycle
        # close". For TF bots emit the unified dealloc + cycle summary
        # Telegram so the CEO gets one consistent message regardless of
        # which exit trigger fired. For manual bots (or orchestrator
        # shutdown) keep the silent return — there's no TF cycle to
        # summarize.
        logger.info(f"[{symbol}] No holdings to liquidate (reason: {reason})")
        if managed_by in ("tf", "tf_grid") and trade_logger is not None:
            try:
                summary = _build_cycle_summary(trade_logger.client, symbol, None)
                if summary:
                    # The cycle summary block already reports Realized P&L,
                    # skim, net, and allocated→returned. The header just
                    # states WHICH trigger closed the cycle — no duplicate
                    # PnL line.
                    msg = (
                        f"🔴 <b>{symbol} DEALLOCATED</b> ({reason})\n"
                        f"Cycle closed — all lots exited via per-lot sells\n"
                        + _format_cycle_summary(summary)
                    )
                    notifier.send_message(msg)
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to emit cycle summary on empty-liquidation: {e}")
        return

    try:
        price = fetch_price(exchange, symbol)

        # 39e Fix 1: cost basis = sum of (lot.amount × lot.buy_price) over
        # the FIFO queue. Fallback to avg_buy_price × holdings only if the
        # queue is empty (shouldn't happen for a live TF bot, but keep the
        # safety net for fixed-mode or edge states).
        open_lots = getattr(bot, "_pct_open_positions", None) or []
        if open_lots:
            lot_cost_basis = sum(
                float(lot.get("amount", 0)) * float(lot.get("price", 0))
                for lot in open_lots
            )
            # Use queue amounts as authoritative — bot.state.holdings can
            # drift from queue sum by floating-point dust after repeated
            # ops. The sell volume is the queue sum so the PnL math stays
            # consistent with the cost basis.
            sell_amount = sum(float(lot.get("amount", 0)) for lot in open_lots)
        else:
            avg_buy = bot.state.avg_buy_price if bot.state and bot.state.avg_buy_price else 0
            lot_cost_basis = avg_buy * holdings
            sell_amount = holdings

        proceeds = price * sell_amount
        # Fees: same rate as GridBot._execute_percentage_sell — charged on
        # BOTH the buy legs (reconstructed from cost basis) and the sell.
        # 52a: paper-mode realized_pnl excludes fees — see grid_bot.py
        # _execute_sell comment for the full rationale.
        from bot.grid.grid_bot import GridBot
        fee_rate = GridBot.FEE_RATE
        sell_fee = proceeds * fee_rate
        buy_fees = lot_cost_basis * fee_rate
        realized_pnl = proceeds - lot_cost_basis

        trade_db_row: dict = {}

        if trade_logger:
            try:
                trade_db_row = trade_logger.log_trade(
                    symbol=symbol,
                    side="sell",
                    amount=sell_amount,
                    price=price,
                    cost=proceeds,
                    fee=sell_fee,
                    strategy="A",
                    brain="grid",
                    mode="paper",
                    reason=f"FORCED_LIQUIDATION ({reason})",
                    realized_pnl=realized_pnl,
                    config_version="v3",
                    managed_by=managed_by,
                ) or {}
            except Exception as e:
                logger.error(f"[{symbol}] Failed to log liquidation trade: {e}")

        # 39e Fix 2: skim 30% (skim_pct) to reserve_ledger when the
        # liquidation PnL is positive. Previously bypassed entirely —
        # today's API3 missed a $0.054 skim because of this path.
        skim_amount = 0.0
        reserve_total = 0.0
        skim_pct = float(getattr(bot, "skim_pct", 0) or 0)
        reserve_ledger = getattr(bot, "reserve_ledger", None)
        if realized_pnl > 0 and skim_pct > 0 and reserve_ledger is not None:
            skim_amount = realized_pnl * (skim_pct / 100)
            try:
                trade_id = trade_db_row.get("id") if isinstance(trade_db_row, dict) else None
                reserve_ledger.log_skim(symbol, skim_amount, trade_id=trade_id,
                                         managed_by=getattr(bot, "managed_by", None))
                reserve_total = reserve_ledger.get_reserve_total(symbol, force_refresh=True)
                logger.info(
                    f"[{symbol}] SKIM ${skim_amount:.4f} → reserve total ${reserve_total:.2f} (liquidation)"
                )
            except Exception as e:
                logger.warning(f"[{symbol}] Failed to log liquidation skim: {e}")
                skim_amount = 0.0  # don't claim a skim that failed

        # Reflect the sell in the in-memory bot state so get_status() and the
        # final stop notification don't report stale holdings. Mirrors the
        # state updates in GridBot._execute_sell.
        if bot.state:
            bot.state.total_received += proceeds
            bot.state.total_fees += sell_fee + buy_fees
            bot.state.realized_pnl += realized_pnl
            bot.state.daily_realized_pnl += realized_pnl
            bot.state.holdings = 0
            bot.state.avg_buy_price = 0
        # Empty the FIFO queue too so any downstream read (e.g. get_status
        # during the farewell log) sees a consistent zero state.
        if hasattr(bot, "_pct_open_positions"):
            bot._pct_open_positions = []

        pnl_emoji = "📈" if realized_pnl >= 0 else "📉"
        pnl_sign = "+" if realized_pnl >= 0 else ""
        msg = (
            f"🔴 <b>{symbol} LIQUIDATED</b> ({reason})\n"
            f"Sold {sell_amount:.6f} at ${price:.4f}\n"
            f"Proceeds: ${proceeds:.2f}\n"
            f"{pnl_emoji} PnL: {pnl_sign}${realized_pnl:.2f}"
        )
        if skim_amount > 0:
            msg += f"\n💰 Reserve: +${skim_amount:.2f} → total ${reserve_total:.2f}"

        # 39e Fix 3: append cycle summary for TF bots. Manual bots don't
        # have a TF "cycle" concept, so skip for them. The summary queries
        # trend_decisions_log for the last ALLOCATE and aggregates all
        # trades since then — including the liquidation sell we just wrote.
        if managed_by in ("tf", "tf_grid") and trade_logger is not None:
            try:
                liquidation_id = trade_db_row.get("id") if isinstance(trade_db_row, dict) else None
                summary = _build_cycle_summary(trade_logger.client, symbol, liquidation_id)
                if summary:
                    msg += "\n" + _format_cycle_summary(summary)
            except Exception as e:
                logger.warning(f"[{symbol}] cycle summary append failed: {e}")

        notifier.send_message(msg)
        logger.info(
            f"[{symbol}] Liquidation complete ({reason}): sold {sell_amount} at {price}, "
            f"PnL: ${realized_pnl:.2f}, skim: ${skim_amount:.4f}"
        )
    except Exception as e:
        logger.error(f"[{symbol}] Liquidation FAILED: {e}")
        notifier.send_message(
            f"🚨 <b>{symbol} LIQUIDATION FAILED</b>\n"
            f"<code>{str(e)[:300]}</code>\n"
            f"Manual intervention needed!"
        )


def _build_portfolio_summary(trade_logger, exchange, current_bot, current_symbol: str) -> dict:
    """
    Consolidated Grid portfolio summary.

    Single source of truth: delegates to commentary.get_grid_state, which
    runs the FIFO replay identical to the public dashboard. The legacy
    formula (initial − bought + received) ignored skim and used the biased
    realized_pnl column from the DB, producing report numbers that drifted
    from the dashboard by up to $14.

    The trade_logger / exchange / current_bot args are kept for backward
    compatibility with callers — they're no longer used here, but the
    signature stays stable so grid_runner's main loop is untouched.
    """
    from commentary import get_grid_state
    state = get_grid_state(trade_logger.client)
    # Telegram renderer expects the same keys the legacy summary returned.
    # get_grid_state already matches them (total_value, cash, holdings_value,
    # initial_capital, total_pnl, positions) and adds extras (realized_total,
    # unrealized_total, fees_total, skim_total) that the renderer can use.
    return state


def _print_status(bot: GridBot):
    """Print current bot status."""
    status = bot.get_status()
    if status.get("status") == "not_initialized":
        logger.info("Bot not initialized.")
        return

    logger.info(f"--- {status['symbol']} Grid Status ---")
    logger.info(f"  Price:        {fmt_price(status['last_price'])}")
    logger.info(f"  Range:        {status['range']}")
    base = status['symbol'].split("/")[0] if "/" in status['symbol'] else status['symbol']
    logger.info(f"  Holdings:     {status['holdings']:.6f} {base}")
    logger.info(f"  Avg buy:      {fmt_price(status['avg_buy_price'])}")
    logger.info(f"  Capital:      ${status['capital']:.2f} total | ${status['available_capital']:.2f} available")
    logger.info(f"  Invested:     ${status['invested']:,.2f}")
    cost_basis = status['received'] - status.get('realized_pnl', 0)
    logger.info(f"  Received:     ${status['received']:,.2f} (cost basis: ${cost_basis:.2f} + profit: ${status.get('realized_pnl', 0):.4f})")
    logger.info(f"  Fees:         ${status['fees']:.4f}")
    logger.info(f"  Realized P&L: ${status['realized_pnl']:.4f}")
    logger.info(f"  Unrealz P&L:  ${status['unrealized_pnl']:.4f}")
    logger.info(f"  Trades today: {status['trades_today']}")
    logger.info(f"  Levels:       {status['levels']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BagHolderAI Grid Bot")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading pair (e.g. SOL/USDT)")
    parser.add_argument("--once", action="store_true", help="Run one cycle only")
    parser.add_argument("--dry-run", action="store_true", help="Don't log to database")
    args = parser.parse_args()

    run_grid_bot(symbol=args.symbol, once=args.once, dry_run=args.dry_run)
