# Brief 81b — Haiku Commentary: Direction Safety + Shorter Output

**Date:** 2026-05-22 (Session 81)
**Based on:** PROJECT_STATE.md 2026-05-22 + audit 60 daily_commentary entries
**Author:** CEO
**Estimated effort:** 30-45 min
**Priority:** MEDIUM — quality-of-life, not blocking

---

## Context

Audit of all 60 `daily_commentary` entries found 1 factual error out of 60 (Day 15, 2026-05-22): Haiku wrote "portfolio at -5.03%, which is somehow marginally better than yesterday's -4.12%". -5.03% is worse than -4.12%, not better. Classic small-model confusion on negative number comparison.

The error was manually corrected in Supabase. This brief prevents recurrence and tightens output length.

**Root cause:** Haiku receives today's numbers as structured JSON, but yesterday's numbers only as free text inside `yesterday_commentary`. To compare, it must parse a percentage from prose and reason about negative numbers — a known weak spot for small models.

---

## Two Changes

### Change 1 — `vs_yesterday` structured field in prompt_data

**File:** `bot/commentary.py` (inside `generate_daily_commentary` or wherever prompt_data is assembled)

Before calling Haiku, query `daily_commentary` for the previous day's entry. Extract yesterday's `prompt_data` → `aggregate_portfolio.total_pnl_pct`. Then add a new top-level field to today's prompt_data:

```json
"vs_yesterday": {
  "yesterday_pnl_pct": -4.12,
  "today_pnl_pct": -5.03,
  "change_pp": -0.91,
  "direction": "worse"
}
```

Logic for `direction` (Python, not Haiku):
- `"better"` if today_pnl_pct > yesterday_pnl_pct + 0.1
- `"worse"` if today_pnl_pct < yesterday_pnl_pct - 0.1
- `"flat"` otherwise

If yesterday's entry doesn't exist (day 1, gap, DB error), **omit the `vs_yesterday` block entirely**. Haiku won't make a comparison it can't make.

**Note:** `yesterday_commentary` stays in the prompt as before — Haiku needs it for narrative continuity and tone. The new field is for numbers only.

### Change 2 — System prompt: shorter + no parrot numbers + use direction field

Add/modify these instructions in the existing system prompt (do NOT rewrite the whole prompt — preserve the character voice and personality instructions that are already there):

**Add these rules** (exact wording can be adapted to fit the existing prompt style):

```
LENGTH: Write 80 words. Never exceed 100. Every word must earn its place.

NUMBERS: The reader already has the portfolio data. Do NOT list each coin's percentage individually unless something changed dramatically (>3pp move in a single day). Give the meaning, not the data.

DIRECTION: When comparing today's performance to yesterday, ALWAYS use the vs_yesterday.direction field if present. Do not independently calculate whether the portfolio improved or worsened.
```

---

## Decisioni delegate a CC

- Exact placement of the three rules within the existing system prompt (CC reads the current prompt and fits them in naturally)
- How to query yesterday's entry (by date arithmetic or by ordering — CC picks the simplest approach)
- Whether `vs_yesterday` source is the previous `daily_commentary.prompt_data` or the previous `daily_pnl` row (both have the aggregate pnl_pct — pick whichever is simpler)

## Decisioni che CC DEVE chiedere al Board

- If `commentary.py` structure requires changes beyond the two blocks described here (e.g. function signature changes that touch `daily_report.py`)
- If the current system prompt already contains length or formatting instructions that conflict with the new rules

## Output atteso a fine sessione

1. `commentary.py` updated with `vs_yesterday` field generation
2. System prompt updated with the three new rules
3. No other files changed (no schema change, no migration, no restart needed — the change takes effect at next 21:00 report)

## Vincoli

- **NON riscrivere** il system prompt da zero — aggiungi le regole al prompt esistente
- **NON toccare** `daily_report.py` beyond the import if needed
- **NON toccare** nessun file di trading logic
- **NON modificare** lo schema di `daily_commentary` (il campo `prompt_data` è già JSONB, il nuovo blocco ci entra dentro)
- Push diretto su main, no PR
- Il prossimo restart del Mac Mini applicherà la modifica; non serve restart immediato

## Roadmap impact

Nessuno. Quality-of-life fix, non cambia timeline né sequenza.
