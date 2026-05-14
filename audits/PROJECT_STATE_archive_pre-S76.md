# PROJECT_STATE.md — Archivio pre-S76

**Generato:** 2026-05-14 (chiusura S76)
**Scopo:** preserva il contenuto rimosso dal `PROJECT_STATE.md` corrente durante la pulizia del 2026-05-14. La regola canonica del file vivo è 40KB; era cresciuto a 78KB con 5 sessioni di storico impilate nell'header + voci in-flight risolte da S70 in poi mai compresse + audit table con righe fino al S67.

**Cosa contiene questo archivio:**
- Header storici delle sessioni S72 → S75 (in ordine cronologico inverso)
- Decisioni recenti delle sessioni S69 (pre-S70 = soglia di taglio scelta da Max)
- Righe della tabella audit esterni di Area 1 / Area 0 fino al S69 incluso

**Cosa NON contiene:**
- Le voci S70+ del file vivo (sono rimaste in PROJECT_STATE.md o compattate in 1-2 righe lì)
- I commit git pre-S76 (sono già in `git log`)

Per recuperare lo stato esatto di un'altra sessione: `git show <commit>:PROJECT_STATE.md` con il commit di chiusura della sessione che cerchi (vedi `git log --grep "S<NN> closure"`).

---

## Header storici (sessioni S72 → S75)

### Sessione 75 chiusura — 2026-05-13 sera

3 commit pushati, sito pubblico. Commit: `f62f781` (howwework v3 — Auditor entity + state-files narrative + badge content refresh), `67f1f57` (brief 75a — blog infrastructure: Content Collections + listing + post + CTA), `cd8ce65` (fix dashboard meta description, era fallback home). Mac Mini fast-forward `b38b88b..cd8ce65` (13 file, +1044/−110), no restart orchestrator (zero impatto bot — tutto in web_astro / STYLEGUIDE / briefresolved / drafts). Brief 75a archiviato in `briefresolved.md/`. Draft `2026-05-07_howwework_v3.md` archiviato in `drafts/applied/2026-05/`. Roadmap 2026-05-14 fissata: (1) refactor `grid_runner.py` (1623 righe), (2) brief 75b stop_buy_unlock_hours (fotocopia di 74d), (3) audit messaggi idle re-entry / recalibrate quando stop_buy attivo. Motivazione empirica al brief 75b: perdita reale 2026-05-13 causata da stop-buy che ha bloccato BUY in down-trend (opportunità DCA persa → avg cost non si è abbassato).

### Sessione 74b chiusura — 2026-05-12 sera tarda

4 commit pushati + 2 migration Supabase + 2 restart bot Mac Mini. Commit: `02b030f` (74c partial fills + orphan recovery script), `f278dea` (74b Bug 1 stop-buy badge + /admin drift freshness), `5a29075` (74d DEAD_ZONE_HOURS per-coin in `bot_config` + tooltip esplicativo), `2f67533` (74b Bug 2 + Bug 1 refactor via nuova table `bot_runtime_state`). Migration: `bot_config.dead_zone_hours` + nuova `bot_runtime_state` (RLS service-role write + anon SELECT, 1 riga per symbol, UPSERT ogni tick). Orphan BONK 21190 (1.37M, $10.38) recuperato in DB via `scripts/insert_orphan_trade_74c.py --write`, reconcile post-cleanup `matched=24 drift=0 orphan=0`. Pulizia chiusura sessione: 3 brief archiviati (65b/72a/74b), 4 vecchi CEO report archiviati, roadmap aggiornata con S71→S74b, Apple Notes letta in sola lettura. **Gate canonical state mainnet €100 ora tutte chiuse**; restano solo mobile test reale + analisi Sentinel/Sherpa 7gg DRY_RUN + Board approval.

### Sessione 74 — 2026-05-12 16:50 UTC

5 commit pushati: `3f3e349` (grid public IT→EN labels, brief 74a Task 4 invertito a EN), `d289a8a` (Telegram "Buying at market" branching fix, brief 74a Task 2), `93dc00d` (Telegram privato standardizzato EN, 9 stringhe IT residue tradotte), `a4674e6` (admin dashboard polish: Opp offset on Sentinel chart + range selector 12h/24h/7d/1m sincronizzato across 5 chart + Opp linea su reaction chart + overlay BTC top-center + reconciliation footnote drift fix), `3535184` (drop hardcoded "24h" da chart titles). Bot Mac Mini restartato 18:32 UTC (Tasks 16+17 live). **TCC fix shipped manualmente**: Max ha attivato python3.13 in FDA, test cron 18:18 verde. Cron reconcile produzione torna OK. Bug critico isolato (brief 74c) poi shipped in S74b. Decisioni strategiche aperte parcheggiate: (a) buy trigger anchor A=last_buy / B=avg_buy / C=hybrid, (b) stop-buy time-limit. HWW v3 (brief 74a Task 1) deferred a S75.

### Sessione 73c chiusura — 2026-05-12

2 fix mainnet-safe SHIPPED. Commits `d10b5ad` (BONK lot_size + BTC phantom) + `5061a29` (ccxt option fix). Diagnosi post-S73b: (1) BONK BUY rejected -2010 LOT_SIZE 6 volte per via di `quoteOrderQty` Binance che ricalcola amount sul fill_price slipped → no lot_step compliance; (2) BTC stop_buy "unrealized $-5,308" mentre managed = $-0.50 perché `state.holdings × (current−avg)` include fantasma BTC ~1.0. **Fix 1**: nuovo `place_market_buy_base(amount)` in `bot/exchange_orders.py` + buy_pipeline preferisce path amount-based quando lot_step_size noto + ccxt option `createMarketBuyOrderRequiresPrice=False`. **Fix 2**: `_phantom_holdings` registrato in `_reconcile_holdings_against_exchange` come `max(0, real_qty−replayed_qty)` + `managed_holdings` property usata in 9 punti critici. Mainnet-safe: fix 1 funziona identico, fix 2 phantom=0 → managed=raw, zero behavior change. Test V nuovo (22/22). Brief separato managed_holdings chiuso strutturalmente.

### Sessione 73b — 2026-05-12 08:35 UTC

Hotfix dust trap SHIPPED. Commits `bc39aeb` (sell_pipeline runtime) + `d85f4be` (state_manager replay). Diagnosi post-osservazione 10h: BONK in loop "BUY BLOCKED" da 23:26 UTC perché 0.8 BONK residue ($0.000006, dust unsellable) post full-sellout S73 non scattava il criterio `holdings <= 0` esatto. Fix in 2 punti: (a) `sell_pipeline.py` aggiunge criterion economico `residual_notional < min_notional`; (b) `state_manager.py` replay aggiunge threshold $0.50 USDT. Test 21/21 verdi (test U nuovo).

### Sessione 73 inizio — 2026-05-11 sera

Hotfix Dead Zone (brief 73a) SHIPPED in <1h. Commit `27c909b`. Fix in `grid_bot.py:576-647`: blocco DEAD ZONE RECALIBRATE prima del SELL CHECK. Quando Grid resta con `_last_sell_price > 0` (ladder attivo), `holdings > 0`, `current > avg`, idle ≥ 4h → reset `_last_sell_price=0` + `_pct_last_buy_price=current`. Test S/T verdi (20/20 totali). Restart Mac Mini 23:26 UTC. Risultati live al primo tick: BONK quasi full-sellout (+$0.4370), SOL 1 lotto venduto (+$0.3832), BTC stop_buy auto-resettato dal restart. DEAD_ZONE_HOURS=4.0 hardcoded; Max ha confermato spostamento in dashboard come parametro per-coin (poi shipped in 74d).

### Sessione 72 chiusura DEFINITIVA — 2026-05-11 pomeriggio

Brief 72a "Fee Unification" SHIPPED + audit visivo Max + frontend canonical refactor + TF rimosso dai totali pubblici. 11 commit pushati. Backend: 3 invariants P1/P2/P3 + 18 sell testnet backfillati (cumulato realized $11.6319 → $10.5347, Δ −$1.097). Boot reconcile golden source asymmetric (negative >2% FAIL, positive sempre WARN). Frontend: 4 superfici (home + dashboard + grid.html + tf.html) ora chiamano la STESSA `computeCanonicalState` via `web_astro/public/lib/pnl-canonical.js`. 4 callsite legacy S70 rename `trend_follower→tf` fixati. TF sparito dai totali. Cron reconcile installato `0 3 * * * Europe/Rome`. Zero ORDER_REJECTED post-restart. 6 processi vivi sul Mac Mini. Bit-identical sui valori chiusi (Net Realized $9.32+vivo). Bias documentato −$0.22 su netRealized testnet.

---

## Decisioni recenti pre-S70 (preservate)

- **2026-05-09 (S69) — Strategy A simmetrico SHIPPED**: buy guard "no buy above avg if holdings>0" specular del 68a sell guard (commit `74a13fa`). IDLE recalibrate guard `current > avg → skip` (commit `84e46ea`). DROP COLUMN `bot_config` × 5. fifo_queue.py via, fixed mode via, cleanup completo ~880 righe.
- **2026-05-09 (S69) — brief s70 FASE 1 + 2 SHIPPED**: avg-cost trading completo, niente più FIFO logic, trigger su state.avg_buy_price.

---

## Audit esterni pre-S70 (preservati, area 0 e 1)

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

---

*Per il contenuto S70+ vai a `PROJECT_STATE.md` corrente. Per cose ancora più antiche di S67 → `git log`.*
