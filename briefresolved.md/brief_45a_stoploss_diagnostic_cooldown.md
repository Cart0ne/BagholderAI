# INTERN BRIEF 45a — Stop-Loss Timing Bug + Post-SL Cooldown

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 22, 2026
**Priority:** HIGH — active capital loss issue

---

## Context

MET/USDT was allocated by TF at 01:52 UTC on April 22. The grid bot bought all $38.34 via multi-lot entry at $0.19. The stop-loss threshold was 3% of allocation = -$1.15.

**Expected behavior:** stop-loss triggers when unrealized reaches -$1.15 (price ~$0.1843).
**Actual behavior:** stop-loss triggered at 02:52 UTC with unrealized = -$5.37 (price $0.1634). That's a **14% loss** instead of the intended 3%.

The stop-loss check lives in `grid_bot.py → check_percentage_grid()` and runs every 60s in the grid bot loop. With 60 checks in that hour, the threshold should have been caught well before -$5.37. Something prevented the check from firing or evaluating correctly.

**Second issue:** after the stop-loss at 02:52, TF re-allocated MET at 03:53 (1 hour later). No cooldown prevented immediate re-entry on the same coin that just stopped out.

---

## Part A — Diagnostic: Why Did the Stop-Loss Miss?

### Step 1: Add verbose logging to every stop-loss evaluation

In `bot/strategies/grid_bot.py`, inside `check_percentage_grid`, find the stop-loss check block (starts with `if self.managed_by == "trend_follower" and self.tf_stop_loss_pct > 0`).

**Add a debug log BEFORE the threshold comparison**, so we can see every evaluation:

```python
# --- 39a: TF stop-loss check ---
if (self.managed_by == "trend_follower"
        and self.tf_stop_loss_pct > 0
        and self.state.holdings > 0
        and self.state.avg_buy_price > 0
        and not self._stop_loss_triggered):
    unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
    loss_threshold = -(self.capital * self.tf_stop_loss_pct / 100)

    # 45a DIAGNOSTIC — log every evaluation, not just triggers
    logger.debug(
        f"[{self.symbol}] SL check: price={current_price:.6f} "
        f"avg_buy={self.state.avg_buy_price:.6f} "
        f"holdings={self.state.holdings:.4f} "
        f"unrealized=${unrealized:.2f} "
        f"threshold=${loss_threshold:.2f} "
        f"tf_sl_pct={self.tf_stop_loss_pct}"
    )

    if unrealized <= loss_threshold:
        # ... existing trigger logic ...
```

**Also add a log when the outer conditions SKIP the check entirely:**

```python
# 45a DIAGNOSTIC — log when stop-loss check is skipped
if self.managed_by == "trend_follower" and self.tf_stop_loss_pct > 0:
    if self.state.holdings <= 0:
        logger.debug(f"[{self.symbol}] SL check SKIPPED: holdings={self.state.holdings}")
    elif self.state.avg_buy_price <= 0:
        logger.debug(f"[{self.symbol}] SL check SKIPPED: avg_buy_price={self.state.avg_buy_price}")
    elif self._stop_loss_triggered:
        logger.debug(f"[{self.symbol}] SL check SKIPPED: already triggered")
elif self.managed_by == "trend_follower" and self.tf_stop_loss_pct == 0:
    logger.debug(f"[{self.symbol}] SL check SKIPPED: tf_stop_loss_pct=0")
```

Place this `elif`/`if` block as a sibling AFTER the main stop-loss `if` block (so it only runs when the main block's conditions are False).

### Step 2: Verify `tf_stop_loss_pct` is refreshed per-tick

In `bot/grid_runner.py`, inside the main loop, I can see that `greed_decay_tiers` and `allocated_at` are refreshed from Supabase every tick. **Check if `tf_stop_loss_pct` is also refreshed per-tick.**

Look for where `bot.tf_stop_loss_pct` is set. If it's ONLY set at bot startup (in the constructor or init block) and NOT refreshed in the per-tick config reload section, that's suspicious — it means a stale value could persist.

**If `tf_stop_loss_pct` is NOT refreshed per-tick, add it** alongside the greed_decay_tiers refresh:

```python
# In the per-tick config refresh block of the main loop:
new_sl_pct = reader.get_trend_config_value("tf_stop_loss_pct")
if new_sl_pct is not None:
    new_sl_pct = float(new_sl_pct)
    if new_sl_pct != bot.tf_stop_loss_pct:
        logger.info(
            f"[{symbol}] tf_stop_loss_pct updated: "
            f"{bot.tf_stop_loss_pct} → {new_sl_pct}"
        )
        bot.tf_stop_loss_pct = new_sl_pct
```

### Step 3: Verify state after multi-lot entry

The multi-lot entry (`_consume_initial_lots`) fires a single aggregated buy. After it completes, the bot state should have:
- `holdings > 0`
- `avg_buy_price > 0`

**Check that `_execute_percentage_buy` correctly updates `self.state.holdings` and `self.state.avg_buy_price` after the aggregated buy.** If the state update happens asynchronously (e.g., only on next DB read), the stop-loss check would see `holdings=0` or `avg_buy_price=0` for the first few cycles and skip.

Add a log after `_consume_initial_lots` returns in the main loop:

```python
# After _consume_initial_lots call:
lots_bought = _consume_initial_lots(config_reader, bot, cfg.symbol, price, notifier)
if lots_bought > 0:
    logger.info(
        f"[{cfg.symbol}] Post multi-lot state: "
        f"holdings={bot.state.holdings:.6f} "
        f"avg_buy={bot.state.avg_buy_price:.6f} "
        f"cash={bot.state.cash_available:.2f} "
        f"tf_sl_pct={bot.tf_stop_loss_pct}"
    )
```

---

## Part B — Post-Stop-Loss Cooldown

### Problem

After MET was stopped out at 02:52, TF re-allocated MET at 03:53. No mechanism prevents re-entry on a coin that just had a stop-loss.

### Solution

Add a `stop_loss_cooldown_hours` concept. When a stop-loss triggers, record the timestamp. The TF allocator skips that coin for N hours.

### Schema change

```sql
ALTER TABLE bot_config ADD COLUMN last_stop_loss_at timestamptz;
```

### Grid bot change

In `grid_bot.py`, when `_stop_loss_triggered` is set to True, also update the DB:

```python
if unrealized <= loss_threshold:
    self._stop_loss_triggered = True
    # 45a: Record stop-loss timestamp for cooldown
    try:
        from db.client import get_client
        get_client().table("bot_config").update(
            {"last_stop_loss_at": datetime.utcnow().isoformat()}
        ).eq("symbol", self.symbol).execute()
    except Exception as e:
        logger.error(f"[{self.symbol}] Failed to write last_stop_loss_at: {e}")
    # ... rest of existing trigger logic ...
```

### Allocator change

In `bot/trend_follower/allocator.py`, when evaluating candidates for ALLOCATE or SWAP, skip any coin that has a recent stop-loss:

```python
# 45a: Skip coins with recent stop-loss (cooldown)
STOP_LOSS_COOLDOWN_HOURS = 6  # Hardcoded for now; move to trend_config later if needed

for candidate in candidates:
    symbol = candidate['symbol']
    # Check if this coin was recently stopped out
    existing = supabase.table("bot_config").select(
        "last_stop_loss_at"
    ).eq("symbol", symbol).maybe_single().execute()

    if existing and existing.data and existing.data.get("last_stop_loss_at"):
        sl_time = datetime.fromisoformat(
            str(existing.data["last_stop_loss_at"]).replace("Z", "+00:00")
        )
        hours_since = (datetime.now(timezone.utc) - sl_time).total_seconds() / 3600
        if hours_since < STOP_LOSS_COOLDOWN_HOURS:
            logger.info(
                f"[{symbol}] SKIP: stop-loss cooldown — "
                f"{hours_since:.1f}h since last SL (need {STOP_LOSS_COOLDOWN_HOURS}h)"
            )
            continue  # Skip this candidate
```

**Where to place this check:** in the candidate filtering loop, BEFORE signal strength comparison. This way, a coin in cooldown is never considered for allocation regardless of how strong its signal is.

### Event logging

Log cooldown skips to `bot_events_log`:

```python
log_event(
    severity="info",
    category="tf",
    event="sl_cooldown_skip",
    symbol=symbol,
    message=f"Skipped: {hours_since:.1f}h since stop-loss (cooldown {STOP_LOSS_COOLDOWN_HOURS}h)",
    details={"hours_since": hours_since, "cooldown": STOP_LOSS_COOLDOWN_HOURS},
)
```

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/strategies/grid_bot.py` | MODIFY | Add diagnostic logging to stop-loss check (every evaluation + skip reasons); write `last_stop_loss_at` on trigger |
| `bot/grid_runner.py` | MODIFY | Add post-multi-lot state log; verify/add `tf_stop_loss_pct` per-tick refresh |
| `bot/trend_follower/allocator.py` | MODIFY | Add stop-loss cooldown check in candidate filtering |
| DB (`bot_config`) | MIGRATE | `ALTER TABLE bot_config ADD COLUMN last_stop_loss_at timestamptz;` |

## Files NOT to touch

- `config/settings.py` — manual bot settings unchanged
- `trend_config` — no schema changes (cooldown is hardcoded 6h for now)
- `web/tf.html` — no admin UI for cooldown yet
- Telegram report logic — no changes

---

## DB Migration

```sql
ALTER TABLE bot_config ADD COLUMN last_stop_loss_at timestamptz;
```

Run on Supabase, then immediately:

```sql
ALTER TABLE bot_config DISABLE ROW LEVEL SECURITY;
```

(Reminder: RLS must be disabled on all new/modified tables per standing rule.)

---

## Test checklist

### Diagnostic logging
- [ ] Deploy and wait for next TF allocation. Tail the grid bot log.
- [ ] Confirm `SL check:` debug lines appear every 60s with correct values (price, avg_buy, holdings, unrealized, threshold, tf_sl_pct)
- [ ] If any `SL check SKIPPED:` lines appear, note the reason — this tells us why the original MET check failed
- [ ] After multi-lot entry: `Post multi-lot state:` log shows holdings > 0, avg_buy > 0, tf_sl_pct = 3

### Per-tick refresh
- [ ] Change `tf_stop_loss_pct` in Supabase admin from 3 to 5 while a TF bot is running
- [ ] Confirm log shows `tf_stop_loss_pct updated: 3.0 → 5.0` within one tick
- [ ] Change it back to 3

### Cooldown
- [ ] After a stop-loss fires, check `bot_config` for the coin: `last_stop_loss_at` should be set
- [ ] On next TF scan, the stopped-out coin should show `SKIP: stop-loss cooldown` in allocator logs
- [ ] After 6 hours, the coin should be eligible for allocation again
- [ ] Manual bots: `last_stop_loss_at` is always NULL, cooldown logic never applies (verify no crash)

### Integration
- [ ] Full cycle: TF allocates coin → multi-lot entry → price drops → stop-loss fires at ~3% (NOT 14%) → coin enters cooldown → TF skips it on next scan → after 6h, coin eligible again
- [ ] If diagnostic shows stop-loss IS checking correctly and the price genuinely gapped through the threshold, note that in the log and report back — we may need a different architectural fix

---

## Scope rules

- **DO NOT** modify manual bot behavior (BTC/SOL/BONK)
- **DO NOT** change the stop-loss percentage (keep at 3%)
- **DO NOT** change scan interval or greed decay logic
- **DO NOT** add admin UI for cooldown (future brief if needed)
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
fix(grid-bot): stop-loss diagnostic logging + post-SL cooldown (45a)

Adds per-tick debug logging to every stop-loss evaluation so we can
diagnose why the 3% threshold was missed on MET (fired at -14%).
Ensures tf_stop_loss_pct is refreshed per-tick like greed_decay_tiers.
Adds 6h cooldown on coins after stop-loss to prevent immediate re-entry.
New column: bot_config.last_stop_loss_at (timestamptz).
```
