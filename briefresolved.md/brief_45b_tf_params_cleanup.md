# INTERN BRIEF 45b — TF Parameters Cleanup (profit_target UI + sell_pct salvage)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 22, 2026
**Priority:** MEDIUM — removes two footguns in the TF/dashboard interface

---

## Context

The audit from session 45 surfaced two mismatches between what the admin
dashboard **appears to let Max edit** and what the Trend Follower
**actually writes** on every ALLOCATE. Both only affect TF-managed bots
— the 3 manual bots (BTC/SOL/BONK) are untouched.

### Problem A — `profit_target_pct` looks editable but is a no-op on TF

On admin.html the "Min Profit %" field is rendered for every bot. For
manual bots it works as advertised (blocks sells below a % margin over
avg_buy, enforced in `_execute_sell` at grid_bot.py:616-623). For TF
bots, the allocator **hardcodes it to `0` on every ALLOCATE**
(allocator.py, in the config snapshot written to `bot_config`). Reason:
the TF stack already manages the sell floor via `greed_decay_tiers` +
`tf_stop_loss_pct` + `tf_take_profit_pct`. Leaving `profit_target_pct`
active on a TF bot would create a deadlock with greed decay (e.g. tier
says "sell at +2%", filter says "block unless +3%" → bot never sells).

The code is correct. The UX is a lie: Max can type 1.5 into the field
for a TF bot, press Save, and nothing happens at the next ALLOCATE.

### Problem B — `sell_pct` is the "post-greed-decay salvage" but TF overwrites it with ATR

On a TF bot, `sell_pct` is **NOT** the normal sell trigger — the greed
decay tier owns that decision. `sell_pct` only matters at one moment:
after the bot has outlived the highest-minutes tier of `greed_decay_tiers`,
`get_effective_tp()` at grid_bot.py:1157 falls back to `sell_pct` as a
final floor. The CEO introduced this as an **editable per-coin salvage
threshold** (2026-04-20 evening decision, replacing the old 999999-minute
placeholder tier).

But allocator.py `_adaptive_steps()` computes `sell_pct = clamp(ATR/price * 1.2, 1.0, 6.0)`
and writes it on every ALLOCATE. So the CEO's "editable salvage" is
overwritten every time TF rotates. The field on admin.html that looks
editable... gets clobbered on the next allocate.

Worse: the value TF writes (1.0–6.0%) is often **higher** than the last
greed decay tier (typically 1.0%). That means once greed decay runs out,
the bot jumps to a **wider** sell threshold than the last tier — the
opposite of the "gets less greedy over time" philosophy.

---

## Solution

### Fix A — UX honesty for `profit_target_pct` on TF bots

Purely cosmetic change to `web/admin.html`. When a bot row is rendered
with `managed_by === 'trend_follower'`:

- The `profit_target_pct` input stays visible (so Max sees the column
  is there), but add a small label next to the input with text
  **"see greed decay"** (or "gestito da greed decay", Max's choice —
  default to the English version to match the other helper text
  conventions in admin.html).
- Optionally dim the field (e.g. `opacity: 0.6` or a muted colour) so
  it reads as "informational, not interactive". Keep it editable — if
  Max types something, the save still patches `bot_config`, but it
  will be clobbered on the next TF ALLOCATE. That's the point of the
  label.

Manual bots render exactly as today — no label, no dimming, field is
fully meaningful.

**No backend change.** This is a pure admin.html UI tweak.

### Fix B — `sell_pct` as a deterministic post-greed-decay salvage

On TF ALLOCATE, replace the ATR-based `sell_pct` with a value
**derived from `greed_decay_tiers`**:

```python
sell_pct = max(last_tier_tp_pct - 0.5, 0.3)
```

Where:
- `last_tier_tp_pct` = the `tp_pct` of the greed decay tier with the
  **highest `minutes` value** (i.e. the tier that holds after all others
  have elapsed). Sort tiers ascending by `minutes` and take the last.
- `0.5` = the delta below the last tier (constant for now; future
  iteration could promote to trend_config if Max wants to tune)
- `0.3` = the hard floor — `sell_pct` must never go below this, even
  if the last tier is already very low. Prevents accidental "sell at
  breakeven" or "sell at a loss" salvage thresholds.

Examples:
| Last tier tp_pct | Computed sell_pct |
|------------------|-------------------|
| 1.0 | max(0.5, 0.3) = **0.5** |
| 0.8 | max(0.3, 0.3) = **0.3** |
| 0.7 | max(0.2, 0.3) = **0.3** |
| 0.6 | max(0.1, 0.3) = **0.3** |
| 5.0 | max(4.5, 0.3) = **4.5** |

**`buy_pct` is NOT changed** — it remains ATR-adaptive
(`clamp(ATR/price * 0.8, 1.0, 2.0)`). `buy_pct` governs buy cadence
only, it doesn't interact with greed decay or SL, so the ATR logic
still fits.

**Manual bots are untouched.** `allocator.py` never touches
`MANUAL_WHITELIST` symbols, and manual bots read `sell_pct` directly
from `bot_config` (editable via admin.html). BTC/SOL/BONK continue
with their current `sell_pct=1.0` (from config/settings.py) or
whatever Max sets via the dashboard.

---

## Implementation

### `bot/trend_follower/allocator.py`

1. **Add a helper near `_adaptive_steps`** (around allocator.py:167):

```python
# 45b: post-greed-decay salvage threshold.
# Delta below the last greed tier + hard floor. Kept as module
# constants for now; promote to trend_config later if Max wants
# to tune them from the dashboard.
SALVAGE_DELTA_PCT = 0.5
SALVAGE_FLOOR_PCT = 0.3


def _compute_sell_pct_salvage(greed_decay_tiers) -> float:
    """
    45b: deterministic sell_pct for TF bots, used only as the post-
    greed-decay salvage floor (see grid_bot.py:get_effective_tp).
    Returns max(last_tier_tp - SALVAGE_DELTA_PCT, SALVAGE_FLOOR_PCT).

    On malformed / empty tiers, falls back to SALVAGE_FLOOR_PCT so the
    salvage is always active and never negative / zero.
    """
    try:
        tiers = sorted(
            (t for t in (greed_decay_tiers or [])
             if isinstance(t, dict)
             and "minutes" in t and "tp_pct" in t),
            key=lambda t: float(t["minutes"]),
        )
    except Exception:
        return SALVAGE_FLOOR_PCT
    if not tiers:
        return SALVAGE_FLOOR_PCT
    try:
        last_tp = float(tiers[-1]["tp_pct"])
    except Exception:
        return SALVAGE_FLOOR_PCT
    return max(last_tp - SALVAGE_DELTA_PCT, SALVAGE_FLOOR_PCT)
```

2. **Modify the call site in the ALLOCATE config snapshot** (search for
   where `_adaptive_steps(coin, signal)` is called and its result is
   written into the dict that becomes the `bot_config` row).

   Currently roughly:
   ```python
   buy_pct, sell_pct = _adaptive_steps(coin, coin["signal"])
   row_fields = {
       ...
       "buy_pct": buy_pct,
       "sell_pct": sell_pct,
       ...
   }
   ```

   Change to:
   ```python
   buy_pct, _atr_sell_pct = _adaptive_steps(coin, coin["signal"])
   sell_pct_salvage = _compute_sell_pct_salvage(config.get("greed_decay_tiers"))
   row_fields = {
       ...
       "buy_pct": buy_pct,
       "sell_pct": sell_pct_salvage,  # 45b: post-greed-decay salvage, not ATR-derived
       ...
   }
   ```

   The ATR-derived `sell_pct` is intentionally discarded — keeping the
   unpack for backwards-compat with `_adaptive_steps` signature, but the
   value is no longer written anywhere.

3. **Same change in the re-ALLOCATE / UPDATE path** (re-used dict when
   a row already exists in `bot_config` — this is the `updated_at`
   branch). Apply the same `sell_pct_salvage` there.

4. **Do NOT change `_adaptive_steps` itself.** Keep it as-is; it's only
   the caller that drops the sell_pct output. Future iterations could
   decouple it, but scope this brief tightly.

5. **Add a one-line comment at the top of `_adaptive_steps`** noting
   that `sell_pct` from this function is **no longer used as of 45b**,
   to avoid the next reader wondering why the output is unpacked and
   discarded.

### `web/admin.html`

1. **Render the "see greed decay" label next to `profit_target_pct`**
   ONLY when `bot.managed_by === 'trend_follower'`.

   Preferred approach: in the row template that emits the Min Profit %
   input (around admin.html:820), append a small `<span>` with a CSS
   class like `tf-managed-hint` that is conditionally rendered based
   on the bot's `managed_by`. Minimal styling — same grey as other
   helper text — no border, no background, just:

   ```html
   <span class="tf-managed-hint">↑ see greed decay</span>
   ```

   or similar. The label does not need to be localised — the rest of
   admin.html is in English helper text, stay consistent.

2. Optionally dim the input itself for TF bots (`opacity: 0.55` via
   same conditional class), so the visual hierarchy reads "this value
   is informational". Keep the input `enabled` — do NOT disable it.
   If Max types into it and saves, the PATCH goes through; the TF
   will clobber it on the next ALLOCATE, which is the intended lesson.

3. **No change to other fields on TF bots in this brief.** The full
   UI honesty pass for buy_pct, sell_pct, skim_pct etc. is out of
   scope — pick one problem at a time.

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/allocator.py` | MODIFY | Add `_compute_sell_pct_salvage` helper + `SALVAGE_DELTA_PCT` / `SALVAGE_FLOOR_PCT` constants; use it in ALLOCATE and re-ALLOCATE paths in place of ATR-derived sell_pct |
| `web/admin.html` | MODIFY | Conditional "see greed decay" label + dimmed styling next to `profit_target_pct` for TF-managed bots only |

## Files NOT to touch

- `bot/strategies/grid_bot.py` — no behaviour change; `get_effective_tp()`
  already handles the salvage correctly once `sell_pct` is populated
- `bot/grid_runner.py` — no config wiring changes
- `web/tf.html` — no new fields (keep the brief small; delta/floor stay
  as module constants for now)
- `config/settings.py` — manual bot config unchanged
- DB schema — no migrations needed in this brief
- Manual bots (BTC/SOL/BONK) — allocator.py never touches these; they
  continue to read `sell_pct` from `bot_config` / `GridInstanceConfig`

---

## Test checklist

### Fix A — UX
- [ ] Open admin.html. For a manual bot (BTC): the `profit_target_pct`
      input renders exactly as before — no hint label, no dimming.
- [ ] For a TF bot (any currently allocated): the `profit_target_pct`
      input renders with the "see greed decay" hint and dimmed styling.
- [ ] Typing a value into the TF bot's input and saving still works
      (PATCH goes through, value shows up in DB). Confirm the label
      does not block the save flow.
- [ ] On the next TF ALLOCATE (or a manual re-run of the allocator),
      the value gets clobbered back to `0`. Expected behaviour.

### Fix B — sell_pct salvage
- [ ] Trigger a TF ALLOCATE (either wait for the next scan or run the
      orchestrator with a forced-rotation test). With current greed
      decay `[5, 3, 2, 1.5, 1]` (last tier = 1.0%), confirm the new
      allocation writes `sell_pct = 0.5` in `bot_config`.
- [ ] Change greed decay so the last tier is `0.7%`. Trigger another
      ALLOCATE. Confirm `sell_pct = 0.3` (hit the floor).
- [ ] Change last tier to `5.0%` (unusual but valid). Trigger ALLOCATE.
      Confirm `sell_pct = 4.5`.
- [ ] Empty / malformed greed_decay_tiers → `sell_pct = 0.3` (floor).
      This case shouldn't happen in production but must not crash.
- [ ] `buy_pct` still reflects ATR adaptive logic — unchanged from
      pre-45b behaviour. Confirm the same coin now allocated gets the
      same buy_pct as it would have before this change.

### Regression — manual bots
- [ ] BTC/SOL/BONK `sell_pct` values in `bot_config` are unchanged
      after deploying 45b (should still be 1.0 each, or whatever Max
      has set via dashboard).
- [ ] Manual bots' sell behaviour unchanged: a sell fires when price
      crosses `avg_buy_price * (1 + sell_pct/100)` and respects
      `profit_target_pct` if set.

### Regression — TF behaviour pre- and post-greed-decay
- [ ] A TF coin within its active greed decay window: sells still
      trigger at the tier's `tp_pct` (unchanged — greed decay owns
      the decision, sell_pct is irrelevant until post-last-tier).
- [ ] A TF coin past the last greed decay tier: sells trigger at
      `sell_pct` (i.e. the new salvage value). Pre-45b this was the
      ATR-derived value; post-45b it's `max(last_tier - 0.5, 0.3)`.

---

## Scope rules

- **DO NOT** change `buy_pct` logic
- **DO NOT** change `_adaptive_steps` — only its caller discards the sell_pct output
- **DO NOT** touch manual bots or their config paths
- **DO NOT** add new `trend_config` fields for SALVAGE_DELTA_PCT /
  SALVAGE_FLOOR_PCT — keep them as module constants. Future brief
  can promote them to editable.
- **DO NOT** redesign the admin.html TF-bot view wholesale — this
  brief fixes only the `profit_target_pct` label. The broader UI
  honesty pass for buy_pct / sell_pct / skim_pct / grid_mode is a
  separate future brief.
- Push to GitHub when done
- Stop when tasks are complete

---

## Commit format

```
feat(tf): deterministic sell_pct salvage + profit_target_pct UI label (45b)

Replaces the ATR-derived sell_pct written by the TF allocator with a
value deterministically derived from greed_decay_tiers:
  sell_pct = max(last_tier_tp_pct - 0.5, 0.3)

This restores the CEO's intent for sell_pct on TF bots: a post-greed-
decay salvage threshold that follows the "less greedy over time"
philosophy instead of jumping back up to whatever ATR*1.2 produces.
buy_pct remains ATR-adaptive — only sell_pct changes.

Also adds a "see greed decay" hint + dimmed styling next to the
profit_target_pct input in admin.html for TF-managed bots, making the
UX honest: TF always clobbers this field to 0 on ALLOCATE, so Max now
knows the field is informational on TF bots (stays fully functional
on manual bots).

Manual bots (BTC/SOL/BONK) untouched — allocator never sees them.
```
