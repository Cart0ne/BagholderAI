# Sentinel + Sherpa Sprint 1 — Deploy Report

**Da:** Intern (Claude Code) → CEO
**Data:** 2026-05-06
**Sessione:** ~62
**Stato:** ✅ Live in produzione (Mac Mini), modalità **DRY_RUN** (default brief)

---

## TL;DR

Sentinel e Sherpa Sprint 1 sono shipped e girano 24/7 sul Mac Mini come processi managed dall'orchestrator, identici al pattern dei grid bot. Comunicazione via Supabase only (tabelle `sentinel_scores` e `sherpa_proposals`, entrambe nuove, RLS+CHECK costraints). `bot_config` non viene mai toccato in DRY_RUN — verificato pre/post restart.

In questa sessione abbiamo: (1) implementato i 13 file Sentinel+Sherpa più la modifica orchestrator, (2) recepito le 5 risposte del Board sulle questioni aperte (architettura base+adjustment, stop_buy_drawdown_pct Board-only, soglia speed_of_fall, range buy_pct, opportunity_score loggato non usato), (3) aggiunto `symbol_price` a `sherpa_proposals` per il replay counterfactual, (4) ridotto del 90% gli eventi `bot_events_log` con dedup tra tabelle Sentinel/Sherpa e Supabase, (5) attivato retention 30/60 giorni nel db_maintenance giornaliero.

Telegram pulito (1 messaggio ogni 10 min per bot di proposta DRY_RUN, 0 errori). I tre Grid bot (BTC, SOL, BONK) continuano coi parametri attuali, intoccati.

**Prossimo check pianificato:** domani ~18:24 UTC, validazione 24h dei dati raccolti per il replay counterfactual (script di replay da scrivere quando i 7 giorni di dati sono completi).

---

## 1. Cosa è stato shipped

### Architettura

```
bot/sentinel/                           bot/sherpa/
    main.py        loop 60s                main.py             loop 120s
    price_monitor  buffer 24h+klines       parameter_rules     base+delta layer
    funding_monitor cache 8h               cooldown_manager    24h Board override
    score_engine   risk + opp 0-100        config_writer       LIVE only
    inputs/binance_btc.py
    inputs/binance_funding.py
```

L'orchestrator ora lancia anche Sentinel e Sherpa con lo stesso pattern di restart-with-backoff (max 5 retry, poi alert Telegram + give-up). 11 processi Python attivi sul Mac Mini: orchestrator + caffeinate + 6 grid_runner (BTC/SOL/BONK/TRX/ZEC/VIRTUAL — TF rotation ha sostituito AR con VIRTUAL durante il restart) + trend_follower + sentinel + sherpa.

### Logica Score Sentinel (Sprint 1, fast signals only)

| Segnale | Δ risk | Δ opp |
|---|---|---|
| BTC -3% in 1h | +30 | — |
| BTC -5% in 1h | +50 | — |
| BTC -10% in 1h | +80 | — |
| BTC +3% in 1h | — | +25 |
| BTC +5% in 1h | — | +40 |
| Speed of fall accelerating | +20 | — |
| Funding > 0.03% | +15 | — |
| Funding > 0.05% | +25 | — |
| Funding < -0.01% | — | +15 |
| Funding < -0.03% | — | +25 |
| Base | 20 | 20 |

`speed_of_fall_accelerating` definito secondo brief: drop ultimi 20 min ≥ 1.5× drop medio orario. Approvato dal Board.

### Logica Parametri Sherpa (architettura base+adjustment)

| Layer | Cosa fa | Sprint 1 |
|---|---|---|
| **Base** (regime) | Tabella 5 regimi (Extreme Fear → Extreme Greed) | Hardcoded `neutral` (1.0% / 1.5% / 1.0h) |
| **Adjustment** (fast signals) | Delta cumulativi da BTC%, funding, speed | Attivo |

Codice già pronto per Sprint 2: basterà sostituire `regime="neutral"` con il regime che il slow loop calcolerà da F&G + CMC. Zero refactoring.

`stop_buy_drawdown_pct` resta Board-only come da brief; Sherpa logga `proposed_stop_buy_active=true` quando risk>90 per analisi futura, ma non scrive mai questo parametro.

---

## 2. Le 5 questioni del Board sono state recepite tutte

| # | Questione | Decisione Board | Stato codice |
|---|---|---|---|
| 1 | Mapping monolitico vs base+adjustment | Base+adjustment da subito | ✅ Implementato in `parameter_rules.py` |
| 2 | `opportunity_score` solo logged | Sì, non usato in Sprint 1 | ✅ Documentato, mai letto da Sherpa |
| 3 | Definizione `speed_of_fall_accelerating` | "drop 20m ≥ 1.5× drop medio 1h" | ✅ In `price_monitor.py` con esempio numerico |
| 4 | `stop_buy_drawdown_pct` (Board-only / Sherpa / dry-run logged) | Opzione C (dry-run logged, decidere a Sprint 2) | ✅ `proposed_stop_buy_active` in `sherpa_proposals` |
| 5 | Range buy_pct in crash estremo | Opzione A (cap 3.0%, alziamo solo coi dati) | ✅ Nessuna modifica al cap |

Brief `brief_sentinel_sherpa_sprint1_bis.md` con le risposte è committato e consultabile.

---

## 3. Smoke test e verifiche live

### Test pre-deploy (Mac Mini, sessione apposita)

| Test | Risultato |
|---|---|
| Import sanity (tutti i moduli importabili) | ✅ |
| Binance API connectivity (BTC ticker, klines, funding) | ✅ BTC $81,725 / -0.006% funding al test |
| Score engine: crash scenario (-5% + speed accelerating + funding>0.05%) | ✅ risk=100 opp=20 |
| Score engine: pump scenario (+4% + funding<-0.03%) | ✅ risk=20 opp=70 |
| Score engine: no signals | ✅ risk=20 opp=20 (base) |
| Parameter rules: extreme crash | ✅ buy_pct cappato a 3.0% (range max) |
| Parameter rules: nessun segnale | ✅ ritorna esatto neutral base |
| Sentinel run 30 min | ✅ 30 INSERT in `sentinel_scores`, 0 errori |
| Sherpa run DRY_RUN ~5 min | ✅ 9 proposte (3 bot × 3 cicli), `bot_config` invariato |
| `bot_config` invariance check | ✅ Pre/post Sherpa run identici |
| Restart orchestrator con Sentinel+Sherpa managed | ✅ 11 processi up, primo poll spawn corretto |

### Stato verificato live (post-restart 18:24 UTC)

| Check | Risultato |
|---|---|
| 11 processi attivi (incluso Sentinel + Sherpa) | ✅ |
| `sentinel_scores` writes | ✅ 1.06 rows/min (target ~1/min) |
| `sherpa_proposals` writes con `symbol_price` non-null | ✅ 100% delle righe popolato |
| Eventi `SENTINEL_SCAN`/`SHERPA_PROPOSAL` rimossi da `bot_events_log` | ✅ Da 2.46 → 0.24 rows/min (-90%) |
| `bot_config` invariato dal momento del deploy | ✅ |
| Errori in 2h+ di run | ✅ Zero |

---

## 4. Audit dati storici (per validare il piano replay)

Il Board ha chiesto: "non aspettiamo 7 giorni per scoprire che mancano dati. Verifica subito che `sherpa_proposals` salvi tutto quello che serve per fare il counterfactual."

### Dati già disponibili in DB

| Fonte | BTC | SOL | BONK | Note |
|---|---|---|---|---|
| `trades` (config v3) | 96 | 91 | 246 | Dal 30/03, completi |
| `bot_state_snapshots` (7gg) | 650 / 167h | 866 / 168h | 1,939 / 169h | Copertura quasi oraria |
| `config_changes_log` | 2 cambi | 6 cambi | 4 cambi | Volume basso = parametri stabili |

### Schema gap identificato e corretto

**Mancava `symbol_price` in `sherpa_proposals`.** Avevamo `btc_price` (utile come indice macro) ma non il prezzo del symbol stesso al momento della proposta. Senza, il replay counterfactual sarebbe stato costretto a recuperare i klines Binance per ogni replay invece di leggere il valore "frozen" al momento della decisione Sherpa.

**Fix:** migration `sherpa_proposals_add_symbol_price` applicata via Supabase MCP, modifica codice Sherpa per fetchare prezzo (endpoint light `/api/v3/ticker/price`) e salvarlo. Test: 100% delle proposte post-deploy hanno `symbol_price` popolato (BTC ~$81.7k, SOL ~$89, BONK ~$0.00000676).

### Strategia replay counterfactual (da implementare dopo i 7 giorni)

```
Per ogni finestra di 2 min con would_have_changed=true:
  1. Carica klines Binance 1m della stessa finestra (gratuito)
  2. Ricostruisce last_buy_price del bot reale da trades
  3. Simula la logica grid_bot tick-by-tick con i parametri proposti
  4. Confronta:
     - cosa il bot ha fatto davvero (da trades)
     - cosa avrebbe fatto con i parametri Sherpa (simulazione)
  5. Differenza P&L FIFO sulla finestra
Aggrega per bot e per giorno → report "Sherpa vs Tu: +/- X% in 7 giorni"
```

Lo script di replay è ~150 righe Python, non lo abbiamo scritto in questa sessione (deciso: prima vediamo se i dati sono completi a 24h). Logica già definita.

---

## 5. Ottimizzazioni anti-spam DB applicate

Pre-deploy ho misurato il volume di scrittura proiettato e ho trovato un problema: stimato ~7,100 righe/giorno tra `sentinel_scores` + `sherpa_proposals` + `bot_events_log`. **Stesso pattern del problema log Telegram di sessione 59** (commit `bbc8477`): generavamo rumore evitabile.

Tre fix applicati:

1. **Dedup tra tabelle:** rimossi i `SENTINEL_SCAN` event (info già in `sentinel_scores`) e `SHERPA_PROPOSAL` event (info già in `sherpa_proposals`). Mantenuti START/STOP/ERROR/COOLDOWN/STALE.
2. **Sherpa scrive solo se rilevante:** `sherpa_proposals` riceve INSERT solo quando `would_have_changed=true OR proposed_stop_buy_active OR cooldown_active`. No-op cycles (proposta == current senza cooldown) eliminati.
3. **Retention attiva:** `db_maintenance.py` (cron giornaliero 04:00 UTC dal brief 59b) ora cancella `sentinel_scores` > 30 giorni e `sherpa_proposals` > 60 giorni.

### Risultato misurato post-deploy

| Tabella | Pre (rows/min) | Post (rows/min) | Riduzione |
|---|---|---|---|
| `sentinel_scores` | 0.99 | 1.06 | invariato (rumore statistico, target ~1/min) |
| `sherpa_proposals` | 1.46 | 1.77 | invariato (rumore statistico) |
| `bot_events_log` (eventi S+S) | 2.46 | **0.24** | **-90%** ✅ |
| **Totale rows/24h** | ~7,100 | ~4,340 | **-39%** |

### Onestà sul fatto che la riduzione non è -70% come previsto

**Ottimizzazione 2 nella pratica non riduce niente.** Filtrare per `would_have_changed=true` doveva eliminare i no-op, ma il Board ha parametri attuali sempre diversi dalla base neutral di Sherpa (`idle_reentry_hours=4` vs neutral=1, ecc.). Quindi `would_have_changed` è SEMPRE `true`, il filtro non filtra mai.

Per ridurre davvero `sherpa_proposals` servirebbe un **fix A** (soglia di significatività sul cambio: ignora variazioni < 0.30%). L'ho lasciato fuori per due motivi:

- **Sprint 1 vuole tutti i dati**, anche il "Sherpa stabile su X per 30 min" è informazione utile per il counterfactual
- **Volume reale** ~4,340 righe/giorno con retention 60 giorni = ~260k righe = ~200 MB stabili. Sotto la soglia di preoccupazione.

Il fix A sarà valutato dopo i 7 giorni di dati reali, dove vedremo se il flicker di parametri impatta davvero la qualità del counterfactual o è solo rumore di superficie.

---

## 6. Osservazione del Board: "messaggi Telegram ogni 10 min, troppi cambi a breve distanza"

Il Board ha notato due messaggi Sherpa a 10 minuti di distanza con proposte diverse (`buy_pct 0.50→1.30` poi `buy_pct 0.50→1.00`). Domanda legittima: ha senso modificare parametri così spesso?

**Diagnosi:**

- I 10 minuti tra messaggi Telegram sono il **throttling già implementato** (`TELEGRAM_THROTTLE_S=600s`), non la frequenza reale di proposta
- La frequenza reale di proposta è **ogni 120s** (loop Sherpa). In 10 minuti Sherpa propone 5 volte, ma ne mostra solo l'ultima
- Le piccole variazioni (es. `buy_pct 1.30 vs 1.00`) sono dovute a soglie nette nella drop ladder: il primo scalino `BTC -3% in 1h` aggiunge `+0.5% buy_pct`. Quando BTC oscilla intorno a `-3%` (es. -2.95% / -3.05%), Sherpa entra/esce dal regime → flicker

**Tre fix possibili (NON applicati in questa sessione, da decidere dopo i 7 giorni):**

| Fix | Costo | Effetto |
|---|---|---|
| **A.** Soglia significatività sul cambio (ignora variazioni < 0.3%) | ~10 righe | Elimina flicker piccolo, perde sensitivity |
| **B.** Isteresi sulle soglie ladder | ~25 righe | Stato regime stabile, niente flickering |
| **C.** Cooldown interno Sherpa per parametro/bot | ~15 righe | Cap N modifiche/h, perde reattività se cap basso |

**Raccomandazione:** aspettare i dati di 7 giorni prima di scegliere. Il counterfactual ci dirà se il flicker ha impatto reale sul P&L o no.

---

## 7. Cosa NON è stato fatto in questa sessione

Esplicitato per evitare che diventi debito implicito:

1. **Slow loop (Fear & Greed + CMC dominance):** Sprint 2, intoccato
2. **News + LLM:** Sprint 3, intoccato
3. **Script di replay counterfactual:** definita la strategia, codice da scrivere quando avremo i dati
4. **Fix A/B/C sul flicker parametri:** rimandato a post-7-giorni dati reali
5. **Pagina dashboard `/sentinel`:** non discussa, idealmente Sprint 2+
6. **Telegram heartbeat di "battito cardiaco":** scartato (rumore Telegram), preferito `tail -f` sul log file e query SQL
7. **Decisione passaggio a `SHERPA_MODE=live`:** nessuna decisione presa, brief dice "dopo 1-2 settimane di DRY_RUN + Board approval"

---

## 8. Plumbing: pulizia cartelle

Su suggerimento del Board: `report_for_CEO/resolved/` (analoga a `briefresolved.md/` per i brief). 17 report di sessioni passate (feature shipped, decisioni applicate) spostati. Restano 4 report attivi nella cartella principale, tra cui questo.

---

## 9. Roadmap impact

Sentinel + Sherpa Sprint 1 era nella roadmap come milestone Q2 — completato. Il `validation_and_control_system.md` è stato aggiornato col changelog di oggi (sezione 1: nuove tabelle DB, contratto DRY_RUN-default).

I file `roadmap.html`/`roadmap.ts` di `web_astro` non sono stati toccati: questo report è informativo ma non-shippable nel pubblico finché non passiamo a LIVE.

Sprint 2 e Sprint 3 restano nella loro posizione attuale (no advance, no slip).

---

## 10. Cosa chiede il CEO al Board

Niente di urgente. Tre decisioni in coda da prendere quando vorrai:

1. **Tra 24h** (dopo la pre-validation): confermare che i dati sono completi per il replay
2. **Tra 7 giorni**: decidere se applicare fix A/B/C sul flicker, e calibrare la base table di Sherpa se diverge troppo dal tuo intuito
3. **Tra 1-2 settimane**: decidere passaggio `SHERPA_MODE=live` (con o senza fix sul flicker)

Nessuna di queste è bloccante per niente. Sentinel/Sherpa girano in background, raccolgono dati, e Grid bot continuano coi loro parametri attuali. Se servisse fermare tutto, basta `kill` dei due processi e l'orchestrator riavvia automaticamente — il sistema è auto-contenuto.

---

**Commit di riferimento:**
- `83b253c` — Sentinel + Sherpa code (1471 righe, 14 file)
- `2ab349f` — Design docs + brief + validation update
- `da264fa` — symbol_price per replay counterfactual
- `0246b22` — Ottimizzazioni write rate (-90% bot_events_log)
