# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-10 — sessione 70c (chiusura, commit `77d4090` web + `6f653b5` commentary, pushati su `main` + pull Mac Mini OK; orchestrator restart pending decisione Board: sito pubblico riaperto dopo 5 giorni di maintenance. TestnetBanner globale; sweep `paper`→`Binance Testnet` solo su home/dashboard/SiteHeader/Layout (storia in blueprint/diary intatta). Capital at Risk breakdown $500 Grid + $100 TF paused. Reconciliation table pubblica su /dashboard. Card homepage Sentinel/Sherpa con badge TEST MODE + cornice colorata. TF placeholder "dal dottore" SVG inline su /dashboard + link `→ see the doctor` dalla card home, easter egg 3-click sul monitor EKG. Roadmap aggiornata: nuova sezione Phase 13 con 14 achievement S65→S70c. Phase 3 Sentinel da `planned` → `active`. Brief 70c §4 (Net Realized Profit hero) PARCHEGGIATO insieme a fix bug `realized_pnl` gross per-riga → Strada 2 brief separato. Step C reconciliation cron + sito mobile review → S71.
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 budget Board) + Sentinel/Sherpa DRY_RUN riaccesi (S70) + sito pubblico online (S70c)**. Mac Mini su commit `4324231` (HEAD), restart 2026-05-10 09:51 UTC con `ENABLE_TF=false ENABLE_SENTINEL=true ENABLE_SHERPA=true`. Avg-cost trading completo + nuovo trigger sell con fee buffer (S70 70a) + sell ladder graduale (`_last_sell_price` reference). Hotfix BONK `sell_pct=4%` (poi 2.5% via /grid editorial 2026-05-10 pomeriggio) per assorbire slippage testnet 2.46% (book sottile). Telegram Sentinel/Sherpa **silenti** via env (`SENTINEL_TELEGRAM_ENABLED`/`SHERPA_TELEGRAM_ENABLED` default false). Sito **ripristinato S70c** (dopo 5 giorni maintenance) con disclaimer Testnet + Reconciliation table pubblica + TF placeholder dal dottore. Target go-live €100 mainnet: **21-24 maggio** invariato.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS, **20 tabelle** post-S70 con `reconciliation_runs`), Telegram (alerts), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn 3 Grid + Sentinel + Sherpa via env flags (TF off)
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config (1591 righe — Phase 2 split candidate)
  exchange.py              Binance ccxt sandbox (S67)
  exchange_orders.py       market-order wrapper, fee USDT canonical (S67)
  health_check.py          daily health check
  db_maintenance.py        daily 04:00 UTC retention (sentinel 30gg, sherpa 60gg)
  grid/                    Brain #1 — Grid (post brief 70a)
    grid_bot.py              public API + GridState + nuovo `_last_sell_price` ladder + FEE_RATE 0.001 + trigger fee-buffered (Grid only)
    state_manager.py         init_avg_cost_state_from_db (replay anche `_last_sell_price`)
    buy_pipeline.py          buy exec + Strategy A guard "no buy above avg" (S69)
    sell_pipeline.py         sell exec + 68a guard + 70a set/reset `_last_sell_price` + post-fill warning slippage_below_avg
    dust_handler.py          write-off helpers
  sentinel/                Brain #2 — Sentinel ON DRY_RUN (S70)
    score_engine.py          ladder granulare -0.5/-1/-2 + funding intermedi (brief 70b)
    price_monitor.py         _SOF_MIN_DROP_1H_PCT=-0.5 floor su sof_accelerating (brief 70b)
    main.py                  loop 60s + SENTINEL_TELEGRAM_ENABLED env (default false)
  sherpa/                  Brain #3 — Sherpa ON DRY_RUN (S70)
    main.py                  loop 120s + SHERPA_TELEGRAM_ENABLED env (default false)
  trend_follower/          Brain #4 — TF (DISABLED via ENABLE_TF=false)
db/, utils/, scripts/, web_astro/  (DB client, telegram, daily reports, sito Astro maintenance)
scripts/reconcile_binance.py  S70 Step A: reconciliation Binance ↔ DB trades (3 OK su primo run)
config/                    settings, validation_and_control_system.md, brief 62b/65b/DUST/eval_skills (parcheggiati)
audits/                    gitignored — formula_verification_s66 + 2026-05-08_pre-reset-s67/
tests/                     test_accounting_avg_cost.py 15/15 verdi (11 originali + 4 brief 70a: L/M/N/O)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. Telegram alerts: solo Grid trade events; Sentinel+Sherpa silenziati via env (memoria `feedback_no_telegram_alerts`).

## 3. In-flight (settimana 2026-05-10+)

- **🟡 [S70 NEW] 24-48h observation post-restart**: bot girando su `4324231` (orchestrator restart 09:51 UTC). Verificare:
  - sell_pct BONK (4% → 2.5% via /grid pomeriggio S70c) sufficiente vs slippage
  - Sentinel ladder granulare scrive risk variabile (non più 20/40)
  - Sherpa proposals coerenti
  - Eventuali warning `slippage_below_avg` in `bot_events_log`
- **🟢 [S70b SHIPPED] Reconciliation Step B (admin panel)**: pannello live, 3 latest per symbol + trade-by-trade compare collassabile + drift details auto-shown. 26/26 ordini matched, 0 drift.
- **🟢 [S70c SHIPPED] Ripristino sito pubblico**: maintenance chiusa dopo 5 giorni. Nuove pagine pubbliche: home con testnet banner + bot card pill colorate, /dashboard con Reconciliation table pubblica + TF placeholder dal dottore SVG inline. Roadmap aggiornata Phase 13. 10/10 pagine pubbliche compilano 200 OK.
- **🟡 [S70c TODO] Reconciliation Step C (cron Mac Mini notturno)**: deferred. Schema: wrapper `scripts/cron_reconcile.sh` (cd repo + venv + python3.13 reconcile_binance.py --write + log su `$HOME/cron_reconcile.log`), crontab `0 3 * * *` (= 03:00 ITA = 01:00 UTC, prima della retention bot 04:00 UTC). Test manuale wrapper. Verificare TCC Full Disk Access. ~30 min con SSH.
- **🟡 [S70c TODO] Brief separato "P&L netto canonico" (Strada 2)**: ~3-4h. Fix codice `realized_pnl = revenue − cost_basis − fee_usdt` + cambio formula avg_buy_price per usare cost USDT vero (`avg = (Σ cost + Σ fee_USDT_buy) / Σ qty_received`). Backfill cumulato avg da inizio storia per 458+ trade storici. Verifica identità S66-style. Decisione editoriale: cambi numeri retroattivi sono OK, si raccontano nel diary (memoria `feedback_story_is_process_not_numbers`).
- **🟡 [S70c TODO] Sito mobile review**: smoke test desktop 10/10 OK, ma layout reconciliation table + bot cards + TF dottore su mobile non verificato.
- **🟡 [S70 NEW] Sherpa rule-aware sell_pct**: in DRY_RUN propone sell_pct=1.5 per BONK (ignorando hotfix 4%/2.5%). Quando andrà live, rule engine deve preservare buffer slippage per coin.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A (stesso scopo).

## 4. Decisioni recenti

- **2026-05-10 (S70c chiusura, commit `77d4090` + `6f653b5`) — Sito pubblico online + bug realized_pnl gross emerso e parcheggiato + decisione editoriale "story is process, not numbers" + Haiku context fix**. Sito ripristinato dopo 5gg maintenance: `TestnetBanner.astro` (global, sotto SiteHeader), sweep `paper`→`Binance Testnet` mirato su home/dashboard/SiteHeader/Layout (regola Max: stato corrente si aggiorna, storia in blueprint/diary intatta). Capital at Risk breakdown $500 Grid + $100 TF paused. Reconciliation table pubblica su /dashboard popolata da `reconciliation_runs` (3 righe BTC/SOL/BONK con status + claim "Zero discrepancies" dinamico). Card homepage Sentinel/Sherpa: pill TEST MODE colorata (blu/rosso) + cornice card `sentinel-active`/`sherpa-active`; TF: pill ON HOLD ambra + body sostituito con icona 🩺 + link `→ see the doctor`. `BotCardOriginal` rifattorizzato con prop `mode: live | testmode | paused`. Dashboard sezione TF sostituita con `<TfDoctor>` SVG inline (768×720 stage del paziente in osservazione, EKG animato CSS, IV drop, easter egg 3-click su monitor → dialog Dr. CC con messaggio "Rest 12-14 days. Will return smarter."). Roadmap.ts aggiornata Phase 13 con 14 achievement S65→S70c; Phase 3 Sentinel `planned`→`active`. Brief 70c §4 (Net Realized Profit hero) PARCHEGGIATO insieme a D2/D3: emerso bug strutturale `realized_pnl per-trade è gross` (non sottrae fee sell + bias residuo ~0.1% fee buy implicita nell'avg). Fix completo Strada 2 (~3-4h) come brief separato post-S70c: include cambio formula avg_buy_price + backfill cumulato + verifica identità. — *why:* Max esplicito 2026-05-10 sessione: cambiare convenzione contabile retroattivamente non è vincolo Board perché "la storia racconta il processo, non i numeri". Salvato come `feedback_story_is_process_not_numbers` in memoria. Tutta la sequenza brief 70c §4 + D2 + D3 ricondotta a un unico brief Strada 2 separato.
- **2026-05-10 (S70b chiusura) — /admin overhaul completo**. Sezione per sezione: (1) titolo h1 con pattern unico mascot Sentinel + Sherpa fianco a sinistra (coerente con grid.html / tf.html `h1-mascot`); (2) Sentinel 24h chart: linea Opp disegnata sotto come dashed 6px alpha 0.65 (visibile come "alone" tratteggiato verde quando coincide con Risk a 20 base); (3) Sentinel + Sherpa scoring rules tables → `<details>` collassabili native (zero JS); (4) Reaction chart + 3 mini-chart Parameters history → vertical jitter ±3px BTC/SOL/BONK (TradingView pattern); (5) Parameters history rebuild: scala intera 0→MAX (0/1/2/3, 0/1/2/3/4, 0/1/2/3/4/5/6h), separator border-bottom tra mini-chart, asse Y destro con 3 valori live BTC/SOL/BONK colorati impilati con anti-collisione 12px; (6) overlay BTC current price + 24h % in alto a sinistra del 24h chart Sentinel (HTML position:absolute, no canvas text); (7) DB monitor live via RPC `public.get_table_sizes()` (security definer, anon SELECT) — sostituito snapshot hardcoded che drift fino a -90% post-S69 retention; aggiunto `reconciliation_runs` a `tablesToCount` con override su `ts` invece di `created_at`; (8) Sezione Reconciliation Binance ex-TODO ora live: card per-symbol + collassabile "📊 Trade-by-trade compare (latest)" 12 colonne side-by-side Binance vs DB (ts/sym/side/qty Bin/DB/Δ%/px Bin/DB/Δ%/fee Bin/DB/Δ$) + collassabile drift details auto-shown solo se DRIFT esiste. — *why:* /admin era oggettivamente leggibile a metà (linee sovrapposte invisibili, regole 30 righe sempre aperte, DB monitor con dati pre-S70, Reconciliation morta con solo commento HTML). Tutto fatto in iterazione guidata 1-cosa-alla-volta con Max, ~12 commit logici.
- **2026-05-10 (S70b) — Schema additions in `reconciliation_runs`**. Migration `s70b_reconciliation_runs_select_policy` (anon SELECT, mancava → frontend bloccato). Migration `s70b_reconciliation_runs_matched_details` (`ALTER TABLE ADD COLUMN matched_details jsonb`). Lo script `reconcile_binance.py` ora popola `matched_details` con la lista completa Binance↔DB per ogni run (db_id, exchange_order_id, ts_ms, qty/price/fee Binance vs DB, side). Storage stimato +2 MB/anno con cron daily. — *why:* per il pannello "trade-by-trade compare" frontend serve il dato grezzo, prima viveva solo in memoria dello script (perso a fine run quando tutto OK).
- **2026-05-10 (S70b) — Migration RPC `public.get_table_sizes()`** (security definer, search_path '', stable, grant execute anon+authenticated). Sostituisce array hardcoded `tableSizes` in admin.html. Linter lamenta `anon_security_definer_function_executable` WARN → intenzionale (pattern coerente con sentinel_scores INSERT anon, sherpa_proposals INSERT anon). — *why:* hardcoded snapshot drift fino a -90% (bot_state_snapshots 3MB→0.3MB post retention). Live RPC = niente più drift, niente manutenzione manuale.

- **2026-05-10 (S70 sera) — Mascot SVG /tf + /admin completati** (commit `2a10028`) e **tabella scoring rules SENTINEL aggiornata post-70b** (commit `40fdc4c`). 3/4 integrazioni brief 65b chiuse (residua solo homepage Astro fuori scope, sito in maintenance). Tabella admin ora coerente con score_engine.py live: drop/pump granulari + funding intermedi + sof floor 1h≤−0.5%. — *why:* preparazione del pannello /admin per la sessione 71 dedicata (Step B reconciliation + eventuali fix sezioni morte).
- **2026-05-10 (S70 sera) — Restart orchestrator con Sentinel + Sherpa DRY_RUN riaccesi** (commit `4324231`, restart 09:51 UTC). Telegram silente per nuovi brain (env flag default false). TF resta off. Smoke test verde: Sentinel scrive ogni 60s, Sherpa ogni 120s, primo proposal 09:51:50 UTC. — *why:* prerequisito per replay counterfactual + decisione futura SHERPA_MODE→live.
- **2026-05-10 (S70) — Brief 70b shipped: Sentinel ricalibrazione**. Ladder drop/pump granulare (-0.5/-1/-2 + +0.5/+1/+2 con incrementi 5-20), funding intermedi (±0.00005/0.0001/0.0002), floor `_SOF_MIN_DROP_1H_PCT=-0.5` su sof_accelerating. Diagnosi su 2,827 record storici: BTC range ±1% (mai -3%), funding ±0.00007 (mai ±0.0003), sof falsi positivi 30% su rumore. Telegram silent flags aggiunti. — *why:* 2,827 record erano risk=20 sempre (compresso), opp=20 sempre (morta), sof=30% falsi positivi. Ladder vecchia tarata su mainnet, cieca su testnet calmo.
- **2026-05-10 (S70) — Brief 70a shipped: sell_pct net-of-fees + sell ladder + post-fill warning** (commit `eb5f38f`). FEE_RATE 0.00075→0.001. Trigger Grid: `reference × (1+sell_pct/100+FEE)/(1-FEE)` formula uniforme primo+gradini (decisione Max iii). `_last_sell_price` campo nuovo, set on partial sell, reset on full sell-out, replay da DB. Post-fill warning `slippage_below_avg` (severity=warn) loggato in `bot_events_log` quando fill < avg, escludendo TF force-liquidate. Test 15/15 verdi. TF/tf_grid invariato (vincolo). — *why:* sell_pct lordo perdeva 0.2% di fee, sell ladder evita "tutto venduto in 3 tick", post-fill warning rende slippage visibile.
- **2026-05-10 (S70) — BONK hotfix `sell_pct 2→4`** (Max via grid.html 09:14 UTC). Investigazione su sell-at-loss BONK 08:57 UTC ($-0.11): root cause = slippage testnet 2.46% > sell_pct 2% buffer (NON guard, NON managed_by, NON recalibrate). Memoria `project_bonk_testnet_slippage` salvata. — *why:* book sottile testnet vs denso mainnet. Su mainnet 2% basta; testnet richiede buffer extra.
- **2026-05-10 (S70) — Open question 19 chiusa: rename `manual→grid` + `trend_follower→tf` su 4 tabelle DB** (`bot_config`, `trades`, `reserve_ledger`, `daily_pnl`) + ALTER CHECK constraint `bot_config.managed_by` a `('grid','tf','tf_grid')` + 6 callsite frontend (`dashboard-live.ts`, `live-stats.ts`, `tf.html`). — *why:* refactor codice S68b non aveva toccato i record DB; reconciliation Step A falliva perché bot scriveva 'manual' (eredità config) e filtro era 'grid'.
- **2026-05-10 (S70) — Reconciliation Binance Step A shipped** (commit `0f6c9b0` + tabella `reconciliation_runs` con RLS service-role). Script `scripts/reconcile_binance.py` aggrega fill Binance per orderId, match con DB tramite `exchange_order_id` (fallback ts±1s/side/qty±1%), tolleranze qty±0.00001/price±0.5%/fee±$0.01. Statuses: OK/WARN_BINANCE_EMPTY/DRIFT/DRIFT_BINANCE_ORPHAN. Primo run: 24/24 ordini matched, zero drift su tutti e 3 i symbol. — *why:* chiude pre-live gate "Wallet reconciliation Binance" + handling reset mensile testnet (warn vuoto, in attesa dati).
- **2026-05-10 (S70) — 4 SVG mascot pushed** (commit `a3443a6`): grid-bot.svg già referenziato in produzione + sentinel/sherpa/trend-follower per uso futuro. Fix 404 sul sito.
- **2026-05-09 (S69) — Strategy A simmetrico SHIPPED**: buy guard "no buy above avg if holdings>0" specular del 68a sell guard (commit `74a13fa`). IDLE recalibrate guard `current > avg → skip` (commit `84e46ea`). DROP COLUMN `bot_config` × 5. fifo_queue.py via, fixed mode via, cleanup completo ~880 righe.
- **2026-05-09 (S69) — brief s70 FASE 1 + 2 SHIPPED**: avg-cost trading completo, niente più FIFO logic, trigger su state.avg_buy_price.

## 5. Bug noti aperti

- **🔴 [S70c NEW] `realized_pnl` per-trade è gross**: il calcolo `revenue - cost_basis` in [bot/grid/sell_pipeline.py:397](bot/grid/sell_pipeline.py#L397) NON sottrae `fee_usdt` (commento `52a: paper-mode realized_pnl excludes fees` mai aggiornato post-testnet). Conseguenza: ogni riga "Recent trades" delle dashboard mostra P&L gonfiato di ~$0.024 su trade da $24 (~0.1%). Cumulato su 458 sell ≈ $30 overstatement. Bias secondo-ordine: avg_buy_price calcolato con `filled_amount` post-fee (in coin) sottostima ~0.1% del cost basis vero USDT-pagato. Hero pubblico "Total P&L" non affetto (parte da Net Worth Binance vero, già netto). Fix in Strada 2 brief separato (~3-4h). Parcheggiato 2026-05-10 (S70c).
- **🟢 [S70 RISOLTO]** Sell-at-loss BONK 08:57 UTC: era slippage testnet 2.46% > sell_pct 2%. Hotfix sell_pct=4% poi 2.5%. Buffer parametrico per coin = brief futuro pre-mainnet.
- **🟢 [S70 RISOLTO]** Sentinel risk binario 20/40: ladder granulare brief 70b + sof floor.
- **🟢 [S70 RISOLTO]** Open question 19 rename `manual→grid`: 4 tabelle DB + frontend allineati.
- **🟢 [S70 PARZIALE]** Reason bugiardo su slippage (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende slippage visibile in `bot_events_log`. La stringa `reason` del trade resta sbagliata (cosmetico, TODO separato).
- **🔴 [S67]** `exchange_order_id=null` su sell OP/USDT — fallback timestamp gestisce reconciliation, ma debt cosmetico. Aperto.
- **🟡 [S67]** Slippage testnet variabile (osservato 2.46% BONK) — gestito con sell_pct buffer per ora. Brief futuro `sell_pct net-of-fees + slippage_buffer parametrico per coin`.
- **🟡 [S69 NEW]** 2 BONK sells fossili pre-S68a con `buy_trade_id NULL` — restano in DB ma niente più check che li flagga.
- **🟡 [S68 NEW]** `grid_runner.py` 1591 righe (di cui ~830 in `run_grid_bot()`). Phase 2 split (brief `62b`) post go-live.
- **🟡 [S70 NEW]** Sherpa propone abbassare BONK sell_pct 4→1.5 in DRY_RUN (ignora hotfix slippage). Quando SHERPA_MODE=live, rule engine deve preservare buffer per-coin. Tracciato in §6.
- **🟡 [S70 NEW]** **LAST SHOT path bypassa lot_step_size rounding** — BUY BONK 11:52:12 UTC rejected da Binance (`code -2010`, "Order book liquidity is less than LOT_SIZE filter minimum quantity"); retry LAST SHOT a 11:52:33 ha avuto successo. Reconcile DB↔Binance OK 12/12 (rejected non scritto in DB, success regolare). Cosmetico (genera 1 Telegram + warn ORDER_REJECTED), ma pre-mainnet vale arrotondare l'amount a `lot_step_size` anche nel path LAST SHOT per evitare il primo tentativo destinato a fallire.
- **TF distance filter 12% fisso vs EMA20** (CEO 2026-05-07): cross-tema Sentinel/Sherpa, post-go-live.

## 6. Domande aperte per CEO

- ✅ **[S70c risolto] Brief 70c Riapertura sito + reconciliation pubblica + TF dottore**: shipped 2026-05-10. §4 (Net Realized Profit hero) parcheggiato come Strada 2 brief separato.
- 🟡 **[S70c NEW] Brief separato "P&L netto canonico" (Strada 2)**: ~3-4h, post-S70c. Combina §4 brief 70c + fix per-riga realized_pnl + cambio formula avg_buy_price + backfill cumulato + verifica identità. Decisione editoriale già confermata Max: "cambi numeri retroattivi raccontati nel diary". Pre o post go-live €100? Probabile pre-go-live (1500 trade paper, identità auditabile prima del capitale reale).
- ✅ **[S70 risolto] Brief 70a sell_pct net-of-fees + sell ladder + post-fill warning**: shipped + restart attivo.
- ✅ **[S70 risolto] Brief 70b Sentinel ricalibrazione + DRY_RUN riaccensione**: shipped + restart attivo.
- ✅ **[S70 risolto] Open question 19 rename managed_by**: chiusa.
- ✅ **[S70 risolto] Reset mensile testnet handling**: integrato in reconcile_binance.py.
- ✅ **[S70b risolto] Reconciliation Step B (pannello /admin)**: shipped con trade-by-trade compare side-by-side.
- ✅ **[S70b risolto] Reaction chart leggibilità in regime calmo**: vertical jitter ±3px applicato a reaction chart + 3 mini-chart Parameters history. Linee sempre distinguibili anche quando coincidono numericamente.
- 🟡 **[S70c TODO] Reconciliation Step C (cron notturno Mac Mini)**: ~30 min, deferred. Schema in §3.
- 🟡 **[S70c TODO] Ripristino sito pubblico**: brief CEO necessario. Sito in maintenance dal S65. Cross-fertilization con pattern /admin (chart, scoring tables, mascot).
- 🟡 **[S70 NEW] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a per pre-mainnet. BONK avrebbe `slippage_buffer=3%`, BTC/SOL=0%. Brief separato.
- 🟡 **[S70 NEW] Sherpa rule-aware sull'hotfix slippage**: prima di SHERPA_MODE=live, rule engine deve sapere che sell_pct=4% di BONK è hotfix da preservare.
- 🟡 **[S70 NEW] Sentinel TELEGRAM flag** (`SENTINEL_TELEGRAM_ENABLED`/`SHERPA_TELEGRAM_ENABLED`): default off; Max abilita quando vuole.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): da rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up. Connesso a sell_pct net-of-fees.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** + Sentinel/Sherpa DRY_RUN dal restart S70 (2026-05-10 09:51 UTC). PID orchestrator 2626 + 3 grid_runner + sentinel + sherpa. Brain TF off (`ENABLE_TF=false`). Mac Mini su `4324231`.
- **Go/no-go €100 LIVE**: target ~**21-24 maggio 2026** confermato Board. Slip a 24-27 se osservazione 24-48h scopre regressioni.
- **Sequenza S71+**: 24-48h observation → eventuale brief slippage_buffer parametrico → reconciliation Step B (admin panel) → Step C (cron). Niente nuove feature finché Grid+Sentinel+Sherpa non girano puliti.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Tutti allineati su commit `4324231`.
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, **sell_pct net-of-fees S70 ✅**, **post-fill warning slippage S70 ✅**, **wallet reconciliation Binance S70 ✅** (Step A clean, Step B+C post-osservazione), **Sentinel ricalibrazione S70 ✅**, slippage_buffer parametrico (🔲 brief separato).

## 8. Cosa NON è stato fatto e perché

In S70b NON è stato implementato **Reconciliation Step C (cron notturno)**: deferred a S70c. Pre-requisito "2-3 run manuali clean" è soddisfatto a 2 (run 14:48 e 14:58 UTC, entrambi 0 drift su 26 ordini), ma per conservatorismo si aspetta una run #3 organica domani prima di abilitare il cron.

In S70b NON è stato riaperto il **sito pubblico** (home + nav). Richiede brief CEO dedicato, non solo lavoro CC. Cross-fertilization con /admin pattern (chart, scoring tables, mascot) — utile risorsa quando si farà.

In S70 NON è stato implementato **slippage_buffer parametrico per coin** (estensione brief 70a): brief separato post osservazione 24-48h, perché serve calibrare valori per coin con dati reali (BONK testnet vs mainnet).

NON è stato implementato **rule-aware Sherpa sull'hotfix slippage**: Sherpa è in DRY_RUN, niente impatto immediato; brief separato pre-SHERPA_MODE=live.

NON è stato risolto il bug **`reason bugiardo`** (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa `reason` del trade resta scritta con dicitura "above avg" anche su fill < avg. Cosmetico, TODO separato.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt cosmetico tracciato post-go-live. Reconciliation S70 Step A gestisce con fallback timestamp.

NON è stato fatto il **Phase 2 split di `grid_runner.py`** (~1591 righe). Brief 62b in config, parcheggiato post-go-live €100.

NON è stato riacceso **TF**. Coerente con pivot Board "minimum viable, solo Grid + Sentinel/Sherpa DRY_RUN".

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| 2026-05-07 | 1 | Phase 1 split grid_bot.py | APPROVED | 0 regressioni, 0 risk gates aperti | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-08 | 1 | Operation Clean Slate Step 0d (formula verification) | CRITICAL FINDING SHIPPED FIX | Bias `realized_pnl` +$26.97 (+29%) certificato | `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md` |
| 2026-05-08 | 1 | S67 brief 67a Step 2-4 (testnet order placement) | SHIPPED + 4 BUG INTERNI | 6 buy + 1 sell live testnet. 4 bug fixati nella stessa sessione | `report_for_CEO/2026-05-08_s67_fee_usdt_design_decision_report_for_ceo.md` |
| 2026-05-08 | 1 | Pre-reset Supabase backup | COMPLETE | 22 tabelle, 51,943 righe, 22.47 MB JSONL | `audits/2026-05-08_pre-reset-s67/_manifest.json` |
| 2026-05-09 | 1 | S68a sell-in-loss guard fix | SHIPPED + TEST 8/8 | Doppio standard FIFO+avg-cost risolto | `report_for_CEO/2026-05-09_s68_brief_68a_shipped_report_for_ceo.md` |
| 2026-05-09 | 1 | S68b refactor folder + managed_by (codice) | SHIPPED | bot/strategies/ → bot/grid/, 'trend_follower' → 'tf', 'manual' → 'grid' | commit `39e05b7` |
| 2026-05-09 | 0 | S68 audit Supabase 22 tabelle | COMPLETE + CLEANUP SHIPPED | 22→19 tabelle | `report_for_CEO/2026-05-09_s68_chiusura_finale_report_for_ceo.md` |
| 2026-05-09 | 1 | S69 BLOCCO 1 B+C: FIFO contabile via dashboard | SHIPPED | Tutto frontend + commentary + health check su avg-cost | commit `6335633`, `7231db7`, `f11b04e` |
| 2026-05-09 | 1 | S69 brief s70 FASE 1+2: avg-cost trading completo | SHIPPED + TEST 11/11 | ~880 righe via, DROP COLUMN × 5, Strategy A simmetrico, IDLE recalibrate guard | commit `cb21179` |
| 2026-05-10 | 1 | S70 reconciliation Binance Step A | SHIPPED | 24/24 ordini matched primo run, 0 drift, 0 orphan | commit `0f6c9b0` + tabella `reconciliation_runs` |
| 2026-05-10 | 0 | S70 rename `manual→grid`/`trend_follower→tf` (DB + frontend) | SHIPPED | 4 tabelle DB + CHECK constraint + 6 callsite frontend. Open question 19 BUSINESS_STATE chiusa | commit `bb575c0` |
| 2026-05-10 | 1 | S70 hotfix BONK sell_pct 2→4 | SHIPPED | Investigazione: slippage testnet 2.46% > sell_pct 2%. NON guard/managed_by/recalibrate | UPDATE bot_config DB; memoria `project_bonk_testnet_slippage` |
| 2026-05-10 | 1 | S70 brief 70a: sell_pct net-of-fees + sell ladder + post-fill warning | SHIPPED + TEST 15/15 | FEE_RATE 0.001, trigger Grid uniforme con fee buffer, `_last_sell_price` ladder, slippage_below_avg event | commit `eb5f38f` |
| 2026-05-10 | 1 | S70 brief 70b: Sentinel ricalibrazione + DRY_RUN riacceso | SHIPPED | Ladder granulare drop/pump/funding, sof floor -0.5%, Telegram silent flags, Sentinel/Sherpa restart 09:51 UTC | commit `4324231` |
| 2026-05-10 | 0 | S70 cleanup brief: 9 brief shipped → briefresolved.md/ | COMPLETE | config/ ridotto a 4 brief parcheggiati + 1 design HTML | commit `a201120` |
| 2026-05-10 | 0 | S70 cleanup round 2+3: 4 brief/decision S65/S62 + 15 CEO reports → archiviati | COMPLETE | config/ + report_for_CEO/ root puliti | commit `f572b33`, `f2c47d0` |
| 2026-05-10 | 1 | S70 mascot /tf + /admin (residui 65b) + scoring rules tabella admin post-70b | SHIPPED | 3/4 integrazioni 65b complete; tabella coerente con score_engine live | commit `2a10028`, `40fdc4c` |
| 2026-05-10 | 0 | S70b /admin overhaul (8 sezioni rivisitate) | SHIPPED | mascot in titolo, dashed-overlay Opp, collapsibles, jitter ±3px, Parameters scala intera + asse Y dx live, BTC overlay, RPC live DB monitor, Reconciliation Step B con trade-by-trade compare side-by-side | commit S70b chiusura |
| 2026-05-10 | 0 | S70c Site relaunch (dopo 5gg maintenance) | SHIPPED | TestnetBanner global + sweep paper→testnet mirato home/dashboard/SiteHeader/Layout + Capital breakdown $500/$100 + Reconciliation table pubblica + Sentinel/Sherpa TEST MODE colorate + TF placeholder dottore SVG inline + easter egg + roadmap Phase 13 (14 achievement S65→S70c). 10/10 pagine 200 OK | sessione S70c — file in §3 in-flight |
| 2026-05-10 | 1 | S70c bug strutturale `realized_pnl` gross documented | DOCUMENTED + PARCHEGGIATO | `revenue - cost_basis` non sottrae `fee_usdt`; avg_buy_price bias residuo ~0.1% (fee buy implicita). Hero pubblico Total P&L NON affetto (parte da Net Worth Binance). Strada 2 brief separato ~3-4h pre-go-live | PROJECT_STATE §5 + roadmap Phase 9 §6 |
| 2026-05-10 | 0 | S70c Haiku commentary context fix | SHIPPED | system prompt riscritto testnet-aware + TESTNET_RESTART_DATE costante + testnet_day counter + system_state in prompt_data. Post di oggi sostituito su Supabase con testo CEO via MCP UPDATE | commit `6f653b5` + memoria `feedback_story_is_process_not_numbers` |
| 2026-05-10 | 0 | S70c report CEO + brief 70c archived | COMPLETE | report_for_CEO/2026-05-10_s70c_site_relaunch_report_for_ceo.md scritto. config/brief_70c_site_relaunch.md → briefresolved.md/session70c_site_relaunch.md | sessione S70c |
| 2026-05-10 | 0 | S70b 3 migrations Supabase | SHIPPED | `s70b_get_table_sizes_rpc` + `s70b_reconciliation_runs_select_policy` + `s70b_reconciliation_runs_matched_details` | apply_migration MCP |
| 2026-05-10 | 1 | S70b Reconciliation Binance run #2 manuale | OK | 26/26 ordini matched (BTC 9, SOL 5, BONK 12), 0 drift, popolato matched_details con dati Binance↔DB | run 14:58 UTC Mac Mini |
