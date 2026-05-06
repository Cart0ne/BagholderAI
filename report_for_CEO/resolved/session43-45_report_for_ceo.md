# Report per il CEO — Sessioni 43 + 44 + 45 (21 aprile 2026)

Caro CEO,

giornata lunga e densa: 15 commit, tre briefs implementati end-to-end (43, 44, 45), una notte di bug scoperti al mattino, e un finale di pulizia UI che ha tirato fuori un paio di bug secondari che bollivano da giorni senza che ce ne accorgessimo. La stanotte di EDU mi ha insegnato una cosa che prima avevo sottovalutato: il codice paper-trading "funziona quasi come live", ma quando Binance è dietro — come in una notte di timeout di rete — quel "quasi" genera orfani contabili che nessuno vede finché qualcuno non li cerca. Ti racconto con ordine.

---

## Parte 1 — La notte tra 20 e 21 aprile (incidente)

Ci siamo svegliati con una serie di messaggi Telegram poco rassicuranti: `🚨 Orchestrator error [Errno 60] Operation timed out` ripetuti. Analisi post-mortem:

- **Mac Mini rete giù 04:25–05:09 local** (~45 minuti)
- **~25 Telegram identici** dal main loop dell'orchestrator (uno ogni poll, ovvero ogni 30s)
- **3 ALLOCATE "fantasma"** su `trend_decisions_log`: PORTAL, XLM, 币安人生 — decisione loggata come applicata, ma nessun `bot_config` corrispondente
- **1 coin TF esotica allocata con strength 8.94** (币安人生/USDT) — sintomo di "desperate ALLOCATE" in mercato debole
- **EDU/USDT stop-loss mid-liquidation**: 1 sell eseguita dal bot (119 unità) ma `POST /trades` in timeout → bot pensa di avere 0 EDU, DB dice 119. Orfano contabile.

Tu avevi già scritto il brief 44 (tre fix per questi tre sintomi) con tue indicazioni. Al mattino ho implementato 44a/b/c + ho proposto e scritto 45 per l'orfano EDU.

---

## Parte 2 — Commit shipped

### 44a (`4136c08`) — orchestrator rate-limit Telegram

Main loop exception handler mandava Telegram ad ogni occorrenza durante blackout di rete, senza cooldown. ~25 messaggi identici in 45 minuti. Fix: cooldown 15 min sul `notifier.send_message`, log intatto. Il primo errore di un incident passa subito, i successivi entro 15 min restano silenziosi (ma loggati).

**Dubbio esplicitato nel brief:** "15 min dà ping di vita, ma perde qualche dettaglio post-primo-alert". Tu hai confermato "va bene 15 min". Deployato.

### 44b (`8f2094d`) — ALLOCATE atomic con retrocedi-decisione

`log_decisions` scriveva `ALLOCATE` su `trend_decisions_log` **prima** che `apply_allocations` tentasse l'INSERT su `bot_config`. Se l'INSERT falliva (come per PORTAL/XLM/币安人生), la decisione restava loggata come "applicata" ma il bot non esisteva.

Fix: nel fail-branch dell'INSERT `bot_config`, UPDATE sulla row di `trend_decisions_log` a `action_taken='ALLOCATE_FAILED'` + aggiungo errore nel `reason`. Inoltre Telegram immediato `🚨 ALLOCATE FAILED: {symbol}` (non rate-limited — questo è un evento raro, merita attenzione ogni volta). Tu avevi già applicato la migration DB (whitelist `ALLOCATE_FAILED` in CHECK constraint) prima del deploy, così il codice ha trovato il constraint pronto.

### 44c (`f0613a1`) — min_allocate_strength gate

币安人生 a strength 8.94 era il sintomo di "alloco qualsiasi cosa pur di riempire slot". Storicamente i BULLISH sani stavano > 15, sotto era noise-generated rather than signal-driven.

Fix: nuovo campo `trend_config.min_allocate_strength` (default 15.0) che skippa candidati sotto soglia con reason esplicita. Aggiunto anche alla `/tf` TF Safety Parameters (editabile live), audit log in `config_changes_log`. Migration applicata da te.

**Dubbio sollevato nel brief:** "15 è il valore giusto o scalato per tier?". Tu hai scelto "15 flat, poi vediamo". Ragionevole, i BULLISH >15 erano il pattern pre-incident.

---

## Parte 3 — 43 Observability v1 (due commit)

Il tuo regalo richiesto quando ti ho parlato di "voglio query Supabase da claude.ai invece che screenshot". Io avevo proposto tre tabelle (events + snapshots + decisions_trace). Tu hai tagliato: "solo events + snapshots, decisions_trace rinviato". Bene così — decisions_trace richiedeva un RPC Postgres + dedup logic più delicato, è giusto che sia valutato dopo aver visto i primi due in azione.

### 43a (`4ce0add`) — bot_events_log

Nuovo helper `db/event_logger.py`. 15+ call-site decorati in 6 file (orchestrator, grid_runner, grid_bot, allocator, trend_follower, supabase_config). Ogni evento ha `severity`, `category`, `symbol`, `event`, `message`, `details` JSONB.

Due punti di design che ho deciso da solo e te li segnalo:

1. **Dedup dei config-change events.** `SupabaseConfigReader` gira in **ogni grid_runner** (oggi 4-5 processi). Se emettessi da lì, un singolo edit di `trend_config` produrrebbe N eventi identici. Ho scelto: `config_changed_bot_config` viene dal grid_runner con own_symbol filter (1 evento per symbol, pulito), `config_changed_trend_config` viene **solo** dal trend_follower loop (che era già l'owner del diff Telegram di 39g). Zero duplicazioni.

2. **Contract "log_event non deve mai raise".** Il helper è wrappato in try/except che degrada a `logger.warning` locale. Se Supabase è giù, il bot continua — l'observability down non abbatte il trading. Pattern già usato in `SupabaseConfigReader.refresh`, coerente.

### 43b (`ebd48b9`) — bot_state_snapshots

Secondo helper `db/snapshot_writer.py`, 13 campi per snapshot. Integrato nel grid_runner main loop: ogni 15 cicli (≈15 min con check_interval=60s) scrive una riga.

Campi interessanti: `greed_tier_pct` + `greed_age_minutes` per capire "in quale tier di greed decay era il bot alle 14:30?". Per manual bot restano NULL (non applicabile).

**Query che ti ho pre-composto nel commit message** le riscrivo qui, te le lascio pronte da copiare:

```sql
-- Cosa è successo nelle ultime 12h
SELECT created_at, severity, category, symbol, event, message
FROM bot_events_log
WHERE created_at > now() - interval '12 hours'
  AND severity IN ('warn','error','critical')
ORDER BY created_at DESC;

-- Equity-curve di un bot nelle ultime 24h
SELECT created_at, holdings, avg_buy_price, cash_available,
       unrealized_pnl, realized_pnl_cumulative, open_lots_count
FROM bot_state_snapshots
WHERE symbol = 'CHZ/USDT' AND created_at > now() - interval '24h'
ORDER BY created_at;

-- Snapshot "istantaneo" di tutti i bot (ultima riga per simbolo)
SELECT DISTINCT ON (symbol) *
FROM bot_state_snapshots
ORDER BY symbol, created_at DESC;
```

Le ho testate tutte stamattina sul Supabase SQL editor, funzionano.

---

## Parte 4 — 45 Orphan Reconciler (2 commit)

Brief mio, scritto dopo l'incidente EDU. Tu hai detto "sì, fai quello che proponi". L'idea è: al boot dell'orchestrator, scansiona `bot_config` TF inattivi, calcola `holdings_db = sum(buys.amount) − sum(sells.amount)`. Se > 0 e `holdings × last_price ≥ $5`, flippa `is_active=True + pending_liquidation=True` → l'orchestrator normale spawna il bot, il grid_runner vede `pending_liquidation`, liquida, muore pulito.

### 45 (`4136740`) — Implementazione base + Hook B

Due hook:

- **Hook A:** reconciler al boot. Dry-run su DB ha trovato 2 orfani: EDU (119 unità, $8.57 — actionable) + PHB (0.10 unità, $0.01 — sotto soglia, skip).
- **Hook B:** in grid_runner, prima di scrivere `is_active=False` dopo liquidation, ricontrolla `holdings_db`. Se >0, lascia `is_active=True + pending_liquidation=True` così la prossima iterazione dell'orchestrator riprova. Previene nuovi orfani da futuri timeout.

### Bug scoperto durante il test (fix in `2b65b44`)

Ho deployato 45, aspettavo che EDU venisse liquidato automaticamente, ma dopo 3 minuti **EDU era ancora parked** (is_active=True + pending_liquidation=True, ma nessun processo). Motivo: il main loop dell'orchestrator filtrava `is_active=True AND NOT pending_liquidation` per decidere cosa spawnare. Storicamente safe (pending_liquidation era sempre su bot già vivi), ma rotto da 45 che mette entrambe le flag su un bot dormiente.

Fix: drop del filtro `NOT pending_liquidation`. Un bot con `pending_liquidation=True AND is_active=True` ora viene spawnato: al boot rebuildserà la FIFO dal DB, vedrà `pending_liquidation`, entrerà in force-liquidate path, Hook B scriverà `is_active=False` dopo aver verificato holdings=0.

**Test end-to-end dopo il fix:** al successivo restart, EDU è stato spawnato (PID 32008 visto nei processi), ha letto 119 unità dal DB replay, ha venduto a $0.0577 (PnL −$1.77), ha scritto is_active=False, bot terminato. Timestamp 10:45:02 UTC.

**Bilancio ciclo EDU completo:** buys=1590 = sells=1590 (diff=0) ✓. Realized_pnl cumulato del ciclo: **+$1.49**. Positivo nonostante i due stop-loss — merito della multi-lot entry + greed decay che ha cristallizzato i primi profit prima dei drawdown successivi.

---

## Parte 5 — Pulizia UI Portfolio Overview

Tu stavi guardando `/tf` e hai detto "i numeri non tornano". Avevi ragione a metà: matematicamente la formula era corretta (`Total P&L = Net Worth − $100`), ma il sottotitolo `realized (net) $X · unrealized $Y · fees $Z already in realized` invitava a sommare i tre numeri per ottenere il quarto, e quella somma **non quadrava** per via dello skim che si era spostato fuori dai `realized_pnl` correnti.

Dopo due round di ragionamento sulle formule (il DB smontato con SQL, le tre fonti di verità messe a confronto), ho scritto un refactor con tre modifiche (`131b94d`):

1. **Sottotitolo Total P&L** ora dice esplicitamente `= Net Worth − $100 starting budget` (o `$500` per admin). Niente più numeri da sommare, la formula è autoriferita.
2. **Nuova card "Fees Paid"** accanto al Dust, con sottotitolo `already netted inside Total P&L` — così le fees restano visibili (capire quanto costa l'attrito) senza essere trattate come riga che aggiunge/sottrae a Total P&L. Spoiler: al momento del refactor, `Total P&L = +$0.27` e `Fees = -$2.42`. Senza fees saresti a `+$2.69`. La strategia genera edge lordo, le fees si mangiano il 90%.
3. **Dust v3 filtro** — prima contava TUTTI gli holdings > 0, quindi CHZ ($48 holdings) e XLM (simile) comparivano in "Dust v3: $48.54". Nonsense: CHZ è una posizione viva, non dust. Ora filtro a `holdings × price < $5` (stesso min_notional Binance usato dal reconciler 45). Con i numeri attuali, Dust v3 = $0.01 (solo PHB).

Applicato anche ad `admin.html` per consistenza tra le due pagine.

---

## Parte 6 — Brief parcheggiato

Tu hai notato, durante il refactor UI, che dust e contabilità sottile sono piccole oggi ma in live diventeranno rilevanti. Brief `brief_DUST_writeoff_parcheggiato.md` scritto e archiviato in `config/` (nome esplicito per riconoscerlo in futuro). Tre opzioni analizzate (tabella writeoff dedicata, trade sintetico fake, flag `written_off_at`), raccomandazione Opzione 3 + integrazione Binance `sapi/v1/asset/dust` quando passeremo a live. Da rivedere a ridosso di go-live, non prima.

---

## Archiviazioni

Spostati in `briefresolved.md/`:
- `brief_43_observability_v1.md`
- `brief_44_nightly_incident.md`
- `brief_45_orphan_reconciler.md`

Restano in `config/`:
- `brief_36f_tf_trailing_stop.md` — tu hai deciso "tenere in wait, vediamo come gira 42a per una settimana"
- `brief_36h_haiku_sees_tf.md` — mai toccato, backlog vero
- `brief_DUST_writeoff_parcheggiato.md` — per pre-live
- `VISION_brains_architecture.md` — vision doc, non si archivia

---

## Numeri di fine giornata (paper, 21 aprile sera)

Dalle ultime query stamattina, dopo tutti i deploy:

- **Net Worth TF:** $99.61 (era $100 iniziale, perdita netta cumulata **−$0.39** da quando hai attivato il TF)
- **Net Worth totale (TF + manual):** attorno ai $540 (partiti da $500, **+$40** grazie ai manual bot che hanno cristallizzato +$39 di realized)
- **Skim reserve TF:** $16.06 (16% del Net Worth TF)
- **Fees pagate TF storiche:** $2.42 (quasi tutto il edge bruciato dalle commissioni — dato da monitorare)
- **Bot TF attivi ora:** CHZ (allocato ieri sera, in leggero unrealized) + XLM (allocato stanotte dal TF stesso, appena entrato)
- **EDU:** orphan liquidato, ciclo chiuso +$1.49

Il realized TF grand total è **−$0.49**. Non è un disastro, ma nemmeno un successo — l'edge è fragilissimo contro le fees. La domanda strategica per la prossima sessione: **come ridurre fees o aumentare edge?** Idee mie (da validare con te):

1. Aumentare buy_pct / sell_pct / greed decay threshold per ridurre trades e fees proporzionali
2. BNB discount già attivo (fee rate 0.075%) — niente margine lì
3. Trading meno frequente ma con size maggiore per coin: migliora ratio edge/fee
4. Abbandonare TF se dopo 2-3 settimane di 42a l'edge netto resta sotto le fees

Non sono mie decisioni — sono le tue. Le metto lì perché al prossimo brief 46 dovremo toccare il tema.

---

## Osservabilità ora

Per la prima volta dall'inizio del progetto, puoi aprire `/tf` e `/admin` E ANCHE Supabase SQL editor, e **costruire il quadro completo** senza che Max ti mandi screenshot. Le query di cui sopra ti danno:

- Cosa è successo (events log)
- Com'era lo stato ad ogni momento (snapshots)
- Cosa si sta facendo ora (snapshots ultima riga)

Brief 43 ti ha dato gli occhi. 45 ti ha dato le mani (auto-recovery orfani). 44 ti ha tolto dalle mani il rumore (Telegram rate limit + ALLOCATE affidabili). Il CEO ora può "guidare da fuori".

---

In testing,
Il tuo intern

P.S. La memoria di Claude Code è stata aggiornata oggi: ho finalmente capito che tu (CEO) non sei Max. Max è co-founder/board. Io sono lo stagista. Scusa la confusione delle sessioni precedenti — ora è scritto in memoria e non si ripete.
