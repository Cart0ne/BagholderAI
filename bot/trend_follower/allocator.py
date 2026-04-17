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

# ---------------------------------------------------------------------------
# CEO-locked constants (session 36e v2, 2026-04-17)
# TODO: move to trend_config in a future session for dynamic tuning.
# ---------------------------------------------------------------------------
SWAP_STRENGTH_DELTA = 20.0   # points of signal_strength advantage required
SWAP_COOLDOWN_HOURS = 8      # min hours a coin must be held before a swap
SWAP_MIN_PROFIT_PCT = -1.0   # % of allocation — negative allows small loss

K_SELL = 1.2                 # ATR multiplier for sell_pct (hold longer)
K_BUY = 0.8                  # ATR multiplier for buy_pct (buy aggressive on dips)
SELL_PCT_MIN, SELL_PCT_MAX = 1.0, 8.0
BUY_PCT_MIN, BUY_PCT_MAX = 1.0, 10.0


def _hours_since(ts) -> float:
    """Hours elapsed since a datetime/ISO string, or +inf if None/invalid."""
    if not ts:
        return float("inf")
    try:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
    except Exception:
        return float("inf")


def _fetch_unrealized_pnl(supabase, symbol: str, current_price: float) -> float:
    """
    Compute unrealized PnL for a TF-managed symbol:
      (current_price - avg_buy_price) * holdings

    Reconstructs holdings + weighted-avg cost basis by replaying every
    TF trade (managed_by='trend_follower', config_version='v3') for the
    symbol in chronological order — matching grid_bot's own cost accounting.

    Returns 0.0 on any failure or when no open position exists, which is
    the safe default for the SWAP profit gate (neither blocks nor forces).
    """
    if current_price <= 0:
        return 0.0
    try:
        result = (
            supabase.table("trades")
            .select("side,amount,price")
            .eq("symbol", symbol)
            .eq("managed_by", "trend_follower")
            .eq("config_version", "v3")
            .order("created_at", desc=False)
            .execute()
        )
        trades = result.data or []
    except Exception as e:
        logger.warning(f"[ALLOCATOR] unrealized PnL fetch failed for {symbol}: {e}")
        return 0.0

    holdings = 0.0
    avg_buy_price = 0.0
    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount") or 0)
        price = float(t.get("price") or 0)
        if side == "buy":
            old = holdings
            holdings += amount
            if holdings > 0:
                avg_buy_price = (avg_buy_price * old + price * amount) / holdings
        elif side == "sell":
            holdings -= amount
            if holdings <= 1e-12:
                holdings = 0.0
                avg_buy_price = 0.0

    if holdings <= 0 or avg_buy_price <= 0:
        return 0.0
    return (current_price - avg_buy_price) * holdings


def _rescan_active_if_missing(
    exchange, coin_lookup: dict, active_symbols: set, config: dict,
) -> dict:
    """
    For each active symbol not in the scan top-N, fetch fresh OHLCV +
    indicators on-demand so downstream logic can always decide
    HOLD/DEALLOCATE/SWAP with fresh signal data.

    On failure: log warning and leave the symbol absent from the
    augmented lookup — the legacy HOLD path then takes over (Opzione A,
    CEO decision 36e v2). No preventive DEALLOCATE.
    """
    from bot.trend_follower.scanner import fetch_indicators_for_symbol
    from bot.trend_follower.classifier import classify_signal

    augmented = dict(coin_lookup)
    for sym in active_symbols:
        if sym in augmented:
            continue
        try:
            coin = fetch_indicators_for_symbol(exchange, sym)
            classify_signal(coin, config)
            augmented[sym] = coin
            logger.info(
                f"[ALLOCATOR] On-demand rescan succeeded for {sym}: "
                f"signal={coin['signal']}, strength={coin.get('signal_strength', 0):.1f}"
            )
        except Exception as e:
            logger.warning(
                f"[ALLOCATOR] On-demand rescan FAILED for {sym}: {e} — "
                f"falling back to HOLD (will retry next scan)"
            )
    return augmented


def _adaptive_steps(coin: dict, signal: str) -> tuple[float, float]:
    """
    Returns (buy_pct, sell_pct) scaled by coin volatility (ATR / price).
    Falls back to fixed legacy steps if ATR or price unavailable.

    CEO decision 36e v2: k_sell > k_buy means we hold positions longer
    before realizing (catch more of the BULLISH trend) and enter dips
    more aggressively (shorter retracement needed to buy).
    """
    atr = coin.get("atr", 0) or 0
    price = coin.get("price", 0) or 0
    if atr <= 0 or price <= 0:
        if signal == "BULLISH":
            return 1.5, 1.2
        if signal == "BEARISH":
            return 2.0, 0.8
        return 1.5, 1.0

    atr_pct = (atr / price) * 100

    sell_pct = max(SELL_PCT_MIN, min(SELL_PCT_MAX, atr_pct * K_SELL))
    buy_pct = max(BUY_PCT_MIN, min(BUY_PCT_MAX, atr_pct * K_BUY))

    # Bearish allocations widen buys slightly to avoid catching a falling knife.
    if signal == "BEARISH":
        buy_pct = min(BUY_PCT_MAX, buy_pct * 1.1)

    return round(buy_pct, 2), round(sell_pct, 2)


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
    exchange=None,
    supabase=None,
) -> list[dict]:
    """
    Returns a list of decisions (ALLOCATE / DEALLOCATE / HOLD / SKIP) for each coin.
    In shadow mode, these are logged but not acted upon.

    `exchange` + `supabase` are required to enable on-demand rescan (Problema 0)
    and the SWAP profit gate (Fix 1). Passing None degrades gracefully: rescan
    is skipped and unrealized PnL is treated as 0 for any SWAP check.
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

    # Problema 0: on-demand rescan for active coins that fell off the top-N
    # scan. Fresh indicators let SWAP/DEALLOCATE see their real signal.
    if exchange is not None:
        coin_lookup = _rescan_active_if_missing(
            exchange, coin_lookup, active_symbols, config,
        )

    # 1a. DEALLOCATE on BEARISH; defer HOLD until after SWAP evaluation so
    # we don't double-emit a decision for a symbol that gets swapped out.
    surviving_active: list[tuple[dict, dict]] = []  # [(alloc, coin), ...]
    for alloc in current_allocations:
        sym = alloc["symbol"]
        if not alloc.get("is_active"):
            continue

        coin = coin_lookup.get(sym)
        if not coin:
            # Rescan failed (or exchange unavailable) → legacy HOLD path.
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
            surviving_active.append((alloc, coin))

    # 2. Find new BULLISH candidates, ranked by signal strength
    bullish = [
        c for c in classified_coins
        if c["signal"] == "BULLISH" and c["symbol"] not in active_symbols
    ]
    bullish.sort(key=lambda c: c["signal_strength"], reverse=True)

    # 1b. Hybrid rotation SWAP (Fix 1 — CEO-locked gates, session 36e v2).
    # At most one swap per scan. A swapped-out coin is DEALLOCATEd here; its
    # budget is virtually returned to `unallocated` so the downstream bullish
    # allocation loop can hand it to the replacement candidate in the same scan.
    swapped_out: set[str] = set()
    best_new = next(
        (c for c in bullish if c["symbol"] not in active_symbols),
        None,
    )
    if best_new is not None:
        for alloc, active_coin in surviving_active:
            sym = alloc["symbol"]
            delta = best_new["signal_strength"] - active_coin["signal_strength"]
            if delta < SWAP_STRENGTH_DELTA:
                continue

            allocated_at = alloc.get("updated_at") or alloc.get("created_at")
            held_hours = _hours_since(allocated_at)
            if held_hours < SWAP_COOLDOWN_HOURS:
                logger.debug(
                    f"[ALLOCATOR] SWAP skip {sym}: held {held_hours:.1f}h < "
                    f"{SWAP_COOLDOWN_HOURS}h cooldown (candidate {best_new['symbol']} +{delta:.1f})"
                )
                continue

            capital_allocation = float(alloc.get("capital_allocation", 0) or 0)
            min_profit_usd = capital_allocation * (SWAP_MIN_PROFIT_PCT / 100.0)
            unrealized = (
                _fetch_unrealized_pnl(supabase, sym, active_coin.get("price", 0))
                if supabase is not None else 0.0
            )
            if unrealized < min_profit_usd:
                logger.debug(
                    f"[ALLOCATOR] SWAP skip {sym}: unrealized ${unrealized:.2f} < "
                    f"threshold ${min_profit_usd:.2f} ({SWAP_MIN_PROFIT_PCT}% of "
                    f"${capital_allocation:.2f})"
                )
                continue

            logger.info(
                f"[ALLOCATOR] SWAP triggered: {sym} (strength "
                f"{active_coin['signal_strength']:.1f}, held {held_hours:.1f}h, "
                f"unrealized ${unrealized:.2f}) → replaced by {best_new['symbol']} "
                f"(+{delta:.1f} strength)"
            )
            decisions.append(_make_decision(
                scan_ts, sym, active_coin, "DEALLOCATE",
                f"SWAP: replaced by {best_new['symbol']} (+{delta:.1f} strength, "
                f"held {held_hours:.1f}h, unrealized ${unrealized:.2f})",
            ))
            swapped_out.add(sym)
            # Virtually free the budget so the replacement can be allocated
            # in the same scan without waiting for grid_runner to liquidate.
            unallocated += capital_allocation
            active_count -= 1
            break  # one swap per scan (CEO decision 36e v2)

    # Emit HOLD for the active coins that survived both BEARISH and SWAP checks.
    for alloc, coin in surviving_active:
        if alloc["symbol"] in swapped_out:
            continue
        decisions.append(_make_decision(
            scan_ts, alloc["symbol"], coin, "HOLD",
            f"Signal: {coin['signal']} (strength={coin['signal_strength']:.1f})",
        ))

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


def apply_allocations(
    supabase, decisions: list[dict], config: dict,
    coin_lookup: dict | None = None,
) -> None:
    """
    Apply TF allocation decisions to bot_config. Called only when dry_run=False.

    ALLOCATE   → INSERT or UPDATE bot_config (is_active=True, managed_by='trend_follower')
    DEALLOCATE → SET pending_liquidation=True (grid_runner forces sell + self-stop)

    `coin_lookup` (symbol → classified coin dict) is used to compute
    ATR-adaptive buy_pct/sell_pct at allocation time. If absent, falls
    back to the legacy fixed-step behavior.

    Never touches symbols in MANUAL_WHITELIST.
    """
    coin_lookup = coin_lookup or {}
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
            coin = coin_lookup.get(symbol, {
                "atr": d.get("atr", 0),
                "price": snapshot.get("price", 0),
            })
            buy_pct, sell_pct = _adaptive_steps(coin, signal)

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
                # TF does not want a min-profit gate (sell_pct is the sole
                # sell threshold for this strategy). Force 0 explicitly so
                # the behavior is independent of the bot_config column default.
                "profit_target_pct": 0,
                # Match the manual bots' skim: 30% of each sell's profit goes
                # to the reserve ledger. Prevents TF from cycling 100% of gains
                # back into positions.
                "skim_pct": 30,
            }

            try:
                existing = supabase.table("bot_config").select("symbol").eq("symbol", symbol).execute()
                if existing.data:
                    # Reset updated_at so the SWAP cooldown clock starts on re-allocation.
                    update_fields = {**row_fields, "updated_at": datetime.now(timezone.utc).isoformat()}
                    supabase.table("bot_config").update(update_fields).eq("symbol", symbol).execute()
                    logger.info(
                        f"[ALLOCATOR] UPDATED {symbol} in bot_config "
                        f"(${capital:.0f}, per_trade=${capital_per_trade:.2f}, "
                        f"buy={buy_pct}%, sell={sell_pct}%)"
                    )
                else:
                    supabase.table("bot_config").insert({"symbol": symbol, **row_fields}).execute()
                    logger.info(
                        f"[ALLOCATOR] INSERTED {symbol} in bot_config "
                        f"(${capital:.0f}, per_trade=${capital_per_trade:.2f}, "
                        f"buy={buy_pct}%, sell={sell_pct}%)"
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
