# BUSINESS_STATE.md — archive storico

File di archiviazione delle sezioni rimosse da `BUSINESS_STATE.md` durante
le compaction successive. Specchia `audits/PROJECT_STATE_archive.md` ma
sul piano strategico (decisioni Board/CEO, vincoli marketing, deadline
non-tecniche, domande aperte chiuse).

Single growing file: non viene letto a ogni sessione, ma serve come
fonte di verità on-demand quando si deve risalire al "perché abbiamo
deciso X in S65?" o "quale era la roadmap pre-pivot S68?".

Le entries sono in ordine cronologico di compaction (più vecchia in
alto). I primi due blocchi (S71 + S79) sono stati ricostruiti
retroattivamente dalla git history in S85 (2026-05-25), perché le
cancellazioni di quei brief erano avvenute prima dell'introduzione di
questa regola di compaction.

---

## Rimosso in sessione S71 (2026-05-11) — heavy cleanup CEO

Brief sorgente: `briefresolved.md/session71_business_state_update.md`
Commit di cleanup: `0ae0610` (213 deletions). Ricostruito da git diff
in S85 (2026-05-25).

### Header pre-S71 (versione S70)

**Last updated:** 2026-05-10 — Session 70 chiusura (sell ladder + net-of-fees, Sentinel ricalibrato, reconciliation 26/26, sito online, TF dal dottore, Haiku fix)
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-10 (S70c chiusura, commits 77d4090 + 6f653b5 + 4987328)

### §2 Marketing — versione pre-S71

**Post X S69+S70 (S70):** thread 2 post in coda (FIFO removal + testnet verified + site back online + TF hospitalized). 🤖+👤 firma. Da pubblicare stasera 2026-05-10.

**Sito online (S70c):** maintenance rimossa dopo 5 giorni. TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE colorati. Public dashboard certificata vs Binance.

### §3 Diary — versione pre-S71

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53+ in accumulo, **nessun lavoro attivo** (Board S68: "prima i fondamentali"). Stima grezza chiusura: sessioni 70–80.

**Sessione corrente:** 69 BUILDING (avg-cost trading completo + Strategy A simmetrico + cleanup FIFO/fixed mode totale). S68 diary "The One Where We Almost Quit" COMPLETE su Supabase, docx prodotto. Volume 3 outline: "Operation Clean Slate" (S65-S66) + "First Contact with Binance" (S67) + "The Pivot" (S68 minimum viable) + "FIFO Divorce" (S69 avg-cost migration + Strategy A) — climax narrativo costruzione/decostruzione tecnica.

### §4 Decisioni — 30+ voci storiche rimosse (S65/S66/S67/S68/S69/S70 e 2026-05-04→07)

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-10 (S70) | **Timer patience parcheggiato** | Servono dati reali dal sell ladder prima di calibrare un timeout |
| 2026-05-10 (S70c) | **Sito online con disclaimer testnet** | "Real orders, simulated money." Reconciliation pubblica come prova di trasparenza |
| 2026-05-10 (S70c) | **Haiku commentary prompt riscritto** | Day counter da 8 maggio, contesto post-reset, brain status esplicito |
| 2026-05-09 (S69) | **Avg-cost trading puro deployed** — trigger sell su avg_buy_price, FIFO queue rimossa, sell amount = capital_per_trade/price | Chiusura completa del debito FIFO. Dashboard, accounting, trigger ora tutti su avg-cost |
| 2026-05-09 (S69) | **Strategy A simmetrico: no sell below avg + no buy above avg** | Sell guard da S68a + buy guard nuovo. Ogni buy deve abbassare la media, ogni sell deve essere profittevole |
| 2026-05-09 (S69) | **IDLE recalibrate guard: skip se price > avg** | Impedisce al bot di riposizionare il buy reference sopra l'avg in mercati laterali/rialzisti |
| 2026-05-09 (S69) | **sell_pct net-of-fees DEFERRED** — Board | Max ha calcolato che le fee mangiano 37% del profitto lordo su BTC. Proposta parcheggiata: richiede decisione semantica + BNB-discount |
| 2026-05-09 (S69) | **No DELETE Supabase pre-restart** — Board | Bot ripartito sopra DB esistente. Fossili BONK pre-S68a restano come record storico |
| 2026-05-09 (S69) | **DROP COLUMN bot_config × 5** (grid_mode, grid_levels, grid_lower, grid_upper, reserve_floor_pct) | Schema cleanup fixed mode. DDL eseguito da CC via Supabase MCP |
| 2026-05-09 (S68) | **Filosofia "Trading minimum viable"** — Board | Complessità solo se valore aggiunto. 67 sessioni hanno accumulato debt strutturale (22 tabelle, 4 brain, 1627 righe in singolo file, 90 notifiche/notte). Restart concettuale del trading subsystem |
| 2026-05-09 (S68) | **Grid only, brain off (TF/Sentinel/Sherpa stay-but-off, codice non cancellato)** — Board | Coerenza con minimum viable. Niente ricollegamento finché Grid non gira pulito |
| 2026-05-09 (S68) | **Fix sell-in-loss guard: confronto su avg_buy_price anziché lot_buy_price** (brief 68a shipped) — CEO | Doppio standard FIFO+avg-cost causava sell in loss strutturali. Evidenza: BONK sell 2026-05-08 22:56 UTC realized −$0.152 |
| 2026-05-09 (S68) | **Guard only, trigger per-lot invariato: no cambio regime strategico** — CEO | Vincolo "non toccare grid_bot.py" in S68a. Trigger sell rimasto FIFO ma guard avg-cost blocca tentativi vuoti |
| 2026-05-09 (S68) | **DB cleanup: DROP feedback + sentinel_logs + portfolio + 2 view orfane + DELETE 54 bot_config inactive** — Board | "Niente backup, capitale paper, tabelle vuote o dichiarate temporanee". 22→19 tabelle, 2→0 view |
| 2026-05-09 (S68) | **No nuove feature finché le esistenti non funzionano** (confirmation timer parcheggiato) — Board | Disciplina del minimum viable: no scope creep |
| 2026-05-09 (S68) | **Mainnet €100 target confermato, timeline 21-24 maggio 2026** — Board | Invariato post-pivot, nonostante slip da fix 68a + brainstorming |
| 2026-05-09 (S68) | **Refactor 68b (folder rename + managed_by cleanup) shipped ma non applicato su Mac Mini** — Board pending | Cosmetico, può aspettare insieme al prossimo restart bot |
| 2026-05-09 (S69) | **FIFO contabile rimosso da tutte le dashboard + commentary + health check** (BLOCCO 1 B+C shipped) — CEO/Board | Dashboard pre-S69 mentivano (FIFO replay client-side ricostruiva una formula non più scritta dal bot post-S66 avg-cost). Coerenza totale bot ↔ dashboard ↔ Binance |
| 2026-05-09 (S67) | **Brief 67a Step 2-4 SHIPPED: testnet live** | Dust prevention + ccxt order execution + DB reset + restart $500 Grid-only. Prima connessione reale a Binance nella storia del progetto |
| 2026-05-08 (S67) | **Fee design: opzione A (USDT-equivalent canonical)** | Il primo BONK buy ha mostrato −$3,419 P&L (raw 3,419.97 BONK letto come USDT). Una sola fonte di verità in USDT per dashboard/P&L/reconciliation |
| 2026-05-08 (S67) | **ccxt confermato come libreria Binance** (brief diceva python-binance) | Codebase già dipende da ccxt (TF, scanner, counterfactual). Zero rework |
| 2026-05-08 (S67) | **$500 testnet, stesso schema paper** | Max: "soldi finti, nessun motivo di downscalare". Più volume = più dati per validazione |
| 2026-05-08 (S67) | **Sito resta in maintenance 24h** | Osservazione testnet pulito prima di rimettere numeri pubblici |
| 2026-05-08 (S67) | **OP/ZEC/TRX is_active=false, non cancellati** | Spawned per errore al primo restart, archiviati |
| 2026-05-08 (S67) | **Brain off per testnet shake-down** | TF/Sentinel/Sherpa disabilitati via env flags. Grid-only isola la variabile testata |
| 2026-05-08 (S66) | **Operation Clean Slate: stop bot, liquidazione totale, audit, fix, restart da zero** | Max: "vendere tutto, verificare le formule, ripartire". L'eredità di 458 sell fossili con bias rendeva ogni fix un rattoppo. Liquidazione SQL bypass, snapshot, verifica formule su dataset chiuso |
| 2026-05-08 (S66) | **Fix avg-cost canonico shippato (1 riga in 2 funzioni)** | Il buy_pipeline aveva già la formula corretta. Il sell_pipeline la ignorava e faceva walk-and-sum della queue (codice 53a). Fix chirurgico, test 5/5 verdi, identità chiude al centesimo su 50 ops random |
| 2026-05-08 (S66) | **Strict-FIFO queue non più usata per realized_pnl** | La queue resta viva solo per la logica decisionale (Strategy A "no sell at loss"). La contabilità usa solo avg_cost + holdings |
| 2026-05-08 (S66) | **Maintenance page + post X "self-roast" pubblicato** | 🤖 AI + 👤 CO-FOUNDER. "An AI that can trade but can't read its own report card" |
| 2026-05-08 (S65 fine) | **Sito offline / pagina maintenance** finché numeri non sono verificati su testnet | Max: "i numeri stanno mentendo al pubblico". Total P&L è matematicamente coerente con Net Worth, ma finché non verifichiamo che la convenzione contabile coincide con Binance non possiamo affermare "≡ Binance live". Sito torna su con numeri certificati post brief 65c testnet |
| 2026-05-08 (S65) | **Brief 60b RISPECIFICATO: avg-cost pulito, NON strict-FIFO** | Max ha intuito durante la sessione che Binance usa avg-cost, non FIFO. Il bot già usa avg-cost ma implementato male (bias +28% Grid perché l'identità contabile non chiude). Fix = stessa formula fatta bene, allineata a Binance. Strict-FIFO era un overlay nostro arbitrario, abbandonato |
| 2026-05-08 (S65) | **Brief 65c NUOVO: migrazione paper → Binance testnet** PRIMA di brief 60b | `config/settings.py:21` ha già `TESTNET=true` ma il bot bypass-a in `exchange.py:8-11` (commento legacy). Riattivare path testnet (1-2h) → ordini eseguiti contro Binance vero (soldi finti) → Binance scrive il SUO realized_pnl → confronto diretto con il nostro DB → risposta definitiva sulla convenzione. Sblocca il brief 60b informato invece di a tentoni |
| 2026-05-08 (S65) | **Opzione 3 approvata: dashboard mostrano SOLO Total P&L** (Net Worth − budget). Realized DB spostato in /admin Reconciliation come audit interno | Le 4 dashboard mostravano 3 numeri diversi (gap fino a $26); Total P&L è l'unico immune al bias avg_buy_price e matematicamente verificato. Il sito ora è offline ma il codice è pronto per quando torna su |
| 2026-05-08 (S65) | **Mascotte Sentinel (blu) e Sherpa (rosso) approvate** | SVG prodotti con Claude Design. Brief 65b per integrazione CC, da fare post-numeri-fixati |
| 2026-05-08 (S65) | **Schema drift `reserve_ledger.managed_by` fixato in DB** via JOIN su trade_id (181 righe migrate). Rename `manual → grid` su tutto il sistema **parcheggiato** post-go-live | Coerenza interna ledger ↔ trades. Rinomina su 4 tabelle è troppo invasiva durante DRY_RUN Sherpa |
| 2026-05-08 (S65) | **Strict-FIFO replay rimosso da dashboard pubbliche** | Era la causa di tutti i gap P&L delle ultime 5 sessioni. Mantenuto solo in /admin Reconciliation come audit, ma con framing aggiornato: "due convenzioni a confronto" non "FIFO è il vero numero" |
| 2026-05-08 (S65 prep) | Workflow "CEO scrive diary da mega-brief CC" validato | Prima sessione operativa senza CEO. CC produce report strutturato, CEO produce diary. La review Board ha intercettato un leak di credenziali nel draft — il ciclo funziona solo con review umana |
| 2026-05-07 (S63 chiusura) | Dashboard `/admin` Sentinel+Sherpa+DB GO LIVE in 1 sessione (read-only, password-gated) | Sblocca osservabilità del sistema senza toccare i bot. Caccia bug guidata Max ha rilevato 5 anomalie in 30 min |
| 2026-05-07 (S63) | 5 bug rilevati grazie alla dashboard: `speed_of_fall` miscalibrato + risk binario + opp morta + Grid polling 60s + Supabase 1000-cap home latente | Tutti documentati in PROJECT_STATE §5. 3 di calibrazione Sentinel rendono il replay counterfactual probabilmente cieco — vedi §6 |
| 2026-05-07 (S63) | WebSocket Binance parcheggiato a "post €100 quando guadagneremo milioni" | Polling REST 60s perde wick BTC ~1.2%. Refactor 470 righe non giustificato a paper trading. Mitigazione pre-mainnet: ridurre check_interval BTC 60s→20s |
| 2026-05-07 (S63) | Strategia long-term Supabase 1000-cap su `trades`: paginazione, NON checkpoint table | Paginazione = 30 min, zero migration. Checkpoint prematuro pre-50k trade (fossilizza FIFO ancora in scoperta bug). VIEW server-side scartata (rompe FIFO unique source) |
| 2026-05-07 | Audit protocol introdotto: `PROJECT_STATE.md` + `BUSINESS_STATE.md` + cartella gitignored `audits/` | Continuità multi-sessione/multi-macchina. Primo canale formale per audit esterni (commits `57aff52`, `e20704c`) |
| 2026-05-07 | Grid Phase 1 completata: split monolite 2200 righe → 6 moduli, zero cambi di comportamento | Prerequisito per Phase 2 (fix 60c + dust). API pubblica `GridBot` invariata (commit `be45fca`) |
| 2026-05-07 | Dashboard admin Sentinel+Sherpa: design approvato, implementazione bloccata | ~9h frontend, ma toccare costanti Grid durante DRY_RUN invalida il counterfactual. Sbloccato post replay (~13 maggio) |
| 2026-05-07 | FIFO-correct P&L per-row nelle dashboard `/admin`, `grid.html`, `tf.html` (60d/60d-bis) | Le tabelle leggevano `realized_pnl` DB (biased) anziché FIFO client-side (commits `0750027`, `21caff0`) |
| 2026-05-06 | Sentinel + Sherpa Sprint 1 deployed (DRY_RUN) | Terzo e quarto cervello operativi. Raccolta dati per counterfactual. Nessun impatto su trading finché `SHERPA_MODE` resta `dry_run` (commit `83b253c`) |
| 2026-05-06 | Dust management: Opzione 3 (prevenire alla fonte + safety net Binance API) | Grid eviterà di creare dust (Phase 2). Safety net: dust converter settimanale post-go-live |
| 2026-05-06 | Sentinel/Sherpa write rate -70% via dedup + filter + retention 30/60gg | Tabelle nuove rischiavano di esplodere il piano Supabase free (commit `0246b22`) |
| 2026-05-05 | Validation & Control System creato (S59), promosso a living milestone | 8 sezioni, specchiato in Phase 9 roadmap. §7 post-go-live + §8 log hygiene aggiunti |
| 2026-05-05 | Osservazione 7 giorni FIFO + health check avviata | Pre-live gate. Il refactoring Grid resetterà il conteggio dei 7 giorni clean |
| 2026-05-05 | httpx/telegram loggers a WARNING in tutti gli entry-point | 23 MB di log con token Telegram in chiaro per 19 giorni. Root cause: httpx loggava ogni long-poll (commit `bbc8477`) |
| 2026-05-05 | Report Equity P&L vs FIFO realized (CC) | Gap strutturale $4.53. **DECISIONE CEO PENDENTE — vedi §6** |
| 2026-05-04 | Fix exit protection holes (trailing peak reset + SL/TP su open value) | DOGE/INJ venduti per peak/base stale (commit `6dcc56f`) |

### §5 Domande aperte — voci con strikethrough / chiuse / superate, rimosse in cleanup

**[S70 Board open questions]**
**[S68 Board open questions]**
**[S69 risolte fine giornata 2026-05-09]**
1. ✅ **Data deploy brief 69a**: entro oggi 2026-05-09 (Board confermato).
2. ✅ **Reset mensile testnet Binance**: confermato dal sito Binance Testnet (~1/mese, no preavviso, API keys preservate post-Aug 2020). Non bloccante.
3. 🟡 **Reconciliation gate (67a Step 5) + Reconciliation Binance (DB ↔ `fetch_my_trades`)**: rimandati a **nuovo brief CEO in preparazione** che probabilmente unifica i due topic.

**[S65/S67 legacy open questions]**
1. **Equity P&L nella home** — proposta 1 del report CC 05/05: secondo numero "Equity P&L" affiancato al FIFO realized. Stima CC: 1–2 ore. Aspetta decisione CEO (§6).
2. ~~**Allineamento sell-decision a FIFO globale**~~ — **SUPERATA in S65, FIXATA in S66**. Il sell_pipeline ora usa avg_cost canonico. La queue resta solo per logica decisionale (Strategy A "no sell at loss"). Identità contabile chiude al centesimo (test 5/5 verdi).
3. **Log file size monitor + log rotation** — §8 del Validation System. Stima CC: 2–4 ore. Brief separato, bassa priorità finché Phase 2 Grid è in corso.
4. **Schema verification automatica** — §1 Validation System, TODO. Confronta colonne DB con aspettative codice.
5. **Surface coherence checks** — §2 Validation System: homepage = dashboard = Telegram P&L. Tutto TODO. Da brief-are dopo stabilizzazione numeri post-Phase 2.
6. **Tradermonty full-repo scan** — parcheggiato. Solo 5 skill su 15+ valutate. Riprendere per Sentinel Phase 3 / TF improvements (brief `evaluate_trading_skills.md`).
7. **Esposizione pubblica Validation System** — il documento è milestone viva su /roadmap ma il contenuto è interno. Quanto esporre pubblicamente? Da decidere quando si apre una pagina pubblica dedicata.
8. **Sherpa Sprint 2** — slow loop (Fear & Greed + CMC dominance + regime detection). Pre-requisito: replay counterfactual Sprint 1 fatto. Schedulato post-2026-05-13.
9. **Sherpa Sprint 3** — news feed (CryptoPanic) + LLM Haiku classification. Idea Apple Note CC 2026-05-06, non ancora analizzata. Da brief-are post-Sprint 2.
10. **Fix flicker Sherpa (A/B/C)** — decisione pending dopo 7gg di dati reali. Apple Note CC 2026-05-06.
11. **Calibrare BASE_TABLE Sherpa** — se troppo distante dai parametri Board. Apple Note CC 2026-05-06. Da valutare dopo replay.
12. **Investigare recalibrate-on-restart** — a ogni restart orchestrator scatta recalibrate su tutti i Grid. Sospetto trigger condition troppo aggressiva. Apple Note CEO 2026-05-07. Da indagare quando si torna sul codice Grid.
13. **TF distance filter 12% fisso** — paralizza TF in mercato rialzista (0 swap da giorni, candidati 20-47% sopra EMA20). Valutare soglia dinamica/regime-aware. Apple Note CEO 2026-05-07. Cross-tema con Sentinel/Sherpa.
14. **Rework comm Telegram post-dashboard /admin** — solo errori critici + buy/sell real-time in Telegram; tutto il resto (scan TF, skip, block, drift, health check) solo DB. Report serale aggregato. Apple Note CEO 2026-05-07. Da brief-are dopo /admin live → **`/admin` ora è live**, prossimo step naturale da schedulare.
15. **[S63] Brief 60e — paginazione home/dashboard pubblica** (NEW imminente, deadline ~2026-05-17): TF passerà 1000 trade prima di quella data, oltre la quale la home mostrerà numeri silenziosamente sbagliati. Soluzione concordata: `sbqAll()` con Range header (pattern già implementato in `admin.html` stasera). Stima ~1h.
16. **[S63] Sostituire emoji con `<BotMascot>` zainetti su /grid /tf /admin** (sessione futura): coerenza visiva + possibile apertura futura a pagine pubbliche read-only. Approccio: convertire `public/*.html` → `src/pages/*.astro`. Stima ~1.5h. Decisione narrativa pendente: in `/admin` mostrare Sentinel/Sherpa "accesi" o tenerli "LOCKED" finché non passano a `live`?
17. **[S63] Sezione "Growth & Retention" in DB Monitor `/admin`** (sessione futura, ~30 min): tasso scrittura, estrapolazione capacità, salute retention con marker `⚠ over`/`⚠ under`. Documentato in `docs/admin-dashboard-guide.md` come TODO.
18. **[S63] Documento architetturale "trades-checkpoint long-term"** (futuro, quando saremo a 30k+ trade): formalizzare la struttura tabella aggregati + trigger Postgres + protocollo di ricalcolo da zero in caso di bug FIFO retroattivi. Per ora paginazione basta.
19. **[S65 NEW] Rename `manual` → `grid` su tutto il sistema** (parcheggiato post-go-live): standardizzare nomenclatura `bot_config.managed_by`, `trades.managed_by`, `reserve_ledger.managed_by`, `daily_pnl.managed_by` da `manual` (legacy v3) a `grid` (4 tabelle DB + bot Python + dashboards). Stima ~2-4h. NON durante DRY_RUN Sherpa. Finestra utile: post-Phase 2 stabile + post-go-live €100.
20. ~~**[S65 NEW] Brief 65c — migrazione paper → Binance testnet**~~ — **SUPERATA in S67** (shipped come parte di brief 67a Step 3, ccxt set_sandbox_mode + place_market_buy/sell + fee USDT canonical).
21. ~~**[S65 NEW] Brief 60b respec — avg-cost pulito nel bot**~~ — **SUPERATA in S66** (shipped come parte di Operation Clean Slate Step 1, test 5/5 verdi, identità chiude al centesimo).
22. **[S65 NEW] Reconciliation gate (nightly script)** — proposto come task Validation System: script su Mac Mini che ogni notte verifica `Realized_avg_cost + Unrealized = Total P&L` al centesimo, alert Telegram se gap > $0.01. Stima ~2h. Da implementare insieme/post brief 60b, gating soft per future regressioni.
23. **[S66 NEW] Aggiornare `tests/test_pct_sell_fifo.py`** — assertion sul realized_pnl cambiate dopo pivot avg-cost. Non gating, non in CI. Manutenzione.
24. **[S67 NEW] exchange_order_id null su sell** — sell OP/USDT non ha popolato il campo. Fix proposto: fallback clientOrderId. ~30min.
25. **[S67 NEW] Recalibrate-on-restart** — buy_pct cambia spontaneamente. Da indagare: Sherpa scrive in bot_config durante DRY_RUN?
26. **[S67 NEW] BNB-discount fee future-proof** — se in mainnet usiamo BNB per sconto 25%, `fee_usdt = 0` quando fee_currency=BNB. Gap trascurabile su €100 ma da risolvere prima dello scale-up.
27. **[S67 NEW] Reason bugiardo su trade con slippage** — quando un market order ha fill_price diverso dal check_price (book sottile, slippage testnet), il `reason` del trade riporta "dropped X% below last buy" usando il **fill_price** invece del check_price. Esempio BONK 2026-05-08 19:49 UTC. L'execution è economicamente corretta, è solo la stringa di motivazione che mente. Cosmetico, non gating.
28. **[S68 NEW] Phase 2 split di `bot/grid_runner.py`** — il file ha raggiunto 1627 righe, di cui 833 in una singola funzione `run_grid_bot()` (main loop). Split proposto: `runner.py` + `runner_config_sync.py` + `runner_force_liquidate.py` + `runner_cycle_summary.py` + `runner_telegram.py` + `runner_status.py`. Stima ~3-4h. Da fare DOPO go-live €100 mainnet. Parcheggiato come "Phase 2 grid_runner split".

### §6 Vincoli — versione pre-S71

**Go-live €100 — target confermato 21-24 maggio 2026** (invariato Board S68→S70). Sito **ONLINE** dal S70c (2026-05-10) con disclaimer testnet + Reconciliation pubblica.

**Orchestrator restart eseguito S70c sera (2026-05-10 21:45 UTC)** — PID parent 4795. Nuovo prompt Haiku attivo da prossimo run 18:00 UTC (Day 4 testnet). Caffeine GUI Max-side previene macOS sleep.

**Pre-requisiti go-live (versione S67 chiusura):**
1. ✅ Opzione A (DB-based dashboards)
2. ✅ Opzione 3 (dashboards mostrano solo Total P&L)
3. ✅ Schema drift skim fixato
4. ✅ Brief 66a Step 1 (fix avg-cost)
5. ✅ **Brief 66a Step 2** (dust prevention) — shipped S67
6. ✅ **Brief 67a Step 3** (testnet order execution via ccxt) — shipped S67
7. ✅ **Brief 66a Step 4** (reset DB + restart $500 testnet) — shipped S67
8. ⬜ **Brief 66a Step 5** (reconciliation gate nightly) — S68
9. ⬜ 24h testnet observation clean — in corso (fino 2026-05-09 21:15 UTC)
10. ⬜ Sito di nuovo online con numeri certificati su testnet
11. ⬜ Board approval finale (Max)

**Removed/downgraded prerequisites (decision CEO 2026-05-08):**
**Pre-live gates (Validation System — aggiornamento S69):**

**Obiettivo go-live**: dimostrare che gap dashboard ↔ Binance ≤ 5%. Con bot biased (no brief 60b) il gap sarebbe ~28%, fuori soglia. Con brief 65c testnet, sapremo davvero se il bot oggi è già allineato a Binance o quanto deve migrare.

**Sito offline:** decisione confermata S67 — resta in maintenance fino a 24h testnet pulito (domani sera).

**Decisione pendente ricalibrazione Sentinel:** bundled in Step 4 pre-restart come da PROJECT_STATE, ma Sentinel è OFF (env flag). Da applicare quando ricolleghiamo i brain.

**~~⚠️ DECISIONE PENDENTE — Equity P&L vs FIFO realized~~ — RISOLTA in S67.** Strict-FIFO abbandonato in S65. Avg-cost canonico shipped in S66. Fee USDT canonical in S67. Tutta la sequenza che era oggetto del gap è ora chiusa: dashboard, P&L, reconciliation tutti su un'unica fonte di verità (avg-cost + fee USDT-equivalent).

**DRY_RUN Sherpa:** raccolta dati ~7 giorni (start ~6 maggio, deadline implicita ~13 maggio). Durante questa finestra: NON modificare costanti Grid/Sentinel. Admin dashboard Sentinel+Sherpa read-only **già live (S63)**. Decisione `SHERPA_MODE=live` = 1–2 settimane + Board approval. Percorso indipendente dal go-live €100.

**⚠️ DECISIONE STRATEGICA PENDENTE — Ricalibrazione Sentinel pre-replay vs post-replay (S63):**
I 3 bug calibrazione Sentinel rilevati 2026-05-07 grazie alla dashboard `/admin` (`speed_of_fall_accelerating` miscalibrato + risk score binario + opportunity score morta — vedi PROJECT_STATE §5) **rendono il replay counterfactual del 13 maggio probabilmente cieco**: Sherpa avrebbe proposto cambi guidati da segnali sbagliati, e il replay dimostrerebbe poco. Due opzioni:
**Raccomandazione CEO (da decidere):** opzione (a) sembra più razionale, ma richiede di accettare che SHERPA_MODE → live slitti di 1-2 settimane oltre il 13-14 maggio originale. Decisione strategica del Board.

**Multi-macchina:** MBP (sviluppo Max) ↔ Mac Mini (runtime `/Volumes/Archivio/bagholderai`). Sempre `git pull` + mount Archivio prima di test/audit.

### §7 Cosa NON sta succedendo — voci duplicate pre-cleanup (23 righe → 10)

| Cosa | Perché no (versione pre-S71) |
|---|---|
| **TF trading attivo** — S70 | Spento, in "osservazione" (dal dottore). Richiede brainstorming completo pre-riaccensione. Vedi `config/TF_RESTORE_INSTRUCTIONS.md` |
| **Volume 3 in lavorazione** — S70 | Non iniziato. Materiale si accumula (S65→S70 è un arco narrativo forte: Clean Slate + Testnet + FIFO Divorce + Sell Ladder + Hospital) |
| **X scanner automation evoluta** — S70 | Parcheggiato. Priorità è go-live mainnet 21-24 maggio. Posting manuale flag-it-when-it-happens funziona |
| **Marketing outreach attivo** — S70 | Parcheggiato fino a sito stabile con numeri mainnet. Sito testnet online è step 1, mainnet è step 2 |
| **Marketing zero attività** (sito offline, niente post X, niente outreach) — S68 update | "Prima i fondamentali" (Board). Pre-traction. Il prodotto (story) è in costruzione. Spingere traffico ora = mostrare un cantiere incompleto |
| **Sentinel/Sherpa/TF spenti, codice presente ma inattivo** — S68 | Filosofia minimum viable: solo Grid attivo finché non gira pulito |
| **Vendite Payhip 0/30 views** — S68 | Invisibilità (sito offline + zero canale promozionale), non difetto del prodotto |
| **Reconciliation gate Step 5 parcheggiato** — S68 | Era in scope S68 ma superato dalla priorità sell-in-loss guard. Candidato 69a o post |
| **Phase 2 Grid split (`grid_runner.py` 1627 righe)** — S68 | Parcheggiata post-go-live |
| **Pannello Reconciliation FIFO in `/admin`** — S69 | Rimosso (audit S65 obsoleto post-S66 avg-cost). Sostituito da TODO Reconciliation Binance brief futuro post go-live |
| **Health check FIFO Check 1+2** — S69 | Rimosso ("non voglio più sentire parlare di FIFO" — Board) |
| **Nessun marketing attivo** | Pre-traction. Il prodotto (story) è in costruzione. Spingere traffico ora = mostrare un cantiere incompleto. Strategia flag-it-when-it-happens |
| **Nessun Volume 3 in lavorazione** | Le sessions 53+ sono in corso. Il volume si chiuderà naturalmente su un arco narrativo chiuso |
| **Nessuna dashboard /sentinel pubblica** | Sprint 2+. DRY_RUN non ha dati sufficienti per un'interfaccia utile. Design approvato, codice bloccato fino a post-replay (~13 maggio) |
| **Nessun Sentinel slow loop (F&G + CMC)** | Sprint 2. Sprint 1 (fast loop BTC + funding) deve raccogliere dati e fare replay counterfactual prima |
| **Nessun go-live €100** | Pre-live gates non superate. Phase 2 Grid ancora da fare. Architettura completa (TF + Sentinel maturo + orchestrator superiore) richiede mesi, non settimane |
| **Nessuna partnership esterna** | Il progetto non ha traction. Prematuro cercare partner senza prodotto finito e traffico organico |
| **sell_pct net-of-fees** | Proposta Max parcheggiata: richiede decisione semantica (sell_pct lordo→netto) + parametrizzazione FEE_RATE per BNB-discount. Brief separato pre-mainnet |
| **Strict-FIFO come sistema di trading** | Abbandonato definitivamente in S69. fifo_queue.py cancellato dal repo. Closed. |
| **Sito pubblico online** | In maintenance da S65. Riapriamo dopo 24h testnet pulito (decisione CEO S67) |
| **Nessun cambio prezzo volumi** | €4.99 è il prezzo di lancio. Nessun dato di vendita su cui ragionare |
| **BTC in portafoglio live** | Costi di conversione USDT→BTC troppo alti per budget €100. Decisione differita |
| **Audit esterni** | Protocollo appena introdotto (S63). Primo audit previsto: V1 Calibration su Sentinel↔Sherpa↔Grid post-Phase 1. Nessuno completato ancora |

*Footer pre-S71: Prossimo aggiornamento: post deploy 69a o alla prossima sessione strategica.*

---

## Rimosso in sessione S79 (2026-05-18) — §4 decisioni più vecchie da tagliare

Brief sorgente: `briefresolved.md/session79_business_state_update.md`
Commit di cleanup: `7945b54`. Ricostruito da git diff in S85 (2026-05-25).

### Header pre-S79 (versione S78 fase 2)

**Last updated:** 2026-05-16 — Session 78 fase 2 (CEO strategy + blog, CC diagnostic + slippage buffer fix). Sessione 78 estesa: fase 1 = 2026-05-15 (primo blog post + tweet lancio + reply strategy + GSC + HN + audit Area 3), fase 2 = 2026-05-16 (blog post 2 LIVE + SWEEP/LAST SHOT slippage buffer 3% shipped + restart Mac Mini + cover evolution memo).
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-16 (S78 chiusura fase 2, ultimo commit `25541b9`)

### §2 Marketing — versione pre-S79

**Sito online:** TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE. Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped).

### §3 Diary — versione pre-S79

**Diari completi:** fino a S78.
**Backlog diary:** S78 = no diary (session notes only). Nessun arretrato.

### §4 Decisioni — voci S76-S78 rimosse per restare entro 15 voci

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-15 (S78 fase 1 CEO) | **Primo blog post pubblicato (anticipato dal weekend 17-18)** | Origin story dual-voice già scritta e approvata. Brief 78a operativo (no testo touch, solo copy+build+push). Anticipa il "blog weekend" del Board, libera il weekend per Post 2 strategico ("why not live yet") |
| 2026-05-15 (S78 fase 1) | **Primo blog post = origin story a due voci (Max + CEO), non update strategico** | I lettori nuovi devono sapere chi siamo prima di interessarsi a dove siamo |
| 2026-05-15 (S78 fase 1) | **Reply strategy > posting frequency su X** | Il dato Montemagno (358 imp da una reply vs 78 media post) guida la nuova strategia. Vedi audit Area 3 marketing+SEO+X |
| 2026-05-15 (S78 fase 1) | **Tweet lancio blog: Opzione B (hook ironico)** | Scelta dal Board tra le opzioni presentate |
| 2026-05-14 (S77) | **Sentinel Sprint 1 audit PASS** | Tutti e 3 i bug calibrazione confermati fix (SoF 2.3%, risk 5 valori, opp 3 valori). Nessun codice aggiuntivo necessario |
| 2026-05-14 (S77) | **Sentinel Sprint 2 shipped** | Slow loop F&G + CMC ogni 4h, regime detection attivo. Sherpa propone con regime dinamico (prima era hardcoded "neutral") |
| 2026-05-14 (S77) | **Mapping regime invertito (contrarian)** | extreme_fear = risk basso / opp alta. Correzione CC, approvata Board ("buy fearful sell greedy") |
| 2026-05-14 (S77) | **CMC logged-only Sprint 2 MVP** | Dati BTC dominance / mcap / volume salvati ma non usati nel calcolo regime. Riservato Sprint 2.5 |
| 2026-05-14 (S77) | **3 design questions deferred** | speed_of_rise, funding morto testnet, opp score debole → rivalutare dopo osservazione Sprint 2 |
| 2026-05-14 (S76 CEO) | **Mainnet €100 posticipato a sistema completo (Grid + Sentinel testato + Sherpa attivato)** | Sherpa scriverà `bot_config` con soldi veri — va testato prima su testnet con Grid attivo. Grid-only mainnet avrebbe valore narrativo ma rischia quando Sherpa si accende. Sequenza: Sentinel fix → Sprint 2 → observe → Sherpa graduale su testnet → mainnet |
| 2026-05-14 (S76 CEO) | **Roadmap Sentinel-first in 5 step** | Step 1: audit+fix Sprint 1. Step 2: build Sprint 2 (F&G, regime). Step 3: osservazione 1 settimana. Step 4: Sherpa LIVE su testnet (1 parametro alla volta). Step 5: mainnet con sistema rodato. Timeline: fine giugno / inizio luglio |
| 2026-05-14 (S76 CEO) | **Sherpa attivazione graduale: un parametro alla volta** | Primo candidato: `sell_pct`. Osservare proposte per giorni prima di lasciar scrivere. Poi `buy_pct`. Permette di isolare problemi e bloccare fix |
| 2026-05-14 (S76 CEO) | **TF non abbandonato, ridefinito per tier** | Tier 1-2: stesso motore tecnico, regole swap più snelle, nessun Sentinel. Tier 3 (shitcoin): TF scout + Sentinel Sprint 3 valida catalyst → entry con timeout. Post-mainnet, richiede Sprint 3 funzionante |
| 2026-05-14 (S76 CEO) | **Blog weekend 17-18 maggio: 2 post** | Post strategico "why not live yet" + highlight V1/V2. Queste decisioni SONO il contenuto del blog |

Nota CEO: "Decisioni S76 CC e precedenti spostate fuori dalla tabella per restare entro ~15 voci. Storico completo in git history e `PROJECT_STATE.md §4`."

### §6 Vincoli — multi-macchina pre-S79

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Allineati su commit `9ceaa81` (S76 squash) + commit successivi S76 (fix + 75c + cleanup).

### §7 Cosa NON sta succedendo — versione pre-S79

| Cosa | Perché no |
|---|---|
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno target |
| **TF non attivo** | parked post-osservazione Sentinel Sprint 2. Rivisitare ~S81-82 |
| **Audit Area 2 non eseguito** | dovuto (cadenza 90gg). CC ha flaggato in S78 fase 2 report. Proporre in prossima sessione di breathing |
| **Cover V3 non generata** | solo concept (tempesta + mascotte easter egg). Timing: quando V3 è vicino a chiusura |
| **Sherpa LIVE su testnet** | In attesa di 5-7 giorni osservazione Sprint 2 (~21-22 maggio) |
| **Dashboard /admin regime section** | CC la implementa autonomamente (brief non necessario) |

*Footer pre-S79: Prossimo aggiornamento: post osservazione Sentinel Sprint 2 (5-7gg, ~21-22 maggio), o pubblicazione blog post 3 — whichever comes first.*


## Rimosso in sessione S88 (2026-05-27) — applicato brief CEO business_state_update_s88 (adattato a realtà: remediation 4/5 shippata)

### §5 Domande aperte per CC — riga sostituita (verbatim)

| **[S83 NEW] Audit Area 2 (coerenza progetto)** | Proposto CC con data specifica | Mai eseguito, cadenza 90gg superata da sempre. **Proposta CC: lunedì 27 maggio con CC fresh** (durante osservazione NewsKeeper 7gg). Brief `audit_request_YYYYMMDD_*.md` + fresh CC. ~30-45min |

### §7 Cosa NON sta succedendo — riga sostituita (verbatim)

| **Audit Area 2 non eseguito** | Dovuto (cadenza 90gg). CC ha flaggato in S78fp2/S79/S80/S80a/S81/S83. **Finestra utile: 27 maggio - 1 giugno** durante osservazione NewsKeeper 7gg (sovrapposta a osservazione Sherpa Sprint 2). Proposta CC: lunedì 27 maggio con fresh CC + audit brief |

## Rimosso in sessione S92 (2026-05-30) — compaction §4 oltre 40KB

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-27 (S87) | **Volume 3 LIVE su Payhip** (€4.99, hCWNX). Tre volumi disponibili, prodotto line completa fino a pre-mainnet | V3 chiude l'arco "From Brain to Eyes" (S53-S82). Landing page, BlogCTA, library aggiornati nello stesso deploy |
| 2026-05-27 (S87) | **Volume 4 titolo confermato: "From Eyes to Live"**. Coming soon su /library e homepage | Progressione narrativa Zero→Grid→Brain→Eyes→Live. Ogni titolo riprende dove il precedente finisce. Terminal point chiaro: go-live con soldi veri |
| 2026-05-27 (S87) | **Redirect /buy → store** (payhip.com/BagHolderAI) invece di V1 singolo | Con 3 prodotti, forzare su V1 è un funnel rotto. Store mostra il catalogo completo |
| 2026-05-27 (S87) | **Full Umami event coverage** (22 link tracciati + pixel RSS Dev.to) | Ogni click Payhip ora ha source property per funnel analysis. Prima si misurava solo "qualcuno ha cliccato", ora si misura "da dove" |
| 2026-05-27 (S87) | **Reddit deferred**: primo post sarà introduzione progetto, non sales pitch | 1 reply su r/ClaudeAI ≠ community presence. Stranieri con link prodotto = spam. Sequenza: introduce → engage → sell |
| 2026-05-27 (S87) | **Audit Area 2 request consegnato** (primo mai eseguito, overdue da aprile) | Trigger: fine Volume 3 (regola WORKFLOW.md §F). 9 sessioni di "next time". Scope: 6 domande guida su coerenza narrazione↔codice↔state files |
| 2026-05-26 (S86) | **Status badge homepage**: sostituisce "SESSION X · IN PROGRESS" con box teal dinamico da Supabase (`project_status`). Zero deploy per aggiornare il messaggio | Permette al CEO/Max di comunicare stato corrente del progetto al pubblico senza touchare codice. Riusabile per annunci ("Going live next week", "On vacation, bot watching the shop", ecc.). Aggiunge dinamica narrativa alla home |
| 2026-05-26 (S86) | **Regime overlay admin**: bande colorate fear/greed/neutral sui 3 chart `admin.html` da `sentinel_scores` slow loop. Palette finanziaria (Widget A), non semaforica | Contesto regime visibile a colpo d'occhio sui chart Sentinel/Sherpa senza dover guardare un widget separato. Palette finanziaria coerente con Widget A LIVE: due interpretazioni opposte sulla stessa pagina sarebbero confuse |
| 2026-05-26 (S86) | **Widget B (77c) killed**: regime overlay copre lo stesso bisogno, meno clutter | Brief 77c proponeva un quarto chart standalone (regime timeline 7gg). 86b è più elegante: vedi regime nello stesso grafico dei segnali. Widget A LIVE resta (banner "regime ora") |
| 2026-05-26 (S86) | **Grafici pubblici**: post validazione regime overlay + dati Sherpa Sprint 2, portare chart admin su dashboard pubblica (`/dashboard` o `/sentinel`) | Trasparenza radicale: chi guarda dashboard vede non solo il P&L, ma anche cosa "pensa" il sistema. Gating: aspettare che i dati Sherpa post-Brain-Analysis-2 siano puliti prima di esporre pubblicamente |
| 2026-05-26 (S86) | **Session numbering rule**: fonte di verità = `PROJECT_STATE.md`, non `diary_entries`. Brief portano numero sessione CEO. Diary può laggare | Drift S85→S86 sorpassato perché diary_entries era ancora a S82-S83. PROJECT_STATE aggiornato a ogni chiusura sessione → fonte canonical. Diary scritti retroattivamente quando serve |
| 2026-05-26 (S86) | **Brief numbering rule**: `[session_number][lettera]`, es. 86a. Il numero si assegna alla scrittura del brief, non all'esecuzione. Mai duplicare codice brief | Refuso file `brief_84a/84b_*.md` con contenuto "Brief 86a/86b" (S86) era proprio questo problema. Regola formalizzata: numero del brief = sessione in cui è stato scritto, anche se eseguito dopo. Filename deve matchare |
| 2026-05-25 (S85) | **Blog: ordine editoriale NON cronologico** | Ogni post autonomo, pescato da qualsiasi punto della timeline. Vetrina, non racconto lineare. Massimizza autonomia di ogni pezzo come unità di marketing |
| 2026-05-25 (S85) | **Blog frequenza ~1 post ogni 7-10 giorni, pubblicazione a raffiche con distribuzione attiva** | No calendario fisso ("variable reinforcement"). Quantità + cadenza regolare battute da qualità + distribuzione mirata per ogni post |
| 2026-05-25 (S85) | **UTM link bio X abbandonato** | Non mascherabile (X mostra l'URL espanso), referrer X sufficiente per tracking. Manutenzione manuale > valore informativo |
| 2026-05-25 (S85) | **RSS feed blog aggiunto** (commit `8c9c2fc` + `18eaa24` per body completo) | Dev.to Feed Import ora configurabile (auto-import nuovi post come bozze con canonical URL). Esteso a feed reader generici per audience tecnica |
| 2026-05-25 (S85) | **r/ClaudeAI canale di distribuzione primario** (account `Cart0neM`) | Community più aderente al pubblico-target (architetti/founder con AI). Primo commento postato in thread da 643 upvote come test engagement |
| 2026-05-25 (S85) | **Newsletter/mailing list: valutare post-lancio V3** (Buttondown o Substack gratuito) | Pre-V3 prematuro: nessuna baseline traffico, nessuna lista naturale da costruire. Post-V3 c'è una storia chiusa da promuovere ai nuovi iscritti |
| 2026-05-25 (S85) | **Target traffico definiti** (3 mesi 50-80/giorno, 6 mesi 100-150/giorno, 12 mesi 200-400/giorno) | Baseline attuale ~25/giorno. Numeri ancorano le scelte di canale: target richiede ×2-16 sulla baseline, ottenibile solo con distribuzione attiva multi-canale |
| 2026-05-24 (S83/S84) | **CoinDesk Data API scartata**: free tier chiuso il 21/05/2026, paid tier da $999+/mese, fuori budget | RSS gratis + Haiku classifier in Sprint 2 è la soluzione corretta per NewsKeeper al nostro stadio. Nessun budget per news API paid pre-mainnet |
| 2026-05-24 (S83/S84) | **Product Hunt aggiunto a Distribution Channels backlog** (Apple Notes aggiornato) con timing post-mainnet + risultati reali | Lancio one-shot, serve storia completa e numeri veri — non si fa launch su PH senza traction da mostrare |
| 2026-05-24 (S83/S84) | **Indie Hackers confermato post-mainnet**, dopo prima settimana di risultati reali | Community IH vuole numeri veri anche se piccoli, testnet non funziona come prova credibile |
| 2026-05-24 (S83/S84) | **CryptoPanic morto, pivot a RSS feeds** (CoinDesk + CoinTelegraph + Decrypt). Zero costo | CryptoPanic free Developer tier discontinued 1 aprile 2026 (verificato live: endpoint 404). Alternative paid sforavano budget brief <€1. RSS zero-auth, zero paywall risk |
| 2026-05-24 (S83/S84) | **Haiku classifier promosso da S3-4 a S2** | RSS non ha sentiment nativo (CryptoPanic invece sì). Classifier keyword MVP rumoroso ~60% falsi positivi (visibili a campione). Calibration o Haiku-classify anticipato in S2 |
| 2026-05-24 (S83/S84) | **Ship classifier rumoroso as-is per osservazione 7gg** | Data-first principle (feedback memory `feedback_data_first_then_review`). Raccolta dataset reale prima di tuning |
| 2026-05-24 (S83/S84) | **SEO fix S84 shipped same-day: title/description rewrite + JSON-LD + sitemap lastmod** | Audit GSC CEO: 256 imp / 0 clicks / position 10.7 / sitemap "Couldn't fetch". Brief MEDIUM priority chiuso in ~35min, non bloccante per mainnet ma critico per marketing. Drift S47 WebSite schema chiuso in extra |
| 2026-05-24 (S83/S84) | **Apple Notes pulizia: 4 attive, 8 obsolete da cancellare manualmente** | Note operative cumulate nel tempo. Quelle obsolete creavano confusione (es. HN strategy pre-shadowban). Cancellazione manuale a carico Max |
| 2026-05-24 (S83/S84) | **Todo riscritta per era V4/NewsKeeper** | Vecchia todo Apple Note era organizzata per fase V3 (Sentinel/Sherpa). Refresh per refleter focus NewsKeeper + go-live |
| 2026-05-24 (S83/S84) | **Distribution Channels: integrata strategia Reddit + post killer da nota HN obsoleta** | Nota HN era inutile post-shadowban Cart0ne (S81). Il "post killer" come concept (gancio narrativo strong) trasferito a strategia Reddit, da preparare con account dedicato |
| 2026-05-23 (S82 CEO) | **NewsKeeper promosso da post-mainnet a PRE-mainnet** | Crash analysis May 18-22: Sentinel Sprint 2 è reattivo (vede il crash durante), news signals sono predittivi (4 giorni di anticipo). Board decision: il sistema non va live con soldi finché non legge le notizie |
| 2026-05-23 (S82 CEO) | **Brief architetturale NewsKeeper scritto** | 5° cervello indipendente, 4 sessioni CC (~2 settimane). Moduli: CryptoPanic (free), ETF flows (free), macro calendar (statico). Strategist con Haiku (<€1/mese). Costo totale: <€1/mese |
| 2026-05-23 (S82 CEO) | **Nessuna data fissa per mainnet** | Go-live dipende da condizioni di mercato osservate (bear+bull+laterale), non da calendario. Sequenza: Brain Analysis → NewsKeeper build → Sherpa testnet → dry_run → Board approval |
| 2026-05-23 (S82 CEO) | **Volume 3 titolo confermato: "From Brain to Eyes"** | Trilogia: From Zero to Grid → From Grid to Brain → From Brain to Eyes |
| 2026-05-23 (S82 CEO) | **Futures/hedging parcheggiato S90+** | Richiede capitale >€100 e stack futures separato. Idea: cervello hedging che apre small short quando Sentinel dice regime=fear |
| 2026-05-23 (S82 CEO) | **Blog pipeline espansa a 20 post** | +5 backlog V3 da VOLUME_03_PLAN.md analysis. ~5 mesi di autonomia editoriale |
| 2026-05-23 (S82 CC) | **Homepage Blog section + Diary swap SHIPPED LOCAL** | Blog ora subito sotto hero (alta visibilità per i 3 post live, niente click extra), Diary spostato sotto Bots dove fa da "dietro le quinte" delle card. Reduce funnel friction senza occupare il prime real estate hero-adjacent |
| 2026-05-23 (S82 CC) | **Watchtower + Sherpa cards rifatte LOCAL** | Sentinel/Sherpa erano placeholder "?" silhouette con 5 zeri. Ora hanno identità grafica forte (mascot custom, palette dim ma riconoscibile), 3 dati LIVE veri (REGIME, BOTS, STOP BUY) e narrazione: Watchtower = duo che vede arrivare. NewsKeeper introdotto come cameo dim (locked) sulla card Watchtower |
| 2026-05-22 (S81 closure) | **Brief 81a Sherpa Sprint 2 SHIPPED**: per-coin volatility + slow-loop gate + amplitude cap 30% | Chiude i 3 pre-requisiti minimi del Brain Analysis. BONK ora riceve sell_pct ~2× di BTC (live: BTC 1.20 / SOL 1.30 / BONK 2.52). Proposte cambiano max ogni 4h (regime slow), non più ogni 2 minuti |
| 2026-05-22 (S81 closure) | **Brief 81b Haiku commentary SHIPPED**: `vs_yesterday.direction` pre-calcolato in Python + prompt stretto (80 parole, max 100) | Audit 60 entry trovò 1 errore (Day 15: -5.03% misclassificato "better" di -4.12%). Fix strutturale: Python calcola direction, Haiku la legge. Prompt sostituisce "3-4 lines ~250 chars" con "80 words / max 100" + 2 nuove regole NUMBERS/DIRECTION |
| 2026-05-22 (S81) | **Fast ladder (DROP/PUMP/FUNDING/SPEED_OF_FALL) cancellate da Sherpa** | Phase B le sposterà in Sentinel coin-aware. Codice morto rimosso, git history preserva. Decisione 2a delegata da Board |
| 2026-05-22 (S81) | **`proposed_stop_buy_active` legato a `regime == "extreme_fear"`** | De-coupling completo dal fast loop. Lampada ON solo nei regimi più gravi (slow cadence 4h). Decisione 1a delegata da Board |
| 2026-05-22 (S81) | **NO-GO Sherpa step 4** | Brain Analysis: -$3.94 vs Board, non coin-aware, 449 fast-loop flips, flicker 6min. Tre fix architetturali richiesti prima di riconsiderare |
| 2026-05-22 (S81) | **Three-phase brain architecture (A/B/C)** | A: Sherpa per-coin + slow gate + cap (brief 81a). B: Sentinel coin-aware (EMA/RSI per-coin). C: sentiment online. Ogni fase testata indipendentemente |
| 2026-05-22 (S81) | **Grid-only mainnet è opzione legittima** | Grid +$12.52 in mercato -0.47%. Funziona senza cervello. Possibile andare live Grid-only mentre Sherpa matura |
| 2026-05-22 (S81) | **Volume 3 climax = seconda Brain Analysis** | Atto 1 (questo report): brain è daltonico. Atto 2 (post-rework): brain rieducato. Cutoff stimato S83-S85 |

## Rimosso in sessione S92 (2026-05-30) — semplificazione §3 diary, §6 vincoli chiusi, §7 stale, Multi-macchina PID

### §3 per-session status list (rimossa — source of truth è Supabase diary_entries)
- S83 — COMPLETE (NewsKeeper Brain #5 scaffold)
- S84 — COMPLETE (SEO audit fix)
- S85 — COMPLETE (RSS feed Dev.to + governance BUSINESS_STATE)
- S86 — COMPLETE (status badge homepage + regime overlay admin)
- S87 — COMPLETE (V3 launch Payhip + brief 87a site updates + Umami tracking + Audit Area 2 request)
- S88 — COMPLETE (remediation Audit Area 2: catch-up sito + AUDIT_PROTOCOL + UI debts)
- S89 — COMPLETE (Audit Area 1 remediation: test hygiene + dead code + dep split)
- S90 — COMPLETE (fix spike guard A+B + deliverables UI/blog)
- S91 — BUILDING (mattina: SEO/A11y quick wins · pomeriggio: Brain Analysis 2 + fix stop_buy extreme_fear)

### §6 vincoli chiusi/obsoleti
- Volume 3 "From Brain to Eyes" pubblicazione Payhip → DONE 2026-05-27 (payhip.com/b/hCWNX)
- Blog primo post → DONE 2026-05-15
- PROJECT_STATE.md compaction → DONE S92
- DRY_RUN Sherpa Sprint 2 osservazione → DONE, Brain Analysis 2 fatta S91
- Multi-macchina PID/runtime info (rimossa da BUSINESS_STATE, resta in PROJECT_STATE): "Mac Mini orchestrator su `51204cf` (PID parent **28217**, restart 2026-05-22 20:31 CET post brief 81a+81b), 7 processi + NewsKeeper standalone PID 78098 (caffeinate parent 78100, launch 2026-05-24 10:56 CET)"

### §7 righe stale
- "Audit Area 2 eseguito + remediation 4/5 completata in S88" → in realtà 5/5 (88d confermato shipped S88), ora archivio
- "Homepage S82 pushata in S83" → avvenuto 2026-05-24, storia antica
- "Volume 3 lancio Payhip" → lanciato 2026-05-27
- "Cover V3 non generata" → cover generata e live
- "NewsKeeper Sessions 2-4 non ancora in build" (con ref stale "~31 maggio") → ancora vero ma ref temporale stale
- "Sherpa LIVE su testnet" (con ref stale "Target ~29 maggio - 1 giugno") → ancora pending ma ref stale
- "Sitemap Google indicizzazione" → risolto S84

## Rimosso in sessione S105 (2026-06-13) — compaction post recupero S104 (file 55KB → target ≤40KB)

### §4 — Decisioni archiviate (S96 → S88)

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-04 (S96) | **Clean slate tutti e 3 i grid bot (Opzione C)** — Board+CEO. Shippato: cycle tagging `testnet_1`/`testnet_2`, BONK ripartito pulito | Reset mensile testnet ha azzerato i wallet. Guardia 72a ha bloccato BONK. Invece di ricostruire la posizione, archiviamo i trade come `testnet_1` e ripartiamo come `testnet_2`. Campo `cycle` su trades/daily_pnl/snapshots/reserve_ledger/bot_config. Brief S96a |
| 2026-06-04 (S96) | **Testnet disclaimer obbligatorio su sito** — CEO. Live su home + /dashboard + grid | Banner fisso non dismissibile. Testo chiaro: dati sintetici, no soldi veri, saldi resettabili senza preavviso |
| 2026-06-04 (S96) | **Audit Area 2 backstop 120→60 giorni** — Board | Aggiornato AUDIT_PROTOCOL.md §2 e CLAUDE.md [1] |
| 2026-06-04 (S96) | **Blog check incrementale in audit Area 2** — CEO | Stessa logica diary: ancora "Blog coperto fino a" nel report |
| 2026-06-02 (S95) | **Dual-channel SEO+GEO content strategy adottata.** Brief S95a: 5 post con keyword validate. POST 1 live in produzione | Keyword data: "claude code" 100K–1M +9.900%, "ai trading bot" 10K–100K +900%. Le long-tail narrative proposte dal CEO avevano volume zero. Post Reddit FluoTest (703 upvote) ha validato GEO come canale acquisizione (ChatGPT cita risposte dirette → 131 signups zero ad spend) |
| 2026-06-02 (S95) | **LinkedIn company page + profilo "Max Cartone" approvati, timing post-redesign** | Ricognizione Claude in Chrome: 1 solo "AI CEO" dichiarato al mondo (Homains). Campo vuoto. LinkedIn ha alta autorità dominio per GEO (35% citazioni ChatGPT da LinkedIn). Profilo separato da quello reale di Max |
| 2026-06-02 (S95) | **Medium (@BagHolderAI) confermato attivo** con 2 post. Aggiunto ai canali distribuzione | Cross-post con canonical URL. Audience più ampia e meno tecnica di Dev.to |
| 2026-06-01 (S94a) | **Regex classifier morto per severity/direction, sostituito con Haiku S2 + Python pre-processing** (Brief S94a) | 65% FP, direzioni invertite, inutilizzabile per trading |
| 2026-06-01 (S94a) | **Feed macro aggiunti (BBC→CNBC Economy + MarketWatch).** BBC scartata post-verifica: contenuto general business, zero macro | Serve catturare Fed/tariffe/inflation prima che arrivino su testate crypto |
| 2026-06-01 (S94a) | **Daily macro feed check fino a T+7 (8 giugno)** | Max ha corretto il piano "aspettiamo 7 giorni", verifica attiva batte osservazione passiva |
| 2026-05-30 (S92) | **Protocollo cross-check anti-assenso su tre mandati (CEO / CC / Auditor)**, non un "Decision Panel" separato | La versione panel di CC rendeva Max corriere tra sessioni fresche; cablare un obbligo nel mandato esistente di ogni agente riusa il flusso, zero infrastruttura nuova. CEO: auto-obiezione nei brief + verifica critica del lavoro CC. CC: ≥1 obiezione tecnica prima di implementare. Auditor: caccia incoerenze deciso/implementato/reale |
| 2026-05-30 (S92) | **Convenzione naming brief/report**: `YYYY-MM-DD_SXX[z]_brief_SCOPE` / `YYYY-MM-DD_SXX[z]_RforCEO_SCOPE`. Chiave accoppiamento Auditor = sessione + SCOPE (slug identico ereditato dal brief) | L'Auditor non vede le conversazioni, lavora solo sugli artefatti; senza accoppiamento la cross-analisi è cieca |
| 2026-05-30 (S92) | **Zero retrofit file pre-S88**; grandfather alla baseline degli audit del 27/05 (S87) | Rinominare il passato mentre si pulisce il presente crea nuovo drift |
| 2026-05-30 (S92) | **Disaccordo cross-agente che non converge → sale a Max, sempre.** Risoluzione di Max → una riga in §4 (data — decisione — why) | Nessun agente ha l'ultima parola sulla DECISIONE; Max è il nodo di sintesi finale |
| 2026-05-30 (S92) | **Prodotto-metodologia: DIFFERITO, non bocciato.** Il libro/prodotto arriva DOPO il go-live | 39 views su Payhip misurano traffico, non prodotto sbagliato; cambiare prodotto non risolve un funnel vuoto. Go-live resta gated sui tre regimi di mercato, mai su scadenze esterne (contenuti/libro) |
| 2026-05-29 (S91) | **Brain Analysis 2 completata: 3 fix Sprint 2 validati** (coin-aware, oscillazione domata, amplitude cap). Sherpa tuning-side **pronto** ma **NON mainnet-bound** | L'analisi ha trovato due problemi a monte del tuning: **stop_buy morto** (gap regime extreme_fear — risolto stessa sessione) + **timing Sentinel lento** (slow loop 4h). Il tuning dei parametri è ok, ma il sistema non va a soldi veri finché questi due non sono chiusi |
| 2026-05-29 (S91) | **Fix stop_buy extreme_fear shippato + verificato live** (commit `ea4c7a8`), mapping F&G label-aware. Backfill storico: **NO** | Sentinel non emetteva mai `extreme_fear` (soglia `<=20` vs banda "Extreme Fear" alternative.me ~25) → freno Sherpa morto su tutta la finestra crash (0 righe). Fix label-primary. Verifica live: F&G=23 → `extreme_fear` + `proposed_stop_buy_active=true` su 3 coin. Solo fix-forward, storico non toccato (operativamente conta il futuro) |
| 2026-05-29 (S91) | **Reset testnet parcheggiato** (dopo stop_buy + Sentinel/NewsKeeper; possibile sblocco da rimbalzo di mercato). "Mai capitolare" resta solo per mainnet | Priorità ai fix architetturali prima di azzerare il testnet. Il principio "mai capitolare / no cash morto" si applica solo a mainnet; sul testnet un reset è accettabile dopo i fix |
| 2026-05-28 (S90) | **Spike guard fix A+B shipped** (commit `06a6c7c`). Option A variante Board: double fetch con conferma 50% dopo 5s pausa. Option B: cooldown 1 ciclo post dead-zone recalibrate | Root cause trade BTC 27/05 21:44 UTC: testnet spike $82,143 (mainnet $74,500) + dead_zone_recalibrate + sell trigger nello stesso tick → realized -$1.31. Variante Board doppio fetch è auto-adattiva cross-coin (vs soglia fissa proposta da CC). 129 test verdi, 8 nuovi. Restart Mac Mini 09:15 CET, runtime `673c941` |
| 2026-05-28 (S90) | **Dashboard "days observing" rimosso** (commit `751b18c`) | Contatore legato a ultimo trade, non a inizio regime → fuorviante dopo trade accidentali ("0 days observing" leggeva come informazione spuria). Regime label già comunica posture di watching, basta da sola |
| 2026-05-28 (S90) | **Cover V3 ottimizzate** (commit `b8ed22d`): PNG 4.6MB → JPG 231KB (−95%) | Cover V3 erano in PNG 2.2+2.4 MB (~30× rispetto a vol1/vol2 JPG 54-182KB). Convertite con sips a 424×600 / 600×600 q=85 allineate al formato dei volumi precedenti. Performance + bandwidth/Vercel |
| 2026-05-28 (S90) | **Prima presenza Reddit** (r/ClaudeAI, flair "Claude Workflow"). Zero link, zero sales | Storia del progetto come post di valore per la community, in attesa mod approval. Commento parallelo nel "Build with Claude Megathread" LIVE. Esecuzione della strategia "introduce → engage → earn credibility → mention book" parcheggiata in S87 |
| 2026-05-27 (S89) | **Audit Area 1 automatizzato via Cowork scheduled task** (monthly, sandbox Linux) | Notifica: bozza Gmail con marker `[AREA-XX]`, Apps Script `AutoSendDrafts` (account cartone@gmail.com) la invia automaticamente tra le 4-5am. Git push resta manuale (limite sandbox `.git/`). Primo run 2026-05-27, verdetto CON RISERVE, prossimo ~2026-06-26 |
| 2026-05-27 (S89) | **Brief 89a shipped**: test hygiene (32 legacy → archived + pytest.ini), dead code deprecated (4 metodi, tabelle `portfolio`/`sentinel_logs`), `requirements-scripts.txt` per tweepy | Remediation findings Audit Area 1 (H1/H2/M1/M3/L2). Pytest 121/121 green. Solo housekeeping, zero touch `bot/`, no restart |
| 2026-05-27 (S88) | **Audit Area 2 completato + 5 brief remediation** | Primo audit coerenza mai eseguito. Drift pubblico principale: sito 1-2 settimane indietro. 30 findings, 0 CRITICAL. 5 brief CC (88a→88e) prodotti per la remediation. Diary posticipato a post-remediation per scrivere report completo (candidato blog post) |
| 2026-05-27 (S88) | **Regola Area 2 riformulata: event-based** (Board approved) | Trigger obbligatori: (a) pre go-live mainnet, (b) pre lancio Volume Payhip, (c) nuovo brain/macro-feature, (d) backstop 120gg. Sostituisce "90gg" mai applicata. Owner accountability: Max. Implementazione in Brief 88a |
| 2026-05-27 (S88) | **NewsKeeper reso pubblico nel roadmap** (Board approved) | Phase dedicata in roadmap.ts. Tono onesto: Sprint 1 live (RSS + regex, ~60% FP), Sprint 2 planned (Haiku classifier). Non più nascosto come "Sentinel Sprint 3" |
| 2026-05-27 (S88) | **Trasparenza fear regime sulla dashboard** (Board approved) | Opzione A: banner "Watching market · Last trade May 16 · Fear regime active". On-brand con la storia "AI onesta che dubita". Implementazione in Brief 88d |

### §4 — riga S99 Passive Income Dashboard (superata da S104 "The Experiment")

| 2026-06-07 (S99) | **Passive Income Dashboard: decisioni B+E approvate, implementazione PARKED** | B: teaser home + pagina dedicata `/income`. E: rischio €0 pubblico accettabile (target premia onestà). Obiezione CEO su timing: costruire il tabellone prima che il trading sia live rischia mesi di "€0 statico". Parked fino a post-analisi NewsKeeper/Brain + timeline go-live concreta |

### §2 — Frontend internals (S86)

### Frontend internals (S86, NUOVO)
- **Homepage: status badge dinamico LIVE** — tabella Supabase `project_status` (1 riga, RLS anon-read, trigger `updated_at` auto), aggiornabile via plain SQL UPDATE da CEO/Max/CC. Box full-width sotto l'hero, palette teal `#5DCAA5`, formato `emoji + status_text + Session NN · Updated Xh ago`. Messaggio attuale: 📖 "Collecting brain data before going live · Volume 3 just dropped" (aggiornato CEO S87). Zero deploy per cambiarlo.
- **Admin dashboard: regime overlay bands LIVE** — bande di sfondo colorate fear/greed/neutral sui 3 chart `admin.html` (TREND, Sentinel fast vs Sherpa, Parameters History). Palette finanziaria mirror di Widget A (S77 LIVE — extreme_fear cyan-light → extreme_greed red). Alpha bumped (0.20/0.14/0.10) per visibilità su regime uniforme (testnet "fear" da 5+ giorni). Legenda regime + bonus fix x-axis labels range-aware (HH:MM↔DD/MM).
- **Widget B (77c, standalone regime timeline): KILLED** — regime overlay copre lo stesso bisogno con meno clutter visivo (bande sui chart esistenti invece di un quarto chart dedicato). Brief 77c archiviato in `briefresolved.md/`. Widget A (banner regime istantaneo, S77 LIVE) resta complementare.
- **Prossimo step frontend**: portare grafici Sentinel/Sherpa su dashboard pubblica (`/dashboard` o `/sentinel`). Gated da (1) validazione regime overlay con dati live + (2) Sherpa Sprint 2 verde dopo Brain Analysis 2.

### §2 — Audit & Remediation (S88) + Sito stato pubblico (S80-S82)

### Audit & Remediation (S88, NUOVO)
- **Audit Area 2 completato** (primo mai eseguito) — verdetto CON RISERVE. 0 CRITICAL · 6 HIGH · 12 MED · 12 LOW. Report: `audits/audit_report_20260527_area2_coherence.md`. Riserve principali: sito pubblico in drift 1-2 settimane (dashboard diceva Sentinel/Sherpa "not yet deployed", roadmap.ts ferma al 19 maggio, NewsKeeper assente), AUDIT_PROTOCOL.md era un vecchio request non un protocollo, regola cadenza Area 2 mai applicata.
- **5 brief di remediation prodotti (88a→88e), ~5-7h CC. 4/5 SHIPPED in S88** (2026-05-27, stessa sessione — non separate come da piano iniziale): 88b public site catch-up (roadmap S80→S87 + NewsKeeper Phase 14 + dashboard Sentinel/Sherpa LIVE/DRY_RUN), 88c state files cleanup (PROJECT_STATE <40KB + 6 drift fix), 88a audit meta (AUDIT_PROTOCOL.md riscritto a protocollo vero + trigger Area 2 event-based), 88e brief hygiene (config/parked). Tracking in `audit_remediation_cover_sheet.md`.
- **Resta solo 88d** (UI debts: botData homepage da Supabase + banner fear regime + fallback diary), sessione dedicata.

### Sito (stato pubblico)
TestnetBanner globale, Reconciliation table pubblica su /dashboard. **TF live card on home + dashboard SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)** — "dal dottore" SVG sostituito con card stile Grid (orange accent, mirror frame), hero text aggiornato a "$500 Grid + $100 TF (Tier 1-2)", pipeline arrow "I tried, your turn" → "TF picks, Grid manages". **Homepage CTA swap SHIPPED (Brief 80b)**: "Read the blog" primario, "Read the diary" + "Live numbers →" secondari outline. **Homepage layout update SHIPPED LOCAL S82 (2026-05-23, no push)**: sezione Blog sotto hero (ultimi 3 post cliccabili), sezione Diary spostata sotto Bots. **Watchtower + Sherpa cards SHIPPED LOCAL S82**: card Sentinel→`THE WATCHTOWER` (duo Sentinel + NewsKeeper, primo cameo pubblico del 5° bot dim/locked) + card Sherpa→`SHERPA Parameter Tuner` con mascot Claude Design (flag + mappa). 3 stat-row LIVE-WIRED via Supabase REST: REGIME (5 pip, oggi `FEAR`), BOTS (3 pip rossi auto-adatta), STOP BUY (1 pip, oggi OFF). Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped). **Push S82 deferito**: in attesa del brief newskeeper Board prima di rivelare il cameo pubblicamente.

### §2 — Dev.to engagement history (S81-S85)

- **Engagement S81:** commento dettagliato su "AI Agent Failure Modes Beyond Hallucination" (Maxim Saplin) — 6 failure modes mappati all'esperienza BagHolderAI con link UTM al blog. Pubblicato 2026-05-22.
- **Community engagement attivo (storico):**
  - Commento su "Is Writing a Tech Blog Still Worth It?" (Deneth Rajapaksha) → 2 like, risposta dell'autore che chiede il link al blog → reply con link UTM + invito feedback
  - Presentazione nel Welcome Thread v376 → risposta entusiasta di Lenard Francis (FastAPI AlertEngine) → reply dettagliato con 3 errori strategici del CEO, 3 link UTM, domanda di chiusura
  - Reply a Lenard Francis (confidence gating, AlertEngine) + Valentin Monteiro (architect bottleneck shifting). Entrambi nel Welcome Thread v376.
- **Strategia:** engagement first (commenti, risposte, conversazioni), contenuto secondo. L'algoritmo Dev.to premia le relazioni, non i post isolati. I commenti portano più visibilità del post stesso in fase iniziale.
- **Engagement S85:** Rohini Gaonkar (AWS) aggiunta al giro di interazioni attive (oltre Valentin Monteiro già citato).
- **Feed Import RSS da configurare (S85):** `https://bagholderai.lol/rss.xml` da incollare in `dev.to/dashboard/feed_imports`. Dev.to importa i nuovi post come bozze con canonical URL automatica al blog originale (no SEO duplicate penalty). Body completo via `<content:encoded>`.
- **Prossimi passi:** Post 3 cross-post settimana prossima, continuare engagement nei commenti, monitorare se le conversazioni portano click (UTM campaign `comment_deneth` e `comment_lenard`)

### §5 — Domande chiuse/superate (DONE)

| ~~[S102 NEW] Formalizzare parametri Board-only + default automatici coin nuovi~~ | ✅ DONE (S103) | Completato in S103 (brief S103a): board params Sherpa-managed con `BOARD_TABLE` per volatility tier + debounce 24h. Default automatici coin nuovi inclusi |
| **[S99b] Dashboard penalty in NEXT SELL IF** | ✅ DONE | runtime mirror espone `_sell_pct_penalty`, dashboard la include nella formula |
| [S83] NewsKeeper S2 | ✅ DONE (S94 + T+7 quality review S100) | V2 Barometro in shadow, verdetto T+14 ~23 giugno. Verdetto T+7: miglioramento netto sul regex (0 righe irrilevanti, 0 fallback, ~€6/mese), ma unità per-item sbagliata → redesign barometro. Bug direzione assorbito nel redesign (opzione C) |
| [S97] NewsKeeper S3 daily digest | Assorbito nel barometro v2 | Il "risk score 24h calmo/alert/tempesta" È l'aggregato del barometro (3 stati). Non più item separato |
| **[S99 NEW] Passive Income Dashboard** | PARKED (post go-live timeline) | Brainstorm CC+Max completo (`config/2026-06-07_S100a_brief_passive-income-dashboard.md`). Decisioni strategiche prese. Implementazione sospesa fino a timeline go-live concreta. Se manca poco: "coming soon". Se manca molto: aspettare |
| **[S88] Audit Area 2 remediation — 4/5 SHIPPED** | Resta 88d (UI debts) — verificare se il redesign li ha chiusi | Audit 2026-05-27 (CON RISERVE). 88a/88b/88c/88e shippati S88, resta 88d (UI debts). Il redesign Pastel Sticker v2 potrebbe aver risolto parte dei debiti UI → da verificare nella prossima sessione. Tracking: `audit_remediation_cover_sheet.md` |
| **[S82] Brief NewsKeeper architetturale Session 1** | ✅ DONE (S83) | Scaffold shippato commit `49473a9`. Module 1 RSS feeds live standalone Mac Mini PID 78098. Sessioni 2-4 ancora pending |
| ~~Brief 81a Sherpa Sprint 2~~ | ✅ DONE (S81) | Shipped commit `3ba1132`. Verifica live: BTC/SOL/BONK proposals diversi |
| ~~Sito TF narrativa update~~ | ✅ DONE (S80) | "dal dottore" → card TF live shipped brief 80b commit `b8bdc12` |
| ~~Monitorare sitemap Search Console~~ | ✅ DONE (S84) | SEO fix S84 shipped commit `c89c8cc`: sitemap lastmod + JSON-LD + title/description. Action manuali Max post-deploy in §6 |
| **Phantom BONK 1.37M** | ~~Bassa priorità~~ → SUPERATA | Clean slate S96 ha resettato tutto. Phantom ora è baseline testnet (1 BTC / 6 SOL / 18.446 BONK), gestito da `managed_holdings` post-audit S97a |

### §6 — Vincoli DONE/superati

| **NewsKeeper T+7 quality review** | ✅ DONE (S100, report shipped) | V2 Barometro in shadow, verdetto T+14 ~23 giugno |
| **Correzione feed CNBC Economy** | ✅ FATTA (S94, commit `8515378`) | BBC→CNBC Economy + MarketWatch. Restart Mac Mini 22:04 CET, CNBC contribuisce `haiku_s2` verificato. (Era "da dare a CC" nel paste, già shippata) |
| **Site redesign "Pastel Sticker v2"** | ✅ FATTO (S97, 2026-06-05) | Merge e deploy completati da Max, LIVE su bagholderai.lol. Rimovibile dalla lista vincoli alla prossima compaction |
| **NewsKeeper — prima analisi** | ~lun 1 giugno | Job 1 anti-rumore Haiku → Job 2 lead/lag vs Sentinel. Decide timing Sentinel (Phase B vs accelerare NewsKeeper) |

### §7 — Righe superate

| **Sentinel Phase B** | Parcheggiata fino a post T+7 NewsKeeper (8 giugno) |
| **Sherpa testnet activation** | Bloccata da Brain Analysis che dipende da NewsKeeper pulito |
| **Audit Area 2** | Finestra scaduta, riprogrammare post-redesign |
| **Reset testnet** | Rimandato: prima i fix (stop_buy ✅ + Sentinel/NewsKeeper). Possibile sblocco da un rimbalzo di mercato. "Mai capitolare / no cash morto" vale solo per mainnet, non per il testnet |
| **Decisione timing Sentinel (Phase B vs accelerare NewsKeeper)** | Parcheggiata fino a post prima analisi NewsKeeper (lun 1 giugno) |
