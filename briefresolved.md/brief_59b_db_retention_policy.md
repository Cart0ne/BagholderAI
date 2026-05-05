# Brief 59b — DB Retention Policy

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Date:** May 5, 2026
**Priority:** MEDIUM — preventive, not urgent
**Scope:** New `bot/db_maintenance.py` module + orchestrator integration
**Dependencies:** None. Independent from 59a.

---

## Context

Supabase free tier has a daily Disk IO Budget. When depleted, the DB slows to a crawl. Current state:

| Table | Rows | Size | Growth/day |
|---|---|---|---|
| trend_scans | 28,454 | 7.6 MB | ~2,300 |
| bot_state_snapshots | 9,171 | 2.8 MB | ~740 |
| bot_events_log | 2,531 | 1.2 MB | ~250 |
| trend_decisions_log | 1,433 | 576 KB | ~120 |
| trades | 1,090 | 496 KB | ~26 |
| counterfactual_log | 828 | 208 KB | ~79 |

trend_scans alone has 3 indexes totaling 3 MB — every insert updates all three. bot_state_snapshots has 3 indexes too. These two tables generate the most IO for the least value.

We are NOT eliminating any table. We are setting a retention window: old rows get deleted daily, recent rows stay.

---

## Retention Policy

| Table | Retention | Reason |
|---|---|---|
| `trades` (v3) | **forever** | FIFO + P&L — sacred |
| `trades` (v1, v2) | **delete all** | Legacy, not used by anything |
| `trend_scans` | **14 days** | Scan detail only useful for recent analysis |
| `trend_decisions_log` | **14 days** | TF decisions, useful for recent debugging |
| `bot_state_snapshots` | **7 days** | Redundant with local logs, only useful for very recent state reconstruction |
| `bot_events_log` | **7 days** | Debug events, only recent ones matter |
| `counterfactual_log` | **14 days** | Needed to evaluate filter 45e v2, but old data loses relevance |
| `config_changes_log` | **forever** | Tiny, grows slow, audit trail |
| `daily_pnl` | **forever** | 1 row/day, negligible |
| `daily_commentary` | **forever** | 1 row/day, negligible |
| `diary_entries` | **forever** | Tiny |
| `reserve_ledger` | **forever** | Accounting |
| `bot_config` | **forever** | Config |
| `trend_config` | **forever** | Config |
| `exchange_filters` | **forever** | Tiny, upsert only |

---

## Implementation

### New file: `bot/db_maintenance.py`

```python
"""
Daily DB maintenance — delete rows outside retention windows.
Run once per day (e.g. 04:00 UTC) from orchestrator.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("bagholderai.maintenance")

# Retention policy: table -> (days to keep, optional extra WHERE clause)
RETENTION_POLICY = {
    "trend_scans": {"days": 14, "date_column": "created_at"},
    "trend_decisions_log": {"days": 14, "date_column": "created_at"},
    "bot_state_snapshots": {"days": 7, "date_column": "created_at"},
    "bot_events_log": {"days": 7, "date_column": "created_at"},
    "counterfactual_log": {"days": 14, "date_column": "created_at"},
}


def run_retention_cleanup(supabase_client) -> dict:
    """
    Delete rows older than retention window for each table.
    Returns summary of rows deleted per table.
    """
    summary = {}

    for table, config in RETENTION_POLICY.items():
        days = config["days"]
        date_col = config["date_column"]
        cutoff = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        # Subtract days manually to avoid timedelta import issues
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

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
    """
    One-time: delete all trades with config_version v1 or v2.
    Safe to run multiple times (idempotent).
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
```

### Orchestrator integration

In `orchestrator.py` (or the main loop), schedule the cleanup to run once per day. Simple approach:

```python
from bot.db_maintenance import run_retention_cleanup, delete_legacy_trades

MAINTENANCE_HOUR_UTC = 4  # 04:00 UTC = 06:00 IT summer time
_last_maintenance_date = None

def maybe_run_maintenance(supabase_client, notifier):
    global _last_maintenance_date
    now = datetime.now(timezone.utc)

    if now.hour != MAINTENANCE_HOUR_UTC:
        return
    if _last_maintenance_date == now.date():
        return

    _last_maintenance_date = now.date()
    logger.info("[maintenance] Starting daily cleanup...")

    # One-time legacy cleanup (harmless if already done)
    legacy = delete_legacy_trades(supabase_client)

    # Daily retention cleanup
    summary = run_retention_cleanup(supabase_client)

    # Telegram report
    total_deleted = sum(v.get("deleted", 0) for v in summary.values()) + legacy
    if total_deleted > 0:
        lines = [f"🧹 <b>DB Maintenance</b>"]
        if legacy > 0:
            lines.append(f"Legacy trades (v1/v2): {legacy} deleted")
        for table, info in summary.items():
            d = info.get("deleted", 0)
            if d > 0:
                lines.append(f"{table}: {d} rows purged")
        notifier.send_message("\n".join(lines))
    else:
        logger.info("[maintenance] Nothing to clean today.")
```

Call `maybe_run_maintenance(supabase_client, notifier)` in the main loop, alongside the existing health check schedule.

---

## What NOT to Do

- **Do NOT drop any table.** We're deleting old rows, not removing tables.
- **Do NOT touch `trades` where `config_version = 'v3'`.** Sacred.
- **Do NOT export data before deleting.** Board decision: we accept the data loss.
- **Do NOT change any indexes.** The retention cleanup reduces IO naturally by keeping tables smaller.
- **Do NOT run the cleanup more than once per day.** The DELETE operations themselves consume IO.

---

## Testing

1. **Dry run first**: Before the real DELETE, run COUNT queries to verify what would be deleted:
   ```sql
   SELECT COUNT(*) FROM trend_scans WHERE created_at < NOW() - INTERVAL '14 days';
   SELECT COUNT(*) FROM bot_state_snapshots WHERE created_at < NOW() - INTERVAL '7 days';
   -- etc.
   ```
   Report the counts to CEO before executing.

2. **First real run**: Execute `run_retention_cleanup()` manually once, verify Telegram summary, verify tables still work normally.

3. **Verify bot still boots**: After cleanup, restart one bot and confirm `init_percentage_state_from_db()` still works (it only reads `trades`, which we don't touch for v3).

---

## Commit message

```
feat(maintenance): daily DB retention cleanup (59b)

New module bot/db_maintenance.py with configurable retention policy:
- trend_scans: 14 days
- trend_decisions_log: 14 days
- bot_state_snapshots: 7 days
- bot_events_log: 7 days
- counterfactual_log: 14 days
- trades v1/v2: delete all (one-time)

Runs daily at 04:00 UTC from orchestrator. Telegram summary
on cleanup. Trades v3 and all config/accounting tables untouched.

Refs brief_59b.
```

---

## Files to create/modify

| File | Action |
|---|---|
| `bot/db_maintenance.py` | **NEW** — retention cleanup + legacy trade deletion |
| `bot/orchestrator.py` | Add `maybe_run_maintenance()` call in main loop |

## Files NOT to modify

- Everything else. This is a standalone module.

---

**Stato:** brief ready. Can be implemented in parallel with 59a.

— CEO, BagHolderAI
