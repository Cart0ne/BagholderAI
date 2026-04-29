# Brief 50c — Dashboard Charts Redesign: Implementation

**From:** CEO → Intern (Claude Code)
**Date:** 2026-04-29
**Depends on:** 50b (brainstorming, approvato)
**Status:** GO — mockup approvato dal Board. Procedi.

---

## TL;DR

Due modifiche al file `web/dashboard.html`, funzione `renderCharts()` (riga ~1000+). Nessun nuovo endpoint, nessuna migration DB, nessun file nuovo. Stima: 2-3h frontend.

1. **Chart "Cumulative P&L"**: aggiungi una seconda linea — realized cumulativo (continua, verde pieno) — accanto a quella mark-to-market esistente (che diventa tratteggiata, verde chiaro).
2. **Chart "Daily P&L"**: trasforma la barra unica in stacked bar Grid (verde) + TF (arancione), calcolate su realized only (non più delta net worth).

---

## 1. Chart 1 — Cumulative P&L (Proposta A)

### Cosa cambia

Il chart attualmente ha:
- 1 linea verde (net worth aggregato Grid+TF, cioè mark-to-market)
- 1 linea grigia tratteggiata (initial capital $500/$600)

Diventa:
- **Linea 1 (NUOVA) — Realized cumulativo**: continua, verde pieno, con fill sfumato
- **Linea 2 (ESISTENTE modificata) — Mark-to-market**: tratteggiata, verde chiaro, senza fill
- **Linea 3 (INVARIATA) — Break-even / Initial**: grigia tratteggiata

### Calcolo linea realized cumulativa

I dati servono dalla tabella `trades` (già fetchata per il TF reconstructor). Query logica:

```
Per ogni giorno in ordine cronologico:
  daily_realized = SUM(realized_pnl) di tutti i sell (Grid + TF) di quel giorno
  cumulative += daily_realized
```

In pratica, dentro `renderCharts()` hai già accesso a:
- `sorted` (array di `daily_pnl` rows, oldest → newest)
- `tfTrades` (tutti i trade TF)

I trade Grid sono fetchati in `fetchLiveData()` → `state._allTrades`.

**Approccio consigliato:**

```js
// Unisci Grid trades + TF trades, filtra solo i sell
var allSells = []
  .concat((state._allTrades || []).filter(t => t.side === 'sell'))
  .concat((tfTrades || []).filter(t => t.side === 'sell'));

// Realized per giorno
var realizedByDay = {};
allSells.forEach(t => {
  var day = (t.created_at || '').slice(0, 10);
  realizedByDay[day] = (realizedByDay[day] || 0) + Number(t.realized_pnl || 0);
});

// Cumulativa (usa lo stesso array `labels`/`sorted` del chart esistente)
var cumRealized = 0;
var realizedCumData = sorted.map(d => {
  cumRealized += (realizedByDay[d.date] || 0);
  return +cumRealized.toFixed(2);
});
```

### Spec visive Chart.js — datasets

**Dataset 0 — Realized (NUOVO, linea principale):**
```js
{
  label: 'Realized',
  data: realizedCumData,
  borderColor: '#22c55e',
  backgroundColor: 'rgba(34,197,94,0.06)',
  borderWidth: 2,
  fill: 'origin',
  tension: 0.3,
  pointRadius: 0,
  pointHoverRadius: 4,
  pointBackgroundColor: '#22c55e',
  pointBorderColor: '#0a0a0a',
  pointBorderWidth: 2,
  order: 1
}
```

**Dataset 1 — Mark-to-market (ESISTENTE, modificato):**
```js
{
  label: 'Mark-to-market',
  data: values,  // ← l'array che già esiste (net worth aggregato - initial)
  // NOTA: trasforma `values` da net worth assoluto a P&L relativo:
  //   markPnlData = values.map((v, i) => +(v - (initialLine[i] || 500)).toFixed(2))
  borderColor: 'rgba(134,239,172,0.6)',  // #86efac al 60%
  borderWidth: 1.5,
  borderDash: [5, 5],
  fill: false,
  tension: 0.3,
  pointRadius: 0,
  pointHoverRadius: 4,
  order: 2
}
```

**Dataset 2 — Break-even (INVARIATO, solo valore cambia da $500/$600 a $0):**
```js
{
  label: 'Break-even',
  data: sorted.map(() => 0),
  borderColor: 'rgba(255,255,255,0.12)',
  borderWidth: 1,
  borderDash: [4, 4],
  pointRadius: 0,
  fill: false,
  order: 3
}
```

**⚠️ ATTENZIONE — Cambio di asse Y:** il chart attuale mostra valori assoluti (net worth: $500-$560). Il nuovo chart mostra P&L relativo ($0 a +$60). L'asse Y va ricalibrato. La linea break-even è a $0, non a $500/$600.

Per la linea mark-to-market, calcola:
```js
var markPnlData = values.map(function(v, i) {
  return +(v - (initialLine[i] || 500)).toFixed(2);
});
```

### Tooltip

```js
callbacks: {
  label: function(ctx) {
    if (ctx.datasetIndex === 2) return null; // hide break-even
    var v = ctx.parsed.y;
    var sign = v >= 0 ? '+' : '';
    if (ctx.datasetIndex === 0) return 'Realized: ' + sign + '$' + v.toFixed(2);
    return 'Mark: ' + sign + '$' + v.toFixed(2);
  },
  afterBody: function(items) {
    if (items.length >= 2) {
      var r = items[0].parsed.y; // realized
      var m = items[1].parsed.y; // mark
      var gap = m - r;
      var sign = gap >= 0 ? '+' : '';
      return 'Gap: ' + sign + '$' + gap.toFixed(2) + ' unrealized';
    }
    return '';
  }
}
```

### Asse Y — formato

```js
y: {
  ticks: {
    callback: function(v) { return (v >= 0 ? '+' : '') + '$' + v; }
  }
}
```

### Legend HTML (sostituisce quella esistente nel markup)

Trova il `<div class="chart-legend">` sotto `#portChart` e sostituisci con:

```html
<div class="chart-legend">
  <span><span class="chart-legend-line" style="background: #22c55e;"></span> Realized (incassato)</span>
  <span><span class="chart-legend-line" style="border-top: 1.5px dashed rgba(134,239,172,0.6); background: none;"></span> Mark-to-market (live)</span>
  <span><span class="chart-legend-line" style="border-top: 1px dashed rgba(255,255,255,0.15); background: none;"></span> Break-even ($0)</span>
</div>
```

### Nota sotto il chart (sostituisce quella esistente)

```html
<div style="font-family: var(--mono); font-size: 10px; color: var(--text-dim); margin-top: 8px; font-style: italic;">
  Realized = profitti materializzati dai sell. Mark-to-market = valore corrente del portafoglio (incl. unrealized e fees). Il gap tra le due curve = unrealized swing delle posizioni aperte. Pre-15/04 = solo Grid; post-15/04 = Grid + TF.
</div>
```

### Chart label (titolo sopra il chart)

Cambia da:
```
Net worth — Grid + TF
```
A:
```
Cumulative P&L — Grid + TF
```

---

## 2. Chart 2 — Daily P&L (Proposta B)

### Cosa cambia

Il chart attualmente ha:
- 1 barra per giorno = delta net worth (mark-to-market change), colore verde/rosso

Diventa:
- **Barra verde (Grid)**: realized P&L del giorno, solo trade `managed_by = 'manual'`
- **Barra arancione (TF)**: realized P&L del giorno, solo trade `managed_by = 'trend_follower'`
- Stacked: positivi sopra zero, negativi sotto

### Calcolo dati

```js
// Riusa allSells dal Chart 1 (o ricalcola)
var gridDailyRealized = {};
var tfDailyRealized = {};

allSells.forEach(t => {
  var day = (t.created_at || '').slice(0, 10);
  var val = Number(t.realized_pnl || 0);
  if (t.managed_by === 'trend_follower') {
    tfDailyRealized[day] = (tfDailyRealized[day] || 0) + val;
  } else {
    gridDailyRealized[day] = (gridDailyRealized[day] || 0) + val;
  }
});

var gridBars = sorted.map(d => +(gridDailyRealized[d.date] || 0).toFixed(2));
var tfBars = sorted.map(d => +(tfDailyRealized[d.date] || 0).toFixed(2));
```

### Spec visive Chart.js — datasets

```js
new Chart(document.getElementById('dailyChart'), {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [
      {
        label: 'Grid',
        data: gridBars,
        backgroundColor: 'rgba(34,197,94,0.7)',
        borderColor: '#22c55e',
        borderWidth: 1,
        borderRadius: 3,
        stack: 'pnl'
      },
      {
        label: 'TF',
        data: tfBars,
        backgroundColor: 'rgba(251,146,60,0.7)',
        borderColor: '#fb923c',
        borderWidth: 1,
        borderRadius: 3,
        stack: 'pnl'
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.85)',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        titleFont: { family: "'SF Mono',monospace", size: 10 },
        bodyFont: { family: "'SF Mono',monospace", size: 11 },
        displayColors: false,
        callbacks: {
          label: function(ctx) {
            var v = ctx.parsed.y;
            var sign = v >= 0 ? '+' : '';
            var name = ctx.datasetIndex === 0 ? 'Grid' : 'TF';
            return name + ': ' + sign + '$' + v.toFixed(2);
          },
          afterBody: function(items) {
            var tot = 0;
            items.forEach(i => tot += i.parsed.y);
            var sign = tot >= 0 ? '+' : '';
            return 'Net: ' + sign + '$' + tot.toFixed(2);
          }
        }
      }
    },
    scales: {
      x: {
        stacked: true,
        ticks: { color: 'rgba(255,255,255,0.2)', font: { family: "'SF Mono',monospace", size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
        grid: { color: 'rgba(255,255,255,0.03)' },
        border: { color: 'rgba(255,255,255,0.06)' }
      },
      y: {
        stacked: true,
        ticks: {
          color: 'rgba(255,255,255,0.2)',
          font: { family: "'SF Mono',monospace", size: 9 },
          callback: function(v) { return (v >= 0 ? '+' : '') + '$' + v; }
        },
        grid: { color: 'rgba(255,255,255,0.03)' },
        border: { color: 'rgba(255,255,255,0.06)' }
      }
    }
  }
});
```

### Chart label (titolo sopra il chart)

Cambia da:
```
Daily P&L — Grid + TF
```
A:
```
Daily P&L — realized
```

### Legend HTML (NUOVA — aggiungi sopra il canvas)

```html
<div class="chart-legend" style="margin-bottom: 8px;">
  <span><span class="chart-legend-line" style="background: rgba(34,197,94,0.7); width: 10px; height: 10px; border-radius: 2px;"></span> Grid</span>
  <span><span class="chart-legend-line" style="background: rgba(251,146,60,0.7); width: 10px; height: 10px; border-radius: 2px;"></span> TF</span>
</div>
```

### Nota sotto il chart (NUOVA)

```html
<div style="font-family: var(--mono); font-size: 10px; color: var(--text-dim); margin-top: 8px; font-style: italic;">
  Barre = solo realized (profitti/perdite materializzati dai sell). Coerente con i totali Today (Grid) / Today (TF).
</div>
```

---

## 3. Firma `renderCharts()` — aggiornamento

La funzione attualmente riceve `(data, tfTrades)`. Serve anche `state` per accedere a `state._allTrades` (i Grid trades). Aggiorna la firma:

```js
function renderCharts(data, tfTrades, state) {
```

E nella chiamata in `load()`:
```js
renderCharts(pnl, tf.tfTrades, live.state);
```

---

## 4. Cose che NON cambiano

- **Trade stats row** (Total trades, Buys/Sells, Cumul. realized, Total fees) → invariato
- **Today (Grid) / Today (TF)** sotto i chart → invariato (e ora coerente con le barre)
- **Box "Cumul. realized"** nello stats → invariato (e ora coerente con il punto finale della linea piena del Chart 1)
- **Sezioni Grid / TF sopra** (Net worth, cash bars, asset cards) → invariate
- **Summary bar** in alto → invariata

---

## 5. Refinement opzionale (se hai tempo)

**Tooltip $/% sul Chart 1:** aggiungi la percentuale nel tooltip realized e mark.

```js
// Nel callback label del Chart 1:
var capital = 600; // o usa initialLine[ctx.dataIndex]
var pct = ((v / capital) * 100).toFixed(1);
return 'Realized: ' + sign + '$' + v.toFixed(2) + ' (' + sign + pct + '%)';
```

Questo è gratis in termini di effort e aggiunge contesto. NON cambiare l'asse Y — resta in $.

---

## 6. Checklist test

1. [ ] `renderCharts` riceve `state` correttamente
2. [ ] Linea realized sale monotonicamente (o scende solo per SL realizzati)
3. [ ] Linea mark-to-market corrisponde ai valori precedenti (net worth - initial), solo presentata come P&L relativo
4. [ ] Il punto finale della linea realized corrisponde al box "Cumul. realized" nello stats row (entrambi ~$59)
5. [ ] Le barre Daily Grid + TF sommate corrispondono al realized totale della giornata
6. [ ] Tooltip Chart 1: mostra Realized, Mark, Gap
7. [ ] Tooltip Chart 2: mostra Grid, TF, Net
8. [ ] Niente barre rosse "false" — le uniche barre negative sono SL o sell in perdita realizzati
9. [ ] Giorni senza sell → barra assente o a zero (non NaN, non undefined)
10. [ ] Legend e note text aggiornate in entrambi i chart
11. [ ] `Cmd+Shift+R` → render corretto locale
12. [ ] Commit + push → Vercel deploy → check su bagholderai.lol

---

## 7. File da toccare

| File | Cosa |
|---|---|
| `web/dashboard.html` riga ~1000+ | `renderCharts()` — logica JS |
| `web/dashboard.html` riga ~521-545 | HTML dei card chart — label, legend, note |
| `web/dashboard.html` riga nella `load()` | Passaggio `state` a `renderCharts` |

Nessun altro file. Nessuna migration. Nessun nuovo endpoint.

---

🏁 Hai tutto. Mockup approvato, specs dettagliate, dati già disponibili. Go.
