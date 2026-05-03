/* Live data fetch for the home page.
   Reads Supabase REST directly with the anon key (matches the legacy
   web/index.html approach — anon key is public by design, RLS handles
   read-only access). All updates are best-effort: if a query fails,
   the markup keeps its server-rendered fallback value. */

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

/* ---------- 2. realized P&L (strict FIFO per symbol) ----------
   The bot writes trades.realized_pnl using avg_buy_price as cost basis,
   which over-credits sells on volatile coins. We recompute with a FIFO
   queue per symbol so this matches /dashboard, /grid, /tf. */
type Trade = {
  symbol: string;
  side: "buy" | "sell";
  amount: string | number;
  cost: string | number;
  created_at: string;
};

/* Today = UTC midnight of the current calendar day. Coherent with the
   bot's daily PnL aggregation (UTC 00→24). */
const todayStartUtcIso = new Date(
  Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    new Date().getUTCDate(),
  ),
).toISOString();

sbq<Trade[]>(
  "trades",
  "select=symbol,side,amount,cost,created_at" +
  "&config_version=eq.v3&order=created_at.asc",
).then(rows => {
  const bySym: Record<string, Trade[]> = {};
  for (const t of rows ?? []) {
    (bySym[t.symbol] ||= []).push(t);
  }
  let total = 0;
  let todayPnl = 0;
  let todayTrades = 0;
  /* Count today's trades (any side) before the FIFO loop — independent
     of the per-symbol queues. */
  for (const t of rows ?? []) {
    if (t.created_at >= todayStartUtcIso) todayTrades++;
  }
  for (const sym of Object.keys(bySym)) {
    const queue: { amount: number; cost: number }[] = [];
    for (const t of bySym[sym]) {
      const amt = Number(t.amount);
      if (t.side === "buy") {
        queue.push({ amount: amt, cost: Number(t.cost) });
      } else {
        const revenue = Number(t.cost || 0);
        let basis = 0;
        let rem = amt;
        while (rem > 1e-6 && queue.length > 0) {
          const lot = queue[0];
          if (lot.amount <= rem + 1e-6) {
            basis += lot.cost;
            rem   -= lot.amount;
            queue.shift();
          } else {
            const portion = rem / lot.amount;
            basis      += lot.cost * portion;
            lot.cost   -= lot.cost * portion;
            lot.amount -= rem;
            rem = 0;
          }
        }
        const pnl = revenue - basis;
        total += pnl;
        if (t.created_at >= todayStartUtcIso) todayPnl += pnl;
      }
    }
  }
  const sign = total >= 0 ? "+" : "-";
  setText("stat-pnl", `${sign}$${Math.abs(total).toFixed(2)}`);
  const tsign = todayPnl >= 0 ? "+" : "-";
  setText("stat-today-pnl", `${tsign}$${Math.abs(todayPnl).toFixed(2)}`);
  setText("stat-today-trades", String(todayTrades));
  /* Dynamic color: red when negative, green when positive/zero.
     We mutate classes directly because today P&L flips daily. */
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
  const rows = await sbq<SellRow[]>(
    "trades",
    `select=side,realized_pnl&config_version=eq.v3&managed_by=eq.${managedBy}` +
    "&side=eq.sell",
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

/* ---------- 5. current session number (max session in diary_entries) ---------- */
sbq<{ session: number }[]>(
  "diary_entries",
  "select=session&order=session.desc&limit=1",
).then(rows => {
  if (!rows || !rows.length) return;
  const el = document.getElementById("stat-session");
  if (el) el.textContent = String(rows[0].session);
}).catch(() => {});
