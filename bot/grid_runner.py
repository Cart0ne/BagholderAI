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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.runner")

# Imports from project
from config.settings import (
    TradingMode, HardcodedRules, GridConfig, ExchangeConfig
)
from bot.exchange import create_exchange
from bot.strategies.grid_bot import GridBot
from db.client import TradeLogger, PortfolioManager, DailyPnLTracker


# === Configuration ===
SYMBOL = "BTC/USDT"
STRATEGY = "A"

# Capital for grid: Strategy A gets 80% of operational capital
# Operational = MAX_CAPITAL * 90% (10% reserve)
# For paper trading, we use a smaller test amount
GRID_CAPITAL = 100.0  # Start small in paper trading

NUM_LEVELS = 10
RANGE_PERCENT = 0.04  # 4% range — tight enough for frequent trades

# How often to check price (seconds)
CHECK_INTERVAL = 30  # Every 30 seconds in paper trading


def fetch_price(exchange, symbol: str) -> float:
    """Fetch current price from exchange."""
    ticker = exchange.fetch_ticker(symbol)
    return ticker["last"]


def run_grid_bot(once: bool = False, dry_run: bool = False):
    """Main loop."""
    
    logger.info("=" * 50)
    logger.info("BagHolderAI Grid Bot starting...")
    logger.info(f"Mode: {'PAPER' if TradingMode.is_paper() else 'LIVE'}")
    logger.info(f"Symbol: {SYMBOL}")
    logger.info(f"Capital: ${GRID_CAPITAL}")
    logger.info(f"Levels: {NUM_LEVELS}")
    logger.info(f"Range: {RANGE_PERCENT * 100}%")
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
        logger.info("DRY RUN — trades will NOT be logged to database")
    else:
        trade_logger = TradeLogger()
        portfolio_manager = PortfolioManager()
        pnl_tracker = DailyPnLTracker()
 
    # Initialize Telegram
    notifier = SyncTelegramNotifier()
 
    # Create grid bot
    bot = GridBot(
        exchange=exchange,
        trade_logger=trade_logger,
        portfolio_manager=portfolio_manager,
        pnl_tracker=pnl_tracker,
        symbol=SYMBOL,
        strategy=STRATEGY,
        capital=GRID_CAPITAL,
        num_levels=NUM_LEVELS,
        range_percent=RANGE_PERCENT,
        mode="paper",
    )
    
    # Fetch initial price and setup grid
    try:
        price = fetch_price(exchange, SYMBOL)
        logger.info(f"Current {SYMBOL} price: ${price:,.2f}")
    except Exception as e:
        logger.error(f"Failed to fetch price: {e}")
        return
    
    bot.setup_grid(price)
    
    # Print initial grid
    logger.info("Grid levels:")
    for level in bot.state.levels:
        marker = "BUY ↓" if level.side == "buy" else "SELL ↑"
        amount_str = f" ({level.order_amount:.6f} BTC)" if level.order_amount > 0 else ""
        logger.info(f"  ${level.price:>10,.2f}  {marker}{amount_str}")
    logger.info(f"  Current price: ${price:,.2f}")
 
    notifier.send_bot_started(bot.get_status())

    if once:
        logger.info("Single cycle mode — checking once and exiting.")
        trades = bot.check_price_and_execute(price)
        _print_status(bot)
        return
    
    # Main loop
    logger.info(f"Starting main loop (checking every {CHECK_INTERVAL}s)...")
    logger.info("Press Ctrl+C to stop.\n")
    
    daily_report_sent = None  # Track which date we sent the report
    REPORT_HOUR = 21  # Send daily report at 21:00

    cycle = 0
    while True:
        try:
            cycle += 1
            price = fetch_price(exchange, SYMBOL)
            
            # Check if grid needs reset (price moved too far)
            if bot.should_reset_grid(price):
                logger.info(f"Price ${price:,.2f} outside grid range. Resetting grid...")
                bot.setup_grid(price)
            
            # Run grid logic
            trades = bot.check_price_and_execute(price)
            
            # Log trades
            if trades:
                for t in trades:
                    emoji = "🟢" if t["side"] == "buy" else "🔴"
                    logger.info(
                        f"{emoji} {t['side'].upper()} {t['amount']:.6f} "
                        f"@ ${t['price']:,.2f} | {t['reason']}"
                    )
                    notifier.send_trade_alert(t)

            # Periodic status update (every 10 cycles = ~5 min)
            if cycle % 10 == 0:
                _print_status(bot)
            
            # Daily report at 21:00
            now = datetime.now()
            if now.hour >= REPORT_HOUR and daily_report_sent != date.today():
                try:
                    today_trades = trade_logger.get_today_trades() if trade_logger else []
                    notifier.send_daily_report(today_trades, bot.get_status())
                    daily_report_sent = date.today()
                    logger.info("Daily report sent via Telegram.")
                except Exception as e:
                    logger.error(f"Failed to send daily report: {e}")
            
            # Check daily P&L limit (hardcoded rule)
            if bot.state.realized_pnl < HardcodedRules.STRATEGY_A_MIN_DAILY_PNL:
                logger.warning(
                    f"Daily P&L ${bot.state.realized_pnl:.2f} below limit "
                    f"${HardcodedRules.STRATEGY_A_MIN_DAILY_PNL}. STOPPING."
                )
                break
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("\nStopping grid bot (Ctrl+C)...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)  # wait and retry
    
    notifier.send_bot_stopped(bot.get_status(), reason="manual")
   
    # Final status
    logger.info("\n" + "=" * 50)
    logger.info("FINAL STATUS")
    _print_status(bot)
    logger.info("=" * 50)


def _print_status(bot: GridBot):
    """Print current bot status."""
    status = bot.get_status()
    if status.get("status") == "not_initialized":
        logger.info("Bot not initialized.")
        return
    
    logger.info(f"--- {status['symbol']} Grid Status ---")
    logger.info(f"  Price:        ${status['last_price']:,.2f}")
    logger.info(f"  Range:        {status['range']}")
    logger.info(f"  Holdings:     {status['holdings']:.6f} BTC")
    logger.info(f"  Avg buy:      ${status['avg_buy_price']:,.2f}")
    logger.info(f"  Invested:     ${status['invested']:,.2f}")
    logger.info(f"  Received:     ${status['received']:,.2f}")
    logger.info(f"  Fees:         ${status['fees']:.4f}")
    logger.info(f"  Realized P&L: ${status['realized_pnl']:.4f}")
    logger.info(f"  Unrealz P&L:  ${status['unrealized_pnl']:.4f}")
    logger.info(f"  Trades today: {status['trades_today']}")
    logger.info(f"  Levels:       {status['levels']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BagHolderAI Grid Bot")
    parser.add_argument("--once", action="store_true", help="Run one cycle only")
    parser.add_argument("--dry-run", action="store_true", help="Don't log to database")
    args = parser.parse_args()
    
    run_grid_bot(once=args.once, dry_run=args.dry_run)
