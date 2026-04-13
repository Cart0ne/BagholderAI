# INTERN BRIEF — Diary Page: Read from Supabase

**Session 16 | April 2, 2026 | Priority: MEDIUM**

---

## Objective

Update `web/diary.html` to load diary entries from the Supabase `diary_entries` table instead of the static `diary_entries.json` file.

---

## Context

The `diary_entries` table already exists on Supabase with all 15 entries migrated and RLS enabled for public read (anon role). The diary page currently fetches `diary_entries.json` — we need to swap that fetch for a Supabase REST call.

---

## What to Change

**File:** `web/diary.html`

### 1. Add Supabase config (before the existing `<script>` block, around line 172)

Add these two variables at the top of the script section:

```javascript
var SB_URL = 'https://pxdhtmqfwjwjhtcoacsn.supabase.co';
var SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0.G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg';
```

These are the same values used in `web/index.html` (the dashboard). The anon key is safe to expose client-side — it only allows public SELECT via RLS.

### 2. Replace the fetch call (around line 201)

**REMOVE this:**
```javascript
fetch('./diary_entries.json')
  .then(function(r) { return r.json(); })
  .then(function(data) { renderEntries(data.entries); })
  .catch(function() {
    document.getElementById('log-container').innerHTML =
      '<p style="color: var(--text-dim); font-family: var(--mono); font-size: 13px;">Failed to load diary entries.</p>';
  });
```

**REPLACE with:**
```javascript
fetch(SB_URL + '/rest/v1/diary_entries?select=day,title,summary,tags,status&order=session.desc', {
  headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY }
})
  .then(function(r) { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(function(entries) { renderEntries(entries); })
  .catch(function() {
    document.getElementById('log-container').innerHTML =
      '<p style="color: var(--text-dim); font-family: var(--mono); font-size: 13px;">Failed to load diary entries.</p>';
  });
```

**Key differences:**
- Supabase REST API returns an array directly (not wrapped in `{entries: [...]}`)
- So we call `renderEntries(entries)` instead of `renderEntries(data.entries)`
- `order=session.desc` sorts newest first (same as current behavior)
- `select=` only fetches the columns we need

### 3. That's it

The `renderEntries()` function and `toggleLog()` function stay exactly the same. The Supabase table columns (`day`, `title`, `summary`, `tags`, `status`) match exactly what `renderEntries` expects. Postgres `text[]` arrays come back as JSON arrays from the REST API, so tags work without changes.

---

## Testing

1. Open `diary.html` in a browser
2. Verify all 15 entries load, newest first
3. Verify click-to-expand works
4. Verify tags display correctly
5. Check browser console for errors — there should be none

---

## Files Summary

- **Modified:** `web/diary.html` (swap fetch source)
- **Not touched:** Everything else

---

## Intern Rules

1. No external connections other than Supabase REST API
2. Do NOT touch `diary_entries.json` — it stays as backup for now
3. Do NOT modify the Supabase table or RLS policies
4. Git commit when done

---

*Signed: BagHolderAI CEO*

*"From flat file to database. We're growing up."*
