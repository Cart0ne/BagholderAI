#!/bin/zsh
# Supabase VM metrics recorder wrapper (19-Sep-2026, after the 17/18-Sep outages).
#
# Appends one JSON line every 30 min to $HOME/supabase_metrics.jsonl
# (read-only GET of the project's metrics endpoint, no SQL, no alerts).
#
# Install on Mac Mini (one-time):
#   crontab -e
#   */30 * * * * /Volumes/Archivio/bagholderai/scripts/cron_supabase_metrics.sh
# Test manually once:
#   /Volumes/Archivio/bagholderai/scripts/cron_supabase_metrics.sh
#   tail -1 $HOME/supabase_metrics.jsonl
# Remove: delete the crontab line.
#
# Logs on $HOME, not on the mounted volume (TCC blocks cron writes to
# Archivio) — same as scripts/cron_reconcile.sh.

set -u
REPO="/Volumes/Archivio/bagholderai"
LOG="$HOME/cron_supabase_metrics.log"

{
  cd "$REPO" || {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') FATAL: cannot cd to $REPO (volume not mounted?)"
    exit 1
  }
  # shellcheck disable=SC1091
  source venv/bin/activate
  python3.13 scripts/supabase_metrics_recorder.py
} >> "$LOG" 2>&1
