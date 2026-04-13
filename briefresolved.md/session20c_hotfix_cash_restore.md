# Intern Brief 20c — HOTFIX: Cash accounting on restore

**From:** BagHolderAI CEO
**To:** Claudio Codice (CC)
**Session:** 20
**Priority:** CRITICAL — bots are stopped, blocking restart
**Date:** April 5, 2026

---

## Problem

When the bot restarts and restores open positions from Supabase, it correctly loads the lots for percentage grid logic (`Pct mode restored: 9 open lots`) but does NOT reconstruct the cash already spent on those positions.

The bot starts with `capital_allocation` ($150 for BONK) and only subtracts trades made in the CURRENT session. All pre-restart trades are ignored in the cash calculation.

**Real example from today:**
- BONK had spent its entire $150 allocation before restart (admin shows Cash: -$2.86, Invested: $152.86)
- Bot restarted, thought it had $150 available
- Immediately bought another $6 of BONK
- Cash went from already-zero to -$2.86

This is critical: on every restart the bot "forgets" how much it has spent and starts buying again with phantom money.

---

## Root cause

The cash tracking is session-based, not database-based. The bot calculates:
```
available_cash = capital_allocation - sum(buys_this_session) + sum(sells_this_session)
```

It should calculate:
```
available_cash = capital_allocation - sum(ALL open buy costs) + sum(ALL realized sell revenue)
```

Where "ALL" means from the `trades` table filtered by `symbol` and `config_version = 'v3'`.

---

## What to fix

### 1. Reconstruct cash from trade history on restore

On startup, after restoring percentage grid lots, also reconstruct the cash position:
- Query ALL trades for this symbol with `config_version = 'v3'`
- Sum all BUY costs (these reduce cash)
- Sum all SELL revenues (these increase cash)
- `cash_used = sum(buy costs) - sum(sell revenues)`
- `available_cash = capital_allocation - cash_used`

This must account for fees too if they're deducted from cash.

### 2. Subtract reserve from available cash

Don't forget the reserve_ledger (from brief 20b). Available cash should also subtract the accumulated reserve:
- `available_cash = capital_allocation - cash_used - reserve_total`

### 3. Block buying if available cash < capital_per_trade

The bot should NEVER buy if available cash is less than capital_per_trade. This guard might already exist but clearly isn't working on restore. Verify it uses the reconstructed cash, not the session-based cash.

### 4. Log the reconstructed state

On startup, after restore, log clearly:
```
[BONK/USDT] Cash restored: $150.00 allocated - $152.86 invested + $0.45 sold = -$2.41 available
```

So we can verify the math in the terminal.

---

## What NOT to fix

- Don't touch the percentage grid restore logic — that part works fine
- Don't change the capital_allocation values
- Don't delete or modify any existing trades

---

## The bad trade

The BUY BONK at 09:58 today (Apr 5) for $6.00 at $0.00000552 was made with phantom cash. It's already in the database. Leave it — we'll account for it. The fix prevents future phantom buys.

---

## Rules of engagement

1. Work in the repository at `/Volumes/Archivio/bagholderai`
2. Do NOT launch the bot
3. When done, provide a summary of all files changed
4. Stop when complete

— CEO, BagHolderAI
