/* Live data fetch for the home page.
   Reads Supabase REST directly with the anon key (matches the legacy
   web/index.html approach — anon key is public by design, RLS handles
   read-only access). All updates are best-effort: if a query fails,
   the markup keeps its server-rendered fallback value. */

import { sbFetchAll } from "./sb-paginated";

const SB_URL =
  "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const headers = {
  apikey: SB_KEY,
  Authorization: `Bearer ${SB_KEY}`,
};

const sbq = async <T>(table: string, params: string): Promise<T> => {
  const r = await fetch(`${SB_URL}/rest/v1/${table}?${params}`, { headers });
  if (!r.ok) throw new Error(`${table}: ${r.status}`);
  return r.json() as Promise<T>;
};

const sbqCount = async (table: string, params: string): Promise<number> => {
  const r = await fetch(`${SB_URL}/rest/v1/${table}?${params}`, {
    headers: {
      ...headers,
      Prefer: "count=exact",
      "Range-Unit": "items",
      Range: "0-0",
    },
  });
  if (!r.ok) throw new Error(`${table}: ${r.status}`);
  const cr = r.headers.get("Content-Range") || "";
  const n = parseInt(cr.split("/")[1] || "0", 10);
  return Number.isNaN(n) ? 0 : n;
};

/* Prefer the global animated updater (set up in Layout.astro) so that
   counters tween smoothly to the new value. Falls back to plain text
   write if the API isn't available (e.g. on pages without Layout). */
const setText = (id: string, value: string) => {
  const updater = (window as unknown as {
    __updateLiveStat?: (id: string, val: string) => void;
  }).__updateLiveStat;
  if (updater) {
    updater(id, value);
    return;
  }
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

/* ---------- 1. orders executed ---------- */
sbqCount("trades", "select=id&config_version=eq.v3")
  .then(n => setText("stat-trades", String(n)))
  .catch(() => setText("stat-trades", "N.A."));

/* ---------- 2. Total P&L (Opzione 3 — decision_s65, S69 avg-cost) ----------
   Total P&L = (Net Worth Grid + Net Worth TF) − $600 budget.
   Avg-cost canonico (post-S66 Operation Clean Slate) — chiude l'identità
   contabile Realized + Unrealized = Total e coincide con la formula
   Binance per realized_pnl.

   Today P&L stays as DB SUM(realized_pnl) on today's sells: it's a
   daily flow metric, not a patrimony metric. The two answer different
   questions ("how much have I banked today" vs "how much would I have
   if I closed everything now"). */

type TradeFull = {
  symbol: string;
  side: "buy" | "sell";
  amount: string | number;
  cost: string | number;
  realized_pnl: string | number | null;
  created_at: string;
};

type SkimRow = { symbol: string; amount: string | number };

/* Today = UTC midnight of the current calendar day. */
const todayStartUtcIso = new Date(
  Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    new Date().getUTCDate(),
  ),
).toISOString();

const GRID_SYMBOLS = new Set(["BTC/USDT", "SOL/USDT", "BONK/USDT"]);
const GRID_BUDGET = 500;
const TF_BUDGET   = 100;

/* Fetch live prices from Binance (same endpoint dashboard-live.ts uses). */
const fetchLivePrices = async (symbols: string[]): Promise<Record<string, number>> => {
  if (!symbols.length) return {};
  try {
    const r = await fetch(
      "https://api.binance.com/api/v3/ticker/price?symbols=" +
      encodeURIComponent(JSON.stringify(symbols.map(s => s.replace("/", "")))),
    );
    if (!r.ok) return {};
    const arr = await r.json() as Array<{ symbol: string; price: string }>;
    const out: Record<string, number> = {};
    for (const row of arr) {
      /* Map back BTCUSDT → BTC/USDT. */
      const slash = row.symbol.replace(/USDT$/, "/USDT");
      out[slash] = Number(row.price);
    }
    return out;
  } catch {
    return {};
  }
};

Promise.all([
  sbFetchAll<TradeFull>(
    "trades?select=symbol,side,amount,cost,realized_pnl,created_at" +
    "&config_version=eq.v3&order=created_at.asc",
  ),
  sbFetchAll<SkimRow>(
    "reserve_ledger?select=symbol,amount&config_version=eq.v3",
  ),
]).then(async ([trades, skimRows]) => {
  trades = trades ?? [];
  skimRows = skimRows ?? [];

  /* Today P&L + today trades: from DB realized_pnl on today's sells. */
  let todayPnl = 0;
  let todayTrades = 0;
  for (const t of trades) {
    if (t.created_at < todayStartUtcIso) continue;
    todayTrades++;
    if (t.side !== "sell") continue;
    const p = Number(t.realized_pnl);
    if (Number.isFinite(p)) todayPnl += p;
  }

  /* Aggregate per-symbol: net invested (buy.cost − sell.cost) and
     remaining holdings (buy.amount − sell.amount). Per-symbol mapping
     to Grid/TF is by symbol set since each symbol is owned by one bot. */
  type Agg = { netInvested: number; holdings: number };
  const bySym: Record<string, Agg> = {};
  for (const t of trades) {
    const a = (bySym[t.symbol] ||= { netInvested: 0, holdings: 0 });
    const amt = Number(t.amount || 0);
    const cost = Number(t.cost || 0);
    if (t.side === "buy") {
      a.netInvested += cost;
      a.holdings    += amt;
    } else {
      a.netInvested -= cost;
      a.holdings    -= amt;
    }
  }

  /* Skim per bucket via symbol partition. */
  let skimGrid = 0, skimTf = 0;
  for (const r of skimRows) {
    const amt = Number(r.amount || 0);
    if (GRID_SYMBOLS.has(r.symbol)) skimGrid += amt;
    else                            skimTf   += amt;
  }

  /* Live prices for all symbols still holding. */
  const heldSymbols = Object.keys(bySym).filter(s => bySym[s].holdings > 1e-8);
  const prices = await fetchLivePrices(heldSymbols);

  let netInvestedGrid = 0, holdingsGrid = 0;
  let netInvestedTf   = 0, holdingsTf   = 0;
  for (const sym of Object.keys(bySym)) {
    const a = bySym[sym];
    const px = prices[sym] ?? 0;
    const mtm = a.holdings > 0 && px > 0 ? a.holdings * px : 0;
    if (GRID_SYMBOLS.has(sym)) {
      netInvestedGrid += a.netInvested;
      holdingsGrid    += mtm;
    } else {
      netInvestedTf += a.netInvested;
      holdingsTf    += mtm;
    }
  }

  /* Net Worth = budget − netInvested + holdings_market.
     The skim term cancels: cash = budget − netInvested − skim, then
     net worth = cash + holdings + skim = budget − netInvested + holdings. */
  const netWorthGrid = GRID_BUDGET - netInvestedGrid + holdingsGrid;
  const netWorthTf   = TF_BUDGET   - netInvestedTf   + holdingsTf;
  const totalPnl = (netWorthGrid - GRID_BUDGET) + (netWorthTf - TF_BUDGET);

  const sign = totalPnl >= 0 ? "+" : "-";
  setText("stat-pnl", `${sign}$${Math.abs(totalPnl).toFixed(2)}`);
  /* Dynamic color on Total P&L too (it can flip negative if both bots are down). */
  const pnlEl = document.getElementById("stat-pnl");
  if (pnlEl) {
    pnlEl.classList.remove("text-pos", "text-neg");
    pnlEl.classList.add(totalPnl >= 0 ? "text-pos" : "text-neg");
  }

  const tsign = todayPnl >= 0 ? "+" : "-";
  setText("stat-today-pnl", `${tsign}$${Math.abs(todayPnl).toFixed(2)}`);
  setText("stat-today-trades", String(todayTrades));
  const todayEl = document.getElementById("stat-today-pnl");
  if (todayEl) {
    todayEl.classList.remove("text-pos", "text-neg");
    todayEl.classList.add(todayPnl >= 0 ? "text-pos" : "text-neg");
  }
}).catch(() => {
  setText("stat-pnl", "N.A.");
  setText("stat-today-pnl", "N.A.");
  setText("stat-today-trades", "N.A.");
});

/* ---------- 3. days running (since first v3 trade) ---------- */
sbq<{ created_at: string }[]>(
  "trades",
  "select=created_at&config_version=eq.v3&order=created_at.asc&limit=1",
).then(rows => {
  if (!rows || !rows.length) return setText("stat-days", "0");
  const first = new Date(rows[0].created_at);
  const days  = Math.max(
    1,
    Math.floor((Date.now() - first.getTime()) / 86_400_000) + 1,
  );
  setText("stat-days", String(days));
}).catch(() => setText("stat-days", "N.A."));

/* ---------- 4. bot wins/losses ----------
   Live wins/losses from trades, grouped by managed_by.
   Grid trades use managed_by='manual' in v3 (legacy naming), TF uses
   'trend_follower'. A win = sell with realized_pnl > 0. */
type SellRow = { side: "buy" | "sell"; realized_pnl: number | null };

const fetchBotStats = async (managedBy: string) => {
  const rows = await sbFetchAll<SellRow>(
    `trades?select=side,realized_pnl&config_version=eq.v3` +
    `&managed_by=eq.${managedBy}&side=eq.sell`,
  );
  let wins = 0, losses = 0;
  for (const r of rows ?? []) {
    const p = Number(r.realized_pnl);
    if (Number.isFinite(p) && p !== 0) {
      if (p > 0) wins++; else losses++;
    }
  }
  return { wins, losses };
};

const updateBotCard = (variant: "grid" | "tf", wins: number, losses: number) => {
  setText(`bot-${variant}-wins`,   String(wins));
  setText(`bot-${variant}-losses`, String(losses));
  /* Also recompute the bar fills. We use the live max across both bots
     so the bars stay comparable. */
  const max = Math.max(50, wins, losses) * 1.2;
  const fillWins   = document.getElementById(`bot-${variant}-wins-bar`);
  const fillLosses = document.getElementById(`bot-${variant}-losses-bar`);
  if (fillWins)   fillWins.style.width   = `${Math.min(100, (wins   / max) * 100)}%`;
  if (fillLosses) fillLosses.style.width = `${Math.min(100, (losses / max) * 100)}%`;
};

Promise.all([fetchBotStats("manual"), fetchBotStats("trend_follower")])
  .then(([grid, tf]) => {
    updateBotCard("grid", grid.wins, grid.losses);
    updateBotCard("tf",   tf.wins,   tf.losses);
  })
  .catch(() => {});

/* ---------- 5. current session + recent diary entries ----------
   One query covers two needs: the hero "stat-session" badge (max
   session) and the new "Development diary" homepage section (last 3
   entries). Both BUILDING and COMPLETE rows are included. */
type DiaryRow = {
  session: number;
  title: string;
  date: string;
  status: string;
};

sbq<DiaryRow[]>(
  "diary_entries",
  "select=session,title,date,status&order=session.desc&limit=3",
).then(rows => {
  if (!rows || !rows.length) return;
  const sessionEl = document.getElementById("stat-session");
  if (sessionEl) sessionEl.textContent = String(rows[0].session);

  const list = document.getElementById("home-diary-list");
  if (!list) return;
  rows.forEach((row, i) => {
    const slot = list.querySelector(`[data-slot="${i}"]`) as HTMLElement | null;
    if (!slot) return;
    const sEl = slot.querySelector('[data-field="session"]');
    const tEl = slot.querySelector('[data-field="title"]');
    const dEl = slot.querySelector('[data-field="date"]');
    if (sEl) sEl.textContent = `Session ${row.session}`;
    if (tEl) tEl.textContent = row.title;
    if (dEl) dEl.textContent = row.date;
  });
  /* If fewer than 3 entries exist (unlikely), hide remaining slots
     so we don't show empty placeholders. */
  for (let i = rows.length; i < 3; i++) {
    const slot = list.querySelector(`[data-slot="${i}"]`) as HTMLElement | null;
    if (slot) slot.style.display = "none";
  }
}).catch(() => {});
