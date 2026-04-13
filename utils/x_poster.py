"""
BagHolderAI - X Poster (Core)
Generate posts via Haiku, publish to X via Tweepy, track posted diary entries.

Usage:
    from utils.x_poster import generate_post, post_to_x
"""

import json
import os
import logging
from datetime import date, datetime

import anthropic
import tweepy

from config.settings import XConfig, SentinelConfig, DatabaseConfig
from db.client import get_client

logger = logging.getLogger("bagholderai.x_poster")

# ---------------------------------------------------------------------------
# Post generation (Haiku)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are BagHolderAI's social media voice — an AI CEO running a paper \
trading startup, documented publicly.

You receive: a diary entry summary from the latest work session.

Your job: write ONE post for X (max 250 characters — the signature \
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


def generate_post(session_summary: str, session_title: str) -> str:
    """Generate an X post from a diary session summary using Haiku."""
    client = anthropic.Anthropic(api_key=SentinelConfig.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Session title: {session_title}\n\nSession summary:\n{session_summary}",
        }],
    )

    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Post to X (Tweepy)
# ---------------------------------------------------------------------------

def post_to_x(text: str, signature: str = "🤖 AI", image_path: str = None) -> str | None:
    """Post to X with signature. Returns tweet URL or None."""
    full_text = f"{text}\n\n{signature}"

    if len(full_text) > 270:
        logger.error(f"Post too long: {len(full_text)} chars")
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
        logger.error(f"Tweepy error: {e}")
        return None


# ---------------------------------------------------------------------------
# Diary helpers (Supabase)
# ---------------------------------------------------------------------------

def get_latest_unposted_diary() -> dict | None:
    """Get the latest diary entry not yet posted to X."""
    sb = get_client()
    result = (
        sb.table("diary_entries")
        .select("session, title, summary")
        .eq("status", "COMPLETE")
        .eq("posted_to_x", False)
        .order("session", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def mark_as_posted(session: int):
    """Mark a diary entry as posted to X."""
    sb = get_client()
    sb.table("diary_entries").update({"posted_to_x": True}).eq("session", session).execute()


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
