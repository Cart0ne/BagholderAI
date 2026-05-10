# S70b Report for CEO — /admin overhaul + Reconciliation Step B

**Data sessione:** 2026-05-10 (pomeriggio/sera)
**Modalità:** sessione interattiva guidata 1-cosa-alla-volta da Board (Max), CEO assente
**Scope dichiarato a inizio sessione:** "lavoriamo solo su admin.html, poi se abbiamo tempo e spazio lavoriamo con il CEO sul ripristino del sito online pubblico"
**Scope effettivo:** /admin completo, sito pubblico deferred a S70c.

---

## TL;DR

Pannello `/admin` rivisitato sezione per sezione. Otto interventi di leggibilità (mascot in titolo, dashed-overlay per linee sovrapposte, vertical jitter ±3px, scoring rules collapsable, Parameters history scala intera 0→max + asse Y destro live, BTC current price overlay, DB monitor live via RPC, Reconciliation Binance Step B con trade-by-trade compare). 3 migrations Supabase (RPC `get_table_sizes`, RLS policy + ALTER TABLE su `reconciliation_runs`). Script `reconcile_binance.py` esteso per popolare `matched_details` snapshot Binance↔DB.

Bot operativo invariato: ancora su commit `4324231`, restart 09:51 UTC. Tutto il lavoro è stato sul frontend `/admin` + database schema migrations.

Non shipped (deferred a **S70c**):
- Reconciliation Step C (cron Mac Mini notturno) — pre-requisito 2-3 run clean soddisfatto a 2/3, conservativi.
- Ripristino sito pubblico (homepage + nav) — necessita brief CEO dedicato.

---

## Cosa è cambiato in /admin (8 interventi)

### 1. Titolo unificato con pattern grid.html / tf.html
- Tolta antenna emoji 📡 dal titolo.
- Aggiunte mascot Sentinel + Sherpa fianco a sinistra del titolo, classe `.h1-mascot` identica a grid.html (`height: 1.6em`, gap 10px, drop-shadow tematico blu/rosso).
- Mascot da 28px nei `section-title` (riga sezione) lasciate invariate — non duplicate, complementari.

### 2. Sentinel 24h chart — overlay dashed per linee sovrapposte
- **Problema osservato:** Risk score (rosso) e Opportunity score (verde) coincidono numericamente a 20 (base score) per 197/197 record nelle ultime 24h, perché regime calmo (BTC ±0.5% in 1h) non scatta nessuna ladder. Il rendering disegnava prima il rosso, poi il verde sopra → vedevi solo verde.
- **Soluzione adottata:** linea Opp disegnata SOTTO con stroke 6px + dash `[6, 4]` + alpha 0.65; linea Risk SOPRA solid 1.8px alpha 1.0. Risultato: anche quando coincidono, i tratti verdi spuntano sopra/sotto la solid rossa creando un alone tratteggiato visibile. Pattern generale per "linee piatte coincidenti".

### 3. Reaction chart + 3 mini-chart Sherpa — vertical jitter ±3px
- **Problema osservato:** in regime "neutral" (Sprint 1 Sherpa) i 3 simboli BTC/SOL/BONK propongono identici buy_pct=1.0 / sell_pct=1.5 / idle=1.0h. 3 linee perfettamente sovrapposte = vedi 1 sola.
- **Soluzione adottata:** offset costante in pixel sull'asse Y per ogni simbolo (BTC -3px, SOL 0, BONK +3px). Distanza adiacenti 3px, totale 6px. Pattern standard TradingView/Plotly. Trade-off documentato in footnote: il valore Y disegnato è off di ±3px dal vero (~0.03 unità su scala 0.3-3.0 buy_pct, sotto la step 0.1 di Sherpa). Tabella sopra mostra valori esatti.

### 4. Scoring rules tables → collassabili native
- 21 righe Sentinel + ~30 righe Sherpa (BASE + ladder + ranges) sempre aperte = scroll fastidioso.
- Convertite a `<details>` / `<summary>` HTML nativi, chiuse di default. Zero JS, accessibili. Stilizzati per matchare `section-title` esistente (mono 12px uppercase, freccia `▶` che ruota a 90° quando aperta).
- **Verifica integrità:** confrontata tabella Sentinel HTML riga-per-riga con `score_engine.py` corrente — tutto allineato post brief 70b. Tabella Sherpa allineata con `parameter_rules.py` (Sherpa non è stato toccato in 70b, solo Sentinel). Nessun drift.

### 5. Parameters history (3 mini-chart) — rebuild completo
- **Problemi osservati da Max:**
  1. Etichetta "IDLE_REENTRY_HOURS" sfora i 110px del flex-basis label → il 3° canvas era shiftato a destra, asse Y disallineato vs gli altri due.
  2. Asse Y mostrava solo MIN e MAX (0.3 / 3.0, 0.8 / 4.0, 0.5 / 6.0), nessuna unità. Con valori live a 1.0/1.5/1.0, le linee sembravano "schiacciate al fondo" = poco leggibili.
  3. 3 linee BTC/SOL/BONK sempre coincidenti in regime neutral = una sola linea visibile.
- **Soluzioni applicate (proposta Board, accettata):**
  - Border-bottom tra `.param-row` (i 3 mini-chart sono valori indipendenti che non si incrociano mai → trattati come card distinte).
  - **Scala intera** sull'asse Y: yMin sempre 0, tick interi a ogni unità (0/1/2/3 buy, 0/1/2/3/4 sell, 0/1/2/3/4/5/6h idle). Suffisso "h" per idle. Linee orizzontali leggerissime di griglia ad ogni intero.
  - **Asse Y destro** con 3 valori live BTC/SOL/BONK colorati (legenda sotto resta per mapping colore→simbolo). Anti-collisione automatica: se due valori coincidono numericamente, vengono separati di 12px verticali, con clamping per non uscire dal plot area.
  - flex-basis label da 110px → 140px (capacità 20 caratteri mono 11px).

### 6. BTC current price overlay sul chart Sentinel 24h
- Richiesta esplicita Board: prezzo BTC corrente + 24h % in alto a sinistra del chart.
- Implementato come `<div class="chart-overlay">` HTML position:absolute sopra il canvas (no canvas text). Font-family mono, prezzo bianco bold 14px, change 11px verde se positivo / rosso se negativo. Aggiornato da `renderLastScan(row)` riusando i dati già letti da `sentinel_scores`.

### 7. DB monitor → live via RPC `public.get_table_sizes()`
- **Problema osservato:** array `tableSizes` hardcoded nel JS, snapshot pre-S70. Drift fino a -90% (`bot_state_snapshots` 3 MB hardcoded vs 0.3 MB reali post retention S69). `bot_events_log` -85%. `sentinel_scores`/`sherpa_proposals` +90% (4 giorni di scrittura in più). `reconciliation_runs` (creata in S70) assente.
- **Soluzione adottata:** migration `s70b_get_table_sizes_rpc` (SECURITY DEFINER, search_path '', stable, GRANT EXECUTE TO anon) che ritorna tablename + bytes + row_estimate per tutte le tabelle public. Helper `sbRpc()` aggiunto in admin.html. Render cambia: top 8 sempre ordinato corretto, fallback `~N` (estimate da `pg_class.reltuples`) per tabelle non in `tablesToCount`. Linter lamenta `anon_security_definer_function_executable` WARN — intenzionale, pattern coerente con `sentinel_scores INSERT anon`.
- **Conseguenza:** pannello DB monitor ora self-updating, niente più manutenzione manuale a ogni cleanup.

### 8. Reconciliation Binance Step B
- **Stato pre-S70b:** sezione era solo un commento HTML "TODO". Tabella `reconciliation_runs` esiste da S70 ma RLS abilitata senza policy SELECT → frontend bloccato.
- **Migrations applicate:**
  1. `s70b_reconciliation_runs_select_policy` (anon SELECT, coerente con sentinel_scores_select pattern; INSERT resta service-role-only via service_role key bypass RLS).
  2. `s70b_reconciliation_runs_matched_details` (`ALTER TABLE ADD COLUMN matched_details jsonb`).
- **Script `reconcile_binance.py` esteso:** popola `matched_details` con la lista completa Binance↔DB per ogni run (db_id, exchange_order_id, ts_ms, qty Binance/DB, price Binance/DB, fee Binance/DB, side). Storage stimato +2 MB/anno con cron daily — trascurabile.
- **Frontend:** sezione "⚖️ Reconciliation (Binance)" in arancione/amber tra Sherpa rules e DB monitor:
  1. Card "Latest run per symbol" — 3 righe sempre visibili (Bot, Last run age + ts, Status badge colorato, Bin/DB count, Matched, Drift, Notes).
  2. Collassabile "📊 Trade-by-trade compare (latest)" — tabella unica 12 colonne (ts/sym/side/qty Bin/qty DB/Δ% qty/px Bin/px DB/Δ% px/fee Bin/fee DB/Δ fee), ordinata per ts DESC, mix dei 3 simboli, deltas colorati (rosso se > tolleranza). Mostra l'ultimo run per ogni simbolo (concat dei matched_details).
  3. Collassabile "⚠ Drift details" — auto-shown solo se ci sono runs DRIFT/DRIFT_BINANCE_ORPHAN. Mostra JSON pretty-printed.
- **Run #2 lanciata stesso giorno** (Mac Mini SSH, 14:58 UTC): 3 righe scritte, 26/26 ordini matched (BTC 9, SOL 5, BONK 12), 0 drift, matched_details popolato.
- **Decisione design**: scelto approccio "salva matched_details in ogni run" (storage cresce ~2 MB/anno) sopra alternative A' (storage costante via UPDATE precedenti) e Z (tabella separata `reconciliation_orders`). Motivazione Board: "se Binance azzera senza avvisare, dovremmo essere coperti dalla regola che abbiamo discusso nella precedente sessione, se c'è un match che non torna lo deve segnalare in automatico" — history dei matched è valore d'archivio in caso di reset testnet.

---

## Decisions

**DECISIONE: scelto approccio A (matched_details in ogni run) sopra A' (solo latest per symbol) e Z (tabella separata).**
**RAZIONALE:** Board ha argomentato che storia dei matched è valore d'archivio in caso di reset testnet asimmetrico. +2 MB/anno = trascurabile su free tier 500 MB.
**ALTERNATIVE CONSIDERATE:**
- A': UPDATE matched_details=NULL su run precedenti, popolato solo per latest. Storage costante.
- Z: tabella separata `reconciliation_orders` con UPSERT per (symbol, exchange_order_id). Audit per-ordine.
**FALLBACK SE SBAGLIATA:** retention policy su `reconciliation_runs.matched_details` (es. NULL su run > 90 giorni) facilmente aggiungibile dopo, senza migration.

**DECISIONE: vertical jitter ±3px per linee sovrapposte (reaction chart + Parameters history).**
**RAZIONALE:** Board ha proposto esplicitamente il pattern come alternativa preferita ad alpha/dashed/spessori diversi. Pulisce visivamente e funziona indipendentemente dal numero di linee. Trade-off accettato: valore Y disegnato off di ±3px dal vero (~0.03 unità su scala buy_pct).
**ALTERNATIVE CONSIDERATE:**
- A) Trasparenza alpha 0.7: i colori si mescolano dove coincidono.
- B) Linee tratteggiate alternate.
- C) Spessori diversi con halo.
**FALLBACK SE SBAGLIATA:** rimuovere il jitter (1 riga di codice per chart). Linee tornano sovrapposte ma il rendering è onesto.

**DECISIONE: storia run history rimossa da pannello Reconciliation post-Board feedback.**
**RAZIONALE:** Board: "la run history secondo me non serve". Effettivamente la history dei run aggregati (5 colonne stato) è ridondante quando hai trade-by-trade compare e drift_details. La sezione "⚠ Drift details" già copre "ho avuto problemi qui qui qui" e si auto-mostra solo quando serve.
**ALTERNATIVE CONSIDERATE:** mantenere history collassabile chiusa di default.
**FALLBACK SE SBAGLIATA:** ripristinare il blocco HTML + JS (codice rimosso ma facilmente recuperabile dal commit precedente).

---

## Cosa NON ho toccato (per scelta)

- **bot Python**: zero modifiche al runtime. Solo `scripts/reconcile_binance.py` (che non è bot, è script ad-hoc di audit, lanciato manualmente o da cron — mai in-process del bot).
- **Sentinel ricalibrazione**: già fatta in 70b (commit `4324231`). Tabella admin scoring rules era già stata aggiornata a fine S70 (commit `40fdc4c`).
- **Sherpa parameter_rules.py**: non toccato in 70b né 70b. Tabella admin Sherpa rules verificata coerente con codice attuale Sprint 1.
- **Sito pubblico**: maintenance dal S65, ripristino richiede brief CEO dedicato.

---

## TODO per S70c (prossima sessione)

### Reconciliation Step C — cron Mac Mini notturno (~30 min)
1. Wrapper script `scripts/cron_reconcile.sh`:
   - cd `/Volumes/Archivio/bagholderai`
   - source venv
   - python3.13 scripts/reconcile_binance.py --write
   - log su `$HOME/cron_reconcile.log` (NON su /Volumes/Archivio per memoria `project_cron_mac_mini`)
2. Crontab entry: `0 3 * * * /Users/max/.../scripts/cron_reconcile.sh` (= 03:00 ITA = 01:00 UTC, prima della retention bot 04:00 UTC, così non si perdono trade del giorno appena chiuso).
3. Test manuale del wrapper (cron-context env minimale potrebbe non avere PATH/python).
4. Verificare TCC Full Disk Access se primo cron sul Mac Mini (memoria ricorda).
5. Run #3 organica domani notte = pre-requisito "2-3 run clean" soddisfatto formalmente.

### Ripristino sito pubblico — brief CEO necessario
- Sito in maintenance dal S65 (decisione 2026-05-08).
- Cosa serve riaprire pubblicamente: homepage + nav + decisione su quali pagine pubbliche tenere live (diary? library? roadmap? blueprint?).
- Cross-fertilization con /admin: pattern visivi (chart, scoring tables, mascot in titolo) ora consolidati e riusabili.
- Decisione strategica: cosa esponiamo con i numeri TESTNET ancora attivi? Aspettiamo go-live €100 (21-24 maggio) per riaprire? Oppure home minima con "behind the scenes" già ora?

### Brief separati ancora aperti (pre-mainnet)
- `sell_pct + slippage_buffer parametrico per coin` (estensione brief 70a)
- `Sherpa rule-aware sull'hotfix slippage` (pre SHERPA_MODE=live)
- `LAST SHOT path bypassa lot_step_size` (cosmetico ma pre-mainnet)
- `reason bugiardo su slippage` (cosmetico, open question 27 BUSINESS_STATE)

---

## Stato bot (invariato dal restart S70b)

- Mac Mini: orchestrator PID 2626 + 3 grid_runner + sentinel + sherpa, dal 09:51 UTC.
- Commit live: `4324231`.
- ENABLE_TF=false, ENABLE_SENTINEL=true, ENABLE_SHERPA=true (DRY_RUN, Telegram off via env flags).
- Sentinel scrive ogni 60s (3062 righe in 24h). Sherpa scrive ogni 120s × 3 simboli (4563 proposals in 24h).
- 0 trade aggiuntivi rispetto al run #1 di reconciliation (totale storico: BTC 9, SOL 5, BONK 12 = 26 ordini Binance).
- 0 drift su 26/26 ordini matched. Reconciliation funziona.

---

## Roadmap impact

**Phase 9 V&C — Pre-Live Gates:**
- ✅ **Wallet reconciliation Binance Step B** (pannello /admin) — shipped S70b.
- 🔲 **Wallet reconciliation Binance Step C** (cron notturno) — S70c.
- 🔲 Restanti gate invariati (slippage_buffer parametrico, sito online certificato, Board approval finale).

**Go-live €100 LIVE**: target ~21-24 maggio confermato. S70b non ha mosso la deadline.

---

*Report scritto da CC alla chiusura di S70b. Prossimo aggiornamento: PROJECT_STATE.md a fine S70c.*
