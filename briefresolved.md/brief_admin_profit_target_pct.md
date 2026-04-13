# BRIEF: Add profit_target_pct to Admin Dashboard + Parameter Labels

**Priority:** HIGH — this parameter silently blocked all BTC sells for days
**Context:** `profit_target_pct` exists in `bot_config` but is invisible in the admin dashboard. Max couldn't see or modify it. It was set to 1.0% and acted as a second gate on sells, requiring price to be above the AVERAGE buy price + 1%, on top of the per-lot `sell_pct` trigger. This blocked BTC from selling profitable lots because expensive lots dragged the average up. Fixed via direct DB update (set to 0), but needs to be visible in the dashboard.

---

## Task 1: Add `profit_target_pct` to admin dashboard

Add a new field in the PERCENTAGE GRID section of each symbol's parameter card, below SELL % and IDLE RE-ENTRY.

**Field:**
- DB column: `profit_target_pct`
- Label: **MIN PROFIT %**
- Current value for all symbols: `0`
- Editable, same style as SELL % and BUY %

---

## Task 2: Add descriptive sublabels to sell-related parameters

Each of these three parameters needs a short sublabel (smaller, muted text below the field label) explaining what it does in plain language. These sublabels help a non-technical user understand the difference.

**SELL %**
- Label: `SELL %`
- Sublabel: `Per-lot trigger: sells a lot when price rises this % above that lot's buy price`

**MIN PROFIT % (the new field)**
- Label: `MIN PROFIT %`
- Sublabel: `Safety gate: blocks ALL sells unless price is this % above the average buy price of all open lots. Set 0 to disable.`

**BUY %**
- Label: `BUY %`
- Sublabel: `Buys when price drops this % below the last buy price`

**SKIM % (PROFIT RESERVE)**
- Sublabel: `% of each sell's profit routed to reserve instead of reinvested`

---

## Implementation notes

- Sublabels should be a `<small>` or `<span>` with muted/dimmed color, placed directly under each label
- Keep them on one line if possible, wrap naturally if not
- The sublabel for MIN PROFIT % is the most important — it must be clear that 0 = disabled
- `profit_target_pct` must be saved to `bot_config` via the same `Save changes` button as the other parameters

---

## Task 3: Fix `profit_target_pct = 0` treated as "use default" (BUG)

**Priority:** HIGH — this makes the DB fix useless

When `profit_target_pct` is set to `0` in the DB, the bot still uses `1.0%`. Almost certainly caused by a Python falsy check like:

```python
# BUGGY — 0 is falsy in Python, falls through to default
profit_target_pct = config.get('profit_target_pct') or 1.0
```

**Fix:** Use explicit None check:

```python
# CORRECT — 0 means disabled, only use default if truly missing
val = config.get('profit_target_pct')
profit_target_pct = val if val is not None else 1.0
```

Search the entire codebase for any `or` fallback on `profit_target_pct` — could be in config loading, grid bot init, or the sell logic itself.

Also check that the **config refresh** (every 300s) properly propagates the updated value to the running grid bot instance. The current log shows the refresh fires but the bot keeps using the old cached threshold. The grid bot needs to recalculate its min profit target after each config refresh.

**Current workaround:** `profit_target_pct` is set to `0.01` (not `0`) in the DB to bypass the falsy bug. Once this code fix is deployed, set it back to `0`.

---

## What NOT to touch

- Other parameters — only add sublabels to the four listed above
- Current DB values — currently set to 0.01 as workaround, will be set to 0 after code fix
