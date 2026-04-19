# Brief 39f — Post-39e Cleanup: View Fix + Stop-Loss Dealloc

**Priority:** MEDIUM. Section A is accounting hygiene (view lies, no operational damage). Section B fixes a real thrash loop that bled fees on PHB today.
**Dependencies:** 39e (deployed). Builds on `_force_liquidate` + cycle summary mechanisms.
**Ship plan:** sections are independent and can deploy as two separate commits. Preferred order below.

---

## Context

Brief 39e is deployed pending Max's OK on the cycle summary rendering. CC's implementation report matches the brief. Two follow-ups surfaced during verification:

**Problem 1 — `tf_capital_summary` view reports phantom capital.**
During session 40 analysis the view returned `capital_available = $14.39`, and I used it to compute a Net Worth of $116 (+16%). The dashboard at the same moment showed Net Worth $100.85 (+0.85%). The dashboard is right; the view is lying. Root cause is almost certainly that the formula uses `bot_config.capital_allocation` (a theoretical ceiling set by the TF scanner) instead of actual cash currently held by the bots. After a stop-loss cascade closes lots, `capital_allocation` still shows ~$42 while real cost basis is ~$0.

**Problem 2 — Stop-loss doesn't trigger dealloc, causing thrash.**
CC flagged that stop-loss/take-profit notifications in mid-tick don't include the cycle summary. The underlying issue is deeper: stop-loss doesn't close the allocation cycle at all. PHB today demonstrated the cost: 6 stop-loss events in ~70 minutes on the same allocation (02:45 → ongoing), because after each cascade the bot was still `is_active=true` and bought again on the next percentage-drop trigger. TF scans lagged behind (the EMA/RSI signals were still BULLISH while the market was falling), so the bot was free to keep buying falling knives.

## Principle

- **The view must not lie.** If `tf_capital_summary` is used, its numbers must match the dashboard. If it's unused, drop it. Silent divergence is the worst failure mode.
- **Stop-loss is a safety, not a reset.** When the safety fires and empties holdings, the next action should be rotation (deploy elsewhere), not "keep trying on the same coin." Dealloc is the correct response. This also unifies notification: every TF exit goes through `_force_liquidate` → cycle summary.

---

## Section A — Fix or deprecate `tf_capital_summary`

### Investigation (first 5 minutes of the task)

Grep the repo for `tf_capital_summary`:
```bash
grep -r "tf_capital_summary" --include="*.py" --include="*.html" --include="*.js" --include="*.md"
```

Check consumers: backend Python, frontend JS (dashboard), Haiku commentary generator, any other brief/script.

### If unused

Drop it. Migration:
```sql
DROP VIEW IF EXISTS tf_capital_summary;
```

Keep the original DDL in the commit message for easy recovery. Done.

### If used

Fix the formula. The current (apparent) formula:
```sql
capital_available = tf_budget + total_realized_pnl − SUM(capital_allocation)
```

Correct formula that matches the dashboard:
```
cash_in_bots      = SUM of each active bot's real free USDT
deployed_cost     = SUM over open lots of (amount × buy_price)
deployed_market   = SUM over open lots of (amount × current_price)
skim_total        = SUM(reserve_ledger.amount) for TF-managed symbols
net_worth_tf      = cash_in_bots + deployed_market + skim_total
unrealized_tf     = deployed_market − deployed_cost
total_pnl_tf      = net_worth_tf − tf_budget_base
```

Expose as columns that mirror the dashboard card names: `cash`, `deployed_cost`, `deployed_market`, `skim`, `net_worth`, `unrealized`, `total_pnl`. Any future consumer then gets a shape identical to the UI.

### Files to touch

- Supabase migration (DROP or CREATE OR REPLACE VIEW)
- Any code reading `tf_capital_summary` (expected: none — verify)

### Verification

Either:
- View dropped, 24h of operation, no consumer complains.
- View returns numbers within ±$0.01 of dashboard across three spot-checks at different times of day.

---

## Section B — Post-stop-loss / post-take-profit deallocation

### Problem (concrete)

PHB today, allocation cycle 02:45 → ongoing:

| Time | Event | Realized |
|---|---|---|
| 07:39 | 3-lot stop-loss cascade | −$4.31 |
| 07:47 | grid buys 75 @ $0.140 | — |
| 07:48 | stop-loss on new lot | −$0.17 |
| 08:17 | grid buys 81 @ $0.129 | — |
| 08:18 | stop-loss | −$0.10 |
| 08:48 | grid buys 85 @ $0.124 | — |
| 08:49 | stop-loss (accidentally positive on rebound) | +$0.15 |

Six stop-loss events in 70 minutes on the same allocation. Fees bleeding, no rotation. TF scan at 08:47 classified PHB as SIDEWAYS (strength 11.06) — not strong enough to trigger a SWAP, and not BEARISH to trigger BEARISH EXIT. So the bot was free to keep buying.

### Fix

In the stop-loss handler in `grid_runner.py` (the mid-tick block CC flagged), after the stop-loss sell is recorded:

```
if holdings == 0 and self.managed_by == 'trend_follower':
    mark bot for deallocation:
      bot_config.pending_liquidation = true
      log a row in trend_decisions_log with action_taken='DEALLOCATE'
        and reason='STOP-LOSS exhausted (cycle closed after N stop-losses)'
```

Same logic for the take-profit handler. TP is a full-exit by design (39c), so after TP `holdings=0` always, and dealloc always follows.

### Effect

On next TF scan (≤1h, could be seconds away):
1. Scanner sees `pending_liquidation=true` → calls the dealloc path.
2. Dealloc path invokes `_force_liquidate`.
3. `_force_liquidate` sees `holdings=0` → no sell to execute → calls CC's fallback (`avg_buy × holdings = 0`) → computes `realized_pnl=0` → no skim row (correctly, PnL=0).
4. Cycle summary message fires via the 39e helper, reading the cycle window from `trend_decisions_log` (last ALLOCATE → now).
5. Bot becomes `is_active=false`. Capital freed for TF to allocate elsewhere on the same scan.

Net result: stop-loss closes a cycle honestly. One unified dealloc notification per cycle, regardless of which exit path triggered it (SWAP, BEARISH, stop-loss-exhaustion, TP-exhaustion). Thrash gone. Fees saved.

### Edge cases

**E1 — Holdings=0 via normal grid sells (not stop-loss, not TP):** do NOT auto-dealloc. The bot finished a normal cycle and is idle waiting for the next percentage-drop. Only stop-loss and take-profit exit paths trigger the dealloc flag. Gate on the trigger reason, not just on `holdings=0`.

**E2 — Stop-loss fires but not all lots closed:** do NOT dealloc. Only when the *last* open lot is closed and holdings goes to 0. Check after the sell, not before.

**E3 — Race between stop-loss and TF scan:** if TF scan fires between the stop-loss sell and the `pending_liquidation=true` write, scan sees active bot with holdings=0. Harmless — the bot survives one more scan cycle, dealloc happens on the next. Acceptable lag (max 1h, typically minutes).

**E4 — `_force_liquidate` with holdings=0:** CC's fallback (`avg_buy × holdings`) returns 0 when `holdings=0`. The code path must skip the `exchange.create_market_sell_order` call (nothing to sell) but still write a "DEALLOCATE cycle closed" trade row (or similar) and fire the cycle summary. **Verify this branch exists** — if `_force_liquidate` crashes or silently exits on holdings=0, Section B breaks. See Integration Check below.

**E5 — Coin re-allocated later with a fresh cycle:** each cycle is independent by design (39e). The dealloc-via-stop-loss closes cycle #N; a future ALLOCATE for the same coin opens cycle #N+1. Cycle summary shows only the most recent. No change needed.

### Files to touch

- `bot/grid_runner.py` — stop-loss handler, take-profit handler (add the `pending_liquidation` + `trend_decisions_log` write on `holdings==0` + TF-managed)
- `bot/grid_runner.py → _force_liquidate` — verify (and fix if needed) the `holdings=0` branch: skip sell, emit cycle summary, set `is_active=false`

### Verification

Paper mode:
1. Start a TF bot with $50 allocation, let it buy 3-4 lots.
2. Feed price data that triggers stop-loss on all lots.
3. Assert: after last stop-loss sell, `bot_config.pending_liquidation=true`.
4. Assert: a row appears in `trend_decisions_log` with `action_taken='DEALLOCATE'` and reason mentioning stop-loss exhaustion.
5. Run a TF scan.
6. Assert: `_force_liquidate` runs with holdings=0, no `create_market_sell_order` called, no skim row inserted, cycle summary Telegram message sent, `is_active=false`.
7. Repeat with take-profit trigger instead of stop-loss.

Real-world verification: next time a TF bot takes stop-loss damage, check that:
- No further buys happen on that coin after full liquidation.
- Cycle summary arrives on Telegram within the next TF scan (≤1h).
- Next TF scan allocates a different candidate.

---

## Integration check with CC's 39e report

Walking through CC's report items:

- ✓ **Fix 1+2 in `_force_liquidate`:** PnL + skim routing is correct for SWAP / BEARISH EXIT paths. After 39f Section B, the same function also handles stop-loss-exhausted and TP-exhausted paths, with `holdings=0`. **Action:** verify E4 above — the `holdings=0` branch must not crash and must emit the cycle summary.

- ✓ **Fix 3 cycle summary in `_force_liquidate`:** correctly tied to dealloc moment. After 39f Section B, this becomes the **unified** dealloc notification for all TF exit paths. No need for per-event cycle summary in mid-tick stop-loss/TP messages — CC was right to flag that as scope creep; 39f makes the feature unnecessary.

- ✓ **`send_tf_decision` no longer sends DEALLOCATE in live mode:** perfectly aligned with 39f. `_force_liquidate` is now the single source of dealloc truth. 39f completes the unification by making stop-loss and TP also route through `_force_liquidate`.

- ⚠️ **Fallback `avg_buy × holdings` for empty FIFO queue:** CC added this as a safety net for fixed-mode / edge cases. After 39f Section B, this fallback also handles the `holdings=0` stop-loss-exhaustion path (trivially: returns 0). **Confirm in paper-mode test** that the fallback path:
  - Does NOT register a skim row when PnL is 0.
  - Does NOT duplicate any realized_pnl.
  - Does NOT attempt a zero-amount market sell (should skip `exchange.create_market_sell_order`).

- ⚠️ **`bot.state.total_fees` and `_pct_open_positions` reset post-liquidation:** correct for SWAP/BEARISH (where there's an actual consolidated sell). For the stop-loss-exhaustion case, `_pct_open_positions` is already empty (stop-losses per lot already consumed it). **Confirm** the reset is idempotent — clearing an already-empty queue must be a no-op, not an error.

No gaps identified in CC's work. The 39e report is clean. 39f extends the same mechanism to cover two paths that 39e explicitly left out of scope.

---

## Out of scope

- Per-event cycle summary in individual stop-loss Telegram messages (CC's literal interpretation of the edge case). 39f Section B makes this unnecessary: the dealloc cycle summary covers the full cycle retrospectively. Don't add a second summary path.
- Retroactive dealloc for PHB right now. It's already thrashed; the allocation is partially drained. If the next TF scan doesn't naturally rotate PHB out (via SIDEWAYS eventually flipping to BEARISH, or another candidate surging), manual SQL intervention.
- Refactoring `_force_liquidate` to split sell vs. summary into separate functions. Keep one function, make it handle `holdings=0` cleanly.
- Any change to Section A's view formula if the view turns out to be used by external code we don't know about. Investigate first, decide after.

---

## Test pre-deploy

- Section A: run the new view on production data, compare column-by-column with dashboard for 3 snapshots at different times. Match within ±$0.01.
- Section B: paper-mode scenario as described above. Both stop-loss and TP paths must produce correct dealloc + cycle summary. Fallback path (empty FIFO, holdings=0) must not crash or write bogus skim.

## Test post-deploy

- Section A: 24h passive observation. No downstream consumer errors. Spot-check view vs dashboard once per day.
- Section B: next real TF stop-loss or TP event (whenever it happens). Verify Telegram sequence: stop-loss notifications, then cycle summary on dealloc, then new candidate allocation on next scan.

---

## Rollback

Standard:
```bash
git revert <commit_hash>
git push origin main
ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull && <restart orchestrator>'
```

Section A rollback: if view was dropped, `CREATE VIEW tf_capital_summary AS <original definition>` (kept in commit message). If view was rewritten, revert migration.

Section B rollback: code-only. Stop-loss goes back to not triggering dealloc. Thrash loop may reappear on the next drawdown. Acceptable fallback state.

---

## Commit format

If shipped together:
```
fix(tf): tf_capital_summary view + post-stop-loss dealloc

- Section A: tf_capital_summary view was reporting phantom
  capital_available based on bot_config.capital_allocation (target
  ceiling) instead of actual cash in bots. [dropped / rewritten]
  to mirror dashboard numbers within $0.01.

- Section B: TF bots now set pending_liquidation=true when stop-loss
  or take-profit closes all open lots. Previously, stop-loss cascaded
  but bot remained is_active=true, producing thrash loops (PHB today:
  6 stop-losses in 70 minutes on same allocation). Post-fix, next TF
  scan routes dealloc through _force_liquidate, reusing the brief 39e
  cycle summary path. One unified dealloc notification per cycle
  regardless of exit trigger.

Refs: brief 39f. Follows 39e (cycle summary) and 39a (stop-loss).
```

If shipped separately: split commits, each with its own Section A or Section B section of the above message.

---

## Ordering recommendation

1. **Section A first (lowest risk).** View fix. No behavior change to the bots. Ship, observe.
2. **Section B second.** Behavior change. Paper-mode test thoroughly, then ship.

If confident, one commit is fine. But the two changes are logically unrelated — Max's "dividi che poi CC fa casino" principle applies. Default to splitting unless there's a reason to combine.
