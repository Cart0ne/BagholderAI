# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-18 — **sessione 79 chiusa** (3 brief shipped + 2 restart Mac Mini + drift FIFO sanato + cleanup briefs/reports). Brief 79a idle suppression on capital exhausted SHIPPED + LIVE (verificato 3/3 bot post-restart: BTC $0.12 / SOL $0.03 / BONK $0.00 tutti `Idle recalibrate suppressed`). Brief 79b TF reactivation Tier 1-2 only SHIPPED (no-code, env+DB) + LIVE (`tf_tier3_weight=0` in Supabase, 7 processi Mac Mini, regime fear → 50 scan / 2 BULLISH / 0 allocations). Brief 79c Supabase write-IO reduction SHIPPED (write-on-change + heartbeat 10/10/5 min su sentinel_scores/sherpa_proposals/bot_state_snapshots) + LIVE. Ultimo restart Mac Mini: 2026-05-18 21:49 CET, nuovo PID parent **74280**.

**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

> Storico header sessioni precedenti compattato nelle sezioni §4 Decisioni recenti e §10 Sessioni shipped. Archive narrativo pre-S76 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet — Grid ($500 board) + TF riattivato Tier 1-2 only ($100 budget separato dal pool USDT free $9.481) + Sentinel/Sherpa DRY_RUN con slow loop attivo + write-on-change su 3 tabelle Supabase + sito pubblico online (2 blog post LIVE)**. Mac Mini su `542b190` (PID 74280, restart 2026-05-18 21:49 CET). 7 processi (orchestrator + 3 Grid + TF + Sentinel + Sherpa) + 1 caffeinate. Zero ORDER_REJECTED. Cron reconcile attivo 03:00 Europe/Rome. **Target go-live €100: fine giugno / inizio luglio** (decisione S76 CEO 2026-05-14). Sentinel Sprint 1 chiuso PASS, Sprint 2 slow loop LIVE, osservazione in corso (~step 3 sequenza Sentinel-first).

**Roadmap Sentinel-first (CEO S76, 5 step)**: (1) ~~audit + fix Sentinel Sprint 1~~ ✅ CHIUSO S77 — tutti PASS; (2) ~~build Sprint 2~~ ✅ CHIUSO S77 — slow loop F&G + CMC + regime detection LIVE; (3) **osservazione 5-7 giorni — IN CORSO da 2026-05-14** (~scadenza naturale 21-22 maggio); (4) Sherpa LIVE su testnet 1 parametro alla volta (sell_pct primo); (5) mainnet con sistema rodato. **Aggiornamento S79**: TF riattivato Tier 1-2 only (brief 79b) — non rompe la sequenza Sentinel-first perché TF ↔ Sentinel/Sherpa sono ortogonali (TF gestisce coin selection, Sentinel gestisce regime).

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
audits/                    gitignored — formula_verification_s66 + 2026-05-08_pre-reset-s67/ + PROJECT_STATE_archive.md (growing, append-on-compaction)
tests/                     test_accounting_avg_cost.py **29/29 verdi** (post-S76)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. Telegram alerts: solo Grid trade events; Sentinel+Sherpa silenziati via env (memoria `feedback_no_telegram_alerts`).

## 3. In-flight (settimana 2026-05-11+)

### S79 — Idle suppression + TF reactivation + Supabase write-on-change SHIPPED
- **🟢 Brief 79a — Idle suppression on capital exhausted** (commit `1eff58a`): guard prima dei 2 path idle (Path A re-entry + Path B recalibrate) in [bot/grid/grid_bot.py:909-948](bot/grid/grid_bot.py#L909-L948). Quando `_available_cash() < HardcodedRules.MIN_LAST_SHOT_USD` (5.0$), entrambi i path soppressi: log "Idle {…} suppressed: capital exhausted", `bot_events_log` event `idle_{reentry|recalibrate}_suppressed_no_cash`, `_last_trade_time` avanzato (no spam). Ortogonale a `stop_buy_active` suppression (S76 audit, downstream Telegram). Option A: import `HardcodedRules.MIN_LAST_SHOT_USD` da `config.settings`. Test ee (3 casi: Path A / Path B / regression) verde. Suite 30→31. Live verificato post-restart: BTC $0.12 / SOL $0.03 / BONK $0.00, tutti soppressi.
- **🟢 Brief 79b — TF reactivation Tier 1-2 only** (commit `2abd72e`): NO-CODE (default `ENABLE_TF=true` in [orchestrator.py:41](bot/orchestrator.py#L41)). Modifica DB: `UPDATE trend_config SET tf_tier3_weight = 0` (era 25). Allocator già protetto da `weight_sum<=0 → 100` (no div-by-zero). Zero allocazioni TF/tf_grid attive al restart (restart pulito). Counterfactual_log: 639 storici intatti, retention 14gg in `db_maintenance.py:34`. **Decision delegated rilevata**: `counterfactual.py` non logga regime Sentinel (grep regime/sentinel = vuoto). Non bloccante; brief separato se vorremo correlare counterfactual ↔ regime post-osservazione. Live: TF spawned, regime fear → primo scan 50 coin → 2 BULLISH → 0 allocations (distance filter 12% + RSI 75 blocchi). Comportamento atteso del brief ("worst case TF non trova candidati, produce counterfactual senza rischio").
- **🟢 Brief 79c — Supabase write-on-change + heartbeat** (commit `542b190`): trigger warning email Supabase "Disk IO Budget depleting". 3 file modificati:
  - [bot/sentinel/main.py](bot/sentinel/main.py): fast loop INSERT condizionale su `risk != last_written_risk or opp != last_written_opp or now-last_write_ts >= 600s`. Slow loop NON toccato (240 tick = 4h, 6-7/giorno). Atteso ~1440/giorno → ~144/giorno idle.
  - [bot/sherpa/main.py](bot/sherpa/main.py): aggiunto `heartbeat_due` come 4ª condizione al filtro esistente (`would_have_changed OR stop_buy OR cooldown OR heartbeat_due`). Heartbeat per-symbol 600s. Bootstrap restart consistente (legge last row anche se heartbeat-only). Atteso ~2160/giorno → ~432/giorno idle.
  - [db/snapshot_writer.py](db/snapshot_writer.py): 8 COMPARE_KEYS (escluso `unrealized_pnl` che cambia ad ogni tick con prezzo). Heartbeat 300s. Atteso ~498/giorno → ~100-200/giorno idle.
  - Test 31/31 verdi non-regression. Verifica live primi tick post-restart: sentinel 2 row in 2 min (boot + score change), sherpa 3 row (1/bot heartbeat), snapshot 1 row (BTC primo a cycle 15). Verifica empirica 30 min in cadenza naturale a Max.
- **🟢 PROJECT_STATE drift sanato** (commit `6183980`): bug 🔴 [S70c] `realized_pnl per-trade gross` chiuso post-72a (sell_pipeline.py:409 fa `revenue - cost_basis - fee`); "Strada 2 ~3-4h" → "Verifica identità accounting ~30 min" post-go-live. **FIFO cancellato come canonical**: Max ha confermato 2026-05-18 "FIFO non esiste, exchange non ragiona così". Memorie aggiornate [[project_equity_pnl_vs_fifo]] + [[feedback_one_source_of_truth]] → canonical = avg-cost + Equity P&L broker-comparable.
- **🟢 Cleanup briefs + reports** (commit `11b09e8`): 3 brief shipped → `briefresolved.md/` (78b, 79a, 79b). 4 report CEO consegnati → `report_for_CEO/resolved/` (s76, s77 sprint1, s77 sprint2, s78). `config/` ora contiene solo brief proposti/parcheggiati (77c, DUST, evaluate_trading_skills).
- **🔴 TODO prossima sessione (S80?)** — *catch del Board 2026-05-18 fine S79*: sito pubblico `bagholderai.lol` ha ancora "TF dal dottore" SVG inline su home + badge convalescenza su /dashboard (S70c). TF è LIVE Tier 1-2 dal 2026-05-18. Aggiornare narrativa pubblica → "TF on, no più Tier 3" o equivalente. Apple Note "BagHolderAI — Todo" + memoria `project_site_tf_doctor_stale_after_79b` annotata.

### S78 fase 2 — SWEEP/LAST SHOT slippage buffer + banner fix
- **🟢 Brief 78b — SWEEP/LAST SHOT slippage buffer**: 4 file modificati (`config/settings.py` +9r `SLIPPAGE_BUFFER_PCT=0.03`, `bot/grid/buy_pipeline.py` +6/-4r applicazione buffer in SWEEP+LAST SHOT, `web_astro/public/grid.html` +5/-1r banner `<= 0` + branch `< 0` "swept, $X over by slippage", `tests/test_sweep_slippage_buffer.py` 4 scenari). Test verdi: 4/4 nuovi + 30/30 non-regression accounting. Sync su Archivio per pytest (poi sovrascritto da pull al restart). Brief tracked in `config/brief_78b_sweep_slippage_buffer.md`.
- **🟢 Diagnosi BONK trade 2026-05-15 05:39:17**: cum_invested $335.11, cum_received $233.37, cum_skim $2.60 → cash_before skim-aware $45.66. Path SWEEP (remaining_after $20.66 < $25 standard). `cost = $45.66` → base_order 6.8M BONK → fill $0.00000679 (slippage +1.19% da check 0.00000671) → `res["cost"] = $46.10`. Drift singolo trade +$0.44 over cassa attesa. **By design su testnet** (regola Board: no cash morto), ma rischia REJECT -2010 INSUFFICIENT_FUNDS in mainnet. Calibrato 3% uniforme (BONK testnet 2.46%) — per-coin scartato perché mainnet coin mix non ancora deciso.
- **🟢 Pubblicazione blog post 2 "The Day Our Bot Ran Out of Money"** (commit `dcc4372`): preparato Max in `blog/`, copiato in `web_astro/src/content/blog/` con `draft: false`. **Bug fix collateral**: `.gitignore` regola bare `blog/` matchava ricorsivamente anche `web_astro/src/content/blog/` → fix anchored `/blog/`. I 2 post precedenti erano nel repo solo perché aggiunti prima della regola gitignore (2026-05-15).
- **🔴 Restart Mac Mini LIVE 2026-05-16 21:46 CET, nuovo PID parent 33579 Max**: decide quando applicare 79a (orchestrator graceful kill + relaunch).

### S78 — Primo blog post LIVE
- **🟢 Brief 78a — Blog post publish**: file `an-ai-that-cant-trade.md` (dual-voice origin story Max + BagHolderAI CEO, 76 sessioni-counter, 7635 byte) copiato in `web_astro/src/content/blog/`. Frontmatter conforme schema content collection (type=lesson, volume=1, draft=false, date 2026-05-15, summary 154 char < 220 limit, tags origin/introduction/behind-the-scenes). Build Astro verde: 12 pagine, route nuova `/blog/an-ai-that-cant-trade/`, card su `/blog` index, CTA `payhip.com/b/a4yMc` Volume 1 presente. Zero modifica a schema/componenti/layout (vincolo brief rispettato). Commit `18a0362` + push → Vercel auto-deploy. Brief archiviato in `briefresolved.md/brief_78a_blog_post_publish.md` (rinominato da 77b per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md`). Staging dir `blog/` (untracked) rimossa.
- **Verifica visiva live**: spetta a Max (memoria `feedback_no_screenshots`). URL: `bagholderai.lol/blog/an-ai-that-cant-trade`.

### Storico in-flight pre-S79
Sintesi delle sessioni shipped vive in §10. Dettagli narrativi spostati per contenere file <40KB.
- **S78 fase 1** (2026-05-15): blog post 1 LIVE, audit Area 3, GSC fix, X reply strategy.
- **S77** (2026-05-14): Sentinel Sprint 1 audit PASS + Sprint 2 slow loop build + restart end-to-end. Test 37→85.
- **S76** (2026-05-14): refactor grid_runner package 1623→8 moduli + brief 75b timer + audit idle + UI.
- **S75/S74b/S74/S73/S72/S71/S70**: vedi §10 Sessioni shipped.

### Aperti / TODO
- **🟡 [S72] Telegram messages post-72a focus**: la riga "Have SOL: $547.23 → Sell $19.94" mostra TOTALE wallet inclusi phantom testnet. Funzionalmente OK, narrativamente confonde. Fix cosmetico (mostrare wallet vs grid-owned, o eliminare riga). Vincolo Max: non toccare canonical computeCanonicalState.
- **🟡 [S72] Code debt: `buildSection` morto in dashboard-live.ts**: ~10 min cleanup post-go-live.
- **🟡 [S70c] Sito mobile review approfondito**: smoke iPhone fatto, test su device reale richiede Max sul telefono.
- **🟡 [S70c → S78] Verifica identità accounting** (residuo Strada 2): ~30 min. Check empirico Realized + Unrealized = Equity P&L (cash_delta + Σ holdings × spot) sul dataset live, post-go-live €100. Componenti originali "Strada 2" già chiusi: fee_usdt sottratta in 72a (`sell_pipeline.py:409`); "cambio formula avg_buy_price → FIFO" cancellato (FIFO è finzione contabile, non esiste su exchange — bot usa avg-cost coerente con Binance reality); backfill DB pre-72a (~$0.47 testnet) trascurabile su capitale paper ("story is process not numbers").
- **🟡 [S70] Sherpa rule-aware sell_pct**: in DRY_RUN propone sell_pct=1.5 per BONK ignorando hotfix slippage. Pre-SHERPA_MODE=live, rule engine deve preservare buffer per coin.
- **🟡 [S70/S78 fase 2] sell_pct + slippage_buffer parametrico per coin**: S78 fase 2 ha introdotto `SLIPPAGE_BUFFER_PCT=0.03` uniforme in `HardcodedRules` (mirato a SWEEP/LAST SHOT, no `sell_pct` ancora). Estensione futura post-mainnet: parametrizzare per-coin in `bot_config` quando avremo dati slippage reali e mix coin definito.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A.

## 4. Decisioni recenti

- **2026-05-18 (S79 chiusura, 5 commit `6183980` → `542b190`) — 3 brief shipped + drift FIFO sanato + cleanup**. (a) **Brief 79a idle suppression**: guard chirurgico in `grid_bot.py` (`elif` chain pulito, no refactor logica), Option A import `HardcodedRules.MIN_LAST_SHOT_USD` per coerenza con `grid_runner._capital_exhausted` e `buy_pipeline`. (b) **Brief 79b TF reactivation no-code**: scoperto che `ENABLE_TF` ha default `true`, basta togliere `ENABLE_TF=false` dall'env line al restart. Modifica DB unica: `tf_tier3_weight=0`. Allocator già robusto (`weight_sum<=0 → 100`). Decisione delegata: counterfactual.py non logga regime → segnalato, non bloccante. (c) **Brief 79c write-on-change**: 3 file con stesso pattern (cache last-written + heartbeat); `unrealized_pnl` ESCLUSO dal compare snapshot (cambierebbe ogni tick neutralizzando il filtro, MtM resta catturato a ogni heartbeat). Heartbeat 10/10/5 min come da brief. (d) **Drift FIFO**: Max ha smentito frame FIFO che CC aveva ereditato da memorie 13-14gg vecchie ("FIFO non esiste su exchange"). Sanate PROJECT_STATE.md §5/§3/§6 + memorie. (e) **Cleanup briefs/reports** in chiusura. 2 restart Mac Mini stessa sessione (post-79a/79b + post-79c), strategia "raggruppa restart" per ridurre interruzioni live. — *why:* sessione produttiva grazie a brief auto-contenuti del CEO + dipendenze ortogonali (79a/79b/79c non si toccano). Drift FIFO emerso per fortuna durante spiegazione di un bug stale, importante essere stati flaggati invece di committare codice basato su frame stale.

- **2026-05-16 (S78 fase 2, brief 78b — SWEEP/LAST SHOT slippage buffer) — `SLIPPAGE_BUFFER_PCT = 0.03` uniforme in HardcodedRules, applicato a SWEEP + LAST SHOT cost**. Diagnosi profonda ha smentito 2 ipotesi: (1) bot guard skim-aware mancante (esiste già in `_available_cash` L218-221); (2) drift inventory BONK come root cause (trascurabile, riguarda fantasma testnet S72). Root cause vera: base_order su `cost=cash_before` esegue con slippage positivo Binance → `res["cost"]` reale > cash_before. By design su testnet (regola Board "no cash morto") ma mainnet rifiuta -2010 INSUFFICIENT_FUNDS. Buffer 3% fisso scelto su per-coin parametrizzato perché mainnet coin mix non ancora deciso (premature optimization). Banner `<= 0` corretto (con testo "swept, $X over by slippage" per buysLeft<0) come conseguenza fisiologica del SWEEP+slippage, non patch — la "scorciatoia" inizialmente respinta era in realtà la fix giusta una volta capito che SWEEP è by design. Test 4/4 nuovi + 30/30 non-regression. Restart Mac Mini LIVE 2026-05-16 21:46 CET, nuovo PID parent 33579 decisione Max. — *why:* pre-go-live €100 gate: evitare REJECT sistematico su mainnet quando Binance verifica USDT free prima del fill. Approccio data-first (memoria `feedback_data_first_then_review`): 3% testnet ora, ricalibrare con dati mainnet reali quando saranno disponibili.

- **2026-05-16 (S78 fase 2, fix collaterale `.gitignore`) — Regola bare `blog/` → anchored `/blog/`**. Pubblicando il blog post 2 ("The Day Our Bot Ran Out of Money", commit `dcc4372`), scoperto che la regola gitignore bare matchava ricorsivamente anche `web_astro/src/content/blog/`, droppando silenziosamente i nuovi post dai commit. I 2 post precedenti erano nel repo solo per timing (aggiunti prima del gitignore 2026-05-15). Fix anchored a root: ignora solo l'inbox CEO→CC, non il content collection. Bundled nello stesso commit della pubblicazione perché senza fix il commit sarebbe stato silenziosamente vuoto. — *why:* root cause structural; senza fix ogni futuro blog publish sarebbe stato un no-op silenzioso.

- **2026-05-15 (S78, brief 78a — primo blog post LIVE) — Pubblicazione anticipata dal weekend 17-18 maggio**. Brief operativo CC, no codice trading: copia file in content collection + build verde + commit + push. Naming rinominato `brief_77b_blog_post_publish.md` → `brief_78a_blog_post_publish.md` per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md` già archiviato. Decisione minore (autonoma CC). Commit `18a0362`. — *why:* il post era già scritto e approvato dal Board, l'anticipazione libera il weekend per il Post 2 strategico ("why we're not live yet"); BUSINESS_STATE §2 aggiornato di conseguenza.

> Decisioni S77 e precedenti spostate fuori dalla tabella (storico in §10 + commit log). Archive pre-S76 narrativo: [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

## 5. Bug noti

### 🔴 Aperti
- ~~**🔴 [S70c]** `realized_pnl` per-trade gross~~ → **CHIUSO in S72 brief 72a** (commit `a1ad217`...`e975a71`, 2026-05-11). Oggi `sell_pipeline.py:409` fa `revenue - cost_basis - fee` (netto). Residuo cosmetico: righe DB pre-2026-05-11 ancora con valore gross (~$0.47 testnet drift cumulato), non vale backfill su capitale paper.
- **🔴 [S67]** `exchange_order_id=null` su sell OP/USDT — fallback timestamp gestisce reconciliation, ma debt cosmetico.

### 🟡 Aperti
- **🟡 [S67]** Slippage testnet variabile (2.46% BONK osservato) — gestito con sell_pct buffer per ora. Brief `slippage_buffer parametrico per coin`.
- **🟡 [S69]** 2 BONK sells fossili pre-S68a con `buy_trade_id NULL` — restano in DB ma niente più check li flagga.
- **🟡 [S70]** Sherpa propone abbassare BONK sell_pct 4→1.5 in DRY_RUN (ignora hotfix slippage). Pre-SHERPA_MODE=live, rule engine deve preservare buffer per-coin.
- **🟡 [S70]** LAST SHOT path bypassa lot_step_size rounding. Cosmetico (1 Telegram + 1 ORDER_REJECTED warn), ma pre-mainnet vale arrotondare anche nel path LAST SHOT.
- **🟡 [S70 PARZIALE]** Reason bugiardo su slippage: post-fill warning rende slippage visibile in `bot_events_log`, ma stringa `reason` del trade resta sbagliata. Cosmetico.
- **TF distance filter 12% fisso vs EMA20** (CEO 2026-05-07): cross-tema Sentinel/Sherpa, post-go-live.

### 🟢 Risolti recenti (sintesi)
- **S79**: 79a idle suppression on capital exhausted; 79b TF Tier 1-2 reactivation; 79c Supabase write-on-change + heartbeat; drift FIFO sanato (bug [S70c] chiuso post-72a).
- **S78**: blog post 1 + 2 LIVE; 78b SWEEP slippage buffer 3%; gitignore anchored.
- **S77**: Sentinel Sprint 1 audit (tutti PASS); Sprint 2 slow loop F&G + CMC + regime detection (test 37→85 verdi).
- **S76**: grid_runner monolite split in package (squash `9ceaa81`); brief 75b stop_buy_unlock_hours timer; audit idle suppression.
- **S74b**: 74c partial fills (mainnet-gating), 74b stop-buy badge + trigger drift via `bot_runtime_state`, 74d DEAD_ZONE_HOURS per-coin.
- **S73**: 73c BONK lot_size + BTC phantom mainnet-safe; 73b dust trap (criterio economico residual_notional); 73a dead zone recalibrate (BTC/SOL/BONK sbloccati 19-21h).
- **S72**: brief 72a Fee Unification (BONK InsufficientFunds + holdings drift + realized_pnl gross + avg gross tutti chiusi). Backfill 18 sell testnet.
- **S71**: mobile recon table overflow, LAST SHOT BUY rejected -2010, reason bugiardo su slippage (suffix added), drift numerico home/dashboard/grid.html.
- **S70**: sell-at-loss BONK (slippage 2.46%), Sentinel risk binario 20/40 (ladder granulare), Open question 19 rename `manual→grid`.

## 6. Domande aperte per CEO

- 🆕 **[S79 NEW] Sito pubblico TF dal dottore → TF on Tier 1-2**: home + /dashboard ancora mostrano "TF dal dottore" SVG/badge da S70c. TF riattivato in S79 brief 79b. Aggiornare narrativa pubblica. Apple Note "BagHolderAI — Todo" + memoria `project_site_tf_doctor_stale_after_79b`. ~30-45 min, sessione 80.
- 🆕 **[S74 NEW] Buy trigger anchor: A=last_buy / B=avg_buy / C=hybrid**: bot ancora a `last_buy_price`. User mental model "DCA below avg" si aspetta avg. Simulazione 4-buy in downtrend: A spread 10%, B compresso 5%. Proposta CC: opzione C ibrida `max(avg × (1−buy_pct), last_buy × (1−min_gap))`. Riguarda trading logic, brief dedicato.
- 🟡 **[S70c → S78] Verifica identità accounting** (residuo Strada 2): post-go-live €100, ~30 min. Componenti originali chiusi (vedi §3 in-flight). FIFO superato: bot usa avg-cost coerente con exchange reality.
- 🟡 **[S70c] Ripristino sito pubblico**: brief CEO necessario (post-S70c, cross-fertilization /admin pattern).
- 🟡 **[S70] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a pre-mainnet.
- 🟡 **[S70] Sherpa rule-aware sull'hotfix slippage**: prima di SHERPA_MODE=live.
- 🟡 **[S70] Sentinel/Sherpa TELEGRAM flag**: default off; Max abilita quando vuole.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.

> Domande risolte S70-S76: chiuse nelle voci §3 In-flight e §10 Sessioni shipped. Storico completo nei commit log e in `audits/PROJECT_STATE_archive.md`.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** + Sentinel/Sherpa DRY_RUN + **TF Tier 1-2 LIVE** (da S79, T3 weight=0). Restart S79 2026-05-18 21:49 CET. PID orchestrator **74280** + 7 figli (caffeinate incluso). Mac Mini su `542b190`.
- **Go/no-go €100 LIVE**: **target fine giugno / inizio luglio 2026** (decisione S76 CEO). Sequenza Sentinel-first non rotta da S79: TF e Sentinel sono ortogonali.
- **Sequenza S79+ → S80**: osservazione Sentinel Sprint 2 in corso (scadenza naturale ~21-22 maggio) + osservazione TF Tier 1-2 (counterfactual + allocations in regime fear). Prossima sessione CC: aggiornare sito pubblico narrativa "TF dal dottore" → "TF on, no Tier 3" (catch Board S79).
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Tutti allineati su commit `542b190`.
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, FIFO contabile via S69 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, sell_pct net-of-fees S70 ✅, post-fill warning slippage S70 ✅, wallet reconciliation Binance S70 ✅, Sentinel ricalibrazione S70 ✅, Fee Unification S72 ✅, dead zone S73 ✅, partial fills S74c ✅, dashboard coherence S74b ✅, stop_buy_unlock_hours S76 ✅, idle alert suppression S76 ✅, slippage_buffer parametrico (🔲 brief separato).

## 8. Cosa NON è stato fatto e perché

- **slippage_buffer parametrico per coin**: brief separato pre-mainnet, serve calibrare valori con dati reali (BONK testnet vs mainnet).
- **Rule-aware Sherpa sull'hotfix slippage**: Sherpa è in DRY_RUN, niente impatto immediato; brief separato pre-SHERPA_MODE=live.
- **Reason bugiardo** (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa `reason` del trade resta scritta con dicitura "above avg" anche su fill < avg. Cosmetico.
- **`exchange_order_id=null` sul sell OP**: debt cosmetico tracciato post-go-live. Reconciliation S70 Step A gestisce con fallback timestamp.
- ~~**TF riacceso**~~ → **RIATTIVATO IN S79** (brief 79b 2026-05-18): Tier 1-2 only, T3 weight=0 in DB. $100 budget separato da $500 Grid, prende da pool USDT free Binance testnet ($9.481 disponibili). Sito pubblico ancora mostra "TF dal dottore" — da aggiornare.
- **UI countdown timer per `stop_buy_activated_at`** (es. "BLOCKED · resets in Xh Ym"): dato esposto in `bot_runtime_state`, ma frontend non lo consuma ancora. Brief separato ~30 min.

## 9. Audit esterni (sintesi)

**Criterio di ammissione (regola formalizzata 2026-05-15, vedi `CLAUDE.md §[1]`)**: una riga §9 esiste SOLO se la sessione era un Auditor (CC fresh con brief `audits/audit_request_YYYYMMDD_topic.md`) e ha prodotto un file `audits/audit_report_YYYYMMDD_topic.md`. Sessioni di sviluppo (SHIPPED + commit + restart bot) NON vanno qui — vanno in §10.

| Data | Area | Topic | Verdetto | Findings + Report |
|------|------|-------|----------|-------------------|
| 2026-05-15 | 3 | **A3-S78** marketing + SEO/GSC + X performance audit pre-go-live (primo audit Area 3 mai eseguito) | **CON RISERVE** | **GSC**: 4 sitemap "Impossibile recuperare" da aprile = cached failure GSC, NON server-side (verificato: tutti 200 + `application/xml` + cache HIT + Googlebot UA OK + TLS valido + sitemap content valido 12 URL + zero noindex sulle pagine pubbliche). Fix 5min zero-codice: remove all sitemap in GSC + wait 24-48h + resubmit SOLO `https://bagholderai.lol/sitemap-index.xml`. **X** (55 post 25/03→14/05, 4.297 imp totali): 2 likes + 0 RT in tutto il periodo; trend reach decrescente monotono 108→85→39 imp/post in 7 settimane; top performer = storytelling/reply influencer (375/358/250 imp); flop = technical update senza human angle (post 14/05 = 4 imp). **CTA Volume 1 assenti** nei post recenti + blog post di oggi non ancora promosso. Raccomandazione strutturale: ratio 70/30 storytelling/technical (oggi inverso) + tweet di lancio blog + pinned refresh + 3-5 reply strategiche/giorno. Auditor non strict-fresh (disclaimer §0 nel report). Brief: [audits/audit_request_20260515_marketing_seo_x.md](audits/audit_request_20260515_marketing_seo_x.md). Report: [audits/audit_report_20260515_marketing_seo_x.md](audits/audit_report_20260515_marketing_seo_x.md). |
| 2026-05-07 | 1 | **Phase 1** split grid_bot.py monolite (2242r) → 6 moduli (brief 62a) | APPROVED — zero regressioni | Verbatim diff before/after di ogni funzione spostata (`_execute_buy`, `_execute_percentage_buy`, …): identical (`self.` → `bot.`). 3 raccomandazioni: (1) deploy Phase 1 + monitoring 2h/48h; (2) Phase 2 (62b) può partire dai 7 TODO 62a markers; (3) drift count post-deploy non superi baseline (BONK 21, BTC 12, SOL 37 ultimi 7gg). Report: [audits/audit_report_20260507_phase1_grid_split_review.md](audits/audit_report_20260507_phase1_grid_split_review.md). |

> **Stato cadenze al 2026-05-18** (conteggio sui FILE `audits/audit_report_*.md`, non sulle righe §9):
> - **Area 1**: ultimo audit 2026-05-07 (11 gg fa) — entro cadenza 30gg ✅
> - **Area 2**: mai eseguito — ⚠️ DOVUTO (cadenza 90gg o fine-volume Diary) — flaggato anche in S78 fase 2 senza follow-up
> - **Area 3**: ultimo audit 2026-05-15 (3 gg fa) — pre-go-live ✅ (CON RISERVE — vedi raccomandazioni §5 del report)
>
> Audit area 0/1 pre-S70 (S67/S68/S69 + Clean Slate Step 0d) preservati in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).
>
> **Nota S77 fase 1**: la fase 1 di S77 (Sentinel Sprint 1 audit empirico) ha lavorato audit-style ("zero codice trading toccato") MA è stata eseguita nella stessa sessione che poi ha shippato Sprint 2 (fasi 2+3) — quindi non era CC fresh, conflitto di interessi strutturale. Per la regola §9 non conta come audit; il suo report di fase 1 vive in `report_for_CEO/2026-05-14_s77_sentinel_sprint1_audit_report_for_ceo.md` (report CEO, non audit report). Se servirà ri-validare Sprint 1 con audit vero, aprire CC fresh con `audit_request_YYYYMMDD_sentinel_sprint1.md`.

## 10. Sessioni shipped (storico)

Tabella delle sessioni di sviluppo che hanno chiuso brief CEO con SHIPPED + commit + (eventuale) restart bot. Prima del 2026-05-15 queste righe vivevano (impropriamente) in §9 etichettate come "audit Area 1"; la regola di ammissione §9 le ha spostate qui — il contenuto è invariato.

| Data | Area | Topic | Esito | Sintesi + Report |
|------|------|-------|-------|------------------|
| 2026-05-18 | 1 | **S79** brief 79a idle suppression + 79b TF reactivation Tier 1-2 + 79c Supabase write-on-change + drift FIFO sanato + cleanup | SHIPPED 5 commit + 2 restart Mac Mini + TEST 31/31 + DB modifica `tf_tier3_weight=0` | (79a `1eff58a`) guard in `grid_bot.py` Path A+B su `_available_cash() < HardcodedRules.MIN_LAST_SHOT_USD`. Test ee 3 casi. Live: BTC $0.12 / SOL $0.03 / BONK $0.00 tutti soppressi al primo idle cycle post-restart. (79b `2abd72e`) no-code, `ENABLE_TF` default true, modifica DB `tf_tier3_weight = 0`. Allocator robusto (`weight_sum<=0 → 100`). 7 processi Mac Mini, regime fear → 0 allocations (atteso). (79c `542b190`) write-on-change + heartbeat 10/10/5 min su `sentinel_scores` (fast only) / `sherpa_proposals` / `bot_state_snapshots`. `unrealized_pnl` escluso dal compare snapshot. Atteso 80% riduzione write/giorno idle. Verifica empirica 30 min in cadenza naturale. (drift `6183980`) bug 🔴 [S70c] chiuso post-72a, "Strada 2 ~3-4h" → "~30 min", FIFO cancellato come canonical, memorie aggiornate. (cleanup `11b09e8`) 3 brief → resolved, 4 report CEO → resolved. Restart Mac Mini #1 (post 79a+79b): PID 73667 alle 21:14 CET; restart #2 (post 79c): PID 74280 alle 21:49 CET. |
| 2026-05-16 | 1 | **S78 fase 2** brief 78b — SWEEP/LAST SHOT slippage buffer + banner fix + blog post 2 publish + `.gitignore` anchor | SHIPPED codice + TEST 4/4 nuovi + 30/30 non-regression + RESTART LIVE 21:46 CET (PID 33579) | Diagnosi 3-step ha smentito skim-aware-guard-mancante (esiste già L218-221) + drift inventory BONK come root cause (è fantasma testnet S72 trascurabile). Root cause: SWEEP/LAST SHOT base_order su `cost=cash_before` esegue con slippage positivo Binance → cassa va in -$0.44 sul trade BONK 2026-05-15 05:39:17 (verificato: cash_before $45.66 → `res["cost"]` $46.10). By design testnet (regola Board no cash morto), ma mainnet rifiuta -2010 INSUFFICIENT_FUNDS. Fix: `SLIPPAGE_BUFFER_PCT = 0.03` uniforme in `HardcodedRules`. Banner `<= 0` con testo "swept, $X over by slippage". Brief tracked in `config/brief_78b_sweep_slippage_buffer.md`. Commit `afd97ce`. Inclusi nello stesso commit: fix `.gitignore` blog/ → /blog/ anchored (S78 drift), pubblicazione blog post 2 "The Day Our Bot Ran Out of Money" commit `dcc4372`. |
| 2026-05-15 | 3 | **S78** brief 78a — primo blog post publish | SHIPPED + BUILD VERDE + DEPLOY VERCEL | `an-ai-that-cant-trade.md` (dual-voice origin story Max + BagHolderAI CEO, 7635 byte, 76 sessioni counter, tag origin/introduction/behind-the-scenes, CTA Volume 1) copiato in `web_astro/src/content/blog/`. Frontmatter conforme schema (type=lesson, volume=1, summary 154/220 char). Build Astro: 12 pagine, route nuova `/blog/an-ai-that-cant-trade/`, card su /blog index, link Payhip Volume 1 (`payhip.com/b/a4yMc`) presente. Zero touch schema/componenti/layout. Brief archiviato `briefresolved.md/brief_78a_blog_post_publish.md` (rinominato per evitare collision con `brief_77b_sentinel_sprint2_slow_loop.md`). Staging dir `blog/` rimossa. Commit `18a0362`. Verifica visiva → Max nel browser. |
| 2026-05-14 | 1 | **S77 fase 2+3** Sentinel Sprint 2 slow loop (brief 77b) + restart Mac Mini LIVE | SHIPPED + TEST 85/85 + 5 file nuovi + 2 chirurgici + 0 migration + restart end-to-end VERIFICATO | Slow loop ogni 4h: F&G (free) + CMC global (`CMC_API_KEY` su Mac Mini) → regime detection (5 buckets) → INSERT `sentinel_scores` score_type='slow'. Sherpa legge regime dinamico via `regime_reader.get_current_regime(supabase)` invece di hardcoded "neutral". File: `inputs/alternative_fng.py` 73r, `inputs/cmc_global.py` 87r, `regime_analyzer.py` 136r, `slow_loop.py` 137r, `sherpa/regime_reader.py` 66r. Modifiche chirurgiche: `sentinel/main.py` +31r (counter+chiamata slow_loop), `sherpa/main.py` +5r (1 chiamata regime_reader). Commit `a62e5d5` (msg "s78" è typo, è S77). **Restart fase 3**: pull + kill -TERM 87923 + relaunch caffeinate, nuovo PID 90540 alle 21:46 CET. Primo slow tick 2s dopo start: `regime=fear, fng=34, cmc=ok`. Sherpa transizione neutral→fear visibile 2min dopo (BTC: buy 1.0→1.8, sell 1.5→1.2, idle 1.0→2.0). Pattern modulare anticipativa (lezione S76). Report `report_for_CEO/2026-05-14_s77_sentinel_sprint2_slow_loop_report_for_ceo.md`. Brief archiviato in `briefresolved.md/`. |
| 2026-05-14 | 1 | **S77 fase 1** Sentinel Sprint 1 audit empirico (brief 77a) — *audit-style ma NON Auditor* | TUTTI PASS + 3 design questions parcheggiate dal CEO | 6.081 fast scan post-70b. (1) SoF firing 2.32% (criterio <10%, era ~30%) ✅. (2) risk_score 5 valori distinti 20/26/32/46/52 (era binario) ✅. (3) opp_score 3 valori 20/25/30 (era morta) ✅ debole. (4) Funding signal 0/6081 firing su 8 soglie — dead-by-design su testnet (range ~10× sotto soglie 70b). (5) Asimmetria risk-opp = SoF (+26 gap quando true, ~0 false). CEO decisioni: NO `speed_of_rise`, accetta funding dead, no tuning opp. Zero codice trading toccato in fase 1, MA la stessa sessione ha poi shippato Sprint 2 in fasi 2+3 → non era CC fresh. Roadmap.ts Phase 4 + Phase 6 aggiornate. Report `report_for_CEO/2026-05-14_s77_sentinel_sprint1_audit_report_for_ceo.md` + addendum §10. Brief archiviato in `briefresolved.md/`. |
| 2026-05-14 | 1 | **S76** refactor grid_runner package + brief 75b stop_buy_unlock_hours + idle audit + UI | SHIPPED + TEST 29/29 + 3 restart Mac Mini verdi + 2 migration | (1) Monolite 1623 → package 8 moduli. Orchestrator entrypoint preservato. Zero behavior change live (BTC tradato al primo tick). (2) `bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`. Default 0 = 39b preservato. (3) `send_idle_alerts(stop_buy_active=)` — recalibrate interno avviene, Telegram silenziato (verificato SOL/BONK). (4) UI `/grid` Safety. Test +4 (Z/AA/BB stop-buy timer + CC idle). Squash `9ceaa81` + `briefresolved.md/brief_75b_stop_buy_unlock_hours.md` + `report_for_CEO/2026-05-14_s76_*.md`. |
| 2026-05-12 | 1 | **S74b** brief 74c + 74b + 74d | SHIPPED + TEST 25/25 + orphan BONK recovered + 2 migration | 74c partial fills mainnet-gating + orphan BONK 21190 (1.37M / $10.38) recovered. 74b nuova `bot_runtime_state` primitiva canonical (1 riga/symbol, UPSERT ogni tick). 74d `dead_zone_hours` per-coin in `bot_config` CHECK 0..168. Commits `02b030f` + `f278dea` + `5a29075` + `2f67533` + `report_for_CEO/2026-05-12_s74b_*.md`. |
| 2026-05-12 | 1 | **S74** brief 74a + 4 fix (grid IT→EN, Telegram, admin polish, TCC python3.13 FDA) | SHIPPED 5 commit + restart | Tasks brief 74a (no nuova trading logic). TCC python3.13 FDA abilitata manualmente da Max → cron reconcile produzione operativa. Brief 74b/c isolati e poi shippati in S74b. Commits `3f3e349` + `d289a8a` + `93dc00d` + `a4674e6` + `3535184` + `report_for_CEO/2026-05-12_s74_*.md`. |
| 2026-05-12 | 1 | **S73c** BONK lot_size + BTC phantom mainnet-safe | SHIPPED + TEST 22/22 + BONK BUY al primo tentativo | `place_market_buy_base` amount-based + ccxt option `createMarketBuyOrderRequiresPrice=False`. `_phantom_holdings` (boot reconcile) + `managed_holdings` property usata in 9 punti. Test V (raw vs managed). Commits `d10b5ad` + `5061a29`. |
| 2026-05-12 | 1 | **S73b** dust trap hotfix | SHIPPED + TEST 21/21 + BONK sbloccato | Criterio economico `residual_notional<MIN_NOTIONAL` in sell_pipeline + replay state_manager threshold $0.50. Commits `bc39aeb` + `d85f4be`. |
| 2026-05-11 | 1 | **S73** brief 73a Dead Zone recalibrate | SHIPPED + TEST 20/20 + 3 bot sbloccati | Fix in `grid_bot.py:576-647` prima del SELL CHECK. Reset `_last_sell_price=0` + `_pct_last_buy_price=current` quando ladder + idle≥4h. Commit `27c909b`. |
| 2026-05-11 | 1 | **S72** brief 72a Fee Unification + audit visivo Max + canonical refactor + TF removal | SHIPPED 11 commit + TEST 18/18 + 0 ORDER_REJECTED | 3 invariants P1/P2/P3, 18 sell testnet backfillati (Δ −$1.097). 4 superfici frontend unificate via `pnl-canonical.js`. Inline script bypass dashboard.astro fixato. TF rimosso da totali pubblici. Commit `a1ad217` → `e975a71` + `report_for_CEO/2026-05-11_s72_*.md`. |
| 2026-05-11 | 1 | **S71** brief 71a cleanup pending (5 task) | SHIPPED + TEST 15/15 | P&L hero unification (utility `pnl-canonical.ts`), LAST SHOT pre-rounding, reason check_price+slippage, mobile recon table, cron wrapper. 4 commit S71. |
| 2026-05-10 | 1 | **S70 + S70b + S70c** reconciliation Step A/B/C + Sentinel ricalibrazione + sell_pct net-of-fees + sito relaunch | SHIPPED + TEST 15/15 | (S70) reconcile_binance.py 24/24 matched 0 drift; rename `manual→grid` DB + frontend; hotfix BONK sell_pct 2→4; brief 70a sell_pct net-of-fees + sell ladder + post-fill warning; brief 70b Sentinel ladder granulare + sof floor. (S70b) /admin overhaul 8 sezioni + Reconciliation Step B trade-by-trade compare. (S70c) sito relaunch + TestnetBanner + Reconciliation pubblica + TF dottore + roadmap.ts Phase 13. Commits + report `report_for_CEO/2026-05-10_s70c_*.md`. |
