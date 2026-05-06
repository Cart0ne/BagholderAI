"""Sherpa config writer (Sprint 1).

LIVE mode only. Writes a single parameter to bot_config and appends a
row to config_changes_log with changed_by='sherpa'. The DRY_RUN path
never reaches this module — it INSERTs into sherpa_proposals from the
main loop instead.

stop_buy_drawdown_pct is intentionally NOT writable from here. Per CEO
brief, it remains Board-only in Sprint 1; Sherpa logs a "would-have"
flag in sherpa_proposals.proposed_stop_buy_active for analysis only.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("bagholderai.sherpa.writer")

# Whitelist: only parameters Sherpa is allowed to write in LIVE mode.
WRITABLE_PARAMETERS = {"buy_pct", "sell_pct", "idle_reentry_hours"}


def write_parameter(
    supabase,
    symbol: str,
    parameter: str,
    new_value: float,
    old_value: Optional[float],
) -> bool:
    """Update bot_config and append config_changes_log. Returns True if
    a write actually happened. Refuses parameters not in WRITABLE_PARAMETERS.
    """
    if parameter not in WRITABLE_PARAMETERS:
        logger.error(f"Refusing to write non-whitelisted parameter '{parameter}'")
        return False

    try:
        supabase.table("bot_config").update({parameter: new_value}).eq(
            "symbol", symbol
        ).execute()
    except Exception as e:
        logger.error(f"bot_config UPDATE failed for {symbol}.{parameter}: {e}")
        return False

    try:
        supabase.table("config_changes_log").insert({
            "symbol": symbol,
            "parameter": parameter,
            "old_value": _to_text(old_value),
            "new_value": _to_text(new_value),
            "changed_by": "sherpa",
        }).execute()
    except Exception as e:
        # The bot_config write already landed; the audit row failing is
        # bad but not fatal. Log loudly and move on.
        logger.error(f"config_changes_log INSERT failed for {symbol}.{parameter}: {e}")

    logger.info(
        f"Sherpa wrote {symbol}.{parameter}: {old_value} -> {new_value}"
    )
    return True


def _to_text(v: Optional[float]) -> Optional[str]:
    if v is None:
        return None
    # config_changes_log columns are text; mirror the dashboard's format
    # (4 decimals max, trim trailing zeros) so values stay comparable.
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return s or "0"
