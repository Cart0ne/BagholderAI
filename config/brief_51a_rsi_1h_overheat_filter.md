# INTERN BRIEF — Session 51a: RSI 1h Overheat Filter (Pre-ALLOCATE)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 51 — April 29, 2026
**Priority:** HIGH — active capital protection
**Prerequisite:** None (standalone)

---

## Context

On April 29, DOGE/USDT was allocated at 10:35 UTC at $0.1099 — practically
at the 30-day high of $0.11. The price immediately reversed and all 3 lots
were stop-lossed at $0.1039, losing $0.73.

The existing distance filter (45e) checks distance from EMA20 on 4h
candles. It didn't fire because EMA20 on 4h is slow — a sharp intraday
pump doesn't move it fast enough. By the time the TF scanner saw DOGE as
BULLISH on 4h, the 1h chart was already screaming overbought.

**Solution:** add a short-timeframe overheat check. RSI(14) on 1h candles
is normalised 0-100, works identically across all coins (no per-coin
threshold calibration needed), and specifically catches "price pumped too
fast in the last few hours." If RSI 1h > 75 → SKIP.

---

## Architecture decision: where to compute RSI 1h

The scanner currently fetches 4h klines for all 50 coins. Fetching 1h
klines for all 50 would double API calls. Instead:

1. Scanner runs as usual (4h klines, EMA, RSI 4h, ATR)
2. Classifier classifies (BULLISH/BEARISH/SIDEWAYS)
3. **`trend_follower.py` enriches BULLISH candidates with RSI 1h BEFORE
   calling allocator** — only BULLISH coins need the check, typically
   10-20 coins, not 50
4. Allocator checks `rsi_1h` field exactly like `distance_from_ema_pct`

This keeps scanner clean, allocator clean, and minimises API calls.

---

## DB migration

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_rsi_1h_max numeric DEFAULT 75;
```

`0` = disabled (kill-switch). Default 75 = skip coins with 1h RSI above 75.

---

## 1. Scanner addition — `bot/trend_follower/scanner.py`

Add a new function (do NOT modify `scan_top_coins` or
`fetch_indicators_for_symbol`):

```python
def fetch_rsi_1h(exchange, symbol: str, period: int = 14) -> float | None:
    """
    Fetch 1h klines for a single symbol and compute RSI(14).
    Returns the RSI value, or None on failure.
    Used by trend_follower.py to enrich BULLISH candidates only.
    """
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=period + 10)
        if len(ohlcv) < period + 1:
            logger.warning(f"[{symbol}] Not enough 1h candles for RSI ({len(ohlcv)})")
            return None
        closes = [c[4] for c in ohlcv]
        return calc_rsi(closes, period)
    except Exception as e:
        logger.warning(f"[{symbol}] Failed to fetch 1h RSI: {e}")
        return None
```

`calc_rsi` already exists in the same file — just reuse it.

---

## 2. Enrichment step — `bot/trend_follower/trend_follower.py`

In the main scan function, AFTER `classify_coins()` returns the classified
list and BEFORE `decide_allocations()` is called, add:

```python
# 51a: enrich BULLISH candidates with 1h RSI for overheat filter.
# Only fetch for BULLISH coins to minimize API calls.
rsi_1h_max = float(config.get("tf_rsi_1h_max") or 0)
if rsi_1h_max > 0:
    bullish = [c for c in coins if c.get("signal") == "BULLISH"]
    logger.info(f"[51a] Fetching 1h RSI for {len(bullish)} BULLISH candidates")
    for coin in bullish:
        rsi_val = fetch_rsi_1h(exchange, coin["symbol"])
        coin["rsi_1h"] = rsi_val
        time.sleep(0.2)  # rate limit
```

Import `fetch_rsi_1h` from scanner at the top of the file.

Non-BULLISH coins will not have `rsi_1h` key — that's fine, the allocator
only checks BULLISH ALLOCATE candidates.

---

## 3. Allocator gate — `bot/trend_follower/allocator.py`

### Read config once at top of `decide_allocations()`

```python
rsi_1h_max = float(config.get("tf_rsi_1h_max") or 0)
```

### ALLOCATE gate

In the per-tier candidate loop, add AFTER the distance filter (45e) and
BEFORE the min_allocate_strength check:

```python
# 51a: RSI 1h overheat filter — skip coins pumping too fast on short tf
if rsi_1h_max > 0:
    rsi_1h = coin.get("rsi_1h")
    if rsi_1h is not None and rsi_1h > rsi_1h_max:
        reason = (
            f"FILTER_RSI_1H_OVERHEAT: RSI(14) 1h = {rsi_1h:.1f} > "
            f"max {rsi_1h_max:.0f} — coin pumping too fast, skip"
        )
        logger.info(f"[ALLOCATOR] SKIP {coin['symbol']}: {reason}")
        log_event(
            severity="info",
            category="tf",
            event="rsi_1h_overheat_skip",
            symbol=coin["symbol"],
            message=reason,
            details={
                "rsi_1h": rsi_1h,
                "rsi_1h_max": rsi_1h_max,
                "path": "ALLOCATE",
            },
        )
        decisions.append(_make_decision(
            scan_ts, coin["symbol"], coin, "SKIP", reason,
        ))
        continue
```

### SWAP gate

Same filter in the SWAP candidate evaluation, same pattern as the distance
filter SWAP gate:

```python
# 51a: RSI 1h overheat filter for SWAP candidates
if rsi_1h_max > 0:
    rsi_1h = c.get("rsi_1h")
    if rsi_1h is not None and rsi_1h > rsi_1h_max:
        logger.info(
            f"[ALLOCATOR] SWAP candidate {c['symbol']} skipped: "
            f"RSI 1h = {rsi_1h:.1f} > max {rsi_1h_max:.0f}"
        )
        log_event(
            severity="info",
            category="tf",
            event="rsi_1h_overheat_skip",
            symbol=c["symbol"],
            message=f"SWAP candidate skipped: RSI 1h = {rsi_1h:.1f} > max {rsi_1h_max:.0f}",
            details={
                "rsi_1h": rsi_1h,
                "rsi_1h_max": rsi_1h_max,
                "path": "SWAP",
            },
        )
        continue
```

---

## 4. Dashboard update — `web/tf.html`

Add to `TF_SAFETY_FIELDS`:

```javascript
{
  key: 'tf_rsi_1h_max',
  label: 'RSI 1h max (overheat filter)',
  sub: '51a: SKIP ALLOCATE/SWAP if the candidate\'s RSI(14) on 1h candles exceeds this value. Prevents entering coins mid-pump. Default 75. Set 0 to disable.'
},
```

Add `tf_rsi_1h_max` to the trend_config SELECT query in the dashboard
loader (same place where `tf_entry_max_distance_pct` is listed).

---

## 5. Telegram report — `bot/trend_follower/trend_follower.py`

After the existing "Entry distance blocked" section, add:

```python
# 51a: RSI 1h overheat-filtered coins
if rsi_1h_max > 0:
    overheat = [
        c for c in coins
        if c.get("signal") == "BULLISH"
        and c.get("rsi_1h") is not None
        and c["rsi_1h"] > rsi_1h_max
    ]
    if overheat:
        lines.append(f"\n🌡️ <b>RSI 1h overheat blocked</b> (pumping too fast):")
        for c in overheat[:5]:
            lines.append(f"  • {c['symbol']}: RSI 1h = {c['rsi_1h']:.0f}")
```

Omit the block if 0 coins filtered or feature disabled.

---

## Files to modify

| File | Action |
|------|--------|
| DB (`trend_config`) | MIGRATE: add `tf_rsi_1h_max numeric DEFAULT 75` |
| `bot/trend_follower/scanner.py` | ADD: `fetch_rsi_1h()` function |
| `bot/trend_follower/trend_follower.py` | ADD: enrichment step (1h RSI for BULLISH coins) + Telegram report section |
| `bot/trend_follower/allocator.py` | ADD: RSI 1h gate in ALLOCATE + SWAP paths |
| `web/tf.html` | ADD: field to `TF_SAFETY_FIELDS` + SELECT query |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes (this is entry-only)
- `bot/grid_runner.py` — no changes
- Stop-loss / greed decay / profit lock / gain saturation — independent
- Manual bots (BTC/SOL/BONK) — allocator never touches them
- `bot_config` table — no schema changes

---

## Scope rules

- **DO NOT** add 1h kline fetch to `scan_top_coins` — only BULLISH coins
  need it, the enrichment happens in `trend_follower.py`
- **DO NOT** replace the existing RSI 4h in the scanner — that's used for
  classification. RSI 1h is a separate overheat-only check
- **DO NOT** hardcode the threshold; always read from `trend_config`
- **DO NOT** touch exit logic — this is entry-only, never exit
- Push to GitHub when done
- Stop when tasks are complete

---

## Test checklist

### DB migration
- [ ] Column `tf_rsi_1h_max` exists in trend_config, default 75
- [ ] RLS disabled on trend_config

### Scanner function
- [ ] `fetch_rsi_1h(exchange, "BTC/USDT")` returns a float 0-100
- [ ] `fetch_rsi_1h(exchange, "INVALID/PAIR")` returns None (no crash)

### Enrichment
- [ ] After enrichment, BULLISH coins have `rsi_1h` key
- [ ] BEARISH/SIDEWAYS coins do NOT have `rsi_1h` key
- [ ] `tf_rsi_1h_max = 0` → enrichment step is skipped entirely (no API calls)

### Allocator gate — ALLOCATE
- [ ] Candidate with RSI 1h = 65, threshold 75 → PASS
- [ ] Candidate with RSI 1h = 80, threshold 75 → SKIP (FILTER_RSI_1H_OVERHEAT)
- [ ] Candidate with RSI 1h = None (fetch failed), threshold 75 → PASS (fail-open)
- [ ] Threshold = 0 → never skips

### Allocator gate — SWAP
- [ ] SWAP candidate with RSI 1h = 82 → skipped
- [ ] SWAP candidate with RSI 1h = 60 → proceeds to strength check

### Logging
- [ ] Each skip writes to `bot_events_log` with `event=rsi_1h_overheat_skip`
- [ ] `trend_decisions_log` has SKIP with reason text

### Telegram
- [ ] Scan with 2 overheat coins → "RSI 1h overheat blocked" section
- [ ] Scan with 0 overheat coins → section omitted
- [ ] Feature disabled (threshold=0) → section never appears

### Regression
- [ ] Distance filter (45e) still works independently
- [ ] SL cooldown (45a) still works
- [ ] Greed decay / profit lock / gain saturation unaffected
- [ ] Manual bots untouched

---

## Commit format

```
feat(tf): RSI 1h overheat filter — skip coins mid-pump (51a)

New pre-ALLOCATE/SWAP gate: if RSI(14) on 1h candles exceeds
tf_rsi_1h_max (default 75), SKIP the coin. Catches sharp intraday
pumps that the 4h-based distance filter (45e) misses.

Triggered by DOGE/USDT loss on Apr 29: allocated at $0.1099
(30-day high), stop-lossed at $0.1039 (-$0.73). 1h RSI was
likely >80 at entry — this filter would have blocked it.

RSI 1h is fetched only for BULLISH candidates (10-20 coins)
to minimize API calls. Fail-open: if fetch fails, coin passes.

New column: trend_config.tf_rsi_1h_max (numeric, default 75).
```
