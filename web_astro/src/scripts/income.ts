/* Live data for the /income page (The Passive Income Experiment — S100a).
   Reads the single `passive_income` table via Supabase REST (anon key,
   RLS read-only — same approach as live-stats.ts).

   This page is a PRIVATE SCAFFOLD (noindex, not linked) we're building to
   fill with real data over time. So the charts render the full structure
   even while everything is €0: the income donut shows a faint "ghost" of
   its future slices today and fills with the real split once a source
   earns. No fabricated data — zeros are real, the shape is a template. */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

const headers = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };

const sbq = async <T>(table: string, params: string): Promise<T> => {
  const r = await fetch(`${SB_URL}/rest/v1/${table}?${params}`, { headers });
  if (!r.ok) throw new Error(`${table}: ${r.status}`);
  return r.json() as Promise<T>;
};

type IncomeRow = {
  block: "revenue" | "traction";
  source_key: string;
  label: string;
  value_num: number | null;
  value_display: string;
  detail: string | null;
  is_status: boolean;
  method: "auto" | "manual";
  sort_order: number;
  updated_at: string;
};

/* Approx EUR→USD used for the $ figure on cost totals (Max's billing
   rate ~1.11: €1.40→$1.54, €1.60→$1.77, €270→$300). Adjust freely. */
const USD_PER_EUR = 1.11;

/* Brand palette (global.css tokens) keyed by source. */
const COLOR: Record<string, string> = {
  // revenue
  payhip_books: "#9A7C3C", // sand
  bmc_tips: "#B5862E", // butter
  aads: "#4E8198", // powder
  trading: "#5E8A54", // sage
  // costs
  claude_max: "#6E68B0", // lilla (Claude)
  haiku_api: "#4E8198", // powder
  grok_api: "#BC4032", // clay
  domain: "#B5862E", // butter
  infra: "#59634F", // muted
};
const SHORT: Record<string, string> = {
  payhip_books: "Books",
  bmc_tips: "Tips",
  aads: "Ads",
  trading: "Trading",
  claude_max: "Claude Max",
  haiku_api: "Haiku",
  grok_api: "Grok",
  domain: "Domain",
  infra: "Infra",
};

/* Book views per volume — real Payhip product views (sum 91). Hardcoded
   for now; move to a table when we wire the per-volume breakdown. */
const BOOK_VIEWS = [
  { label: "Vol 1", value: 14, color: "#9A7C3C" },
  { label: "Vol 2", value: 50, color: "#4E8198" },
  { label: "Vol 3", value: 27, color: "#B5862E" },
];

const SVG_NS = "http://www.w3.org/2000/svg";

function experimentMonth(): number {
  const start = new Date("2026-03-18T00:00:00Z");
  const now = new Date();
  const months =
    (now.getUTCFullYear() - start.getUTCFullYear()) * 12 +
    (now.getUTCMonth() - start.getUTCMonth());
  return Math.max(1, months + 1);
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const days = Math.floor((Date.now() - then) / (24 * 60 * 60 * 1000));
  if (days <= 0) return "today";
  if (days === 1) return "1d ago";
  if (days <= 30) return `${days}d ago`;
  return new Date(iso).toISOString().slice(0, 10);
}

type Seg = { label: string; value: number; color: string; display?: string };

/* SVG donut (circumference normalized to 100 via r=15.9155). When the
   total is zero we draw equal faint slices — the "ghost" of the future
   pie — so the structure is visible without claiming real proportions. */
function renderDonut(
  segsId: string,
  legendId: string,
  centerId: string,
  segments: Seg[],
  centerText: string,
): void {
  const segsEl = document.getElementById(segsId);
  const legEl = document.getElementById(legendId);
  if (!segsEl || !legEl) return;

  const total = segments.reduce((s, x) => s + x.value, 0);
  const ghost = total <= 0;
  segsEl.replaceChildren();
  legEl.replaceChildren();

  let offset = 0;
  for (const s of segments) {
    const frac = ghost ? 1 / segments.length : s.value / total;
    const pct = frac * 100;
    if (pct <= 0) continue;
    const c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("cx", "18");
    c.setAttribute("cy", "18");
    c.setAttribute("r", "15.9155");
    c.setAttribute("fill", "none");
    c.setAttribute("stroke", s.color);
    c.setAttribute("stroke-width", "3.4");
    c.setAttribute("stroke-dasharray", `${pct} ${100 - pct}`);
    c.setAttribute("stroke-dashoffset", String(25 - offset));
    if (ghost) c.setAttribute("opacity", "0.28");
    segsEl.appendChild(c);
    offset += pct;
  }

  for (const s of segments) {
    const li = document.createElement("li");
    li.className = "flex items-center justify-between gap-2";
    const left = document.createElement("span");
    left.className = "flex min-w-0 items-center gap-2";
    const dot = document.createElement("span");
    dot.className = "inline-block h-2.5 w-2.5 shrink-0 rounded-full";
    dot.style.backgroundColor = s.color;
    if (ghost) dot.style.opacity = "0.45";
    const name = document.createElement("span");
    name.className = "truncate text-text-dim";
    name.textContent = s.label;
    left.appendChild(dot);
    left.appendChild(name);
    const val = document.createElement("span");
    val.className = "shrink-0 font-mono font-semibold text-text";
    val.textContent = s.display ?? String(s.value);
    li.appendChild(left);
    li.appendChild(val);
    legEl.appendChild(li);
  }

  const centerEl = document.getElementById(centerId);
  if (centerEl) centerEl.textContent = centerText;
}

/* One income-stream card (Books / Tips / Ads / Trading). */
function buildCard(row: IncomeRow): HTMLDivElement {
  const card = document.createElement("div");
  card.className =
    "rounded-2xl border border-border bg-surface px-5 py-4 shadow-sticker-sm";

  const top = document.createElement("div");
  top.className = "flex items-center gap-2";
  const dot = document.createElement("span");
  dot.className = "inline-block h-2.5 w-2.5 rounded-full";
  dot.style.backgroundColor = COLOR[row.source_key] ?? "#9A7C3C";
  const lab = document.createElement("span");
  lab.className = "text-[13px] font-semibold text-text";
  lab.textContent = row.label;
  top.appendChild(dot);
  top.appendChild(lab);

  const val = document.createElement("div");
  if (row.is_status) {
    val.className = "mt-2 font-mono text-[14px] font-medium italic text-sand";
    val.textContent = `⏳ ${row.value_display}`;
  } else {
    val.className =
      "mt-2 font-display text-[24px] font-extrabold leading-none text-text";
    val.textContent = row.value_display;
  }

  const det = document.createElement("div");
  det.className = "mt-1 text-[12px] text-text-muted";
  det.textContent = row.detail ?? "";

  const chip = document.createElement("div");
  chip.className =
    "mt-2 font-mono text-[9.5px] uppercase tracking-[0.1em] text-text-muted";
  chip.textContent = row.is_status
    ? "testnet"
    : `${row.method} · ${relativeTime(row.updated_at)}`;

  card.appendChild(top);
  card.appendChild(val);
  card.appendChild(det);
  card.appendChild(chip);
  return card;
}

/* One traction row (Site visits / Book views). */
function buildTractionRow(row: IncomeRow): HTMLLIElement {
  const li = document.createElement("li");
  li.className =
    "flex items-baseline justify-between gap-4 border-b border-border-soft py-3.5 last:border-b-0";
  const left = document.createElement("div");
  left.className = "min-w-0";
  const label = document.createElement("div");
  label.className = "text-[14px] font-semibold leading-tight text-text";
  label.textContent = row.label;
  left.appendChild(label);
  if (row.detail) {
    const detail = document.createElement("div");
    detail.className = "mt-0.5 text-[12.5px] leading-tight text-text-muted";
    detail.textContent = row.detail;
    left.appendChild(detail);
  }
  const right = document.createElement("div");
  right.className = "shrink-0 text-right";
  const value = document.createElement("div");
  value.className = "font-display text-[19px] font-extrabold leading-none text-text";
  value.textContent = row.value_display;
  const chip = document.createElement("div");
  chip.className =
    "mt-1 font-mono text-[9.5px] uppercase tracking-[0.1em] text-text-muted";
  chip.textContent = `${row.method} · ${relativeTime(row.updated_at)}`;
  right.appendChild(value);
  right.appendChild(chip);
  li.appendChild(left);
  li.appendChild(right);
  return li;
}

function render(rows: IncomeRow[]): void {
  const sorted = [...rows].sort((a, b) => a.sort_order - b.sort_order);
  const revenue = sorted.filter((r) => r.block === "revenue");
  const traction = sorted.filter((r) => r.block === "traction");

  /* Income-stream cards */
  document
    .getElementById("income-streams")
    ?.replaceChildren(...revenue.map(buildCard));

  /* Traction rows */
  document
    .getElementById("income-traction-list")
    ?.replaceChildren(...traction.map(buildTractionRow));

  /* Total (non-status revenue, EUR) + KPI + money bar */
  const total = revenue
    .filter((r) => !r.is_status && typeof r.value_num === "number")
    .reduce((s, r) => s + (r.value_num as number), 0);
  const totalStr =
    total === 0
      ? "€0"
      : "€" + total.toLocaleString("en-US", { maximumFractionDigits: 2 });
  const totalEl = document.getElementById("income-total");
  if (totalEl) totalEl.textContent = totalStr;
  const kpiRev = document.getElementById("kpi-revenue");
  if (kpiRev) kpiRev.textContent = totalStr;
  const moneyLabel = document.getElementById("bar-money-label");
  if (moneyLabel) moneyLabel.textContent = totalStr;
  const moneyFill = document.getElementById("bar-money-fill");
  if (moneyFill) (moneyFill as HTMLElement).style.width = total > 0 ? "55%" : "0%";

  /* KPI reach + attention bar label from traction */
  const visits = traction.find((r) => r.source_key === "umami_visits");
  const kpiReach = document.getElementById("kpi-reach");
  if (kpiReach && visits) kpiReach.textContent = visits.value_display;
  const attnLabel = document.getElementById("bar-attention-label");
  if (attnLabel && traction.length) {
    attnLabel.textContent = traction
      .map((r) => `${r.value_display} ${r.label.toLowerCase()}`)
      .join(" · ");
  }

  /* Donut 1 — income by source (ghost while €0, real split once it earns) */
  renderDonut(
    "donut-income-segs",
    "donut-income-legend",
    "donut-income-center",
    revenue.map((r) => ({
      label: SHORT[r.source_key] ?? r.label,
      value: typeof r.value_num === "number" ? r.value_num : 0,
      display: r.is_status ? "soon" : r.value_display,
      color: COLOR[r.source_key] ?? "#9A7C3C",
    })),
    totalStr,
  );

  /* Donut 2 — attention by book (real data today) */
  const viewsTotal = BOOK_VIEWS.reduce((s, b) => s + b.value, 0);
  renderDonut(
    "donut-views-segs",
    "donut-views-legend",
    "donut-views-center",
    BOOK_VIEWS,
    String(viewsTotal),
  );

  /* Costs — running expenses (QuickBooks-style expense donut). The donut
     legend doubles as the cost breakdown, so no separate list. */
  const costs = sorted.filter((r) => r.block === "cost");
  const costTotal = costs.reduce(
    (s, r) => s + (typeof r.value_num === "number" ? r.value_num : 0),
    0,
  );
  const costEur = "€" + costTotal.toLocaleString("en-US", { maximumFractionDigits: 0 });
  const costUsd = "$" + Math.round(costTotal * USD_PER_EUR).toLocaleString("en-US");
  const costTotalEl = document.getElementById("income-cost-total");
  if (costTotalEl) costTotalEl.textContent = `${costEur} · ~${costUsd}`;
  const kpiSpent = document.getElementById("kpi-spent");
  if (kpiSpent) kpiSpent.textContent = "~" + costEur;
  renderDonut(
    "donut-costs-segs",
    "donut-costs-legend",
    "donut-costs-center",
    costs.map((r) => ({
      label: SHORT[r.source_key] ?? r.label,
      value: typeof r.value_num === "number" ? r.value_num : 0,
      display: r.value_display,
      color: COLOR[r.source_key] ?? "#59634F",
    })),
    costEur,
  );
}

/* Month label first (no network needed), then the data. */
const monthEl = document.getElementById("income-month");
if (monthEl) monthEl.textContent = `Month ${experimentMonth()}`;

/* Render the book-views donut immediately (constant data) so the page has
   a populated chart even before the network resolves. */
renderDonut(
  "donut-views-segs",
  "donut-views-legend",
  "donut-views-center",
  BOOK_VIEWS,
  String(BOOK_VIEWS.reduce((s, b) => s + b.value, 0)),
);

sbq<IncomeRow[]>(
  "passive_income",
  "select=block,source_key,label,value_num,value_display,detail,is_status,method,sort_order,updated_at",
)
  .then((rows) => {
    if (Array.isArray(rows) && rows.length) render(rows);
    else throw new Error("empty");
  })
  .catch(() => {
    document
      .querySelectorAll("[data-income-list]")
      .forEach((el) => ((el as HTMLElement).innerHTML = ""));
    document.getElementById("income-error")?.classList.remove("hidden");
  });

/* ---------- Test-history P&L chart (Chart.js) ----------
   Two real series come from daily_pnl (testnet v1 / v2). The paper era
   lives in a backup — drop its daily points into PAPER below (date +
   P&L in $) and the third line draws itself, no other change needed. */
type PnlRow = {
  date: string;
  total_value: number | null;
  total_pnl: number | null;
  initial_capital: number | null;
  cycle: string;
};

/* Paper era (pre-testnet, initial €500) — restored from the S67 pre-reset
   backup daily_pnl.jsonl (bagholderai_backups/2026-05-08_pre-reset-s67/).
   Static historical data, never changes; lives here rather than in the
   live daily_pnl table to avoid affecting other readers. */
const PAPER: { date: string; pnl: number }[] = [
  { date: "2026-03-29", pnl: -11.1 }, { date: "2026-03-30", pnl: -0.4 },
  { date: "2026-03-31", pnl: 0.51 }, { date: "2026-04-01", pnl: 1.08 },
  { date: "2026-04-02", pnl: -0.12 }, { date: "2026-04-03", pnl: 1.18 },
  { date: "2026-04-04", pnl: 2.49 }, { date: "2026-04-05", pnl: -5.68 },
  { date: "2026-04-06", pnl: 7.42 }, { date: "2026-04-07", pnl: 7.43 },
  { date: "2026-04-08", pnl: 8.56 }, { date: "2026-04-09", pnl: 11.97 },
  { date: "2026-04-10", pnl: 15.49 }, { date: "2026-04-11", pnl: 15.95 },
  { date: "2026-04-12", pnl: 11.51 }, { date: "2026-04-13", pnl: 14.85 },
  { date: "2026-04-14", pnl: 20.82 }, { date: "2026-04-15", pnl: 24.35 },
  { date: "2026-04-16", pnl: 29.64 }, { date: "2026-04-17", pnl: 34.95 },
  { date: "2026-04-18", pnl: 21.98 }, { date: "2026-04-19", pnl: 12.89 },
  { date: "2026-04-20", pnl: 20.34 }, { date: "2026-04-21", pnl: 18.41 },
  { date: "2026-04-22", pnl: 40.59 }, { date: "2026-04-23", pnl: 35.33 },
  { date: "2026-04-24", pnl: 39.04 }, { date: "2026-04-25", pnl: 32.75 },
  { date: "2026-04-26", pnl: 40.59 }, { date: "2026-04-27", pnl: 38.13 },
  { date: "2026-04-28", pnl: 37.11 }, { date: "2026-04-29", pnl: 36.61 },
  { date: "2026-04-30", pnl: 38.87 }, { date: "2026-05-01", pnl: 48.72 },
  { date: "2026-05-02", pnl: 48.56 }, { date: "2026-05-03", pnl: 24.03 },
  { date: "2026-05-04", pnl: 56.73 }, { date: "2026-05-05", pnl: 60.51 },
  { date: "2026-05-06", pnl: 69.95 }, { date: "2026-05-07", pnl: 69.05 },
];

const CYCLE_STYLE: Record<string, { label: string; color: string }> = {
  paper: { label: "Paper", color: "#9A7C3C" },
  testnet_1: { label: "Testnet v1", color: "#4E8198" },
  testnet_2: { label: "Testnet v2 (live)", color: "#5E8A54" },
};

function waitForChart(cb: (C: unknown) => void, tries = 0): void {
  const C = (window as unknown as { Chart?: unknown }).Chart;
  if (C) return cb(C);
  if (tries > 60) return;
  setTimeout(() => waitForChart(cb, tries + 1), 100);
}

function pnlOf(r: PnlRow): number | null {
  if (typeof r.total_pnl === "number") return r.total_pnl;
  if (typeof r.total_value === "number" && typeof r.initial_capital === "number")
    return r.total_value - r.initial_capital;
  return null;
}

function fmtDay(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function renderPnlChart(C: any, rows: PnlRow[]): void {
  const canvas = document.getElementById("income-pnl-chart") as HTMLCanvasElement | null;
  if (!canvas) return;

  const byCycle: Record<string, Record<string, number>> = {};
  for (const r of rows) {
    const v = pnlOf(r);
    if (v === null || !r.cycle) continue;
    (byCycle[r.cycle] ??= {})[r.date] = v;
  }
  if (PAPER.length) {
    const m: Record<string, number> = {};
    for (const p of PAPER) m[p.date] = p.pnl;
    byCycle.paper = m;
  }

  const order = ["paper", "testnet_1", "testnet_2"].filter((c) => byCycle[c]);
  const empty = document.getElementById("income-pnl-empty");
  if (!order.length) {
    empty?.classList.remove("hidden");
    return;
  }
  empty?.classList.add("hidden");

  const labels = Array.from(
    new Set(order.flatMap((c) => Object.keys(byCycle[c]))),
  ).sort();

  const datasets = order.map((c) => {
    const style = CYCLE_STYLE[c] ?? { label: c, color: "#59634F" };
    return {
      label: style.label,
      data: labels.map((d) => (d in byCycle[c] ? byCycle[c][d] : null)),
      borderColor: style.color,
      backgroundColor: style.color,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 4,
      tension: 0.25,
      spanGaps: false,
    };
  });

  const mono = { family: "JetBrains Mono", size: 10 };
  new C(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { font: { family: "JetBrains Mono", size: 11 }, color: "#455041", usePointStyle: true, pointStyle: "line" },
        },
        tooltip: {
          callbacks: {
            title: (items: any[]) => (items.length ? fmtDay(String(items[0].label)) : ""),
            label: (it: any) =>
              `${it.dataset.label}: ${it.parsed.y >= 0 ? "+" : ""}$${Number(it.parsed.y).toFixed(2)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "#DFE4D5" },
          ticks: { color: "#59634F", font: mono, maxRotation: 0, autoSkip: true, maxTicksLimit: 7, callback: (_v: any, i: number) => fmtDay(labels[i]) },
        },
        y: {
          grid: { color: "#DFE4D5" },
          ticks: { color: "#59634F", font: mono, callback: (v: any) => (v >= 0 ? "+" : "") + "$" + v },
          title: { display: true, text: "P&L ($)", color: "#59634F", font: mono },
        },
      },
    },
  });
}

sbq<PnlRow[]>(
  "daily_pnl",
  "select=date,total_value,total_pnl,initial_capital,cycle&order=date.asc&limit=2000",
)
  .then((rows) => waitForChart((C) => renderPnlChart(C, rows)))
  .catch(() => document.getElementById("income-pnl-empty")?.classList.remove("hidden"));
