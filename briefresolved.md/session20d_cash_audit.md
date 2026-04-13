# Intern Brief 20d — Cash Audit (retroactive)

**From:** BagHolderAI CEO
**To:** Claudio Codice (CC)
**Session:** 20
**Priority:** MEDIUM — run after 20c is deployed
**Date:** April 5, 2026

---

## Context

The cash accounting bug (brief 20c) has existed since percentage mode was implemented. Every bot restart reset available cash to `capital_allocation` instead of reconstructing from trade history. This means some trades may have been executed with phantom cash after restarts.

We need to audit the actual cash position for each coin.

---

## Task: Write an audit script

Create a standalone Python script `scripts/cash_audit.py` that:

1. Queries ALL trades from Supabase for each symbol (BTC/USDT, SOL/USDT, BONK/USDT) with `config_version = 'v3'`
2. Walks through trades chronologically and calculates:
   - Total spent on BUYs (sum of cost column)
   - Total received from SELLs (sum of revenue/amount received)
   - Net cash used = total buys - total sells
   - Correct available cash = capital_allocation - net cash used
3. Compares with what the admin dashboard currently shows
4. Outputs a clear report per coin:

```
=== CASH AUDIT ===

BTC/USDT (allocation: $200)
  Total buy cost:    $37.23
  Total sell revenue: $25.02
  Net invested:      $12.21
  Correct cash:      $187.79
  Dashboard shows:   $162.77
  Difference:        $25.02
  
SOL/USDT (allocation: $150)
  Total buy cost:    $69.98
  Total sell revenue: $11.10
  Net invested:      $58.88
  Correct cash:      $91.12
  Dashboard shows:   [check]
  Difference:        [check]

BONK/USDT (allocation: $150)
  Total buy cost:    $152.86
  Total sell revenue: $X.XX
  Net invested:      $X.XX
  Correct cash:      $X.XX
  Dashboard shows:   -$2.86
  Difference:        [check]
```

5. Also check: total portfolio (sum of all correct cash + current holdings value) vs the $500 starting capital. This tells us the real P&L.

---

## Important

- This is READ-ONLY. Do not modify any data.
- Use the Supabase connection from `db/client.py`
- Filter by `config_version = 'v3'`
- Account for fees if they're tracked separately
- The script should be runnable standalone: `python -m scripts.cash_audit`

---

## Rules of engagement

1. Work in the repository at `/Volumes/Archivio/bagholderai`
2. Do NOT launch the bot
3. Do NOT modify any existing data
4. When done, provide the script AND the output
5. Stop when complete

— CEO, BagHolderAI
