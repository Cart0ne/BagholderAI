# Brief 80a — Brain Analysis: Sentinel + Sherpa + TF Readiness

**Data di riferimento PROJECT_STATE.md:** 2026-05-18 (S79 chiusa)  
**Sessione target:** S80, da eseguire il 21 maggio 2026 (mercoledì)  
**Tipo:** Analisi dati — nessun codice da shippare, nessun brief tecnico.  
**Tempo stimato:** 2-3 ore  

---

## Contesto

Siamo allo step 3 della sequenza Sentinel-first (osservazione 5-7 giorni). Al 21 maggio Sprint 2 slow loop avrà ~6.5 giorni di dati. Il Board vuole decidere se:
- Sherpa aggiunge valore reale o solo complessità
- Sentinel Sprint 2 ha migliorato il timing rispetto a Sprint 1
- Siamo pronti per lo step 4 (Sherpa LIVE su testnet, sell_pct prima) o servono modifiche
- Sprint 3 (online sentiment) diventa prioritario

Il mercato degli ultimi 11 giorni è stato bearish — il portfolio è passato da circa +2% a circa -10%. Questo è importante: stiamo valutando il cervello in condizioni di stress, non di noia.

---

## Prerequisito — Piano in italiano

Questo brief è complesso. CC DEVE produrre PRIMA un piano di lavoro in italiano leggibile da Max, che descrive:
1. Quali tabelle interroga e quali colonne usa
2. Come costruisce il dataset prezzi (interni + klines)
3. Quale metodo usa per il counterfactual Sherpa
4. Output atteso per ogni blocco

Max approva il piano PRIMA che CC scriva codice o query.

---

## Blocco 0 — Costruzione dataset

**Obiettivo:** assemblare la base dati unificata prima di qualsiasi analisi.

### 0a. Inventario dati interni
Verificare quali tabelle contengono prezzi e con quale granularità:
- `sentinel_scores`: ha colonne prezzo? Quale granularità effettiva?
- `sherpa_proposals`: cosa contiene esattamente ogni riga? (parametro proposto, valore corrente, valore suggerito, timestamp)
- `trades`: trade Grid effettivi con prezzo e timestamp
- `trend_scans`, `counterfactual_log`: dati TF storici

Query `information_schema.columns` per ogni tabella coinvolta. Documentare lo schema nel report.

### 0b. Prezzi Binance retroattivi
Scaricare candele klines da Binance API (`/api/v3/klines`) per:
- BTC/USDT, SOL/USDT, BONK/USDT
- Periodo: 2026-05-05 → 2026-05-21 (copre tutto il dataset)
- Granularità: 1h (sufficiente per correlare con proposte Sherpa)
- Opzionale: 5m per finestra attorno ai cambi regime Sentinel (Blocco 3)

### 0c. Dataset unificato
Produrre una timeline unificata per coin: timestamp → prezzo → score Sentinel (fast+slow) → proposta Sherpa → trade Grid effettivo. Questo è il dataset su cui girano tutti i blocchi successivi.

---

## Blocco 1 — Caratterizzazione del periodo

**Obiettivo:** capire in che condizioni stiamo valutando il cervello.

Per ogni coin (BTC, SOL, BONK):
- Range di prezzo (min, max, % change totale)
- Volatilità media giornaliera
- Drawdown massimo nel periodo
- Numero e timing dei movimenti significativi (>3% in 24h)
- Eventuali eventi macro noti (se correlano con movimenti improvvisi)

**Output:** 1 paragrafo per coin + 1 tabella riassuntiva. Risponde alla domanda: "quanto sono affidabili le conclusioni dei blocchi successivi dato questo contesto?"

---

## Blocco 2 — Sherpa Counterfactual

**Obiettivo:** rispondere a "se avessimo applicato le proposte Sherpa, il Grid bot avrebbe performato meglio o peggio?"

### 2a. Inventario proposte
- Quante proposte ha generato Sherpa in 11 giorni? Per quale parametro (sell_pct, buy_pct, altro)?
- Frequenza: distribuzione temporale (costante, a raffica, solo in certi momenti?)
- Ampiezza: i cambiamenti proposti sono piccoli aggiustamenti o oscillazioni grandi?

### 2b. Counterfactual vs realtà
Per ogni proposta Sherpa:
- Cosa avrebbe cambiato nel comportamento del Grid bot?
- Con i prezzi reali (klines), il bot avrebbe venduto prima/dopo? Comprato di più/meno?
- Stima P&L con parametri Sherpa vs P&L reale con parametri Board statici

### 2c. Baseline "stupida"
Calcolare: cosa sarebbe successo con parametri fissi per tutto il periodo? Nessun Sentinel, nessun Sherpa, solo i parametri Board iniziali da `bot_config`. Se la baseline statica performa uguale o meglio, il cervello non sta aggiungendo valore — sta aggiungendo complessità.

### 2d. Caveat
Dichiarare esplicitamente:
- Quanti giorni di dati coprono la simulazione
- Se il periodo è rappresentativo o eccezionale
- Margine di incertezza stimato
- Cosa NON si può concludere da questi dati

---

## Blocco 3 — Sentinel Timing

**Obiettivo:** il slow loop (Sprint 2) anticipa i movimenti di prezzo o li conferma a posteriori?

### 3a. Sprint 1 vs Sprint 2
Incrociare i timestamp dei cambi di risk score Sentinel con i movimenti di prezzo:
- Per ogni cambio significativo di risk score: cosa aveva fatto il prezzo nelle 2h precedenti? Cosa ha fatto nelle 2h successive?
- Sprint 1 (fast loop) vs Sprint 2 (slow loop): quale reagisce prima?
- Il slow loop ha mai anticipato un movimento che il fast loop ha visto in ritardo?

### 3b. Regime detection
Analizzare i cambi di regime (`fear` / `neutral` / `greed` o equivalenti):
- Quanti cambi di regime in 6.5 giorni?
- Sono correlati con movimenti di prezzo reali o sono rumore?
- Il regime attuale (`fear`) è giustificato dai dati di mercato?

---

## Blocco 4 — Stabilità Sherpa (Flicker Analysis)

**Obiettivo:** Sherpa è stabile o oscilla troppo?

- Contare quante volte Sherpa ha cambiato proposta per lo stesso parametro in meno di 4h / 8h / 24h
- Identificare pattern di flicker: propone A → torna a B → torna a A
- Confrontare flicker pre e post attivazione Sprint 2 (se ci sono dati sufficienti)
- Se flicker è alto: il passaggio a testnet LIVE è prematuro

---

## Output atteso

Un report unico per il Board, in inglese (va nel repo come `report_for_CEO/`), che contenga:

1. **Executive summary** (5 righe max): Sherpa aggiunge valore sì/no, Sentinel migliora il timing sì/no, raccomandazione go/no-go step 4
2. **Dati e metodo** (Blocco 0 + 1): dataset usato, copertura, limitazioni, contesto mercato
3. **Sherpa analysis** (Blocco 2): inventario, counterfactual, baseline, conclusioni con incertezza
4. **Sentinel timing** (Blocco 3): Sprint 1 vs 2, regime detection quality
5. **Sherpa stability** (Blocco 4): flicker metrics, raccomandazione
6. **Raccomandazione finale**: step 4 go / step 4 con modifiche / raccogliere più dati / modifiche architetturali necessarie

Formato: markdown, salvato in `report_for_CEO/s80_brain_analysis.md`.
Lunghezza target: max 3 pagine leggibili, non un paper accademico. Se serve supporto numerico, usare tabelle inline.

Approccio ai numeri: **incertezza esplicita**. Non "Sherpa migliora del 12%" ma "su N giorni in condizioni bearish, la differenza stimata è X con caveat Y." Niente numeri fabbricati.

---

## Decisioni delegate a CC

- Scelta della granularità klines (1h proposta, CC può ridurre a 5m se serve per Blocco 3)
- Metodo di simulazione counterfactual (CC propone nel piano, Max approva)
- Struttura delle query Supabase
- Formato tabelle e grafici nel report

## Decisioni che CC DEVE chiedere a Max

- Se i dati sono insufficienti per uno dei blocchi: FERMARSI e chiedere, non inventare conclusioni
- Se il counterfactual richiede assunzioni significative (es. "assumo che il bot avrebbe eseguito il trade entro 5 minuti dalla proposta"): chiedere conferma dell'assunzione
- Se emerge un problema architetturale non previsto: segnalare prima di proporre fix

## Vincoli

- **Nessun codice da shippare.** Questa è una sessione di sola analisi.
- **Non modificare nessuna tabella Supabase** — solo SELECT.
- **Non toccare il bot, i config, i file del repo.**
- **Se serve scrivere script di analisi:** salvarli in `analysis/` (gitignored o da gitignorare), non in `bot/` o `db/`.
- **TF post-riattivazione:** NON analizzare. Con ~3 giorni al 21 maggio e 0 counterfactual rows, non c'è materiale. Menzionare nel report come gap noto.
