# Intern Brief 20a — Bug Fixes

**From:** BagHolderAI CEO
**To:** Claudio Codice (CC)
**Session:** 20
**Priority:** HIGH — these bugs are in production right now
**Date:** April 5, 2026

---

## Context

The bots are running on Mac Mini with percentage grid mode (`grid_mode=percentage`). The config is read from Supabase `bot_config` table every 5 minutes. Three bots run simultaneously: BTC/USDT, SOL/USDT, BONK/USDT.

Current config values:
- BTC: buy_pct=1.8, sell_pct=1.0
- SOL: buy_pct=1.5, sell_pct=1.0
- BONK: buy_pct=1.0, sell_pct=1.0

Capital: BTC $200, SOL $150, BONK $150.

---

## Bug 1 — CRITICAL: sell_pct not respected in percentage mode

**Problem:** The bot sells without waiting for the sell margin. In percentage mode, a sell should only trigger when the current price is >= (buy_price * (1 + sell_pct/100)). The bot is selling as soon as price is above buy price, ignoring sell_pct entirely.

**Expected behavior:** If sell_pct=1.0 and a position was bought at $100, the bot should only sell at $101 or above (1% margin). FIFO order: sell the oldest holding first.

**Action:** Find and fix the sell logic in percentage grid mode. This is the most important fix — the core trading strategy depends on it.

---

## Bug 2 — Config change notification spam (×9)

**Problem:** When a config change is detected, each of the 3 bots sends a notification for ALL coins, not just its own. Result: 3 bots × 3 coins = 9 Telegram notifications for a single config change.

**Expected behavior:** Each bot should only notify about config changes for ITS OWN symbol. BTC bot notifies about BTC config changes only, etc.

**Action:** Filter config change detection by the bot's own symbol.

---

## Bug 3 — Config change notifications missing parameter values

**Problem:** Config change notifications don't show what actually changed. They just say a change was detected, without showing the new buy_pct/sell_pct values.

**Expected behavior:** Notification should include the new parameter values, e.g.:
```
⚙️ CONFIG CHANGE DETECTED — BTC/USDT
buy_pct: 1.5 → 1.8
sell_pct: 0.8 → 1.0
grid_mode: percentage
```

**Action:** Include old vs new values in the config change notification message.

---

## Bug 4 — Duplicate daily report at 20:00

**Problem:** The daily report fires twice at REPORT_HOUR (20:00). Likely caused by the config change detection triggering a report alongside the scheduled one.

**Expected behavior:** Exactly ONE daily report per day, at REPORT_HOUR. Never two. If a config change happened during the day, mention it inside the report (e.g., "⚙️ Config changed today at 14:32").

**Action:** Add a guard so the report can only fire once per day (e.g., a flag or timestamp check). Optionally note config changes that happened during the day in the report body.

---

## Bug 5 — Trade P&L: show single trade profit in notifications

**Problem:** Trade sell notifications currently show overall P&L vs average, but not the profit of the individual trade being executed.

**Expected behavior:** When a sell executes, the Telegram notification should show:
1. The profit of THIS specific trade (sell price - buy price for the specific FIFO holding)
2. The existing P&L vs average

Example:
```
💰 SELL BTC/USDT
Price: $84,500.00
Amount: 0.00118 BTC
Trade P&L: +$1.23 (+1.48%)
Portfolio P&L: +$3.45 (+1.72%)
```

**Action:** Calculate and display the individual trade profit in sell notifications.

---

## Bug 6 — KeyboardInterrupt during error sleep doesn't send Telegram stop message

**Problem:** When the bot is in an error sleep (e.g., waiting after a Binance timeout), pressing Ctrl+C doesn't send the shutdown notification to Telegram. The bot just dies silently.

**Expected behavior:** KeyboardInterrupt should ALWAYS send the stop message to Telegram, even if caught during an error sleep or retry wait.

**Action:** Wrap the error sleep in a try/except KeyboardInterrupt that triggers the shutdown notification before exiting.

---

## Bug 7 — Switch fixed→percentage with open positions triggers first buy

**Problem:** When switching grid_mode from `fixed` to `percentage`, the bot does a "first buy" at market price even if it already has holdings in that coin. This causes a duplicate initial position.

**Expected behavior:** If the bot already has holdings (check Supabase `trades` table for open positions), skip the first buy on mode switch. The first buy should ONLY happen when there are zero holdings.

**Action:** Add a holdings check before the first buy logic. If holdings > 0, skip first buy and start monitoring from the existing position.

---

## Bug 8 — Buy skipped spam on Telegram

**Problem:** When capital is insufficient, the bot sends a "⚠️ BUY SKIPPED" notification every cycle (every 30 seconds or less). This floods Telegram.

Example of spam:
```
⚠️ BUY SKIPPED BONK/USDT
Level: $0.00000554
💵 Cash BONK: $3.14 → Servono $6.00 ❌ SKIPPED
Motivo: capitale insufficiente
```

**Expected behavior:** Send the "buy skipped" notification ONCE per price level. Don't repeat until either:
- The cash balance changes (new deposit or a sell frees up capital)
- A different price level is attempted

**Action:** Track the last notified "skip" per symbol (level + cash amount). Only re-notify if something changed.

---

## Rules of engagement

1. Work in the repository at `/Volumes/Archivio/bagholderai` (Mac Mini path)
2. Do NOT launch the bot. Do NOT connect to external services.
3. Do NOT modify Supabase schema without explicit approval in this brief.
4. Test your changes with dry-run logic where possible.
5. When done, provide a summary of all files changed and what was modified.
6. Stop when all tasks are complete.

---

## Priority order

1. **Bug 1** (sell_pct) — CRITICAL, fix first
2. **Bug 7** (first buy with holdings) — prevents bad trades on restart
3. **Bug 4** (duplicate report) — data integrity
4. **Bug 8** (buy skipped spam) — annoying but harmless
5. **Bug 2** (config ×9) — annoying but harmless
6. **Bug 3** (config params) — nice to have
7. **Bug 5** (trade P&L) — nice to have
8. **Bug 6** (KeyboardInterrupt) — edge case

Good luck. Don't break anything that's already working.

— CEO, BagHolderAI
