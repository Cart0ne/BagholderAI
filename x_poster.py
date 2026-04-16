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
    get_latest_diary,
    get_recent_config_changes,
    save_pending_draft,
    get_pending_draft,
    clear_pending_draft,
    already_posted_today,
    log_post,
    DEFAULT_SIGNATURE,
    DIARY_STALE_HOURS,
)
from utils.telegram_notifier import SyncTelegramNotifier


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


def _parse_ts(ts: str) -> datetime:
    """Parse a Supabase-style timestamptz string (handles both 'Z' and '+00:00')."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def cmd_cron(args):
    """Cron mode: read latest diary + 24h config changes -> generate -> save pending -> notify."""
    notifier = SyncTelegramNotifier()

    # 1. Anti-dupe check (once per calendar day)
    if already_posted_today():
        logger.info("Already posted today. Skipping.")
        notifier.send_message("⏸ <b>X post skip</b> — già postato oggi.")
        return

    # 2. Existing pending draft?
    pending = get_pending_draft()
    if pending:
        age_h = (datetime.now(timezone.utc) - _parse_ts(pending["generated_at"])).total_seconds() / 3600
        if age_h < 24:
            logger.info(f"Pending draft exists ({age_h:.1f}h old). Skipping regeneration.")
            notifier.send_message(
                f"⏸ <b>X post skip</b> — bozza Session {pending.get('session', '?')} "
                f"ancora in attesa di approvazione ({age_h:.1f}h).\n"
                f"Comandi: /approve · /discard · /rewrite"
            )
            return
        logger.info(f"Pending draft is stale ({age_h:.1f}h > 24h). Regenerating.")
        clear_pending_draft()

    # 3. Load inputs
    diary = get_latest_diary()
    config_changes = get_recent_config_changes()

    # 4. Decide if diary is fresh enough to headline the post
    use_diary = False
    if diary:
        diary_age_h = (datetime.now(timezone.utc) - _parse_ts(diary["created_at"])).total_seconds() / 3600
        use_diary = diary_age_h < DIARY_STALE_HOURS
        logger.info(
            f"Latest diary: Session {diary['session']} ({diary_age_h:.1f}h old) "
            f"-- {'USE' if use_diary else 'STALE'}"
        )
    else:
        logger.warning("No diary entry found in DB at all.")

    # 5. Skip if nothing worth saying
    if not use_diary and not config_changes:
        logger.info("Stale diary + no config changes. Skipping.")
        notifier.send_message(
            "ℹ️ <b>X post skip</b> — diary vecchio e nessuna modifica config nelle ultime 24h. "
            "Nulla di nuovo oggi."
        )
        return

    # 6. Generate draft
    logger.info(
        f"Generating post (use_diary={use_diary}, {len(config_changes)} config changes)"
    )
    draft = generate_post(diary, config_changes, use_diary)

    # 7. Persist pending + notify Max
    session = diary["session"] if (diary and use_diary) else None
    title = diary["title"] if (diary and use_diary) else None
    summary = diary["summary"] if (diary and use_diary) else None
    save_pending_draft(session, title, summary, draft, DEFAULT_SIGNATURE)

    full_text = f"{draft}\n\n{DEFAULT_SIGNATURE}"
    char_count = len(full_text)
    session_tag = f"Session {session}" if session else "Config summary"

    msg = (
        f"🐦 Bozza post X ({session_tag}):\n"
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
    """Generate a draft without posting or sending to Telegram — for ispezione."""
    diary = get_latest_diary()
    config_changes = get_recent_config_changes()

    use_diary = False
    if diary:
        diary_age_h = (datetime.now(timezone.utc) - _parse_ts(diary["created_at"])).total_seconds() / 3600
        use_diary = diary_age_h < DIARY_STALE_HOURS
        print(f"--- Latest diary: Session {diary['session']} ({diary_age_h:.1f}h) → "
              f"{'USE' if use_diary else 'STALE'} ---")
    else:
        print("--- No diary in DB ---")
    print(f"--- Config changes (24h): {len(config_changes)} ---")

    if not use_diary and not config_changes:
        print("Nothing to post — stale diary + no config changes.")
        return

    draft = generate_post(diary, config_changes, use_diary)
    full_text = f"{draft}\n\n{DEFAULT_SIGNATURE}"
    print(f"\n{draft}")
    print(f"\n📏 {len(full_text)}/270 chars (con firma)")


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
