# INTERN BRIEF 42a — Multi-Lot Entry + Greed Decay

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 42 — April 20, 2026
**Priority:** HIGH — Step 1 of internal roadmap

---

## Context

Data analysis of all TF sells (102 trades) shows a clear pattern:

| Time bucket | Trades | Total PnL | Avg PnL | Win Rate |
|-------------|--------|-----------|---------|----------|
| 0–3h        | 25     | +$13.68   | +$0.55  | 96%      |
| 3–8h        | 33     | +$1.06    | +$0.03  | 70%      |
| 8–20h       | 25     | +$8.02    | +$0.32  | 76%      |
| 20h+        | 19     | −$22.49   | −$1.18  | 42%      |

**Two problems this brief solves:**

1. **Slow entry:** TF allocates a bullish coin but the grid bot waits for dips to buy. If the coin keeps rising, we miss the momentum window entirely.
2. **Late exit:** Positions held 20h+ bleed all the profit earned in the first hours. The static `profit_target_pct` doesn't account for decay of momentum over time.

---

## Feature A — Multi-Lot Entry

### What changes

When the TF scanner performs an ALLOCATE, the grid bot should immediately buy multiple lots at market price on its first cycle, instead of waiting for the price to dip to grid levels.

### Schema changes

**`trend_config`** — add column:

```sql
ALTER TABLE trend_config ADD COLUMN tf_initial_lots integer NOT NULL DEFAULT 3;
```

**`bot_config`** — add column:

```sql
ALTER TABLE bot_config ADD COLUMN initial_lots integer NOT NULL DEFAULT 0;
```

### Logic

**TF allocator** (`trend_follower.py` or wherever ALLOCATE writes to `bot_config`):

When inserting a new `bot_config` row for a TF coin, set:
```
initial_lots = trend_config.tf_initial_lots   (currently 3)
```

**Grid bot** (`grid_bot.py` or `grid_runner.py`):

At the **start of each cycle**, before normal grid logic:

```python
if config['managed_by'] == 'trend_follower' and config.get('initial_lots', 0) > 0:
    lots_to_buy = config['initial_lots']
    for i in range(lots_to_buy):
        # Market buy at current price, amount = capital_per_trade
        execute_market_buy(symbol, capital_per_trade)
        log_trade(...)  # normal trade logging, so sell queue picks them up
    # Reset the flag so this only happens once
    UPDATE bot_config SET initial_lots = 0 WHERE symbol = ?
```

- Buy type: **market order** (not limit), one order per lot
- Amount per lot: `capital_per_trade` (same as normal grid buys, ~$12.50)
- After buying, set `initial_lots = 0` on the `bot_config` row
- Normal grid logic then takes over for subsequent buys/sells
- **Manual bots are unaffected** — their `initial_lots` is always 0

### Admin UI

Add `tf_initial_lots` to the TF Safety Parameters section in `/tf` page. Simple integer input, label "Initial lots on entry", min 1, max 4.

### Telegram alert

When multi-lot entry fires:
```
🚀 [SYMBOL] Multi-lot entry: bought [N] lots at market ($[COST] total)
```

---

## Feature B — Greed Decay (Time-Based Take Profit)

### What changes

Instead of a static `profit_target_pct`, the grid bot uses a **time-decaying take-profit** based on how long ago the TF allocated the coin. The longer we hold, the lower the TP threshold — making the bot increasingly eager to exit.

### Schema changes

**`trend_config`** — add column:

```sql
ALTER TABLE trend_config ADD COLUMN greed_decay_tiers jsonb NOT NULL DEFAULT '[
  {"minutes": 15, "tp_pct": 12},
  {"minutes": 60, "tp_pct": 8},
  {"minutes": 180, "tp_pct": 5},
  {"minutes": 480, "tp_pct": 3},
  {"minutes": 999999, "tp_pct": 1.5}
]'::jsonb;
```

**Format:** Array of objects sorted by `minutes` ascending. Each object means: "from this many minutes after allocation, use this `tp_pct`." The last entry is the fallback (effectively "forever").

**`bot_config`** — add column:

```sql
ALTER TABLE bot_config ADD COLUMN allocated_at timestamptz;
```

### Logic

**TF allocator:**

When inserting a new `bot_config` row for a TF coin, set:
```
allocated_at = NOW()
```

**Grid bot — sell evaluation:**

Before checking if a lot should be sold, determine the effective TP:

```python
def get_effective_tp(allocated_at, greed_decay_tiers):
    """Return the current tp_pct based on time since allocation."""
    if allocated_at is None:
        # Manual bot or missing timestamp — use static profit_target_pct
        return config['profit_target_pct']

    age_minutes = (datetime.utcnow() - allocated_at).total_seconds() / 60
    effective_tp = config['profit_target_pct']  # fallback

    for tier in sorted(greed_decay_tiers, key=lambda t: t['minutes']):
        if age_minutes >= tier['minutes']:
            effective_tp = tier['tp_pct']
        else:
            break

    return effective_tp
```

Then use `effective_tp` instead of `config['profit_target_pct']` when deciding whether to sell a lot.

**Important:**
- `allocated_at` is coin-level (one timestamp per coin), NOT per lot
- The timer starts from the TF ALLOCATE moment, shared by all lots of that coin
- **Manual bots** have `allocated_at = NULL` → always use static `profit_target_pct` → no change in behavior
- When the admin edits `greed_decay_tiers`, it takes effect on the **next cycle** for ALL active TF bots — no snapshot, no per-trade storage
- When a TF coin is DEALLOCATED and later re-ALLOCATED (swap), `allocated_at` resets to the new allocation time

### Admin UI

Add a "Greed Decay Tiers" section to the TF Safety Parameters in `/tf` page:

```
GREED DECAY TIERS
┌──────────────┬────────────┐
│ After (min)  │ TP %       │
├──────────────┼────────────┤
│ 15           │ 12         │
│ 60           │ 8          │
│ 180          │ 5          │
│ 480          │ 3          │
│ 999999       │ 1.5        │
└──────────────┴────────────┘
[+ Add tier]              [Save]
```

- Each row: two inputs (minutes, tp_pct)
- "Add tier" button adds a new empty row
- "X" button on each row to remove it (minimum 1 tier)
- "Save" button writes the JSON to `trend_config.greed_decay_tiers`
- Log change to `config_changes_log` as `parameter: 'greed_decay_tiers'`

### Telegram alerts

When a sell is triggered by greed decay, include the tier info:
```
💰 [SYMBOL] SELL — +$[PNL] ([PCT]%) — Greed tier: [AGE]min → TP [TIER_PCT]%
```

---

## Migration summary

Run these in order:

```sql
-- 1. Multi-lot entry columns
ALTER TABLE trend_config ADD COLUMN tf_initial_lots integer NOT NULL DEFAULT 3;
ALTER TABLE bot_config ADD COLUMN initial_lots integer NOT NULL DEFAULT 0;

-- 2. Greed decay columns
ALTER TABLE trend_config ADD COLUMN greed_decay_tiers jsonb NOT NULL DEFAULT '[
  {"minutes": 15, "tp_pct": 12},
  {"minutes": 60, "tp_pct": 8},
  {"minutes": 180, "tp_pct": 5},
  {"minutes": 480, "tp_pct": 3},
  {"minutes": 999999, "tp_pct": 1.5}
]'::jsonb;
ALTER TABLE bot_config ADD COLUMN allocated_at timestamptz;
```

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `trend_follower.py` (or allocator module) | MODIFY | Set `initial_lots` and `allocated_at` on ALLOCATE |
| `grid_bot.py` / `grid_runner.py` | MODIFY | Multi-lot market buy on first cycle + greed decay TP logic |
| `config/supabase_config.py` | MODIFY | Fetch `initial_lots`, `allocated_at`, `greed_decay_tiers` |
| `web/tf.html` | MODIFY | Admin UI for `tf_initial_lots` + greed decay tier editor |

---

## Test checklist

### Multi-lot entry
- [ ] TF allocates a new coin → `bot_config.initial_lots = 3`
- [ ] Grid bot first cycle: 3 market buys logged to `trades` table
- [ ] Grid bot second cycle: `initial_lots = 0`, normal grid logic
- [ ] Telegram receives multi-lot entry alert with total cost
- [ ] Manual bots (BTC/SOL/BONK): `initial_lots = 0`, behavior unchanged
- [ ] `/tf` admin shows "Initial lots on entry" field, editable

### Greed decay
- [ ] TF allocates new coin → `bot_config.allocated_at` is set
- [ ] At 0–15 min: grid bot uses 12% TP (sells only if lot is +12% or more)
- [ ] At 60+ min: TP drops to 8%
- [ ] At 180+ min: TP drops to 5%
- [ ] At 480+ min: TP drops to 3%
- [ ] At 999999+ min: TP drops to 1.5%
- [ ] Manual bots: `allocated_at` is NULL → static `profit_target_pct` used → no change
- [ ] Change tiers in admin → next cycle picks up new values for ALL TF coins
- [ ] Telegram sell alert includes greed tier info
- [ ] Coin gets DEALLOCATED then re-ALLOCATED → `allocated_at` resets

### Integration
- [ ] Multi-lot entry + greed decay work together: 3 lots bought immediately, greed timer starts from allocation
- [ ] If coin pumps +12% in first 15 min → all 3 lots sell → maximum capture
- [ ] If coin stagnates for 8h+ → lots sell at 1.5% profit or better → minimal bag-holding

---

## Scope rules

- **DO NOT** modify manual bot behavior (BTC/SOL/BONK)
- **DO NOT** change the TF scanner or rotation logic
- **DO NOT** touch `trend_decisions_log` structure
- **DO NOT** add new tables — only new columns on existing tables
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(grid-bot): multi-lot entry + greed decay take-profit
```
