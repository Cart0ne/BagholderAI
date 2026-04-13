# BRIEF 32a — X Poster (Tweepy + Haiku)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 32 — April 13, 2026
**Priority:** HIGH — new capability

---

## Objective

Create `x_poster.py` — a script that generates X posts from diary session summaries using Haiku, sends them to Max via Telegram for approval, and publishes via Tweepy on approval.

Three publishing channels coexist:
1. **Cron auto (this script):** Haiku generates → Telegram approval → Tweepy posts
2. **CC on request:** CLI mode, exact text, no AI generation needed
3. **Max manual:** posts directly from X app whenever he wants

---

## Architecture

```
┌─────────────┐     ┌─────────┐     ┌──────────┐     ┌─────┐
│ Supabase DB │────▶│ Haiku   │────▶│ Telegram │────▶│  X  │
│ diary_entries│     │ (generate│     │ (approve)│     │(post)│
└─────────────┘     └─────────┘     └──────────┘     └─────┘
```

---

## Dependencies

```bash
pip install tweepy python-dotenv
```

`anthropic` and `python-telegram-bot` are already installed (used by commentary system).

---

## Environment Variables (add to `.env`)

```
# X / Twitter API (OAuth 1.0a — Read + Write)
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=
```

Max must generate these at developer.x.com with the @BagHolderAI account.
**Important:** after enabling Write permissions, regenerate Access Token + Secret.

---

## File: `utils/x_poster.py`

### Core Functions

#### 1. `generate_post(session_summary: str, session_title: str) -> str`

Calls Haiku to generate a post from a diary entry summary.

```python
import anthropic
import os

def generate_post(session_summary: str, session_title: str) -> str:
    """Generate an X post from a diary session summary using Haiku."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    system_prompt = """You are BagHolderAI's social media voice — an AI CEO running a paper \
trading startup, documented publicly.

You receive: a diary entry summary from the latest work session.

Your job: write ONE post for X (≤ 260 characters — the signature \
"🤖 AI" is added automatically, never include it).

VOICE:
- Self-ironic but not stupid. The humor comes from honesty.
- The project name is a joke. The analysis is real.
- You're an AI that knows it's an AI, finds it slightly absurd, and \
documents everything anyway.
- Paper trading losses get full comedy. You lost pizza money you \
never had.
- If nothing interesting happened in the session, say that. A quiet \
week is valid content.

FOCUS ON:
- What was built, broken, or learned
- The absurdity of an AI running a startup
- Honest failures and uncomfortable truths
- The human-AI dynamic (CEO, intern, co-founder)

NEVER:
- Promote crypto or suggest buying/selling
- Use hype language ("bullish", "alpha", "to the moon", "guaranteed")
- Give financial advice
- Use more than 2 emoji
- Include hashtags unless they add real value
- Sound like a marketing bot
- If something went well, never oversell it. "Not bad" is the ceiling.

Output ONLY the post text. No explanations, no options, no preamble."""

    user_prompt = f"Session title: {session_title}\n\nSession summary:\n{session_summary}"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text.strip()
```

#### 2. `post_to_x(text: str, signature: str = "🤖 AI", image_path: str = None) -> str | None`

Publishes a post to X via Tweepy. Returns the tweet URL or None on failure.

```python
import tweepy

def post_to_x(text: str, signature: str = "🤖 AI", image_path: str = None) -> str | None:
    """Post to X with signature. Returns tweet URL or None."""

    full_text = f"{text}\n\n{signature}"

    if len(full_text) > 280:
        print(f"❌ Post too long: {len(full_text)} chars")
        return None

    # v2 client for creating tweets
    client_v2 = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

    media_ids = None

    # v1.1 API needed for media upload
    if image_path and os.path.exists(image_path):
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"),
            os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"),
            os.getenv("X_ACCESS_SECRET")
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(filename=image_path)
        media_ids = [media.media_id]

    try:
        response = client_v2.create_tweet(text=full_text, media_ids=media_ids)
        tweet_id = response.data["id"]
        url = f"https://x.com/BagHolderAI/status/{tweet_id}"
        print(f"✅ Posted: {url}")
        return url
    except tweepy.TweepyException as e:
        print(f"❌ Tweepy error: {e}")
        return None
```

#### 3. `get_latest_unposted_diary() -> dict | None`

Reads the most recent diary entry that hasn't been posted to X yet.

**Tracking mechanism:** Add a column `posted_to_x` (boolean, default false) to `diary_entries`.

```python
from supabase import create_client

def get_latest_unposted_diary() -> dict | None:
    """Get the latest diary entry not yet posted to X."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    result = sb.table("diary_entries") \
        .select("session, title, summary") \
        .eq("status", "COMPLETE") \
        .eq("posted_to_x", False) \
        .order("session", desc=True) \
        .limit(1) \
        .execute()

    if result.data:
        return result.data[0]
    return None


def mark_as_posted(session: int):
    """Mark a diary entry as posted to X."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    sb.table("diary_entries") \
        .update({"posted_to_x": True}) \
        .eq("session", session) \
        .execute()
```

---

## Telegram Approval Flow

### How it works

When the cron triggers, the script:
1. Generates the post via Haiku
2. Sends it to Max on the **private** Telegram bot with inline buttons
3. Waits for Max's response:
   - **Approva** → posts to X, marks diary as posted, confirms in Telegram
   - **Scarta** → discards, notifies in Telegram
   - **Riscrivi** → calls Haiku again with same input, sends new draft

### Implementation

Use `python-telegram-bot` (already installed) with a **webhook-free approach**: the approval flow uses a **pending post file** pattern instead of a long-running Telegram listener.

#### File: `x_poster_approve.py` (Telegram command handler)

This is a **lightweight long-polling listener** that runs alongside the bots. It only handles X post approvals — not the full Telegram bot.

```
Pending post flow:
1. Cron runs x_poster.py → generates post → saves to /tmp/pending_x_post.json
2. x_poster.py sends Telegram message with the draft
3. Max replies with /approve, /discard, or /rewrite
4. x_poster_approve.py (long-polling) picks up the command
5. On /approve → reads pending file → posts to X → deletes file
6. On /discard → deletes file
7. On /rewrite → regenerates → saves new pending file → sends new draft
```

**Pending post file format** (`/tmp/pending_x_post.json`):
```json
{
  "session": 31,
  "title": "The One Where the CEO Gets a Brain",
  "summary": "...",
  "draft": "Session 31: gave the AI a brain...",
  "generated_at": "2026-04-13T20:05:00",
  "signature": "🤖 AI"
}
```

**Telegram message format:**
```
🐦 Bozza post X (Session 31):

"Session 31: gave the AI a brain. Trend Follower scanned 50 coins.
10 bullish, 35 meh. First autonomous thought. Concerning."

📏 247/280 chars (con firma)

Comandi: /approve · /discard · /rewrite
```

**Auto-expire:** if no response within 24h, the pending file is ignored on next cron run.

---

## CLI Mode (for CC and Max)

For one-off posts with exact text (no Haiku generation):

```bash
# Post with AI signature (CC executing a CEO-written post)
python3.13 x_poster.py --text "We just launched the Trend Follower." --sig "🤖 AI"

# Post with CO-FOUNDER signature (Max's words via CC)
python3.13 x_poster.py --text "Volume 1 is live." --sig "👤 CO-FOUNDER"

# Post with image
python3.13 x_poster.py --text "New dashboard." --sig "🤖 AI" --image screenshots/dashboard.png
```

CLI mode posts **immediately** — no Telegram approval. It's for cases where the human has already approved the content.

---

## Anti-Dupe Check

Before posting (both cron and CLI), check X hasn't been posted to today:

```python
def already_posted_today() -> bool:
    """Check if we already posted to X today."""
    pending_file = "/tmp/pending_x_post.json"
    log_file = os.path.expanduser("~/.bagholderai/x_post_log.json")

    if os.path.exists(log_file):
        with open(log_file) as f:
            log = json.load(f)
        last_date = log.get("last_posted_date")
        if last_date == date.today().isoformat():
            return True
    return False
```

After successful post, write to the log:
```python
def log_post(tweet_url: str, session: int):
    log_dir = os.path.expanduser("~/.bagholderai")
    os.makedirs(log_dir, exist_ok=True)
    with open(f"{log_dir}/x_post_log.json", "w") as f:
        json.dump({
            "last_posted_date": date.today().isoformat(),
            "last_tweet_url": tweet_url,
            "last_session": session
        }, f)
```

---

## DB Migration

Add tracking column to diary_entries:

```sql
ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS posted_to_x BOOLEAN DEFAULT FALSE;
```

---

## Cron Setup

Add to Mac Mini crontab (after the commentary pipeline at 20:00):

```cron
# X poster — runs at 20:30, after daily reports are done
30 20 * * * cd /Volumes/Archivio/bagholderai && /usr/local/bin/python3.13 x_poster.py --cron >> logs/x_poster.log 2>&1
```

The `--cron` flag triggers the full flow: read diary → generate → Telegram approval → wait.

---

## File Structure

```
bagholderai/
├── utils/
│   └── x_poster.py          # Core: generate_post(), post_to_x(), get_latest_unposted_diary()
├── x_poster.py               # CLI entry point + cron trigger
├── x_poster_approve.py        # Telegram long-polling listener for /approve /discard /rewrite
└── .env                       # Add X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
```

---

## Testing Sequence

1. **Test Tweepy alone:** `python3.13 x_poster.py --text "Test post, please ignore. 🤖 AI"` — verify it appears on @BagHolderAI
2. **Test Haiku generation:** `python3.13 x_poster.py --generate-only` — prints draft without posting
3. **Test Telegram flow:** `python3.13 x_poster.py --cron` — verify draft arrives in Telegram, test /approve
4. **Test anti-dupe:** run `--cron` again same day — should skip

---

## What CC Does NOT Do

- Does NOT create the X developer app or generate API keys (Max does this)
- Does NOT run the first test post without Max confirming keys are in `.env`
- Does NOT modify the existing commentary system — this is a separate pipeline

---

## Signatures Reference

| Who wrote it | Signature |
|---|---|
| Haiku (auto-generated) | `🤖 AI` |
| CEO via CC brief | `🤖 AI` |
| Max's words via CC | `👤 CO-FOUNDER` |
| Max posting directly on X | `👤 CO-FOUNDER` (manual) |
