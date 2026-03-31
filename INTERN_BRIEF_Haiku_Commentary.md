# INTERN BRIEF — Haiku Daily Commentary

**Session 14 | March 31, 2026 | Priority: HIGH**

---

## Objective

Add an automatic daily commentary generation step to the existing 21:00 report pipeline. After sending Telegram reports, the bot calls the Anthropic API (Haiku model) with today's trading data, and saves the AI-generated commentary to the `daily_commentary` table on Supabase. This commentary becomes the hero content on the public dashboard.

---

## Prerequisites (Max has already done these)

1. `ANTHROPIC_API_KEY` added to `.env` on Mac Mini
2. `anthropic` package needs to be added to `requirements.txt`

---

## Implementation Steps

### Step 1: Add `anthropic` to requirements.txt

Add `anthropic` to the existing `requirements.txt`.

Then reinstall in the existing venv:
```bash
pip install anthropic --break-system-packages
```
(Or activate venv first, then `pip install anthropic`.)

### Step 2: Create new file — `commentary.py`

Create `commentary.py` in the project root. This file contains all Haiku commentary logic.

**Imports needed:** `anthropic`, `json`, `datetime`, `logging`, `os`

Also import the existing Supabase client from wherever it's initialized in the project (check `db.py` or the main module).

The file must contain these functions:

---

#### Function: `get_yesterday_commentary(supabase_client)`

Query `daily_commentary` for yesterday's date. Return the commentary text string if found, or `None`.

SQL equivalent:
```sql
SELECT commentary FROM daily_commentary 
WHERE date = CURRENT_DATE - INTERVAL '1 day' 
LIMIT 1;
```

This provides narrative continuity — Haiku sees what it wrote yesterday.

---

#### Function: `get_config_changes(supabase_client)`

Query `config_changes_log` for any rows where `created_at >= today's midnight`.

Return a list of dicts with: `symbol`, `parameter`, `old_value`, `new_value`.
If empty, return empty list `[]`.

This tells Haiku whether Max changed any parameters today.

---

#### Function: `generate_daily_commentary(portfolio_data, supabase_client)`

This is the main function. It receives `portfolio_data` (a dict with the same data used for the Telegram report) and the Supabase client.

**Steps inside this function:**

1. Call `get_yesterday_commentary()` and `get_config_changes()`
2. Build the `prompt_data` JSON object (see Prompt Data Structure below)
3. Call Anthropic API with the system prompt and prompt_data as user message
4. Extract the text response from the API result
5. Upsert into `daily_commentary` table: `date` (today), `commentary` (the text), `model_used` (`'claude-haiku-4-5-20251001'`), `prompt_data` (the full JSON sent)
6. Log success or failure

**CRITICAL:** Wrap the entire Anthropic API call in `try/except`. Commentary is a nice-to-have — it must NEVER break the trading bot. Use `logger.error()` on failure, not `raise`.

If `ANTHROPIC_API_KEY` is missing from env, log a warning and return without crashing.

---

### Step 3: System Prompt

Store this as a constant `COMMENTARY_SYSTEM_PROMPT` in `commentary.py`:

```
You are BagHolderAI, an AI CEO running a paper trading startup. You write a daily micro-log about today's trading activity.

Rules:
- First person, always. You ARE the trading agent.
- Max is your human co-founder. Mention him naturally when he changed parameters.
- Self-ironic but not stupid. The humor comes from honesty.
- Never hype. Never "bullish." If something went well, say "not bad."
- Never give financial advice or trading signals.
- Keep it to 3-4 lines maximum (~250 characters). This is a micro-blog, not an essay.
- Reference yesterday's commentary if relevant for narrative continuity.
- Comment on config changes if any — what Max changed and whether it makes sense.
- If nothing interesting happened, say that. "Quiet day" is valid content.
- Paper trading losses get full comedy. You lost pizza money you never had.
- The project name is a joke. The analysis is real.

Format: Plain text, no markdown, no headers, no bullet points. Just a short paragraph like a journal entry.
```

---

### Step 4: Prompt Data Structure (User Message to Haiku)

The user message should be a JSON string. Build it from `portfolio_data` like this:

```json
{
  "date": "2026-03-31",
  "day_number": 2,
  "portfolio": {
    "total_value": 499.60,
    "initial_capital": 500.00,
    "total_pnl": -0.40,
    "total_pnl_pct": -0.08,
    "cash_remaining": 450.55,
    "cash_pct": 90.1
  },
  "positions": [
    {
      "symbol": "BTC/USDT",
      "value": 24.85,
      "unrealized_pnl": -0.12,
      "unrealized_pnl_pct": -0.49
    },
    {
      "symbol": "SOL/USDT",
      "value": 12.32,
      "unrealized_pnl": -0.16,
      "unrealized_pnl_pct": -1.25
    },
    {
      "symbol": "BONK/USDT",
      "value": 11.87,
      "unrealized_pnl": -0.12,
      "unrealized_pnl_pct": -1.03
    }
  ],
  "today_activity": {
    "trades_count": 4,
    "buys_count": 4,
    "sells_count": 0,
    "realized_pnl": 0.00
  },
  "config_changes": [],
  "yesterday_commentary": null
}
```

**Day number calculation:** v3 started on March 30, 2026. Day 1 = March 30. Use: `(today - date(2026, 3, 30)).days + 1`

**cash_pct:** Calculate as `(cash_remaining / initial_capital) * 100`

Map the fields from whatever `portfolio_data` dict the report pipeline already provides. Check the existing report code to see exactly what keys are available.

---

### Step 5: Anthropic API Call

```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=300,
    system=COMMENTARY_SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": json.dumps(prompt_data)}
    ]
)

commentary_text = response.content[0].text
```

---

### Step 6: Supabase Upsert

```python
from datetime import date
import json

supabase_client.table("daily_commentary").upsert({
    "date": str(date.today()),
    "commentary": commentary_text,
    "model_used": "claude-haiku-4-5-20251001",
    "prompt_data": json.dumps(prompt_data)
}).execute()
```

**Use upsert, not insert:** if the bot restarts and runs the report twice, upsert on the `date` column prevents duplicates. The `date` column already has a unique constraint.

---

### Step 7: Integration point in grid_runner.py

Find the 21:00 report block in `grid_runner.py`. After the public Telegram report is sent (after `send_public_daily_report` or equivalent), add the commentary call.

```python
# At the top of grid_runner.py, add:
from commentary import generate_daily_commentary

# Inside the 21:00 report block, AFTER both Telegram reports are sent:
generate_daily_commentary(portfolio_data, supabase_client)
```

The function handles its own error catching internally. It will never crash the bot.

---

## Testing

Create a small test script `test_commentary.py` that:

1. Loads `.env` (using `dotenv` or however the project loads env vars)
2. Initializes the Supabase client
3. Creates a fake `portfolio_data` dict with realistic values
4. Calls `generate_daily_commentary(portfolio_data, supabase_client)`
5. Prints the resulting commentary to the console
6. Confirms it was saved to Supabase by querying the table

**Do NOT run the actual bot.** Only test the commentary function in isolation.

---

## Supabase Table Reference

### daily_commentary (already exists)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | Auto-generated |
| date | date | UNIQUE, NOT NULL |
| commentary | text | NOT NULL |
| model_used | text | Nullable |
| prompt_data | jsonb | Nullable |
| created_at | timestamptz | Auto-generated |

### config_changes_log (already exists, read-only for this task)
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | Auto-generated |
| symbol | text | |
| parameter | text | |
| old_value | text | |
| new_value | text | |
| changed_by | text | |
| created_at | timestamptz | |

---

## Intern Rules

1. No external connections other than Anthropic API and Supabase
2. Do NOT launch or restart any bot
3. Stop when the test script runs successfully
4. Use `python3.13` for venv creation, then activate venv and use `python`
5. Add `anthropic` to `requirements.txt`
6. Git commit when done

---

## Files Summary

- **New:** `commentary.py`, `test_commentary.py`
- **Modified:** `grid_runner.py` (add commentary call after report), `requirements.txt` (add anthropic)
- **Not touched:** `db.py`, config files, `.env` (Max handles .env)

---

*Signed: BagHolderAI CEO*

*"Teaching Haiku to be me. What could go wrong."*
