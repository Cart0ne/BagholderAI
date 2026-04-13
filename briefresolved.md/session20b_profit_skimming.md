# Intern Brief 20b — Profit Skimming (Reserve Accumulation)

**From:** BagHolderAI CEO
**To:** Claudio Codice (CC)
**Session:** 20
**Priority:** MEDIUM — new feature, no rush, do it clean
**Date:** April 5, 2026

---

## Context

The grid bot generates micro-profits on each sell (buy low, sell slightly higher). Currently, 100% of the profit goes back into the trading pool and gets reinvested. This means all accumulated profits are exposed to market risk.

We want a **profit skimming** mechanism: after each sell, a configurable percentage of the trade profit is set aside as "reserve." The reserve is USDT that the bot does NOT use for buying. It's purely internal accounting — Binance sees the full balance, but the bot self-limits.

---

## What to build

### 1. Supabase: new fields in `bot_config`

Add to the existing `bot_config` table:
- `skim_pct` (numeric, default 0) — percentage of each sell's profit to skim into reserve. 0 = disabled.

**Note:** Do NOT create a new table for this. Keep it simple.

### 2. Supabase: reserve tracking

Add a new table `reserve_ledger`:
- `id` (uuid, primary key, default gen_random_uuid())
- `symbol` (text, not null) — e.g., 'BTC/USDT'
- `amount` (numeric, not null) — USDT amount skimmed from this trade
- `trade_id` (uuid, nullable) — reference to the sell trade that generated it
- `created_at` (timestamptz, default now())
- `config_version` (text, default 'v3')

Also add a convenience view or query pattern: total reserve per symbol = SUM(amount) from reserve_ledger WHERE symbol = X AND config_version = 'v3'.

### 3. Bot logic: skim after sell

In the sell execution flow (after a successful sell trade is recorded):
1. Read `skim_pct` from config
2. If `skim_pct > 0`, calculate: `skim_amount = trade_profit * (skim_pct / 100)`
3. Insert a row into `reserve_ledger`
4. Include skim info in the Telegram sell notification (e.g., "💰 Reserve: +$0.36 (→ total $12.50)")

### 4. Bot logic: subtract reserve from available cash

When calculating available cash for buying:
- `available_cash = total_usdt_balance - total_reserve`
- `total_reserve = SUM(amount) FROM reserve_ledger WHERE symbol = current_symbol AND config_version = 'v3'`

**Important:** Query the reserve total on each config refresh (every 5 minutes), not on every cycle. Cache it.

### 5. Admin dashboard: skim_pct field

Add `skim_pct` to the admin dashboard config panel, alongside buy_pct and sell_pct. Same edit/save pattern.

### 6. Telegram daily report: reserve summary

In the daily report, add a line per asset showing the accumulated reserve:
```
💰 Reserve BTC: $12.50
💰 Reserve SOL: $8.30
💰 Reserve BONK: $2.10
📊 Total Reserve: $22.90
```

### 7. Public dashboard (optional, low priority)

If time permits, show the reserve total on the public dashboard somewhere. Not critical for now.

---

## What NOT to build

- No manual reserve management (withdraw, reset). That's a future feature.
- No Binance API calls. This is pure internal accounting.
- No changes to the buy/sell logic beyond subtracting reserve from available cash.
- No separate reserve wallet or transfer mechanism.

---

## Rules of engagement

1. Work in the repository at `/Volumes/Archivio/bagholderai`
2. Do NOT launch the bot.
3. Supabase schema changes: YES, you can create the `reserve_ledger` table and add `skim_pct` to `bot_config`. Use the Supabase MCP connection.
4. When done, provide a summary of all files changed.
5. Stop when complete.

---

## Default values

Set `skim_pct = 0` for all three bots on deploy. We'll activate it manually after review.

— CEO, BagHolderAI
