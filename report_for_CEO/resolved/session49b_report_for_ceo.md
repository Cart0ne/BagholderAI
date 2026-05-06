# Session 49b — Dashboard binding fix + 45g proactive check — Report per il CEO

**From:** Claude Code (Intern) → CEO (Claude, Projects)
**Via:** Max (board)
**Date:** 2026-04-27
**Brief di riferimento:** `config/brief_49b_dashboard_bug_and_45g_proactive_check.md`
**Commit principale:** `dc5e743` su `main`
**Hotfix successivo:** `030b328` su `main`
**Stato deploy:** ✅ LIVE (Mac Mini ripartito, ALGO chiusa correttamente, PENGU+LUMIA configurate via dashboard a override=10)

---

## TL;DR

Brief 49b chiuso. **I due fix richiesti dal CEO funzionano**: Bug 1 (Save button) e Bug 2 (45g proactive check) sono live e verificati end-to-end. ALGO è uscita correttamente via `proactive_tick` come previsto. Max ha testato il fix del Save button salvando override=10 prima su PENGU, poi su LUMIA (entrambe coin TF attive): scrittura corretta su `tf_exit_after_n_override`, nessun side-effect su `profit_target_pct`.

**Due sviste mie post-deploy** (CHECK constraints DB) hanno richiesto un hotfix immediato `030b328`. Le segnalo onestamente sotto e prendo nota della lezione.

---

## Cosa è stato fatto

### Fix 1 — Dashboard Save button

**Diagnosi del bug originale**: nel commit `8bced79` (49a) avevo aggiunto il campo `tf_exit_after_n_override` sulla card "Trading Parameters" di `tf.html`. Avevo aggiornato `saveConfig()` (la funzione che fa la PATCH a Supabase) e l'array `allFields` per il change-tracking dell'input. **Avevo dimenticato di aggiornare `checkChanges()`**, la funzione che decide se il pulsante "Save changes" si attiva o resta grigio.

Risultato: l'utente scrive un valore nel campo, ma il pulsante non si abilita mai. Niente save. Il CEO ha aggirato il problema settando ALGO=4 via SQL diretto su Supabase per sbloccare il test E2E di 45g.

**Fix**: una riga in `web/tf.html:1517-1520`. Aggiunto `tf_exit_after_n_override` alla lista di `checkChanges()`.

**Test live**: Max ha salvato override=10 prima su PENGU, poi su LUMIA (coin appena allocata stasera dal TF). Verificato sul DB:
- `bot_config.tf_exit_after_n_override` = 10 su entrambe ✅
- `bot_config.profit_target_pct` = 0 su entrambe (non toccato) ✅

**Bug "binding sbagliato" cita dal brief**: il sintomo `profit_target_pct: 0 → 4` su ALGO che il CEO aveva visto in `bot_events_log` non era dovuto a binding sbagliato del nuovo campo — era il **side-effect** del flusso del CEO che ha settato ALGO via SQL toccando per sbaglio anche `profit_target_pct`, poi pulito di nuovo. Il binding del nuovo campo è sempre stato corretto: il problema era solo il pulsante Save che non si attivava.

### Fix 2 — 45g check proattivo

**Background**: nel commit `8bced79` (49a) il check 45g viveva solo dentro `check_price_and_execute`, eseguito **dopo** ogni sell positivo. Questo design copriva il caso "organic": una coin che fa un sell che la porta sopra la soglia. Lasciava scoperto il caso che il backtest aveva esposto ma sottovalutato:

- Coin con counter già ≥ N **al deploy** (PENGU e ALGO erano in questo stato già stasera).
- Coin con holdings=0 (cycle chiuso, in idle re-entry) e counter pre-existing — non vendono nulla, il post-sell check non scatta mai. Esempio concreto: ALGO oggi alle 20:30 era counter=6, holdings=0, override=4 → avrebbe dovuto uscire ma non c'era trigger.

**Fix**: `bot/trend_follower/gain_saturation.py` ha 2 funzioni nuove:
- `should_run_proactive_check(symbol, interval_s=300)`: rate-limit per simbolo. Il check proattivo gira al massimo ogni 5 minuti per coin, evita di hammerare Supabase su 30 bot TF.
- (estensione del modulo esistente) — la logica trigger è stata refactorata in un metodo `GridBot.evaluate_gain_saturation(price, trigger_source)` cosí il check post-sell e quello proattivo condividono UNA implementazione, idempotente via il flag `_gain_saturation_triggered`.

`bot/grid_runner.py` chiama il check al main loop subito dopo `_sync_config_to_bot`. Se il flag latched già esiste, no-op. Se la rate-limit window non è scaduta, no-op. Altrimenti valuta. Se trigger:
- **holdings=0**: setto `pending_liquidation=True` direttamente in `evaluate_gain_saturation`. Al prossimo passaggio del top-of-loop, `_force_liquidate(reason="GAIN-SATURATION")` parte, scrive il Telegram cycle-close, esce.
- **holdings>0**: lascia che il flag scateni l'override Strategy A nei sell del prossimo `check_price_and_execute` (esattamente come 39a/39c/45f), che a cycle-closed setterà `pending_liquidation`.

### Telemetria — campo `trigger_source` nuovo

L'evento `tf_exit_saturated` su `bot_events_log` ora include `details.trigger_source ∈ {"post_sell", "proactive_tick"}`. Permette al CEO in revisione settimanale di analizzare quanti trigger arrivano da una via vs l'altra. Se `proactive_tick` finisce > 50% dei trigger, conferma che il design originario di 49a era insufficiente; se è raro, è una safety net.

### Test E2E live

ALGO/USDT con counter=6, holdings=0, override=4 al primo restart post-49b:
- **20:59:00** [grid] WARNING: GAIN-SATURATION TRIGGERED (proactive_tick): 6 positive sells ≥ N=4 (override) ✅
- **20:59:00** [runner] INFO: pending_liquidation=true (GAIN-SATURATION) — force-selling all positions ✅
- **20:59:00** [runner] INFO: No holdings to liquidate (reason: GAIN-SATURATION) ✅
- ALGO esce, `is_active=False`. Bot terminato.

---

## Deviazioni dal brief (discusse con Max, approvate)

### Deviazione 1 — Diagnosi del bug binding diversa da quella ipotizzata dal CEO

**Brief diceva (open question 7.2):** *"sospetto sia in una `saveCoinConfig()` (o simile) dove i campi vengono mappati al PATCH body. Cerca dove `profit_target_pct` riceve un valore da un input del form e verifica se quell'input è il campo 'Exit after N...' o invece il campo 'Take Profit %' originale."*

**Cosa ho trovato invece**: il binding sul codice attuale è **corretto**. Il PATCH manda `tf_exit_after_n_override`, niente confusione di name/var. Il problema era il pulsante Save che non si attivava — quindi nessun PATCH partiva proprio. Max ha confermato il sintomo replicandolo: ha scritto "20" sul campo e ha visto Save grigio. Una volta fixato `checkChanges()`, ha potuto salvare normalmente.

L'evento `profit_target_pct: 0 → 4` su ALGO che il CEO citava in `bot_events_log` come prova del bug-binding era originato dal flusso del CEO (intervento manuale via SQL su Supabase per sbloccare il test E2E), non da una scrittura della dashboard.

### Deviazione 2 — Architettura del check proattivo

**Brief proponeva** (sezione 3.1): inserire il check 45g all'inizio del tick **dentro grid_bot.py**, prima dei filtri 39a/39c/45f.

**Cosa ho fatto invece**: il check post-sell è rimasto dentro `grid_bot.check_price_and_execute` (refactorato in `evaluate_gain_saturation`). Il check proattivo invece vive **in `grid_runner.py`**, nel main loop, prima di `check_price_and_execute`. Tre ragioni:
1. Il check proattivo deve girare anche quando **non viene chiamato `check_price_and_execute`** (es. coin con `is_active=False` in arrivo, branch top-of-loop). Mettere il check dentro `check_price_and_execute` lo lega al flusso "sto valutando trade ora", che è esattamente il caso che si voleva sganciare.
2. Coerenza con dove vivono altri check di stato globale (es. `pending_liquidation` check, `is_active` check) — questi sono nel main loop di grid_runner, non dentro grid_bot.
3. Il rate-limit `should_run_proactive_check` ha senso vicino al main loop, non dentro la decisione trade-by-trade.

Il risultato funzionale è identico al brief. Max ha approvato in sessione.

### Deviazione 3 — Cooldown 5 min confermato

Il brief lasciava aperta la scelta del valore di `PROACTIVE_CHECK_INTERVAL_S` (suggerimento: 300s). Tenuto **300s**: TF non ha urgenza secondo-per-secondo, e su 30+ bot TF potenziali 5 min sono il giusto compromesso tra reattività e load Supabase.

---

## Errori miei post-deploy (sviste, fixate ma da segnalare)

Quando ALGO ha triggerato 45g per la prima volta (20:59:00), sono affiorati **due bug DB-level che non avevo previsto** perché i miei test offline non scrivevano realmente sul DB:

### Svista 1 — CHECK constraint su `bot_events_log.category`

Avevo usato `category="TF_GAIN_SATURATION"` per l'evento `tf_exit_saturated`. Ma `bot_events_log` ha un CHECK constraint che limita `category` a `('tf', 'lifecycle', 'safety', 'config')`.

Sintomo: insert silent-failed con un warning nei log:
```
violates check constraint "bot_events_log_category_check"
```

L'evento NON veniva scritto. Il DEALLOCATE comunque avveniva (il flusso operativo è disgiunto), ma il CEO non avrebbe avuto traccia strutturata in `bot_events_log` per la review settimanale.

**Fix** (commit `030b328`): cambiato a `category="safety"`, coerente con 39a/39c/45f.

### Svista 2 — DEALLOCATE row mancante in trend_decisions_log

Il flusso 45g proattivo con holdings=0 termina nel branch **top-of-loop** di grid_runner (quello che gestisce `pending_liquidation`). Quel branch **NON scriveva** una riga DEALLOCATE in `trend_decisions_log` — solo il branch mid-tick (post `check_price_and_execute`) lo faceva. Il codice originario era ok perché il flusso BEARISH passa per l'allocator che già scriveva il DEALLOCATE; ma il flusso 45g proattivo bypassava entrambi.

Conseguenza: ALGO `is_active=False` ma in `trend_decisions_log` non c'era DEALLOCATE row. Per il prossimo ALLOCATE su ALGO, `get_period_start` non avrebbe visto un DEALLOCATE recente → counter = 6 ancora. **Loop di trigger immediati al prossimo ALLOCATE-update** (esattamente lo scenario che la decisione di Max "no reset on update" voleva proteggere — ma in modo diverso).

**Fix** (commit `030b328`): aggiunta scrittura DEALLOCATE row nel branch top-of-loop di grid_runner, gated su `top_reason == "GAIN-SATURATION"` (BEARISH path skip perché allocator già lo scrive). Inoltre `signal="NO_SIGNAL"` per soddisfare il CHECK `trend_decisions_log_signal_check` (un altro CHECK constraint che mi era passato sotto al naso — strings vuote non sono accettate, valori validi: `BULLISH`, `NO_SIGNAL`, `SIDEWAYS`).

**Backfill manuale per ALGO**: il primo trigger ALGO (20:59:00) era partito col bug ancora presente. DEALLOCATE row non scritto. Ho fatto un INSERT manuale in `trend_decisions_log` con `reason="GAIN_SATURATION (manual backfill: proactive trigger fired pre-writer-fix)"`. Verificato: ora `get_period_start("ALGO/USDT")` restituisce `None` (coerente con "is_active=False, ultimo evento è DEALLOCATE"). Counter resetterebbe a 0 al prossimo ALLOCATE.

### Lezione e azione

Le mie 6 unit test offline (`tests/test_gain_saturation.py`) usano un mock di Supabase. Non hanno potuto vedere CHECK constraints reali. Per cose nuove che scrivono in DB, vale la pena un dry-run di `.insert(...).execute()` contro il DB live **prima** del deploy. Lo metto nella mia checklist personale per le prossime sessioni.

---

## Stato attuale del sistema

### Coin TF attive

- **PENGU/USDT**: `tf_exit_after_n_override = 10`, counter = 6. 45g non scatta finché non arriva alla 10ª positive sell.
- **LUMIA/USDT**: `tf_exit_after_n_override = 10`, counter = 0 (appena allocata stasera dal TF). Stesso comportamento, parte da 0.
- **ALGO/USDT**: `is_active=False` (deallocata via 45g), `tf_exit_after_n_override = 4` preservato per il prossimo ciclo.

### Configurazione globale 45g

- `tf_exit_after_n_enabled = TRUE` (kill-switch globale acceso).
- `tf_exit_after_n_positive_sells = 0` (default globale → regola disattivata system-wide tranne per coin con override esplicito).

### Bot in esecuzione

5 bot vivi: BTC, SOL, BONK (manuali) + PENGU, LUMIA (TF) + TF scanner. Orchestrator PID rinnovato dopo restart pulito.

---

## Test checklist del brief — stato

| # | Item | Stato |
|---|---|---|
| 1 | Dashboard fix verificato manualmente (PENGU/LUMIA a 10) | ✅ |
| 2 | Tornare a vuoto cancella l'override | ⏳ Non testato esplicitamente — il binding NULL è coperto da unit test e dal saveConfig (`null` mappato esplicitamente quando rawVal è ''), ma Max non ha provato il flusso end-to-end. Se serve confermare al 100%, basta che Max lo provi. |
| 3 | Check proattivo trigger su counter pre-existing (ALGO) | ✅ Triggerato esattamente come previsto |
| 4 | Check proattivo trigger con holdings>0 | ⏳ Non testato live (nessuna coin in quello stato stasera). Coperto dalla logica del codice (il flag triggered → override Strategy A → cycle_closed → pending_liquidation) ma non da test live. |
| 5 | No double-trigger | ✅ Coperto dal flag `_gain_saturation_triggered` che è la primissima precondizione di `evaluate_gain_saturation` |
| 6 | Cooldown rispettato (300s) | ✅ Unit test `test_proactive_check_cooldown` passa |
| 7 | Restart-safety | ✅ ALGO trigger live alle 20:59:00 al primo tick post-restart |

---

## File toccati

```
bot/grid_runner.py                    +60 righe (proactive check entry point + GAIN-SATURATION DEALLOCATE writer + reason switching)
bot/strategies/grid_bot.py            +88 righe (refactor in evaluate_gain_saturation, riusato da entrambi i path)
bot/trend_follower/gain_saturation.py +13 righe (PROACTIVE_CHECK_INTERVAL_S + should_run_proactive_check)
tests/test_gain_saturation.py         +18 righe (test cooldown rate-limit)
web/tf.html                           +1 riga  (checkChanges() fix)
config/brief_49b_dashboard_bug_and_45g_proactive_check.md  (added)
```

---

## Numeri operativi

- 7 unit test offline passano (era 6 in 49a, +1 per cooldown).
- Tempo dal restart al primo trigger 45g: **~5 secondi** (ALGO).
- 0 errori bloccanti nei log (ci sono stati 2 warning su `bot_events_log_category_check` e `trend_decisions_log_signal_check` che ora sono fixati con il commit `030b328`).
- Mac Mini sincronizzato `030b328`, orchestrator restarted senza orphan processes.

---

**Bandiera bianca.** Brief 49b chiuso, sistema live, ALGO uscita correttamente, override per-coin via dashboard funzionante. Aspetto nuovi brief o altri input.
