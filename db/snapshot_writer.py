"""
BagHolderAI - bot_state_snapshots helper (43b)

Periodic snapshot of each grid bot's operational state, written every
~15 minutes by the grid_runner main loop. Lets the CEO answer
"com'era X alle 14:30?" with a single SELECT instead of replaying
trades from the beginning.

Table schema (pre-created by CEO, RLS disabled):
    id                       uuid PK
    created_at               timestamptz
    symbol                   text
    managed_by               text
    holdings                 numeric
    avg_buy_price            numeric
    cash_available           numeric
    unrealized_pnl           numeric
    realized_pnl_cumulative  numeric
    open_lots_count          integer
    pct_last_buy_price       numeric NULL
    greed_tier_pct           numeric NULL  -- NULL for manual bots
    greed_age_minutes        numeric NULL  -- NULL for manual bots
    stop_loss_active         boolean
    stop_buy_active          boolean
    last_trade_at            timestamptz NULL

Contract:
- write_state_snapshot never raises. Failure degrades to a local
  warning. The main loop must not be blocked by an observability
  write error.
"""

import logging
import time
from datetime import timezone

from db.client import get_client, get_current_cycle

_logger = logging.getLogger("bagholderai.snapshots")

# Brief 79c (S79 2026-05-18): write-on-change + heartbeat for
# bot_state_snapshots. State fields are compared with the last written
# row; if nothing meaningful changed and the heartbeat hasn't elapsed,
# the write is skipped. Heartbeat is mandatory so dashboards can
# distinguish a dormant bot from a crashed one.
SNAPSHOT_HEARTBEAT_S = 300  # 5 min

# Fields whose change justifies an immediate write. `unrealized_pnl` is
# DELIBERATELY EXCLUDED — it tracks the live spot price and would change
# on every tick, defeating the filter. The MtM value is still captured
# every SNAPSHOT_HEARTBEAT_S, which is enough granularity for the
# equity timeline. realized_pnl_cumulative IS included because it only
# moves on actual sells (discrete, meaningful events).
_SNAPSHOT_COMPARE_KEYS = (
    "holdings",
    "avg_buy_price",
    "cash_available",
    "realized_pnl_cumulative",
    "open_lots_count",
    "pct_last_buy_price",
    "stop_loss_active",
    "stop_buy_active",
)

# Per-symbol cache of the last row written. Module-level — resets on
# process restart (which intentionally forces a fresh write on the first
# call post-restart).
_last_snapshot_per_symbol: dict[str, dict] = {}


def _snapshot_changed(current: dict, last: dict) -> bool:
    """True if any field in _SNAPSHOT_COMPARE_KEYS differs."""
    return any(current.get(k) != last.get(k) for k in _SNAPSHOT_COMPARE_KEYS)


def write_state_snapshot(bot, symbol: str) -> None:
    """Record a snapshot of `bot` for `symbol` in bot_state_snapshots. Never raises.

    Pulls data from bot.get_status() + a few direct attributes that aren't
    exposed via get_status (greed tier, stop flags, last_trade_at).
    """
    try:
        status = bot.get_status() if bot and bot.state else None
        if not status or status.get("status") == "not_initialized":
            return

        # Greed decay tier info — only meaningful for TF bots with allocated_at.
        greed_tier_pct = None
        greed_age_minutes = None
        try:
            tp_pct, age_min, _tier = bot.get_effective_tp()
            # get_effective_tp returns (sell_pct, None, None) for the manual
            # fallback path — distinguish by age_min presence.
            if age_min is not None:
                greed_tier_pct = float(tp_pct)
                greed_age_minutes = float(age_min)
        except Exception:
            # If the bot lacks get_effective_tp (e.g. a future refactor),
            # keep the snapshot going with nulls.
            pass

        last_trade_at_iso = None
        ltt = getattr(bot, "_last_trade_time", None)
        if ltt is not None:
            try:
                # _last_trade_time is UTC-naive in grid_bot; attach tz.
                dt = ltt if ltt.tzinfo else ltt.replace(tzinfo=timezone.utc)
                last_trade_at_iso = dt.isoformat()
            except Exception:
                last_trade_at_iso = None

        row = {
            "symbol": symbol,
            "managed_by": getattr(bot, "managed_by", "grid"),
            "holdings": float(status.get("holdings") or 0),
            "avg_buy_price": float(status.get("avg_buy_price") or 0),
            "cash_available": float(status.get("available_capital") or 0),
            "unrealized_pnl": float(status.get("unrealized_pnl") or 0),
            "realized_pnl_cumulative": float(status.get("realized_pnl") or 0),
            # Brief s70 FASE 2: avg-cost trading — no more FIFO queue.
            # Column kept for backward compat with legacy snapshots: 1 if holdings>0.
            "open_lots_count": 1 if (bot.state and bot.state.holdings > 0) else 0,
            "pct_last_buy_price": float(getattr(bot, "_pct_last_buy_price", 0) or 0),
            "greed_tier_pct": greed_tier_pct,
            "greed_age_minutes": greed_age_minutes,
            "stop_loss_active": bool(getattr(bot, "_stop_loss_triggered", False)),
            "stop_buy_active": bool(getattr(bot, "_stop_buy_active", False)),
            "last_trade_at": last_trade_at_iso,
            "cycle": get_current_cycle(get_client(), symbol),  # S96a clean slate
        }

        # Brief 79c (S79): skip if nothing meaningful changed AND last
        # write < SNAPSHOT_HEARTBEAT_S ago. Always writes the first time
        # after process restart (last cache is empty).
        now_ts = time.time()
        last = _last_snapshot_per_symbol.get(symbol)
        heartbeat_due = (
            last is None
            or (now_ts - last.get("_write_ts", 0)) >= SNAPSHOT_HEARTBEAT_S
        )
        if last is None or heartbeat_due or _snapshot_changed(row, last):
            get_client().table("bot_state_snapshots").insert(row).execute()
            _last_snapshot_per_symbol[symbol] = {**row, "_write_ts": now_ts}
        else:
            _logger.debug(
                "[%s] bot_state_snapshots write skipped: no change", symbol,
            )
    except Exception as e:
        _logger.warning(f"[{symbol}] bot_state_snapshots write failed: {e}")
