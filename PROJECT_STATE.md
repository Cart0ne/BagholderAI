# PROJECT_STATE.md

**Ultimo aggiornamento:** 2026-05-08 — sessione 66 (chiusura: Operation Clean Slate Step 0+1 + sito offline + bot fermo + audit shipped + fix avg-cost canonico shippato)
**Owner del file:** Claude Code (Intern). Rigenerato a ogni fine sessione.

---

## 1. Stato attuale

Fase: **paper era CHIUSA. Bot fermo (Operation Clean Slate). Sito pubblico offline (maintenance landing). Reset DB in S67**. Tutte le posizioni v3 liquidate via SQL bypass (7 sell synthetic, 1 lifecycle event), audit Step 0d ha certificato bias `realized_pnl` +29% del bot ($91.80 DB vs $64.83 vero matematico) — root cause: queue desync per 4 cause concorrenti (dust pop senza log, double-call 60c, bug fossile 53a, Strategy A skip-then-walk). Fix Step 1 shipped: pivot da walk-and-sum FIFO a avg-cost canonico (`bot.state.avg_buy_price`). Test 5/5 verdi, identità contabile chiude al centesimo su 50 ops random. Prossimi step S67: 2 (dust prevention sell pipeline) → 3 (testnet path reactivation) → 4 (reset DB + restart $100 fresh testnet) → 5 (reconciliation gate nightly). Vincolo del momento: bot fermo, in attesa di S67 per riavvio. Target go-live €100 mainnet: **16-20 maggio 2026**.

## 2. Architettura attiva

Repo locale: `/Users/max/Desktop/BagHolderAI/Repository/bagholder` (MBP). Repo runtime: `/Volumes/Archivio/bagholderai` su Mac Mini. Stack: Python 3.13, Supabase (DB+RLS), Telegram (alerts/approvals), Vercel (sito Astro `bagholderai.lol`).

```
bot/
  orchestrator.py          single-process supervisor: spawn/restart 3 Grid + TF + Sentinel + Sherpa
  grid_runner.py           per-symbol process wrapper, hot-reload bot_config, drawdown/SL alerts
  health_check.py          daily FIFO/holdings/cash integrity (57a)
  db_maintenance.py        daily 04:00 UTC retention (59b) + Sentinel/Sherpa retention 30/60d
  exchange.py              Binance live (testnet bypass legacy: ancora attivo, S67 lo rimuoverà)
  strategies/              Brain #1 — Grid (Phase 1 split 62a + S66 fix avg-cost)
    grid_bot.py              public API + dataclasses
    fifo_queue.py            FIFO replay + verify_fifo_queue (57a, ora solo strumento di audit)
    state_manager.py         boot-time state restore (S66: replay canonical avg-cost)
    buy_pipeline.py          buy exec (avg-cost canonical su buy: già OK pre-S66)
    sell_pipeline.py         sell exec — S66 fix: cost_basis = avg × qty (pre: walk queue)
    dust_handler.py          dust pop helpers (bug 60c documentato, Step 2 in S67)
  trend_follower/          Brain #2 — TF (live mode + tf_grid handoff)
  sentinel/                Brain #3 — risk/opportunity score (Sprint 1, DRY_RUN)
  sherpa/                  Brain #4 — parameter writer (Sprint 1, DRY_RUN, freeze in S66)
db/, utils/, scripts/, web_astro/  (DB client, telegram notifier, daily reports, sito Astro maintenance)
config/                    settings, briefs (in briefresolved.md/), validation_and_control_system.md
audits/                    gitignored — formula_verification_s66.md, snapshot.json, report.md S66
tests/                     test_accounting_avg_cost.py NEW (5/5 verdi), test_pct_sell_fifo.py legacy
scripts/                   liquidate_all.py NEW (S66 0b), verify_formulas_s66.py NEW (S66 0d)
```

Comm Sentinel↔Sherpa↔Grid via Supabase only (no imports cross-brain). Bot orchestrator FERMO, restart pianificato S67 post brief 66a Step 4.

## 3. In-flight (settimana 2026-05-08, S67 imminente)

- **🔴 Brief 66a Step 2 — dust prevention sell pipeline** (S67 prossimo): nel `_execute_percentage_sell`, se il residuo post-sell < min order size Binance, arrotondare a "sell all". File: `bot/strategies/sell_pipeline.py`, `bot/strategies/dust_handler.py`, `bot/exchange.py` (per fetchare min order size). Stima ~1h. Risolve fonte 4a di queue desync (dust pop senza log) prevenendo la creazione di dust upstream.

- **🔴 Brief 66a Step 3 — testnet path reactivation** (S67): rimuovere bypass `bot/exchange.py:8-11` (commento legacy "We don't use Binance testnet"), aggiungere chiavi API testnet in `.env`, redirigere ordini a `testnet.binance.vision`. Max genera le chiavi su `testnet.binance.vision`. Stima ~1-2h codice + setup. Verifica coin disponibili: BONK quasi certo NO, SOL probabile sì.

- **🔴 Brief 66a Step 4 — reset DB + restart $100 fresh testnet** (S67): TRUNCATE delle tabelle di trading + Sentinel/Sherpa, riconfigura `bot_config` con budget $100, restart orchestrator. Inclusa ricalibrazione Sentinel pre-restart (speed_of_fall floor + opportunity thresholds). Decisione "reset preoccupa Max" — da affrontare a freddo.

- **🟡 Brief 66a Step 5 — reconciliation gate nightly** (S67/S68): script cron 04:30 UTC che verifica `Realized + Unrealized = Total P&L` al centesimo, alert Telegram se gap > $0.01. Stima ~2h. Prevenzione future regressioni.

- **Aggiornare `tests/test_pct_sell_fifo.py`** post-pivot avg-cost: assertions sul realized_pnl cambiate. Non gating, manutenzione (ticket §6.23 BUSINESS_STATE).

- **Sentinel/Sherpa replay counterfactual**: rimandato. Dataset DRY_RUN sarà azzerato in Step 4. Replay pianificato post-restart con dati nuovi (~150 righe Python, sessione futura).

## 4. Decisioni recenti

- **2026-05-08 (S66 chiusura) — Operation Clean Slate Step 0+1 SHIPPED**. Sequenza: sito offline (commit `e0aeb42`) → stop orchestrator via SSH (TERM cascade ai 11 child processes) → liquidate_all.py SQL bypass (7 sell synthetic, $264.77 revenue, −$3.39 realized, $0.07 skim) → snapshot post-liq (audits/2026-05-08_pre-clean-slate/) → verifica formule via verify_formulas_s66.py: bias certificato +$26.97 ($91.80 DB vs $64.83 vero), 80.6% sell mismatch, root cause queue desync. — *why:* l'eredità di 1158+ trade fossili con bias rendeva ogni fix un rattoppo; l'unico modo era audit a freddo su dataset chiuso.
- **2026-05-08 (S66) — Fix avg-cost canonico Step 1 shipped**. Sostituito `cost_basis = walk-and-sum della queue` (53a) con `cost_basis = bot.state.avg_buy_price × sell_qty` (66a) in `_execute_sell` e `_execute_percentage_sell`. State manager replay aggiornato per tracking canonical avg in parallelo a queue FIFO. Test 5/5 verdi, identità chiude al centesimo su 50 ops random. — *why:* il bot già aggiornava `avg_buy_price` correttamente su buy; il sell ignorava quel valore e usava la queue (vulnerabile a desync). Fix chirurgico: 1 riga in 2 funzioni + tracking parallelo nel boot replay. Strict-FIFO queue NON più usata per realized_pnl (resta solo per Strategy A trigger "no sell at loss").
- **2026-05-08 (S66) — Maintenance page sito + post X "self-roast" pubblicato** (commit `e0aeb42`). Home + dashboard sostituite con `MaintenanceLanding` component, status strip ambra "numbers under audit · bot paused", "Dashboard" rimosso da nav (commentato per ripristino). Post X "An AI that can trade but can't read its own report card". — *why:* radical transparency. Onesto del rebuild in corso (CEO + Board).
- **2026-05-08 (S66) — Apple Note "BagHolderAI — Todo" diventa READ-ONLY per CC**. Solo Max e CEO scrivono. — *why:* riduzione drift / cleanup canale.
- **2026-05-08 (S65 fine) — Sito pubblico OFFLINE / pagina maintenance fino a numeri certificati**. Telegram canale pubblico in pausa. /admin (privato) resta su per Max.
- **2026-05-08 (S65) — Brief 60b RISPECIFICATO da strict-FIFO ad avg-cost pulito** (poi superato in S66 dal fix shipped).
- **2026-05-08 (S65) — Brief 65c (testnet) bundled in brief 66a Step 3**. Verificato in S66 che il bypass è in `exchange.py:8-11`, riattivazione gestita in S67.
- **2026-05-08 (S65) — Opzione 3: dashboard mostrano SOLO Total P&L** (commit `6100caf`). Conferma S66: la home **già** esponeva il numero matematicamente corretto ($64) tramite `Total P&L = Net Worth − budget` calcolato client-side, bypassando il `realized_pnl` biased del DB. Decisione S65 = salvavita.
- **2026-05-08 (S65) — Schema drift `reserve_ledger.managed_by` fixato in DB** (UPDATE one-shot via JOIN su `trade_id`).
- **2026-05-07 (S63) — Dashboard `/admin` Sentinel+Sherpa+DB GO LIVE in 1 sessione** (read-only). Sostituita con maintenance landing in S66 chiusura.
- **2026-05-07 — Audit protocol + cartella gitignored `audits/` + due state files (PROJECT_STATE/BUSINESS_STATE)**. Primo audit interno completo: S66 0d (formula_verification_s66.md).
- **2026-05-07 — Phase 1 di brief 62a: split monolite `grid_bot.py` (2200 righe) in 6 moduli a API pubblica invariata** (commit `be45fca`).
- **2026-05-06 — Sentinel + Sherpa Sprint 1 deployati in DRY_RUN** (commit `83b253c`). Dataset sarà azzerato in Step 4.
- **2026-05-05 — DB retention policy daily cleanup 04:00 UTC** (commit `1ae4c01`).

## 5. Bug noti aperti

- **🟢 [S66 RISOLTO] Bias `realized_pnl` +29%** — Fix avg-cost canonico shippato. `_execute_sell` e `_execute_percentage_sell` ora usano `cost_basis = avg × qty`. State manager replay coerente. Test 5/5 verdi, identità chiude al centesimo. **Closed**.
- **🟢 [S66 RISOLTO] verify_fifo_queue strict-FIFO false positive** — La queue non è più fonte di verità per realized_pnl. Resta solo come supporto Strategy A trigger. Verifier può continuare a esistere come tool di audit ma non gating.
- `bot/strategies/grid_bot.py:758` — `# TODO 62a (Phase 2): this loop is the 60c double-call source.` (gating Phase 2 brief 62b — sostituito da brief 66a Step 2 dust prevention)
- `bot/strategies/sell_pipeline.py:23` — `# TODO 62a (Phase 2): make _execute_percentage_sell atomic` (race condition tra audit log e log_trade — non gating per S67 Step 2-4)
- `bot/strategies/dust_handler.py:17` — `# TODO 62a (Phase 2): emit 'dust_lot_removed' events` (osservabilità dust — Step 2 in S67)
- `bot/trend_follower/allocator.py:43` — `# TODO: move to trend_config in a future session for dynamic tuning.` (non bloccante)
- **Recalibrate automatico on-restart su ogni moneta** (CEO, 2026-05-07): a ogni restart orchestrator scatta recalibrate. Da indagare in S67 post-restart.
- **TF distance filter 12% fisso vs EMA20** (CEO, 2026-05-07): in mercato rialzista paralizza TF. Tema cross con Sentinel/Sherpa.
- **Health check FAIL count 87 — fossili pre-2026-05-05** (CC, 2026-05-07): debito storico. Sarà azzerato dal Reset DB Step 4.
- **🔴 [S63] `speed_of_fall_accelerating` miscalibrato** (`bot/sentinel/price_monitor.py:117-132`): scatta ~30% del tempo. Ricalibrare in Step 4 pre-restart (CEO authorized).
- **🟡 [S63] Risk score binario** (solo valori 20 e 40): conseguenza del bug speed_of_fall. Risolto da ricalibrazione Step 4.
- **🔴 [S63] Opportunity score morta a 20**: soglie funding troppo larghe. Ricalibrare in Step 4.
- **🟡 [S63] Grid polling REST 60s perde i picchi BTC sub-minuto**. Mitigazione pre-mainnet: ridurre BTC interval 60s → 20s. Soluzione vera (WebSocket): parcheggiata.
- **🟡 [S63] Supabase REST cap 1000 righe latente in home/dashboard pubblica**: ora il sito è offline in maintenance, problema posticipato. Brief 60e sblocca al ritorno online.
- **Bias storico DB `trades.realized_pnl`** (pre-S66 1158+ trades): non più scritto biased post-S66; storico fossile sarà azzerato in Step 4.
- **Equity P&L (Binance vero) ≠ realized DB**: gap chiarito in S66 — il "vero" è $64.83 (matematico, paper), $48.16 era proxy mainnet net. Coerenti entro l'errore.
- **🟢 [S66 RISOLTO] Implementazione avg-cost incoerente** (sell_pipeline) — Fix shipped, identità chiude.

## 6. Domande aperte per CEO

- **SHERPA_MODE: dry_run → live?** Rimandato a post-Step 4 reset (S67/S68). Dataset DRY_RUN sarà azzerato; nuovo replay counterfactual su dati post-restart.
- **Coin disponibili su testnet** per Step 3: BONK probabilmente assente, SOL probabile presente. Da verificare quando si genera chiavi API. Mia raccomandazione: BTC + SOL only, BONK disabilitato finché mainnet.
- **Reset DB Step 4 — boundary conferma**: tabelle `trades`, `reserve_ledger`, `bot_state_snapshots`, `bot_events_log`, `daily_pnl`, `sentinel_scans`, `sherpa_proposals`, `sherpa_parameter_history` da TRUNCATE; `bot_config` riconfigurato budget $100; `trend_config` invariato. Confermi tutto in S67?
- **Equity P&L proxy mainnet**: ora chiarito ($64 paper lordo = ~$47.5 mainnet net). Quando ripartiamo testnet, decisione Board: lo storico paper si "cementa" come narrative-only (no carry-over al testnet), $100 fresh start. Confermare.
- **Tradermonty full-repo scan** parcheggiato (memoria `project_tradermonty_full_scan`).
- **Esposizione pubblica Validation & Control System** rimandata.
- **BASE_TABLE.neutral vs parametri Board fissi disallineati** — ricalibrazione bundled in Step 4 pre-restart.
- **Reaction chart `/admin` poco leggibile in regime calmo** — fix grafico, post-restart.
- **Sentinel/Sherpa mascot in `/admin`** — decisione narrativa (LOCKED vs accesi). Post-restart.
- **Skim_pct 30% è la soglia giusta?** (Max 2026-05-08 sera) — decisione strategica del CEO/Board, da rivalutare quando ripartiamo paper budget testnet/mainnet. Trade-off: più skim = più protezione drawdown ma meno cash operativo.

## 7. Vincoli stagionali / deadline tecniche

- **Bot fermo dal 2026-05-08 18:00 UTC**. Restart pianificato S67 post Step 2-4. Nessun trade in corso, nessun dato Sentinel/Sherpa nuovo.
- **Go/no-go €100 LIVE**: target ~2026-05-20 (4 giorni di window per S67 Step 2-4 + 7gg clean run testnet + go/no-go decision).
- **Sequenza critica S67**: Step 2 (dust ~1h) → Step 3 (testnet ~1-2h) → Step 4 (reset + restart ~1h) → 7gg testnet clean → go-live.
- **Decisione "reset DB preoccupa Max"** affrontare a freddo a inizio S67. CC pronto piano dettagliato + dry-run prima execution.
- **Multi-macchina**: MBP (sviluppo) ↔ Mac Mini (runtime, repo `/Volumes/Archivio/bagholderai`). Sempre `git pull` a inizio sessione e mount Archivio prima di test/audit.
- **Replay Sherpa counterfactual** posticipato post-restart (era ~13 maggio, ora ~20+ maggio testnet).
- **Phase 9 V&C — Pre-Live Gates**: contabilità (S66 ✅), reconciliation gate nightly (Step 5 S67/S68), wallet reconciliation Binance settimanale (post go-live), dust converter pre-mainnet (Step 2 S67).

## 8. Cosa NON è stato fatto e perché

In S66 NON è stato fatto **Step 2-5 di brief 66a** (dust prevention, testnet path, reset DB, reconciliation gate). CEO + Max hanno scelto consapevolmente di chiudere S66 al checkpoint Step 1 con test verdi e di aprire S67 fresh per le fasi successive. Motivazioni: (1) il "reset DB preoccupa Max" — merita una sessione dedicata a freddo; (2) Step 1 da solo è già un cambio strutturale importante che merita "sedimentare" prima di toccare ulteriori file; (3) Step 2 e Step 3 hanno dipendenze esterne (chiavi API testnet che Max deve generare); (4) sequenza sequenziale 1→2→3→4→5 è più sicura di parallelo. Tutti gli incompiuti sono volutamente parcheggiati con date di sblocco note (S67 imminente, ≤ 2026-05-12) e brief già scritto + audit Step 0d come reference. La regola "non rompere ≠ non toccare" rispettata: Step 1 NON ha cambiato logica decisionale (Strategy A, greed-decay, stop-loss invariati).

Vecchio test `tests/test_pct_sell_fifo.py` lasciato non aggiornato — non gating (test manuale, no CI), assertions legacy sul realized_pnl 53a sono ora obsolete dopo pivot avg-cost. Aggiornamento previsto come task di manutenzione (BUSINESS_STATE §5.23).

## 9. Audit esterni (sintesi)

| Data | Area | Topic | Verdetto | Findings chiave | Report |
|------|------|-------|----------|-----------------|--------|
| 2026-05-07 | 1 | Phase 1 split grid_bot.py | APPROVED | 0 regressioni, 0 risk gates aperti | `audits/audit_report_20260507_phase1_grid_split_review.md` |
| 2026-05-08 | 1 | Operation Clean Slate Step 0d (formula verification) | CRITICAL FINDING SHIPPED FIX | Bias `realized_pnl` +$26.97 (+29%) certificato da 2 metodi indipendenti (per-trade replay + identità contabile globale). Root cause: queue desync per 4 cause concorrenti. Fix Step 1 immediato chiude identità al centesimo. 80.6% sells avevano mismatch > $0.01. | `audits/2026-05-08_pre-clean-slate/formula_verification_s66.md` (gitignored) + `report.md` + `snapshot.json` + `verify_formulas_output.txt` |
