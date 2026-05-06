"""Cooldown manager (Sherpa Sprint 1).

If the Board has touched a parameter in the last 24h via grid.html (the
dashboard writes config_changes_log rows with changed_by != 'sherpa'),
Sherpa MUST NOT overwrite that parameter on that bot until the cooldown
expires. This is the user-override contract.

Implementation note: the dashboard currently writes changed_by='manual-ceo'
(see web/grid.html). We don't hard-code that string — any value that is
not 'sherpa' counts as a non-Sherpa change and arms the cooldown. That
keeps the rule robust if the dashboard label is renamed later.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

logger = logging.getLogger("bagholderai.sherpa.cooldown")

COOLDOWN_HOURS = 24


def parameters_in_cooldown(
    supabase,
    symbol: str,
    parameters: Iterable[str],
) -> list[str]:
    """Return the subset of `parameters` that are currently locked by a
    non-Sherpa change within the last COOLDOWN_HOURS. Empty list = all
    free.

    Exceptions are caught and logged: if Supabase is briefly unavailable
    we err on the side of treating everything as free, because Sherpa is
    in DRY_RUN by default and the cost of a missed cooldown in LIVE is a
    Telegram-loud parameter overwrite (loud, but recoverable).
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_HOURS)).isoformat()
        # Pull recent non-Sherpa changes for this symbol; filter in Python.
        # config_changes_log.symbol can be NULL for global TF settings, but
        # that's not a Grid parameter so we always filter by symbol here.
        rows = (
            supabase.table("config_changes_log")
            .select("parameter, changed_by, created_at")
            .eq("symbol", symbol)
            .gte("created_at", cutoff)
            .neq("changed_by", "sherpa")
            .execute()
        )
    except Exception as e:
        logger.warning(f"Cooldown query failed for {symbol}: {e}")
        return []

    locked = {r["parameter"] for r in (rows.data or []) if r.get("parameter") in set(parameters)}
    return sorted(locked)


def latest_manual_change(
    supabase,
    symbol: str,
    parameter: str,
) -> dict | None:
    """Return the most recent non-Sherpa change row for (symbol, parameter)
    inside the cooldown window, or None. Used for the SHERPA_COOLDOWN
    event payload so the CEO can see when the override was set.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_HOURS)).isoformat()
        rows = (
            supabase.table("config_changes_log")
            .select("changed_by, created_at, old_value, new_value")
            .eq("symbol", symbol)
            .eq("parameter", parameter)
            .gte("created_at", cutoff)
            .neq("changed_by", "sherpa")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning(f"latest_manual_change failed for {symbol}/{parameter}: {e}")
        return None
    return (rows.data or [None])[0]
