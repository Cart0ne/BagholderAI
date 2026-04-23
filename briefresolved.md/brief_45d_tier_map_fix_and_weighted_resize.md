# INTERN BRIEF 45d — Tier-Map Collision Fix + Weighted Resize

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 23, 2026
**Priority:** HIGH — closes a correctness bug that already produced a 4th TF allocation beyond tf_max_coins

---

## Context

After deploying 45c (volume-tiered allocation) on 2026-04-23, the
first post-deploy scan at 10:56:48 UTC produced an allocation that
violated the `tf_max_coins = 3` invariant: the system ended up with 4
active TF bots (RUNE, SPK, HUMA, STRK). Post-mortem traced the bug to
two independent issues:

### Bug A — dict collision in `active_tier_map`

The current 45c code maps active bots to their frozen tier:

```python
active_tier_map: dict[int, str] = {}
for alloc in current_allocations:
    ...
    active_tier_map[tier_n] = sym  # silent overwrite
```

When 2+ active bots fall into the same tier (common on legacy rows
where `volume_tier IS NULL` and fallback uses current scan volume),
the second assignment **overwrites** the first silently. The code
then sees 2 active bots as "1 active bot in tier X + 1 slot free
elsewhere" and happily allocates a 4th bot.

Concrete example from the 10:56:48 scan:
- RUNE active (legacy NULL → fallback volume $7M → T3)
- SPK active (legacy NULL → fallback volume $105M → T1)
- HUMA active (legacy NULL → fallback volume $9M → T3)

Fallback dict state after the loop: `{1: SPK, 3: HUMA}` (RUNE's
T3 entry was overwritten by HUMA). Code saw T2 as empty and
allocated STRK as a 4th TF bot.

### Bug B — `resize_active_allocations` ignores tier weights

The resize function at `allocator.py:727-807` predates 45c. It still
applies equal-split:

```python
target_alloc = tf_total_capital / tf_max_coins  # $74.83 / 3 = $24.94 for all
```

This means even if the allocation loop writes correct per-tier
budgets at ALLOCATE time, the resize on the next scan "levels" them
all to the same amount, undoing the 40/35/25 weight design.

---

## Scope

Two surgical fixes in `bot/trend_follower/allocator.py`. No DB
migration, no new config fields, no dashboard changes.

### Fix A — `active_tier_map` collision

Replace the dict-based map with a **set of occupied tiers + list of
bots per tier** so collisions are visible to downstream logic:

```python
# 45d: set of tiers that are already occupied by at least one active bot.
# Using a set avoids the silent overwrite that dict[int, str] had when
# two legacy bots fell into the same tier via fallback tagging.
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
            tier_n = 3
    active_tiers.add(tier_n)
    active_count_global += 1
```

Then in Step B, use `active_tiers` in place of `active_tier_map`:

```python
for tier_key in (1, 2, 3):
    if tier_key in active_tiers:
        tier_best[tier_key] = None
        continue
    # ... existing candidate selection ...
```

Same in Step C (empty-tier detection), SWAP logic reads
`alloc["volume_tier"]` directly from the bot's own row, not from a
shared map, so the SWAP guard is unaffected.

### Fix B — Global slot cap

Add a safety net: regardless of tier logic, if the number of active
TF bots is already at `tf_max_coins`, **no new ALLOCATE** is issued.
This is the belt-and-suspenders guard that would have prevented the
10:56:48 incident even if Bug A still existed:

```python
# 45d: global slot cap. With 3 tiers × 1 slot each, tf_max_coins must
# act as an upper bound regardless of what the per-tier logic decides.
# Belt-and-suspenders against any future bug that lets active_count
# drift above max_grids.
max_total = int(config.get("tf_max_coins") or 3)
if active_count_global >= max_total:
    # Emit a SKIP for every tier that still has a tier_best candidate,
    # so the decision trail shows why we didn't allocate.
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
```

Place this guard at the start of Step D (right before the ALLOCATE
emission loop). If the guard fires, all subsequent per-tier
allocations are skipped and the function returns.

### Fix C — Tier-weighted resize

Replace the equal-split logic in `resize_active_allocations` with a
tier-aware split. Legacy bots (`volume_tier IS NULL`) fall back to
the current equal-split so nothing breaks during the transition.

Current code:

```python
target_alloc = tf_total_capital / max_coins
target_cpt = min(cpt_cap, max(6.0, round(target_alloc / lots_per_coin, 2)))
```

Replace with per-tier computation inside the loop:

```python
# 45d: read tier weights + per-tier lots from trend_config
t1_weight = float(config.get("tf_tier1_weight", 40))
t2_weight = float(config.get("tf_tier2_weight", 35))
t3_weight = float(config.get("tf_tier3_weight", 25))
weight_sum = t1_weight + t2_weight + t3_weight
if weight_sum <= 0:
    weight_sum = 100
tier_weight = {
    1: t1_weight / weight_sum,
    2: t2_weight / weight_sum,
    3: t3_weight / weight_sum,
}
tier_lots = {
    1: int(config.get("tf_tier1_lots", 4)),
    2: int(config.get("tf_tier2_lots", 3)),
    3: int(config.get("tf_tier3_lots", 2)),
}

# Legacy fallback budget (used for pre-45c allocations with NULL tier).
# Same formula as the pre-45d equal-split so behavior is preserved.
legacy_lots = int(config.get("tf_lots_per_coin", 4))
legacy_target_alloc = tf_total_capital / max_coins
legacy_target_cpt = min(cpt_cap, max(6.0, round(legacy_target_alloc / legacy_lots, 2)))
```

Then inside the per-bot loop:

```python
for alloc in tf_active:
    symbol = alloc["symbol"]
    if symbol in MANUAL_WHITELIST:
        continue

    # 45d: tier-weighted target. Legacy rows (volume_tier IS NULL) fall
    # back to equal-split so nothing breaks during transition.
    stored_tier = alloc.get("volume_tier")
    if stored_tier is not None:
        t = int(stored_tier)
        target_alloc = tf_total_capital * tier_weight.get(t, 1.0 / max_coins)
        lots = tier_lots.get(t, legacy_lots)
        target_cpt = min(cpt_cap, max(6.0, round(target_alloc / lots, 2)))
    else:
        target_alloc = legacy_target_alloc
        target_cpt = legacy_target_cpt

    current_alloc = float(alloc.get("capital_allocation") or 0)
    delta = target_alloc - current_alloc

    if abs(delta) < threshold:
        continue

    # ... rest of the existing update logic ...
```

The existing `threshold` (default $10) keeps the resize idempotent:
small deltas (e.g. SPK $24.94 → $29.93 = Δ$4.99) are skipped.

**Important:** the resize does NOT force-sell anything. It only
updates `capital_allocation` and `capital_per_trade` in `bot_config`.
A bot whose new allocation is below its current `invested` simply
stops buying (cash_available goes negative) until its grid sells
something naturally. No liquidation, no artificial trades.

---

## Why no DB migration or dashboard change

Both fixes are pure code — they use existing columns and existing
config fields (`tf_tier{1,2,3}_weight`, `tf_tier{1,2,3}_lots`, all
introduced in 45c). The dashboard already surfaces all relevant
controls. No new user-facing surface.

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/allocator.py` | MODIFY | Replace `active_tier_map` with `active_tiers` set + add `active_count_global`; add global slot-cap guard at start of Step D; rewrite `resize_active_allocations` to use per-tier weights/lots with legacy fallback |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no changes
- `bot/grid_runner.py` — no changes
- `bot/trend_follower/trend_follower.py` — no changes (the resize is
  invoked by name; its signature stays identical)
- `bot/trend_follower/scanner.py` — no changes
- `web/tf.html` / `web2/tf.html` — no new fields
- DB schema — no migration
- Manual bots (BTC/SOL/BONK) — resize already excludes them via
  MANUAL_WHITELIST
- `apply_allocations` — untouched (already reads `tier_lots` from
  snapshot per 45c)

---

## Test checklist

### Fix A — tier-map collision

- [ ] With 3 legacy bots (`volume_tier IS NULL`) whose fallback volumes
      place 2 of them in the same tier, `active_tiers` contains both
      unique tiers (no silent loss). Log should show `len(active_tiers)
      = 2` with 3 bots counted.
- [ ] After fallback tagging, the code treats the "double-occupied"
      tier as filled (no new ALLOCATE for that tier) and also treats
      the missing tier as filled (because the global cap guard stops
      the allocation first).

### Fix B — global slot cap

- [ ] 3 active TF bots (any tier combination) + a BULLISH candidate
      for an empty tier → `global slot cap reached` SKIP decision,
      no ALLOCATE emitted.
- [ ] 2 active TF bots + 1 empty tier with BULLISH candidate →
      ALLOCATE proceeds normally.
- [ ] 3 active TF bots where one is flagged `pending_liquidation`
      → currently counts as active. That's acceptable: the
      liquidation is about to free the slot; the next scan
      (post-liquidation) will allocate.

### Fix C — tier-weighted resize

- [ ] Active TF with `volume_tier=1`, current $25, weight 40 on $74.83
      budget → target $29.93, delta $4.93 < $10 threshold → SKIP.
- [ ] Active TF with `volume_tier=3`, current $34, weight 25 on $74.83
      → target $18.71, delta $-15.29 → UPDATE to $18.71, cpt $9.36.
- [ ] Active TF with `volume_tier=2`, current $14, weight 35 on $74.83
      → target $26.19, delta $+12.19 → UPDATE.
- [ ] Legacy active TF with `volume_tier IS NULL` → uses equal-split
      fallback, same behavior as pre-45d.
- [ ] Weights that don't sum to 100 are normalized via `weight_sum`.

### End-to-end with current live state (post-HUMA close)

Current state: RUNE ($34, NULL), SPK ($24.94, NULL), STRK ($13.71,
volume_tier=2), HUMA deactivated. Budget $74.83.

Expected at next scan with 45d live:
- Bug A irrelevant now (HUMA out, tier collision gone)
- Global cap: 3 active == tf_max_coins=3 → any attempted ALLOCATE SKIPs
- Resize:
  - RUNE legacy (NULL) → equal-split target $24.94, delta $-9.47 < $10 → SKIP
  - SPK legacy (NULL) → equal-split target $24.94, delta $0 → SKIP
  - STRK tier=2 → weighted target $26.19, delta $+12.48 ≥ $10 → UPDATE
    STRK to $26.19 (cpt $8.73)

Note: RUNE and SPK will only get tier-weighted resize once they get
re-allocated (next BEARISH → DEALLOCATE → next scan ALLOCATE writes
volume_tier). This is expected behavior; the legacy fallback is a
bridge, not a permanent state.

### Regression

- [ ] ALLOCATE loop still emits ALLOCATE decisions for empty tiers
      with valid BULLISH candidates when active_count < tf_max_coins
- [ ] SWAP logic is unchanged (reads `alloc['volume_tier']` per-bot,
      not from `active_tiers` set)
- [ ] `resize_active_allocations` return shape unchanged (same list
      of dicts with same keys) — the trend_follower.py caller is not
      modified
- [ ] Manual bots untouched (BTC/SOL/BONK) — resize skips them via
      MANUAL_WHITELIST as before

---

## Scope rules

- **DO NOT** change stop-loss / cooldown / greed decay / sell_pct
  salvage logic (features 45a / 45b remain independent)
- **DO NOT** touch `decide_allocations` beyond the map-and-cap fixes
  above (tier logic, redistribution, SWAP, filter checks stay as-is)
- **DO NOT** redistribute orphan budget differently (the 45c upward-
  only rule is correct)
- **DO NOT** add new config fields — every lever needed is already
  in trend_config from 45c
- **DO NOT** force-resize legacy bots: the `abs(delta) < threshold`
  gate must stay; large swings only
- **DO NOT** liquidate or force-sell anything — resize is a DB update
  only
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
fix(tf): tier-map collision + tier-weighted resize (45d)

Two correctness fixes on top of 45c:

1. active_tier_map silently overwrote when two legacy bots fell in
   the same tier via fallback tagging, causing the code to see a
   free tier and ALLOCATE a 4th TF bot (violating tf_max_coins=3).
   Post-mortem from the 2026-04-23 10:56:48 scan where RUNE+HUMA
   both tagged as T3, HUMA overwrote RUNE, code saw T2 empty and
   allocated STRK as a 4th bot.

   Replaced dict[int,str] with a set[int] so collisions are
   visible. Added a global slot-cap guard at the start of the
   ALLOCATE loop: if active_count >= tf_max_coins, every tier
   that would have been allocated emits SKIP instead.

2. resize_active_allocations used equal-split (tf_total_capital /
   tf_max_coins), undoing the 40/35/25 tier weights the ALLOCATE
   loop had written. Rewrote it to apply per-tier weights + lots
   from trend_config. Legacy rows (volume_tier IS NULL) keep
   equal-split as a safe fallback until they get re-allocated.

No DB migration, no config changes, no dashboard changes. Pure
code fixes in allocator.py.
```
