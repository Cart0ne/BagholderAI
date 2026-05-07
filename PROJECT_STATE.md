# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-07 — fine sessione 63 (init)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **paper trading multi-bot in Phase 1 refactor + Sentinel/Sherpa Sprint 1 in DRY_RUN data collection (~7gg)**. Stack vivo sul Mac Mini: orchestrator + 3 Grid (BTC/SOL/BONK) + 1+ Trend Follower con tf_grid + Sentinel + Sherpa, tutti managed processes. Prossimo deploy atteso: **brief 62b — Phase 2 grid refactor + fix 60c + dust management** (in attesa di piano CC). Vincolo del momento: **DRY_RUN Sherpa NON va contaminato** (no edit costanti su parametri Grid finché counterfactual non ha 7gg di dati). Go-live capitale reale €100 ancora dietro i gate Phase 9 V&C.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS), Telegram (alerts/approvals), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn/restart 3 Grid + TF + Sentinel + Sherpa
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config, drawdown/SL alerts
  health_check.py          daily FIFO/holdings/cash integrity (57a)
  db_maintenance.py        daily 04:00 UTC retention (59b) + Sentinel/Sherpa retention 30/60d
  exchange.py              Binance testnet + filter rounding
  strategies/              Brain #1 — Grid (split Phase 1, brief 62a, 2026-05-07)
    grid_bot.py              public API + dataclasses (was 2200-line monolith)
    fifo_queue.py            FIFO replay + verify_fifo_queue (57a)
    state_manager.py         boot-time state restore from DB
    buy_pipeline.py          buy exec (fixed + pct, multi-lot 42a)
    sell_pipeline.py         sell exec + greed-decay TP + gain-saturation (45g)
    dust_handler.py          dust pop helpers (bug 60c documented inline)
  trend_follower/          Brain #2 — TF (live mode + tf_grid handoff 502e88a)
    trend_follower.py | scanner.py | classifier.py | allocator.py | floating.py |
    counterfactual.py | gain_saturation.py
  sentinel/                Brain #3 — risk/opportunity score (Sprint 1, fast loop 60s)
    main.py | price_monitor.py | funding_monitor.py | score_engine.py | inputs/
  sherpa/                  Brain #4 — parameter writer (Sprint 1, DRY_RUN default, loop 120s)
    main.py | parameter_rules.py | cooldown_manager.py | config_writer.py
db/, utils/, scripts/, web_astro/  (DB client, telegram notifier, daily reports, sito Astro live)
config/                    settings, briefs (in-flight + parked), validation_and_control_system.md
```

Comm Sentinel↔Sherpa↔Grid via Supabase only (no imports cross-brain). Sherpa scrive `bot_config` solo in `SHERPA_MODE=live`; oggi è `dry_run`.

## 3. In-flight (settimana 2026-05-07)

- **Brief 62b — Grid Phase 2** (`config/brief_62b_grid_refactor_phase2.md`): atteso piano CC per fix 60c (init queue post-restart sbagliato → P&L bot biased +80%) + dust management completo. Tocca `bot/strategies/sell_pipeline.py:544-572`, `dust_handler.py`, `grid_bot.py:758` (loop double-call).
- **PROJECT_STATE.md** (questo file) + AUDIT_PROTOCOL.md + cartella gitignored `audits/` — appena introdotti (commit `57aff52`, `e20704c`). Prima sessione "live" del protocollo: questa.
- **Sentinel/Sherpa data collection DRY_RUN**: in raccolta 7gg, replay counterfactual da scrivere quando dati completi (~2026-05-13). Deadline implicita Sprint 2 = post-replay.
- **Brief 60c FIFO init bug**: bundled dentro 62b. NON parte da solo.
- **Brief evaluate_trading_skills.md** (`config/`): doc-only, non urgente, valuta skill esterne pre-Sentinel Phase 3.
- **Brief dust_management_gate.md** (`config/`): doc pre-mainnet gate, non scrive codice ora.
- **Admin dashboard Sentinel+Sherpa** (design report 2026-05-07): disegno approvato, **non ancora implementato**. ~9h frontend, parte quando Board dà via. Dipende dalla fine raccolta DRY_RUN (cambiare costanti invalida counterfactual).

## 4. Decisioni recenti

- **2026-05-07 — Audit protocol + cartella gitignored `audits/` + due state files (PROJECT_STATE/BUSINESS_STATE)** — *why:* dare un canale formale per audit esterni e per la continuità multi-sessione/multi-macchina (commit `57aff52`, `e20704c`).
- **2026-05-07 — Phase 1 di brief 62a: split monolite `grid_bot.py` (2200 righe) in 6 moduli a API pubblica invariata** — *why:* il file era diventato impossibile da auditare; lo split prepara Phase 2 (fix 60c + dust) senza cambiare comportamento (commit `be45fca`).
- **2026-05-07 — Dashboard `/admin` Sentinel+Sherpa: read-only fino a Sprint 2** — *why:* modificare costanti durante DRY_RUN invaliderebbe il counterfactual (report design `2026-05-07_admin_..._design_report`).
- **2026-05-07 — FIFO-correct per-row P&L in dashboard `/admin` § Recent Activity (60d-bis) + per-coin/per-row breakdown grid.html/tf.html (60d)** — *why:* le tabelle leggevano `realized_pnl` DB (biased) anziché ricalcolare FIFO client-side; bug visibile pre-LIVE €100 (commit `0750027`, `21caff0`).
- **2026-05-06 — Sherpa Telegram alert solo on proposal *change*, non a ogni diff** — *why:* tagliare rumore senza perdere segnale (commit `65f82c2`).
- **2026-05-06 — Sentinel/Sherpa: -70% DB write rate via dedup + filter + retention 30/60gg** — *why:* tabelle nuove rischiavano di esplodere il piano Supabase free (commit `0246b22`).
- **2026-05-06 — Sentinel + Sherpa Sprint 1 deployati in DRY_RUN come processi managed dall'orchestrator** — *why:* base+adjustment dell'architettura parametri pronta da subito (Board option 1) per non rifare refactor a Sprint 2 (commit `83b253c`).
- **2026-05-05 — Phase 9 "Validation & Control System" promossa a *living milestone* su /roadmap; aggiunta §7 (post-go-live monitoring) + §8 (process & log hygiene)** — *why:* la validazione non si chiude al go-live, intensifica; logs `httpx` leakavano token Telegram (incidente x_poster_approve.log 23 MB) (commit `561f3a8`, `c1e362e`, `bbc8477`).
- **2026-05-05 — DB retention policy daily cleanup 04:00 UTC (brief 59b)** — *why:* trades v1/v2 cancellati, log lunghi limitati (commit `1ae4c01`).
- **2026-05-05 — FIFO integrity hotfix: `verify_fifo_queue` filtra dust < $1 (57a)** — *why:* falsi positivi sui lot polverosi bloccavano il health check (commit `189fbf9`).
- **2026-05-05 — Brief 57a 4-fix shipped (verify_fifo_queue + _execute_sell FIFO + health_check + audit log in `bot_events_log`)** — *why:* gate FIFO integrity verso LIVE €100 (commit `659b3eb`, `6968854`, `f355e5d`, `596a5b7`).
- **2026-05-04 — TF exit protection holes fixed: peak reset on buy + SL/TP su `open_value`** — *why:* trailing peak rimaneva dal ciclo precedente, falsi exit (commit `6dcc56f`).
- **2026-05-03 — Unified Grid+TF accounting: dashboard, report Telegram privato e report pubblico ora leggono tutti `commentary.get_grid_state` / `get_tf_state` (FIFO replay)** — *why:* esistevano 3 formule diverse per "stessi numeri Grid", la dashboard era l'unica corretta (commit `b9348a0`, `584ebe2`).
- **2026-05-03 — TF "tf_grid" handoff Tier 1-2 a GRID management** — *why:* TF a quel punto del ciclo è in regime grid, non più trend (commit `502e88a`).
- **2026-05-02..05 — Sito Astro nuovo (`web_astro/`) GO LIVE con home + diary + dashboard + library + howwework + roadmap + blueprint + legal** — *why:* sostituisce `web/` (untracked, commit `591d6f3`); dark single-mode editoriale-tecnico, mobile-first.

## 5. Bug noti aperti

- `bot/strategies/grid_bot.py:758` — `# TODO 62a (Phase 2): this loop is the 60c double-call source.` (gating Phase 2 brief 62b)
- `bot/strategies/sell_pipeline.py:23` — `# TODO 62a (Phase 2): make _execute_percentage_sell atomic — state changes [...]` (race condition tra audit log e log_trade)
- `bot/strategies/sell_pipeline.py:544` — `# TODO 62a (Phase 2): this audit is written before log_trade. If [...]` (audit/sequenza)
- `bot/strategies/sell_pipeline.py:572` — `# TODO 62a (Phase 2): these state mutations happen BEFORE log_trade.`
- `bot/strategies/fifo_queue.py:12` — `# TODO 62a (Phase 2): introduce FIFOQueue class wrapping _pct_open_positions.`
- `bot/strategies/fifo_queue.py:96` — `# TODO 62a (Phase 2): mem_queue is NOT filtered for dust here, only [...]`
- `bot/strategies/dust_handler.py:17` — `# TODO 62a (Phase 2): emit 'dust_lot_removed' events to bot_events_log [...]` (osservabilità dust)
- `bot/trend_follower/allocator.py:43` — `# TODO: move to trend_config in a future session for dynamic tuning.` (non bloccante, abbellimento)
- **Bias storico DB `trades.realized_pnl`** (pre-53a 458 SELL): non più scritto biased dal 2026-05-01, ma DB history resta fossile. Mitigato: dashboard ricalcola FIFO client-side. Non patchare backward (vedi memoria `project_57a_fifo_punto_fisso`).
- **Equity P&L (Binance vero) ≠ FIFO realized home**: $48.16 vs $52.69 al 2026-05-05; gap strutturale (FIFO ignora MtM lotti aperti). Vedi sezione 6 — pending input CEO.

## 6. Domande aperte per CEO

- **Equity P&L vs FIFO realized**: 3 proposte pending dal report `2026-05-05_equity_pnl_vs_fifo_realized_report_for_ceo.md`. La logica del bot per la decisione di vendita usa `avg_buy_price` — è gating per il go-live mainnet €100? Servirebbe scelta di un numero canonico (FIFO realized vs equity Binance vero) prima di promettere "il numero in dashboard ≡ Binance".
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`): solo 5 skill su 15+ valutate. Riprendere quando torniamo su Sentinel Phase 3 / TF improvements? Dipende da brief `evaluate_trading_skills.md`.
- **Esposizione pubblica Validation & Control System**: il documento `config/validation_and_control_system.md` è milestone viva su /roadmap, ma quanto del contenuto va esposto pubblicamente vs interno? Da decidere per la sessione che apre la pagina pubblica.

## 7. Vincoli stagionali / deadline tecniche

- **DRY_RUN Sherpa: ~7 giorni di raccolta dati prima del replay counterfactual** (start ~2026-05-06). Deadline implicita ~2026-05-13. Durante questa finestra: non modificare costanti dei Grid bot (invaliderebbe il counterfactual); l'admin dashboard Sentinel+Sherpa va read-only.
- **Phase 9 V&C — Pre-Live Gates**: necessari prima del €100 mainnet. FIFO integrity ✅ (57a), retention ✅ (59b), exit protection ✅ (6dcc56f), health check ✅ (daily). Restano: equity P&L vs FIFO (sezione 6), wallet reconciliation Binance settimanale (TODO go-live), dust converter pre-mainnet (brief `dust_management_gate.md`).
- **Roadmap go-live mainnet**: "qualche mese" non settimane (memoria `project_roadmap_to_mainnet`). Architettura completa = TF + Sentinel + bot orchestrator superiore, non solo bug-fix.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime, repo `/Volumes/Archivio/bagholderai`). Sempre `git pull` a inizio sessione e mount Archivio prima di test/audit.

## 8. Cosa NON è stato fatto e perché

In Phase 1 di brief 62a (split `grid_bot.py`) NON è stato toccato il comportamento: i 7 TODO `62a (Phase 2)` annotati nei moduli sono **debiti consapevoli** (atomicità `_execute_percentage_sell`, ordine audit/log_trade, dust events, FIFOQueue class wrapper, fix loop 60c double-call). Sono il punto di partenza di brief 62b. La regola "non rompere ≠ non toccare" è stata rispettata letteralmente: nessuna riga di logica modificata, solo riorganizzazione. Anche l'admin dashboard Sentinel+Sherpa è ferma: design completo, zero codice — perché toccare le costanti Grid mentre è attivo DRY_RUN invaliderebbe il counterfactual e quindi tutto il senso dello Sprint 1. Entrambi gli "incompiuti" sono volutamente parcheggiati con date di sblocco note (Phase 2 = ora pending piano CC; admin dashboard = post replay ~2026-05-13).

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| _(nessun audit ancora completato — primo previsto: 2026-05-07 V1 Calibration su Sentinel↔Sherpa↔Grid post-Phase 1)_ | | | | | |
