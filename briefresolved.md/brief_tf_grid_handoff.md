# INTERN BRIEF — TF→GRID Handoff for Tier 1-2 Coins

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Date:** May 2, 2026
**Priority:** HIGH — architectural change, test carefully
**Depends on:** 45c (volume tiers), 45f (profit lock) — both deployed ✅
**Scope:** allocator, grid_bot, grid_runner, trend_follower, dashboard, DB

---

## The Problem (with data)

TF scans well but manages poorly. The stop-loss cycle destroys value:

**SPK/USDT** — 60 trades, 4 days. Price went from $0.028 to $0.047 (+70%).
TF result: **−$2.37**. Eight stop-loss cascades ate all profits on a coin
that nearly doubled.

**ORCA/USDT** — 4 trades, 3 days. Price went from $1.71 to $2.01 (+17%).
TF result: **−$1.43**. Stopped out twice on a coin that was rising.

Meanwhile, GRID bots (BTC/SOL/BONK) consistently produce profit by buying
dips and selling at target with patience. No stop-loss, no panic exits.

## The Idea

TF becomes a **scout**: it scans, classifies, selects coins. But for
Tier 1 and Tier 2 coins (≥$20M volume), instead of managing them with
its own destructive logic, it **hands them to GRID**.

- **Tier 1 + 2** → `managed_by = 'tf_grid'` — GRID management, patient,
  no stop-loss. Exit via **Profit Lock** only.
- **Tier 3** → `managed_by = 'trend_follower'` — unchanged, TF manages
  as today. Small budget, high risk, fast rotation.

---

## New `managed_by` value: `tf_grid`

This is the core change. A new value `'tf_grid'` means:
"TF selected this coin, but GRID manages the position."

### What `tf_grid` ENABLES:
- **Greed decay** — per-lot sells at decaying TP thresholds (the profit engine)
- **Profit Lock** — force-enabled regardless of `tf_profit_lock_enabled` setting.
  When net PnL (realized + unrealized) reaches `tf_profit_lock_pct` of
  `capital_allocation`, liquidate all lots, free the tier slot.
- **Buy-the-dip** — normal percentage-mode grid buying on dips
- **stop_buy_drawdown** — still active (prevents buying into a freefall)

### What `tf_grid` DISABLES:
- **Stop-loss** (`tf_stop_loss_pct`) — NO. This is the whole point.
- **BEARISH forced liquidation** — NO. Signal changes don't trigger exit.
- **Trailing stop** — NO. This is a TF exit mechanism.
- **Take-profit** (`tf_take_profit_pct`) — NO. Superseded by Profit Lock.
- **Gain saturation** (`exit_after_n`) — NO. GRID is patient, let it run.
- **SWAP** — NO. You don't swap a GRID position that's building.

### Mental model:
`tf_grid` behaves like a manual bot (BTC/SOL/BONK) **plus** Profit Lock
as the only automatic exit. TF chose the coin; GRID does the work;
Profit Lock books the gains.

---

## File changes

### 1. `bot/strategies/grid_bot.py` — behavior gates

All the TF safety features currently gate on `self.managed_by == "trend_follower"`.
We need to update these gates so `tf_grid` gets GRID behavior, not TF behavior.

#### 1a. Stop-loss check

Find the stop-loss trigger block (the one that sets `self._stop_loss_triggered`).
It currently checks `self.managed_by == "trend_follower"`. **No change needed** —
`tf_grid` is not `trend_follower`, so stop-loss is already disabled. ✅

#### 1b. Trailing stop check

Find the trailing stop block (sets `self._trailing_stop_triggered`).
Same gate: `self.managed_by == "trend_follower"`. Already disabled for tf_grid. ✅

#### 1c. Take-profit check

Find the take-profit block (sets `self._take_profit_triggered`).
Same gate. Already disabled for tf_grid. ✅

#### 1d. Gain saturation (`evaluate_gain_saturation`)

Find `evaluate_gain_saturation`. It gates on `self.managed_by == "trend_follower"`.
Already disabled for tf_grid. ✅

#### 1e. Profit Lock check — MUST CHANGE

Find the profit lock block. Currently:

```python
if (self.managed_by == "trend_follower"
        and self.tf_profit_lock_enabled
        and ...):
```

Change to:

```python
if (self.managed_by in ("trend_follower", "tf_grid")
        and (self.tf_profit_lock_enabled or self.managed_by == "tf_grid")
        and ...):
```

This means:
- For `trend_follower`: respects `tf_profit_lock_enabled` (opt-in as today)
- For `tf_grid`: **always enabled** regardless of the global toggle

#### 1f. Greed decay — MUST CHANGE

Find `get_effective_tp()`. It currently applies greed decay only for
`self.managed_by == "trend_follower"`. Change the gate:

```python
if self.managed_by in ("trend_follower", "tf_grid"):
    # greed decay logic
```

This is critical — greed decay is how individual lots exit profitably
in a GRID. Without it, tf_grid lots would use `sell_pct` which is less
sophisticated.

#### 1g. Force liquidation cascade — MUST CHANGE

Find the `force_liquidate` check:

```python
force_liquidate = (
    self.managed_by == "trend_follower"
    and (self._stop_loss_triggered
         or self._trailing_stop_triggered
         or self._take_profit_triggered
         or self._profit_lock_triggered
         or self._gain_saturation_triggered
         or self.pending_liquidation)
)
```

Change to:

```python
force_liquidate = (
    self.managed_by in ("trend_follower", "tf_grid")
    and (self._stop_loss_triggered
         or self._trailing_stop_triggered
         or self._take_profit_triggered
         or self._profit_lock_triggered
         or self._gain_saturation_triggered
         or self.pending_liquidation)
)
```

For tf_grid, the only triggers that can actually fire are
`_profit_lock_triggered` and `pending_liquidation` (manual exit).
The others are disabled by their own gates (1a-1d). But we need
the cascade mechanism to work when profit lock DOES fire.

#### 1h. cycle_closed pending_liquidation flag

Find the `cycle_closed` block that sets `self.pending_liquidation = True`
after a forced liquidation completes. It currently checks:

```python
if ((self._stop_loss_triggered
     or self._trailing_stop_triggered
     or ...
```

Same logic — these flags are already correctly gated. Only profit_lock
and pending_liquidation can fire for tf_grid, so this block only
activates in those cases. **No change needed.** ✅

---

### 2. `bot/trend_follower/allocator.py` — set managed_by per tier

Find `apply_allocations()`. Where it builds the `row` dict for ALLOCATE:

```python
row = {
    "symbol": symbol,
    "is_active": True,
    "managed_by": "trend_follower",
    ...
}
```

Change to:

```python
# Determine management mode by volume tier
volume_tier = d.get("volume_tier") or d.get("config_snapshot", {}).get("volume_tier")
if volume_tier is not None:
    volume_tier = int(volume_tier)

if volume_tier in (1, 2):
    mgmt_mode = "tf_grid"
else:
    mgmt_mode = "trend_follower"

row = {
    "symbol": symbol,
    "is_active": True,
    "managed_by": mgmt_mode,
    ...
}
```

Also make sure `volume_tier` is included in the `config_snapshot` and
`row_fields` so it's written to `bot_config`. Check that brief 45c
already does this — if not, add `"volume_tier": volume_tier` to the row.

**IMPORTANT:** log the management mode clearly:

```python
logger.info(
    f"[ALLOCATOR] Tier {volume_tier} ALLOCATE {symbol} "
    f"managed_by={mgmt_mode} ..."
)
```

---

### 3. `bot/trend_follower/allocator.py` — disable SWAP for tf_grid

Find the SWAP evaluation section. Before the strength-delta comparison,
after the existing same-tier guard (45c), add:

```python
# tf_grid coins are never swapped — GRID positions build over time.
# Only trend_follower (Tier 3) coins are eligible for SWAP.
active_managed_by = alloc.get("managed_by", "trend_follower")
if active_managed_by == "tf_grid":
    logger.debug(
        f"[ALLOCATOR] SWAP skip {sym}: managed_by=tf_grid, "
        f"GRID positions are not swappable"
    )
    continue
```

---

### 4. `bot/trend_follower/trend_follower.py` — skip BEARISH exit for tf_grid

Find where the TF main loop handles BEARISH/DEALLOCATE signals for active
coins. There's a section that sets `pending_liquidation = True` when the
signal flips to BEARISH. Add a guard:

```python
# tf_grid coins ignore signal changes — GRID manages regardless of
# BULLISH/BEARISH. Only Profit Lock or manual exit can close them.
if active_config.get("managed_by") == "tf_grid":
    logger.info(
        f"[TF] {symbol} signal is {signal} but managed_by=tf_grid — "
        f"ignoring signal change, GRID manages independently"
    )
    continue  # or skip the DEALLOCATE logic
```

This is the second most important change after the stop-loss disable.
Without this, TF would still force-liquidate tf_grid coins on BEARISH.

---

### 5. `bot/grid_runner.py` — hot-reload behavior for tf_grid

Find `_sync_config_to_bot()`. The section that hot-reloads TF safety
params currently gates on:

```python
if bot.managed_by == "trend_follower":
```

Change to:

```python
if bot.managed_by in ("trend_follower", "tf_grid"):
```

This ensures tf_grid bots also receive hot-reloaded params from
`trend_config` (greed_decay_tiers, profit_lock_pct, etc.).

Also find the `_force_liquidate` / pending_liquidation handler section
in the main loop. The event_label logic already handles multiple
trigger types. For tf_grid, the only triggers are profit_lock and
pending_liquidation (manual). The existing code handles this correctly
because the label selection is based on which flag is set. **No change
needed** in the label logic. ✅

BUT: find where the DEALLOCATE row is written to `trend_decisions_log`
after liquidation. Make sure the reason string reflects tf_grid:

```python
if bot.managed_by == "tf_grid":
    dealloc_reason = f"PROFIT-LOCK EXIT (tf_grid): {event_label}"
else:
    dealloc_reason = f"{event_label}: ..."
```

---

### 6. `bot/grid_runner.py` — initial_lots for tf_grid

Find `_consume_initial_lots()`. This fires on first cycle after ALLOCATE
to do multi-lot market entry. Currently gates on managed_by == "trend_follower".

Change to:

```python
if bot.managed_by in ("trend_follower", "tf_grid"):
```

tf_grid coins need the same initial burst entry as TF coins.

---

### 7. Dashboard — `web/tf.html` + `web2/tf.html`

tf_grid coins should appear in the TF dashboard (they're TF-selected),
but with a visual distinction.

In the bot card renderer, add a badge or tag:

```javascript
// After the symbol name
if (bot.managed_by === 'tf_grid') {
    html += '<span style="background:#2ecc71;color:#fff;padding:2px 6px;'
         +  'border-radius:4px;font-size:11px;margin-left:6px;">GRID</span>';
}
```

The existing TF dashboard query fetches `managed_by=eq.trend_follower`.
Change to fetch both:

```javascript
// Old:
sbGet('bot_config', 'managed_by=eq.trend_follower&order=symbol')

// New:
sbGet('bot_config', 'managed_by=in.(trend_follower,tf_grid)&order=symbol')
```

Do the same for the trades query on the TF dashboard:

```javascript
sbGet('trades', '...&managed_by=in.(trend_follower,tf_grid)&...')
```

---

### 8. Dashboard — `web/admin.html` + `web2/admin.html`

Admin dashboard already filters `managed_by=neq.trend_follower`. Update
to also exclude tf_grid:

```javascript
// Old:
sbGet('bot_config', 'managed_by=neq.trend_follower&order=symbol')

// New:
sbGet('bot_config', 'managed_by=not.in.(trend_follower,tf_grid)&order=symbol')
```

Same for the trades query in admin.

---

### 9. Telegram report — `bot/trend_follower/trend_follower.py`

In the scan report, show the management mode for active allocations.
Find where active allocations are displayed and add:

```python
mode_tag = "🟢 GRID" if alloc.get("managed_by") == "tf_grid" else "🔵 TF"
# Include in the active allocation line
```

---

## NO DB migration needed

All required columns already exist:
- `bot_config.managed_by` — text, already supports arbitrary values
- `bot_config.volume_tier` — smallint, already populated by 45c
- `trend_config.tf_profit_lock_enabled` — already exists (default false)
- `trend_config.tf_profit_lock_pct` — already exists (default 5)

The only "new" thing is the string value `'tf_grid'` in `managed_by`,
which requires no schema change.

---

## Test checklist

### Core behavior: tf_grid disables TF exits

- [ ] Allocate a Tier 2 coin → `managed_by` is `tf_grid` in bot_config
- [ ] Allocate a Tier 3 coin → `managed_by` is `trend_follower`
- [ ] tf_grid coin: price drops 5% → **NO stop-loss fires**
- [ ] tf_grid coin: signal flips BEARISH → **NO forced liquidation**
- [ ] tf_grid coin: trailing stop conditions met → **NO trailing stop fires**
- [ ] tf_grid coin: take-profit conditions met → **NO take-profit fires**
- [ ] tf_grid coin: gain saturation (N sells) reached → **NO exit**
- [ ] Tier 3 coin: all the above still fire normally (regression check)

### Core behavior: tf_grid enables GRID features

- [ ] tf_grid coin: greed decay sells lots at decaying thresholds ✓
- [ ] tf_grid coin: buys dips at buy_pct intervals ✓
- [ ] tf_grid coin: stop_buy_drawdown blocks buys during freefall ✓
- [ ] tf_grid coin: initial_lots fires on first cycle ✓

### Profit Lock exit

- [ ] tf_grid coin: net PnL reaches +5% → Profit Lock fires
- [ ] Profit Lock fires even when `tf_profit_lock_enabled = false` (force-enabled for tf_grid)
- [ ] After Profit Lock: all lots liquidated, pending_liquidation set
- [ ] After Profit Lock: DEALLOCATE row written to trend_decisions_log
- [ ] After Profit Lock: tier slot is freed, next scan can allocate new coin
- [ ] Telegram alert shows "🔒 Profit Lock" with correct PnL

### SWAP protection

- [ ] Active tf_grid coin with strength 20 → new Tier 2 candidate with strength 50 → **NO SWAP**
- [ ] Active Tier 3 (trend_follower) coin → SWAP still works as before

### BEARISH immunity

- [ ] tf_grid coin: signal goes BEARISH → bot keeps running, keeps buying dips
- [ ] tf_grid coin: signal goes BEARISH → TF log says "ignoring signal, tf_grid"
- [ ] Tier 3 coin: signal goes BEARISH → forced liquidation fires as before

### Dashboard

- [ ] TF dashboard shows tf_grid coins with "GRID" badge
- [ ] TF dashboard shows both tf_grid and trend_follower coins
- [ ] Admin dashboard does NOT show tf_grid coins
- [ ] Telegram scan report shows 🟢 GRID / 🔵 TF tags on active allocations

### Manual exit

- [ ] Set pending_liquidation=true on a tf_grid coin via dashboard
- [ ] Bot liquidates all lots and exits cleanly
- [ ] Tier slot is freed

---

## Scope rules

- **DO NOT** change stop-loss / trailing / greed decay logic itself — only change the gates (which managed_by values activate them)
- **DO NOT** touch manual bots (BTC/SOL/BONK) — they remain managed_by='manual'
- **DO NOT** change Profit Lock calculation logic — only change when it's enabled
- **DO NOT** change Tier 3 behavior — trend_follower management is unchanged
- **DO NOT** redistribute budget between tiers — existing 45c logic stays
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(tf): Tier 1-2 handoff to GRID management (tf_grid)

TF-selected Tier 1-2 coins (≥$20M volume) now get managed_by='tf_grid'
instead of 'trend_follower'. This disables:
  - Stop-loss (no panic exits on dips)
  - BEARISH forced liquidation (signal changes ignored)
  - Trailing stop, take-profit, gain saturation

And enables:
  - GRID-style patient management (buy dips, greed decay sells)
  - Profit Lock as the ONLY automatic exit (force-enabled for tf_grid)

Tier 3 (<$20M volume) remains managed_by='trend_follower' — unchanged.

Data-driven: SPK lost $2.37 on a +70% coin, ORCA lost $1.43 on a +17%
coin — both due to stop-loss cascades that GRID would have avoided.
```

---

## Summary for the Board

TF è bravo a trovare le monete giuste. È pessimo a gestirle. Questa
modifica separa le due funzioni: TF sceglie, GRID gestisce. Per le
monete Tier 1-2 (liquidità reale, basso rischio di flash crash totale),
GRID compra i dip con pazienza e vende ai target con greed decay.
L'unica uscita automatica è il Profit Lock: quando il guadagno netto
raggiunge +5% sull'allocazione, tutto viene liquidato e il capitale è
libero per la prossima rotazione.

Tier 3 resta in mano a TF — budget piccolo, rischio alto, rotazione
veloce. "Botta di culo" mode.
