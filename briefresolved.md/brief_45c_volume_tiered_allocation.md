# INTERN BRIEF 45c — Volume-Tiered TF Allocation

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 22, 2026
**Priority:** HIGH — structural risk reduction

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
small caps). Think of it like a fund that balances blue chips, mid caps,
and small caps.

The scanner already has `volume_24h` (from `exchange.fetch_tickers() →
quoteVolume`) on every coin. No extra API calls needed.

---

## Design

### Volume tiers

| Tier | Volume 24h (USDT) | Label | Typical coins | Risk |
|------|-------------------|-------|---------------|------|
| 1 | > $100M | Blue chip | ETH, DOGE, BNB, TAO | Low |
| 2 | $20M – $100M | Mid cap | AVAX, LINK, ADA, SUI, PEPE | Medium |
| 3 | < $20M | Small cap | MET, RUNE, CHZ, MOVR | High |

BTC/USDT, SOL/USDT, BONK/USDT are already excluded by
`MANUAL_WHITELIST` — they never enter the candidate pool.

### Budget allocation

| Tier | Weight | Amount ($100 budget) |
|------|--------|---------------------|
| 1 | 45% | $45 |
| 2 | 35% | $35 |
| 3 | 20% | $20 |

More capital on liquid coins (less risk), less on monetacce (more risk
but capped exposure). If a Tier 3 coin flash-crashes 19%, worst case
is ~$2.80 loss instead of ~$7 with equal allocation.

### Max coins: 2 → 3

`tf_max_coins` changes from 2 to 3 (one per tier). This is a DB update,
not a code change.

### Slot logic

Each tier has exactly 1 slot. The allocator picks the strongest BULLISH
coin **within each tier** independently. If no BULLISH coin exists in a
tier, that slot stays empty — the budget is NOT redistributed to other
tiers. This prevents the system from concentrating on a single tier
when the market is quiet.

---

## DB migration

```sql
-- Volume tier thresholds and weights (new columns on trend_config)
ALTER TABLE trend_config ADD COLUMN tf_tier1_min_volume numeric DEFAULT 100000000;
ALTER TABLE trend_config ADD COLUMN tf_tier2_min_volume numeric DEFAULT 20000000;
ALTER TABLE trend_config ADD COLUMN tf_tier1_weight numeric DEFAULT 45;
ALTER TABLE trend_config ADD COLUMN tf_tier2_weight numeric DEFAULT 35;
ALTER TABLE trend_config ADD COLUMN tf_tier3_weight numeric DEFAULT 20;

-- Bump max coins from 2 to 3
UPDATE trend_config SET tf_max_coins = 3;

-- RLS
ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
```

Threshold columns are in raw USDT (not millions) for easier math.
Weights are percentages that must sum to 100; enforced in code, not DB.

---

## Scanner change — `bot/trend_follower/scanner.py`

### Replace rank-based tiers with volume-based tiers

Currently, tiers are assigned by **rank position** (top 20 = A, next
20 = B, last 10 = C). This is wrong — a coin at rank 21 with $90M
volume gets tier B, while rank 20 with $95M gets tier A. Volume tiers
must be based on actual `quoteVolume`.

Find the tier assignment block at the end of `scan_top_coins()`:

```python
# Current code (REPLACE):
for i, coin in enumerate(coins):
    coin["rank"] = i + 1
    if i < 20:
        coin["tier"] = "A"
    elif i < 40:
        coin["tier"] = "B"
    else:
        coin["tier"] = "C"
```

Replace with:

```python
# 45c: volume-based tier assignment
# Thresholds are passed via trend_config but we don't have access here.
# Instead, the raw volume_24h is already on each coin — the allocator
# assigns the tier at decision time using the config thresholds. Here
# we just keep rank for logging/display and remove the old tier field.
for i, coin in enumerate(coins):
    coin["rank"] = i + 1
    # Tier assignment moved to allocator (45c) — scanner no longer
    # assigns tier. Legacy tier field kept for backwards compat with
    # trend_scans table and Telegram report.
    vol = coin.get("volume_24h", 0)
    if vol >= 100_000_000:
        coin["tier"] = "A"
    elif vol >= 20_000_000:
        coin["tier"] = "B"
    else:
        coin["tier"] = "C"
```

**Note:** this still uses hardcoded thresholds for the scanner's tier
label (used in Telegram report + trend_scans). The allocator reads the
real thresholds from `trend_config` for the allocation decision. A small
mismatch is acceptable — the scanner tier is cosmetic, the allocator
tier is what matters.

---

## Allocator change — `bot/trend_follower/allocator.py`

This is the main change. The allocator currently picks the N strongest
BULLISH coins regardless of volume. We change it to pick 1 coin per
volume tier.

### 1. Add tier helper

Near the top of the file, after `MANUAL_WHITELIST`:

```python
# 45c: Volume tier thresholds (defaults, overridden by trend_config)
DEFAULT_TIER1_MIN_VOLUME = 100_000_000  # > $100M = blue chip
DEFAULT_TIER2_MIN_VOLUME = 20_000_000   # $20M–$100M = mid cap
# < $20M = small cap (implicit)


def _assign_volume_tier(coin: dict, t1_min: float, t2_min: float) -> str:
    """
    Assign a volume tier based on 24h quoteVolume.
    Returns '1', '2', or '3'.
    """
    vol = float(coin.get("volume_24h", 0) or 0)
    if vol >= t1_min:
        return "1"
    elif vol >= t2_min:
        return "2"
    else:
        return "3"
```

### 2. Read tier config

In `decide_allocations`, after reading existing config values (where
`tf_max_coins`, `min_allocate_strength`, etc. are read), add:

```python
# 45c: volume tier thresholds and weights
t1_min = float(config.get("tf_tier1_min_volume", DEFAULT_TIER1_MIN_VOLUME))
t2_min = float(config.get("tf_tier2_min_volume", DEFAULT_TIER2_MIN_VOLUME))
t1_weight = float(config.get("tf_tier1_weight", 45))
t2_weight = float(config.get("tf_tier2_weight", 35))
t3_weight = float(config.get("tf_tier3_weight", 20))
weight_sum = t1_weight + t2_weight + t3_weight
if weight_sum <= 0:
    weight_sum = 100  # safety fallback
```

### 3. Assign volume tier to each classified coin

After the existing classifier pass (where each coin gets `signal` and
`signal_strength`), and BEFORE the BEARISH/HOLD/SWAP logic for active
coins, add:

```python
# 45c: assign volume tier to every classified coin
for coin in classified_coins:
    coin["volume_tier"] = _assign_volume_tier(coin, t1_min, t2_min)
```

### 4. Rewrite the ALLOCATE loop

The current ALLOCATE logic iterates over `bullish` (sorted by strength)
and fills up to `max_grids` slots with equal-split budget. Replace this
with a **per-tier** approach.

Replace the ALLOCATE section (from the "Equal-split allocation" comment
through the end of the bullish loop) with:

```python
# 45c: Per-tier allocation — 1 coin per volume tier, weighted budget.
# Each tier independently picks the strongest BULLISH candidate.
# If no BULLISH coin exists in a tier, that slot stays empty.

tier_budget = {
    "1": total_capital * (t1_weight / weight_sum),
    "2": total_capital * (t2_weight / weight_sum),
    "3": total_capital * (t3_weight / weight_sum),
}

# Which tiers already have an active TF bot?
active_tiers = {}
for alloc in current_allocs:
    if not alloc.get("is_active"):
        continue
    sym = alloc["symbol"]
    # Find this symbol's volume tier from the classified coins
    matching = [c for c in classified_coins if c["symbol"] == sym]
    if matching:
        vt = matching[0].get("volume_tier", "3")
    else:
        # Active coin not in current scan (fell out of top-N);
        # fall back to its stored volume_24h or default to tier 3
        vt = "3"
    active_tiers[vt] = sym

for tier_key in ["1", "2", "3"]:
    # Skip if this tier already has an active coin
    if tier_key in active_tiers:
        continue

    # Candidates for this tier: BULLISH, correct volume tier, not in
    # MANUAL_WHITELIST (already filtered), not already active
    active_symbols = {a["symbol"] for a in current_allocs if a.get("is_active")}
    tier_candidates = [
        c for c in bullish
        if c.get("volume_tier") == tier_key
        and c["symbol"] not in active_symbols
    ]

    if not tier_candidates:
        logger.info(
            f"[ALLOCATOR] Tier {tier_key}: no BULLISH candidates, slot empty"
        )
        continue

    # Pick the strongest by signal_strength
    best = max(tier_candidates, key=lambda c: float(c.get("signal_strength", 0)))

    # min_allocate_strength gate (44c)
    coin_strength = float(best.get("signal_strength", 0) or 0)
    if coin_strength < min_strength:
        decisions.append(_make_decision(
            scan_ts, best["symbol"], best, "SKIP",
            f"Tier {tier_key} best ({best['symbol']}) strength "
            f"{coin_strength:.2f} below min {min_strength}",
        ))
        continue

    alloc_amount = tier_budget[tier_key]

    # Sanity cap (existing logic)
    sanity_cap_usd = float(config.get("tf_sanity_cap_usd", 300))
    alloc_amount = min(alloc_amount, sanity_cap_usd)

    # Check unallocated capital
    if alloc_amount > unallocated:
        alloc_amount = unallocated
    if alloc_amount <= 0:
        decisions.append(_make_decision(
            scan_ts, best["symbol"], best, "SKIP",
            f"Tier {tier_key}: no capital remaining",
        ))
        continue

    # Exchange filter check (existing logic)
    ef = exchange_filters.get(best["symbol"], {})
    min_notional = ef.get("min_notional", 5.0)
    test_amount = alloc_amount / 5
    if test_amount < min_notional:
        decisions.append(_make_decision(
            scan_ts, best["symbol"], best, "SKIP",
            f"Tier {tier_key}: allocation ${alloc_amount:.0f} too small "
            f"for exchange filter (min_notional=${min_notional})",
        ))
        continue

    decisions.append(_make_decision(
        scan_ts, best["symbol"], best, "ALLOCATE",
        f"Tier {tier_key} (vol ${best.get('volume_24h', 0)/1e6:.1f}M): "
        f"strongest BULLISH (strength={coin_strength:.1f})",
        config_snapshot={"capital_allocation": round(alloc_amount, 2),
                         "price": best.get("price", 0)},
    ))
    unallocated -= alloc_amount
    active_count += 1

    logger.info(
        f"[ALLOCATOR] Tier {tier_key} ALLOCATE {best['symbol']} "
        f"(vol ${best.get('volume_24h', 0)/1e6:.1f}M, "
        f"strength {coin_strength:.1f}, "
        f"budget ${alloc_amount:.0f})"
    )
```

### 5. SWAP logic — tier-aware

The existing SWAP logic replaces an active coin with a stronger one.
With volume tiers, a SWAP should only replace within the SAME tier —
a Tier 3 coin should not be swapped for a Tier 1 coin (they have
different budget allocations and risk profiles).

In the SWAP section, add a tier filter. Find where swap candidates are
compared against active coins. Add this guard:

```python
# 45c: SWAP only within the same volume tier
active_tier = _assign_volume_tier(active_coin_data, t1_min, t2_min)
candidate_tier = candidate.get("volume_tier", "3")
if active_tier != candidate_tier:
    continue  # cross-tier swap not allowed
```

Place this BEFORE the strength-delta comparison. Log the skip if useful:

```python
if active_tier != candidate_tier:
    logger.debug(
        f"[ALLOCATOR] SWAP skip {candidate['symbol']} for "
        f"{active_coin_data['symbol']}: cross-tier "
        f"(candidate tier {candidate_tier} vs active tier {active_tier})"
    )
    continue
```

---

## Dashboard change — `web/tf.html`

Add the new `trend_config` fields to the TF Safety Parameters section.

In the `TF_SAFETY_FIELDS` array (around tf.html:85), add:

```javascript
{ key: 'tf_tier1_min_volume', label: 'Tier 1 min volume ($)',
  sub: '45c: coins with 24h quoteVolume above this are Tier 1 (blue chip). Default $100M.' },
{ key: 'tf_tier2_min_volume', label: 'Tier 2 min volume ($)',
  sub: '45c: coins between Tier 2 min and Tier 1 min are Tier 2 (mid cap). Below this = Tier 3 (small cap). Default $20M.' },
{ key: 'tf_tier1_weight', label: 'Tier 1 weight (%)',
  sub: '45c: % of TF budget allocated to Tier 1 slot. All 3 weights must sum to 100.' },
{ key: 'tf_tier2_weight', label: 'Tier 2 weight (%)',
  sub: '45c: % of TF budget allocated to Tier 2 slot.' },
{ key: 'tf_tier3_weight', label: 'Tier 3 weight (%)',
  sub: '45c: % of TF budget allocated to Tier 3 slot.' },
```

---

## Telegram report — `bot/trend_follower/trend_follower.py`

The scan report already shows "Top bullish per tier". With volume-based
tiers, the labels should reflect volume ranges instead of rank ranges.

In `send_scan_report`, update the `tier_names` dict:

```python
# 45c: volume-based tier labels
tier_names = {
    "A": "🔵 Tier 1 (>$100M vol)",
    "B": "🟡 Tier 2 ($20M–$100M)",
    "C": "🔴 Tier 3 (<$20M)",
}
```

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/scanner.py` | MODIFY | Replace rank-based tier assignment with volume-based |
| `bot/trend_follower/allocator.py` | MODIFY | Add `_assign_volume_tier` helper; rewrite ALLOCATE loop to per-tier; tier-guard SWAP logic |
| `bot/trend_follower/trend_follower.py` | MODIFY | Update tier labels in Telegram report |
| `web/tf.html` | MODIFY | Add tier threshold + weight fields to dashboard |
| DB (`trend_config`) | MIGRATE | Add tier columns; update `tf_max_coins = 3` |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes
- `bot/grid_runner.py` — no changes
- `config/settings.py` — manual bot config unchanged
- Manual bots (BTC/SOL/BONK) — `MANUAL_WHITELIST` already excludes them
- `bot_config` table — no schema changes
- Stop-loss / cooldown / greed decay logic — independent features

---

## Test checklist

### DB migration
- [ ] Run migration on Supabase
- [ ] Confirm new columns exist with correct defaults
- [ ] Confirm `tf_max_coins = 3`

### Volume tier assignment
- [ ] Coin with volume $200M → tier "1" (or "A" in scanner)
- [ ] Coin with volume $50M → tier "2" (or "B")
- [ ] Coin with volume $5M → tier "3" (or "C")
- [ ] Coin with volume exactly $100M → tier "1" (boundary: >=)
- [ ] Coin with volume exactly $20M → tier "2" (boundary: >=)
- [ ] Coin with volume $0 or missing → tier "3"

### Per-tier allocation
- [ ] 3 BULLISH coins in different tiers → all 3 allocated with
      correct tier budgets ($45 / $35 / $20)
- [ ] 2 BULLISH coins in Tier 1 and Tier 2, none in Tier 3 →
      2 allocated, Tier 3 slot empty. Budget NOT redistributed.
- [ ] 3 BULLISH coins all in Tier 3 → only 1 allocated (1 slot
      per tier). Other 2 get SKIP.
- [ ] No BULLISH coins in any tier → no allocation, all SKIP.
- [ ] Active coin in Tier 1 + new scan → Tier 1 HOLD, Tier 2 and
      Tier 3 evaluated for ALLOCATE.

### SWAP tier guard
- [ ] Active Tier 2 coin with strength 20. New Tier 1 candidate with
      strength 45. SWAP should NOT fire (cross-tier).
- [ ] Active Tier 2 coin with strength 20. New Tier 2 candidate with
      strength 45. SWAP fires (same tier, +25 delta).
- [ ] Active Tier 3 coin with strength 15. New Tier 3 candidate with
      strength 38. SWAP fires (same tier, +23 delta).

### Manual bot exclusion
- [ ] BTC/USDT (volume > $1B, Tier 1 by volume) is never in the
      candidate pool. Confirm MANUAL_WHITELIST filters it out before
      tier assignment.
- [ ] SOL/USDT same check.
- [ ] BONK/USDT same check (would be Tier 3 by volume, still excluded).

### Dashboard
- [ ] `/tf` shows new fields with correct defaults
- [ ] Change thresholds → DB updates correctly
- [ ] Change weights → DB updates correctly

### Telegram report
- [ ] Scan report shows volume-based tier labels
- [ ] Top bullish per tier reflects actual volume grouping

### Budget math
- [ ] With $100 budget and weights 45/35/20:
      Tier 1 = $45, Tier 2 = $35, Tier 3 = $20.
      Sum = $100 ✓
- [ ] With weights 50/30/20 (changed by Max):
      Tier 1 = $50, Tier 2 = $30, Tier 3 = $20.
      Sum = $100 ✓
- [ ] With weights that don't sum to 100 (e.g. 45/35/25 = 105):
      normalized: 45/105 × 100 = $42.86, etc. Code handles via
      `weight_sum` normalization.

### Compounding interaction
- [ ] If TF budget grows via compounding (36g), tier budgets scale
      proportionally. E.g. budget $120: T1=$54, T2=$42, T3=$24.

---

## Scope rules

- **DO NOT** change stop-loss, cooldown, or greed decay logic
- **DO NOT** redistribute unused tier budget to other tiers
- **DO NOT** allow cross-tier SWAP
- **DO NOT** touch manual bots
- **DO NOT** change `capital_per_trade` calculation (it derives from
  `capital_allocation / tf_lots_per_coin` — works automatically with
  the new per-tier budgets)
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(tf): volume-tiered allocation — 1 coin per liquidity tier (45c)

Replaces flat best-2-by-strength allocation with per-tier selection:
  Tier 1 (>$100M vol): 45% budget, 1 coin — liquid, low flash-crash risk
  Tier 2 ($20M–$100M): 35% budget, 1 coin — mid cap
  Tier 3 (<$20M vol):  20% budget, 1 coin — small cap, capped exposure

Each tier picks its strongest BULLISH coin independently. Empty tiers
stay empty — budget is NOT redistributed. SWAP restricted to same tier.
tf_max_coins bumped from 2 to 3.

Thresholds and weights are configurable via trend_config and /tf dashboard.
Manual bots (BTC/SOL/BONK) remain excluded by MANUAL_WHITELIST.

Motivated by MET/USDT flash crash: 19% drop in 1 minute on a $3M/day
volume coin caused -$5.42 loss. With tiered allocation, worst-case
Tier 3 exposure is $20 instead of $50.

New columns: tf_tier1_min_volume, tf_tier2_min_volume,
tf_tier1_weight, tf_tier2_weight, tf_tier3_weight.
```
