# BagHolderAI — Master Task List

**Data:** 18 giugno 2026 (creata) · **Ultimo aggiornamento:** **7 agosto 2026 (S125 — CUTOVER COMPLETO + REVEAL PUBBLICO)**

> **Il progetto ha cambiato stato.** Non è più "un sistema su testnet che si prepara al denaro reale": è **un sistema che tratta denaro reale e lo dichiara pubblicamente** (sito live dalle 19:15 UTC del 7-ago). Il testnet Binance non esiste più — si è azzerato il 5-6 agosto e non è stato riaperto. Su Kraken gira tutto: BTC/USD $250 + SOL/USD $150. Il Trend Follower è fermo.
>
> Di conseguenza **la Fase 1 di questa lista è chiusa** e le priorità si sono spostate: il lavoro che conta ora non è "arrivare al denaro reale" ma **rendere affidabile ciò che già lo tratta** — a partire dalla riconciliazione, che su Kraken non esiste.

**Regola:** niente nuovi task salvo bug fix e ciò che rende sicuro il denaro reale. Si finisce quello che c'è.

---

## FASE 1 — PRE-MAINNET / CUTOVER KRAKEN

Contesto: Binance EU ha sospeso gli ordini spot dal **1-lug** (MiCA). Venue di go-live = **Kraken USD** (deciso S112b). L'adapter è già shippato **dormiente** (S112b, `bot/exchanges/`); manca il cablaggio dell'hot-path (= cutover). Trigger cutover: **Max consegna le chiavi API Kraken** (aggiornato 2026-07-07 — il vecchio gate "reset testnet Binance" è superato: Binance EU ha già sospeso gli ordini spot dall'1-lug, quindi non c'è più un reset da aspettare).

| # | Cosa | Dipende da | Chi | Stato |
|---|---|---|---|---|
| ~~K.1~~ | ✅ **CUTOVER Kraken COMPLETATO** — Fasi 0/1/2a/2b/3 tutte chiuse. Denaro reale dal **17-lug** (ordine di prova $25 confermato a mano), autonomo dal **22-lug**, sistema intero su Kraken dal **7-ago** ($250 BTC + $150 SOL, testnet abbandonato). I 2 blocker della review S118 risolti in Fase 2a (fill via `fetch_order`+halt, cycle-fetch venue-robusto). Storico: `briefresolved.md/`, report in `report_for_CEO/resolved/` | — | CC + Max | ✅ **CHIUSO S125** |
| ~~K.1-old~~ | *(testo storico)* **CUTOVER Kraken — Fasi 0-4 (Max, 11-lug)**. Chiavi API ✅ (Withdraw OFF). **Fase 0 ✅**: plumbing 18/18 — fee taker 0,80% tier-0. **Fase 1 ✅ SHIPPED S118 (11-12 lug)**: venue per-riga + cablaggio hot-path + fee dinamica + floor fee-aware + fix contabile + hands-off Sherpa + gate `ALLOW_REAL_MONEY` + bonifica cycle-fetch + disclaimer-toggle. Invariante binance: zero diff (290 test). **⚠️ Review avversaria S118 → 2 BLOCKER da fixare PRIMA della Fase 2** (`config/2026-07-12_S118_review-findings.md`, PROJECT_STATE §5): 🔴 KrakenClient normalizza ogni ordine reale come non-eseguito (serve follow-up `fetch_order`); 🟠 cycle-fetch sito non venue-robusto. + 2 MEDIUM (`_alert_rejection` su validate; fallback cycle) + 2 LOW. **Fase 2 spezzata da Max in 2a+2b (12-lug); ⚠️ $100 GIÀ su Kraken (fermi).** **Fase 2a**: risolvere i 2 blocker + 2 medium (review) + nuovi test; accettazione = **ordine reale minimo ~$3-5 sorvegliato** (prova il fix critical, i test verdi non bastano). **Fase 2b**: nodo 5 (parametri, margine floor 0,4%) → runbook finestra coordinata (insert righe kraken → is_active flip → disclaimer on → `ALLOW_REAL_MONEY=true` → restart) → grid sui $100 caricati. **Fase 3** collaudo. **Fase 4** deployment | 2a: fix+test · 2b: switch+Max | CC + Max | **Fase 1 ✅ · 2 blocker aperti · 2a prossima** |
| K.2 | **WebSocket `executions` Kraken** — feed fill real-time (oggi polling: regge, ma è il pezzo "nuovo di paradigma") | dopo K.1 | CC | fast-follow |
| ~~K.3~~ | ✅ **Frontend cutover FATTO S125 (7-ago)** — homepage + dashboard su Kraken, badge "real money on kraken", riga "The logic is real. So is the money.", `/history` per le ere chiuse, `/terms` sanata (chiude finding H1 audit A2), guidelines emendate a v3, pannelli privati Kraken-only. **7 superfici** avevano numeri o filtri cablati sul venue vecchio. Dettaglio: `report_for_CEO/2026-08-07_S125b_RforCEO_real-money-reveal.md` | — | CC | ✅ **CHIUSO** |
| ~~K.3-old~~ | *(testo storico)* **Frontend cutover** — homepage (live-snapshot Kraken + badge "real money, real Kraken" + scena hero aggiornata) + dashboard (sezione disclaimer in alto, TF congelata, Grid filtrato a moneta attiva, reconciliation Kraken) + pagina-disclaimer toggle per le finestre di setup (piano confermato Max 2026-07-07, `config/COLLAUDO_COMMS_GUIDELINES.md`) | dopo K.1 | CC (design) + CEO (copy) | pending |
| ~~K.4~~ | ✅ **Nonce Kraken CHIUSO** — Max ha impostato la Nonce Window a **10.000 ms** sulla chiave; il codice usa già numerazione al microsecondo (`kraken_client.py:68-73`). Nota: la finestra si imposta **solo alla creazione** della chiave, non è modificabile dopo. Subaccount per-coin: non serve, i 2 processi convivono | — | Max ✅ | ✅ **CHIUSO** |
| 1.3 | **Sessione go-live experiment** — rampa/rabbocco/verdetto/Victory Lap (da `config/APPROVED_golive_experiment_design.md`). ⚠️ **Parzialmente superata dai fatti**: il lineup previsto era BTC $250 / SOL $150 / **BONK $100** + TF $100; la realtà è BTC $250 + SOL $150, **BONK escluso** (volume Kraken $29K/24h) e **TF fermo**. Resta da formalizzare: **quando si rabbocca, con che criterio, e cosa dichiara "riuscito" il collaudo** — oggi non c'è una soglia scritta | — | CEO + Max | **PENDING, da riscrivere** |
| ~~1.8~~ | ✅ **Board approval** — dato da Max il **21-lug (S121)**, Opzione B: 1 moneta / $100 / tutto il resto invariato. Il go-live è avvenuto | — | Max ✅ | ✅ **CHIUSO** |

---

## 🔴 FASE 1b — RENDERE AFFIDABILE IL DENARO REALE (nuova, S125)

Il cutover è fatto. Questa è la lista di ciò che manca perché il sistema che tratta denaro vero sia **verificabile**, non solo funzionante. Ordinata per gravità.

| # | Cosa | Perché adesso | Chi | Stato |
|---|---|---|---|---|
| **R.1** | **Riconciliazione Kraken** — oggi `scripts/reconcile_binance.py` parla solo con Binance, e persino le colonne di `reconciliation_runs` sono Binance-shaped (`binance_count`, `unmatched_binance_count`). Serve: script che interroghi Kraken + colonne venue-agnostiche + cron. **E spegnere o riconvertire il cron attuale**, che alle 03:00 interroga un exchange su cui non operiamo | È il controllo che prova che i trade a DB corrispondono agli ordini veri. Sul testnet era una formalità; **sul denaro reale è l'unica cosa che separa "i conti tornano" da "crediamo che tornino"**. Dichiarato anche dentro `/admin` | CC | 🔴 **PRIORITÀ 1** |
| **R.2** | **`trades` non ha colonna `venue`** — e `mode` non serve a distinguere: vale `'live'` per **tutte e 319** le operazioni, testnet incluso (significa "mandato a un exchange", non "soldi veri"). Oggi l'unico appiglio è la **stringa del ciclo**: contiamo come reale ciò che si chiama `kraken*` | Convenzione sui nomi, non un dato. Il 7-ago è costata **due guasti veri** (report serale sul portafoglio morto, superfici pubbliche congelate). Un ciclo battezzato fuori-schema verrebbe contato male | CC | 🟠 alla prossima migrazione |
| **R.3** | **Cap di rifiuto sullo slippage del fill, per-venue** — bug ETH bad-tick aperto da S122: fill accettati a **+15%** di slippage senza rifiuto, solo un avviso dopo | Il gate BONK si è allontanato (BONK escluso), ma BTC e SOL girano a **denaro reale** senza quel cap, e il book SOL è meno profondo di quello BTC | CC | 🟠 aperto |
| **R.4** | **`trend_config` dietro il portiere** — la Edge Function `config-write` copre solo `bot_config`, quindi il Save di `/tf` è spento | Non urge: il TF è fermo. Rientra quando rientra lui (~50 colonne in allowlist) | CC | 🟡 con il TF |
| **R.5** | **`passive_income`** è l'ultima tabella con scrittura anonima aperta (editor `/admin` per le cifre di `/income`) | Non muove denaro, ma è la stessa porta. Stesso portiere | CC | 🟡 coda |
| **R.6** | ~~`bot_state_snapshots.last_trade_at` riporta l'ultimo *recalibrate*, non l'ultimo trade~~ → **non è un bug di dato: è un nome sbagliato, e non si ripara.** La colonna contiene un valore legittimo (l'ultimo recalibrate) sotto un nome che ne promette un altro — tanto che `bot_runtime_state` salva lo **stesso identico valore** col nome giusto, `last_recalibrate_at`. La fonte per "da quanto non opera questo bot" **è e resta la tabella `trades`**: mai toccata dalla retention, mentre gli snapshot vengono potati a 7 giorni — la copia è deperibile, la fonte è permanente. Rinominare la colonna **solo se/quando** si tocca lo schema degli snapshot per altri motivi: un rename è migrazione + caccia a tutti i filtri letterali, per una colonna che non legge nessuno (verificato S126: zero riferimenti in `web_astro/`) | Max, 09-ago: *"abbiamo già tabelle pubbliche e private con l'elenco dei last trade, a cosa mi serve tutto questo?"* — obiezione corretta, il fix proposto riparava una copia settimanale di un dato già disponibile e giusto. Il rischio residuo è di **abitudine**, non tecnico: il campo si chiama "ultimo trade" e chi ci passa sopra ci crede (è successo in una prep di brief). La difesa è sapere che la fonte è `trades`, non cambiare il valore | CC | ⚪️ **CHIUSA come non-lavoro** (S126, 09-ago) |

---

## 🧪 ESPERIMENTO XRP — MISURARE LA COMMISSIONE MAKER (nuovo, S125)

**Perché è il lavoro col maggior effetto sui numeri fra tutti quelli in lista.**

Oggi paghiamo **0,80% taker** a ogni operazione. Il dato del 7-ago: **+$0,87 di guadagno latente contro $0,94 di commissioni** — il mercato ci ha dato ottantasette centesimi, il broker ne ha presi novantaquattro. E l'archivio delle ere lo dice in modo ancora più netto: **30 ordini al giorno** sul paper a $0,0144 di commissione, **0,2 al giorno** su Kraken a $0,2702. La strategia non è cambiata; è cambiato il prezzo di sbagliare.

Il listino Kraken dà la **maker fee a 0,25%** — un terzo. Se si conferma, a parità di tutto il resto quella riga da −$0,07 diventa **+$0,58**.

⚠️ **Il listino è già stato smentito una volta**: dichiarava 0,40% taker, sul fill reale abbiamo pagato **0,7999%**. Quindi non si progetta niente su un numero letto: **si misura**.

| # | Cosa | Stima | Chi | Stato |
|---|---|---|---|---|
| **X.1** | **Un singolo ordine limite su XRP/USD, sorvegliato, per leggere l'addebito reale.** Nient'altro: nessuna macchina, nessuna integrazione. Serve solo a rispondere "quanto ci addebitano davvero quando siamo maker?" | ~30 min | CC + Max | 🆕 **PRONTO** — non dipende da nulla |
| **X.2** | **Decisione dopo X.1**: se la maker fee è confermata, vale la pena costruire la gestione degli ordini in attesa? Cambia il motore del grid da "market order" a "limite + gestione code" | — | Max + CEO | 🆕 dipende da X.1 |
| **X.3** | **Macchina completa di gestione ordini in attesa** (piazzamento, riprezzamento, cancellazione, fill parziali, timeout) | **settimane**, non ore | CC | 🔲 solo se X.2 dice sì |

> **Da tenere separati X.1 e X.3.** Il primo è una misura da mezz'ora che produce un dato; il terzo è un cambio di paradigma del motore. Confonderli è il modo migliore per non fare nessuno dei due.
>
> **Escluso dal Board (7-ago): il margine.** Proposto e ritirato nella stessa sessione — il bot non ha modello contabile per la leva (le posizioni a margine non compaiono in `fetch_balance()`), e il DCA del grid *è* il comportamento che viene liquidato.

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
| T.1 | **🆕 Rivedere i contenuti del canale Telegram** (il privato ma aperto al pubblico) — cosa pubblicare oltre al daily report per tenerlo vivo e dare valore agli iscritti (anti-squat) | CC + Max | ✅ **SHIPPED+LIVE S120** — sottosistema `telegram_publisher.py` (cron 10min sul Mini): (a) status line post+pin, (b) diario, (c) regime F&G debounced, (d) rassegna stampa 1×/gg. Alert trade (idea 5) **parcheggiato** → **sciolto in T.4 il 09-ago**: Max ha scelto il *digest settimanale* invece dell'alert per-trade. Pin solo su status line. |
| T.2 | **🆕 [BUG] Daily report del canale: mostra i guadagni delle vendite ma non le perdite delle posizioni aperte** — la riga "Today · Realized 🟢 $+X" somma solo i `realized_pnl` delle vendite del giorno (`scripts/send_daily_reports_now.py:48` + formula in `commentary.py`), ignorando la variazione **unrealized** (spesso negativa) delle posizioni aperte → quadro falsamente positivo (es. 01/07: Today +$1.05 mentre BTC −2.1%, BONK −7.3%, ETH −8.9%). Fix: aggiungere il **P&L mark-to-market del giorno** (delta equity vs snapshot di ieri, infra `daily_pnl`). Onestà / one-source-of-truth | CC | ✅ **CODED S120** `f4c2d95` (**solo report privato**, scelta Max; il pubblico è già onesto via frecce+P&L rosso). Riga "Day P&L (Grid): realized+paper" via `get_yesterday_grid_pnl` phantom-invariant. **Effetto al prossimo RESTART bot.** |
| T.3 | **🆕 [BUG — VERIFICATO 2026-07-18] Il report Telegram eredita il fantasma $25 Kraken** (lato bot, NON risolto dal fix sito S119b). **Causa**: `commentary.py:503-514` `get_grid_state` somma `capital_allocation` di **tutte** le righe `managed_by=grid` **senza filtro venue/is_active** (il commento dice pure "Inactive coins still contribute their slice") → con la riga collaudo Kraken `BTC/USD` ($25, `venue=kraken`, `is_active=false`) il `grid_budget = 525` invece di 500, mentre i trade sono filtrati per cycle (Kraken escluso) → il **Total P&L del report è depresso di $25** (baseline gonfiato). `get_grid_state` alimenta **sia il daily report Telegram sia lo snapshot `daily_pnl`** (per questo `daily_pnl.initial_capital` è saltato 500→525 il 17-lug). **Fix** = 1 riga: aggiungere `.eq("venue","binance")` alla query `bot_config` (riga 506), **stesso identico fix già fatto sul sito** (`GRID_BUDGET` filtra venue, commit `f6388b6`). NB: il cycle è già a posto (`get_current_cycle` path globale pinnato `venue=binance`, S119, `db/client.py:45`). **È lato bot → serve restart**; è la STESSA correzione del parked `config/parked/PARKED_daily_pnl_canonical_fase2b.md` (work item A) → **conviene farla insieme a quella, al restart della Fase 2b** (ciclo nuovo azzera pure la deriva dust-reset storica). Se la si vuole prima (report letto ogni giorno), è comunque 1 riga + restart. | CC | ✅ **CODED S120** `0965471` (`get_grid_state` filtra `venue=binance`; sana report Telegram **e** snapshot `daily_pnl`, gemello del fix sito `f6388b6`). **Effetto al prossimo RESTART bot.** |
| T.4 | **🅿️ [IDEA PARCHEGGIATA — Max, 09-ago] Digest settimanale "ultimo trade per bot" su ENTRAMBI i canali** (dev-console + pubblico: sono i due configurati, `TELEGRAM_CHAT_ID` e `TELEGRAM_PUBLIC_CHAT_ID`). **Perché**: è l'unico posto dove si legge *"questo bot è fermo da N giorni"* senza aprire il sito né interrogare il DB. Nasce dal caso BTC/USD **fermo dal 28-lug** (12 giorni), che dopo la soppressione dell'alert idle fuorviante (S126, `1b5846e`) non è più visibile da nessuna parte — vedi anche R.6, dove si è stabilito che la fonte per "da quanto non opera" è la tabella `trades`, non gli snapshot. **Perimetro: solo Kraken / denaro reale.** Paper escluso — *"paper non esiste più"* (Max, 09-ago). ⚠️ Nel costruirlo NON filtrare per `bot_config.is_active`: i testnet risultano spenti eppure hanno operato il 5–6 ago (è il riconciliatore che liquida i residui) — guidare l'elenco da `trades` filtrando `venue='kraken'`. **Come**: dentro `utils/telegram_publisher.py`, stesso stampo di `publish_press_review` (gate su giorno-della-settimana + segnalibro a settimana ISO invece che ora + segnalibro giornaliero) + 1 riga in `run_all`. **Nessun processo né cron nuovo** — il publisher gira già ogni 10 min sul Mini. **Nota di mandato**: sul canale pubblico il messaggio dichiara ogni settimana quante operazioni ha fatto il sistema (oggi direbbe: SOL 3, BTC 0). Scelta di trasparenza già presa scegliendo entrambi i canali. Bozza formato: `SOL/USD 3 operazioni · ultima ieri 18:35` / `BTC/USD 0 operazioni · ultima 28 lug — 12 giorni fa ⚠️` | CC | 🅿️ **PARCHEGGIATA** — idea approvata, non pianificata. Scioglie l'"alert trade (idea 5)" di T.1 |

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
