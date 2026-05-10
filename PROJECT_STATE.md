# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-10 — sessione 70 (chiusura serale: brief 70a sell_pct net-of-fees + sell ladder + post-fill warning shipped, brief 70b Sentinel ricalibrazione + DRY_RUN riacceso, reconciliation Binance Step A live, rename `manual→grid` chiuso open question 19, BONK hotfix sell_pct 2→4 per slippage testnet)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 budget Board) + Sentinel/Sherpa DRY_RUN riaccesi (S70)**. Mac Mini su commit `4324231` (HEAD), restart 2026-05-10 09:51 UTC con `ENABLE_TF=false ENABLE_SENTINEL=true ENABLE_SHERPA=true`. Avg-cost trading completo + nuovo trigger sell con fee buffer (S70 70a) + sell ladder graduale (`_last_sell_price` reference). Hotfix BONK `sell_pct=4%` per assorbire slippage testnet 2.46% (book sottile). Telegram Sentinel/Sherpa **silenti** via env (`SENTINEL_TELEGRAM_ENABLED`/`SHERPA_TELEGRAM_ENABLED` default false). Sito **maintenance** dal S65. Target go-live €100 mainnet: **21-24 maggio** invariato.

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

- **🟡 [S70 NEW] 24-48h observation post-restart**: bot girando su `4324231`. Verificare:
  - sell_pct=4% BONK basta vs slippage (eventuale ulteriore aumento se -ve slippage > 4%)
  - Sentinel ladder granulare scrive risk variabile (non più 20/40)
  - Sherpa proposals coerenti
  - Eventuali warning `slippage_below_avg` in `bot_events_log`
- **🟡 [S70] Reconciliation Step B (admin panel)**: legge `reconciliation_runs` table, mostra status per symbol. Non urgente, post osservazione.
- **🟡 [S70] Reconciliation Step C (cron Mac Mini notturno)**: dopo 2-3 run manuali clean. Output va su `reconciliation_runs` (no Telegram).
- **🟡 [S70] Sherpa rule-aware sell_pct**: in DRY_RUN propone sell_pct=1.5 per BONK (ignorando hotfix 4%). Quando andrà live, rule engine deve preservare buffer slippage per coin.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A (stesso scopo).

## 4. Decisioni recenti

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

- **🟢 [S70 RISOLTO]** Sell-at-loss BONK 08:57 UTC: era slippage testnet 2.46% > sell_pct 2%. Hotfix sell_pct=4%. Buffer parametrico per coin = brief futuro pre-mainnet.
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

- ✅ **[S70 risolto] Brief 70a sell_pct net-of-fees + sell ladder + post-fill warning**: shipped + restart attivo.
- ✅ **[S70 risolto] Brief 70b Sentinel ricalibrazione + DRY_RUN riaccensione**: shipped + restart attivo.
- ✅ **[S70 risolto] Open question 19 rename managed_by**: chiusa.
- ✅ **[S70 risolto] Reset mensile testnet handling**: integrato in reconcile_binance.py (status `WARN_BINANCE_EMPTY` quando Binance returna 0 trades, no panic, in attesa nuovi dati).
- 🟡 **[S70 NEW] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a per pre-mainnet. BONK avrebbe `slippage_buffer=3%`, BTC/SOL=0%. Brief separato.
- 🟡 **[S70 NEW] Sherpa rule-aware sull'hotfix slippage**: prima di SHERPA_MODE=live, rule engine deve sapere che sell_pct=4% di BONK è hotfix da preservare.
- 🟡 **[S70 NEW] Reconciliation Step B (pannello /admin) + Step C (cron notturno)**: post 24-48h observation Step A.
- 🟡 **[S70 NEW] Sentinel TELEGRAM flag** (`SENTINEL_TELEGRAM_ENABLED`/`SHERPA_TELEGRAM_ENABLED`): default off; Max abilita quando vuole.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): da rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up. Connesso a sell_pct net-of-fees.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.
- **Reaction chart `/admin` poco leggibile in regime calmo** — fix grafico, post-restart Sentinel.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** + Sentinel/Sherpa DRY_RUN dal restart S70 (2026-05-10 09:51 UTC). PID orchestrator 2626 + 3 grid_runner + sentinel + sherpa. Brain TF off (`ENABLE_TF=false`). Mac Mini su `4324231`.
- **Go/no-go €100 LIVE**: target ~**21-24 maggio 2026** confermato Board. Slip a 24-27 se osservazione 24-48h scopre regressioni.
- **Sequenza S71+**: 24-48h observation → eventuale brief slippage_buffer parametrico → reconciliation Step B (admin panel) → Step C (cron). Niente nuove feature finché Grid+Sentinel+Sherpa non girano puliti.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Tutti allineati su commit `4324231`.
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, **sell_pct net-of-fees S70 ✅**, **post-fill warning slippage S70 ✅**, **wallet reconciliation Binance S70 ✅** (Step A clean, Step B+C post-osservazione), **Sentinel ricalibrazione S70 ✅**, slippage_buffer parametrico (🔲 brief separato).

## 8. Cosa NON è stato fatto e perché

In S70 NON è stato implementato **slippage_buffer parametrico per coin** (estensione brief 70a): brief separato post osservazione 24-48h, perché serve calibrare valori per coin con dati reali (BONK testnet vs mainnet).

NON è stato implementato **rule-aware Sherpa sull'hotfix slippage**: Sherpa è in DRY_RUN, niente impatto immediato; brief separato pre-SHERPA_MODE=live.

NON è stato implementato **reconciliation Step B (pannello /admin) + Step C (cron)**: dipendono da 2-3 run manuali clean (oggi solo 1 run dry-run). Candidati S71+.

NON è stato risolto il bug **`reason bugiardo`** (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa `reason` del trade resta scritta con dicitura "above avg" anche su fill < avg. Cosmetico, TODO separato.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt cosmetico tracciato post-go-live. Reconciliation S70 Step A gestisce con fallback timestamp.

NON è stato fatto il **Phase 2 split di `grid_runner.py`** (~1591 righe). Brief 62b in config, parcheggiato post-go-live €100.

NON è stato riacceso **TF**. Coerente con pivot Board "minimum viable, solo Grid + Sentinel/Sherpa DRY_RUN".

NON è stato riaperto il **sito pubblico** (home + nav). Decisione CEO S65 ancora valida.

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
| 2026-05-10 | 0 | S70 cleanup brief: 9 brief shipped → briefresolved.md/ | COMPLETE | config/ ridotto a 4 brief parcheggiati + 1 design HTML | commit imminente |
