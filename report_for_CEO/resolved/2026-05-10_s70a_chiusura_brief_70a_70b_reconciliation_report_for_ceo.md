# Sessione 70 — Chiusura: brief 70a + 70b + reconciliation Step A + cleanup totale

**Da:** CC (Claude Code, intern) → CEO
**Data:** 2026-05-10
**Sessione:** 70
**Presenti:** Max (Board) + CC. **CEO assente.**
**Durata:** ~6 ore (mattino + pomeriggio)
**Modello workflow:** sessione "CC + Max only" senza CEO. Questo report serve da input al diary di Volume 3 + aggiornamento BUSINESS_STATE.

---

## TL;DR (30 secondi)

S70 ha shipped **due brief grossi** (70a sell_pct net-of-fees + sell ladder + post-fill warning, 70b Sentinel ricalibrazione + DRY_RUN riacceso) + **reconciliation Binance Step A** (script + tabella DB) + **rename `manual→grid` su 4 tabelle DB** (chiude open question 19 BUSINESS_STATE) + **hotfix BONK sell_pct 2→4** post sell-at-loss da slippage testnet 2.46%. Mac Mini riavviato 09:51 UTC con TF=off, SENTINEL=ON, SHERPA=ON; Telegram silente per nuovi brain via env flag (memoria `feedback_no_telegram_alerts`). 12 commit, ~600 righe nette di codice + DDL DB. Test 15/15 verdi. Cleanup: 13 brief shipped + 15 CEO reports archiviati. **Bug residuo annotato**: LAST SHOT path bypassa lot_step_size rounding (cosmetico, pre-mainnet).

---

## 1. Cosa è stato shipped

### 1.1 Brief 70a — sell_pct net-of-fees + sell ladder + post-fill warning (commit `eb5f38f`)

5 parti integrate, 15/15 test verdi:

- **Parte 1**: `FEE_RATE` 0.00075 → 0.001 (worst-case spot fee, conservativo)
- **Parte 2+3**: trigger sell uniforme con fee buffer **solo per Grid manual**:
  ```
  reference × (1 + sell_pct/100 + FEE) / (1 - FEE)
  ```
  con `reference = _last_sell_price` (sell ladder graduale) o `avg_buy_price` (primo sell del ciclo). TF/tf_grid invariato (rispetta calibrazione greed-decay esistente).
- **Parte 3 dettaglio**: nuovo campo `_last_sell_price` set on partial sell, reset on full sell-out, replay da DB in `state_manager.init_avg_cost_state_from_db`.
- **Parte 4**: post-fill warning `slippage_below_avg` in `bot_events_log` quando fill < avg, escludendo TF force-liquidate path. Non blocca il trade (è già eseguito), solo rende visibile lo slippage.
- **Parte 5**: widget grid.html "Next sell if ↑" replay client-side `lastSellPrice` + nuova formula con FEE_RATE inline.

**Decisione semantica chiave (chat con Max)**: formula uniforme primo + gradini (opzione iii), invece di 2 formule separate come da brief originale. Pro: 1 sola formula in codice + dashboard, semantica chiara ("sell_pct% netto sopra il riferimento"). Contro: ~0.1% over-buffer "fee buy fantasma" sui gradini successivi (accettato come buffer micro-slippage).

### 1.2 Brief 70b — Sentinel ricalibrazione + DRY_RUN riacceso (commit `4324231`)

**Diagnosi sui 2,827 record raccolti 6-8 maggio**:
- BTC `change_1h` range osservato: ±0.96% (mai −3% per attivare le ladder originali)
- `funding_rate` range: −0.00007 a +0.00002 (1 ordine grandezza sotto le soglie originali)
- `speed_of_fall_accelerating`: 850/2827 = **30% TRUE** (falsi positivi su rumore)

**Fix**:
- **`score_engine.py`**: ladder granulare drop −2/−1/−0.5 (+20/+12/+6), pump +2/+1/+0.5 (+15/+10/+5), funding intermedi ±0.0001/±0.0002/±0.00005/±0.00002 con incrementi minori. Soglie originali (−3%, −5%, −10%, ±0.0003, ±0.0005) restano per movimenti veri di mercato (mainnet).
- **`price_monitor.py`**: aggiunto floor `_SOF_MIN_DROP_1H_PCT = -0.5` su `speed_of_fall_accelerating`. Ignora accelerazione se l'ora intera non è in vero calo. Risolve il 30% di falsi positivi.
- **`bot/sentinel/main.py` + `bot/sherpa/main.py`**: nuovi env flag `SENTINEL_TELEGRAM_ENABLED` / `SHERPA_TELEGRAM_ENABLED` **default false**. Riaccensione DRY_RUN senza spam Telegram (priorità assoluta Max: "non mi arrivino 600 telegram").

**Restart orchestrator Mac Mini 09:51 UTC**: TF=off (`ENABLE_TF=false`), Sentinel + Sherpa accesi DRY_RUN. Smoke test verde — Sentinel scrive ogni 60s, Sherpa propose ogni 120s, primo proposal 09:51:50 UTC.

### 1.3 Reconciliation Binance Step A (commit `0f6c9b0`)

Script `scripts/reconcile_binance.py` + tabella `reconciliation_runs` (DDL via Supabase MCP, RLS service-role-only).

Logica idea Max: "se Binance dati = 0 (testnet reset) → warning, se > 0 → confronta a ritroso N comuni". Implementata con 4 statuses:
- `OK` — tutto matched within tolerance
- `WARN_BINANCE_EMPTY` — Binance returna 0 trades (probabile testnet reset, informational)
- `DRIFT` — matched orders fuori tolleranza (qty±0.00001, price±0.5%, fee±$0.01)
- `DRIFT_BINANCE_ORPHAN` — ordine su Binance senza match in DB (serio: bot eseguito ma non loggato)

Match strategy: `exchange_order_id` (preferito) + fallback ts±1s/side/qty±1% (per S67 debt con `exchange_order_id=NULL`).

**Primo run dry-run**: 24/24 ordini matched, zero drift, zero orphan su tutti e 3 i symbol. Pre-live gate "Wallet reconciliation Binance" **chiuso**.

### 1.4 Rename `manual→grid` + `trend_follower→tf` (commit `bb575c0`)

Open question 19 BUSINESS_STATE chiusa. Migrazione DB: ALTER CHECK constraint `bot_config.managed_by` → `('grid','tf','tf_grid')`, UPDATE 4 tabelle (`bot_config`, `trades`, `reserve_ledger`, `daily_pnl`), 6 callsite frontend allineati (`dashboard-live.ts`, `live-stats.ts`, `tf.html`).

Rilevato durante reconciliation: il refactor S68b aveva rinominato il **codice** ma non i **dati DB**. Il bot continuava a scrivere `managed_by='manual'` perché ereditava dal `bot_config` non migrato.

### 1.5 Hotfix BONK sell_pct 2→4

Investigazione su sell BONK 11:52 CEST (08:57 UTC) realized −$0.11. Diagnosi: NON guard, NON `managed_by`, NON recalibrate. **È slippage testnet 2.46%** > sell_pct=2% buffer:
- avg_cost = $0.000007314, sell_pct=2% → trigger atteso $0.0000074602
- check_price ha superato il trigger, market sell spedito
- fill arrivato a $0.00000728 (slippage 2.46% su book BONK testnet sottile)
- guard a `sell_pipeline.py:282` controlla `check_price < avg`, passa; il fill non viene rivalutato

Pattern cross-symbol confermato: BTC e SOL su 6 sell post-S68a hanno gap fill vs avg ≈ +1% (= sell_pct, slippage trascurabile). BONK su 1 sample post-S68a ha gap −0.46% (slippage 2.46%). Book sottile vs denso.

Hotfix: Max via grid.html alza `bot_config.sell_pct` BONK a 4.0%. Memoria `project_bonk_testnet_slippage` salvata.

### 1.6 Mascot SVG /tf + /admin (commit `2a10028`)

Brief 65b residui: integrate `trend-follower.svg` in /tf header, `sentinel.svg` + `sherpa.svg` in /admin section-titles. Pattern coerente con grid.html (commit cb21179). 3/4 integrazioni 65b complete; homepage Astro pendente (sito in maintenance).

### 1.7 Tabella scoring rules SENTINEL aggiornata (commit `40fdc4c`)

Tabella statica in /admin allineata al nuovo `score_engine.py`: aggiunte 10 righe (drop/pump granulari + funding intermedi). Footnote aggiornata con riferimento a brief 70b + nota sul floor `_SOF_MIN_DROP_1H_PCT`.

### 1.8 Cleanup totale (3 round, commit `a201120`, `f572b33`, `f2c47d0`)

- Round 1: 9 brief shipped (S62/63/66/67a/68a/69a/70/70a/70b) → `briefresolved.md/`
- Round 2: 4 brief/decision S65/S62 superati → `briefresolved.md/`
- Round 3: 15 CEO reports S62-S69 → `report_for_CEO/resolved/`

**28 file archiviati totali**, naming history preservato. `config/` ora ha solo lavoro vivo (4 brief parcheggiati + 1 milestone + 2 design HTML). `report_for_CEO/` root vuoto pronto per S71.

---

## 2. Decisioni prese (elenco per BUSINESS_STATE §4)

1. **Formula uniforme primo + gradini** in 70a (decisione semantica Max chat S70): 1 sola formula in codice + dashboard, semplicità, accetta ~0.1% over-buffer come buffer micro-slippage.
2. **Filtro `managed_by=='grid'`** per fee buffer 70a: TF/tf_grid invariati per non alterare calibrazione greed-decay (vincolo brief).
3. **Telegram default OFF** per Sentinel + Sherpa al riavvio post-DRY_RUN: env flag `SENTINEL_TELEGRAM_ENABLED` / `SHERPA_TELEGRAM_ENABLED`. Memoria `feedback_no_telegram_alerts` aggiornata. Max abilita via env quando vuole.
4. **Hotfix BONK sell_pct 2→4** (Max via grid.html): non risolve slippage strutturale, blocca prossimi sell-at-loss su book sottile.
5. **Reconciliation Step A → Step B → Step C in fasi**: oggi solo script + tabella DB. Step B (pannello /admin) nella prossima sessione admin-focused, Step C (cron notturno) dopo 2-3 run manuali clean.
6. **Niente `--write` reconcile oggi**: persistenza in `reconciliation_runs` deferred a quando si attiva il pannello /admin (Step B).

---

## 3. Bug residui annotati

- **🟡 LAST SHOT path bypassa `lot_step_size` rounding** — primo BUY BONK 11:52 UTC rejected da Binance (`code -2010`), retry success. Reconcile DB↔Binance OK 12/12 (rejected non scritto, success regolare). Cosmetico ma genera Telegram + warn `ORDER_REJECTED`. Memoria salvata, fix pre-mainnet (annotato in PROJECT_STATE §5).
- **🟡 Sherpa propone abbassare BONK sell_pct 4→1.5 in DRY_RUN** — ignora hotfix slippage. Quando SHERPA_MODE=live, rule engine deve preservare buffer per-coin. Brief separato pre-`SHERPA_MODE=live`.
- **🟡 Reason bugiardo** (open question 27 BUSINESS_STATE) — la stringa `reason` del trade dice "above avg" anche su fill < avg. Post-fill warning brief 70a Parte 4 rende il drift visibile, ma la stringa resta cosmeticamente sbagliata. TODO separato.

---

## 4. Domande aperte per CEO

1. **Slippage_buffer parametrico per coin** — estensione brief 70a per pre-mainnet. BONK avrebbe `slippage_buffer=3%`, BTC/SOL=0%. Brief separato.
2. **Sherpa rule-aware sull'hotfix slippage** — pre-`SHERPA_MODE=live`.
3. **Reconciliation Step B (pannello /admin)** — sessione admin-focused.
4. **Sentinel Telegram flag** — Max abilita quando vuole (default off).
5. **Skim_pct 30% è la soglia giusta?** — da rivalutare con dati testnet veri (open from S68).
6. **BNB-discount fee** — connesso a sell_pct net-of-fees pre-mainnet.

---

## 5. Roadmap impact

**Pre-Live Gates Phase 9 V&C — aggiornamento S70**:
- ✅ contabilità S66
- ✅ fee USDT canonical S67
- ✅ dust prevention S67
- ✅ sell-in-loss guard avg_cost S68a
- ✅ DB schema cleanup S68 + S70
- ✅ FIFO contabile via S69
- ✅ avg-cost trading completo S69
- ✅ Strategy A simmetrico S69
- ✅ IDLE recalibrate guard S69
- ✅ **sell_pct net-of-fees S70** (brief 70a)
- ✅ **post-fill warning slippage S70** (brief 70a Parte 4)
- ✅ **wallet reconciliation Binance S70** (Step A clean, Step B+C post-osservazione)
- ✅ **Sentinel ricalibrazione S70** (brief 70b)
- 🔲 slippage_buffer parametrico per coin (brief separato pre-mainnet)
- 🔲 Reconciliation Step B (pannello /admin)
- 🔲 Reconciliation Step C (cron notturno)
- 🔲 24-48h observation post-restart 09:51 UTC
- 🔲 Sito online con numeri certificati
- 🔲 Board approval finale (Max)

**Target go-live €100 mainnet**: 21-24 maggio 2026 invariato.

---

## 6. Stato Mac Mini fine sessione

- Commit: `eafe3b1` (PROJECT_STATE update finale)
- Bot orchestrator: PID 2626, restart 09:51 UTC con `ENABLE_TF=false ENABLE_SENTINEL=true ENABLE_SHERPA=true`
- 6 processi vivi: orchestrator + 3 grid_runner (BTC/SOL/BONK) + sentinel + sherpa
- Telegram alerts: solo Grid trade events; Sentinel + Sherpa silenziati
- DB: 20 tabelle (con `reconciliation_runs`), naming pulito (grid/tf/tf_grid)

---

## 7. Numeri sessione

- **12 commit** in `main`: a3443a6, 0f6c9b0, bb575c0, eb5f38f, 4324231, a201120, f572b33, f2c47d0, 805b546, 2a10028, 40fdc4c, eafe3b1
- **2 brief shipped** (70a + 70b) con 4 nuovi test (15/15 verdi totali)
- **1 nuova tabella DB** (`reconciliation_runs`)
- **1 migration DB** (rename managed_by + ALTER CHECK constraint × 4 tabelle)
- **1 hotfix DB diretto** (BONK sell_pct 2→4)
- **28 file archiviati** (cleanup config + report)
- **4 memorie nuove**: `project_bonk_testnet_slippage`, `project_last_shot_lot_size_bypass`, `feedback_no_telegram_alerts` (aggiornata)
- **0 Telegram nuovi alert types** (priorità Max rispettata)
- **0 regressioni** osservate sui test esistenti

---

*CC, 2026-05-10*
