"""
BagHolderAI — Reddit Stats
==========================
Fetches our Reddit account (Cart0neM) activity and writes a dated markdown
report: karma, recent submissions (score, upvote ratio, comments) and recent
comments (the "engagement first" strategy lives in others' threads).

STATO (verificato 2026-05-30): connettore DORMIENTE per scelta strutturale.
Reddit ha CHIUSO l'accesso API self-service → un piccolo uso non-commerciale
esterno non è più ottenibile. Strade provate e tutte chiuse:
  1. App self-service (prefs/apps "script") → r/redditdev automod: "Reddit has
     ended self-service API access".
  2. JSON pubblico (about/submitted/comments, no auth) → 403 block page anche
     con UA browser / old.reddit.
  3. Devvit (Developer Platform) → app on-platform TS/JS, non esporta verso il
     nostro audit: strumento sbagliato.
  4. Contratto commerciale → N/A (siamo non-commerciali, volume minimo).
Nell'audit Area 3 Reddit è quindi una **osservazione manuale** (come Payhip):
l'Auditor guarda u/Cart0neM nel browser. Vedi audit_request_A3.md §1.

Auth — IBRIDO (resta nel codice nel caso Reddit riapra un domani):
  1. praw (app OAuth "script") se le credenziali REDDIT_* sono complete.
  2. Endpoint JSON pubblici, no auth, fallback (oggi 403).
Le altre fonti (X, Dev.to, Umami, Bing, GSC) coprono l'audit senza Reddit.

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict.

Usage:
    python3.13 -m scripts.reddit_stats

Output:
    marketing_data/reddit_YYYY-MM-DD.md

Keys (config/.env.marketing): per praw → REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT (app approvata). Per il
fallback pubblico basta REDDIT_USERNAME.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from config.settings import RedditConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
LIMIT = 25
BASE = "https://www.reddit.com"
DEFAULT_UA = "bagholderai-marketing-audit/1.0 (read-only public stats)"


def truncate(text: str, n: int = 60) -> str:
    clean = (text or "").replace("\n", " ").replace("\r", " ").strip()
    if len(clean) > n:
        clean = clean[:n] + "..."
    return clean.replace("|", "\\|")


def _get_json(path: str, ua: str, params: dict | None = None) -> dict:
    """GET su un endpoint .json pubblico di Reddit. Solleva su errore."""
    resp = requests.get(
        f"{BASE}{path}",
        headers={"User-Agent": ua},
        params=params or {},
        timeout=30,
    )
    if resp.status_code == 429:
        raise RuntimeError("Reddit rate-limit (429) — riprova più tardi o riduci la frequenza.")
    if resp.status_code in (403, 404):
        raise RuntimeError(f"Reddit {resp.status_code} su {path} — utente inesistente o accesso pubblico bloccato.")
    resp.raise_for_status()
    return resp.json()


def _fetch_public(username, ua):
    """Strada 2: endpoint JSON pubblici, no auth."""
    about = _get_json(f"/user/{username}/about.json", ua)
    subs_raw = _get_json(f"/user/{username}/submitted.json", ua, {"limit": LIMIT})
    coms_raw = _get_json(f"/user/{username}/comments.json", ua, {"limit": LIMIT})

    a = about.get("data", {})
    link_karma = a.get("link_karma", 0)
    comment_karma = a.get("comment_karma", 0)
    total_karma = a.get("total_karma", link_karma + comment_karma)

    submissions = []
    for child in subs_raw.get("data", {}).get("children", []):
        s = child.get("data", {})
        submissions.append({
            "title": s.get("title", ""),
            "subreddit": s.get("subreddit", ""),
            "score": s.get("score", 0),
            "upvote_ratio": s.get("upvote_ratio"),
            "comments": s.get("num_comments", 0),
            "date": datetime.fromtimestamp(s.get("created_utc", 0)).strftime("%Y-%m-%d"),
            "url": f"{BASE}{s.get('permalink', '')}",
        })

    comments = []
    for child in coms_raw.get("data", {}).get("children", []):
        c = child.get("data", {})
        comments.append({
            "subreddit": c.get("subreddit", ""),
            "score": c.get("score", 0),
            "body": truncate(c.get("body", ""), 70),
            "date": datetime.fromtimestamp(c.get("created_utc", 0)).strftime("%Y-%m-%d"),
            "url": f"{BASE}{c.get('permalink', '')}",
        })
    return link_karma, comment_karma, total_karma, submissions, comments


def _fetch_praw():
    """Strada 1: praw (app OAuth approvata). Solleva se praw manca o auth fallisce."""
    import praw
    reddit = praw.Reddit(
        client_id=RedditConfig.CLIENT_ID,
        client_secret=RedditConfig.CLIENT_SECRET,
        username=RedditConfig.USERNAME,
        password=RedditConfig.PASSWORD,
        user_agent=RedditConfig.USER_AGENT or DEFAULT_UA,
    )
    me = reddit.user.me()
    if me is None:
        raise RuntimeError("autenticazione praw fallita (credenziali errate?)")

    link_karma = getattr(me, "link_karma", 0)
    comment_karma = getattr(me, "comment_karma", 0)
    total_karma = getattr(me, "total_karma", link_karma + comment_karma)

    submissions = [{
        "title": s.title, "subreddit": str(s.subreddit), "score": s.score,
        "upvote_ratio": getattr(s, "upvote_ratio", None), "comments": s.num_comments,
        "date": datetime.fromtimestamp(s.created_utc).strftime("%Y-%m-%d"),
        "url": f"https://reddit.com{s.permalink}",
    } for s in me.submissions.new(limit=LIMIT)]

    comments = [{
        "subreddit": str(c.subreddit), "score": c.score, "body": truncate(c.body, 70),
        "date": datetime.fromtimestamp(c.created_utc).strftime("%Y-%m-%d"),
        "url": f"https://reddit.com{c.permalink}",
    } for c in me.comments.new(limit=LIMIT)]
    return link_karma, comment_karma, total_karma, submissions, comments


def main():
    username = RedditConfig.USERNAME
    if not username:
        print("[ERROR] Manca REDDIT_USERNAME in config/.env.marketing.")
        sys.exit(1)

    ua = RedditConfig.USER_AGENT or DEFAULT_UA
    has_praw_creds = all([RedditConfig.CLIENT_ID, RedditConfig.CLIENT_SECRET,
                          RedditConfig.USERNAME, RedditConfig.PASSWORD])

    try:
        if has_praw_creds:
            print(f"[INFO] Reddit via praw (app OAuth) per u/{username}...")
            link_karma, comment_karma, total_karma, submissions, comments = _fetch_praw()
        else:
            print(f"[INFO] Reddit via JSON pubblico (no app) per u/{username}...")
            link_karma, comment_karma, total_karma, submissions, comments = _fetch_public(username, ua)
    except ImportError:
        print("[ERROR] Modulo 'praw' non installato. Esegui: pip install praw")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[ERROR] Reddit API error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        if not has_praw_creds:
            print("        Il JSON pubblico è bloccato da Reddit (403): serve un'app approvata.")
            print("        Compila le chiavi REDDIT_* quando Reddit approva l'app (Responsible Builder Policy).")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# Reddit — u/{username} — {today}\n\n"
    src = "praw (app OAuth)" if has_praw_creds else "endpoint JSON pubblici (no auth)"
    md += f"**Generato:** {now}  ·  _fonte: {src}_\n\n---\n\n"
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
