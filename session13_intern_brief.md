# SESSION 13 — INTERN BRIEF

## Context

The grid bot has been running v2 config since Session 10. We discovered that `get_open_position()` in `db/client.py` includes ALL historical trades (v1 + v2) when reconstructing the bot's state. This means:

- BONK bot ($30 allocation) is managing ~8.5M tokens inherited from v1
- BTC total_invested is $444 against a $100 allocation
- Cash calculates to $0 because cumulative invested exceeds initial capital
- Sell amounts on grid levels don't correspond to individual buys (they're averaged across inflated holdings)

**Decision:** We reset to v3. All new trades tagged `config_version='v3'`. `get_open_position()` filters by v3 only. Bots start with clean state.

---

## Changes Required

### FILE 1: `db/client.py`

**Change 1a** — `log_trade()` default config_version: `"v2"` → `"v3"`

```python
# Line ~46: change default parameter
def log_trade(
    self,
    ...
    config_version: str = "v3",  # was "v2"
) -> dict:
```

**Change 1b** — `get_open_position()`: add config_version filter

```python
# Replace the entire method (starting ~line 108)
def get_open_position(self, symbol: str, config_version: str = "v3") -> dict:
    """
    Reconstruct net position for a symbol from trades in DB.
    Filters by config_version to avoid cross-contamination between v1/v2/v3.
    Returns dict with holdings, avg_buy_price, realized_pnl, total_fees.
    """
    query = (
        self.client.table("trades")
        .select("*")
        .eq("symbol", symbol)
        .order("created_at", desc=True)
    )
    if config_version:
        query = query.eq("config_version", config_version)
    result = query.execute()
    trades = result.data or []

    holdings = 0.0
    avg_buy_price = 0.0
    realized_pnl = 0.0
    total_fees = 0.0
    total_invested = 0.0
    total_received = 0.0

    # Process in chronological order
    for t in reversed(trades):
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        fee = float(t.get("fee", 0))
        total_fees += fee

        if side == "buy":
            total_invested += amount * price
            old_holdings = holdings
            holdings += amount
            if holdings > 0:
                avg_buy_price = (avg_buy_price * old_holdings + price * amount) / holdings
        elif side == "sell":
            total_received += amount * price
            rpnl = float(t.get("realized_pnl", 0) or 0)
            realized_pnl += rpnl
            holdings -= amount
            if holdings <= 0:
                holdings = 0.0
                avg_buy_price = 0.0

    return {
        "holdings": holdings,
        "avg_buy_price": avg_buy_price,
        "realized_pnl": realized_pnl,
        "total_fees": total_fees,
        "total_invested": total_invested,
        "total_received": total_received,
    }
```

**Change 1c** — `get_today_trades()`: ensure config_version is passed when called from grid_runner

No code change here — the method already accepts `config_version` parameter. The caller needs to use it (see File 3 below).

---

### FILE 2: `bot/strategies/grid_bot.py`

**No changes needed.** `restore_state_from_db()` calls `self.trade_logger.get_open_position(self.symbol)` which now defaults to `config_version="v3"`. Since there are zero v3 trades, it returns holdings=0 and the bot starts clean.

---

### FILE 3: `bot/grid_runner.py`

**Change 3a** — `_build_portfolio_summary()`: use v3 trades only for position calculation

Find this line (~line 312):
```python
pos = trade_logger.get_open_position(inst.symbol)
```

Replace with:
```python
pos = trade_logger.get_open_position(inst.symbol, config_version="v3")
```

**Change 3b** — Daily report: filter today's trades by v3

Find this line (~line 188):
```python
today_all_trades = trade_logger.get_today_trades() if trade_logger else []
```

Replace with:
```python
today_all_trades = trade_logger.get_today_trades(config_version="v3") if trade_logger else []
```

---

### FILE 4: `config/settings.py`

**No changes needed.** The `TELEGRAM_PUBLIC_BOT_TOKEN` and `TELEGRAM_PUBLIC_CHAT_ID` variables are already defined. Max has updated the `.env` file on the Mac Mini with the correct values.

---

### FILE 5: `utils/telegram_notifier.py`

**No changes needed.** The public report logic is correct — it was just missing the env vars.

---

## Testing

After making changes, run this sequence:

```bash
# 1. Activate venv (IMPORTANT: use python3.13 explicitly)
cd /Volumes/Archivio/bagholderai
source venv/bin/activate

# 2. Quick sanity check — run each bot with --once --dry-run
python3.13 -m bot.grid_runner --symbol BTC/USDT --once --dry-run
python3.13 -m bot.grid_runner --symbol SOL/USDT --once --dry-run
python3.13 -m bot.grid_runner --symbol BONK/USDT --once --dry-run

# 3. Verify in logs that:
#    - "No open position found in DB for XXX" appears (v3 has no trades yet)
#    - Grid sets up with correct capital ($100 BTC, $50 SOL, $30 BONK)
#    - No errors in Telegram send
```

---

## What NOT to do

1. Do NOT delete any data from the `trades` table — v1/v2 data stays for analysis
2. Do NOT delete data from `daily_pnl` — the CEO will handle that separately
3. Do NOT change grid parameters (capital, levels, ranges, cooldowns) — v2 params carry forward
4. Do NOT launch the bots in production — Max will do that after review
5. Do NOT make any external connections beyond what's needed for --dry-run
6. Stop when tasks are complete. Do not continue working.

---

## Summary of changes

| File | Change | Lines |
|------|--------|-------|
| `db/client.py` | `config_version` default `"v2"` → `"v3"` | ~46 |
| `db/client.py` | `get_open_position()` add config_version filter | ~108-145 |
| `bot/grid_runner.py` | Pass `config_version="v3"` to `get_open_position` | ~312 |
| `bot/grid_runner.py` | Pass `config_version="v3"` to `get_today_trades` | ~188 |

Total: 4 changes across 2 files. Zero new dependencies. Zero schema changes.
