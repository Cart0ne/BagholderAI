# INTERN BRIEF — Session 51b: Trailing Stop (Protect Unrealized Gains)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 51 — April 29, 2026
**Priority:** HIGH — active capital protection
**Prerequisite:** None (standalone, can be deployed independently of 51a)

---

## Context

The grid runner currently has two exit modes for TF bots:

1. **Greed decay sell** — per-lot, "I've earned enough on this lot"
2. **Stop-loss** — total position, "I'm losing too much, sell everything"

Missing: **"I was winning, now I'm losing the winnings — exit before they
become losses."**

On April 29, DOGE/USDT was re-allocated at 10:35 UTC. The price rose to
$0.11 (30-day high), then crashed. The bot kept buying the dip (grid
logic) while the price fell, and eventually hit stop-loss at $0.1039.

With a trailing stop: the bot would have tracked the peak at $0.11,
and when the price dropped 2% from peak to ~$0.1078, it would have
sold everything. The 3 extra buys during the decline (12:03, 13:35)
would never have happened.

**Estimated savings on this single trade: ~$0.69.**

---

## How it works

A trailing stop tracks the highest price seen since the bot started on
a coin. It activates only after the position has reached a minimum
profit, then triggers if the price drops a configurable percentage from
the peak.

```
peak_price = highest price seen since bot started on this coin
activation = avg_buy_price * (1 + activation_pct / 100)

IF peak_price >= activation (position has been in profit):
  trailing_trigger = peak_price * (1 - trailing_pct / 100)
  IF current_price <= trailing_trigger:
    → SELL ALL (trailing stop)
```

**Why the activation threshold?** Without it, any micro-dip from the
first buy price would trigger an exit. The bot needs room to breathe.
"Activate trailing only after seeing at least +1.5% profit from avg buy"
means: the position must have been meaningfully in the green before we
start protecting those gains.

---

## DB migration

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_trailing_stop_activation_pct numeric DEFAULT 1.5,
  ADD COLUMN tf_trailing_stop_pct numeric DEFAULT 2.0;
```

- `tf_trailing_stop_activation_pct`: minimum profit (as % of avg_buy)
  the peak must reach before trailing engages. Default 1.5%.
  `0` = trailing activates immediately (aggressive).
- `tf_trailing_stop_pct`: how far price can drop from peak before
  triggering. Default 2.0%.
  `0` = feature entirely disabled (kill-switch).

---

## 1. GridBot changes — `bot/strategies/grid_bot.py`

### New attributes

In `__init__` or wherever config is loaded (same pattern as
`tf_stop_loss_pct`, `tf_take_profit_pct`, etc.):

```python
self.tf_trailing_stop_activation_pct = float(cfg.get('tf_trailing_stop_activation_pct', 1.5))
self.tf_trailing_stop_pct = float(cfg.get('tf_trailing_stop_pct', 2.0))
self._trailing_peak_price = 0.0
self._trailing_stop_triggered = False
```

### Peak tracking

In `_check_percentage_and_execute`, at the very TOP (before any sell/buy
checks), update the peak tracker:

```python
# 51b: trailing stop — track peak price every tick
if (self.managed_by == "trend_follower"
    and self.tf_trailing_stop_pct > 0
    and self.state.holdings > 0):
    if current_price > self._trailing_peak_price:
        self._trailing_peak_price = current_price
```

### Trailing stop check

Add AFTER the peak tracking and AFTER the stop-loss check (39a),
but BEFORE the take-profit check (39c). Order matters: stop-loss is
the emergency exit (big loss), trailing stop is the "protect gains"
exit, take-profit is the "enough profit, cash out" exit.

```python
# 51b: trailing stop — exit when losing unrealized gains
if (self.managed_by == "trend_follower"
    and self.tf_trailing_stop_pct > 0
    and not self._stop_loss_triggered
    and not self._trailing_stop_triggered
    and self.state.holdings > 0
    and self.state.avg_buy_price > 0
    and self._trailing_peak_price > 0):

    activation_price = self.state.avg_buy_price * (1 + self.tf_trailing_stop_activation_pct / 100)

    if self._trailing_peak_price >= activation_price:
        trailing_trigger = self._trailing_peak_price * (1 - self.tf_trailing_stop_pct / 100)

        if current_price <= trailing_trigger:
            drop_from_peak = ((self._trailing_peak_price - current_price) / self._trailing_peak_price) * 100
            unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings

            logger.warning(
                f"[{self.symbol}] TRAILING STOP TRIGGERED: price {fmt_price(current_price)} "
                f"dropped {drop_from_peak:.1f}% from peak {fmt_price(self._trailing_peak_price)} "
                f"(trigger: {fmt_price(trailing_trigger)}). "
                f"Unrealized: ${unrealized:+.2f}"
            )
            self._trailing_stop_triggered = True

            # Force sell ALL lots — same pattern as stop-loss
            for lot in list(self._pct_open_positions):
                trade = self._execute_percentage_sell(current_price)
                if trade:
                    trades.append(trade)

            log_event(
                severity="warn",
                category="safety",
                event="trailing_stop_triggered",
                symbol=self.symbol,
                message=(
                    f"TF trailing stop: price dropped {drop_from_peak:.1f}% from "
                    f"peak {fmt_price(self._trailing_peak_price)}"
                ),
                details={
                    "peak_price": self._trailing_peak_price,
                    "trigger_price": trailing_trigger,
                    "current_price": float(current_price),
                    "avg_buy_price": float(self.state.avg_buy_price),
                    "drop_from_peak_pct": round(drop_from_peak, 2),
                    "unrealized": unrealized,
                    "activation_pct": self.tf_trailing_stop_activation_pct,
                    "trailing_pct": self.tf_trailing_stop_pct,
                    "lots": len(self._pct_open_positions),
                },
            )
```

### Strategy A override

The trailing stop may sell lots at a loss (if avg_buy of a specific lot
is above current_price, even though the overall position was once in
profit). The existing `_execute_percentage_sell` blocks sells below lot
buy price for Strategy A — UNLESS an override flag is set.

Add `_trailing_stop_triggered` to the override check, same block where
`_stop_loss_triggered` and `pending_liquidation` are checked:

```python
# In _execute_percentage_sell, the Strategy A block:
if self.strategy == "A" and price < lot_buy_price:
    if self.managed_by == "trend_follower" and self._stop_loss_triggered:
        logger.warning(f"STOP-LOSS OVERRIDE: ...")
    elif self.managed_by == "trend_follower" and self._trailing_stop_triggered:
        logger.warning(
            f"TRAILING-STOP OVERRIDE: Selling {self.symbol} at {fmt_price(price)} "
            f"< lot buy {fmt_price(lot_buy_price)}. "
            f"Price dropped from peak {fmt_price(self._trailing_peak_price)}."
        )
    elif self.managed_by == "trend_follower" and self.pending_liquidation:
        logger.warning(f"BEARISH EXIT OVERRIDE: ...")
    else:
        logger.info(f"BLOCKED: ...")
        return None
```

### Force-liquidation flag

After the trailing stop sells all lots, `pending_liquidation` needs to
be set so the grid_runner closes the bot properly. This is handled by
the existing logic in `_check_percentage_and_execute`:

```python
# After the sell loop, the existing code checks if holdings are empty
# and sets pending_liquidation. The trailing stop sells reduce holdings
# to 0 (or dust), which triggers the existing cycle_closed path.
```

**Verify** that the existing `pending_liquidation` logic after the sell
loop also recognises `_trailing_stop_triggered` as a forced exit. In the
grid_runner, the `pending_liquidation` handler already checks multiple
flags — add `_trailing_stop_triggered`:

In `grid_runner.py`, in the block where `event_label` and
`stop_reason_tag` are assigned (the `if getattr(bot, ...)` chain):

```python
is_ts = getattr(bot, "_trailing_stop_triggered", False)
# Insert BEFORE the stop-loss check so trailing has its own label
if is_gs:
    event_label = "GAIN-SATURATION"
    stop_reason_tag = "gain_saturation"
elif is_pl:
    event_label = "PROFIT-LOCK"
    stop_reason_tag = "profit_lock"
elif is_tp:
    event_label = "TAKE-PROFIT"
    stop_reason_tag = "take_profit"
elif is_ts:
    event_label = "TRAILING-STOP"
    stop_reason_tag = "trailing_stop"
else:
    event_label = "STOP-LOSS"
    stop_reason_tag = "stop_loss"
```

### SL cooldown after trailing stop

A trailing stop exit should trigger the same SL cooldown as a stop-loss,
preventing immediate re-entry on the same coin. The existing code in
grid_bot.py writes `last_stop_loss_at` for stop-loss and profit-lock
triggers. Add the same write for trailing stop:

```python
# After the trailing stop log_event, add:
if self.trade_logger is not None:
    try:
        self.trade_logger.client.table("bot_config").update(
            {"last_stop_loss_at": datetime.now(timezone.utc).isoformat()}
        ).eq("symbol", self.symbol).execute()
    except Exception as e:
        logger.error(
            f"[{self.symbol}] Failed to write last_stop_loss_at (trailing stop): {e}"
        )
```

### Boot: _trailing_peak_price reconstruction

At boot, `_trailing_peak_price` starts at 0. The first tick updates it
to current_price. This is fine — if the bot restarts mid-cycle, it
"forgets" the pre-restart peak, which is conservative (it may miss a
trailing trigger for one cycle, but won't false-trigger).

No DB persistence needed. Same pattern as `_stop_buy_active`.

---

## 2. Grid runner changes — `bot/grid_runner.py`

### Config passthrough

Where config values are read from `trend_config` and passed to GridBot
(same place as `tf_stop_loss_pct`, `tf_take_profit_pct`, etc.):

```python
'tf_trailing_stop_activation_pct': float(tc.get('tf_trailing_stop_activation_pct', 1.5)),
'tf_trailing_stop_pct': float(tc.get('tf_trailing_stop_pct', 2.0)),
```

### Event label (see section 1 above)

Add `_trailing_stop_triggered` to the flag check chain. See code above.

---

## 3. Dashboard update — `web/tf.html`

Add to `TF_SAFETY_FIELDS`:

```javascript
{
  key: 'tf_trailing_stop_activation_pct',
  label: 'Trailing stop activation (%)',
  sub: '51b: Trailing stop engages only after peak price ≥ avg_buy × (1 + X%). Prevents premature exit on micro-dips. Default 1.5%. Set 0 to activate immediately.'
},
{
  key: 'tf_trailing_stop_pct',
  label: 'Trailing stop drop (%)',
  sub: '51b: Once active, SELL ALL if price drops X% from peak. Default 2.0%. Set 0 to disable trailing stop entirely.'
},
```

Add both columns to the trend_config SELECT query.

---

## 4. Telegram notification

The existing stop-loss Telegram notification pattern (in grid_runner's
`_force_liquidate` or the cycle summary block) will handle trailing stop
because it uses the `event_label` variable. The "TRAILING-STOP" label
will appear in the cycle close message automatically.

No additional Telegram code needed.

---

## Files to modify

| File | Action |
|------|--------|
| DB (`trend_config`) | MIGRATE: add 2 columns |
| `bot/strategies/grid_bot.py` | ADD: peak tracking, trailing stop check, Strategy A override, SL cooldown write |
| `bot/grid_runner.py` | ADD: config passthrough, event label for trailing stop |
| `web/tf.html` | ADD: 2 fields to `TF_SAFETY_FIELDS` + SELECT query |

## Files NOT to touch

- `bot/trend_follower/scanner.py` — no changes
- `bot/trend_follower/allocator.py` — no changes
- `bot/trend_follower/trend_follower.py` — no changes
- Stop-loss / greed decay / profit lock / gain saturation logic — only ADD
  trailing stop alongside them, never modify their existing behaviour
- Manual bots — `managed_by != "trend_follower"` guard ensures manual bots
  are unaffected

---

## Scope rules

- **DO NOT** persist `_trailing_peak_price` to DB — in-memory is fine
- **DO NOT** modify stop-loss logic — trailing stop is INDEPENDENT
- **DO NOT** apply trailing stop to manual bots (`managed_by` guard)
- **DO NOT** disable buy operations when trailing is active — the trailing
  check sells ALL lots when it fires, so subsequent buys don't happen
  (the bot exits after selling)
- **DO NOT** add a separate Telegram block — reuse existing cycle summary
- Push to GitHub when done
- Stop when tasks are complete

---

## Test checklist

### DB migration
- [ ] `tf_trailing_stop_activation_pct` exists, default 1.5
- [ ] `tf_trailing_stop_pct` exists, default 2.0
- [ ] RLS disabled on trend_config

### Peak tracking
- [ ] Bot starts → `_trailing_peak_price` = 0
- [ ] First tick at $100 → `_trailing_peak_price` = 100
- [ ] Price rises to $105 → `_trailing_peak_price` = 105
- [ ] Price drops to $103 → `_trailing_peak_price` stays 105

### Trailing stop logic
- [ ] avg_buy = $100, activation = 1.5%, trailing = 2%
  - Peak reaches $101 (below activation $101.50) → trailing NOT active
  - Peak reaches $102 (above activation) → trailing active
  - Price drops to $100 ($102 × 0.98 = $99.96) → trailing fires at $99.96
- [ ] avg_buy = $100, activation = 0% (immediate), trailing = 2%
  - Peak = $100.50 → trailing active immediately
  - Price drops to $98.49 → fires
- [ ] `tf_trailing_stop_pct = 0` → feature entirely disabled, no peak tracking

### Strategy A override
- [ ] Trailing stop can sell lots below their individual buy price
- [ ] Without trailing flag, Strategy A still blocks loss sells for manual bots

### Event labeling
- [ ] grid_runner shows "TRAILING-STOP" in log and Telegram
- [ ] Cycle summary includes "TRAILING-STOP" reason

### SL cooldown
- [ ] After trailing stop, `last_stop_loss_at` is written
- [ ] TF respects cooldown before re-allocating the same coin

### Interaction with other exits
- [ ] Stop-loss fires BEFORE trailing (price crashes fast) → trailing
  doesn't interfere (stop-loss already set `_stop_loss_triggered`)
- [ ] Take-profit fires if position hits TP threshold → trailing
  doesn't interfere (TP triggers first in code order)
- [ ] Gain saturation fires → trailing doesn't interfere

### Regression
- [ ] Stop-loss (39a) still works independently
- [ ] Take-profit (39c) still works
- [ ] Profit lock (45f) still works
- [ ] Gain saturation (45g/49b) still works
- [ ] Greed decay sell still works for per-lot profits
- [ ] Manual bots completely unaffected

---

## Visual example: DOGE April 29

```
Time    Price    Peak    Activation($0.1115)  Trailing trigger    Action
10:35   $0.1099  $0.1099  not reached          n/a                BUY (first)
10:50   $0.1105  $0.1105  not reached          n/a                —
11:00   $0.1100  $0.1105  not reached          n/a                —
11:10   $0.1120  $0.1120  ✓ REACHED            $0.1098            —
11:20   $0.1095  $0.1120  active               $0.1098            ⚡ TRAILING STOP
        (price $0.1095 ≤ trigger $0.1098)

Result: exit at ~$0.1095 instead of SL at $0.1039
Savings: ~$0.10 per lot × 3 lots ≈ $0.30+ saved
(Plus avoids 2 extra buys during decline = more capital preserved)
```

---

## Commit format

```
feat(grid): trailing stop — protect unrealized gains (51b)

New exit mechanism for TF bots: tracks the peak price each tick.
Once the peak exceeds avg_buy × (1 + activation_pct%), if price
drops trailing_pct% from peak → SELL ALL.

Triggered by DOGE/USDT on Apr 29: price peaked at $0.11 then
crashed to SL at $0.1039. Trailing stop would have exited at
~$0.1078 (2% below peak), saving ~$0.69.

Exit priority: stop-loss → trailing stop → take-profit → greed decay.
Strategy A override included (same pattern as SL/TP).
Writes last_stop_loss_at so SL cooldown applies post-trailing.

New columns: trend_config.tf_trailing_stop_activation_pct (default 1.5),
trend_config.tf_trailing_stop_pct (default 2.0). 0 = disabled.
```
