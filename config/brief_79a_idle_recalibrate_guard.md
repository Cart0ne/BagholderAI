# Brief 79a — Idle Recalibration Guard: Suppress When Capital Exhausted

**Date:** May 18, 2026  
**Author:** CEO (Claude)  
**Based on:** PROJECT_STATE.md aggiornato 2026-05-15 (S78 chiusura)  
**Priority:** Alta — riduce rumore operativo durante drawdown  
**Estimated effort:** 20–30 minuti  

---

## Context

When all capital is deployed (drawdown scenario, Strategy A "never sell at loss"), the idle recalibration in `grid_bot.py` fires every `idle_reentry_hours` resetting `_pct_last_buy_price` to `current_price`. This is pointless: there's no cash to buy. The recalibrate generates log noise and Telegram alerts (when not suppressed by stop_buy) without any operational benefit.

Board observation (Max, S79): "I vari idle recalibration se ho tutto il cash impegnato dovrebbero essere disabilitati in automatico."

Current suppression already exists for **stop_buy_active** (S76 audit, `idle_alerts.py`). This brief adds a second, independent suppression for **capital exhausted**.

---

## What to change

### File: `bot/grid/grid_bot.py`

In the `IDLE RE-ENTRY / RECALIBRATE CHECK` block, add a guard at the top of the idle check (before both Path A and Path B):

**New guard logic:**

```python
# Check available capital before idle actions
available = self._get_available_capital()  # or compute inline
capital_exhausted = available < MIN_LAST_SHOT_USD  # same constant used by grid_runner
```

**Path B (holdings > 0, recalibrate):**
- If `capital_exhausted` → skip recalibrate, log:
  `[{symbol}] Idle recalibrate suppressed: capital exhausted (${available:.2f} available)`
- Still advance `_last_trade_time` (prevents per-cycle spam)
- Emit `idle_recalibrate_suppressed_no_cash` event to `bot_events_log` (severity=info, category=trade_audit)
- Do NOT add to `idle_reentry_alerts` (no Telegram)

**Path A (holdings <= 0, re-entry buy):**
- If `capital_exhausted` → skip re-entry, log:
  `[{symbol}] Idle re-entry suppressed: capital exhausted (${available:.2f} available)`
- Still advance `_last_trade_time`
- Emit `idle_reentry_suppressed_no_cash` event to `bot_events_log`
- Do NOT add to `idle_reentry_alerts`

**Why both paths:** Path A with holdings=0 AND cash=0 is a degenerate state (fully liquidated but no capital returned — shouldn't happen under normal conditions). Suppressing it avoids a failed buy attempt; the state itself warrants investigation if it occurs, hence the bot_events_log entry.

### File: `bot/grid_runner/__init__.py`

No changes needed. The `_capital_exhausted` flag in grid_runner is for Telegram dedup, independent of this guard.

### File: `bot/grid_runner/idle_alerts.py`

No changes needed. Existing `stop_buy_active` suppression is orthogonal. When capital is exhausted, the alert never reaches this function (suppressed upstream in grid_bot.py).

---

## Available capital computation

`grid_bot.py` doesn't currently have `MIN_LAST_SHOT_USD` imported. Two options:

**Option A (preferred):** Import `MIN_LAST_SHOT_USD` from `bot/grid_runner/__init__.py` (where `HardcodedRules` lives) or from a shared constants module.

**Option B:** Compute inline: `available = self.capital - self.state.total_invested + self.state.total_received` and check `available < 1.0` (the grid_runner value is 1.0 USD). This avoids the import but hardcodes the threshold.

CC decides. Both work. The threshold must match the one used by grid_runner for `_capital_exhausted` notifications.

---

## Decisions delegated to CC

- Which option for available capital computation (A or B above)
- Whether to extract `MIN_LAST_SHOT_USD` to a shared constants module (nice-to-have, not required)
- Exact placement of the guard within the idle block (before the `elapsed >= self.idle_reentry_hours` check, or inside it)

## Decisions CC MUST ask Board

- None — this is a straightforward guard addition

---

## Expected output at end of session

1. Modified `bot/grid/grid_bot.py` with idle guard
2. Commit on main, push
3. Restart orchestrator on Mac Mini
4. Verify in logs: next idle cycle for SOL (currently 6 days idle with no cash) should show "suppressed" instead of "recalibrate"

---

## Constraints

- Do NOT change the recalibrate logic itself — only add the guard
- Do NOT modify `idle_alerts.py` or `grid_runner/__init__.py`
- Do NOT touch Sentinel/Sherpa/TF code
- `_last_trade_time` MUST still advance even when suppressed (prevents per-cycle spam)
- The `bot_events_log` entry is mandatory (audit trail for the suppression)

---

## Roadmap impact

None. This is a quality-of-life fix, not a roadmap item. Mention in V&C §8 (log hygiene) if appropriate.

---

## Test verification

After restart, check logs for the first idle cycle of each bot:
- SOL (6 days idle, likely capital exhausted) → should show "suppressed"
- BTC/BONK → may or may not trigger depending on available capital
