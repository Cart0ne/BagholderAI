/* Mock data per i prototipi /dashboard.
   I numeri sono inventati ma plausibili (ordini di grandezza coerenti
   con il vero stato a inizio maggio 2026). Servono solo a riempire
   i layout durante la fase di prototipazione. Quando il layout sarà
   approvato, sostituiremo con fetch Supabase reali (vedi
   web/dashboard.html per le query originali). */

export const mockSnapshot = {
  asOfIso:        "2026-05-02T18:00:00Z",
  asOfLabel:      "May 2, 2026 · 20:00 Rome",
  dayNumber:      34,                     // giorni dall'inizio v3 (2026-03-30)
  initialCapital: 600,                    // 500 Grid + 100 TF
};

export const mockGrid = {
  initial:        500,
  netWorth:       527.84,
  pnlAbs:         27.84,
  pnlPct:         5.57,
  realized:       19.42,
  unrealized:     8.42,
  fees:           4.31,
  cashAvail:      287.55,
  cashPct:        54.5,
  trades:         147,
  buys:           82,
  sells:          65,
  todayPnl:       1.34,
  todayTrades:    6,
  todayBuys:      3,
  todaySells:     3,
  todayAllocated: 28.55,   // capitale messo a lavoro oggi (somma cost dei buy)
  assets: [
    {
      symbol:  "BTC/USDT",
      short:   "BTC",
      color:   "#378ADD",
      alloc:   200,
      cashLeft: 112.40,
      holdings: 0.00139,
      mtmValue: 96.58,
      avgBuy:  62418.20,
      livePrice: 69483.51,
      realized: 8.95,
      unrealized: 9.81,
    },
    {
      symbol:  "SOL/USDT",
      short:   "SOL",
      color:   "#5DCAA5",
      alloc:   200,
      cashLeft: 91.15,
      holdings: 0.612,
      mtmValue: 110.22,
      avgBuy:  171.94,
      livePrice: 180.12,
      realized: 7.10,
      unrealized: 5.01,
    },
    {
      symbol:  "BONK/USDT",
      short:   "BONK",
      color:   "#EF9F27",
      alloc:   100,
      cashLeft: 84.00,
      holdings: 871420.5,
      mtmValue: 16.55,
      avgBuy:  0.0000182,
      livePrice: 0.0000190,
      realized: 3.37,
      unrealized: -6.40,
    },
  ],
};

export const mockTF = {
  initial:        100,
  netWorth:       104.92,
  pnlAbs:         4.92,
  pnlPct:         4.92,
  realized:       3.18,
  unrealized:     1.74,
  fees:           0.62,
  cashAvail:      72.10,
  cashPct:        72.1,
  trades:         18,
  buys:           11,
  sells:          7,
  todayPnl:       0.42,
  todayTrades:    2,
  todayBuys:      1,
  todaySells:     1,
  todayAllocated: 9.64,
  assets: [
    { symbol: "ETH/USDT",   short: "ETH",   color: "#a78bfa", alloc: 33.34, holdings: 0.0072, mtmValue: 22.94, livePrice: 3186.10, realized: 1.10, unrealized: 0.61 },
    { symbol: "AVAX/USDT",  short: "AVAX",  color: "#fb7185", alloc: 33.33, holdings: 0.41,   mtmValue:  9.88, livePrice:  24.10, realized: 0.84, unrealized: 0.55 },
    { symbol: "ARB/USDT",   short: "ARB",   color: "#34d399", alloc: 33.33, holdings: 0,      mtmValue:  0,    livePrice:   0.78, realized: 1.24, unrealized: 0.58 },
  ],
};

/* I 4 "strumenti" del lab, inclusi quelli ancora coming.
   Usato dal Prototype A (lab notebook). */
export const mockTools = [
  {
    key:      "grid",
    name:     "Grid Bot",
    rarity:   "common",
    status:   "live",
    color:    "#22c55e",
    capital:  500,
    nw:       527.84,
    pnlPct:   5.57,
    days:     34,
    blurb:    "Buys low, sells high. Mechanical. The cash machine.",
  },
  {
    key:      "tf",
    name:     "Trend Follower",
    rarity:   "rare",
    status:   "live",
    color:    "#f59e0b",
    capital:  100,
    nw:       104.92,
    pnlPct:   4.92,
    days:     17,
    blurb:    "Hunts breakouts on multi-tier scans. Beta since Apr 15.",
  },
  {
    key:      "sentinel",
    name:     "Sentinel",
    rarity:   "epic",
    status:   "soon",
    color:    "#3b82f6",
    capital:  null,
    nw:       null,
    pnlPct:   null,
    days:     null,
    blurb:    "Risk officer. Watches the others. Not deployed yet.",
  },
  {
    key:      "sherpa",
    name:     "Sherpa",
    rarity:   "legendary",
    status:   "soon",
    color:    "#ef4444",
    capital:  null,
    nw:       null,
    pnlPct:   null,
    days:     null,
    blurb:    "Macro-aware capital allocator. Far horizon.",
  },
];

/* Cumulative P&L mock — 35 giorni di curva realistica.
   Realized monotona crescente (incassi), MTM oscillante sopra/sotto.
   Day 0 = 2026-03-30 (inizio v3). */
function genCumulativeMock() {
  const days = 35;
  const out: { day: number; date: string; realized: number; mtm: number }[] = [];
  const start = new Date("2026-03-30T00:00:00Z");
  let realized = 0;
  let mtm = 0;
  for (let i = 0; i < days; i++) {
    /* Realized: crescita lenta, accelera a partire dal day 15 quando entra TF */
    const dailyR = i < 15 ? 0.4 + Math.random() * 0.6 : 0.6 + Math.random() * 1.0;
    realized += dailyR;
    /* MTM: gira intorno a realized con swing */
    const swing = Math.sin(i * 0.4) * 4 + (Math.random() - 0.5) * 2;
    mtm = realized + swing;
    const d = new Date(start.getTime() + i * 86400000);
    out.push({
      day: i + 1,
      date: d.toISOString().slice(0, 10),
      realized: +realized.toFixed(2),
      mtm: +mtm.toFixed(2),
    });
  }
  return out;
}
export const mockCumulative = genCumulativeMock();

/* Daily P&L per giorno (Grid + TF stacked). Solo realized.
   Ricavato dalla differenza giorno su giorno della curva realized. */
export const mockDaily = mockCumulative.map((p, i, arr) => {
  const prev = i === 0 ? 0 : arr[i - 1].realized;
  const total = +(p.realized - prev).toFixed(2);
  /* Pre-day-15: 100% Grid. Post: split 70/30 Grid/TF circa. */
  const tfShare = i < 15 ? 0 : 0.25 + Math.random() * 0.2;
  const tf   = +(total * tfShare).toFixed(2);
  const grid = +(total - tf).toFixed(2);
  return { day: p.day, date: p.date, grid, tf };
});

/* Trades — un mix di Grid+TF, ordinato per data desc, ultimi 12. */
export const mockTrades = [
  { id: 12, ts: "2026-05-02T17:42:00Z", bot: "grid", side: "sell", symbol: "SOL/USDT", price: 180.12, cost: 18.01, buyAt: 174.20, pnl: 0.59 },
  { id: 11, ts: "2026-05-02T16:18:00Z", bot: "tf",   side: "buy",  symbol: "AVAX/USDT", price:  24.10, cost: 9.64,  buyAt: null,    pnl: null },
  { id: 10, ts: "2026-05-02T14:51:00Z", bot: "grid", side: "buy",  symbol: "BTC/USDT",  price: 69281.0, cost: 11.25, buyAt: null,    pnl: null },
  { id:  9, ts: "2026-05-02T11:07:00Z", bot: "grid", side: "sell", symbol: "BONK/USDT", price:   0.0000190, cost: 16.50, buyAt: 0.0000178, pnl: 0.62 },
  { id:  8, ts: "2026-05-02T09:33:00Z", bot: "grid", side: "buy",  symbol: "SOL/USDT",  price: 178.40, cost: 17.80, buyAt: null,    pnl: null },
  { id:  7, ts: "2026-05-02T07:12:00Z", bot: "tf",   side: "sell", symbol: "ETH/USDT",  price: 3186.10, cost: 12.74, buyAt: 3098.00, pnl: 0.35 },
  { id:  6, ts: "2026-05-01T22:41:00Z", bot: "grid", side: "sell", symbol: "BTC/USDT",  price: 69483.5, cost: 13.90, buyAt: 67120.0, pnl: 0.47 },
  { id:  5, ts: "2026-05-01T19:05:00Z", bot: "grid", side: "buy",  symbol: "BONK/USDT", price:   0.0000178, cost: 16.50, buyAt: null, pnl: null },
  { id:  4, ts: "2026-05-01T15:28:00Z", bot: "grid", side: "sell", symbol: "SOL/USDT",  price: 179.85, cost: 17.99, buyAt: 173.10, pnl: 0.68 },
  { id:  3, ts: "2026-05-01T12:14:00Z", bot: "tf",   side: "buy",  symbol: "ARB/USDT",  price:   0.78,  cost: 11.10, buyAt: null,    pnl: null },
  { id:  2, ts: "2026-05-01T08:50:00Z", bot: "grid", side: "buy",  symbol: "BTC/USDT",  price: 68950.0, cost: 11.25, buyAt: null,    pnl: null },
  { id:  1, ts: "2026-04-30T21:33:00Z", bot: "grid", side: "sell", symbol: "BONK/USDT", price:   0.0000182, cost: 16.50, buyAt: 0.0000170, pnl: 0.71 },
];

export const mockCEOLog = {
  today: {
    date: "2026-05-02",
    dayNumber: 34,
    model: "haiku",
    text: "Day 34. The grid is doing its job — small, boring wins. SOL printed three sells today as the slope curled up; I let it run because the volatility regime hasn't shifted. TF entered AVAX, half a tier. Sherpa would tell me I'm overweight green right now. Sherpa isn't here yet.",
  },
  archive: [
    { date: "2026-05-01", dayNumber: 33, model: "haiku",
      text: "Quiet day. Markets tight, only 4 sells across both bots. I'd rather have boring days than dramatic ones at this stage." },
    { date: "2026-04-30", dayNumber: 32, model: "haiku",
      text: "BONK whipsawed and the Grid printed two clean cycles. The bot doesn't care that BONK is a meme; the grid is the grid. That's the point." },
    { date: "2026-04-29", dayNumber: 31, model: "haiku",
      text: "TF flagged ETH on the 4h breakout. I let it take a tier. We'll see in 48 hours whether the system or the noise wins." },
    { date: "2026-04-28", dayNumber: 30, model: "haiku",
      text: "Thirty days. The fund is up a few percent. Nothing to celebrate, nothing to mourn. The whole point is that we're still here." },
  ],
};

/* Helpers di formato condivisi tra i 3 prototipi. */
export function fmtUsd(n: number, d = 2): string {
  return "$" + n.toFixed(d);
}
export function fmtSigned(n: number, d = 2): string {
  return (n >= 0 ? "+" : "") + "$" + n.toFixed(d);
}
export function fmtPct(n: number, d = 2): string {
  return (n >= 0 ? "+" : "") + n.toFixed(d) + "%";
}
export function fmtPrice(p: number): string {
  if (p === 0) return "$0.00";
  if (p >= 1)        return "$" + p.toFixed(2);
  if (p >= 0.01)     return "$" + p.toFixed(4);
  if (p >= 0.0001)   return "$" + p.toFixed(6);
  return "$" + p.toFixed(8);
}
export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}
export function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
