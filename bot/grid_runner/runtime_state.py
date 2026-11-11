"""Runtime state mirror for public dashboard widgets.

Brief 74b (S74b 2026-05-12): the bot mirrors its in-memory state to the
`bot_runtime_state` table every tick. Dashboard widgets that used to
derive these values from `trades` / `bot_events_log` (and drifted, see
brief 74b Bug 1 & 2) read this table directly now.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
"""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("bagholderai.runner")

# S134 (alleggerire Supabase): the mirror used to be UPSERTed every tick
# (~2.700 writes/day for 2 grids) even when nothing had changed. Now: write
# when the content changes, otherwise one heartbeat every 10 min so
# `updated_at` stays fresh. After a failed write, retry at most every 10 min
# (a call during a Supabase outage blocks the loop for minutes).
RUNTIME_STATE_HEARTBEAT_S = 600
_LAST_WRITE: dict = {}  # symbol -> {"sig": tuple | None, "ts": float}


def _signature(payload: dict) -> tuple:
    return tuple(
        (k, round(v, 8) if isinstance(v, float) else v)
        for k, v in sorted(payload.items()) if k != "updated_at"
    )


def _upsert_runtime_state(trade_logger, bot, symbol: str) -> None:
    """UPSERT the bot's canonical in-memory state into bot_runtime_state.

    Called after each `check_price_and_execute` tick. Best-effort: any
    Supabase blip is swallowed so it can never break the trade loop.

    Brief 75b (S76, 2026-05-14): adds `stop_buy_activated_at` so the
    /grid widget can show a countdown when the unlock timer is armed.
    """
    try:
        managed = getattr(bot, "managed_holdings", None)
        phantom = getattr(bot, "_phantom_holdings", 0.0) or 0.0
        last_recal = getattr(bot, "_last_trade_time", None)
        sb_activated = getattr(bot, "_stop_buy_activated_at", None)
        sb_baseline = float(getattr(bot, "_stop_buy_baseline_price", 0.0) or 0.0)
        payload = {
            "symbol": symbol,
            "buy_reference_price": float(bot._pct_last_buy_price or 0) or None,
            "last_sell_price": float(bot._last_sell_price or 0) or None,
            "stop_buy_active": bool(getattr(bot, "_stop_buy_active", False)),
            "stop_buy_activated_at": sb_activated.isoformat() if sb_activated else None,
            "stop_buy_baseline_price": sb_baseline if sb_baseline > 0 else None,  # 75c
            # S99b-b Parte B: mirror the Adaptive Sell Penalty so the /grid
            # dashboard can fold it into NEXT SELL IF (the bot trades on
            # sell_pct + _sell_pct_penalty; without this the widget understates
            # the real trigger whenever a penalty is armed — e.g. BONK).
            "sell_pct_penalty": float(getattr(bot, "_sell_pct_penalty", 0.0) or 0.0) or None,
            "phantom_holdings": float(phantom),
            "managed_holdings": float(managed) if managed is not None else None,
            "last_recalibrate_at": last_recal.isoformat() if last_recal else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        sig = _signature(payload)
        now = time.time()
        last = _LAST_WRITE.get(symbol)
        if last is not None and (now - last["ts"]) < RUNTIME_STATE_HEARTBEAT_S:
            if last["sig"] is None or last["sig"] == sig:
                return  # unchanged, or backing off after a failed write
        _LAST_WRITE[symbol] = {"sig": None, "ts": now}
        trade_logger.client.table("bot_runtime_state") \
            .upsert(payload, on_conflict="symbol").execute()
        _LAST_WRITE[symbol] = {"sig": sig, "ts": now}
    except Exception as e:
        logger.debug(f"[{symbol}] bot_runtime_state upsert failed: {e}")
