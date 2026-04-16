"""
BagHolderAI - Trend Follower Allocator
Decides which coins to allocate capital to, respecting tier limits,
exchange filters, and max active grids.
"""

import logging
from datetime import datetime, timezone
from utils.exchange_filters import validate_order

logger = logging.getLogger("bagholderai.trend.allocator")

# Symbols managed manually by Max — TF must NEVER touch these
MANUAL_WHITELIST = {"BTC/USDT", "SOL/USDT", "BONK/USDT"}

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
    max_grids = config.get("tf_max_coins") or config.get("max_active_grids", 5)
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

    # Equal-split allocation for TF (bypasses coin_tiers MAX_ALLOC_PCT).
    # The tier table was sized for the manual 5-grid / $500 system, where
    # T3 10% = $50/coin. Applied to TF with $100 budget and tf_max_coins=2
    # it degenerates to $10/coin and the grid taps out on the first buy.
    # Here we split the remaining budget equally across the slots that
    # will actually be filled this scan. Sanity cap prevents any single
    # coin from eating more than 1.5× the equal share (e.g. if only one
    # BULLISH is available and tf_max_coins > 1, it still caps at 1.5×
    # unless it's the very last slot).
    slots_remaining = max(0, max_grids - active_count)
    num_new = min(len(bullish), slots_remaining)
    sanity_cap = (total_capital / max_grids) * 1.5 if max_grids > 0 else total_capital
    if num_new <= 1:
        per_coin_target = unallocated
    else:
        per_coin_target = min(unallocated / num_new, sanity_cap)

    for coin in bullish:
        if active_count >= max_grids:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Max active grids reached ({max_grids})",
            ))
            continue

        tier, max_pct = _get_tier_info(coin["symbol"], coin_tiers)
        alloc_amount = min(per_coin_target, unallocated)

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

        # Build config snapshot (what WOULD be written). max_allocation_pct
        # is kept for telemetry only — it no longer gates the allocation.
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
            f"BULLISH T{tier} — ${alloc_amount:.0f} (equal-split {num_new}/{max_grids})",
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


def apply_allocations(supabase, decisions: list[dict], config: dict) -> None:
    """
    Apply TF allocation decisions to bot_config. Called only when dry_run=False.

    ALLOCATE   → INSERT or UPDATE bot_config (is_active=True, managed_by='trend_follower')
    DEALLOCATE → SET pending_liquidation=True (grid_runner forces sell + self-stop)

    Never touches symbols in MANUAL_WHITELIST.
    """
    for d in decisions:
        symbol = d["symbol"]
        action = d["action_taken"]

        if symbol in MANUAL_WHITELIST:
            logger.warning(f"[ALLOCATOR] Skipping {symbol} — in MANUAL_WHITELIST")
            continue

        if action == "ALLOCATE":
            snapshot = d.get("config_snapshot", {})
            capital = snapshot.get("capital_allocation", 0)

            if capital <= 0:
                logger.warning(f"[ALLOCATOR] {symbol}: capital=0, skipping ALLOCATE")
                continue

            signal = d.get("signal", "SIDEWAYS")
            if signal == "BULLISH":
                buy_pct, sell_pct = 1.5, 1.2
            elif signal == "BEARISH":
                buy_pct, sell_pct = 2.0, 0.8
            else:
                buy_pct, sell_pct = 1.5, 1.0

            # capital_per_trade: 1/4 of allocation, floor $6 (> Binance min_notional $5).
            # Prevents grid from defaulting to BTC's $25 per-trade when TF allocates $10.
            capital_per_trade = max(6.0, round(capital / 4, 2))

            row_fields = {
                "is_active": True,
                "managed_by": "trend_follower",
                "pending_liquidation": False,
                "capital_allocation": capital,
                "capital_per_trade": capital_per_trade,
                "buy_pct": buy_pct,
                "sell_pct": sell_pct,
                "grid_mode": "percentage",
                # grid_levels / grid_lower / grid_upper are NOT NULL in the DB
                # but unused in percentage mode — set placeholders so INSERT succeeds.
                "grid_levels": 10,
                "grid_lower": 0,
                "grid_upper": 0,
                # The DB default for profit_target_pct is 1.0. grid_bot interprets
                # min_profit_pct as a raw decimal (1.0 → +100% required to sell),
                # which would freeze every TF sell. Force 0 to disable the guard.
                "profit_target_pct": 0,
                # Match the manual bots' skim: 30% of each sell's profit goes
                # to the reserve ledger. Prevents TF from cycling 100% of gains
                # back into positions.
                "skim_pct": 30,
            }

            try:
                existing = supabase.table("bot_config").select("symbol").eq("symbol", symbol).execute()
                if existing.data:
                    supabase.table("bot_config").update(row_fields).eq("symbol", symbol).execute()
                    logger.info(
                        f"[ALLOCATOR] UPDATED {symbol} in bot_config "
                        f"(${capital:.0f}, per_trade=${capital_per_trade:.2f})"
                    )
                else:
                    supabase.table("bot_config").insert({"symbol": symbol, **row_fields}).execute()
                    logger.info(
                        f"[ALLOCATOR] INSERTED {symbol} in bot_config "
                        f"(${capital:.0f}, per_trade=${capital_per_trade:.2f})"
                    )
            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply ALLOCATE for {symbol}: {e}")

        elif action == "DEALLOCATE":
            try:
                existing = supabase.table("bot_config").select(
                    "symbol, managed_by"
                ).eq("symbol", symbol).execute()

                if not existing.data:
                    logger.warning(f"[ALLOCATOR] {symbol}: not in bot_config, nothing to deallocate")
                    continue

                current_managed_by = existing.data[0].get("managed_by")
                if current_managed_by != "trend_follower":
                    logger.warning(
                        f"[ALLOCATOR] {symbol}: managed_by={current_managed_by}, "
                        f"skipping DEALLOCATE (not TF-managed)"
                    )
                    continue

                supabase.table("bot_config").update({
                    "pending_liquidation": True,
                }).eq("symbol", symbol).execute()
                logger.info(f"[ALLOCATOR] SET pending_liquidation=True for {symbol}")
            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply DEALLOCATE for {symbol}: {e}")
