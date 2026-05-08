"""
S67 — Pre-reset Supabase backup (brief 66a Step 4 prerequisite).

Dumps every public-schema table to JSONL on the local filesystem ahead
of the TRUNCATE that brings the dataset to a $100 fresh testnet baseline.
Output layout is restoreable via a companion restore script (not included
yet — write only when needed).

Usage (on Mac Mini, where the bot's venv + .env live):
    cd /Volumes/Archivio/bagholderai
    source venv/bin/activate
    python3.13 scripts/backup_db_s67.py audits/2026-05-08_pre-reset-s67/

Output:
    <out_dir>/<table_name>.jsonl     one JSON row per line
    <out_dir>/_manifest.json         row counts + sizes + timestamps

Table list mirrors mcp.list_tables on project pxdhtmqfwjwjhtcoacsn,
schema=public, snapshot 2026-05-08. If new tables appear later, add
them here — the script will not auto-discover.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.client import get_client

TABLES = [
    "trades",
    "portfolio",
    "sentinel_logs",
    "agent_rules",
    "feedback",
    "daily_pnl",
    "daily_commentary",
    "config_changes_log",
    "diary_entries",
    "bot_config",
    "reserve_ledger",
    "trend_config",
    "coin_tiers",
    "trend_decisions_log",
    "exchange_filters",
    "trend_scans",
    "pending_x_posts",
    "bot_events_log",
    "bot_state_snapshots",
    "counterfactual_log",
    "sentinel_scores",
    "sherpa_proposals",
]

PAGE_SIZE = 1000


def dump_table(client, table_name: str, out_path: Path) -> int:
    """Stream a table to JSONL, paginated. Returns row count written."""
    rows_written = 0
    page = 0
    with out_path.open("w") as f:
        while True:
            start = page * PAGE_SIZE
            end = start + PAGE_SIZE - 1
            try:
                resp = client.table(table_name).select("*").range(start, end).execute()
            except Exception as e:
                print(f"  ! {table_name}: page {page} failed: {e}", file=sys.stderr)
                break
            rows = resp.data or []
            for r in rows:
                f.write(json.dumps(r, default=str))
                f.write("\n")
            rows_written += len(rows)
            if len(rows) < PAGE_SIZE:
                break
            page += 1
            if page % 5 == 0:
                print(f"  ...{table_name}: {rows_written} rows so far")
    return rows_written


def main(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    client = get_client()

    started_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "started_at": started_at,
        "project_id": "pxdhtmqfwjwjhtcoacsn",
        "schema": "public",
        "page_size": PAGE_SIZE,
        "tables": {},
    }

    for table in TABLES:
        out_path = out_dir / f"{table}.jsonl"
        print(f"\n→ {table}")
        try:
            count = dump_table(client, table, out_path)
            manifest["tables"][table] = {
                "rows": count,
                "file": out_path.name,
                "size_bytes": out_path.stat().st_size,
            }
            print(f"  {table}: {count} rows  ({out_path.stat().st_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"  ! {table} FAILED: {e}", file=sys.stderr)
            manifest["tables"][table] = {"error": str(e)}

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path = out_dir / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    total_rows = sum(t.get("rows", 0) for t in manifest["tables"].values() if isinstance(t.get("rows"), int))
    total_size = sum(t.get("size_bytes", 0) for t in manifest["tables"].values() if isinstance(t.get("size_bytes"), int))
    failed = [t for t, info in manifest["tables"].items() if "error" in info]

    print("\n" + "=" * 60)
    print(f"Backup complete: {len(TABLES)} tables, {total_rows} rows, {total_size / 1e6:.2f} MB")
    print(f"Output: {out_dir}")
    print(f"Manifest: {manifest_path}")
    if failed:
        print(f"\n⚠️  FAILED TABLES ({len(failed)}): {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("audits/pre-reset-s67")
    sys.exit(main(out_dir))
