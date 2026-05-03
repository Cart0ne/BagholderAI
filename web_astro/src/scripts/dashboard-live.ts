/* Dashboard live data — wires real Supabase queries into the elements
   currently populated with mock values. Replaces piece by piece.

   Same anon-key pattern as live-stats.ts (anon is public, RLS enforces
   read-only). All updates are best-effort: if a query fails we leave
   the server-rendered mock fallback in place. */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
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

const setText = (id: string, value: string) => {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

const fmtUsd     = (n: number)         => `$${Math.abs(n).toFixed(2)}`;
const fmtSigned  = (n: number)         => `${n >= 0 ? "+" : "-"}${fmtUsd(n)}`;
const fmtPct     = (n: number)         => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;

/* ====================================================================
   0. HEADER — date label + hero meta strip (day, net worth, P&L).
   The "Today" date is just today's calendar date (UTC, same boundary
   used downstream). Day number = floor((now - v3_launch) / 1 day) + 1.
   ==================================================================== */

const V3_LAUNCH_ISO = "2026-03-30T00:00:00Z";   /* Grid v3 start */
const TF_LAUNCH_ISO = "2026-04-15T00:00:00Z";   /* first TF trade — matches legacy dashboard.html */

(() => {
  const today = new Date();
  /* "May 3, 2026" — coerente con fmtDate in dashboard-mock.ts */
  const dateLabel = today.toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
  setText("today-date", dateLabel);

  const launch = new Date(V3_LAUNCH_ISO);
  const dayN = Math.max(
    1,
    Math.floor((today.getTime() - launch.getTime()) / 86_400_000) + 1,
  );
  setText("hero-day", String(dayN));
})();

/* ====================================================================
   1. TODAY snapshot row — fotografia del giorno (Grid + TF aggregato).
   Reuses the FIFO logic already in live-stats.ts pattern. The "today"
   window is UTC midnight → now (matches the bot's daily PnL aggregation).
   ==================================================================== */

type Trade = {
  symbol: string;
  side: "buy" | "sell";
  amount: string | number;
  cost: string | number;
  created_at: string;
};

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
  if (!rows) return;

  /* Counts of today's trades, by side. Independent of FIFO. */
  let todayTrades = 0;
  let todayBuys = 0;
  let todaySells = 0;
  let todayAllocated = 0;
  for (const t of rows) {
    if (t.created_at < todayStartUtcIso) continue;
    todayTrades++;
    if (t.side === "buy") {
      todayBuys++;
      todayAllocated += Number(t.cost || 0);
    } else {
      todaySells++;
    }
  }

  /* Today P&L via strict FIFO per symbol. Same algorithm as live-stats.ts:
     replay all v3 trades in order, build a per-symbol buy queue, and on
     each sell consume from the head of the queue to compute basis. The
     P&L of a sell counts toward today only if its `created_at` is in the
     today window. */
  const bySym: Record<string, Trade[]> = {};
  for (const t of rows) (bySym[t.symbol] ||= []).push(t);

  let todayPnl = 0;
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
        if (t.created_at >= todayStartUtcIso) todayPnl += pnl;
      }
    }
  }

  /* Write into the dashboard's today snapshot row. */
  setText("today-pnl", fmtSigned(todayPnl));
  setText("today-trades", String(todayTrades));
  setText("today-buys", String(todayBuys));
  setText("today-sells", String(todaySells));
  setText("today-allocated", fmtUsd(todayAllocated));

  /* Color flip on P&L cell. */
  const pnlEl = document.getElementById("today-pnl");
  if (pnlEl) {
    pnlEl.classList.remove("text-pos", "text-neg");
    pnlEl.classList.add(todayPnl >= 0 ? "text-pos" : "text-neg");
  }
}).catch(err => {
  console.warn("[dashboard-live] today snapshot fetch failed:", err);
});

/* ====================================================================
   1b. CEO log — § 1 (today) + § 5 (archive).
   Fetches the most recent daily_commentary entries, dedupes by date
   (sometimes multiple rows exist per day → keep the latest), shows the
   newest as the "today" hero quote and the rest as the archive list.
   ==================================================================== */

type Commentary = {
  date: string;          /* ISO date YYYY-MM-DD */
  commentary: string;
  model_used: string | null;
  created_at: string;
};

const escapeHTML = (s: string) =>
  String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
  }[c]!));

const dayNumber = (isoDate: string): number => {
  const launch = new Date(V3_LAUNCH_ISO);
  const d = new Date(isoDate + "T00:00:00Z");
  return Math.max(1, Math.floor((d.getTime() - launch.getTime()) / 86_400_000) + 1);
};

const fmtCeoDate = (isoDate: string): string => {
  const d = new Date(isoDate + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const modelShortName = (raw: string | null): string => {
  if (!raw) return "haiku";
  /* "claude-haiku-4-5-20251001" → "haiku 4.5" */
  if (raw.includes("haiku-4-5")) return "haiku 4.5";
  if (raw.includes("haiku"))     return "haiku";
  if (raw.includes("sonnet"))    return "sonnet";
  if (raw.includes("opus"))      return "opus";
  return raw;
};

sbq<Commentary[]>(
  "daily_commentary",
  "select=date,commentary,model_used,created_at" +
  "&order=date.desc,created_at.desc&limit=100",
).then(rows => {
  if (!rows || !rows.length) return;

  /* Dedup per date — keep the first (= latest created_at) for each date. */
  const seen = new Set<string>();
  const entries = rows.filter(r => {
    if (seen.has(r.date)) return false;
    seen.add(r.date);
    return true;
  });

  const today = entries[0];
  const archive = entries.slice(1);       /* show all earlier entries — scrollable window handles overflow */

  /* === § 1 — today === */
  setText("ceo-today-meta", `Day ${dayNumber(today.date)} · ${fmtCeoDate(today.date)}`);
  setText("ceo-today-model", `via ${modelShortName(today.model_used)}`);
  /* Wrap in straight quotes the same way the mock did. */
  setText("ceo-today-text", `"${today.commentary}"`);

  /* === § 5 — archive (scrollable window, all entries inside) === */
  const archiveEl = document.getElementById("ceo-archive");
  if (archiveEl && archive.length) {
    archiveEl.innerHTML = archive.map(e => `
      <article class="px-4 py-3">
        <div class="font-mono text-[10px] uppercase tracking-[0.16em]
                    text-pos/60 mb-1">
          Day ${dayNumber(e.date)} · ${fmtCeoDate(e.date)}
        </div>
        <p class="text-text-dim text-[13px] leading-[1.6] italic">
          "${escapeHTML(e.commentary)}"
        </p>
      </article>
    `).join("");
  }
}).catch(err => {
  console.warn("[dashboard-live] CEO log fetch failed:", err);
});

/* ====================================================================
   2. HERO net worth — aggregato Grid manual + TF + tf_grid.
   Same formula as legacy dashboard.html: net = cash + holdings_value
     where:
       cash             = initial - net_invested - skim
       net_invested     = sum(buy.cost) - sum(sell.cost)   (per coin)
       holdings_value   = remaining_amount * live_price    (per coin)
       skim             = sum(reserve_ledger.amount)       (full fund)
     Aggregated across Grid manual ($500 budget) and TF ($100 budget).
   ==================================================================== */

type Config = { symbol: string; capital_allocation: string | number; managed_by: string };
type SkimRow = { symbol: string; amount: string | number };
type AllTrade = Trade & { realized_pnl?: string | number; managed_by?: string };

const fetchLivePrices = async (symbols: string[]): Promise<Record<string, number>> => {
  if (!symbols.length) return {};
  const binSyms = symbols.map(s => s.replace("/", ""));
  try {
    const r = await fetch(
      `https://api.binance.com/api/v3/ticker/price?symbols=` +
      encodeURIComponent(JSON.stringify(binSyms)),
    );
    if (!r.ok) throw new Error(`binance: ${r.status}`);
    const arr = (await r.json()) as { symbol: string; price: string }[];
    const out: Record<string, number> = {};
    for (const t of arr) {
      /* Binance returns "BTCUSDT" — convert back to "BTC/USDT". */
      const sym = t.symbol.replace("USDT", "/USDT");
      out[sym] = Number(t.price);
    }
    return out;
  } catch (err) {
    console.warn("[dashboard-live] binance prices failed:", err);
    return {};
  }
};

(async () => {
  try {
    const [configs, allTrades, skimRows] = await Promise.all([
      sbq<Config[]>("bot_config", "select=symbol,capital_allocation,managed_by"),
      sbq<AllTrade[]>(
        "trades",
        "select=symbol,side,amount,cost,created_at,managed_by" +
        "&config_version=eq.v3&order=created_at.asc",
      ),
      sbq<SkimRow[]>(
        "reserve_ledger",
        "select=symbol,amount&config_version=eq.v3",
      ),
    ]);

    /* Grid initial = $500 (3 manual coins) + $100 (TF budget).
       The legacy dashboard hardcoded these; we follow suit until we
       have a single source of truth for "fund initial". */
    const GRID_INITIAL = 500;
    const TF_INITIAL = 100;
    const totalInitial = GRID_INITIAL + TF_INITIAL;

    /* Group symbols and aggregate trades per symbol (single pass). */
    const symbolsActive = new Set<string>();
    const tradesBySym: Record<string, AllTrade[]> = {};
    for (const t of allTrades ?? []) {
      symbolsActive.add(t.symbol);
      (tradesBySym[t.symbol] ||= []).push(t);
    }

    /* Skim total — full fund. */
    const skimTotal = (skimRows ?? []).reduce(
      (s, r) => s + Number(r.amount || 0), 0,
    );

    /* Live prices for all symbols that have trades. */
    const prices = await fetchLivePrices([...symbolsActive]);

    /* Net invested + holdings amount per coin → cash & holdings_value. */
    let totalNetInvested = 0;
    let totalHoldingsValue = 0;
    for (const sym of symbolsActive) {
      const ts = tradesBySym[sym];
      let bought = 0, sold = 0, holdings = 0;
      for (const t of ts) {
        const amt = Number(t.amount || 0);
        const cost = Number(t.cost || 0);
        if (t.side === "buy") {
          bought += cost;
          holdings += amt;
        } else {
          sold += cost;
          holdings -= amt;
        }
      }
      totalNetInvested += (bought - sold);
      const px = prices[sym] ?? 0;
      if (holdings > 0 && px > 0) totalHoldingsValue += holdings * px;
    }

    const totalCash = totalInitial - totalNetInvested - skimTotal;
    const netWorth = totalCash + totalHoldingsValue + skimTotal;
    const totalPnl = netWorth - totalInitial;
    const totalPct = (totalPnl / totalInitial) * 100;

    setText("hero-nw", fmtUsd(netWorth));

    const pnlEl = document.getElementById("hero-pnl");
    if (pnlEl) {
      pnlEl.classList.remove("text-pos", "text-neg");
      pnlEl.classList.add(totalPnl >= 0 ? "text-pos" : "text-neg");
      pnlEl.textContent = `(${fmtSigned(totalPnl)}, ${fmtPct(totalPct)})`;
    }
  } catch (err) {
    console.warn("[dashboard-live] hero net worth failed:", err);
  }
})();

/* ====================================================================
   3. § 2 INSTRUMENTS — TF + GRID totals + coin lists (brief 46b).
   Budget logic:
     - TF section (net worth, P&L, cash):  managed_by IN ('trend_follower', 'tf_grid')
     - GRID section: managed_by = 'manual' only
   tf_grid coins are TF capital but appear visually under both bots.
   ==================================================================== */

type ConfigFull = {
  symbol: string;
  capital_allocation: string | number;
  managed_by: string;
  is_active: boolean;
  volume_tier: number | null;
};

/* Asset color palette — used for cash bar segments and card accents.
   Matches the colors used in the mock so the design system is preserved. */
const COIN_COLORS: Record<string, string> = {
  "BTC/USDT":  "#378ADD",
  "SOL/USDT":  "#5DCAA5",
  "BONK/USDT": "#EF9F27",
  "ETH/USDT":  "#a78bfa",
  "AVAX/USDT": "#fb7185",
  "ARB/USDT":  "#34d399",
  "TRX/USDT":  "#e11d48",
  "DOGE/USDT": "#f97316",
  "INJ/USDT":  "#22d3ee",
};
const colorFor = (sym: string) => COIN_COLORS[sym] ?? "#9aa3b8";
const shortFor = (sym: string) => sym.replace("/USDT", "");

/* Per-coin breakdown helper — runs FIFO replay (chronologically) to
   compute realized P&L (FIFO-correct), plus the cost basis of the
   still-open lots (openCost) and the open holdings amount.
   Matches the legacy /web/dashboard.html algorithm so numbers align. */
function analyzeCoin(trades: AllTrade[]): {
  realized: number; openCost: number; openAmount: number;
  netInvested: number; fees: number;
} {
  /* Sort defensively in case the caller didn't. */
  const sorted = [...trades].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  const queue: { amount: number; cost: number }[] = [];
  let realized = 0, fees = 0, netInvested = 0;
  for (const t of sorted) {
    const amt  = Number(t.amount || 0);
    const cost = Number(t.cost || 0);
    fees += Number(t.fee || 0);
    if (t.side === "buy") {
      queue.push({ amount: amt, cost });
      netInvested += cost;
    } else {
      let basis = 0;
      let rem   = amt;
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
      realized    += cost - basis;
      netInvested -= cost;
    }
  }
  /* Open lots = what's left in the queue after FIFO consumption.
     openCost is the TRUE cost basis for the still-held position,
     NOT raw sum(buy.cost) - sum(sell.cost) which mixes realized P&L
     into net cash flow and breaks the unrealized calculation. */
  const openAmount = queue.reduce((s, l) => s + l.amount, 0);
  const openCost   = queue.reduce((s, l) => s + l.cost,   0);
  return { realized, openCost, openAmount, netInvested, fees };
}

(async () => {
  try {
    const [configs, allTrades, skimRows, trendCfg] = await Promise.all([
      sbq<ConfigFull[]>(
        "bot_config",
        "select=symbol,capital_allocation,managed_by,is_active,volume_tier",
      ),
      sbq<AllTrade[]>(
        "trades",
        "select=symbol,side,amount,cost,fee,realized_pnl,created_at,managed_by" +
        "&config_version=eq.v3&order=created_at.asc",
      ),
      sbq<SkimRow[]>(
        "reserve_ledger",
        "select=symbol,amount&config_version=eq.v3",
      ),
      sbq<{ tf_budget: string | number }[]>(
        "trend_config",
        "select=tf_budget&limit=1",
      ),
    ]);
    /* TF budget is the canonical fund size for the TF section (not the
       sum of active allocations, which fluctuates). Falls back to 100. */
    const TF_BUDGET = Number(trendCfg?.[0]?.tf_budget ?? 100);
    /* GRID budget is the sum of manual coin allocations (fixed by design:
       BTC + SOL + BONK = $500 in v3). */
    const GRID_BUDGET = (configs ?? [])
      .filter(c => c.managed_by === "manual")
      .reduce((s, c) => s + Number(c.capital_allocation || 0), 0);

    /* Brief 46b filter: which managed_by values count for which section. */
    const tfManagedBy   = (mb: string) => mb === "trend_follower" || mb === "tf_grid";
    const gridManagedBy = (mb: string) => mb === "manual";

    /* Active configs grouped by management mode — used for net worth
       (cash, holdings) which only count for currently-open positions. */
    const tfActive = (configs ?? []).filter(c => c.is_active && tfManagedBy(c.managed_by));
    const gridActive = (configs ?? []).filter(c => c.is_active && gridManagedBy(c.managed_by));

    /* Group trades by symbol for FIFO replay. */
    const tradesBySym: Record<string, AllTrade[]> = {};
    for (const t of allTrades ?? []) (tradesBySym[t.symbol] ||= []).push(t);

    /* Live prices for all symbols that ever traded. */
    const allSymbols = Object.keys(tradesBySym);
    const prices = await fetchLivePrices(allSymbols);

    /* Trades for realized P&L + fees aggregation, filtered by managed_by
       (brief 46b). Includes trades from deallocated coins (their managed_by
       reflects the moment of the trade, so historical realized stays in the
       right bucket). */
    const tfAllTrades   = (allTrades ?? []).filter(t => tfManagedBy(t.managed_by ?? ""));
    const gridAllTrades = (allTrades ?? []).filter(t => gridManagedBy(t.managed_by ?? ""));

    /* FIFO realized + fees across ALL coins of the group (active or deallocated). */
    function realizedAndFeesAcross(trades: AllTrade[]): { realized: number; fees: number } {
      const bySym: Record<string, AllTrade[]> = {};
      for (const t of trades) (bySym[t.symbol] ||= []).push(t);
      let realized = 0, fees = 0;
      for (const sym of Object.keys(bySym)) {
        const a = analyzeCoin(bySym[sym]);
        realized += a.realized;
        fees     += a.fees;
      }
      return { realized, fees };
    }

    /* For currently-open positions: per-coin metrics (mtm, unrealized, etc.) */
    function perCoinMetrics(cfgs: ConfigFull[]) {
      const out: Array<{
        symbol: string; alloc: number; managed_by: string;
        mtmValue: number; realized: number; unrealized: number;
        avgBuy: number; livePrice: number; holdings: number;
        openCost: number;
      }> = [];
      let totalHoldingsValue = 0;
      let totalUnrealized    = 0;
      let totalOpenCost      = 0;
      let totalNetInvested   = 0;
      for (const c of cfgs) {
        const sym = c.symbol;
        const ts  = tradesBySym[sym] ?? [];
        const a   = analyzeCoin(ts);
        const px  = prices[sym] ?? 0;
        let mtm = 0, unr = 0, avgBuy = 0;
        if (a.openAmount > 0 && px > 0) {
          avgBuy = a.openCost / a.openAmount;
          mtm    = a.openAmount * px;
          unr    = mtm - a.openCost;
          totalHoldingsValue += mtm;
          totalUnrealized    += unr;
          totalOpenCost      += a.openCost;
        }
        totalNetInvested += a.netInvested;
        out.push({
          symbol: sym, alloc: Number(c.capital_allocation || 0),
          managed_by: c.managed_by,
          mtmValue: mtm, realized: a.realized, unrealized: unr,
          avgBuy, livePrice: px, holdings: a.openAmount,
          openCost: a.openCost,
        });
      }
      return {
        perCoin: out, totalHoldingsValue, totalUnrealized,
        totalOpenCost, totalNetInvested,
      };
    }

    /* Skim filtered to this group of symbols (active or not). */
    function skimFor(cfgs: ConfigFull[], allTradesGroup: AllTrade[]): number {
      /* Collect all symbols ever traded by this group + currently configured. */
      const symSet = new Set<string>();
      for (const c of cfgs) symSet.add(c.symbol);
      for (const t of allTradesGroup) symSet.add(t.symbol);
      return (skimRows ?? []).reduce(
        (s, r) => symSet.has(r.symbol) ? s + Number(r.amount || 0) : s, 0,
      );
    }

    function buildSection(
      cfgs: ConfigFull[],
      allTradesGroup: AllTrade[],
      fundBudget: number,
    ) {
      const { realized, fees } = realizedAndFeesAcross(allTradesGroup);
      const m = perCoinMetrics(cfgs);
      const skim = skimFor(cfgs, allTradesGroup);
      /* Net worth identity (legacy dashboard):
           netWorth = budget + realized + unrealized
         This naturally accounts for deallocated coins: their realized P&L
         flows into the cumulative `realized` term, while their holdings are
         zero (already excluded from `unrealized`). */
      const netWorth = fundBudget + realized + m.totalUnrealized;
      /* Cash = whatever isn't currently locked in open positions or skimmed:
           cash = netWorth - holdingsValue - skim
         This equals "fund free liquidity at the bot's disposal right now". */
      const cash = netWorth - m.totalHoldingsValue - skim;
      /* Cash% is computed against the OPERATIONAL budget (= fundBudget - skim),
         not the original budget. Skim is set aside and no longer available
         for trading, so it doesn't make sense to count it as part of the
         denominator when measuring "how much is free for reinvest right now". */
      const operationalBudget = fundBudget - skim;
      const cashPct = operationalBudget > 0 ? (cash / operationalBudget) * 100 : 0;
      return {
        totalAlloc: fundBudget, skim, cash, netWorth, cashPct,
        realized, unrealized: m.totalUnrealized, fees,
        perCoin: m.perCoin,
      };
    }

    const tf   = buildSection(tfActive,   tfAllTrades,   TF_BUDGET);
    const grid = buildSection(gridActive, gridAllTrades, GRID_BUDGET);

    /* Day counters from each bot's start date. */
    const daysSince = (iso: string) => {
      const start = new Date(iso).getTime();
      return Math.max(1, Math.floor((Date.now() - start) / 86_400_000) + 1);
    };

    /* ============ Render TF totals ============ */
    setText("tf-budget", `$${tf.totalAlloc.toFixed(0)}`);
    setText("tf-day", String(daysSince(TF_LAUNCH_ISO)));
    setText("tf-cash-reinvest", fmtUsd(tf.cash));
    setText("tf-nw", fmtUsd(tf.netWorth));
    const tfPnl = tf.netWorth - tf.totalAlloc;
    const tfPct = tf.totalAlloc > 0 ? (tfPnl / tf.totalAlloc) * 100 : 0;
    const tfPnlEl = document.getElementById("tf-pnl-pct");
    if (tfPnlEl) {
      tfPnlEl.classList.remove("text-pos", "text-neg", "text-text-muted");
      tfPnlEl.classList.add(tfPnl >= 0 ? "text-pos" : "text-neg");
      tfPnlEl.textContent = `${fmtSigned(tfPnl)} (${fmtPct(tfPct)})`;
    }
    applyMetric("tf-realized",   tf.realized);
    applyMetric("tf-unrealized", tf.unrealized);
    applyFees("tf-fees", tf.fees);
    applySkim("tf-skim", tf.skim);
    setText("tf-cash-pct", `${tf.cashPct.toFixed(0)}%`);
    renderCashBar("tf-cash-bar", tf.perCoin, tf.totalAlloc - tf.skim);

    /* ============ Render GRID totals ============ */
    setText("grid-budget", `$${grid.totalAlloc.toFixed(0)}`);
    setText("grid-day", String(daysSince(V3_LAUNCH_ISO)));
    setText("grid-cash-reinvest", fmtUsd(grid.cash));
    setText("grid-nw", fmtUsd(grid.netWorth));
    const gridPnl = grid.netWorth - grid.totalAlloc;
    const gridPct = grid.totalAlloc > 0 ? (gridPnl / grid.totalAlloc) * 100 : 0;
    const gridPnlEl = document.getElementById("grid-pnl-pct");
    if (gridPnlEl) {
      gridPnlEl.classList.remove("text-pos", "text-neg", "text-text-muted");
      gridPnlEl.classList.add(gridPnl >= 0 ? "text-pos" : "text-neg");
      gridPnlEl.textContent = `${fmtSigned(gridPnl)} (${fmtPct(gridPct)})`;
    }
    applyMetric("grid-realized",   grid.realized);
    applyMetric("grid-unrealized", grid.unrealized);
    applyFees("grid-fees", grid.fees);
    applySkim("grid-skim", grid.skim);
    setText("grid-cash-pct", `${grid.cashPct.toFixed(0)}%`);
    renderCashBar("grid-cash-bar", grid.perCoin, grid.totalAlloc - grid.skim);

    /* ============ Render coin cards ============ */
    const tfNatives = tf.perCoin.filter(c => c.managed_by === "trend_follower");
    const sharedCoins = tf.perCoin.filter(c => c.managed_by === "tf_grid");
    const gridNatives = grid.perCoin;   /* always managed_by='manual' */

    renderTfNatives("tf-natives", tfNatives);
    renderSharedCards("shared-cards", sharedCoins);
    renderGridNatives("grid-natives", gridNatives, sharedCoins);
  } catch (err) {
    console.warn("[dashboard-live] § 2 instruments failed:", err);
  }
})();

/* ====================================================================
   4. § 4 RECENT ACTIVITY — last N trades, FIFO-annotated for sells.
   Same pattern as legacy dashboard.html renderRecentTrades:
   - Replay all trades chronologically per symbol with a FIFO buy queue
   - For each sell, compute the average buy price of the consumed lots
     (so the user sees "I bought at $X, sold at $Y, P&L = (Y-X) × amount")
   - Render the most recent N (mixed Grid + TF) with bot tag color-coded.
   ==================================================================== */

const RECENT_TRADES_LIMIT = 6;

(async () => {
  try {
    const trades = await sbq<AllTrade[]>(
      "trades",
      "select=symbol,side,amount,price,cost,realized_pnl,created_at,managed_by" +
      "&config_version=eq.v3&order=created_at.asc",
    );
    if (!trades || !trades.length) return;

    /* Split by bot section per brief 46b:
       - Grid = managed_by='manual' only
       - TF   = managed_by IN ('trend_follower','tf_grid') */
    const gridTrades = trades.filter(t => t.managed_by === "manual");
    const tfTrades   = trades.filter(t =>
      t.managed_by === "trend_follower" || t.managed_by === "tf_grid",
    );

    /* FIFO replay per symbol within each group → annotate sells with
       the avg buy price of the lots they consumed. */
    function annotateBuyAvg(group: AllTrade[]): Map<AllTrade, number> {
      const bySym: Record<string, AllTrade[]> = {};
      for (const t of group) (bySym[t.symbol] ||= []).push(t);
      const out = new Map<AllTrade, number>();
      for (const sym of Object.keys(bySym)) {
        const queue: { amount: number; price: number }[] = [];
        for (const t of bySym[sym]) {
          const amt   = Number(t.amount || 0);
          const price = Number(t.price  || 0);
          if (t.side === "buy") {
            queue.push({ amount: amt, price });
          } else {
            let rem = amt, cost = 0, consumed = 0;
            while (rem > 1e-6 && queue.length > 0) {
              const lot = queue[0];
              if (lot.amount <= rem + 1e-6) {
                cost     += lot.amount * lot.price;
                consumed += lot.amount;
                rem      -= lot.amount;
                queue.shift();
              } else {
                cost     += rem * lot.price;
                consumed += rem;
                lot.amount -= rem;
                rem = 0;
              }
            }
            if (consumed > 0) out.set(t, cost / consumed);
          }
        }
      }
      return out;
    }

    const gridAnnotated = annotateBuyAvg(gridTrades);
    const tfAnnotated   = annotateBuyAvg(tfTrades);

    const fmtTradeTime = (iso: string): string => {
      const d = new Date(iso);
      return d.toLocaleString("en-US", {
        month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", hour12: false,
      });
    };
    const fmtCost = (n: number): string => `$${n.toFixed(2)}`;
    const fmtPnl  = (n: number): string => `${n >= 0 ? "+" : "-"}$${Math.abs(n).toFixed(2)}`;

    /* Render last N trades as table rows. tagPromoted=true marks tf_grid
       rows in the TF table with a tiny "→G" badge so the user can tell
       which TF trades were managed by Grid. */
    function renderRows(
      group: AllTrade[],
      annotated: Map<AllTrade, number>,
      showPromotedTag: boolean,
    ): string {
      const recent = group.slice(-RECENT_TRADES_LIMIT).reverse();
      if (!recent.length) {
        return `<tr><td colspan="5" class="px-3 py-6 text-center text-text-muted">
          No trades yet.
        </td></tr>`;
      }
      return recent.map(t => {
        const isSell  = t.side === "sell";
        const pnl     = Number(t.realized_pnl || 0);
        const buyAt   = annotated.get(t);
        const pnlClass = isSell
          ? (pnl >= 0 ? "text-pos" : "text-neg")
          : "text-text-muted";
        const sideClass = isSell ? "text-text" : "text-text-dim";
        const coin = (t.symbol || "").replace("/USDT", "");
        const promotedBadge = showPromotedTag && t.managed_by === "tf_grid"
          ? ` <span class="font-mono text-[8px] tracking-[0.1em] uppercase ml-1 px-1 py-0.5 rounded" style="background:#0f2a3a;color:#38bdf8">→g</span>`
          : "";
        const pnlCell = isSell
          ? `${fmtPnl(pnl)}${buyAt
              ? ` <span class="text-text-muted text-[10px]">@ ${fmtPriceJs(buyAt)}</span>`
              : ""}`
          : "—";
        return `
          <tr class="border-t border-border-soft hover:bg-surface-hover transition-colors">
            <td class="px-3 py-2.5 text-text-muted whitespace-nowrap">${fmtTradeTime(t.created_at)}</td>
            <td class="px-3 py-2.5 ${sideClass}">${t.side}</td>
            <td class="px-3 py-2.5 text-text whitespace-nowrap">${escapeHTML(coin)}${promotedBadge}</td>
            <td class="px-3 py-2.5 text-right text-text-dim">${fmtCost(Number(t.cost || 0))}</td>
            <td class="px-3 py-2.5 text-right ${pnlClass} whitespace-nowrap">${pnlCell}</td>
          </tr>
        `;
      }).join("");
    }

    const gridBody = document.getElementById("grid-trades-body");
    if (gridBody) gridBody.innerHTML = renderRows(gridTrades, gridAnnotated, false);

    const tfBody = document.getElementById("tf-trades-body");
    if (tfBody) tfBody.innerHTML = renderRows(tfTrades, tfAnnotated, true);
  } catch (err) {
    console.warn("[dashboard-live] recent activity fetch failed:", err);
    const errMsg = `<tr><td colspan="5" class="px-3 py-6 text-center text-text-muted">
      Failed to load trades.
    </td></tr>`;
    const gridBody = document.getElementById("grid-trades-body");
    if (gridBody) gridBody.innerHTML = errMsg;
    const tfBody = document.getElementById("tf-trades-body");
    if (tfBody) tfBody.innerHTML = errMsg;
  }
})();

/* ============ § 2 helpers ============ */

function applyMetric(id: string, value: number) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("text-pos", "text-neg", "text-text-muted");
  el.classList.add(value >= 0 ? "text-pos" : "text-neg");
  el.textContent = fmtSigned(value);
}

function applyFees(id: string, value: number) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("text-pos", "text-neg", "text-text-muted");
  el.classList.add("text-neg");
  el.textContent = `-${fmtUsd(Math.abs(value))}`;
}

function applySkim(id: string, value: number) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("text-pos", "text-neg", "text-text-muted");
  el.classList.add("text-pos");
  el.textContent = `+$${value.toFixed(4)}`;
}

function renderCashBar(
  id: string,
  perCoin: Array<{ symbol: string; mtmValue: number }>,
  totalAlloc: number,
) {
  const el = document.getElementById(id);
  if (!el || totalAlloc <= 0) return;
  el.innerHTML = perCoin
    .filter(c => c.mtmValue > 0)
    .map(c => {
      const pct = (c.mtmValue / totalAlloc) * 100;
      return `<div style="width:${pct}%;background:${colorFor(c.symbol)}"></div>`;
    })
    .join("");
}

function fmtPriceJs(p: number): string {
  if (!p || p === 0) return "—";
  if (p >= 1)        return `$${p.toFixed(2)}`;
  if (p >= 0.01)     return `$${p.toFixed(4)}`;
  if (p >= 0.0001)   return `$${p.toFixed(6)}`;
  return `$${p.toFixed(8)}`;
}

/* Unrealized % is computed against the cost basis of the open lots
   (avg buy price), matching the legacy dashboard. This represents
   "how much am I up/down vs. what I paid for the open position",
   NOT "how much vs. the total budget allocation". */
function unrealizedPct(unrealized: number, openCost: number): number {
  return openCost > 0 ? (unrealized / openCost) * 100 : 0;
}

function renderTfNatives(
  id: string,
  coins: Array<{
    symbol: string; alloc: number; mtmValue: number; avgBuy: number;
    unrealized: number; openCost: number;
  }>,
) {
  const el = document.getElementById(id);
  if (!el) return;
  /* TF native: tag "tf" amber, avg buy price (consistent with Grid). */
  const cards = coins.map(c => `
    <div class="rounded-lg border border-border bg-surface p-3 h-full">
      <div class="flex items-baseline justify-between gap-1.5 mb-1">
        <span class="font-mono text-[11px] tracking-[0.05em]"
              style="color:${colorFor(c.symbol)}">${shortFor(c.symbol)}</span>
        <span class="font-mono text-[7px] uppercase tracking-[0.14em] px-1.5 py-0.5 rounded"
              style="background:rgba(245,158,11,0.12);color:#f59e0b">tf</span>
      </div>
      <div class="text-[16px] font-semibold text-text my-1">${fmtUsd(c.mtmValue)}</div>
      <div class="font-mono text-[10px] text-text-muted">avg ${fmtPriceJs(c.avgBuy)}</div>
      <div class="font-mono text-[11px] mt-1 ${c.unrealized >= 0 ? "text-pos" : "text-neg"}">
        ${fmtSigned(c.unrealized)} (${fmtPct(unrealizedPct(c.unrealized, c.openCost))})
      </div>
    </div>
  `).join("");
  /* Pad with empty cells so single-coin TF doesn't stretch. */
  const padding = "<div></div>".repeat(Math.max(0, 3 - coins.length));
  el.innerHTML = cards + padding;
}

function renderSharedCards(
  id: string,
  coins: Array<{
    symbol: string; alloc: number; mtmValue: number; avgBuy: number;
    unrealized: number; openCost: number;
  }>,
) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = coins.map(c => `
    <div class="rounded-lg border bg-[#0d1a2e] p-3 shadow-[0_8px_24px_rgba(0,0,0,0.35)]"
         style="border-color:#38bdf8">
      <div class="flex items-baseline justify-between gap-1.5 mb-1">
        <span class="font-mono text-[11px] tracking-[0.05em]"
              style="color:${colorFor(c.symbol)}">${shortFor(c.symbol)}</span>
        <span class="pulse-shared font-mono text-[7px] uppercase tracking-[0.14em] px-1.5 py-0.5 rounded"
              style="background:#0f2a3a;color:#38bdf8">shared</span>
      </div>
      <div class="text-[15px] font-semibold text-text">${fmtUsd(c.mtmValue)}</div>
      <div class="font-mono text-[9px] text-text-muted">avg ${fmtPriceJs(c.avgBuy)}</div>
      <div class="font-mono text-[10px] mt-1 ${c.unrealized >= 0 ? "text-pos" : "text-neg"}">
        ${fmtSigned(c.unrealized)} (${fmtPct(unrealizedPct(c.unrealized, c.openCost))})
      </div>
    </div>
  `).join("");
}

function renderGridNatives(
  id: string,
  coins: Array<{
    symbol: string; alloc: number; mtmValue: number; avgBuy: number;
    unrealized: number; openCost: number;
  }>,
  _shared: Array<{
    symbol: string; alloc: number; mtmValue: number; avgBuy: number;
    unrealized: number; openCost: number;
  }>,
) {
  const el = document.getElementById(id);
  if (!el) return;
  /* Manual coins shown with their stats. Shared coins show as "from TF"
     but financially do NOT count under Grid totals (those are tf.* above). */
  const manualCards = coins.map(c => `
    <div class="rounded-lg border border-border bg-surface p-3 h-full">
      <span class="font-mono text-[11px] tracking-[0.05em]"
            style="color:${colorFor(c.symbol)}">${shortFor(c.symbol)}</span>
      <div class="text-[16px] font-semibold text-text my-1">${fmtUsd(c.mtmValue)}</div>
      <div class="font-mono text-[10px] text-text-muted">avg ${fmtPriceJs(c.avgBuy)}</div>
      <div class="font-mono text-[11px] mt-1 ${c.unrealized >= 0 ? "text-pos" : "text-neg"}">
        ${fmtSigned(c.unrealized)} (${fmtPct(unrealizedPct(c.unrealized, c.openCost))})
      </div>
    </div>
  `).join("");
  el.innerHTML = manualCards;
}
