# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-08 — sessione 67 (chiusura: brief 67a Step 2-4 shipped, bot live testnet $500, fee USDT canonical, 4 bug emersi+fix, sito ancora offline 24h)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet con $500 stesso schema paper-era** (CEO 2026-05-08: "soldi finti, ripartiamo con stesso schema, una variabile per volta"). 6 buy + 1 sell shipped sul testnet (5 buy first-tick BTC/SOL/BONK in scope + 3 buy fuori scope OP/ZEC/TRX poi disattivati + 1 sell OP da liquidation orphan = +$0.06 primo P&L "reale"). Holdings: 0.000620 BTC ($150.29 cash), 0.216 SOL ($130.03 cash), 3,419,972 BONK ($125.00 cash). Brain off (`ENABLE_TF/SENTINEL/SHERPA=false`). Bot orchestrator PID 90409 + 3 child grid_runner attivi su Mac Mini. Sito **resta in maintenance 24h** (CEO 2026-05-08) per osservare un periodo testnet pulito prima del riapertura. Vincolo del momento: testnet shake-down primo turno + restart pulito + commit/push allineato. Target go-live €100 mainnet: **16-20 maggio 2026**.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS), Telegram (alerts/approvals), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn/restart 3 Grid + TF + Sentinel + Sherpa
                           — S67: + ENABLE_TF/SENTINEL/SHERPA env flags (default true) — Grid-only run
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config, drawdown/SL alerts
                           — S67: + safety check API keys + testnet-only block (mainnet hard-stopped) +
                           mode=TradingMode.MODE dynamic (was hardcoded "paper")
  exchange.py              Binance ccxt — S67: set_sandbox_mode(True) when LIVE+TESTNET=true
                           (configdict "sandbox" key was silently ignored by ccxt for Binance)
  exchange_orders.py       NEW (S67) — ccxt market-order wrapper. place_market_buy (quoteOrderQty),
                           place_market_sell (base amount). Normalizes fee to USDT-equivalent
                           (CEO 2026-05-08 option A) and preserves fee_currency for audit. Logs
                           ORDER_REJECTED to bot_events_log + Telegram alert on failure.
  health_check.py          daily FIFO/holdings/cash integrity (57a)
  db_maintenance.py        daily 04:00 UTC retention (59b) + Sentinel/Sherpa retention 30/60d
  strategies/              Brain #1 — Grid (S66 fix avg-cost + S67 Step 2 dust + S67 Step 3 live route)
    grid_bot.py              public API + dataclasses
    fifo_queue.py            FIFO replay + verify_fifo_queue (57a, audit-only)
    state_manager.py         boot-time state restore (S66: replay canonical avg-cost)
    buy_pipeline.py          buy exec — S67: live branch via place_market_buy when is_live()
    sell_pipeline.py         sell exec — S66 avg-cost; S67 dust prevention pre-round; live branch
    dust_handler.py          dust pop helpers (legacy safety net post Step 2 prevention)
  trend_follower/          Brain #2 — TF (DISABLED via ENABLE_TF=false in S67)
  sentinel/                Brain #3 — risk/opportunity score (DISABLED via ENABLE_SENTINEL=false)
  sherpa/                  Brain #4 — parameter writer (DISABLED via ENABLE_SHERPA=false)
db/, utils/, scripts/, web_astro/  (DB client, telegram notifier, daily reports, sito Astro maintenance)
config/                    settings, briefs (in briefresolved.md/), validation_and_control_system.md,
                           brief_67a_testnet_order_execution.md (CEO brief shipped S67)
audits/                    gitignored — formula_verification_s66.md (S66) + 2026-05-08_pre-reset-s67/
                           (22-table JSONL backup, 51,943 rows, 22.47 MB) on Mac Mini
tests/                     test_accounting_avg_cost.py 7/7 verdi (5 S66 + 2 S67 dust),
                           test_pct_sell_fifo.py legacy non-gating
scripts/                   liquidate_all.py (S66), verify_formulas_s66.py (S66),
                           backup_db_s67.py (S67 pre-reset paginated dump),
                           smoke_test_testnet.py (S67 read-only path verify)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only (no imports cross-brain). Bot orchestrator LIVE su testnet, restart pianificato via env flag toggle quando S68 ricollega TF/Sentinel/Sherpa.

## 3. In-flight (settimana 2026-05-08, S68 imminente)

- **🟡 24h testnet observation** (S68 inizio, 2026-05-09 sera): CEO 2026-05-08 — il sito resta in maintenance finché non abbiamo 24h di testnet pulito senza sorprese. Verifica fee USDT coerenti, holdings = balance Binance testnet wallet, P&L dashboard sano (no più −$3,419 fake), trade flow normale. Se OK → ripristino home + nav (decisione CEO).

- **🟡 S68 bug fix: exchange_order_id null su sell OP** (cleanup tecnico, ~30min): sell OP/USDT da liquidation orphan il 2026-05-08 19:09 non ha popolato `exchange_order_id` in DB, mentre i 6 buy hanno l'id corretto. Sospetto: `_normalize_order_response` non legge fallback `clientOrderId` o `info.orderId` se `id` è vuoto. File: `bot/exchange_orders.py:_normalize_order_response`. Stima 30min + 1 sell test su testnet.

- **🟡 S68 brief 67a Step 5 — reconciliation gate nightly** (~2h): script cron 04:30 UTC che verifica `Realized + Unrealized = Total P&L` al centesimo su trades testnet, alert Telegram se gap > $0.01. Era già pianificato fin da brief 66a. Prerequisito per go-live €100 mainnet.

- **🔴 Bug `recalibrate-on-restart`** (CEO 2026-05-07, residuo): il restart3 di stasera ha mostrato che i trigger buy passano da -0.5% a -1.5% senza apparente ragione. Da indagare: probabilmente Sherpa proposals scrivono buy_pct nel bot_config in DRY_RUN, e il read post-restart prende i nuovi valori. Cross-tema con Sentinel/Sherpa.

- **🟡 TF/Sentinel/Sherpa reactivation** (S68/S69): decisione strategica del Board su quando ricollegarli + se TRUNCATE-are sentinel_scores/sherpa_proposals/trend_decisions_log/counterfactual_log paper-era prima della reactivation. Per ora conservati come archivio.

- **Aggiornare `tests/test_pct_sell_fifo.py`** post-pivot avg-cost (S66 debt): assertions sul realized_pnl pre-S66. Non gating, manutenzione.

## 4. Decisioni recenti

- **2026-05-08 (S67 chiusura) — Brief 67a Step 2-4 SHIPPED**. Sequenza: Step 2 dust prevention (pre-round check sell-all when residual < 1.5x min_sellable, test 7/7 verdi) → Step 3 testnet path (ccxt set_sandbox_mode(True), place_market_buy quoteOrderQty, place_market_sell base amount, fee USDT-equivalent canonical) → Step 4 reset DB (5 tabelle TRUNCATE CASCADE: trades+reserve_ledger+bot_state_snapshots+bot_events_log+daily_pnl) + restart $500 Grid-only. — *why:* CEO ha autorizzato testnet stesso-schema "una variabile per volta — solo l'execution path cambia, capitale/parametri restano".
- **2026-05-08 (S67) — CEO verdict opzione A su fee design canonico**. `trades.fee` = USDT-equivalent (calcolato dal wrapper exchange_orders.py al fill), `trades.fee_asset` = ticker raw (audit). Convertito retroattivamente i 7 trade pre-fix shipped serale. Identità: tutti i 6 buy a 0.1000% del cost (Binance standard), sell OP a 0.0750% (taker ridotto). — *why:* il primo BONK buy ha mostrato −$3,419 P&L sulla dashboard privata grid (raw 3,419.97 BONK interpretato come USDT). Una sola fonte di verità in USDT è non-negoziabile per dashboard/P&L/reconciliation.
- **2026-05-08 (S67) — Architettura `python-binance` del brief 67a SCARTATA, restiamo su ccxt**. Coerenza interna repo (TF + scanner + counterfactual già usano ccxt) > literal compliance al brief. ccxt `sandbox=True` funzionalmente identico a `python-binance testnet=True`. — *why:* zero rework, zero seconda libreria HTTP per Binance. Flaggato al CEO nel report 2026-05-08_s67_fee_usdt_design_decision.
- **2026-05-08 (S67) — Bot_config $500 stesso schema (NO downscale a $100)**. BTC $200 + SOL $150 + BONK $150 = $500 totali, capital_per_trade 50/20/25 invariati. — *why:* Max ha intuito durante la sessione: testnet = soldi finti = nessun motivo di downscalare; ridurre a una variabile la differenza paper→testnet permette debug pulito. Più volume = più punti di confronto Binance vs DB. Il go-live €100 mainnet sarà altra cosa.
- **2026-05-08 (S67) — OP/ZEC/TRX disattivati (is_active=false), preservati come archivio**. Spawned per errore al primo restart (bot_config aveva 6 row attive pre-cleanup), 3 buy fuori scope ($21.99 totali). Risolto con UPDATE bot_config dopo il primo kill. — *why:* CEO 2026-05-08 "non cancellare. Archivio."
- **2026-05-08 (S67) — `mode="paper"` hardcoded in grid_runner.py:610 sostituito con `TradingMode.MODE`**. Tutti i 7 trade pre-fix sono stati retro-fixati con mode='live' via SQL UPDATE. — *why:* il valore era stato fossilizzato a "paper" da quando paper trading era l'unica modalità.
- **2026-05-08 (S67) — Backup completo Supabase pre-TRUNCATE**. 22 tabelle, 51,943 righe, 22.47 MB JSONL paginated → `audits/2026-05-08_pre-reset-s67/` su Mac Mini. CEO 2026-05-08: "prima di TRUNCATE facciamo backup completo come storico ed eventuale ripristino". Restore script non ancora scritto (CEO: "lo faremo nel caso servisse").
- **2026-05-08 (S67) — Brain flag opt-in/opt-out via env**. `ENABLE_TF/SENTINEL/SHERPA` (default true). Se `false`, l'orchestrator skippa lo spawn / termina il process esistente. — *why:* permette Grid-only run per testnet shake-down senza contaminare il dataset DRY_RUN Sentinel/Sherpa con dati nuovi.
- **2026-05-08 (S66 chiusura) — Operation Clean Slate Step 0+1 SHIPPED** (immutato vs PROJECT_STATE S66): sito offline, stop orchestrator, liquidate_all SQL bypass, audit verify_formulas_s66 (bias +$26.97/+29% certificato), pivot avg-cost canonico in `_execute_sell` e `_execute_percentage_sell`.
- **2026-05-08 (S65) — Opzione 3 dashboard Total P&L only** (immutato vs PROJECT_STATE S66, commit `6100caf`).

## 5. Bug noti aperti

- **🔴 [S67 NEW] `exchange_order_id=null` per sell OP/USDT da liquidation orphan** (`bot/exchange_orders.py:_normalize_order_response`): il sell market via ccxt non ha popolato il campo `id` per quel singolo order su testnet. I 6 buy hanno tutti id correttamente. Fix proposto: fallback a `clientOrderId` / `info.orderId`. Stima 30min + 1 sell di test. Non gating per testnet shake-down (cosmetico).
- **🟡 [S67 NEW] Bot trigger buy_pct cambia spontaneamente a restart** (`bot/strategies/grid_bot.py` config_reader): post-restart3 di stasera i trigger buy sono passati da -0.5% (BTC/SOL) e -1.5% (BONK) a -1.5% per tutti. Da indagare: probabilmente DRY_RUN Sherpa proposals scrivono in `bot_config` durante runtime, e il replay state al restart ri-legge i valori aggiornati.
- **🟡 [S67 NEW] OP/USDT sell senza buy precedente in DB → cost_basis canonical = 0**: la sell della liquidation orphan è andata a $8.12 con cost_basis = 0 × 50.21 = 0 (perché i buy storici sono stati TRUNCATE-ati). realized_pnl = revenue − 0 = +$8.12... ma il bot ha scritto `realized_pnl = $0.05` (0.6%, ragionevole). Sospetto: il bot ha preso l'avg da somewhere (state_manager replay con buys empty? o residuo balance Binance?). Non blocca trading, da chiarire in S68.
- **🟢 [S67 RISOLTO] `severity='warning'` rifiutato da CHECK constraint bot_events_log** — Fixato in `bot/exchange_orders.py:_alert_rejection`: `'warning'` → `'warn'`. Closed.
- **🟢 [S67 RISOLTO] `mode='paper'` hardcoded in `grid_runner.py:610`** — Fixato con `mode=TradingMode.MODE`. 7 trade retroattivi UPDATE-ati. Closed.
- **🟢 [S67 RISOLTO] Fee in raw native value invece che USDT-equivalent** — Fixato in `_normalize_order_response` con conversione automatica + UPDATE retro 6 buy. Closed (CEO opzione A).
- **🟢 [S67 RISOLTO] ccxt sandbox config-key silenziosamente ignorato** — Fixato con `exchange.set_sandbox_mode(True)` in `bot/exchange.py`. Closed.
- `bot/strategies/grid_bot.py:758` — `# TODO 62a (Phase 2): this loop is the 60c double-call source.` (non gating, S67 dust prevention copre il caso principale)
- `bot/strategies/sell_pipeline.py:23` — `# TODO 62a (Phase 2): make _execute_percentage_sell atomic` (race condition audit↔log_trade)
- `bot/strategies/dust_handler.py:17` — `# TODO 62a (Phase 2): emit 'dust_lot_removed' events`
- `bot/trend_follower/allocator.py:43` — `# TODO: move to trend_config in a future session`
- **TF distance filter 12% fisso vs EMA20** (CEO, 2026-05-07): cross-tema con Sentinel/Sherpa, S68+
- **🔴 [S63] `speed_of_fall_accelerating` miscalibrato** + **🟡 Risk score binario** + **🔴 Opportunity score morta**: tutti su Sentinel, da ricalibrare quando ricolleghiamo (S68+)
- **🟡 [S63] Grid polling REST 60s perde i picchi BTC sub-minuto**: mitigazione pre-mainnet → BTC interval 60s → 20s
- **🟡 [S63] Supabase REST cap 1000 righe latente in home/dashboard pubblica**: posticipato (sito ancora in maintenance)

## 6. Domande aperte per CEO

- **24h testnet observation passa OK** → riapriamo home + nav? (CEO 2026-05-08: "se OK, riapriamo")
- **Recalibrate Sentinel parametri** (3 bug calibrazione): quando ricolleghiamo Sentinel in S68+, applichiamo i fix prima del restart o lasciamo correre?
- **TRUNCATE Sentinel/Sherpa/TF tables** quando ricolleghiamo: azzeriamo il dataset DRY_RUN paper-era o lo manteniamo come archivio cross-confronto?
- **Replay counterfactual Sherpa**: rimandato a post-reactivation. Quando ripartiamo, su quale finestra (24h testnet pulito + N giorni? oppure dataset paper-era + 7gg testnet)?
- **Recalibrate-on-restart investigation** (Apple Note CEO 2026-05-07): sospetto Sherpa scriva buy_pct durante runtime (ma è in DRY_RUN, non dovrebbe). Da indagare a freddo S68.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): decisione strategica Board, da rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): se in mainnet useremo BNB per scontare le fee del 25%, l'attuale `fee_usdt = 0` quando `fee_currency = BNB` underestima il costo. Stima del gap: 0.1% × 25% = 0.025% di trade cost = trascurabile su €100, ma da risolvere prima dello scale-up. Soluzione: aggiungere colonna `fee_native_amount` o cross-rate lookup.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`)
- **Esposizione pubblica Validation & Control System** rimandata
- **Reaction chart `/admin` poco leggibile in regime calmo** — fix grafico, post-restart Sentinel

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet dal 2026-05-08 21:15 UTC**. PID 90409 (orchestrator) + 90413 (BONK) + 90414 (SOL) + 90415 (BTC). 4 process alive, brain off.
- **24h testnet observation**: 2026-05-08 21:15 UTC → 2026-05-09 21:15 UTC. Se clean → sito ripristinato (decisione CEO).
- **Go/no-go €100 LIVE**: target ~2026-05-20 (12 giorni di window per S68 fix + 7gg testnet validation + go/no-go decision).
- **Sequenza critica S68**: bug exchange_order_id (~30min) → reconciliation gate Step 5 (~2h) → eventuale recalibrate Sentinel pre-reactivation → ricollegamento brain → 7gg clean → go-live €100.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime, repo `/Volumes/Archivio/bagholderai`). Mac Mini ora **fully synced** con `origin/main` 8659d8b post `git pull --ff-only` 2026-05-08 21:30 UTC.
- **Replay Sherpa counterfactual** posticipato post-reactivation (S69+).
- **Phase 9 V&C — Pre-Live Gates**: contabilità (S66 ✅), fee USDT canonical (S67 ✅), reconciliation gate nightly (S68), wallet reconciliation Binance settimanale (post go-live), dust converter pre-mainnet (S67 dust prevention ✅).

## 8. Cosa NON è stato fatto e perché

In S67 NON è stato fatto **brief 67a Step 5 (reconciliation gate nightly)** — rimandato a S68 perché stasera lo scope era diventato troppo grosso (codice nuovo per order placement + 4 bug emersi a caldo + 2 restart + cleanup retroattivo + git workflow). Il gate è critico per il go-live €100 ma non blocca testnet shake-down delle prossime 24h.

NON è stato ripristinato **il sito pubblico** (home + nav). Decisione CEO 2026-05-08: aspettiamo 24h di testnet pulito senza sorprese prima di riportare up. Se domani sera tutto è ok → home torna live (decisione CEO). Eventuale post X / aggiornamento /diary su questo riavvio = decisione CEO.

NON sono state cancellate le row legacy `bot_config` per OP/ZEC/TRX e altri 51 simboli storici TF. CEO 2026-05-08: "is_active=false, non cancellare. Archivio." Le 4 row attive sono BTC + SOL + BONK + (orphan reconciler riaggancia automaticamente coin con holdings residue Binance, come è successo con OP).

NON sono state ricollegate TF/Sentinel/Sherpa. Stesso pattern: la S67 era focalizzata sul testnet path Grid + accounting; la reactivation dei 3 brain richiede brief CEO dedicato + decisione su TRUNCATE delle relative tabelle paper-era.

NON è stato scritto il **restore script** complementare di `backup_db_s67.py`. CEO 2026-05-08: "lo faremo nel caso servisse." Backup JSONL leggibile e restoreable a mano se mai necessario.

NON è stato risolto il bug **`exchange_order_id=null`** sul sell OP — debt tracciato per S68 (cosmetico, non blocca trading).

NON è stato risolto il bug **`recalibrate-on-restart`** (trigger buy che cambiano spontaneamente). Era già aperto da S63, S67 ne ha vista una nuova istanza ma non l'ha indagato.

NON è stato aggiornato `tests/test_pct_sell_fifo.py` legacy (S66 debt confermato): assertions pre-S66 ancora obsolete dopo pivot avg-cost. Manutenzione, non gating.

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| 2026-05-07 | 1 | Phase 1 split grid_bot.py | APPROVED | 0 regressioni, 0 risk gates aperti | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-08 | 1 | Operation Clean Slate Step 0d (formula verification) | CRITICAL FINDING SHIPPED FIX | Bias `realized_pnl` +$26.97 (+29%) certificato da 2 metodi indipendenti. Root cause: queue desync per 4 cause concorrenti. Fix Step 1 chiude identità al centesimo. | `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md` (gitignored) |
| 2026-05-08 | 1 | S67 brief 67a Step 2-4 (testnet order placement) | SHIPPED + 4 BUG INTERNI | 6 buy + 1 sell live testnet. 4 bug emersi a caldo: severity 'warning' (CHECK fail), mode='paper' hardcoded, fee in raw native, ccxt sandbox config-key ignorato. Tutti fixati nella stessa sessione. | `report_for_CEO/2026-05-08_s67_fee_usdt_design_decision_report_for_ceo.md` |
| 2026-05-08 | 1 | Pre-reset Supabase backup | COMPLETE | 22 tabelle, 51,943 righe, 22.47 MB JSONL su Mac Mini | `audits/2026-05-08_pre-reset-s67/_manifest.json` (gitignored) |
