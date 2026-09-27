#!/bin/zsh
# Nightly reconciliation wrapper — KRAKEN since R.1 (S129, 2026-09-27).
#
# Runs reconcile_kraken.py --write: one row per real-money symbol
# (venue='kraken') in `reconciliation_runs`, shown in /admin
# "Reconciliation · Kraken". Until 2026-09-27 this ran reconcile_binance.py
# (brief 71a, S71) against the Binance testnet, retired on 7 Aug 2026 and
# returning only WARN_BINANCE_EMPTY since; that script stays in the repo, unused. Scheduled via crontab at 03:00 Europe/Rome (= 01:00 UTC),
# BEFORE the bot's daily retention at 04:00 UTC.
#
# Install on Mac Mini (one-time):
#   1. ensure repo lives at /Volumes/Archivio/bagholderai
#   2. ensure venv exists with ccxt + httpx (already true)
#   3. confirm Full Disk Access for `cron` (System Settings →
#      Privacy & Security → Full Disk Access → toggle `/usr/sbin/cron`).
#      Without this, the cron job can't read /Volumes/Archivio.
#   4. install crontab:
#        crontab -e
#        0 3 * * * /Volumes/Archivio/bagholderai/scripts/cron_reconcile.sh
#   5. test manually once:
#        /Volumes/Archivio/bagholderai/scripts/cron_reconcile.sh
#        tail $HOME/cron_reconcile.log
#
# Memoria `project_cron_mac_mini.md`: cron logs MUST live on $HOME, not
# on the mounted volume (TCC blocks writes from cron daemon to Archivio).
# Same reason as the previous daily_report cron.

set -u
REPO="/Volumes/Archivio/bagholderai"
LOG="$HOME/cron_reconcile.log"
TS="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

{
  echo ""
  echo "===== $TS reconcile start ====="
  cd "$REPO" || {
    echo "FATAL: cannot cd to $REPO (volume not mounted?)"
    exit 1
  }
  # shellcheck disable=SC1091
  source venv/bin/activate
  python3.13 scripts/reconcile_kraken.py --write
  rc=$?
  echo "===== $TS reconcile exit=$rc ====="
} >> "$LOG" 2>&1
