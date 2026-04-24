"""
BagHolderAI — X Stats Refresh
=============================
Scans @BagHolderAI timeline via X API v2, generates a dated markdown report
with all original posts + own replies (retweets excluded).

Usage:
    python3.13 -m scripts.x_stats_refresh

Output:
    report_for_CEO/x_scan_YYYY-MM-DD.md

Read-only on X API. Does NOT touch Supabase or config/Posts_X_v3.md.
Estimated cost: ~$0.001 per post fetched (pay-as-you-go tier).
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tweepy
from dotenv import load_dotenv

load_dotenv()

from config.settings import XConfig


REPORT_DIR = Path(__file__).parent.parent / "report_for_CEO"
COST_PER_POST_USD = 0.001  # X API pay-as-you-go, Owned Reads tier


def detect_author(text: str) -> str:
    """Heuristic author detection from post signature. Non-critical."""
    t = text.lower()
    has_bot_emoji = "🤖" in text
    has_person_emoji = "👤" in text
    has_brain_emoji = "🧠" in text

    if has_bot_emoji:
        return "🤖 AI"
    if has_person_emoji or "co-founder" in t:
        return "👤 CO-FOUNDER"
    if has_brain_emoji or ("ceo" in t and "claude" in t):
        return "🧠 CEO"
    # fallback: many old posts ended with just "bagholder.lol" / "bagholderai.lol"
    if "bagholderai.lol" in t or "bagholder.lol" in t or "bagholderai·lol" in t:
        return "? (bot-like)"
    return "?"


def truncate_text(text: str, max_len: int = 80) -> str:
    """Single-line truncate for table cell. Escapes pipe chars."""
    clean = text.replace("\n", " ").replace("\r", " ").strip()
    if len(clean) > max_len:
        clean = clean[:max_len] + "..."
    return clean.replace("|", "\\|")


def fmt_metric(value) -> str:
    """None/missing -> '-', else str. Keeps table readable."""
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def main():
    # 1. Authenticate (OAuth 1.0a, same pattern as utils/x_poster.py)
    if not all([XConfig.API_KEY, XConfig.API_SECRET, XConfig.ACCESS_TOKEN, XConfig.ACCESS_SECRET]):
        print("[ERROR] Missing X credentials in .env. Required: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET")
        sys.exit(1)

    client = tweepy.Client(
        consumer_key=XConfig.API_KEY,
        consumer_secret=XConfig.API_SECRET,
        access_token=XConfig.ACCESS_TOKEN,
        access_token_secret=XConfig.ACCESS_SECRET,
        wait_on_rate_limit=True,
    )

    # 2. Get own user ID
    try:
        me = client.get_me()
    except tweepy.TweepyException as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)

    username = me.data.username
    user_id = me.data.id
    print(f"[INFO] Authenticated as @{username} (ID: {user_id})")

    # 3. Fetch timeline (originals + own replies, no retweets)
    print("[INFO] Fetching posts + replies (excluding retweets)...")

    try:
        paginator = tweepy.Paginator(
            client.get_users_tweets,
            id=user_id,
            max_results=100,
            tweet_fields=["created_at", "public_metrics", "text", "in_reply_to_user_id"],
            exclude=["retweets"],
        )
        tweets = list(paginator.flatten(limit=200))
    except tweepy.TweepyException as e:
        err = str(e).lower()
        if "429" in err or "rate limit" in err:
            print(f"[ERROR] X API rate limited: {e}")
        elif "401" in err or "403" in err:
            print(f"[ERROR] X API auth/permission error: {e}")
        else:
            print(f"[ERROR] X API error: {e}")
        sys.exit(1)

    total = len(tweets)
    if total == 0:
        print("[WARN] No posts fetched. Profile empty or API filtering everything out.")
        sys.exit(0)

    # 4. Process posts
    posts = []
    total_impr = 0
    total_likes = 0
    total_rt = 0
    total_replies_received = 0
    originals_count = 0
    replies_count = 0

    for t in tweets:
        m = t.public_metrics or {}
        impr = m.get("impression_count")  # may be None on some tiers
        likes = m.get("like_count", 0)
        rt = m.get("retweet_count", 0)
        replies_recv = m.get("reply_count", 0)

        is_reply = t.in_reply_to_user_id is not None
        if is_reply:
            replies_count += 1
        else:
            originals_count += 1

        if isinstance(impr, int):
            total_impr += impr
        total_likes += likes
        total_rt += rt
        total_replies_received += replies_recv

        posts.append({
            "date": t.created_at.strftime("%d/%m %H:%M") if t.created_at else "N/A",
            "created_at": t.created_at,
            "type": "Reply" if is_reply else "Post",
            "author": detect_author(t.text),
            "text_short": truncate_text(t.text),
            "text_full": t.text,
            "impressions": impr,
            "likes": likes,
            "retweets": rt,
            "replies": replies_recv,
            "url": f"https://x.com/{username}/status/{t.id}",
        })

    print(f"[INFO] Fetched {total} posts in 1 API call")
    print(f"[INFO] {originals_count} originals, {replies_count} replies")

    # 5. Sort by date descending
    posts_sorted = sorted(
        posts,
        key=lambda p: p["created_at"] or datetime.min.replace(tzinfo=None),
        reverse=True,
    )

    # 6. Top 3 by impressions (skip posts with None impressions)
    posts_with_impr = [p for p in posts if isinstance(p["impressions"], int)]
    top3 = sorted(posts_with_impr, key=lambda p: p["impressions"], reverse=True)[:3]

    # 7. Build markdown
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cost = total * COST_PER_POST_USD

    md = f"# X Scan — @{username} — {today}\n\n"
    md += f"**Generato:** {now}\n"
    md += f"**Post scaricati:** {total} ({originals_count} originali + {replies_count} reply)\n"
    md += f"**Costo stimato API:** ${cost:.3f}\n\n"
    md += "---\n\n"

    md += "## 📊 Riepilogo\n\n"
    md += f"- **Post originali:** {originals_count}\n"
    md += f"- **Reply:** {replies_count}\n"
    md += f"- **Impressions totali:** {total_impr:,}\n"
    md += f"- **Likes totali:** {total_likes:,}\n"
    md += f"- **Retweets totali:** {total_rt:,}\n"
    md += f"- **Replies ricevute:** {total_replies_received:,}\n\n"
    md += "---\n\n"

    md += "## 📋 Tutti i post (più recenti prima)\n\n"
    md += "| Data | Tipo | Autore | Testo | Impr | Lk | RT | Rp | Link |\n"
    md += "|------|------|--------|-------|------|----|----|----|------|\n"
    for p in posts_sorted:
        md += (
            f"| {p['date']} | {p['type']} | {p['author']} | {p['text_short']} | "
            f"{fmt_metric(p['impressions'])} | {fmt_metric(p['likes'])} | "
            f"{fmt_metric(p['retweets'])} | {fmt_metric(p['replies'])} | "
            f"[→]({p['url']}) |\n"
        )
    md += "\n---\n\n"

    if top3:
        md += "## 🏆 Top 3 per impressions\n\n"
        for i, p in enumerate(top3, 1):
            md += (
                f"**{i}.** {truncate_text(p['text_full'], 120)}\n"
                f"   - Impressions: **{p['impressions']:,}** · "
                f"Likes: {p['likes']} · RT: {p['retweets']} · Reply: {p['replies']}\n"
                f"   - {p['url']}\n\n"
            )
        md += "---\n\n"
    else:
        md += "## 🏆 Top 3 per impressions\n\n"
        md += "_Nessun post con `impression_count` restituito dall'API (tier X potrebbe non supportarlo)._\n\n"
        md += "---\n\n"

    md += "## ⚠️ Note\n\n"
    md += "- Post senza `impression_count` mostrati come `-` (API non sempre restituisce il dato)\n"
    md += "- Autore `?` = firma non riconosciuta, controllo manuale consigliato\n"
    md += "- Retweet di altri account **esclusi** dal conteggio\n"
    md += "- Reply **nostre** a tweet di altri **incluse** (tipo = Reply)\n"

    # 8. Write file
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"x_scan_{today}.md"
    out_path.write_text(md, encoding="utf-8")

    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] Estimated cost: ${cost:.3f}")


if __name__ == "__main__":
    main()
