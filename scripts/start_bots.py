#!/usr/bin/env python3
"""BagHolderAI — avvio a freddo dei bot sul Mac Mini (R.7, S129 2026-09-27).

Unica fonte dei flag di lancio: la usa sia l'avvio manuale (runbook §3) sia
l'avvio automatico al login (config/launchd/com.bagholderai.autostart.plist).

Uso (dal repo sul Mini):
  venv/bin/python3.13 scripts/start_bots.py               manuale: un giro di controlli, poi lancia
  venv/bin/python3.13 scripts/start_bots.py --auto        LaunchAgent: se rete/volume mancano riprova
                                                          ogni 60s per 30 min; rispetta il file "non avviare"
  venv/bin/python3.13 scripts/start_bots.py --dry-run     controlli + stampa cosa lancerebbe, non lancia
  venv/bin/python3.13 scripts/start_bots.py --test-detach lancia un processo finto al posto dei bot

Non riavvia mai bot già vivi: lancia solo ciò che manca (orchestrator, NewsKeeper v2).
Niente respawn: se un bot muore dopo l'avvio, questo script non lo rilancia.

Solo libreria standard + curl/pgrep di sistema: gira anche col python di Homebrew
del LaunchAgent. È Python e non bash perché sotto launchd /bin/bash non ha il
permesso macOS (TCC) di leggere /Volumes/Archivio, il python di Homebrew sì
(lo stesso del listener /approve) — verificato il 27-set.
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

REPO = "/Volumes/Archivio/bagholderai"
VENV_PY = "venv/bin/python3.13"
NO_AUTOSTART = os.path.expanduser("~/.bagholderai_no_autostart")
BOT_ENV = {
    "ENABLE_TF": "false",
    "ENABLE_SENTINEL": "true",
    "ENABLE_SHERPA": "true",
    "SHERPA_MODE": "live",
    "ALLOW_REAL_MONEY": "true",
}
RETRY_SECONDS = 60
AUTO_ATTEMPTS = 30

ORCHESTRATOR = "[-]m bot.orchestrator"
NEWSKEEPER = "[-]m bot.newskeeper_v2"
GRID = "[-]m bot.grid_runner"

MODE = "manual"


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} [start_bots:{MODE}] {msg}", flush=True)


def http_code(url: str) -> int:
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-m", "10", "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    try:
        return int(r.stdout.strip() or 0)
    except ValueError:
        return 0


def supabase_url() -> str:
    try:
        with open(f"{REPO}/config/.env") as f:
            for line in f:
                if line.startswith("SUPABASE_URL="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


def not_ready_reason() -> str:
    """'' = pronto a lanciare; altrimenti il motivo per riprovare più tardi."""
    if not os.access(f"{REPO}/{VENV_PY}", os.X_OK):
        return "Archivio non montato o venv assente"
    sb = supabase_url()
    if not sb:
        return "SUPABASE_URL non leggibile da config/.env"
    problems = []
    k = http_code("https://api.kraken.com/0/public/Time")
    if k != 200:
        problems.append(f"kraken={k}")
    s = http_code(f"{sb}/rest/v1/")  # sano = 401 senza chiave; bloccato = 0 o 5xx
    if not 200 <= s < 500:
        problems.append(f"supabase={s}")
    t = http_code("https://api.telegram.org")
    if t == 0:
        problems.append("telegram=000")
    return " ".join(problems)


def alive(pattern: str) -> bool:
    return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0


def spawn(cmd: list, logpath: str, append: bool, extra_env: dict | None = None) -> int:
    env = dict(os.environ)
    # launchd dà un ambiente minimo: stesso PATH/lingua di una sessione normale.
    env["PATH"] = "/opt/homebrew/bin:" + env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    env.setdefault("LANG", "en_US.UTF-8")
    env.update(extra_env or {})
    out = open(logpath, "a" if append else "w")
    p = subprocess.Popen(
        ["nohup", "caffeinate", "-i", *cmd],
        cwd=REPO, env=env, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
    )
    return p.pid


def launch() -> int:
    if MODE == "test":
        pid = spawn(["sleep", "901"], f"{REPO}/logs/autostart_detach_test.log", append=False)
        log(f"processo finto lanciato (pid {pid}, 'sleep 901'): deve sopravvivere alla fine del job")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    orch_log = f"logs/orchestrator_restart_{ts}.log"
    flags = " ".join(f"{k}={v}" for k, v in BOT_ENV.items())
    if alive(ORCHESTRATOR):
        log("orchestrator già vivo: non lo tocco")
    elif MODE == "dry":
        log(f"LANCEREI: {flags} nohup caffeinate -i {VENV_PY} -m bot.orchestrator > {orch_log}")
    else:
        pid = spawn([VENV_PY, "-m", "bot.orchestrator"], f"{REPO}/{orch_log}", append=False, extra_env=BOT_ENV)
        log(f"orchestrator lanciato (wrapper pid {pid}, log {orch_log}, flag {flags})")

    if alive(NEWSKEEPER):
        log("NewsKeeper v2 già vivo: non lo tocco")
    elif MODE == "dry":
        log(f"LANCEREI: nohup caffeinate -i {VENV_PY} -m bot.newskeeper_v2 >> logs/newskeeper_v2_boot.log")
    else:
        nk_log = f"{REPO}/logs/newskeeper_v2_boot.log"
        with open(nk_log, "a") as f:
            f.write(f"=== {datetime.now():%c} cold start ({MODE}, start_bots.py) ===\n")
        pid = spawn([VENV_PY, "-m", "bot.newskeeper_v2"], nk_log, append=True)
        log(f"NewsKeeper v2 lanciato (wrapper pid {pid})")

    if MODE == "dry":
        return 0
    time.sleep(20)
    if not alive(ORCHESTRATOR):
        log("ERRORE: orchestrator non risulta vivo 20s dopo il lancio")
        return 1
    grids = subprocess.run(["pgrep", "-f", GRID], capture_output=True, text=True).stdout.split()
    log(f"OK: orchestrator vivo, {len(grids)} grid attivi")
    return 0


def main() -> int:
    global MODE
    ap = argparse.ArgumentParser(description="Avvio a freddo dei bot BagHolderAI (R.7)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--auto", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--test-detach", action="store_true")
    a = ap.parse_args()
    MODE = "auto" if a.auto else "dry" if a.dry_run else "test" if a.test_detach else "manual"

    if MODE == "auto" and os.path.exists(NO_AUTOSTART):
        log(f"file 'non avviare' presente ({NO_AUTOSTART}): non faccio nulla")
        return 0

    attempts = AUTO_ATTEMPTS if MODE == "auto" else 1
    for attempt in range(1, attempts + 1):
        if MODE != "test" and alive(ORCHESTRATOR) and alive(NEWSKEEPER):
            log("bot già vivi: non faccio nulla")
            return 0
        why = not_ready_reason()
        if not why:
            return launch()
        log(f"tentativo {attempt}/{attempts}: non pronto ({why})")
        if attempt < attempts:
            time.sleep(RETRY_SECONDS)
    log("RINUNCIO: condizioni mai soddisfatte. Avvio a mano: runbook §3")
    return 1


if __name__ == "__main__":
    sys.exit(main())
