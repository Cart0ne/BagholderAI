"""
Supabase VM metrics recorder — one line every 30 min (cron, Mac Mini).

Why: the Supabase outages of 17/18-Sep-2026 were diagnosed as memory
exhaustion (swap ~420 MB on a 431 MB Nano VM). The dashboard only keeps
24 h and goes blind during a block; this keeps our own history so we can
see how fast swap refills after a project restart and what the VM looked
like in the hours before the next block.

Reads the project's Prometheus endpoint (read-only, no SQL, no alerts):
    GET {SUPABASE_URL}/customer/v1/privileged/metrics
    basic auth service_role:{SUPABASE_KEY}
and appends one JSON line to the output file. Counters are cumulative
since VM boot: rates = diff between consecutive lines. A failed read is
written too (ok=false) — during a block that failure IS the data point.

Usage:
    python3.13 scripts/supabase_metrics_recorder.py [out_file]
    (default out_file: $HOME/supabase_metrics.jsonl — cron can't write
    to /Volumes/Archivio, see scripts/cron_reconcile.sh)
"""

import base64
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DatabaseConfig

GAUGES = {
    "node_memory_MemTotal_bytes": "mem_total",
    "node_memory_MemAvailable_bytes": "mem_available",
    "node_memory_SwapTotal_bytes": "swap_total",
    "node_memory_SwapFree_bytes": "swap_free",
    "node_memory_Committed_AS_bytes": "committed_as",
    "node_memory_CommitLimit_bytes": "commit_limit",
    "node_vmstat_pswpin": "pswpin",
    "node_vmstat_pswpout": "pswpout",
    "node_vmstat_pgmajfault": "pgmajfault",
}
DISK = {
    "node_disk_reads_completed_total": "reads",
    "node_disk_writes_completed_total": "writes",
    "node_disk_read_bytes_total": "read_bytes",
    "node_disk_written_bytes_total": "written_bytes",
}
LINE = re.compile(r"^([a-zA-Z_:]+)(\{[^}]*\})?\s+(\S+)")


def parse(text: str) -> dict:
    out = {"disk": {}, "cpu_s": {}}
    for raw in text.splitlines():
        m = LINE.match(raw)
        if not m:
            continue
        name, labels, val = m.group(1), m.group(2) or "", float(m.group(3))
        if name in GAUGES:
            out[GAUGES[name]] = val
        elif name in DISK:
            dev = re.search(r'device="([^"]+)"', labels)
            if dev:
                out["disk"].setdefault(dev.group(1), {})[DISK[name]] = val
        elif name == "node_cpu_seconds_total":
            mode = re.search(r'mode="([^"]+)"', labels)
            if mode:
                out["cpu_s"][mode.group(1)] = out["cpu_s"].get(mode.group(1), 0.0) + val
    return out


def main() -> int:
    out_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "supabase_metrics.jsonl"
    row = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    url = DatabaseConfig.SUPABASE_URL.rstrip("/") + "/customer/v1/privileged/metrics"
    auth = base64.b64encode(f"service_role:{DatabaseConfig.SUPABASE_KEY}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        row.update(ok=True, ms=round((time.monotonic() - t0) * 1000), **parse(body))
    except Exception as exc:  # the failure itself is the signal during a block
        row.update(ok=False, ms=round((time.monotonic() - t0) * 1000), error=f"{type(exc).__name__}: {exc}"[:300])
    with out_file.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
