# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-06-12 (pomeriggio) — **S103a-analisi volume-pnl-correlation CONSEGNATA** (report only: zero codice, zero restart, zero DB write). Verdetto: **volume_24h NON utilizzabile come filtro TF** — pattern esplorazione CEO = artefatto righe ORPHAN (PnL=0 per costruzione, concentrate nei quartili alti); esterno spurio (driver = surge/pump, morto col clustering); letteratura contraria. Candidato **guard anti-surge** parked (§6). Igiene dati: escludere ORPHAN dalle analisi su `trend_decisions_log`. Dettaglio completo §4 + §10. ⚠️ 2° brief "S103a" del giorno (SCOPE diversi, accoppiamento ok). — In mattinata: **S103b SHIPPED + DEPLOY — redesign dashboard**

> Storico header S102/S102b, S101 e precedenti: vedi §10 + [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) (compaction S102 + S103a-analisi).

**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

> Storico header sessioni precedenti compattato nelle sezioni §4 Decisioni recenti e §10 Sessioni shipped. Archive narrativo pre-S76 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet — Grid ($500) + TF Tier 1-2 ($100) + Sentinel slow LIVE + Sherpa LIVE 7/7 parametri (`SHERPA_MODE=live` da S102b; 4 protettivi regime×tier + debounce 24h da S103a) + NewsKeeper v1 standalone + v2 barometro shadow + sito pubblico (8 post, dashboard 5 card live S103b)**. Mac Mini orchestrator: **restart S103a 2026-06-12 13:46 CET (CC), PID 24606, runtime `3d0bdbb`** — takeover S103a verificato a DB; `SHERPA_TELEGRAM_ENABLED=true` temporaneo. 7 processi orchestrator-managed + NewsKeeper v1 (pid 10899) + v2 shadow (pid 97566, NON in Sentinel). Grid su `testnet_2` (clean slate S96a, Day 1 = 2026-06-05). Cron reconcile 03:00 Europe/Rome. **Go-live €100: nessuna data fissa** — gated da condizioni di mercato (bear+bull+lateral, decisione S82). Sequenza: Sherpa LIVE ✅ → osservazione → verdetto barometro (~23 giu) → Board approval → mainnet.

**Roadmap Sentinel-first (CEO S76, 5 step)**: (1) ~~audit + fix Sentinel Sprint 1~~ ✅ CHIUSO S77; (2) ~~build Sprint 2 slow loop~~ ✅ CHIUSO S77; (3) ~~osservazione 5-7 giorni~~ ✅ CHIUSO S80a con Brain Analysis (NO-GO Sherpa step 4, 3 fix architetturali richiesti); **(3.5) Sherpa Sprint 2 rework** ✅ CHIUSO S81 (per-coin volatility + slow-gate + amplitude cap, brief 81a); (4) ~~osservazione Sherpa DRY_RUN + Brain Analysis 2~~ ✅ CHIUSO (Brain Analysis 2 S91 + coherence audit S102); **(5) Sherpa LIVE testnet** ✅ FATTO S102b (2026-06-11, tutti e 3 i parametri insieme — non un parametro alla volta: il cap ±30% rende la transizione comunque graduale; decisione Board S102b); (6) mainnet — gated da osservazione + S103 + barometro verdict + Board approval. **Architecture vision three-phase brain (CEO S81)**: Phase A (questo brief, Sherpa coin-aware) ✅; Phase B (Sentinel coin-aware con EMA/RSI per-coin, Sherpa diventa traduttore score→param); Phase C (Sentinel + sentiment online).

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS, 20 tabelle post-S70 con `reconciliation_runs`), Telegram (alerts), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn 3 Grid + TF + Sentinel + Sherpa via env flags (TF Tier 1-2 LIVE da S79b)
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
  trend_follower/          Brain #4 — TF (LIVE Tier 1-2 only, ENABLE_TF=true, tf_tier3_weight=0, da S79b 2026-05-18)
db/, utils/, scripts/, web_astro/  (DB client, telegram, daily reports, sito Astro maintenance)
  web_astro/public/admin.html   Admin dashboard (auth-gate SHA-256, non indicizzato). Sentinel+Sherpa charts, regime overlay.
  web_astro/public/grid.html    Grid admin panel (auth-gate SHA-256). Config + P&L dettaglio per coin.
  web_astro/public/tf.html      TF admin panel (auth-gate SHA-256). Config + scans + portfolio.
scripts/reconcile_binance.py  S70 Step A: reconciliation Binance ↔ DB trades (cron 03:00 Europe/Rome)
config/                    settings, validation_and_control_system.md; config/parked/ brief parcheggiati con trigger (DUST writeoff + evaluate_trading_skills, vedi README)
audits/                    gitignored — formula_verification_s66 + 2026-05-08_pre-reset-s67/ + PROJECT_STATE_archive.md (growing, append-on-compaction)
tests/                     **195/195 verdi** (S102; 121 S89 → +NewsKeeper v2 S100 +write gate S102); tests/archived/ (legacy + test_trend_36e_v2) escluso via pytest.ini
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. Telegram alerts: solo Grid trade events; Sentinel+Sherpa silenziati via env (memoria `feedback_no_telegram_alerts`).

## 3. In-flight (settimana 2026-05-18+)

### S100 — NewsKeeper v2 «Barometro» (shadow LIVE, in osservazione T+14)
- Package `bot/newskeeper_v2/`, shadow sul Mac Mini (pid 97566) accanto a v1, scrive `newskeeper_signals` (`event_key NOT NULL`) + `newskeeper_regime`. NON cablato in Sentinel. **Check T+36h ✅ OK** (11-giu, routine remota: 203 Haiku, 0 fallback, abstain 0, 1 flip neutral→bearish 10-giu). **Verdetto T+14 ~23 giu** (vedi TODO sotto). Dettaglio archiviato in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). Brief/report in `briefresolved.md/` e `report_for_CEO/resolved/`.

> Voce S99 Passive Income Dashboard (PARKED, resta tracciata in BUSINESS_STATE §5) archiviata in compaction S103a-analisi. Voci §3 di sessioni shipped **S88-S98** (redesign Pastel v2 LIVE 2026-06-04; blog 2-voci + cross-post; pointer S88-S92) archiviate nelle compaction S95b/S99b-b → [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md). Sintesi in §10.

### Aperti / TODO
> TODO ✅ chiusi (S102b restart+GO LIVE, S103a board-params, S103b dashboard, S95 branch orfani) archiviati in compaction S103a-analisi → [archive](audits/PROJECT_STATE_archive.md). Da osservare restano: convergenza buy_pct post-Sherpa-LIVE; `sherpa_proposals` ≤ ~18 righe/gg; lampada STOP BUY viva; togliere `SHERPA_TELEGRAM_ENABLED=true` a un restart futuro.
- 🔔 **[S100] Verdetto barometro T+14 — DOVUTO ~2026-06-23.** Validare i flip di `newskeeper_regime` vs ritorno prezzo BTC 24h (da `sentinel_scores.btc_price` a flip+24h), **NON vs F&G** (circolare). Flip da validare: neutral→bearish 2026-06-10 00:08 UTC. Lente regime: se i 14gg restano solo-bear → verdetto parziale, estendere. Esito: promuovere (cablaggio Sentinel) o bocciare (→ /news, blog "esperimento fallito"). (Check T+36h ✅ chiuso 11-giu: routine remota OK, report `2026-06-11_S100_newskeeper-v2-shadow-check.md`, barometro sano e non-muto.)
- **🟡 [S101 NEW] daily_pnl snapshot day-1 sottostimato (follow-up)**: `total_value` 5-giu=350.63 / 6-giu=476.72 vs ~497 atteso (a fine 5-giu: net invested $496.53 su 18 trade, realized +$0.18 → nessuna perdita reale; il 6-giu "recupera" +$126 con realized −$6.30 = impossibile come mercato). La curva §3 mostra quindi un dip day-1 in parte finto. Pista: snapshot scritto dal PRIMO grid bot al blocco 20:00 (`db/client.py:306`, `ignore_duplicates=True`, mai più aggiornato) che al day-1 post-reset valutava un portafoglio parziale. Da brief: hardening calcolo snapshot + eventuale correzione righe 5-6 giu. Nota correlata: snapshot ≈ ore 20:00 locali, non EOD reale → la card dice "as of <data>". Ricorre a ogni reset mensile testnet.
- **🟡 [S81 NEW] Cap kicks BONK in mainnet**: con `MAX_DELTA_PCT=0.30` Board BONK sell_pct=2.5, Sherpa può proporre max 3.25 in un tick. Pre-mainnet vorremo forse 0.10-0.15 (slippage mainnet 10× più basso). Brief separato pre-mainnet.
- **🟡 [S70→S102b] Sherpa rule-aware sull'hotfix slippage**: il `sell_pct` Sherpa non conosce esplicitamente `SLIPPAGE_BUFFER_PCT`. Su testnet (Sherpa ora LIVE, S102b) è coperto a runtime dall'Adaptive Sell Penalty (S98/S99b) + per-coin scaling Sprint 2; resta un follow-up esplicito pre-mainnet.
- **🟡 [S70/S78 fase 2] sell_pct + slippage_buffer parametrico per coin**: estensione post-mainnet, parametrizzare per-coin in `bot_config` con dati slippage reali.
- **🟡 [S72] Telegram messages post-72a**: "Have SOL: $547 → Sell $19.94" mostra TOTALE wallet inclusi phantom testnet. Cosmetico. Vincolo Max: non toccare canonical computeCanonicalState.
- **🟡 [S72] Code debt: `buildSection` morto in dashboard-live.ts**: ~10 min cleanup post-go-live.
- **🟡 [S70c] Sito mobile review approfondito**: smoke iPhone fatto, test su device reale richiede Max sul telefono.
- **🟡 [S70c → S78] Verifica identità accounting** (residuo Strada 2): ~30 min check empirico Realized + Unrealized = Equity P&L, post-go-live €100.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A.

## 4. Decisioni recenti

- **2026-06-12 (S103a-analisi) — Verdetto volume↔PnL: nessun filtro volume per il TF; esclusione righe ORPHAN dal campione inferenziale; validazione esterna via Binance public API**.
  DECISIONE: (D1) le 32 righe `ORPHAN_PERIOD_CLOSE` (su 51 coppie) escluse dall'inferenza — 29 hanno PnL=0 per costruzione (timestamp exit ≈ entry) e si concentrano nei quartili di volume alto (Spearman +0.46, p=0.0007): il pattern dell'esplorazione CEO era composizione del campione. (D2) validazione esterna su Binance public API (no key → nessuna richiesta a Max necessaria) invece di CoinGecko/CMC. (D3) proxy segnale = golden cross EMA20/50 daily, dichiarato come proxy. (D4) robustezza pre-consegna: il gradiente raw esterno (p=0.0004) è spurio — driver = surge di volume (pump), morto con clustering mensile (p=0.82).
  RAZIONALE: tre livelli di evidenza convergono sul NO (interno artefatto, esterno spurio, letteratura contraria al momentum-su-illiquide). FALLBACK: `pairs.csv` con flag `is_orphan` + script riproducibili negli assets — ogni scelta reversibile. Report `2026-06-12_S103a_RforCEO_volume-pnl-correlation.md`. §7 anti-assenso: obiezione "tier=f(volume) per costruzione" dichiarata pre-analisi.

- **2026-06-12 (S103b) — redesign dashboard: admin a 3 gruppi (ownership) + §2 pubblica a 5 card live in pipeline**.
  DECISIONE: (D1) PART 1 su `grid.html` (non `admin.html` come da brief — lì non c'è editor) — già a gruppi, delta = Min Profit→Security + label ownership (Trading=Board, Grid+Security=Sherpa post-S103a). (D2) PART 2 `/dashboard` §2: 5 card statiche → righe live (TF→Grid + NK→Sentinel→Sherpa), riuso `computeCanonicalState` per i trader (id invariati, zero rischio), rail brain nuovi, sparkline 7g da `daily_pnl`, polling 5min, `<style is:global>` mappato ai token. (D3) 3 query brain del brief corrette vs schema reale (barometro=`newskeeper_regime.state`, headlines=`summary`+`polarity`, sentinel btc/funding=colonne fast + regime/fng=raw_signals slow). (D4 — deviazione autorizzata Max) migration RLS read-only `s103b_newskeeper_regime_anon_read` perché il barometro era morto sul sito (tabella non anon-readable come le sorelle).
  RAZIONALE: design handoff Claude Design ad alta fedeltà; ownership coerente con S103a; dati reali verificati con query anon in review locale prima del deploy.
  ALTERNATIVE: barometro client-side (approssimato) o "—" onesto (scartate, Max ha scelto la lettura pubblica). FALLBACK: revert `638d1e4`/`0d6e1a0`; droppare la policy RLS. Report `report_for_CEO/2026-06-12_S103b_RforCEO_dashboard-brain-cards.md`. §7: 3 drift brief segnalati/corretti (file PART 1, query schema, ownership label).

- **2026-06-12 (S103a) — i 4 parametri protettivi → Sherpa-managed (regime×tier) + debounce 24h (oltre il brief)**.
  DECISIONE: (D1) i 4 freni (`stop_buy_drawdown_pct`, `stop_buy_unlock_hours`, `dead_zone_hours`, `profit_target_pct`) passano da Board-only/statici a Sherpa-managed su `BOARD_TABLE[regime][tier]` (5×3, valori del brief; tier dal volatility multiplier, confini 1.30/1.65 in settings; nessun cap/clamp — interi). **Ribalta la decisione specifica S102** ("statici, Sicurezza ≠ strategia") ma **rispetta il principio ownership S102** (Board=soldi: allocation/$-trade/skim; Sherpa=resto) — flag bloccante §7 segnalato a Max pre-codice, Max (veto) ha confermato il ribaltamento. (D2) **Debounce 24h NON nel brief** (direttiva Board/Max dopo obiezione tecnica CC sul tier-flapping): una coppia (regime,tier) dev'essere stabile 24h prima di scrivere; copre con una regola sia il flapping tier (multiplier orario) sia regime (F&G sul bordo banda); coin nuova = subito; stato in `sherpa_board_state` (sopravvive ai riavvii). (D3) colonna DB `profit_target` non `min_profit_pct` (nome reale `bot_config`).
  RAZIONALE: testnet = zero rischio, go-live mainnet gated a parte. Senza cap i freni interi flapperebbero secchi sul confine; il dwell sul valore risolto lo impedisce, al costo di ~24h di ritardo sulle reazioni giuste (lato prudente, accettabile su un freno).
  ALTERNATIVE: tenere S102 (statici); solo `stop_buy_dd` regime-aware (via di mezzo CC); banda morta stateless (non copre il regime); congelare tier all'ingresso (no auto-adattamento, che Max voleva). FALLBACK: revert `a1826fe` + togliere i 4 dalla whitelist `config_writer` = ricongelati Board-only; `BOARD_DEBOUNCE_HOURS` in settings; svuotare `sherpa_board_state` = riparte da prima classificazione. Report `report_for_CEO/2026-06-12_S103a_RforCEO_sherpa-board-params.md`. §7 anti-assenso: 1 flag bloccante (drift S102) + 1 obiezione tecnica (tier-flapping), entrambi risolti con Max prima del codice.

- **2026-06-11 (S102b+S102)** — sintesi: Sherpa GO LIVE testnet via env flag `SHERPA_MODE=live` (default dry_run intatto — ogni restart futuro DEVE includere il flag o torna dry_run in silenzio) + battito liveness ~18 righe/gg + write gate flip-based (correzione filtro 79c, non filtro nuovo) + heartbeat 4h. Telegram Sherpa ON temporaneo. Testo integrale (DECISIONE/RAZIONALE/ALTERNATIVE/FALLBACK) archiviato in compaction S103a-analisi → [archive](audits/PROJECT_STATE_archive.md). Report S102/S102b in `report_for_CEO/`.

> Decisioni **S101/S101b/S100/S99b-b** archiviate in compaction S103a-analisi; **S99a/S98** in compaction S102; **S97c/S97b/S96a/S95a/S91** in compaction S99b-b → [archive](audits/PROJECT_STATE_archive.md). Sintesi §10. Decisioni S81→S84 e precedenti: §10 + commit log + archive (compaction S83/S86).

## 5. Bug noti

### 🔴 Aperti
- ~~**🔴 [S70c]** `realized_pnl` per-trade gross~~ → **CHIUSO in S72 brief 72a** (commit `a1ad217`...`e975a71`, 2026-05-11). Oggi `sell_pipeline.py:409` fa `revenue - cost_basis - fee` (netto). Residuo cosmetico: righe DB pre-2026-05-11 ancora con valore gross (~$0.47 testnet drift cumulato), non vale backfill su capitale paper.

### 🟡 Aperti
- **🟡 [S67]** Slippage testnet variabile (2.46% BONK osservato) — gestito con sell_pct buffer per ora. Brief `slippage_buffer parametrico per coin`.
- **🟡 [S69]** 2 BONK sells fossili pre-S68a con `buy_trade_id NULL` — restano in DB ma niente più check li flagga.
- **🟡 [S70]** Sherpa propone abbassare BONK sell_pct 4→1.5 in DRY_RUN (ignora hotfix slippage). Pre-SHERPA_MODE=live, rule engine deve preservare buffer per-coin.
- **🟡 [S70]** LAST SHOT path bypassa lot_step_size rounding. Cosmetico (1 Telegram + 1 ORDER_REJECTED warn), ma pre-mainnet vale arrotondare anche nel path LAST SHOT.
- **🟡 [S70 PARZIALE]** Reason bugiardo su slippage: post-fill warning rende slippage visibile in `bot_events_log`, ma stringa `reason` del trade resta sbagliata. Cosmetico.
- **TF distance filter 12% fisso vs EMA20** (CEO 2026-05-07): cross-tema Sentinel/Sherpa, post-go-live.

### 🟢 Risolti recenti (sintesi)
- **S102**: volume `sherpa_proposals` ~2.100 righe/gg — il filtro 79c era bypassato a ogni tick dal pass-through a LIVELLO di `proposed_stop_buy_active` (extreme_fear persistente dal 29 mag) e `cooldown_active`. Fix: gate flip-based + heartbeat 4h (commit `a867179`). ⚠️ DEPLOY PENDING (restart rimandato). Chiarito (no-bug): `btc_price` null = gap integrazione Sprint 2 (slow writer Sentinel); `would_have_changed` 100% = artefatto DRY_RUN.
> Risolti **S101/S99b-b** archiviati in compaction S103a-analisi; **S98a/S97a/S96b/S96a/S81/S79** in compaction S102 → [archive](audits/PROJECT_STATE_archive.md).

## 6. Domande aperte per CEO

- 🆕 **[S103a-analisi] Guard anti-surge sul TF** (eventuale, post-verdetto barometro): unico candidato sopravvissuto all'analisi volume↔PnL — sopprimere/penalizzare ALLOCATE quando `vol_7g / mediana(vol_90g)` supera ~2-3× (il cross sta cavalcando un pump → mean reversion). Evidenza: +5.72 p.p./mese, positivo 6/8 mesi, **p=0.092 → sotto soglia, NON implementare**; ri-testare con più dati prima di qualunque brief. Dettagli report S103a volume-pnl §3.2/§5.
- 🆕 **[S102] Gate pre-LIVE: `idle_reentry_hours` 8 (bot_config) vs range design/clamp Sherpa 0.5–6**: in LIVE Sherpa riporterebbe idle ai valori di design in 2-7 tick, annullando la scelta operativa del Board. Opzioni: (A) alzare il clamp ≥8; (B) togliere idle dalla whitelist; (C) accettare il rientro nel range. Da decidere PRIMA di `SHERPA_MODE=live`. (Report S102 §B3.)
- 🆕 **[S102] btc_price null su sherpa_proposals**: micro-brief ~3 righe (fetch diretto in Sherpa, pattern symbol_price) oppure accettare il fallback klines per il replay. + owner unico del dominio circuit-breaker (soglia Board / flag Sherpa / auto-unlock grid non coordinati). (Report S102 §B4/§B3.)
- 🆕 **[S81 NEW] Cap parametrico per mainnet**: `MAX_DELTA_PCT=0.30` calibrato per testnet (slippage volatile). Pre-mainnet probabilmente vorremo 0.10-0.15. Brief separato pre-step 5.
- 🆕 **[S81 NEW] Sentinel Phase B (coin-aware EMA/RSI per-coin)**: secondo step three-phase brain architecture. Sentinel computa metriche per ogni active coin → Sherpa diventa traduttore score→param (no più volatility.py interno). Brief separato post Brain Analysis 2.
- 🆕 **[S74 NEW] Buy trigger anchor: A=last_buy / B=avg_buy / C=hybrid**: bot ancora a `last_buy_price`. User mental model "DCA below avg" si aspetta avg. Simulazione 4-buy in downtrend: A spread 10%, B compresso 5%. Proposta CC: opzione C ibrida `max(avg × (1−buy_pct), last_buy × (1−min_gap))`. Riguarda trading logic, brief dedicato.
- 🟡 **[S70c → S78] Verifica identità accounting** (residuo Strada 2): post-go-live €100, ~30 min. FIFO superato: bot usa avg-cost coerente con exchange reality.
- 🟡 **[S70] sell_pct + slippage_buffer parametrico per coin**: estensione brief 70a pre-mainnet.
- 🟡 **[S70] Sherpa rule-aware sull'hotfix slippage**: prima di SHERPA_MODE=live.
- 🟡 **[S70] Sentinel/Sherpa TELEGRAM flag**: default off; Max abilita quando vuole.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08): rivalutare con dati testnet veri.
- **BNB-discount fee** (CEO opzione A future-proof): trascurabile su €100, da risolvere prima dello scale-up.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.
- **2 brief parcheggiati** in `config/parked/` con trigger di sblocco (DUST writeoff → pre-mainnet; evaluate_trading_skills → ~metà agosto post-trimestre TF) — vedi `config/parked/README.md`.

> Domande risolte S70-S76: chiuse nelle voci §3 In-flight e §10 Sessioni shipped. Storico completo nei commit log e in `audits/PROJECT_STATE_archive.md`.

## 7. Vincoli stagionali / deadline tecniche

- **Bot LIVE su Binance testnet** + Sentinel slow LIVE + **Sherpa LIVE 7/7 parametri** + **TF Tier 1-2 LIVE** (T3 weight=0). Restart corrente: **S103a 2026-06-12 13:46 CET, PID 24606, runtime `3d0bdbb`** (storico restart in §10/archive). `SHERPA_TELEGRAM_ENABLED=true` temporaneo (da togliere a un restart futuro). NewsKeeper v1/v2 standalone NON orchestrator-managed.
- **Go/no-go €100 LIVE**: **nessuna data fissa** — gated da condizioni di mercato (bear + bull + lateral). Sequenza: Sherpa LIVE testnet ✅ (S102b) → osservazione → S103 parametri Board-only → barometro verdict (~23 giu) → Board approval → mainnet.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Runtime Mac Mini commit `5290872` (restart S102b 2026-06-11 21:42).
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, sell_pct net-of-fees S70 ✅, post-fill warning slippage S70 ✅, wallet reconciliation Binance S70 ✅, Sentinel ricalibrazione S70 ✅, Fee Unification S72 ✅, dead zone S73 ✅, partial fills S74c ✅, dashboard coherence S74b ✅, **dashboard SUBLABEL coherence S99b ✅**, stop_buy_unlock_hours S76 ✅, idle alert suppression S76 ✅, **Sherpa coin-aware S81 ✅**, **Sherpa decoupled fast-loop S81 ✅**, **Sherpa amplitude cap S81 ✅**, **Sherpa write guard + battito liveness S102/S102b ✅**, **Sherpa LIVE testnet S102b ✅**, **Sherpa 4 parametri protettivi dinamici regime×tier + debounce 24h S103a ✅ (restart pending)**, slippage_buffer parametrico (🔲 brief separato pre-mainnet).

## 8. Cosa NON è stato fatto e perché

- **slippage_buffer parametrico per coin**: brief separato pre-mainnet, serve calibrare valori con dati reali (BONK testnet vs mainnet).
- **Rule-aware Sherpa sull'hotfix slippage**: Sherpa è in DRY_RUN, niente impatto immediato; brief separato pre-SHERPA_MODE=live.
- **Reason bugiardo** (open question 27 BUSINESS_STATE): post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa `reason` del trade resta scritta con dicitura "above avg" anche su fill < avg. Cosmetico.
- **`exchange_order_id=null` sul sell OP**: debt cosmetico tracciato post-go-live. Reconciliation S70 Step A gestisce con fallback timestamp.
- **UI countdown timer per `stop_buy_activated_at`** (es. "BLOCKED · resets in Xh Ym"): dato esposto in `bot_runtime_state`, ma frontend non lo consuma ancora. Brief separato ~30 min.
- **PortfolioManager dead-instantiation** (scoperto S89 audit A1): `bot/grid_runner/__init__.py:156` istanzia `PortfolioManager()` e lo passa a `GridBot`, ma nessun metodo viene mai invocato (i suoi metodi toccano la tabella inesistente `portfolio`, ora deprecati no-op). Rimuovere l'istanziazione tocca `bot/` runtime → fuori scope brief 89a. Flaggato al Board come follow-up cleanup.
- **`datetime.utcnow()` deprecato** (scoperto S89 audit A1): pytest emette 409 DeprecationWarning, originate in `bot/grid/grid_bot.py` (righe ~607/632/947) + nei test. Sostituire con `datetime.now(datetime.UTC)` tocca `bot/` runtime → fuori scope brief 89a (solo housekeeping test/dead-code). Micro-brief futuro, nessun impatto funzionale (solo rumore nei warning).

## 9. Audit esterni (sintesi)

**Criterio**: riga §9 esiste SOLO se sessione Auditor (CC fresh) con file `audits/reports/YYYYMMDD_audit[AX].md`. Sessioni shipped → §10.

| Data | Area | Topic | Verdetto | Findings + Report |
|------|------|-------|----------|-------------------|
| 2026-05-31 | 3 | **A3-20260531** cruscotto bisettimanale tutti i canali (X/Dev.to/Umami+funnel/GSC/Bing/blog/Payhip/Reddit) — Cowork scheduled automatico | **CON RISERVE** | Movimento misto a 16gg: infra recuperata (GSC da "Impossibile recuperare" → 381 imp/0 click/pos 8,8; Dev.to 5 art/97 view/1 react; Umami+5 funnel ora misurati: 575 pv/89 uv/30gg, bounce 92%/17s; **5/5 connettori OK dalla sandbox Linux**), output piatto/in calo. **3 HIGH**: X declino monotono (108→85→39→**~15,6** imp/post, 1 like/0 RT su 16gg); conversione zero (GSC 0 click CTR 0%, bounce 92%, funnel e2e 0-3,9%, 1 buy-click/0 vendite verif.); Reddit canale primario "in mod approval" dal 28/05 + tracker vuoto. **4 MED**: query GSC off-brand (telegram bot api = 78/381 imp); Bing 0 imp + 54 errori crawl; Payhip non verificato (CSV assente); drift blog↔Dev.to ("AI Is Useful" su Dev.to ma non sul blog canonical). **2 LOW**: Dev.to engagement ~nullo; firme X inconsistenti. Next: sbloccare Reddit + riscrivere title/meta `/roadmap` (320 imp/0 click) + decidere conversione-goal sito (Board). Report: [audits/reports/20260531_audit[A3].md](audits/reports/20260531_audit[A3].md). |
| 2026-05-27 | 1 | **A1-automated** monthly technical integrity audit (codebase + DB schema + bot health + code patterns) | **CON RISERVE** | Bot runtime healthy: 0 ERROR events 48h, all 5 brains writing. No hardcoded secrets. **2 HIGH**: (H1) 32 legacy tests broken since S76; (H2) `sys.exit(1)` at module level in test file. **3 MED**: (M1) dead code referencing non-existent tables; (M2) print() in __main__ blocks; (M3) tweepy missing from requirements.txt. **2 LOW**. Findings H1/H2/M1/M3/L2 chiusi in S89. Report: [audits/reports/20260527_audit[A1].md](audits/reports/20260527_audit[A1].md). |
| 2026-05-27 | 2 | **A2-S87** coherence check narrazione pubblica ↔ codice LIVE ↔ state files (primo audit Area 2 mai eseguito) | **CON RISERVE** | **6 HIGH + 12 MED + 11 LOW + 0 CRITICAL**. Principali: sito pubblico 1-2 settimane in drift (dashboard/roadmap/NewsKeeper); AUDIT_PROTOCOL era un vecchio request, non protocollo; regola cadenza Area 2 mai applicata → riformulata event-based. Remediation: brief 88a-88e, tutti SHIPPED in S88. Report: [audits/reports/20260527_audit[A2].md](audits/reports/20260527_audit[A2].md). |
| 2026-05-15 | 3 | **A3-S78** marketing + SEO/GSC + X performance audit pre-go-live (primo audit Area 3 mai eseguito) | **CON RISERVE** | GSC: cached failure (non server-side). X: trend decrescente, ratio storytelling/technical inverso rispetto al raccomandato. Recommendations applicate in S84 (SEO) e S85 (distribuzione). Report: [audits/reports/20260515_audit[A3].md](audits/reports/20260515_audit[A3].md). |
| 2026-05-07 | 1 | **Phase 1** split grid_bot.py monolite → 6 moduli (brief 62a) | APPROVED — zero regressioni | Verbatim diff: identical. Report: [audits/reports/20260507_audit[A1]_phase1_grid_split_review.md](audits/reports/20260507_audit[A1]_phase1_grid_split_review.md). |

> **Stato cadenze al 2026-06-09** (conteggio sui FILE `audits/reports/YYYYMMDD_audit[AX].md`, non sulle righe §9):
> - **Area 1**: ultimo audit 2026-05-27 (13 gg fa) — entro cadenza 30gg ✅ (prossimo scade ~2026-06-26). Findings H1/H2/M1/M3/L2 chiusi in S89.
> - **Area 2**: ultimo audit 2026-05-27 (13 gg fa) — trigger event-based (pre-mainnet / pre-Volume / pre-nuovo-brain / backstop 60gg). Nuovo audit request in `audits/requests/20260530_audit[A2]_followup_pre_sherpa_live.md` (sessione fresh in Cowork). Nota: BUSINESS_STATE §7 segna A2 da riprogrammare **post-redesign**.
> - **Area 3**: ultimo audit **2026-05-31** (9 gg fa) — cadenza bisettimanale 14gg ✅ (prossimo scade ~2026-06-14). Eseguito da Cowork scheduled automatico. Template `audits/requests/audit_request_A3.md`.
>
> Pre-S70 e nota S77 fase 1 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

## 10. Sessioni shipped (storico)

| Data | Area | Topic | Esito | Sintesi + Report |
|------|------|-------|-------|------------------|
| 2026-06-12 | 1 | **S103a** analisi volume↔PnL paper trading + validazione esterna (2° brief "S103a" del giorno — collisione ID segnalata, SCOPE diversi) | ANALISI consegnata — zero codice, zero restart, zero scritture DB | Brief `briefresolved.md/2026-06-12_S103a_brief_volume-pnl-correlation.md`. **Verdetto: volume_24h NON utilizzabile come filtro TF.** (1) Interno: pattern CEO "Q1 low-vol meglio" = artefatto — 32/51 coppie sono ORPHAN_PERIOD_CLOSE sintetiche (29 con PnL=0 per costruzione, exit_ts≈entry_ts) concentrate nei quartili alti (5/13→12/13, Spearman vol↔orphan +0.46 p=0.0007); sui 19 trade chiusi da mercato: WR 52.6%, PnL +1.49%, correlazione ~0, T3 alto migliore. Inversione segno Tier B (+0.20) vs C (−0.18) segnalata come da brief (n.s., rumore). (2) Esterno (Binance public API no-key, 162 symbol × 377 gg, 318 golden cross EMA20/50 daily): Q1−Q4 raw +8.8 p.p. p=0.0004 ma **spurio** — driver = surge (vol7/vol90, Spearman −0.215 p=0.0001), non liquidità strutturale (p=0.26); con clustering mensile p=0.82. Doppio sort: struct-basso+no-surge +3.65% ma mediana −2.79% (lottery). (3) Letteratura (16 paper + practitioner): illiquidity premium incondizionato supportato (LTW JF 2022, Amihud), momentum-su-illiquide contraddetto (momentum vive nelle coin grandi/liquide; nelle illiquide reversal + pump&dump + premio da liquidity-provider che un taker paga). BTC periodo: +2.2% feed / +3.6% mainnet, laterale-rialzista, regime unico (auto-obiezione CEO fondata). Candidato anti-surge parked in §6 (p=0.092). **Igiene dati: escludere ORPHAN dalle analisi su trend_decisions_log.** TF reale del periodo: WR 53% non 27% — numeri esplorazione schiacciati dagli zeri sintetici. Report `report_for_CEO/2026-06-12_S103a_RforCEO_volume-pnl-correlation.md` + `assets/2026-06-12_S103a_volume-pnl/` (4 script + 2 CSV + 7 PNG riproducibili). |
| 2026-06-12 | 3 | **S103b** redesign dashboard (admin 3 gruppi + §2 pubblica 5 card live pipeline) | SHIPPED `638d1e4`+`0d6e1a0` + deploy Vercel + migration RLS | Brief `config/2026-06-12_S103b_brief_dashboard-brain-cards.md` (+ Max ha aggiunto le card TF/Grid). PART 1 `grid.html`: Min Profit→Security, label ownership (Trading=Board, Grid+Security=Sherpa). PART 2 `/dashboard` §2: TF→Grid + NK→Sentinel→Sherpa live rows, sparkline 7g, polling 5min, token `--color-bot-news`, `<style is:global>`. 3 query brain corrette vs schema (auto-obiezione CEO fondata). Migration RLS `s103b_newskeeper_regime_anon_read` (barometro pubblico, deviazione autorizzata Max). Roadmap Phase 3 → LIVE. Build verde, dati reali verificati in review locale. Report `report_for_CEO/2026-06-12_S103b_RforCEO_dashboard-brain-cards.md`. |
| 2026-06-12 | 1 | **S103a** 4 parametri protettivi → Sherpa-managed (regime×tier) + debounce 24h | SHIPPED `a1826fe` + migration + **restart CC 13:46 CET (PID 24606, `3d0bdbb`), takeover verificato a DB** | Brief `config/2026-06-12_S103a_brief_sherpa-board-params.md`. `BOARD_TABLE[regime][tier]` (nuovo `board_parameter_rules.py`), debounce su coppia (regime,tier) — `board_debounce.py` puro + tabella `sherpa_board_state` — adottato dopo 24h stabili, coin nuova subito. main.py scrive 7 param (cooldown-aware), whitelist config_writer +4 (additivo). admin.html sotto-riga "safety"+tier, label LIVE. Migration: sherpa_proposals +8 col + CHECK tier. 21 test nuovi (suite 219/219). **Ribalta S102 specifica, rispetta principio ownership**; debounce = direttiva Board oltre il brief (anti tier/regime-flapping). 1 flag bloccante + 1 obiezione §7 risolti con Max pre-codice. Report `report_for_CEO/2026-06-12_S103a_RforCEO_sherpa-board-params.md`. |
| 2026-06-11 | 1 | **S102 + S102b** Sherpa coherence audit + write gate flip-based + GO LIVE testnet + battito liveness | SHIPPED `a867179` + `ce92ed2` + **restart 21:42 CET PID 91177, runtime `5290872`** | Sherpa LIVE verificato a DB (9 scritture primo tick = tabella B1). Write gate: −99% volume sherpa_proposals. Parte B: indagine 25 agenti (coin-agnostic SÌ, idle Opzione C, btc_price=gap Sprint 2). 13 test nuovi (198/198). Righe verbose archiviate in compaction S103a-analisi → [archive](audits/PROJECT_STATE_archive.md). Report `..._S102_RforCEO_sherpa-coherence-audit.md` + `..._S102b_RforCEO_sherpa-go-live.md`. |
| 2026-06-10 | 3+docs | **S101 + S101a + S101b** (dashboard §3 redesign + fix MTM −$100 · blog two-voice canonical · GSC chiuso come artefatto + SEO_RULES.md) | SHIPPED `8ea0a23` · `944e74d` · `ccaaf24`, tutte web-only | Sintesi in §4 (S101/S101b) e header. Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). Report in `report_for_CEO/resolved/`. |
| 2026-06-09 | 1+3 | **S100** NewsKeeper T+7 review → redesign "barometro" v2 (build + shadow) | SHIPPED `c8774db` + **shadow LIVE Mac Mini (pid 97566)** + migration | Barometro 3-stati architettura C (Haiku decide polarità) + dedup event-level. Gate falsificabile: shadow ~2 sett, validazione vs prezzo BTC 24h (NON F&G). Verdetto T+14 ~23 giu (vedi §3). Riga verbosa archiviata in compaction S103a-analisi → [archive](audits/PROJECT_STATE_archive.md). Report `report_for_CEO/resolved/2026-06-09_S100_RforCEO_newskeeper-v2-barometro-build.md`. |
| 2026-06-07/08 | 1+3 | **S99a + S99b/S99b-b** (SEO trailing-slash+llms.txt · sell-ladder audit + anti-slippage v2 + dashboard) | SHIPPED `9787aa5` · `e26e67c` + restart 08-giu | Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-06-06 | 1 | **S98 (brief S98a)** Adaptive Sell Penalty (sell-loss-guard) + analisi tbot (S93b) | SHIPPED `507ebd6`→`a7d644d` + **restart 15:15 (PID 85566)** | Guardia post-fill anti-slippage, design v2 Board (penalty = ultima perdita, non cumulativa). Riga verbosa archiviata in compaction S103a-analisi → [archive](audits/PROJECT_STATE_archive.md). Report `report_for_CEO/resolved/2026-06-06_S98a_RforCEO_sell-loss-guard.md`. |
| 2026-06-02→06-05 | 1+3+docs | **S95 → S97c** (7 righe: S95 dashboard mascotte + POST1 SEO live · S95a content plan FAQ schema + 5 draft · S96a clean slate testnet · S96b phantom-safe avg-cost + fee B · S97a phantom audit · S97b blog 2-voci + Keep reading · S97c cycle filter commentary + reconcile cycle-scoped) | tutte SHIPPED | Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-05-23→06-01 | 1+3 | **S82 → S94a** (14 righe: S82 homepage redesign Watchtower/Sherpa · S83 NewsKeeper scaffold RSS · S84 SEO fix · S85 RSS Dev.to + compaction policy · S86 status badge + regime overlay · S87 V3 launch + Umami · S88 remediation Audit A2 · S89 remediation Audit A1 · S90 spike guard A+B · S91 stop_buy extreme_fear + SEO quick wins · S92 layer dati marketing A3 · S93a tono Haiku · S94a NewsKeeper Haiku classifier) | tutte SHIPPED | Righe-sintesi archiviate in compaction S99b-b → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-05-14→-22 | 1 | **S76 → S81** (S76 grid_runner package + 75b; S77 fase1/2+3 Sentinel Sprint1/2; S78/78fase2 primo blog + SWEEP slippage buffer; S79 idle/TF/write-on-change; S80/80a funnel+UTM+Brain Analysis; S81 Sherpa Sprint2 coin-aware) | tutte SHIPPED | Righe verbose archiviate (compaction S88 + S99b-b) in [archive](audits/PROJECT_STATE_archive.md). Topic chiave: refactor package, Sentinel slow loop 4h, Sherpa per-coin volatility, slippage buffer SWEEP, drift FIFO sanato. |
| 2026-05-10 → -12 | 1 | **S70 → S74b** (8 sessioni: S70/70b/70c, S71, S72, S73, S73b, S73c, S74, S74b) | tutte SHIPPED, dettagli in archive | Righe verbose spostate in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sezione "Rimosso in sessione S84 → §10 Sessioni shipped — righe S70 → S74b". Topic chiave: reconciliation Step A/B/C + sell_pct net-of-fees (S70a/b/c); P&L hero unification (S71); Fee Unification + canonical refactor + TF removal pubblici (S72); Dead Zone recalibrate + dust trap + BONK lot_size + BTC phantom mainnet-safe (S73/b/c); brief 74a IT→EN + Telegram + TCC python3.13 FDA + partial fills + dead_zone_hours per-coin (S74/b). |
