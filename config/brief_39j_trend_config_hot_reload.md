# BRIEF — 39j: hot-reload di trend_config nei grid_runner TF

**Date:** 2026-04-19
**Priority:** MEDIUM — feature di convenienza, non blocca trading. Serve per dare consistenza al flusso "modifico su /tf → il bot lo recepisce senza restart".
**Prerequisito:** 39g (audit + Telegram su trend_config changes) deployato ✅, 39i (anon UPDATE policy) deployato ✅
**Target branch:** `main` (push diretto)
**Deploy:** richiede restart orchestrator per far partire il nuovo polling (ma post-restart non servirà più per modifiche future)

---

## Problema

Oggi `tf_stop_loss_pct` e `tf_take_profit_pct` vivono su `trend_config`. Sono letti **una sola volta** all'avvio del grid_runner ([bot/grid_runner.py:208-227](bot/grid_runner.py#L208-L227)) e passati al `GridBot()` constructor. Dopo di che il valore resta in RAM del processo e **non viene più ricontrollato**.

Il `SupabaseConfigReader` che gira ogni 300s su ogni grid_runner fa hot-reload di `bot_config` (buy_pct, sell_pct, skim_pct, stop_buy_drawdown_pct, ecc.) ma **non tocca `trend_config`**. Il TF scanner legge `trend_config` ad ogni scan (ogni 1h) ma solo per le proprie decisioni (rotation, alloc) — non propaga il valore ai grid_runner TF già vivi.

**Conseguenza:**
- Modifichi `tf_stop_loss_pct` da 10 a 5 via /tf UI → DB aggiornato, audit loggato, Telegram inviato dal TF loop entro 1h
- I grid_runner TF attivi (es. PHB, BLUR) continuano a usare **10** finché non vengono riavviati o deallocati/riallocati
- Solo i **futuri** bot TF allocati da scan successivi leggeranno il DB fresco con 5

Il CEO si aspetta che "modifico → cambia", come succede per i parametri `bot_config`. Il comportamento attuale è incoerente con il resto del sistema.

---

## Principio di design

- **Hot-reload mirato**: solo i due safety params (`tf_stop_loss_pct`, `tf_take_profit_pct`). Non voglio estendere il polling a tutto `trend_config` — molti campi sono gated o richiedono re-calcoli (es. `scan_interval_hours` influenza il TF scanner, non i grid), e allargare lo scope apre a bug da effetti collaterali.
- **Stesso intervallo del bot_config polling** (300s): semplicità operativa, non serve un thread dedicato, riuso l'infrastruttura esistente.
- **Per-bot cache**: ogni grid_runner legge `trend_config` in modo indipendente. Nessuna coordinazione, nessuna singola sorgente di truth centralizzata — coerente col design attuale.
- **Niente notifica Telegram** lato grid_runner quando il valore cambia: quella è già responsabilità del TF loop (39g) che la manda una sola volta per ogni cambio. Se i grid_runner mandassero anche loro una notifica ciascuno, per un cambio su `tf_stop_loss_pct` riceveresti N messaggi (uno per bot TF attivo). Il grid_runner si limita ad aggiornare il valore in memoria silenziosamente, logga in INFO.

---

## Fix

### Parte 1 — estendere `SupabaseConfigReader` (o un reader parallelo) per polling di `trend_config`

Due approcci possibili:

**Opzione A — aggiungere lettura `trend_config` dentro `SupabaseConfigReader.refresh()`:**

Riuso il thread esistente, aggiungo un campo `self._trend_config: dict` e lo aggiorno dentro `refresh()` prima del return. Espongo un metodo `get_trend_config_value(key)` che il grid_runner può chiamare nel `_sync_config_to_bot`.

Pro: nessun nuovo thread, meno codice duplicato.
Contro: il reader nasce come "bot_config reader" e diventa "multi-table reader", si sporca concettualmente.

**Opzione B — classe `SupabaseTrendConfigReader` parallela:**

Nuova classe in `config/supabase_config.py`, stesso pattern di polling (thread daemon, 300s). Il grid_runner la istanzia accanto al `SupabaseConfigReader` esistente.

Pro: separazione di responsabilità pulita. Facile estendere per altri polling futuri.
Contro: un thread in più per processo, un po' più di codice.

**Raccomandazione:** A. Il reader esistente tocca già Telegram, logica di diff, notifier. Aggiungere una singola tabella al polling è meno invasivo che creare una classe nuova che replica il 70% del codice.

### Parte 2 — sync dei due safety params nel `_sync_config_to_bot` del grid_runner

In [bot/grid_runner.py:69-111](bot/grid_runner.py#L69-L111), aggiungere dopo gli altri field sync:

```python
if bot.managed_by == "trend_follower":
    tf_slp = reader.get_trend_config_value("tf_stop_loss_pct")
    if tf_slp is not None and float(tf_slp) != bot.tf_stop_loss_pct:
        logger.info(
            f"[{symbol}] tf_stop_loss_pct updated: "
            f"{bot.tf_stop_loss_pct} → {tf_slp}"
        )
        bot.tf_stop_loss_pct = float(tf_slp)

    tf_tpp = reader.get_trend_config_value("tf_take_profit_pct")
    if tf_tpp is not None and float(tf_tpp) != bot.tf_take_profit_pct:
        logger.info(
            f"[{symbol}] tf_take_profit_pct updated: "
            f"{bot.tf_take_profit_pct} → {tf_tpp}"
        )
        bot.tf_take_profit_pct = float(tf_tpp)
```

Guardia `bot.managed_by == "trend_follower"`: i bot manuali non usano questi param, non serve leggerli (anche se leggerli sarebbe innocuo perché il check lato `grid_bot` ignora non-TF).

### Parte 3 — rendere il flag `_stop_loss_triggered` / `_take_profit_triggered` resettabile (opzionale)

**Scenario edge-case:** un bot TF ha già triggerato stop-loss, `_stop_loss_triggered=True`, `pending_liquidation=True`, sta per chiudersi. Se nel frattempo abbasso `tf_stop_loss_pct` da 10 a 5, il polling lo aggiorna. Ma il flag latched era stato settato con 10, quindi il bot chiude correttamente.

Viceversa: bot TF attivo, unrealized −7%, `_stop_loss_triggered=False` perché threshold è 10. Se abbasso il valore a 5, al prossimo tick il check riparte con il nuovo threshold e scatta subito.

Questo è il comportamento desiderato — non serve resettare nulla. **Parte 3 out of scope.**

---

## Files da modificare

| File | Azione |
|---|---|
| `config/supabase_config.py` | Estendere `refresh()` per leggere anche `trend_config` (selezionare solo `tf_stop_loss_pct,tf_take_profit_pct,id`); aggiungere metodi `get_trend_config_value(key)` + dict privato |
| `bot/grid_runner.py` | In `_sync_config_to_bot`, dopo i field esistenti, aggiungere i 2 blocchi per `tf_stop_loss_pct` / `tf_take_profit_pct` (solo per TF bots) |

## Files da NON toccare

- `bot/strategies/grid_bot.py` — i check stop-loss / take-profit usano già `self.tf_*_pct`, che viene aggiornato via `_sync_config_to_bot`. Nessuna modifica alla state machine.
- `bot/trend_follower/trend_follower.py` — il polling TF loop (39g) resta come è: continua a mandare la notifica Telegram sui cambi `trend_config`. Quella NON è la stessa notifica del grid_runner, sono due path indipendenti (lo scanner decide rotation/alloc, i grid_runner leggono per i propri safety).
- `web/tf.html` — il save UI non cambia, il flusso era già corretto post-39i.
- DB — nessuna migration, nessuna colonna nuova.

---

## Test pre-deploy

1. **Unit-ish test locale** (paper mode manuale): in una shell Python carica `SupabaseConfigReader`, chiama `refresh()`, verifica che `_trend_config` contenga i tre valori attesi.
2. **Test manuale end-to-end su Mac Mini** post-deploy:
   - Restart orchestrator
   - Verifica nei log grid_<TF_SYMBOL>.log che appaia un INFO al primo refresh con `tf_stop_loss_pct: 10 → 10` (no-op, solo conferma lettura) entro 300s
   - Modifica `tf_stop_loss_pct` da 10 a 8 via /tf UI
   - Attendi max 300s
   - Verifica nei log che appaia `INFO: [SYMBOL] tf_stop_loss_pct updated: 10 → 8`
   - Verifica che `bot.tf_stop_loss_pct` (tramite get_status o log periodico) sia ora 8
   - Riporta a 10

---

## Test post-deploy

- Primo scan TF dopo il deploy: il Telegram "CONFIG CHANGE DETECTED" (da 39g) deve continuare ad arrivare normalmente
- Se modifichi un safety param via UI, entro 5 minuti i log dei grid_runner TF attivi devono mostrare l'aggiornamento
- Nessun aumento notevole di traffico Supabase (una SELECT in più per processo ogni 300s, trascurabile)

---

## Edge cases

**E1 — trend_config irraggiungibile durante il polling:** lo stesso `SupabaseConfigReader` esistente già gestisce il caso "Supabase unreachable" mantenendo l'ultimo valore noto. Il nuovo polling eredita questo comportamento.

**E2 — race tra modifica DB e check stop-loss:** il check avviene ogni 20-60s (tick grid_runner), il polling ogni 300s. Finestra massima in cui il check usa il valore vecchio: 300s dalla modifica. Accettabile.

**E3 — bot TF appena spawnato:** legge `trend_config` al boot (come oggi) + entra nel polling. Nessuna differenza di comportamento, il polling da quel momento lo mantiene allineato.

**E4 — bot manuale nel grid_runner:** il sync dei safety TF è gated da `managed_by == "trend_follower"`. Il bot manuale legge ma non usa nulla. Zero impatto.

**E5 — `scan_interval_hours` non viene fatto hot-reload:** corretto. Quel valore è del TF scanner, non dei grid_runner. Il TF loop lo legge ad ogni scan naturalmente.

---

## Rollback

```bash
git revert <commit_hash>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# restart orchestrator per far ripartire senza il polling trend_config
```

Rollback riporta al comportamento pre-39j: modifiche a `tf_stop_loss_pct` / `tf_take_profit_pct` richiedono restart orchestrator per propagarsi ai bot TF vivi. Nessuna perdita di dati.

---

## Commit format

```
feat(tf): hot-reload tf_stop_loss_pct + tf_take_profit_pct in live grid_runners

The two TF safety params live in trend_config and were previously
read once at grid_runner startup. Modifying them via /tf UI updated
the DB but left running TF bots with stale thresholds until next
restart or dealloc/alloc.

SupabaseConfigReader now also polls trend_config (selecting only the
two safety fields) on the same 300s interval. grid_runner's
_sync_config_to_bot syncs bot.tf_stop_loss_pct / bot.tf_take_profit_pct
from the reader on every tick for TF-managed bots. Within 5 minutes
of a UI save, all live TF bots pick up the new threshold.

Telegram notification on trend_config changes is NOT duplicated here —
the trend_follower scan-loop (39g) remains the single source of that
message; grid_runners silently update their in-memory value and log
at INFO level.
```

---

## Out of scope

- Polling di altri campi di `trend_config` (es. `tf_budget`, `tf_max_coins`): quelli sono usati dal TF scanner, non dai grid_runner. Se in futuro servisse hot-reload lato scanner, brief separato.
- Notifica Telegram per-bot del cambio (duplicazione del messaggio del 39g).
- Cache centralizzata di `trend_config` condivisa tra i processi: overkill per lo scope attuale. Ogni processo legge la propria copia, è ok.
- Reset dei flag `_stop_loss_triggered` / `_take_profit_triggered` al cambio di threshold: non serve (vedi Parte 3).

---

## Note finali

Brief piccolo per natura, ma con impatto UX forte: rende coerente il flusso "modifica DB → bot recepisce" per tutti i parametri, non solo quelli di `bot_config`. Dopo il deploy di 39j, /tf UI si comporterà allineato ad admin UI: clicco Save, entro 5 minuti i bot vivi applicano il nuovo valore.
