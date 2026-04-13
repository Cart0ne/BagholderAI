#!/usr/bin/env python3.13
"""
BagHolderAI - X Poster Approval Listener (Telegram Long-Polling)

Lightweight Telegram listener that handles X post approvals.
Commands: /approve, /discard, /rewrite

Usage:
    python3.13 x_poster_approve.py
"""

import json
import logging
import os

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
)

PENDING_FILE = "/tmp/pending_x_post.json"


def load_pending() -> dict | None:
    """Load pending post from file."""
    if not os.path.exists(PENDING_FILE):
        return None
    with open(PENDING_FILE) as f:
        return json.load(f)


def delete_pending():
    """Remove pending post file."""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)


def is_max(update: Update) -> bool:
    """Check if the message is from Max's chat."""
    return str(update.effective_chat.id) == TelegramConfig.CHAT_ID


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve and publish the pending post to X."""
    if not is_max(update):
        return

    pending = load_pending()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    if already_posted_today():
        await update.message.reply_text("Gia' postato oggi. Uso /approve domani o --force da CLI.")
        return

    draft = pending["draft"]
    signature = pending.get("signature", "🤖 AI")
    session = pending["session"]

    url = post_to_x(draft, signature=signature)
    if url:
        mark_as_posted(session)
        log_post(url, session)
        delete_pending()
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

    pending = load_pending()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    delete_pending()
    await update.message.reply_text(f"🗑 Post scartato (Session {pending['session']}).")
    logger.info(f"Post discarded for session {pending['session']}")


async def cmd_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regenerate the post via Haiku and send new draft."""
    if not is_max(update):
        return

    pending = load_pending()
    if not pending:
        await update.message.reply_text("Nessun post in attesa.")
        return

    session = pending["session"]
    title = pending["title"]
    summary = pending["summary"]

    await update.message.reply_text("🔄 Riscrivo...")

    new_draft = generate_post(summary, title)
    pending["draft"] = new_draft

    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)

    full_text = f"{new_draft}\n\n{pending.get('signature', '🤖 AI')}"
    char_count = len(full_text)

    await update.message.reply_text(
        f"🐦 Nuova bozza (Session {session}):\n"
        f"\n"
        f"{new_draft}\n"
        f"\n"
        f"🤖 AI\n"
        f"\n"
        f"📏 {char_count}/270 chars\n"
        f"\n"
        f"Comandi: /approve · /discard · /rewrite"
    )
    logger.info(f"Post rewritten for session {session} ({char_count}/280 chars)")


async def cmd_xstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if there's a pending post."""
    if not is_max(update):
        return

    pending = load_pending()
    if pending:
        full_text = f"{pending['draft']}\n\n{pending.get('signature', '🤖 AI')}"
        await update.message.reply_text(
            f"📋 Post in attesa (Session {pending['session']}):\n"
            f"\n"
            f"{pending['draft']}\n"
            f"\n"
            f"🤖 AI\n"
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
