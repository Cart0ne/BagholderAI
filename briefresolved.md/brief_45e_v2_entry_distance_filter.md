# INTERN BRIEF 45e — Entry Distance Filter (price stretched above EMA20)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 23, 2026
**Priority:** HIGH — data-validated, 92.4% of v3 TF losses would have been blocked
**Depends on:** 45c deployed ✅, 45d deployed ✅
**Scope:** `scanner.py` (flag computation) + `allocator.py` (filter gate) + DB + dashboard
**Supersedes:** earlier 45e draft (Sonnet proposal with 2 gates: EMA-above + RSI cap)

---

## Why this v2 supersedes Sonnet's original 45e

Sonnet's original 45e proposed two gates: "price ≥ EMA_fast" (Gate 1) and
"RSI < 70" (Gate 2). The idea was sound but the scoping was wrong.
Running historical validation on the 11 losing TF allocations from v3
(MOVR, MET, BOME, BLUR, KAT, TST, SUPER, CFG, STRK, XLM, TRX) shows:

| Filter | Losses blocked | % of total loss |
|--------|----------------|-----------------|
| Gate 1 (price < EMA20) | **0/11** | 0.0% |
| Gate 2 (RSI ≥ 70) | 6/11 | 83.5% |
| **Distance from EMA > 10%** | **7/11** | **92.4%** |

Gate 1 never fired because every BULLISH-classified coin had price above
EMA20 by definition of the classifier (EMA20 > EMA50 + above trend).
Gate 2 (RSI > 70) was reasonable but incomplete — it missed BOME, which
had normal RSI but was stretched 15.6% above EMA20.

**The winning filter is "distance from EMA20 > threshold"**, which catches
everything Gate 2 catches **plus** the coins in pullback-ready territory
without elevated RSI. Distance is also conceptually cleaner: it measures
how "stretched" the price is relative to its recent mean — a direct
proxy for mean-reversion risk.

---

## The filter

One deterministic gate:

```python
distance_pct = ((close - ema20) / ema20) * 100
if distance_pct > tf_entry_max_distance_pct:
    SKIP (FILTER_ENTRY_DISTANCE)
```

**Default threshold: 10%.** Historical 7/11 losses blocked at this level,
same as 15% (the incremental coins between 15% and 10% are borderline
protective). 20% is too loose (only 4/11 blocked).

Kill-switch: set `tf_entry_max_distance_pct = 0` (or negative) → disabled.

---

## Historical validation data

```
MOVR/USDT    +87.3% from EMA20 at entry → would have been BLOCKED (saved $13.39)
TST/USDT     +29.5%                      → BLOCKED (saved $2.36)
BLUR/USDT    +23.3%                      → BLOCKED (saved $1.17)
BOME/USDT    +15.6%                      → BLOCKED (saved $2.46)
SUPER/USDT   +17.7%                      → BLOCKED (saved $0.75)
MET/USDT     +19.8%                      → BLOCKED (saved $4.47)
KAT/USDT     +27.0%                      → BLOCKED (saved $1.06)

TRX/USDT     +1.0%  → passed (lost $0.09)
CFG/USDT     +5.7%  → passed (lost $1.35)
XLM/USDT     +5.0%  → passed (lost $0.25)
STRK/USDT    +6.4%  → passed (lost $0.43)

Total:  $25.66 / $27.78 of v3 losses blocked (92.4%)
Unblocked: $2.12 across 4 small-loss coins — acceptable tail
```

Note: these are not just "losses avoided". The opportunity cost matters
too: the capital not deployed on MOVR could have been deployed on a
better candidate the TF scanner had identified that day. The upside
is not captured in the 92.4% figure but is real.

---

## DB migration

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_entry_max_distance_pct numeric DEFAULT 10;

ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
```

Only one new column. `0` = disabled (kill-switch).

No new bot_config columns. No change to existing defaults. No removal
of 45a/b/c/d columns.

---

## Scanner change — `bot/trend_follower/scanner.py`

In `scan_top_coins()`, the existing indicator computation already has
`ema_fast_value` (EMA20) and the current close price. Add the distance
flag per coin right after the existing classification:

```python
# 45e: entry distance filter
# Computes how far the current close is from EMA20, as a percentage.
# Positive = price above EMA20 (stretched upward); negative = below.
# The allocator uses this value against tf_entry_max_distance_pct.
ema20 = coin.get("ema_fast", 0) or 0
close = coin.get("price", 0) or 0
if ema20 > 0:
    coin["distance_from_ema_pct"] = round(((close - ema20) / ema20) * 100, 2)
else:
    coin["distance_from_ema_pct"] = 0.0
```

CC to verify the exact variable names in the scanner — the logic is
trivial, just reuse what's already computed.

---

## Allocator change — `bot/trend_follower/allocator.py`

### ALLOCATE gate

In `decide_allocations()`, in the tier candidate selection loop (Step B
or equivalent), add the distance check right after the SL cooldown gate
and before the min_allocate_strength gate:

```python
# 45e: entry distance filter
max_distance = float(config.get("tf_entry_max_distance_pct") or 0)
distance = float(coin.get("distance_from_ema_pct", 0) or 0)
if max_distance > 0 and distance > max_distance:
    reason = (
        f"FILTER_ENTRY_DISTANCE: price {distance:.1f}% above EMA20 "
        f"(max {max_distance:.1f}% — coin is stretched, mean-reversion risk)"
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
            "max_distance_pct": max_distance,
            "path": "ALLOCATE",
        },
    )
    decisions.append(_make_decision(
        scan_ts, coin["symbol"], coin, "SKIP", reason,
    ))
    continue
```

### SWAP gate

Same filter in the SWAP candidate evaluation. In the block where
`best_new` is chosen (the same place the SL cooldown is checked):

```python
# 45e: apply entry distance filter to SWAP candidates too.
# The original MOVR entry was via SWAP; if this filter had existed,
# the SWAP would have been blocked (MOVR was +87% above EMA20).
distance = float(c.get("distance_from_ema_pct", 0) or 0)
if max_distance > 0 and distance > max_distance:
    logger.info(
        f"[ALLOCATOR] SWAP candidate {c['symbol']} skipped: "
        f"distance {distance:.1f}% > max {max_distance:.1f}%"
    )
    log_event(
        severity="info",
        category="tf",
        event="entry_distance_skip",
        symbol=c["symbol"],
        message=f"SWAP candidate skipped: distance {distance:.1f}% above EMA20",
        details={
            "distance_pct": distance,
            "max_distance_pct": max_distance,
            "path": "SWAP",
        },
    )
    continue
```

Read `max_distance` once at the top of `decide_allocations` so both
ALLOCATE and SWAP paths reuse it.

---

## Dashboard update — `web/tf.html` and `web_old/tf.html`

Only `web/` is currently live. Add one field to `TF_SAFETY_FIELDS`:

```javascript
{
  key: 'tf_entry_max_distance_pct',
  label: 'Entry max distance from EMA20 (%)',
  sub: '45e: SKIP ALLOCATE/SWAP if the candidate coin\'s price is more than X% above its EMA20 (4h). Prevents entering stretched coins due for mean reversion. Default 10. Set 0 to disable.'
},
```

Also add the field to the trend_config SELECT in the dashboard loader
(the query currently lists every TF field explicitly — add
`tf_entry_max_distance_pct` to the list).

`web_old/tf.html` is the archived old site — do NOT update.

---

## Telegram report update — `bot/trend_follower/trend_follower.py`

Add a compact "filtered by distance" section to the scan report, after
the existing per-tier bullish breakdown:

```python
# 45e: distance-filtered BULLISH coins
max_dist = float(config.get("tf_entry_max_distance_pct") or 0)
if max_dist > 0:
    filtered = [
        c for c in coins
        if c.get("signal") == "BULLISH"
        and float(c.get("distance_from_ema_pct", 0) or 0) > max_dist
    ]
    if filtered:
        lines.append(f"\n⛔ <b>Entry distance blocked</b> (price too far above EMA20):")
        for c in filtered[:5]:
            d = c.get("distance_from_ema_pct", 0)
            lines.append(f"  • {c['symbol']}: +{d:.1f}% above EMA20")
```

Omits the block if 0 coins filtered or if the feature is disabled.

---

## Files to modify

| File | Action |
|------|--------|
| DB (`trend_config`) | MIGRATE: add `tf_entry_max_distance_pct numeric DEFAULT 10` |
| `bot/trend_follower/scanner.py` | Add `distance_from_ema_pct` computation per coin |
| `bot/trend_follower/allocator.py` | Read `tf_entry_max_distance_pct`; add FILTER_ENTRY_DISTANCE gate in ALLOCATE + SWAP |
| `bot/trend_follower/trend_follower.py` | Add filtered-coins section to Telegram scan report |
| `web/tf.html` | Add new field to `TF_SAFETY_FIELDS` + SELECT query |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes
- `bot/grid_runner.py` — no changes
- Stop-loss / SL cooldown / greed decay / sell_pct salvage / tier logic —
  independent features (45a / 45b / 45c / 45d)
- Manual bots (BTC/SOL/BONK) — allocator never touches them
- `web_old/tf.html` — archived
- `bot_config` table schema — no changes

---

## Test checklist

### DB migration
- [ ] Column `tf_entry_max_distance_pct` exists, default 10
- [ ] RLS disabled on trend_config

### Scanner computation
- [ ] Coin with close $1.00, EMA20 $0.95 → `distance_from_ema_pct = 5.26`
- [ ] Coin with close $0.95, EMA20 $1.00 → `distance_from_ema_pct = -5.00`
- [ ] Coin with EMA20 = 0 or missing → `distance_from_ema_pct = 0`

### Allocator gate — ALLOCATE
- [ ] Candidate with distance 8%, threshold 10% → PASS
- [ ] Candidate with distance 12%, threshold 10% → SKIP (FILTER_ENTRY_DISTANCE)
- [ ] Candidate with distance 10% exactly, threshold 10% → PASS (strict `>` not `>=`)
- [ ] Candidate with distance -5% (below EMA20), threshold 10% → PASS (negative distance is fine; only stretching ABOVE triggers)
- [ ] Threshold = 0 (disabled) → never skips, regardless of distance

### Allocator gate — SWAP
- [ ] SWAP candidate with distance 12% → skipped, current active bot kept
- [ ] SWAP candidate with distance 8% → proceeds to strength-delta check
- [ ] Same threshold applies to both paths

### Logging
- [ ] Each FILTER_ENTRY_DISTANCE skip writes a `bot_events_log` row with
      `event=entry_distance_skip`, path (ALLOCATE/SWAP), distance, threshold
- [ ] `trend_decisions_log` has the corresponding SKIP with reason text

### Telegram report
- [ ] Scan with 2 coins above threshold → "Entry distance blocked" section
      with both listed
- [ ] Scan with 0 coins filtered → section omitted (no empty block)
- [ ] Feature disabled (threshold=0) → section never appears

### Regression
- [ ] BEARISH coins unaffected (filter only runs on BULLISH ALLOCATE candidates)
- [ ] DEALLOCATE logic unchanged
- [ ] Tier assignment (45c) + resize (45d) + SL cooldown (45a) + sell_pct
      salvage (45b) all still work
- [ ] Manual bots untouched

### Historical sanity
- [ ] After deploy, run this query and confirm no new TF allocations
      have distance > 10% (unless manually over-ridden by raising threshold)

---

## Scope rules

- **DO NOT** add new OHLCV fetches — scanner already computes EMA20
- **DO NOT** filter on `< -X%` (below EMA) — only the stretched-above case
  is validated as a loss signal; below EMA in a BULLISH coin is a normal
  dip-buy entry and should NOT be blocked
- **DO NOT** touch stop-loss / cooldown / greed decay / resize / salvage
- **DO NOT** apply filter to active bots — entry-only, never exit
- **DO NOT** hardcode the threshold; always read from trend_config
- Push to GitHub when done
- Stop when tasks are complete

---

## Future iterations (out of scope for 45e)

Distance is the **single most powerful deterministic entry filter** on the
historical data. Other signals discussed during session 45 brainstorming
that did NOT make the cut for 45e but are candidates for future briefs:

- BTC correlation filter (validated: 0/11 blocked in this bull phase —
  re-validate in a bear/sideways regime)
- RSI slope (reversal from overbought, not just level)
- Volume spike filter (entry at volume climax = entry at price peak)
- ATR spike filter
- Order book depth asymmetry
- Recent realized volatility

See `config/VISION_sentinel_design_notes.md` for the full brainstorming
notes — these signals may eventually be absorbed into the AI Sentinel
(phase 3) as a non-deterministic layer on top of the deterministic
filters.

---

## Commit format

```
feat(tf): entry distance filter — skip stretched coins (45e)

One deterministic gate in the TF allocator + SWAP path: if the
candidate's price is more than tf_entry_max_distance_pct (default 10%)
above its EMA20 (4h), SKIP with FILTER_ENTRY_DISTANCE reason.

Supersedes Sonnet's original 45e draft (EMA-above + RSI cap gates).
Historical validation on v3 TF losses (11 losing allocations, $27.78
total) showed:
  Gate 1 "price < EMA20"      → 0/11 blocked (no protection)
  Gate 2 "RSI >= 70"           → 6/11 blocked (83.5% of losses)
  Distance "from EMA20 > 10%" → 7/11 blocked (92.4% of losses)

Distance catches everything RSI catches plus coins in mean-reversion
setup without elevated RSI (BOME case). It's a cleaner conceptual
proxy for "the price is too stretched from its mean".

Kill-switch: tf_entry_max_distance_pct = 0 disables. Dashboard
exposes the setting. Applies to both ALLOCATE and SWAP candidates.

New column: trend_config.tf_entry_max_distance_pct (numeric, default 10).
```
