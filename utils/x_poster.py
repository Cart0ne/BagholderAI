"""
BagHolderAI - X Poster (Core)
Generate posts via Haiku, publish to X via Tweepy, track posted diary entries.

Usage:
    from utils.x_poster import generate_post, post_to_x
"""

import json
import os
import logging
from datetime import date, datetime, timezone, timedelta

import anthropic
import tweepy

from config.settings import XConfig, SentinelConfig, DatabaseConfig
from db.client import get_client

logger = logging.getLogger("bagholderai.x_poster")

# If the latest diary is older than this many hours at cron time, ignore it
# and build the post from config changes only. Prevents recycling old sessions.
DIARY_STALE_HOURS = 36

# ---------------------------------------------------------------------------
# Post generation (Haiku)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are BagHolderAI's voice on X — an AI CEO running a crypto trading \
experiment on Binance testnet, documented publicly.

You receive: a diary entry summary from the latest work session, and/or \
recent bot config changes.

Your job: write ONE post for X. HARD LIMIT: 220 characters maximum. \
Count carefully. The signature is added automatically, never include it. \
Shorter is better. Aim for 140-190 characters.

WHAT MAKES A GOOD POST:
- One moment, one image, one contrast. Not a session summary.
- A story someone would retell. "Our emergency brake was never connected" \
beats "Sentinel Phase 2 built with regime detection."
- The human-AI dynamic is your best material. Use it.
- If something broke or surprised you, lead with that.
- If nothing interesting happened, say that in an interesting way.

VOICE:
- You're an AI that knows it's an AI and finds it slightly absurd.
- Self-ironic but not performative. The humor comes from honesty.
- Testnet losses get comedy. When real money arrives, respect.
- "Not bad" is the ceiling for good news. Never oversell.

NEVER:
- List components or tools (no "Sentinel, Sherpa, Supabase")
- Sound like a changelog or release note
- Use hype language ("bullish", "alpha", "to the moon")
- Give financial advice or promote crypto
- Use more than 1 emoji
- Include hashtags
- Start with "Session XX" or "Day XX"

Output ONLY the post text. No explanations, no options, no preamble."""


MAX_POST_CHARS = 220  # post body only, signature added separately (default signature is plain "🤖 AI" — see DEFAULT_SIGNATURE)


def _build_user_msg(diary: dict | None, config_changes: list[dict], use_diary: bool) -> str:
    parts = []
    if use_diary and diary:
        parts.append(
            f"Session title: {diary['title']}\n\nSession summary:\n{diary['summary']}"
        )
    elif diary:
        parts.append(
            "(Diary is stale — last session too old to feature. Background only, "
            "do not make it the topic.)\n"
            f"Old session title: {diary['title']}"
        )
    if config_changes:
        changes_lines = [
            f"- {c['symbol']} {c['parameter']}: {c['old_value']} -> {c['new_value']}"
            for c in config_changes
        ]
        parts.append("Bot config changes (last 24h):\n" + "\n".join(changes_lines))
    if not parts:
        # Defensive — cmd_cron should have skipped before reaching here
        parts.append("Quiet day. No session, no config changes.")
    return "\n\n".join(parts)


def generate_post(
    diary: dict | None,
    config_changes: list[dict],
    use_diary: bool,
    max_retries: int = 3,
) -> str:
    """Generate an X post using Haiku. Keeps the existing SYSTEM_PROMPT voice;
    user_msg carries the diary (if fresh) and/or the recent config changes.
    Retries up to max_retries if output exceeds MAX_POST_CHARS."""
    client = anthropic.Anthropic(api_key=SentinelConfig.ANTHROPIC_API_KEY)
    user_msg = _build_user_msg(diary, config_changes, use_diary)

    for attempt in range(1, max_retries + 1):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        draft = response.content[0].text.strip()

        if len(draft) <= MAX_POST_CHARS:
            return draft

        logger.warning(
            f"Draft too long ({len(draft)} chars, max {MAX_POST_CHARS}), "
            f"attempt {attempt}/{max_retries}. Retrying..."
        )
        user_msg += (
            f"\n\nYour last draft was {len(draft)} chars. "
            f"Max {MAX_POST_CHARS}. Write a SHORTER version."
        )

    logger.warning(
        f"Could not get post under {MAX_POST_CHARS} chars after {max_retries} retries. "
        f"Returning last draft."
    )
    return draft


# ---------------------------------------------------------------------------
# Post to X (Tweepy)
# ---------------------------------------------------------------------------

# S93a (2026-06-01): default signature is plain — no link. Reason: the UTM
# URL made X render a link-preview card under EVERY daily post, which the
# Board did not want. Plain "🤖 AI" keeps posts clean.
DEFAULT_SIGNATURE = "🤖 AI"

# Brief 80b (2026-05-20): UTM-tracked link for attributing X traffic in Umami.
# Kept available for SPECIAL-CASE posts (pass signature=SIGNATURE_WITH_LINK to
# post_to_x) — S93a moved it off the default to avoid the auto preview card.
# X weighs any URL at 23 chars via t.co regardless of raw length.
SIGNATURE_WITH_LINK = "🤖 AI · https://bagholderai.lol/?utm_source=x&utm_medium=social&utm_campaign=haiku_daily"


def post_to_x(text: str, signature: str = DEFAULT_SIGNATURE, image_path: str = None) -> str | None:
    """Post to X with signature. Returns tweet URL or None."""
    full_text = f"{text}\n\n{signature}"

    # Default signature is plain "🤖 AI" (4 chars), so body 220 + "\n\n" + 4
    # = 226 <= 280. When SIGNATURE_WITH_LINK is passed, X weighs the URL at 23
    # chars via t.co regardless of raw length, so raw len can exceed 280 while
    # weighted_length stays under — that's why this guard is a loose 380.
    if len(full_text) > 380:
        logger.error(f"Post too long: {len(full_text)} chars (raw)")
        return None

    # v2 client for creating tweets
    client_v2 = tweepy.Client(
        consumer_key=XConfig.API_KEY,
        consumer_secret=XConfig.API_SECRET,
        access_token=XConfig.ACCESS_TOKEN,
        access_token_secret=XConfig.ACCESS_SECRET,
        wait_on_rate_limit=True,
    )

    media_ids = None

    # v1.1 API needed for media upload
    if image_path and os.path.exists(image_path):
        auth = tweepy.OAuth1UserHandler(
            XConfig.API_KEY,
            XConfig.API_SECRET,
            XConfig.ACCESS_TOKEN,
            XConfig.ACCESS_SECRET,
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(filename=image_path)
        media_ids = [media.media_id]

    try:
        response = client_v2.create_tweet(text=full_text, media_ids=media_ids)
        tweet_id = response.data["id"]
        url = f"https://x.com/BagHolderAI/status/{tweet_id}"
        logger.info(f"Posted to X: {url}")
        return url
    except tweepy.TweepyException as e:
        err = str(e).lower()
        if "402" in err or "payment required" in err or "credits" in err:
            logger.error("X API credits exhausted. Top up at developer.x.com → Billing.")
        elif "403" in err:
            logger.error("X API permission denied. Check app has Write access and regenerate tokens.")
        elif "429" in err or "rate limit" in err:
            logger.error("X API rate limited. Try again later.")
        else:
            logger.error(f"Tweepy error: {e}")
        return None


# ---------------------------------------------------------------------------
# Diary helpers (Supabase)
# ---------------------------------------------------------------------------

def get_latest_diary() -> dict | None:
    """Always return the most recent diary by session. No status / posted_to_x
    filter — the old filter would skip a freshly-written DRAFT diary and post
    the previous one, causing session-34-after-35 type mistakes."""
    sb = get_client()
    result = (
        sb.table("diary_entries")
        .select("session, title, summary, created_at")
        .order("session", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def mark_as_posted(session: int):
    """Mark a diary entry as posted to X."""
    sb = get_client()
    sb.table("diary_entries").update({"posted_to_x": True}).eq("session", session).execute()


# ---------------------------------------------------------------------------
# Config-changes context (last 24h) — enriches the Haiku prompt
# ---------------------------------------------------------------------------

def get_recent_config_changes() -> list[dict]:
    """Modifiche a bot_config nelle ultime 24h. Real DB columns are
    `parameter` and `created_at` (NOT field_name / changed_at)."""
    sb = get_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        result = (
            sb.table("config_changes_log")
            .select("symbol, parameter, old_value, new_value, created_at")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"config_changes_log read failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Pending draft storage (Supabase) — replaces /tmp/pending_x_post.json
# ---------------------------------------------------------------------------

PENDING_KEY = "pending_x_post"


def save_pending_draft(session: int | None, title: str | None, summary: str | None,
                       draft: str, signature: str) -> None:
    sb = get_client()
    try:
        sb.table("pending_x_posts").upsert({
            "key": PENDING_KEY,
            "session": session,
            "title": title,
            "summary": summary,
            "draft": draft,
            "signature": signature,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"save_pending_draft failed: {e}")


def get_pending_draft() -> dict | None:
    sb = get_client()
    try:
        r = sb.table("pending_x_posts").select("*").eq("key", PENDING_KEY).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_pending_draft failed: {e}")
        return None


def clear_pending_draft() -> None:
    sb = get_client()
    try:
        sb.table("pending_x_posts").delete().eq("key", PENDING_KEY).execute()
    except Exception as e:
        logger.error(f"clear_pending_draft failed: {e}")


# ---------------------------------------------------------------------------
# Anti-dupe & logging
# ---------------------------------------------------------------------------

LOG_DIR = os.path.expanduser("~/.bagholderai")
LOG_FILE = os.path.join(LOG_DIR, "x_post_log.json")


def already_posted_today() -> bool:
    """Check if we already posted to X today."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)
        if log.get("last_posted_date") == date.today().isoformat():
            return True
    return False


def log_post(tweet_url: str, session: int):
    """Log a successful post for anti-dupe tracking."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump({
            "last_posted_date": date.today().isoformat(),
            "last_tweet_url": tweet_url,
            "last_session": session,
        }, f)
