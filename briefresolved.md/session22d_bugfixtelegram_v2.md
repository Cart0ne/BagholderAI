# BagHolderAI — Intern Brief: Session 22b (Afternoon)
## Cosmetic fixes + smart last-lot logic + admin dashboard

**Priority:** Medium — bots are running, these are improvements  
**Date:** 2026-04-06 (afternoon)

---

## Fix 1 — Race condition on daily Telegram reports

**Problem:** Two bots (running on separate terminals) both check at ~21:00 if the daily report exists. Both find NULL (neither has written yet), both send the report → duplicate messages on Telegram.

**Evidence:** April 5, both reports timestamped 20:07:19 from different terminals.

**Fix:** Use `INSERT ... ON CONFLICT DO NOTHING` with a UNIQUE constraint on `(date)` in the daily report/snapshot table. The first bot to insert wins. The second bot's insert silently fails → it skips sending.

If no dedicated report table exists, add a unique constraint on whichever table/column is used for the "has report been sent today" check. The key is: **the check and the write must be atomic** — no window between SELECT and INSERT.

---

## Fix 2 — Trade P&L % shows 0.00% in Telegram

**Problem:** Telegram sell messages show `Trade P&L: +$0.6885 (+0.00%)` — the absolute PnL is correct but the percentage is always 0.00%.

**Fix:** Find where the P&L percentage is calculated in the Telegram message formatting. The calculation should be: `realized_pnl / cost_basis * 100`.

---

## Fix 3 — Clarify "Reserve" label in Telegram messages

**Problem:** Telegram sell messages say `🏦 Reserve: +$0.2065 (→ total $0.45)`. The "total" is per-coin but this isn't clear from the message.

**Fix:** Change label to include the coin symbol. Example:
```
🏦 BONK Reserve: +$0.2065 (→ total $0.45)
```

---

## Fix 4 — Spam SELL SKIPPED notifications

**Problem:** Same pattern as the BUY SKIPPED spam fixed in Session 21. When holdings drop below what a sell level requires, the bot sends a "SELL SKIPPED" notification every cycle (every 20s for BONK).

**Fix:** Apply same deduplication pattern used for BUY SKIPPED — once a SELL SKIPPED has been sent for a given state, don't send again until something changes. The one-time "ho venduto tutto" / "non posso più comprare" messages stay as-is.

---

## Fix 5 — Smart last-lot logic (BUY and SELL)

**This is the most important fix in this brief.**

### Current behavior (broken)
- **Last sell:** Bot tries to sell exact lot size. If holdings are less than lot size → SELL SKIPPED → bot stuck with unsellable residual holdings forever.
- **Last buy:** Bot tries to buy with `capital_per_trade`. If cash remaining < `capital_per_trade` → BUY SKIPPED → leftover cash sits idle forever.

### Desired behavior

#### SELL side
When the bot evaluates a sell and the remaining holdings after this sell would be **less than one lot size**:
→ **Sell ALL remaining holdings in a single trade** (not just the lot amount).

After selling everything (holdings = 0):
1. Stop evaluating further sell levels (nothing left to sell — no notifications)
2. **Reset the buy reference price** to the price of this last sell
3. Bot enters buy mode: next buy triggers when price drops `buy_pct`% below that reference

#### BUY side
When the bot evaluates a buy and the remaining cash after this buy would be **less than `capital_per_trade`**:
→ **Buy with ALL remaining cash in a single trade** (e.g., $9.14 instead of $6.00 + $3.14 stranded).

After spending all cash (available = 0):
1. Stop evaluating further buy levels (no cash left — no notifications)
2. Bot enters sell mode as normal (avg_buy is updated with this last buy included)

### Key detail
The threshold for "last lot" detection: `remaining_after_trade < capital_per_trade` (buy side) or `remaining_after_trade < one_lot_size` (sell side). One-time "capital exhausted" / "sold everything" notifications remain.

---

## Fix 6 — Admin dashboard: broken data for fully-closed positions

**File:** `web/admin.html`

### Problem
When a coin's position is fully closed (all sold, holdings = 0), the admin dashboard shows confusing data:

**BONK (fully sold):**
- Invested: **$-3.59** (should be $0 or show "Position closed")
- Grid capacity: **-2 / 25 filled** (sells > buys = negative, makes no sense)
- Capital usage: **-2%** (negative percentage)

**BTC (fully sold):**
- Invested: **$-1.87**
- Grid capacity: **-2 / 8 filled**

**SOL (open position) shows correctly.**

### Root cause
The dashboard calculates:
- "Invested" = total_bought - total_sold → goes negative when fully sold
- "Grid capacity filled" = buys - sells → goes negative when sells > buys

These formulas were built for the fixed grid where sells never exceed buys. With percentage grid selling everything, they break.

### Fix
When a coin has **holdings = 0** (fully closed position), the dashboard should show:

- **Invested:** `$0.00` (nothing currently deployed)
- **Grid capacity:** `0 / N filled` or a label like `Position closed — awaiting re-entry`
- **Capital usage bar:** 0% (empty)
- **Cash:** should reflect the allocated capital + realized gains ready for re-deployment

The "Realized" field already shows correctly (+$3.46 for BONK, +$1.69 for BTC) — keep that as-is.

**How to detect:** if `total_bought_amount - total_sold_amount <= 0` for a symbol (i.e., net holdings ≈ 0), treat it as a closed position.

---

## Fix 7 — Admin dashboard: add auto-refresh

**File:** `web/admin.html`

### Problem
The admin dashboard only refreshes on manual button click. Since Max monitors it while bots are running, it should update automatically.

### Fix
Add a `setInterval` that calls `loadAll()` every **30 seconds**. Show a countdown or last-refresh timestamp so it's clear the page is live.

Example:
```javascript
// After initial loadAll()
setInterval(() => {
  loadAll();
}, 30000); // 30 seconds
```

Update the refresh bar to show:
```
Last refresh: 13:21:30 (auto-refresh every 30s)  [↻ Refresh]
```

The manual refresh button should remain for immediate refresh.

---

## Files involved

| File | Fixes |
|------|-------|
| `bot/grid_runner.py` or `bot/grid.py` | Fix 4 (sell skip dedup), Fix 5 (last-lot logic) |
| `bot/grid_bot.py` | Fix 5 (last-lot logic + reference reset) |
| `bot/telegram_notifier.py` | Fix 2 (P&L %), Fix 3 (Reserve label) |
| `bot/db/client.py` + `bot/grid_runner.py` | Fix 1 (race condition) |
| `web/admin.html` | Fix 6 (closed position display), Fix 7 (auto-refresh) |

---

## Testing checklist

- [ ] Fix 1: Start two bots, wait for report time → only one report sent
- [ ] Fix 2: Trigger a sell → Telegram shows correct P&L percentage
- [ ] Fix 3: Trigger a sell with skim → Telegram shows coin name in Reserve label
- [ ] Fix 4: Let holdings go below lot size → only one SELL SKIPPED notification
- [ ] Fix 5 SELL: With small remaining holdings → bot sells ALL, then resets buy reference
- [ ] Fix 5 BUY: With cash < 2x capital_per_trade → bot buys with ALL remaining cash
- [ ] Fix 6: Open admin with a fully-closed coin → shows $0 invested, not negative
- [ ] Fix 7: Open admin, wait 30s → data refreshes automatically

---

## Out of scope

- Changing grid parameters or capital allocation
- Public homepage changes (skim % of invested was done separately)
- Any structural changes beyond what's described above
