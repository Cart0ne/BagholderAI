# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-09 — sessione 68 (chiusura: fix sell-in-loss 68a shipped, refactor folder 68b shipped, cleanup DB Supabase eseguito, brainstorming Board pivot a "trading minimum viable")
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 convenzione interna)** post fix 68a. 4 processi attivi su Mac Mini (orchestrator 96199 + 3 grid_runner). 13 trade live testnet totali (12 da S67 + 1 BONK buy nuovo 09:30 UTC oggi). Total P&L stabile ~+$0.10/+$0.30. **Pivot strategico**: Board ha formulato filosofia "trading minimum viable, complessità solo se valore aggiunto". Sito **maintenance** dal S65. Vincolo del momento: prossima chat dedicata a grid.html rebuild + pulizia codice + decisione budget $10K vs $500. Target go-live €100 mainnet: **21-24 maggio 2026**.

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

- **🟡 Apply 68b sul Mac Mini** (decisione Board pending): refactor cosmetico folder + managed_by, richiederà 1 riavvio bot.

- **🟡 grid.html rebuild card-by-card**: 3 anomalie identificate sulla dashboard `/admin/grid.html`: label "fees not deducted in paper mode" obsoleta, formula skim "0.01% of net worth" sbagliata, drift Total P&L $0.11 vs Realized+Unrealized teorico $0.45. Definire dati che Board vuole vedere, eventuale sezione "Reconciliation Binance".

- **🟡 Decisione budget**: $10K (allinea wallet ↔ DB) vs $500 (convenzione interna). Se $10K, aggiornare `MAX_CAPITAL`, `capital_allocation`, `capital_per_trade` (ipotesi $200/$100/$100). Eventuale TRUNCATE + restart post-decisione.

- **🟡 Pulizia codice**: rimozione fixed mode (~500-800 righe + 4 colonne DB inutilizzate), rimozione `main_old.py` gemello.

- **🔴 Bug `recalibrate-on-restart`** (CEO 2026-05-07, residuo): trigger buy passano da -0.5% a -1.5% senza apparente ragione. Debt aperto.

- **Aggiornare `tests/test_pct_sell_fifo.py`** post-pivot avg-cost (S66 debt): assertions sul realized_pnl pre-S66 obsolete. Non gating.

## 4. Decisioni recenti

- **2026-05-09 (S68 chiusura) — Cleanup DB Supabase shipped**. DROP `feedback` + `sentinel_logs` + `portfolio` (3 tabelle vuote/legacy). DROP view `v_portfolio_summary` + `v_reserve_totals` (orfane). DELETE 54 row `bot_config WHERE is_active=false` (TF legacy allocations). 22→19 tabelle, 2→0 view. Niente backup (Board: paper money, tabelle vuote o temporanee). — *why:* "complessità solo se valore aggiunto", riconoscimento debt strutturale Board.
- **2026-05-09 (S68) — Pivot Board "trading minimum viable"**. Board ha formulato filosofia: "Trading minimum viable. Ogni complicazione deve dimostrare prima di esistere." Solo Grid attivo. TF/Sentinel/Sherpa stay-but-off (no codice cancellato). 3 monete (BTC + SOL + BONK). Mainnet €100 invariato. Volumi Payhip + sito + narrativa NON toccati. — *why:* Max ha riconosciuto che 67 sessioni hanno accumulato complessità (22 tabelle, 4 brain, 1627 righe in singolo file, 90 notifiche/notte). Il restart riguarda solo il trading subsystem, non l'intero progetto.
- **2026-05-09 (S68) — Brief 68b SHIPPED locale**. `bot/strategies/` → `bot/grid/` (7 file via git mv, history preservata). 23 import statements aggiornati. Replace `'trend_follower'` → `'tf'` (61 occorrenze) e `'manual'` → `'grid'` (24 occorrenze, eccezioni preservate per stop reason Telegram). Test 8/8 verdi. Commit `39e05b7`. **NON applicato sul Mac Mini** (in attesa decisione Board, cosmetico). — *why:* preparazione standardizzazione `managed_by` + namespace coerente.
- **2026-05-09 (S68) — Brief 68a SHIPPED**. `bot/grid/sell_pipeline.py` linea 264 + 451: guard "Strategy A no sell at loss" da `price < lot_buy_price` a `price < bot.state.avg_buy_price`. Reason string + log BLOCKED aggiornati a "avg cost". Test 8/8 verdi (incluso `test_h` nuovo). Commit `a8e91a0`, applicato su Mac Mini. — *why:* doppio standard FIFO (S57a guard) + avg-cost (S66 realized) causava sell in loss strutturali. Evidenza: BONK sell 2026-05-08 22:56 UTC realized −$0.152.
- **2026-05-09 (S68) — Verifica testnet Binance**: wallet ha 446 asset preassegnati + ~$10K USDT (NON $500). Il "$500" è convenzione interna, Binance non lo conosce. History `fetch_my_trades` + `fetch_orders` persistente → reconciliation DB ↔ Binance fattibile. Reset mensile testnet non confermato in 60s, da verificare.
- **2026-05-08 (S67 chiusura) — Brief 67a Step 2-4 SHIPPED** (immutato): dust prevention + ccxt set_sandbox_mode(True) + place_market_buy/sell + fee USDT canonical (CEO opzione A) + reset DB + restart $500 Grid-only.
- **2026-05-08 (S66 chiusura) — Operation Clean Slate Step 0+1 SHIPPED** (immutato): pivot avg-cost canonico in `_execute_sell` e `_execute_percentage_sell`.
- **2026-05-08 (S65) — Opzione 3 dashboard Total P&L only** (immutato, commit `6100caf`).

## 5. Bug noti aperti

- **🟢 [S68a RISOLTO] Doppio standard FIFO + avg-cost causava sell in loss strutturali** — Fixato in `bot/grid/sell_pipeline.py`: guard ora su `bot.state.avg_buy_price`. Closed.
- **🔴 [S67] `exchange_order_id=null` su sell OP/USDT** (`bot/exchange_orders.py:_normalize_order_response`): non gating, debt cosmetico. Aperto.
- **🟡 [S67] Bot trigger buy_pct cambia spontaneamente a restart** (`bot/grid/grid_bot.py` config_reader): post-restart3 i trigger sono passati da -0.5% e -1.5% a -1.5% per tutti. Da indagare. Cross-tema con Sherpa.
- **🟡 [S67] Slippage testnet ~1% sui BONK trade**: Binance testnet con book sottile. Bot non logga `check_price`, solo `fill_price` → impossibile misurare slippage post-hoc. Reason mente con fill_price (BUSINESS_STATE §27).
- **🟡 [S68 NEW] Trigger sell in `bot/grid/grid_bot.py:749-752`** valuta per-lot (non avg_cost). Brief 68a NON l'ha toccato (vincolo CEO "NON toccare grid_bot.py"). Sell-in-loss bloccati a valle dal guard fix in `sell_pipeline.py`. Coerente, ma il bot fa "tentativi vuoti" loggati.
- **🟡 [S68 NEW] `grid_runner.py` 1627 righe** di cui 833 in `run_grid_bot()`. Phase 2 split candidato post-go-live (BUSINESS_STATE §28).
- **🟡 [S68 NEW] Fixed mode Grid è codice morto**: 0 record DB lo usa. ~500-800 righe rimovibili + 4 colonne DB. Pulizia rimandata a prossima chat.
- **🟡 [S68 NEW] `main_old.py` gemello inutile** in root (visibile e confondente). Pulizia rimandata.
- `bot/grid/grid_bot.py:758` — `# TODO 62a (Phase 2): this loop is the 60c double-call source.` (non gating, S67 dust prevention copre il caso principale)
- `bot/grid/sell_pipeline.py:23` — `# TODO 62a (Phase 2): make _execute_percentage_sell atomic` (race audit↔log_trade)
- `bot/grid/dust_handler.py:17` — `# TODO 62a (Phase 2): emit 'dust_lot_removed' events`
- `bot/trend_follower/allocator.py:43` — `# TODO: move to trend_config in a future session`
- **TF distance filter 12% fisso vs EMA20** (CEO, 2026-05-07): cross-tema Sentinel/Sherpa, S69+
- **🔴 [S63] `speed_of_fall_accelerating` miscalibrato** + **🟡 Risk score binario** + **🔴 Opportunity score morta**: tutti su Sentinel, da ricalibrare quando ricolleghiamo (S69+)
- **🟡 [S63] Grid polling REST 60s perde i picchi BTC sub-minuto**: mitigazione pre-mainnet → BTC interval 60s → 20s
- **🟡 [S63] Supabase REST cap 1000 righe latente in home/dashboard pubblica**: posticipato (sito ancora in maintenance)

## 6. Domande aperte per CEO

- **🆕 [S69] Reconciliation Binance (DB ↔ `fetch_my_trades`)**: brief separato post go-live €100 mainnet. Sostituisce il pannello "Reconciliation FIFO vs DB" rimosso da `/admin` in S69 (era audit S65 ormai obsoleto post-pivot avg-cost S66). Verifica periodica che il nostro DB (`trades` v3) coincida con la verità Binance (order ID/fill price/fee/timestamp). Stima: ~3-4h. Trigger: TRUNCATE+restart bot pulito (BLOCCO 3.2).
- **Apply 68b sul Mac Mini**: ora (riavvio bot) o post nuova chat?
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
- **Go/no-go €100 LIVE**: target ~**21-24 maggio 2026** (slip da 16-20 originario, causa fix 68a + brainstorming Board).
- **Sequenza nuova chat S69**: (1) grid.html rebuild card-by-card, (2) pulizia codice (rimozione fixed mode + main_old + apply 68b), (3) decisione budget + eventuale TRUNCATE + restart, (4) 24h observation baseline.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Mac Mini su commit `a8e91a0`. MBP+GitHub su `39e05b7`. Disallineamento volontario.
- **Replay Sherpa counterfactual** parcheggiato (post-reactivation Sherpa, S70+).
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, reconciliation gate nightly (S69+), wallet reconciliation Binance settimanale (post go-live).

## 8. Cosa NON è stato fatto e perché

In S68 NON è stato shipped **brief 67a Step 5 (reconciliation gate nightly)** — rimandato perché il focus si è spostato su (1) fix bug 68a, (2) refactor 68b, (3) pivot strategico Board, (4) cleanup DB. Il gate è critico per go-live €100, è prerequisito Phase 9 V&C aperto.

NON è stato applicato il **refactor 68b sul Mac Mini**. Decisione Board pending: cosmetico, può aspettare. Mac Mini gira su commit `a8e91a0`.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt cosmetico tracciato per S69.

NON è stato risolto il bug **`recalibrate-on-restart`**. Era già aperto da S63, S67 ne ha vista una nuova istanza, S68 non l'ha indagato per priorità.

NON è stato fatto **backup pre-cleanup DB**. Board: "niente backup, capitale paper, tabelle vuote o dichiarate temporanee".

NON è stato verificato il **reset mensile testnet Binance**. Da fare in S69.

NON sono stati rimossi `main_old.py` né il fixed mode Grid (~500-800 righe). Pulizia rimandata.

NON è stato shipped **Phase 2 split `grid_runner.py`**. Parcheggiato post-go-live (BUSINESS_STATE §28).

NON sono state ricollegate TF/Sentinel/Sherpa. Coerente con pivot Board "minimum viable, solo Grid".

NON è stato riaperto il **sito pubblico** (home + nav). Decisione CEO S65 ancora valida: aspettiamo numeri certificati post-restart pulito.

NON è stato aggiornato `tests/test_pct_sell_fifo.py` legacy (S66 debt confermato).

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
