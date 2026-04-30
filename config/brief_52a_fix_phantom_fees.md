# Brief 52a — Fix Phantom Fee Deduction from realized_pnl

## Problem

In paper mode, fees are **informational only**. The bot calculates them (`fee = cost * 0.00075`) and records them in the `fee` column of the trades table for future reference ("this is what Binance would charge in production"). But they are never deducted from the paper portfolio:

- **Buy:** `total_invested += cost` — no fee deducted (line 700)
- **Sell:** `total_received += revenue` — no fee deducted (line 1747)
- **Cash:** `capital - total_invested + total_received - reserve` — no fee anywhere (line 169)

However, the `realized_pnl` formula **does** subtract them:

```python
realized_pnl = revenue - cost_basis - fee - buy_fee   # line 1744
```

This creates a mismatch: the paper portfolio gained $0.41 on a trade, but `realized_pnl` says $0.37 because it subtracted $0.04 of fees that were never actually paid.

**Cumulative impact on Grid manual bots: ~$7.19 of phantom losses.**

The dashboards' Total P&L happens to be correct for open positions because it uses USDT flow (`alloc - netSpent - skim`), which naturally ignores fees. But for **closed positions** and **deallocated TF coins**, the dashboards switch to a different formula that uses `realized_pnl` — and there the error shows up.

## Root cause verified

Verified on a matched BONK trade:
- Buy: 4,078,303 at $0.00000613 = $25.00, fee $0.0188
- Sell: same at $0.00000623 = $25.41, fee $0.0191
- Paper portfolio gained: $25.41 - $25.00 = **$0.408**
- DB `realized_pnl`: **$0.370** (= $0.408 - $0.038 phantom fees)
- Correct `realized_pnl`: **$0.408**

The fee ($0.038) was never deducted from cash, holdings, or anything else in the paper portfolio. It was only subtracted inside the `realized_pnl` formula.

---

## Fix Part A — Bot code (3 lines)

Remove `- fee - buy_fee` from realized_pnl. Keep `fee` calculation for the `fee` column and for `state.total_fees` tracking (informational — will matter when we go live).

### File 1: `bot/strategies/grid_bot.py` — `_execute_sell` (fixed mode)

Line 830, change:
```python
realized_pnl = revenue - cost_basis - fee - buy_fee
```
to:
```python
realized_pnl = revenue - cost_basis
```

### File 2: `bot/strategies/grid_bot.py` — `_execute_percentage_sell`

Line 1744, change:
```python
realized_pnl = revenue - cost_basis - fee - buy_fee
```
to:
```python
realized_pnl = revenue - cost_basis
```

### File 3: `bot/grid_runner.py` — `force_liquidate_position`

Line 1434, change:
```python
realized_pnl = proceeds - lot_cost_basis - sell_fee - buy_fees
```
to:
```python
realized_pnl = proceeds - lot_cost_basis
```

### What NOT to change

- Keep `fee = revenue * self.FEE_RATE` — still needed for the `fee` column in trades table
- Keep `buy_fee = cost_basis * self.FEE_RATE` — still needed for `state.total_fees`
- Keep `self.state.total_fees += fee + buy_fee` — informational tracking for when we go live
- Keep `fee` parameter in `trade_logger.log_trade(...)` calls — still recorded in DB
- Keep `FEE_RATE = 0.00075` — unchanged

### Skim impact

`skim_amount = realized_pnl * (skim_pct / 100)` — skim will be slightly higher on future trades because realized_pnl increases. On a $0.40 trade this is ~$0.009 more skim. Accepted by Max.

---

## Fix Part B — Dashboards + commentary (unified cash formula)

The current code has TWO formulas for cash:
```javascript
if (positionClosed) {
    cashLeft = alloc + realizedPnl - skimForCoin;  // USES realized_pnl (WRONG)
} else {
    cashLeft = alloc - netSpent - skimForCoin;      // USES USDT flow (CORRECT)
}
```

The USDT flow formula works for BOTH open AND closed positions:
- Open position: netSpent is positive → cash = alloc minus what's deployed
- Closed profitable position: netSpent is negative (sold > bought) → cash = alloc + profit
- Closed unprofitable: netSpent is positive → cash = alloc - loss

**Replace with a single formula everywhere. Kill the `positionClosed` branch.**

### File 4: `web/dashboard.html`

Lines 748-753. Replace:
```javascript
if (positionClosed) {
    netSpent = 0;
    cashLeft = alloc + realizedPnl - skimForCoin;
} else {
    cashLeft = alloc - netSpent - skimForCoin;
}
```
with:
```javascript
cashLeft = alloc - netSpent - skimForCoin;
```

(Remove the entire `if/else` block. `positionClosed` variable can stay — it's used elsewhere for display. Just don't use it for cash calculation.)

### File 5: `web/admin.html`

Lines 596-604. Same change:
```javascript
if (positionClosed) {
    netSpent = 0;
    cashLeft = alloc + realizedPnl - skimForCoin;
} else {
    ...
    cashLeft = alloc - netSpent - skimForCoin;
```
becomes:
```javascript
cashLeft = alloc - netSpent - skimForCoin;
```

**ALSO** remove the `netSpent = 0;` reset (line 597) — netSpent should keep its real value for display/debugging even when position is closed.

### File 6: `web/tf.html`

**Two locations:**

(a) Lines 1105-1112 (active coins, closed position). Same pattern — replace the if/else with:
```javascript
cashLeft = alloc - netSpent - skimForCoin;
```

(b) Line 1070 (inactive/deallocated coins):
```javascript
cashReturned: realizedPnl - skimForCoin,
```
Change to:
```javascript
cashReturned: (totalSold - totalBought) - skimForCoin,
```

Explanation: for a deallocated coin, `alloc` is 0 in bot_config. The cash that "returned" to the TF pool = what came back from selling minus what was spent buying, minus skim. `totalBought` and `totalSold` are already computed on lines 1041-1042 of the same function.

### File 7: `commentary.py`

**Two locations:**

(a) Line 228 (inactive TF coins):
```python
total_cash += realized_pnl - skim_for_coin
```
Change to:
```python
total_cash += (total_sold - total_bought) - skim_for_coin
```

(`total_bought` and `total_sold` are already computed on lines 215-216.)

(b) Lines 255-258 (active coins, closed position):
```python
if position_closed:
    cash_left = alloc + realized_pnl - skim_for_coin
else:
    cash_left = alloc - net_spent - skim_for_coin
```
Change to:
```python
cash_left = alloc - net_spent - skim_for_coin
```

---

## Fix Part C — Dashboard display: update "Fees Paid" description

In all three dashboards, the FEES PAID card currently says:
> "already netted inside Total P&L"

This was always wrong — fees were never netted inside the USDT-based Total P&L. Update to:

> "tracked for reference · not deducted in paper mode"

### Files to update:
- `web/dashboard.html` — search for "already netted inside Total P&L"
- `web/admin.html` — same string
- `web/tf.html` — same string

---

## Historical data

Old trades in the DB have understated `realized_pnl` values (phantom fees subtracted). We do NOT fix them because:
1. Dashboards no longer use `realized_pnl` for cash/P&L calculation after this fix
2. The `fee` column is still correct for reference
3. Reconstructing correct values would require FIFO lot matching for every historical trade

The `realized_pnl` column for old trades will show a slightly lower value than reality. This is acceptable — it's an informational field, not a calculation input.

---

## Future: going live

When we switch from paper to real money, fees WILL be real. At that point we need to decide:
- **BNB payment** (current Binance setting): fees come from BNB balance, not USDT → `realized_pnl = revenue - cost_basis` stays correct
- **USDT payment**: fees deducted from trade → revert to `realized_pnl = revenue - cost_basis - fee - buy_fee`

This is a decision for when we go live. For now, paper mode = no fees deducted = current fix is correct.

---

## Checklist

- [ ] `bot/strategies/grid_bot.py:830` — remove `- fee - buy_fee`
- [ ] `bot/strategies/grid_bot.py:1744` — remove `- fee - buy_fee`
- [ ] `bot/grid_runner.py:1434` — remove `- sell_fee - buy_fees`
- [ ] `web/dashboard.html` — unified cash formula, remove positionClosed branch
- [ ] `web/admin.html` — unified cash formula, remove positionClosed branch
- [ ] `web/tf.html` — unified cash formula (active closed + inactive deallocated)
- [ ] `commentary.py` — unified cash formula (inactive + closed)
- [ ] All 3 dashboards — update "Fees Paid" description text
- [ ] Push to main
- [ ] Max: `git pull` on Mac Mini + restart orchestrator
- [ ] Verify dashboard P&L unchanged for open positions, slightly higher for any closed ones

## Commit message

```
fix: remove phantom fee deduction from realized_pnl

In paper mode, fees are informational only — calculated and stored
in the fee column for reference, but never deducted from the paper
portfolio (total_invested, total_received, available cash).

However, realized_pnl subtracted them as if they were real costs,
understating profits by ~$7.19 cumulative on Grid manual bots.

Fix: realized_pnl = revenue - cost_basis (no fee subtraction).
Fee tracking unchanged — still recorded for when we go live.

Also unifies dashboard cash formula: always use USDT flow
(alloc - netSpent - skim) instead of branching on positionClosed.
Fixes P&L display for closed/deallocated positions in
dashboard.html, admin.html, tf.html, and commentary.py.
```

## Rules

No external connections. No launching the bot. Push directly to main. Stop when done.
