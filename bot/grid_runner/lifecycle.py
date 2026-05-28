"""Bot lifecycle helpers: exchange interaction, status logging, portfolio summary.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
Bootstrap (config loading, GridBot construction, exchange filters, replay)
is kept inline in `__init__.run_grid_bot` for now — splitting it would
require exposing ~10 locals across modules without reducing complexity.
"""

import logging
import time
from typing import TYPE_CHECKING, Optional

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


def fetch_price_with_spike_guard(
    exchange,
    symbol: str,
    last_known_price: float,
    threshold_pct: float = 4.0,
    confirm_pct: float = 50.0,
    pause_seconds: float = 5.0,
) -> Optional[float]:
    """Brief fix_slippage_AB (S90, 2026-05-28): doppio-fetch con conferma.

    Protegge dal caso in cui `ticker["last"]` di Binance restituisca un valore
    di spike single-tick (orderbook sottile testnet, flash crash mainnet) che
    `check_price_and_execute` userebbe come prezzo "vero" e su cui spara un
    market order, prendendo slippage enorme tra check e fill.

    Logica:
      1. tick_1 = fetch_price(...)
      2. Se last_known_price <= 0 (primissimo tick post-restart) → return tick_1
         senza guard (niente baseline contro cui confrontare).
      3. delta_pct = |tick_1 − last_known_price| / last_known_price × 100.
      4. delta_pct < threshold_pct (default 4%) → return tick_1 immediato.
      5. Altrimenti il movimento è "sospetto": pausa pause_seconds, ri-fetch
         tick_2, verifica che il movimento si conferma almeno per confirm_pct
         (default 50%) nello stesso verso. Se sì → rally/crash reale, return
         tick_2. Se no → spike → return None (caller skippa il ciclo).

    Riferimento: investigations/slippage_btc_20260527.md
    """
    tick_1 = fetch_price(exchange, symbol)

    # Primissimo tick post-restart: state.last_price ancora 0, niente baseline.
    if last_known_price <= 0:
        return tick_1

    movement_1 = tick_1 - last_known_price
    delta_pct = abs(movement_1) / last_known_price * 100

    if delta_pct < threshold_pct:
        return tick_1

    logger.warning(
        f"[{symbol}] Spike guard armed: tick_1 {fmt_price(tick_1)} vs "
        f"last_known {fmt_price(last_known_price)} = {delta_pct:+.2f}% "
        f"(threshold {threshold_pct}%). Pausing {pause_seconds}s for confirmation..."
    )
    time.sleep(pause_seconds)
    tick_2 = fetch_price(exchange, symbol)

    movement_2 = tick_2 - last_known_price
    # Conferma: stesso verso (sign match) E ampiezza >= confirm_pct% del movimento iniziale.
    same_sign = (movement_1 >= 0) == (movement_2 >= 0)
    confirmed_ratio = (abs(movement_2) / abs(movement_1) * 100) if movement_1 != 0 else 0.0

    if same_sign and confirmed_ratio >= confirm_pct:
        logger.warning(
            f"[{symbol}] Spike guard CONFIRMED: tick_2 {fmt_price(tick_2)} "
            f"confirms {confirmed_ratio:.0f}% of move (≥ {confirm_pct}%). "
            f"Real rally/crash, proceeding with tick_2."
        )
        return tick_2

    logger.warning(
        f"[{symbol}] Spike guard REJECTED: tick_2 {fmt_price(tick_2)} only "
        f"confirms {confirmed_ratio:.0f}% of move (< {confirm_pct}%, "
        f"same_sign={same_sign}). Skipping cycle."
    )
    return None


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
