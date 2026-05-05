# Brief 57a — FIFO Integrity Fix + Health Check System

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Date:** May 5, 2026
**Priority:** CRITICAL — gating for all future development + mainnet readiness
**Scope:** grid_bot.py, grid_runner.py, new health_check.py module
**Rule:** ZERO new features until this brief is verified and stable.

---

## Context — Why This Is the Only Priority

The bot sells BONK lots believing it made +$0.52. The global FIFO recalculation (same DB, same trades) says it lost −$0.07. The cause: the bot's in-memory FIFO queue (`_pct_open_positions`) drifts from the true FIFO derived from all DB trades. When it drifts, two things break:

1. **Strategy A is violated**: the bot sells lots that are FIFO-loss, thinking they're in profit. On paper with $25 this is noise. On mainnet with €50,000 this is hundreds of euros lost per drift event, repeatedly.
2. **DB `realized_pnl` is wrong**: every downstream consumer (Telegram, homepage, Haiku, diary) that reads the bot's `realized_pnl` sees a number that doesn't match what Binance would show.

The Board's directive: nothing gets built, nothing gets deployed, until the bot's numbers match the global FIFO at all times. A €100 live test follows this fix.

---

## Problem: How Does the Queue Drift?

The bot rebuilds `_pct_open_positions` at boot via `init_percentage_state_from_db()`. During runtime, it maintains the queue in memory: appending on buy, popping on sell. Drift can enter through:

1. **Floating-point dust**: after hundreds of partial-lot sells, `remaining -= lot["amount"]` accumulates rounding errors. A lot that should be fully consumed stays as a 0.0000001 residual, shifting which lot the next sell consumes.
2. **Bot restart with stale state**: if `init_percentage_state_from_db()` replays trades slightly differently from how the runtime consumed them (edge: a lot partially consumed in memory, then bot restarts, replay yields different partial amounts).
3. **Self-heal re-init**: the `_self_heal_attempted` path calls `init_percentage_state_from_db()` mid-operation, which can re-derive a queue that doesn't match the sell decisions already made in the current session.
4. **Concurrent bot instances**: if two processes trade the same symbol simultaneously (shouldn't happen, but no guard prevents it), each has its own queue.

We don't need to identify the EXACT source for every past drift. We need to **detect and correct drift before it causes a bad trade**.

---

## Fix 1: FIFO Queue Integrity Check (CORE FIX)

### New function: `verify_fifo_queue()`

Add to `grid_bot.py` a method that re-derives the FIFO queue from DB and compares with the in-memory queue:

```python
def verify_fifo_queue(self) -> bool:
    """
    Re-derive FIFO open positions from DB trades and compare
    with in-memory _pct_open_positions.
    Returns True if queues match, False if drift detected and corrected.
    """
    if not self.trade_logger:
        return True

    # 1. Replay all v3 trades for this symbol (same logic as init_percentage_state_from_db)
    try:
        result = (
            self.trade_logger.client.table("trades")
            .select("side,amount,price,cost,created_at")
            .eq("symbol", self.symbol)
            .eq("config_version", "v3")
            .order("created_at", desc=False)
            .execute()
        )
        trades = result.data or []
    except Exception as e:
        logger.warning(f"[{self.symbol}] FIFO verify failed (DB error): {e}")
        return True  # can't verify, don't crash

    # 2. Rebuild queue from scratch
    db_queue = []
    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        if side == "buy":
            db_queue.append({"amount": amount, "price": price})
        elif side == "sell":
            remaining = amount
            while remaining > 1e-12 and db_queue:
                oldest = db_queue[0]
                if oldest["amount"] <= remaining + 1e-12:
                    remaining -= oldest["amount"]
                    db_queue.pop(0)
                else:
                    oldest["amount"] -= remaining
                    remaining = 0

    # 3. Compare with in-memory queue
    mem_queue = self._pct_open_positions or []

    if len(db_queue) != len(mem_queue):
        drift = True
    else:
        drift = False
        for db_lot, mem_lot in zip(db_queue, mem_queue):
            # Allow tiny float differences but flag real drift
            if (abs(db_lot["amount"] - mem_lot["amount"]) > 1e-6
                    or abs(db_lot["price"] - mem_lot["price"]) > 1e-6):
                drift = True
                break

    if drift:
        logger.warning(
            f"[{self.symbol}] FIFO DRIFT DETECTED! "
            f"Memory queue: {len(mem_queue)} lots, "
            f"DB queue: {len(db_queue)} lots. Rebuilding from DB."
        )

        # Log details for forensic analysis
        log_event(
            severity="warn",
            category="integrity",
            event="fifo_drift_detected",
            symbol=self.symbol,
            message=f"FIFO queue drift: mem={len(mem_queue)} lots, db={len(db_queue)} lots",
            details={
                "mem_queue_summary": [
                    {"amount": round(l["amount"], 8), "price": round(l["price"], 6)}
                    for l in mem_queue[:5]  # first 5 for brevity
                ],
                "db_queue_summary": [
                    {"amount": round(l["amount"], 8), "price": round(l["price"], 6)}
                    for l in db_queue[:5]
                ],
            },
        )

        # 4. Replace in-memory queue with DB truth
        self._pct_open_positions = db_queue

        # Recalculate holdings and avg_buy_price from corrected queue
        if db_queue:
            total_amount = sum(lot["amount"] for lot in db_queue)
            weighted_cost = sum(lot["amount"] * lot["price"] for lot in db_queue)
            self.state.holdings = total_amount
            self.state.avg_buy_price = weighted_cost / total_amount if total_amount > 0 else 0.0
        else:
            self.state.holdings = 0.0
            self.state.avg_buy_price = 0.0

        # Send Telegram alert
        try:
            from utils.telegram_notifier import get_notifier
            notifier = get_notifier()
            notifier.send_message(
                f"⚠️ <b>FIFO DRIFT — {self.symbol}</b>\n"
                f"Queue corrected from DB.\n"
                f"Memory had {len(mem_queue)} lots → DB has {len(db_queue)} lots.\n"
                f"Holdings: {self.state.holdings:.6f}"
            )
        except Exception:
            pass  # best-effort notification

        return False

    return True
```

### Where to call it

**1. At boot** — after `init_percentage_state_from_db()` returns. This is a sanity check that the replay is internally consistent. Call in `grid_runner.py`:

```python
bot.init_percentage_state_from_db()
bot.verify_fifo_queue()  # belt + suspenders on startup
```

**2. Before every sell decision** — in `_check_percentage_and_execute()`, before the sell loop. This is the critical gate:

```python
# --- SELL CHECK ---
if self.state.holdings > 0:
    # Verify FIFO queue integrity before making sell decisions
    self.verify_fifo_queue()

    # ... existing sell loop ...
```

**3. Performance note**: This makes a DB query on every tick when holdings > 0. For 3 manual bots + 2 TF bots = 5 queries per tick. At 30-second cycles = 10 queries/minute. Supabase free tier handles this easily. If it ever becomes a concern, add a cooldown (verify every 5 minutes, not every tick). But **start with every tick** — correctness first.

---

## Fix 2: Align `_execute_sell` (Fixed Mode) with FIFO

The fixed-mode sell path in `_execute_sell()` still uses `avg_buy_price` for cost basis:

```python
# CURRENT (line ~830):
cost_basis = self.state.avg_buy_price * amount
realized_pnl = revenue - cost_basis
```

No bots currently use fixed mode, but for correctness and to prevent future bugs, align it with the percentage-mode pattern:

```python
# FIXED:
# Use the first FIFO lot's price if available, else fall back to avg_buy_price
if self._pct_open_positions:
    lot = self._pct_open_positions[0]
    lot_buy_price = lot["price"]
    cost_basis = lot_buy_price * amount
else:
    cost_basis = self.state.avg_buy_price * amount

realized_pnl = revenue - cost_basis
```

Also update the Strategy A guard in `_execute_sell` to use `lot_buy_price` instead of `avg_buy_price` if the FIFO queue is available. Currently it checks:

```python
if price * amount <= self.state.avg_buy_price * amount:
```

Change to:

```python
lot_buy_price = (
    self._pct_open_positions[0]["price"]
    if self._pct_open_positions
    else self.state.avg_buy_price
)
if price <= lot_buy_price:
```

---

## Fix 3: Health Check Module

New file: `bot/health_check.py`

A standalone function that can be called from the orchestrator (on startup, then every 30 minutes) or manually. It performs 5 checks:

### Check 1: FIFO P&L Reconciliation

For each active symbol, re-derive FIFO realized P&L from all v3 trades and compare with the DB `realized_pnl` sum:

```sql
-- DB realized_pnl sum
SELECT symbol, ROUND(SUM(realized_pnl)::numeric, 4) as db_pnl
FROM trades
WHERE config_version = 'v3' AND side = 'sell'
  AND symbol IN ('BTC/USDT', 'SOL/USDT', 'BONK/USDT')
GROUP BY symbol;
```

Compare with FIFO recalculated P&L (same algorithm as homepage). If delta > $0.05 for any symbol → alert.

### Check 2: Holdings Consistency

For each symbol, compare:
- `bot_config.holdings` (if stored)
- Sum of FIFO open lots from DB trade replay
- `state.holdings` in memory (only available when called from inside the bot)

If any two disagree beyond dust (>1e-6) → alert.

### Check 3: Negative Holdings Guard

```sql
-- Should NEVER return rows
SELECT symbol, SUM(CASE WHEN side='buy' THEN amount ELSE -amount END) as net_holdings
FROM trades
WHERE config_version = 'v3'
GROUP BY symbol
HAVING SUM(CASE WHEN side='buy' THEN amount ELSE -amount END) < -0.000001;
```

If any symbol has negative net holdings → CRITICAL alert (data corruption).

### Check 4: Cash Accounting

For each symbol:
```
expected_cash = capital_allocation - SUM(buy costs) + SUM(sell revenues) - SUM(skim)
```

Compare with what the dashboard would show. Delta > $0.10 → alert.

### Check 5: Orphan Lots

Check for sell trades with `buy_trade_id = NULL` that aren't FORCED_LIQUIDATION. These indicate the FIFO matching at trade-write time failed silently.

### Output

The health check function returns a structured report:

```python
{
    "timestamp": "2026-05-05T14:30:00Z",
    "all_ok": False,
    "checks": [
        {"name": "fifo_pnl", "status": "FAIL", "symbol": "BONK/USDT",
         "detail": "DB pnl=$78.88, FIFO pnl=$52.69, delta=$26.19"},
        {"name": "holdings", "status": "OK", "symbol": "BTC/USDT"},
        ...
    ]
}
```

If `all_ok == False` → send Telegram summary. If `all_ok == True` on startup → send a single "✅ Health check passed" message.

### Integration

In `orchestrator.py` (or wherever the bot startup sequence lives):

```python
# At boot, after all bots are initialized
from bot.health_check import run_health_check
report = run_health_check(supabase_client, symbols=active_symbols)
if not report["all_ok"]:
    notifier.send_message("🚨 HEALTH CHECK FAILED AT BOOT — see details above")

# Then every 30 minutes in the main loop
if time_since_last_health_check > 1800:
    run_health_check(supabase_client, symbols=active_symbols)
```

---

## Fix 4: Bot Event Logging for Drift Forensics

Every FIFO drift detection (Fix 1) already logs to `bot_events_log`. Additionally, log:

- **Every sell decision**: the lot's `buy_price` and `amount` from the in-memory queue, alongside the `realized_pnl` written to DB. This creates an audit trail we can replay if numbers don't match later.

In `_execute_percentage_sell`, after calculating `realized_pnl`:

```python
log_event(
    severity="info",
    category="trade_audit",
    event="sell_fifo_detail",
    symbol=self.symbol,
    message=f"Sell lot: buy@{lot_buy_price}, amount={amount}, pnl=${realized_pnl:.4f}",
    details={
        "lot_buy_price": lot_buy_price,
        "sell_price": price,
        "amount": amount,
        "cost_basis": cost_basis,
        "revenue": revenue,
        "realized_pnl": realized_pnl,
        "queue_depth": len(self._pct_open_positions),
    },
)
```

This is cheap (one insert per sell, we do maybe 20 sells/day) and invaluable for debugging.

---

## What NOT to Touch

- **No new features.** No new config parameters. No new trading logic.
- **No homepage changes.** The homepage FIFO calculation is already correct.
- **No Telegram report redesign.** Just make the source data correct.
- **No changes to TF bot logic** (allocator, scanner, trailing stop, greed decay). Those are frozen.
- **Do not change `sell_pct`, `buy_pct`, or any trading threshold.**
- **Do not add the "equity P&L" to the homepage.** That proposal is withdrawn.

---

## Testing

### Pre-deploy verification

1. **Unit test for `verify_fifo_queue()`**:
   - Create 5 buys, 2 sells in DB for a test symbol
   - Let `init_percentage_state_from_db()` build the queue
   - Manually corrupt one lot's price in `_pct_open_positions`
   - Call `verify_fifo_queue()` → expect: drift detected, queue rebuilt, Telegram sent
   - Call again → expect: no drift (queue now matches DB)

2. **Unit test for FIFO P&L**:
   - Create a known sequence: buy 100 @ $1.00, buy 100 @ $1.50, sell 100 @ $1.20
   - FIFO P&L should be: $120 - $100 = +$20 (sold the $1.00 lot)
   - NOT: $120 - $125 = −$5 (avg_buy_price = $1.25)
   - Verify the bot writes +$20 to DB, not −$5

3. **Health check dry run**:
   - Run `health_check.py` against current production DB
   - It WILL flag discrepancies (we know DB `realized_pnl` is inflated by ~$26)
   - This is expected — it confirms the check works
   - After the FIFO integrity fix runs for a few days, new sells should not create new discrepancies

### Post-deploy monitoring

- Watch Telegram for FIFO DRIFT alerts. In the first 24h, there may be corrections as the queue re-syncs. After that, any drift alert is a bug to investigate.
- Run health check manually: `python -m bot.health_check` (make it callable standalone)
- After 48h with zero drift alerts → report to CEO for go/no-go on €100 live test

---

## Commit message

```
fix(integrity): FIFO queue verification + health check system (57a)

Core fix: bot verifies its in-memory FIFO queue against DB truth
before every sell decision. If drift detected → auto-rebuild +
Telegram alert. Prevents Strategy A violations where bot sells
FIFO-loss lots believing they're profitable.

Additional:
- _execute_sell (fixed mode) now uses FIFO lot cost, not avg_buy_price
- New health_check.py module: 5 automated integrity checks
  (FIFO P&L reconciliation, holdings consistency, negative holdings
  guard, cash accounting, orphan lots)
- Sell audit trail in bot_events_log for forensic replay

Refs brief_57a. Zero new features — correctness only.
```

---

## Files to modify

| File | Action |
|---|---|
| `bot/strategies/grid_bot.py` | Add `verify_fifo_queue()` method; call before sell loop; fix `_execute_sell` FIFO alignment |
| `bot/grid_runner.py` | Call `verify_fifo_queue()` after boot init |
| `bot/health_check.py` | **NEW** — 5 integrity checks + Telegram alerting |
| `bot/orchestrator.py` | Call health check at boot + every 30 min |

## Files NOT to modify

- `bot/trend_follower/*` — frozen
- `web/*` — no frontend changes
- `bot/commentary.py` — no Haiku changes
- `config/*` — no config changes
- Supabase schema — no migrations needed (uses existing tables)

---

**Stato:** brief ready. CC: start with Fix 1 (verify_fifo_queue), test it standalone, then Fix 3 (health_check.py), then Fix 2 + Fix 4 together. Ship as one commit.**

— CEO, BagHolderAI
