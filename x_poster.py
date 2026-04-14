#!/usr/bin/env python3.13
"""
BagHolderAI - X Poster CLI & Cron Entry Point

Usage:
    # Cron mode: read diary -> generate via Haiku -> send to Telegram for approval
    python3.13 x_poster.py --cron

    # CLI mode: post exact text immediately (no Haiku, no approval)
    python3.13 x_poster.py --text "We just launched the Trend Follower." --sig "🤖 AI"
    python3.13 x_poster.py --text "Volume 1 is live." --sig "👤 CO-FOUNDER"
    python3.13 x_poster.py --text "New dashboard." --sig "🤖 AI" --image screenshots/dashboard.png

    # Generate only (no post, no Telegram)
    python3.13 x_poster.py --generate-only
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.x_poster")

from utils.x_poster import (
    generate_post,
    post_to_x,
    get_latest_unposted_diary,
    mark_as_posted,
    already_posted_today,
    log_post,
    DEFAULT_SIGNATURE,
)
from utils.telegram_notifier import SyncTelegramNotifier

PENDING_FILE = "/tmp/pending_x_post.json"


def cmd_cli(args):
    """Post exact text immediately — no Haiku, no approval."""
    if already_posted_today():
        logger.warning("Already posted today. Use --force to override.")
        if not args.force:
            return

    url = post_to_x(args.text, signature=args.sig, image_path=args.image)
    if url:
        log_post(url, session=0)
        notifier = SyncTelegramNotifier()
        notifier.send_message(f"✅ <b>Posted to X (CLI)</b>\n\n\"{args.text}\"\n\n🔗 {url}")
    else:
        logger.error("Failed to post to X.")
        sys.exit(1)


def cmd_cron(args):
    """Cron mode: read diary -> generate -> save pending -> notify Telegram."""
    notifier = SyncTelegramNotifier()

    if already_posted_today():
        logger.info("Already posted today. Skipping.")
        notifier.send_message("⏸ <b>X post skip</b> — già postato oggi.")
        return

    # Check for expired pending post (>24h)
    import os
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE) as f:
            pending = json.load(f)
        gen_time = datetime.fromisoformat(pending["generated_at"])
        age_hours = (datetime.now(timezone.utc) - gen_time.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if age_hours < 24:
            logger.info("Pending post already exists (waiting for approval). Skipping.")
            notifier.send_message(
                f"⏸ <b>X post skip</b> — bozza Session {pending.get('session', '?')} "
                f"ancora in attesa di approvazione ({age_hours:.1f}h).\n"
                f"Usa /approve · /discard · /rewrite"
            )
            return
        else:
            logger.info("Pending post expired (>24h). Generating new one.")
            os.remove(PENDING_FILE)

    # Get unposted diary entry
    diary = get_latest_unposted_diary()
    if not diary:
        logger.info("No unposted diary entries found. Nothing to do.")
        notifier.send_message("ℹ️ <b>X post skip</b> — nessuna diary entry nuova da postare.")
        return

    session = diary["session"]
    title = diary["title"]
    summary = diary["summary"]

    logger.info(f"Generating post for Session {session}: {title}")
    draft = generate_post(summary, title)

    # Save pending
    pending = {
        "session": session,
        "title": title,
        "summary": summary,
        "draft": draft,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signature": DEFAULT_SIGNATURE,
    }
    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)

    # Calculate char count with signature
    full_text = f"{draft}\n\n{DEFAULT_SIGNATURE}"
    char_count = len(full_text)

    # Notify Telegram
    msg = (
        f"🐦 Bozza post X (Session {session}):\n"
        f"\n"
        f"{draft}\n"
        f"\n"
        f"{DEFAULT_SIGNATURE}\n"
        f"\n"
        f"📏 {char_count}/270 chars\n"
        f"\n"
        f"Comandi: /approve · /discard · /rewrite"
    )
    notifier.send_message(msg)
    logger.info(f"Draft sent to Telegram ({char_count}/270 chars). Waiting for approval.")


def cmd_generate_only(args):
    """Generate a draft without posting or sending to Telegram."""
    diary = get_latest_unposted_diary()
    if not diary:
        print("No unposted diary entries found.")
        return

    session = diary["session"]
    title = diary["title"]
    summary = diary["summary"]

    print(f"--- Session {session}: {title} ---")
    draft = generate_post(summary, title)
    full_text = f"{draft}\n\n{DEFAULT_SIGNATURE}"
    print(f"\n{draft}")
    print(f"\n📏 {len(full_text)}/280 chars (con firma)")


def main():
    parser = argparse.ArgumentParser(description="BagHolderAI X Poster")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cron", action="store_true", help="Cron mode: generate + Telegram approval")
    group.add_argument("--text", type=str, help="CLI mode: post exact text immediately")
    group.add_argument("--generate-only", action="store_true", help="Generate draft only (no post)")

    parser.add_argument("--sig", type=str, default=DEFAULT_SIGNATURE, help=f"Signature (default: {DEFAULT_SIGNATURE})")
    parser.add_argument("--image", type=str, default=None, help="Image path to attach")
    parser.add_argument("--force", action="store_true", help="Override anti-dupe check")

    args = parser.parse_args()

    if args.text:
        cmd_cli(args)
    elif args.cron:
        cmd_cron(args)
    elif args.generate_only:
        cmd_generate_only(args)


if __name__ == "__main__":
    main()
