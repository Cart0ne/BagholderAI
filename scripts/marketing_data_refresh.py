"""
BagHolderAI — Marketing Data Refresh (orchestrator)
===================================================
Runs all marketing data connectors in sequence and prints a summary of which
ones succeeded and which failed (missing key / API error). One command to
refresh everything before an Area 3 (marketing) audit.

Each connector runs as a SUBPROCESS so a failure (e.g. a missing API key) does
not abort the others. Output files land in marketing_data/ (gitignored).

Usage:
    python3.13 -m scripts.marketing_data_refresh

Connectors:
    X         scripts.x_stats_refresh   (keys in config/.env)
    Dev.to    scripts.devto_stats       (keys in config/.env.marketing)
    Umami     scripts.umami_stats
    Bing SEO  scripts.bing_seo_stats
    GSC       scripts.gsc_stats

Fonti MANUALI (no connettore, recupero a mano prima dell'audit):
    Payhip    export CSV vendite → marketing_data/payhip_YYYY-MM-DD.csv
    Reddit    Reddit ha CHIUSO la API self-service (verif. 2026-05-30) → l'Auditor
              guarda u/Cart0neM nel browser. scripts/reddit_stats.py resta
              dormiente/pronto se riaprono. NON è nel run automatico (fallirebbe
              sempre con un falso ❌). Vedi audit_request_A3.md §1.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Reddit NON è qui: API self-service chiusa da Reddit (2026-05-30) → fonte
# manuale (vedi docstring). Inserirlo darebbe un ❌ fisso fuorviante.
CONNECTORS = [
    ("X", "scripts.x_stats_refresh"),
    ("Dev.to", "scripts.devto_stats"),
    ("Umami", "scripts.umami_stats"),
    ("Bing SEO", "scripts.bing_seo_stats"),
    ("GSC", "scripts.gsc_stats"),
]
TIMEOUT_S = 180


def run_connector(name: str, module: str) -> dict:
    print(f"\n{'='*60}\n▶ {name}  ({module})\n{'='*60}")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", module],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {name} oltre {TIMEOUT_S}s")
        return {"name": name, "ok": False, "note": "timeout"}

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if out:
        print(out)
    if err:
        print(err)

    ok = proc.returncode == 0
    # Last meaningful line for the summary
    last_info = ""
    for line in reversed(out.splitlines()):
        if line.startswith("[INFO]") or line.startswith("[ERROR]"):
            last_info = line
            break
    if not ok and not last_info:
        last_info = (err.splitlines()[-1] if err else f"exit {proc.returncode}")
    return {"name": name, "ok": ok, "note": last_info.replace("[INFO] ", "").replace("[ERROR] ", "")}


def main():
    print(f"Marketing data refresh — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    results = [run_connector(name, module) for name, module in CONNECTORS]

    print(f"\n\n{'='*60}\n RIEPILOGO\n{'='*60}")
    ok_count = sum(1 for r in results if r["ok"])
    for r in results:
        icon = "✅" if r["ok"] else "❌"
        print(f"  {icon} {r['name']:<10} {r['note']}")
    print(f"\n  {ok_count}/{len(results)} connettori OK")
    print("\n  ℹ️  Fonti manuali (a mano prima dell'audit):")
    print("       • Payhip → marketing_data/payhip_<oggi>.csv")
    print("       • Reddit → guarda u/Cart0neM nel browser (API self-service chiusa)")
    print(f"  📁 Output in: marketing_data/ (gitignored)")

    # Non-zero exit only if everything failed (nothing collected)
    if ok_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
