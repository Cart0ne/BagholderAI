# Brief S110 (estemporanea) — grid-regime-backtest — 2026-06-28

## Contesto

BagHolderAI va live a breve con €600 di capitale reale. Prima del deployment
vogliamo rispondere a una domanda che tutti i grid bot operator si pongono ma
nessuno documenta in modo onesto: **come si comporta un grid bot — con parametri
congelati — nei diversi regimi di mercato, confrontato con un semplice hold?**

L'obiettivo NON è ottimizzare. È produrre una **mappa comportamentale** con
numeri reali: previsione qualitativa dichiarata prima, numeri del backtest dopo.
I risultati verranno congelati e poi confrontati con i dati live del mainnet.

Il deliverable finale è sia uno strumento interno (benchmark pre-deployment) sia
la base per un contenuto pubblico (guida/blog post).

Basato su PROJECT_STATE.md e BUSINESS_STATE.md al 2026-06-26.

## Scope

Costruire uno **script di simulazione grid bot** che:
1. Scarica dati storici OHLCV da Binance (via ccxt)
2. Simula il comportamento del nostro grid bot sui dati storici
3. Confronta con hold puro sullo stesso periodo/capitale
4. Produce report con metriche + grafici

**Nessuna modifica al bot reale.** Questo è un progetto read-only: legge i
parametri da `bot_config`, non scrive nulla nel DB di produzione.

## Parametri della simulazione

### Grid bot
- **Leggere i parametri reali da `bot_config`** per BTC/USDT: spacing, livelli,
  buy/sell size, fee. Il simulatore deve usare la stessa logica percentuale del
  grid reale (calibrazione al prezzo di mercato, recalibrate dopo idle).
- **Capitale iniziale:** €250 (equivalente USDT al prezzo del giorno 1)
- **Fee:** usare la fee reale Binance spot (verificare: 0.1% maker/taker
  standard, o il valore attuale in `bot_config`)
- **Setup giorno 1:** il grid "si accende" come un deploy reale — calibra al
  prezzo di apertura, piazza gli ordini virtuali, e comincia a lavorare

### Hold (benchmark)
- Stesso capitale, stesso giorno 1
- Compra tutto al prezzo di apertura del primo giorno
- Non fa nient'altro
- Valore = holdings × prezzo corrente a ogni candela

### Risoluzione candele
- **VERIFICARE** nel codice del bot (`grid_runner`) ogni quanto il bot controlla
  il prezzo in live (il loop interval). Usare quella risoluzione per la
  simulazione, così il comportamento simulato è fedele al reale.
- Se il loop è ad esempio ogni 60 secondi, usare candele da 1 minuto.
  Se è ogni 5 minuti, usare candele da 5 minuti. Eccetera.
- Documentare la scelta nel report.

## Scenari (Fase 1 — solo BTC)

Tre periodi storici, un mese calendario ciascuno:

| Scenario | Periodo proposto | Caratteristica attesa |
|---|---|---|
| **Bearish** | 1–30 giugno 2022 | Discesa ~38% (post Terra/Luna). Quasi nessun rimbalzo significativo |
| **Bullish** | 1–30 novembre 2024 | Salita ~37% (post-elezione Trump). Rally sostenuto con pullback |
| **Laterale** | Agosto o settembre 2023 | Range $25K–$30K, nessun trend direzionale |

**DECISIONE DELEGATA A CC:** per il laterale, verificare dai dati scaricati
quale mese tra agosto e settembre 2023 è più pulitamente range-bound (prezzo di
apertura e chiusura vicini, oscillazioni intramese senza breakout). Scegliere
quello e documentare perché.

**DECISIONE CHE CC DEVE CHIEDERE A MAX:** se i dati mostrano che nessuno dei due
mesi è realmente laterale (es. c'è un trend nascosto >10%), fermarsi e proporre
alternative.

## Output atteso

Per ogni scenario, produrre:

### 1. Grafico prezzo + operazioni
- Grafico a linea (o candlestick) del prezzo nel periodo
- **Marker verdi** dove il grid compra, **marker rossi** dove vende
- Prezzo e timestamp di ogni operazione visibili (tooltip o legenda)
- Il grafico deve rendere visivamente chiaro il comportamento del grid

### 2. Curva equity comparativa
- Due linee sullo stesso grafico: valore portafoglio grid vs valore hold
- Asse X: tempo. Asse Y: valore in USDT
- Evidenziare i punti di incrocio (dove grid supera hold o viceversa)

### 3. Tabella metriche (per scenario)

| Metrica | Grid | Hold |
|---|---|---|
| P&L finale (USDT) | | |
| P&L finale (%) | | |
| Max drawdown (%) | | |
| Numero trade completati | | |
| Skim totale accumulato (USDT) | | |
| Tempo attivo vs dormiente (%) | | |
| Valore unrealized holdings fine periodo | | |

### 4. Tabella riepilogativa (3 scenari a confronto)
Una tabella unica che mostra i risultati dei 3 scenari fianco a fianco,
per vedere a colpo d'occhio dove il grid batte hold e dove perde.

### Formato output
- Grafici: salvare come immagini PNG (matplotlib o plotly)
- Report: un file markdown con le tabelle + i grafici embedded
- Script: riutilizzabile per le fasi successive (SOL, BONK, altri periodi)

## Cosa NON fare

- **NON ottimizzare nulla.** I parametri si congelano, si gira, si guarda.
  Se i risultati sono brutti, si documentano brutti.
- **NON modificare il bot reale**, il DB, o qualsiasi file in `bot/`
- **NON simulare il Trend Follower, Sentinel, Sherpa, o NewsKeeper.** Questo
  backtest riguarda SOLO il grid bot puro.
- **NON inventare parametri.** Leggere da `bot_config` quelli reali di BTC.

## File off-limits

- `bot/` — tutto il runtime, non si tocca
- `bot_config`, `trend_config` — si LEGGONO, non si scrivono
- DB di produzione — nessuna INSERT/UPDATE

## Dove mettere il codice

- Script: `scripts/backtest/` (nuova cartella)
- Output (grafici + report): `audits/backtest/` (nuova cartella)
- NON committare i dati OHLCV scaricati (sono grandi, aggiungerli a .gitignore)

## Task non banale — piano richiesto

Stima: >1h di lavoro. **Prima di scrivere codice, produci un piano in italiano
leggibile da Max** con:
- Struttura dello script (moduli, flusso)
- Come leggi i parametri da bot_config
- Come simuli il loop del grid (pseudo-codice)
- Librerie necessarie (ccxt, matplotlib/plotly, pandas)
- Eventuali dubbi o ambiguità da risolvere

Attendi conferma di Max prima di implementare.

## Espansioni future (NON in scope ora)

- Fase 2: SOL con stessi scenari (dove i dati esistono)
- Fase 3: BONK (storia più corta, dal tardo 2022)
- Fase 4: scenari aggiuntivi (flash crash, bear→bull transition, bull→bear)
- Fase 5: contenuto pubblico (blog post/guida con i risultati)

Queste fasi verranno briefate separatamente se/quando il Board decide.

## Auto-obiezioni

1. **Il grid simulato potrebbe non essere identico al grid reale.** Il bot ha
   logica di recalibrate, idle detection, dust handling, guardie varie. Lo
   script di backtest è una semplificazione. Il rischio è che i numeri simulati
   e i numeri live divergano per ragioni strutturali, non di mercato. Mitigazione:
   CC deve leggere il loop reale del grid (`grid_runner`) e replicare la logica
   di decisione buy/sell il più fedelmente possibile, documentando le
   semplificazioni. Se qualcosa è troppo complesso da simulare (es. recalibrate
   timing esatto), dichiararlo nel report come caveat.

2. **Un mese per scenario potrebbe non essere statisticamente significativo.**
   Un singolo mese di bear non è "tutti i bear." Ma questo non è un paper
   accademico — è un benchmark orientativo. Il valore sta nel pattern (grid
   batte hold nel laterale, perde nel bull, accumula bag nel bear), non nei
   numeri esatti al centesimo. Lo dichiariamo esplicitamente nel report.

3. **I dati storici Binance hanno granularità limitata.** Se il bot live
   controlla il prezzo ogni 30 secondi ma le candele disponibili sono da 1
   minuto, c'è una perdita di informazione. I micro-rimbalzi inframinuto che il
   bot reale catturerebbe vengono persi. Questo potrebbe sottostimare gli skim
   nel laterale. Documentare la risoluzione scelta e il motivo.

## Sequenza

Indipendente da S110c/S110d. **NON è un gate per il mainnet.** Caso 2: cammina
in parallelo. Priorità: dopo S110d (tf-grid-exit-thresholds), prima o in
parallelo con S110c (USDT→USDC migration).
