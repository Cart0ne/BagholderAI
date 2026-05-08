# Brief proposal 60b — verify_fifo_queue should match the bot's sell semantics, not strict FIFO

> **SUPERSEDED 2026-05-08 (S65)** — il brief originale era una proposta strict-FIFO/multiset.
> A fine S65 il CEO + Max hanno deciso che strict-FIFO è abbandonato come metodo contabile
> (Binance probabilmente usa avg-cost). Il nuovo brief 60b respec sarà su "avg-cost pulito"
> invece, e va preceduto da brief 65c (Binance testnet verification). Vedi
> `config/decision_s65_gap_reconciled.md` e `BUSINESS_STATE.md §4` per la cronistoria.

**From:** CC (Claude Code, Intern) — proposal for the CEO
**To:** CEO (Claude, Projects) + Max (Board)
**Date:** May 6, 2026
**Priority:** MEDIUM — correctness of an internal check, not a trading bug
**Scope:** `bot/strategies/grid_bot.py::verify_fifo_queue`, unit tests
**Status:** proposal awaiting CEO approval. No code changes yet.

---

## Context

Brief 57a shipped a `verify_fifo_queue` that re-derives the FIFO queue from DB
trades and rebuilds the in-memory queue when they diverge. The implementation
assumes **strict FIFO**: every sell consumes the oldest buy. This is what the
verifier replays from DB.

But the bot does NOT execute strict FIFO at runtime. Looking at
`_check_percentage_and_execute` (`grid_bot.py:1348–1351`), the comment is
explicit:

> Iterate ALL open lots; sell any whose trigger is hit.
> FIFO order: among triggered lots, sell oldest first.
> **A lot can sell even if an older lot hasn't triggered yet.**

The bot is **FIFO among triggered lots** — i.e., it skips older lots that
haven't reached their sell threshold and sells newer lots that have. This is
intentional: it preserves Strategy A ("never sell at a loss").

When the bot skips a lot and sells the one behind, the in-memory queue records
the consumption as it actually happened. The verifier replays the same trade
sequence assuming strict FIFO and concludes that a *different* lot was
consumed. The two ricostruzioni diverge on **which lot was consumed**, even
though both queues have the same number of lots and the same totals.

---

## Concrete incident — BTC, 2026-05-06 11:05 UTC

DB sequence (chronological):
```
2026-05-05 17:02  BUY  0.00061 @ $81,245.64   (lot B, oldest)
2026-05-05 22:33  BUY  0.00061 @ $81,168.82   (lot C, newer, lower price)
2026-05-06 11:04  SELL 0.00061 @ $82,427.99   reason="above lot buy $81,168.82"
2026-05-06 11:05  SELL 0.00061 @ $82,448.76   reason="above lot buy $81,168.82"
```

At 11:04, only lot C had crossed its 1.5% sell threshold (lot B's trigger was
$82,463; price was $82,427 < trigger). The bot sold lot C, leaving B in queue.

`verify_fifo_queue` then re-played the DB:
- Strict FIFO: 2 buys, 1 sell of 0.00061 → consume lot B → queue = [lot C].
- Bot RAM: explicitly said "sold lot C (it triggered)" → queue = [lot B].

Alert telegram fired at 11:05:
```
DB queue:  amount=0.00061  price=$81,168.82   (= lot C, what FIFO replay says)
Mem queue: amount=0.00061  price=$81,245.64   (= lot B, what the bot kept)
```

The verifier rebuilt RAM with the strict-FIFO version. **This was the wrong
correction.** The bot's internal accounting was correct; the verifier was wrong.
At the next sell, the next `realized_pnl` written to DB used a cost basis that
no longer reflects which lot the bot actually consumed.

---

## Why this matters (and why it doesn't, in paper)

**Paper today**: zero impact on USDT cash flow. The bot still uses revenue and
total_invested correctly; only the per-trade `realized_pnl` may be slightly
miscomputed. Total realized P&L cumulative drifts in the noise.

**On mainnet**: the realized_pnl per sell becomes the basis for the daily P&L
narrative, the public Telegram report, the Haiku log. If the verifier keeps
"correcting" the queue toward strict FIFO, the bot will be telling the world
incorrect per-trade numbers (small but compounding) while internal state is
actually right.

**Worse**: the verifier today is the *only* piece declared as the gate before
the €100 live test (Phase 9 / §6 of the validation system). If the verifier's
own assumption is wrong, the gate is meaningless.

---

## Three options

**Option A — Set-based comparison**
Compare the *multiset* of `(amount, price)` between RAM and DB-replay, ignoring
order. If both queues contain the same lots regardless of position, no drift.

- ✅ Trivial: 5 lines, no schema change.
- ✅ Catches every "real" drift case (lots disappeared, lots appeared, lots
  changed in size/price).
- ❌ Loses ordering information. If the bot has correctly preserved a non-FIFO
  order due to triggered selling, the verifier's "no drift" verdict is right;
  but if the bot's order has actually been corrupted (real bug), the verifier
  no longer catches it.
- Risk: very low. The only way the order alone would mismatch *without* either
  amount or price changing is a bug we have never observed.

**Option B — Track lot identity in the trade record**
Every sell already has a `buy_trade_id` column in the schema. Today it's almost
always NULL. Populate it: when the bot sells, write the `id` of the buy whose
lot is being consumed.

- ✅ The replay becomes deterministic and faithful: no ambiguity about which
  lot was consumed.
- ✅ Permanent forensic record for any future drift investigation.
- ❌ More work: ~20 lines in `_execute_percentage_sell` to track and write the
  buy_trade_id; consideration for multi-lot consumes (one sell crossing 2 lots
  = one buy_trade_id? a list? schema change?).
- ❌ Historical sells stay NULL forever — the verifier needs a fallback strategy
  for the pre-fix tail anyway.

**Option C — Replay the bot's own decision logic in the verifier**
Re-walk the trade sequence using `sell_pct` and per-lot trigger logic to
determine which lot was consumed at each sell.

- ✅ Most correct theoretically.
- ❌ Most fragile in practice: depends on knowing `sell_pct` at each historical
  point in time (it may have changed via config_changes_log), TF override flags
  (stop_loss / trailing / take_profit / profit_lock / 45g all bypass strict
  FIFO too). Replicating all of that in the verifier is essentially
  re-implementing half the bot.
- ❌ Can only be approximate; small drifts will become "is this a real drift
  or just my approximation diverging" — the verifier becomes unreliable.

---

## Recommendation

**Option A** for the immediate fix, **possibly migrating toward B post-mainnet**.

Reasoning:
- A removes the false-positive class entirely with minimal code. The trade-off
  is losing detection of a bug class we have never seen and which is unlikely
  in practice (you would need amount and price to silently swap between two
  lots without changing the totals — pure code corruption).
- B is the architectural answer but doubles as an audit trail. Better as a
  go-live deliverable when the cost of forensic investigation is paid in real
  euros, not paper.
- C should be skipped; it's a reimplementation of the bot in the verifier and
  fragile by construction.

---

## Proposed implementation (Option A)

In `verify_fifo_queue`, replace the order-based comparison loop:

```python
# Current
if len(db_queue) != len(mem_queue):
    drift = True
else:
    drift = False
    for db_lot, mem_lot in zip(db_queue, mem_queue):
        if (abs(db_lot["amount"] - mem_lot["amount"]) > 1e-6
                or abs(db_lot["price"] - mem_lot["price"]) > 1e-6):
            drift = True
            break
```

with a multiset comparison:

```python
def _normalize(q):
    return sorted(
        ((round(l["amount"], 8), round(l["price"], 8)) for l in q),
        key=lambda t: (t[1], t[0]),
    )

drift = _normalize(db_queue) != _normalize(mem_queue)
```

Plus, when drift is detected, **don't unconditionally rebuild the RAM with the
DB version**. The bot's RAM might be the correct one. Instead:

- Log the drift event with both queues for forensic review.
- **Send Telegram alert** as today (the human gate).
- **Do not auto-rebuild** unless the totals also disagree (`Σ amount` and
  `Σ amount × price`). If totals match but composition differs, it's a
  ordering-only divergence and the safest choice is to keep the bot's RAM
  intact (RAM has the bot's actual decisions; DB-replay has the strict-FIFO
  guess).

---

## Tests

Add to `tests/test_verify_fifo_queue.py`:

1. **`test_set_match_no_drift`**: same lots, different order in queue.
   Assert: `result is True`, no rebuild, no Telegram (today this would be a
   false positive; with Option A it should be silent).
2. **`test_real_drift_still_caught`**: lot is missing or its amount changed
   on one side. Assert: `result is False`, rebuild + alert (regression check).
3. **`test_total_match_but_composition_differs`**: 2 lots in RAM with prices
   $100/$110, 2 lots in DB with prices $105/$105 (same Σ amount, same Σ value).
   Assert: this should still be flagged because the composition is materially
   different — multisets differ. (Or, more conservatively: this is a corner
   case that won't occur with the bot's logic; alternative — flag it and let
   the human decide.)

---

## Roadmap impact

- Phase 9 / §1 Technical integrity: no new check, modification of an existing
  check (`Health check: FIFO P&L reconciliation`).
- Phase 9 / §6 Pre-live gates: the gate "zero FIFO drift alerts for 7 days"
  becomes meaningful again — today it is biased by the false positives this
  brief eliminates.
- A new entry in Phase 8 (Backlog) once shipped, under "Phase 9 (Validation)".

---

## What NOT to Change

- **Do not ship Option B or C in this brief.** Option A is the surgical fix.
- **Do not relax the dust check.** That's `cd5074b` from this morning, lives
  on a different layer (it filters before the comparison; this brief is about
  the comparison itself).
- **Do not silence Telegram alerts unconditionally.** Real drift still alerts.
  The brief just removes the spurious-drift class.
- **Do not auto-rebuild on ordering-only drift.** When the bot's RAM disagrees
  with strict-FIFO replay but totals match, the RAM is more likely right (it
  reflects the bot's actual decisions). Auto-rebuilding could introduce
  regressions.

---

## Files to modify

| File | Action |
|---|---|
| `bot/strategies/grid_bot.py` | Replace order-based comparison with multiset; conditional rebuild |
| `tests/test_verify_fifo_queue.py` | 3 new tests (no-drift on reorder, real drift caught, totals-match composition-differs) |
| `web_astro/src/data/roadmap.ts` | Add 1 task in Phase 8 backlog when shipped |

---

## Origin

Diagnosed by CC on 2026-05-06 11:05 UTC analyzing the BTC drift alert
"`Memory had 1 lots → DB has 1 lots`" and the SOL spam earlier in the day.
Same root cause across symbols where the bot uses the FIFO-among-triggered
strategy: the verifier sees a divergence that is correct by design, not a bug.
