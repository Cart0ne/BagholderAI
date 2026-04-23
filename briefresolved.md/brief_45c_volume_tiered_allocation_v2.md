# INTERN BRIEF 45c v2 — Volume-Tiered TF Allocation

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 23, 2026
**Priority:** HIGH — structural risk reduction
**Supersedes:** brief_45c_volume_tiered_allocation.md (v1)

---

## Why v2

v1 was sound in direction but had 9 open points flagged during CC's
critical review. The CEO reviewed and decided each one. v2 bakes those
decisions in. Key changes vs v1:

1. **Upward-only budget redistribution** when tiers are empty (v1 said
   "no redistribution"; too conservative — capital sits idle)
2. **Tier frozen at ALLOCATE time** via new `bot_config.volume_tier`
   column (v1 was ambiguous)
3. **`tf_max_coins` becomes derived/read-only** in dashboard
4. **Tier weights: 40 / 35 / 25** (not 45/35/20) — fixes T3 `min_notional`
   collision on Binance ($20 / 4 lots = $5, right at the limit)
5. **Scanner reads thresholds from `trend_config`** (v1 hardcoded them,
   creating a split source of truth)
6. **Exchange filter check** reuses existing `round_to_step` +
   `validate_order` logic (v1 over-simplified it)
7. **SWAP same-tier only** (v1 was ambiguous; cross-tier upgrades are
   a future brief if empirically useful)

---

## Context

The TF currently picks the 2 strongest BULLISH coins regardless of
liquidity. This produced allocations like MET/USDT ($3M daily volume)
and MOVR/USDT ($1M daily volume) — coins where a single large sell
order can crash the price 19% in one minute. The MET flash crash of
2026-04-22 cost us -$5.42 in 59 seconds. Meanwhile, high-volume coins
like AVAX ($65M/day) or LINK ($47M/day) rarely gap through stop-loss
thresholds.

**Solution:** diversify across 3 volume tiers, 1 coin per tier, with
weighted budget allocation (more capital on liquid coins, less on risky
small caps). Think of it like a fund that balances blue chips, mid
caps, and small caps.

The scanner already has `volume_24h` (from `exchange.fetch_tickers() →
quoteVolume`) on every coin. No extra API calls.

---

## Design

### Volume tiers

| Tier | Volume 24h (USDT) | Label | Typical coins | Risk |
|------|-------------------|-------|---------------|------|
| 1 | ≥ $100M | Blue chip | DOGE, BNB, TAO, ZEC | Low |
| 2 | $20M – $100M | Mid cap | AVAX, LINK, ADA, SUI, PEPE | Medium |
| 3 | < $20M | Small cap | MET, RUNE, CHZ, MOVR | High |

BTC/SOL/BONK are excluded by `MANUAL_WHITELIST` — they never enter the
candidate pool regardless of their volume tier.

### Budget allocation (CEO-revised weights)

| Tier | Weight | Amount ($100 budget) | Per-lot ($/tf_lots_per_coin=4) |
|------|--------|----------------------|-------------------------------|
| 1 | 40% | $40 | $10.00 |
| 2 | 35% | $35 | $8.75 |
| 3 | 25% | $25 | $6.25 |

T3 per-lot = $6.25 clears Binance `min_notional=$5` with ~25% headroom.
With v1 weights (20%) it was $5.00 — exactly at the limit, flakey.

### Max coins

`tf_max_coins = 3`, **derived constant, not user-editable**. The
dashboard renders it read-only with a label "derived from tier count".
If we ever add multi-slot-per-tier, that'll be a separate brief.

### Slot logic & upward budget redistribution

Each tier has 1 slot. The allocator picks the strongest BULLISH coin
within each tier independently.

**Orphan budget rule (CEO-revised):** budget flows **upward only** when
a tier has no BULLISH candidate.

| Scenario | Flow | Rationale |
|----------|------|-----------|
| No T1 candidate, T2 + T3 present | T2 gets $40 + $35 = $75, T3 stays $25 | Promote mid cap, cap small cap |
| No T2 candidate, T1 + T3 present | T1 gets $40 + $35 = $75, T3 stays $25 | Concentrate on blue chip |
| No T1 & no T2, only T3 present | T3 stays $25, $75 sits idle | Market is illiquid — stay mostly out |
| All 3 tiers present | 40 / 35 / 25 as designed | Normal path |
| No T3 candidate, T1 + T2 present | T1 $40, T2 $35, T3's $25 **sits idle** | Budget never flows **down** — small caps are risk-capped |

**Key rule:** orphan budget from Tier N flows to Tier N-1 (upward).
Never down. Never skipping levels (T1 orphan does not flow to T3).

### Tier freezing

When a coin is ALLOCATEd, its current tier is written to
`bot_config.volume_tier`. The tier is **frozen** — subsequent volume
changes don't re-tier the active coin. On DEALLOCATE / SWAP, the next
entrant gets a fresh tier lookup.

**Why:** re-tiering active coins would cause budget mismatches
(T1-allocated coin now needs T2 budget?) and SWAP incoherence. Simpler
to freeze at allocation time.

### SWAP logic

**Same-tier only.** A T2 SWAP candidate cannot replace a T1 active coin
or a T3 active coin. The existing `SWAP_STRENGTH_DELTA = 20.0` +
`SWAP_COOLDOWN_HOURS = 8` + `SWAP_MIN_PROFIT_PCT = -1.0` gates all
continue to apply within the tier.

Cross-tier upgrade (e.g. strong T2 replaces weak T3, with budget
adjustment) is intentionally out of scope for 45c. Revisit in a
follow-up if the same-tier rule proves too rigid.

---

## DB migration

```sql
-- Tier thresholds (raw USDT, easier math than "millions")
ALTER TABLE trend_config ADD COLUMN tf_tier1_min_volume numeric DEFAULT 100000000;
ALTER TABLE trend_config ADD COLUMN tf_tier2_min_volume numeric DEFAULT 20000000;

-- Tier weights (percentages; normalized in code if they don't sum to 100)
ALTER TABLE trend_config ADD COLUMN tf_tier1_weight numeric DEFAULT 40;
ALTER TABLE trend_config ADD COLUMN tf_tier2_weight numeric DEFAULT 35;
ALTER TABLE trend_config ADD COLUMN tf_tier3_weight numeric DEFAULT 25;

-- Per-coin frozen tier
ALTER TABLE bot_config ADD COLUMN volume_tier smallint;

-- Bump max coins from 2 to 3
UPDATE trend_config SET tf_max_coins = 3;

-- RLS standing rule
ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config DISABLE ROW LEVEL SECURITY;
```

---

## Scanner change — `bot/trend_follower/scanner.py`

The scanner assigns a **display tier** for Telegram reports and the
`trend_scans` table. This is cosmetic but must read the **same
thresholds** as the allocator so the two don't disagree.

### Replace rank-based with volume-based, pulling thresholds from trend_config

Currently tiers are rank-based (top 20 = A, next 20 = B, rest = C).
This is wrong: a rank-21 coin with $90M volume gets B while rank-20 at
$95M gets A.

Find the tier assignment block at the end of `scan_top_coins()` and
replace with volume-based logic. Pass the thresholds as parameters to
the function so there's a single source of truth.

```python
def scan_top_coins(
    exchange,
    n: int = 50,
    # ... existing params ...
    tier1_min_volume: float = 100_000_000,  # 45c: default matches trend_config
    tier2_min_volume: float = 20_000_000,   # 45c: default matches trend_config
):
    # ... existing body ...

    # 45c: volume-based tier assignment. Thresholds come from trend_config
    # via the caller (trend_follower.py) so the scanner and allocator
    # agree on tier boundaries.
    for i, coin in enumerate(coins):
        coin["rank"] = i + 1
        vol = float(coin.get("volume_24h", 0) or 0)
        if vol >= tier1_min_volume:
            coin["tier"] = "A"  # display label kept as A/B/C for existing consumers
        elif vol >= tier2_min_volume:
            coin["tier"] = "B"
        else:
            coin["tier"] = "C"
```

### Caller update — `bot/trend_follower/trend_follower.py`

Pass the thresholds from `trend_config` to `scan_top_coins()`:

```python
# 45c: pass volume tier thresholds so scanner and allocator agree
coins = scan_top_coins(
    exchange,
    n=scan_top_n,
    # ... existing args ...
    tier1_min_volume=float(config.get("tf_tier1_min_volume", 100_000_000)),
    tier2_min_volume=float(config.get("tf_tier2_min_volume", 20_000_000)),
)
```

---

## Allocator change — `bot/trend_follower/allocator.py`

### 1. Tier helper + constants

Near the top, after `MANUAL_WHITELIST`:

```python
# 45c: Volume tier defaults (overridden by trend_config values)
DEFAULT_TIER1_MIN_VOLUME = 100_000_000
DEFAULT_TIER2_MIN_VOLUME = 20_000_000
# < TIER2 = tier 3 (implicit)


def _assign_volume_tier(coin: dict, t1_min: float, t2_min: float) -> int:
    """45c: returns 1, 2, or 3 based on 24h quoteVolume.
    Uses integers (not strings) to match the smallint DB column."""
    vol = float(coin.get("volume_24h", 0) or 0)
    if vol >= t1_min:
        return 1
    elif vol >= t2_min:
        return 2
    else:
        return 3
```

### 2. Read tier config in `decide_allocations`

Near the existing config reads (where `max_grids`, `min_strength`, etc.
are read):

```python
# 45c: volume tier thresholds + weights
t1_min = float(config.get("tf_tier1_min_volume", DEFAULT_TIER1_MIN_VOLUME))
t2_min = float(config.get("tf_tier2_min_volume", DEFAULT_TIER2_MIN_VOLUME))
t1_weight = float(config.get("tf_tier1_weight", 40))
t2_weight = float(config.get("tf_tier2_weight", 35))
t3_weight = float(config.get("tf_tier3_weight", 25))
weight_sum = t1_weight + t2_weight + t3_weight
if weight_sum <= 0:
    weight_sum = 100  # safety fallback; weights effectively become 0/0/0 elsewhere
```

### 3. Assign tier to every classified coin

After the classifier has set `signal` / `signal_strength` on each coin,
and before the BEARISH / HOLD / SWAP logic:

```python
# 45c: tag every candidate with its current volume tier (1/2/3)
for coin in classified_coins:
    coin["volume_tier"] = _assign_volume_tier(coin, t1_min, t2_min)
```

### 4. Rewrite ALLOCATE loop (per-tier with upward redistribution)

Replace the existing "Equal-split allocation" block and the `for coin
in bullish:` loop with:

```python
# 45c: Per-tier allocation with upward-only orphan redistribution.
# Each tier has 1 slot. Empty slot budget flows UP to the next tier
# (T3 orphan → T2, T2 orphan → T1). Never flows down — T3 exposure
# stays capped regardless of T1/T2 signals.

# Step A: which tiers already have an active bot? Read volume_tier
# from the DB record (frozen at allocation time). Fallback: re-tier
# using current scan data if volume_tier is NULL (pre-45c allocations).
active_tier_map: dict[int, str] = {}  # tier -> symbol
for alloc in current_allocations:
    if not alloc.get("is_active"):
        continue
    sym = alloc["symbol"]
    stored_tier = alloc.get("volume_tier")
    if stored_tier is not None:
        tier = int(stored_tier)
    else:
        # Legacy row (pre-45c); infer tier from current scan
        matching = [c for c in classified_coins if c["symbol"] == sym]
        if matching:
            tier = _assign_volume_tier(matching[0], t1_min, t2_min)
        else:
            tier = 3  # safest fallback for illiquid active coin
    active_tier_map[tier] = sym

# Step B: pick the strongest BULLISH candidate per empty tier.
# Build a dict of {tier: best_candidate or None} so we can later
# redistribute budgets without losing track of which tiers are empty.
active_symbols = {a["symbol"] for a in current_allocations if a.get("is_active")}
tier_best: dict[int, Optional[dict]] = {}
for tier_key in (1, 2, 3):
    if tier_key in active_tier_map:
        tier_best[tier_key] = None  # slot occupied, no new allocation
        continue
    candidates = [
        c for c in bullish
        if c.get("volume_tier") == tier_key
        and c["symbol"] not in active_symbols
    ]
    if not candidates:
        tier_best[tier_key] = None
        continue
    tier_best[tier_key] = max(
        candidates,
        key=lambda c: float(c.get("signal_strength", 0) or 0),
    )

# Step C: compute tier budgets with upward-only orphan flow.
# Walk from T3 up: if a tier's slot is unfilled AND its budget would
# otherwise sit idle, push it up to the next-higher tier.
base_budget = {
    1: total_capital * (t1_weight / weight_sum),
    2: total_capital * (t2_weight / weight_sum),
    3: total_capital * (t3_weight / weight_sum),
}
tier_budget = dict(base_budget)

# T3 orphan flows up to T2 if T3 is unfilled (neither active nor
# newly-assigned). T2 orphan then flows up to T1 by the same logic.
# Order matters: resolve T3 first, then T2.
def _tier_will_be_empty(tier: int) -> bool:
    return tier not in active_tier_map and tier_best.get(tier) is None

if _tier_will_be_empty(3):
    tier_budget[2] += tier_budget[3]
    tier_budget[3] = 0.0
if _tier_will_be_empty(2):
    tier_budget[1] += tier_budget[2]
    tier_budget[2] = 0.0
# T1 orphan stays idle by design — never flows down.

# Step D: emit ALLOCATE decisions for each filled slot.
lots_per_coin = int(config.get("tf_lots_per_coin", 4))
cpt_cap = float(config.get("tf_capital_per_trade_cap_usd", 50))
sanity_cap_usd = float(config.get("tf_sanity_cap_usd", 300))

for tier_key in (1, 2, 3):
    coin = tier_best.get(tier_key)
    if coin is None:
        # Either tier is already active (HOLD path handles it) or
        # truly empty (orphan redistribution has moved the budget).
        continue

    alloc_amount = tier_budget[tier_key]
    alloc_amount = min(alloc_amount, sanity_cap_usd, unallocated)
    if alloc_amount <= 0:
        decisions.append(_make_decision(
            scan_ts, coin["symbol"], coin, "SKIP",
            f"Tier {tier_key}: no unallocated capital",
        ))
        continue

    # min_allocate_strength gate (44c — applies per-tier)
    coin_strength = float(coin.get("signal_strength", 0) or 0)
    if coin_strength < min_strength:
        decisions.append(_make_decision(
            scan_ts, coin["symbol"], coin, "SKIP",
            f"Tier {tier_key} best ({coin['symbol']}) strength "
            f"{coin_strength:.2f} below min {min_strength}",
        ))
        continue

    # Exchange filter check — REUSE the existing round_to_step +
    # validate_order logic from the old allocator (don't simplify).
    # Simulate per-level: alloc / 5 grid levels.
    per_level_usd = alloc_amount / 5
    per_level_amount = per_level_usd / coin["price"] if coin.get("price", 0) > 0 else 0
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

    # Config snapshot — note the new volume_tier field
    tier, max_pct = _get_tier_info(coin["symbol"], coin_tiers)
    config_snapshot = {
        "symbol": coin["symbol"],
        "capital_allocation": round(alloc_amount, 2),
        "tier": tier,
        "max_allocation_pct": max_pct,
        "signal": coin["signal"],
        "signal_strength": coin["signal_strength"],
        "volume_tier": tier_key,  # 45c: frozen volume tier
        "volume_24h": float(coin.get("volume_24h", 0) or 0),
    }

    decisions.append(_make_decision(
        scan_ts, coin["symbol"], coin, "ALLOCATE",
        f"Tier {tier_key} (vol ${coin.get('volume_24h', 0)/1e6:.1f}M): "
        f"strongest BULLISH (strength={coin_strength:.1f}, "
        f"budget ${alloc_amount:.0f})",
        config_snapshot=config_snapshot,
    ))

    unallocated -= alloc_amount
    active_count += 1

    logger.info(
        f"[ALLOCATOR] Tier {tier_key} ALLOCATE {coin['symbol']} "
        f"(vol ${coin.get('volume_24h', 0)/1e6:.1f}M, "
        f"strength {coin_strength:.1f}, budget ${alloc_amount:.0f})"
    )
```

### 5. Include `volume_tier` in the ALLOCATE `row_fields`

In the `apply_allocations` / `_make_decision` path, wherever the dict
that becomes `bot_config` is built, add `volume_tier` from the
`config_snapshot`. Mirror how other snapshot fields (capital_allocation,
signal, etc.) get propagated.

### 6. SWAP tier guard (same-tier only)

In the SWAP evaluation loop, after picking `best_new` but before the
strength-delta / profit checks, add the tier comparison:

```python
# 45c: SWAP only within the same volume tier. Read active coin's
# frozen tier from its bot_config row (via current_allocations),
# NOT from the current scan data.
active_tier = alloc.get("volume_tier")
if active_tier is not None:
    active_tier = int(active_tier)
else:
    # Legacy row — infer from current scan
    active_tier = _assign_volume_tier(active_coin, t1_min, t2_min)

candidate_tier = best_new.get("volume_tier")
if candidate_tier != active_tier:
    logger.debug(
        f"[ALLOCATOR] SWAP skip {best_new['symbol']} → {sym}: cross-tier "
        f"(candidate tier {candidate_tier} vs active tier {active_tier})"
    )
    continue
```

This `continue` skips to the next active coin — the candidate gets a
shot against each active coin, but only same-tier matches proceed.

---

## Dashboard change — `web/tf.html` + `web2/tf.html`

Add 5 fields to `TF_SAFETY_FIELDS` (both copies, keep them in sync):

```javascript
{ key: 'tf_tier1_min_volume', label: 'Tier 1 min volume ($)',
  sub: '45c: coins with 24h quoteVolume ≥ this are Tier 1 (blue chip). Default $100M. Scanner + allocator both read this.' },
{ key: 'tf_tier2_min_volume', label: 'Tier 2 min volume ($)',
  sub: '45c: ≥ this = Tier 2 (mid cap); below = Tier 3 (small cap). Default $20M.' },
{ key: 'tf_tier1_weight', label: 'Tier 1 weight (%)',
  sub: '45c: % of TF budget allocated to Tier 1 slot. Default 40. All 3 weights normalized if they don\'t sum to 100.' },
{ key: 'tf_tier2_weight', label: 'Tier 2 weight (%)',
  sub: '45c: % of TF budget for Tier 2. Default 35.' },
{ key: 'tf_tier3_weight', label: 'Tier 3 weight (%)',
  sub: '45c: % of TF budget for Tier 3. Default 25. Orphan budget (empty tier) flows UPWARD only — T3 orphan → T2, T2 orphan → T1. T3 exposure always capped at this weight.' },
```

**Also: render `tf_max_coins` as read-only** with a hint like
`"derived: 1 slot × 3 tiers = 3"`. Detect it by key name in the
existing `configField` renderer, or add a `readOnly` flag to the
field descriptor — whichever fits the existing pattern best.

---

## Telegram report — `bot/trend_follower/trend_follower.py`

Update the tier names in the scan report so the labels reflect volume
ranges, not rank ranges:

```python
# 45c: volume-based tier labels
tier_names = {
    "A": "🔵 Tier 1 (≥$100M vol)",
    "B": "🟡 Tier 2 ($20M–$100M)",
    "C": "🔴 Tier 3 (<$20M)",
}
```

Labels are cosmetic; keep the A/B/C keys for backwards-compat with
existing log consumers.

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/scanner.py` | MODIFY | Accept `tier1_min_volume` + `tier2_min_volume` params; replace rank-based tiers with volume-based |
| `bot/trend_follower/trend_follower.py` | MODIFY | Pass thresholds to `scan_top_coins()`; update Telegram tier labels |
| `bot/trend_follower/allocator.py` | MODIFY | Add `_assign_volume_tier` helper + DEFAULT constants; tag coins with `volume_tier`; rewrite ALLOCATE loop (per-tier + upward orphan redistribution); add same-tier SWAP guard; include `volume_tier` in config_snapshot / row_fields |
| `web/tf.html` | MODIFY | Add 5 tier fields to `TF_SAFETY_FIELDS`; make `tf_max_coins` read-only |
| `web2/tf.html` | MODIFY | Same as web/tf.html (keep copies in sync) |
| DB (`trend_config`, `bot_config`) | MIGRATE | Add tier columns; UPDATE `tf_max_coins=3` |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes
- `bot/grid_runner.py` — no changes
- `config/settings.py` — manual bot config unchanged
- Manual bots (BTC/SOL/BONK) — `MANUAL_WHITELIST` excludes them
- Stop-loss / SL cooldown / greed decay / sell_pct salvage — independent features (45a, 45b)
- `capital_per_trade` calculation — automatically correct because it
  derives from `capital_allocation / tf_lots_per_coin` and the new
  25% weight on T3 keeps the per-lot above min_notional
- `web/admin.html` — manual bots only, allocator never touches them

---

## Test checklist

### DB migration
- [ ] Columns present with correct defaults (100M / 20M / 40 / 35 / 25)
- [ ] `bot_config.volume_tier` exists (smallint, nullable)
- [ ] `tf_max_coins = 3`
- [ ] RLS disabled on both tables

### Tier assignment
- [ ] Coin with volume $200M → tier 1
- [ ] Coin with volume exactly $100M → tier 1 (boundary: ≥)
- [ ] Coin with volume $50M → tier 2
- [ ] Coin with volume exactly $20M → tier 2 (boundary: ≥)
- [ ] Coin with volume $5M → tier 3
- [ ] Coin with volume 0 or missing → tier 3
- [ ] Scanner + allocator agree on tier for the same coin

### Per-tier allocation — full lineup
- [ ] 3 BULLISH candidates, one per tier → all 3 allocated with
      $40 / $35 / $25 respectively
- [ ] Each `bot_config` row has `volume_tier` set (1, 2, 3)

### Upward orphan redistribution
- [ ] No T3 candidate, T1 + T2 present → T1 $40, T2 $35,
      **T3's $25 sits idle** (never flows down)
- [ ] No T2 candidate, T1 + T3 present → T1 gets $40 + $35 = $75,
      T3 gets $25
- [ ] No T1 candidate, T2 + T3 present → T2 gets $40 + $35 = $75,
      T3 gets $25
- [ ] No T1, no T2, only T3 → T3 gets $25, rest idle
- [ ] All tiers empty → no allocation, no crash

### Tier freezing
- [ ] ALLOCATE a coin as T2. Manually lower its volume in the next
      scan so it would recompute as T3. Confirm the active coin's
      tier stays 2 (frozen) and its budget doesn't change.
- [ ] SWAP / DEALLOCATE → the replacement gets a fresh tier lookup.

### SWAP tier guard
- [ ] Active T2 (strength 20). New T1 candidate (strength 45).
      SWAP does NOT fire (cross-tier).
- [ ] Active T2 (strength 20). New T2 candidate (strength 45).
      SWAP fires (same tier, +25 delta ≥ 20).
- [ ] Active T3 (strength 15). New T3 candidate (strength 38).
      SWAP fires (same tier, +23 delta).
- [ ] Active T3 (strength 15). New T1 candidate (strength 60).
      SWAP does NOT fire, even though delta is massive (cross-tier).

### Exchange filter (the T3-at-$20 bug from v1)
- [ ] Tier 3 allocation of $25 / 4 lots = $6.25 per lot — passes
      Binance `min_notional=$5`.
- [ ] T3 coin with `step_size` that makes per-level quantity round
      below min_notional → FILTER_FAIL SKIP (reuses existing logic).

### Manual bot exclusion
- [ ] BTC/USDT (T1 by volume) never enters tier_candidates.
- [ ] SOL/USDT same.
- [ ] BONK/USDT (T3 by volume) same.

### tf_max_coins read-only
- [ ] Dashboard renders `tf_max_coins = 3` dimmed / read-only.
- [ ] Manually PATCHing `trend_config.tf_max_coins` in Supabase
      has no effect on allocator behaviour (allocator ignores it —
      logic is hardcoded to 3 tiers × 1 slot).

### Dashboard (web + web2)
- [ ] All 5 new fields render on `/tf` with correct defaults
- [ ] Edit each → DB updates correctly
- [ ] Changes apply to next TF scan (no restart needed for reads;
      scanner + allocator both fetch trend_config per-scan)

### Telegram report
- [ ] Tier labels show "Tier 1 (≥$100M vol)" etc.
- [ ] Top bullish per tier groups coins by actual volume

### Budget math
- [ ] Budget $100, weights 40/35/25 → $40 / $35 / $25 ✓
- [ ] Weights that don't sum to 100 (e.g. 40/30/20 = 90) →
      normalized: $44.44 / $33.33 / $22.22 (proportional)
- [ ] Compound growth: budget $150 → $60 / $52.50 / $37.50
      (tier budgets scale proportionally)

### Legacy data (pre-45c allocations at first scan)
- [ ] MET, RUNE active before deploy with `volume_tier = NULL`.
      First post-deploy scan: allocator infers their tier from the
      current scan and populates `active_tier_map` correctly.
- [ ] If they're both T3, T1 + T2 slots are empty → next scan
      fills them.

---

## Scope rules

- **DO NOT** change stop-loss, SL cooldown, greed decay, sell_pct
  salvage (features from 45a / 45b are independent)
- **DO NOT** allow orphan budget to flow downward
- **DO NOT** allow cross-tier SWAP (even upgrades — future brief)
- **DO NOT** touch manual bots or `web/admin.html`
- **DO NOT** change `capital_per_trade` formula (it automatically
  adapts because it's derived from `capital_allocation / lots_per_coin`)
- **DO NOT** hardcode tier thresholds in the scanner — always read
  from `trend_config` via the caller
- **DO NOT** simplify the exchange filter check — reuse `round_to_step`
  + `validate_order` as the existing allocator does
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(tf): volume-tiered allocation (45c v2)

Replaces flat top-N-by-strength allocation with a 3-tier liquidity split:
  Tier 1 (≥$100M vol): 40% budget, 1 coin — blue chip, low flash risk
  Tier 2 ($20M–$100M): 35% budget, 1 coin — mid cap
  Tier 3 (<$20M vol):  25% budget, 1 coin — small cap, capped exposure

Each tier picks its strongest BULLISH coin independently. Orphan budget
from empty tiers flows UPWARD only (T3 orphan → T2, T2 orphan → T1),
never down — small-cap exposure stays capped at 25%. SWAP restricted to
same tier.

Tier is frozen at ALLOCATE time (new column bot_config.volume_tier) so
subsequent volume shifts don't re-tier active coins. Thresholds read
from trend_config by both scanner (display) and allocator (decision) —
single source of truth. tf_max_coins becomes a derived constant (= 3).

Weights 40/35/25 (not 45/35/20) so T3 per-lot = $6.25 clears Binance
min_notional=$5 with headroom. Manual bots (BTC/SOL/BONK) remain
excluded via MANUAL_WHITELIST.

Motivated by the MET/USDT flash crash (2026-04-22): 19% drop in 1
minute on a $3M/day volume coin caused -$5.42 loss. With tiered
allocation, worst-case T3 exposure is $25 instead of $50.

New columns: trend_config.tf_tier1_min_volume, tf_tier2_min_volume,
tf_tier1_weight, tf_tier2_weight, tf_tier3_weight, bot_config.volume_tier.
```
