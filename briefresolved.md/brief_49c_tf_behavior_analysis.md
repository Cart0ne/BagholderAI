# Brief 49c — TF Behavior Analysis post 49a/49b

**From:** Max (board) → CC (Intern, prossima sessione)
**Date:** 2026-04-28
**Priority:** Media. È un'analisi di osservazione, niente di rotto da fixare.
**Stima:** ~2-3h (è ricerca dati, non implementazione)
**Predecessori:** brief 49a (commit `8bced79`) + 49b (commits `dc5e743` + `030b328` + `5b9d34d` + `40354d7` + `e70c670`)

---

## 1. Contesto (per ripartire da zero)

Nella sessione del 27/04 abbiamo deployato due brief in cascata sul Trend Follower:

- **49a — 45g Gain-Saturation Circuit Breaker**: una nuova regola di safety che fa uscire il TF dopo N sell positive nel soggiorno corrente. Counter stateless dalle `trades`, override per-coin via `bot_config.tf_exit_after_n_override`, default globale via `trend_config.tf_exit_after_n_positive_sells` (oggi a **0** = regola disattivata system-wide), kill-switch globale `tf_exit_after_n_enabled` (TRUE).

- **49b — proactive check + dashboard fix**: il check 45g originale era post-sell, ma una coin con holdings=0 e counter già ≥ N non vendeva mai e quindi non triggerava. Aggiunto un check al tick (in grid_runner main loop), idempotente con quello post-sell via flag `_gain_saturation_triggered`. Fixato anche un bug del Save button nella dashboard.

**Stato live al momento del handoff (notte 27→28 aprile)**:
- ALGO è uscita correttamente alle 20:59 via 45g `proactive_tick` (counter=6, override=4 → fire) — primo trigger live in assoluto.
- PENGU e LUMIA hanno entrambe `tf_exit_after_n_override = 10` (settati da Max via dashboard come test del fix Save button).
- Default globale = 0 → solo le coin con override esplicito sono protette dalla regola.

**File chiave da rileggere prima di partire**:
- [config/brief_49a_tf_exit_after_n_positive_sells.md](brief_49a_tf_exit_after_n_positive_sells.md) — il brief originario del CEO
- [config/brief_49b_dashboard_bug_and_45g_proactive_check.md](brief_49b_dashboard_bug_and_45g_proactive_check.md) — il fix proattivo
- [report_for_CEO/exit_after_n_positive_sells_proposal.md](../report_for_CEO/exit_after_n_positive_sells_proposal.md) — backtest che ha motivato la regola
- [report_for_CEO/session49b_report_for_ceo.md](../report_for_CEO/session49b_report_for_ceo.md) — recap dell'implementazione (incluse 2 sviste mie sui CHECK constraints)
- [bot/trend_follower/gain_saturation.py](../bot/trend_follower/gain_saturation.py) — il modulo helper
- [bot/strategies/grid_bot.py](../bot/strategies/grid_bot.py) — `evaluate_gain_saturation()` (~riga 517)

---

## 2. Obiettivo dell'analisi

Capire **come si è comportato il TF** dopo il deploy di 49a + 49b, e in particolare se la regola 45g sta producendo l'edge atteso oppure no. Tre domande operative da rispondere con dati:

### Domanda A — La regola 45g sta funzionando come atteso?

- Quanti `tf_exit_saturated` events ci sono in `bot_events_log` dopo le 20:00 del 27/04?
- Per ognuno: `n_threshold` (effettivo), `was_override` (vero/default), `trigger_source` (`post_sell` vs `proactive_tick`), `total_period_realized_pnl_usd`.
- Distribuzione: quante volte ha triggerato come `proactive_tick` vs `post_sell`? (Se è > 50% proactive, conferma che il design originario di 49a era insufficiente; se è raro, il proactive è solo una safety net.)

### Domanda B — Le coin con override esplicito hanno un comportamento diverso da quelle al default?

- PENGU e LUMIA hanno `override=10`. Nei prossimi giorni vedremo se accumulano abbastanza positive sells da arrivare a 10, e se quando arrivano la regola scatta come previsto.
- Tutte le altre coin TF (default=0) sono **non protette**. Servono come gruppo di controllo: posso confrontare il loro P&L per soggiorno con quello di PENGU/LUMIA per misurare l'effetto reale della regola live (non solo backtest).

### Domanda C — Il backtest era predittivo?

- Il backtest del 27/04 (vedi proposal report) prevedeva edge totale +$35.30 a N=4 su 27 soggiorni (12 giorni). Ora con dati live post-deploy possiamo:
  - **Replicare il backtest** sui nuovi soggiorni TF dopo il deploy → confrontare l'edge predetto con quello osservato.
  - Verificare se il pattern "MOVR-like" (coin che regala 4 sell positive e poi seppellisce) si ripresenta o era un artefatto del periodo specifico 15-27 aprile.
  - Aggiornare il consiglio al CEO se vale la pena spostare il default globale da 0 a 4 (= attivare la regola system-wide).

---

## 3. Cosa fare concretamente

### 3.1 Recap rapido dello stato attuale (10 min)

```python
# Quante coin TF attive ora? Quale override su ognuna?
SELECT symbol, is_active, tf_exit_after_n_override, capital_allocation, allocated_at
FROM bot_config WHERE managed_by='trend_follower' AND is_active=true;

# Stato del default globale
SELECT tf_exit_after_n_enabled, tf_exit_after_n_positive_sells FROM trend_config;
```

### 3.2 Analisi degli eventi 45g (30 min)

```python
SELECT created_at, symbol, details
FROM bot_events_log
WHERE event = 'tf_exit_saturated'
ORDER BY created_at;
```

Per ognuno parsare `details`:
- `n_threshold`, `was_override`, `trigger_source`, `positive_sells_count`,
- `residual_holdings`, `liq_value_usd`, `liq_pnl_usd`, `total_period_realized_pnl_usd`
- `period_started_at`

Tabella riassuntiva. Quante volte è scattata la regola? Su quali coin? Quale fonte (override vs default)?

### 3.3 Replica del backtest sui dati post-deploy (45 min)

Lo script esiste già: [scripts/backtest_exit_after_n_positive_sells.py](../scripts/backtest_exit_after_n_positive_sells.py).

Modifica/duplica per filtrare solo i soggiorni TF chiusi **dopo le 20:00 del 27/04** (= dopo il deploy di 45g). Output:

```
Closed managed periods POST-DEPLOY: N
N=2: trig=X beat=Y worse=Z totΔ=$W
...
N=4: trig=X beat=Y worse=Z totΔ=$W   ← match col backtest pre-deploy?
```

Se l'edge live a N=4 si conferma positivo → raccomandazione al CEO: spostare default globale da 0 a 4. Se è negativo o inconsistente → mantenere default 0 e protezione solo via override per-coin.

### 3.4 Confronto coin-protette vs coin-non-protette (30 min)

Se nel periodo post-deploy abbiamo abbastanza coin TF chiuse (target ≥ 10), splitto in due gruppi:
- **Protette**: avevano `tf_exit_after_n_override > 0` durante il loro soggiorno.
- **Non protette**: `override = NULL` o `0`.

Confronta il P&L medio per soggiorno tra i due gruppi. Limite: campione piccolo (poche coin TF, pochi giorni). Riportare con onestà i numeri ma anche i caveat.

### 3.5 Report finale (30 min)

Scrivi un report nella cartella `report_for_CEO/`. Nome suggerito: `session49c_tf_behavior_analysis_post_deploy.md`. Contenuto:

- TL;DR di 3 righe massimo
- Numeri dei trigger 45g (con tabella)
- Replica backtest con confronto pre/post deploy
- Raccomandazione operativa: alzare il default globale a 4? Lasciare a 0 e usare override per coin specifiche? Aspettare più dati?
- Domande aperte per il CEO

Non implementare nulla. Solo analisi.

---

## 4. Cose da NON fare in questa sessione

- **Non modificare 45g**. Il codice è in produzione e sta funzionando. Se l'analisi rivela problemi, raccogli evidenze e chiedi al CEO un brief 49d dedicato.
- **Non muovere il default globale** da 0 senza approvazione esplicita. Anche se i dati supportassero il cambio, è una decisione di policy del CEO.
- **Non toccare il dashboard** né i daily report — la sessione 27/04 li ha già messi a posto.
- **Non scrivere nuovi unit test** o refactor — è una sessione di analisi pura.

---

## 5. Quello che la nuova chat NON sa (e che serve sapere subito)

Dato che si parte da zero, ecco i fatti operativi che il bot non può inferire dal codice:

1. **Naming**: in questo progetto i filtri di safety sono numerati per sessione (39a, 39b, 39c, 45f, 45g, ...). `45g` = "gain saturation breaker". Niente magia nel nome, è solo "il prossimo dopo 45f".

2. **Architettura runtime**: orchestrator (PID padre) + N grid_bot subprocess (uno per coin attiva) + 1 trend_follower scanner subprocess. Tutti girano sul Mac Mini in `/Volumes/Archivio/bagholderai`. SSH passwordless via `max@Mac-mini-di-Max.local`. Repo locale Mac Air è `/Users/max/Desktop/BagHolderAI/Repository/bagholder`.

3. **Lavoro in produzione**: paper mode su Binance testnet, ma **sembra reale** (decisioni autonome, soldi simulati che però replicano logica live). Trattare come prod.

4. **Stack DB**: Supabase. Tabelle chiave per questa analisi: `trades`, `bot_events_log`, `trend_decisions_log`, `bot_config`, `trend_config`.

5. **Paranoia DB constraints**: `bot_events_log.category` accetta solo `('tf','lifecycle','safety','config')`. `trend_decisions_log.signal` solo `('BULLISH','NO_SIGNAL','SIDEWAYS')`. Se devi inserire qualcosa, attieniti a quelli (**ma per questa sessione non devi inserire niente**).

6. **CEO vs Max**: il CEO è Claude su claude.ai (scrive i brief). Max è il board, l'interlocutore diretto. Tu sei l'intern. Non confondere i ruoli.

7. **Linguaggio preferito**: italiano per la conversazione con Max. Documenti tecnici e codice in inglese. Gli analytics nel report finale possono mescolare (descrizione it + table en va bene).

8. **Da fare all'inizio della chat**: chiedere a Max se serve `git pull`. Il repo si sviluppa su 2 macchine (Mac Air + Mac Mini), può essere disallineato.

---

## 6. Output atteso

Un report in `report_for_CEO/session49c_tf_behavior_analysis_post_deploy.md` che il CEO possa leggere in 5 minuti e capire:

- 45g sta funzionando? (sì / no / parzialmente)
- Vale la pena alzare il default globale a 4? (sì / no / aspettiamo)
- C'è qualcosa di inaspettato che merita un brief di follow-up? (sì → cosa / no)

Bandiera bianca quando il report è scritto.
