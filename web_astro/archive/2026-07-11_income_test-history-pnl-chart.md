# Archive — /income "Test history (P&L by run)" chart

Rimosso da `/income` il 2026-07-11 (S117) e sostituito dal burn chart
"Money out vs money in". Decisione Max: la pagina è un'analisi
costi/entrate, il P&L testnet risponde a un'altra domanda ("il bot
funziona?") che vive già sulla /dashboard. **Il codice va conservato per
poterlo rigenerare** (richiesta esplicita Max, 2026-07-11).

Ultimo commit con il grafico live: `13011ef`
(`git show 13011ef:web_astro/src/scripts/income.ts`).

⚠️ La costante `PAPER` qui sotto è **irrecuperabile altrove**: è l'era
paper (€500 iniziali, 2026-03-29 → 2026-05-07) ricostruita in S106a dal
backup pre-reset `bagholderai_backups/2026-05-08_pre-reset-s67/daily_pnl.jsonl`.
Non perderla.

⚠️ Caveat noto (mai fixato): i cicli sono cablati in `CYCLE_STYLE` +
`order` — un ciclo nuovo (es. `testnet_3` dopo un reset Binance) NON
viene disegnato finché non lo aggiungi a entrambe le liste. Se rigeneri
il grafico, valuta di renderlo dinamico (qualsiasi `cycle` distinto in
`daily_pnl`, palette per indice, "(live)" sull'ultimo).

## Come rigenerarlo

1. Incolla la sezione HTML in una pagina Astro (il tag `<canvas>` e il
   CDN Chart.js sono il minimo indispensabile).
2. Incolla il blocco TS in uno script client della stessa pagina
   (`waitForChart` è già presente in `income.ts` — non duplicarlo se
   rigeneri dentro /income).
3. Servono: `sbq()` helper (fetch REST Supabase con anon key) e la
   tabella `daily_pnl` (colonne date/total_value/total_pnl/
   initial_capital/cycle).

## HTML (da income.astro, sezione "TEST HISTORY")

```html
<section class="reveal mx-auto max-w-4xl px-4 pt-4 pb-10 sm:px-6">
  <div class="rounded-2xl border border-border bg-surface px-5 py-5
              shadow-sticker-sm sm:px-7 sm:py-6">
    <div class="mb-1 flex items-baseline justify-between">
      <h2 class="font-display text-[18px] font-extrabold tracking-[-0.01em] text-text">
        Test history <span class="text-sand">(P&amp;L by run)</span>
      </h2>
      <span class="font-mono text-[10px] uppercase tracking-[0.12em] text-text-muted">
        paper · testnet v1 · v2
      </span>
    </div>
    <p class="mb-4 text-[14px] leading-[1.6] text-text-dim">
      Trading revenue is €0 because we're not live with real money yet — the
      bot runs on Binance <strong class="font-semibold text-text">testnet</strong>
      (real orders, simulated funds). That €0 means <em>not started</em>, not
      <em>not working</em>. Here's the running P&amp;L of each test run:
    </p>

    <div class="relative h-72 w-full">
      <canvas id="income-pnl-chart"></canvas>
      <p id="income-pnl-empty"
         class="hidden absolute inset-x-0 top-1/2 -translate-y-1/2
                text-center font-mono text-[12px] text-text-muted">
        No P&amp;L history yet.
      </p>
    </div>

    <p class="mt-3 text-[11.5px] leading-[1.5] text-text-muted">
      Daily portfolio P&amp;L from <code>daily_pnl</code>. The gap is the
      monthly testnet reset (a fresh start, by design). Live values on the
      <a href="/dashboard" class="underline decoration-border-soft hover:text-text">dashboard</a>.
    </p>
  </div>
</section>

<!-- Chart.js CDN (same version as /dashboard) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" is:inline></script>
```

## TypeScript (da income.ts)

```ts
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
  paper: { label: "Paper", color: "#B5562F" }, // brick
  testnet_1: { label: "Testnet v1", color: "#4E8198" }, // bot-sentinel
  testnet_2: { label: "Testnet v2 (live)", color: "#5E8A54" }, // bot-grid
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
      borderWidth: 2.5,
      pointRadius: 2.5,
      pointHoverRadius: 4,
      // tension:0 (S106a) — straight point-to-point segments. Same honesty
      // rule as the dashboard P&L chart: smooth splines invent values that
      // never existed, a lie on a radical-transparency page.
      tension: 0,
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
          border: { display: false },
          ticks: { color: "#59634F", font: mono, maxRotation: 0, autoSkip: true, maxTicksLimit: 7, callback: (_v: any, i: number) => fmtDay(labels[i]) },
        },
        y: {
          grid: { color: "#DFE4D5" },
          border: { display: false },
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
```
