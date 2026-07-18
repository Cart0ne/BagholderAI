"""Telegram content publisher (public channel) — T.1.

A subsystem SEPARATE from the trading bots: the `telegram_publisher.py` cron
entrypoint watches Supabase and posts channel content when something worth
sharing changes. Design notes:

- Send-only (never calls getUpdates) → cannot conflict with the /approve
  listener's single-consumer constraint.
- Idempotent via a small marker store (`telegram_publish_state`): the cron runs
  every ~10 min but each novelty is posted exactly once.
- Decoupled from the grid/orchestrator lifecycle (Max: "Telegram è indipendente
  dal resto"): restarting the bots does not touch this, and vice-versa.
- The `telegram` SDK is imported lazily inside the IO functions so this module
  stays importable (and its pure logic testable) on the dev box, where the
  python-telegram-bot install is broken (the bot only runs on the Mac Mini).

Features are built incrementally:
  (a) status line  — post + PIN (only the status line is ever pinned)
  (b) diary        — post the CEO's session summary  [TODO]
  (c) regime F&G   — post on regime-bucket change, debounced  [TODO]
  (d) press review — one digest/day, top-N with links  [TODO]
"""

import logging
from datetime import datetime, timezone

from config.settings import TelegramConfig
from db.client import get_client

logger = logging.getLogger("bagholderai.telegram_publisher")

STATE_TABLE = "telegram_publish_state"

SITE_LINK = (
    '<a href="https://bagholderai.lol/?utm_source=telegram&amp;'
    'utm_medium=social&amp;utm_campaign={campaign}">bagholderai.lol</a>'
)


# ----------------------------------------------------------------------
# Marker store (key -> value). The publisher's memory of what it already sent.
# ----------------------------------------------------------------------

def get_state(sb, key):
    """Return the stored value for `key`, or None."""
    try:
        r = (
            sb.table(STATE_TABLE)
            .select("value")
            .eq("key", key)
            .limit(1)
            .execute()
        )
        return r.data[0]["value"] if r.data else None
    except Exception as e:
        logger.warning("get_state(%s) failed: %s", key, e)
        return None


def set_state(sb, key, value):
    """Upsert `key` = `value`."""
    try:
        sb.table(STATE_TABLE).upsert(
            {
                "key": key,
                "value": str(value),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="key",
        ).execute()
    except Exception as e:
        logger.warning("set_state(%s) failed: %s", key, e)


# ======================================================================
# (a) STATUS LINE — post + pin (only the status line is ever pinned)
# ======================================================================

STATUS_MARKER = "status_line:last_updated_at"
STATUS_PIN = "status_line:pinned_message_id"


def read_latest_project_status(sb):
    """The single project_status row (updated in place)."""
    r = (
        sb.table("project_status")
        .select("status_text, status_emoji, updated_at")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def build_status_post(row) -> str:
    """Render the status-line post. status_text is the CEO's public-crafted
    line (English, mirrors the site) → posted verbatim."""
    emoji = (row.get("status_emoji") or "📌").strip()
    text = (row.get("status_text") or "").strip()
    return (
        f"{emoji} <b>Status update</b>\n\n"
        f"{text}\n\n"
        f"<i>{SITE_LINK.format(campaign='status')}</i>"
    )


def status_changed(row, last_marker) -> bool:
    """New iff the row's updated_at differs from the stored marker."""
    if not row:
        return False
    return str(row.get("updated_at")) != (last_marker or "")


def publish_status_line(sb=None, dry_run=False) -> dict:
    """Post + pin the status line if project_status changed since last time.
    Returns a small result dict (never raises)."""
    sb = sb or get_client()
    row = read_latest_project_status(sb)
    if not row:
        return {"feature": "status_line", "posted": False, "reason": "no project_status row"}
    if not status_changed(row, get_state(sb, STATUS_MARKER)):
        return {"feature": "status_line", "posted": False, "reason": "unchanged"}

    text = build_status_post(row)
    if dry_run:
        logger.info("[dry-run] status_line post:\n%s", text)
        return {"feature": "status_line", "posted": False, "reason": "dry-run", "text": text}

    prev_pin = get_state(sb, STATUS_PIN)
    msg_id = _send_and_pin_public(text, prev_pin)
    if msg_id is None:
        return {"feature": "status_line", "posted": False, "reason": "send failed"}

    set_state(sb, STATUS_MARKER, str(row.get("updated_at")))
    set_state(sb, STATUS_PIN, str(msg_id))
    return {"feature": "status_line", "posted": True, "message_id": msg_id}


# ----------------------------------------------------------------------
# IO layer (telegram) — lazy SDK import so the module loads without it.
# Posts to the PUBLIC channel; keeps exactly one pinned message (the status
# line) by unpinning our previous pin before pinning the new one.
# ----------------------------------------------------------------------

def _send_and_pin_public(text, prev_pin_message_id):
    token = TelegramConfig.PUBLIC_BOT_TOKEN
    chat = TelegramConfig.PUBLIC_CHAT_ID
    if not token or not chat:
        logger.warning("public bot not configured (token/chat missing) — skipping send")
        return None
    try:
        return _run_async(_async_send_and_pin(token, chat, text, prev_pin_message_id))
    except Exception as e:
        logger.error("send/pin failed: %s", e)
        return None


async def _async_send_and_pin(token, chat, text, prev_pin_message_id):
    from telegram import Bot
    from telegram.constants import ParseMode

    bot = Bot(token=token)
    msg = await bot.send_message(
        chat_id=chat,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    # Keep exactly one pinned message: unpin our previous status pin (if any),
    # then pin the new one. We only ever touch pins we created.
    if prev_pin_message_id:
        try:
            await bot.unpin_chat_message(chat_id=chat, message_id=int(prev_pin_message_id))
        except Exception as e:
            logger.warning("unpin previous status pin failed: %s", e)
    try:
        await bot.pin_chat_message(
            chat_id=chat, message_id=msg.message_id, disable_notification=True
        )
    except Exception as e:
        logger.warning("pin failed (is the bot admin with pin rights?): %s", e)
    return msg.message_id


def _send_public(text, campaign="channel"):
    """Send a plain (non-pinned) message to the public channel. Returns the
    message_id or None. Used by the non-pinned features (b/c/d)."""
    token = TelegramConfig.PUBLIC_BOT_TOKEN
    chat = TelegramConfig.PUBLIC_CHAT_ID
    if not token or not chat:
        logger.warning("public bot not configured (token/chat missing) — skipping send")
        return None
    try:
        return _run_async(_async_send(token, chat, text))
    except Exception as e:
        logger.error("send failed: %s", e)
        return None


async def _async_send(token, chat, text):
    from telegram import Bot
    from telegram.constants import ParseMode

    bot = Bot(token=token)
    msg = await bot.send_message(
        chat_id=chat,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    return msg.message_id


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)


# ----------------------------------------------------------------------
# Orchestration — run all enabled publishers (called by the cron entrypoint).
# ----------------------------------------------------------------------

def run_all(dry_run=False) -> list:
    """Run every enabled publisher once. Returns a list of result dicts."""
    sb = get_client()
    results = []
    for fn in (publish_status_line,):  # (b)/(c)/(d) appended as they land
        try:
            results.append(fn(sb=sb, dry_run=dry_run))
        except Exception as e:
            logger.error("%s raised: %s", getattr(fn, "__name__", fn), e)
            results.append({"feature": getattr(fn, "__name__", "?"), "posted": False, "reason": f"exception: {e}"})
    return results
