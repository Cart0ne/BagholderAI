# Brief 70b — Ricalibrazione Sentinel + riaccensione DRY_RUN

**Data:** 2026-05-10  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-09 (S69 chiusura, commit cb21179)  
**Autore:** CEO  
**Priorità:** non gating per go-live €100, ma necessario per raccolta dati Sentinel/Sherpa  
**Stima:** ~2-3h (analisi bug + fix + test + restart orchestrator)

---

## Contesto

Sentinel e Sherpa sono stati deployati in DRY_RUN il 6 maggio (Sprint 1, commit `83b253c`), poi spenti in S68 (flag `ENABLE_SENTINEL=false`, `ENABLE_SHERPA=false` nell'orchestrator) durante il pivot "minimum viable Grid-only".

Il Grid ora gira pulito in avg-cost trading (S69). È il momento di riaccendere Sentinel + Sherpa per raccogliere dati sul nuovo regime. Problema: **3 bug di calibrazione** trovati in S63 grazie alla dashboard /admin non sono mai stati fixati:

1. **`speed_of_fall_accelerating` miscalibrato** — soglia troppo alta o formula sbagliata, non distingue cadute reali da rumore
2. **Risk score binario** — produce solo 0 o 100, nessuna sfumatura intermedia. Renderebbe il replay counterfactual inutile
3. **Opportunity score morta** — sempre 0 per tutti i simboli. Sherpa non ha segnale di opportunità su cui proporre

Dettagli nei bug log di PROJECT_STATE §5 (versione S63) e nel report `report_for_CEO/2026-05-07_session64_admin_dashboard_bug_hunt_report_for_ceo.md`.

Se riaccendiamo senza fixare, raccogliamo 7+ giorni di dati da sensori rotti. Già successo una volta, non ripetiamo.

---

## Cosa implementare

### Step 1 — Analisi e fix dei 3 bug (score_engine.py / price_monitor.py)

CC deve:

1. **Aprire `bot/sentinel/score_engine.py`** e individuare la logica di scoring risk + opportunity. Capire perché:
   - Risk è binario (quali condizioni producono solo 0 o 100? Soglie? Clamp?)
   - Opportunity è sempre 0 (il segnale non arriva? La formula è morta? Mancano dati di input?)

2. **Aprire `bot/sentinel/price_monitor.py`** e individuare il calcolo `speed_of_fall`. Capire:
   - Come viene calcolato (derivata del prezzo? Delta su N tick?)
   - Perché `_accelerating` non scatta mai o scatta sempre

3. **Proporre fix** con nuove soglie/formule calibrate. NON inventare numeri — basarsi sui dati reali in `sentinel_scores` (i ~1400 record raccolti dal 6 al 7 maggio, se ancora presenti nonostante la retention). Se i dati sono spariti, basarsi su range di prezzo tipici BTC/SOL/BONK degli ultimi giorni e calibrare di conseguenza.

### Step 2 — Riaccensione DRY_RUN

1. **Flag orchestrator**: `ENABLE_SENTINEL=true`, `ENABLE_SHERPA=true`
2. **Verificare** che `SHERPA_MODE=dry_run` sia ancora il default (NON deve essere `live`)
3. **Restart orchestrator** sul Mac Mini con i 3 fix applicati
4. **Smoke test**: verificare che sentinel_scores e sherpa_proposals ricevano nuovi record entro 5 minuti dal restart

### Step 3 — Retention check

Verificare che `db_maintenance.py` abbia retention corretta per le tabelle Sentinel/Sherpa:
- `sentinel_scores`: 30 giorni
- `sherpa_proposals`: 60 giorni

Se la retention è stata modificata o disabilitata durante il periodo offline, ripristinare.

---

## Decisioni delegate a CC

- Scelta delle nuove soglie / formule di calibrazione per i 3 bug — CC ha accesso ai dati storici e al contesto tecnico
- Pattern di test: unit test sui nuovi calcoli di scoring o solo smoke test runtime. A discrezione CC
- Ordine dei fix (tutti e 3 in un commit o separati)

## Decisioni che CC DEVE chiedere

- Se il fix richiede **modifiche allo schema** di `sentinel_scores` o `sherpa_proposals` (nuove colonne, tipi diversi): STOP e chiedere
- Se il fix richiede **modifiche alle tabelle `bot_config` o `trend_config`**: STOP e chiedere
- Se la retention ha cancellato tutti i dati storici e non c'è baseline per calibrare: segnalare e proporre approccio alternativo

## Output atteso

1. 3 bug fixati in `score_engine.py` / `price_monitor.py`
2. Sentinel + Sherpa riaccesi in DRY_RUN sull'orchestrator Mac Mini
3. Evidenza di nuovi record in `sentinel_scores` e `sherpa_proposals` (screenshot query o output)
4. Nessun impatto sul Grid (i bot continuano a girare indisturbati)
5. Contatore 7 giorni raccolta dati parte dal momento del restart

## Vincoli

- **SHERPA_MODE deve restare `dry_run`** — Sherpa NON deve scrivere `bot_config` in produzione
- **NON toccare** codice Grid (grid_bot.py, sell_pipeline.py, buy_pipeline.py, state_manager.py)
- **NON toccare** il path TF (trend_follower/)
- **NON modificare** la dashboard /admin — i fix sono backend, la dashboard legge e basta
- **NON riaccendere TF** (ENABLE_TF resta false)
- **Task > 1h → piano in italiano** leggibile da Max prima di scrivere codice

## Roadmap impact

Non gating per go-live €100, ma prerequisito per:
- Replay counterfactual Sherpa (7 giorni post-restart)
- Decisione SHERPA_MODE → live (post replay + Board approval)
- Sentinel Sprint 2 (slow loop: Fear & Greed + CMC dominance)

---

*CEO, 2026-05-10*
