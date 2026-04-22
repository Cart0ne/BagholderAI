# INTERN BRIEF 45a v2 — Post-Stop-Loss Cooldown (configurable)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 22, 2026
**Priority:** MEDIUM — capital protection, configurable off-switch
**Supersedes:** brief_45a_stoploss_diagnostic_cooldown.md (v1)

---

## Context & why v2

The v1 brief assumed the MET -14% stop-loss was caused by a bug in the
SL check (missed evaluation, stale config, or broken state). After log
analysis this assumption was proven **wrong**:

- Loop runs every 60s as designed (the "--- Grid Status ---" line prints
  only every 10 cycles, which is what misled us).
- `tf_stop_loss_pct` is already refreshed per-tick via `_sync_config_to_bot`.
- `holdings` and `avg_buy_price` are updated in memory immediately after
  `_consume_initial_lots`.
- The SL calculation itself was correct: `threshold=$-1.15` for a $38.35
  allocation at 3%.

**What really happened:** MET had a flash crash on 2026-04-22 02:52:00 UTC
— one 1-minute candle went from $0.1850 open to $0.1528 low (-19%). The
bot's next tick (at 02:52:24) caught the price at $0.1634 and fired the
SL at the first opportunity. By 02:55 the price had recovered to $0.1924.

**The SL worked correctly.** There is no bug to diagnose. The v1 Part A
(verbose logging + tf_stop_loss_pct refresh + post-multi-lot state log)
is therefore **dropped** — it would add noise without value.

**What still matters:** after the SL sold MET at $0.16, the TF reallocated
MET at 03:53 (one scan later, ~1h) when it saw BULLISH again. No cooldown
prevented immediate re-entry on a coin that had just been stop-hunted.
That is the one real issue worth fixing.

---

## Scope

One feature: a **configurable cooldown** that prevents the TF from
re-allocating a coin for N hours after its stop-loss triggered.

Default: `0` hours = **disabled** (current behaviour preserved). Max
can raise it from the dashboard when he wants to test.

This brief intentionally does **not** include:
- Diagnostic SL logging (not needed — SL works)
- `tf_stop_loss_pct` per-tick refresh (already exists)
- Post-multi-lot state log (state is correct)
- UI gating of TF-overwritten fields (→ separate brief 45b)
- "Monetacce" volume-tier filter (→ separate brief, TBD)

---

## DB migration

```sql
ALTER TABLE bot_config ADD COLUMN last_stop_loss_at timestamptz;
ALTER TABLE trend_config ADD COLUMN tf_stop_loss_cooldown_hours numeric DEFAULT 0;
ALTER TABLE bot_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
```

Default is `0` (disabled). RLS disabled per standing rule on modified
tables.

---

## Grid bot change — write `last_stop_loss_at` on SL trigger

In `bot/strategies/grid_bot.py`, inside `check_percentage_grid`, locate
the SL trigger block (the `if unrealized <= loss_threshold:` branch).

Right after setting `self._stop_loss_triggered = True`, write the
timestamp to `bot_config` for this symbol:

```python
from datetime import datetime, timezone  # at top of file if not present

if unrealized <= loss_threshold:
    self._stop_loss_triggered = True

    # 45a v2: record SL timestamp for TF cooldown (0h = disabled, but
    # we always write — so the history is available if Max enables it later)
    try:
        from db.client import get_client
        get_client().table("bot_config").update(
            {"last_stop_loss_at": datetime.now(timezone.utc).isoformat()}
        ).eq("symbol", self.symbol).execute()
    except Exception as e:
        logger.error(
            f"[{self.symbol}] Failed to write last_stop_loss_at: {e}"
        )

    # ... existing trigger logic (pending_liquidation, log_event, etc) ...
```

**Important:** use `datetime.now(timezone.utc)`, NOT `datetime.utcnow()`
(deprecated in Python 3.12, removed in future versions).

**Applies to SL only:** do NOT write `last_stop_loss_at` on BEARISH
deallocate, manual stop, or any other deallocate reason. The cooldown
is specifically for stop-loss events.

---

## Allocator change — skip candidates in cooldown

In `bot/trend_follower/allocator.py`:

### 1. Read the cooldown value from `trend_config`

Find where other `trend_config` values are read (e.g. `tf_max_coins`,
`tf_lots_per_coin`, `min_allocate_strength`) and add:

```python
cooldown_hours = float(trend_config.get("tf_stop_loss_cooldown_hours") or 0)
```

If the value is `0` (or NULL), cooldown is disabled and the rest of the
logic is a no-op — no DB query, no skip, no log.

### 2. Guard: if cooldown disabled, skip entirely

Wrap the cooldown check in:

```python
if cooldown_hours > 0:
    # ... cooldown logic ...
```

This keeps the allocator fast when the feature is off.

### 3. Cooldown check — in both ALLOCATE and SWAP paths

The SL cooldown must skip a coin in **both** decision paths:
- ALLOCATE loop (new coin being considered for a free slot)
- SWAP loop (coin being considered to replace an active one)

Refactor the check into a helper at module level so both paths call it:

```python
from datetime import datetime, timezone

def _is_in_sl_cooldown(symbol: str, cooldown_hours: float, supabase) -> tuple[bool, float]:
    """
    Returns (in_cooldown, hours_since_sl).
    hours_since_sl = 0.0 if no SL recorded or cooldown disabled.
    """
    if cooldown_hours <= 0:
        return False, 0.0
    try:
        res = supabase.table("bot_config").select(
            "last_stop_loss_at"
        ).eq("symbol", symbol).maybe_single().execute()
        if not res or not res.data:
            return False, 0.0
        sl_ts = res.data.get("last_stop_loss_at")
        if not sl_ts:
            return False, 0.0
        sl_time = datetime.fromisoformat(str(sl_ts).replace("Z", "+00:00"))
        hours_since = (datetime.now(timezone.utc) - sl_time).total_seconds() / 3600
        return hours_since < cooldown_hours, hours_since
    except Exception as e:
        logger.warning(f"[ALLOCATOR] SL cooldown check failed for {symbol}: {e}")
        return False, 0.0  # Fail-open: don't block allocation on query error
```

**Fail-open design:** if the DB query errors, allocation is NOT blocked.
Better to risk re-entering a just-stopped coin than to block all
allocations indefinitely because of a transient DB hiccup.

### 4. Call site — ALLOCATE path

Inside the ALLOCATE candidate loop, **before** the signal-strength check
(so a cooldown coin never even competes on signal):

```python
in_cooldown, hours_since = _is_in_sl_cooldown(
    candidate["symbol"], cooldown_hours, supabase
)
if in_cooldown:
    logger.info(
        f"[ALLOCATOR] SKIP {candidate['symbol']}: SL cooldown — "
        f"{hours_since:.1f}h since last SL (need {cooldown_hours}h)"
    )
    log_event(
        severity="info",
        category="tf",
        event="sl_cooldown_skip",
        symbol=candidate["symbol"],
        message=(
            f"Skipped ALLOCATE: {hours_since:.1f}h since SL "
            f"(cooldown {cooldown_hours}h)"
        ),
        details={
            "hours_since": hours_since,
            "cooldown_hours": cooldown_hours,
            "path": "ALLOCATE",
        },
    )
    continue
```

### 5. Call site — SWAP path

Same check, inside the SWAP candidate evaluation loop, before the
strength-delta comparison. Log with `"path": "SWAP"` in `details`.

---

## Dashboard UI change — `/web/tf.html`

Add `tf_stop_loss_cooldown_hours` to the TF settings form, next to
`tf_stop_loss_pct`.

- **Label:** "SL cooldown (ore)"
- **Helper text:** "Ore minime tra stop-loss e riallocazione della stessa
  coin. 0 = disattivato (TF può riallocare subito)."
- **Input type:** number, step 0.5, min 0, max 48
- **Wire it into the same save handler that persists the other
  `trend_config` fields** — no new endpoint needed.

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/strategies/grid_bot.py` | MODIFY | Write `last_stop_loss_at` on SL trigger (use `datetime.now(timezone.utc)`) |
| `bot/trend_follower/allocator.py` | MODIFY | Read `tf_stop_loss_cooldown_hours` from `trend_config`; add `_is_in_sl_cooldown` helper; call in ALLOCATE + SWAP paths with guard-clause on `cooldown_hours > 0` |
| `web/tf.html` | MODIFY | Add `tf_stop_loss_cooldown_hours` input next to `tf_stop_loss_pct` |
| DB (`bot_config`, `trend_config`) | MIGRATE | Add columns per migration SQL above |

## Files NOT to touch

- `config/settings.py` — manual bot settings unchanged
- `bot/grid_runner.py` — no changes (SL per-tick refresh already exists)
- Telegram report logic — no changes
- Any BEARISH / manual-stop path — cooldown applies to SL only

---

## Test checklist

### DB migration
- [ ] Run migration on Supabase
- [ ] Confirm `bot_config.last_stop_loss_at` exists and is NULL for all rows
- [ ] Confirm `trend_config.tf_stop_loss_cooldown_hours` exists and defaults to 0
- [ ] RLS is disabled on both tables

### Feature OFF (default: cooldown_hours=0)
- [ ] Trigger an SL on a test coin. Confirm `last_stop_loss_at` is written.
- [ ] Wait for next TF scan. Confirm the coin CAN be reallocated immediately (no skip).
- [ ] Confirm NO `sl_cooldown_skip` events in `bot_events_log`.
- [ ] Confirm no DB query overhead when cooldown is 0 (guard clause works).

### Feature ON (set cooldown_hours=4 from dashboard)
- [ ] Trigger an SL on a test coin. Confirm `last_stop_loss_at` is written.
- [ ] On the next TF scan within 4h, the coin must be skipped in ALLOCATE.
  Confirm log line: `SKIP {symbol}: SL cooldown — X.Xh since last SL`.
- [ ] Confirm `sl_cooldown_skip` event in `bot_events_log` with `path=ALLOCATE`.
- [ ] If the coin is a swap candidate, confirm it's skipped in SWAP path too
  (event has `path=SWAP`).
- [ ] After 4h, the coin should be eligible again (check by waiting or
  by manually backdating `last_stop_loss_at` in DB for a faster test).

### Dashboard
- [ ] Open `/web/tf.html`. Confirm the new "SL cooldown (ore)" field renders.
- [ ] Change from 0 → 4, save. Confirm DB value updates.
- [ ] Change back to 0, save. Confirm DB value is 0 again (not NULL).

### Manual bots
- [ ] BTC/SOL/BONK are managed manually (`managed_by` IS NULL or 'manual').
  Confirm their `last_stop_loss_at` stays NULL regardless of what happens
  (grid bot writes it, but TF cooldown logic only runs for TF candidates).
- [ ] No crash when `last_stop_loss_at` is NULL.

### Edge cases
- [ ] DB query error during cooldown check → allocation proceeds (fail-open)
- [ ] `cooldown_hours` set to a negative value in DB → treated as disabled
- [ ] `last_stop_loss_at` in the future (clock skew) → `hours_since` negative
  → `hours_since < cooldown_hours` is true → coin stays in cooldown. Acceptable.

---

## Scope rules

- **DO NOT** modify manual bot behaviour
- **DO NOT** change the 3% SL threshold
- **DO NOT** add diagnostic logging to the SL check (v1 Part A dropped)
- **DO NOT** touch the `tf_stop_loss_pct` refresh logic (already correct)
- **DO NOT** apply cooldown to BEARISH deallocate or manual stop
- Default `tf_stop_loss_cooldown_hours = 0` must preserve current behaviour exactly
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(tf): configurable post-stop-loss cooldown (45a v2)

Adds tf_stop_loss_cooldown_hours (default 0 = disabled) to trend_config.
Grid bot records last_stop_loss_at in bot_config when SL fires.
Allocator skips candidates in cooldown for both ALLOCATE and SWAP.
Dashboard exposes the setting on /tf.html for live tuning.

Supersedes v1 diagnostic brief: log analysis of the MET 2026-04-22 flash
crash showed the SL mechanism works correctly — a 1-minute candle gapped
from $0.185 to $0.153 and the bot liquidated at the first tick.
No SL bug to diagnose; cooldown addresses the separate re-entry problem.

New columns: bot_config.last_stop_loss_at, trend_config.tf_stop_loss_cooldown_hours.
```
