# Brief S70 — Deploy avg-cost trading + TRUNCATE + restart

**From:** CEO (Claude, Projects) → CC (Intern)
**Via:** Max (Board)
**Date:** 2026-05-09
**Session:** 70
**Priority:** CRITICA — Board approval ricevuto, bot deve girare stasera
**Riferimento stato:** PROJECT_STATE.md aggiornato 2026-05-09 (S69 chiusura, commit `0b27a88`)
**Riferimento brief originale:** `config/brief_69a_avg_cost_trading_truncate_restart.md`
**Stima:** 4–6h sviluppo + restart (obiettivo: bot live entro sera)

---

## 0. Contesto

Board ha approvato il deploy del brief 69a. Vincolo temporale: Max vuole il bot in testnet stasera (16:20 CET = ~14:20 UTC, finestra ~5h).

Il brief 69a originale stima 10–14h. Per rispettare la deadline, lo scope è **diviso in due fasi**:

- **FASE 1 (questa sessione):** core avg-cost trading + TRUNCATE + restart. Il bot parte.
- **FASE 2 (S71, post-24h observation):** cleanup completo (DROP COLUMN DB, rimozione file, fixed mode via).

---

## 1. FASE 1 — Scope obbligatorio (questa sessione)

### 1.1 Riscrittura trigger sell in `bot/grid/grid_bot.py`

**Cosa cambia:** il bot oggi decide se vendere iterando `_pct_open_positions` e confrontando `current_price >= lot["price"] * (1 + threshold_pct / 100)` (per-lot FIFO). Post-fix: unico confronto su `state.avg_buy_price`.

**Logica nuova:**
```
IF state.holdings > 0 AND current_price >= state.avg_buy_price * (1 + sell_pct / 100):
    sell_amount = capital_per_trade / current_price
    sell_amount = min(sell_amount, state.holdings)  # non vendere più di quanto abbiamo
    → esegui sell
```

Per TF/force_liquidate (stop-loss, trailing, etc.): vendere tutto `state.holdings`. Ma TF è OFF — questo path non è urgente, basta che non crashi.

**Cosa rimuovere dal hot path:**
- La chiamata a `verify_fifo_queue()` (riga ~730 area)
- L'iterazione `for _ in lots_to_sell` — diventa un singolo sell
- Il reorder queue `sell_ids = {id(lot) for lot in lots_to_sell}` etc.

**Cosa lasciare per ora (FASE 2):**
- `_pct_open_positions` come attributo può restare (non usato, non chiamato)
- `fifo_queue.py` come file può restare (non importato nel hot path se rimuovi `verify_fifo_queue`)
- Il codice fixed mode può restare (non eseguito, `grid_mode='percentage'` su tutti i record)

### 1.2 Riscrittura sell_pipeline (se necessario)

`sell_pipeline.py` già usa avg-cost per il realized_pnl (post-S66). Verificare che la funzione `_execute_percentage_sell` accetti il nuovo pattern (singolo sell di `sell_amount` calcolato dal chiamante, non più "pop lot dalla queue").

**Attenzione:** `_execute_percentage_sell` oggi prende `lot` come argomento e usa `lot["amount"]` e `lot["price"]`. Dovrà accettare un `sell_amount` calcolato e usare `state.avg_buy_price` come costo base. Il guard S68a (`price < bot.state.avg_buy_price`) resta valido — anzi diventa ridondante col nuovo trigger, ma lascialo come safety net.

### 1.3 Rimozione init FIFO da state_manager

`state_manager.py` fa boot-time restore che include la ricostruzione della FIFO queue da DB. Questa init non serve più per il trading. Due opzioni:

- **(a) Rimuovere la funzione** — pulito ma più invasivo
- **(b) Lasciarla ma non chiamarla** — `grid_bot.py` smette di chiamare `init_percentage_state_from_db()` / `restore_state_from_db()` che rebuilda la queue

**Decisione delegata a CC:** scegli l'opzione che minimizza le righe toccate e il rischio di regressione. L'importante è che al boot il bot carichi `avg_buy_price` e `holdings` dal DB (o da `bot_state_snapshots`) senza ricostruire la queue FIFO.

### 1.4 Apply 68b sul Mac Mini

Il refactor 68b (`bot/strategies/` → `bot/grid/`) è già su GitHub (commit `39e05b7`). Il Mac Mini è su `a8e91a0`. Al momento del deploy:

```
# Sul Mac Mini
cd /Volumes/Archivio/bagholderai
git pull --ff-only
```

Questo porta sia 68b (folder rename) sia S69 (dashboard cleanup) sia il codice S70.

### 1.5 TRUNCATE baseline

Dopo aver pushato il codice e prima di fare `git pull` + restart sul Mac Mini:

**DB cleanup (Supabase):**
```sql
DELETE FROM trades WHERE config_version = 'v3';
DELETE FROM reserve_ledger;
DELETE FROM daily_pnl;
DELETE FROM bot_state_snapshots;
DELETE FROM bot_events_log;
```

**Perché DELETE e non TRUNCATE:** RLS attivo, TRUNCATE richiede owner. DELETE funziona con service_role.

### 1.6 Restart bot

```bash
# Sul Mac Mini (Max esegue)
# 1. Stop bot
kill <PID orchestrator 96199>

# 2. Git pull
cd /Volumes/Archivio/bagholderai
source venv/bin/activate
git pull --ff-only

# 3. Restart
ENABLE_TF=false ENABLE_SENTINEL=false ENABLE_SHERPA=false \
python3.13 -m bot.orchestrator
```

### 1.7 Test

**Prima del deploy:**
- Test esistenti `test_accounting_avg_cost.py` devono restare verdi (8/8)
- Aggiungere almeno 1 test nuovo: sell trigger su avg_buy_price (non su lot price)
- Astro build pulito (`npm run build` nella cartella `web_astro/`)

---

## 2. Decisioni delegate a CC

- Come refactorare la firma di `_execute_percentage_sell` (accettare amount calcolato vs lot dict)
- Come gestire `state_manager.py` boot (opzione a vs b, §1.3)
- Ordine dei commit (1 grande o 2-3 incrementali — preferire incrementali con test verdi a ogni step)

## 3. Decisioni che CC DEVE chiedere a Max

- Qualsiasi modifica a tabelle DB oltre i DELETE della §1.5
- Qualsiasi modifica al comportamento del buy (buy_pipeline non va toccato)
- Se emerge un bug bloccante che richiede più di 1h di investigazione → fermarsi e riportare

## 4. Vincoli

- **NON toccare:** `buy_pipeline.py` (la logica buy è corretta e stabile)
- **NON aggiungere colonne** a nessuna tabella
- **NON fare DROP COLUMN** (quello è FASE 2, S71)
- **NON cancellare file** (`fifo_queue.py`, codice fixed mode — cleanup è FASE 2)
- **Python 3.13**, `source venv/bin/activate`
- **Push diretto su main**, niente PR
- **Mac Mini:** Max gestisce il deploy fisico (stop/pull/restart)

## 5. Output atteso a fine sessione

1. `grid_bot.py` con trigger sell su `avg_buy_price` (non per-lot)
2. `sell_pipeline.py` adattato al nuovo pattern (se serve)
3. `verify_fifo_queue()` non chiamato nel hot path
4. Test 9/9+ verdi (8 esistenti + almeno 1 nuovo)
5. Astro build pulito
6. Commit pushato su main
7. DB TRUNCATE eseguito (CEO via Supabase MCP)
8. Max fa git pull + restart sul Mac Mini
9. Report per CEO con conferma "fix shipped, test verdi, bot pronto per restart"
10. `PROJECT_STATE.md` aggiornato

## 6. FASE 2 — scope S71 (post-24h observation)

Queste cose le facciamo DOPO che il bot ha girato 24h pulito:

- DROP COLUMN DB: `grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`, `reserve_floor_pct` da `bot_config`
- Rimozione `fifo_queue.py`
- Rimozione codice fixed mode da `grid_bot.py` (~200 righe)
- Rimozione `_pct_open_positions` e `init_percentage_state_from_db`
- Pulizia `state_manager.py` (boot restore senza FIFO)
- Rimozione `test_verify_fifo_queue.py`
- Reconciliation gate nightly (brief 67a Step 5)

## 7. Roadmap impact

- **Pre-live gate "avg-cost trading"**: passa da 🔲 a ✅ se il deploy va a buon fine
- **Target go-live €100 mainnet**: 21–24 maggio confermato. Se bot parte stasera + 24h clean, siamo in linea
- **Reconciliation gate nightly**: S71 (post-24h observation)

---

*Brief S70 — CEO, 2026-05-09. Board approval ricevuto. Bot deve girare stasera.*
