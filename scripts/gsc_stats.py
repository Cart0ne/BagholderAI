"""
BagHolderAI — Google Search Console Stats
=========================================
Fetches search performance from Google Search Console (Search Analytics API) via
a service account, and writes a dated markdown report: aggregate
clicks/impressions/CTR/position, top queries, top pages and a daily trend.

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict. Fails clearly if the
service-account JSON or site URL is missing.

Usage:
    python3.13 -m scripts.gsc_stats
    python3.13 -m scripts.gsc_stats --days 28

Output:
    marketing_data/seo_gsc_YYYY-MM-DD.md

Setup: Google Cloud → service account → download JSON → enable "Google Search
Console API" → in Search Console add the service-account email as a user (read).
Keys (config/.env.marketing): GSC_SERVICE_ACCOUNT_JSON (path), GSC_SITE_URL.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import GSCConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
# GSC data lags ~2-3 days; end the window a few days back to avoid empty tails.
LAG_DAYS = 3


def _query(service, site, start, end, dimensions, limit=25):
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": limit,
    }
    return service.searchanalytics().query(siteUrl=site, body=body).execute().get("rows", [])


def main():
    parser = argparse.ArgumentParser(description="Google Search Console stats")
    parser.add_argument("--days", type=int, default=28, help="finestra in giorni (default 28)")
    args = parser.parse_args()

    if not GSCConfig.SERVICE_ACCOUNT_JSON or not GSCConfig.SITE_URL:
        print("[ERROR] Manca GSC_SERVICE_ACCOUNT_JSON (path al .json) o GSC_SITE_URL in config/.env.marketing.")
        print("        Crea un service account su Google Cloud, abilita Search Console API,")
        print("        e in Search Console aggiungi l'email del service account come utente in lettura.")
        sys.exit(1)

    json_path = GSCConfig.SERVICE_ACCOUNT_JSON
    if not os.path.isabs(json_path):
        json_path = str(Path(__file__).parent.parent / json_path)
    if not os.path.exists(json_path):
        print(f"[ERROR] File credenziali non trovato: {json_path}")
        sys.exit(1)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Librerie Google mancanti. Esegui: pip install google-api-python-client google-auth")
        sys.exit(1)

    print(f"[INFO] Authenticating to GSC for {GSCConfig.SITE_URL}...")
    try:
        creds = service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[ERROR] GSC auth error: {e}")
        sys.exit(1)

    end_d = datetime.now().date() - timedelta(days=LAG_DAYS)
    start_d = end_d - timedelta(days=args.days)
    start, end = start_d.isoformat(), end_d.isoformat()
    site = GSCConfig.SITE_URL

    print(f"[INFO] Fetching Search Analytics {start} → {end}...")
    try:
        totals = _query(service, site, start, end, [], limit=1)
        queries = _query(service, site, start, end, ["query"], limit=20)
        pages = _query(service, site, start, end, ["page"], limit=20)
        by_date = _query(service, site, start, end, ["date"], limit=400)
    except Exception as e:
        print(f"[ERROR] GSC API error: {e}")
        sys.exit(1)

    def _agg(rows):
        clicks = sum(r.get("clicks", 0) for r in rows)
        impr = sum(r.get("impressions", 0) for r in rows)
        return clicks, impr

    if totals:
        t = totals[0]
        t_clicks, t_impr = t.get("clicks", 0), t.get("impressions", 0)
        t_ctr = t.get("ctr", 0) * 100
        t_pos = t.get("position", 0)
    else:
        t_clicks, t_impr = _agg(by_date)
        t_ctr = (t_clicks / t_impr * 100) if t_impr else 0
        t_pos = 0

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# SEO — Google Search Console — {site} — {today}\n\n"
    md += f"**Generato:** {now}\n"
    md += f"**Finestra:** {start} → {end} ({args.days}gg, lag GSC {LAG_DAYS}gg)\n\n---\n\n"
    md += "## Riepilogo\n\n"
    md += f"- **Click:** {t_clicks:,}\n"
    md += f"- **Impressions:** {t_impr:,}\n"
    md += f"- **CTR:** {t_ctr:.2f}%\n"
    md += f"- **Posizione media:** {t_pos:.1f}\n\n---\n\n"

    md += "## Top query (per impressions)\n\n"
    md += "| Query | Click | Impr | CTR | Pos |\n|---|---|---|---|---|\n"
    if not queries:
        md += "| _nessuna query indicizzata_ | — | — | — | — |\n"
    for r in sorted(queries, key=lambda x: x.get("impressions", 0), reverse=True):
        kw = str(r.get("keys", ["?"])[0]).replace("|", "\\|")[:60]
        md += (f"| {kw} | {r.get('clicks',0):,} | {r.get('impressions',0):,} | "
               f"{r.get('ctr',0)*100:.1f}% | {r.get('position',0):.1f} |\n")
    md += "\n---\n\n"

    md += "## Top pagine (per impressions)\n\n"
    md += "| Pagina | Click | Impr | CTR | Pos |\n|---|---|---|---|---|\n"
    if not pages:
        md += "| _nessuna pagina_ | — | — | — | — |\n"
    for r in sorted(pages, key=lambda x: x.get("impressions", 0), reverse=True):
        pg = str(r.get("keys", ["?"])[0]).replace("|", "\\|")[:70]
        md += (f"| {pg} | {r.get('clicks',0):,} | {r.get('impressions',0):,} | "
               f"{r.get('ctr',0)*100:.1f}% | {r.get('position',0):.1f} |\n")
    md += "\n---\n\n"

    md += "## Trend giornaliero (ultimi 14gg della finestra)\n\n"
    md += "| Data | Click | Impr |\n|---|---|---|\n"
    if not by_date:
        md += "| _nessun dato_ | — | — |\n"
    for r in sorted(by_date, key=lambda x: x.get("keys", [""])[0])[-14:]:
        d = r.get("keys", ["?"])[0]
        md += f"| {d} | {r.get('clicks',0):,} | {r.get('impressions',0):,} |\n"
    md += "\n"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"seo_gsc_{today}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] {t_clicks:,} click · {t_impr:,} impressions · CTR {t_ctr:.2f}% · pos {t_pos:.1f}")

    return {
        "clicks": t_clicks,
        "impressions": t_impr,
        "ctr_pct": round(t_ctr, 2),
        "position": round(t_pos, 1),
        "report_path": str(out_path),
    }


if __name__ == "__main__":
    main()
