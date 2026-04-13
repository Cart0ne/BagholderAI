# INTERN BRIEF — Session 31b: Trend Follower Core (Shadow Mode)

**Date:** April 12, 2026
**Priority:** HIGH — core Phase B deliverable
**Prerequisite:** Brief 31a must be completed first (is_active, exchange filters, idle re-entry fix)
**Reference:** `Trend_Follower_Spec_v1c.md` (attached to this session — read it before starting)

---

## Context

The Trend Follower (TF) is a new autonomous script that scans crypto markets, detects trends, and decides which coins to trade via grid bots. In this brief, it launches in **shadow mode only** (`dry_run = true` in `trend_config`). It analyzes, decides, and reports via Telegram — but does NOT write to `bot_config` and does NOT affect running grid bots.

---

## Architecture

```
trend_follower.py        ← NEW: main script (this brief)
├── scanner.py           ← NEW: fetches coins + calculates indicators
├── classifier.py        ← NEW: classifies signals + ranks coins
├── allocator.py         ← NEW: decides allocations + respects tiers/filters
└── utils/
    ├── exchange_filters.py  ← EXISTS (from Brief 31a)
    └── telegram_notifier.py ← EXISTS (extend with TF message types)
```

All new files go in `bot/trend_follower/` as a subpackage.

---

## 1. Scanner (`bot/trend_follower/scanner.py`)

### What it does

Fetches market data from Binance and calculates technical indicators for each coin.

### Implementation

```python
def scan_top_coins(exchange, top_n: int = 50) -> list[dict]:
    """
    1. Fetch all USDT tickers from Binance
    2. Sort by 24h quoteVolume (USDT volume), take top N
    3. For each coin, fetch 4h klines (minimum 50 candles = 200 hours)
    4. Calculate indicators: EMA 20, EMA 50, RSI 14, ATR 14
    5. Return list of dicts with all data
    """
```

**Return format per coin:**
```python
{
    "symbol": "SOL/USDT",
    "price": 145.80,
    "volume_24h": 1234567890.0,
    "ema_fast": 143.20,        # EMA 20
    "ema_slow": 140.50,        # EMA 50
    "rsi": 62.3,
    "atr": 4.85,
    "atr_avg": 3.90,           # Historical average ATR (mean of last 50 ATR values)
}
```

### Technical indicator calculations

Use **pandas** + manual calculations (no TA-Lib dependency — keep it simple):

**EMA (Exponential Moving Average):**
```python
def calc_ema(closes: list[float], period: int) -> float:
    """Standard EMA calculation using pandas."""
    import pandas as pd
    series = pd.Series(closes)
    return series.ewm(span=period, adjust=False).mean().iloc[-1]
```

**RSI (Relative Strength Index):**
```python
def calc_rsi(closes: list[float], period: int = 14) -> float:
    """Wilder's RSI."""
    import pandas as pd
    series = pd.Series(closes)
    delta = series.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]
```

**ATR (Average True Range):**
```python
def calc_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    """Standard ATR: EMA of true range."""
    import pandas as pd
    h, l, c = pd.Series(highs), pd.Series(lows), pd.Series(closes)
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean().iloc[-1]
```

### Binance data fetching

Use ccxt (already in the project):
```python
# Tickers for volume ranking
tickers = exchange.fetch_tickers()
usdt_tickers = {k: v for k, v in tickers.items() if k.endswith("/USDT")}

# Klines for a specific coin
ohlcv = exchange.fetch_ohlcv(symbol, timeframe="4h", limit=100)
# Returns: [[timestamp, open, high, low, close, volume], ...]
```

### Rate limiting

Binance has rate limits. Between each `fetch_ohlcv` call, add a small delay:
```python
import time
time.sleep(0.2)  # 200ms between kline requests — well within Binance limits
```

For 50 coins, this adds ~10 seconds to the scan. Acceptable.

---

## 2. Classifier (`bot/trend_follower/classifier.py`)

### What it does

Takes scanner output and classifies each coin's trend signal.

### Signal classification

```python
def classify_signal(coin: dict, config: dict) -> dict:
    """
    Classify a coin's trend based on indicator values.
    Returns the coin dict with added 'signal' and 'signal_strength' fields.
    """
```

**Rules (from spec Section 1):**

| Signal | Conditions |
|--------|-----------|
| BULLISH | EMA fast > EMA slow AND RSI > 50 AND ATR > ATR average |
| BEARISH | EMA fast < EMA slow AND RSI < 50 AND ATR > ATR average |
| SIDEWAYS | ATR > ATR average BUT EMAs close together (abs(fast-slow)/slow < 0.5%) OR RSI between 45-55 |
| NO_SIGNAL | ATR ≤ ATR average (market too flat to trade) |

**Signal strength** (for ranking bullish coins):
```python
signal_strength = abs(rsi - 50) + (atr / atr_avg)
```

Higher = stronger signal. Used to rank candidates when selecting top N.

### Output

Each coin dict gets two new fields:
```python
coin["signal"] = "BULLISH"  # or BEARISH, SIDEWAYS, NO_SIGNAL
coin["signal_strength"] = 8.2
```

---

## 3. Allocator (`bot/trend_follower/allocator.py`)

### What it does

Decides which coins to allocate capital to, respecting tier limits, exchange filters, and max active grids.

### Implementation

```python
def decide_allocations(
    classified_coins: list[dict],
    current_allocations: list[dict],  # from bot_config (active grids)
    coin_tiers: list[dict],           # from coin_tiers table
    exchange_filters: dict,           # from exchange_filters table
    config: dict,                     # from trend_config
    total_capital: float,
) -> list[dict]:
    """
    Returns a list of decisions (ALLOCATE / DEALLOCATE / HOLD / SKIP) for each coin.
    In shadow mode, these are logged but not acted upon.
    """
```

### Logic flow

1. Get current active grids count from `bot_config` (where `is_active = true`)
2. Get unallocated capital = `total_capital - sum(allocated_capital of active grids)`
3. Filter classified coins: only BULLISH (for now — bearish accumulation is Phase F)
4. Rank by signal_strength descending
5. For each candidate (top to bottom):
   a. Look up tier → max allocation percent
   b. Calculate allocation amount = `min(unallocated, total_capital * tier_max_pct)`
   c. Check exchange filters: can this allocation support meaningful grid levels? (use `validate_order` from exchange_filters.py with the tier allocation divided by ~5 levels)
   d. If passes → decision = `ALLOCATE`
   e. If fails → decision = `SKIP` with reason
   f. Stop when `max_active_grids` reached
6. For existing active grids: check if signal has reversed → decision = `DEALLOCATE` (with reason)
7. For existing active grids with unchanged signal → decision = `HOLD`

### Tier lookup

Read `coin_tiers` table from Supabase. If a coin is not in the table:
- Check if it's BTC or ETH → T1 (40%)
- Otherwise → T3 (10%) by default

The auto-assignment by market cap (T2 detection) is a future enhancement. For now, T2 coins must be manually added to `coin_tiers` by Max via the admin dashboard.

### Shadow mode behavior

When `dry_run = true` in `trend_config`:
- ALL decisions are logged to `trend_decisions_log` with `is_shadow = true`
- `config_written` is populated with what WOULD be written (as JSON), but nothing is written to `bot_config`
- Telegram gets `[SHADOW]`-prefixed messages

---

## 4. Telegram Reporting

### Extend existing notifier

Add new methods to `utils/telegram_notifier.py` (the `SyncTelegramNotifier` class):

#### `send_scan_report(scan_summary: dict)`

```
📊 TREND SCAN — April 12, 2026 08:00 UTC

Scanned: 50 coins
Bullish: 7 | Bearish: 12 | Sideways: 28 | No signal: 3

Top signals:
1. SOL — BULLISH (strength: 8.2) — RSI 62, EMA cross ↑
2. AVAX — BULLISH (strength: 6.5) — RSI 58, EMA cross ↑
3. ETH — SIDEWAYS (strength: 3.1) — EMAs flat

Active grids: 3/5
Capital deployed: $350 / $500
```

Show top 5 signals max. Use HTML formatting (already used by the existing notifier).

#### `send_tf_decision(decision: dict, is_shadow: bool)`

If `is_shadow`:
```
[SHADOW] 🟢 WOULD ALLOCATE — SOL/USDT
Trend: BULLISH | Strength: 8.2
Capital: $100 (20% — T2)
Grid would be: $138.50 – $165.20 (bullish bias)
⚠️ Shadow mode — no config written
```

If NOT shadow (future — not used in this brief):
```
🟢 ALLOCATE — SOL/USDT
Trend: BULLISH | Strength: 8.2
Capital: $100 (20% — T2)
Grid: $138.50 – $165.20 (bullish bias)
Entry: $145.80 | Stop: $138.51 (-5%)
```

#### `send_tf_error(error_msg: str)`

```
🚨 TREND FOLLOWER ERROR
{error_msg}
```

---

## 5. Main Script (`bot/trend_follower/trend_follower.py`)

### What it does

Orchestrates the full cycle: scan → classify → allocate → log → report → sleep → repeat.

### Entry point

```python
def run_trend_follower():
    """Main loop for the Trend Follower."""
    
    # 1. Initialize
    exchange = create_exchange()
    exchange.load_markets()
    notifier = SyncTelegramNotifier()
    supabase = get_client()
    
    # 2. Load config from trend_config table
    config = load_trend_config(supabase)
    
    if not config["trend_follower_enabled"]:
        logger.info("Trend Follower disabled (trend_follower_enabled=false). Exiting.")
        notifier.send_message("🛑 Trend Follower disabled. Exiting.")
        return
    
    logger.info(f"Trend Follower starting — dry_run={config['dry_run']}")
    notifier.send_message(
        f"🧠 Trend Follower started\n"
        f"Mode: {'SHADOW (dry run)' if config['dry_run'] else 'LIVE'}\n"
        f"Scan interval: {config['scan_interval_hours']}h\n"
        f"Max grids: {config['max_active_grids']}"
    )
    
    # 3. Main loop
    while True:
        try:
            # Reload config each cycle (allows hot changes)
            config = load_trend_config(supabase)
            
            if not config["trend_follower_enabled"]:
                logger.info("Trend Follower disabled mid-run. Exiting.")
                notifier.send_message("🛑 Trend Follower stopped (disabled via config).")
                break
            
            # Scan
            coins = scan_top_coins(exchange, config["scan_top_n"])
            
            # Classify
            for coin in coins:
                classify_signal(coin, config)
            
            # Load context
            coin_tiers = load_coin_tiers(supabase)
            exchange_filters = load_exchange_filters(supabase)
            current_allocs = load_current_allocations(supabase)
            total_capital = sum_total_capital(supabase)  # from bot_config.capital_allocation
            
            # Allocate (decisions only)
            decisions = decide_allocations(
                coins, current_allocs, coin_tiers, 
                exchange_filters, config, total_capital
            )
            
            # Log to Supabase
            log_decisions(supabase, decisions, is_shadow=config["dry_run"])
            
            # Report to Telegram
            send_scan_report(notifier, coins, current_allocs, config)
            for d in decisions:
                if d["action_taken"] in ("ALLOCATE", "DEALLOCATE"):
                    send_tf_decision(notifier, d, is_shadow=config["dry_run"])
            
            # If NOT shadow mode, write to bot_config (FUTURE — not in this brief)
            # if not config["dry_run"]:
            #     apply_allocations(supabase, decisions)
            
            logger.info(f"Scan complete. Sleeping {config['scan_interval_hours']}h...")
            time.sleep(config["scan_interval_hours"] * 3600)
            
        except KeyboardInterrupt:
            logger.info("Trend Follower stopped by user.")
            notifier.send_message("🛑 Trend Follower stopped (manual).")
            break
        except Exception as e:
            logger.error(f"Trend Follower error: {e}", exc_info=True)
            notifier.send_tf_error(str(e))
            time.sleep(300)  # 5 min backoff on error
```

### CLI

```python
if __name__ == "__main__":
    run_trend_follower()
```

Run with: `python3.13 -m bot.trend_follower.trend_follower`

---

## 6. Helper Functions

### `load_trend_config(supabase) -> dict`

```python
result = supabase.table("trend_config").select("*").limit(1).execute()
return result.data[0] if result.data else DEFAULT_CONFIG
```

### `load_coin_tiers(supabase) -> dict`

```python
result = supabase.table("coin_tiers").select("*").execute()
# Return as dict keyed by symbol: {"BTC": {"tier": 1, "max_allocation_percent": 40}, ...}
```

### `load_exchange_filters(supabase) -> dict`

```python
result = supabase.table("exchange_filters").select("*").execute()
# Return as dict keyed by symbol: {"BTCUSDT": {"min_notional": 5.0, ...}, ...}
```

If `exchange_filters` is empty (first run), fetch from Binance and cache:
```python
if not result.data:
    fetch_and_cache_filters(exchange, symbols)  # from utils/exchange_filters.py
```

### `load_current_allocations(supabase) -> list[dict]`

```python
result = supabase.table("bot_config").select("symbol,is_active,capital_allocation,managed_by").execute()
return [r for r in result.data if r.get("is_active")]
```

### `log_decisions(supabase, decisions, is_shadow)`

Insert each decision into `trend_decisions_log`:
```python
for d in decisions:
    supabase.table("trend_decisions_log").insert({
        "scan_timestamp": d["scan_timestamp"],
        "symbol": d["symbol"],
        "ema_fast_value": d["ema_fast"],
        "ema_slow_value": d["ema_slow"],
        "rsi_value": d["rsi"],
        "atr_value": d["atr"],
        "signal": d["signal"],
        "signal_strength": d["signal_strength"],
        "action_taken": d["action_taken"],
        "is_shadow": is_shadow,
        "reason": d["reason"],
        "config_written": d.get("config_snapshot"),  # JSON of what would be written
    }).execute()
```

Only log coins where `action_taken` is ALLOCATE, DEALLOCATE, or HOLD (for coins already active). Don't log every SKIP — that's 45+ rows per scan of coins we don't care about. Exception: log SKIP if `reason` contains `FILTER_FAIL` (those are interesting).

---

## 7. Seed Data

### Coin Tiers

The `coin_tiers` table needs initial data. Insert via the script on first run if table is empty:

```python
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
# Everything else → T3 (10%) by default in allocator logic
```

---

## Dependencies

- **pandas** — for indicator calculations. Check if already installed: `python3.13 -c "import pandas"`. If not: `pip install pandas`
- **ccxt** — already in the project
- **supabase** — already in the project

---

## Files to create/modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/__init__.py` | CREATE | Empty init |
| `bot/trend_follower/scanner.py` | CREATE | Market scanner + indicator calculations |
| `bot/trend_follower/classifier.py` | CREATE | Signal classification |
| `bot/trend_follower/allocator.py` | CREATE | Allocation decisions |
| `bot/trend_follower/trend_follower.py` | CREATE | Main orchestrator + CLI |
| `utils/telegram_notifier.py` | MODIFY | Add TF message methods |

---

## Scope Rules

- Supabase reads: `trend_config`, `coin_tiers`, `bot_config`, `exchange_filters`
- Supabase writes: `trend_decisions_log`, `exchange_filters` (cache), `coin_tiers` (seed only)
- **DO NOT** write to `bot_config` — shadow mode only
- **DO NOT** launch grid bots or modify running bots
- Binance API: `fetch_tickers()`, `fetch_ohlcv()`, `load_markets()` — all read-only
- Telegram: send to private channel only
- Push to GitHub when done
- Stop when tasks are complete

---

## Test

- [ ] `python3.13 -m bot.trend_follower.trend_follower` starts cleanly
- [ ] Scans 50 coins, logs indicator values
- [ ] Classifies signals correctly (at least verify BTC/SOL/BONK manually)
- [ ] Sends scan report to Telegram (private channel)
- [ ] Sends [SHADOW] decision notifications to Telegram
- [ ] Logs decisions to `trend_decisions_log` with `is_shadow = true`
- [ ] `trend_follower_enabled = false` → exits cleanly
- [ ] `dry_run = true` → no writes to `bot_config` (verify)
- [ ] Sleeps for `scan_interval_hours` between cycles
- [ ] Error handling: if Binance API fails, retries after 5 min without crashing
- [ ] Coin tiers seeded on first run if table is empty

---

## Commit format

```
feat(trend-follower): shadow mode scanner + classifier + allocator + telegram
```
