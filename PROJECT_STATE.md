# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-06-11 — **S102+S102b SHIPPED — Sherpa coherence audit + GO LIVE testnet + write guard + battito liveness** (commit `a867179` write guard, `ce92ed2` battito LIVE, + docs/report; **restart Mac Mini 21:42 CET, orchestrator PID 91177, codice runtime `5290872`** — fatto da CC su richiesta Max). **Sherpa è LIVE**: `SHERPA_MODE=live`, al primo tick ha scritto i parametri reali (DB `config_changes_log` changed_by='sherpa': BTC 0.65/1.05/5.6, SOL 0.65/1.53/5.6, BONK 3.0/1.75/5.6 — combaciano al centesimo con la tabella B1). Telegram alert ON temporaneo (`SHERPA_TELEGRAM_ENABLED=true`, D5, da togliere a un restart futuro). **Parte A** (write guard): il filtro 79c era bypassato dal pass-through a LIVELLO di `proposed_stop_buy_active` (extreme_fear dal 29 mag → ~2.100 righe/gg) → gate flip-based + heartbeat 600s→4h. **Battito (S102b)**: in LIVE Sherpa scrive ~18 righe/gg di solo polso su `sherpa_proposals` (liveness + lampada dashboard), i cambi reali vanno in `config_changes_log`. Suite 198/198. **Parte B**: report `report_for_CEO/2026-06-11_S102_RforCEO_sherpa-coherence-audit.md` (indagine multi-agente, 25 agenti). Verdetti: coin-agnostic SÌ; 5 regimi = design S61; fast loop rimosso Sprint 2; btc_price null = gap Sentinel slow writer; would_have_changed 100% = artefatto DRY_RUN; idle 8 vs clamp 6 → Opzione C (accettato rientro nel range). Report go-live `..._S102b_RforCEO_sherpa-go-live.md`. Dettaglio §4/§10. **+ S100 T+36h check**: routine remota OK (`0ad599b`, barometro 203 Haiku, 0 fallback, non-muto).

**Sessioni 2026-06-10:** S101a (blog two-voice canonical `944e74d`), S101 (dashboard §3 redesign + fix MTM −$100 `8ea0a23`), S101b (GSC chiuso come artefatto + SEO_RULES.md `ccaaf24`) — tutte web-only. Dettaglio §4/§10.

> Storico header S101 e precedenti: vedi §10 + [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) (compaction S102).

**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

> Storico header sessioni precedenti compattato nelle sezioni §4 Decisioni recenti e §10 Sessioni shipped. Archive narrativo pre-S76 in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md).

---

## 1. Stato attuale

Fase: **bot LIVE su Binance testnet — Grid ($500 board) + TF Tier 1-2 only ($100 budget) + Sentinel slow loop LIVE + Sherpa Sprint 2 LIVE coin-aware (`SHERPA_MODE=live` dal 2026-06-11, scrive buy_pct/sell_pct/idle_reentry_hours in bot_config) + NewsKeeper standalone LIVE (Haiku classifier S2 `haiku_s2`, RSS crypto+macro CNBC/MarketWatch, NON orchestrator-managed) + write-on-change su 3 tabelle Supabase + sito pubblico online (8 blog post LIVE, convenzione 2 voci + byline + "Keep reading" correlati da S97b)**. Mac Mini orchestrator **restart 2026-06-11 21:42 CET (S102b), PID 91177, codice runtime `5290872`** (Sherpa LIVE + write guard + battito liveness; `SHERPA_TELEGRAM_ENABLED=true` temporaneo) — repo Mac Mini allineato a session HEAD; i 3 grid girano su `testnet_2` (clean slate S96a 2026-06-04, primo trade reale 2026-06-05 = Day 1) con avg corretto + fee sintetiche 0,1% (S96b). 7 processi orchestrator-managed + NewsKeeper standalone v1 (Haiku, pid 10899) + **v2 "barometro" shadow LIVE (pid 97566, da 2026-06-09, accanto a v1, NON in Sentinel)** — i due NewsKeeper NON toccati dal restart S102b. Cron reconcile attivo 03:00 Europe/Rome. **Go-live €100: nessuna data fissa** — dipende da condizioni di mercato osservate (bear + bull + lateral), non da calendario (decisione S82 Board 2026-05-23). Sequenza Sentinel-first: step 4 Sherpa LIVE testnet ✅ FATTO S102b; ora osservazione + S103 (4 parametri Board-only) + verdetto barometro (~23 giu).

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

### S99 — Passive Income Dashboard (brainstorming, doc per CEO)
- Brainstorming Max+CC su WIP Max (blueprint domanda #2: "AI genera passive income?"). Doc strutturato `config/2026-06-07_passive-income-dashboard_brainstorm-for-CEO.md` (untracked — Max lo gira al CEO; commit all'archiviazione). **Deciso**: revenue+traction · domanda-bot APERTA (zero numeri; il "30% datacenter" S80 è puntuale, non fidabile) · Trading="waiting to go live" · Payhip usa 150 (dashboard, dichiarando fonte; lista prodotti dà 91) · cadenza per-fonte con `updated` per riga · backend = Supabase + pattern `project_status` + connettori marketing esistenti, **MVP tutto manuale** (anti-over-engineering). **Al CEO**: (B) dove vive — racc. teaser home + pagina `/income`; (E) rischio €0 vs vendite libri. WIP Max in `config/brief_WIP_grafico-passive_income.xml` (untracked).

> Voci §3 di sessioni shipped **S88-S98** (redesign Pastel v2 LIVE 2026-06-04; blog 2-voci + cross-post; pointer S88-S92) archiviate nelle compaction S95b/S99b-b → [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md). Sintesi in §10.

### Aperti / TODO
- ✅ **[S102b] Restart orchestrator + Sherpa GO LIVE — FATTO 2026-06-11 21:42 CET** (PID 91177, runtime `5290872`). Sherpa LIVE verificato (9 scritture `changed_by='sherpa'` al primo tick). Write guard + battito liveness deployati. `SHERPA_TELEGRAM_ENABLED=true` temporaneo (togliere a un restart futuro). **Da osservare**: convergenza buy_pct nei primi giorni; volume `sherpa_proposals` ≤ ~18 righe/gg (solo battiti) in regime stabile; lampada STOP BUY dashboard di nuovo viva.
- 🆕 **[S103 — domani] Chiudere Sherpa + redesign dashboard grid.html** (piano Max fine S102):
  - **(1)** i 4 parametri "fix" Board-only impostati **in automatico su ogni nuova moneta**: `stop_buy_drawdown_pct`, `stop_buy_unlock_hours`, `dead_zone_hours`, `min_profit_pct` (etichetta dashboard "MIN PROFIT %"; ⚠️ verificare il nome reale del campo `bot_config` — probabilmente `profit_target_pct`). Default universali o per-coin via volatility multiplier (da decidere).
  - **(2)** `web_astro/public/grid.html`: separare i parametri gestiti da Sherpa (buy/sell/idle) da quelli gestiti da Max/Board, e dividere la dashboard **per singola moneta in 3 fasce** (ipotesi CC da confermare: Sherpa/strategia · Board/sicurezza · Board/soldi).
- 🔔 **[S100] Verdetto barometro T+14 — DOVUTO ~2026-06-23.** Validare i flip di `newskeeper_regime` vs ritorno prezzo BTC 24h (da `sentinel_scores.btc_price` a flip+24h), **NON vs F&G** (circolare). Flip da validare: neutral→bearish 2026-06-10 00:08 UTC. Lente regime: se i 14gg restano solo-bear → verdetto parziale, estendere. Esito: promuovere (cablaggio Sentinel) o bocciare (→ /news, blog "esperimento fallito"). (Check T+36h ✅ chiuso 11-giu: routine remota OK, report `2026-06-11_S100_newskeeper-v2-shadow-check.md`, barometro sano e non-muto.)
- **🟡 [S101 NEW] daily_pnl snapshot day-1 sottostimato (follow-up)**: `total_value` 5-giu=350.63 / 6-giu=476.72 vs ~497 atteso (a fine 5-giu: net invested $496.53 su 18 trade, realized +$0.18 → nessuna perdita reale; il 6-giu "recupera" +$126 con realized −$6.30 = impossibile come mercato). La curva §3 mostra quindi un dip day-1 in parte finto. Pista: snapshot scritto dal PRIMO grid bot al blocco 20:00 (`db/client.py:306`, `ignore_duplicates=True`, mai più aggiornato) che al day-1 post-reset valutava un portafoglio parziale. Da brief: hardening calcolo snapshot + eventuale correzione righe 5-6 giu. Nota correlata: snapshot ≈ ore 20:00 locali, non EOD reale → la card dice "as of <data>". Ricorre a ogni reset mensile testnet.
- **✅ [S95→S99] Branch orfani cancellati**: `refactor/grid_runner_split` + `redesign/pastel-sticker-v2` non più su GitHub (verificato S99, resta solo `origin/main`). Drift §3 sanato.
- **🟡 [S81 NEW] Cap kicks BONK in mainnet**: con `MAX_DELTA_PCT=0.30` Board BONK sell_pct=2.5, Sherpa può proporre max 3.25 in un tick. Pre-mainnet vorremo forse 0.10-0.15 (slippage mainnet 10× più basso). Brief separato pre-mainnet.
- **🟡 [S70→S102b] Sherpa rule-aware sull'hotfix slippage**: il `sell_pct` Sherpa non conosce esplicitamente `SLIPPAGE_BUFFER_PCT`. Su testnet (Sherpa ora LIVE, S102b) è coperto a runtime dall'Adaptive Sell Penalty (S98/S99b) + per-coin scaling Sprint 2; resta un follow-up esplicito pre-mainnet.
- **🟡 [S70/S78 fase 2] sell_pct + slippage_buffer parametrico per coin**: estensione post-mainnet, parametrizzare per-coin in `bot_config` con dati slippage reali.
- **🟡 [S72] Telegram messages post-72a**: "Have SOL: $547 → Sell $19.94" mostra TOTALE wallet inclusi phantom testnet. Cosmetico. Vincolo Max: non toccare canonical computeCanonicalState.
- **🟡 [S72] Code debt: `buildSection` morto in dashboard-live.ts**: ~10 min cleanup post-go-live.
- **🟡 [S70c] Sito mobile review approfondito**: smoke iPhone fatto, test su device reale richiede Max sul telefono.
- **🟡 [S70c → S78] Verifica identità accounting** (residuo Strada 2): ~30 min check empirico Realized + Unrealized = Equity P&L, post-go-live €100.
- **🟡 [S67 residuo]** Brief 67a Step 5 superato da reconciliation S70 Step A.

## 4. Decisioni recenti

- **2026-06-11 (S102b) — Sherpa GO LIVE su testnet + battito liveness; attivazione via env flag, non cambio di codice**.
  DECISIONE: (D1) attivazione `SHERPA_MODE=live` come env flag al restart, default `dry_run` in codice intatto (safety: ogni restart futuro deve includere il flag o Sherpa torna a dry_run in silenzio). (D2) i cambi parametro in LIVE vanno solo in `config_changes_log` (no shadow-write completo delle proposte). (D4) **battito di liveness** in LIVE (`ce92ed2`): ~18 righe/gg di solo polso su `sherpa_proposals` — risolve "vivo vs zombie" (il monitoraggio orchestrator copre solo il crash) e la lampada STOP BUY della dashboard (che leggeva sherpa_proposals e si congelava). (D5) `SHERPA_TELEGRAM_ENABLED=true` temporaneo, alert sui cambi parametro per i primi giorni. **Restart eseguito da CC (richiesta Max) 21:42 CET, PID 91177**; Sherpa LIVE verificato a DB (9 scritture sherpa al primo tick, valori = tabella B1).
  RAZIONALE: DRY_RUN su config congelata non produceva dati nuovi (cap ±30% → 50K righe identiche); testnet = zero rischio. La premessa del brief S102b ("file di config con SHERPA_MODE") era errata: è un env flag → niente da committare per attivare, solo runbook.
  ALTERNATIVE: cambiare il default a `live` (scartata: rovescia la safety); shadow-write completo in LIVE (scartata D2); heartbeat su bot_events_log (scartata: non risolve la dashboard). FALLBACK: togliere `SHERPA_MODE=live` al restart → dry_run; rimuovere il blocco heartbeat (isolato). Report `report_for_CEO/2026-06-11_S102b_RforCEO_sherpa-go-live.md`. §7 anti-assenso: 2 drift brief↔repo segnalati pre-codice (env flag + sherpa_proposals muto in LIVE).

- **2026-06-11 (S102) — Sherpa write gate: correzione flip-based del filtro 79c, non filtro nuovo + heartbeat 4h**.
  DECISIONE: (a) il brief S102 Parte A assumeva "nessun filtro write-on-change" — premessa superata (filtro 79c esistente da 18 mag): implementata la CORREZIONE del filtro, convertendo `proposed_stop_buy_active` e `cooldown_active` da pass-through a LIVELLO → a FLIP, ed estendendo il confronto on-change all'identità completa della proposta (3 numerici + regime + stop_buy + cooldown). (b) Heartbeat 600s→4h (D1 Max: allineato a cadenza slow-loop; floor 18 righe/gg, il "<10" del brief non raggiungibile a 3 coin). (c) Log skip = contatore nella riga heartbeat (D2: il per-skip letterale = ~2.000 righe log/gg). (d) Cooldown nel gate come flip (D3, non nel brief: traccia apertura/chiusura finestre override a costo 2 righe). (e) Restart: inizialmente rimandato, poi eseguito in S102b (vedi decisione sopra).
  RAZIONALE: dal 29 mag (extreme_fear persistente) il pass-through a livello bypassava il filtro a OGNI tick → ~2.100 righe/gg con stop_buy_true≈100%; il flip era già calcolato ma usato solo per Telegram. Bootstrap esteso (regime/stop_buy/cooldown, finestra 8h) per evitare righe spurie al restart.
  ALTERNATIVE: implementare il brief letterale (filtro duplicato); heartbeat 8h per il "<10" (scartato: dimezza liveness). FALLBACK: revert `a867179`, zero migration. Report: `report_for_CEO/2026-06-11_S102_RforCEO_sherpa-coherence-audit.md`.

- **2026-06-10 (S101) — Dashboard §3: una sola linea MTM su asse "portfolio value" + fix TF_BUDGET**.
  DECISIONE: card cumulativa con SOLO la linea mark-to-market (la realized resta nelle barre weekly sotto), fill semantico verde/clay sopra/sotto break-even, asse Y ri-etichettato in valore assoluto ($600 = break-even; D1 Max: "$600" senza segno), big number dall'ultimo snapshot reale con "as of" (D2: il numero deve combaciare con la fine della curva; il valore live resta nell'hero), tooltip "est." sui giorni in fallback, sticker `CleanSlateSticker` bottom-right (scala 0.8, tilt hero — iterazione Max, commit `ce5602d`) su entrambe le card. Fix: `reconstructTFForDay` → `TF_BUDGET` (non 0) senza trade TF nel ciclo; `weekKey` formattato in date locali (non `toISOString`).
  RAZIONALE: due linee divergenti + "+$0" + zero copy = grafico illeggibile per neofiti (feedback Max, origine della sessione); e la MTM era −$100 esatti (TF idle → `return 0` con `initial=600`) — il grafico era proprio sbagliato, non solo confuso. La sola realized nasconderebbe le bags aperte: incoerente con la trasparenza del brand.
  ALTERNATIVE: tenere 2 linee con copy migliore (scartata: la realized è già nelle barre); big number live come l'hero (scartata: si disallinea dalla curva sottostante). FALLBACK: revert `8ea0a23`, dati DB intatti.

- **2026-06-10 (S101b) — Sitemap lastmod onesto per-pagina + GSC "Couldn't fetch" derubricato a bug di report**.
  DECISIONE: (a) rimosso il `lastmod: new Date()` globale (S84) da `web_astro/astro.config.mjs`: i post prendono `date:` dal frontmatter via `serialize()`, `/blog` la data del post più recente, le statiche nessun lastmod; (b) il caso GSC "Couldn't fetch" è **chiuso come artefatto del report** (failure cached del primo submit + retry low-priority sui domini piccoli), NON problema sito; (c) regole consolidate in **`SEO_RULES.md`** (root, nuovo file di stato SEO).
  RAZIONALE: (a) lastmod build-time su tutte le URL a ogni deploy = segnale che Google documenta come inaffidabile→ignorato; la motivazione S84 ("missing lastmod contribuiva al couldn't fetch") è superata dalle evidenze; (b) dossier completo: server 200 verificato 2× (15/05+10/06), live test OK su pagine HTML, `/roadmap` in SERP, 381 imp/pos 8,8 (31/05), Firewall Vercel pulito (Bot Protection inactive, 0 rules, 0 denied/challenged).
  ALTERNATIVE: tenere il lastmod build-time (scartata: anti-pattern documentato); ticket/escalation Vercel (scartata: zero evidenze di blocco). FALLBACK: playbook in `SEO_RULES.md §4`; resubmit tracciante `?v=20260610` in osservazione — se ancora rossa ~17/06 → post Google Search Central col dossier e stop energie.

- **2026-06-09 (S100) — NewsKeeper "barometro" v2: architettura C + dedup window/decay-aware**.
  DECISIONE: NewsKeeper diventa un barometro lento 3-stati. Polarità decisa da Haiku (architettura **C**, il lexicon Python perde il veto e resta solo come sensore `direction_conflict` loggato) + voto pesato per confidenza (astiene sotto soglia) + dedup a livello-evento (`event_key` di Haiku). La dedup sceglie il rappresentante per `(in_window, directional, peso=relevance×confidence×decay)`.
  RAZIONALE: la T+7 review ha provato che l'unità per-item è sbagliata e che il guardrail "direction Python authoritative" causava inversioni sui segnali più forti. C recide quell'accoppiamento. La dedup window/decay-aware nasce da un finding della review avversariale (la versione naïve sceglieva un rappresentante stale → perdeva eventi freschi / annullava il decadimento).
  ALTERNATIVE: opzione B (Python da veto a hint) — scartata, conserva l'accoppiamento che causava il bug; dedup solo per relevance/confidenza (buggy). FALLBACK: reversibile (firme isolate); soglie/parametri in `BarometerParams`. **Gate**: shadow ~2 sett, validazione vs prezzo BTC 24h (NON F&G), niente Sentinel pre-verdetto. §7: 3 obiezioni reali (anticipo non provato, F&G circolare, dedup=chiave di C) — recepite nel gate falsificabile.

- **2026-06-08 (S99b-b) — Adaptive Sell Penalty anti-slippage + restore restart Opzione 1**.
  DECISIONE: (a) la penalty si arma anche su sell **profittevoli** (fill≥avg) quando lo slippage avverso supera `SLIPPAGE_PENALTY_THRESHOLD_PCT=1.0` (costante in `sell_pipeline.py`, non bot_config); (b) restore al restart **Opzione 1**: la slippage-penalty NON viene ricostruita dal replay di `trades`, si ri-arma al primo sell reale.
  RAZIONALE: (a) il burst BONK 8-giu (5 sell in 4 min, slippage 3.4-4%) non veniva frenato perché tutti i fill erano sopra avg → penalty mai armata; la ladder si ancora al fill abbassato dallo slippage → loop auto-accelerante. La nuova soglia lo rompe (mainnet 0.1-0.3% < 1% → non scatta). (b) lo slippage richiede `check_price` pre-ordine, assente come colonna strutturata in `trades` (vive nel `reason`, inaffidabile [S70]); parsarlo sarebbe fragile. La penalty è reattiva al mercato corrente → si ri-arma da sola.
  ALTERNATIVE: (b) Opzione 2 = restore da `bot_runtime_state` (scartata: cambia la fonte del restore, mirror best-effort). FALLBACK: (a) soglia→bot_config se serve per-coin (BONK freeze su testnet); (b) leggere `sell_pct_penalty` da `bot_runtime_state` al boot (~5 righe). §7: 1 obiezione bloccante (restore) + 2 note, risolte con Max pre-codice.

> Decisioni **S99a/S98** archiviate in compaction S102; **S97c/S97b/S96a/S95a/S91** in compaction S99b-b → [archive](audits/PROJECT_STATE_archive.md). Sintesi §10. Decisioni S81→S84 e precedenti: §10 + commit log + archive (compaction S83/S86).

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
- **S101**: linea MTM dashboard §3 a −$100 (TF idle nel ciclo → `reconstructTFForDay` ritornava 0 invece di `TF_BUDGET`; con `initial=600` la curva mostrava −$102.71 vs −$2.71 reale) + etichette settimane shiftate di un giorno (`weekKey` via `toISOString` su mezzanotte locale). Commit `8ea0a23`.
- **S99b-b**: Adaptive Sell Penalty estesa anti-slippage — si arma anche su sell profittevoli con slippage avverso >1% (caso 2, `sell_penalty_slippage`). + dashboard: SUBLABEL `sell_pct` corretto (era fossile FIFO) + NEXT SELL IF somma `_sell_pct_penalty` (mirror in `bot_runtime_state`, migration). Commit `e26e67c`. Suite 160/160.
> Risolti **S98a/S97a/S96b/S96a/S81/S79** archiviati in compaction S102 → [archive](audits/PROJECT_STATE_archive.md).

## 6. Domande aperte per CEO

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

- **Bot LIVE su Binance testnet** + Sentinel slow LIVE + **Sherpa Sprint 2 LIVE coin-aware** (`SHERPA_MODE=live` da S102b) + **TF Tier 1-2 LIVE** (S79, T3 weight=0). Restart **S102b 2026-06-11 21:42 CET** (Sherpa GO LIVE + write guard `a867179` + battito liveness `ce92ed2`). PID orchestrator **91177** + figli (caffeinate + 3 grid + TF + Sentinel + Sherpa). Mac Mini runtime commit `5290872`. `SHERPA_TELEGRAM_ENABLED=true` temporaneo (D5). I due NewsKeeper standalone (v1 pid 10899, v2 shadow pid 97566) NON toccati dal restart.
- **Go/no-go €100 LIVE**: **nessuna data fissa** — gated da condizioni di mercato (bear + bull + lateral). Sequenza: Sherpa LIVE testnet ✅ (S102b) → osservazione → S103 parametri Board-only → barometro verdict (~23 giu) → Board approval → mainnet.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime). Runtime Mac Mini commit `5290872` (restart S102b 2026-06-11 21:42).
- **Phase 9 V&C — Pre-Live Gates**: contabilità S66 ✅, fee USDT canonical S67 ✅, dust prevention S67 ✅, sell-in-loss guard avg_cost S68a ✅, DB schema cleanup S68 ✅, avg-cost trading completo S69 ✅, Strategy A simmetrico S69 ✅, IDLE recalibrate guard S69 ✅, sell_pct net-of-fees S70 ✅, post-fill warning slippage S70 ✅, wallet reconciliation Binance S70 ✅, Sentinel ricalibrazione S70 ✅, Fee Unification S72 ✅, dead zone S73 ✅, partial fills S74c ✅, dashboard coherence S74b ✅, **dashboard SUBLABEL coherence S99b ✅**, stop_buy_unlock_hours S76 ✅, idle alert suppression S76 ✅, **Sherpa coin-aware S81 ✅**, **Sherpa decoupled fast-loop S81 ✅**, **Sherpa amplitude cap S81 ✅**, **Sherpa write guard + battito liveness S102/S102b ✅**, **Sherpa LIVE testnet S102b ✅**, slippage_buffer parametrico (🔲 brief separato pre-mainnet).

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
| 2026-06-11 | 1 | **S102b** Sherpa GO LIVE testnet + battito liveness | SHIPPED `ce92ed2` (battito) + **restart 21:42 CET PID 91177, runtime `5290872`** | Brief `config/2026-06-11_S102b_brief_sherpa-go-live.md`. Attivazione `SHERPA_MODE=live` via env flag (no cambio codice, default dry_run intatto). Restart eseguito da CC (richiesta Max), cumulativo (write guard + battito). **Sherpa LIVE verificato a DB**: 9 scritture `changed_by='sherpa'` al primo tick (BTC 0.65/1.05/5.6, SOL 0.65/1.53/5.6, BONK 3.0/1.75/5.6 = tabella B1). Battito liveness in LIVE (~18 righe/gg su sherpa_proposals: vivo-vs-zombie + lampada dashboard). `SHERPA_TELEGRAM_ENABLED=true` temporaneo (D5). NewsKeeper v1/v2 non toccati. 3 test nuovi (suite 198/198). 2 drift brief↔repo segnalati pre-codice (env flag; sherpa_proposals muto in LIVE). Report `report_for_CEO/2026-06-11_S102b_RforCEO_sherpa-go-live.md`. |
| 2026-06-11 | 1 | **S102** Sherpa coherence audit (Parte B) + write gate flip-based (Parte A) | SHIPPED `a867179` (bot+test) + report | Brief `config/2026-06-11_S102_brief_sherpa-coherence-audit.md`. **Drift brief↔repo segnalato pre-codice**: il filtro write-on-change esisteva già (79c); causa vera del volume = pass-through a livello di stop_buy/cooldown → convertiti a flip + confronto esteso (numerici+regime+stop_buy+cooldown) + heartbeat 600s→4h + bootstrap esteso (8h) + skip-counter nell'heartbeat. Atteso ~18 righe/gg (−99%). 10 test nuovi. **Parte B** (indagine multi-agente, 25 agenti, verifica avversariale per claim): B1 mappa 5 regimi×3 coin TARGET-vs-PRIMA-PROPOSTA (cap ±30% domina i dati DRY_RUN; multiplier live BTC 1.0/SOL 1.53/BONK 1.75; fast loop S61 rimosso in `3ba1132`; boundary F&G riviste vs S61); B2 coin-agnostic SÌ (DOGE=1 riga config, provato live); B3 copertura 3/12 = Level A (gate pre-LIVE idle 8 vs 6 → Opzione C; skim/dead_zone giudicati Board-only; circuit-breaker frammentato su 3 owner); B4 btc_price=gap integrazione Sprint 2 + WC 100%=artefatto DRY_RUN (driver buy_pct 98%); B5 stickiness fattibile (a)+(c) ~5-7h/4 file, post-verdetto barometro. Report `report_for_CEO/2026-06-11_S102_RforCEO_sherpa-coherence-audit.md`. **+ pull `0ad599b`** (report T+36h barometro routine remota: ✅ OK). |
| 2026-06-10 | 3+docs | **S101 + S101a + S101b** (dashboard §3 redesign + fix MTM −$100 · blog two-voice canonical · GSC chiuso come artefatto + SEO_RULES.md) | SHIPPED `8ea0a23` · `944e74d` · `ccaaf24`, tutte web-only | Sintesi in §4 (S101/S101b) e header. Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). Report in `report_for_CEO/resolved/`. |
| 2026-06-09 | 1+3 | **S100** NewsKeeper T+7 review → redesign "barometro" v2 (build + shadow) | SHIPPED `c8774db` + **shadow LIVE Mac Mini (pid 97566)** + migration | Catena: review T+7 (unità per-item sbagliata + bug direzione) → concept CEO → critica CC (3 obiezioni) → brief → build. Package `bot/newskeeper_v2/`: barometro 3-stati aggregato 24h, architettura C (Haiku decide polarità) + voto pesato-confidenza + dedup event-level. Gate falsificabile: shadow ~2 sett, validazione vs prezzo BTC 24h (NON F&G), no Sentinel pre-verdetto. Migration `newskeeper_signals` +4 col + tabella `newskeeper_regime`. Test 185/185 (+25). Review avversariale: 1 bug dedup fixato. Verdetto T+14 ~23 giu; routine check T+36h schedulata. Brief `briefresolved.md/2026-06-09_S100_brief_newskeeper-v2-barometro.md`, report `report_for_CEO/resolved/2026-06-09_S100_RforCEO_newskeeper-v2-barometro-build.md` (+ review T+7 + critica). |
| 2026-06-07/08 | 1+3 | **S99a + S99b/S99b-b** (SEO trailing-slash+llms.txt · sell-ladder audit + anti-slippage v2 + dashboard) | SHIPPED `9787aa5` · `e26e67c` + restart 08-giu | Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-06-06 | 1 | **S98 (brief S98a)** Adaptive Sell Penalty (sell-loss-guard) + analisi tbot (S93b) | SHIPPED `507ebd6`→`a7d644d` + **restart 15:15 (PID 85566)** | Sintesi/decisioni in header §1 + §4. Guardia post-fill (Grid/Strategy A) dopo incidente BONK 06-06 (7 sell in perdita, fill sotto avg da book vuoto): `effective_sell_pct = sell_pct + _sell_pct_penalty`. **Design v2 (Max+CEO): penalty = ultima perdita, NON cumulativa** (il cumulativo → deadlock/freeze coin). 3 file bot + test 157/157. **Restart verificato**: BONK `Restored sell penalty 3.96% (effective 6.46%)`, boot puliti, 0 errori. + analisi competitiva tbot (read-only, report S93b in `report_for_CEO/`): moat confermato. Brief `briefresolved.md/2026-06-06_S98a_brief_sell-loss-guard.md`, report `report_for_CEO/resolved/2026-06-06_S98a_RforCEO_sell-loss-guard.md`. |
| 2026-06-02→06-05 | 1+3+docs | **S95 → S97c** (7 righe: S95 dashboard mascotte + POST1 SEO live · S95a content plan FAQ schema + 5 draft · S96a clean slate testnet · S96b phantom-safe avg-cost + fee B · S97a phantom audit · S97b blog 2-voci + Keep reading · S97c cycle filter commentary + reconcile cycle-scoped) | tutte SHIPPED | Righe verbose archiviate in compaction S102 → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-05-23→06-01 | 1+3 | **S82 → S94a** (14 righe: S82 homepage redesign Watchtower/Sherpa · S83 NewsKeeper scaffold RSS · S84 SEO fix · S85 RSS Dev.to + compaction policy · S86 status badge + regime overlay · S87 V3 launch + Umami · S88 remediation Audit A2 · S89 remediation Audit A1 · S90 spike guard A+B · S91 stop_buy extreme_fear + SEO quick wins · S92 layer dati marketing A3 · S93a tono Haiku · S94a NewsKeeper Haiku classifier) | tutte SHIPPED | Righe-sintesi archiviate in compaction S99b-b → [archive](audits/PROJECT_STATE_archive.md). |
| 2026-05-14→-22 | 1 | **S76 → S81** (S76 grid_runner package + 75b; S77 fase1/2+3 Sentinel Sprint1/2; S78/78fase2 primo blog + SWEEP slippage buffer; S79 idle/TF/write-on-change; S80/80a funnel+UTM+Brain Analysis; S81 Sherpa Sprint2 coin-aware) | tutte SHIPPED | Righe verbose archiviate (compaction S88 + S99b-b) in [archive](audits/PROJECT_STATE_archive.md). Topic chiave: refactor package, Sentinel slow loop 4h, Sherpa per-coin volatility, slippage buffer SWEEP, drift FIFO sanato. |
| 2026-05-10 → -12 | 1 | **S70 → S74b** (8 sessioni: S70/70b/70c, S71, S72, S73, S73b, S73c, S74, S74b) | tutte SHIPPED, dettagli in archive | Righe verbose spostate in [audits/PROJECT_STATE_archive.md](audits/PROJECT_STATE_archive.md) sezione "Rimosso in sessione S84 → §10 Sessioni shipped — righe S70 → S74b". Topic chiave: reconciliation Step A/B/C + sell_pct net-of-fees (S70a/b/c); P&L hero unification (S71); Fee Unification + canonical refactor + TF removal pubblici (S72); Dead Zone recalibrate + dust trap + BONK lot_size + BTC phantom mainnet-safe (S73/b/c); brief 74a IT→EN + Telegram + TCC python3.13 FDA + partial fills + dead_zone_hours per-coin (S74/b). |
