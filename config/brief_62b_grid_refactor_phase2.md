# Brief 62b — Grid Bot Refactoring Phase 2: Fix 60c + Dust Management

**From:** CEO (Claude, Projects) → CC (Intern)
**Via:** Max (Board)
**Date:** 2026-05-07
**Session:** 62
**Priority:** ALTA — ultimo step prima del clean run di 7 giorni per go/no-go LIVE €100
**Stima:** ~6-8h (1 sessione CC piena)
**Predecessori:** Brief 62a (Phase 1 split) DEPLOYED + 48h clean run validated
**Non iniziare questo brief finché Phase 1 non ha 48h senza anomalie.**

---

## 1. Contesto

Phase 1 ha splittato grid_bot.py in moduli senza cambiare comportamento. I bug noti sono marcati con `# TODO 62a`. Ora li fixiamo dentro la struttura modulare pulita.

Tre fix in questo brief, tutti circoscritti ai moduli creati in Phase 1:

| Fix | Modulo target | Impatto |
|---|---|---|
| 60c — double-call sell pipeline | `sell_pipeline.py` + `grid_bot.py` (loop) | Elimina sell fantasma, state in-memory diventa accurato |
| Phantom audit | `sell_pipeline.py` | Audit solo dopo trade DB riuscito |
| Dust management (Opzione 3) | `dust_handler.py` + `sell_pipeline.py` | Elimina dust residui + converter settimanale |

---

## 2. Fix 60c — Double-call + Atomicity

### 2.1 Root cause (verificata Session 62)

`_execute_percentage_sell` viene chiamato 2 volte ravvicinate (<1s) per lo stesso simbolo. La seconda chiamata fallisce su `log_trade` ("Duplicate trade rejected within 5s") ma le mutazioni di state sono già avvenute:
- `state.holdings -= amount` (riga sell_pipeline.py ~572)
- `state.realized_pnl += pnl`
- `state.daily_realized_pnl += pnl`
- Queue ha già fatto pop

Evidenza: 3 coppie di sell SOL il 7-may (09:28-09:31), 9 audit vs 6 trade reali, 5 drift events.

### 2.2 Fix A — Rendere la sell pipeline atomica

**Principio: state changes DOPO log_trade riuscito, mai prima.**

In `sell_pipeline.py`, la sequenza attuale è:

```
1. Calcola PnL
2. Scrivi audit sell_fifo_detail  ← BUG: scritto anche se trade fallirà
3. Pop dalla queue
4. Aggiorna state (holdings, realized_pnl, daily...)
5. log_trade()  ← se fallisce, state è già corrotto
6. Log messaggio
```

La sequenza corretta:

```
1. Calcola PnL
2. log_trade()  ← PRIMA di tutto
3. SE log_trade riuscito:
   a. Scrivi audit sell_fifo_detail
   b. Pop dalla queue
   c. Aggiorna state
   d. Log messaggio
4. SE log_trade fallito:
   a. Log warning "Trade rejected, rolling back"
   b. NON toccare state, queue, audit
   c. Return None
```

### 2.3 Fix B — Identificare e bloccare il double-call

Il loop in `grid_bot.py` (~riga 758, ex riga 1414) itera `for _ in lots_to_sell`. Due possibili cause del double-call:

**Ipotesi 1:** Il loop chiama `execute_percentage_sell` N volte, ma Strategy A ha reordinato la queue mettendo lo stesso lotto in cima dopo un pop fallito (dust path) → il lotto riappare e viene ritentato.

**Ipotesi 2:** Qualche flusso di self-heal o verify_fifo_queue rebuilda la queue durante il loop di sell, rimettendo il lotto poppato.

**Cosa fare:**
1. Aggiungere un guard nel loop: se `execute_percentage_sell` ritorna None, fermarsi (non continuare a iterare sperando che il prossimo giro funzioni)
2. Aggiungere un idempotency check in `execute_percentage_sell`: se un trade per (symbol, side='sell', amount, price) esiste in DB negli ultimi 5s, return None senza tentare. Non delegare al DB trigger — prevenire client-side.

```python
# In grid_bot.py, loop di sell
for i, _ in enumerate(lots_to_sell):
    result = sell_pipeline.execute_percentage_sell(...)
    if result is None:
        logger.info(f"[{symbol}] Sell #{i+1} returned None, stopping sell loop")
        break  # Non continuare
```

```python
# In sell_pipeline.py, inizio di execute_percentage_sell
def _check_recent_duplicate(trade_logger, symbol, side, amount, price, window_s=5):
    """Client-side idempotency: skip if same trade exists within window."""
    # Query trades table per (symbol, side, amount, price) negli ultimi window_s secondi
    # Return True se duplicato trovato
    ...

# All'inizio di execute_percentage_sell:
if _check_recent_duplicate(trade_logger, symbol, 'sell', amount, price):
    logger.warning(f"[{symbol}] Duplicate sell detected client-side, skipping")
    return None
```

### 2.4 Fix C — verify_fifo_queue dust filter simmetrico

In `fifo_queue.py` (~riga 96), il confronto mem vs db filtra dust solo da db_queue. Aggiungere lo stesso filtro a mem_queue:

```python
# PRIMA (asimmetrico, produce drift spurio):
db_filtered = [lot for lot in db_queue if lot['amount'] > dust_threshold]
# mem_queue NON filtrato

# DOPO (simmetrico):
db_filtered = [lot for lot in db_queue if lot['amount'] > dust_threshold]
mem_filtered = [lot for lot in mem_queue if lot['amount'] > dust_threshold]
# Confrontare mem_filtered vs db_filtered
```

---

## 3. Dust Management (Opzione 3)

Decisione Board Session 60. Due componenti:

### 3.1 Prevenzione — Arrotondamento sell per svuotare posizione

In `sell_pipeline.py`, quando il bot calcola la quantità di sell:

```python
remaining_after_sell = holdings - sell_amount
if remaining_after_sell > 0 and remaining_after_sell < min_order_size:
    # Il residuo sarebbe dust → vendi TUTTO
    sell_amount = holdings
    logger.info(f"[{symbol}] Rounding up sell to avoid dust: {remaining_after_sell} < min_order_size")
```

`min_order_size` = step_size di Binance per il simbolo (es. 0.001 per SOL). Già disponibile nel bot come `self.step_size` o calcolabile da exchange info.

### 3.2 Safety net — Dust converter settimanale

In `dust_handler.py`, aggiungere una funzione che chiama Binance API `/sapi/v1/asset/dust`:

```python
def convert_dust_via_binance(exchange):
    """Weekly dust conversion via Binance Small Assets to BNB.
    
    API: POST /sapi/v1/asset/dust
    Converte asset sotto 0.001 BTC equivalente in BNB.
    """
    # 1. GET /sapi/v1/asset/dust-btc per listare convertibili
    # 2. POST /sapi/v1/asset/dust con asset selezionati
    # 3. Log risultato in bot_events_log (event='dust_conversion', category='maintenance')
```

**Scheduling:** chiamare dal main loop una volta a settimana (es. domenica 03:00 UTC). Guard: controllare `bot_events_log` per ultimo `dust_conversion` event, se < 7 giorni → skip.

**ATTENZIONE:** Questa API funziona SOLO in live trading (endpoint autenticato, muove asset reali). In paper trading, implementare solo la logica + log "would convert X assets" senza chiamata reale. Aggiungere flag `PAPER_MODE` check.

---

## 4. Logging migliorato per dust

In `dust_handler.py`, quando un lotto dust viene rimosso dalla queue:

```python
# PRIMA (bug attuale): pop silenzioso, niente traccia in DB
# DOPO:
log_event(
    symbol=symbol,
    event='dust_lot_removed',
    severity='info',
    category='integrity',
    message=f"Dust lot removed: {amount} units (${notional:.4f})",
    details={'amount': amount, 'price': price, 'notional': notional, 'reason': reason}
)
```

---

## 5. Test e verifica

### 5.1 Replay storico

Dopo il deploy, verificare su dati SOL 7-may 07:28-07:33 UTC:
- Query audit `sell_fifo_detail`: devono essere 6, non 9
- Query drift `fifo_drift_detected`: count deve scendere drasticamente
- `state.realized_pnl` deve allinearsi a somma `trades.realized_pnl`

### 5.2 Baseline continuity

Stesse query del Brief 62a §5. I trade count e realized_pnl devono continuare a crescere coerentemente. La somma realized_pnl potrebbe cambiare leggermente (fix 60c elimina il bias in-memory), ma i trade in DB NON devono cambiare.

### 5.3 Dust test

Creare manualmente una situazione con lotto dust (SOL, <0.001 units) e verificare:
- Il lotto viene arrotondato nella sell (§3.1)
- Se sfugge, il converter lo identifica (§3.2, log-only in paper mode)
- L'evento `dust_lot_removed` appare in `bot_events_log` (§4)

---

## 6. Pacchetto Review Phase 2

Come Phase 1, preparare `/review/phase2/`:

```
/review/phase2/
├── README.md
├── before/           # File post-Phase 1 (pre-fix)
│   ├── sell_pipeline.py
│   ├── dust_handler.py
│   ├── fifo_queue.py
│   └── grid_bot.py
└── after/            # File post-fix
    ├── sell_pipeline.py
    ├── dust_handler.py
    ├── fifo_queue.py
    └── grid_bot.py
```

README deve specificare: "Phase 2 fixes 3 known bugs. Reviewer should verify: (1) sell pipeline is now atomic — state changes only after successful log_trade, (2) dust lots are logged and prevented, (3) FIFO queue comparison is symmetric, (4) no new side-effects introduced."

---

## 7. Deploy e monitoring

1. Push a main
2. `git pull` su Mac Mini
3. Test import: `python -c "from bot.strategies.grid_bot import GridBot; print('import OK')"`
4. Restart orchestrator
5. Monitoring 2h → 48h → 7 giorni clean run
6. Go/no-go LIVE €100 dopo 7 giorni puliti (~20 maggio)

---

## 8. Cosa NON fare

- NON toccare `buy_pipeline.py` o `state_manager.py` (fuori scope)
- NON cambiare la struttura dei moduli Phase 1
- NON aggiungere feature nuove (es. trailing stop improvements)
- NON modificare il DB trigger anti-duplicato di Session 15 — resta come safety net

---

## 9. Rollback

```bash
git revert <commit>
git push origin main
# Mac Mini:
cd /Volumes/Archivio/bagholderai && git pull
# restart orchestrator
```

---

Buon lavoro. Dopo questo brief, grid_bot è pronto per i soldi veri.

— CEO, BagHolderAI
