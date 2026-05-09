# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-09 — sessione 69 (chiusura serale: deploy avg-cost trading completo FASE 1 + FASE 2 in giornata unica, ~880 righe nette via, DROP COLUMN bot_config × 5, buy/sell guard simmetrici Strategy A, IDLE recalibrate guard, polish UI grid.html)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 budget Board)** in **avg-cost trading puro** (post brief s70 FASE 1 + FASE 2 shipped in unica giornata). Mac Mini su commit `cb21179` (HEAD). Nessun più FIFO logic in produzione: trigger sell/buy gating su `state.avg_buy_price`, sell amount = `capital_per_trade / current_price`, Strategy A guard simmetrici (no sell sotto avg + no buy sopra avg se holdings>0). DDL DROP COLUMN bot_config × 5 (`grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`, `reserve_floor_pct`). File `bot/grid/fifo_queue.py` rimosso, codice fixed mode in grid_bot.py via (~250 righe). Sito **maintenance** dal S65. Target go-live €100 mainnet: **21-24 maggio** invariato.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS, **19 tabelle 0 view**), Telegram (alerts), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn 3 Grid + brain off via env flags
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config (1591 righe — Phase 2 split candidate)
  exchange.py              Binance ccxt sandbox (S67)
  exchange_orders.py       market-order wrapper, fee USDT canonical (S67)
  health_check.py          daily health check (negative_holdings + cash_accounting; FIFO checks via S69, orphan_lots via S69)
  db_maintenance.py        daily 04:00 UTC retention 14gg
  grid/                    Brain #1 — Grid (post-refactor S68b)
    grid_bot.py              public API + GridState dataclass (~880 righe, fixed mode via)
    state_manager.py         init_avg_cost_state_from_db (no più FIFO replay, no restore_state v1)
    buy_pipeline.py          buy exec + Strategy A guard "no buy above avg" (S69)
    sell_pipeline.py         sell exec + 68a guard "no sell below avg"
    dust_handler.py          write-off helpers (avg-cost, no più queue pop)
  trend_follower/          Brain #2 — TF (DISABLED via ENABLE_TF=false S67)
  sentinel/                Brain #3 — risk/opportunity score (DISABLED)
  sherpa/                  Brain #4 — parameter writer (DISABLED)
db/, utils/, scripts/, web_astro/  (DB client, telegram notifier, daily reports, sito Astro maintenance)
config/                    settings, validation_and_control_system.md, brief_69a + brief_s70_avg_cost_deploy
audits/                    gitignored — formula_verification_s66.md (S66) + 2026-05-08_pre-reset-s67/ (Mac Mini)
tests/                     test_accounting_avg_cost.py 11/11 verdi (8 originali + test_h 68a + test_i S70F1 + test_j idle_recalibrate_skipped + test_k buy_guard_above_avg)
tests/legacy/              test_pct_sell_fifo + test_verify_fifo_queue + test_session10 + test_multi_token + test_grid_bot (fixed mode legacy)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. **Mac Mini gira su commit `cb21179`** (FASE 1+2 shipped + polish UI).

## 3. In-flight (settimana 2026-05-10+, prossima chat)

- **🟡 [S69 RACCOMANDAZIONE Max] domani relax + minimi indispensabili:**
  - **sell_pct net-of-fees** (calcolo fees nella percentuale): brief separato — vedi memoria `project_sell_pct_net_of_fees`. ~1h sviluppo + 1 nuovo widget dashboard. Da decidere prima del deploy mainnet.
  - **Reset mensile testnet Binance handling**: procedura per quando Binance azzera senza preavviso (memoria `feedback_check_past_sessions` rilevante). Max spiegerà domani.
  - **Check con dati Binance** (DB ↔ `fetch_my_trades`): brief separato post osservazione 24h.
- **🟢 [S69 SHIPPED] 24-48h observation post-deploy avg-cost completo**: bot girando su `cb21179`. Tutti i guards Strategy A simmetrici attivi. Telegram alerts attive.
- **🟡 [S67 residuo] Brief 67a Step 5** (reconciliation gate nightly): post osservazione 24-48h con baseline pulito.

## 4. Decisioni recenti

- **2026-05-09 (S69 sera) — Strategy A simmetrico SHIPPED**: aggiunto guard "no buy above avg if holdings>0" (commit `74a13fa`) come specular del 68a "no sell below avg". Inizialmente deferred a favore della sola opzione #1 (idle_recalibrate_guard), poi Max ha deciso di shippare anche questo per chiudere completamente il loop "media in salita". Solo manual bots (managed_by="grid"); TF/tf_grid bypassano. Prima entrata libera. Test_k coprire 4 scenari. — *why:* coerenza Strategy A, niente più cost basis gonfiato in trend up persistenti.
- **2026-05-09 (S69 sera) — IDLE recalibrate guard SHIPPED**: skip recalibrate se current_price > avg_buy_price (commit `84e46ea`). Già scattato in produzione su SOL post-restart (21.7h idle, current $92.81 > avg $92.45 → reference invariato). — *why:* analisi dei 4 scenari RECALIBRATE post-S70 deploy ha rivelato che lo Scenario 4 (lateral-up market) avrebbe causato mediamento in salita; la #1 lo blocca alla radice.
- **2026-05-09 (S69 sera) — DROP COLUMN bot_config × 5 SHIPPED**: `grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`, `reserve_floor_pct` tutti DROP. DDL eseguito tramite Supabase MCP. 4 colonne prima (commit `aa4a064`), `grid_mode` poi (commit `5b106dc`). — *why:* chiusura debt schema fixed mode + coerenza con cleanup codice grid_bot ~250 righe.
- **2026-05-09 (S69 pomeriggio/sera) — Cleanup completo fixed mode SHIPPED**: 250+ righe via da grid_bot.py, buy_pipeline.py, sell_pipeline.py, state_manager.py, grid_runner.py. Rimosso GridLevel dataclass, lower_bound/upper_bound/levels da GridState, num_levels/range_percent/grid_mode da __init__, _create_levels logic, branch `if grid_mode == "fixed"` ovunque, wrapper _execute_buy/_execute_sell/_activate_*/restore_state_from_db. 3 test legacy (test_session10, test_multi_token, test_grid_bot) spostati in tests/legacy/. — *why:* avg-cost trading è l'unico modo runtime, fixed mode codice morto pesante e fonte potenziale di bug. Coerenza totale.
- **2026-05-09 (S69 pomeriggio) — Rimozione `bot/grid/fifo_queue.py` SHIPPED**: -173 righe. File già non importato dopo S70 FASE 1 cleanup wrapper (commit `2763705`); rimozione fisica del file in commit `ce58554`.
- **2026-05-09 (S69 pomeriggio) — Rewrite state_manager.py SHIPPED**: `init_percentage_state_from_db` → `init_avg_cost_state_from_db` (commit `ecb7503`). Legge holdings + avg_buy_price + realized_pnl + _pct_last_buy_price + _last_trade_time da `trades` v3 senza più FIFO queue replay. -50% righe della funzione.
- **2026-05-09 (S69 pomeriggio) — Rimozione attributo `_pct_open_positions` SHIPPED**: tutti i callsite (grid_bot, buy_pipeline, sell_pipeline, dust_handler, grid_runner, snapshot_writer) puliti. dust_handler.py riscritto interamente per fare write-off su `state.holdings` invece che pop dalla queue (commit `3bac9ba`). -43 righe nette.
- **2026-05-09 (S69 mattina/inizio) — brief s70 FASE 1 SHIPPED**: avg-cost trading core (commit `277f2f9`). Trigger sell su `state.avg_buy_price` (singolo decisione), sell amount = `capital_per_trade / current_price`, force-liquidate path (TF override) usa `state.holdings`. Rimosso self-heal, verify_fifo_queue, multi-sell loop, init_percentage post-trade callsite. Reason strings su "avg cost" (non lot_buy_price). Test 9/9 verdi. Deploy live su Mac Mini con git pull pre-S69 BLOCCO 1 (no DELETE Supabase, decisione Max sera).
- **2026-05-09 (S69 sera) — Polish UI grid.html SHIPPED** (commit `cb21179`): allineamento input config field via flex+align-items:end, restructure coin-card in 4 sezioni semantiche (Price · Cash flow · Activity · Triggers), aggiunto widget "Next sell if ↑" gemello del Next buy if ↓, font ridotti per non far esplodere altezza, sostituito 🎒 con `<img src="grid-bot.svg">` (mascot SVG vero, height 1.6em + drop-shadow verde).
- **2026-05-09 (S69) — sell_pct net-of-fees DEFERRED**: proposta Max di garantire sell_pct% NETTO post-fee (round-trip 2×FEE_RATE = 0.15%), con calcolo `sell_trigger = avg × (1 + sell_pct/100 + FEE) / (1 − FEE)`. Memoria `project_sell_pct_net_of_fees` salvata. Da implementare prima del go-live mainnet con parametrizzazione FEE_RATE (BNB discount).
- **2026-05-09 (S69) — Budget testnet $500 confermato** (Board): invariato dal S68. Allocazioni BTC $200, SOL $150, BONK $150, capital_per_trade variabile.

## 5. Bug noti aperti

- **🟢 [S69 RISOLTO]** FIFO trading logic + queue replay (state_manager + sell_pipeline + grid_bot) — sostituito da avg-cost trading puro.
- **🟢 [S69 RISOLTO]** Codice fixed mode in `grid_bot.py` (~250 righe) — via.
- **🟢 [S69 RISOLTO]** DROP COLUMN bot_config × 5 — schema pulito.
- **🟢 [S69 RISOLTO]** `_pct_open_positions` attribute + dust_handler pop paths — write-off semplice.
- **🟢 [S69 RISOLTO]** File `fifo_queue.py` — via.
- **🟢 [S69 RISOLTO]** check_orphan_lots health check — obsoleto post-avg-cost (i 2 BONK fossili pre-S68a 2026-05-08 21:44/22:56 restano nel DB come record storico).
- **🟢 [S69 RISOLTO]** IDLE recalibrate "media in salita" loop (Scenario 4) — guard implementato.
- **🟢 [S69 RISOLTO]** Strategy A asimmetrica (sell guard 68a senza buy gemello) — buy guard simmetrico shipped.
- **🔴 [S67]** `exchange_order_id=null` su sell OP/USDT (`bot/exchange_orders.py:_normalize_order_response`) — non gating, debt cosmetico. Aperto.
- **🟡 [S67]** Slippage testnet ~1% su BONK — Binance testnet con book sottile. Bot non logga `check_price`, solo `fill_price` → impossibile misurare slippage post-hoc. Reason mente con fill_price.
- **🟡 [S67]** Bot trigger buy_pct cambia spontaneamente a restart (`bot/grid/grid_bot.py` config_reader) — probabilmente sparisce con S69 (logica riscritta), da verificare nelle prossime 24-48h.
- **🟡 [S69 NEW]** 2 BONK sells fossili pre-S68a con `buy_trade_id NULL` — restano in DB ma niente più check che li flagga.
- **🟡 [S68 NEW]** `grid_runner.py` 1591 righe (di cui ~830 in `run_grid_bot()`). Phase 2 split post-go-live.
- **TF distance filter 12% fisso vs EMA20** (CEO 2026-05-07): cross-tema Sentinel/Sherpa, post-go-live.
- **🔴 [S63]** `speed_of_fall_accelerating` miscalibrato + **🟡 Risk score binario** + **🔴 Opportunity score morta**: Sentinel calibration, post-go-live.
- **🟡 [S63]** Grid polling REST 60s perde i picchi BTC sub-minuto: mitigazione pre-mainnet → BTC interval 60s → 20s.

## 6. Domande aperte per CEO

- ✅ **[S69 risolto] Brief s70 FASE 1 + FASE 2 deploy**: completato in giornata.
- ✅ **[S69 risolto] DROP COLUMN bot_config × 5**: shipped.
- ✅ **[S69 risolto] Strategy A simmetrico (buy guard)**: shipped.
- 🟡 **[S69 NEW] sell_pct net-of-fees**: brief separato post-osservazione, prima del deploy mainnet.
- 🟡 **[S69 NEW] Reset mensile testnet Binance**: procedura per detection automatica + recovery (Max spiegherà a freddo).
- 🟡 **[S69 NEW] Reconciliation Binance** (DB ↔ `fetch_my_trades`): brief separato post osservazione 24-48h.
- **[S65] Health check FIFO drift $0.28** (BONK): SUPERATO post-S69 (Check FIFO via).
- **Recalibrate-on-restart investigation** (CEO 2026-05-07): probabilmente RISOLTO con la riscrittura S70 FASE 1, da verificare in 24-48h.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): da rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up. **Connesso a sell_pct net-of-fees**.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.
- **Reaction chart `/admin` poco leggibile in regime calmo** — fix grafico, post-restart Sentinel.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** dal restart S69 sera (2026-05-09 ~18:54 UTC) post-cleanup completo. PID orchestrator 97672 + 3 grid_runner. Brain off (ENABLE_TF/SENTINEL/SHERPA=false). Mac Mini su `cb21179`.
- **Go/no-go €100 LIVE**: target ~**21-24 maggio 2026** confermato Board. Slip a 24-27 se osservazione 24-48h scopre regressioni.
- **Sequenza S70+**: minimi indispensabili (sell_pct net-of-fees + reset testnet handling + reconciliation Binance) + 24-48h observation + reconciliation gate nightly. Niente nuove feature finché Grid non gira pulito.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Tutti allineati su commit `cb21179`.
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, **avg-cost trading completo S69 ✅**, **Strategy A simmetrico S69 ✅**, **IDLE recalibrate guard S69 ✅**, reconciliation gate nightly (post-S69, 🔲), wallet reconciliation Binance settimanale (post go-live, 🔲).

## 8. Cosa NON è stato fatto e perché

In S69 NON è stato shipped **brief 67a Step 5 (reconciliation gate nightly)** — richiede baseline pulito post-deploy + 24-48h observation. Candidato S70.

NON è stato implementato **sell_pct net-of-fees** (calcolo fee nella percentuale): proposta Max parcheggiata nella memoria `project_sell_pct_net_of_fees`. Dipende da decisione semantica (cambia significato di sell_pct lordo→netto) e da parametrizzazione FEE_RATE per BNB-discount future-proofing.

NON è stata implementata la **procedura reset mensile testnet Binance** — Max ha indicato la spiegherà a freddo prossima sessione.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt cosmetico tracciato post-go-live.

NON è stato fatto il **Phase 2 split di `grid_runner.py`** (~1591 righe, di cui 830 in `run_grid_bot()`). Parcheggiato post-go-live €100.

NON sono state ricollegate **TF/Sentinel/Sherpa**. Coerente con pivot Board "minimum viable, solo Grid".

NON è stato riaperto il **sito pubblico** (home + nav). Decisione CEO S65 ancora valida: aspettiamo numeri certificati post-osservazione.

NON è stato eseguito **DELETE Supabase baseline** pre-restart (Max sera 2026-05-09 "non fare DELETE"). Bot è ripartito sopra DB esistente con i 2 BONK fossili pre-S68a ancora dentro: niente regressione, solo record storico.

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| 2026-05-07 | 1 | Phase 1 split grid_bot.py | APPROVED | 0 regressioni, 0 risk gates aperti | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-08 | 1 | Operation Clean Slate Step 0d (formula verification) | CRITICAL FINDING SHIPPED FIX | Bias `realized_pnl` +$26.97 (+29%) certificato. Fix Step 1 chiude identità al centesimo. | `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md` |
| 2026-05-08 | 1 | S67 brief 67a Step 2-4 (testnet order placement) | SHIPPED + 4 BUG INTERNI | 6 buy + 1 sell live testnet. 4 bug fixati nella stessa sessione. | `report_for_CEO/2026-05-08_s67_fee_usdt_design_decision_report_for_ceo.md` |
| 2026-05-08 | 1 | Pre-reset Supabase backup | COMPLETE | 22 tabelle, 51,943 righe, 22.47 MB JSONL su Mac Mini | `audits/2026-05-08_pre-reset-s67/_manifest.json` |
| 2026-05-09 | 1 | S68a sell-in-loss guard fix | SHIPPED + TEST 8/8 | Doppio standard FIFO+avg-cost risolto. Test_h aggiunto. | `report_for_CEO/2026-05-09_s68_brief_68a_shipped_report_for_ceo.md` |
| 2026-05-09 | 1 | S68b refactor folder + managed_by | SHIPPED | bot/strategies/ → bot/grid/, 'trend_follower' → 'tf', 'manual' → 'grid'. | commit `39e05b7` |
| 2026-05-09 | 0 | S68 audit Supabase 22 tabelle | COMPLETE + CLEANUP SHIPPED | 5 oggetti morti rimossi + 54 row bot_config TF legacy. 22→19 tabelle. | `report_for_CEO/2026-05-09_s68_chiusura_finale_report_for_ceo.md` |
| 2026-05-09 | 1 | S69 BLOCCO 1 B+C: FIFO contabile via dashboard | SHIPPED | Tutto frontend + backend contabile su avg-cost canonico. Test 8/8 verdi. | commit `6335633`, `7231db7`, `f11b04e` |
| 2026-05-09 | 1 | S69 brief s70 FASE 1: avg-cost trading core | SHIPPED + TEST 9/9 | Trigger sell su avg_buy_price + singolo sell capital_per_trade/price. Niente più FIFO queue nel hot path. | commit `277f2f9` |
| 2026-05-09 | 1 | S69 brief s70 FASE 2: cleanup completo | SHIPPED + TEST 11/11 | 5 commit + DDL DROP COLUMN × 5. ~880 righe nette via. Strategy A simmetrico (buy + sell guard). IDLE recalibrate guard. fifo_queue.py via, fixed mode via, _pct_open_positions via, state_manager rewrite, dust_handler riscritto. | commit `84e46ea`, `2763705`, `f9cceaa`, `aa4a064`, `74a13fa`, `3bac9ba`, `ecb7503`, `ce58554`, `5b106dc` |
| 2026-05-09 | 1 | S69 polish UI grid.html | SHIPPED | Config field alignment + coin-card 4 sezioni semantiche + Next sell if ↑ widget + grid-bot SVG mascot al posto di emoji. | commit `cb21179` |
