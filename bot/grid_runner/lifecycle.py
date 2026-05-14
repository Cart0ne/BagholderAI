"""Bot lifecycle helpers: exchange interaction, status logging, portfolio summary.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
Bootstrap (config loading, GridBot construction, exchange filters, replay)
is kept inline in `__init__.run_grid_bot` for now — splitting it would
require exposing ~10 locals across modules without reducing complexity.
"""

import logging
import time
from typing import TYPE_CHECKING

from utils.formatting import fmt_price

if TYPE_CHECKING:
    from bot.grid.grid_bot import GridBot

logger = logging.getLogger("bagholderai.runner")


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


def _print_status(bot: "GridBot"):
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
    # Brief s70 FASE 2: niente più state.levels (avg-cost mode).
    if status.get('buy_trigger') and status.get('sell_trigger'):
        logger.info(
            f"  Triggers:     buy ↓ {fmt_price(status['buy_trigger'])} / "
            f"sell ↑ {fmt_price(status['sell_trigger'])}"
        )
