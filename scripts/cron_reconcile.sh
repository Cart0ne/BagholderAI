#!/bin/zsh
# Brief 71a Task 2 — nightly Binance reconciliation wrapper.
#
# Runs reconcile_binance.py --write so every overnight produces a fresh
# row in `reconciliation_runs` for the public /dashboard reconciliation
# table. Scheduled via crontab at 03:00 Europe/Rome (= 01:00 UTC),
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
  python3.13 scripts/reconcile_binance.py --write
  rc=$?
  echo "===== $TS reconcile exit=$rc ====="
} >> "$LOG" 2>&1
