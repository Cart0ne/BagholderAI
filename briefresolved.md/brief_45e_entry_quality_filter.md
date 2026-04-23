# INTERN BRIEF 45e — Entry Quality Filter (Price > EMA + RSI cap)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 23, 2026
**Priority:** MEDIUM-HIGH — prevents entering coins already in downtrend
**Depends on:** 45c deployed ✅, 45d deployed ✅
**Scope:** `scanner.py` (flag computation) + `allocator.py` (filter gate) + DB + dashboard

---

## Context

The TF selects coins based on **relative strength** vs. the rest of
the scan pool. This catches rising coins well, but doesn't protect
against a coin that looks strong *relative to others* while being
in absolute downtrend — i.e. price already below its own EMA.

Concrete examples from v3 trading history:
- **MOVR/USDT**: selected via SWAP (high relative strength delta),
  price was already declining below EMA20 at entry time.
  Result: -$13.39.
- **BOME/USDT**: similar pattern, ROI -26.8%.
- **MET/USDT**: flash crash of 19% in 59 seconds. ROI -2.09%.

The fix: add two deterministic gates in the scanner/allocator that
check the coin's **absolute technical state** at entry time, not just
its relative ranking.

Both values (`ema_fast`, `rsi_period`) are already computed by the
scanner for every candidate coin — no extra API calls, no new data
sources. This is a filter on existing data.

---

## Two gates

### Gate 1 — Price above EMA_fast (4h)

`ema_fast` (default 20, from `trend_config.ema_fast`) is already
computed by the scanner on the 4h OHLCV series. The current close
price is `ohlcv[-1][4]` in the same series.

**Rule:** if `close < ema_fast_value` → coin is in short-term
downtrend → mark `entry_ok = False`.

In plain language: if the coin's price is below its own 20-period
average (on the 4h chart), we don't enter. We might be catching
a falling knife.

**Why EMA_fast not EMA_slow?** EMA_fast (20) is the recent trend;
EMA_slow (50) is the medium-term. We want the entry filter to be
sensitive to recent momentum — a coin can be above EMA50 but already
rolling over below EMA20. That's exactly the MOVR scenario.

### Gate 2 — RSI not overbought

`rsi_period` (default 14) is also already computed by the scanner.

**Rule:** if `rsi_value >= tf_entry_max_rsi` → coin is overbought at
entry → mark `entry_ok = False`.

Default threshold: **70**. Entering a coin at RSI 72-80 means buying
near the top of a local move — the grid will immediately face a
pullback and accumulate losing lots.

This is the **opposite** of Gate 1: Gate 1 catches coins already
falling, Gate 2 catches coins about to reverse after a spike.

Together they define the entry window: uptrend (above EMA20) but not
yet exhausted (RSI < 70).

---

## DB migration

Two new boolean/numeric fields in `trend_config`:

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_entry_require_price_above_ema boolean DEFAULT true,
  ADD COLUMN tf_entry_max_rsi numeric DEFAULT 70;

ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
```

Both are configurable from the dashboard so we can tune or disable
without a code deploy.

`tf_entry_require_price_above_ema = false` disables both gates
simultaneously (single kill-switch). This is intentional — if we
ever want to disable the filter quickly during a test, one toggle
is simpler than two.

---

## Scanner change — `bot/trend_follower/scanner.py`

In `scan_top_coins()`, after the existing EMA and RSI computations
for each coin, add the `entry_ok` flag:

```python
# 45e: entry quality filter
# ema_fast_val and rsi_val are already computed above for the
# BULLISH/BEARISH classification. Reuse them — no extra API call.
price_above_ema = float(close_price) >= float(ema_fast_val)
rsi_in_range = float(rsi_val) < float(tier1_max_rsi)  # passed from caller

coin["price_above_ema"] = price_above_ema
coin["rsi_at_scan"] = round(float(rsi_val), 1)
coin["entry_ok"] = price_above_ema and rsi_in_range
```

The exact variable names for `ema_fast_val`, `rsi_val`, and
`close_price` must match what already exists in the function body
— CC to verify against the current implementation. The logic is:
reuse computed values, add three new keys to the coin dict.

### Caller update — `trend_follower.py`

Pass `tf_entry_max_rsi` from trend_config to `scan_top_coins()`:

```python
coins = scan_top_coins(
    exchange,
    n=scan_top_n,
    tier1_min_volume=tier1_min_volume,
    tier2_min_volume=tier2_min_volume,
    # 45e: entry quality filter threshold
    entry_max_rsi=float(config.get("tf_entry_max_rsi") or 70),
)
```

Add `entry_max_rsi: float = 70` to the `scan_top_coins()` signature.

---

## Allocator change — `bot/trend_follower/allocator.py`

### ALLOCATE gate

In `decide_allocations()`, in the candidate selection loop for each
tier (Step B), after confirming the coin is BULLISH, add the entry
filter check:

```python
# 45e: entry quality filter
require_ema_filter = bool(config.get("tf_entry_require_price_above_ema", True))
if require_ema_filter and not candidate.get("entry_ok", True):
    reason_parts = []
    if not candidate.get("price_above_ema", True):
        reason_parts.append(
            f"price ${candidate.get('close', '?'):.4f} below "
            f"EMA{config.get('ema_fast', 20)} "
            f"(downtrend at entry)"
        )
    rsi = candidate.get("rsi_at_scan", 0)
    max_rsi = float(config.get("tf_entry_max_rsi") or 70)
    if rsi >= max_rsi:
        reason_parts.append(
            f"RSI {rsi:.1f} >= {max_rsi:.0f} (overbought at entry)"
        )
    decisions.append(_make_decision(
        scan_ts, candidate["symbol"], candidate,
        "SKIP",
        "FILTER_ENTRY: " + "; ".join(reason_parts),
    ))
    continue
```

Place this block **after** the BULLISH check and **after** the
volume-tier assignment, but **before** updating `tier_best`.
This way the SKIP is logged in `trend_decisions_log` with a clear
reason, and the tier slot remains open for the next candidate in
that tier.

### SWAP gate

The same filter must apply to SWAP candidates. In the SWAP evaluation
block (where `swap_candidate` is chosen per active coin), add:

```python
# 45e: entry quality filter also applies to SWAP candidates
if require_ema_filter and not swap_candidate.get("entry_ok", True):
    decisions.append(_make_decision(
        scan_ts, swap_candidate["symbol"], swap_candidate,
        "SKIP",
        "FILTER_ENTRY (SWAP candidate): price below EMA or RSI overbought",
    ))
    continue  # keep current active coin
```

**Why on SWAP too?** The original MOVR entry was via SWAP (AXL →
MOVR). If this filter had existed, the SWAP would have been blocked
because MOVR's price was already below EMA20 at the time of the
swap decision.

---

## Telegram report update

In the scan summary sent to Telegram, add a section showing coins
that were filtered out due to entry gates:

```python
# 45e: entry-filtered coins in scan report
filtered_coins = [c for c in coins if c.get("signal") == "BULLISH"
                  and not c.get("entry_ok", True)]
if filtered_coins:
    lines.append("\n⛔ <b>Entry filter blocked</b> (BULLISH but entry not ok):")
    for c in filtered_coins[:5]:   # max 5 to keep report readable
        rsi = c.get("rsi_at_scan", "?")
        above = "✅" if c.get("price_above_ema") else "❌ below EMA"
        rsi_flag = "✅" if float(rsi or 0) < 70 else f"❌ RSI {rsi}"
        lines.append(
            f"  • {c['symbol']}: {above} | {rsi_flag}"
        )
```

This gives visibility into how many good candidates are being
rejected by the filter — useful for calibration. If we see 8 out
of 10 BULLISH coins being blocked, the thresholds may be too strict.

---

## Dashboard update — `web/tf.html` and `web2/tf.html`

Add two fields to the `TF_SAFETY_FIELDS` array (same pattern as
the 45c tier fields):

```javascript
{ key: 'tf_entry_require_price_above_ema',
  label: 'Entry EMA filter',
  type: 'boolean',
  sub: '45e: If true, only ALLOCATE/SWAP coins where price ≥ EMA_fast (4h). Kill-switch for both EMA and RSI gates.' },

{ key: 'tf_entry_max_rsi',
  label: 'Entry max RSI',
  sub: '45e: Skip coin at entry if RSI ≥ this value (overbought). Default 70. Only active when entry EMA filter is enabled.' },
```

---

## Files to modify

| File | Action |
|------|--------|
| `bot/trend_follower/scanner.py` | Add `entry_max_rsi` param; compute `price_above_ema`, `rsi_at_scan`, `entry_ok` per coin |
| `bot/trend_follower/trend_follower.py` | Pass `entry_max_rsi` to `scan_top_coins()`; add filtered coins section to Telegram report |
| `bot/trend_follower/allocator.py` | Add FILTER_ENTRY gate in ALLOCATE loop and SWAP block; read `tf_entry_require_price_above_ema` from config |
| `web/tf.html` | Add 2 new fields to TF_SAFETY_FIELDS |
| `web2/tf.html` | Same |
| DB (`trend_config`) | Migration: add `tf_entry_require_price_above_ema`, `tf_entry_max_rsi` |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes
- `bot/grid_runner.py` — no changes
- `bot/trend_follower/scanner.py` OHLCV fetch logic — don't add new API calls
- Stop-loss / cooldown / greed decay / resize (45a / 45b / 45d) — independent
- Manual bots (BTC/SOL/BONK) — MANUAL_WHITELIST still excludes them
- DB schema beyond the two new columns

---

## Test checklist

### DB migration
- [ ] `tf_entry_require_price_above_ema` exists, default `true`
- [ ] `tf_entry_max_rsi` exists, default `70`
- [ ] RLS disabled on trend_config

### Gate 1 — Price above EMA

- [ ] Coin with close $1.00, EMA20 $0.90 → `price_above_ema = True`,
      `entry_ok = True` (assuming RSI < 70)
- [ ] Coin with close $0.80, EMA20 $0.90 → `price_above_ema = False`,
      `entry_ok = False` → SKIP with reason "price below EMA20"
- [ ] Coin exactly at EMA (close == ema_fast_val) → `True`
      (boundary: `>=` is pass)

### Gate 2 — RSI cap

- [ ] Coin with RSI 65, threshold 70 → `rsi_in_range = True`
- [ ] Coin with RSI 70, threshold 70 → `rsi_in_range = False`
      (boundary: `>=` is fail)
- [ ] Coin with RSI 82 → SKIP with reason "RSI 82.0 >= 70 (overbought)"
- [ ] Coin with RSI 55, price above EMA → both gates pass → eligible

### Combined

- [ ] Coin BULLISH, price above EMA, RSI 60 → ALLOCATE proceeds
- [ ] Coin BULLISH, price **below** EMA, RSI 60 → FILTER_ENTRY SKIP
- [ ] Coin BULLISH, price above EMA, RSI 75 → FILTER_ENTRY SKIP
- [ ] Coin BULLISH, price below EMA, RSI 80 → FILTER_ENTRY SKIP
      (both reasons in message)

### Kill-switch

- [ ] Set `tf_entry_require_price_above_ema = false` in trend_config
      → coins with price below EMA and/or high RSI are **not** skipped
      → allocator behaves as pre-45e (only relative strength matters)
- [ ] Re-enable → filter resumes at next scan (no restart needed)

### SWAP gate

- [ ] Active coin A, SWAP candidate B (same tier, +20 delta, BULLISH)
      but B has price below EMA → SWAP does NOT fire, A stays active,
      SKIP logged with FILTER_ENTRY (SWAP candidate)
- [ ] Same scenario, B passes both gates → SWAP fires normally

### Telegram report

- [ ] Scan with 3 BULLISH coins, 2 filtered → report shows
      "⛔ Entry filter blocked (2 coins)" with per-coin EMA/RSI flags
- [ ] No coins filtered → the section is absent (don't show empty block)

### Regression

- [ ] BEARISH coins are unaffected (filter only applies to BULLISH)
- [ ] DEALLOCATE logic unchanged (filter is entry-only, not exit)
- [ ] Tier assignment (45c) unchanged — filter runs after tier, not before
- [ ] `trend_decisions_log` records FILTER_ENTRY SKIP with clear reason
- [ ] Manual bots (BTC/SOL/BONK) unaffected

---

## Scope rules

- **DO NOT** add new OHLCV fetches — reuse what scanner already computes
- **DO NOT** apply this filter to active (already allocated) coins —
  entry filter only, never exit
- **DO NOT** change the BEARISH → DEALLOCATE path
- **DO NOT** touch stop-loss, cooldown, greed decay, resize (45a/b/d)
- **DO NOT** apply filter when `tf_entry_require_price_above_ema = false`
- Push to GitHub when done
- Stop when tasks are complete

---

## Historical validation (manual check, not automated test)

Once deployed, CC can run this query to see how many of the v3
TF losses would have been filtered:

```sql
SELECT symbol,
  ROUND(SUM(realized_pnl)::numeric, 2) as total_pnl,
  COUNT(*) FILTER (WHERE side='sell') as sells
FROM trades
WHERE config_version='v3'
  AND managed_by='trend_follower'
  AND symbol IN ('MOVR/USDT','BOME/USDT','MET/USDT','CFG/USDT',
                 'KAT/USDT','TST/USDT','BLUR/USDT')
GROUP BY symbol
ORDER BY total_pnl;
```

These are the 7 TF coins with negative PnL. MOVR and BOME in
particular are expected to have been below EMA20 at entry time —
if CC can verify this against historical OHLCV (ccxt
`fetch_ohlcv('MOVR/USDT', '4h', since=<entry_timestamp>)`) that
would make a compelling validation note for the diary.

Not a blocker — deploy first, validate after.

---

## Commit format

```
feat(tf): entry quality filter — price>EMA + RSI cap (45e)

Two new deterministic gates in the TF allocator that check a
coin's absolute technical state before ALLOCATE or SWAP:

  Gate 1: price >= EMA_fast (4h) — rejects coins already in
    short-term downtrend. MOVR and BOME had price below EMA20
    at the time of their entry decision.

  Gate 2: RSI < tf_entry_max_rsi (default 70) — rejects coins
    entering overbought territory. Avoids buying near local top.

Both values are already computed by the scanner (ema_fast and
rsi_period from trend_config). No new API calls. Gates apply to
ALLOCATE and SWAP candidates. Filter is logged in
trend_decisions_log as FILTER_ENTRY with specific reason.

Kill-switch: tf_entry_require_price_above_ema = false disables
both gates. tf_entry_max_rsi is separately tunable.

New DB columns: trend_config.tf_entry_require_price_above_ema
(boolean, default true), trend_config.tf_entry_max_rsi
(numeric, default 70).
```
