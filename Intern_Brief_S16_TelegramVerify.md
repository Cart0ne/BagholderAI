# INTERN BRIEF — Session 16: Telegram Trade Verification

## Objective

After every BUY or SELL, the Telegram notification must show how much the bot had BEFORE the trade vs how much it's spending/selling. Max needs to verify at a glance that the bot isn't selling tokens it doesn't have or buying without budget.

## Expected Telegram output

**BUY:**
```
🟢 BUY BTC/USDT
Amount: 0.000283
Price: $84,500.00
Cost: $23.91
Fee: $0.0179
Brain: grid | Mode: PAPER
💵 Cash $76.00 → Spendo $23.91 ✅
```

**SELL (ok):**
```
🔴 SELL BTC/USDT
Amount: 0.000283
Price: $85,200.00
Revenue: $24.11
Fee: $0.0181
Brain: grid | Mode: PAPER
💰 P&L: $0.1342
📦 Ho $48.00 → Vendo $24.11 ✅
```

**SELL (anomaly):**
```
📦 Ho $10.00 → Vendo $24.11 ⚠️
```

## Changes (3 changes, 2 files)

### Change 1: `bot/strategies/grid_bot.py` → `_execute_buy()`

At the TOP of the method, BEFORE any state mutation (before `self.state.total_invested += cost`), add:

```python
# Snapshot for Telegram verification
cash_before = max(0.0, self.capital - self.state.total_invested + self.state.total_received)
```

Then add these keys to the `trade_data` dict:

```python
"cash_before": cash_before,
"capital_allocated": self.capital,
```

### Change 2: `bot/strategies/grid_bot.py` → `_execute_sell()`

After the early return checks but BEFORE state mutations (before `self.state.total_received += revenue`), add:

```python
# Snapshot for Telegram verification
holdings_value_before = self.state.holdings * price
```

Then add this key to the `trade_data` dict:

```python
"holdings_value_before": holdings_value_before,
```

### Change 3: `utils/telegram_notifier.py` → `send_trade_alert()`

Replace the entire `send_trade_alert` method with:

```python
async def send_trade_alert(self, trade: dict) -> bool:
    """Send a single trade notification with verification."""
    emoji = "🟢" if trade["side"] == "buy" else "🔴"
    pnl_line = ""
    if trade.get("realized_pnl") is not None:
        pnl_line = f"\n💰 P&L: ${trade['realized_pnl']:.4f}"

    cost_label = "Revenue" if trade["side"] == "sell" else "Cost"

    # Verification line
    verify_line = ""
    TOLERANCE = 0.01  # 1% tolerance for rounding
    if trade["side"] == "buy" and "cash_before" in trade:
        cash = trade["cash_before"]
        spend = trade["cost"]
        ok = cash >= spend * (1 - TOLERANCE)
        icon = "✅" if ok else "⚠️"
        verify_line = f"\n💵 Cash ${cash:.2f} → Spendo ${spend:.2f} {icon}"
    elif trade["side"] == "sell" and "holdings_value_before" in trade:
        have = trade["holdings_value_before"]
        sell_val = trade["cost"]
        ok = have >= sell_val * (1 - TOLERANCE)
        icon = "✅" if ok else "⚠️"
        verify_line = f"\n📦 Ho ${have:.2f} → Vendo ${sell_val:.2f} {icon}"

    text = (
        f"{emoji} <b>{trade['side'].upper()}</b> {trade['symbol']}\n"
        f"Amount: {trade['amount']:.6f}\n"
        f"Price: {fmt_price(trade['price'])}\n"
        f"{cost_label}: ${trade['cost']:.2f}\n"
        f"Fee: ${trade['fee']:.4f}\n"
        f"Brain: {trade['brain']} | Mode: {trade['mode']}"
        f"{pnl_line}"
        f"{verify_line}"
    )
    return await self.send_message(text)
```

## Important notes

1. Snapshots MUST be captured BEFORE state mutation. In `_execute_buy`, `total_invested` gets incremented — snapshot before that. In `_execute_sell`, `holdings` gets decremented — snapshot before that.
2. 1% TOLERANCE prevents false ⚠️ from floating point rounding (e.g. holdings worth $23.99 vs sell of $24.00).
3. Backward-compatible: if keys aren't in trade_data, the verify line simply doesn't appear.
4. `trade["cost"]` = `amount * price` for both buy (cost) and sell (revenue). Same field, different label.
5. Do NOT modify any other files. Do NOT change any logic outside these three changes.

## Commit message

```
feat: add holdings/cash verification to Telegram trade alerts
```

## Rules

No external connections. No launching the bot. Stop when done.
