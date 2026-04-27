# Brief 49b — Dashboard binding fix + 45g proactive check

**From:** CEO (Claude, Projects) → CC (Intern)
**Via:** Max (board)
**Date:** 2026-04-27
**Session:** 49
**Priority:** Alta. Sblocca il test E2E di 45g che oggi non può triggerare sui counter pre-existing.
**Stima:** ~1.5-2h
**Predecessore:** Brief 49a (chiuso, commit `8bced79`)

---

## 1. Contesto

Lavoro impeccabile sul brief 49a. Dopo il deploy abbiamo provato il primo test E2E su ALGO/USDT (counter=6, holdings=0) e abbiamo scoperto due cose:

### Bug 1 — Dashboard binding sbagliato

L'utente prova a settare `tf_exit_after_n_override=4` per ALGO/USDT dalla card "Trading Parameters" su `tf.html`. Il save apparentemente non funziona ("il campo torna vuoto"). In realtà funziona ma scrive sulla colonna sbagliata: `profit_target_pct` viene aggiornato da 0 a 4, mentre `tf_exit_after_n_override` resta NULL.

Confermato da `bot_events_log`:
```
2026-04-27 18:27:39.915
event: config_changed_bot_config
message: "bot_config changed for ALGO/USDT: 1 field(s)"
details: {"changes":[{"key":"profit_target_pct", "new":"4", "old":"0"}]}
```

Il CEO ha già ripulito manualmente `profit_target_pct` di ALGO a 0 (era 0 prima del bug). Ora `tf_exit_after_n_override=4` su ALGO è stato settato correttamente via SQL diretto.

### Bug 2 — 45g è solo reattivo, non proattivo (design oversight nel brief 49a)

Il brief 49a sezione 3.4 specificava il check 45g come post-sell. Quel design era completo per coin che FANNO un nuovo sell positivo, ma lascia scoperto un caso edge importante:

**Scenario problematico:** una coin TF con counter già ≥ effective_n e holdings=0. Il bot non sta vendendo nulla → il check post-sell non scatta → la coin resta in soggiorno indefinitamente, ad aspettare un nuovo positive sell organico (ore/giorni).

ALGO oggi è esattamente in questo stato: counter=6, holdings=0, override=4 → 45g dovrebbe scattare immediatamente, ma non scatta perché il bot non ha sell da fare. Il design originario manca questo caso.

**Il backtest aveva proprio questo segnale** ma l'avevo sottovalutato: 7/14 dei trigger nel backtest avvenivano con `residual_qty=0` al trigger time (caso "coin già flat") — quei trigger funzionavano perché la N-esima positive sell era proprio quella che li scatenava. Ma nel mondo reale, post-deploy, abbiamo coin con counter pre-existing che non faranno mai un nuovo sell senza prima passare un nuovo buy → scenario non coperto.

---

## 2. Obiettivo

Due fix paralleli, da deliverare in un singolo commit:

### Fix 1 — Dashboard binding (tf.html)

Il campo "Exit after N positive sells" deve scrivere su `bot_config.tf_exit_after_n_override`, non su `profit_target_pct`. Tu sai dov'è il file (deve esserci una funzione di save che mappa i campi della UI alle colonne DB) — cerca dove `profit_target_pct` viene assegnato ricevendo input da quel campo specifico, e sostituisci.

Sintomo da riprodurre per verifica: aprire la card di una coin TF, scrivere un valore nel campo "Exit after N positive sells", cliccare Save, ricaricare la pagina. Atteso: il valore appare nel campo. Osservato pre-fix: il campo torna vuoto, ma `profit_target_pct` ha cambiato valore.

### Fix 2 — Check proattivo 45g

Aggiungere al main loop del grid_bot un check periodico che, **per coin TF managed**, valuti la condizione di saturazione anche al tick (non solo dopo un sell positivo).

Il check post-sell esistente NON va rimosso. Si aggiunge un secondo punto di valutazione a tick, idempotente col primo.

---

## 3. Specifiche Fix 2 (45g proactive check)

### 3.1 Dove va il nuovo check

Nel main loop di `bot/strategies/grid_bot.py`, idealmente all'inizio del tick (prima di valutare buy/hold/sell). Posizionamento: subito dopo il refresh della config (hot-reload), prima dei filtri 39a/39c/45f esistenti.

### 3.2 Logica

```python
# === Filter 45g proactive check (al tick, oltre al post-sell esistente) ===
if tf_managed and effective_n > 0 and not is_saturated(symbol):
    # Read counter only periodically to limit DB load — vedi 3.3
    pos_count = get_tf_positive_sells_count(symbol, since=current_period_start)
    if pos_count >= effective_n:
        # TRIGGER — stesso path del check post-sell esistente
        if holdings > 0:
            execute_forced_sell(symbol, holdings, price=current_price)
        mark_saturated(symbol)
        log_event_saturated(
            ...,
            n_threshold=effective_n,
            was_override=(bot_config.tf_exit_after_n_override is not None),
            trigger_source="proactive_tick",  # nuovo campo, vedi 3.4
        )
        # Continua il flow normale — la pipeline pending_liquidation
        # gestisce il DEALLOCATE come fa già col check post-sell
```

### 3.3 Frequenza del check (importante per non spammare il DB)

Il check post-sell è naturalmente raro (solo dopo sell positivi). Il check proattivo invece girerebbe ad ogni tick (~60s) per ogni bot TF. Su 30+ bot TF in rotazione potenziali, sono potenzialmente 30 query/min a Supabase solo per questo.

**Soluzione:** introduci un cooldown in-memory per coin. Il check proattivo gira al massimo ogni `_PROACTIVE_CHECK_INTERVAL_S` secondi (suggerimento: **300s = 5 min**) per coin. Implementazione semplice:

```python
_last_proactive_check: dict[str, float] = {}  # symbol → epoch seconds

def should_run_proactive_check(symbol: str) -> bool:
    now = time.time()
    last = _last_proactive_check.get(symbol, 0)
    if now - last >= PROACTIVE_CHECK_INTERVAL_S:
        _last_proactive_check[symbol] = now
        return True
    return False
```

5 minuti è abbastanza: una coin TF non ha urgenza al secondo. È molto meglio che non avere il check del tutto, ed è un costo trascurabile sul DB. Se preferisci una frequenza diversa, scegli pure tu sulla base di quanto già usi Supabase per altri letture nel main loop.

### 3.4 Telemetria — campo nuovo `trigger_source`

L'evento `tf_exit_saturated` esistente ha già tutti i campi giusti. Aggiungi solo un campo:

```python
{
  "event": "tf_exit_saturated",
  "details": {
    ...esistenti...,
    "trigger_source": "post_sell" | "proactive_tick"
  }
}
```

Mi serve per analizzare in revisione settimanale quanti trigger arrivano da una via vs l'altra. Se `proactive_tick` è > 50% dei trigger, vuol dire che il design originario (solo post-sell) era davvero insufficiente; se è raro, è solo una safety net.

### 3.5 Idempotenza

Critico: il check post-sell e il check proattivo possono in teoria triggerare entrambi sullo stesso tick. La protezione è la flag `is_saturated(symbol)`:

- Il check proattivo controlla `not is_saturated(symbol)` come precondizione (vedi 3.2).
- Il check post-sell esistente controlla la stessa cosa? Se non lo fa, aggiungilo. Probabilmente lo fa già (il tuo `mark_saturated` è già idempotente, ma evitiamo doppio log e doppio Telegram).

Risultato netto: una coin viene saturated **una sola volta per soggiorno**, indipendentemente dal path.

### 3.6 Restart-safety

Dopo un restart del bot, `_last_proactive_check` riparte vuoto → al primo tick post-restart il check proattivo gira. Atteso e voluto: se durante il downtime il counter è andato sopra soglia, voglio che la regola scatti subito.

---

## 4. Test checklist

- [ ] **Dashboard fix verificato manualmente**: aprire una card di coin TF, settare "Exit after N positive sells" a 5, salvare, ricaricare, verificare che 5 sia ancora visibile e che `bot_config.tf_exit_after_n_override` lo contenga, e che `profit_target_pct` NON sia cambiato.
- [ ] **Tornare a vuoto cancella l'override**: stesso flusso, settare a 5 → save → ricaricare → cancellare il campo → save → verificare che `tf_exit_after_n_override` sia NULL.
- [ ] **Check proattivo trigger su counter pre-existing**: scenario ALGO attuale (counter=6, holdings=0, override=4). Atteso: al primo tick post-deploy, 45g triggera con `trigger_source="proactive_tick"`, viene loggato il DEALLOCATE, ALGO esce dalla rotazione TF.
- [ ] **Check proattivo trigger con holdings>0**: simulare una coin con counter pre-existing E holdings>0 (es. test su una coin manuale temporaneamente flagged trend_follower, oppure unit test). Atteso: forced sell di tutto il residuo + saturated + DEALLOCATE.
- [ ] **No double-trigger**: il check post-sell e il check proattivo non devono entrambi loggare l'evento sullo stesso tick. Verifica con un mock o uno scenario dove il counter raggiunge N esattamente sul tick di un sell.
- [ ] **Cooldown rispettato**: con `PROACTIVE_CHECK_INTERVAL_S=300`, il check proattivo non deve girare più di ~12 volte/ora per coin. Verifica con un log a livello DEBUG che mostra quando il check skippa per cooldown.
- [ ] **Restart-safety**: dopo restart, il primo tick di una coin con counter>=N triggera 45g entro pochi secondi.

---

## 5. Roll-out

1. Push diretto a main come standard
2. `git pull` su Mac Mini, restart orchestrator + bot
3. **Atteso entro 1-5 min post-restart**: ALGO triggera 45g con `trigger_source="proactive_tick"`. Telegram privato manda il messaggio di DEALLOCATE GAIN-SATURATION. ALGO esce.
4. Notificami quando vedi la notifica (o se NON la vedi entro 5 min) — controllerò io `bot_events_log` per il record completo

---

## 6. Open questions

1. **Cooldown 5 min va bene?** Se preferisci una frequenza diversa basata su quanto altri filtri ricaricano dati simili, fai tu. Non andare sotto 60s o sopra 15 min senza dirmelo.
2. **Dove esattamente nel tf.html sta il bug del binding?** Non ho accesso al file ma sospetto sia in una `saveCoinConfig()` (o simile) dove i campi vengono mappati al PATCH body. Cerca dove `profit_target_pct` riceve un valore da un input del form e verifica se quell'input è il campo "Exit after N..." o invece il campo "Take Profit %" originale (se esiste). Probabilmente c'è uno scambio di name attribute o di var.
3. **Test E2E**: dopo il deploy, mi aspetto che il test su ALGO scatti con `trigger_source=proactive_tick`. Se il primo trigger invece è `post_sell` (perché ALGO nel frattempo ha fatto buy + sell positivo), va bene lo stesso — l'importante è che scatti. Non c'è da aspettarsi nulla di rigido.

---

## 7. Commit message suggerito

```
fix(tf,frontend): dashboard binding + 45g proactive check

Two parallel fixes for issues discovered post-49a deploy:

1. Frontend: tf.html "Exit after N positive sells" field was binding to
   profit_target_pct instead of tf_exit_after_n_override. PATCH now
   targets the correct column; profit_target_pct is no longer touched
   by this field.

2. Filter 45g: added a proactive check at tick time (not just post-sell)
   to handle pre-existing counters on coins with holdings=0 or whose
   next positive sell may never come organically. Cooldown of
   PROACTIVE_CHECK_INTERVAL_S=300 per symbol limits DB load. Idempotent
   with the post-sell check via is_saturated() guard.

Telemetry: bot_events_log details now include `trigger_source`
("post_sell" | "proactive_tick") for revision analysis.

Refs brief_49b in /report_for_CEO/.
```

---

**Tutto chiaro? Bandiera bianca quando hai finito.**
