# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-06-01 — **sessione 93a (S93a) SHIPPED — shift tono Haiku (narrativo > tecnico)** — brief `S93a_brief_haiku-tone-shift`: nuovo `SYSTEM_PROMPT` X (`utils/x_poster.py`, target 140-190 char, niente liste componenti, max 1 emoji), firma default ridotta a `🤖 AI` (URL UTM Brief 80b conservato come `SIGNATURE_WITH_LINK` per casi particolari — niente più link-preview card sotto ogni post), nuovo prompt micro-diary `commentary.py` (2-3 frasi, 280 char) **con guardrail anti-allucinazione reinserite** (TF in pausa / no FIFO / epoca testnet / `vs_yesterday.direction` Brief 81b). Commit `1f5849a`. **Restart Mac Mini 16:12 CET (PID 19118, runtime `4110e93`)**, 6 figli OK, flag preservati. Dettaglio §10.

**Ultimo aggiornamento precedente:** 2026-05-30 — **S92 — pulizia, riorganizzazione, programmazione (no bot, no restart)** — (1) `config/` cleanup → 10 file in `briefresolved.md/`; (2) `audits/` ristrutturata (`reports/`/`requests/`/`snapshots/` + naming `YYYYMMDD_audit[AX].md`); (3) BUSINESS_STATE compaction 45→34KB; (4) PROJECT_STATE compaction; (5) **layer dati audit Area 3 (marketing)**: 5 connettori API (X/Dev.to/Umami/Bing/GSC) + orchestratore, GSC via OAuth, Reddit chiuso→manuale, deploy Mac Mini. Commit pushati (`origin/main` `d209588`). Dettaglio §10.

> Storico S88/S83/S82/S81/...: vedi §10 + [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

> Storico header sessioni precedenti compattato nelle sezioni §4 Decisioni recenti e §10 Sessioni shipped. Archive narrativo pre-S76 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet — Grid ($500 board) + TF Tier 1-2 only ($100 budget) + Sentinel slow loop LIVE + Sherpa Sprint 2 DRY_RUN coin-aware + NewsKeeper standalone LIVE (RSS feeds, classifier MVP rumoroso, NON orchestrator-managed) + write-on-change su 3 tabelle Supabase + sito pubblico online (3 blog post LIVE)**. Mac Mini orchestrator **runtime commit `4110e93`** (PID parent **19118**, caffeinate 19120, restart 2026-06-01 16:12 CET post shift tono Haiku S93a); allineato a HEAD git locale + NewsKeeper standalone PID 78098 (caffeinate parent 78100, launch 2026-05-24 10:56 CET). 7 processi orchestrator-managed + 2 NewsKeeper standalone. Cron reconcile attivo 03:00 Europe/Rome. **Go-live €100: nessuna data fissa** — dipende da condizioni di mercato osservate (bear + bull + lateral), non da calendario (decisione S82 Board 2026-05-23, sovrascrive S76 "giugno/luglio"). Sequenza Sentinel-first: step 3 osservazione completata, step 4 Sherpa LIVE testnet sbloccabile dopo 7-10gg DRY_RUN Sprint 2 + seconda Brain Analysis.

**Roadmap Sentinel-first (CEO S76, 5 step)**: (1) ~~audit + fix Sentinel Sprint 1~~ ✅ CHIUSO S77; (2) ~~build Sprint 2 slow loop~~ ✅ CHIUSO S77; (3) ~~osservazione 5-7 giorni~~ ✅ CHIUSO S80a con Brain Analysis (NO-GO Sherpa step 4, 3 fix architetturali richiesti); **(3.5) Sherpa Sprint 2 rework** ✅ CHIUSO S81 (per-coin volatility + slow-gate + amplitude cap, brief 81a); (4) **osservazione 7-10gg Sherpa Sprint 2 DRY_RUN + seconda Brain Analysis — IN CORSO da 2026-05-22 sera** (~scadenza naturale 29 maggio - 1 giugno); (5) Sherpa LIVE testnet 1 parametro alla volta (sell_pct primo) post-Brain-Analysis-2; (6) mainnet. **Architecture vision three-phase brain (CEO S81)**: Phase A (questo brief, Sherpa coin-aware) ✅; Phase B (Sentinel coin-aware con EMA/RSI per-coin, Sherpa diventa traduttore score→param); Phase C (Sentinel + sentiment online).

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
tests/                     **121/121 verdi** su 11 file attivi (S89); tests/archived/ (legacy + test_trend_36e_v2) escluso via pytest.ini
```

Comm Sentinel↔Sherpa↔Grid via Supabase only. Telegram alerts: solo Grid trade events; Sentinel+Sherpa silenziati via env (memoria `feedback_no_telegram_alerts`).

## 3. In-flight (settimana 2026-05-18+)

### S92 — pulizia, riorganizzazione, programmazione SHIPPED (no bot, no restart)
- `config/` cleanup: 10 file → `briefresolved.md/` (brief risolti: 88d, stop_buy, S92 crosscheck, umami, TF restore; archivi: Memo brainstorming, VISION v2, HTML sentinella, validation_and_control); `audit_remediation_cover_sheet.md` → `audits/`.
- `audits/` ristrutturata: sottocartelle `reports/`, `requests/`, `snapshots/`; 4 report e 2 request rinominati `YYYYMMDD_audit[AX].md`; AUDIT_PROTOCOL §4/§5/§7/§8 aggiornati; rimosso concetto `audit_in_flight`.
- BUSINESS_STATE.md: 5 righe S92 aggiunte §4, compaction S81-S87 (45KB→34KB).
- PROJECT_STATE.md: compaction header + §3 S91 mattina + aggiornamento §4/§9/§10.
- **Layer dati audit Area 3 (marketing)**: 5 connettori in `scripts/` (X + `devto_stats` + `umami_stats` con 5 funnel+UTM + `bing_seo_stats` + `gsc_stats`) + orchestratore `marketing_data_refresh`; chiavi in `config/.env.marketing` (gitignored, separato da `.env`); output `marketing_data/` (gitignored). **GSC via OAuth** (login owner, token cache headless — il service account non si autorizzava su proprietà Dominio). **Reddit dormiente**: API self-service chiusa da Reddit → fonte manuale come Payhip; connettore ibrido pronto. Deploy Mac Mini: `git pull` + deps in venv + 3 segreti scp; orchestratore live **5/5 OK headless**. `audit_request_A3` corretto (Mac Mini usa `./venv/bin/python`, non `python3.13`); `audit_request_A1` ricostruito (gemello leggibile del prompt Cowork). Cartelle `audits/` MBP↔MacMini riallineate (dump 25MB fuori repo). Report CEO + memorie aggiornate.

### S91 — SEO/A11y quick wins + fix stop_buy extreme_fear SHIPPED → §3 verbatim archiviato in compaction S92. Sintesi §10 righe S91. In breve: (mattina) WP1+WP2 sito, diagnosi sitemap GSC, fix noRss feed; (pomeriggio) regime_analyzer.py fix label-aware F&G, test 131✅, restart Mac Mini PID 33218 runtime `51895f8`, verificato LIVE.

### S90 — fix_slippage_AB + deliverables UI/blog SHIPPED → §3 verbatim archiviato in compaction S91 ([audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sez. "Rimosso in sessione S91"). Sintesi §10 riga S90. In breve: spike guard `fetch_price_with_spike_guard` (lifecycle.py) + `_skip_next_decision` doppio gate (grid_bot.py), test 129✅, restart Mac Mini PID 93187 runtime `673c941`; pomeriggio (no bot) dashboard banner + cover Vol-3 JPG + 4° blog post.

### S89 — brief 89a Audit Area 1 remediation SHIPPED → §3 verbatim archiviato in compaction S91. Sintesi §10 riga S89. In breve: atterraggio audit automatico (CC corriere scp), test hygiene (tests/archived + pytest.ini, 121✅), 4 metodi dead-table no-op, tweepy → requirements-scripts.txt.

### S88 — brief 88b/88c/88a/88e + 88d SHIPPED (remediation Audit Area 2)
- Dettaglio §3 verbatim archiviato in compaction S89 → [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sez. "Rimosso in sessione S89". Sintesi in §10 riga S88. In breve: catch-up sito S80→S87 (roadmap.ts + Phase 14 NewsKeeper), PROJECT_STATE 61KB→<40KB + drift fix, AUDIT_PROTOCOL riscritto + trigger Area 2 event-based, config/parked, UI debts dashboard + botData homepage live. Findings 1.1-1.5/2.2/2.3/3.1-3.3/4.2/4.4/5.x/6.1/6.2.

### S87 — V3 launch site updates + 2 task umami SHIPPED
- Dettaglio in §10 riga S87. Blocco in-flight verbatim archiviato in compaction S88 → [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sez. "Rimosso in sessione S88".

### Storico in-flight pre-S87
- **S82→S86 dettaglio archiviato** in compaction S88 (`audits/PROJECT_STATE_archive.md`) + righe sintetiche §10. In breve: S86 status badge + regime overlay admin; S85 RSS feed Dev.to + governance BUSINESS_STATE; S84 SEO fix; S83 NewsKeeper scaffold; S82 homepage redesign Watchtower/Sherpa.

### Aperti / TODO
- **🟡 [S81 NEW] Cap kicks BONK in mainnet**: con `MAX_DELTA_PCT=0.30` Board BONK sell_pct=2.5, Sherpa può proporre max 3.25 in un tick. Pre-mainnet vorremo forse 0.10-0.15 (slippage mainnet 10× più basso). Brief separato pre-step 5.
- **🟡 [S70] Sherpa rule-aware sull'hotfix slippage**: ora coperto parzialmente dal per-coin scaling Sprint 2, ma il `sell_pct` Sherpa non conosce esplicitamente `SLIPPAGE_BUFFER_PCT`. Da chiudere prima di `SHERPA_MODE=live`.
- **🟡 [S70/S78 fase 2] sell_pct + slippage_buffer parametrico per coin**: estensione post-mainnet, parametrizzare per-coin in `bot_config` con dati slippage reali.
- **🟡 [S72] Telegram messages post-72a**: "Have SOL: $547 → Sell $19.94" mostra TOTALE wallet inclusi phantom testnet. Cosmetico. Vincolo Max: non toccare canonical computeCanonicalState.
- **🟡 [S72] Code debt: `buildSection` morto in dashboard-live.ts**: ~10 min cleanup post-go-live.
- **🟡 [S70c] Sito mobile review approfondito**: smoke iPhone fatto, test su device reale richiede Max sul telefono.
- **🟡 [S70c → S78] Verifica identità accounting** (residuo Strada 2): ~30 min check empirico Realized + Unrealized = Equity P&L, post-go-live €100.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A.

## 4. Decisioni recenti

- **2026-05-30 (S92) — layer marketing Area 3: GSC OAuth + Reddit chiuso + env separato SHIPPED (no bot)**.
  DECISIONE 1 (GSC): auth via **OAuth** (login owner cartone@gmail.com), non service account.
  RAZIONALE: il service account dà "email not found" in Search Console su proprietà Dominio; OAuth come owner bypassa l'autorizzazione (sei già proprietario). Token cache → headless sul Mac Mini. Auto-detect SA vs OAuth → reversibile senza modifiche.
  DECISIONE 2 (Reddit): connettore **dormiente**, fonte manuale come Payhip.
  RAZIONALE: Reddit ha chiuso l'API self-service; tutte le strade esterne (app, JSON pubblico, Devvit, contratto) bloccate. Ibrido praw+JSON pronto se riapre. Vedi memoria `project_reddit_api_closed`.
  DECISIONE 3 (env): chiavi marketing in `config/.env.marketing` **isolato** da `.env` → un leak marketing non tocca i fondi trading.

- **2026-05-30 (S92) — pulizia/riorganizzazione estremporanea SHIPPED (no bot)**.
  DECISIONE: sessione dedicata a cleanup config/, audits/, compaction state files.
  RAZIONALE: PROJECT_STATE a 50KB (+10KB sopra cap), audits/ piatta senza struttura, ~10 brief risolti ancora in config/.
  ALTERNATIVE CONSIDERATE: fare tutto in fondo a una sessione tecnica — scartato (rischio di fare solo metà e lasciare inconsistenze).

- **2026-05-29 (S91) — Brain Analysis 2 + fix stop_buy extreme_fear SHIPPED**.
  DECISIONE: fix label-primary `fng_label=="Extreme Fear" OR fng_value<=25` in `regime_analyzer.py`; solo fix-forward (no backfill storico).
  RAZIONALE: soglia hardcoded `<=20` escludeva F&G 21-25 (etichettati "Extreme Fear" da alternative.me) → Sherpa non armava mai stop_buy in regime crash reale. Brain Analysis 2 ha validato i 3 fix Sprint 2 (coin-aware, oscillazione, cap); Sherpa pronto ma non mainnet-bound finché timing Sentinel lento non chiuso.
  ALTERNATIVE CONSIDERATE: backfill storico — scartato (operativamente conta il futuro, costo/beneficio nullo).

- **2026-05-28 (S90) — fix slippage A+B SHIPPED**.
  DECISIONE: Opzione A variante Board ("doppio fetch con conferma") al posto della soglia fissa proposta da CC + Opzione B con doppio gate (within-tick + next-tick).
  RAZIONALE: soglia fissa è impossibile da calibrare su coin con volatilità diverse (BTC vs BONK); doppio fetch è auto-adattivo (50% confirmation ratio funziona uguale per uno spike $82K o per un pump BONK +12%). Doppio gate B è necessario perché `dead_zone_recalibrate` e SELL CHECK vivono nella stessa `check_price_and_execute` — un singolo flag letto in cima alla funzione protegge solo il tick successivo, lasciando scoperto il tick attuale (= esattamente lo scenario 27/05).
  ALTERNATIVE CONSIDERATE: (B-only) lasciato perdere — non protegge altri path che potrebbero leggere uno spike ticker; (A-only) lasciato perdere — non protegge il caso dove lo spike è "lento" (presente per 5+ secondi); (C-pre-trade SLIPPAGE_BUFFER esteso) parcheggiato come follow-up pre-mainnet, vedi §6.
  FALLBACK: in `bot_config` si possono cambiare via Supabase i 3 parametri (threshold_pct/confirm_pct/pause_seconds) — oggi sono default argument della funzione, se servono tunable per-coin facciamo passaggio esplicito da config in un brief separato. Soglia 4% scelta a posteriori sui dati osservati (BONK 2.46% slippage S70, BTC 5.83% questo episode); abbastanza largo da non scattare sul rumore mainnet (~0.5-1% tick-to-tick).

- **2026-05-26 (S86) — status badge homepage + regime overlay admin SHIPPED** (2 commit `9321a75`+`e511a7f`). Decisioni (drift Chart.js→Canvas 2D, palette finanziaria, Widget B killed, box positioning) verbatim → archive S88 + §10 riga S86.

- **2026-05-25/26 (S85) — housekeeping CEO-driven SHIPPED** (5 commit `8c9c2fc`→`86af67b`). RSS feed Dev.to + CLAUDE.md §[2b] compaction BUSINESS_STATE + S85 update. Verbatim → archive S88 + §10 riga S85.

- **2026-05-24 (S84 chiusura) → vedi voce §10**. Verbatim §4 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sezione "Rimosso in sessione S86".
- **2026-05-24 (S83 chiusura) → vedi voce §10**. Verbatim §4 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sezione "Rimosso in sessione S86".
- **2026-05-23 (S82) → vedi voce §10**.
- **2026-05-22 (S81) → vedi voce §10**.

> Decisioni S81 + S82 + tutte le precedenti compattate in S83 + S86 compaction. Storico completo in §10 + commit log + archive.

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
- **S81**: brief 81a Sherpa Sprint 2 — per-coin volatility scaling + slow-loop gate + amplitude cap 30%. BONK ora riceve sell_pct proporzionato a volatilità (2.09× BTC). Brief 81b — Haiku `vs_yesterday.direction` field + 3 nuove rules system prompt (LENGTH/NUMBERS/DIRECTION).
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

- **Bot LIVE su Binance testnet** + Sentinel slow LIVE + **Sherpa Sprint 2 DRY_RUN coin-aware** + **TF Tier 1-2 LIVE** (S79, T3 weight=0). Restart S91 2026-05-29 15:53 CET (post fix regime extreme_fear). PID orchestrator **33218** + 6 figli (caffeinate 33219 + 3 grid + TF + Sentinel + Sherpa). Mac Mini runtime commit `51895f8`.
- **Go/no-go €100 LIVE**: **nessuna data fissa** — gated da condizioni di mercato (bear + bull + lateral). Sequenza: NewsKeeper S2-S4 → Sherpa LIVE testnet (1 parametro alla volta, sell_pct primo) → dry_run → Board approval.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Runtime Mac Mini commit `51895f8` (restart S91 2026-05-29).
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, sell_pct net-of-fees S70 ✅, post-fill warning slippage S70 ✅, wallet reconciliation Binance S70 ✅, Sentinel ricalibrazione S70 ✅, Fee Unification S72 ✅, dead zone S73 ✅, partial fills S74c ✅, dashboard coherence S74b ✅, stop_buy_unlock_hours S76 ✅, idle alert suppression S76 ✅, **Sherpa coin-aware S81 ✅**, **Sherpa decoupled fast-loop S81 ✅**, **Sherpa amplitude cap S81 ✅**, slippage_buffer parametrico (🔲 brief separato pre-mainnet).

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

> **Stato cadenze al 2026-05-31** (conteggio sui FILE `audits/reports/YYYYMMDD_audit[AX].md`, non sulle righe §9):
> - **Area 1**: ultimo audit 2026-05-27 (4 gg fa) — entro cadenza 30gg ✅ (prossimo scade ~2026-06-26). Findings H1/H2/M1/M3/L2 chiusi in S89.
> - **Area 2**: ultimo audit 2026-05-27 (4 gg fa) — trigger event-based (pre-mainnet / pre-Volume / pre-nuovo-brain / backstop 120gg). Nuovo audit request in `audits/requests/20260530_audit[A2]_followup_pre_sherpa_live.md` (sessione fresh in Cowork).
> - **Area 3**: ultimo audit **2026-05-31** (0 gg fa) — cadenza bisettimanale 14gg ✅ (prossimo scade ~2026-06-14). Eseguito da Cowork scheduled automatico. Template `audits/requests/audit_request_A3.md`.
>
> Pre-S70 e nota S77 fase 1 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

## 10. Sessioni shipped (storico)


| Data | Area | Topic | Esito | Sintesi + Report |
|------|------|-------|-------|------------------|
| 2026-06-01 | 3 | **S93a** shift tono Haiku — narrativo > tecnico | SHIPPED commit `1f5849a` + **RESTART Mac Mini 16:12 CET (PID 19118, `4110e93`)** | Brief `briefresolved.md/2026-06-01_S93a_brief_haiku-tone-shift.md` (A3 31/05: post meno tecnici performano meglio). `utils/x_poster.py`: nuovo `SYSTEM_PROMPT` (target 140-190 char, una storia non un changelog, niente liste componenti, max 1 emoji); **firma default `🤖 AI`** (eliminata card link-preview sotto ogni post — decisione Max), URL UTM Brief 80b conservato come `SIGNATURE_WITH_LINK` per casi particolari. `commentary.py`: nuovo micro-diary (2-3 frasi, 280 char) **+ guardrail anti-allucinazione reinserite** (TF pausa / no FIFO / epoca testnet / regola `vs_yesterday.direction` Brief 81b — deviazione dal brief autorizzata da Max). Anti-assenso: 2 obiezioni reali sollevate (rimozione UTM, rimozione guardrail) → entrambe risolte con Max prima di codare. Solo prompt+firma, logica intatta. Restart pulito, 6 figli, flag preservati. |
| 2026-05-30 | docs+3 | **S92** pulizia/riorganizzazione + layer dati marketing Area 3 (no bot, no restart) | SHIPPED più commit (`origin/main` `d209588`) | `config/` cleanup (10 file → `briefresolved.md/`); `audits/` ristrutturata (reports/requests/snapshots + naming `YYYYMMDD_audit[AX]`); AUDIT_PROTOCOL §4/§5/§7/§8; BUSINESS_STATE compaction 45→34KB; PROJECT_STATE compaction. **Layer marketing**: 5 connettori API (X/Dev.to/Umami+5funnel/Bing/GSC) + orchestratore `marketing_data_refresh`; **GSC via OAuth** (token headless), **Reddit chiuso→manuale**, env separato `.env.marketing`; deploy Mac Mini venv+segreti (5/5 headless OK); `audit_request_A3` venv-fix + `audit_request_A1` ricostruito; `audits/` MBP↔MacMini riallineate (dump 25MB fuori repo). Report CEO `2026-05-30_area3_marketing_audit_data_layer`. Commit `13d5dd4`/`6568ca9`/`f643a7b`/`dc866ef`/`d209588`. |
| 2026-05-29 | 1 | **S91 (pomeriggio)** fix stop_buy irraggiungibile — gap regime "extreme_fear" in Sentinel slow loop | SHIPPED 1 commit `ea4c7a8` + TEST 131/131 + **RESTART Mac Mini 15:53 CET (PID 33218, `51895f8`) + VERIFICATO LIVE** | `regime_analyzer.py` soglia `fng_value<=20` → `fng_label=="Extreme Fear" OR fng_value<=25`. F&G 21-25 finiva "fear" → stop_buy morto. Fix-forward. Verifica: F&G=23 → `extreme_fear` + `proposed_stop_buy_active=true` su 3 coin al primo ciclo Sherpa. |
| 2026-05-29 | 3 | **S91 (mattina)** SEO/A11y quick wins sito (web-only, no bot/no restart) | SHIPPED + BUILD 15 pagine | Brief da 2 file `config/` (Lighthouse 29/05 + guida canonical/Bing). WP1: file verifica Bing/IndexNow in `public/`, iframe a-ads `title`, fix `<dl>` malformato (index.astro), aria-label distinti 3 link Payhip (index+library), redirect `/sitemap.xml`→`/sitemap-index.xml`. WP2: `--color-text-muted` #5d6680→#828aa0 (~5,1:1 AA). Canonical già presente (brief stale). **Sitemap "Couldn't fetch" diagnosi**: non rotta (200/XML valido anche Googlebot, SSL ok) → stato stale GSC dominio nuovo, fix operativo Max (invio solo sitemap-index + Domain property). WP3 perf SALTATO (Vercel RUM ~96), WP4 proxy Binance/header RIMANDATO pre-mainnet → `config/SEO_deferred.md`. Sorgenti → `briefresolved.md/SEO_*`. |
| 2026-05-28 | 1+3 | **S90** fix spike guard A+B + UI/blog pomeriggio | SHIPPED 8 commit + TEST 129/129 + RESTART PID 93187 runtime `673c941` + BUILD 15 pagine | Parte 1: `fetch_price_with_spike_guard` (lifecycle.py, threshold 4%/confirm 50%/pause 5s) + `_skip_next_decision` doppio gate (grid_bot.py). Root cause: testnet spike $82K + dead_zone_recalibrate + SELL stesso tick. Parte 2: dashboard banner rimosso, cover Vol-3 JPG, 4° blog post. Verbatim → archive S92. |
| 2026-05-27 | 1 | **S89** Audit Area 1 remediation + atterraggio audit automatico | SHIPPED 2 commit + TEST 121/121 | CC corriere (scp dal Mac Mini scheduled). legacy tests + test_trend_36e_v2 → tests/archived/ + pytest.ini; 4 metodi dead-table no-op; tweepy → requirements-scripts.txt. Findings H1/H2/M1/M3/L2 chiusi. Verbatim → archive S92. |
| 2026-05-27 | 2+3 | **S88** remediation Audit Area 2 — 5 brief (88a-88e tutti SHIPPED) | SHIPPED + BUILD 14 pagine | catch-up sito S80→S87, AUDIT_PROTOCOL riscritto, config/parked, UI debts (botData homepage + banner fear regime). Findings 1.1→6.2 chiusi. Verbatim → archive S89+S92. |
| 2026-05-27 | 3 | **S87** V3 launch site updates + Umami | SHIPPED 4 commit + BUILD 14 pagine | V3 Payhip live su tutti i touchpoint (BlogCTA, library, /buy→store). 22 data-umami-event + pixel RSS. Verbatim → archive S88+S92. |
| 2026-05-26 | 3 | **S86** status badge homepage + regime overlay admin | SHIPPED 2 commit + DEPLOY VERCEL | 86a: Supabase project_status + box teal homepage. 86b: drawRegimeBands() su 3 chart admin.html (Canvas 2D). Widget B killed. Verbatim → archive S88+S92. |
| 2026-05-25/26 | 3 | **S85** housekeeping CEO-driven — RSS feed Dev.to + BUSINESS_STATE compaction policy + S85 update | SHIPPED 5 commit (`8c9c2fc`→`86af67b`), no bot | RSS `/rss.xml` + `content:encoded` markdown→HTML; CLAUDE.md §[2b] compaction BUSINESS_STATE + archive retroattivo; BUSINESS_STATE S85 update. Verbatim → archive S88. |
| 2026-05-24 | 3 | **S84** SEO audit fix — title/desc 8 pagine + JSON-LD WebSite+Article + sitemap lastmod | SHIPPED `c89c8cc` + BUILD VERDE + DEPLOY VERCEL | Layout prop `jsonLd`, WebSite SearchAction su home (chiude drift S47), Article auto da frontmatter. Action Max: GSC re-submit + URL inspection + CTR 7-14gg. Verbatim → archive S88. |
| 2026-05-24 | 1 | **S83** NewsKeeper Brain #5 scaffold Session 1 (RSS Module 1) + push S82 + deploy standalone Mac Mini | SHIPPED `49473a9` + 2 migration + LIVE PID 78098 | Pivot CryptoPanic→RSS (free tier dead). Package `bot/newskeeper/` 5 file standalone (non orchestrator-managed), classifier regex ~60% FP, osservazione 7gg. Verbatim → archive S88. |
| 2026-05-23 | 3 | **S82** Homepage redesign — WatchtowerCard + SherpaLockedCard + Blog section + Diary swap + 3 stat-row LIVE Supabase | SHIPPED + push in S83 (`cdb5ff8`+`85b2751`) | Mascot Claude Design, NewsKeeper cameo dim/locked, live wiring `watchtower-live.ts`+`sherpa-live.ts`. Verbatim → archive S88. |
| 2026-05-22 | 1 | **S81** brief 81a Sherpa Sprint 2 (per-coin volatility + slow gate + cap 30%) + 81b Haiku direction safety + restart | SHIPPED 2 commit `3ba1132`+`51204cf` + TEST 121/121 | BTC 1.0/SOL 1.6×/BONK 2.1×, proposte diverse per coin → Brain Analysis finding 'non coin-aware' CHIUSO. Verbatim → archive S88. |
| 2026-05-22 | 1+3 | **S80a** brief 80a Brain Analysis (counterfactual Sherpa + Sentinel timing) + AADS refresh | SHIPPED report + frontend, NO trading code | Sherpa applied -$3.94 vs Board, root cause non coin-aware (319 proposte identiche). NO-GO step 4 → 3 pre-req. Verbatim → archive S88. |
| 2026-05-20 | 1+3 | **S80** brief 80b homepage funnel + UTM + TF live narrativa + Dev.to launch + roadmap Phase 9 §3 | SHIPPED `b8bdc12` + web + DEPLOY VERCEL | 3 CTA home, UTM x_poster+telegram, TfDoctor→card TF live. Mac Mini restart pending (signatures). Verbatim → archive S88. |
| 2026-05-18 | 1 | **S79** 79a idle suppression + 79b TF reactivation Tier 1-2 + 79c write-on-change + drift FIFO sanato | SHIPPED 5 commit + 2 restart + TEST 31/31 | `tf_tier3_weight=0`, write-on-change heartbeat 10/10/5min, bug [S70c] chiuso. Verbatim → archive S88. |
| 2026-05-16 | 1 | **S78 fase 2** brief 78b SWEEP/LAST SHOT slippage buffer + banner + blog post 2 + gitignore anchor | SHIPPED + TEST 4/4+30/30 + RESTART PID 33579 | `SLIPPAGE_BUFFER_PCT=0.03` (cassa -$0.44 su SWEEP by-design testnet, mainnet -2010). Commit `afd97ce`. Verbatim → archive S88. |
| 2026-05-15 | 3 | **S78** brief 78a primo blog post publish | SHIPPED + DEPLOY VERCEL | 'An AI That Can't Trade' dual-voice, commit `18a0362`. Verbatim → archive S88. |
| 2026-05-14 | 1 | **S77 fase 2+3** Sentinel Sprint 2 slow loop (brief 77b) + restart | SHIPPED + TEST 85/85 + restart PID 90540 | Slow loop 4h F&G+CMC→regime (5 bucket), Sherpa legge regime dinamico. Commit `a62e5d5`. Verbatim → archive S88. |
| 2026-05-14 | 1 | **S77 fase 1** Sentinel Sprint 1 audit empirico (brief 77a) — audit-style ma NON Auditor | TUTTI PASS + 3 design Q parcheggiate | 6.081 fast scan: SoF 2.32%, risk 5 valori, opp 3 valori, funding dead-by-design testnet. Verbatim → archive S88. |
| 2026-05-14 | 1 | **S76** refactor grid_runner package (1623→8 moduli) + 75b stop_buy_unlock_hours + idle audit | SHIPPED + TEST 29/29 + 3 restart + 2 migration | Squash `9ceaa81`, zero behavior change live. Verbatim → archive S88. |
| 2026-05-10 → -12 | 1 | **S70 → S74b** (8 sessioni: S70/70b/70c, S71, S72, S73, S73b, S73c, S74, S74b) | tutte SHIPPED, dettagli in archive | Righe verbose spostate in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sezione "Rimosso in sessione S84 → §10 Sessioni shipped — righe S70 → S74b". Topic chiave: reconciliation Step A/B/C + sell_pct net-of-fees (S70a/b/c); P&L hero unification (S71); Fee Unification + canonical refactor + TF removal pubblici (S72); Dead Zone recalibrate + dust trap + BONK lot_size + BTC phantom mainnet-safe (S73/b/c); brief 74a IT→EN + Telegram + TCC python3.13 FDA + partial fills + dead_zone_hours per-coin (S74/b). |
