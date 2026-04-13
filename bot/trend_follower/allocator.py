"""
BagHolderAI - Trend Follower Allocator
Decides which coins to allocate capital to, respecting tier limits,
exchange filters, and max active grids.
"""

import logging
from datetime import datetime, timezone
from utils.exchange_filters import validate_order

logger = logging.getLogger("bagholderai.trend.allocator")

# Default tier for coins not in coin_tiers table
DEFAULT_TIER = 3
DEFAULT_MAX_ALLOC_PCT = 10  # T3 = 10%

# Known T1 coins (if not in coin_tiers)
T1_COINS = {"BTC", "ETH"}
T1_MAX_ALLOC_PCT = 40


def _get_tier_info(symbol: str, coin_tiers: dict) -> tuple[int, float]:
    """
    Look up tier and max allocation percent for a coin.
    Returns (tier, max_allocation_percent).
    """
    base = symbol.split("/")[0] if "/" in symbol else symbol

    if base in coin_tiers:
        entry = coin_tiers[base]
        return entry.get("tier", DEFAULT_TIER), entry.get("max_allocation_percent", DEFAULT_MAX_ALLOC_PCT)

    # Fallback: T1 for BTC/ETH, T3 for everything else
    if base in T1_COINS:
        return 1, T1_MAX_ALLOC_PCT
    return DEFAULT_TIER, DEFAULT_MAX_ALLOC_PCT


def decide_allocations(
    classified_coins: list[dict],
    current_allocations: list[dict],
    coin_tiers: dict,
    exchange_filters: dict,
    config: dict,
    total_capital: float,
) -> list[dict]:
    """
    Returns a list of decisions (ALLOCATE / DEALLOCATE / HOLD / SKIP) for each coin.
    In shadow mode, these are logged but not acted upon.
    """
    scan_ts = datetime.now(timezone.utc).isoformat()
    max_grids = config.get("max_active_grids", 5)
    decisions = []

    # Current state
    active_symbols = {a["symbol"] for a in current_allocations if a.get("is_active")}
    active_count = len(active_symbols)
    allocated_capital = sum(
        float(a.get("capital_allocation", 0))
        for a in current_allocations if a.get("is_active")
    )
    unallocated = total_capital - allocated_capital

    # Build lookup: symbol -> coin data
    coin_lookup = {c["symbol"]: c for c in classified_coins}

    # 1. Check existing active grids for signal reversal → DEALLOCATE or HOLD
    for alloc in current_allocations:
        sym = alloc["symbol"]
        if not alloc.get("is_active"):
            continue

        coin = coin_lookup.get(sym)
        if not coin:
            # Coin not in scan (maybe dropped out of top N) → HOLD
            decisions.append(_make_decision(
                scan_ts, sym, coin, "HOLD",
                f"Not in current scan top — keeping existing grid",
            ))
            continue

        if coin["signal"] == "BEARISH":
            decisions.append(_make_decision(
                scan_ts, sym, coin, "DEALLOCATE",
                f"Signal reversed to BEARISH (RSI={coin['rsi']:.1f}, EMA cross down)",
            ))
        else:
            decisions.append(_make_decision(
                scan_ts, sym, coin, "HOLD",
                f"Signal: {coin['signal']} (strength={coin['signal_strength']:.1f})",
            ))

    # 2. Find new BULLISH candidates, ranked by signal strength
    bullish = [
        c for c in classified_coins
        if c["signal"] == "BULLISH" and c["symbol"] not in active_symbols
    ]
    bullish.sort(key=lambda c: c["signal_strength"], reverse=True)

    for coin in bullish:
        if active_count >= max_grids:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Max active grids reached ({max_grids})",
            ))
            continue

        tier, max_pct = _get_tier_info(coin["symbol"], coin_tiers)
        alloc_amount = min(unallocated, total_capital * max_pct / 100)

        if alloc_amount <= 0:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"No unallocated capital remaining",
            ))
            continue

        # Check exchange filters: can this allocation support meaningful trades?
        # Simulate: allocation / 5 levels = per-level amount
        base = coin["symbol"].split("/")[0] if "/" in coin["symbol"] else coin["symbol"]
        per_level_usd = alloc_amount / 5
        per_level_amount = per_level_usd / coin["price"] if coin["price"] > 0 else 0
        sym_filters = exchange_filters.get(coin["symbol"], {})
        valid, reason = validate_order(coin["symbol"], per_level_amount, coin["price"], sym_filters)
        if not valid:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"FILTER_FAIL: {reason} (per-level ${per_level_usd:.2f})",
            ))
            continue

        # Build config snapshot (what WOULD be written)
        config_snapshot = {
            "symbol": coin["symbol"],
            "capital_allocation": round(alloc_amount, 2),
            "tier": tier,
            "max_allocation_pct": max_pct,
            "signal": coin["signal"],
            "signal_strength": coin["signal_strength"],
        }

        decisions.append(_make_decision(
            scan_ts, coin["symbol"], coin, "ALLOCATE",
            f"BULLISH T{tier} — ${alloc_amount:.0f} ({max_pct}% cap)",
            config_snapshot=config_snapshot,
        ))

        # Track as if allocated (for shadow accounting)
        unallocated -= alloc_amount
        active_count += 1

    return decisions


def _make_decision(
    scan_ts: str,
    symbol: str,
    coin: dict | None,
    action: str,
    reason: str,
    config_snapshot: dict | None = None,
) -> dict:
    """Build a decision dict."""
    d = {
        "scan_timestamp": scan_ts,
        "symbol": symbol,
        "action_taken": action,
        "reason": reason,
    }
    if coin:
        d.update({
            "ema_fast": coin.get("ema_fast", 0),
            "ema_slow": coin.get("ema_slow", 0),
            "rsi": coin.get("rsi", 0),
            "atr": coin.get("atr", 0),
            "signal": coin.get("signal", "NO_SIGNAL"),
            "signal_strength": coin.get("signal_strength", 0),
        })
    else:
        d.update({
            "ema_fast": 0, "ema_slow": 0, "rsi": 0, "atr": 0,
            "signal": "NO_SIGNAL", "signal_strength": 0,
        })
    if config_snapshot:
        d["config_snapshot"] = config_snapshot
    return d
