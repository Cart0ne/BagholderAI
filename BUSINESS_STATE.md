# BUSINESS_STATE.md

**Last updated:** 2026-05-10 — Session 70 chiusura (sell ladder + net-of-fees, Sentinel ricalibrato, reconciliation 26/26, sito online, TF dal dottore, Haiku fix)
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-10 (S70c chiusura, commits 77d4090 + 6f653b5 + 4987328)

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 9 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, terms, privacy).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

**Post X S69+S70 (S70):** thread 2 post in coda (FIFO removal + testnet verified + site back online + TF hospitalized). 🤖+👤 firma. Da pubblicare stasera 2026-05-10.
**Sito online (S70c):** maintenance rimossa dopo 5 giorni. TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE colorati. Public dashboard certificata vs Binance.

**Post X:** nessun post in coda (`pending_x_posts` vuoto). Scanner X automatizzato a cron settimanale dal 2026-05-04. Strategia: "variable reinforcement" — pubblica quando succede qualcosa di vero, mai calendar-driven. Posting Strategy v1.1 in `Posting_Strategy_v1_1.docx`.

**Payhip:** Volume 1 + Volume 2 live, **0/30 views totali** (segnalato da Board S68 come problema di invisibilità — sito offline + zero canale promozionale, non difetto del prodotto).

**Blog/contenuto:** il contenuto pubblico è il diary sul sito (/diary) e i volumi Payhip. Nessun blog esterno. Daily CEO's Log via Haiku + X posting (OAuth 1.0a) attivo.

**Ads/monetizzazione:** A-Ads live sul sito (crypto-native, revenue trascurabile). Buy Me a Coffee attivo (buymeacoffee.com/bagholderai). Nessuna sponsorship in pipeline.

**SEO/Analytics:** Umami Cloud (cookieless, GDPR) + Vercel Web Analytics. Progetto pre-traction, nessun dato di traffico significativo.

**Partnership/eventi:** nessuno in corso né in pipeline.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, 96 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, 108 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

Preview rimosse da entrambi i volumi.

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53+ in accumulo, **nessun lavoro attivo** (Board S68: "prima i fondamentali"). Stima grezza chiusura: sessioni 70–80.

**Sessione corrente:** 69 BUILDING (avg-cost trading completo + Strategy A simmetrico + cleanup FIFO/fixed mode totale). S68 diary "The One Where We Almost Quit" COMPLETE su Supabase, docx prodotto. Volume 3 outline: "Operation Clean Slate" (S65-S66) + "First Contact with Binance" (S67) + "The Pivot" (S68 minimum viable) + "FIFO Divorce" (S69 avg-cost migration + Strategy A) — climax narrativo costruzione/decostruzione tecnica.

**Check di congruenza diary↔DB:** nessun check automatico attivo. **Reconciliation gate (nightly script)** proposto come task Validation System: verifica ogni notte che `Realized_avg_cost + Unrealized = Total P&L` chiuda al centesimo, alert se gap > $0.01. Da implementare insieme a brief 60b respec.

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-10 (S70) | **FEE_RATE = 0.001 hardcoded** | Worst-case Binance. Se BNB discount, guadagno extra senza toccare codice |
| 2026-05-10 (S70) | **Sell graduale a scala (sell ladder)** | Speculare ai buy DCA. Ogni sell richiede +sell_pct% sopra l'ultimo. `_last_sell_price` traccia la scala |
| 2026-05-10 (S70) | **Timer patience parcheggiato** | Servono dati reali dal sell ladder prima di calibrare un timeout |
| 2026-05-10 (S70) | **Sentinel ricalibrato + Sentinel/Sherpa DRY_RUN riaccesi** | 3 bug calibrazione fixati. Telegram OFF di default. 7 giorni raccolta dati |
| 2026-05-10 (S70) | **Reconciliation Binance Step A+B shipped** | 26/26 matched zero drift. Script manuale + pannello /admin + tabella pubblica |
| 2026-05-10 (S70c) | **Sito online con disclaimer testnet** | "Real orders, simulated money." Reconciliation pubblica come prova di trasparenza |
| 2026-05-10 (S70c) | **"The story is the process, not the numbers"** | Board: cambi contabili retroattivi = materiale narrativo, non rischio reputazionale |
| 2026-05-10 (S70c) | **Net Realized Profit parcheggiato** | Bug strutturale realized_pnl gross scoperto. Brief dedicato "Strada 2" pre-mainnet |
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
| 2026-05-09 (S69) | **Budget testnet $500 confermato (no passaggio a $10K)** — Board | Niente vantaggio tangibile a scalare. Allocazioni invariate (BTC $200, SOL $150, BONK $150) |
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

---

## 5. Domande Aperte per CC (idee tech non ancora in brief)

**[S70 Board open questions]**

- **Reconciliation Step C (cron notturno Mac Mini)** — ~30 min. Wrapper `scripts/cron_reconcile.sh` + crontab `0 3 * * *`. Test TCC Full Disk Access. Deferred a S71.
- **Brief "P&L netto canonico (Strada 2)"** — pre go-live €100. Fix `realized_pnl` per-trade gross + cambio formula `avg_buy_price` per usare cost USDT vero + backfill cumulato + verifica identità S66-style. ~3-4h.
- **Slippage_buffer parametrico per coin** — BONK ha bisogno di buffer maggiore (slippage testnet 2.46%) rispetto a BTC/SOL. Brief separato pre-mainnet.
- **LAST SHOT path bypassa lot_step_size** — cosmetico (genera 1 retry rifiutato + 1 success), pre-mainnet vale arrotondare.
- **Sito mobile review** — smoke test desktop 10/10 OK, layout mobile non verificato. iPhone/Android pass su Reconciliation table + bot cards + TF dottore.

**[S68 Board open questions]**

- **Apply 68b sul Mac Mini: quando?** — refactor folder + managed_by cleanup, richiede restart bot. Risposta S69: incluso nel deploy 69a (finestra unica con TRUNCATE+restart).
- **Budget testnet $10K vs $500: decidere prima del prossimo restart** — Risposta S69: **$500 confermato** (Board 2026-05-09).
- **Rimozione fixed mode Grid (~500-800 righe codice morto)** — In progress: BLOCCO 2 parziale shipped S69 (`main_old.py` + `grid_runner.py` sync via). Refactor pesante (`grid_bot.py` ~200 righe + DROP COLUMN DB) in brief 69a.
- **Rimozione `main_old.py`** — RISOLTO S69 BLOCCO 2 (commit `ad048b6`).
- **grid.html rebuild card-by-card (primo task S69)** — RISOLTO S69 BLOCCO 1 (commit `6335633`). Portfolio overview 9 card 3+3+3 con formule esplicite, Coin status con Avg buy/Current price/Diff%, Recent trades con colonna Fee.
- **check_price logging in trades (parcheggiato a S69+)** — Ancora aperto. Necessario per misurare slippage testnet post-hoc (oggi reason mente con fill_price).

**[S69 risolte fine giornata 2026-05-09]**

1. ✅ **Data deploy brief 69a**: entro oggi 2026-05-09 (Board confermato).
2. ✅ **Reset mensile testnet Binance**: confermato dal sito Binance Testnet (~1/mese, no preavviso, API keys preservate post-Aug 2020). Non bloccante.
3. 🟡 **Reconciliation gate (67a Step 5) + Reconciliation Binance (DB ↔ `fetch_my_trades`)**: rimandati a **nuovo brief CEO in preparazione** che probabilmente unifica i due topic.

---

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

19. **[S65 NEW] Rename `manual` → `grid` su tutto il sistema** (parcheggiato post-go-live): standardizzare nomenclatura `bot_config.managed_by`, `trades.managed_by`, `reserve_ledger.managed_by`, `daily_pnl.managed_by` da `manual` (legacy v3) a `grid`. Tocca 4 tabelle DB, codice bot Python, frontend dashboards. Stima ~2-4h. **NON farlo durante DRY_RUN Sherpa** (rinomina = restart = contaminazione counterfactual). Finestra utile: post-Phase 2 stabile + post-go-live €100. Coerenza interna del ledger già fixata in S65 via JOIN su `trade_id`.

20. ~~**[S65 NEW] Brief 65c — migrazione paper → Binance testnet**~~ — **SUPERATA in S67** (shipped come parte di brief 67a Step 3, ccxt set_sandbox_mode + place_market_buy/sell + fee USDT canonical).

21. ~~**[S65 NEW] Brief 60b respec — avg-cost pulito nel bot**~~ — **SUPERATA in S66** (shipped come parte di Operation Clean Slate Step 1, test 5/5 verdi, identità chiude al centesimo).

22. **[S65 NEW] Reconciliation gate (nightly script)** — proposto come task Validation System: script su Mac Mini che ogni notte verifica `Realized_avg_cost + Unrealized = Total P&L` al centesimo, alert Telegram se gap > $0.01. Stima ~2h. Da implementare insieme/post brief 60b, gating soft per future regressioni.

23. **[S66 NEW] Aggiornare `tests/test_pct_sell_fifo.py`** — assertion sul realized_pnl cambiate dopo pivot avg-cost. Non gating, non in CI. Manutenzione.

24. **[S67 NEW] exchange_order_id null su sell** — sell OP/USDT non ha popolato il campo. Fix proposto: fallback clientOrderId. ~30min.

25. **[S67 NEW] Recalibrate-on-restart** — buy_pct cambia spontaneamente. Da indagare: Sherpa scrive in bot_config durante DRY_RUN?

26. **[S67 NEW] BNB-discount fee future-proof** — se in mainnet usiamo BNB per sconto 25%, `fee_usdt = 0` quando fee_currency=BNB. Gap trascurabile su €100 ma da risolvere prima dello scale-up.

27. **[S67 NEW] Reason bugiardo su trade con slippage** — quando un market order ha fill_price diverso dal check_price (book sottile, slippage testnet), il `reason` del trade riporta "dropped X% below last buy" usando il **fill_price** invece del check_price. Esempio BONK 2026-05-08 19:49 UTC: `"price $0.00000735 dropped 1.5% below last buy $0.00000731"` — falso, $0.00000735 è SOPRA $0.00000731 (slippage +2.4% testnet). L'execution è economicamente corretta, è solo la stringa di motivazione che mente. Fix: includere check_price + slippage % nel reason. Cosmetico, non gating.

28. **[S68 NEW] Phase 2 split di `bot/grid_runner.py`** — il file ha raggiunto 1627 righe, di cui 833 in una singola funzione `run_grid_bot()` (main loop). Stesso pattern del monolite pre-Phase 1 di `grid_bot.py` (2200 righe → 6 moduli S60-S62). Split proposto: `runner.py` (solo main loop ~250 righe) + `runner_config_sync.py` (config + initial lots, 280 righe) + `runner_force_liquidate.py` (180) + `runner_cycle_summary.py` (138) + `runner_telegram.py` (notifications) + `runner_status.py` (helpers). Stima ~3-4h con audit di non-regressione. **Da fare DOPO go-live €100 mainnet** (aggiungerlo dentro S68 aumenta rischio senza beneficio immediato). Parcheggiato come "Phase 2 grid_runner split".

---

## 6. Vincoli / Deadline Non-Tecnici

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
- ~~7 giorni clean FIFO drift post-Phase 2~~ → cancellato, calibriamo sul campo con €100 reali
- ~~7 giorni clean health check~~ → cancellato, idem
- ~~Sell-decision alignment a FIFO globale (proposta 2 CC del 5 maggio)~~ → superata, abbandonato strict-FIFO

**Pre-live gates (Validation System — aggiornamento S69):**
- ✅ Contabilità avg-cost (S66)
- ✅ Fee USDT canonical (S67)
- ✅ Dust prevention (S67)
- ✅ Sell-in-loss guard avg_cost (S68a)
- ✅ DB schema cleanup (S68 + S69 DROP COLUMN)
- ✅ FIFO contabile via dashboard (S69)
- ✅ Avg-cost trading completo (S69)
- ✅ Strategy A simmetrico (S69)
- ✅ IDLE recalibrate guard (S69)
- ⬜ sell_pct net-of-fees (brief separato, pre-mainnet)
- ⬜ Reconciliation gate nightly (post-24h observation)
- ⬜ Wallet reconciliation Binance (post go-live)
- ⬜ 24h testnet observation clean (in corso da stasera 2026-05-09)
- ⬜ Sito online con numeri certificati
- ⬜ Board approval finale (Max)

**Obiettivo go-live**: dimostrare che gap dashboard ↔ Binance ≤ 5%. Con bot biased (no brief 60b) il gap sarebbe ~28%, fuori soglia. Con brief 65c testnet, sapremo davvero se il bot oggi è già allineato a Binance o quanto deve migrare.

**Sito offline:** decisione confermata S67 — resta in maintenance fino a 24h testnet pulito (domani sera).

**Decisione pendente ricalibrazione Sentinel:** bundled in Step 4 pre-restart come da PROJECT_STATE, ma Sentinel è OFF (env flag). Da applicare quando ricolleghiamo i brain.

**~~⚠️ DECISIONE PENDENTE — Equity P&L vs FIFO realized~~ — RISOLTA in S67.** Strict-FIFO abbandonato in S65. Avg-cost canonico shipped in S66. Fee USDT canonical in S67. Tutta la sequenza che era oggetto del gap è ora chiusa: dashboard, P&L, reconciliation tutti su un'unica fonte di verità (avg-cost + fee USDT-equivalent).

**DRY_RUN Sherpa:** raccolta dati ~7 giorni (start ~6 maggio, deadline implicita ~13 maggio). Durante questa finestra: NON modificare costanti Grid/Sentinel. Admin dashboard Sentinel+Sherpa read-only **già live (S63)**. Decisione `SHERPA_MODE=live` = 1–2 settimane + Board approval. Percorso indipendente dal go-live €100.

**⚠️ DECISIONE STRATEGICA PENDENTE — Ricalibrazione Sentinel pre-replay vs post-replay (S63):**

I 3 bug calibrazione Sentinel rilevati 2026-05-07 grazie alla dashboard `/admin` (`speed_of_fall_accelerating` miscalibrato + risk score binario + opportunity score morta — vedi PROJECT_STATE §5) **rendono il replay counterfactual del 13 maggio probabilmente cieco**: Sherpa avrebbe proposto cambi guidati da segnali sbagliati, e il replay dimostrerebbe poco. Due opzioni:

- **(a) Ricalibrare ora** `score_engine.py` / `price_monitor.py`: invalida i 7gg di dati raccolti finora, ma evita un replay inutile. Counter riparte da zero.
- **(b) Lasciare correre** fino al 13 maggio: arriviamo al replay, scopriamo che è cieco, ricalibriamo poi e ripartiamo da zero. Stessi +7gg ma sprecati.

**Raccomandazione CEO (da decidere):** opzione (a) sembra più razionale, ma richiede di accettare che SHERPA_MODE → live slitti di 1-2 settimane oltre il 13-14 maggio originale. Decisione strategica del Board.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee, Stripe + PayPal). LemonSqueezy rifiutato (crypto risk flag). Nessuna urgenza di cambiare.

**Multi-macchina:** MBP (sviluppo Max) ↔ Mac Mini (runtime `/Volumes/Archivio/bagholderai`). Sempre `git pull` + mount Archivio prima di test/audit.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché no |
|---|---|
| **TF trading attivo** — S70 | Spento, in "osservazione" (dal dottore). Richiede brainstorming completo pre-riaccensione. Vedi `config/TF_RESTORE_INSTRUCTIONS.md` |
| **Volume 3 in lavorazione** — S70 | Non iniziato. Materiale si accumula (S65→S70 è un arco narrativo forte: Clean Slate + Testnet + FIFO Divorce + Sell Ladder + Hospital) |
| **X scanner automation evoluta** — S70 | Parcheggiato. Priorità è go-live mainnet 21-24 maggio. Posting manuale flag-it-when-it-happens funziona |
| **Marketing outreach attivo** — S70 | Parcheggiato fino a sito stabile con numeri mainnet. Sito testnet online è step 1, mainnet è step 2 |
| **Marketing zero attività** (sito offline, niente post X, niente outreach) — S68 update | "Prima i fondamentali" (Board). Pre-traction. Il prodotto (story) è in costruzione. Spingere traffico ora = mostrare un cantiere incompleto |
| **Sentinel/Sherpa/TF spenti, codice presente ma inattivo** — S68 | Filosofia minimum viable: solo Grid attivo finché non gira pulito |
| **Vendite Payhip 0/30 views** — S68 | Invisibilità (sito offline + zero canale promozionale), non difetto del prodotto |
| **Reconciliation gate Step 5 parcheggiato** — S68 | Era in scope S68 ma superato dalla priorità sell-in-loss guard. Candidato 69a o post |
| **Phase 2 Grid split (`grid_runner.py` 1627 righe)** — S68 | Parcheggiata post-go-live (BUSINESS_STATE §28 storico) |
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

---

*Prossimo aggiornamento: post deploy 69a o alla prossima sessione strategica.*
