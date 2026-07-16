/* Live data fetch for the home page.
   Reads Supabase REST directly with the anon key (matches the legacy
   web/index.html approach — anon key is public by design, RLS handles
   read-only access). All updates are best-effort: if a query fails,
   the markup keeps its server-rendered fallback value. */

import { sbFetchAll } from "./sb-paginated";
import {
  computeCanonicalState,
  fetchLivePrices,
  type CanonicalTrade,
} from "../lib/pnl-canonical";

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

/* Current cycle — DATA-DRIVEN since S117 (2026-07-11): read from
   bot_config.cycle so a testnet reset — or the Kraken live switch — needs
   ONE `UPDATE bot_config SET cycle=...` and every site surface follows.
   S118: the row is "the most recently updated ACTIVE grid row" instead of
   the literal BTC/USDT — at the Kraken cutover the live row is BTC/USD and
   a symbol literal would silently freeze the site on the dead cycle
   (lexical-drift family, S70/S72).
   S119 (Fase 2a): pin to venue='binance'. During the Kraken test/collaudo
   (Board decision S119) binance is the canonical public venue — the S118
   "most-recently-updated active row" rule coincided with binance ONLY because
   every row shares one cycle today; activating a Kraken row (its UPDATE becomes
   the newest write) would make the whole site jump onto the near-empty Kraken
   cycle. The explicit venue filter makes the public view robust, not lucky.
   All rows are venue='binance' today (migration default NOT NULL) → no-op now.
   Top-level await: the page scripts are ES modules, and every query below
   depends on CQ anyway. */
const CYCLE_FALLBACK = "testnet_2";   // used only if the bot_config fetch fails
const CYCLE = await sbq<{ cycle: string }[]>(
  "bot_config",
  "select=cycle&managed_by=eq.grid&is_active=eq.true&venue=eq.binance&order=updated_at.desc&limit=1",
)
  .then((rows) => rows?.[0]?.cycle || CYCLE_FALLBACK)
  .catch(() => CYCLE_FALLBACK);
const CQ = `&cycle=eq.${CYCLE}`;

/* ---------- 0. disclaimer gate (S118, K.3 prep) ----------
   site_flags.disclaimer_mode=true → swap the homepage for the disclaimer
   overlay (COLLAUDO_COMMS_GUIDELINES Step 1/3). Zero-deploy: the flag row is
   flipped with a plain UPDATE (same pattern as project_status, Brief 86a).
   Fire-and-forget: any failure leaves the gate hidden (site behaves as
   pre-S118); the flip is a Fase 2 runbook step. */
sbq<{ disclaimer_mode: boolean; disclaimer_text: string }[]>(
  "site_flags",
  "select=disclaimer_mode,disclaimer_text&id=eq.1&limit=1",
)
  .then((rows) => {
    const flag = rows?.[0];
    if (!flag?.disclaimer_mode) return;
    const gate = document.getElementById("disclaimer-gate");
    if (!gate) return;
    const text = document.getElementById("disclaimer-gate-text");
    if (text && flag.disclaimer_text) text.textContent = flag.disclaimer_text;
    gate.classList.remove("hidden");
    gate.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden"; // the overlay owns the scroll
  })
  .catch(() => { /* gate stays off — never break the homepage over a flag */ });

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
sbqCount("trades", "select=id&config_version=eq.v3" + CQ)
  .then(n => setText("stat-trades", String(n)))
  .catch(() => setText("stat-trades", "N.A."));

/* ---------- 2. Total P&L (Brief 71a — canonical NET-of-fees) ----------
   Total P&L = (Net Worth Grid + Net Worth TF) − $600 budget, where
     netWorth = cash + holdings_mtm + skim − fees    (post-fees, brief 71a)
   Single source of truth: lib/pnl-canonical.ts, mirror of grid.html
   formula (the only one that already subtracted fees pre-71a).

   Today P&L stays as DB SUM(realized_pnl) on today's sells: it's a
   daily flow metric, not a patrimony metric. The two answer different
   questions ("how much have I banked today" vs "how much would I have
   if I closed everything now"). */

type TradeFull = CanonicalTrade & { fee?: string | number | null; managed_by?: string | null };

type SkimRow = { symbol: string; amount: string | number };

/* Today = UTC midnight of the current calendar day. */
const todayStartUtcIso = new Date(
  Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    new Date().getUTCDate(),
  ),
).toISOString();

const GRID_BUDGET = 500;
const TF_BUDGET   = 100;

Promise.all([
  sbFetchAll<TradeFull>(
    /* Brief 72a (S72): fee_asset added so the canonical replay can detect
       BUY rows where Binance scaled the fee from the base coin (live live
       testnet) and apply P2 (qty_acquired = filled − fee_native). */
    "trades?select=symbol,side,amount,cost,fee,fee_asset,realized_pnl,created_at,managed_by" +
    "&config_version=eq.v3" + CQ + "&order=created_at.asc",
  ),
  sbFetchAll<SkimRow>(
    "reserve_ledger?select=symbol,amount&config_version=eq.v3" + CQ,
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

  /* Partition trades + skim by managed_by — NOT by symbol — so coins handed
     off by TF to the grid (managed_by='tf_grid', e.g. ETH) land in the TF
     fund instead of being dropped. Mirrors LabRoom.jsx / dashboard-live.ts
     (the S107 board fix). Brief 71a: canonical state via lib/pnl-canonical.ts. */
  const gridTrades = trades.filter(t => t.managed_by === "grid");
  const tfTrades   = trades.filter(t => t.managed_by === "tf" || t.managed_by === "tf_grid");
  const gridSyms = new Set(gridTrades.map(t => t.symbol));
  const tfSyms   = new Set(tfTrades.map(t => t.symbol));
  let skimGrid = 0, skimTf = 0;
  for (const r of skimRows) {
    const amt = Number(r.amount || 0);
    if (gridSyms.has(r.symbol))    skimGrid += amt;
    else if (tfSyms.has(r.symbol)) skimTf   += amt;
  }

  /* Fetch live prices for every held symbol across both funds. */
  const allSymbols = Array.from(new Set(trades.map(t => t.symbol)));
  const prices = await fetchLivePrices(allSymbols);

  /* S108 (Max audit 2026-06-19): both funds contribute, $600 basis
     (Grid $500 + TF $100), matching the scene board. The old S72 Grid-only
     $500 rule dropped the live TF→grid handoff (ETH, managed_by='tf_grid'),
     showing a fake-positive Total P&L. computeCanonicalState is the SAME
     formula; we just stop discarding the TF fund. */
  const gridState = computeCanonicalState(gridTrades, skimGrid, prices, GRID_BUDGET);
  const tfState   = computeCanonicalState(tfTrades, skimTf, prices, TF_BUDGET);
  const totalPnl = gridState.totalPnL + tfState.totalPnL;

  const sign = totalPnl >= 0 ? "+" : "-";
  setText("stat-pnl", `${sign}$${Math.abs(totalPnl).toFixed(2)}`);
  /* Dynamic color on Total P&L too (it can flip negative if both bots are down). */
  const pnlEl = document.getElementById("stat-pnl");
  if (pnlEl) {
    pnlEl.classList.remove("text-pos", "text-neg");
    pnlEl.classList.add(totalPnl >= 0 ? "text-pos" : "text-neg");
  }

  /* Per-fund split under Total P&L — same canonical figures the admin
     snap-split shows (gridState.totalPnL / tfState.totalPnL). Each is the
     fund's own Net Worth − budget, so they sum to the headline Total P&L. */
  const splitEl = document.getElementById("stat-pnl-split");
  if (splitEl) {
    const fmt = (v: number) => `${v >= 0 ? "+" : "-"}$${Math.abs(v).toFixed(2)}`;
    const g = gridState.totalPnL, tf = tfState.totalPnL;
    splitEl.innerHTML =
      `<span class="${g >= 0 ? "text-pos" : "text-neg"}">Grid ${fmt(g)}</span>` +
      `<br>` +
      `<span class="${tf >= 0 ? "text-pos" : "text-neg"}">TF ${fmt(tf)}</span>`;
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
  "select=created_at&config_version=eq.v3" + CQ + "&order=created_at.asc&limit=1",
).then(rows => {
  if (!rows || !rows.length) return setText("stat-days", "0");
  const first = new Date(rows[0].created_at);
  const days  = Math.max(
    1,
    Math.floor((Date.now() - first.getTime()) / 86_400_000) + 1,
  );
  setText("stat-days", String(days));

  /* CEO decision S88 (88d Task 1): Grid card "since <date>" qualifier =
     MIN(created_at) of v3 trades, so the win/loss counter reads as the
     current testnet era. Set directly (not via the numeric tweener). */
  const sinceEl = document.getElementById("bot-grid-since");
  if (sinceEl) {
    sinceEl.textContent = `since ${first.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    })}`;
  }
}).catch(() => setText("stat-days", "N.A."));

/* ---------- 4. bot wins/losses (Grid only) ----------
   Live wins/losses from trades where managed_by='grid' (S70 rename:
   'manual'→'grid'). A win = sell with realized_pnl > 0, a loss < 0.
   CEO decision S88 (88d Task 1): only Grid shows a win/loss record. TF
   never trades directly — it hands coins to Grid — so its card shows a
   "scanning" line instead of 0/0 (see BotCardOriginal). */
type SellRow = { side: "buy" | "sell"; realized_pnl: number | null };

const fetchBotStats = async (managedBy: string) => {
  const rows = await sbFetchAll<SellRow>(
    `trades?select=side,realized_pnl&config_version=eq.v3${CQ}` +
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

fetchBotStats("grid")
  .then(grid => updateBotCard("grid", grid.wins, grid.losses))
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

/* Shared promise: project_status (section 6) needs the latest session
   number too. Resolves to null on error so the status badge still
   renders without the "Session NN" prefix. */
const diaryPromise: Promise<DiaryRow[] | null> = sbq<DiaryRow[]>(
  "diary_entries",
  "select=session,title,date,status&order=session.desc&limit=3",
).catch(() => null);

diaryPromise.then(rows => {
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
    if (sEl) sEl.textContent = String(row.session);
    if (tEl) tEl.textContent = row.title;
    if (dEl) {
      const d = new Date(`${row.date}T00:00:00`);
      dEl.textContent = isNaN(d.getTime())
        ? row.date
        : d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    }
  });
  /* If fewer than 3 entries exist (unlikely), hide remaining slots
     so we don't show empty placeholders. */
  for (let i = rows.length; i < 3; i++) {
    const slot = list.querySelector(`[data-slot="${i}"]`) as HTMLElement | null;
    if (slot) slot.style.display = "none";
  }
});

/* ---------- 6. project_status badge (Brief 86a) ----------
   Single-row table updatable by CEO/Max/CC via plain UPDATE. The badge
   stays hidden until the fetch resolves (no fallback text, better
   nothing than broken — brief 86a). Joins with diaryPromise so the
   "Session NN · Updated X" meta line gets the live session number. */
type ProjectStatusRow = {
  status_text: string;
  status_emoji: string;
  updated_at: string;
};

const relativeTime = (iso: string): string => {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const diffMs = Date.now() - then;
  if (diffMs < 60 * 60 * 1000) return "Updated just now";
  const hours = Math.floor(diffMs / (60 * 60 * 1000));
  if (hours < 24) return `Updated ${hours}h ago`;
  const days = Math.floor(diffMs / (24 * 60 * 60 * 1000));
  if (days <= 30) return `Updated ${days}d ago`;
  return `Updated ${new Date(iso).toISOString().slice(0, 10)}`;
};

Promise.all([
  sbq<ProjectStatusRow[]>(
    "project_status",
    "select=status_text,status_emoji,updated_at&limit=1",
  ).catch(() => null),
  diaryPromise,
]).then(([statusRows, diaryRows]) => {
  const box = document.getElementById("project-status-box");
  if (!box) return;
  if (!statusRows || !statusRows.length || !statusRows[0].status_text) return;
  const row = statusRows[0];
  const emojiEl = document.getElementById("project-status-emoji");
  const textEl = document.getElementById("project-status-text");
  const metaEl = document.getElementById("project-status-meta");
  if (emojiEl) emojiEl.textContent = row.status_emoji || "";
  if (textEl) textEl.textContent = row.status_text;
  const session = diaryRows && diaryRows.length ? diaryRows[0].session : null;
  const updated = relativeTime(row.updated_at);
  if (metaEl) {
    metaEl.textContent = session != null
      ? `Session ${session} · ${updated}`
      : updated;
  }
  box.classList.remove("hidden");
});

/* ---------- Mixer coins on the GRID card: live from bot_config ----------
   The GRID card's decorative mixer (MixerSVG.astro) shows coin labels,
   server-rendered to the grid-core default (BTC/SOL/BONK). Refresh them from
   the live config so they never drift. managed_by='grid' ONLY — ETH
   (managed_by='tf_grid') belongs to the TF fund, not the Grid card.
   Best-effort: on failure / empty result, keep the server-rendered default. */
type GridCfgRow = { symbol: string };
const MIXER_COIN_ORDER: Record<string, number> = { BTC: 0, SOL: 1, BONK: 2 };
sbq<GridCfgRow[]>(
  "bot_config",
  "select=symbol&managed_by=eq.grid&is_active=eq.true",
)
  .then(rows => {
    const coins = (rows ?? [])
      .map(r => r.symbol.replace("/USDT", ""))
      .sort((a, b) => (MIXER_COIN_ORDER[a] ?? 9) - (MIXER_COIN_ORDER[b] ?? 9))
      .slice(0, 3);
    if (!coins.length) return; // keep server-rendered default
    const labels = document.querySelectorAll<SVGTextElement>(
      ".bot-mixer [data-mixer-coin]",
    );
    coins.forEach((c, i) => {
      const el = labels[i];
      if (el) el.textContent = c;
    });
  })
  .catch(() => { /* keep server-rendered default */ });
