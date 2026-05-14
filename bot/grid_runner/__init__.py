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
from datetime import datetime, date, timezone
from utils.formatting import fmt_price
# `SyncTelegramNotifier` is imported lazily inside run_grid_bot() so that
# tests can `from bot.grid_runner.idle_alerts import send_idle_alerts`
# without paying the python-telegram-bot dependency cost (and breaking on
# environments where the library isn't installed).


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
    TradingMode, HardcodedRules, ExchangeConfig, get_grid_config,
    GRID_INSTANCES,
)
from config.supabase_config import SupabaseConfigReader
from bot.exchange import create_exchange
from bot.grid.grid_bot import GridBot
from db.client import TradeLogger, PortfolioManager, DailyPnLTracker, ReserveLedger
from db.event_logger import log_event
from db.snapshot_writer import write_state_snapshot


STRATEGY = "A"


from bot.grid_runner.runtime_state import _upsert_runtime_state
from bot.grid_runner.config_sync import _sync_config_to_bot
from bot.grid_runner.idle_alerts import send_idle_alerts
from bot.grid_runner.lifecycle import fetch_price, _build_portfolio_summary, _print_status
from bot.grid_runner.liquidation import (
    _deactivate_if_fully_liquidated,
    _consume_initial_lots,
    _force_liquidate,
)
from bot.grid_runner.daily_report import maybe_send_daily_report


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
            # Brief s70 FASE 2: tutte le colonne fixed-mode (grid_mode +
            # grid_levels/lower/upper + reserve_floor_pct) DROPPED dal DB.
            # Avg-cost only.
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
    logger.info(f"Capital per trade: ${cfg.capital_per_trade}")
    logger.info(f"Buy pct: {cfg.buy_pct}% / Sell pct: {cfg.sell_pct}%")
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
    from utils.telegram_notifier import SyncTelegramNotifier  # lazy import (see top-of-file note)
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

    # 75b (S76 2026-05-14): per-coin unlock timer for the stop-buy guard.
    # 0 = disabled (only profitable sell resets the flag). Hot-reloaded via
    # config_sync; CHECK constraint guarantees 0 ≤ unlock ≤ 168.
    stop_buy_unlock_hours = 0.0
    try:
        if sb_cfg and sb_cfg.get("stop_buy_unlock_hours") is not None:
            stop_buy_unlock_hours = float(sb_cfg["stop_buy_unlock_hours"])
    except Exception as e:
        logger.warning(f"Could not read bot_config.stop_buy_unlock_hours for {cfg.symbol}: {e}. Defaulting to 0.")

    # 74b (S74b 2026-05-12): per-coin dead-zone recalibrate threshold
    # (replaces the DEAD_ZONE_HOURS=4.0 hardcoded constant in grid_bot.py).
    # CHECK constraint guarantees > 0 ≤ 168; safe fallback to 4.0 on read error.
    dead_zone_hours = 4.0
    try:
        if sb_cfg and sb_cfg.get("dead_zone_hours") is not None:
            dead_zone_hours = float(sb_cfg["dead_zone_hours"])
    except Exception as e:
        logger.warning(f"Could not read bot_config.dead_zone_hours for {cfg.symbol}: {e}. Defaulting to 4.0.")

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
        # 67a: read the trading mode dynamically. Hardcoding "paper" caused
        # all live testnet trades to be tagged as paper in the DB, breaking
        # downstream filters (dashboards, reconciliation, audit). The CHECK
        # constraint on trades.mode accepts only 'paper' | 'live', so any
        # live mode (testnet OR mainnet) maps to 'live' here.
        mode=TradingMode.MODE,
        buy_cooldown_seconds=cfg.buy_cooldown_seconds,
        min_profit_pct=cfg.min_profit_pct,
        buy_pct=cfg.buy_pct,
        sell_pct=cfg.sell_pct,
        capital_per_trade=cfg.capital_per_trade,
        reserve_ledger=reserve_ledger,
        skim_pct=cfg.skim_pct,
        tf_stop_loss_pct=tf_stop_loss_pct,
        stop_buy_drawdown_pct=stop_buy_drawdown_pct,
        stop_buy_unlock_hours=stop_buy_unlock_hours,  # 75b
        dead_zone_hours=dead_zone_hours,
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
    # Brief s70 FASE 2: avg-cost only. Boot replay popola state.holdings
    # + state.avg_buy_price + _pct_last_buy_price + _last_trade_time.
    bot.init_avg_cost_state_from_db()

    # Print initial grid
    logger.info("Grid triggers (avg-cost mode):")
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

            # Brief 74b (S74b 2026-05-12): mirror in-memory state for the
            # public dashboard widgets. Best-effort, never fails the loop.
            _upsert_runtime_state(trade_logger, bot, cfg.symbol)

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

            # Idle re-entry / recalibrate alert: send BEFORE trade alerts so context arrives first.
            # S76 audit: suppress when stop-buy is active (structural block → idle is noise).
            send_idle_alerts(notifier, bot.idle_reentry_alerts,
                             stop_buy_active=getattr(bot, "_stop_buy_active", False))

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
                        f"💵 Cash {base}: ${skip['cash_before']:.2f} → Need ${skip['cost']:.2f} ❌ SKIPPED\n"
                        f"Reason: insufficient capital"
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
                    f"Reason: insufficient holdings"
                )
                notifier.send_message(msg)

            # Alert: capital exhausted / recovered
            available = bot.get_status()["available_capital"]
            if available < HardcodedRules.MIN_LAST_SHOT_USD and not _capital_exhausted:
                _capital_exhausted = True
                notifier.send_message(
                    f"⚠️ <b>{cfg.symbol}: Capital exhausted</b>\n"
                    f"Available cash: ${available:.2f}\n"
                    f"All positions deployed.\n"
                    f"Bot waits for a sell to resume buying."
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
                    f"✅ <b>{cfg.symbol}: Capital restored</b>\n"
                    f"Available cash: ${available:.2f}\n"
                    f"Bot can resume buying."
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
                    f"✅ <b>{cfg.symbol}: Loop restored</b>\n"
                    f"Consecutive errors resolved: {_error_count}\n"
                    f"Bot operational."
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
            daily_report_sent = maybe_send_daily_report(
                bot, cfg, trade_logger, exchange, reserve_ledger, pnl_tracker,
                notifier, daily_report_sent, REPORT_HOUR, _build_portfolio_summary,
            )

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
                repeat_note = f"\nNext alert in 30min if persistent." if _error_count > 1 else ""
                notifier.send_message(
                    f"🔴 <b>{cfg.symbol}: Loop error</b>\n"
                    f"<code>{str(e)[:300]}</code>\n"
                    f"Consecutive errors: {_error_count}"
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


# CLI entrypoint moved to bot/grid_runner/__main__.py (refactor S76).
# The orchestrator spawns this module via `python -m bot.grid_runner`,
# which Python routes to __main__.py.
