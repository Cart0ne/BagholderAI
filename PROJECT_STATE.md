# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-09 — sessione 69 (chiusura: BLOCCO 1 B+C completo FIFO contabile via, BLOCCO 2 parziale main_old + grid_runner sync, brief 69a avg-cost trading scritto pending Board approval)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 budget Board confermato)** invariato da fine S68. 4 processi attivi su Mac Mini (orchestrator 96199 + 3 grid_runner) su commit `a8e91a0` (fix 68a, folder ancora `bot/strategies/`). **Dashboard ↔ bot ↔ Binance ora coerenti su avg-cost canonico**: rimosso ogni FIFO replay client-side da grid.html / tf.html / admin.html / dashboard-live.ts / commentary.py / health_check.py (BLOCCO 1 shipped 5 commit S69). FIFO trading logic (Strategy A per-lot) **ancora viva** nel bot: brief 69a pronto per deploy in finestra unica con TRUNCATE+restart. Sito **maintenance** dal S65. Target go-live €100 mainnet: **21-24 maggio 2026** se 69a deploy entro 17-18 maggio.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS, **19 tabelle 0 view post cleanup S68**), Telegram (alerts), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn 3 Grid + brain off via env flags
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config (1627 righe — Phase 2 split candidate)
  exchange.py              Binance ccxt sandbox (S67)
  exchange_orders.py       NEW (S67) — market-order wrapper. fee USDT canonical.
  health_check.py          daily FIFO/holdings/cash integrity (57a)
  db_maintenance.py        daily 04:00 UTC retention 14gg (47c) + Sentinel/Sherpa retention 30/60d
  grid/                    Brain #1 — Grid (post-refactor S68b: era bot/strategies/, NON ancora live su Mac Mini)
    grid_bot.py              public API + dataclasses (~1700 righe; fixed mode è codice morto, da rimuovere)
    fifo_queue.py            FIFO replay + verify_fifo_queue (57a, audit-only)
    state_manager.py         boot-time state restore (S66 avg-cost canonical)
    buy_pipeline.py          buy exec — S67 live route via place_market_buy
    sell_pipeline.py         sell exec — S66 avg-cost; S67 dust prevention; S68a guard avg_cost
    dust_handler.py          dust pop helpers (legacy safety net)
  trend_follower/          Brain #2 — TF (DISABLED via ENABLE_TF=false S67)
  sentinel/                Brain #3 — risk/opportunity score (DISABLED)
  sherpa/                  Brain #4 — parameter writer (DISABLED)
db/, utils/, scripts/, web_astro/  (DB client, telegram notifier, daily reports, sito Astro maintenance)
config/                    settings, briefs (in briefresolved.md/), validation_and_control_system.md,
                           brief_67a / brief_68a (in repo)
audits/                    gitignored — formula_verification_s66.md (S66) + 2026-05-08_pre-reset-s67/ (Mac Mini) +
                           2026-05-09_pre-cleanup-s68/ (folder vuota: Board ha rifiutato backup pre-cleanup)
tests/                     test_accounting_avg_cost.py 8/8 verdi (5 S66 + 2 S67 dust + 1 S68a guard)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. **Mac Mini gira su commit `a8e91a0`** (fix 68a + folder ancora `bot/strategies/`). Refactor 68b (`bot/grid/`) è solo locale + GitHub, non applicato sul Mac Mini.

## 3. In-flight (settimana 2026-05-09, prossima chat)

- **🔴 Brief 69a deploy** (PENDING Board approval data): avg-cost trading + rimozione fixed mode grid_bot.py + DROP COLUMN DB + apply 68b + TRUNCATE+restart. Earliest 2026-05-10, latest 2026-05-15. Brief in `config/brief_69a_avg_cost_trading_truncate_restart.md`.

- **🟡 Brief 67a Step 5** (reconciliation gate nightly): ancora aperto, va shipped post-69a (richiede baseline pulita).

- **🔴 Bug `recalibrate-on-restart`** (CEO 2026-05-07, residuo): trigger buy passano da -0.5% a -1.5% senza apparente ragione. Probabilmente sparisce con 69a (logica riscritta) ma da verificare post-deploy.

- **🟢 Brief Reconciliation Binance** (DB ↔ `fetch_my_trades`): brief separato post go-live €100 mainnet baseline (vedi §6).

## 4. Decisioni recenti

- **2026-05-09 (S69 chiusura) — Budget testnet $500 confermato (Board)**. Niente passaggio a $10K. Allocazioni invariate: BTC $200, SOL $150, BONK $150, capital_per_trade $50/$20/$25. — *why:* Board ha valutato e ha scelto continuità con paper money setup, niente vantaggio tangibile a scalare a $10K solo per allinearsi al wallet Binance preassegnato.
- **2026-05-09 (S69) — BLOCCO 1 shipped: B+C FIFO contabile via**. 3 commit (`6335633` grid+tf, `7231db7` admin+commentary+health_check, `f11b04e` dashboard-live.ts). Tutto frontend (grid.html / tf.html / admin.html / dashboard-live.ts / live-stats.ts) e backend (commentary.py / health_check.py / telegram_notifier.py) ora avg-cost. Pannello "Reconciliation FIFO vs DB" rimosso da admin.html (audit S65 obsoleto post-S66). Health check Check 1+2 (FIFO replay) via, restano 3 check (negative holdings, cash accounting, orphan lots). Test 8/8 verdi. Astro build pulito 10 pagine. Net -555 righe cross-file. — *why:* dashboard mentiva pre-S69 (FIFO replay client-side ricostruiva una formula non più scritta dal bot post-S66 avg-cost). Coerenza totale bot ↔ dashboard ↔ Binance.
- **2026-05-09 (S69) — Portfolio overview ridisegnata 9 card** (commit `6335633`). Layout 3+3+3: Budget · Stato attuale · Total P&L / Cash to reinvest · Deployed · Skim / Unrealized · Fees · Dust. "Stato attuale" sostituisce "Net Worth" e SOTTRAE le fees (chiude anomalia "fees not deducted in paper mode"). Coin status aggiunte stat: Avg buy / Current price / Diff%. Recent trades: aggiunta colonna Fee, "Buy@" usa avg_buy_price snapshot al sell. Parameters: rimossa intera sezione Fixed Grid + select grid_mode. — *why:* spec Board richiesta sessione per sezione (data-by-data design conversation).
- **2026-05-09 (S69) — BLOCCO 2 parziale shipped** (commit `ad048b6`). main_old.py cancellato (era in .gitignore via `*_old*`, gemello inutile). grid_runner.py sync delle 4 colonne fixed-mode (`grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`) rimosso. — *why:* preparazione a 69a, codice morto sicuro. Refactor pesante grid_bot.py (~200 righe fixed mode) + DROP COLUMN DB rinviati a 69a per coerenza con TRUNCATE+restart.
- **2026-05-09 (S69) — Brief 69a scritto** (commit `ee2b0aa`). Deploy in finestra unica: avg-cost trading (Strategy A: trigger su avg_buy_price, sell pool a price, niente più _pct_open_positions queue) + DROP COLUMN DB (5 colonne) + apply 68b + TRUNCATE testnet baseline + restart bot vergine. Stima 10-14h sviluppo + 24h observation = ~3 giornate. — *why:* chiudere debt strutturale FIFO/fixed mode prima di go-live €100 mainnet, in finestra unica per non avere riavvi multipli del bot.
- **2026-05-09 (S68 chiusura) — Cleanup DB Supabase shipped**. DROP `feedback` + `sentinel_logs` + `portfolio` (3 tabelle vuote/legacy). DROP view `v_portfolio_summary` + `v_reserve_totals` (orfane). DELETE 54 row `bot_config WHERE is_active=false` (TF legacy allocations). 22→19 tabelle, 2→0 view. Niente backup (Board: paper money, tabelle vuote o temporanee). — *why:* "complessità solo se valore aggiunto", riconoscimento debt strutturale Board.
- **2026-05-09 (S68) — Pivot Board "trading minimum viable"**. Board ha formulato filosofia: "Trading minimum viable. Ogni complicazione deve dimostrare prima di esistere." Solo Grid attivo. TF/Sentinel/Sherpa stay-but-off (no codice cancellato). 3 monete (BTC + SOL + BONK). Mainnet €100 invariato. Volumi Payhip + sito + narrativa NON toccati. — *why:* Max ha riconosciuto che 67 sessioni hanno accumulato complessità (22 tabelle, 4 brain, 1627 righe in singolo file, 90 notifiche/notte). Il restart riguarda solo il trading subsystem, non l'intero progetto.
- **2026-05-09 (S68) — Brief 68b SHIPPED locale**. `bot/strategies/` → `bot/grid/` (7 file via git mv, history preservata). 23 import statements aggiornati. Replace `'trend_follower'` → `'tf'` (61 occorrenze) e `'manual'` → `'grid'` (24 occorrenze, eccezioni preservate per stop reason Telegram). Test 8/8 verdi. Commit `39e05b7`. **NON applicato sul Mac Mini** (in attesa decisione Board, cosmetico). — *why:* preparazione standardizzazione `managed_by` + namespace coerente.
- **2026-05-09 (S68) — Brief 68a SHIPPED**. `bot/grid/sell_pipeline.py` linea 264 + 451: guard "Strategy A no sell at loss" da `price < lot_buy_price` a `price < bot.state.avg_buy_price`. Reason string + log BLOCKED aggiornati a "avg cost". Test 8/8 verdi (incluso `test_h` nuovo). Commit `a8e91a0`, applicato su Mac Mini. — *why:* doppio standard FIFO (S57a guard) + avg-cost (S66 realized) causava sell in loss strutturali. Evidenza: BONK sell 2026-05-08 22:56 UTC realized −$0.152.
- **2026-05-09 (S68) — Verifica testnet Binance**: wallet ha 446 asset preassegnati + ~$10K USDT (NON $500). Il "$500" è convenzione interna, Binance non lo conosce. History `fetch_my_trades` + `fetch_orders` persistente → reconciliation DB ↔ Binance fattibile. Reset mensile testnet non confermato in 60s, da verificare.
- **2026-05-08 (S67 chiusura) — Brief 67a Step 2-4 SHIPPED** (immutato): dust prevention + ccxt set_sandbox_mode(True) + place_market_buy/sell + fee USDT canonical (CEO opzione A) + reset DB + restart $500 Grid-only.
- **2026-05-08 (S66 chiusura) — Operation Clean Slate Step 0+1 SHIPPED** (immutato): pivot avg-cost canonico in `_execute_sell` e `_execute_percentage_sell`.
- **2026-05-08 (S65) — Opzione 3 dashboard Total P&L only** (immutato, commit `6100caf`).

## 5. Bug noti aperti

- **🟢 [S69 RISOLTO parziale] Pulizia codice fixed mode**: main_old.py cancellato + grid_runner.py sync 4 colonne via. Refactor pesante grid_bot.py (~200 righe) + DROP COLUMN DB → in brief 69a.
- **🟢 [S69 RISOLTO] FIFO replay client-side dashboard**: tutto avg-cost ovunque (grid.html / tf.html / admin.html / dashboard-live.ts / commentary.py / health_check.py / telegram_notifier.py). Pannello "Reconciliation FIFO vs DB" eliminato.
- **🟡 [S68 NEW] Trigger sell in `bot/grid/grid_bot.py:749-752`** valuta per-lot (non avg_cost). Sell-in-loss bloccati a valle dal guard fix S68a. **Brief 69a chiude questo bug** (riscrittura trigger + rimozione _pct_open_positions queue).
- **🟡 [S68 NEW] Strange sell BONK 22:56 in DB v3** (lot fantasma riusato): emerso in audit S69. **Brief 69a chiude per costruzione** (niente più queue, no possibilità di lot fantasma).
- **🟡 [S68 NEW] `grid_runner.py` 1627 righe** di cui 833 in `run_grid_bot()`. Phase 2 split candidato post-go-live.
- **🔴 [S67] `exchange_order_id=null` su sell OP/USDT** (`bot/exchange_orders.py:_normalize_order_response`): non gating, debt cosmetico. Aperto.
- **🟡 [S67] Slippage testnet ~1% sui BONK trade**: Binance testnet con book sottile. Bot non logga `check_price`, solo `fill_price` → impossibile misurare slippage post-hoc. Reason mente con fill_price (BUSINESS_STATE §27).
- **🟡 [S67] Bot trigger buy_pct cambia spontaneamente a restart** (`bot/grid/grid_bot.py` config_reader): probabilmente sparisce con 69a (riscrittura), da verificare post-deploy.
- `bot/grid/grid_bot.py:758` — `# TODO 62a (Phase 2): this loop is the 60c double-call source.` (non gating, S67 dust prevention copre il caso principale)
- `bot/grid/sell_pipeline.py:23` — `# TODO 62a (Phase 2): make _execute_percentage_sell atomic` (race audit↔log_trade)
- `bot/grid/dust_handler.py:17` — `# TODO 62a (Phase 2): emit 'dust_lot_removed' events`
- `bot/trend_follower/allocator.py:43` — `# TODO: move to trend_config in a future session`
- **TF distance filter 12% fisso vs EMA20** (CEO, 2026-05-07): cross-tema Sentinel/Sherpa, S69+
- **🔴 [S63] `speed_of_fall_accelerating` miscalibrato** + **🟡 Risk score binario** + **🔴 Opportunity score morta**: tutti su Sentinel, da ricalibrare quando ricolleghiamo (S69+)
- **🟡 [S63] Grid polling REST 60s perde i picchi BTC sub-minuto**: mitigazione pre-mainnet → BTC interval 60s → 20s
- **🟡 [S63] Supabase REST cap 1000 righe latente in home/dashboard pubblica**: posticipato (sito ancora in maintenance)

## 6. Domande aperte per CEO

- ✅ **[S69 risolto] Data deploy brief 69a**: **entro oggi 2026-05-09** (Board fine giornata).
- ✅ **[S69 risolto] Reset mensile testnet Binance**: confermato dal sito ufficiale Binance Testnet (~1/mese, no preavviso, API keys preservate dal 2020). Non bloccante per il deploy.
- 🟡 **[S69] Reconciliation gate / 67a Step 5**: rimandato. **CEO sta preparando un nuovo brief separato** che probabilmente assorbe/sostituisce 67a Step 5 + Reconciliation Binance.
- **[S69] Reconciliation Binance (DB ↔ `fetch_my_trades`)**: brief separato post go-live €100 mainnet (vedi sopra, in attesa del nuovo brief CEO).
- **Budget testnet $10K vs $500**: Board valuta. Se $10K, scaling `capital_per_trade` $200/$100/$100 + `MAX_CAPITAL`.
- **Reset mensile testnet Binance**: vale verifica formale?
- **Phase 2 split `grid_runner.py`**: confermi parking post-go-live?
- **Health check FIFO drift $0.28** (BONK): riclassificare da "fail" a "audit informativo" (post-S66 expected)?
- **Recalibrate-on-restart investigation** (Apple Note CEO 2026-05-07): da indagare a freddo prossima chat
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): da rivalutare con dati testnet veri
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`)
- **Esposizione pubblica Validation & Control System** rimandata
- **Reaction chart `/admin` poco leggibile in regime calmo** — fix grafico, post-restart Sentinel

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** dal 2026-05-08 21:15 UTC (post-restart S67) + restartato 2026-05-09 09:24 UTC (post-fix 68a). PID orchestrator 96199 + 3 child grid_runner. Brain off.
- **Go/no-go €100 LIVE**: target ~**21-24 maggio 2026** se 69a deploy entro 17-18 maggio. Slip a 24-27 se deploy 19-20.
- **Sequenza S70**: deploy brief 69a (avg-cost trading + DROP COLUMN DB + apply 68b + TRUNCATE+restart) + 24h observation + brief 67a Step 5 reconciliation gate.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Mac Mini su commit `a8e91a0`. MBP+GitHub su `ee2b0aa`. Disallineamento volontario fino a deploy 69a.
- **Replay Sherpa counterfactual** parcheggiato (post-reactivation Sherpa, post go-live €100).
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, avg-cost trading (deploy 69a, 🔲), reconciliation gate nightly (post-69a, 🔲), wallet reconciliation Binance settimanale (post go-live, 🔲).

## 8. Cosa NON è stato fatto e perché

In S69 NON è stato deployato il **brief 69a** (avg-cost trading): scritto e pronto, in attesa decisione Board sulla data deploy. Earliest 2026-05-10, latest 2026-05-15.

NON è stato shipped **brief 67a Step 5 (reconciliation gate nightly)** — sarà parte del deploy 69a o sessione separata post-69a.

NON è stato applicato il **refactor 68b sul Mac Mini**. Sarà parte del deploy 69a (richiede comunque restart bot).

NON è stato fatto il refactor pesante di **fixed mode in `grid_bot.py`** (~200 righe): rimandato a 69a per coerenza con TRUNCATE+restart e DROP COLUMN DB.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt cosmetico tracciato per post-69a.

NON è stato risolto il bug **`recalibrate-on-restart`**. Probabilmente sparisce con 69a (riscrittura logica), da verificare post-deploy.

NON è stato verificato il **reset mensile testnet Binance**. Da fare prima del deploy 69a (per pianificare la finestra).

NON è stato shipped **Phase 2 split `grid_runner.py`**. Parcheggiato post-go-live.

NON sono state ricollegate TF/Sentinel/Sherpa. Coerente con pivot Board "minimum viable, solo Grid".

NON è stato riaperto il **sito pubblico** (home + nav). Decisione CEO S65 ancora valida: aspettiamo numeri certificati post-69a.

NON è stato aggiornato il test `tests/test_verify_fifo_queue.py` (lascio finché `verify_fifo_queue` esiste; sparisce con 69a).

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| 2026-05-07 | 1 | Phase 1 split grid_bot.py | APPROVED | 0 regressioni, 0 risk gates aperti | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-08 | 1 | Operation Clean Slate Step 0d (formula verification) | CRITICAL FINDING SHIPPED FIX | Bias `realized_pnl` +$26.97 (+29%) certificato. Root cause: queue desync per 4 cause concorrenti. Fix Step 1 chiude identità al centesimo. | `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md` (gitignored) |
| 2026-05-08 | 1 | S67 brief 67a Step 2-4 (testnet order placement) | SHIPPED + 4 BUG INTERNI | 6 buy + 1 sell live testnet. 4 bug emersi a caldo: severity 'warning' (CHECK fail), mode='paper' hardcoded, fee in raw native, ccxt sandbox config-key ignorato. Tutti fixati nella stessa sessione. | `report_for_CEO/2026-05-08_s67_fee_usdt_design_decision_report_for_ceo.md` |
| 2026-05-08 | 1 | Pre-reset Supabase backup | COMPLETE | 22 tabelle, 51,943 righe, 22.47 MB JSONL su Mac Mini | `audits/2026-05-08_pre-reset-s67/_manifest.json` (gitignored) |
| 2026-05-09 | 1 | S68a sell-in-loss guard fix | SHIPPED + TEST 8/8 | Doppio standard FIFO+avg-cost risolto. Test_h aggiunto. Bot Mac Mini restartato Grid-only. | `report_for_CEO/2026-05-09_s68_brief_68a_shipped_report_for_ceo.md` |
| 2026-05-09 | 1 | S68b refactor folder + managed_by | SHIPPED LOCAL | bot/strategies/ → bot/grid/, 'trend_follower' → 'tf', 'manual' → 'grid'. NON ancora live su Mac Mini. | commit `39e05b7` |
| 2026-05-09 | 0 | S68 audit Supabase 22 tabelle | COMPLETE + CLEANUP SHIPPED | 5 oggetti morti rimossi (3 tabelle + 2 view) + 54 row bot_config TF legacy. 22→19 tabelle, 2→0 view. | `report_for_CEO/2026-05-09_s68_chiusura_finale_report_for_ceo.md` |
| 2026-05-09 | 1 | S69 BLOCCO 1 B+C: FIFO contabile via dashboard + commentary + health_check | SHIPPED | 5 commit, -555 righe nette cross-file. Tutto frontend + backend contabile su avg-cost canonico. Test 8/8 verdi. Astro build pulito. Pannello Reconciliation FIFO admin via, sostituito da TODO Reconciliation Binance. | commit `6335633`, `7231db7`, `f11b04e` |
| 2026-05-09 | 1 | S69 BLOCCO 2 parziale: main_old.py + grid_runner sync fixed via | SHIPPED | -1 file, -8 righe netto grid_runner.py. Refactor pesante grid_bot.py + DROP COLUMN DB rinviati a 69a. | commit `ad048b6` |
| 2026-05-09 | 1 | S69 BLOCCO 3.1: brief 69a avg-cost trading scritto | PENDING BOARD | 199 righe brief con scope, file:linea, sequenza deploy, test, rollback, decision log. Stima 10-14h sviluppo + 24h observation. | commit `ee2b0aa`, file `config/brief_69a_avg_cost_trading_truncate_restart.md` |
