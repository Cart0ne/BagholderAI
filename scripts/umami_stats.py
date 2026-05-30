"""
BagHolderAI — Umami Stats
=========================
Fetches website traffic from Umami Cloud (api.umami.is/v1) and writes a dated
markdown report: pageviews/visitors over the last 30 days (with delta vs the
previous 30 days, returned natively by Umami), top referrers, top pages and
custom events (buy-click, cta-*, etc.).

Mirrors scripts/x_stats_refresh.py: read-only, one dated file under
marketing_data/ (gitignored), returns a summary dict. Fails clearly if the key
is missing.

Usage:
    python3.13 -m scripts.umami_stats
    python3.13 -m scripts.umami_stats --days 14

Output:
    marketing_data/umami_YYYY-MM-DD.md

API: https://umami.is/docs/api  — header `x-umami-api-key`. Free (Hobby) tier
includes API access. Rate limit: 50 calls / 15s.
Keys: UMAMI_API_KEY, UMAMI_WEBSITE_ID in config/.env.marketing.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from config.settings import UmamiConfig

REPORT_DIR = Path(__file__).parent.parent / "marketing_data"
DAY_MS = 24 * 60 * 60 * 1000

# The 5 conversion funnels configured in the Umami dashboard, rebuilt in code so
# the connector doesn't depend on saved-report access. Steps are URL paths;
# "/blog/*" is a wildcard (any article). Window = 60 min (as configured).
FUNNELS = [
    ("Homepage → Blog → Articolo", ["/", "/blog", "/blog/*"]),
    ("Homepage → Dashboard → Diary", ["/", "/dashboard", "/diary"]),
    ("Homepage → Blog → Diary", ["/", "/blog", "/diary"]),
    ("Homepage → How We Work → Blueprint", ["/", "/howwework", "/blueprint"]),
    ("Homepage → Library", ["/", "/library"]),
]
FUNNEL_WINDOW_MIN = 60


def _headers() -> dict:
    return {"x-umami-api-key": UmamiConfig.API_KEY, "Accept": "application/json"}


def _get(path: str, params: dict) -> dict | list:
    url = f"{UmamiConfig.BASE_URL}/websites/{UmamiConfig.WEBSITE_ID}/{path}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    if resp.status_code in (401, 403):
        raise PermissionError(f"Umami API {resp.status_code} — UMAMI_API_KEY non valida o senza accesso al sito.")
    resp.raise_for_status()
    return resp.json()


def _metric_value(node) -> int:
    """Umami stats fields are {'value': N, 'prev': M} (v2) or plain int (v1)."""
    if isinstance(node, dict):
        return int(node.get("value", 0) or 0)
    return int(node or 0)


def _metric_prev(node) -> int:
    if isinstance(node, dict):
        return int(node.get("prev", 0) or 0)
    return 0


def _delta_str(cur: int, prev: int) -> str:
    if prev == 0:
        return "—" if cur == 0 else f"+{cur:,} (nuovo)"
    pct = (cur - prev) / prev * 100
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow} {pct:+.0f}% (prec. {prev:,})"


def fetch_funnel(steps: list, start_iso: str, end_iso: str) -> list | None:
    """POST /reports/funnel. Returns the step array, or None on any error
    (endpoint shape varies on cloud — failure here must not kill the report)."""
    body = {
        "websiteId": UmamiConfig.WEBSITE_ID,
        "type": "funnel",
        "parameters": {
            "startDate": start_iso,
            "endDate": end_iso,
            "steps": [{"type": "path", "value": v} for v in steps],
            "window": FUNNEL_WINDOW_MIN,
        },
    }
    try:
        resp = requests.post(
            f"{UmamiConfig.BASE_URL}/reports/funnel",
            headers={**_headers(), "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Response may be the step array directly or wrapped under a key.
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "result", "steps"):
                if isinstance(data.get(key), list):
                    return data[key]
        return None
    except (requests.RequestException, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Umami website stats")
    parser.add_argument("--days", type=int, default=30, help="finestra in giorni (default 30)")
    args = parser.parse_args()

    if not UmamiConfig.API_KEY:
        print("[ERROR] Manca UMAMI_API_KEY in config/.env.marketing.")
        print("        Generala su cloud.umami.is → Settings → API keys (free tier ok).")
        sys.exit(1)

    end_at = int(time.time() * 1000)
    start_at = end_at - args.days * DAY_MS
    base_params = {"startAt": start_at, "endAt": end_at}
    start_iso = datetime.fromtimestamp(start_at / 1000, tz=timezone.utc).isoformat()
    end_iso = datetime.fromtimestamp(end_at / 1000, tz=timezone.utc).isoformat()

    print(f"[INFO] Fetching Umami stats (ultimi {args.days}gg)...")
    try:
        stats = _get("stats", base_params)
        referrers = _get("metrics", {**base_params, "type": "referrer", "limit": 10})
        pages = _get("metrics", {**base_params, "type": "url", "limit": 10})
        events = _get("metrics", {**base_params, "type": "event", "limit": 20})
    except PermissionError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[ERROR] Umami API error: {e}")
        sys.exit(1)

    print("[INFO] Fetching conversion funnels...")
    funnel_results = []
    for name, steps in FUNNELS:
        funnel_results.append((name, steps, fetch_funnel(steps, start_iso, end_iso)))

    pv = _metric_value(stats.get("pageviews"))
    pv_prev = _metric_prev(stats.get("pageviews"))
    vis = _metric_value(stats.get("visitors"))
    vis_prev = _metric_prev(stats.get("visitors"))
    visits = _metric_value(stats.get("visits"))
    bounces = _metric_value(stats.get("bounces"))
    totaltime = _metric_value(stats.get("totaltime"))

    bounce_rate = (bounces / visits * 100) if visits else 0
    avg_time = (totaltime / visits) if visits else 0

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# Umami Stats — bagholderai.lol — {today}\n\n"
    md += f"**Generato:** {now}\n"
    md += f"**Finestra:** ultimi {args.days} giorni (delta vs {args.days}gg precedenti)\n\n"
    md += "> ⚠️ Umami è bloccato da adblocker (~40-60% del pubblico tech): i numeri sono sotto-stimati. Incrociare con Vercel Web Analytics per il totale reale.\n\n---\n\n"

    md += "## Traffico\n\n"
    md += "| Metrica | Valore | Trend |\n|---|---|---|\n"
    md += f"| Page views | {pv:,} | {_delta_str(pv, pv_prev)} |\n"
    md += f"| Visitatori unici | {vis:,} | {_delta_str(vis, vis_prev)} |\n"
    md += f"| Visite | {visits:,} | — |\n"
    md += f"| Bounce rate | {bounce_rate:.0f}% | — |\n"
    md += f"| Tempo medio visita | {avg_time:.0f}s | — |\n\n---\n\n"

    def _render_metric_table(title: str, data: list, label: str) -> str:
        out = f"## {title}\n\n| {label} | Conteggio |\n|---|---|\n"
        if not data:
            out += "| _nessun dato_ | — |\n"
        for item in data:
            name = (item.get("x") or "(direct/none)") if isinstance(item, dict) else str(item)
            count = item.get("y", 0) if isinstance(item, dict) else 0
            name = str(name).replace("|", "\\|")[:70]
            out += f"| {name} | {count:,} |\n"
        return out + "\n---\n\n"

    md += _render_metric_table("Top referrer", referrers, "Referrer")
    md += _render_metric_table("Top pagine", pages, "URL")
    md += _render_metric_table("Eventi custom (CTA / conversioni)", events, "Evento")

    # --- Funnel di conversione ---
    def _step_visitors(step) -> int:
        if not isinstance(step, dict):
            return 0
        for k in ("visitors", "count", "value", "y"):
            if k in step and step[k] is not None:
                return int(step[k])
        return 0

    md += "## Funnel di conversione\n\n"
    md += f"_Finestra step: {FUNNEL_WINDOW_MIN} min. Conversione = visitatori ultimo step / primo step._\n\n"
    funnels_ok = 0
    for name, steps, result in funnel_results:
        if not result:
            md += f"### {name}\n\n_Dati non disponibili (endpoint funnel non ha risposto)._\n\n"
            continue
        funnels_ok += 1
        entered = _step_visitors(result[0])
        converted = _step_visitors(result[-1])
        conv_rate = (converted / entered * 100) if entered else 0
        md += f"### {name}\n\n"
        md += f"**Conversione end-to-end: {conv_rate:.1f}%** ({converted:,}/{entered:,})\n\n"
        md += "| Step | Path | Visitatori | % vs inizio |\n|---|---|---|---|\n"
        for i, (label, step) in enumerate(zip(steps, result)):
            v = _step_visitors(step)
            pct = (v / entered * 100) if entered else 0
            md += f"| {i+1} | `{label}` | {v:,} | {pct:.0f}% |\n"
        md += "\n"
    md += "\n---\n\n"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"umami_{today}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"[INFO] Report saved: {out_path.relative_to(Path(__file__).parent.parent)}")
    print(f"[INFO] {pv:,} pageviews · {vis:,} visitatori · {len(events)} eventi custom · "
          f"{funnels_ok}/{len(FUNNELS)} funnel")

    return {
        "pageviews": pv,
        "pageviews_prev": pv_prev,
        "visitors": vis,
        "visitors_prev": vis_prev,
        "events_tracked": len(events),
        "funnels_ok": funnels_ok,
        "report_path": str(out_path),
    }


if __name__ == "__main__":
    main()
