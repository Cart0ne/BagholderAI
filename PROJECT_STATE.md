# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-15 — **sessione 78 chiusa** (brief 78a CEO: primo blog post pubblicato in produzione). Sessione corta, operativa, puramente content+deploy.

**Sessione 78 — Primo blog post LIVE**: brief 78a operativo (no codice trading, no migration, no restart bot). Sorgente `an-ai-that-cant-trade.md` (origin story dual-voice Max + BagHolderAI CEO) copiato in `web_astro/src/content/blog/`, build Astro verde (12 pagine, route nuova `/blog/an-ai-that-cant-trade/`), commit `18a0362` + push → Vercel auto-deploy. Brief archiviato come `briefresolved.md/brief_78a_blog_post_publish.md` (rinominato da 77b per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md`). Staging dir `blog/` (untracked) rimossa. Pubblicazione anticipata dal weekend 17-18 maggio.

---

**Fase 1 — Audit Sentinel Sprint 1 (brief 77a)**: tutti PASS empirici su 6.081 fast scan post-70b. SoF firing 2.32% (era ~30%), risk 5 valori distinti, opp 3 valori. 2 issue parcheggiate dal CEO: SoF mono-laterale by design, funding dead-by-design su testnet. Zero codice toccato. Commit `39460a9`.

**Fase 2 — Build Sentinel Sprint 2 (brief 77b)**: piano italiano approvato + 8 step granulari + pytest verde a ogni step. 5 file nuovi (`inputs/alternative_fng.py` 73r, `inputs/cmc_global.py` 87r, `regime_analyzer.py` 136r, `slow_loop.py` 137r, `sherpa/regime_reader.py` 66r), 2 modifiche chirurgiche (`sentinel/main.py` 207→238 +31r; `sherpa/main.py` 535→540 +5r). Pattern modulare anticipativa (lezione S76 grid_runner). Pytest **37 → 85 verdi** (+48 nuovi). Nessun file > 250 righe. 3 decision log: inversione mapping regime→risk/opp (extreme_fear=opp alta, risk basso — "buy fearful sell greedy"), boundaries F&G inclusive low (20→extreme_fear, 21→fear), boot-init counter a MAX (primo slow tick immediato). Commit `a62e5d5` (nota: commit message usa "s78" per errore di numerazione, è S77).

**Fase 3 — Restart Mac Mini LIVE + verifica end-to-end**: graceful kill PID 87923 + relaunch con caffeinate. **Nuovo orchestrator PID 90540** (restart 2026-05-14 21:46 CET). Primo slow tick scattato 2s dopo start (boot-init counter): `regime=fear, risk=30, opp=65, fng=34, cmc=yes, inserted=yes`. DB conferma riga slow con tutti i campi (regime, F&G 34/Fear, BTC dominance 60.24%, decision_log completo). Sherpa cycle successivo (19:48:23 UTC) mostra `proposed_regime=fear` con BTC buy 1.0→1.8, sell 1.5→1.2, idle 1.0→2.0 — diverso dal ciclo precedente (`proposed_regime=neutral` di 2 min prima, pre-slow-tick). **Macchina viva e end-to-end verificata.**

**Fase 4 — Brief 77c proposto** (admin widgets per visualizzare Sentinel slow): in attesa OK CEO. Stima 45-60 min implementazione.

`CMC_API_KEY` aggiunta a `config/.env` Mac Mini da Max prima del restart. Free tier 10.000 crediti/mese, uso atteso ~180.

---

**Sessione 76** (rif. precedente): squash `9ceaa81` + 5 commit feature-branch + 2 migration Supabase + 3 restart watch verdi. Refactor grid_runner package (1623→8 moduli), brief 75b stop_buy_unlock_hours timer, audit idle suppression, UI Safety. Test suite 25→29 verdi. Brief 77a CEO eseguito in FASE 1 puro (6.081 fast scan post-fix 70b analizzate via Supabase MCP). **Tutti e 3 i bug 70b PASS**: SoF firing 2.32% (criterio <10%, era ~30%); risk_score 5 valori distinti 20/26/32/46/52 (era binario); opp_score 3 valori 20/25/30 (era morta a 20). 2 issue strutturali emerse → tutte parcheggiate dal CEO con razionale "va bene così, Sprint 2 risolverà": (A) SoF resta mono-laterale (capitulations crypto asimmetriche per natura, no `speed_of_rise`); (B) funding signal dead-by-design su testnet (soglie 70b calibrate per mainnet 0.01-0.03%, testnet ~10× sotto, riapparirà su mainnet); (C) opp debole accettata fino a Sprint 2 (F&G + regime sono il vero moltiplicatore). Report consegnato + addendum decisioni Board. Roadmap.ts aggiornata: Phase 4 description con sequenza Sentinel-first S76, task "Sentinel Sprint 1 audit empirico (brief 77a)" added as done, "Sherpa Sprint 2" rinominato in "Sentinel Sprint 2" (era misnamed), "Sherpa LIVE one parameter at a time (sell_pct first)" aggiunto come todo. Phase 6 description + timeframe aggiornati ("Target late June / early July 2026"). **Prossima mossa nella sequenza: Brief 78a — Sentinel Sprint 2 build** (slow loop F&G + CMC dominance + regime detection). Mac Mini resta su `b2ae5f7` (nessun restart richiesto dal brief).

---

**Sessione 76** (rif. precedente): squash `9ceaa81` + 5 commit feature-branch + 2 migration Supabase + 3 restart watch verdi. Refactor grid_runner package (1623→8 moduli), brief 75b stop_buy_unlock_hours timer, audit idle suppression, UI Safety. Test suite 25→29 verdi.

**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

> Storico header sessioni S72→S75 in [audits/PROJECT_STATE_archive_pre-S76.md](audits/PROJECT_STATE_archive_pre-S76.md).

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet (Grid-only, $500 budget Board) + Sentinel/Sherpa DRY_RUN con slow loop attivo + sito pubblico online con primo blog post LIVE (S78) + tutte le gate canonical state CHIUSE post-S74b + S76 package refactor + 75b/75c stop-buy unlock + S77 Sentinel Sprint 1 audit PASS + S77 Sentinel Sprint 2 slow loop LIVE**. Mac Mini su `a62e5d5` (PID 90540, restart 2026-05-14 21:46 CET, end-to-end Sprint 2 verificato). Zero ORDER_REJECTED. Cron reconcile attivo 03:00 Europe/Rome. **Target go-live €100: fine giugno / inizio luglio** (POSTICIPATO dalla decisione S76 CEO 2026-05-14). Sentinel Sprint 1 chiuso con tutti PASS (S77 audit empirico 6.081 scan): SoF firing 2.32%, risk 5 valori, opp 3 valori. 2 issue strutturali parcheggiate by design (SoF mono-laterale, funding dead su testnet).

**Roadmap Sentinel-first (CEO S76, 5 step)**: (1) ~~audit + fix Sentinel Sprint 1~~ ✅ CHIUSO S77 — tutti PASS; (2) ~~build Sprint 2~~ ✅ CHIUSO S77 — slow loop F&G + CMC + regime detection SHIPPED + LIVE su Mac Mini; (3) **osservazione 5-7 giorni — IN CORSO (orchestrator restart 21:46 CET 2026-05-14)**; (4) Sherpa LIVE su testnet 1 parametro alla volta (sell_pct primo); (5) mainnet con sistema rodato.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS, 20 tabelle post-S70 con `reconciliation_runs`), Telegram (alerts), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn 3 Grid + Sentinel + Sherpa via env flags (TF off)
  grid_runner/             per-symbol process wrapper PACKAGE (S76 refactor, era monolite 1623 righe)
    __init__.py              bootstrap + main loop (~779)
    __main__.py              CLI entrypoint per `python -m bot.grid_runner` (~26)
    config_sync.py           _sync_config_to_bot — hot-reload Supabase config (~197)
    runtime_state.py         _upsert_runtime_state — mirror in-memory al DB (~45, 75b espone stop_buy_activated_at)
    idle_alerts.py           send_idle_alerts — Telegram recalibrate/re-entry + suppression policy (~52, S76 audit)
    telegram_dispatcher.py   _build_cycle_summary + _format_cycle_summary (~154)
    daily_report.py          maybe_send_daily_report — blocco 20:00 + Haiku commentary (~162)
    liquidation.py           _force_liquidate + _consume_initial_lots + _deactivate (~355)
    lifecycle.py             fetch_price + _print_status + _build_portfolio_summary (~88)
  exchange.py              Binance ccxt sandbox (S67)
  exchange_orders.py       market-order wrapper, fee USDT canonical (S67)
  health_check.py          daily health check
  db_maintenance.py        daily 04:00 UTC retention (sentinel 30gg, sherpa 60gg)
  grid/                    Brain #1 — Grid (post brief 70a)
    grid_bot.py              public API + GridState + `_last_sell_price` ladder + FEE_RATE 0.001 + trigger fee-buffered + 75b `_stop_buy_activated_at` + auto-reset block
    state_manager.py         init_avg_cost_state_from_db (replay anche `_last_sell_price`)
    buy_pipeline.py          buy exec + Strategy A guard "no buy above avg" (S69)
    sell_pipeline.py         sell exec + 68a guard + 70a set/reset `_last_sell_price` + post-fill warning slippage_below_avg + 75b clear timestamp
    dust_handler.py          write-off helpers
  sentinel/                Brain #2 — Sentinel ON DRY_RUN (S70)
    score_engine.py          ladder granulare -0.5/-1/-2 + funding intermedi (brief 70b)
    price_monitor.py         _SOF_MIN_DROP_1H_PCT=-0.5 floor su sof_accelerating (brief 70b)
    main.py                  loop 60s + SENTINEL_TELEGRAM_ENABLED env (default false)
  sherpa/                  Brain #3 — Sherpa ON DRY_RUN (S70)
    main.py                  loop 120s + SHERPA_TELEGRAM_ENABLED env (default false)
  trend_follower/          Brain #4 — TF (DISABLED via ENABLE_TF=false)
db/, utils/, scripts/, web_astro/  (DB client, telegram, daily reports, sito Astro maintenance)
scripts/reconcile_binance.py  S70 Step A: reconciliation Binance ↔ DB trades (cron 03:00 Europe/Rome)
config/                    settings, validation_and_control_system.md, brief parcheggiati (DUST + evaluate_trading_skills)
audits/                    gitignored — formula_verification_s66 + 2026-05-08_pre-reset-s67/ + PROJECT_STATE_archive_pre-S76.md
tests/                     test_accounting_avg_cost.py **29/29 verdi** (post-S76)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. Telegram alerts: solo Grid trade events; Sentinel+Sherpa silenziati via env (memoria `feedback_no_telegram_alerts`).

## 3. In-flight (settimana 2026-05-11+)

### S78 — Primo blog post LIVE
- **🟢 Brief 78a — Blog post publish**: file `an-ai-that-cant-trade.md` (dual-voice origin story Max + BagHolderAI CEO, 76 sessioni-counter, 7635 byte) copiato in `web_astro/src/content/blog/`. Frontmatter conforme schema content collection (type=lesson, volume=1, draft=false, date 2026-05-15, summary 154 char < 220 limit, tags origin/introduction/behind-the-scenes). Build Astro verde: 12 pagine, route nuova `/blog/an-ai-that-cant-trade/`, card su `/blog` index, CTA `payhip.com/b/a4yMc` Volume 1 presente. Zero modifica a schema/componenti/layout (vincolo brief rispettato). Commit `18a0362` + push → Vercel auto-deploy. Brief archiviato in `briefresolved.md/brief_78a_blog_post_publish.md` (rinominato da 77b per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md`). Staging dir `blog/` (untracked) rimossa.
- **Verifica visiva live**: spetta a Max (memoria `feedback_no_screenshots`). URL: `bagholderai.lol/blog/an-ai-that-cant-trade`.

### S77 fase 2 — Sentinel Sprint 2 slow loop SHIPPED + LIVE
- **🟢 Brief 77b — Sentinel Sprint 2 slow loop**: piano italiano approvato + 8 step granulari + pytest verde a ogni step. 5 file nuovi (`inputs/alternative_fng.py` 73r, `inputs/cmc_global.py` 87r, `regime_analyzer.py` 136r, `slow_loop.py` 137r, `sherpa/regime_reader.py` 66r), 2 file modificati chirurgicamente (`sentinel/main.py` 207→238 +31r aggiunge contatore + chiamata `slow_loop.tick(supabase)` al boot e ogni 240 fast tick = 4h; `sherpa/main.py` 535→540 +5r sostituisce hardcoded `regime="neutral"` con `current_regime = get_current_regime(supabase)`). Pattern modulare anticipativa: nessun file > 250 righe, ogni modulo testabile in isolamento. Commit `a62e5d5` (msg dice "s78" per typo, è S77).
- **🟢 Test +48**: `test_fng_input.py` 7 (happy + 6 failure modes), `test_cmc_input.py` 7 (incluso no_api_key path), `test_regime_analyzer.py` 21 (5 buckets + 8 boundary 20/21/40/41/60/61/80/81 + fallback chain), `test_slow_loop.py` 6 (happy / F&G only / both None / DB err / fetcher raise / inversion check), `test_regime_reader.py` 7 (5 regimi validi + 4 fallback paths). Suite globale **37 → 85 verdi**.
- **🟢 Decisioni delegate a CC**: inversione mapping `extreme_fear → risk=20/opp=80` (trading-sense "buy fearful sell greedy") vs brief originale `risk=80/opp=20`; boundaries F&G inclusive low documentate; contatore boot-init a MAX (primo slow tick immediato).
- **🟢 Architettura**: `slow_loop.py` separato anziché aggiunto a `main.py` (lezione S76 grid_runner monolite 1623r). Pattern simmetrico per Sprint 3 news feed (basterà `news_loop.py` + secondo contatore, zero refactor).
- **🟢 CMC_API_KEY** aggiunta a `/Volumes/Archivio/bagholderai/config/.env` da Max. Free tier 10.000 crediti/mese, uso atteso 180/mese a 6 call/day.
- **🟢 raw_signals jsonb slow**: contiene `regime`, `decision_log` (per audit S77-style), `fng_value/label/timestamp`, e se presente CMC `btc_dominance/total_market_cap_usd/total_volume_24h_usd/active_cryptocurrencies`. Sprint 2 logga CMC ma NON lo usa nel regime calc — riservato a Sprint 2.5.
- **🟢 NEVER-raise contract** uniforme sui 2 nuovi input + slow_loop tick: nessuna eccezione può crashare Sentinel fast loop. Fallback chain: F&G None → neutral / F&G stale 36h → neutral / DB err → log+swallow+retry next tick.

### S77 fase 3 — Restart Mac Mini + verifica end-to-end LIVE
- **🟢 Pull + graceful restart**: `git pull` su `/Volumes/Archivio/bagholderai`, `kill -TERM 87923` (parent precedente), relaunch con caffeinate + env flags identici al pattern S76. Nuovo PID parent: 90540. 6 processi python + 1 caffeinate = struttura attesa.
- **🟢 Verifica primo slow tick (2s dopo start)**: log Sentinel `21:46:23 INFO bagholderai.sentinel.slow_loop: Slow tick: regime=fear, risk=30, opp=65, fng=34, cmc=yes, inserted=yes`. Boot-init counter funziona come previsto, no 4h ciechi.
- **🟢 Verifica DB**: prima riga `sentinel_scores score_type='slow'` con regime=fear, fng_value=34, fng_label="Fear", btc_dominance=60.24%, decision_log completo (`cmc_seen=true, fng_used=true, fng_age_s=71183, fallback_reason=null`).
- **🟢 Verifica Sherpa transizione**: ciclo 19:46:22 con `proposed_regime=neutral` (pre-slow-tick, fallback "neutral" da regime_reader); ciclo 19:48:23 con `proposed_regime=fear` (post-slow-tick). BTC: buy 1.0→1.8, sell 1.5→1.2, idle 1.0→2.0 — proposte diverse, conferma che `calculate_parameters(regime=current_regime, ...)` riceve il regime corretto.
- **🟢 Brief 77b archiviato in `briefresolved.md/`.**

### S77 fase 4 — Brief 77c admin widgets (PROPOSTO, in attesa OK CEO)
- **🟡 Brief 77c** scritto e parcheggiato in `config/brief_77c_admin_sentinel_slow_widgets.md`. Propone 2 widget per `/admin`: Widget A = regime banner (15 min), Widget B = regime timeline 7gg (30 min). Tutto presentation layer, zero backend touch, no sito pubblico (solo /admin privata). CC in standby per implementazione appena CEO approva i 4 punti aperti (palette colori, F&G line overlay, polling rate, posizione in /admin).

### S77 fase 1 — Sentinel Sprint 1 audit empirico (brief 77a) SHIPPED
- **🟢 Brief 77a — Sentinel Sprint 1 audit empirico**: 6.081 fast scan post-fix 70b (~4.5 giorni di DRY_RUN), 6 query brief + 3 query custom asimmetria via Supabase MCP. Tutti e 3 i bug 70b PASS sui criteri brief. 2 issue strutturali (SoF asimmetrico, funding dead) emerse e parcheggiate dal CEO con decisione "va bene così, Sprint 2 risolverà". Report consegnato: [report_for_CEO/2026-05-14_s77_sentinel_sprint1_audit_report_for_ceo.md](report_for_CEO/2026-05-14_s77_sentinel_sprint1_audit_report_for_ceo.md) con addendum §10 decisioni Board.
- **🟢 Roadmap.ts aggiornata** in fase 1: Phase 4 description con sequenza Sentinel-first S76, task "Sentinel Sprint 1 audit empirico" added as done, rename "Sherpa Sprint 2" → "Sentinel Sprint 2" (era misnamed da S63), aggiunto task "Sherpa LIVE one parameter at a time (sell_pct first)" come todo, Phase 6 description + timeframe aggiornati con la sequenza posticipata "Target late June / early July 2026". Commit `39460a9`.
- **🟢 Brief 77a archiviato** in `briefresolved.md/`.
- Zero codice toccato in fase 1, zero migration, nessun restart bot.

### S76 SHIPPED (squash `9ceaa81`)
- **🟢 Refactor `grid_runner.py` → package 8 moduli**: 1623 → 779 main loop + 7 moduli specializzati. Orchestrator entrypoint preservato. BTC tradato al primo tick post-restart 11:50 UTC. Pytest 25/25 ad ogni step. Lazy import `SyncTelegramNotifier` per testabilità.
- **🟢 Brief 75b — stop_buy_unlock_hours timer**: 2 migration (`bot_config.stop_buy_unlock_hours` REAL DEFAULT 0 CHECK 0..168 + `bot_runtime_state.stop_buy_activated_at` TIMESTAMPTZ). Default 0 = comportamento 39b preservato (solo profitable sell resetta). Quando > 0, auto-reset post N ore. Profitable sell ha priorità sul timer. Test +3 (Z/AA/BB).
- **🟢 Audit idle alert suppression**: `send_idle_alerts(stop_buy_active=False)` — quando True, recalibrate interno avviene comunque, solo Telegram silenziato. Test +1 (CC). Verificato live SOL/BONK restart 12:18 UTC.
- **🟢 UI `/grid` Safety — `stop_buy_unlock_hours`**: riga editabile in Safety section, pattern 74d, sublabel didattica. Save via `sbPatch` su `bot_config` (RLS anon UPDATE già attiva).

### S75 SHIPPED
- **🟢 howwework v3** (`f62f781`): page + diagram refactor con Auditor entity, rules of engagement drift fix, badge content refresh. Draft `2026-05-07_howwework_v3.md` archived in `drafts/applied/2026-05/`.
- **🟢 Brief 75a — Blog infrastructure** (`67f1f57`): Astro Content Collections (v6 path `src/content.config.ts`). 6 file nuovi: config schema + placeholder + BlogCTA volume-aware + BlogPostCard + index + slug. SiteHeader 7 voci con Blog in posizione 3. STYLEGUIDE § 22 nuova.
- **🟢 Fix dashboard meta description** (`cd8ce65`): Layout.astro propaga unico prop a meta + og + twitter card.

### S74b SHIPPED
- **🟢 Brief 74c — Partial fills recovery** (`02b030f`): `_normalize_order_response` spezzato in due branch + event `ORDER_PARTIAL_FILL`. Test W/X/Y → 25/25. Orphan BONK 21190 recuperato via script ad-hoc. Mainnet-gating chiusa.
- **🟢 Brief 74b — Stop-buy badge + trigger drift via `bot_runtime_state`** (`f278dea` + `2f67533`): nuova table UPSERT ogni tick. /grid widget anchored al bot, /admin drift filtrato latest-run-per-symbol. Primitiva canonical riusabile.
- **🟢 Brief 74d — DEAD_ZONE_HOURS per-coin in `bot_config`** (`5a29075`): hot-reload, /grid Safety editable con sublabel.

### S73 SHIPPED
- **🟢 73c BONK lot_size + BTC phantom mainnet-safe** (`d10b5ad` + `5061a29`): `place_market_buy_base` amount-based + `_phantom_holdings` registrato al boot + `managed_holdings` property in 9 punti hot path.
- **🟢 73b dust trap hotfix** (`bc39aeb` + `d85f4be`): criterio "fully sold out" da `holdings <= 0` esatto a residual_notional < MIN_NOTIONAL/threshold.
- **🟢 73a Dead Zone recalibrate** (`27c909b`): reset `_last_sell_price=0` + `_pct_last_buy_price=current` quando ladder mode + idle ≥ 4h. BTC/SOL/BONK fermi 19-21h sbloccati al primo tick.

### S72 / S71 / S70 SHIPPED (riepiloghi compatti)
- **🟢 S72 brief 72a Fee Unification + canonical refactor + TF removal** (11 commit `a1ad217` → `e975a71`): 3 invariants + 18 sell backfillati + 4 superfici frontend unificate via `pnl-canonical.js`. TF sparito dai totali pubblici.
- **🟢 S71 brief 71a cleanup pending (5 task)** (4 commit): P&L hero unification + LAST SHOT pre-rounding + reason check_price+slippage + mobile recon table + cron wrapper.
- **🟢 S70/S70a/S70b/S70c**: avg-cost trading completo + reconciliation Binance Step A/B/C + Sentinel ricalibrazione + sell_pct net-of-fees + post-fill warning + /admin overhaul + sito pubblico relaunch + roadmap.ts Phase 13. Vedi §9 audit table per i commit specifici.

### Aperti / TODO
- **🟡 [S72] Telegram messages post-72a focus**: la riga "Have SOL: $547.23 → Sell $19.94" mostra TOTALE wallet inclusi phantom testnet. Funzionalmente OK, narrativamente confonde. Fix cosmetico (mostrare wallet vs grid-owned, o eliminare riga). Vincolo Max: non toccare canonical computeCanonicalState.
- **🟡 [S72] Code debt: `buildSection` morto in dashboard-live.ts**: ~10 min cleanup post-go-live.
- **🟡 [S70c] Sito mobile review approfondito**: smoke iPhone fatto, test su device reale richiede Max sul telefono.
- **🟡 [S70c] Brief "P&L netto canonico" (Strada 2)**: ~3-4h. Fix per-riga `realized_pnl` (sottrazione fee_usdt) + cambio formula avg_buy_price + backfill cumulato + verifica identità. Pre o post go-live €100? Decisione Max.
- **🟡 [S70] Sherpa rule-aware sell_pct**: in DRY_RUN propone sell_pct=1.5 per BONK ignorando hotfix slippage. Pre-SHERPA_MODE=live, rule engine deve preservare buffer per coin.
- **🟡 [S70] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a pre-mainnet. BONK avrebbe slippage_buffer=3%, BTC/SOL=0%.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A.

## 4. Decisioni recenti

- **2026-05-15 (S78, brief 78a — primo blog post LIVE) — Pubblicazione anticipata dal weekend 17-18 maggio**. Brief operativo CC, no codice trading: copia file in content collection + build verde + commit + push. Naming rinominato `brief_77b_blog_post_publish.md` → `brief_78a_blog_post_publish.md` per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md` già archiviato. Decisione minore (autonoma CC). Commit `18a0362`. — *why:* il post era già scritto e approvato dal Board, l'anticipazione libera il weekend per il Post 2 strategico ("why we're not live yet"); BUSINESS_STATE §2 aggiornato di conseguenza.

- **2026-05-14 (S77 fase 2+3, Sprint 2 slow loop SHIPPED + LIVE) — Sentinel ora ha slow loop ogni 4h, Sherpa legge regime dinamico, verificato end-to-end su Mac Mini**. Architettura: 5 file nuovi + 2 chirurgici, nessun monolite (lezione S76). 3 decision log: (1) **inversione mapping regime→risk/opp** (Board approved): extreme_fear → opp=80/risk=20, extreme_greed → opp=20/risk=80, mapping monotono simmetrico attorno a neutral=40/40. Razionale trading: panic = buy zone, euphoria = top. (2) **`slow_loop.py` come modulo separato** (Board explicit request "evitiamo 2000 righe in un file"): orchestra fetch+regime+score+INSERT in isolamento, mock-friendly per test, pattern simmetrico futuro `news_loop.py` Sprint 3. (3) **boot-friendly counter**: parte a MAX → primo slow tick immediato, Sherpa ha regime reale dal primo ciclo. Pytest +48 nuovi test = 85 verdi totali. Mac Mini restart in carico a Max. — *why:* sblocca step 3 sequenza Sentinel-first (osservazione 5-7 giorni delle proposte Sherpa con regime attivo).

- **2026-05-14 (S77 chiusura, audit-only) — Sentinel Sprint 1 chiuso con tutti PASS + 3 design questions parcheggiate dal CEO**. FASE 1 audit empirico eseguita in puro (no FASE 3 fix necessaria perché tutti i bug 70b hanno passato i criteri brief). Findings critici: (a) firing rate SoF crollato da ~30% a 2.32%, fix structural via floor `change_1h ≤ -0.5%` funziona; (b) risk distribution 5 valori distinti, ladder granulare 70b funziona; (c) opp distribution 3 valori ma vita debole (92% a base 20) → dipende interamente da BTC ladder, funding signal zero firing; (d) gap risk-opp = +26 quando SoF acceso, ~0 quando spento → SoF è driver unico dell'asimmetria visiva osservata sul grafico /admin. CEO ha deciso: NO `speed_of_rise` (rumore, no azione sensata per Grid), accetta funding dead-by-design su testnet (soglie calibrate per mainnet 0.01-0.03%), non tunare opp adesso (Sprint 2 sarà il moltiplicatore). — *why:* Sprint 1 è già "good enough" per la sequenza Sentinel-first; toccare ora sarebbe overfitting al testnet di maggio 2026 invece di calibrare per mainnet. Sblocca brief 78a Sprint 2.

- **2026-05-14 (S76 chiusura, squash `9ceaa81` + 5 sub-commit + 2 migration + 3 restart) — Refactor grid_runner package + brief 75b + audit idle + UI**. Strategia: refactor PRIMA come prerequisito strutturale (zero behavior change), perché i due brief successivi toccano esattamente i moduli `runtime_state.py` (75b) e `idle_alerts.py` (audit) — separarli rende i diff stretti. Pattern shipping: 8 step granulari, pytest verde dopo ognuno, smoke su Mac Mini con 3 restart osservativi (11:50 refactor / 12:00 75b / 12:18 audit). Decisione disciplinare: durante refactor avevo anticipato un cambio payload `stop_buy_activated_at` su runtime_state — fermato + rimosso, perché refactor doveva essere puramente strutturale. UI pattern fotocopia 74d. Default 0 ovunque per i 3 bot live → zero behavior change live finché Max non edita. Verifica empirica audit inequivocabile (log idle recalibrate presente, Telegram assente solo dal restart 12:18 in poi). Branch `refactor/grid_runner_split` cancellato in locale, preservato su origin come archivio. — *why:* roadmap S75 chiusa intera + UI bonus richiesto a fine sessione. Investimento architetturale paga subito e continuerà a pagare per futuri brief sulle componenti modulari.

- **2026-05-13 (S75 chiusura, 3 commit) — Sito pubblico ampliato**: howwework v3 + blog infrastructure + dashboard meta fix. HWW v3 opzione B (coerenza completa: prose hero + meta + badge + diagramma React Auditor). Blog Astro Content Collections v6 path `src/content.config.ts`. Dashboard meta description specifica $500 testnet + reconciliation. — *why:* chiusura del "private-first then public" pivot di S74. Salvato `feedback_cc_runs_orchestrator` + `project_next_session_grid_refactor_dca` con roadmap S76.

- **2026-05-12 (S74b chiusa, 4 commit + 2 migration) — Strada B canonical: nuova table `bot_runtime_state` come primitiva**. Trigger: Bug 2 (trigger drift widget vs bot, ~1.5% BONK) richiedeva esporre `_pct_last_buy_price`. Scelta B (mirror table) su A (events log + recompute) per primitiva canonical riusabile. Schema 6 colonne UPSERT ogni tick. /grid widget anchored al bot's source of truth. Brief 74c partial fills + cleanup orphan BONK 1.37M (script ad-hoc) + DEAD_ZONE_HOURS spostato in bot_config per-coin con tooltip. — *why:* gate canonical state mainnet €100 chiuse strutturalmente. Strada B paga dividendi: ogni futuro brief "il dashboard mente" usa la stessa primitiva.

- **2026-05-11 (S73 hotfix Dead Zone, commit `27c909b`) — brief 73a SHIPPED in <1h**. Trigger: BTC/SOL/BONK fermi 19h/5h/21h post-sell run per incrocio 3 meccanismi S69-S70 (ladder + buy guard + IDLE recalibrate skip). Fix Opzione A "mirata": reset `_last_sell_price=0` + `_pct_last_buy_price=current` dopo DEAD_ZONE_HOURS idle quando ladder attivo + current>avg. Variazione guard sostituita con `_last_sell_price > 0` per evitare false negative su fantasma S72. Risultati live: BONK quasi full-sellout, SOL 1 lotto, BTC stop_buy resettato dal restart. — *why:* sblocco rapido critico; Opzione A additiva, basso rischio.

- **2026-05-11 (S72 chiusura DEFINITIVA, 11 commit) — Brief 72a Fee Unification + audit visivo + canonical refactor + TF removal**. Sessione doppia: brief 72a CEO + audit Max che rivela 5 problemi strutturali (frontend P2 non uniforme, lexical drift S70 rename 4 callsite tf.html broken 49gg, 2 implementazioni P&L divergenti → `pnl-canonical.js` shared, inline script bypass dashboard.astro, TF nei totali Grid). Tutti risolti. Verifica Chrome headless dump-dom: bit-identical 4 superfici. Memoria `feedback_lexical_drift_after_rename` salvata. — *why:* l'audit visivo Max funziona come secondo paio d'occhi pre-go-live €100 — pytest + boot reconcile non catturano questi bug.

- **2026-05-11 (S72 inizio — sessione diagnosi) — Brief 71b assorbito in 72a "Fee Unification"**. Diagnosi via `fetch_my_trades` Mac Mini: fee BONK reale 30.726,2 BONK (0.1% lordo) + initial balance fantasma testnet +18.446 BONK pre-S67. Equazione chiusa. Svolta design: **holdings = `fetch_balance()` golden source**. — *why:* "fee unification, non voglio più avere problemi" → un brief unico chiude la radice invece di 3 fix paralleli. Codice più semplice, mainnet più robusto.

- **2026-05-10 (S70c chiusura) — Sito online + decisione editoriale "story is process, not numbers"**. Sito ripristinato dopo 5gg maintenance: TestnetBanner global + sweep paper→testnet mirato + Capital breakdown + Reconciliation table pubblica + TF dottore SVG inline. Bug strutturale `realized_pnl per-trade gross` emerso e parcheggiato (Strada 2). Decisione editoriale: cambiare convenzione contabile retroattivamente OK perché "la storia racconta il processo, non i numeri". Salvato `feedback_story_is_process_not_numbers`.

- **2026-05-10 (S70 + S70b) — Reconciliation Binance Step A + /admin overhaul + rename `manual→grid`**. Script `reconcile_binance.py` aggrega fill per orderId + match `exchange_order_id` con fallback ts. Primo run: 24/24 ordini matched, zero drift. /admin: mascot in titolo, dashed-overlay Opp, collapsibles, jitter ±3px, Parameters scala intera + asse Y dx live, BTC overlay, RPC live DB monitor, Reconciliation Step B con trade-by-trade compare. Open question 19 chiusa (4 tabelle DB + 6 callsite frontend allineati).

- **2026-05-10 (S70 brief 70a + 70b) — sell_pct net-of-fees + sell ladder + Sentinel ricalibrazione**. FEE_RATE 0.00075→0.001. Trigger Grid: `reference × (1+sell_pct/100+FEE)/(1-FEE)`. `_last_sell_price` campo nuovo + replay da DB. Post-fill warning `slippage_below_avg`. Sentinel: ladder drop/pump granulare + funding intermedi + sof floor -0.5%. Telegram silent flags. Test 15/15 verdi. Restart 09:51 UTC.

> Decisioni S69 e precedenti: vedi [audits/PROJECT_STATE_archive_pre-S76.md](audits/PROJECT_STATE_archive_pre-S76.md).

## 5. Bug noti

### 🔴 Aperti
- **🔴 [S70c]** `realized_pnl` per-trade gross: `revenue - cost_basis` in [sell_pipeline.py:397](bot/grid/sell_pipeline.py#L397) NON sottrae `fee_usdt`. Conseguenza: ogni "Recent trades" gonfiato ~$0.024 su trade da $24 (~0.1%). Cumulato 458 sell ≈ $30 overstatement. Bias secondo-ordine su avg_buy_price (~0.1%). Hero "Total P&L" non affetto (parte da Net Worth Binance vero). Fix in Strada 2 (~3-4h, brief separato).
- **🔴 [S67]** `exchange_order_id=null` su sell OP/USDT — fallback timestamp gestisce reconciliation, ma debt cosmetico.

### 🟡 Aperti
- **🟡 [S67]** Slippage testnet variabile (2.46% BONK osservato) — gestito con sell_pct buffer per ora. Brief `slippage_buffer parametrico per coin`.
- **🟡 [S69]** 2 BONK sells fossili pre-S68a con `buy_trade_id NULL` — restano in DB ma niente più check li flagga.
- **🟡 [S70]** Sherpa propone abbassare BONK sell_pct 4→1.5 in DRY_RUN (ignora hotfix slippage). Pre-SHERPA_MODE=live, rule engine deve preservare buffer per-coin.
- **🟡 [S70]** LAST SHOT path bypassa lot_step_size rounding. Cosmetico (1 Telegram + 1 ORDER_REJECTED warn), ma pre-mainnet vale arrotondare anche nel path LAST SHOT.
- **🟡 [S70 PARZIALE]** Reason bugiardo su slippage: post-fill warning rende slippage visibile in `bot_events_log`, ma stringa `reason` del trade resta sbagliata. Cosmetico.
- **TF distance filter 12% fisso vs EMA20** (CEO 2026-05-07): cross-tema Sentinel/Sherpa, post-go-live.

### 🟢 Risolti recenti (sintesi)
- **S76**: grid_runner monolite split in package (squash `9ceaa81`); brief 75b stop_buy_unlock_hours timer; audit idle suppression.
- **S74b**: 74c partial fills (mainnet-gating), 74b stop-buy badge + trigger drift via `bot_runtime_state`, 74d DEAD_ZONE_HOURS per-coin.
- **S73**: 73c BONK lot_size + BTC phantom mainnet-safe; 73b dust trap (criterio economico residual_notional); 73a dead zone recalibrate (BTC/SOL/BONK sbloccati 19-21h).
- **S72**: brief 72a Fee Unification (BONK InsufficientFunds + holdings drift + realized_pnl gross + avg gross tutti chiusi). Backfill 18 sell testnet.
- **S71**: mobile recon table overflow, LAST SHOT BUY rejected -2010, reason bugiardo su slippage (suffix added), drift numerico home/dashboard/grid.html.
- **S70**: sell-at-loss BONK (slippage 2.46%), Sentinel risk binario 20/40 (ladder granulare), Open question 19 rename `manual→grid`.

## 6. Domande aperte per CEO

- 🆕 **[S74 NEW] Buy trigger anchor: A=last_buy / B=avg_buy / C=hybrid**: bot ancora a `last_buy_price`. User mental model "DCA below avg" si aspetta avg. Simulazione 4-buy in downtrend: A spread 10%, B compresso 5%. Proposta CC: opzione C ibrida `max(avg × (1−buy_pct), last_buy × (1−min_gap))`. Riguarda trading logic, brief dedicato.
- 🟡 **[S70c NEW] Brief separato "P&L netto canonico" (Strada 2)**: ~3-4h. Combina fix per-riga `realized_pnl` + cambio formula avg_buy_price + backfill cumulato + verifica identità. Decisione editoriale già confermata: cambi retroattivi raccontati nel diary. Pre o post go-live €100?
- 🟡 **[S70c] Ripristino sito pubblico**: brief CEO necessario (post-S70c, cross-fertilization /admin pattern).
- 🟡 **[S70] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a pre-mainnet.
- 🟡 **[S70] Sherpa rule-aware sull'hotfix slippage**: prima di SHERPA_MODE=live.
- 🟡 **[S70] Sentinel/Sherpa TELEGRAM flag**: default off; Max abilita quando vuole.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.

> Domande risolte S70-S76: chiuse nelle voci §3 In-flight e §9 Audit. Storico completo nei commit log e in `audits/PROJECT_STATE_archive_pre-S76.md`.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** + Sentinel/Sherpa DRY_RUN. Restart S76 2026-05-14 13:35 UTC (post-75c). PID orchestrator **87923** + 5 figli. Brain TF off. Mac Mini su `b2ae5f7`.
- **Go/no-go €100 LIVE**: **target fine giugno / inizio luglio 2026** (POSTICIPATO dalla decisione S76 CEO da 18-21 maggio). Gate canonical state già chiuse post-S74b, MA la nuova roadmap Sentinel-first aggiunge step intermedi: Sentinel Sprint 1 fix + Sprint 2 build + osservazione 1 settimana + Sherpa LIVE testnet graduale (un parametro alla volta) → solo dopo mainnet €100.
- **Sequenza S76+**: PROJECT_STATE + BUSINESS_STATE refresh shipped → **prossima sessione CC: Sentinel Sprint 1 audit + fix** (verifica empirica 3 bug noti, dashboard /admin disponibile per osservazione live).
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Tutti allineati su commit `b2ae5f7`.
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, sell_pct net-of-fees S70 ✅, post-fill warning slippage S70 ✅, wallet reconciliation Binance S70 ✅, Sentinel ricalibrazione S70 ✅, Fee Unification S72 ✅, dead zone S73 ✅, partial fills S74c ✅, dashboard coherence S74b ✅, stop_buy_unlock_hours S76 ✅, idle alert suppression S76 ✅, slippage_buffer parametrico (🔲 brief separato).

## 8. Cosa NON è stato fatto e perché

- **slippage_buffer parametrico per coin**: brief separato pre-mainnet, serve calibrare valori con dati reali (BONK testnet vs mainnet).
- **Rule-aware Sherpa sull'hotfix slippage**: Sherpa è in DRY_RUN, niente impatto immediato; brief separato pre-SHERPA_MODE=live.
- **Reason bugiardo** (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa `reason` del trade resta scritta con dicitura "above avg" anche su fill < avg. Cosmetico.
- **`exchange_order_id=null` sul sell OP**: debt cosmetico tracciato post-go-live. Reconciliation S70 Step A gestisce con fallback timestamp.
- **TF riacceso**: coerente con pivot Board "minimum viable, solo Grid + Sentinel/Sherpa DRY_RUN".
- **UI countdown timer per `stop_buy_activated_at`** (es. "BLOCKED · resets in Xh Ym"): dato esposto in `bot_runtime_state`, ma frontend non lo consuma ancora. Brief separato ~30 min.

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings + Report |
|------|------|-------|----------|-------------------|
| 2026-05-15 | 3 | **S78** brief 78a — primo blog post publish | SHIPPED + BUILD VERDE + DEPLOY VERCEL | `an-ai-that-cant-trade.md` (dual-voice origin story Max + BagHolderAI CEO, 7635 byte, 76 sessioni counter, tag origin/introduction/behind-the-scenes, CTA Volume 1) copiato in `web_astro/src/content/blog/`. Frontmatter conforme schema (type=lesson, volume=1, summary 154/220 char). Build Astro: 12 pagine, route nuova `/blog/an-ai-that-cant-trade/`, card su /blog index, link Payhip Volume 1 (`payhip.com/b/a4yMc`) presente. Zero touch schema/componenti/layout. Brief archiviato `briefresolved.md/brief_78a_blog_post_publish.md` (rinominato per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md`). Staging dir `blog/` rimossa. Commit `18a0362`. Verifica visiva → Max nel browser. |
| 2026-05-14 | 1 | **S77 fase 2+3** Sentinel Sprint 2 slow loop (brief 77b) + restart Mac Mini LIVE | SHIPPED + TEST 85/85 + 5 file nuovi + 2 chirurgici + 0 migration + restart end-to-end VERIFICATO | Slow loop ogni 4h: F&G (free) + CMC global (`CMC_API_KEY` su Mac Mini) → regime detection (5 buckets) → INSERT `sentinel_scores` score_type='slow'. Sherpa legge regime dinamico via `regime_reader.get_current_regime(supabase)` invece di hardcoded "neutral". File: `inputs/alternative_fng.py` 73r, `inputs/cmc_global.py` 87r, `regime_analyzer.py` 136r, `slow_loop.py` 137r, `sherpa/regime_reader.py` 66r. Modifiche chirurgiche: `sentinel/main.py` +31r (counter+chiamata slow_loop), `sherpa/main.py` +5r (1 chiamata regime_reader). Commit `a62e5d5` (msg "s78" è typo, è S77). **Restart fase 3**: pull + kill -TERM 87923 + relaunch caffeinate, nuovo PID 90540 alle 21:46 CET. Primo slow tick 2s dopo start: `regime=fear, fng=34, cmc=ok`. Sherpa transizione neutral→fear visibile 2min dopo (BTC: buy 1.0→1.8, sell 1.5→1.2, idle 1.0→2.0). Pattern modulare anticipativa (lezione S76). Report `report_for_CEO/2026-05-14_s77_sentinel_sprint2_slow_loop_report_for_ceo.md`. Brief archiviato in `briefresolved.md/`. |
| 2026-05-14 | 1 | **S77** Sentinel Sprint 1 audit empirico (brief 77a) | TUTTI PASS + 3 design questions parcheggiate dal CEO | 6.081 fast scan post-70b. (1) SoF firing 2.32% (criterio <10%, era ~30%) ✅. (2) risk_score 5 valori distinti 20/26/32/46/52 (era binario) ✅. (3) opp_score 3 valori 20/25/30 (era morta) ✅ debole. (4) Funding signal 0/6081 firing su 8 soglie — dead-by-design su testnet (range ~10× sotto soglie 70b). (5) Asimmetria risk-opp = SoF (+26 gap quando true, ~0 false). CEO decisioni: NO `speed_of_rise`, accetta funding dead, no tuning opp. Zero codice trading toccato, zero restart. Roadmap.ts Phase 4 + Phase 6 aggiornate. Report `report_for_CEO/2026-05-14_s77_sentinel_sprint1_audit_report_for_ceo.md` + addendum §10. Brief archiviato in `briefresolved.md/`. |
| 2026-05-14 | 1 | **S76** refactor grid_runner package + brief 75b stop_buy_unlock_hours + idle audit + UI | SHIPPED + TEST 29/29 + 3 restart Mac Mini verdi + 2 migration | (1) Monolite 1623 → package 8 moduli. Orchestrator entrypoint preservato. Zero behavior change live (BTC tradato al primo tick). (2) `bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`. Default 0 = 39b preservato. (3) `send_idle_alerts(stop_buy_active=)` — recalibrate interno avviene, Telegram silenziato (verificato SOL/BONK). (4) UI `/grid` Safety. Test +4 (Z/AA/BB stop-buy timer + CC idle). Squash `9ceaa81` + `briefresolved.md/brief_75b_stop_buy_unlock_hours.md` + `report_for_CEO/2026-05-14_s76_*.md`. |
| 2026-05-12 | 1 | **S74b** brief 74c + 74b + 74d | SHIPPED + TEST 25/25 + orphan BONK recovered + 2 migration | 74c partial fills mainnet-gating + orphan BONK 21190 (1.37M / $10.38) recovered. 74b nuova `bot_runtime_state` primitiva canonical (1 riga/symbol, UPSERT ogni tick). 74d `dead_zone_hours` per-coin in `bot_config` CHECK 0..168. Commits `02b030f` + `f278dea` + `5a29075` + `2f67533` + `report_for_CEO/2026-05-12_s74b_*.md`. |
| 2026-05-12 | 1 | **S74** audit respiro + 4 fix (grid IT→EN, Telegram, admin polish, TCC python3.13 FDA) | SHIPPED 5 commit + restart | Tasks brief 74a (no nuova trading logic). TCC python3.13 FDA abilitata manualmente da Max → cron reconcile produzione operativa. Brief 74b/c isolati e poi shippati in S74b. Commits `3f3e349` + `d289a8a` + `93dc00d` + `a4674e6` + `3535184` + `report_for_CEO/2026-05-12_s74_*.md`. |
| 2026-05-12 | 1 | **S73c** BONK lot_size + BTC phantom mainnet-safe | SHIPPED + TEST 22/22 + BONK BUY al primo tentativo | `place_market_buy_base` amount-based + ccxt option `createMarketBuyOrderRequiresPrice=False`. `_phantom_holdings` (boot reconcile) + `managed_holdings` property usata in 9 punti. Test V (raw vs managed). Commits `d10b5ad` + `5061a29`. |
| 2026-05-12 | 1 | **S73b** dust trap hotfix | SHIPPED + TEST 21/21 + BONK sbloccato | Criterio economico `residual_notional<MIN_NOTIONAL` in sell_pipeline + replay state_manager threshold $0.50. Commits `bc39aeb` + `d85f4be`. |
| 2026-05-11 | 1 | **S73** brief 73a Dead Zone recalibrate | SHIPPED + TEST 20/20 + 3 bot sbloccati | Fix in `grid_bot.py:576-647` prima del SELL CHECK. Reset `_last_sell_price=0` + `_pct_last_buy_price=current` quando ladder + idle≥4h. Commit `27c909b`. |
| 2026-05-11 | 1 | **S72** brief 72a Fee Unification + audit visivo Max + canonical refactor + TF removal | SHIPPED 11 commit + TEST 18/18 + 0 ORDER_REJECTED | 3 invariants P1/P2/P3, 18 sell testnet backfillati (Δ −$1.097). 4 superfici frontend unificate via `pnl-canonical.js`. Inline script bypass dashboard.astro fixato. TF rimosso da totali pubblici. Commit `a1ad217` → `e975a71` + `report_for_CEO/2026-05-11_s72_*.md`. |
| 2026-05-11 | 1 | **S71** brief 71a cleanup pending (5 task) | SHIPPED + TEST 15/15 | P&L hero unification (utility `pnl-canonical.ts`), LAST SHOT pre-rounding, reason check_price+slippage, mobile recon table, cron wrapper. 4 commit S71. |
| 2026-05-10 | 1 | **S70 + S70b + S70c** reconciliation Step A/B/C + Sentinel ricalibrazione + sell_pct net-of-fees + sito relaunch | SHIPPED + TEST 15/15 | (S70) reconcile_binance.py 24/24 matched 0 drift; rename `manual→grid` DB + frontend; hotfix BONK sell_pct 2→4; brief 70a sell_pct net-of-fees + sell ladder + post-fill warning; brief 70b Sentinel ladder granulare + sof floor. (S70b) /admin overhaul 8 sezioni + Reconciliation Step B trade-by-trade compare. (S70c) sito relaunch + TestnetBanner + Reconciliation pubblica + TF dottore + roadmap.ts Phase 13. Commits + report `report_for_CEO/2026-05-10_s70c_*.md`. |

> Audit area 0/1 pre-S70 (S67/S68/S69 + Phase 1 split grid_bot.py + Clean Slate Step 0d) preservati in [audits/PROJECT_STATE_archive_pre-S76.md](audits/PROJECT_STATE_archive_pre-S76.md).
