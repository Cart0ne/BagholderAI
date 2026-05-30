"""
BagHolderAI — Reddit Stats
==========================
Fetches our Reddit account (Cart0neM) activity via the official API (praw) and
writes a dated markdown report: karma, recent submissions (score, upvote ratio,
comments) and recent comments (the "engagement first" strategy lives in others'
threads).

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict. Fails clearly if creds
are missing.

Usage:
    python3.13 -m scripts.reddit_stats

Output:
    marketing_data/reddit_YYYY-MM-DD.md

Keys (config/.env.marketing): REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT.
App: reddit.com/prefs/apps → create app type "script".
"""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import RedditConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
LIMIT = 25


def truncate(text: str, n: int = 60) -> str:
    clean = (text or "").replace("\n", " ").replace("\r", " ").strip()
    if len(clean) > n:
        clean = clean[:n] + "..."
    return clean.replace("|", "\\|")


def main():
    if not all([RedditConfig.CLIENT_ID, RedditConfig.CLIENT_SECRET,
                RedditConfig.USERNAME, RedditConfig.PASSWORD]):
        print("[ERROR] Credenziali Reddit incomplete in config/.env.marketing.")
        print("        Servono REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD.")
        print("        Crea una app 'script' su reddit.com/prefs/apps.")
        sys.exit(1)

    try:
        import praw
    except ImportError:
        print("[ERROR] Modulo 'praw' non installato. Esegui: pip install praw")
        sys.exit(1)

    print(f"[INFO] Authenticating to Reddit as u/{RedditConfig.USERNAME}...")
    try:
        reddit = praw.Reddit(
            client_id=RedditConfig.CLIENT_ID,
            client_secret=RedditConfig.CLIENT_SECRET,
            username=RedditConfig.USERNAME,
            password=RedditConfig.PASSWORD,
            user_agent=RedditConfig.USER_AGENT,
        )
        me = reddit.user.me()
        if me is None:
            raise RuntimeError("autenticazione fallita (credenziali errate?)")
    except Exception as e:
        print(f"[ERROR] Reddit auth error: {e}")
        sys.exit(1)

    link_karma = getattr(me, "link_karma", 0)
    comment_karma = getattr(me, "comment_karma", 0)
    total_karma = getattr(me, "total_karma", link_karma + comment_karma)

    submissions = []
    for s in me.submissions.new(limit=LIMIT):
        submissions.append({
            "title": s.title,
            "subreddit": str(s.subreddit),
            "score": s.score,
            "upvote_ratio": getattr(s, "upvote_ratio", None),
            "comments": s.num_comments,
            "date": datetime.fromtimestamp(s.created_utc).strftime("%Y-%m-%d"),
            "url": f"https://reddit.com{s.permalink}",
        })

    comments = []
    for c in me.comments.new(limit=LIMIT):
        comments.append({
            "subreddit": str(c.subreddit),
            "score": c.score,
            "body": truncate(c.body, 70),
            "date": datetime.fromtimestamp(c.created_utc).strftime("%Y-%m-%d"),
            "url": f"https://reddit.com{c.permalink}",
        })

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# Reddit — u/{RedditConfig.USERNAME} — {today}\n\n"
    md += f"**Generato:** {now}\n\n---\n\n"
    md += "## Karma\n\n"
    md += f"- **Totale:** {total_karma:,}\n"
    md += f"- **Post (link):** {link_karma:,}\n"
    md += f"- **Commenti:** {comment_karma:,}\n\n---\n\n"

    md += f"## Post recenti (ultimi {len(submissions)})\n\n"
    md += "| Data | Subreddit | Titolo | Score | Ratio | Commenti | Link |\n"
    md += "|---|---|---|---|---|---|---|\n"
    if not submissions:
        md += "| _nessun post_ | — | — | — | — | — | — |\n"
    for s in submissions:
        ratio = f"{s['upvote_ratio']:.0%}" if s["upvote_ratio"] is not None else "-"
        md += (f"| {s['date']} | r/{s['subreddit']} | {truncate(s['title'])} | "
               f"{s['score']} | {ratio} | {s['comments']} | [→]({s['url']}) |\n")
    md += "\n---\n\n"

    md += f"## Commenti recenti (ultimi {len(comments)} — engagement)\n\n"
    md += "| Data | Subreddit | Score | Testo | Link |\n|---|---|---|---|---|\n"
    if not comments:
        md += "| _nessun commento_ | — | — | — | — |\n"
    for c in comments:
        md += f"| {c['date']} | r/{c['subreddit']} | {c['score']} | {c['body']} | [→]({c['url']}) |\n"
    md += "\n"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"reddit_{today}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] karma {total_karma:,} · {len(submissions)} post · {len(comments)} commenti")

    return {
        "total_karma": total_karma,
        "link_karma": link_karma,
        "comment_karma": comment_karma,
        "submissions": len(submissions),
        "comments": len(comments),
        "report_path": str(out_path),
    }


if __name__ == "__main__":
    main()
