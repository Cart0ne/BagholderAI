"""
BagHolderAI - 59b Daily DB retention maintenance

Supabase free-tier disk IO budget is the bottleneck, not storage.
trend_scans + bot_state_snapshots have 3 indexes each — every insert
updates all three. Keeping these tables small keeps insert latency
flat and our daily IO budget intact.

This module deletes rows older than the per-table retention window
once a day (04:00 UTC). It also drops legacy v1/v2 trades on first
run (idempotent — safe to re-execute).

Tables NOT touched here (full table sacred or tiny):
  trades(v3), config_changes_log, daily_pnl, daily_commentary,
  diary_entries, reserve_ledger, bot_config, trend_config,
  exchange_filters.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("bagholderai.maintenance")


# Retention policy: table → window in days, with the timestamp column to filter on.
# Tightening the windows is safe (deletes more); loosening means re-introducing IO.
RETENTION_POLICY: dict[str, dict] = {
    "trend_scans":         {"days": 14, "date_column": "created_at"},
    "trend_decisions_log": {"days": 14, "date_column": "created_at"},
    "bot_state_snapshots": {"days":  7, "date_column": "created_at"},
    "bot_events_log":      {"days":  7, "date_column": "created_at"},
    "counterfactual_log":  {"days": 14, "date_column": "created_at"},
    # Sentinel/Sherpa: 30 days for raw scores (used to verify Sherpa
    # decisions against actual market state), 60 days for proposals
    # (so the 7-day weekly counterfactual report always has a full
    # comparison window even when run a few weeks late).
    "sentinel_scores":     {"days": 30, "date_column": "created_at"},
    "sherpa_proposals":    {"days": 60, "date_column": "created_at"},
}


def _utc_midnight_minus(days: int) -> str:
    """Cutoff = today 00:00 UTC minus N days, ISO format."""
    cutoff = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(days=days)
    )
    return cutoff.isoformat()


def run_retention_cleanup(supabase_client) -> dict:
    """Delete rows past the retention window for each table in RETENTION_POLICY.

    Per-table failures are logged and recorded in the summary but never raise:
    one bad table cannot stop the others (or the orchestrator).

    Returns:
        {table: {"deleted": int, "cutoff": iso8601} | {"deleted": 0, "error": str}}
    """
    summary: dict[str, dict] = {}

    for table, cfg in RETENTION_POLICY.items():
        days = cfg["days"]
        date_col = cfg["date_column"]
        cutoff_iso = _utc_midnight_minus(days)

        try:
            result = (
                supabase_client.table(table)
                .delete()
                .lt(date_col, cutoff_iso)
                .execute()
            )
            deleted = len(result.data) if result.data else 0
            summary[table] = {"deleted": deleted, "cutoff": cutoff_iso}
            if deleted > 0:
                logger.info(
                    f"[maintenance] {table}: deleted {deleted} rows "
                    f"older than {days} days (cutoff: {cutoff_iso})"
                )
        except Exception as e:
            logger.error(f"[maintenance] {table}: cleanup failed: {e}")
            summary[table] = {"deleted": 0, "error": str(e)}

    return summary


def delete_legacy_trades(supabase_client) -> int:
    """One-time cleanup of v1/v2 trades. Idempotent: re-running deletes 0.

    These were march/april experimentation runs (62 rows total as of 2026-05-05).
    No code path reads them — every consumer filters config_version='v3'.
    """
    total = 0
    for version in ("v1", "v2"):
        try:
            result = (
                supabase_client.table("trades")
                .delete()
                .eq("config_version", version)
                .execute()
            )
            deleted = len(result.data) if result.data else 0
            total += deleted
            if deleted > 0:
                logger.info(
                    f"[maintenance] trades: deleted {deleted} rows "
                    f"with config_version={version}"
                )
        except Exception as e:
            logger.error(f"[maintenance] trades {version} cleanup failed: {e}")

    return total


# ---------------------------------------------------------------------- #
# Orchestrator-side scheduling helper
# ---------------------------------------------------------------------- #

MAINTENANCE_HOUR_UTC = 4  # 04:00 UTC = 06:00 IT estate / 05:00 IT inverno

# Module-level so the orchestrator process retains it across loop iterations.
_last_maintenance_date: "datetime.date | None" = None


def maybe_run_maintenance(supabase_client, notifier=None) -> dict | None:
    """Run the daily cleanup once per UTC day, at MAINTENANCE_HOUR_UTC.

    Designed to be called every poll iteration from the orchestrator main
    loop — it returns immediately on the wrong hour or if today's run is
    already done. Sends a Telegram summary only if something was deleted.

    Returns the per-table summary on a real run, None on a no-op.
    """
    global _last_maintenance_date
    now = datetime.now(timezone.utc)

    if now.hour != MAINTENANCE_HOUR_UTC:
        return None
    if _last_maintenance_date == now.date():
        return None

    _last_maintenance_date = now.date()
    logger.info("[maintenance] Starting daily cleanup...")

    legacy_deleted = delete_legacy_trades(supabase_client)
    summary = run_retention_cleanup(supabase_client)

    total = sum(v.get("deleted", 0) for v in summary.values()) + legacy_deleted

    if notifier is not None and total > 0:
        try:
            lines = ["🧹 <b>DB Maintenance</b>"]
            if legacy_deleted > 0:
                lines.append(f"Legacy trades (v1/v2): {legacy_deleted} deleted")
            for table, info in summary.items():
                d = info.get("deleted", 0)
                if d > 0:
                    lines.append(f"{table}: {d} rows purged")
            notifier.send_message("\n".join(lines))
        except Exception as e:
            logger.warning(f"[maintenance] Telegram summary send failed: {e}")
    elif total == 0:
        logger.info("[maintenance] Nothing to clean today.")

    return {"legacy_deleted": legacy_deleted, "tables": summary, "total": total}


# ---------------------------------------------------------------------- #
# CLI entry — run it manually when needed.
# ---------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    from db.client import get_client
    client = get_client()

    print("--- Manual maintenance run ---")
    legacy = delete_legacy_trades(client)
    summary = run_retention_cleanup(client)

    print(f"\nLegacy trades deleted: {legacy}")
    print("\nRetention cleanup:")
    for table, info in summary.items():
        if "error" in info:
            print(f"  {table}: ERROR — {info['error']}")
        else:
            print(f"  {table}: {info['deleted']} rows (cutoff {info['cutoff']})")

    total = sum(v.get("deleted", 0) for v in summary.values()) + legacy
    print(f"\nTotal rows deleted: {total}")
    sys.exit(0 if all("error" not in v for v in summary.values()) else 1)
