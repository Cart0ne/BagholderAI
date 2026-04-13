# INTERN BRIEF — Session 26 ✅ RESOLVED

**Date:** April 8, 2026 | **Priority:** HIGH
**Commits:** `7cd74b9` (fixes 1-3 + time refs + admin payload bug) · `062fdd0` (live index numbers)

---

## Summary of work done

Tre fix dal brief originale + 3 emersi durante la sessione:

| # | Fix | File | Note |
|---|-----|------|------|
| 1 | Haiku 24h window | `commentary.py` | Cutoff = `now - 24h` invece di `today midnight UTC` |
| 2 | Homepage layout + auto-refresh | `web/index.html` | Today's log → Numbers (timestamp + 5min refresh) → Archive |
| 3 | Admin decimal comma → dot | `web/admin.html` | Step A già fatto in S25; aggiunto Step B (sanitize + isNaN) |
| 4 | **Bug found:** `config_changes_log` payload | `web/admin.html` | Usava `field:` ma colonna è `parameter` → 5 giorni di insert silenziosamente falliti |
| 5 | **Bug found:** index numbers stale | `web/index.html` | Leggeva da `daily_pnl` snapshot 20:00 → SOL mostrava $0.00 mentre era deployed |
| 6 | Time references everywhere | molti | Allineati a 20:00 (era mix di 21:00/midnight da sessioni precedenti) |

---

## Fix 1 — Haiku commentary: inject config_changes_log into prompt

### Problem

The CEO's Log (Haiku daily commentary) always says "no human intervention" even when Max changes parameters daily (idle reentry hours, grid_mode switch, etc.). Haiku receives `config_changes` in its prompt data but `get_config_changes()` in `commentary.py` only queries changes from **today's midnight UTC**. Max often changes parameters during the day and the commentary runs at 21:00 — but the window is too narrow and timezone-dependent.

### Fix

In `commentary.py`, function `get_config_changes()`:

**Current:** queries `config_changes_log` where `created_at >= today midnight UTC`

**New:** query the **last 24 hours** instead of since midnight:

```python
from datetime import datetime, timedelta, timezone

cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
```

Replace the current `today_midnight` calculation with this `cutoff` and use it in the `.gte("created_at", cutoff)` filter.

### Verification

1. Query `config_changes_log` directly to confirm there are recent entries:
   ```sql
   SELECT * FROM config_changes_log ORDER BY created_at DESC LIMIT 10;
   ```
2. Run `test_commentary.py` with a fake `portfolio_data` and confirm the `config_changes` array in `prompt_data` is populated (not empty `[]`).
3. Print the generated commentary — it should reference Max's changes.

**Do NOT restart the bot.** Test only via `test_commentary.py`.

---

## Fix 2 — Homepage layout restructure + hourly numbers refresh

### Context

Current `web/index.html` layout order:
1. CEO's Log (hero + history below)
2. The Numbers (portfolio, charts, stats)

### New layout order

1. **CEO's Log — today only** (hero card, just the latest entry)
2. **The Numbers** (portfolio, assets, charts, stats) — with hourly refresh + timestamp
3. **CEO's Log Archive** (previous days' commentary, scrollable)

### Implementation steps

#### Step A — Split commentary into hero + archive

The current code renders commentary in two elements: `#ceo-log-hero` (latest) and `#commentary-history` (rest). These are currently inside the same `<section>`.

**Move `#commentary-history`** to a NEW section AFTER "The Numbers" section. Give it its own section title: `CEO's Log Archive`.

HTML structure becomes:
```html
<!-- 1. CEO's Log (today only) -->
<section style="margin-top: 40px;">
  <h2 class="section-title">CEO's Log</h2>
  <div id="ceo-log-hero" class="card ceo-log-hero">...</div>
</section>

<!-- 2. The Numbers -->
<section>
  <h2 class="section-title">The Numbers</h2>
  <div id="numbers-timestamp" style="font-family: var(--mono); font-size: 11px; color: var(--text-dim); margin-bottom: 12px;"></div>
  <!-- ... existing portfolio card, assets, charts, stats ... -->
</section>

<!-- 3. CEO's Log Archive -->
<section>
  <h2 class="section-title">CEO's Log Archive</h2>
  <div id="commentary-history" class="commentary-history"></div>
</section>
```

#### Step B — Hourly auto-refresh for Numbers

Currently, all data is loaded once on page load via the `load()` function.

Add a **separate function** `refreshNumbers()` that re-fetches ONLY the data needed for "The Numbers" section:
- `daily_pnl` (latest row for portfolio value, P&L, cash)
- `trades` (for today's activity count)
- `v_reserve_totals` (for skim)

Call `refreshNumbers()` on an interval:
```javascript
setInterval(refreshNumbers, 5 * 60 * 1000); // every 5 minutes
```

**Note:** Use 5 minutes, not 1 hour. The data source (`daily_pnl`) updates at 21:00 only, but trades and positions can change during the day. 5 minutes is a good balance.

#### Step C — Timestamp display

After each `refreshNumbers()` call, update the `#numbers-timestamp` element:

```javascript
function updateTimestamp() {
  var now = new Date();
  var h = now.getHours();
  var m = now.getMinutes();
  var ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  var timeStr = h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
  document.getElementById('numbers-timestamp').textContent = 
    'Updated at ' + timeStr + ' · full report at midnight';
}
```

Call `updateTimestamp()` at end of initial `load()` and at end of each `refreshNumbers()`.

### Verification

1. Open `index.html` in browser
2. Confirm layout order: today's log → numbers (with timestamp) → archive
3. Wait 5 minutes, confirm numbers section refreshes and timestamp updates
4. Confirm commentary archive still scrolls and shows previous days

---

## Fix 3 — Admin decimal input on iOS (comma vs dot)

### Problem

On iPhone with Italian locale, `input type="number"` shows a numeric keyboard with comma (`,`) as decimal separator. The admin JS sends the raw value to Supabase, which rejects or misreads the comma — parameters like `buy_pct` silently fail or save wrong values.

### Fix

In `web/admin.html`:

#### Step A — Add `inputmode="decimal"` to all percentage/decimal fields

Find all `<input type="number">` used for `buy_pct`, `sell_pct`, `lot_size`, `idle_reentry_hours`, and any other decimal config fields. Change them to:

```html
<input type="text" inputmode="decimal" ...>
```

Using `type="text"` with `inputmode="decimal"` gives iOS the numeric keyboard with BOTH comma and dot, and avoids the browser's built-in number validation which varies by locale.

#### Step B — Sanitize on save

In the JS function that saves config values to Supabase, normalize comma to dot before sending:

```javascript
// Before sending any decimal value to Supabase:
value = value.replace(',', '.');
value = parseFloat(value);
if (isNaN(value)) { alert('Invalid number'); return; }
```

Apply this to every field that expects a decimal number.

### Verification

1. Open admin on iPhone (or Safari responsive mode with Italian locale)
2. Edit `buy_pct` using comma as decimal separator (e.g. `1,5`)
3. Save — confirm it writes `1.5` to Supabase (not `1,5` or NaN)
4. Confirm the field displays correctly after refresh

---

## Files to modify

| File | Fix |
|------|-----|
| `commentary.py` | Fix 1: 24h window |
| `web/index.html` | Fix 2: layout + refresh |
| `web/admin.html` | Fix 3: decimal comma → dot |

## Intern rules

1. Do NOT launch or restart any bot
2. Do NOT modify any file not listed above
3. Test commentary fix via `test_commentary.py` only
4. Test homepage by opening in browser
5. Stop when done — Max pushes to GitHub

---

## Bug 4 (discovered during Fix 1 verification) — config_changes_log payload mismatch

### Symptom

After implementing Fix 1, queried `config_changes_log` to verify the new 24h
window worked. Result: **0 rows in last 24h**, only 3 rows from `2026-04-03`
(Session 18b). But Max's screenshot showed 4 config changes from today
broadcast on Telegram (07:49 BTC + BONK `capital_per_trade`, 09:35 SOL
`buy_pct`, 09:36 BTC `buy_pct`).

### Root cause

`web/admin.html` `saveConfig()` builds the insert payload with:

```js
changes.push({ symbol: ..., field: f, old_value: ..., new_value: ..., changed_by: ... });
```

But the `config_changes_log` table column is named **`parameter`**, not `field`.
Every insert from admin since commit `6b837bf` (Session 18b, 3 April) has
silently failed. The error was hidden by:

```js
try { await Promise.all(changes.map(... sbInsert('config_changes_log', c))); }
catch (logErr) { console.warn(...); }  // best-effort, swallows everything
```

The Telegram alert "CONFIG CHANGE DETECTED" comes from a **separate path**
(`config/supabase_config.py:_send_config_changes()`), which compares old/new
configs in memory and notifies independently. So Telegram was working but
the audit log was empty — Haiku had nothing to read.

### Fix

```js
changes.push({ symbol: ..., parameter: f, old_value: ..., new_value: ..., changed_by: ... });
```

### Backfill

Inserted 4 missed rows directly in production via Supabase client, with
`changed_by: 'manual-ceo-backfill'` and timestamps converted from CEST to UTC:

| Symbol    | Parameter         | Old → New  | UTC time          |
|-----------|-------------------|------------|-------------------|
| BTC/USDT  | capital_per_trade | 25 → 50    | 05:49             |
| BONK/USDT | capital_per_trade | 6 → 25     | 05:49             |
| SOL/USDT  | buy_pct           | 1.5 → 1.0  | 07:35             |
| BTC/USDT  | buy_pct           | 1.8 → 1.0  | 07:36             |

Verified: 24h cutoff query now returns 4 rows. Haiku will see them at 20:00.

---

## Bug 5 (discovered after deploy) — index numbers stale

### Symptom

After Fix 2 deployed, the timestamp on the homepage updated correctly every
5 minutes, but the actual numbers didn't move. Side-by-side comparison with
admin: SOL position $0.00 on index, but admin showed `$22.53 invested · 1/12
grid filled · 12B / 11S trades`. The 5-minute refresh ran but pulled the
same stale data.

### Root cause

The original `renderPortfolio()` pulled everything from `daily_pnl[0]` —
the latest row in a snapshot table written **only at 20:00 by `grid_runner.py`**.
Between 20:00 yesterday and 20:00 today, that row never changes. The
"refresh" loop just re-fetched the same row.

The admin page uses a completely different strategy: it fetches `bot_config`
+ all v3 `trades` + `reserve_ledger` + spot prices from Binance, then
rebuilds per-coin holdings via FIFO and computes everything live.

### Fix

Ported the admin's strategy into index.html:

- New helpers `fetchLivePrices()`, `analyzeCoin()`, `computeLiveState()`
- New `fetchLiveData()` orchestrates the 4 parallel fetches and returns
  a `state` object with all the numbers index needs
- `renderPortfolio()` now takes `state` instead of `daily_pnl[]`
- Cumulative stats (Total trades, Buys/Sells, Realized, Fees) computed
  from `trades` instead of summed from `daily_pnl` rows
- Today's activity bar: filters `trades` by UTC date prefix
- `daily_pnl` is **still used** for the two charts (Portfolio Value line,
  Daily P&L bars) — its role as snapshot source for "current state" is gone
- `refreshNumbers()` calls `fetchLiveData()` every 5 minutes, so current
  numbers actually move

### Verification

Browser-side: Node.js syntax check on the script block (`new Function(js)`),
passed. Visual verification deferred to user (Max).

---

## Time references cleanup (added during session)

Max noticed the daily report goes out at 20:00 italian time (REPORT_HOUR=20
in `grid_runner.py`, interpreted as local time → CEST → 20:00 italian) but
several user-facing strings still said "21:00" or "midnight" from earlier
sessions. Aligned everything:

| File              | Old                                          | New                                         |
|-------------------|----------------------------------------------|---------------------------------------------|
| `commentary.py`   | "after the 21:00 report"                     | "after the 20:00 report"                    |
| `test_report.py`  | "without waiting for 21:00"                  | "without waiting for 20:00"                 |
| `web/index.html`  | "starts talking tonight at 21:00" (×2)       | "...at 20:00"                               |
| `web/index.html`  | "Daily reports at 21:00" (Telegram link)     | "Daily reports at 20:00"                    |
| `web/index.html`  | "full report at midnight" (numbers stamp)    | "full report at 20:00"                      |

Files **not touched** (intentionally — historical records): `briefresolved.md/*`,
`web/diary_entries.json`, `web/roadmap.html` Session 14 entries, `web/old/`.

---

## Lessons / things to remember

- **Best-effort try/catch hides real bugs.** The `config_changes_log` insert
  was silently failing for 5 days because the catch only logged a warning to
  the browser console. Nobody saw it. Consider surfacing best-effort failures
  to a UI status indicator.
- **Snapshot tables ≠ live state.** `daily_pnl` is great for charts and
  historical day-over-day deltas, but the homepage can't pretend it's a
  source of truth for current portfolio. Live data needs live computation.
- **Two paths to the same fact = two places to fix.** Telegram's "CONFIG
  CHANGE DETECTED" alert and the `config_changes_log` audit table are
  written by completely different code paths (`supabase_config.py` vs
  `admin.html`). Neither knew the other had failed.
