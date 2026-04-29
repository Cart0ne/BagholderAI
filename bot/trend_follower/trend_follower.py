"""
BagHolderAI - Trend Follower (Shadow Mode)
Scans crypto markets, detects trends, decides allocations.
In shadow mode: analyzes and reports via Telegram, but does NOT
write to bot_config or affect running grid bots.

Usage:
    python3.13 -m bot.trend_follower.trend_follower
"""

import signal
import time
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.trend")


def _sigterm_to_keyboard_interrupt(signum, frame):
    """Map SIGTERM to KeyboardInterrupt so the farewell path (Telegram
    message + clean exit) runs when the orchestrator or any external
    supervisor terminates us."""
    raise KeyboardInterrupt()

from bot.exchange import create_exchange
from db.client import get_client
from db.event_logger import log_event
from utils.telegram_notifier import SyncTelegramNotifier
from utils.exchange_filters import fetch_and_cache_filters

from bot.trend_follower.scanner import scan_top_coins, fmt_volume, fetch_rsi_1h
from bot.trend_follower.classifier import classify_signal
from bot.trend_follower.allocator import (
    decide_allocations, apply_allocations, resize_active_allocations,
)
from bot.trend_follower.floating import compute_tf_floating_cash
from bot.trend_follower.counterfactual import run_counterfactual_check


# ---------------------------------------------------------------------------
# Default config (used if trend_config table is empty)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "trend_follower_enabled": True,
    "dry_run": True,
    "scan_interval_hours": 4,
    "scan_top_n": 50,
    "max_active_grids": 5,
}

DEFAULT_TIERS = [
    {"symbol": "BTC", "tier": 1, "max_allocation_percent": 40, "is_override": False},
    {"symbol": "ETH", "tier": 1, "max_allocation_percent": 40, "is_override": False},
    {"symbol": "SOL", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "ADA", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "AVAX", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "DOGE", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "DOT", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "LINK", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "MATIC", "tier": 2, "max_allocation_percent": 20, "is_override": False},
    {"symbol": "XRP", "tier": 2, "max_allocation_percent": 20, "is_override": False},
]


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def load_trend_config(supabase) -> dict:
    """Load trend follower config from Supabase. Falls back to defaults."""
    try:
        result = supabase.table("trend_config").select("*").limit(1).execute()
        if result.data:
            cfg = result.data[0]
            # Merge with defaults for any missing keys
            return {**DEFAULT_CONFIG, **{k: v for k, v in cfg.items() if v is not None}}
    except Exception as e:
        logger.warning(f"Could not load trend_config: {e}")
    return dict(DEFAULT_CONFIG)


def load_coin_tiers(supabase) -> dict:
    """Load coin tiers from Supabase. Seeds defaults if table is empty."""
    try:
        result = supabase.table("coin_tiers").select("*").execute()
        if result.data:
            return {row["symbol"]: row for row in result.data}
    except Exception as e:
        logger.warning(f"Could not load coin_tiers: {e}")

    # Seed defaults
    logger.info("coin_tiers table empty — seeding defaults")
    try:
        for tier in DEFAULT_TIERS:
            supabase.table("coin_tiers").upsert(tier, on_conflict="symbol").execute()
        logger.info(f"Seeded {len(DEFAULT_TIERS)} default coin tiers")
        return {t["symbol"]: t for t in DEFAULT_TIERS}
    except Exception as e:
        logger.warning(f"Failed to seed coin_tiers: {e}")
        return {t["symbol"]: t for t in DEFAULT_TIERS}


def load_exchange_filters(supabase, exchange=None) -> dict:
    """
    Load exchange filters from Supabase cache.
    If empty and exchange provided, fetch from Binance and cache.
    Returns dict keyed by symbol.
    """
    try:
        result = supabase.table("exchange_filters").select("*").execute()
        if result.data:
            return {row["symbol"]: row for row in result.data}
    except Exception as e:
        logger.warning(f"Could not load exchange_filters: {e}")

    if exchange:
        logger.info("exchange_filters empty — fetching from Binance")
        try:
            # Fetch for common pairs
            exchange.load_markets()
            usdt_symbols = [s for s in exchange.markets if s.endswith("/USDT")][:100]
            fetch_and_cache_filters(exchange, usdt_symbols, supabase_client=supabase)
            # Reload
            result = supabase.table("exchange_filters").select("*").execute()
            if result.data:
                return {row["symbol"]: row for row in result.data}
        except Exception as e:
            logger.warning(f"Failed to fetch/cache exchange filters: {e}")

    return {}


def load_current_allocations(supabase) -> list[dict]:
    """Load active bot configs from Supabase. Includes updated_at/created_at
    so the allocator's SWAP cooldown gate can compute held hours."""
    try:
        result = supabase.table("bot_config").select(
            "symbol,is_active,capital_allocation,managed_by,updated_at,created_at,volume_tier"
        ).execute()
        return [r for r in (result.data or []) if r.get("is_active")]
    except Exception as e:
        logger.warning(f"Could not load bot_config: {e}")
        return []


def sum_total_capital(supabase) -> float:
    """Sum total capital from all bot configs."""
    try:
        result = supabase.table("bot_config").select("capital_allocation").execute()
        return sum(float(r.get("capital_allocation", 0)) for r in (result.data or []))
    except Exception as e:
        logger.warning(f"Could not sum capital: {e}")
        return 500.0  # fallback to MAX_CAPITAL


def log_decisions(supabase, decisions: list[dict], is_shadow: bool):
    """Log decisions to trend_decisions_log. Only logs actionable decisions."""
    logged = 0
    for d in decisions:
        action = d["action_taken"]
        # Skip most SKIPs unless they're FILTER_FAILs
        if action == "SKIP" and "FILTER_FAIL" not in d.get("reason", ""):
            continue

        try:
            supabase.table("trend_decisions_log").insert({
                "scan_timestamp": d["scan_timestamp"],
                "symbol": d["symbol"],
                "ema_fast_value": d.get("ema_fast", 0),
                "ema_slow_value": d.get("ema_slow", 0),
                "rsi_value": d.get("rsi", 0),
                "atr_value": d.get("atr", 0),
                "signal": d.get("signal", ""),
                "signal_strength": d.get("signal_strength", 0),
                "action_taken": action,
                "is_shadow": is_shadow,
                "reason": d.get("reason", ""),
                "config_written": d.get("config_snapshot"),
            }).execute()
            logged += 1
        except Exception as e:
            logger.warning(f"Failed to log decision for {d['symbol']}: {e}")

    logger.info(f"Logged {logged} decisions to trend_decisions_log (shadow={is_shadow})")


def log_full_scan(supabase, coins: list[dict]):
    """Log all scanned coins to trend_scans for debugging. Temporary."""
    scan_ts = datetime.now(timezone.utc).isoformat()
    rows = []
    for c in coins:
        rows.append({
            "scan_timestamp": scan_ts,
            "symbol": c["symbol"],
            "rank": c.get("rank", 0),
            "tier": c.get("tier", "?"),
            "price": c.get("price", 0),
            "volume_24h": c.get("volume_24h", 0),
            "ema_fast": c.get("ema_fast", 0),
            "ema_slow": c.get("ema_slow", 0),
            "rsi": c.get("rsi", 0),
            "atr": c.get("atr", 0),
            "atr_avg": c.get("atr_avg", 0),
            "signal": c.get("signal", "NO_SIGNAL"),
            "signal_strength": c.get("signal_strength", 0),
        })

    try:
        supabase.table("trend_scans").insert(rows).execute()
        logger.info(f"Logged {len(rows)} coins to trend_scans")
    except Exception as e:
        logger.warning(f"Failed to log scan data: {e}")


def cleanup_old_trend_scans(supabase, retention_days: int = 14) -> int:
    """Delete trend_scans rows older than retention_days. Returns rows deleted.

    47c: trend_scans is "temporary for debugging" (see log_full_scan) and is
    the largest contributor to DB growth — ~50 rows per scan. With scan_interval
    halved (1h → 30min) we double the daily volume, so a periodic prune keeps
    the Supabase Free tier (500 MB) viable for the foreseeable future.

    Best-effort: never raises. Failure logs a warning and the loop proceeds.
    """
    try:
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(days=retention_days)).isoformat()
        # PostgREST DELETE returns the deleted rows when prefer=return=representation;
        # supabase-py defaults to that, so result.data is the deleted set.
        result = (supabase.table("trend_scans")
                  .delete()
                  .lt("scan_timestamp", cutoff)
                  .execute())
        deleted = len(result.data or [])
        if deleted > 0:
            logger.info(
                f"trend_scans cleanup: removed {deleted} row(s) older than "
                f"{retention_days}d (cutoff {cutoff})"
            )
        return deleted
    except Exception as e:
        logger.warning(f"trend_scans cleanup failed: {e}")
        return 0


# ---------------------------------------------------------------------------
# Telegram reporting
# ---------------------------------------------------------------------------

def send_scan_report(notifier: SyncTelegramNotifier, coins: list[dict],
                     current_allocs: list[dict], config: dict,
                     tf_budget_nominal: float = 100.0,
                     tf_floating: float = 0.0):
    """Send tiered scan report to Telegram."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

    bullish = sum(1 for c in coins if c.get("signal") == "BULLISH")
    bearish = sum(1 for c in coins if c.get("signal") == "BEARISH")
    sideways = sum(1 for c in coins if c.get("signal") == "SIDEWAYS")
    no_signal = sum(1 for c in coins if c.get("signal") == "NO_SIGNAL")

    active_count = len([a for a in current_allocs if a.get("is_active")])
    max_grids = config.get("tf_max_coins") or config.get("max_active_grids", 5)
    deployed = sum(float(a.get("capital_allocation", 0)) for a in current_allocs if a.get("is_active"))

    shadow_tag = "[SHADOW] " if config.get("dry_run") else ""

    # 45c: volume-based tier labels (keys A/B/C kept for backwards compat).
    # NB: Telegram parse_mode='HTML' interprets '<' as a tag-opener, so
    # we escape it as '&lt;' to avoid "unsupported start tag" errors.
    tier_names = {
        "A": "🔵 Tier 1 (≥$100M vol)",
        "B": "🟡 Tier 2 ($20M–$100M)",
        "C": "🔴 Tier 3 (&lt;$20M)",
    }
    tier_sections = []

    for tier_key in ["A", "B", "C"]:
        tier_coins = [c for c in coins if c.get("tier") == tier_key]
        tier_count = len(tier_coins)
        # Only bullish coins are ALLOCATE candidates, so the teaser should
        # show bullish only. Previous behavior mixed bullish/bearish/no-signal
        # in top-2 by strength, which made the final ALLOCATE look like it
        # came from nowhere when the bullish ranking didn't match the top-2.
        bullish_coins = [c for c in tier_coins if c.get("signal") == "BULLISH"]
        tier_bullish = len(bullish_coins)

        top2 = sorted(bullish_coins, key=lambda c: c.get("signal_strength", 0), reverse=True)[:2]

        lines = []
        for c in top2:
            sym = c["symbol"].split("/")[0]
            strength = c.get("signal_strength", 0)
            rsi = c.get("rsi", 0)
            ema_dir = "cross up" if c.get("ema_fast", 0) > c.get("ema_slow", 0) else "cross down"
            vol = fmt_volume(c.get("volume_24h", 0)) if "volume_24h" in c else "?"
            lines.append(
                f"  {sym} — BULLISH ({strength:.1f}) — RSI {rsi:.0f}, EMA {ema_dir} — Vol {vol}"
            )
        if not lines:
            lines.append("  (no bullish candidates)")

        header = f"{tier_names.get(tier_key, tier_key)} ({tier_count} coins, {tier_bullish} bullish)"
        tier_sections.append(header + "\n" + "\n".join(lines))

    # 45e v2: BULLISH coins blocked by entry distance filter — show up to 5
    # so Max can see calibration of the threshold.
    max_dist = float(config.get("tf_entry_max_distance_pct") or 0)
    distance_block_lines = []
    if max_dist > 0:
        filtered = [
            c for c in coins
            if c.get("signal") == "BULLISH"
            and float(c.get("distance_from_ema_pct", 0) or 0) > max_dist
        ]
        if filtered:
            filtered.sort(key=lambda c: c.get("distance_from_ema_pct", 0), reverse=True)
            distance_block_lines.append(
                f"\n⛔ <b>Entry distance blocked</b> ({len(filtered)} coin"
                + ("s" if len(filtered) != 1 else "")
                + f", max {max_dist:.0f}% above EMA20):"
            )
            for c in filtered[:5]:
                sym = c["symbol"].split("/")[0]
                d = c.get("distance_from_ema_pct", 0)
                distance_block_lines.append(f"  • {sym}: +{d:.1f}% above EMA20")

    # 51a: BULLISH coins blocked by RSI 1h overheat filter — same display
    # pattern as the distance filter. Skipped when feature disabled or no
    # coin trips it.
    rsi_1h_max_report = float(config.get("tf_rsi_1h_max") or 0)
    if rsi_1h_max_report > 0:
        overheat = [
            c for c in coins
            if c.get("signal") == "BULLISH"
            and c.get("rsi_1h") is not None
            and c["rsi_1h"] > rsi_1h_max_report
        ]
        if overheat:
            overheat.sort(key=lambda c: c.get("rsi_1h", 0), reverse=True)
            distance_block_lines.append(
                f"\n🌡️ <b>RSI 1h overheat blocked</b> ({len(overheat)} coin"
                + ("s" if len(overheat) != 1 else "")
                + f", max RSI 1h {rsi_1h_max_report:.0f}):"
            )
            for c in overheat[:5]:
                sym = c["symbol"].split("/")[0]
                distance_block_lines.append(f"  • {sym}: RSI 1h = {c['rsi_1h']:.0f}")

    text = (
        f"{shadow_tag}📊 <b>TREND SCAN — {now}</b>\n"
        f"\n"
        f"Scanned: {len(coins)} coins (stablecoins excluded)\n"
        f"Bullish: {bullish} | Bearish: {bearish} | Sideways: {sideways} | No signal: {no_signal}\n"
        f"\n"
        f"<b>Top 2 bullish per tier:</b>\n"
        + "\n\n".join(tier_sections) + "\n"
        + "\n".join(distance_block_lines) + ("\n" if distance_block_lines else "")
        + f"\n"
        f"Active grids: {active_count}/{max_grids}\n"
        f"Capital deployed: ${deployed:.0f}\n"
        f"TF budget: ${tf_budget_nominal:.0f} base"
        + (f" + ${tf_floating:.2f} floating = ${tf_budget_nominal + tf_floating:.2f} effective"
           if abs(tf_floating) > 0.01 else "")
    )
    notifier.send_message(text)


def send_tf_decision(notifier: SyncTelegramNotifier, decision: dict, is_shadow: bool):
    """Send an ALLOCATE or DEALLOCATE decision to Telegram."""
    action = decision["action_taken"]
    symbol = decision["symbol"]
    signal = decision.get("signal", "?")
    strength = decision.get("signal_strength", 0)
    reason = decision.get("reason", "")

    if action == "ALLOCATE":
        emoji = "🟢"
        verb = "WOULD ALLOCATE" if is_shadow else "ALLOCATE"
        snap = decision.get("config_snapshot", {})
        capital = snap.get("capital_allocation", 0)
        tier = snap.get("tier", "?")
        max_pct = snap.get("max_allocation_pct", "?")
        text = (
            f"{'[SHADOW] ' if is_shadow else ''}{emoji} <b>{verb} — {symbol}</b>\n"
            f"Trend: {signal} | Strength: {strength:.1f}\n"
            f"Capital: ${capital:.0f} ({max_pct}% — T{tier})\n"
        )
        if is_shadow:
            text += "⚠️ Shadow mode — no config written"
    elif action == "DEALLOCATE":
        # 39e: in LIVE mode, suppress this notification. The grid_runner
        # sends a single consolidated "LIQUIDATED + cycle summary" Telegram
        # when _force_liquidate actually closes the position (tens of
        # seconds later). Two messages ("decision" + "result") were
        # redundant — the CEO can't intervene in the gap anyway. Shadow
        # mode still fires because there's no subsequent liquidation path.
        if not is_shadow:
            return
        emoji = "🔴"
        verb = "WOULD DEALLOCATE"
        text = (
            f"[SHADOW] {emoji} <b>{verb} — {symbol}</b>\n"
            f"Reason: {reason}\n"
            f"⚠️ Shadow mode — grid not stopped"
        )
    else:
        return

    notifier.send_message(text)


def send_resize_report(notifier: SyncTelegramNotifier, resize_actions: list[dict],
                       is_shadow: bool):
    """Send a consolidated resize notification for the scan (Phase 2 compound)."""
    if not resize_actions:
        return

    tag = "[SHADOW] " if is_shadow else ""
    verb = "WOULD RESIZE" if is_shadow else "RESIZED"
    lines = []
    for a in resize_actions:
        sym = a["symbol"].split("/")[0]
        arrow = "↑" if a["delta"] > 0 else "↓"
        lines.append(
            f"  {arrow} {sym}: ${a['current_alloc']:.2f} → ${a['target_alloc']:.2f} "
            f"(cpt ${a['target_cpt']:.2f})"
        )
    text = (
        f"{tag}⚙️ <b>{verb} — TF compound propagate</b>\n"
        + "\n".join(lines)
    )
    if is_shadow:
        text += "\n⚠️ Shadow mode — bot_config not updated"
    notifier.send_message(text)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_trend_follower():
    """Main loop for the Trend Follower."""
    # SIGTERM → KeyboardInterrupt so the existing shutdown path runs.
    signal.signal(signal.SIGTERM, _sigterm_to_keyboard_interrupt)

    exchange = create_exchange()
    exchange.load_markets()
    notifier = SyncTelegramNotifier()
    supabase = get_client()

    # Load config
    config = load_trend_config(supabase)

    if not config.get("trend_follower_enabled", True):
        logger.info("Trend Follower disabled (trend_follower_enabled=false). Exiting.")
        notifier.send_message("🛑 Trend Follower disabled. Exiting.")
        return

    logger.info(f"Trend Follower starting — dry_run={config.get('dry_run', True)}")
    # Startup notification suppressed: the orchestrator's single summary
    # message already confirms "Trend Follower: on/off". Log still carries
    # full config details for audit.

    # 39g: track safety params across cycles so we can Telegram-notify
    # the CEO when /tf UI edits them mid-run. Mirrors how
    # SupabaseConfigReader alerts on bot_config changes.
    _SAFETY_KEYS = (
        "tf_stop_loss_pct", "tf_take_profit_pct", "scan_interval_hours",
        "tf_profit_lock_enabled", "tf_profit_lock_pct",  # 45f
        # Lacuna pre-esistente colmata: questi parametri cambiano materialmente
        # il comportamento operativo del TF e meritano l'alert Telegram tanto
        # quanto SL/TP. dry_run è il piu critico (switch shadow vs live).
        "dry_run",
        "tf_entry_max_distance_pct",
        "tf_stop_loss_cooldown_hours",
        "tf_initial_lots",
        "min_allocate_strength",
    )
    prev_safety = {k: config.get(k) for k in _SAFETY_KEYS}

    # 47c: track last cleanup so trend_scans prune runs ~1×/day regardless of
    # scan_interval. Initial value = epoch so the first scan after a restart
    # always triggers a cleanup (catches up on whatever piled up while the
    # bot was down).
    last_cleanup_at: datetime | None = None

    # Main loop
    while True:
        try:
            # Reload config each cycle (allows hot changes)
            config = load_trend_config(supabase)

            # 39g: detect safety param edits done via /tf UI and Telegram
            # the delta. Config reloads every scan (default 1h), so the
            # notification can lag up to one scan interval.
            safety_changes = []
            for k in _SAFETY_KEYS:
                new_val = config.get(k)
                old_val = prev_safety.get(k)
                if old_val is not None and new_val != old_val:
                    safety_changes.append((k, old_val, new_val))
            if safety_changes:
                lines = ["⚙️ <b>CONFIG CHANGE DETECTED — trend_config</b>"]
                for key, old_val, new_val in safety_changes:
                    lines.append(f"{key}: {old_val} → {new_val}")
                try:
                    notifier.send_message("\n".join(lines))
                except Exception as e:
                    logger.warning(f"Telegram alert for trend_config change failed: {e}")
                # 43a: single event per scan-diff, groups all changed safety keys.
                log_event(
                    severity="info",
                    category="config",
                    event="config_changed_trend_config",
                    symbol=None,
                    message=f"trend_config changed: {len(safety_changes)} field(s)",
                    details={
                        "changes": [
                            {"key": k, "old": str(o), "new": str(n)}
                            for k, o, n in safety_changes
                        ],
                    },
                )
            prev_safety = {k: config.get(k) for k in _SAFETY_KEYS}

            if not config.get("trend_follower_enabled", True):
                logger.info("Trend Follower disabled mid-run. Exiting.")
                notifier.send_message("🛑 Trend Follower stopped (disabled via config).")
                break

            # Scan — 45c: pass tier thresholds so scanner and allocator
            # agree on volume boundaries (single source of truth in trend_config).
            coins = scan_top_coins(
                exchange,
                config.get("scan_top_n", 50),
                tier1_min_volume=float(config.get("tf_tier1_min_volume", 100_000_000)),
                tier2_min_volume=float(config.get("tf_tier2_min_volume", 20_000_000)),
            )

            # Classify
            for coin in coins:
                classify_signal(coin, config)

            # Log full scan to trend_scans (temporary — for debugging tier splits)
            log_full_scan(supabase, coins)

            # Load context
            coin_tiers = load_coin_tiers(supabase)
            exchange_filters = load_exchange_filters(supabase, exchange=exchange)
            current_allocs = load_current_allocations(supabase)

            # TF operates only on its own budget and its own allocations.
            # Manual bots (BTC/SOL/BONK) are excluded from the TF universe so
            # decide_allocations never sees them as "existing" and never tries
            # to DEALLOCATE them.
            tf_allocs = [a for a in current_allocs if a.get("managed_by") == "trend_follower"]
            tf_budget_nominal = float(config.get("tf_budget", 100))

            # Session 36g Phase 1: compound retained profits from deallocated
            # TF bots into the effective budget. Only fully-liquidated dead
            # bots count.
            tf_floating, floating_breakdown = compute_tf_floating_cash(supabase)
            tf_raw = tf_budget_nominal + tf_floating

            # Phase 2: hard sanity cap (CEO: $300 = 3× tf_budget nominal).
            # If compound exceeds the cap, clamp and log for visibility.
            sanity_cap = float(config.get("tf_sanity_cap_usd", 300))
            tf_total_capital = min(tf_raw, sanity_cap)
            tf_capped = tf_raw > sanity_cap

            if floating_breakdown:
                parts = [
                    f"{b['symbol'].split('/')[0]} ${b['retained']:+.2f}"
                    for b in floating_breakdown
                ]
                cap_note = f" (capped from ${tf_raw:.2f} at ${sanity_cap:.0f})" if tf_capped else ""
                logger.info(
                    f"TF budget: ${tf_budget_nominal:.2f} base + "
                    f"${tf_floating:.2f} floating = ${tf_total_capital:.2f} effective"
                    f"{cap_note} [{' · '.join(parts)}]"
                )
            else:
                logger.info(
                    f"TF budget: ${tf_total_capital:.2f} (no floating)"
                )

            if tf_capped:
                logger.warning(
                    f"TF compound hit sanity cap: raw ${tf_raw:.2f} > cap "
                    f"${sanity_cap:.0f}. Raise tf_sanity_cap_usd in trend_config if intentional."
                )

            # 51a: enrich BULLISH candidates with RSI(14) on 1h candles before
            # the allocator runs. Catches sharp intraday pumps that the 4h
            # distance filter (45e) misses (DOGE 29/04: ALLOCATE at the
            # 30-day high → SL the same day). Only BULLISH coins are queried
            # to keep API cost flat (10-20 fetches vs 50). Fail-open: if a
            # fetch fails, the coin enters allocator without rsi_1h and the
            # allocator gate treats it as "missing data → pass".
            rsi_1h_max = float(config.get("tf_rsi_1h_max") or 0)
            if rsi_1h_max > 0:
                bullish = [c for c in coins if c.get("signal") == "BULLISH"]
                logger.info(f"[51a] Fetching 1h RSI for {len(bullish)} BULLISH candidates (threshold {rsi_1h_max:.0f})")
                for coin in bullish:
                    rsi_val = fetch_rsi_1h(exchange, coin["symbol"])
                    coin["rsi_1h"] = rsi_val
                    time.sleep(0.2)  # rate limit — Binance public API

            # Decide allocations (exchange + supabase enable on-demand rescan
            # and the SWAP profit gate; see allocator 36e v2).
            decisions = decide_allocations(
                coins, tf_allocs, coin_tiers,
                exchange_filters, config, tf_total_capital,
                exchange=exchange, supabase=supabase,
            )

            # Phase 2: resize active TF bots so compound propagates to per-bot
            # capital_allocation / capital_per_trade. Runs AFTER rotation
            # decisions (pending_liquidation bots are excluded inside) and
            # BEFORE new ALLOCATEs so the fresh equal-split includes survivors.
            is_shadow = config.get("dry_run", True)
            resize_actions = resize_active_allocations(
                supabase, tf_allocs, tf_total_capital, config,
                is_shadow=is_shadow,
            )

            # Log to Supabase
            log_decisions(supabase, decisions, is_shadow=is_shadow)

            # 47a: counterfactual tracker — for entry_distance_skip events
            # >=24h old that aren't yet recorded, fetch the +24h price and
            # peak so we can later compare "what we skipped" vs "what would
            # have happened". Best-effort: never raises, never blocks the
            # allocation flow. Runs once per scan cycle.
            try:
                run_counterfactual_check(exchange, supabase=supabase)
            except Exception as e:
                logger.warning(f"counterfactual_check raised unexpectedly: {e}")

            # 47c: prune old trend_scans rows once per day. trend_scans is the
            # largest table by row count (~50/scan); without a TTL it would
            # eat the Supabase Free 500 MB allowance over time. 14 days is
            # enough to investigate any "what happened on day X?" question.
            now = datetime.now(timezone.utc)
            if last_cleanup_at is None or (now - last_cleanup_at).total_seconds() >= 86400:
                cleanup_old_trend_scans(supabase, retention_days=14)
                last_cleanup_at = now

            # Report to Telegram (TF-only view: active/deployed count reflects TF's universe)
            send_scan_report(notifier, coins, tf_allocs, config,
                             tf_budget_nominal=tf_budget_nominal,
                             tf_floating=tf_floating)
            for d in decisions:
                if d["action_taken"] in ("ALLOCATE", "DEALLOCATE"):
                    send_tf_decision(notifier, d, is_shadow=is_shadow)
            if resize_actions:
                send_resize_report(notifier, resize_actions, is_shadow=is_shadow)

            # Apply allocations if live mode. Pass the classified coin dict
            # so _adaptive_steps sees fresh ATR/price at allocation time.
            if not is_shadow:
                coin_lookup = {c["symbol"]: c for c in coins}
                apply_allocations(supabase, decisions, config, coin_lookup=coin_lookup)

            scan_interval = config.get("scan_interval_hours", 4)
            logger.info(f"Scan complete. Sleeping {scan_interval}h...")
            time.sleep(scan_interval * 3600)

        except KeyboardInterrupt:
            logger.info("Trend Follower stopped by user.")
            # Farewell suppressed: covered by "Orchestrator shutting down"
            # when shutdown is driven by the orchestrator.
            break
        except Exception as e:
            logger.error(f"Trend Follower error: {e}", exc_info=True)
            notifier.send_message(f"🚨 <b>TREND FOLLOWER ERROR</b>\n<code>{str(e)[:300]}</code>")
            time.sleep(300)  # 5 min backoff on error


if __name__ == "__main__":
    run_trend_follower()
