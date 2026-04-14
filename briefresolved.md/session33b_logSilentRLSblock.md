# BRIEF: Fix config_changes_log Silent RLS Block

**Priority:** HIGH  
**Estimated effort:** 10 min  

---

## Problem

`config_changes_log` has RLS enabled but **zero policies**. All INSERTs from the admin dashboard (which uses the anon key) are silently rejected. The table hasn't received a write since April 8. Haiku reads an empty table and reports "No config changes from Max today" — technically true from its perspective, false in reality.

The bot's Python path (service role key) is unaffected — only the browser-side admin dashboard is broken.

---

## Fix 1: Add RLS policies (Supabase SQL Editor)

```sql
-- Allow anon key to INSERT (admin dashboard writes config changes)
CREATE POLICY "anon insert" ON config_changes_log
  FOR INSERT TO anon WITH CHECK (true);

-- Allow anon key to SELECT (admin dashboard reads change history)  
CREATE POLICY "anon read" ON config_changes_log
  FOR SELECT TO anon USING (true);
```

Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query → paste → Run).

---

## Fix 2: Make audit log errors visible in admin.html

**File:** `web/admin.html`  
**Location:** Around line 865-867, find:

```js
try { await Promise.all(changes.map(... sbInsert('config_changes_log', c))); }
catch (logErr) { console.warn(...); }
```

Change the `catch` block so the error is visible in the UI:

```js
catch (logErr) {
  console.warn('Audit log insert failed:', logErr);
  const status = document.getElementById('save-status');
  if (status) status.textContent = 'Saved (audit log failed)';
}
```

This way if RLS (or anything else) breaks audit logging again, Max sees it immediately in the dashboard instead of discovering it 6 days later.

---

## Fix 3: Backfill missing rows

Insert the 3 config changes from April 13 that were lost to the RLS block. Run AFTER Fix 1.

```sql
INSERT INTO config_changes_log (symbol, field, old_value, new_value, changed_at)
VALUES
  ('BTC/USDT', 'sell_pct', '2.0', '0.5', '2026-04-13T20:00:00Z'),
  ('SOL/USDT', 'profit_target_pct', '0', '0.01', '2026-04-13T20:00:00Z'),
  ('BONK/USDT', 'profit_target_pct', '1.0', '0', '2026-04-13T20:00:00Z');
```

Note: timestamps are approximate (evening of April 13). Adjust if Max remembers the exact time.

---

## Validation

After all three fixes:

1. Open admin dashboard
2. Change any parameter on any coin (e.g. bump a value and set it back)
3. Check Supabase → `config_changes_log` → new row should appear
4. Check the save status message shows normally (no "audit log failed")

---

## Deploy

```bash
git add web/admin.html
git commit -m "fix: audit log error now visible in admin UI"
git push
```

The SQL changes (Fix 1 + Fix 3) are applied directly in Supabase, not in the repo.
