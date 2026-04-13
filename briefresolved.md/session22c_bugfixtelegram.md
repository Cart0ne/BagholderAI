# BagHolderAI — Intern Brief: Session 22b (Afternoon)
## Cosmetic fixes + smart last-lot logic

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

**Example from BONK sell:**
```
💰 Trade P&L: +$0.6885 (+0.00%)
```
Should be: `+$0.6885 (+2.29%)` (0.6885 / 30.03 cost basis ≈ 2.29%)

**Fix:** Find where the P&L percentage is calculated in the Telegram message formatting. It's likely getting 0 or None from somewhere after the `trade_pnl_pct` parameter was removed/fixed earlier today. The calculation should be: `realized_pnl / cost_basis * 100`.

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

**Additional issue:** The skip fires even when Need == Have, because fees make the net amount insufficient. But this is now handled by Fix 5 below, so the skip should rarely happen. 

**Fix:** Apply same deduplication pattern used for BUY SKIPPED — once a SELL SKIPPED has been sent for a given state, don't send again until something changes (e.g., a new trade happens). The one-time "ho venduto tutto" / "non posso più comprare" messages stay as-is.

---

## Fix 5 — Smart last-lot logic (BUY and SELL)

This is a behavior change, not just cosmetic. **This is the most important fix in this brief.**

### Current behavior (broken)
- **Last sell:** Bot tries to sell exact lot size. If holdings are less than lot size (or equal but fees make it fail) → SELL SKIPPED → bot stuck with unsellable residual holdings forever.
- **Last buy:** Bot tries to buy with `capital_per_trade`. If cash remaining < `capital_per_trade` → BUY SKIPPED → leftover cash sits idle forever.

### Desired behavior

#### SELL side
When the bot evaluates a sell and the remaining holdings after this sell would be **less than one lot size** (or there isn't enough for the current lot):
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

### Key implementation details
- The threshold for "last lot" detection should be: `remaining_after_trade < one_lot_size` (sell) or `remaining_after_trade < capital_per_trade` (buy)
- The one-time "capital exhausted" / "sold everything" Telegram notifications remain
- The repeated SELL SKIPPED / BUY SKIPPED spam does NOT happen (covered by Fix 4, but this fix also prevents the root cause)
- The buy reference reset after selling everything is critical — without it the bot won't know when to buy again

---

## Files likely involved

| File | Fixes |
|------|-------|
| `bot/grid_runner.py` or `bot/grid.py` | Fix 4 (sell skip dedup), Fix 5 (last-lot logic + reference reset) |
| `bot/telegram.py` or message formatting | Fix 2 (P&L %), Fix 3 (Reserve label) |
| `bot/daily_report.py` or equivalent | Fix 1 (race condition) |

---

## Testing checklist

- [ ] Fix 1: Start two bots, wait for report time → only one report sent
- [ ] Fix 2: Trigger a sell → Telegram shows correct P&L percentage
- [ ] Fix 3: Trigger a sell with skim → Telegram shows coin name in Reserve label
- [ ] Fix 4: Let holdings go below lot size → only one SELL SKIPPED notification (or none if Fix 5 sold everything)
- [ ] Fix 5 SELL: With small remaining holdings → bot sells ALL, then resets buy reference
- [ ] Fix 5 BUY: With cash < 2x capital_per_trade → bot buys with ALL remaining cash in one trade

---

## Out of scope

- Changing grid parameters or capital allocation
- Dashboard/frontend work
- Any structural changes beyond what's described above
