# Brief 39e — TF Liquidation Accounting: PnL Fix, Skim Fix, Cycle Summary

**Priority:** HIGH — accounting correctness + operational visibility
**Dependencies:** 39a (stop-loss), 36e v2 (rotation/SWAP), 20b (skim)
**Commit as single unit** — Fix 1 + Fix 2 must ship together to avoid toxic skim on bogus PnL.

---

## Context

Supabase analysis of the session 40 trading window surfaced three related issues in the accounting path of TF-managed bots at deallocation time. All three touch the same code surface (the FORCED_LIQUIDATION flow in `grid_bot.py`) and the same mental model (the "cycle" of a TF allocation).

Problem statement:
1. The `realized_pnl` recorded for a FORCED_LIQUIDATION is wrong when multiple lots are open.
2. The FORCED_LIQUIDATION bypasses the skim routine even when `realized_pnl > 0`.
3. The CEO has no single view of "what this allocation cycle produced" at the moment of deallocation. He sees individual trade notifications that look misleading in isolation.

Concrete example from today (API3/USDT SWAP-driven deallocation at 02:46):
- 4 open lots with total cost basis $44.36
- Sold 107.76 units for $43.16
- **Actual PnL: −$1.21**
- **Recorded PnL: +$0.18** ← wrong, off by ~$1.39
- Skim inserted: nothing (bypass) — accidentally correct because the PnL should have been negative anyway. The two bugs compensate today. They will stop compensating as soon as either is fixed alone.

## Principle

CEO policy confirmed: *"If I liquidate and I'm in positive, 30% goes to skim. All the 30% of what I take home in positive goes to skim."*

Corollary: `realized_pnl` on a liquidation must be the honest cash delta between what was bought and what was sold. It must not favor one lot over the others.

Corollary: at deallocation, the CEO must be able to read the full cycle result in one Telegram message without cross-referencing five trade notifications.

---

## Fix 1: Correct `realized_pnl` on FORCED_LIQUIDATION

### Bug

When a FORCED_LIQUIDATION event fires (triggered by either BEARISH EXIT from TF, SWAP from TF, or the `pending_liquidation` flag being set), the code sells all open lots and writes a single trade row with `side='sell'` and `reason='FORCED_LIQUIDATION (...)'`. The `realized_pnl` stored on that row is computed against **one lot's buy price** (likely the last or first, but irrelevant — whichever single one it is, it's wrong). Result: the PnL reflects only one lot out of potentially many, and can show profit when the aggregate was a loss.

### Fix

In the FORCED_LIQUIDATION code path in `bot/strategies/grid_bot.py`, compute `realized_pnl` as:

```
realized_pnl = revenue                                   # sell_amount × sell_price
             − Σ(lot.amount × lot.buy_price)            # sum over ALL open lots being liquidated
             − sell_fee                                  # the liquidation's own fee
             − Σ(lot.buy_fee)                            # sum of buy fees of the open lots
```

The existing normal-sell PnL routine already does this correctly for per-lot sells (verified: each STOP-LOSS lot sells with correct per-lot PnL). The FORCED_LIQUIDATION routine does not because it consolidates all lots into one trade record without summing their cost bases.

Two options for the implementation:

**Option A (preferred):** keep the single consolidated trade row, but compute PnL as the sum above before writing. Preserves current DB shape. Cleanest.

**Option B:** split the FORCED_LIQUIDATION into N separate sell trade records (one per lot, same timestamp, same reason string). Mirrors the STOP-LOSS pattern exactly. More uniform but changes trade-count semantics in the UI.

CC decides — I'd go with A unless there's a blocker.

### Files to touch

- `bot/strategies/grid_bot.py` — `_execute_forced_liquidation` (or whatever the method is named internally). Replace the single-lot PnL calculation with the multi-lot sum.

### Verification

New test helper or manual verification with a paper-mode liquidation: set up 3 open lots at known prices, trigger liquidation, assert `trades.realized_pnl` matches `revenue − Σ(cost_bases) − fees`.

---

## Fix 2: Route skim on FORCED_LIQUIDATION when PnL is positive

### Bug

The FORCED_LIQUIDATION flow does not call the skim routine, regardless of the sign of `realized_pnl`. Evidence:
- API3 today: 5 profitable sells, only 4 in `reserve_ledger`. The 5th (the forced liquidation with `reason='FORCED_LIQUIDATION (BEARISH EXIT)'`) was skipped.
- PHB today: 5 profitable sells — including one STOP-LOSS that closed accidentally positive (+$0.15) — **all 5** are in `reserve_ledger`. So STOP-LOSS with positive PnL correctly skims. Only FORCED_LIQUIDATION doesn't.

### Fix

After Fix 1 produces a correct `realized_pnl` on the FORCED_LIQUIDATION sell, invoke the same skim routine used by normal sells:

```python
if realized_pnl > 0 and self.skim_pct > 0:
    skim_amount = realized_pnl * (self.skim_pct / 100)
    self.reserve_ledger.add(symbol=self.symbol, amount=skim_amount, trade_id=sell.id)
    # include skim line in Telegram message
```

### Ordering dependency

**This fix MUST deploy together with Fix 1, in the same commit.** If Fix 2 deploys alone (without Fix 1), the skim routine will be fed the bogus pre-fix PnL and write incorrect amounts to `reserve_ledger`. Example with today's API3: skim would have been 30% × $0.18 = $0.054 on what was actually a −$1.21 trade. Accumulated drift over many liquidations.

### Files to touch

- `bot/strategies/grid_bot.py` — same method as Fix 1.

### Verification

After deploy, at the next FORCED_LIQUIDATION event with positive PnL:
1. Telegram message includes a `💰 Reserve: +$X → total $Y` line.
2. A new row appears in `reserve_ledger` with `trade_id` matching the liquidation trade.
3. Amount equals `realized_pnl × 0.30` (for TF bots where skim_pct=30).
4. If liquidation PnL is negative (e.g., a true stop-loss on underwater position), no skim row and no reserve line in Telegram.

---

## Fix 3: Cycle Summary on DEALLOCATE (Telegram)

### Goal

Give the CEO a single Telegram message at the moment of DEALLOCATE that answers: *"how did this allocation cycle go, end to end?"*

### Definition of "cycle"

For a given symbol, a cycle is the time window between its most recent `ALLOCATE` event and the `DEALLOCATE` that is just happening now, as recorded in `trend_decisions_log`.

- Cycle start = `scan_timestamp` of the last row where `symbol = X` and `action_taken = 'ALLOCATE'`
- Cycle end = `scan_timestamp` of the current `DEALLOCATE` event (this message)
- Cycle trades = all rows in `trades` where `symbol = X` and `created_at` in [start, end]
- Cycle skim = all rows in `reserve_ledger` where `trade_id` in (cycle trades' IDs)

For coins that are allocated, deallocated, and reallocated later, each cycle is treated independently. Only the most recent cycle is summarized.

### Message format (target)

```
🔴 API3/USDT DEALLOCATED (SWAP — replaced by PHB/USDT)
Cycle: 14:47 → 02:46 (12h 0m)
━━━━━━━━━━━━━━━━━━━━
Trades: 8 buys · 5 sells
Realized P&L: +$2.01
  ├─ Grid profits:      +$3.22  (4 sells)
  └─ Exit liquidation:  −$1.21  (1 liquidation)
Skimmed to reserve:    +$0.97  (30% of grid profits)
Net to trading pool:   +$1.04
━━━━━━━━━━━━━━━━━━━━
Allocated: $42.04 → Returned: $44.05 (+4.8%)
```

Layout notes:
- First line: the existing DEALLOCATE header. Use the real reason (SWAP / BEARISH / STOP-LOSS-driven if a future variant adds it). No more hardcoded "BEARISH EXIT" label on what's actually a SWAP — read `action_taken` and `reason` from `trend_decisions_log`.
- "Trades" line: counts only; details are in the individual trade notifications already sent.
- "Realized P&L" main line: sum of `realized_pnl` for all cycle sells (now correct post-Fix 1).
- Subtotals split grid vs liquidation for clarity — but only if BOTH are present. If the cycle closed with only grid sells (e.g., allocation still open, not this case), skip the split. If only a liquidation (e.g., very short cycle), skip the split too.
- "Skimmed to reserve": sum of `reserve_ledger.amount` for cycle trades.
- "Net to trading pool": realized P&L − skim. What actually flowed into `tf_total_capital` / cash.
- "Allocated → Returned": initial allocation of the cycle (from `bot_config.capital_allocation` at ALLOCATE time — may require snapshot) vs. what came back (allocation + realized P&L). Percentage shown on the initial allocation.

Edge case: the "Allocated" snapshot. Option A: read `capital_allocation` at DEALLOCATE time (approximate if compounding resized it mid-cycle — but acceptable). Option B: log `capital_allocation` at ALLOCATE time in a dedicated column on `trend_decisions_log` or a new `tf_cycles` table. Option A is fine for now — the approximation is small and the message value is high. Don't build tables unless needed.

### Where to trigger

The DEALLOCATE message already fires somewhere in the TF scan flow (either in the scanner itself or in the grid_bot when it processes `pending_liquidation`). Attach the summary to whichever side already sends the DEALLOCATE message — don't introduce a second notification path.

### Files to touch

- The TF scanner or grid_bot code that currently sends DEALLOCATE notifications.
- Likely a new helper function `build_cycle_summary(symbol, cycle_start, cycle_end) -> dict` that queries trades + reserve_ledger and formats the message.
- Telegram notification module for the new message format.

### Verification

At the next real DEALLOCATE event:
1. Message contains all the labeled fields above.
2. "Cycle" window starts at the last ALLOCATE, ends at this DEALLOCATE.
3. Trade counts match `SELECT COUNT(*) FROM trades WHERE symbol=X AND created_at BETWEEN ... GROUP BY side`.
4. Realized P&L matches `SELECT SUM(realized_pnl) ... side='sell'` on the cycle window (and is honest post-Fix 1).
5. Skimmed amount matches `SELECT SUM(amount) FROM reserve_ledger WHERE trade_id IN (cycle sell IDs)`.
6. Aritmetica banale: `Allocated + Realized ≈ Returned`.

---

## Out of scope

- Dashboard "Recently Closed Positions" section on `tf.html`: mentioned in conversation as a later enhancement. Do not build in this brief. Ship the Telegram summary first, see if it's enough.
- Backfilling cycle summaries for historical deallocations: nice-to-have, not now.
- Renaming `FORCED_LIQUIDATION (BEARISH EXIT)` to a more accurate label string (`SWAP EXIT` / `BEARISH EXIT` depending on the real trigger): touch only if trivial in the context of Fix 3 header. Otherwise parked as a polish item.
- Tracking allocation capital snapshots in a new table (`tf_cycles`): not yet. Revisit if Option A in Fix 3 proves inaccurate.
- Skim re-run on historical FORCED_LIQUIDATION events: the skim missed is $0.054 (API3 today only). Not worth a backfill. Move on.

---

## Test pre-deploy

1. In paper mode, set up a TF bot with 3 open lots at known prices. Manually set `pending_liquidation=true`. Verify the consolidated liquidation trade records `realized_pnl = revenue − Σ(cost) − fees` (not a single-lot value).
2. Paper-mode liquidation with overall positive PnL: verify `reserve_ledger` row is created with 30% of PnL.
3. Paper-mode liquidation with overall negative PnL: verify NO `reserve_ledger` row is created.
4. Paper-mode DEALLOCATE: verify the Telegram message contains all cycle fields and arithmetic balances.

## Test post-deploy

At the first real DEALLOCATE event on production:
1. Fetch the trade row and verify `realized_pnl` against manual calculation (sum of cost bases of previously-open lots).
2. If realized_pnl > 0, verify `reserve_ledger` has the new row.
3. Verify the Telegram DEALLOCATE message contains the full cycle summary.
4. Cross-check cycle totals via SQL on `trades` + `reserve_ledger`.

Send a screenshot to Max in Telegram. He reviews the first occurrence before we consider the brief closed.

## Rollback

```bash
git revert <commit_hash>
git push origin main
ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull && <restart orchestrator>'
```

Rollback restores pre-fix behavior. No DB migration is involved in this brief — rollback is code-only. `reserve_ledger` and `trades` rows written during the fix's active period remain; they are correct under the new policy anyway.

## Commit format

```
fix(grid-bot): correct liquidation PnL + skim + add cycle summary

- FORCED_LIQUIDATION now computes realized_pnl as the sum across all
  liquidated lots' cost bases (was: single-lot reference, producing
  ~$1.4 error on 4-lot liquidation).

- FORCED_LIQUIDATION with realized_pnl > 0 now routes 30% (skim_pct)
  to reserve_ledger. Previously bypassed. Today's skim had compensated
  for the PnL bug; now both are honest.

- DEALLOCATE Telegram notification includes a cycle summary: window,
  trade counts, grid vs liquidation P&L split, skim total, allocated
  vs returned. CEO now reads cycle outcome without cross-referencing
  individual trade messages.

Refs: brief 39e. Depends on 39a (stop-loss), 36e v2 (rotation), 20b (skim).
```

---

## Notes on priority ordering

If for any reason CC has to deploy incrementally:
1. **Fix 1 + Fix 2 together, first.** Data correctness. Non-negotiable same-commit pairing.
2. **Fix 3 after.** Feature, can ship in a second commit a day later without breaking anything.

Do not ship Fix 2 before Fix 1. Do not ship Fix 3 before Fix 1 (the summary would quote wrong numbers).
