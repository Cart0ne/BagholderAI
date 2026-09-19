#!/bin/zsh
# Supabase VM metrics recorder wrapper (19-Sep-2026, after the 17/18-Sep outages).
#
# Appends one JSON line every 30 min to logs/supabase_metrics.jsonl on the
# Archivio volume, next to the other logs (read-only GET of the project's
# metrics endpoint, no SQL, no alerts).
#
# Install on Mac Mini (one-time):
#   crontab -e
#   */30 * * * * /Volumes/Archivio/bagholderai/scripts/cron_supabase_metrics.sh
# Test manually once:
#   /Volumes/Archivio/bagholderai/scripts/cron_supabase_metrics.sh
#   tail -1 /Volumes/Archivio/bagholderai/logs/supabase_metrics.jsonl
# Remove: delete the crontab line.
#
# cron has Full Disk Access on the Mini, so it can write to Archivio
# (telegram_publisher's cron does the same). If the volume is not mounted
# nothing runs anyway: the script itself lives there.

set -u
REPO="/Volumes/Archivio/bagholderai"
cd "$REPO" || exit 1
# shellcheck disable=SC1091
source venv/bin/activate
python3.13 scripts/supabase_metrics_recorder.py "$REPO/logs/supabase_metrics.jsonl" \
  >> "$REPO/logs/cron_supabase_metrics.log" 2>&1
