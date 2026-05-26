# Brief 86b — Regime overlay sui grafici admin.html

**Autore:** CEO, 2026-05-26  
**Priorità:** MEDIA  
**Stima:** ~1.5h  
**Scope:** admin.html — solo JS/CSS, zero backend  

---

## Contesto

La pagina `/admin` (admin.html) ha 3 grafici Chart.js che mostrano dati Sentinel e Sherpa:

1. **TREND — SENTINEL SIGNALS × BTC PRICE** (risk score + opportunity score + prezzo BTC)
2. **SENTINEL FAST (RISK + OPP) VS SHERPA PROPOSED** (linee Sentinel fast + proposte Sherpa per-coin)
3. **PARAMETERS HISTORY** (buy_pct, sell_pct, idle_reentry_hours per BTC/SOL/BONK)

Manca il contesto macro: il regime Sentinel (fear/greed/neutral/extreme_fear/extreme_greed) che viene dal **slow loop** (4h cadenza). Il Board vuole bande colorate di sfondo sui grafici per vedere a colpo d'occhio in che regime si trovava il sistema in ogni momento.

---

## Task — Aggiungere bande colorate di regime a tutti e 3 i grafici

### Fonte dati

```sql
SELECT created_at, regime
FROM sentinel_scores
WHERE score_type = 'slow'
ORDER BY created_at ASC
```

Il regime cambia raramente (3 transizioni in 8 giorni nell'ultimo dataset). Ogni riga definisce l'inizio di un periodo; il regime vale fino alla riga successiva.

### Fetch

Un **unico fetch** al caricamento della pagina (e al cambio del range selector 12h/24h/7d/1m). I dati sono condivisi tra tutti e 3 i grafici — non fare 3 query separate.

Filtro temporale: usare la stessa finestra del `currentRangeHours` globale già presente in admin.html.

### Rendering

Usare il **Chart.js annotation plugin** (`chartjs-plugin-annotation`) per disegnare box rettangolari di sfondo. Se il plugin non è già caricato in admin.html, aggiungerlo via CDN:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.1.0/chartjs-plugin-annotation.min.js"></script>
```

Ogni periodo di regime diventa un box annotation:
```js
{
  type: 'box',
  xMin: regimeStartTimestamp,
  xMax: regimeEndTimestamp,  // o undefined per "fino a ora"
  yMin: 'min',
  yMax: 'max',
  backgroundColor: regimeColor,
  borderWidth: 0,
  drawTime: 'beforeDatasetsDraw'  // dietro le linee
}
```

### Colori

| Regime | Colore sfondo (rgba, molto trasparente) |
|---|---|
| `extreme_fear` | `rgba(226, 75, 74, 0.10)` — rosso |
| `fear` | `rgba(226, 75, 74, 0.06)` — rosso chiaro |
| `neutral` | `rgba(239, 159, 39, 0.06)` — giallo/amber |
| `greed` | `rgba(29, 158, 117, 0.06)` — verde chiaro |
| `extreme_greed` | `rgba(29, 158, 117, 0.10)` — verde |

L'opacità deve essere bassa perché le bande sono sfondo — non devono competere visivamente con le linee dati.

### Legenda

Aggiungere una riga di legenda sotto il grafico 1 (TREND):
```
◼ extreme_fear  ◼ fear  ◼ neutral  ◼ greed  ◼ extreme_greed
```
Colori pieni (non trasparenti) per la legenda. Stile monospace, font-size 11px, coerente con le legende Chart.js esistenti. Non serve ripeterla sotto ogni grafico — una sola volta basta.

### Applicazione ai 3 grafici

I 3 grafici usano Chart.js con asse X temporale. Per ognuno:
1. Dopo il fetch dei dati regime, costruire l'array di annotation box
2. Iniettarli nelle options del chart via `chart.options.plugins.annotation.annotations`
3. Chiamare `chart.update()`

Se il grafico viene distrutto e ricreato al cambio di range (pattern comune in admin.html), passare le annotations nella config iniziale.

---

## Decisioni delegate a CC

- Come integrare il fetch regime con il flusso di dati esistente in admin.html (probabile: aggiungere alla funzione `bootstrap()` o equivalente)
- Se usare `chartjs-plugin-annotation` o disegnare manualmente con un plugin custom (annotation è più pulito)
- Exact positioning nell'array annotations se i grafici hanno già altre annotations

## Decisioni che CC DEVE chiedere

- Se un grafico usa un asse X diverso (non temporale) → chiedere prima di adattare
- Se il CDN annotation plugin ha conflitti di versione con la Chart.js già caricata

---

## Test

- [ ] Fetch `sentinel_scores WHERE score_type='slow'` restituisce dati
- [ ] Grafico 1 (Sentinel × BTC) mostra bande colorate di sfondo coerenti con i regime periods
- [ ] Grafico 2 (Sentinel Fast vs Sherpa) mostra le stesse bande
- [ ] Grafico 3 (Parameters History) mostra le stesse bande
- [ ] Cambio range selector (12h → 7d) → bande si aggiornano correttamente
- [ ] Con zero righe regime nel range → nessuna banda, nessun errore
- [ ] Legenda regime visibile sotto il primo grafico
- [ ] Le bande sono dietro le linee dati (drawTime: beforeDatasetsDraw)

---

## Commit

```
feat(admin): regime background bands on Sentinel/Sherpa/Params charts
```

---

## Roadmap impact

None.
