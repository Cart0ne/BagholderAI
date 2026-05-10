# S69 — Chiusura sessione: avg-cost migration B+C completa, brief 69a pronto

**Data**: 2026-05-09
**Autore**: Claude Code (Intern)
**Destinatario**: CEO
**Stato sessione**: **CHIUSA**
**Sessione precedente**: S68 chiusa stesso giorno (`6389ca7`) con cleanup DB Supabase + pivot Board "trading minimum viable"

---

## 1. TL;DR

Sessione 69 dedicata al **divorzio FIFO ↔ avg-cost** sulla parte contabile. 6 commit shipped: rimosso ogni FIFO replay client-side da dashboard (grid.html / tf.html / admin.html / dashboard-live.ts) e backend (commentary.py / health_check.py), redesign Portfolio overview di `/grid` a 9 card con formule esplicite, rimosso pannello "Reconciliation FIFO vs DB" da `/admin` (audit S65 obsoleto post-S66), pulizia parziale fixed mode. Scritto **brief 69a** per il deploy finale (FIFO trading logic via dal bot + DROP COLUMN DB + apply 68b + TRUNCATE+restart) pronto per Board approval. Bot Mac Mini live invariato (commit `a8e91a0`). Net: **-555 righe contabili + brief 199 righe**.

---

## 2. Cosa è stato shipped

### 2.1 BLOCCO 1 — B+C: FIFO contabile via dalle dashboard (commit `6335633`, `7231db7`, `f11b04e`)

Tre commit progressivi.

**Step 1 (`6335633`) — grid.html + tf.html avg-cost migration**:
- `grid.html` Portfolio overview ridisegnata: **9 card layout 3+3+3** con label Italian + sub-label formule esplicite. Card row 1 = Budget · Stato attuale · Total P&L. Row 2 = Cash to reinvest · Deployed · Skim. Row 3 = Unrealized · Fees · Dust. "Stato attuale" sostituisce il vecchio "Net Worth" e SOTTRAE le fees (chiude anomalia "fees not deducted in paper mode" S68).
- `grid.html` Coin status per coin: aggiunte stat **Avg buy / Current price / Diff%** (con colore verde/rosso). Sostituita "Open lots" (concetto FIFO morto) con "Avg buy".
- `grid.html` Recent trades: aggiunta colonna **Fee** per ogni riga. "Buy@" sui sell ora mostra `avg_buy_price` snapshot al momento del sell (non più ricostruzione FIFO dei lots consumati).
- `grid.html` Parameters: rimossa intera sezione "Fixed Grid" (`grid_levels`, `grid_lower`, `grid_upper`, `reserve_floor_pct`) + select `grid_mode` + CSS `.fixed-grid-fields` orfana. Lista campi config centralizzata in `GRID_CONFIG_FIELDS` (8 campi).
- `tf.html` minimum viable mirror: stessa logica avg-cost, layout invariato (TF è OFF e in maintenance, valore basso a redesignare ora). 0 codice FIFO operativo residuo.

**Step 2 (`7231db7`) — backend + admin.html**:
- `admin.html` Reconciliation panel rimosso (era audit "FIFO vs DB" S65, obsoleto post-S66). 204 righe via inclusi disclaimer, tabella, logica `loadReconciliation()`, CSS `.recon` orfana. Sostituito da TODO comment che punta al brief futuro **Reconciliation Binance** (DB ↔ `fetch_my_trades`).
- `bot/health_check.py` Check 1 (FIFO P&L reconciliation) e Check 2 (Holdings consistency via FIFO replay, tautologico) **rimossi**. Helper `_replay_fifo_pnl` via, costanti `PNL_TOLERANCE_USD` + `HOLDINGS_TOLERANCE` via. Restano 3 check: negative-holdings + cash-accounting + orphan-lots.
- `commentary.py` `_analyze_coin_fifo` → `_analyze_coin_avg_cost`. Stessa firma di output (realized, openCost, openAmount, netInvested, fees) → niente rotture downstream. Realized = `trades.realized_pnl` DB SUM (avg-cost canonico post-S66).
- `utils/telegram_notifier.py` + `web_astro/src/scripts/live-stats.ts` cleanup commenti FIFO.
- `tests/test_pct_sell_fifo.py` archiviato in `tests/legacy/` (debt S66 esplicito). `test_verify_fifo_queue.py` lasciato finché `verify_fifo_queue` esiste (sparisce con 69a).
- `PROJECT_STATE.md §6` aggiunta nota "Reconciliation Binance" come brief futuro.

**Step 3 (`f11b04e`) — dashboard-live.ts**:
- `analyzeCoin` riscritta avg-cost: running weighted average specchio `bot/grid/buy_pipeline.py:117`. `openCost = avg_buy_price × holdings`. price ricavato da `cost/amount` (evita aggiungere `price` allo schema query).
- `annotateBuyAvg` Recent Activity § 4: stessa logica avg-cost. "Buy at" sui sell = avg_buy snapshot al momento del sell.
- Pulizia commenti FIFO ovunque (header doc, fetchAllTrades doc, sezioni 1/4/5).
- Astro build pulito: 10 pagine generate senza errori TS.

**Test**: 8/8 verdi (`tests/test_accounting_avg_cost.py`) prima e dopo ogni commit.

**Net BLOCCO 1**: **-555 righe** cross-file.

### 2.2 BLOCCO 2 parziale — pulizia codice (commit `ad048b6`)

- `main_old.py` cancellato dal filesystem (era in `.gitignore` via regola `*_old*`, gemello legacy non importato da nessuna parte). Risolve PROJECT_STATE bug noto S68 NEW.
- `bot/grid_runner.py` sync delle 4 colonne fixed-mode (`grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`) rimosso. Codice morto: tutti i `bot_config` hanno `grid_mode='percentage'` post S68 cleanup.

**NON fatto in BLOCCO 2** (rimandato a 69a per coerenza con TRUNCATE+restart):
- Refactor pesante fixed mode in `bot/grid/grid_bot.py` (~200 righe)
- DROP COLUMN DB delle 5 colonne fixed (grid_mode, grid_levels, grid_lower, grid_upper, reserve_floor_pct)
- Allocator dummy keys (vincolati a NOT NULL constraint DB)

### 2.3 BLOCCO 3.1 — brief 69a scritto (commit `ee2b0aa`)

`config/brief_69a_avg_cost_trading_truncate_restart.md` — 199 righe, **PENDING Board approval data deploy**.

Scope brief 69a:
1. **Avg-cost trading**: bot smette di mantenere `_pct_open_positions` queue. Trigger sell su `state.avg_buy_price × (1 + sell_pct/100)`. Sell amount = `capital_per_trade / current_price`.
2. **Rimozione fixed mode**: `grid_bot.py` (~200 righe), `sell_pipeline.py` (`execute_sell` fixed path), `state_manager.py` (init avg-cost replay), eliminazione `fifo_queue.py`.
3. **DROP COLUMN DB**: 5 colonne `bot_config` + verifica `bot_state_snapshots`.
4. **Apply 68b sul Mac Mini**: refactor folder cosmetico `bot/strategies/` → `bot/grid/` + standardizzazione `managed_by`/'tf'.
5. **TRUNCATE testnet baseline**: DELETE trades v3 + reserve_ledger + daily_pnl + bot_state_snapshots.
6. **Restart bot vergine**.
7. **24h observation post-deploy**.

Stima: 10-14h sviluppo + 24h observation = ~3 giornate wall-clock.

### 2.4 PROJECT_STATE.md S69 chiusura (commit `0b27a88`)

8 sezioni aggiornate: stato, in-flight, decisioni recenti, bug noti, domande CEO, deadlines, NOT done, audit log. 151 righe totali (sotto 40K vincolo). Vincolo CLAUDE.md regola n.1 rispettato.

---

## 3. Decisioni Board prese in S69

| # | Decisione | Stato |
|---|-----------|-------|
| 1 | Budget testnet **$500 confermato** (no passaggio a $10K) | ✅ Acquisita |
| 2 | Allocazioni invariate: BTC $200, SOL $150, BONK $150 | ✅ |
| 3 | Capital per trade invariato: $50 / $20 / $25 | ✅ |
| 4 | Scope FIFO removal: B+C ora (contabilità), A in finestra dedicata (trading logic) | ✅ |
| 5 | Pannello "Reconciliation FIFO" admin: rimuovere completamente, sostituire con Reconciliation Binance brief futuro | ✅ |
| 6 | Health check FIFO Check 1+2: rimuovere ("non voglio più sentire parlare di FIFO") | ✅ |
| 7 | tf.html: minimum viable cleanup, ridisegno post-riattivazione TF | ✅ |
| 8 | grid.html Portfolio overview: 9 card layout 3+3+3 con formule esplicite | ✅ |
| 9 | grid.html Coin status: aggiunte Avg buy / Current price / Diff% | ✅ |
| 10 | grid.html Recent trades: aggiunta colonna Fee | ✅ |
| 11 | grid.html Parameters: rimossa intera sezione Fixed Grid + grid_mode select | ✅ |

## 4. Decisioni Board ancora aperte (in valutazione)

| # | Tema | Stato |
|---|------|-------|
| 1 | Data deploy brief 69a (earliest 2026-05-10, latest 2026-05-15) | ⏳ |
| 2 | Brief 67a Step 5 (reconciliation gate nightly): shipped insieme a 69a o sessione separata? | ⏳ |
| 3 | Reset mensile testnet Binance: verifica formale prima del deploy 69a? | ⏳ |
| 4 | Brief Reconciliation Binance (DB ↔ `fetch_my_trades`): post go-live €100 mainnet | ⏳ |

## 5. Numeri shipped

- **6 commit S69**: `6335633`, `7231db7`, `f11b04e`, `ad048b6`, `ee2b0aa`, `0b27a88`
- **File toccati operativamente**: 11 (grid.html, tf.html, admin.html, dashboard-live.ts, live-stats.ts, telegram_notifier.py, commentary.py, health_check.py, grid_runner.py, PROJECT_STATE.md, brief 69a nuovo)
- **File rimossi**: 2 (`main_old.py` filesystem, `tests/test_pct_sell_fifo.py` → `tests/legacy/`)
- **Net righe**: **-555 contabili + 199 brief = -356 globale netto**
- **Test 8/8 verdi** in 3 punti (post step 1, step 2, step 3)
- **Astro build pulito**: 10 pagine generate
- **Tempo wall-clock S69**: ~6h di lavoro effettivo (~10h sessione totale incluso brainstorming)

## 6. Stato runtime al termine sessione

- Bot Mac Mini: **LIVE** invariato su commit `a8e91a0` (fix 68a, folder ancora `bot/strategies/`)
- 4 processi: orchestrator 96199, BONK 96200, SOL 96201, BTC 96202
- Brain flags: `TF=False SENTINEL=False SHERPA=False` (Grid-only)
- **MBP+GitHub** su commit `0b27a88` (S69 chiusura). Disallineamento volontario fino al deploy 69a.
- Total P&L stabile zona +$0.10 / +$0.30 (variabile col prezzo)
- Sito: in maintenance da S65, decisione riapertura post-69a clean baseline
- DB: 19 tabelle pubbliche, 0 view, schema ancora con 5 colonne fixed-mode-only (DROP in 69a)

## 7. Handoff alla nuova chat (S70)

Prossima sessione = **deploy brief 69a**. Earliest 2026-05-10, latest 2026-05-15.

Sequenza S70 proposta (mirror del brief):
1. **Pre-deploy** (1h): snapshot DB + Board approval finale
2. **Sviluppo refactor** (8-10h): `grid_bot.py`, `sell_pipeline.py`, `state_manager.py`, rimozione `fifo_queue.py`, allocator dummy keys via, test nuovi
3. **Deploy day** (~2h): stop bot Mac Mini → TRUNCATE DB → DDL DROP COLUMN → git pull Mac Mini → restart Grid-only
4. **24h observation**: smoke test 1h + osservazione comportamento avg-cost trading
5. **Aggiornamento PROJECT_STATE + report**: chiusura S70 + brief 67a Step 5 (reconciliation gate nightly) candidato

In parallelo (post-deploy):
- Verifica bug `recalibrate-on-restart` (probabile sparisce con riscrittura)
- Verifica strange sell BONK 22:56 v3 non ripetibile (impossibile in avg-cost)
- 1° trigger sell con avg-cost: confermare matematica e log

## 8. Roadmap impact

- **Pre-live gate Phase 9 V&C**:
  - ✅ Contabilità S66 (avg-cost canonico bot)
  - ✅ Fee USDT canonical S67
  - ✅ Dust prevention S67
  - ✅ Sell-in-loss guard avg_cost S68a
  - ✅ DB schema cleanup S68
  - ✅ **FIFO contabile via S69** (NUOVO)
  - 🔲 Avg-cost trading (deploy 69a)
  - 🔲 Reconciliation gate nightly (post-69a)
  - 🔲 Wallet reconciliation Binance settimanale (post go-live)

- **Target go-live €100 mainnet**: 21-24 maggio se 69a deploy entro 17-18 maggio. Slip a 24-27 maggio se deploy 19-20.

- **Brief 69a parcheggiati**: il brief ingloba e chiude (a deploy time) i seguenti debt aperti:
  - "Apply 68b sul Mac Mini" (era da S68)
  - "Trigger sell per-lot bug `grid_bot.py:749-752`" (era da S68)
  - "Strange sell BONK 22:56 lot fantasma" (emerso in audit S69)
  - "Bug `recalibrate-on-restart`" (probabile sparizione)
  - "Fixed mode codice morto" (BLOCCO 2 parziale → completo a 69a)

## 9. Cosa NON è stato fatto in S69

- ❌ Deploy brief 69a (PENDING Board)
- ❌ Step 5 reconciliation gate nightly (sarà 69a o post)
- ❌ Refactor pesante fixed mode in `bot/grid/grid_bot.py` (~200 righe, va in 69a)
- ❌ DROP COLUMN DB (va in 69a)
- ❌ Apply 68b sul Mac Mini (va in 69a)
- ❌ Fix `exchange_order_id=null` su sell (debt cosmetico, post-69a)
- ❌ Verifica reset mensile testnet Binance
- ❌ Reapertura sito pubblico (post-69a)
- ❌ TF/Sentinel/Sherpa riconnessione (coerente con pivot S68)

## 10. Domande aperte per il CEO (non bloccanti)

1. **Quando deployiamo 69a?** Earliest 2026-05-10, latest 2026-05-15.
2. **Reconciliation gate nightly (brief 67a Step 5)**: la facciamo nello stesso slot di 69a o subito dopo (con baseline pulita più affidabile)?
3. **Allineamento fee discount BNB** (CEO opzione A future-proof): trascurabile su €100, ma vale chiudere prima di mainnet. Sessione separata?

---

## 11. Decision log della sessione

DECISIONE 1: Scope B+C ora, A in finestra dedicata
RAZIONALE: il refactor A (FIFO trading logic → avg-cost) richiede TRUNCATE + restart bot + decisione strategica. B+C invece è solo dashboard/contabilità, niente bot toccato.
ALTERNATIVE CONSIDERATE: A diretto (rifiutato — rischio alto pre-mainnet); solo B (rifiutato — health check FIFO andava comunque rimosso).
FALLBACK SE SBAGLIATA: revert dei 3 commit B+C, dashboard torna a FIFO replay (solo lettura, nessun impatto runtime bot).

DECISIONE 2: tf.html minimum viable invece di redesign card-by-card
RAZIONALE: TF è OFF in produzione, dashboard /tf in maintenance pubblica, valore basso a disegnare card di un cervello spento.
ALTERNATIVE CONSIDERATE: redesign completo come grid.html (rifiutato — tempo non giustificato dato che TF cambierà al prossimo riaccendi).
FALLBACK SE SBAGLIATA: redesign futuro post-riattivazione TF, costo trascurabile.

DECISIONE 3: rimozione completa health_check Check 1 + Check 2 (non solo declassamento)
RAZIONALE: Max esplicito "non voglio più sentire parlare di FIFO". Check 1 confrontava DB con FIFO replay legacy ormai obsoleto. Check 2 era tautologico (net == net via FIFO).
ALTERNATIVE CONSIDERATE: declassamento Check 1 a "info-only" (rifiutato — confonde, meglio chiarezza).
FALLBACK SE SBAGLIATA: re-add helper + 2 check via git revert (10 min).

DECISIONE 4: Reconciliation Binance brief separato post go-live €100
RAZIONALE: panel admin attuale era "FIFO vs DB" obsoleto. Sostituirlo subito con "Binance API vs DB" richiede infrastruttura `fetch_my_trades` periodico + UI nuova. Meglio brief dedicato post-baseline pulita.
ALTERNATIVE CONSIDERATE: implementare subito (rifiutato — scope creep S69).
FALLBACK SE SBAGLIATA: nessuno; brief tracciato in PROJECT_STATE §6.

DECISIONE 5: BLOCCO 2 parziale invece di completo
RAZIONALE: refactor fixed mode in `grid_bot.py` (~200 righe) è invasivo. Va fatto insieme al deploy 69a per:
- coerenza con DROP COLUMN DB
- 1 solo restart bot invece di 2
- 1 sola finestra di rischio
ALTERNATIVE CONSIDERATE: refactor completo oggi (rifiutato — rischio + niente DB cleanup → restart inutile).
FALLBACK SE SBAGLIATA: includere comunque in 69a (è già lì).

---

*CC, S69 chiusura, 2026-05-09 ~16:30 UTC. Sessione next-action: decision Board su data deploy 69a + sviluppo + deploy + 24h observation.*
