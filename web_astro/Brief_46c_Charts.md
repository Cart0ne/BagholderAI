# Brief 46c — Dashboard Charts (§ 3 Performance)

**Session:** future (mente fresca)
**Priority:** Medium
**Scope:** `web_astro/src/pages/dashboard.astro` — sezione `§ 3 · Performance · time series`
**Depends on:** brief 46b (budget logic), § 2 Instruments già wired

---

## Contesto

La sezione § 3 della nuova `/dashboard` mostra 2 grafici Chart.js affiancati,
attualmente popolati da **mock data** (`mockCumulative`, `mockDaily` da
`dashboard-mock.ts`). Il resto della dashboard è già su dati reali Supabase.
Manca questa sezione + decisioni di sostanza che richiedono ragionamento.

---

## Cosa c'è oggi (mock)

**Grafico 1 — Cumulative P&L** (line chart):
- 2 serie: `realized` (linea piena verde) + `mtm` (linea tratteggiata verde)
- Asse X: data (35 giorni)
- Asse Y: dollari
- Label: "Cumulative P&L · realized + mtm"

**Grafico 2 — Daily realized** (bar chart stacked):
- 2 serie stacked: `grid` (verde) + `tf` (arancione)
- Asse X: data
- Asse Y: dollari
- Label: "Daily realized · grid + tf stacked"

Il pattern è verbatim dal vecchio `web/dashboard.html` (linee 522-553).

---

## Stato dei dati Supabase

Tabella `daily_pnl` (verificata 2026-05-03):
- 35 record (Mar 29 → May 2)
- **Tutti con `managed_by = 'grid'`** — nessuna entry per `tf` o `trend_follower`
- Colonne utili: `date`, `total_value`, `realized_pnl_today`, `total_pnl`, `holdings_value`, `cash_remaining`, `trades_count`, `managed_by`

**Conseguenza**: `daily_pnl` storicamente è stato scritto **solo per Grid manuale**.
Il TF non aveva snapshot daily registrati. Quindi il grafico cumulative,
se vogliamo includere TF, deve essere ricostruito da `trades` lato client
(stesso approccio della vecchia dashboard, vedi `reconstructTFForDay` linee 974-1060
del legacy `web/dashboard.html`).

---

## Decisioni da prendere col CEO/Max

### 1. Scope dei grafici dopo il brief 46b

Il brief 46b ha cambiato la semantica:
- **GRID section** = solo `manual` (BTC/SOL/BONK)
- **TF section** = `trend_follower + tf_grid`

Le 3 opzioni per il **Cumulative P&L**:

**(a) Solo Grid (più semplice)**
- Fetch diretto da `daily_pnl WHERE managed_by='grid'`
- 2 linee: realized cumul + total_pnl (= mtm cumul)
- Label: "Cumulative P&L · Grid Bot"
- Pro: zero ricostruzione, dati già pronti
- Contro: utente non vede TF

**(b) Grid + TF aggregato (medio)**
- Grid: come (a)
- TF: ricostruito client-side da `trades` con `managed_by IN ('trend_follower','tf_grid')`
- Sommato giorno per giorno
- Pro: vista del fondo intero
- Contro: TF storico è approssimato (no snapshot serale fissato), MTM passato richiede prezzo storico daily che non abbiamo

**(c) 2 grafici/serie separate (massimo dettaglio)**
- Una linea Grid e una linea TF, distinguibili per colore
- L'utente vede contributo individuale
- Pro: chiarezza
- Contro: più lavoro, possibile rumore visivo

**Domanda secca**: a, b, o c?

### 2. MTM storico (mark-to-market) — scope

Il "mtm" del grafico cumulative usa il valore del portafoglio a fine giornata.
- Per Grid (da `daily_pnl.total_value`) abbiamo lo snapshot serale ✓
- Per TF non c'è snapshot. Ricostruirlo richiede:
  - Per ogni giorno: holdings amount × prezzo di quella sera
  - **Non abbiamo prezzi storici daily affidabili** (Binance ticker è "live", per storico serve klines daily)
  - La vecchia approssima usando "ultimo prezzo trade ≤ end-of-day" → ~5% margine d'errore (vedi commento legacy linea 970-973)

**Domanda**: accettiamo l'approssimazione legacy (~5% di errore) o vogliamo:
- Skippare MTM TF e mostrare solo realized
- Fetchare klines daily Binance per ogni coin TF (lento, molte chiamate)
- Lasciare il grafico a "Grid only" finché TF non scrive `daily_pnl`

### 3. Daily P&L bar chart — split TF/Grid

Più semplice: il bar chart usa `realized_pnl_today` di `daily_pnl`.
Per TF dobbiamo aggregare giorno per giorno i trade (somma `realized_pnl` raw o
ricalcolato FIFO?).

**Sotto-domanda**: per il chart usiamo `realized_pnl` raw del DB (più veloce,
ha bias multi-lot pre-53a) o ricalcoliamo FIFO daily client-side (più lento ma
preciso)?

La vecchia usa **`realized_pnl` raw**. Memoria 53a dice che il bias storico è
~$17.74 totale, distribuito su molti giorni → effetto visivo trascurabile su
un bar chart. Probabile opzione: usiamo raw per coerenza con la vecchia.

---

## Implementazione suggerita (una volta approvate le decisioni)

### Approccio (a) — solo Grid (consigliato per partire)

```ts
// In dashboard-live.ts, aggiungere:

const dailyPnlRows = await sbq<{
  date: string; total_value: string; realized_pnl_today: string;
  total_pnl: string;
}[]>(
  "daily_pnl",
  "select=date,total_value,realized_pnl_today,total_pnl" +
  "&managed_by=eq.grid&order=date.asc",
);

// Cumulative line chart:
//   labels = dates
//   realized series = cumulative sum of realized_pnl_today
//   mtm series = total_pnl (già cumulativo)

// Daily bar chart:
//   labels = dates
//   single bar per day = realized_pnl_today (no stack — solo Grid)
```

Charts esistenti già configurati in `dashboard.astro` linee ~500-560 con
Chart.js 4.4.1 via CDN. Sostituire `chartData` mock con quello calcolato dal
fetch e re-renderizzare al `pageshow`.

### Approccio (b) — Grid + TF aggregato

Aggiungere a (a):

```ts
const tfTrades = await sbq<AllTrade[]>(
  "trades",
  "select=symbol,side,amount,cost,realized_pnl,created_at,managed_by" +
  "&config_version=eq.v3" +
  "&managed_by=in.(trend_follower,tf_grid)" +
  "&order=created_at.asc",
);

// Per ogni giorno:
//   tfRealizedDay[d] = sum(realized_pnl) of tf trades with date=d
//   tfMtmDay[d] = reconstructTFForDay(tfTrades, d)   // approssimato

// Sommare a Grid serie corrispondenti
```

Il `reconstructTFForDay` legacy (linee 974-1060) prende ~80 righe di FIFO
+ holdings + last-known-price.

---

## File coinvolti

| File | Modifica |
|------|----------|
| `web_astro/src/scripts/dashboard-live.ts` | Aggiungere blocco `§ 3 charts` con fetch + Chart.js update |
| `web_astro/src/pages/dashboard.astro` | Eventualmente cambiare label "Daily realized" se opzione (a) → "Daily realized · Grid only" |
| `web_astro/src/data/dashboard-mock.ts` | A fine wiring, rimuovere `mockCumulative` e `mockDaily` (no longer used) |

---

## Test checklist

- [ ] Cumulative line chart popolato con dati reali, asse X = date corrette
- [ ] Linea realized monotona crescente (può scendere se un giorno ha P&L negativo, ma cumul può scendere solo se realized_today < 0)
- [ ] Linea MTM oscillante intorno a realized
- [ ] Bar chart daily: barre verdi/arancioni, asse Y in dollari
- [ ] Tooltip Chart.js mostra valore esatto al hover
- [ ] Loading state: charts mostrano "Loading…" finché fetch non completa
- [ ] Error state: se fetch fallisce, charts mostrano messaggio neutro
- [ ] Numeri matchano vecchia `web/dashboard.html` per Grid (caso a)

---

## Decisioni di sostanza da fissare PRIMA di codare

1. **Scope chart**: a / b / c (vedi sezione 1)
2. **MTM TF storico**: approssimato / skippato / fetch klines (vedi sezione 2)
3. **Daily bar chart**: realized raw o FIFO ricalcolato? (probabile: raw)
4. **TF inizia il 15 aprile**: il chart cumulative parte da Mar 30 (Grid) ma
   TF appare solo da Apr 15 → il primo mese il chart mostra solo Grid?
   Confermare comportamento.

---

## Riferimenti legacy

- `web/dashboard.html` linee 522-553 — markup chart
- `web/dashboard.html` linee 967-1060 — `reconstructTFForDay` + chart rendering
- `web/dashboard.html` linee 1062-1180 — Chart.js config (colors, options)
- Memory `project_fifo_fix_53a.md` — context bias multi-lot
