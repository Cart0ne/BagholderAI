# INTERN BRIEF — Session 35: Trend Follower v2 — Tiered Scanning

**Date:** April 14, 2026
**Priority:** HIGH
**Prerequisite:** Trend Follower shadow mode already running (Brief 31b)

---

## Context

The Trend Follower (TF) has been running in shadow mode for 2 days (10 scans). Analysis revealed three problems:

1. **Stablecoin pollution**: USDC/USDT, FDUSD/USDT, USD1/USDT etc. waste spots in the top 50. They always produce NO_SIGNAL (RSI ~50, flat EMAs).
2. **Flat ranking mixes everything**: The top-5 by signal strength is dominated by meme coins (RSI 85+, strength 39–43) while serious coins like BTC (strength 13–21) are invisible. Comparing BROCCOLI714 to BTC by signal strength is meaningless.
3. **No scan data persisted**: The 50 scanned coins disappear after each cycle — only the 3 active grid decisions are logged. No way to audit what the scanner saw.

**Solution**: Filter stablecoins, split the remaining coins into 3 volume tiers, report top 2 per tier, and temporarily log full scan data.

---

## 1. Scanner changes (`bot/trend_follower/scanner.py`)

### 1a. Add stablecoin filter

After filtering for `/USDT` pairs and before sorting, exclude stablecoins:

```python
STABLECOIN_SYMBOLS = {
    "USDC/USDT", "FDUSD/USDT", "USD1/USDT", "TUSD/USDT",
    "DAI/USDT", "PYUSD/USDT", "BUSD/USDT", "USDP/USDT",
    "EURI/USDT", "RLUSD/USDT", "U/USDT",
}

usdt_tickers = {
    k: v for k, v in tickers.items()
    if k.endswith("/USDT")
    and v.get("quoteVolume")
    and v.get("last")
    and k not in STABLECOIN_SYMBOLS
}
```

Place `STABLECOIN_SYMBOLS` as a module-level constant at the top of `scanner.py`.

### 1b. Add tier assignment

After scanning and calculating indicators, assign a `tier` field to each coin based on its rank position in the volume-sorted list. Add this AFTER the main scan loop, before returning:

```python
# Assign volume tier based on rank position
# coins list is already ordered by volume (descending) from the sorted_tickers order
for i, coin in enumerate(coins):
    coin["rank"] = i + 1
    if i < 20:
        coin["tier"] = "A"       # Top 20: blue chip + large cap
    elif i < 40:
        coin["tier"] = "B"       # Next 20: mid cap
    else:
        coin["tier"] = "C"       # Last 10: small cap / meme
```

**Important**: the `coins` list preserves insertion order from `sorted_tickers`, which is already sorted by `quoteVolume` descending. The rank is the position in that list. Do NOT re-sort after indicator calculation.

### 1c. Add `volume_24h` formatting helper (optional but useful for logs)

```python
def fmt_volume(v: float) -> str:
    """Format volume for display: $1.2B, $340M, $5.6M"""
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:.0f}"
```

---

## 2. Classifier changes (`bot/trend_follower/classifier.py`)

**No changes needed.** The classifier already works correctly — it assigns `signal` and `signal_strength` to each coin. Tier assignment happens in the scanner, not the classifier.

---

## 3. Telegram report changes (`bot/trend_follower/trend_follower.py`)

### 3a. Replace `send_scan_report` function

The current report shows a flat top-5 by signal strength. Replace it with a tiered report showing top 2 per tier.

Find the `send_scan_report` function in `trend_follower.py` and replace it entirely:

```python
def send_scan_report(notifier, coins, current_allocs, config):
    """Send tiered scan report to Telegram."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

    bullish = sum(1 for c in coins if c.get("signal") == "BULLISH")
    bearish = sum(1 for c in coins if c.get("signal") == "BEARISH")
    sideways = sum(1 for c in coins if c.get("signal") == "SIDEWAYS")
    no_signal = sum(1 for c in coins if c.get("signal") == "NO_SIGNAL")

    active_count = len([a for a in current_allocs if a.get("is_active")])
    max_grids = config.get("max_active_grids", 5)
    deployed = sum(float(a.get("capital_allocation", 0)) for a in current_allocs if a.get("is_active"))

    shadow_tag = "[SHADOW] " if config.get("dry_run") else ""

    # Group coins by tier, pick top 2 per tier by signal_strength
    tier_names = {"A": "🔵 Large cap", "B": "🟡 Mid cap", "C": "🔴 Small cap"}
    tier_sections = []

    for tier_key in ["A", "B", "C"]:
        tier_coins = [c for c in coins if c.get("tier") == tier_key]
        tier_count = len(tier_coins)
        tier_bullish = sum(1 for c in tier_coins if c.get("signal") == "BULLISH")

        # Top 2 by signal strength (any signal, not just bullish)
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
```

### 3b. Import `fmt_volume`

At the top of `trend_follower.py`, update the scanner import:

```python
from bot.trend_follower.scanner import scan_top_coins, fmt_volume
```

---

## 4. Temporary scan logging (`trend_scans` table)

### 4a. Create table

Run this SQL migration on Supabase (project ID: `pxdhtmqfwjwjhtcoacsn`):

```sql
CREATE TABLE IF NOT EXISTS trend_scans (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    scan_timestamp timestamptz NOT NULL,
    symbol text NOT NULL,
    rank integer NOT NULL,
    tier text NOT NULL,
    price numeric,
    volume_24h numeric,
    ema_fast numeric,
    ema_slow numeric,
    rsi numeric,
    atr numeric,
    atr_avg numeric,
    signal text,
    signal_strength numeric,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_trend_scans_timestamp ON trend_scans (scan_timestamp DESC);

COMMENT ON TABLE trend_scans IS 'TEMPORARY — full scan data for debugging tier splits. Delete after validation.';
```

### 4b. Log full scan data

In the main loop of `trend_follower.py`, after classification and BEFORE the allocator, add:

```python
# Log full scan to trend_scans (temporary — for debugging tier splits)
log_full_scan(supabase, coins)
```

Add the helper function:

```python
def log_full_scan(supabase, coins: list[dict]):
    """Log all scanned coins to trend_scans for debugging. Temporary."""
    from datetime import datetime, timezone

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
        # Batch insert all coins in one call
        supabase.table("trend_scans").insert(rows).execute()
        logger.info(f"Logged {len(rows)} coins to trend_scans")
    except Exception as e:
        logger.warning(f"Failed to log scan data: {e}")
```

Place this function in `trend_follower.py` near the other helper functions (`log_decisions`, `load_trend_config`, etc.).

---

## 5. RLS check

The `trend_scans` table needs RLS disabled (or a permissive policy) for inserts to work. The existing `trend_decisions_log` had an RLS bug in Session 33 — don't repeat it.

After creating the table, verify:

```sql
ALTER TABLE trend_scans DISABLE ROW LEVEL SECURITY;
```

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/scanner.py` | MODIFY | Add `STABLECOIN_SYMBOLS` filter, tier assignment, `fmt_volume` helper |
| `bot/trend_follower/trend_follower.py` | MODIFY | Replace `send_scan_report` with tiered version, add `log_full_scan`, import `fmt_volume` |

No new files. No changes to `classifier.py` or `allocator.py`.

---

## Test

After changes, restart the trend follower:

```bash
# Kill existing process
pkill -f "trend_follower"

# Restart
cd ~/BagholderAI
python3.13 -m bot.trend_follower.trend_follower
```

- [ ] Telegram report shows 3 tiers (A/B/C) with 2 coins each instead of flat top-5
- [ ] Stablecoins (USDC, FDUSD, etc.) are NOT in the scan
- [ ] Total scanned coins should be ~46-47 (50 minus stablecoins)
- [ ] Each coin in the scan has a `rank` (1-N) and `tier` (A/B/C) field
- [ ] `trend_scans` table receives ~46-47 rows per scan cycle
- [ ] Verify tier A = ranks 1-20, tier B = ranks 21-40, tier C = ranks 41+
- [ ] Existing `trend_decisions_log` still works (still logs BTC/SOL/BONK decisions)
- [ ] No crashes, no Binance rate limit errors

---

## Scope rules

- **DO NOT** modify `classifier.py` or `allocator.py`
- **DO NOT** touch `bot_config` or any grid bot behavior
- **DO NOT** change `trend_config` table or its values
- **DO NOT** remove or modify the existing `trend_decisions_log` logic
- Binance API: read-only (same as before)
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(trend-follower): tiered scanning (20/20/10), stablecoin filter, scan logging
```
