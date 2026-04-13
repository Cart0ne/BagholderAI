# BagHolderAI — Intern Brief: Session 22 (UPDATE)
## Two bugs to fix BEFORE restarting bots

**Priority:** URGENT — bots are stopped  
**Date:** 2026-04-06

---

## Context

The position reconstruction fix from earlier today WORKS correctly. Bots now reload holdings from DB at boot. However, two new bugs surfaced during the first live run.

---

## Bug 1 — TradeLogger crash on `trade_pnl_pct`

**Symptom:**
```
ERROR: Failed to log trade: TradeLogger.log_trade() got an unexpected keyword argument 'trade_pnl_pct'
```

**Impact:** Trades execute in memory (and on Telegram) but are NOT saved to the database. This causes:
- Missing trade records
- State desync between bot memory and DB
- On next restart, the bot reconstructs stale state and may re-execute the same trades

**Fix:** In `grid_runner.py` (or wherever `log_trade()` is called), the call passes a `trade_pnl_pct` keyword argument that `TradeLogger.log_trade()` does not accept. Either:
- **Option A:** Remove `trade_pnl_pct` from the call site (if it's not needed in the DB)
- **Option B:** Add `trade_pnl_pct` as a parameter to `TradeLogger.log_trade()` (if there's a column for it)

Check the `trades` table schema — there is no `trade_pnl_pct` column, so **Option A** (remove it from the call) is likely correct. The PnL data is already being sent via Telegram and the `realized_pnl` column exists for the absolute value.

**Verification:** After fix, restart any bot, wait for a trade, confirm it appears in the `trades` table in Supabase.

---

## Bug 2 — Hidden 2% minimum profit target blocking BONK sells

**Symptom (from BONK log):**
```
SKIP: pct sell at $0.00000576 below min profit target (need $0.00000583, 2.0% above avg buy)
```

**Impact:** BONK has `sell_pct = 1.0%` in `bot_config`, but the code enforces a **hardcoded 2% minimum profit target** that overrides it. This means BONK needs a 2% rise above avg buy to sell, not 1%. For a coin that barely moves 1-2% per day, this effectively blocks all sells.

**Fix:** Find the hardcoded minimum profit target in the grid/sell logic. It's likely a line like:
```python
MIN_PROFIT_PCT = 0.02  # or min_profit_target = 2.0
```

This should either:
- **Option A:** Be removed entirely — let `sell_pct` from `bot_config` be the sole threshold
- **Option B:** Be made configurable via `bot_config` (there's already a `profit_target_pct` column — check if it's being used correctly)

Check `bot_config.profit_target_pct` values in the DB. If they're set to 2%, update them to match `sell_pct` or remove the override logic.

**Verification:** After fix, BONK should sell when price reaches ~$0.000005777 (1% above avg buy of $0.00000572), NOT $0.00000583.

---

## Files to check/modify

| File | Issue |
|------|-------|
| `bot/grid_runner.py` or `bot/grid.py` | `trade_pnl_pct` argument in `log_trade()` call |
| `bot/trade_logger.py` (or similar) | `log_trade()` method signature |
| `bot/grid.py` or sell logic | Hardcoded 2% min profit target |

---

## What was already fixed manually

The two BTC sell trades that failed to log have been manually inserted into the `trades` table:
1. SELL 0.000195 BTC @ $69,163.95 (realized PnL: +$0.6411)
2. SELL 0.000371 BTC @ $69,163.94 (realized PnL: +$0.6069)

No other manual DB intervention needed.

---

## Out of scope

- Changing grid parameters or capital allocation
- Frontend/dashboard work
- Anything not directly related to these two fixes
