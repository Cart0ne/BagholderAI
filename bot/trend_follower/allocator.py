"""
BagHolderAI - Trend Follower Allocator
Decides which coins to allocate capital to, respecting tier limits,
exchange filters, and max active grids.
"""

import logging
from datetime import datetime, timezone
from utils.exchange_filters import validate_order, round_to_step
from db.event_logger import log_event

logger = logging.getLogger("bagholderai.trend.allocator")

# Symbols managed manually by Max — TF must NEVER touch these
MANUAL_WHITELIST = {"BTC/USDT", "SOL/USDT", "BONK/USDT"}

# 45c: Volume tier defaults (overridden by trend_config at runtime)
DEFAULT_TIER1_MIN_VOLUME = 100_000_000   # ≥ $100M → Tier 1 (blue chip)
DEFAULT_TIER2_MIN_VOLUME = 20_000_000    # ≥ $20M  → Tier 2 (mid cap)
# < DEFAULT_TIER2_MIN_VOLUME → Tier 3 (small cap)


def _assign_volume_tier(coin: dict, t1_min: float, t2_min: float) -> int:
    """45c: returns 1, 2, or 3 based on 24h quoteVolume.
    Uses integers (not strings) to match bot_config.volume_tier smallint."""
    vol = float(coin.get("volume_24h", 0) or 0)
    if vol >= t1_min:
        return 1
    if vol >= t2_min:
        return 2
    return 3

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
# 36e integration (2026-04-17): clamps tightened to enforce CEO trading
# philosophy ("buy small dips ≤2%, sell target ≤6%"). Above ATR% ≈ 2.5%
# the buy side saturates at 2.0 — intentional, matches the manual bots.
SELL_PCT_MIN, SELL_PCT_MAX = 1.0, 6.0
BUY_PCT_MIN, BUY_PCT_MAX = 1.0, 2.0


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


def _is_in_sl_cooldown(supabase, symbol: str, cooldown_hours: float) -> tuple[bool, float]:
    """
    45a v2: post-stop-loss cooldown check.
    Returns (in_cooldown, hours_since_sl). Fail-open: on query error or
    missing data, returns (False, 0.0) so allocation proceeds — a transient
    DB hiccup must not block the TF.
    """
    if cooldown_hours <= 0 or supabase is None:
        return False, 0.0
    try:
        res = supabase.table("bot_config").select(
            "last_stop_loss_at"
        ).eq("symbol", symbol).maybe_single().execute()
        if not res or not res.data:
            return False, 0.0
        sl_ts = res.data.get("last_stop_loss_at")
        if not sl_ts:
            return False, 0.0
        hours_since = _hours_since(sl_ts)
        return hours_since < cooldown_hours, hours_since
    except Exception as e:
        logger.warning(f"[ALLOCATOR] SL cooldown check failed for {symbol}: {e}")
        return False, 0.0


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


# 45b: post-greed-decay salvage threshold.
# On TF ALLOCATE, sell_pct is NOT ATR-derived any more — it's computed
# deterministically from greed_decay_tiers so it fits the "less greedy
# over time" philosophy. See _compute_sell_pct_salvage below and the
# callsite in decide_allocations.
SALVAGE_DELTA_PCT = 0.5
SALVAGE_FLOOR_PCT = 0.3


def _compute_sell_pct_salvage(greed_decay_tiers) -> float:
    """
    45b: deterministic post-greed-decay salvage for TF bots.
    Returns max(last_tier_tp_pct - SALVAGE_DELTA_PCT, SALVAGE_FLOOR_PCT).

    "Last tier" = tier with the highest `minutes` value (sorted
    ascending, last wins). On malformed/empty tiers, returns the floor
    so the salvage is always positive and grid_bot never gets a
    nonsensical sell threshold.
    """
    try:
        tiers = sorted(
            (t for t in (greed_decay_tiers or [])
             if isinstance(t, dict)
             and "minutes" in t and "tp_pct" in t),
            key=lambda t: float(t["minutes"]),
        )
    except Exception:
        return SALVAGE_FLOOR_PCT
    if not tiers:
        return SALVAGE_FLOOR_PCT
    try:
        last_tp = float(tiers[-1]["tp_pct"])
    except Exception:
        return SALVAGE_FLOOR_PCT
    return round(max(last_tp - SALVAGE_DELTA_PCT, SALVAGE_FLOOR_PCT), 2)


def _adaptive_steps(coin: dict, signal: str) -> tuple[float, float]:
    """
    Returns (buy_pct, sell_pct) scaled by coin volatility (ATR / price).
    Falls back to fixed legacy steps if ATR or price unavailable.

    CEO decision 36e v2: k_sell > k_buy means we hold positions longer
    before realizing (catch more of the BULLISH trend) and enter dips
    more aggressively (shorter retracement needed to buy).

    45b: the sell_pct output is NO LONGER USED for TF allocations — the
    caller (decide_allocations) discards it and writes the value from
    _compute_sell_pct_salvage instead. buy_pct remains ATR-adaptive.
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
    # 45a v2: post-stop-loss cooldown (hours). 0 = disabled, edit from /tf admin UI.
    sl_cooldown_hours = float(config.get("tf_stop_loss_cooldown_hours") or 0)
    # 45c: volume tier thresholds and weights. Defaults mirror trend_config
    # defaults and are overridable from the /tf dashboard.
    t1_min = float(config.get("tf_tier1_min_volume", DEFAULT_TIER1_MIN_VOLUME))
    t2_min = float(config.get("tf_tier2_min_volume", DEFAULT_TIER2_MIN_VOLUME))
    t1_weight = float(config.get("tf_tier1_weight", 40))
    t2_weight = float(config.get("tf_tier2_weight", 35))
    t3_weight = float(config.get("tf_tier3_weight", 25))
    weight_sum = t1_weight + t2_weight + t3_weight
    if weight_sum <= 0:
        weight_sum = 100  # safety fallback; won't divide by zero below
    # 45e v2: entry distance filter — skip candidates too stretched above EMA20.
    # 0 (or negative) = disabled. Historical validation on v3 losses showed
    # threshold 10 blocks 92.4% of the loss by dollar amount.
    max_entry_distance = float(config.get("tf_entry_max_distance_pct") or 0)
    # 45c: tag every classified coin with its current volume tier (1/2/3)
    for _c in classified_coins:
        _c["volume_tier"] = _assign_volume_tier(_c, t1_min, t2_min)
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
    # 45a v2: pick the strongest bullish candidate that isn't already active
    # AND isn't in SL cooldown. A just-stop-hunted coin is a bad swap target
    # regardless of signal strength. Log each cooldown-skip so the TF decision
    # trail in bot_events_log stays self-explanatory.
    best_new = None
    for c in bullish:
        if c["symbol"] in active_symbols:
            continue
        in_cd, hrs = _is_in_sl_cooldown(supabase, c["symbol"], sl_cooldown_hours)
        if in_cd:
            logger.info(
                f"[ALLOCATOR] SWAP candidate {c['symbol']} skipped: "
                f"SL cooldown ({hrs:.1f}h < {sl_cooldown_hours}h)"
            )
            log_event(
                severity="info",
                category="tf",
                event="sl_cooldown_skip",
                symbol=c["symbol"],
                message=f"SWAP candidate skipped: {hrs:.1f}h since SL (cooldown {sl_cooldown_hours}h)",
                details={
                    "hours_since": hrs,
                    "cooldown_hours": sl_cooldown_hours,
                    "path": "SWAP",
                },
            )
            continue
        # 45e v2: apply entry distance filter to SWAP candidates too.
        # The MOVR incident (2026-04-17) was a SWAP — the coin entered at
        # +87% above EMA20. With this gate, that SWAP would have been blocked.
        if max_entry_distance > 0:
            dist_c = float(c.get("distance_from_ema_pct", 0) or 0)
            if dist_c > max_entry_distance:
                logger.info(
                    f"[ALLOCATOR] SWAP candidate {c['symbol']} skipped: "
                    f"distance {dist_c:.1f}% > max {max_entry_distance:.1f}%"
                )
                log_event(
                    severity="info",
                    category="tf",
                    event="entry_distance_skip",
                    symbol=c["symbol"],
                    message=(
                        f"SWAP candidate skipped: price {dist_c:.1f}% above "
                        f"EMA20 (max {max_entry_distance:.1f}%)"
                    ),
                    details={
                        "distance_pct": dist_c,
                        "max_distance_pct": max_entry_distance,
                        "path": "SWAP",
                        # 47a: counterfactual tracker — snapshot of price+EMA at
                        # skip time so the post-scan job can fetch the +24h
                        # delta without re-querying historical candles.
                        "skip_price": float(c.get("price", 0) or 0),
                        "skip_ema20": float(c.get("ema_fast", 0) or 0),
                    },
                )
                continue
        best_new = c
        break
    if best_new is not None:
        for alloc, active_coin in surviving_active:
            sym = alloc["symbol"]
            # 45c: SWAP only within the same volume tier. Active tier comes
            # from the frozen bot_config.volume_tier written at ALLOCATE
            # time. Legacy rows (pre-45c, NULL) fall back to the current
            # scan's tier for the symbol.
            stored_tier = alloc.get("volume_tier")
            if stored_tier is not None:
                active_tier = int(stored_tier)
            else:
                active_tier = _assign_volume_tier(active_coin, t1_min, t2_min)
            candidate_tier = int(best_new.get("volume_tier") or 3)
            if candidate_tier != active_tier:
                logger.debug(
                    f"[ALLOCATOR] SWAP skip {best_new['symbol']} → {sym}: "
                    f"cross-tier (candidate T{candidate_tier} vs active T{active_tier})"
                )
                continue

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
            log_event(
                severity="info",
                category="tf",
                event="tf_swap",
                symbol=sym,
                message=f"SWAP {sym} → {best_new['symbol']} (+{delta:.1f} strength, held {held_hours:.1f}h)",
                details={
                    "swapped_out": sym,
                    "swapped_in": best_new["symbol"],
                    "strength_delta": delta,
                    "held_hours": held_hours,
                    "unrealized": unrealized,
                },
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

    # 45c: Per-tier ALLOCATE with upward-only orphan redistribution.
    # Each volume tier (1/2/3) has 1 slot. The allocator picks the strongest
    # BULLISH candidate per empty tier. Orphan budget (empty tier) flows
    # UPWARD only (T3 orphan → T2, T2 orphan → T1). Never flows down so
    # small-cap exposure stays capped at its weight.

    # 44c: minimum signal_strength threshold. Applied per-tier. Prevents
    # "desperate ALLOCATE" on weak candidates just to fill a slot.
    min_strength = float(config.get("min_allocate_strength", 15.0))

    # Step A: identify occupied tiers + count active TF bots globally.
    # 45d: switched from dict[int, str] to set[int] so two active bots
    # in the same tier (common with legacy volume_tier IS NULL rows)
    # don't silently overwrite each other. The global count is the
    # belt-and-suspenders guard against allocating above tf_max_coins.
    active_tiers: set[int] = set()
    active_count_global = 0
    for alloc in current_allocations:
        if not alloc.get("is_active"):
            continue
        sym = alloc["symbol"]
        stored_tier = alloc.get("volume_tier")
        if stored_tier is not None:
            tier_n = int(stored_tier)
        else:
            match = coin_lookup.get(sym)
            if match is not None:
                tier_n = _assign_volume_tier(match, t1_min, t2_min)
            else:
                tier_n = 3  # safest fallback for illiquid active coin
        active_tiers.add(tier_n)
        active_count_global += 1

    # Step B: for each empty tier, pick the strongest BULLISH candidate
    # (not already active, not swapped out earlier). `bullish` is already
    # sorted by signal_strength desc, so `max()` per tier is cheap/clear.
    tier_best: dict[int, dict | None] = {}
    for tier_key in (1, 2, 3):
        if tier_key in active_tiers:
            tier_best[tier_key] = None  # slot occupied by HOLD
            continue
        tier_candidates = [
            c for c in bullish
            if int(c.get("volume_tier") or 3) == tier_key
            and c["symbol"] not in active_symbols
        ]
        if not tier_candidates:
            tier_best[tier_key] = None
            continue
        tier_best[tier_key] = max(
            tier_candidates,
            key=lambda c: float(c.get("signal_strength", 0) or 0),
        )

    # Step C: compute tier budgets. Start from base weights, then route
    # orphan budget to the SAFER tier that has a candidate. Rules:
    #   - T3 orphan → T2 (if T2 has candidate), else idle (never flows to T1
    #     skipping; T1 has its own budget; and NEVER flows down is a no-op here)
    #   - T2 orphan → T1 (if T1 has candidate), else idle
    #   - T1 orphan → T2 (if T2 has candidate), else idle
    # Key invariant: T3 exposure is ALWAYS capped at its base weight.
    # Small-cap risk never grows, regardless of market conditions.
    base_budget = {
        1: total_capital * (t1_weight / weight_sum),
        2: total_capital * (t2_weight / weight_sum),
        3: total_capital * (t3_weight / weight_sum),
    }
    tier_budget = dict(base_budget)

    def _tier_filled(t: int) -> bool:
        return t in active_tiers or tier_best.get(t) is not None

    # T3 orphan → T2 (T3's $25 stays capped; never flows further up)
    if not _tier_filled(3) and _tier_filled(2):
        tier_budget[2] += tier_budget[3]
        tier_budget[3] = 0.0
    # T2 orphan → T1
    if not _tier_filled(2) and _tier_filled(1):
        tier_budget[1] += tier_budget[2]
        tier_budget[2] = 0.0
    # T1 orphan → T2 (downgrade only to the next-safer available tier,
    # never to T3 — small-cap exposure stays capped)
    if not _tier_filled(1) and _tier_filled(2):
        tier_budget[2] += tier_budget[1]
        tier_budget[1] = 0.0

    # Step D: emit ALLOCATE / SKIP decisions per tier.
    sanity_cap_usd = float(config.get("tf_sanity_cap_usd", 300))
    # 45c: per-tier lot counts. More lots on blue chips (smoother entry),
    # fewer on small caps (decisive entry, smaller bag-accumulation risk).
    # Defaults 4/3/2; overridable from /tf dashboard.
    tier_lots = {
        1: int(config.get("tf_tier1_lots", 4)),
        2: int(config.get("tf_tier2_lots", 3)),
        3: int(config.get("tf_tier3_lots", 2)),
    }

    # 45d: global slot cap. Belt-and-suspenders guard: even if the per-tier
    # logic thinks a slot is free (e.g. due to legacy fallback tagging
    # oddities), we must NEVER allocate beyond tf_max_coins total TF bots.
    # If we're already at the cap, every would-be ALLOCATE emits SKIP so the
    # decision trail is self-explanatory.
    max_total = int(max_grids) if max_grids else 3
    if active_count_global >= max_total:
        for tier_key in (1, 2, 3):
            coin = tier_best.get(tier_key)
            if coin is None:
                continue
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Tier {tier_key}: global slot cap reached "
                f"({active_count_global}/{max_total} TF bots active)",
            ))
        return decisions

    for tier_key in (1, 2, 3):
        coin = tier_best.get(tier_key)
        if coin is None:
            continue  # active HOLD or truly empty (budget already redistributed)

        # Apply 45a SL cooldown gate (redundant with SWAP gate, but the
        # ALLOCATE path is independent — a just-stop-hunted coin must not
        # be re-picked on the same scan).
        in_cooldown, hours_since = _is_in_sl_cooldown(
            supabase, coin["symbol"], sl_cooldown_hours
        )
        if in_cooldown:
            reason = (
                f"SL cooldown: {hours_since:.1f}h since last stop-loss "
                f"(need {sl_cooldown_hours}h)"
            )
            logger.info(f"[ALLOCATOR] SKIP {coin['symbol']}: {reason}")
            log_event(
                severity="info",
                category="tf",
                event="sl_cooldown_skip",
                symbol=coin["symbol"],
                message=reason,
                details={
                    "hours_since": hours_since,
                    "cooldown_hours": sl_cooldown_hours,
                    "path": "ALLOCATE",
                },
            )
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP", reason,
            ))
            continue

        # 45e v2: entry distance filter — skip coins too stretched above EMA20.
        # Historical validation (11 v3 losses) showed threshold 10 blocks
        # 92.4% of loss by dollar amount. 0 = disabled.
        if max_entry_distance > 0:
            distance = float(coin.get("distance_from_ema_pct", 0) or 0)
            if distance > max_entry_distance:
                reason = (
                    f"FILTER_ENTRY_DISTANCE: price {distance:.1f}% above EMA20 "
                    f"(max {max_entry_distance:.1f}% — stretched, mean-reversion risk)"
                )
                logger.info(f"[ALLOCATOR] SKIP {coin['symbol']}: {reason}")
                log_event(
                    severity="info",
                    category="tf",
                    event="entry_distance_skip",
                    symbol=coin["symbol"],
                    message=reason,
                    details={
                        "distance_pct": distance,
                        "max_distance_pct": max_entry_distance,
                        "path": "ALLOCATE",
                        # 47a: counterfactual tracker — see SWAP-path comment.
                        "skip_price": float(coin.get("price", 0) or 0),
                        "skip_ema20": float(coin.get("ema_fast", 0) or 0),
                    },
                )
                decisions.append(_make_decision(
                    scan_ts, coin["symbol"], coin, "SKIP", reason,
                ))
                continue

        coin_strength = float(coin.get("signal_strength", 0) or 0)
        if coin_strength < min_strength:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Tier {tier_key} best ({coin['symbol']}) strength "
                f"{coin_strength:.2f} below min_allocate_strength {min_strength}",
            ))
            continue

        alloc_amount = min(tier_budget[tier_key], sanity_cap_usd, unallocated)
        if alloc_amount <= 0:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Tier {tier_key}: no unallocated capital",
            ))
            continue

        # Exchange filter check — reuses round_to_step + validate_order so
        # we validate what Binance would actually see (post-rounding).
        # 45c: divide by per-tier lot count so the filter simulation matches
        # TF's real per-lot spend. With defaults 4/3/2 and weights 40/35/25,
        # T3 per-lot is $12.50 — well clear of min_notional=$5.
        lots_for_tier = tier_lots[tier_key]
        per_level_usd = alloc_amount / lots_for_tier
        per_level_amount = (
            per_level_usd / coin["price"] if coin.get("price", 0) > 0 else 0
        )
        sym_filters = exchange_filters.get(coin["symbol"], {})
        step_size = sym_filters.get("lot_step_size", 0)
        if step_size > 0:
            per_level_amount = round_to_step(per_level_amount, step_size)
        valid, reason = validate_order(
            coin["symbol"], per_level_amount, coin.get("price", 0), sym_filters,
        )
        if not valid:
            decisions.append(_make_decision(
                scan_ts, coin["symbol"], coin, "SKIP",
                f"Tier {tier_key} FILTER_FAIL: {reason} "
                f"(per-level ${per_level_usd:.2f})",
            ))
            continue

        tier_info, max_pct = _get_tier_info(coin["symbol"], coin_tiers)
        # 45c: initial_lots policy — T1/T2 keep 1 lot in reserve for dips;
        # T3 fires everything at entry (illiquid coins don't wait for dips).
        initial_lots_for_tier = (
            lots_for_tier if tier_key == 3 else max(0, lots_for_tier - 1)
        )
        config_snapshot = {
            "symbol": coin["symbol"],
            "capital_allocation": round(alloc_amount, 2),
            "tier": tier_info,
            "max_allocation_pct": max_pct,
            "signal": coin["signal"],
            "signal_strength": coin["signal_strength"],
            # 45c: freeze the volume tier so subsequent scans don't re-tier
            # the active coin.
            "volume_tier": tier_key,
            "volume_24h": float(coin.get("volume_24h", 0) or 0),
            # 45c: per-tier lot counts override the global tf_lots_per_coin
            # for this specific ALLOCATE. apply_allocations reads these to
            # set capital_per_trade + initial_lots correctly.
            "tier_lots": lots_for_tier,
            "tier_initial_lots": initial_lots_for_tier,
        }

        decisions.append(_make_decision(
            scan_ts, coin["symbol"], coin, "ALLOCATE",
            f"Tier {tier_key} (vol ${float(coin.get('volume_24h', 0) or 0)/1e6:.1f}M): "
            f"strongest BULLISH — ${alloc_amount:.0f} "
            f"(strength={coin_strength:.1f})",
            config_snapshot=config_snapshot,
        ))

        logger.info(
            f"[ALLOCATOR] Tier {tier_key} ALLOCATE {coin['symbol']} "
            f"(vol ${float(coin.get('volume_24h', 0) or 0)/1e6:.1f}M, "
            f"strength {coin_strength:.1f}, budget ${alloc_amount:.0f})"
        )

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


def resize_active_allocations(
    supabase,
    current_allocations: list[dict],
    tf_total_capital: float,
    config: dict,
    is_shadow: bool = True,
) -> list[dict]:
    """
    Session 36g Phase 2: propagate compound to live TF bots.
    Session 45d: tier-weighted resize. Each bot's target is computed from
    its frozen bot_config.volume_tier and the matching tier weight +
    per-tier lot count. Legacy rows (volume_tier IS NULL) keep the old
    equal-split formula so they don't thrash during the transition — they
    get proper tier-weighted sizing once re-allocated.

    Skip UPDATE if the delta vs current is below tf_resize_threshold_usd
    or if the bot is pending_liquidation.

    Returns a list of resize actions (for logging + Telegram).
    """
    max_coins = int(config.get("tf_max_coins") or config.get("max_active_grids", 5))
    if max_coins <= 0:
        return []

    threshold = float(config.get("tf_resize_threshold_usd", 10))
    cpt_cap = float(config.get("tf_capital_per_trade_cap_usd", 50))

    # 45d: per-tier weights + lots from trend_config. Defaults match 45c.
    t1_weight = float(config.get("tf_tier1_weight", 40))
    t2_weight = float(config.get("tf_tier2_weight", 35))
    t3_weight = float(config.get("tf_tier3_weight", 25))
    weight_sum = t1_weight + t2_weight + t3_weight
    if weight_sum <= 0:
        weight_sum = 100
    tier_weight_frac = {
        1: t1_weight / weight_sum,
        2: t2_weight / weight_sum,
        3: t3_weight / weight_sum,
    }
    tier_lots_map = {
        1: int(config.get("tf_tier1_lots", 4)),
        2: int(config.get("tf_tier2_lots", 3)),
        3: int(config.get("tf_tier3_lots", 2)),
    }

    # Legacy fallback (equal-split, pre-45d behaviour) for rows with
    # volume_tier IS NULL. Same formula as before so nothing thrashes
    # until the bot gets re-allocated and receives a proper frozen tier.
    legacy_lots = int(config.get("tf_lots_per_coin", 4))
    legacy_target_alloc = tf_total_capital / max_coins
    legacy_target_cpt = min(
        cpt_cap, max(6.0, round(legacy_target_alloc / legacy_lots, 2))
    )

    tf_active = [
        a for a in current_allocations
        if a.get("is_active") and a.get("managed_by") == "trend_follower"
        and not a.get("pending_liquidation")
    ]

    resize_actions: list[dict] = []
    for alloc in tf_active:
        symbol = alloc["symbol"]
        if symbol in MANUAL_WHITELIST:
            continue

        # 45d: tier-weighted target when volume_tier is set; legacy
        # equal-split otherwise.
        stored_tier = alloc.get("volume_tier")
        if stored_tier is not None:
            t = int(stored_tier)
            frac = tier_weight_frac.get(t, 1.0 / max_coins)
            lots = tier_lots_map.get(t, legacy_lots)
            target_alloc = tf_total_capital * frac
            target_cpt = min(cpt_cap, max(6.0, round(target_alloc / lots, 2)))
        else:
            target_alloc = legacy_target_alloc
            target_cpt = legacy_target_cpt

        current_alloc = float(alloc.get("capital_allocation") or 0)
        delta = target_alloc - current_alloc

        if abs(delta) < threshold:
            continue

        action = {
            "symbol": symbol,
            "current_alloc": round(current_alloc, 2),
            "target_alloc": round(target_alloc, 2),
            "target_cpt": target_cpt,
            "delta": round(delta, 2),
        }

        if is_shadow:
            action["applied"] = False
            logger.info(
                f"[RESIZE] [SHADOW] {symbol}: ${current_alloc:.2f} → "
                f"${target_alloc:.2f} (Δ ${delta:+.2f}, cpt ${target_cpt:.2f}) — not written"
            )
        else:
            try:
                supabase.table("bot_config").update({
                    "capital_allocation": target_alloc,
                    "capital_per_trade": target_cpt,
                }).eq("symbol", symbol).execute()
                action["applied"] = True
                logger.info(
                    f"[RESIZE] {symbol}: ${current_alloc:.2f} → ${target_alloc:.2f} "
                    f"(Δ ${delta:+.2f}, cpt ${target_cpt:.2f})"
                )
            except Exception as e:
                action["applied"] = False
                action["error"] = str(e)
                logger.error(f"[RESIZE] {symbol}: UPDATE failed — {e}")

        resize_actions.append(action)

    return resize_actions


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
            buy_pct, _atr_sell_pct = _adaptive_steps(coin, signal)
            # 45b: sell_pct is NOT ATR-derived — it's the post-greed-decay
            # salvage threshold (see _compute_sell_pct_salvage). The ATR
            # value is intentionally discarded.
            sell_pct = _compute_sell_pct_salvage(config.get("greed_decay_tiers"))

            # capital_per_trade: allocation / tier_lots, capped at
            # tf_capital_per_trade_cap_usd, floor $6 (> Binance min_notional $5).
            # 45c: use per-tier lot count from snapshot so T3 = $25 / 2 = $12.50,
            # T2 = $35 / 3 = $11.67, T1 = $40 / 4 = $10.00. Falls back to the
            # global tf_lots_per_coin if snapshot lacks tier_lots (legacy
            # shadow scans or pre-45c decisions).
            lots_per_coin = int(
                snapshot.get("tier_lots") or config.get("tf_lots_per_coin", 4)
            )
            cpt_cap = float(config.get("tf_capital_per_trade_cap_usd", 50))
            capital_per_trade = min(cpt_cap, max(6.0, round(capital / lots_per_coin, 2)))

            # 42a + 45c: multi-lot entry on first cycle + greed decay TP from
            # allocation moment. T1/T2 keep 1 lot in reserve (initial = lots-1),
            # T3 fires everything at entry. initial_lots is consumed (reset to 0)
            # by grid_runner after the market buys fire; allocated_at anchors the
            # greed decay clock (reset on every re-ALLOCATE, including SWAPs).
            initial_lots = int(
                snapshot.get("tier_initial_lots")
                if snapshot.get("tier_initial_lots") is not None
                else config.get("tf_initial_lots", 3)
            )
            allocated_at_iso = datetime.now(timezone.utc).isoformat()

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
                # 39a: TF is a rotator, not a holder — re-align the reference
                # price after 1 hour of no trades (vs. 24h manual default) so
                # a fresh buy lands at current market instead of a stale level.
                "idle_reentry_hours": 1,
                # 42a:
                "initial_lots": initial_lots,
                "allocated_at": allocated_at_iso,
                # 45c: freeze volume tier so subsequent volume changes don't
                # re-tier active coin. Read back by SWAP guard + active_tier_map.
                "volume_tier": snapshot.get("volume_tier"),
                # 45g invariant: tf_exit_after_n_override is intentionally NOT
                # listed here. It is a CEO-set policy field that must survive
                # ALLOCATE/UPDATE cycles. INSERT path leaves it as DB default
                # (NULL); UPDATE path leaves whatever value the CEO set.
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
                log_event(
                    severity="info",
                    category="tf",
                    event="tf_allocate",
                    symbol=symbol,
                    message=f"TF ALLOCATE {symbol} ${capital:.0f} (signal={signal}, strength={coin.get('signal_strength', 0):.2f})",
                    details={
                        "capital": capital,
                        "capital_per_trade": capital_per_trade,
                        "buy_pct": buy_pct,
                        "sell_pct": sell_pct,
                        "signal": signal,
                        "signal_strength": coin.get("signal_strength", 0),
                        "update": bool(existing.data),
                    },
                )
            except Exception as e:
                # 44b: the bot_config INSERT/UPDATE just failed, but
                # trend_decisions_log was already written with
                # action_taken='ALLOCATE' by the caller (log_decisions in
                # trend_follower.py runs BEFORE apply_allocations). Without
                # correction, this produces a "ghost" bot: the decision log
                # says we allocated, but no grid_runner ever starts because
                # bot_config doesn't have the row.
                #
                # Retrocede the decision row: mark it ALLOCATE_FAILED and
                # append the DB error to the reason. ALLOCATE_FAILED is
                # whitelisted in the trend_decisions_log.action_taken CHECK
                # constraint (migration applied by CEO ahead of this code).
                err_str = str(e)[:240]
                logger.error(f"[ALLOCATOR] Failed to apply ALLOCATE for {symbol}: {err_str}")
                try:
                    supabase.table("trend_decisions_log").update({
                        "action_taken": "ALLOCATE_FAILED",
                        "reason": f"bot_config write failed: {err_str}",
                    }).eq("scan_timestamp", d["scan_timestamp"]).eq("symbol", symbol).execute()
                except Exception as upd_err:
                    logger.warning(
                        f"[ALLOCATOR] Also failed to retrocede trend_decisions_log "
                        f"for {symbol}: {upd_err}"
                    )
                # Send a Telegram alert so the CEO sees the failure in real
                # time. Lazy import the notifier to keep allocator.py free
                # of a hard dependency (and to preserve existing unit tests
                # that don't mock a Telegram client).
                try:
                    from utils.telegram_notifier import SyncTelegramNotifier
                    SyncTelegramNotifier().send_message(
                        f"🚨 <b>ALLOCATE FAILED: {symbol}</b>\n"
                        f"<code>{err_str}</code>\n"
                        f"Decision retroceded to ALLOCATE_FAILED."
                    )
                except Exception as tg_err:
                    logger.warning(f"[ALLOCATOR] Telegram alert failed: {tg_err}")

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
                # 43a: reason is attached on the decision dict from the
                # scanner (BEARISH / SWAP / etc). Thread it into the event.
                log_event(
                    severity="info",
                    category="tf",
                    event="tf_deallocate",
                    symbol=symbol,
                    message=f"TF DEALLOCATE {symbol}: {d.get('reason', '')[:120]}",
                    details={"reason": d.get("reason", "")},
                )
            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply DEALLOCATE for {symbol}: {e}")
