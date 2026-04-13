# BagHolderAI — Intern Brief: Session 22
## CRITICAL BUG FIX — Position reconstruction from DB at boot

**Priority:** URGENT — bot has missed 30+ hours of sell opportunities  
**Date:** 2026-04-06

---

## The Problem

The grid runner holds positions (holdings, avg_buy_price) **in memory only**. When the bot restarts — or when it switched from fixed to percentage grid mode — this state resets to zero. The bot then thinks it owns nothing and never triggers sells.

**Evidence from live logs (today, all three bots):**
```
Holdings:     0.000000 SOL
Avg buy:      $0.00000000
active_sells: 0
```

**But the database shows open positions:**
- SOL: 0.72 units, avg cost ~$79.81
- BTC: 0.00057 units, avg cost ~$65,838
- BONK: 25.7M tokens, avg cost ~$0.000005704

All three coins went above sell thresholds overnight. Zero sells executed.

---

## The Fix

**File:** `bot/grid_runner.py`

At bot startup (before the main trading loop begins), the grid runner must reconstruct its position state from the `trades` table in Supabase.

### Logic

For each symbol, query open positions — i.e. buys that haven't been matched to a sell (FIFO). The bot already uses FIFO for sells, so the logic should be consistent.

**Query to get current open position per symbol:**

```sql
WITH buys AS (
  SELECT id, symbol, amount, cost, created_at
  FROM trades
  WHERE config_version = 'v3' AND side = 'buy'
  ORDER BY created_at ASC
),
sells AS (
  SELECT symbol, SUM(amount) as total_sold
  FROM trades
  WHERE config_version = 'v3' AND side = 'sell'
  GROUP BY symbol
)
SELECT 
  b.symbol,
  SUM(b.amount) - COALESCE(s.total_sold, 0) AS open_holdings,
  CASE 
    WHEN SUM(b.amount) - COALESCE(s.total_sold, 0) > 0 
    THEN (SUM(b.cost) - COALESCE(
      (SELECT SUM(t2.cost) FROM trades t2 
       WHERE t2.config_version = 'v3' AND t2.side = 'sell' AND t2.symbol = b.symbol), 0
    )) / (SUM(b.amount) - COALESCE(s.total_sold, 0))
    ELSE 0 
  END AS avg_cost_price
FROM buys b
LEFT JOIN sells s ON b.symbol = s.symbol
GROUP BY b.symbol, s.total_sold;
```

Alternatively, if the bot already has internal functions to compute holdings/avg from DB, use those. The key is: **do NOT start the loop with holdings=0 if the DB says otherwise.**

### What to set at boot

For each symbol, before the loop starts, set:
1. **holdings** = total bought amount minus total sold amount (from `trades` where `config_version = 'v3'`)
2. **avg_buy_price** = total cost of open positions / holdings (weighted average of unsold buys, FIFO)
3. **last_buy_price** = price of the most recent `side='buy'` trade with `reason LIKE 'Pct%'` (this is the reference for the next percentage buy trigger)

### Also reconstruct for percentage grid

The percentage grid needs `last_buy_price` as reference for the next buy. Query:

```sql
SELECT price FROM trades 
WHERE config_version = 'v3' 
  AND side = 'buy' 
  AND symbol = '<SYMBOL>' 
  AND reason LIKE 'Pct%'
ORDER BY created_at DESC 
LIMIT 1;
```

If no pct buy exists yet (fresh start), the bot should do a "first buy at market" as it currently does.

---

## Important constraints

- **Filter `config_version = 'v3'` on ALL queries.** Legacy data will corrupt the state.
- **FIFO consistency.** The avg_cost calculation must match how the bot does FIFO sells. If the bot's internal sell logic computes avg differently, match that method — don't introduce a second calculation.
- **Log the reconstruction.** At boot, log something like:
  ```
  [INFO] Rebuilt state from DB: SOL/USDT holdings=0.7207, avg_buy=$79.81, last_pct_buy=$79.67
  ```
  This way we can verify it's working from the terminal.
- **Run reconstruction ONCE at startup**, not every loop cycle. The in-memory state stays authoritative during runtime — this just seeds it correctly.

---

## How to test

1. Stop the bot
2. Apply the fix
3. Restart the bot
4. Check logs — should show rebuilt holdings for all 3 symbols
5. If current price is above sell threshold (avg_cost * 1.01), a sell should trigger within the next cycle

**Current sell thresholds (price must be above):**
- BONK: $0.000005761
- SOL: $80.98 (using daily_pnl avg of $80.18)
- BTC: $67,332

---

## Files to modify

| File | Change |
|------|--------|
| `bot/grid_runner.py` | Add position reconstruction from DB at startup |

---

## Out of scope

- Changing grid parameters
- Changing capital allocation
- Any frontend/dashboard work
- Anything not directly related to this fix
