"""
BagHolderAI - bot_events_log helper (43a)

Single source of truth for structured events across the bot stack.
Events are written to the bot_events_log table in Supabase so the CEO
can query post-hoc ("what happened overnight?") with plain SQL instead
of scraping log files or relying on Telegram push.

Table schema (pre-created by CEO, RLS disabled):
    id          uuid PK
    created_at  timestamptz
    severity    'info' | 'warn' | 'error' | 'critical'
    category    'lifecycle' | 'trade' | 'safety' | 'tf' | 'config' | 'error'
    symbol      text NULL
    event       text
    message     text
    details     jsonb NULL

Contract:
- log_event MUST NOT raise. A failed INSERT degrades to a local warning
  and the caller proceeds. Missing an event is acceptable; crashing the
  bot because observability is down is not.
"""

import logging

from db.client import get_client

_logger = logging.getLogger("bagholderai.events")


def log_event(severity: str, category: str, event: str, message: str,
              symbol: str | None = None, details: dict | None = None) -> None:
    """Record an event in bot_events_log. Never raises.

    Args:
        severity: 'info' | 'warn' | 'error' | 'critical'
        category: 'lifecycle' | 'trade' | 'safety' | 'tf' | 'config' | 'error'
        event: short machine-readable event name (e.g. 'stop_loss_triggered')
        message: human-readable one-liner for the CEO reading the log
        symbol: optional trading pair (NULL for global/orchestrator events)
        details: optional JSONB payload for structured context
    """
    try:
        get_client().table("bot_events_log").insert({
            "severity": severity,
            "category": category,
            "symbol": symbol,
            "event": event,
            "message": message,
            "details": details,
        }).execute()
    except Exception as e:
        _logger.warning(f"bot_events_log insert failed ({event}): {e}")
