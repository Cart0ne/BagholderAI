# Brief 66a — Operation Clean Slate

**Da:** CEO (Claude, Projects) — Sessione 66, 2026-05-08
**A:** CC (Claude Code, Intern)
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-08 (S65 chiusura)
**Priorità:** 🔴 GATING per go-live €100
**Stima totale:** 6-8h
**Prerequisito:** CC produce PRIMA un piano in italiano leggibile da Max, da approvare prima di scrivere codice.

---

## Contesto

Il Board (Max) ha deciso di chiudere l'era paper trading e ripartire da zero su Binance testnet. Motivazione: l'eredità di 458 sell fossili, avg_buy_price accumulato con errore, restart che perdono stato e dust residuo rendono ogni fix un rattoppo su dati sporchi. Meglio fixare le formule a bot fermo, collegare al testnet, e ripartire dal trade 1 con verifica continua.

Questo brief **sostituisce e assorbe**: brief 65c (testnet), brief 60b respec (avg-cost), la parte "dust prevention" di brief 62b, e il reset procedure.

---

## Decisioni già prese (Board + CEO)

- **Strict-FIFO abbandonato** come metodo contabile. Il bot usa avg-cost, Binance usa avg-cost. Il fix è fare avg-cost correttamente, non cambiare metodo.
- **Reset totale dello stato**: niente liquidazione simulata. Snapshot → azzeramento DB → restart da zero.
- **Il dust storico muore col reset.** Il dust futuro va prevenuto nel codice prima di ripartire.
- **Reconciliation gate attivo dal giorno 1**: script notturno che verifica l'identità contabile.

## Decisioni delegate a CC

- Scelta implementativa su come resettare le tabelle DB (TRUNCATE vs soft-delete con flag, vs nuova config_version). Proponi nel piano.
- Struttura dello snapshot pre-reset (quali tabelle, formato).
- Come gestire le chiavi API testnet (env var, settings.py, vault).
- Ordine interno dei fix (puoi riorganizzare i sotto-task se c'è un ordine più logico).

## Decisioni che CC DEVE chiedere

- Se durante il fix avg-cost scopri che il bug è in un file/funzione non elencato qui, FERMA e chiedi.
- Se il path testnet in `exchange.py` richiede modifiche oltre la rimozione del bypass (es. endpoint diversi per nuove API), FERMA e chiedi.
- Se il reset DB impatta tabelle non elencate (es. `sentinel_scans`, `sherpa_proposals`), FERMA e chiedi.
- Qualsiasi modifica che tocca Sentinel o Sherpa: CHIEDI.

---

## Sequenza di esecuzione

### Step 0 — Snapshot + Stop

1. **Snapshot completo** dello stato attuale:
   - Export delle tabelle chiave: `trades`, `bot_config`, `trend_config`, `reserve_ledger`, `bot_state_snapshots`, `daily_pnl`
   - Include: P&L attuale (Total, Realized DB, Unrealized), posizioni aperte per coin, cash balance
   - Formato: un file `.md` o `.json` leggibile, salvato in `audits/` (gitignored)
   - Questo diventa materiale narrativo per il Volume 3
2. **Stop orchestrator** sul Mac Mini

### Step 1 — Fix formula avg-cost (ex brief 60b respec)

**Il bug:** il bot scrive `realized_pnl` usando `avg_buy_price`, ma l'implementazione non chiude l'identità contabile `Realized + Unrealized = Total P&L`. Bias +28% su Grid.

**La formula corretta (e unica) per avg-cost:**

Quando il bot compra:
```
new_avg_cost = (old_avg_cost × old_qty + buy_price × buy_qty) / (old_qty + buy_qty)
```

Quando il bot vende:
```
realized_pnl = (sell_price - avg_cost) × sell_qty
# avg_cost NON cambia dopo una vendita
```

**File principali da toccare:**
- `bot/strategies/sell_pipeline.py` — dove viene calcolato `realized_pnl`
- `bot/strategies/grid_bot.py` — dove viene aggiornato `avg_buy_price`
- `bot/strategies/buy_pipeline.py` — verificare che il buy aggiorni la media correttamente

**Criteri di accettazione:**
- Su una sequenza di N buy e M sell simulati, `Realized + Unrealized = Total P&L` chiude al centesimo
- avg_cost NON si aggiorna mai su una sell
- avg_cost si aggiorna correttamente su ogni buy (media ponderata)
- Test unitario con almeno 3 scenari: (a) buy-sell semplice, (b) multi-buy poi sell parziale, (c) buy-sell-buy-sell alternati

### Step 2 — Prevenzione dust nelle sell (ex pezzo di brief 62b)

**Il problema:** quando il bot vende una percentuale di una posizione, il residuo può essere sotto il minimum order size di Binance → dust non vendibile.

**Il fix:** nel sell pipeline, se dopo una vendita il residuo sarebbe sotto il minimum order size di Binance, arrotondare la quantità venduta per svuotare la posizione interamente.

**File principali:**
- `bot/strategies/sell_pipeline.py`
- `bot/strategies/dust_handler.py`
- `bot/exchange.py` — per recuperare i minimum order size (su testnet: verificare che i filtri siano disponibili)

**Criteri di accettazione:**
- Nessuna sell può lasciare un residuo sotto il minimum order size
- Se il residuo sarebbe sotto soglia, la sell diventa "sell all"
- Test unitario con caso limite: posizione da $1.50, minimum order $1.00, sell 60% → deve vendere tutto

### Step 3 — Riattivare path Binance testnet (ex brief 65c)

**Il problema:** `config/settings.py:21` ha già `TESTNET=true`, ma `bot/exchange.py:8-11` bypassa il path con un commento legacy ("We don't use Binance testnet because... paper trading simulates fills internally").

**Il fix:**
1. Rimuovere il bypass in `exchange.py:8-11`
2. Configurare chiavi API testnet (Max le genera su `testnet.binance.vision`)
3. Verificare che tutti gli endpoint usati dal bot esistano sul testnet (ticker, order, account, trades history)
4. Testare un singolo buy + sell manualmente prima di collegare il bot

**Criteri di accettazione:**
- Il bot piazza ordini reali su `testnet.binance.vision`
- Ogni sell produce un `realized_pnl` sia nel nostro DB sia nella trade history di Binance
- I due numeri sono confrontabili (stesso metodo, stesso ordine di grandezza)

**⚠️ ATTENZIONE:** il testnet Binance potrebbe non avere tutte le coin che usiamo. Verificare la lista spot disponibile. Se SOL o BONK non ci sono, il Grid parte solo con BTC (e ne discutiamo).

### Step 4 — Reset DB + Restart

1. **Reset delle tabelle di trading:**
   - `trades` — svuotare (o marcare con un epoch flag, a discrezione CC)
   - `reserve_ledger` — svuotare
   - `bot_state_snapshots` — svuotare
   - `bot_events_log` — svuotare (oppure mantenere come log storico, proponi)
   - `daily_pnl` — svuotare
   - `bot_config` — NON svuotare, riconfigurare con budget iniziale fresco
   - `trend_config` — NON svuotare, mantenere configurazione attuale
2. **Sentinel e Sherpa:**
   - `sentinel_scans` — svuotare (ripartono da zero, tanto i dati precedenti sono da calibrazione sbagliata)
   - `sherpa_proposals` — svuotare
   - `sherpa_parameter_history` — svuotare
   - Sentinel: ricalibrazione dei bug S63 (speed_of_fall floor + opportunity thresholds) VA FATTA ORA, prima del restart. Non ha più senso preservare il DRY_RUN con dati ciechi.
3. **Budget:** $100 USDT (paper/testnet). Cash = $100, posizioni = 0.
4. **Restart orchestrator** con tutti i processi: Grid + TF + Sentinel + Sherpa (DRY_RUN)

### Step 5 — Reconciliation gate (dal giorno 1)

**Script notturno** (cron sul Mac Mini, es. 04:30 UTC, dopo db_maintenance):
1. Legge tutte le `trades` dal DB
2. Calcola `Realized_avg_cost` sommando tutti i `realized_pnl`
3. Calcola `Unrealized` come `sum(current_price × qty - avg_cost × qty)` per ogni posizione aperta
4. Calcola `Total P&L` come `Net Worth - budget`
5. Confronta: `|Realized + Unrealized - Total P&L| < $0.01`
6. Se non chiude → alert Telegram a Max con i numeri

**Criteri di accettazione:**
- Lo script gira automaticamente ogni notte
- Alert solo se gap > $0.01 (no spam)
- Il primo run su stato vuoto (trade 0) deve passare senza alert

---

## Output atteso a fine sessione CC

1. ✅ Snapshot dello stato pre-reset (in `audits/`)
2. ✅ Formula avg-cost fixata con test unitari
3. ✅ Dust prevention nel sell pipeline con test
4. ✅ Path testnet riattivato (ma non ancora collegato — serve che Max generi le chiavi API)
5. ✅ Script di reset DB pronto (da eseguire dopo che Max conferma le chiavi)
6. ✅ Reconciliation gate script pronto
7. ✅ PROJECT_STATE.md e BUSINESS_STATE.md aggiornati
8. ✅ Piano di ricalibrazione Sentinel (almeno: floor su speed_of_fall + soglie opportunity)

## Vincoli — cosa NON cambiare

- **Logica di buy/sell dei Grid bot** (trigger, percentuali, greed-decay) — tocchiamo SOLO la contabilità
- **Logica TF** (scanner, classifier, allocator) — non in scope
- **Architettura Sentinel/Sherpa** — tocchiamo solo la calibrazione dei parametri, non la struttura
- **Frontend/dashboard** — non in scope. I numeri si aggiustano alla fonte (bot), le dashboard già leggono dal DB
- **Nessun rinomina** (`strategies/` → `grid/`, `manual` → `grid`) — non ora

---

*"Sometimes the bravest thing a CEO can do is admit the engine needs rebuilding, not another oil change." — CEO, Session 66*
