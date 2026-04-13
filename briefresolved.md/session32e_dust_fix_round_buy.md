# BRIEF: Round Buy Amount to Step Size (Dust Elimination)

**Priority:** MEDIUM
**Context:** Post-fix analysis of `exchange_filters.py` revealed that sell-side rounding creates dust residuals. Fix is to round at the source — the buy.

---

## Problem

After the exchange filters fix (April 13), `round_to_step()` correctly rounds sell amounts down to the exchange step size. But buy amounts are calculated as `capital / price` which produces non-aligned values. When the bot later sells, it rounds down and leaves dust (unsellable residual < 1 step).

**Real example from today (SOL/USDT, step = 0.001):**
- Buy: `12.50 / 85.87` = **0.14556888** SOL
- Sell: rounded to **0.14500** SOL
- Dust lost: 0.00056888 SOL ($0.047 today — but valued at future price)

**Why it matters:**
- Dust is denominated in coin, not USD — it appreciates/depreciates with the asset
- On SOL, dust ≈ 15% of per-trade profit at current micro-lot sizes
- On BTC, no dust observed (amounts already aligned) — but not guaranteed
- On BONK, dust < 1 token — negligible

---

## Fix

In `grid_bot.py`, after calculating buy amount as `capital / price`, apply `round_to_step()` **before** placing the buy order.

```python
# CURRENT (produces non-aligned amounts)
amount = capital / price

# FIXED (align to step at buy time)
amount = round_to_step(capital / price, lot_step_size)
```

This means:
- Buy spends slightly less than allocated capital (fractions of a cent)
- Sell amount = buy amount exactly → zero dust
- No risk of Binance rejection (rounding is always DOWN)

### Where to apply

Find every place in `grid_bot.py` (and any other file) where a buy amount is calculated from `capital / price` or similar. Apply `round_to_step()` immediately after the calculation, before the amount is stored or used for order placement.

---

## What NOT to touch

- **Sell logic** — already fixed, leave as-is
- **Skim logic** — works on USDT profit, unrelated to coin amounts
- **`round_to_step()` function** — already fixed with Decimal, leave as-is
- **Dust removal logic** (the `amount <= 0` pop) — keep it as safety net

---

## Verification

After applying:
1. Restart all three bots
2. Wait for at least 1 buy per symbol
3. Check Supabase: `SELECT amount FROM trades WHERE config_version='v3' AND side='buy' ORDER BY created_at DESC LIMIT 5`
4. Verify each buy amount is cleanly divisible by its step size:
   - SOL: amount × 1000 should be a whole number
   - BTC: amount × 100000 should be a whole number  
   - BONK: amount should be a whole number

---

## NOT a bug (for reference)

During analysis we found more sell records than buy records per symbol (e.g., BONK: 31 buys / 34 sells). This is **normal** — the bot splits lots across multiple sell events. Total amounts balance correctly:
- BONK: net holding = 0.99 BONK (pure dust)
- SOL: net holding = 0.00056888 SOL (today's dust)
- BTC: net holding = 0.00284706 BTC (open positions)

No action needed on this.
