# Brief proposal 60a — Dust-merge at sell

**From:** CC (Claude Code, Intern) — proposal for the CEO
**To:** CEO (Claude, Projects) + Max (Board)
**Date:** May 6, 2026
**Priority:** MEDIUM — quality of life + pre-mainnet hygiene
**Scope:** `bot/strategies/grid_bot.py` (`_execute_percentage_sell`), unit tests
**Status:** ARCHIVED 2026-05-07 — superseded by 62b §3.1.

---

> **ARCHIVED 2026-05-07 — ABSORBED INTO BRIEF 62b §3.1**
>
> Il brief CEO 62b ha adottato un approccio diverso (più semplice) per
> la prevenzione dust: "arrotonda la sell per svuotare la posizione quando
> il residuo sarebbe < min_order_size". Vedi
> `config/brief_62b_grid_refactor_phase2.md` §3.1 ("Prevenzione —
> Arrotondamento sell per svuotare posizione").
>
> L'approccio 60a (fold dust into next lot) NON è quello che 62b implementa,
> ma risolve lo stesso problema alla fonte. Conservato qui per traccia
> forense. NON implementare 60a separatamente — Phase 2 chiude la storia
> della dust prevention.

---

## Context

After 57a (FIFO integrity) and the dust-threshold hotfix (`cd5074b`), the bot
no longer mis-attributes dust to drift alerts. But the dust itself — sub-MIN_NOTIONAL
lots — still accumulates over time as a side effect of partial sells against
exchange step_size constraints.

State 2026-05-06 mid-day (Grid manual):
- BONK: 0.99 BONK ≈ $0.000006 (dust)
- BTC:  0.00000706 BTC ≈ $0.58 (dust)
- SOL:  0.04256888 SOL ≈ $3.79 (dust, **created today** by the 5-sell cascade
  at 08:52–08:56 UTC when SOL ran from $84 to $89)

Total ≈ $4.39 of dust lots that the bot recognizes but cannot sell — the runtime
pops them on every sell tick, the DB keeps the buy record, and the value is
trapped contabile-wise without being convertible into USDT through normal grid
operations.

On paper this is a $4 cosmetic issue. On mainnet at 50× scale this becomes
~$200/month of "stuck" capital, plus a small but recurring divergence between
the dashboard P&L (which counts dust × spot price) and the wallet P&L (which
cannot liquidate dust at market).

**Important pre-existing context**: a parked brief from 2026-04-21 already
analyzed three options for dust handling (`config/brief_DUST_writeoff_parcheggiato.md`).
The CEO's recommendation there was: **defer everything until live, then
implement Option 3 (`written_off_at` flag) plus integration with Binance
`/sapi/v1/asset/dust` API**.

This proposal is **different** from that one. It does not write-off the dust;
it prevents it from being created in the first place. The two solutions can
coexist:
- **This brief (60a)**: stop creating new dust at the source.
- **The parked brief**: deal with dust that already exists in the wallet at
  go-live (historical residuals, edge cases, externally injected positions).

---

## Problem

In `_execute_percentage_sell` (`grid_bot.py:1645–1649`) the "last-lot logic"
sells one lot at a time:

```python
# Last-lot logic: if holdings are <= lot size, sell everything in one trade
if self.state.holdings <= lot["amount"] + 1e-10:
    amount = self.state.holdings
else:
    amount = lot["amount"]
```

When the first lot in the FIFO queue is dust (sub-MIN_NOTIONAL), `amount`
becomes the dust amount. The validate_order check fails (MIN_NOTIONAL violated),
the lot is popped from RAM, `_execute_percentage_sell` returns None. **No sell
happens this tick**, even though the second lot was sellable. The real lot gets
sold one tick later (~5–10s).

Effect:
1. Dust persists in DB indefinitely.
2. Each tick where the dust is at the head of the queue costs latency on the
   real sell behind it.
3. On Binance live, the dust accumulates in the wallet as "small balances"
   that need a periodic dust converter.

---

## Proposed Fix

Extend the last-lot logic with a **dust-merge** branch: if the first lot is
sub-MIN_NOTIONAL **and** there is at least one further lot in the queue,
fold the dust into the next sell instead of popping it.

Pseudo-code in `_execute_percentage_sell` before the existing `amount = ...` decision:

```python
lot = self._pct_open_positions[0]
lot_value = lot["amount"] * price
min_notional = float((self._exchange_filters or {}).get("min_notional") or 0)

if (min_notional > 0
    and lot_value < min_notional
    and len(self._pct_open_positions) >= 2):
    # Dust-merge: fold lot 0 into the sell of lot 1.
    # Sell amount = lot[0].amount + lot[1].amount.
    # Cost basis is summed across both lots in the existing FIFO walk
    # (lines 1767-1781 already handle multi-lot consume correctly post-53a).
    # The sell becomes a single transaction that drains both lots.
    next_lot = self._pct_open_positions[1]
    amount = lot["amount"] + next_lot["amount"]
    # Use lot 1's buy_price for the Strategy A guard (lot 0 is dust;
    # checking it would always block if its buy_price is high).
    lot_buy_price = next_lot["price"]
else:
    # Existing branches: full liquidation when holdings <= lot size,
    # otherwise sell exactly one lot.
    if self.state.holdings <= lot["amount"] + 1e-10:
        amount = self.state.holdings
    else:
        amount = lot["amount"]
    lot_buy_price = lot["price"]
```

**Why it works:**
- The existing FIFO walk at lines 1767–1781 already computes
  `cost_basis = Σ lot.amount × lot.price` over **all consumed lots**.
  No further math change needed — the loop just consumes lots 0 + 1 in one
  pass instead of failing on lot 0 alone.
- `realized_pnl = revenue − cost_basis` is automatically correct: the dust's
  cost (low) is included in the basis; the revenue covers both lots; the lot
  behind contributes its real margin.
- The Strategy A guard already uses `lot_buy_price` of the lot being primarily
  sold (lot 1 here, the real lot). The dust's high buy_price (which would
  always block sells if checked) is bypassed correctly — it should be: the
  dust is consumed, not "sold for profit on its own".

---

## Edge cases to test

1. **Dust + real lot, both in profit at sell**: classic case. SOL after 08:55
   today would have triggered this if the fix had been live. Expected: one
   single sell, both lots drained, dust stops existing.
2. **Dust + real lot, real lot in profit but dust would be in loss**: bot
   should still sell. The dust is not "sold at a loss" — it's consumed as part
   of a profitable aggregate sell.
3. **Two dust lots in a row + real lot**: the recursive case. Today's fix
   only merges lot 0 into lot 1. If lot 1 is also dust, the new sell still
   fails MIN_NOTIONAL. Decide: extend to fold all consecutive dust lots until
   the cumulative value clears MIN_NOTIONAL, or accept that two consecutive
   dust lots are a corner case worth deferring.
4. **Only dust in the queue (no real lot behind)**: skip merge, fall through
   to the existing `pop and return None` path. The dust stays trapped, same
   behavior as today.
5. **No exchange filters loaded yet (boot edge)**: skip merge, behavior
   identical to today (the runtime would have fallen into the same path
   anyway since it can't validate).

---

## Tests

In `tests/test_pct_sell_fifo.py`:

1. **`test_dust_merge_basic`**: queue = [dust 0.0426 @ $87, real 0.223 @ $89.65],
   exchange_filters min_notional=$5, price = $90. Sell triggers. Assert: one
   trade executed, amount = 0.2656, queue empty, realized_pnl correct
   (FIFO over both lots).
2. **`test_dust_merge_only_dust`**: queue = [dust only]. Assert: no trade,
   pop, return None (existing behavior, regression check).
3. **`test_dust_merge_no_filters`**: queue = [dust, real], `_exchange_filters = None`.
   Assert: falls through to existing logic (no merge, dust eventually popped
   the old way, no regression on boot edge).

In `tests/test_verify_fifo_queue.py`: no changes needed, the verifier already
handles the post-merge state correctly (queue shrinks by 2, value totals match).

---

## What NOT to Change

- **No write-off, no `written_off_at` column.** That belongs to the parked
  Apr-21 brief and should wait for live trading where Binance wallet is the
  ground truth. This brief only changes the bot's sell logic.
- **No changes to the verifier (`verify_fifo_queue`)**. Today's `cd5074b`
  hotfix already filters dust on the DB side correctly. The merge fix on the
  sell side will mostly *prevent* the verifier from ever seeing dust again,
  because dust no longer accumulates.
- **No changes to TF allocator or scanner.** Dust-merge is symmetric; it just
  applies to grid_bot's sell path.
- **No CEO/Haiku narrative changes.** Reports already use FIFO realized_pnl,
  and the merged sell will produce a single correct realized_pnl row.

---

## Roadmap impact

- Phase 9 / §1 Technical integrity: the existing checks become *quieter* (less
  dust drift to flag) but no check definition changes.
- Phase 9 / §8 Process & Log Hygiene: the "dust converter via Binance API" task
  becomes lower priority once 60a is shipped — most dust is auto-merged before
  it hits the wallet.
- A new entry in Phase 8 (Backlog) under "Phase 1 — Grid Bot & Paper Trading"
  documenting the dust-merge fix once shipped.

---

## Files to modify

| File | Action |
|---|---|
| `bot/strategies/grid_bot.py` | Extend last-lot logic in `_execute_percentage_sell` |
| `tests/test_pct_sell_fifo.py` | Add 3 test cases for dust-merge branches |
| `web_astro/src/data/roadmap.ts` | Add 1 task in Phase 8 backlog when shipped |

---

## Origin

Idea proposed by Max on 2026-05-05 ("ho dust per 0.57, non posso comprare 9.43+0.57?").
The intuition was right, but the implementation point is the **sell**, not the
**buy** — confirmed by today's SOL spam incident which also vindicated this
approach: each new dust lot creates pressure on the verifier, and pre-empting
dust at sell time eliminates the source.
