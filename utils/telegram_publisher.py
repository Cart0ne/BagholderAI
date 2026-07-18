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

import json
import logging
from datetime import datetime, timedelta, timezone

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


# ======================================================================
# (b) DIARY — post the CEO's session summary on a new COMPLETE entry (no pin)
# ======================================================================

DIARY_MARKER = "diary:last_posted_session"


def read_latest_diary(sb):
    """Most recent COMPLETE diary entry (gate on status so we never post a
    half-written draft)."""
    r = (
        sb.table("diary_entries")
        .select("session, title, summary, date, status")
        .eq("status", "COMPLETE")
        .order("session", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def build_diary_post(row) -> str:
    session = row.get("session")
    title = (row.get("title") or "").strip()
    summary = (row.get("summary") or "").strip()
    date_str = (row.get("date") or "").strip()
    head = f"📓 <b>New diary entry — Session {session}</b>"
    if date_str:
        head += f"\n<i>{date_str}</i>"
    body = ""
    if title:
        body += f"\n\n<b>{title}</b>"
    if summary:
        body += f"\n{summary}"
    return (
        f"{head}{body}\n\n"
        f"<i>{SITE_LINK.format(campaign='diary')}</i>"
    )


def diary_is_new(row, marker) -> bool:
    """New iff a COMPLETE entry with a summary has a higher session than the
    last posted one. Latest-only (a burst of back-written sessions announces
    just the newest → anti-spam)."""
    if not row or row.get("status") != "COMPLETE":
        return False
    if not (row.get("summary") or "").strip():
        return False
    try:
        last = int(marker) if marker is not None else -1
    except (TypeError, ValueError):
        last = -1
    try:
        return int(row.get("session")) > last
    except (TypeError, ValueError):
        return False


def publish_diary(sb=None, dry_run=False) -> dict:
    """Post the latest CEO diary summary if a newer COMPLETE session exists."""
    sb = sb or get_client()
    row = read_latest_diary(sb)
    if not row:
        return {"feature": "diary", "posted": False, "reason": "no COMPLETE diary"}
    if not diary_is_new(row, get_state(sb, DIARY_MARKER)):
        return {"feature": "diary", "posted": False, "reason": "no new session"}

    text = build_diary_post(row)
    if dry_run:
        logger.info("[dry-run] diary post:\n%s", text)
        return {"feature": "diary", "posted": False, "reason": "dry-run", "text": text}

    msg_id = _send_public(text, campaign="diary")
    if msg_id is None:
        return {"feature": "diary", "posted": False, "reason": "send failed"}

    set_state(sb, DIARY_MARKER, str(row.get("session")))
    return {"feature": "diary", "posted": True, "message_id": msg_id, "session": row.get("session")}


# ======================================================================
# (c) REGIME F&G — post on a confirmed regime-bucket change (debounced, no pin)
# ======================================================================
#
# Source: sentinel_scores (score_type='slow'). raw_signals already carries the
# computed regime bucket ("extreme_fear".."extreme_greed") + fng_value/label —
# so we read the regime the system already decided (no re-deriving thresholds).
# F&G updates ~1×/day; the slow loop (~4h) re-reads the same daily value.
#
# Anti-chatter guards (Max's "freno anti-tremolio"), all three must pass:
#   1. CONFIRMED: the latest K slow scans all agree on the bucket (kills a
#      single-scan fetch glitch).
#   2. CHANGED: the confirmed bucket differs from the last one we announced.
#   3. MIN-HOLD: at least REGIME_MIN_HOLD_HOURS since our last regime post
#      (caps to ~1/day, kills day-to-day flapping across a bucket boundary).

REGIME_MARKER = "regime:last_bucket"
REGIME_POSTED_AT = "regime:last_posted_at"
REGIME_CONFIRM_SCANS = 2
REGIME_MIN_HOLD_HOURS = 18

REGIME_LABELS = {
    "extreme_fear":  ("😱", "Extreme Fear"),
    "fear":          ("😨", "Fear"),
    "neutral":       ("😐", "Neutral"),
    "greed":         ("🤑", "Greed"),
    "extreme_greed": ("🤯", "Extreme Greed"),
}


def _parse_raw_signals(rs):
    if isinstance(rs, str):
        try:
            return json.loads(rs)
        except Exception:
            return {}
    return rs or {}


def read_recent_slow(sb, limit):
    r = (
        sb.table("sentinel_scores")
        .select("raw_signals, created_at")
        .eq("score_type", "slow")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return r.data or []


def confirmed_regime(rows, k=REGIME_CONFIRM_SCANS):
    """Return the regime bucket iff the latest k slow rows all agree; else None
    (chattering, or not enough history yet)."""
    if len(rows) < k:
        return None
    buckets = [_parse_raw_signals(r.get("raw_signals")).get("regime") for r in rows[:k]]
    if buckets and all(b and b == buckets[0] for b in buckets):
        return buckets[0]
    return None


def build_regime_post(bucket, fng_value=None, fng_label=None, prev_bucket=None) -> str:
    emoji, label = REGIME_LABELS.get(bucket, ("🌡️", bucket))
    if prev_bucket and prev_bucket in REGIME_LABELS:
        _, plabel = REGIME_LABELS[prev_bucket]
        line = f"The Fear &amp; Greed climate shifted from {plabel} to {emoji} <b>{label}</b>"
    else:
        line = f"The Fear &amp; Greed climate is now {emoji} <b>{label}</b>"
    fng_bit = f" (F&amp;G {fng_value})" if fng_value is not None else ""
    return (
        f"🌡️ <b>Market regime</b>\n"
        f"{line}{fng_bit}.\n\n"
        f"<i>{SITE_LINK.format(campaign='regime')}</i>"
    )


def publish_regime(sb=None, dry_run=False, k=REGIME_CONFIRM_SCANS, now=None) -> dict:
    """Post a regime shift if confirmed + changed + past the min-hold window."""
    sb = sb or get_client()
    rows = read_recent_slow(sb, k)
    bucket = confirmed_regime(rows, k)
    if not bucket:
        return {"feature": "regime", "posted": False, "reason": "not confirmed (chatter/insufficient history)"}

    last_bucket = get_state(sb, REGIME_MARKER)
    if bucket == last_bucket:
        return {"feature": "regime", "posted": False, "reason": "unchanged"}

    now = now or datetime.now(timezone.utc)
    last_at = get_state(sb, REGIME_POSTED_AT)
    if last_at:
        try:
            prev_dt = datetime.fromisoformat(last_at)
            if (now - prev_dt).total_seconds() < REGIME_MIN_HOLD_HOURS * 3600:
                return {"feature": "regime", "posted": False, "reason": "debounced (min-hold)"}
        except Exception:
            pass

    latest = _parse_raw_signals(rows[0].get("raw_signals"))
    text = build_regime_post(bucket, latest.get("fng_value"), latest.get("fng_label"), last_bucket)
    if dry_run:
        logger.info("[dry-run] regime post:\n%s", text)
        return {"feature": "regime", "posted": False, "reason": "dry-run", "text": text, "bucket": bucket}

    msg_id = _send_public(text, campaign="regime")
    if msg_id is None:
        return {"feature": "regime", "posted": False, "reason": "send failed"}

    set_state(sb, REGIME_MARKER, bucket)
    set_state(sb, REGIME_POSTED_AT, now.isoformat())
    return {"feature": "regime", "posted": True, "message_id": msg_id, "bucket": bucket}


# ======================================================================
# (d) PRESS REVIEW — one digest/day, top-N NewsKeeper articles with links (no pin)
# ======================================================================
#
# Source: newskeeper_signals (~82 rows/day → must rank + cap). NewsKeeper already
# labels relevance high/medium/discard; we keep high>medium, drop discard,
# break ties by confidence, dedup by event_key (same story across outlets),
# take the top PRESS_MAX. Posted once/day, in the morning (hour gate).
#
# v2 is still "shadow", but a press review (links to real articles it surfaced)
# is the LOW-risk way to give it a public airing — worst case a so-so article,
# not a wrong trade signal.

PRESS_MARKER = "press_review:last_date"
PRESS_HOUR = 9            # local hour gate (cron runs Europe/Rome on the Mini)
PRESS_MAX = 5
PRESS_RELEVANCE_RANK = {"high": 2, "medium": 1}  # "discard"/unknown → excluded


def _esc(s) -> str:
    """Escape for Telegram HTML parse mode."""
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _polarity_emoji(p) -> str:
    try:
        p = int(p)
    except (TypeError, ValueError):
        return "•"
    return "📈" if p > 0 else ("📉" if p < 0 else "•")


def read_press_candidates(sb):
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    r = (
        sb.table("newskeeper_signals")
        .select("summary, relevance, confidence, polarity, event_key, raw_data, created_at")
        .gte("created_at", since)
        .in_("relevance", ["high", "medium"])
        .order("created_at", desc=True)
        .limit(120)
        .execute()
    )
    return r.data or []


def rank_press(rows, max_n=PRESS_MAX):
    """Rank by relevance (high>medium) then confidence; dedup by event_key
    (fallback link); keep the best per story; return the top max_n."""
    cand = []
    for r in rows:
        rank = PRESS_RELEVANCE_RANK.get((r.get("relevance") or "").lower())
        if rank is None:
            continue
        raw = _parse_raw_signals(r.get("raw_data"))
        link = raw.get("link")
        title = (r.get("summary") or "").strip()
        if not link or not title:
            continue
        cand.append({
            "title": title,
            "link": link,
            "rank": rank,
            "confidence": float(r.get("confidence") or 0),
            "polarity": r.get("polarity"),
            "key": r.get("event_key") or link,
        })
    cand.sort(key=lambda x: (x["rank"], x["confidence"]), reverse=True)
    out, seen = [], set()
    for c in cand:
        if c["key"] in seen:
            continue
        seen.add(c["key"])
        out.append(c)
        if len(out) >= max_n:
            break
    return out


def build_press_post(items, date_str) -> str:
    lines = ["🗞️ <b>Daily crypto press review</b>", f"<i>{_esc(date_str)}</i>", ""]
    for it in items:
        emoji = _polarity_emoji(it.get("polarity"))
        lines.append(f'{emoji} <a href="{_esc(it["link"])}">{_esc(it["title"])}</a>')
    lines.append("")
    lines.append(f"<i>Selected by NewsKeeper · {SITE_LINK.format(campaign='press')}</i>")
    return "\n".join(lines)


def publish_press_review(sb=None, dry_run=False, now=None) -> dict:
    """One morning digest per day of NewsKeeper's top relevant articles."""
    sb = sb or get_client()
    now = now or datetime.now()  # local (hour gate); matches daily_report convention
    if now.hour < PRESS_HOUR:
        return {"feature": "press_review", "posted": False, "reason": f"before {PRESS_HOUR}:00"}
    today = now.date().isoformat()
    if get_state(sb, PRESS_MARKER) == today:
        return {"feature": "press_review", "posted": False, "reason": "already posted today"}

    items = rank_press(read_press_candidates(sb), PRESS_MAX)
    if not items:
        return {"feature": "press_review", "posted": False, "reason": "no relevant articles"}

    text = build_press_post(items, today)
    if dry_run:
        logger.info("[dry-run] press_review post:\n%s", text)
        return {"feature": "press_review", "posted": False, "reason": "dry-run", "text": text, "count": len(items)}

    msg_id = _send_public(text, campaign="press")
    if msg_id is None:
        return {"feature": "press_review", "posted": False, "reason": "send failed"}

    set_state(sb, PRESS_MARKER, today)
    return {"feature": "press_review", "posted": True, "message_id": msg_id, "count": len(items)}


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
    for fn in (publish_status_line, publish_diary, publish_regime, publish_press_review):
        try:
            results.append(fn(sb=sb, dry_run=dry_run))
        except Exception as e:
            logger.error("%s raised: %s", getattr(fn, "__name__", fn), e)
            results.append({"feature": getattr(fn, "__name__", "?"), "posted": False, "reason": f"exception: {e}"})
    return results
