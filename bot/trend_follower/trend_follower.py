"""
BagHolderAI - Trend Follower (Shadow Mode)
Scans crypto markets, detects trends, decides allocations.
In shadow mode: analyzes and reports via Telegram, but does NOT
write to bot_config or affect running grid bots.

Usage:
    python3.13 -m bot.trend_follower.trend_follower
"""

import time
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.trend")

from bot.exchange import create_exchange
from db.client import get_client
from utils.telegram_notifier import SyncTelegramNotifier
from utils.exchange_filters import fetch_and_cache_filters

from bot.trend_follower.scanner import scan_top_coins, fmt_volume
from bot.trend_follower.classifier import classify_signal
from bot.trend_follower.allocator import decide_allocations


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
    """Load active bot configs from Supabase."""
    try:
        result = supabase.table("bot_config").select(
            "symbol,is_active,capital_allocation,managed_by"
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


# ---------------------------------------------------------------------------
# Telegram reporting
# ---------------------------------------------------------------------------

def send_scan_report(notifier: SyncTelegramNotifier, coins: list[dict],
                     current_allocs: list[dict], config: dict):
    """Send tiered scan report to Telegram."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

    bullish = sum(1 for c in coins if c.get("signal") == "BULLISH")
    bearish = sum(1 for c in coins if c.get("signal") == "BEARISH")
    sideways = sum(1 for c in coins if c.get("signal") == "SIDEWAYS")
    no_signal = sum(1 for c in coins if c.get("signal") == "NO_SIGNAL")

    active_count = len([a for a in current_allocs if a.get("is_active")])
    max_grids = config.get("max_active_grids", 5)
    deployed = sum(float(a.get("capital_allocation", 0)) for a in current_allocs if a.get("is_active"))

    shadow_tag = "[SHADOW] " if config.get("dry_run") else ""

    tier_names = {"A": "🔵 Large cap", "B": "🟡 Mid cap", "C": "🔴 Small cap"}
    tier_sections = []

    for tier_key in ["A", "B", "C"]:
        tier_coins = [c for c in coins if c.get("tier") == tier_key]
        tier_count = len(tier_coins)
        tier_bullish = sum(1 for c in tier_coins if c.get("signal") == "BULLISH")

        top2 = sorted(tier_coins, key=lambda c: c.get("signal_strength", 0), reverse=True)[:2]

        lines = []
        for c in top2:
            sym = c["symbol"].split("/")[0]
            sig = c.get("signal", "?")
            strength = c.get("signal_strength", 0)
            rsi = c.get("rsi", 0)
            ema_dir = "cross up" if c.get("ema_fast", 0) > c.get("ema_slow", 0) else "cross down"
            vol = fmt_volume(c.get("volume_24h", 0)) if "volume_24h" in c else "?"
            lines.append(
                f"  {sym} — {sig} ({strength:.1f}) — RSI {rsi:.0f}, EMA {ema_dir} — Vol {vol}"
            )

        header = f"{tier_names.get(tier_key, tier_key)} ({tier_count} coins, {tier_bullish} bullish)"
        tier_sections.append(header + "\n" + "\n".join(lines))

    text = (
        f"{shadow_tag}📊 <b>TREND SCAN — {now}</b>\n"
        f"\n"
        f"Scanned: {len(coins)} coins (stablecoins excluded)\n"
        f"Bullish: {bullish} | Bearish: {bearish} | Sideways: {sideways} | No signal: {no_signal}\n"
        f"\n"
        f"<b>Top 2 per tier:</b>\n"
        + "\n\n".join(tier_sections) + "\n"
        f"\n"
        f"Active grids: {active_count}/{max_grids}\n"
        f"Capital deployed: ${deployed:.0f}"
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
        emoji = "🔴"
        verb = "WOULD DEALLOCATE" if is_shadow else "DEALLOCATE"
        text = (
            f"{'[SHADOW] ' if is_shadow else ''}{emoji} <b>{verb} — {symbol}</b>\n"
            f"Reason: {reason}\n"
        )
        if is_shadow:
            text += "⚠️ Shadow mode — grid not stopped"
    else:
        return

    notifier.send_message(text)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_trend_follower():
    """Main loop for the Trend Follower."""
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
    notifier.send_message(
        f"🧠 <b>Trend Follower started</b>\n"
        f"Mode: {'SHADOW (dry run)' if config.get('dry_run') else 'LIVE'}\n"
        f"Scan interval: {config.get('scan_interval_hours', 4)}h\n"
        f"Max grids: {config.get('max_active_grids', 5)}"
    )

    # Main loop
    while True:
        try:
            # Reload config each cycle (allows hot changes)
            config = load_trend_config(supabase)

            if not config.get("trend_follower_enabled", True):
                logger.info("Trend Follower disabled mid-run. Exiting.")
                notifier.send_message("🛑 Trend Follower stopped (disabled via config).")
                break

            # Scan
            coins = scan_top_coins(exchange, config.get("scan_top_n", 50))

            # Classify
            for coin in coins:
                classify_signal(coin, config)

            # Log full scan to trend_scans (temporary — for debugging tier splits)
            log_full_scan(supabase, coins)

            # Load context
            coin_tiers = load_coin_tiers(supabase)
            exchange_filters = load_exchange_filters(supabase, exchange=exchange)
            current_allocs = load_current_allocations(supabase)
            total_capital = sum_total_capital(supabase)

            # Decide allocations
            decisions = decide_allocations(
                coins, current_allocs, coin_tiers,
                exchange_filters, config, total_capital,
            )

            # Log to Supabase
            log_decisions(supabase, decisions, is_shadow=config.get("dry_run", True))

            # Report to Telegram
            send_scan_report(notifier, coins, current_allocs, config)
            for d in decisions:
                if d["action_taken"] in ("ALLOCATE", "DEALLOCATE"):
                    send_tf_decision(notifier, d, is_shadow=config.get("dry_run", True))

            scan_interval = config.get("scan_interval_hours", 4)
            logger.info(f"Scan complete. Sleeping {scan_interval}h...")
            time.sleep(scan_interval * 3600)

        except KeyboardInterrupt:
            logger.info("Trend Follower stopped by user.")
            notifier.send_message("🛑 Trend Follower stopped (manual).")
            break
        except Exception as e:
            logger.error(f"Trend Follower error: {e}", exc_info=True)
            notifier.send_message(f"🚨 <b>TREND FOLLOWER ERROR</b>\n<code>{str(e)[:300]}</code>")
            time.sleep(300)  # 5 min backoff on error


if __name__ == "__main__":
    run_trend_follower()
