#!/usr/bin/env python3.13
"""
BagHolderAI — Telegram content publisher (cron entrypoint).

Watches Supabase and posts channel content when something worth sharing
changes. Send-only, decoupled from the trading bots. See
utils/telegram_publisher.py for the design notes.

Usage (on the Mac Mini, from the repo root, inside the venv):
    # Cron: run every enabled publisher once (this is what crontab calls)
    python3.13 telegram_publisher.py --cron

    # Dry-run: print what WOULD be posted, send nothing (safe anywhere)
    python3.13 telegram_publisher.py --cron --dry-run

    # Single feature (debug)
    python3.13 telegram_publisher.py --status
    python3.13 telegram_publisher.py --status --dry-run

Suggested crontab (Europe/Rome), every 10 minutes:
    */10 * * * * cd /Volumes/Archivio/bagholderai && venv/bin/python3.13 telegram_publisher.py --cron >> logs/telegram_publisher.log 2>&1
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.telegram_publisher.cli")

from utils.telegram_publisher import run_all, publish_status_line


def main():
    ap = argparse.ArgumentParser(description="BagHolderAI Telegram content publisher")
    ap.add_argument("--cron", action="store_true", help="run all enabled publishers once")
    ap.add_argument("--status", action="store_true", help="run only the status-line publisher")
    ap.add_argument("--dry-run", action="store_true", help="print what would be posted, send nothing")
    args = ap.parse_args()

    if not (args.cron or args.status):
        ap.print_help()
        sys.exit(2)

    if args.cron:
        results = run_all(dry_run=args.dry_run)
    else:  # --status
        results = [publish_status_line(dry_run=args.dry_run)]

    for r in results:
        logger.info("result: %s", r)


if __name__ == "__main__":
    main()
