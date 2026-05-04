#!/bin/bash
# X Scanner Weekly Cron — BagHolderAI
# Runs every Saturday at 08:00 (Mac Mini local time)
#
# Install (Mac Mini):
#   crontab -e
#   0 8 * * 6 /Volumes/Archivio/bagholderai/scripts/x_scanner_cron.sh

set -e

REPO_DIR="/Volumes/Archivio/bagholderai"
LOG_DIR="$REPO_DIR/logs"
LOG_FILE="$LOG_DIR/x_scanner_cron.log"

mkdir -p "$LOG_DIR"

cd "$REPO_DIR"
source venv/bin/activate

{
    echo "=== X Scanner run: $(date) ==="
    python3.13 -m scripts.x_scanner_cron
    echo "=== Completed at $(date) ==="
    echo ""
} 2>&1 | tee -a "$LOG_FILE"
