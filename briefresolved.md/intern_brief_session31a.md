# INTERN BRIEF — Session 31a: Infrastructure Prep for Trend Follower

**Date:** April 12, 2026
**Priority:** HIGH — prerequisite for Trend Follower, includes active bug fix
**Scope:** Bot code + grid_runner only — no new scripts, no external connections beyond Binance API

---

## Context

We're preparing the infrastructure for the Trend Follower (TF). Before building the TF itself, the existing grid bot needs three things fixed/added:

1. A live bug: SOL idle re-entry isn't firing despite `idle_reentry_hours = 1` and 3 days of inactivity
2. The `is_active` flag exists in `bot_config` but is never checked — the grid bot ignores it
3. Grid bots need to validate orders against Binance exchange filters (MIN_NOTIONAL, LOT_SIZE) to prevent ghost trades and prepare for live trading

---

## Fix 1 — SOL Idle Re-Entry Bug (INVESTIGATE + FIX)

### Symptom

SOL/USDT last trade: April 9, 22:17 UTC (a sell at $85.50). Since then: zero activity. `idle_reentry_hours = 1` in `bot_config`. The bot should have re-entered within 1 hour. It's been 3+ days.

### What to investigate

The idle re-entry check in `grid_bot.py` → `_check_percentage_and_execute()` has 4 conditions that ALL must be true:

```python
if (self.state.holdings <= 0
    and self._pct_last_buy_price > 0
    and self._last_trade_time is not None
    and self.idle_reentry_hours > 0):
```

One of these is failing silently. Most likely candidates:

**A) `_last_trade_time is None` after bot restart**
- Check `init_percentage_state_from_db()` — does it restore `_last_trade_time` from the DB?
- The brief from Session 22c specified: "Al boot, leggere il `created_at` dell'ultimo trade v3 per questo symbol dal DB e salvarlo in `self._last_trade_time`"
- If this isn't implemented (or uses wrong query), `_last_trade_time` stays None after restart and idle re-entry never fires
- **This is the most likely cause** — verify first

**B) `_pct_last_buy_price == 0` after selling everything**
- After a complete sell-off, the buy reference resets. Check if it resets to the sell price (correct) or to 0 (would block re-entry)
- Look at the sell function: there should be a line like `self._pct_last_buy_price = price` after selling everything

**C) `self.state.holdings > 0` due to dust**
- Floating point issue: holdings might be 0.000000001 instead of exactly 0
- Check if the comparison is `<= 0` (correct) or `== 0` (fragile)

**D) Bot process crashed / not running**
- Check if the SOL process is alive on the Mac Mini
- If it crashed, check logs for the crash reason

### Diagnostic steps for CC

1. Read the SOL bot logs from the last 72 hours. Look for:
   - Any `IDLE RE-ENTRY CHECK` log lines (these are logged every hour boundary)
   - Any crash/exception traces
   - The boot sequence log (was the bot restarted recently?)

2. In `init_percentage_state_from_db()`, verify that `_last_trade_time` is being restored. Add a log line if it's not there:
   ```python
   logger.info(f"[{self.symbol}] Restored _last_trade_time = {self._last_trade_time}")
   ```

3. After identifying the cause, fix it. The fix must ensure that after any restart, `_last_trade_time` is always restored from the DB.

### Test

- [ ] Restart the SOL bot → check logs → `_last_trade_time` should show the last trade timestamp from DB
- [ ] With holdings=0 and idle_reentry_hours=1, the bot should re-enter within 1 hour
- [ ] After re-entry, normal trading resumes

---

## Fix 2 — Implement `is_active` Check in Grid Runner

### Current state

`is_active` is fetched from Supabase in `_CONFIG_FIELDS` (in `supabase_config.py`) but is **never used**. The function `_sync_config_to_bot()` in `grid_runner.py` does not sync `is_active` to the bot, and the main loop never checks it.

Setting `is_active = false` in the dashboard currently does nothing.

### Required behavior

In the main loop of `grid_runner.py`, after config sync and before the price check:

1. Read `is_active` from the config reader
2. If `is_active == false`:
   - Log: `[{symbol}] is_active=false — shutting down gracefully`
   - Send Telegram notification: `🛑 {SYMBOL} grid bot stopped (is_active=false)`
   - Break the main loop (graceful exit — do NOT force-sell positions)
   - The bot process ends cleanly

### Also: guard idle re-entry

In the idle re-entry check (grid_bot.py), add `is_active` as a condition. The bot must NOT re-enter if it's been deactivated. This requires passing `is_active` from the config to the bot.

**Option A (simple):** Add `is_active` to `_sync_config_to_bot()` so the bot has access:
```python
if "is_active" in sb_cfg:
    bot.is_active = sb_cfg["is_active"]
```

Then in the idle re-entry check:
```python
if (self.is_active  # <-- new condition
    and self.state.holdings <= 0
    and self._pct_last_buy_price > 0
    ...):
```

### Test

- [ ] Set `is_active = false` for a test symbol in Supabase → bot stops within one config refresh cycle (5 minutes max)
- [ ] Telegram notification is sent
- [ ] With `is_active = false` and holdings=0, idle re-entry does NOT fire
- [ ] Set `is_active = true` again → bot needs manual restart (this is expected — the Runner/Orchestrator will handle auto-restart in Phase D)

---

## Fix 3 — Exchange Filter Validation in Grid Bot

### Context

In paper trading, orders with `amount = 0` or tiny amounts pass because there's no exchange validation. Yesterday we fixed a ghost sell bug (amount=0 sell passing through). But the root cause is broader: we need to validate ALL orders against Binance's exchange filters before executing them.

This is preparation for live trading AND for the Trend Follower (which needs to check filters during coin selection).

### Implementation

#### 3a. Fetch and cache exchange filters

Create a new utility module: `utils/exchange_filters.py`

```python
"""
Fetches and caches Binance exchange filters (MIN_NOTIONAL, LOT_SIZE).
Used by grid bots and (future) Trend Follower.
"""
```

**Functions needed:**

1. `fetch_filters(exchange, symbol: str) -> dict`
   - Call Binance API: `exchange.fetch_markets()` or use ccxt's market info
   - Extract for the given symbol:
     - `min_notional`: from the NOTIONAL or MIN_NOTIONAL filter
     - `lot_step_size`: from LOT_SIZE filter → `stepSize`
     - `min_qty`: from LOT_SIZE filter → `minQty`
   - Return dict: `{"min_notional": float, "lot_step_size": float, "min_qty": float}`

2. `fetch_and_cache_filters(exchange, symbols: list[str]) -> None`
   - Fetch filters for all symbols
   - Write to Supabase table `exchange_filters` (upsert by symbol)
   - Log: `[exchange_filters] Cached filters for N symbols`

3. `validate_order(symbol: str, amount: float, price: float, filters: dict) -> tuple[bool, str]`
   - Check: `amount > 0`
   - Check: `amount >= min_qty`
   - Check: `amount * price >= min_notional`
   - Check: `amount % lot_step_size == 0` (within floating point tolerance)
   - Return: `(True, "OK")` or `(False, "MIN_NOTIONAL not met: $3.20 < $5.00")`

4. `round_to_step(amount: float, step_size: float) -> float`
   - Round amount DOWN to nearest valid step size
   - Used before placing orders

**Note on ccxt:** The exchange object already uses ccxt. Market info is available via `exchange.markets[symbol]` after calling `exchange.load_markets()`. The filters are in `market['limits']` and `market['precision']`. Check the ccxt docs — the data might already be there without a separate API call.

#### 3b. Integrate into grid bot

In `_execute_percentage_buy()` and `_execute_percentage_sell()`, BEFORE executing the trade:

```python
# Validate order against exchange filters
valid, reason = validate_order(self.symbol, amount, price, self._exchange_filters)
if not valid:
    logger.warning(f"[{self.symbol}] Order rejected: {reason}")
    return None
```

The bot needs to load filters once at startup. In `grid_runner.py` → `run_grid_bot()`, after exchange initialization:

```python
from utils.exchange_filters import fetch_filters
filters = fetch_filters(exchange, cfg.symbol)
bot.set_exchange_filters(filters)  # store on the bot instance
```

#### 3c. Round amounts to step size

In `_execute_percentage_buy()`, after calculating `amount = cost / price`:
```python
amount = round_to_step(amount, self._exchange_filters["lot_step_size"])
```

In `_execute_percentage_sell()`, same treatment for the sell amount.

### Test

- [ ] Bot starts → logs fetched filters for its symbol
- [ ] Buy with amount below min_qty → order rejected with log warning
- [ ] Buy with notional below min_notional → order rejected with log warning
- [ ] Amounts are always rounded to valid step sizes
- [ ] Ghost sell (amount=0) → caught by `amount > 0` check before it reaches the execute step
- [ ] Filters are written to `exchange_filters` table in Supabase (verify via admin query)

---

## Files involved

| File | Fixes |
|------|-------|
| `bot/strategies/grid_bot.py` | Fix 1 (idle re-entry bug), Fix 2 (is_active guard), Fix 3b/3c (order validation) |
| `bot/grid_runner.py` | Fix 2 (is_active main loop check), Fix 3b (load filters at startup) |
| `utils/exchange_filters.py` | Fix 3a (NEW FILE — fetch, cache, validate) |
| `config/supabase_config.py` | Fix 2 (ensure is_active is available) — likely no changes needed, already fetched |

---

## Scope Rules

- No launching bots
- Binance API calls allowed ONLY for `exchange.load_markets()` / `exchange.fetch_markets()` (read-only market info)
- Supabase writes allowed ONLY to `exchange_filters` table
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
fix(bot): SOL idle re-entry bug + is_active check + exchange filter validation
```

If the changes are large, split into:
```
fix(bot): restore _last_trade_time on restart (SOL idle re-entry)
feat(bot): implement is_active graceful shutdown
feat(bot): exchange filter validation + round to step size
```
