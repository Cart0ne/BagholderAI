# Brief 47b — Dashboard v2: Grid + Trend Follower Unified

## Context

The public dashboard at `bagholderai.lol/dashboard` currently shows only the Grid Bot
($500 initial). The Trend Follower ($100 initial) has been running since April 15
with 407 trades, but is invisible to visitors. Before the HN launch (April 28),
we need a single dashboard showing both bots with aggregated totals.

**Design principle:** one page, one story. Visitor sees the full picture immediately.

## Current Dashboard Structure (for reference)

1. CEO's Log (Haiku commentary, latest day)
2. THE NUMBERS — Net worth card ($500 initial, realized, unrealized, fees, skim)
3. Cash allocation bar (BTC/SOL/BONK/Cash)
4. Per-coin cards (BTC, SOL, BONK)
5. NET WORTH chart (line, daily)
6. DAILY P&L chart (bar, daily)
7. Trade stats row (total trades, buys/sells, cumul. realized, total fees)
8. Today's trades line
9. CEO'S LOG ARCHIVE

## New Dashboard Structure (v2)

### Section 1 — CEO's Log (unchanged)
Same as today. Haiku already comments on both Grid and TF.

### Section 2 — THE NUMBERS (aggregated)
**Critical change:** this section must aggregate Grid + TF.

- **Net worth:** Grid net worth + TF net worth (see data sources below)
- **Initial:** `$600.00` with subtitle `Grid: $500 · TF: $100`
- **Realized (net):** SUM of realized_pnl from trades WHERE config_version='v3',
  both managed_by values, minus fees
- **Unrealized:** Grid unrealized (from current positions) + TF unrealized
  (from bot_state_snapshots latest per symbol WHERE managed_by='trend_follower')
- **Fees paid:** SUM of fee from trades WHERE config_version='v3'
- **Skim reserved:** SUM of amount from reserve_ledger WHERE config_version='v3'
  (already includes both Grid and TF skims)

### Section 3 — GRID BOT section
Header: `GRID BOT` (with small pill/badge: `$500 initial`)

- Cash allocation bar (BTC/SOL/BONK/Cash) — same as today
- Per-coin cards (BTC, SOL, BONK) — same as today
- Trade stats row — filtered to `managed_by = 'grid'`

### Section 4 — TREND FOLLOWER section
Header: `TREND FOLLOWER` with badge `beta` and `$100 initial`

Content (keep it lean):
- **Status line:** "Active: GALA/USDT" or "Idle — waiting for entry signal"
  (derive from bot_config WHERE managed_by='trend_follower' AND is_active=true)
- **Stats row** (same layout as Grid stats row):
  - Total trades (from trades WHERE managed_by='trend_follower' AND config_version='v3')
  - Buys / Sells
  - Cumul. realized
  - Total fees
- **Active positions cards** (if any):
  Same card format as Grid coins — symbol, allocation, avg price, unrealized PnL.
  Derive from bot_state_snapshots DISTINCT ON symbol WHERE managed_by='trend_follower'
  ORDER BY created_at DESC, but ONLY show coins that are is_active=true in bot_config.
- **Recent TF trades** (last 10):
  Small table or list — timestamp, symbol, side (buy/sell), amount, price, realized PnL.
  This gives the visitor a sense of what the TF does without needing a full chart.

### Section 5 — AGGREGATED CHARTS
Header: `PORTFOLIO PERFORMANCE`

Two charts, stacked vertically (same style as current):

1. **NET WORTH** (line chart, daily)
   - Shows the combined portfolio value over time
   - Data source: see "Daily PnL Table Changes" below

2. **DAILY P&L** (bar chart, red/green, daily)
   - Shows combined daily realized PnL
   - Data source: see below

### Section 6 — CEO's Log Archive (unchanged)

---

## Data Layer Changes

### Option A (recommended): Add `managed_by` column to `daily_pnl`

```sql
ALTER TABLE daily_pnl ADD COLUMN managed_by TEXT DEFAULT 'grid';
```

Then the nightly PnL snapshot script must write TWO rows per day:
- One with managed_by='grid' (same logic as today, initial_capital=500)
- One with managed_by='trend_follower' (initial_capital=100, computed from TF trades/positions)

The dashboard queries aggregate with:
```sql
SELECT date,
  SUM(total_value) as total_value,
  SUM(realized_pnl_today) as realized_pnl_today
FROM daily_pnl
GROUP BY date
ORDER BY date;
```

For the individual bot sections:
```sql
SELECT * FROM daily_pnl WHERE managed_by = 'grid' ORDER BY date;
SELECT * FROM daily_pnl WHERE managed_by = 'trend_follower' ORDER BY date;
```

**Backfill:** TF has trades from April 15. We can compute daily TF value retroactively
from trades table — for each day, sum up the realized PnL and estimate holdings value
from the last trade prices. This doesn't need to be perfect — approximate is fine for
a 10-day backfill. If backfill is too complex, start TF chart from today (April 25).

### Option B (simpler, less clean): Separate table `daily_pnl_tf`

Same schema as daily_pnl but for TF only. Dashboard joins both.
Avoid if possible — Option A keeps everything in one table.

**CEO's recommendation: Option A.** One table, one query pattern, managed_by filter.

---

## Visual Design Notes

- Keep the current dark theme, green/red color scheme, monospace font — all unchanged.
- TF section should feel like a natural extension, not a bolt-on.
  Same card sizes, same spacing, same stat-row format.
- The `beta` badge on TF: small, muted color (e.g., dark yellow/amber text,
  not a bright flashy badge). It signals "this is real but early."
- Active TF coin cards should show the coin ticker prominently.
  Since TF rotates coins, the visitor should immediately see *what* TF is trading right now.
- If TF has zero active positions (idle state), show a single card:
  `"Idle — scanning for entry signals"` with the cash balance ($100 or whatever is available).

---

## What NOT to Build

- No separate URL/page for TF. One dashboard, one URL.
- No TF-specific Net Worth or Daily P&L charts (only aggregated charts).
- No trade history table for Grid (keep it same as today — total stats only).
- No filters, toggles, or interactive elements. Static, readable, honest.

---

## Local Testing

Build `dashboard_v2.html` first and test locally before deploying.
Max wants to see it and approve before it goes live.

**Dev approach:**
1. Copy current `dashboard.html` → `dashboard_v2.html`
2. Add TF section and modify aggregated numbers
3. Max reviews locally
4. If approved: replace `dashboard.html` with v2 content, delete v2 file
5. Deploy to main

---

## Test Checklist

1. Aggregated Net Worth matches Grid Net Worth + TF Net Worth
   (verify by querying both separately and comparing sum)
2. Trade stats in Grid section exclude TF trades (managed_by filter)
3. Trade stats in TF section exclude Grid trades
4. Skim total includes both Grid and TF (reserve_ledger has no managed_by —
   it's already combined. Note: Grid symbols = BTC/USDT, SOL/USDT, BONK/USDT;
   TF symbols = everything else. Could add per-bot skim display later)
5. TF active positions show only is_active=true coins from bot_config
6. When TF is idle (all coins inactive), shows "Idle" card correctly
7. Initial capital displays "$600" with "Grid: $500 · TF: $100" subtitle
8. Daily PnL table writes two rows (grid + TF) after migration
9. Dashboard loads in < 3 seconds (no new heavy queries)

## Execution

```bash
cd ~/BagholderAI
source venv/bin/activate
# implement, test locally, then:
git add -A && git commit -m "47b: dashboard v2 - grid + trend follower unified" && git push
```

On Mac Mini after push:
```bash
cd ~/BagholderAI && git pull
# no orchestrator restart needed — dashboard is static HTML served by Vercel
```
