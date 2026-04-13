# INTERN BRIEF — Session 18

**Priority: CRITICAL**
**Date: April 3, 2026**

---

## Context

We are migrating from fixed grid levels to percentage-based buy/sell logic. The `bot_config` table in Supabase already has the new columns (`buy_pct`, `sell_pct`, `grid_mode`). The bots must also start reading config from Supabase instead of local files, so parameter changes via the admin dashboard take effect without restarting.

Three tasks below. Do them in order.

---

## Task 1 — Percentage-Based Grid Logic (CRITICAL)

### Current behavior
The grid bot uses fixed price levels defined by `grid_lower`, `grid_upper`, and `grid_levels`. It buys/sells when price crosses a level.

### New behavior
When `grid_mode = 'percentage'` in `bot_config`:

**BUY logic:**
- Trigger: current price is **X% below the last buy price** for this symbol → execute buy
- X = `buy_pct` from `bot_config`
- "Last buy price" = price of the most recent BUY trade for this symbol in the `trades` table with current `config_version`
- If there are **no previous buys** (fresh start), the bot should execute the first buy immediately at current market price (this establishes the reference point)
- `capital_per_trade` defines how much to spend per buy (unchanged)

**SELL logic:**
- Trigger: current price is **Y% above the average buy price** of current holdings → execute sell
- Y = `sell_pct` from `bot_config`
- "Average buy price" = weighted average of all open buy positions for this symbol (already calculated by the bot as `avg_buy_price`)
- Sell amount: sell the quantity from the **oldest open position** (FIFO) — same as current behavior

**Guards (unchanged):**
- Cash guard: if not enough cash → skip buy, log warning, send Telegram alert
- Holdings guard: if not enough holdings → skip sell, log warning, send Telegram alert
- Anti-duplicate trigger in Supabase still applies

### Implementation notes
- Keep the old fixed-grid logic intact — it runs when `grid_mode = 'fixed'`
- The `grid_mode` field determines which logic runs
- All three coins start as `grid_mode = 'fixed'` — we will switch them to `'percentage'` manually after verifying the code works
- **Do NOT change config_version.** This is the same v3 config, just with a new grid mode.

### Current values in bot_config

| Symbol | buy_pct | sell_pct | capital_per_trade | capital_allocation |
|--------|---------|----------|-------------------|--------------------|
| BTC/USDT | 1.80 | 1.00 | 25.00 | 200 |
| SOL/USDT | 1.50 | 1.00 | 12.50 | 150 |
| BONK/USDT | 1.00 | 1.00 | 6.00 | 150 |

---

## Task 2 — Read Config from Supabase (CRITICAL)

### Current behavior
Bots read config from local Python files/dicts at startup. Changes require restart.

### New behavior
- On startup, bot reads all config from `bot_config` table in Supabase
- Every **300 seconds (5 minutes)**, bot re-reads the config from Supabase
- If any value has changed since last read, log the change: `[bagholderai.config] INFO: Config updated for BTC/USDT: buy_pct 1.80 → 2.00`
- If Supabase is unreachable during refresh, log a warning and keep using the last known config. Do NOT crash.
- The refresh interval (300s) should be a constant at the top of the config reader module, easy to change later.

### What to read from bot_config
All fields: `symbol`, `capital_allocation`, `grid_levels`, `grid_lower`, `grid_upper`, `profit_target_pct`, `reserve_floor_pct`, `capital_per_trade`, `is_active`, `buy_pct`, `sell_pct`, `grid_mode`

### Supabase connection
Use the same Supabase client already in the codebase (the one used by `TradeLogger`). REST API with anon key. The `bot_config` table already has RLS policy for anon reads.

---

## Task 3 — Fix BONK $0.00 Log Formatting (COSMETIC)

### Problem
BONK/USDT has micro-prices like $0.00000581. The log formatter uses `:.2f` which rounds to `$0.00`. This produces confusing log lines:

```
SKIP: sell at $0.00 below min profit target (need $0.00, 2.0% above avg buy)
```

### Fix
Replace the fixed `:.2f` format with a dynamic formatter that adapts to the price magnitude. Suggestion:

```python
def format_price(price):
    if price < 0.001:
        return f"${price:.8f}"
    elif price < 1:
        return f"${price:.4f}"
    else:
        return f"${price:.2f}"
```

Apply this wherever prices are formatted in log messages in `grid.py` (and any other file that formats prices for logging).

---

## Scope Rules (as always)

- No external connections beyond Supabase and Binance API (already in use)
- Do NOT launch the bot
- Do NOT modify `config_version`
- Push all changes to GitHub when done
- Stop when tasks are complete

---

## Files likely involved

- `grid.py` — main grid logic (Task 1 + Task 3)
- New file or module: `config_reader.py` or similar (Task 2)
- `runner.py` — integrate config refresh loop (Task 2)
- `bot_config` table in Supabase — already updated, read-only for the intern
