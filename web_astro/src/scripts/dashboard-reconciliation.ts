/* Public reconciliation table — brief 70c §5.
   Reads `reconciliation_runs` (latest run per symbol) populated by
   scripts/reconcile_binance.py. RLS: anon SELECT enabled by migration
   s70b_reconciliation_runs_select_policy. Best-effort: failure leaves
   the server-rendered skeleton "—" in place. */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const HEADERS = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };

type ReconRun = {
  symbol: string;
  status: string;
  binance_count: number | null;
  db_count: number | null;
  drift_count: number | null;
  ts: string;
};

const SYMBOLS: Array<{ key: "btc" | "sol" | "bonk"; symbol: string; label: string }> = [
  { key: "btc",  symbol: "BTC/USDT",  label: "BTC"  },
  { key: "sol",  symbol: "SOL/USDT",  label: "SOL"  },
  { key: "bonk", symbol: "BONK/USDT", label: "BONK" },
];

async function fetchLatestRun(symbol: string): Promise<ReconRun | null> {
  const url = `${SB_URL}/rest/v1/reconciliation_runs`
    + `?symbol=eq.${encodeURIComponent(symbol)}`
    + `&order=ts.desc&limit=1`
    + `&select=symbol,status,binance_count,db_count,drift_count,ts`;
  try {
    const r = await fetch(url, { headers: HEADERS });
    if (!r.ok) return null;
    const rows = (await r.json()) as ReconRun[];
    return rows[0] ?? null;
  } catch {
    return null;
  }
}

function statusBadge(status: string | undefined): { text: string; cls: string } {
  switch (status) {
    case "OK":
      return { text: "✓ OK", cls: "text-pos" };
    case "DRIFT":
    case "DRIFT_BINANCE_ORPHAN":
      return { text: "⚠ DRIFT", cls: "text-neg" };
    case "WARN_BINANCE_EMPTY":
      return { text: "⚠ Binance empty", cls: "text-neu" };
    default:
      return { text: status ?? "—", cls: "text-text-muted" };
  }
}

function fmtUtc(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "—";
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  const day = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" });
  return `${day} · ${hh}:${mm} UTC`;
}

function setCell(id: string, text: string, cls?: string) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  if (cls) el.className = cls;
}

async function hydrate() {
  let totalDrift = 0;
  let anyMissing = false;
  for (const { key, symbol } of SYMBOLS) {
    const run = await fetchLatestRun(symbol);
    if (!run) {
      anyMissing = true;
      setCell(`recon-${key}-status`, "— no data —", "font-mono text-[12px] text-text-muted");
      continue;
    }
    const badge = statusBadge(run.status);
    setCell(`recon-${key}-status`, badge.text, `font-mono text-[12px] font-semibold ${badge.cls}`);
    const verified = `${run.db_count ?? 0} / ${run.binance_count ?? 0}`;
    setCell(`recon-${key}-verified`, verified, "font-mono text-[12px] text-text tabular-nums");
    const drift = run.drift_count ?? 0;
    totalDrift += drift;
    setCell(
      `recon-${key}-drift`,
      String(drift),
      `font-mono text-[12px] tabular-nums ${drift > 0 ? "text-neg" : "text-text"}`,
    );
    setCell(`recon-${key}-ts`, fmtUtc(run.ts), "font-mono text-[11px] text-text-muted");
  }
  const tail = document.getElementById("recon-claim-tail");
  if (tail) {
    if (anyMissing) {
      tail.textContent = "Latest run pending.";
      tail.className = "text-text-muted font-semibold";
    } else if (totalDrift > 0) {
      const label = totalDrift === 1 ? "discrepancy" : "discrepancies";
      tail.textContent = `${totalDrift} ${label} under review.`;
      tail.className = "text-neg font-semibold";
    } else {
      tail.textContent = "Zero discrepancies.";
      tail.className = "text-pos font-semibold";
    }
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", hydrate);
  } else {
    hydrate();
  }
}
