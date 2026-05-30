"""
BagHolderAI — Bing Webmaster SEO Stats
======================================
Fetches search performance from Bing Webmaster Tools and writes a dated markdown
report: aggregate impressions/clicks trend, top queries (impressions, clicks,
position) and top pages.

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict. Fails clearly if the key
is missing.

Usage:
    python3.13 -m scripts.bing_seo_stats

Output:
    marketing_data/seo_bing_YYYY-MM-DD.md

API: https://ssl.bing.com/webmaster/api.svc/json/<Method>?apikey=<KEY>&siteUrl=<URL>
Methods used: GetRankAndTrafficStats, GetQueryStats, GetPageStats.
Responses wrap the payload under key "d"; dates come as /Date(ms)/.
Keys: BING_WEBMASTER_API_KEY, BING_SITE_URL in config/.env.marketing.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from config.settings import BingConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
_DATE_RE = re.compile(r"/Date\((\d+)")


def _parse_date(raw: str) -> str:
    """Bing returns '/Date(1700000000000)/'. Return YYYY-MM-DD."""
    if not raw:
        return ""
    m = _DATE_RE.search(str(raw))
    if not m:
        return str(raw)[:10]
    return datetime.fromtimestamp(int(m.group(1)) / 1000).strftime("%Y-%m-%d")


def _call(method: str) -> list:
    url = f"{BingConfig.BASE_URL}/{method}"
    resp = requests.get(
        url,
        params={"apikey": BingConfig.API_KEY, "siteUrl": BingConfig.SITE_URL},
        timeout=30,
    )
    if resp.status_code in (401, 403):
        raise PermissionError(f"Bing API {resp.status_code} — BING_WEBMASTER_API_KEY non valida o sito non verificato.")
    resp.raise_for_status()
    data = resp.json()
    # WCF JSON wraps results under "d"
    payload = data.get("d", data) if isinstance(data, dict) else data
    return payload if isinstance(payload, list) else []


def main():
    if not BingConfig.API_KEY:
        print("[ERROR] Manca BING_WEBMASTER_API_KEY in config/.env.marketing.")
        print("        Generala su bing.com/webmasters → Settings → API access.")
        sys.exit(1)

    print(f"[INFO] Fetching Bing Webmaster stats for {BingConfig.SITE_URL}...")
    try:
        traffic = _call("GetRankAndTrafficStats")
        queries = _call("GetQueryStats")
        pages = _call("GetPageStats")
        crawl = _call("GetCrawlStats")
    except PermissionError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[ERROR] Bing API error: {e}")
        sys.exit(1)

    # Aggregate traffic
    total_impr = sum(int(t.get("Impressions", 0) or 0) for t in traffic)
    total_clicks = sum(int(t.get("Clicks", 0) or 0) for t in traffic)
    ctr = (total_clicks / total_impr * 100) if total_impr else 0

    # Recent trend (last 14 daily points)
    traffic_sorted = sorted(traffic, key=lambda t: _parse_date(t.get("Date", "")))
    recent = traffic_sorted[-14:]

    # Top queries by impressions
    q_sorted = sorted(queries, key=lambda q: int(q.get("Impressions", 0) or 0), reverse=True)[:15]
    # Top pages by impressions
    p_sorted = sorted(pages, key=lambda p: int(p.get("Impressions", 0) or 0), reverse=True)[:15]

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# SEO — Bing Webmaster — {BingConfig.SITE_URL} — {today}\n\n"
    md += f"**Generato:** {now}\n\n---\n\n"
    md += "## Riepilogo (intervallo restituito da Bing, ~6 mesi)\n\n"
    md += f"- **Impressions totali:** {total_impr:,}\n"
    md += f"- **Click totali:** {total_clicks:,}\n"
    md += f"- **CTR medio:** {ctr:.2f}%\n\n---\n\n"

    # --- Indicizzazione & crawl (utile anche quando le performance sono a zero) ---
    crawl_sorted = sorted(crawl, key=lambda c: _parse_date(c.get("Date", "")))
    in_index = in_links = 0
    crawled = crawl_errors = code_4xx = code_5xx = blocked = 0
    if crawl_sorted:
        # InIndex/InLinks sono snapshot: prendo il max sulla finestra (più stabile
        # del singolo ultimo giorno, che può essere parziale).
        in_index = max(int(c.get("InIndex", 0) or 0) for c in crawl_sorted)
        in_links = max(int(c.get("InLinks", 0) or 0) for c in crawl_sorted)
        crawled = sum(int(c.get("CrawledPages", 0) or 0) for c in crawl_sorted)
        crawl_errors = sum(int(c.get("CrawlErrors", 0) or 0) for c in crawl_sorted)
        code_4xx = sum(int(c.get("Code4xx", 0) or 0) for c in crawl_sorted)
        code_5xx = sum(int(c.get("Code5xx", 0) or 0) for c in crawl_sorted)
        blocked = sum(int(c.get("BlockedByRobotsTxt", 0) or 0) for c in crawl_sorted)
    md += "## Indicizzazione & crawl\n\n"
    md += f"- **Pagine nell'indice di ricerca (InIndex):** {in_index:,}\n"
    md += f"- **Link in entrata (InLinks):** {in_links:,}\n"
    md += f"- **Pagine crawlate (finestra):** {crawled:,}\n"
    md += f"- **Errori crawl:** {crawl_errors:,} · 4xx: {code_4xx:,} · 5xx: {code_5xx:,} · bloccate da robots: {blocked:,}\n\n"
    md += "> Nota: `InIndex` (pagine effettivamente nell'indice di ricerca) può differire dal contatore \"pagine indicizzate\" della dashboard Bing, che spesso mostra URL note/crawlate o quelle in sitemap.\n\n---\n\n"

    md += "## Trend recente (ultimi punti giornalieri)\n\n"
    md += "| Data | Impressions | Click |\n|---|---|---|\n"
    if not recent:
        md += "| _nessun dato_ | — | — |\n"
    for t in recent:
        md += f"| {_parse_date(t.get('Date',''))} | {int(t.get('Impressions',0) or 0):,} | {int(t.get('Clicks',0) or 0):,} |\n"
    md += "\n---\n\n"

    md += "## Top query (per impressions)\n\n"
    md += "| Query | Impr | Click | Pos. media |\n|---|---|---|---|\n"
    if not q_sorted:
        md += "| _nessuna query_ | — | — | — |\n"
    for q in q_sorted:
        query = str(q.get("Query", "")).replace("|", "\\|")[:60]
        pos = q.get("AvgImpressionPosition", q.get("AvgClickPosition", "-"))
        md += f"| {query} | {int(q.get('Impressions',0) or 0):,} | {int(q.get('Clicks',0) or 0):,} | {pos} |\n"
    md += "\n---\n\n"

    md += "## Top pagine (per impressions)\n\n"
    md += "| Pagina | Impr | Click |\n|---|---|---|\n"
    if not p_sorted:
        md += "| _nessuna pagina_ | — | — |\n"
    for p in p_sorted:
        page = str(p.get("Query", p.get("Page", ""))).replace("|", "\\|")[:70]
        md += f"| {page} | {int(p.get('Impressions',0) or 0):,} | {int(p.get('Clicks',0) or 0):,} |\n"
    md += "\n"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"seo_bing_{today}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] {total_impr:,} impressions · {total_clicks:,} click · CTR {ctr:.2f}% · {len(q_sorted)} query")

    return {
        "total_impressions": total_impr,
        "total_clicks": total_clicks,
        "ctr_pct": round(ctr, 2),
        "queries": len(queries),
        "pages_in_index": in_index,
        "report_path": str(out_path),
    }


if __name__ == "__main__":
    main()
