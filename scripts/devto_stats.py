"""
BagHolderAI — Dev.to Stats
==========================
Fetches our own Dev.to (Forem) articles via the authenticated API and writes a
dated markdown report with per-article page views, reactions and comments.

Mirrors scripts/x_stats_refresh.py: read-only on the external API, writes one
dated file under marketing_data/ (gitignored), returns a summary dict for the
orchestrator. Fails with a clear message if the API key is missing.

Usage:
    python3.13 -m scripts.devto_stats

Output:
    marketing_data/devto_YYYY-MM-DD.md

API: GET /api/articles/me/all  (header `api-key`)
Docs: https://developers.forem.com/api  — returns page_views_count,
public_reactions_count, comments_count per article.
Key: DEVTO_API_KEY in config/.env.marketing.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from config.settings import DevtoConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
PER_PAGE = 100


def truncate_text(text: str, max_len: int = 60) -> str:
    clean = (text or "").replace("\n", " ").replace("\r", " ").strip()
    if len(clean) > max_len:
        clean = clean[:max_len] + "..."
    return clean.replace("|", "\\|")


def fetch_articles() -> list:
    """Fetch all own articles (published) with stats, paginated."""
    headers = {"api-key": DevtoConfig.API_KEY, "Accept": "application/vnd.forem.api-v1+json"}
    articles = []
    page = 1
    while True:
        resp = requests.get(
            f"{DevtoConfig.BASE_URL}/articles/me/all",
            headers=headers,
            params={"page": page, "per_page": PER_PAGE},
            timeout=30,
        )
        if resp.status_code == 401:
            raise PermissionError("Dev.to API 401 — chiave DEVTO_API_KEY non valida o assente.")
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        articles.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
    return articles


def main():
    if not DevtoConfig.API_KEY:
        print("[ERROR] Manca DEVTO_API_KEY in config/.env.marketing.")
        print("        Generala su dev.to → Settings → Extensions → DEV Community API Keys.")
        sys.exit(1)

    print("[INFO] Fetching Dev.to articles (own, with stats)...")
    try:
        articles = fetch_articles()
    except PermissionError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[ERROR] Dev.to API error: {e}")
        sys.exit(1)

    if not articles:
        print("[WARN] Nessun articolo restituito dall'API.")
        return {"articles": 0, "total_views": 0, "total_reactions": 0,
                "total_comments": 0, "report_path": None}

    rows = []
    total_views = total_reactions = total_comments = 0
    for a in articles:
        views = a.get("page_views_count", 0) or 0
        reactions = a.get("public_reactions_count", 0) or 0
        comments = a.get("comments_count", 0) or 0
        total_views += views
        total_reactions += reactions
        total_comments += comments
        rows.append({
            "title": a.get("title", ""),
            "published_at": (a.get("published_at") or "")[:10],
            "views": views,
            "reactions": reactions,
            "comments": comments,
            "url": a.get("url", ""),
        })

    rows.sort(key=lambda r: r["published_at"], reverse=True)
    top = sorted(rows, key=lambda r: r["views"], reverse=True)[:3]

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# Dev.to Stats — @cart0ne — {today}\n\n"
    md += f"**Generato:** {now}\n"
    md += f"**Articoli:** {len(rows)}\n\n---\n\n"
    md += "## Riepilogo\n\n"
    md += f"- **Articoli pubblicati:** {len(rows)}\n"
    md += f"- **Page views totali:** {total_views:,}\n"
    md += f"- **Reactions totali:** {total_reactions:,}\n"
    md += f"- **Commenti totali:** {total_comments:,}\n\n---\n\n"

    md += "## Articoli (più recenti prima)\n\n"
    md += "| Data | Titolo | Views | React | Commenti | Link |\n"
    md += "|------|--------|-------|-------|----------|------|\n"
    for r in rows:
        md += (f"| {r['published_at']} | {truncate_text(r['title'])} | {r['views']:,} | "
               f"{r['reactions']:,} | {r['comments']:,} | [→]({r['url']}) |\n")
    md += "\n---\n\n"

    md += "## Top 3 per page views\n\n"
    for i, r in enumerate(top, 1):
        md += (f"**{i}.** {truncate_text(r['title'], 80)} — "
               f"**{r['views']:,}** views · {r['reactions']} react · {r['comments']} commenti\n"
               f"   - {r['url']}\n\n")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"devto_{today}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] {len(rows)} articoli · {total_views:,} views · "
          f"{total_reactions:,} reactions · {total_comments:,} commenti")

    return {
        "articles": len(rows),
        "total_views": total_views,
        "total_reactions": total_reactions,
        "total_comments": total_comments,
        "report_path": str(out_path),
    }


if __name__ == "__main__":
    main()
