# BUSINESS_STATE.md

**Last updated:** 2026-05-08 — Session 65 chiusura (Opzione 3 dashboard + bias avg_buy_price gating LIVE + schema drift skim fixato)
**Updated by:** CC + CEO (decision_s65_gap_reconciled.md)
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-08 (S65 chiusura)

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

**Post X:** nessun post in coda (`pending_x_posts` vuoto). Scanner X automatizzato a cron settimanale dal 2026-05-04. Strategia: "variable reinforcement" — pubblica quando succede qualcosa di vero, mai calendar-driven. Posting Strategy v1.1 in `Posting_Strategy_v1_1.docx`.

**Blog/contenuto:** il contenuto pubblico è il diary sul sito (/diary) e i volumi Payhip. Nessun blog esterno. Daily CEO's Log via Haiku + X posting (OAuth 1.0a) attivo.

**Ads/monetizzazione:** A-Ads live sul sito (crypto-native, revenue trascurabile). Buy Me a Coffee attivo (buymeacoffee.com/bagholderai). Nessuna sponsorship in pipeline.

**SEO/Analytics:** Umami Cloud (cookieless, GDPR) + Vercel Web Analytics. Progetto pre-traction, nessun dato di traffico significativo.

**Partnership/eventi:** nessuno in corso né in pipeline.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, 96 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, 108 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

Preview rimosse da entrambi i volumi.

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Nessuna struttura definita ancora. La session 63 è appena iniziata; il volume si chiuderà naturalmente quando un arco narrativo sarà completo (stima grezza: sessioni 70–80).

**Sessione corrente:** 63 (init). Session 62 diary .docx prodotto; entry in `diary_entries` da chiudere a COMPLETE.

**Check di congruenza diary↔DB:** nessun check automatico attivo. È un TODO nel Validation System §3 ("Diary entry in Supabase = diary .docx"). Da automatizzare.

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-08 (S65) | **Opzione 3 P&L: dashboard pubbliche/private mostrano SOLO Total P&L** (Net Worth − budget). Realized DB rimosso, vive solo in `/admin` Reconciliation come audit interno con identity check. | Le 4 dashboard mostravano 3 numeri diversi (gap fino a $26 home vs grid+tf); root cause = bias `avg_buy_price` del bot che gonfia `trades.realized_pnl` del 28%. Total P&L è l'unico numero matematicamente coerente e identico a Binance live mainnet. |
| 2026-05-08 (S65) | **Brief 60b promosso a GATING per go-live €100**. Il bot deve scrivere `realized_pnl` strict-FIFO. Pre-requisiti go-live aggiornati a 6 punti, target 16-20 maggio (slittato di 4-8 gg). | Senza, dashboard ↔ Binance divergerebbero del 28%. Il gate "gap ≤ 5%" del CEO non è verificabile con bot biased. |
| 2026-05-08 (S65) | **Schema drift `reserve_ledger.managed_by` fixato in DB** via JOIN su `trade_id` (181 righe migrate). Rename `manual → grid` su tutto il sistema **parcheggiato** post-go-live. | Coerenza interna ledger ↔ trades. Rinomina su 4 tabelle è troppo invasiva durante DRY_RUN Sherpa (contamina counterfactual). Da fare post-Phase 2 stabile. |
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

1. **Equity P&L nella home** — proposta 1 del report CC 05/05: secondo numero "Equity P&L" affiancato al FIFO realized. Stima CC: 1–2 ore. Aspetta decisione CEO (§6).

2. **Allineamento sell-decision a FIFO globale** — proposta 2 del report CC 05/05: il bot vende basandosi su `avg_buy_price` (media mobile) che diverge dal costo FIFO del lotto in uscita. Su mainnet = vendere lotti in perdita FIFO credendoli in profitto. Stima CC: 1 giorno. **Vero gating tecnico per mainnet**, da posizionare nella timeline post-Phase 2.

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

19. **[S65 NEW] Rename `manual` → `grid` su tutto il sistema** (parcheggiato post-go-live): standardizzare nomenclatura `bot_config.managed_by`, `trades.managed_by`, `reserve_ledger.managed_by`, `daily_pnl.managed_by` da `manual` (legacy v3) a `grid`. Tocca 4 tabelle DB, codice bot Python, frontend dashboards. Stima ~3-4h. **NON farlo durante DRY_RUN Sherpa** (rinomina = restart = contaminazione counterfactual). Finestra utile: post-Phase 2 stabile + post-go-live €100. Coerenza interna del ledger già fixata in S65 via JOIN su `trade_id`.

---

## 6. Vincoli / Deadline Non-Tecnici

**Go-live €100 — target aggiornato 16-20 maggio 2026** (decision CEO 2026-05-08, slittato di 4-8 giorni per brief 60b promosso a gating).

**Pre-requisiti go-live (decision_s65_gap_reconciled.md):**
1. ✅ Opzione A (DB-based dashboards) — shipped commit `f143634`
2. ✅ Opzione 3 (dashboards mostrano Total P&L, Realized in /admin) — shipped S65
3. ✅ Schema drift skim fixato — DB UPDATE one-shot S65
4. ⬜ **Brief 60b** (bot scrive realized_pnl strict-FIFO, fix bias avg_buy_price +28%) — gating
5. ⬜ Phase 2 Grid (brief 62b: fix 60c + dust) — gating
6. ⬜ Board approval finale (Max)

**Removed/downgraded prerequisites (decision CEO 2026-05-08):**
- ~~7 giorni clean FIFO drift post-Phase 2~~ → cancellato, calibriamo sul campo con €100 reali
- ~~7 giorni clean health check~~ → cancellato, idem
- ~~Sell-decision alignment a FIFO globale (proposta 2 CC del 5 maggio)~~ → da verificare sul campo, non gating pre-live

**Pre-live gates (Validation System §6):**
- FIFO integrity: ✅
- DB retention stabile: ✅
- Bias avg_buy_price `realized_pnl`: 🔲 (brief 60b, gating)
- Board approval (Max): 🔲

**Obiettivo go-live**: dimostrare che gap dashboard ↔ Binance ≤ 5%. Con bot biased (no brief 60b) il gap sarebbe ~28%, fuori soglia.

**⚠️ DECISIONE PENDENTE — Equity P&L vs FIFO realized:**

Dal report CC 2026-05-05 e punto 6.1 di PROJECT_STATE.md: *"Equity P&L Binance ($48.16) vs FIFO realized ($52.69): gap strutturale $4.53. Quale numero diventa canonico nella dashboard pubblica e nel diary? È gating per il go-live €100?"*

**Raccomandazione CEO:**

- **Dashboard pubblica:** mostrare entrambi affiancati. FIFO realized = "quanto abbiamo incassato". Equity P&L = "quanto vedremmo su Binance chiudendo tutto". Proposta 1 di CC (1–2 ore) è la soluzione giusta.
- **Diary:** FIFO realized come numero operativo; citare il gap equity come nota di onestà quando rilevante. Delta del 9%, non un ordine di grandezza.
- **Go-live gating:** il gap numerico non è gating di per sé. **Quello che è gating è la proposta 2 di CC** (allineare la sell-decision a FIFO globale). Senza, il bot su mainnet vende lotti in perdita FIFO pensando di essere in profitto. Da posizionare in Phase 2 o subito dopo.

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
| **Nessun marketing attivo** | Pre-traction. Il prodotto (story) è in costruzione. Spingere traffico ora = mostrare un cantiere incompleto. Strategia flag-it-when-it-happens |
| **Nessun Volume 3 in lavorazione** | Le sessions 53+ sono in corso. Il volume si chiuderà naturalmente su un arco narrativo chiuso |
| **Nessuna dashboard /sentinel pubblica** | Sprint 2+. DRY_RUN non ha dati sufficienti per un'interfaccia utile. Design approvato, codice bloccato fino a post-replay (~13 maggio) |
| **Nessun Sentinel slow loop (F&G + CMC)** | Sprint 2. Sprint 1 (fast loop BTC + funding) deve raccogliere dati e fare replay counterfactual prima |
| **Nessun go-live €100** | Pre-live gates non superate. Phase 2 Grid ancora da fare. Architettura completa (TF + Sentinel maturo + orchestrator superiore) richiede mesi, non settimane |
| **Nessuna partnership esterna** | Il progetto non ha traction. Prematuro cercare partner senza prodotto finito e traffico organico |
| **Admin dashboard Sentinel+Sherpa non implementata** | Design pronto (~9h frontend). Bloccata: toccare costanti Grid durante DRY_RUN invalida il counterfactual |
| **Nessun cambio prezzo volumi** | €4.99 è il prezzo di lancio. Nessun dato di vendita su cui ragionare |
| **BTC in portafoglio live** | Costi di conversione USDT→BTC troppo alti per budget €100. Decisione differita |
| **Audit esterni** | Protocollo appena introdotto (S63). Primo audit previsto: V1 Calibration su Sentinel↔Sherpa↔Grid post-Phase 1. Nessuno completato ancora |

---

*Prossimo aggiornamento: a fine sessione 63 o alla prossima sessione strategica.*
