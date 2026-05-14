"""Runtime state mirror for public dashboard widgets.

Brief 74b (S74b 2026-05-12): the bot mirrors its in-memory state to the
`bot_runtime_state` table every tick. Dashboard widgets that used to
derive these values from `trades` / `bot_events_log` (and drifted, see
brief 74b Bug 1 & 2) read this table directly now.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("bagholderai.runner")


def _upsert_runtime_state(trade_logger, bot, symbol: str) -> None:
    """UPSERT the bot's canonical in-memory state into bot_runtime_state.

    Called after each `check_price_and_execute` tick. Best-effort: any
    Supabase blip is swallowed so it can never break the trade loop.
    """
    try:
        managed = getattr(bot, "managed_holdings", None)
        phantom = getattr(bot, "_phantom_holdings", 0.0) or 0.0
        last_recal = getattr(bot, "_last_trade_time", None)
        payload = {
            "symbol": symbol,
            "buy_reference_price": float(bot._pct_last_buy_price or 0) or None,
            "last_sell_price": float(bot._last_sell_price or 0) or None,
            "stop_buy_active": bool(getattr(bot, "_stop_buy_active", False)),
            "phantom_holdings": float(phantom),
            "managed_holdings": float(managed) if managed is not None else None,
            "last_recalibrate_at": last_recal.isoformat() if last_recal else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        trade_logger.client.table("bot_runtime_state") \
            .upsert(payload, on_conflict="symbol").execute()
    except Exception as e:
        logger.debug(f"[{symbol}] bot_runtime_state upsert failed: {e}")
