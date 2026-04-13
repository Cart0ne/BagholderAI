# INTERN BRIEF — Session 17

## Task 1: Fix `cash_before` regression bug
**Priority: CRITICAL — Every trade since bot restart is a phantom trade**

### The Problem

The guard code deployed in Session 16 passes a `cash_before` keyword argument when logging trades. But `TradeLogger.log_trade()` does not accept that parameter. Result: the trade executes in memory, Telegram notification goes out, but the Supabase write crashes silently.

**Error from terminal (identical on both BONK and SOL):**
```
ERROR: Failed to log trade: TradeLogger.log_trade() got an unexpected keyword argument 'cash_before'
```

### Evidence

BONK buy at 10:43 — Telegram sent, no DB record:
```
10:43:00 [bagholderai.grid] ERROR: Failed to log trade: TradeLogger.log_trade() got an unexpected keyword argument 'cash_before'
10:43:00 [bagholderai.grid] INFO: BUY 1052970.253590 BONK/USDT @ $0.00 (cost: $5.98, fee: $0.0045)
```

SOL buy at 13:40 — same pattern:
```
13:40:38 [bagholderai.grid] ERROR: Failed to log trade: TradeLogger.log_trade() got an unexpected keyword argument 'cash_before'
13:40:38 [bagholderai.grid] INFO: BUY 0.159092 SOL/USDT @ $78.56 (cost: $12.50, fee: $0.0094)
```

### The Fix

Find where `log_trade()` is called with `cash_before=...` (likely in the guard code added in Session 16). Two options:

**Option A (preferred):** Add `cash_before` as an accepted parameter in `TradeLogger.log_trade()` and store it (useful for auditing capital checks). If the trades table doesn't have a `cash_before` column, just accept the param and ignore it for now.

**Option B:** Remove `cash_before=...` from the call site if we don't need the data.

### After the Fix

1. Do NOT restart the bots — Max handles that
2. Confirm the fix compiles / has no syntax errors
3. The two phantom trades from today (BONK + SOL) will need to be reconciled after restart

---

## Task 2: Clarify "Cash" label in Telegram buy/sell messages
**Priority: LOW — cosmetic, but prevents confusion**

### The Problem

The Telegram notification currently shows:
```
💵 Cash $31.37 → Spendo $12.50 ✅
```

This looks like total portfolio cash, but it's actually the **per-coin allocated cash**. Both the CEO and the co-founder got confused by this.

### The Fix

Change the label to include the coin symbol. Before:
```
💵 Cash $31.37 → Spendo $12.50 ✅
```

After:
```
💵 Cash SOL: $31.37 → Spendo $12.50 ✅
```

The symbol should come from whatever variable holds the current trading pair (e.g., `SOL/USDT` → use just `SOL`). Apply to both buy and sell messages, and to both the ✅ and ⚠️ variants.

Also apply to the "BUY SKIPPED" alert from the guard:
```
💵 Cash SOL: $18.87 → Servono $12.50 ❌ SKIPPED
```

---

## Rules

- Do NOT touch the guard logic itself — it works correctly
- Do NOT launch the bots — Max handles that
- Do NOT make external connections
- Stop when both fixes are committed
