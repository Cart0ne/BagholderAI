#!/usr/bin/env python3.13
"""
BagHolderAI - X Poster Approval Listener (Telegram Long-Polling)

Lightweight Telegram listener that handles X post approvals.
Commands: /approve, /discard, /rewrite, /xstatus

Pending drafts live in Supabase (`pending_x_posts`) — not on the local
filesystem — so they survive Mac Mini restarts and are the same source
of truth that the cron reads/writes.

Usage:
    python3.13 x_poster_approve.py
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bagholderai.x_approve")

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config.settings import TelegramConfig
from utils.x_poster import (
    generate_post,
    post_to_x,
    mark_as_posted,
    already_posted_today,
    log_post,
    get_pending_draft,
    clear_pending_draft,
    save_pending_draft,
    get_recent_config_changes,
    DEFAULT_SIGNATURE,
    DIARY_STALE_HOURS,
)


def is_max(update: Update) -> bool:
    """Check if the message is from Max's chat."""
    return str(update.effective_chat.id) == TelegramConfig.CHAT_ID


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve and publish the pending post to X."""
    if not is_max(update):
        return

    pending = get_pending_draft()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    if already_posted_today():
        await update.message.reply_text("Già postato oggi. /approve domani o --force da CLI.")
        return

    draft = pending["draft"]
    signature = pending.get("signature") or DEFAULT_SIGNATURE
    session = pending.get("session")

    url = post_to_x(draft, signature=signature)
    if url:
        if session is not None:
            mark_as_posted(session)
        log_post(url, session or 0)
        clear_pending_draft()
        await update.message.reply_text(
            f"✅ Pubblicato!\n\n\"{draft}\"\n\n🔗 {url}"
        )
        logger.info(f"Post approved and published: {url}")
    else:
        await update.message.reply_text("❌ Errore nella pubblicazione. Controlla i log.")


async def cmd_discard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Discard the pending post."""
    if not is_max(update):
        return

    pending = get_pending_draft()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    session_tag = f"Session {pending['session']}" if pending.get("session") else "draft"
    clear_pending_draft()
    await update.message.reply_text(f"🗑 Post scartato ({session_tag}).")
    logger.info(f"Post discarded ({session_tag})")


async def cmd_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regenerate the post via Haiku and send new draft."""
    if not is_max(update):
        return

    pending = get_pending_draft()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    await update.message.reply_text("🔄 Riscrivo...")

    # Reconstruct a diary dict from the saved pending row (if it had one).
    diary = None
    use_diary = False
    if pending.get("session") is not None and pending.get("summary"):
        diary = {
            "session": pending["session"],
            "title": pending.get("title") or "",
            "summary": pending["summary"],
            # Not saved at pending time; treat as fresh so rewrite uses it.
            "created_at": None,
        }
        use_diary = True

    # Config changes are re-fetched fresh — may have moved since first draft.
    config_changes = get_recent_config_changes()

    new_draft = generate_post(diary, config_changes, use_diary)

    save_pending_draft(
        session=pending.get("session"),
        title=pending.get("title"),
        summary=pending.get("summary"),
        draft=new_draft,
        signature=pending.get("signature") or DEFAULT_SIGNATURE,
    )

    full_text = f"{new_draft}\n\n{DEFAULT_SIGNATURE}"
    char_count = len(full_text)
    session_tag = f"Session {pending['session']}" if pending.get("session") else "Config summary"

    await update.message.reply_text(
        f"🐦 Nuova bozza ({session_tag}):\n"
        f"\n"
        f"{new_draft}\n"
        f"\n"
        f"{DEFAULT_SIGNATURE}\n"
        f"\n"
        f"📏 {char_count}/270 chars\n"
        f"\n"
        f"Comandi: /approve · /discard · /rewrite"
    )
    logger.info(f"Post rewritten ({session_tag}, {char_count}/270 chars)")


async def cmd_xstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if there's a pending post."""
    if not is_max(update):
        return

    pending = get_pending_draft()
    if pending:
        signature = pending.get("signature") or DEFAULT_SIGNATURE
        full_text = f"{pending['draft']}\n\n{signature}"
        session_tag = f"Session {pending['session']}" if pending.get("session") else "Config summary"
        await update.message.reply_text(
            f"📋 Post in attesa ({session_tag}):\n"
            f"\n"
            f"{pending['draft']}\n"
            f"\n"
            f"{DEFAULT_SIGNATURE}\n"
            f"\n"
            f"📏 {len(full_text)}/270 chars\n"
            f"Comandi: /approve · /discard · /rewrite"
        )
    else:
        posted = "Si" if already_posted_today() else "No"
        await update.message.reply_text(f"Nessun post in attesa.\nGia' postato oggi: {posted}")


def main():
    logger.info("X Poster Approval Listener starting...")

    app = ApplicationBuilder().token(TelegramConfig.BOT_TOKEN).build()

    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("discard", cmd_discard))
    app.add_handler(CommandHandler("rewrite", cmd_rewrite))
    app.add_handler(CommandHandler("xstatus", cmd_xstatus))

    logger.info("Listening for /approve, /discard, /rewrite, /xstatus commands...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
