"""
Grid-regime-backtest — frozen parameter snapshot for the BTC grid bot.

Brief: config/2026-06-28_S110_brief_grid-regime-backtest.md
Read-only: legge i parametri reali da bot_config (Supabase), NON scrive nulla.

Il brief vuole "parametri congelati": questo modulo prende uno SNAPSHOT dei
valori effettivi che il grid BTC live userebbe in questo istante e lo congela
in un dict. Per i campi NULL in bot_config si applica lo stesso fallback del
runtime (settings.py / costruzione GridBot), documentato riga per riga.

NB FEDELTA': in LIVE alcuni di questi parametri (buy_pct/sell_pct/idle) li
muove Sherpa per regime. Lo snapshot li fotografa e li tiene fissi per tutto
il periodo simulato — è esattamente il "caso a freno fisso" richiesto dal
brief. Il report dichiara timestamp + caveat.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional

# repo root on sys.path so we can import the project's db client / settings
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# Documented fallbacks for bot_config columns that are NULL for BTC.
# Sourced from config/settings.py GRID_INSTANCES[0] (BTC) + GridBot defaults.
# ---------------------------------------------------------------------------
_BTC_DEFAULTS = {
    "capital_per_trade": 50.0,
    "buy_pct": 2.5,
    "sell_pct": 1.0,
    "skim_pct": 30.0,
    "min_profit_pct": 0.0,            # bot_config.profit_target_pct
    "idle_reentry_hours": 4.0,
    "dead_zone_hours": 2.0,
    "stop_buy_drawdown_pct": 3.0,
    "stop_buy_unlock_hours": 12.0,
    # NOT hot-reloaded by config_sync -> construction value (GRID_INSTANCES[0])
    "buy_cooldown_seconds": 1800.0,   # 30 min
    "slippage_buffer_pct": 0.03,      # HardcodedRules.SLIPPAGE_BUFFER_PCT
    "check_interval_seconds": 60.0,   # -> 1-minute candles
}

# Hardcoded rules mirrored from the runtime (config/settings.py).
MIN_LAST_SHOT_USD = 5.0               # HardcodedRules.MIN_LAST_SHOT_USD
DAILY_TRADE_LIMIT = 50               # grid_bot.py check_price_and_execute
STRATEGY = "A"
# BTC min-notional proxy (Binance ~ $5 / Kraken BTC ~0.00005 BTC). Used only as
# the "dust" threshold (fully-sold-out / re-entry gate). Immaterial at $50 lots.
MIN_NOTIONAL_USD = 5.0

# Fee presets (fraction). Kraken taker is the live target (market orders = taker).
FEE_KRAKEN_TAKER = 0.004    # 0.40% — PRIMARY
FEE_KRAKEN_MAKER = 0.0025   # 0.25%
FEE_BINANCE = 0.001         # 0.10% — "testnet illusion" comparison


def _read_bot_config_btc() -> Optional[dict]:
    """Read the live BTC row from bot_config. Returns None on any failure."""
    try:
        from db.client import get_client
        c = get_client()
        r = (
            c.table("bot_config")
            .select(
                "symbol,managed_by,is_active,cycle,capital_allocation,"
                "capital_per_trade,buy_pct,sell_pct,skim_pct,profit_target_pct,"
                "idle_reentry_hours,dead_zone_hours,stop_buy_drawdown_pct,"
                "stop_buy_unlock_hours,slippage_buffer_pct"
            )
            .ilike("symbol", "%BTC%")
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception as e:  # pragma: no cover - network/credentials dependent
        print(f"[params] WARN: could not read bot_config ({e}); using defaults.")
        return None


def _pick(db_row: Optional[dict], db_key: str, default_key: str):
    """bot_config value if present & not None, else documented default."""
    if db_row is not None:
        v = db_row.get(db_key)
        if v is not None:
            return float(v), "bot_config"
    return _BTC_DEFAULTS[default_key], "default"


def load_frozen_params(fee_rate: float = FEE_KRAKEN_TAKER,
                       capital: float = 250.0) -> dict:
    """Build the frozen BTC parameter snapshot.

    capital defaults to 250 (brief: "€250 equivalente USDT al giorno 1").
    fee_rate defaults to Kraken taker (0.40%).
    """
    db = _read_bot_config_btc()

    p = {}
    sources = {}

    def put(name, db_key, default_key):
        val, src = _pick(db, db_key, default_key)
        p[name] = val
        sources[name] = src

    put("capital_per_trade", "capital_per_trade", "capital_per_trade")
    put("buy_pct", "buy_pct", "buy_pct")
    put("sell_pct", "sell_pct", "sell_pct")
    put("skim_pct", "skim_pct", "skim_pct")
    put("min_profit_pct", "profit_target_pct", "min_profit_pct")
    put("idle_reentry_hours", "idle_reentry_hours", "idle_reentry_hours")
    put("dead_zone_hours", "dead_zone_hours", "dead_zone_hours")
    put("stop_buy_drawdown_pct", "stop_buy_drawdown_pct", "stop_buy_drawdown_pct")
    put("stop_buy_unlock_hours", "stop_buy_unlock_hours", "stop_buy_unlock_hours")
    put("slippage_buffer_pct", "slippage_buffer_pct", "slippage_buffer_pct")

    # Not hot-reloaded -> always the construction value.
    p["buy_cooldown_seconds"] = _BTC_DEFAULTS["buy_cooldown_seconds"]
    sources["buy_cooldown_seconds"] = "construction (not hot-reloaded)"
    p["check_interval_seconds"] = _BTC_DEFAULTS["check_interval_seconds"]
    sources["check_interval_seconds"] = "construction"

    # Brief / decided.
    p["capital"] = float(capital)
    sources["capital"] = "brief (€250)"
    p["fee_rate"] = float(fee_rate)
    sources["fee_rate"] = "decided (Kraken taker primary)"
    p["strategy"] = STRATEGY
    p["min_last_shot_usd"] = MIN_LAST_SHOT_USD
    p["daily_trade_limit"] = DAILY_TRADE_LIMIT
    p["min_notional_usd"] = MIN_NOTIONAL_USD

    meta = {
        "symbol": (db or {}).get("symbol", "BTC/USDT"),
        "snapshot_utc": datetime.now(timezone.utc).isoformat()
        if db is not None else "DEFAULTS (no DB)",
        "bot_config_read": db is not None,
        "managed_by": (db or {}).get("managed_by"),
        "cycle": (db or {}).get("cycle"),
        "capital_allocation_live": (db or {}).get("capital_allocation"),
    }

    return {"params": p, "sources": sources, "meta": meta}


def save_snapshot(snapshot: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)


if __name__ == "__main__":
    import pprint
    snap = load_frozen_params()
    pprint.pprint(snap)
