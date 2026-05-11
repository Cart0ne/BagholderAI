/* Canonical P&L formulas — single source of truth across home, dashboard,
   and grid.html. Brief 71a Task 1 (P&L Hero Unification).

   Two metrics, both NET of fees, applied identically everywhere:

   - Total P&L (hero):
       netWorth   = cash + holdings_mtm + skim − fees
       totalPnL   = netWorth − budget
     where:
       cash       = budget − netInvested − skim         (USDT free at bot disposal)
       netInvested= Σ buy.cost − Σ sell.cost            (per fund partition)
       holdings_mtm= Σ open_amount × live_price         (mark-to-market)
       skim       = Σ reserve_ledger.amount             (skim accantonata)
       fees       = Σ trades.fee                        (USDT-equivalent, already canonical)

   - Net Realized Profit (post-fees):
       netRealized = Σ realized_pnl − fees              (escluso unrealized)

   Inputs are filtered by the caller (managed_by, symbol-set, ecc.).
   This module assumes the trade rows have ALREADY been narrowed to the
   bot/section you care about — it just runs the avg-cost replay. */

export type CanonicalTrade = {
  symbol: string;
  side: "buy" | "sell";
  amount: string | number;
  cost: string | number;
  fee?: string | number | null;
  /* Brief 72a (S72): broker's fee currency. When it equals the base coin
     (e.g. 'BONK' on BONK/USDT BUY), Binance scaled the fee from the wallet
     base balance — we must subtract `fee/price` from qty_acquired so the
     replay matches the bot. Paper trades default to 'USDT' (no impact). */
  fee_asset?: string | null;
  realized_pnl?: string | number | null;
  created_at: string;
};

export type CanonicalState = {
  cash: number;
  holdingsMtm: number;
  skim: number;
  fees: number;
  realized: number;
  unrealized: number;
  netInvested: number;
  netWorth: number;
  totalPnL: number;
  netRealized: number;
  perCoin: Array<{
    symbol: string;
    holdings: number;
    avgBuyPrice: number;
    livePrice: number;
    mtm: number;
    openCost: number;
    unrealized: number;
    unrealizedPct: number;
    realized: number;
  }>;
};

/* Avg-cost canonical replay — mirror of bot/grid/buy_pipeline.py:117 +
   bot/grid/sell_pipeline.py:374 (reset avg when holdings hit zero). */
type SymState = {
  holdings: number;
  avgBuyPrice: number;
  totalInvested: number;
  totalReceived: number;
  realized: number;
  fees: number;
};

function replayAvgCost(trades: CanonicalTrade[]): Record<string, SymState> {
  const out: Record<string, SymState> = {};
  const sorted = [...trades].sort(
    (a, b) => a.created_at.localeCompare(b.created_at),
  );
  for (const t of sorted) {
    const sym = t.symbol;
    const base = sym.split("/")[0]?.toUpperCase() ?? "";
    const s = (out[sym] ||= {
      holdings: 0, avgBuyPrice: 0,
      totalInvested: 0, totalReceived: 0,
      realized: 0, fees: 0,
    });
    const amt = Number(t.amount || 0);
    const cost = Number(t.cost || 0);
    const fee = Number(t.fee || 0);
    const feeAsset = (t.fee_asset || "USDT").toString().toUpperCase();
    s.fees += fee;
    if (t.side === "buy") {
      const price = amt > 0 ? cost / amt : 0;
      /* Brief 72a P2 (S72): when fee_asset matches the base coin (live BUY),
         Binance scales the commission from the base balance — derive
         fee_native ≈ fee_usdt / price and subtract from qty_acquired so the
         replay matches the actual wallet. Paper trades have fee_asset='USDT'
         (default) → fee_native_est = 0 → legacy behaviour preserved. */
      const feeNativeEst = (feeAsset === base && price > 0) ? fee / price : 0;
      const qtyAcquired = amt - feeNativeEst;
      const newH = s.holdings + qtyAcquired;
      if (newH > 0) {
        /* P2 formula: avg = total_cost_usdt / qty_net_acquired (mirror of
           bot/grid/buy_pipeline.py:215). On paper trades the formula
           collapses to the legacy (cost = price × amt, qty_acquired = amt)
           — numerically identical. */
        s.avgBuyPrice = (s.avgBuyPrice * s.holdings + cost) / newH;
      }
      s.holdings = newH;
      s.totalInvested += cost;
    } else {
      s.holdings -= amt;
      s.totalReceived += cost;
      const dbPnl = Number(t.realized_pnl);
      if (Number.isFinite(dbPnl)) s.realized += dbPnl;
      if (s.holdings <= 1e-9) {
        s.holdings = 0;
        s.avgBuyPrice = 0;
      }
    }
  }
  return out;
}

/* Main entry point. Returns the full canonical breakdown for one bot/fund.

   - `trades`     trade rows already filtered to this fund (managed_by, …)
   - `skim`       total skim USDT for this fund (Σ reserve_ledger.amount)
   - `livePrices` map "BTC/USDT" → live price (Binance ticker)
   - `budget`     allocated starting capital ($500 Grid, $100 TF, …) */
export function computeCanonicalState(
  trades: CanonicalTrade[],
  skim: number,
  livePrices: Record<string, number>,
  budget: number,
): CanonicalState {
  const bySym = replayAvgCost(trades);

  let netInvested = 0;
  let holdingsMtm = 0;
  let fees = 0;
  let realized = 0;
  let unrealized = 0;
  const perCoin: CanonicalState["perCoin"] = [];

  for (const sym of Object.keys(bySym)) {
    const s = bySym[sym];
    netInvested += (s.totalInvested - s.totalReceived);
    fees += s.fees;
    realized += s.realized;
    const px = livePrices[sym] ?? 0;
    const mtm = s.holdings > 0 && px > 0 ? s.holdings * px : 0;
    const openCost = s.avgBuyPrice * s.holdings;
    const unr = mtm > 0 ? mtm - openCost : 0;
    holdingsMtm += mtm;
    unrealized += unr;
    perCoin.push({
      symbol: sym,
      holdings: s.holdings,
      avgBuyPrice: s.avgBuyPrice,
      livePrice: px,
      mtm,
      openCost,
      unrealized: unr,
      unrealizedPct: openCost > 0 ? (unr / openCost) * 100 : 0,
      realized: s.realized,
    });
  }

  const cash = budget - netInvested - skim;
  const netWorth = cash + holdingsMtm + skim - fees;
  const totalPnL = netWorth - budget;
  /* Known bias (Brief 72a S72): for the 18 live testnet trades that were
     backfilled with realized = (price - avg) × qty − fee_sell, this formula
     subtracts fee_sell twice (once via the backfilled value, once via the
     `fees` total). Bias ≈ −$0.22 cumulato (sotto-rappresenta netRealized).
     Per i 458 paper trade pre-S67 la formula resta corretta (realized gross,
     una sottrazione di fees totale). Decisione editoriale CEO 2026-05-11:
     paper as-is, accettato bias temporaneo. Fix architetturale rinviato
     a brief S73+ (split paper/live nel rendering pubblico). */
  const netRealized = realized - fees;

  return {
    cash, holdingsMtm, skim, fees, realized, unrealized,
    netInvested, netWorth, totalPnL, netRealized, perCoin,
  };
}

/* Helper used by the 4-coin Binance ticker fetch. Same endpoint in
   live-stats.ts and dashboard-live.ts — extracted here so the home and
   dashboard hit Binance via one shared code path. */
export async function fetchLivePrices(
  symbols: string[],
): Promise<Record<string, number>> {
  if (!symbols.length) return {};
  try {
    const binSyms = symbols.map(s => s.replace("/", ""));
    const r = await fetch(
      "https://api.binance.com/api/v3/ticker/price?symbols=" +
      encodeURIComponent(JSON.stringify(binSyms)),
    );
    if (!r.ok) return {};
    const arr = (await r.json()) as { symbol: string; price: string }[];
    const out: Record<string, number> = {};
    for (const row of arr) {
      const slash = row.symbol.replace(/USDT$/, "/USDT");
      out[slash] = Number(row.price);
    }
    return out;
  } catch {
    return {};
  }
}
