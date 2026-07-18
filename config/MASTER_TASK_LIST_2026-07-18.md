# BagHolderAI — Master Task List

**Data:** 18 giugno 2026 (creata) · **Ultimo aggiornamento:** 18 luglio 2026 (**S120 canale Telegram**: T.1 contenuti ✅ **SHIPPED+LIVE** — publisher `telegram_publisher.py` cron 10min sul Mini con status+pin/diario/regime F&G/rassegna stampa; T.2/T.3 fix daily report **CODED, pending restart** bot; alert trade parcheggiato. Prec. 12-lug: K.1 Fase 1 ✅ SHIPPED S118)
**Regola:** niente nuovi task salvo bug fix e il **cutover Kraken** (forzato da MiCA, Board-approved). Si finisce quello che c'è.

---

## FASE 1 — PRE-MAINNET / CUTOVER KRAKEN

Contesto: Binance EU ha sospeso gli ordini spot dal **1-lug** (MiCA). Venue di go-live = **Kraken USD** (deciso S112b). L'adapter è già shippato **dormiente** (S112b, `bot/exchanges/`); manca il cablaggio dell'hot-path (= cutover). Trigger cutover: **Max consegna le chiavi API Kraken** (aggiornato 2026-07-07 — il vecchio gate "reset testnet Binance" è superato: Binance EU ha già sospeso gli ordini spot dall'1-lug, quindi non c'è più un reset da aspettare).

| # | Cosa | Dipende da | Chi | Stato |
|---|---|---|---|---|
| K.1 | **CUTOVER Kraken — Fasi 0-4 (Max, 11-lug)**. Chiavi API ✅ (Withdraw OFF). **Fase 0 ✅**: plumbing 18/18 — fee taker 0,80% tier-0. **Fase 1 ✅ SHIPPED S118 (11-12 lug)**: venue per-riga + cablaggio hot-path + fee dinamica + floor fee-aware + fix contabile + hands-off Sherpa + gate `ALLOW_REAL_MONEY` + bonifica cycle-fetch + disclaimer-toggle. Invariante binance: zero diff (290 test). **⚠️ Review avversaria S118 → 2 BLOCKER da fixare PRIMA della Fase 2** (`config/2026-07-12_S118_review-findings.md`, PROJECT_STATE §5): 🔴 KrakenClient normalizza ogni ordine reale come non-eseguito (serve follow-up `fetch_order`); 🟠 cycle-fetch sito non venue-robusto. + 2 MEDIUM (`_alert_rejection` su validate; fallback cycle) + 2 LOW. **Fase 2 spezzata da Max in 2a+2b (12-lug); ⚠️ $100 GIÀ su Kraken (fermi).** **Fase 2a**: risolvere i 2 blocker + 2 medium (review) + nuovi test; accettazione = **ordine reale minimo ~$3-5 sorvegliato** (prova il fix critical, i test verdi non bastano). **Fase 2b**: nodo 5 (parametri, margine floor 0,4%) → runbook finestra coordinata (insert righe kraken → is_active flip → disclaimer on → `ALLOW_REAL_MONEY=true` → restart) → grid sui $100 caricati. **Fase 3** collaudo. **Fase 4** deployment | 2a: fix+test · 2b: switch+Max | CC + Max | **Fase 1 ✅ · 2 blocker aperti · 2a prossima** |
| K.2 | **WebSocket `executions` Kraken** — feed fill real-time (oggi polling: regge, ma è il pezzo "nuovo di paradigma") | dopo K.1 | CC | fast-follow |
| K.3 | **Frontend cutover** — homepage (live-snapshot Kraken + badge "real money, real Kraken" + scena hero aggiornata) + dashboard (sezione disclaimer in alto, TF congelata, Grid filtrato a moneta attiva, reconciliation Kraken) + pagina-disclaimer toggle per le finestre di setup (piano confermato Max 2026-07-07, `config/COLLAUDO_COMMS_GUIDELINES_v1.md`) | dopo K.1 | CC (design) + CEO (copy) | pending |
| K.4 | **Nonce Kraken** — alzare "Nonce Window" lato account + valutare subaccount/chiave per-coin (grid = 1 processo per coin, nonce per-chiave) | al cutover | Max + CC | pending |
| 1.3 | **Sessione go-live experiment** — formalizzare rampa/rabbocco/verdetto/Victory Lap (da `config/APPROVED_golive_experiment_design.md`). Venue Kraken USD; lineup **BTC $250 / SOL $150 / BONK $100** (grid) + **TF $100** (dalle /USD) | K.1 | CEO + Max | **PENDING** |
| 1.8 | **Board approval call** (go/no-go €100 reali) | 1.3 + cutover | Max | **PENDING** |

---

## FASE 2 — CONTENUTI / BLOG (parallela, non bloccante)

| # | Cosa | Stato | Chi | Note |
|---|---|---|---|---|
| 2.1 | Cross-post "non-coder-5-brains" → Substack | Pronto | Max | ~15min, copia+adatta |
| 2.3 | Pubblicare "why-most-ai-trading-bots-fail.md" ⭐ | SEO già forte (head keyword "ai trading bot" + FAQ + intro GEO); serve SOLO intro umana | CEO rivede → Max intro → CC pubblica | two-voice |
| 2.4 | "ai-crypto-trading-bot-real-testnet-results.md" | PARKED — placeholder data | — | sblocca post go-live |
| 2.5 | "Thirty-Two Hours" Dev.to cross-post | Draft su Dev.to | Max intro + lezione tecnica | da PARKED_blog_voice_strategy |
| 2.6 | **🆕 Blog post sul grid-regime backtest** — raccontare il verdetto "**il grid è un ammortizzatore di volatilità, non un motore**": confermato su 3 coin (bear batte hold, bull hold stravince, laterale vero grid vince; più choppy = più edge, BONK +5.2 p.p.). L'onestà è il differenziante narrativo | **SBLOCCATO** — 2.7 fatto, dataset BTC+SOL+BONK pronto | CC (draft) + CEO/Max | usa i dati backtest S113+S115 |
| 2.7 | **🆕 Estendere il backtest a SOL e BONK** — finora fatto **solo BTC** (3 regimi). Rifare su SOL e BONK con lo stesso harness (`scripts/backtest/`, fee Kraken, output gitignored) → chiude i backtest e alimenta 2.6 | ✅ **FATTO S115** (02-lug, `f9e8a98`) — nuovo `scan_regimes.py` + harness multi-coin; report `report_for_CEO/2026-07-02_grid-regime-backtest-sol-bonk_report_for_ceo.md` | CC | chiude i backtest |
| 2.8 | **🆕 Campagna X "Fails & Masterpoints"** (con CEO) — setacciare **TUTTE le sessioni + i diari**, estrarre i **fallimenti** autentici e i **colpi vincenti** ("masterpoint"), e trasformarli in post X che si chiudono con una **domanda alla community** per generare engagement. Es.: *"Anche a voi l'AI sbaglia l'analisi dei numeri? Quale state usando?"*. Materiale tutto interno (diary Supabase + transcript sessioni); sfrutta il listener `/approve` appena riparato | CEO (voce/cura) + **CC ✅ mining done 03-lug** + Max (/approve) | **CC done 2026-07-03**: dossier 69 post distinti/11 filoni + tracker CSV in `drafts/` (gitignored) → CEO per voce/selezione. ~150 momenti grezzi → **69 lezioni distinte** (ceiling non-ripetitivo, NON 230); riserva TIER-C catalogata. Memoria `project-x-campaign-fails-masterpoints` |
| 2.9 | **🆕 Backtest hand-off TF** — quando Sentinel dichiara BULLISH, passare grid→TF (ride a piena allocazione, può piramidare, no guardia "no buy above avg") e misurare quanto ci si avvicina al hold nel bull mantenendo il grid come ammortizzatore fuori. **Follow-up esperimento trend-gate S115**: il grid da solo NON cattura il bull in modo robusto (overfit N=1). Modellare il TF nel harness `scripts/backtest/` (grid-only vs grid+TF-handoff vs hold, BTC/SOL/BONK × 3 regimi) | Da fare | CC | report contesto `report_for_CEO/2026-07-02_grid-trend-capture-experiment_report_for_ceo.md` |

---

## FASE 3 — SUBITO DOPO GO-LIVE

| # | Cosa | Note |
|---|---|---|
| 3.1 | **Monitor "griglia silenziosa"** — alert quando una griglia non trada da X ore | Brief da scrivere (buco osservabilità S105). Soglia X da decidere |
| 3.2 | Verifica commenti Haiku | Da todo Board |
| 3.5 | BNB-discount fee future-proof — colonna `fee_native_amount` | Pre scale-up |

---

## FASE 4 — POST GO-LIVE / BACKLOG

| # | Cosa | Trigger |
|---|---|---|
| 4.1 | Sentinel oltre F&G Index (Phase B, coin-aware EMA/RSI) | dopo stabilità mainnet |
| 4.2 | TF distance filter + regime-awareness (12% fisso paralizza TF) | post Brain Analysis |
| 4.3 | Calibrare BASE_TABLE Sherpa se troppo distante | post-analysis |
| 4.4 | Pagina /news pubblica con label AI | post verdetto barometro |
| 4.5 | Tabella "Performance per regime" in dashboard | serve profondità dati mainnet |
| 4.6 | History paper mode sito/blog | quando ha senso |
| 4.7 | Guida all'uso | quando ha senso |
| 4.8 | Patience timer per sell ladder | serve dati reali testnet cycle 2 |
| 4.9 | Script replay counterfactual Sherpa | da brief 80a |
| 4.10 | Decidere TRUNCATE tabelle Sentinel/Sherpa/TF paper-era | quando si ricollega brain |
| 4.13 | TF dashboard card per-coin mode-aware (Path 2) | quando TF trada diretto (`managed_by='tf'` > 0) |

---

## 🆕 CANALE TELEGRAM (attivo — non più "congelato")

> 📋 **BRIEF DI SESSIONE CONSOLIDATO: [`config/2026-07-18_brief_telegram-session.md`](2026-07-18_brief_telegram-session.md)** — mette in un posto solo T.1/T.2/T.3 + infra canale + mappa codice + le 4 decisioni aperte + i drift da risolvere (v1 ritirato, .env stale). **Da leggere per primo** all'apertura della sessione Telegram.

Contesto: il listener `/approve` è stato **riparato 1-lug** (era morto dal 2/6, `bfe3433`); il canale report è **privato ma aperto al pubblico** (anti-squat: canale attivo + iscritti = nome al sicuro — memoria `reference_telegram_channel_squat`).

| # | Cosa | Chi | Note |
|---|---|---|---|
| T.1 | **🆕 Rivedere i contenuti del canale Telegram** (il privato ma aperto al pubblico) — cosa pubblicare oltre al daily report per tenerlo vivo e dare valore agli iscritti (anti-squat) | CC + Max | ✅ **SHIPPED+LIVE S120** — sottosistema `telegram_publisher.py` (cron 10min sul Mini): (a) status line post+pin, (b) diario, (c) regime F&G debounced, (d) rassegna stampa 1×/gg. Alert trade (idea 5) **parcheggiato** (Max ci pensa). Pin solo su status line. |
| T.2 | **🆕 [BUG] Daily report del canale: mostra i guadagni delle vendite ma non le perdite delle posizioni aperte** — la riga "Today · Realized 🟢 $+X" somma solo i `realized_pnl` delle vendite del giorno (`scripts/send_daily_reports_now.py:48` + formula in `commentary.py`), ignorando la variazione **unrealized** (spesso negativa) delle posizioni aperte → quadro falsamente positivo (es. 01/07: Today +$1.05 mentre BTC −2.1%, BONK −7.3%, ETH −8.9%). Fix: aggiungere il **P&L mark-to-market del giorno** (delta equity vs snapshot di ieri, infra `daily_pnl`). Onestà / one-source-of-truth | CC | ✅ **CODED S120** `f4c2d95` (**solo report privato**, scelta Max; il pubblico è già onesto via frecce+P&L rosso). Riga "Day P&L (Grid): realized+paper" via `get_yesterday_grid_pnl` phantom-invariant. **Effetto al prossimo RESTART bot.** |
| T.3 | **🆕 [BUG — VERIFICATO 2026-07-18] Il report Telegram eredita il fantasma $25 Kraken** (lato bot, NON risolto dal fix sito S119b). **Causa**: `commentary.py:503-514` `get_grid_state` somma `capital_allocation` di **tutte** le righe `managed_by=grid` **senza filtro venue/is_active** (il commento dice pure "Inactive coins still contribute their slice") → con la riga collaudo Kraken `BTC/USD` ($25, `venue=kraken`, `is_active=false`) il `grid_budget = 525` invece di 500, mentre i trade sono filtrati per cycle (Kraken escluso) → il **Total P&L del report è depresso di $25** (baseline gonfiato). `get_grid_state` alimenta **sia il daily report Telegram sia lo snapshot `daily_pnl`** (per questo `daily_pnl.initial_capital` è saltato 500→525 il 17-lug). **Fix** = 1 riga: aggiungere `.eq("venue","binance")` alla query `bot_config` (riga 506), **stesso identico fix già fatto sul sito** (`GRID_BUDGET` filtra venue, commit `f6388b6`). NB: il cycle è già a posto (`get_current_cycle` path globale pinnato `venue=binance`, S119, `db/client.py:45`). **È lato bot → serve restart**; è la STESSA correzione del parked `config/parked/PARKED_daily_pnl_canonical_fase2b.md` (work item A) → **conviene farla insieme a quella, al restart della Fase 2b** (ciclo nuovo azzera pure la deriva dust-reset storica). Se la si vuole prima (report letto ogni giorno), è comunque 1 riga + restart. | CC | ✅ **CODED S120** `0965471` (`get_grid_state` filtra `venue=binance`; sana report Telegram **e** snapshot `daily_pnl`, gemello del fix sito `f6388b6`). **Effetto al prossimo RESTART bot.** |

---

## CONGELATO (non toccare, non pianificare)

| Cosa | Perché |
|---|---|
| X Scanner automazione weekly cron | manuale on-demand per ora |
| IG/Canva | post risultati cambio tono Haiku X |
| Anthropic Admin API (costi Haiku) | parked |
| Security audit (headers, CSP, RLS) | parked |
| Breadth Tier 3 come segnale Sentinel | parked S109 (analisi 6 mesi negativa in fear, ridondante con F&G); re-test post risk-on. Script `scripts/breadth_analysis_s109.py` |
| Newsletter/mailing list blog | post-lancio V3 |
| Reddit r/ClaudeAI | serve 50 karma (Max karma building) |
| HN | account shadowbannato, serve nuovo account |
| Post Show HN / X su Sentinel+Sherpa | post go-live |
| NewsKeeper modulo 2 Grok/X scanner | post-mainnet, API X premium |
| Brain Analysis round 2 | serve NewsKeeper maturo |
| Futures/hedging | post-mainnet, capitale >€100 |

---

## BUG APERTI

| Bug | Priorità | Chi | Stato |
|---|---|---|---|
| Daily report canale: unrealized non mostrato (vedi **T.2**) | Med (onestà) | CC | 🟡 **CODED S120** `f4c2d95` (report privato), **pending restart** |
| Report Telegram + `daily_pnl`: fantasma $25 Kraken nel budget (`get_grid_state` no filtro venue, vedi **T.3**) | Med (onestà, baseline P&L −$25) | CC | 🟡 **CODED S120** `0965471` (`venue=binance`), **pending restart** |
| PGRST100 "failed to parse columns" nel TF (warning ricorrente nei log) | Low | CC | aperto (PROJECT_STATE §5) |

---

## DECISO DI RECENTE (non riaprire)

- **4.11** Recalibrate-on-restart (buy_pct al boot) → CHIUSO S111: era `config_sync` al boot in DRY_RUN, risolto da Sherpa LIVE S102b.
- **4.12** BONK last-shot floor → DECISO S111: tenere **$5 fisso** (anti-micro-buy).
- **4.14** Compounding grid → DECISO S111: **Opzione A** (lotto fisso, rischio/trade costante).
- **realized_pnl** drift → Fix A (sito) S111 + **churn-avg-fix Piano A** shipped+LIVE S113 (`8d2fdd6`).
- **Audit A1** remediation → S114 (retention newskeeper 90gg + fix test-leak, `81d00dd`).
- **X-poster `/approve`** morto dal 2/6 → riparato 1-lug (LaunchAgent launchd, `bfe3433`).

---

## DIARIO

- Volume 4 "From Eyes to Live" (S83+): in corso, arco NewsKeeper → go-live → primi risultati. Nessun task — si scrive sessione per sessione.

---

*Compilata: CEO, 18 giugno 2026. Aggiornamenti CC: 18/25/26 giugno.*

*Aggiornato: CC, 1 luglio 2026 — allineato a S111-S114 + pivot Kraken. **Rimossi** gli item chiusi: FASE 0 (barometro + Sherpa verdetti), 1.1/1.2/1.2b/1.4/1.5/1.6/1.7, 2.2, 3.3/3.4, 4.11, e i 4 bug S109 (exchange_order_id, datetime.utcnow, PortfolioManager, validation §2). **Aggiunti:** cutover Kraken (K.1-K.4), estensione backtest SOL/BONK + blog post (2.6/2.7), contenuti canale Telegram + bug daily-report unrealized (T.1/T.2). 4.12/4.14/4.11 → sezione "Deciso di recente".*

*Aggiornato: CC, 18 luglio 2026 (**S120**) — canale Telegram. **T.1** (contenuti canale) ✅ **SHIPPED+LIVE**: nuovo sottosistema `telegram_publisher.py` (cron 10min send-only sul Mini, tabella `telegram_publish_state`) con 4 feature — status line post+pin / diario / regime F&G debounced / rassegna stampa 1×/gg; seminati i 4 post attuali + cron attivo; **alert trade (idea 5) parcheggiato** (Max ci pensa). **T.2/T.3** (bug daily report) **CODED+test** (`f4c2d95`, `0965471`), **effetto al prossimo restart bot**. File **rinominato** `MASTER_TASK_LIST_2026-07-12.md` → `MASTER_TASK_LIST_2026-07-18.md` (convenzione: data-nel-nome = ultimo aggiornamento). Bug T.2/T.3 → CODED-pending-restart nella sezione BUG APERTI.*
