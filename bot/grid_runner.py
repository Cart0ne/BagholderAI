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
import time
import logging
import argparse
from datetime import datetime, date
from utils.telegram_notifier import SyncTelegramNotifier
from utils.formatting import fmt_price
from commentary import generate_daily_commentary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.runner")

# Imports from project
from config.settings import (
    TradingMode, HardcodedRules, GridConfig, ExchangeConfig, get_grid_config,
    GRID_INSTANCES,
)
from config.supabase_config import SupabaseConfigReader
from bot.exchange import create_exchange
from bot.strategies.grid_bot import GridBot
from db.client import TradeLogger, PortfolioManager, DailyPnLTracker, ReserveLedger


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
    if "is_active" in sb_cfg:
        bot.is_active = bool(sb_cfg["is_active"])


def run_grid_bot(symbol: str = "BTC/USDT", once: bool = False, dry_run: bool = False):
    """Main loop."""

    # Load local config for this symbol (fallback / initial values)
    cfg = get_grid_config(symbol)

    # --- Read config from Supabase (Task 2) ---
    config_reader = SupabaseConfigReader(own_symbol=cfg.symbol)
    try:
        config_reader.load_initial()
        sb_cfg = config_reader.get_config(symbol)
        if sb_cfg:
            # Override local config with Supabase values
            if sb_cfg.get("capital_allocation") is not None:
                cfg.capital = float(sb_cfg["capital_allocation"])
            if sb_cfg.get("grid_levels") is not None:
                cfg.num_levels = int(sb_cfg["grid_levels"])
            if sb_cfg.get("capital_per_trade") is not None:
                cfg.capital_per_trade = float(sb_cfg["capital_per_trade"])
            if sb_cfg.get("buy_pct") is not None:
                cfg.buy_pct = float(sb_cfg["buy_pct"])
            if sb_cfg.get("sell_pct") is not None:
                cfg.sell_pct = float(sb_cfg["sell_pct"])
            if sb_cfg.get("grid_mode") is not None:
                cfg.grid_mode = sb_cfg["grid_mode"]
            gl = sb_cfg.get("grid_lower")
            gu = sb_cfg.get("grid_upper")
            if gl is not None and gu is not None:
                gl, gu = float(gl), float(gu)
                if gu > gl > 0:
                    center = (gl + gu) / 2
                    cfg.grid_range_pct = (gu - gl) / center
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

    # Safety check
    if TradingMode.is_live():
        logger.error("LIVE TRADING NOT IMPLEMENTED YET. Use paper mode.")
        return

    if not ExchangeConfig.API_KEY:
        logger.error("No API key configured. Set up config/.env first.")
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
        mode="paper",
        buy_cooldown_seconds=cfg.buy_cooldown_seconds,
        min_profit_pct=cfg.min_profit_pct,
        grid_mode=cfg.grid_mode,
        buy_pct=cfg.buy_pct,
        sell_pct=cfg.sell_pct,
        capital_per_trade=cfg.capital_per_trade,
        reserve_ledger=reserve_ledger,
        skim_pct=cfg.skim_pct,
    )

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
        open_lots = bot._pct_open_positions
        if open_lots:
            for i, lot in enumerate(open_lots, 1):
                sell_trigger = lot["price"] * (1 + bot.sell_pct / 100)
                logger.info(f"  Sell lot {i}:     {fmt_price(sell_trigger)}  (bought {fmt_price(lot['price'])} +{bot.sell_pct}%)")
        else:
            logger.info(f"  Open lots:      none")
        logger.info(f"  Current price:  {fmt_price(price)}")
    else:
        logger.info("Grid levels (fixed mode):")
        for level in bot.state.levels:
            marker = "BUY ↓" if level.side == "buy" else "SELL ↑"
            base = cfg.symbol.split("/")[0] if "/" in cfg.symbol else cfg.symbol
            amount_str = f" ({level.order_amount:.6f} {base})" if level.order_amount > 0 else ""
            logger.info(f"  {fmt_price(level.price):>14}  {marker}{amount_str}")
        logger.info(f"  Current price:  {fmt_price(price)}")

    notifier.send_bot_started(bot.get_status())

    if once:
        logger.info("Single cycle mode — checking once and exiting.")
        trades = bot.check_price_and_execute(price)
        _print_status(bot)
        return

    # Main loop — Task 6: use per-asset check interval from config
    check_interval = cfg.check_interval_seconds
    logger.info(f"Starting main loop (checking every {check_interval}s)...")
    logger.info("Press Ctrl+C to stop.\n")

    daily_report_sent = None  # Track which date we sent the report
    REPORT_HOUR = 20  # Send daily report at 20:00

    # Proactive alert state
    _capital_exhausted = False
    _error_count = 0
    _error_last_alert = 0.0
    ERROR_ALERT_COOLDOWN = 30 * 60  # 30 minutes between repeated error alerts
    # Skip-notification dedup: symbol -> (level_price_rounded, cash_rounded)
    _last_skip_notification: dict = {}
    # Sell-skip dedup: symbol -> (level_price_rounded, holdings_rounded)
    _last_sell_skip_notification: dict = {}

    cycle = 0
    while True:
        try:
            cycle += 1

            # Sync dynamic config fields from Supabase reader to bot
            _sync_config_to_bot(config_reader, bot, cfg.symbol)

            # Graceful shutdown if is_active=false in Supabase
            if not bot.is_active:
                logger.info(f"[{cfg.symbol}] is_active=false — shutting down gracefully")
                notifier.send_message(
                    f"🛑 <b>{cfg.symbol} grid bot stopped</b> (is_active=false)"
                )
                break

            price = fetch_price(exchange, cfg.symbol)

            # Check if grid needs reset (price moved too far)
            if bot.should_reset_grid(price):
                old_range = bot.get_status().get("range", "N/A")
                logger.info(f"Price {fmt_price(price)} outside grid range. Resetting grid...")
                bot.setup_grid(price)
                new_range = bot.get_status().get("range", "N/A")
                notifier.send_grid_reset(old_range, new_range, price)

            # Run grid logic
            trades = bot.check_price_and_execute(price)

            # Idle re-entry alert: send BEFORE trade alerts so context arrives first
            for alert in bot.idle_reentry_alerts:
                base = alert["symbol"].split("/")[0] if "/" in alert["symbol"] else alert["symbol"]
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
            elif available >= HardcodedRules.MIN_LAST_SHOT_USD and _capital_exhausted:
                _capital_exhausted = False
                notifier.send_message(
                    f"✅ <b>{cfg.symbol}: Capitale ripristinato</b>\n"
                    f"Cash disponibile: ${available:.2f}\n"
                    f"Il bot può tornare a comprare."
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
                        generate_daily_commentary(report_data, trade_logger.client)
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

    notifier.send_bot_stopped(bot.get_status(), reason="manual")

    # Final status
    logger.info("\n" + "=" * 50)
    logger.info("FINAL STATUS")
    _print_status(bot)
    logger.info("=" * 50)


def _build_portfolio_summary(trade_logger, exchange, current_bot, current_symbol: str) -> dict:
    """
    Build a consolidated portfolio summary across all grid instances.
    Queries DB positions + live prices to calculate total portfolio value.

    FIX Session 12:
    - initial_capital uses MAX_CAPITAL ($500), not sum of grid allocations ($180)
    - Cash calculated globally, not per-instance (which clamped to $0)
    """
    initial_capital = HardcodedRules.MAX_CAPITAL

    total_invested_all = 0.0
    total_received_all = 0.0
    holdings_value = 0.0
    positions = []

    for inst in GRID_INSTANCES:
        pos = trade_logger.get_open_position(inst.symbol, config_version="v3")
        h = pos["holdings"]
        total_invested_all += pos["total_invested"]
        total_received_all += pos["total_received"]

        if h > 0:
            # Use current bot's price if same symbol, otherwise fetch
            if inst.symbol == current_symbol:
                live_price = current_bot.state.last_price if current_bot.state else 0
            else:
                try:
                    ticker = exchange.fetch_ticker(inst.symbol)
                    live_price = ticker["last"]
                except Exception:
                    live_price = pos["avg_buy_price"]  # fallback

            value = h * live_price
            unrealized = (live_price - pos["avg_buy_price"]) * h if pos["avg_buy_price"] > 0 else 0
            unrealized_pct = ((live_price / pos["avg_buy_price"]) - 1) * 100 if pos["avg_buy_price"] > 0 else 0
            holdings_value += value
            positions.append({
                "symbol": inst.symbol,
                "holdings": h,
                "value": value,
                "avg_buy_price": pos["avg_buy_price"],
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
                "realized_pnl": pos["realized_pnl"],
                "live_price": live_price,
            })

    # Global cash: what's left from the real initial investment
    cash = max(0.0, initial_capital - total_invested_all + total_received_all)
    total_value = cash + holdings_value
    total_pnl = total_value - initial_capital

    return {
        "total_value": total_value,
        "cash": cash,
        "holdings_value": holdings_value,
        "initial_capital": initial_capital,
        "total_pnl": total_pnl,
        "positions": positions,
    }


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
