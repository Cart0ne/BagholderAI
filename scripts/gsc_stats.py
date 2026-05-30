"""
BagHolderAI — Google Search Console Stats
=========================================
Fetches search performance from Google Search Console (Search Analytics API) and
writes a dated markdown report: aggregate clicks/impressions/CTR/position, top
queries, top pages and a daily trend.

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict. Fails clearly if the
credentials JSON or site URL is missing.

Auth — auto-detected from the credentials JSON (GSC_SERVICE_ACCOUNT_JSON):
  - OAuth client (file con chiave "installed"/"web", scaricato da Google Cloud →
    Credenziali → "ID client OAuth" tipo "App desktop"): il connettore fa login
    COME l'utente proprietario (consenso browser una-tantum), e cache del token
    in marketing_data/gsc_token.json. Nessun "Add user" in Search Console: il
    proprietario vede già le sue proprietà. È il percorso consigliato.
  - Service account (file con "type":"service_account"): identità-macchina, va
    aggiunta come utente nella proprietà Search Console (spesso problematico).

Usage:
    python3.13 -m scripts.gsc_stats
    python3.13 -m scripts.gsc_stats --days 28

Output:
    marketing_data/seo_gsc_YYYY-MM-DD.md

Keys (config/.env.marketing): GSC_SERVICE_ACCOUNT_JSON (path al file credenziali,
service account O OAuth client), GSC_SITE_URL (proprietà preferita; se non
combacia, da OAuth-owner il connettore risolve in automatico quella giusta).
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


def _oauth_creds(client_json_path):
    """OAuth installed-app flow: login as the owner, cache the refresh token.

    First run opens the browser for consent; subsequent runs reuse/refresh the
    token in marketing_data/gsc_token.json (gitignored, contiene il refresh
    token → trattalo come una password)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = Path(client_json_path).parent / "gsc_token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_json_path, SCOPES)
            # Apre il browser per il consenso una-tantum (server locale, porta libera).
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _build_service(json_path):
    """Build a Search Console service, auto-detecting the credential type."""
    import json as _json

    from googleapiclient.discovery import build

    with open(json_path) as f:
        info = _json.load(f)

    if info.get("type") == "service_account":
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)
    elif "installed" in info or "web" in info:
        creds = _oauth_creds(json_path)
    else:
        raise ValueError(
            "File credenziali non riconosciuto: né service account "
            "(\"type\":\"service_account\") né OAuth client (\"installed\"/\"web\")."
        )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _resolve_site(service, configured):
    """Pick the right Search Console property.

    Da OAuth-owner si vedono TUTTE le proprietà → se quella configurata non
    combacia (es. è 'sc-domain:' invece di 'https://.../'), si sceglie la
    migliore automaticamente. Con service account la list può essere vuota →
    si usa il valore configurato."""
    try:
        entries = service.sites().list().execute().get("siteEntry", [])
    except Exception:
        return configured
    available = [e.get("siteUrl", "") for e in entries]
    if not available:
        return configured
    if configured in available:
        return configured
    for s in available:  # preferisci la proprietà Dominio del nostro sito
        if s.startswith("sc-domain:") and "bagholderai" in s:
            return s
    for s in available:
        if "bagholderai" in s:
            return s
    return available[0]


def main():
    parser = argparse.ArgumentParser(description="Google Search Console stats")
    parser.add_argument("--days", type=int, default=28, help="finestra in giorni (default 28)")
    args = parser.parse_args()

    if not GSCConfig.SERVICE_ACCOUNT_JSON or not GSCConfig.SITE_URL:
        print("[ERROR] Manca GSC_SERVICE_ACCOUNT_JSON (path al .json) o GSC_SITE_URL in config/.env.marketing.")
        print("        Scarica da Google Cloud → Credenziali un 'ID client OAuth' tipo 'App desktop'")
        print("        (consigliato), oppure un service account JSON, e metti il path qui.")
        sys.exit(1)

    json_path = GSCConfig.SERVICE_ACCOUNT_JSON
    if not os.path.isabs(json_path):
        json_path = str(Path(__file__).parent.parent / json_path)
    if not os.path.exists(json_path):
        print(f"[ERROR] File credenziali non trovato: {json_path}")
        sys.exit(1)

    try:
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        print("[ERROR] Librerie Google mancanti. Esegui:")
        print("        pip install google-api-python-client google-auth google-auth-oauthlib")
        sys.exit(1)

    print(f"[INFO] Authenticating to GSC (cred: {os.path.basename(json_path)})...")
    try:
        service = _build_service(json_path)
    except Exception as e:
        print(f"[ERROR] GSC auth error: {e}")
        sys.exit(1)

    site = _resolve_site(service, GSCConfig.SITE_URL)
    if site != GSCConfig.SITE_URL:
        print(f"[INFO] Proprietà risolta: {site}  (configurata: {GSCConfig.SITE_URL})")

    end_d = datetime.now().date() - timedelta(days=LAG_DAYS)
    start_d = end_d - timedelta(days=args.days)
    start, end = start_d.isoformat(), end_d.isoformat()

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
