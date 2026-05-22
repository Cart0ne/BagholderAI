# S79 — 3 brief shipped (79a/79b/79c) + drift FIFO sanato + cleanup

**Da:** Claude Code (Intern)
**Per:** CEO + Board (Max)
**Data:** 2026-05-18 sera
**Brief di riferimento:**
- [briefresolved.md/brief_79a_idle_recalibrate_guard.md](../briefresolved.md/brief_79a_idle_recalibrate_guard.md) — idle suppression on capital exhausted
- [briefresolved.md/brief_79b_tf_reactivation_t1t2.md](../briefresolved.md/brief_79b_tf_reactivation_t1t2.md) — TF reactivation Tier 1-2 only
- [briefresolved.md/brief_79c_supabase_io_reduction.md](../briefresolved.md/brief_79c_supabase_io_reduction.md) — Supabase write-on-change + heartbeat

**Modalità:** sessione "3 brief auto-contenuti + ortogonali" (79a tocca grid_bot, 79b tocca DB+env, 79c tocca sentinel/sherpa/snapshot_writer). 2 restart Mac Mini raggruppati (post-79a/79b combinati, post-79c isolato).
**Test suite:** 30 → 31 verdi (test_ee idle suppression con 3 casi)
**Restart bot:** **2 FATTI** — Mac Mini PID parent 73667 (21:14 CET, post 79a/79b) → PID parent **74280** (21:49 CET, post 79c, attuale)
**Commit pushati:** 6 commit (`6183980` → `fe8fca9`) su `main`

---

## 0. TL;DR

Tre brief CEO consegnati interamente nella stessa sessione. Tutti shipped, tutti LIVE su Mac Mini, tutti con verifica empirica:

| Brief | Cosa | Verifica live |
|---|---|---|
| 79a | Bot non spreca cicli su idle recalibrate quando il cash è esaurito | ✅ 3/3 Grid soppressi al primo cycle (BTC $0.12 / SOL $0.03 / BONK $0.00) |
| 79b | TF riacceso Tier 1-2 (T3 weight=0 in DB, fuori dai Grid $500) | ✅ 7 processi, regime fear → 50 scan / 2 BULLISH / 0 allocations (atteso) |
| 79c | Supabase write-on-change + heartbeat su 3 tabelle pesanti | ✅ first-tick OK; verifica rate 30min schedulata `trig_01XmwTmHthrCAgRS6HveTcJ8` per 22:31 CET |

**Sorpresa positiva**: il **drift FIFO** che CC stava per inerzialmente trasportare in S79 (memorie 13-14gg vecchie ancora frame "FIFO canonical") è stato sanato grazie al tuo flag *"FIFO non esiste su exchange"*. Bug §5 🔴 [S70c] chiuso (era già fixato in 72a, lo stavamo trascinando come aperto). Brief "Strada 2 ~3-4h" → "verifica identità accounting ~30 min". 2 memorie aggiornate.

**Catch del Board a fine sessione**: sito pubblico (`bagholderai.lol`) mostra ancora "TF dal dottore" SVG/badge da S70c. TF è LIVE dal 2026-05-18 21:14 CET. Aggiornare narrativa pubblica prossima sessione (annotato Apple Note + memoria dedicata).

---

## 1. Brief 79a — Idle suppression on capital exhausted

### Cosa è stato fatto
Guard chirurgico in [bot/grid/grid_bot.py:909-948](../bot/grid/grid_bot.py#L909-L948), `elif` chain pulito:

```python
if elapsed >= self.idle_reentry_hours:
    available = self._available_cash()
    if available < HardcodedRules.MIN_LAST_SHOT_USD:
        # suppress (log + bot_events_log + advance _last_trade_time)
    elif self.state.holdings <= 0:
        # Path A re-entry (esistente)
    else:
        # Path B recalibrate (esistente)
```

Quando `_available_cash() < $5`:
- Log: `Idle {re-entry|recalibrate} suppressed: capital exhausted ($X.XX available, floor $5.00)`
- `bot_events_log` event: `idle_{reentry|recalibrate}_suppressed_no_cash` (severity=info, category=trade_audit)
- `_last_trade_time` avanzato (no spam per-cycle)
- Nessuna entry in `idle_reentry_alerts` (no Telegram)

Ortogonale a `stop_buy_active` suppression del S76 audit (quella è downstream Telegram). Questa è upstream sul calcolo idle stesso.

### Test
Test `ee_idle_suppressed_when_capital_exhausted` (3 casi):
- CASE 1: Path B recalibrate soppresso (ref unchanged, no alert, time advanced)
- CASE 2: Path A re-entry soppresso (holdings=0 ma cash=0)
- CASE 3: regression — cash healthy → recalibrate fires normalmente

Suite 30 → 31 verdi.

### Verifica live post-restart
Dal log Mac Mini, primo idle cycle post-restart su 3 bot:
```
[BTC/USDT]  Idle recalibrate suppressed: capital exhausted ($0.12 available, floor $5.00)
[SOL/USDT]  Idle recalibrate suppressed: capital exhausted ($0.03 available, floor $5.00)
[BONK/USDT] Idle recalibrate suppressed: capital exhausted ($0.00 available, floor $5.00)
```

Tutti e 3 i Grid sono cash-exhausted (DB sottostimava BTC $1.16 vs $0.12 reale: reserve_ledger skim a runtime). `_last_trade_time` avanzato — la riga successiva mostra `elapsed=0.01h` invece di continuare ad accumulare.

**Decisione delegata CC**: Option A (import `HardcodedRules.MIN_LAST_SHOT_USD` da `config.settings`) per coerenza con `grid_runner._capital_exhausted` (L654) e `buy_pipeline` (L114). Single source of truth, no hardcoded threshold.

**Commit**: `1eff58a`.

---

## 2. Brief 79b — TF reactivation Tier 1-2 only

### Sorpresa: brief no-code
Letto il brief, scoperto che **`ENABLE_TF` ha default `"true"`** in [orchestrator.py:41](../bot/orchestrator.py#L41). Lo spegnimento avveniva solo via env var al launch (`ENABLE_TF=false` nella memoria `reference_orchestrator_start`). Quindi:
- ✅ Nessun cambio codice repo necessario per il flag
- ✅ Modifica DB unica: `UPDATE trend_config SET tf_tier3_weight = 0` (era 25)
- ✅ Restart Mac Mini con env line ripulita: `ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true`

### Verifiche pre-restart
| Aspetto | Stato |
|---|---|
| Allocator robusto con `t3_weight=0` | ✅ Guard `weight_sum <= 0 → 100` a [allocator.py:311](../bot/trend_follower/allocator.py#L311) e [:949](../bot/trend_follower/allocator.py#L949) — no div-by-zero |
| Allocazioni TF/tf_grid attive | ✅ Zero in `bot_config` — restart pulito |
| tf_grid handoff intatto post-S76 refactor | ✅ S76 ha toccato `grid_runner/`, non `trend_follower/` |
| `counterfactual_log` esiste | ✅ 639 record storici 4-8 maggio, retention 14gg |
| `trend_follower_enabled` DB | ✅ Già `true` |
| USDT free su Binance testnet | ✅ **$9,481** — i $100 TF prendono dal pool, NON dai $500 Grid |

### Decisione delegata rilevata (non bloccante)
`counterfactual.py` **non logga regime Sentinel** (grep `regime|sentinel|score_type` su counterfactual.py = vuoto). I nuovi record post-restart cattureranno solo price/EMA come pre-Sprint 2. Brief separato se vorremo correlare counterfactual ↔ regime — utile post-osservazione (decisione tua, ~30-45 min lavoro).

### Verifica live post-restart
```
Brain flags: TF=True  SENTINEL=True  SHERPA=True
Trend Follower starting — dry_run=False
TF budget: $100.00 (no floating)
Scanning top 50 coins by 24h USDT volume...
Logged 50 coins to trend_scans
[51a] Fetching 1h RSI for 2 BULLISH candidates (threshold 75)
Logged 0 decisions to trend_decisions_log (shadow=False)
trend_scans cleanup: removed 1568 row(s) older than 14d
```

In regime fear, su 50 coin top scan → **solo 2 BULLISH** → filtrati ulteriormente da distance 12% + RSI 75 → **0 allocations**. Esatto scenario del brief ("worst case TF non trova candidati — produce counterfactual senza rischio"). Zero T3 nel ranking (T3 weight=0 → frac=0).

**Commit**: `2abd72e`.

---

## 3. Brief 79c — Supabase write-on-change + heartbeat

### Contesto
Warning email Supabase "Disk IO Budget depleting". DB query pre-fix delle 3 tabelle:
- `sentinel_scores fast`: 1.423/24h (1.440 atteso al rate 1/min, ~99% saturazione)
- `sherpa_proposals`: 2.117/24h (2.160 atteso al rate 1/2min × 3 bot, ~98%)
- `bot_state_snapshots`: 498/24h

### 3 file modificati
| File | Pattern | Heartbeat |
|---|---|---|
| [bot/sentinel/main.py](../bot/sentinel/main.py) | Guard prima INSERT: write se `risk/opp` cambiano OR `now − last_write_ts ≥ 600s` | 10 min |
| [bot/sherpa/main.py](../bot/sherpa/main.py) | Heartbeat come 4ª condizione al filtro esistente (`would_have_changed OR stop_buy OR cooldown OR heartbeat_due`) | 10 min per-symbol |
| [db/snapshot_writer.py](../db/snapshot_writer.py) | Modulo-level cache `_last_snapshot_per_symbol`; 8 COMPARE_KEYS | 5 min per-symbol |

### Decisione delegata CC: `unrealized_pnl` ESCLUSO dal compare snapshot
Tipo decisione che il brief lasciava aperta. Razionale: `unrealized_pnl = (current_price - avg) × holdings` cambia ad **ogni tick** col current_price, neutralizzando completamente il filtro write-on-change. Il MtM resta catturato a ogni heartbeat 5 min — granularity sufficiente per equity timeline post-go-live. Coerente con frame avg-cost canonical (memoria [[project_equity_pnl_vs_fifo]] aggiornata).

8 COMPARE_KEYS attivi: `holdings, avg_buy_price, cash_available, realized_pnl_cumulative, open_lots_count, pct_last_buy_price, stop_loss_active, stop_buy_active`. Tutti booleani o derivati da counter discreti/aggiornati solo su trade → `!=` esatto OK, no epsilon necessaria.

### Slow loop NON toccato
Vincolo brief rispettato: `sentinel_scores score_type='slow'` (240 tick = 4h, 6-7 row/giorno) ha path separato in [slow_loop.py:128](../bot/sentinel/slow_loop.py#L128), non è dietro il guard fast loop.

### Verifica live primi 2 minuti post-restart
| Tabella | Row in 2 min | Atteso |
|---|---:|---|
| sentinel_scores fast | 2 | boot + 1 tick (score cambiato BTC oscillazione) |
| sherpa_proposals | 3 | 1/bot al primo cycle (heartbeat_due=true post-restart) |
| bot_state_snapshots | 1 | BTC primo a cycle 15 (snapshot ogni 15 cycle × 60s) |

Comportamento atteso. Verifica empirica vera (30 min count vs baseline 24h) **schedulata come routine** `trig_01XmwTmHthrCAgRS6HveTcJ8`, run **2026-05-18 22:31 CET**. Output a https://claude.ai/code/routines/trig_01XmwTmHthrCAgRS6HveTcJ8

**Expected outcome**:
| Tabella | Pre-fix /30min | Post-fix /30min idle | Riduzione |
|---|---:|---:|---:|
| sentinel_scores fast | ~30 | ~3-10 | 70-90% |
| sherpa_proposals | ~45 | ~9-15 | 70-80% |
| bot_state_snapshots | ~12 | ~10-15 | ~0-20% (era già lento) |

**Commit**: `542b190`.

---

## 4. Drift FIFO sanato (commit `6183980`)

Mentre spiegavo un bug §5 🔴 [S70c] (`realized_pnl per-trade gross`) hai notato che riferivo a FIFO come benchmark. Risposta tua: *"ma non abbiamo detto che FIFO non esiste più? Mainnet e qualunque exchange non ragiona con FIFO"*. Ragione tua piena.

**Verificato:** [sell_pipeline.py:409](../bot/grid/sell_pipeline.py#L409) oggi fa `realized_pnl = revenue - cost_basis - fee` (netto). Bug stato chiuso da **S72 brief 72a Fee Unification** (commit `a1ad217`...`e975a71`, 2026-05-11). Lo stavamo trascinando come 🔴 aperto da 7 giorni.

**Frame canonical post-S72 chiarito:**
1. Bot trading logic usa `avg_buy_price` (avg-cost), coerente con quello che Binance mostra
2. `realized_pnl` per-trade post-72a = `revenue - cost_basis(avg) - fee` netto
3. **P&L totale broker-comparable = Equity P&L** = `cash_delta + Σ(holdings × spot)` (unico numero che match Binance Net Worth)
4. **FIFO è solo finzione contabile/fiscale**, non esiste fisicamente su exchange (Binance ti mostra holdings totali + avg cost, non lotti)

### Conseguenze per il roadmap

"Brief P&L netto canonico (Strada 2) ~3-4h" si riduce drasticamente:

| Componente Strada 2 originale | Stato post-frame chiarito |
|---|---|
| Sottrazione fee_usdt | ✅ DONE in 72a |
| Cambio formula avg_buy_price → FIFO | ❌ **CANCELLATO** (FIFO is dead) |
| Backfill DB pre-72a (~$0.47 testnet) | Trascurabile su paper, "story is process not numbers" |
| Verifica identità Realized + Unrealized = Equity | Sensata, ~30 min post-go-live |

**PROJECT_STATE.md aggiornato:** §5 bug [S70c] segnato CHIUSO; §3 in-flight "Strada 2 ~3-4h" → "verifica identità ~30 min"; §6 domanda CEO coerente.

**2 memorie aggiornate** fuori repo:
- `project_equity_pnl_vs_fifo` → "FIFO is dead, canonical = avg-cost + Equity P&L broker-comparable"
- `feedback_one_source_of_truth` → rimosso "FIFO replay via commentary._analyze_coin_fifo" come canonical, sostituito con avg-cost ovunque

---

## 5. Cleanup briefs + reports (commit `11b09e8`)

Su tua richiesta:
- **3 brief shipped** → `briefresolved.md/`: 78b sweep slippage, 79a idle suppress, 79b TF reactivation
- **4 report CEO consegnati** → `report_for_CEO/resolved/`: s76 refactor, s77 sprint1 audit, s77 sprint2 slow loop, s78 sweep

In `config/` restano solo i 3 brief proposti/parcheggiati: 77c admin Sentinel widgets, DUST writeoff, evaluate_trading_skills.

---

## 6. Catch del Board — sito pubblico stale

A fine sessione hai notato: *"intanto devi segnarti che domani, cambiamo il sito internet dashboard pubblica, avevamo TRF dal dottore ed invece si è riattivato"*.

Segnato in **3 posti**:
1. **Apple Note "BagHolderAI — Todo"** (canale condiviso Board↔CEO↔CC) con firma `— CC, 2026-05-18`
2. **Memoria dedicata** `project_site_tf_doctor_stale_after_79b` (cross-session)
3. **PROJECT_STATE.md §6** domanda aperta CEO + §3 TODO prossima sessione

**Idea narrativa CEO da decidere**: "TF on, ma senza shitcoin" / "Tornato dal dottore, niente più Tier 3" / o altra cornice. Stima 30-45 min implementazione (un SVG + qualche badge, no logica).

---

## 7. Decisioni delegate CC (riepilogo)

Tutte autonomi, non hai bisogno di approvarne nessuna ex-post — ma per audit trail:

1. **79a Option A** (import `HardcodedRules.MIN_LAST_SHOT_USD`) — single source of truth con grid_runner/buy_pipeline
2. **79b — non aggiungere regime a counterfactual.py** — non bloccante per restart, brief separato post-osservazione se utile
3. **79c — `unrealized_pnl` escluso dal compare snapshot** — non lo includere annullerebbe il filtro, MtM ancora catturato a heartbeat 5min
4. **79c — modulo-level state** vs refactor a classe — pattern minimo invasivo, ripartono vuoti a restart (voluto: forza fresh write post-restart)
5. **Restart raggruppato 79a+79b** poi 79c isolato — strategia "raggruppa restart" per ridurre interruzioni live (1 restart sarebbe stato meglio, ma 79c veniva dopo)

---

## 8. Audit Area 2 dovuto

**Stato cadenze al 2026-05-18** (conteggio sui file `audits/audit_report_*.md`):
- Area 1 (tecnica): ultimo 2026-05-07 (11 gg) — entro cadenza 30gg ✅
- **Area 2 (coerenza progetto)**: **MAI ESEGUITO** ⚠️ — flaggato in S78 fase 2 senza follow-up. Cadenza 90gg superata da sempre.
- Area 3 (strategy & marketing): ultimo 2026-05-15 (3 gg) — pre-go-live ✅ con riserve

Propongo: prossima sessione, prima del lavoro narrativa-sito, **breve audit Area 2 fresh CC** (brief `audit_request_20260519_area2_coerenza.md`) — ~30-45 min. Verifiche tipiche: roadmap.ts vs PROJECT_STATE vs BUSINESS_STATE consistency, validation_and_control_system.md aggiornato, memorie attive coerenti col codice, decisioni recenti tracciabili in commit.

---

## 9. Prossimi step (proposta)

**Sessione 80 (calendario tuo):**
1. **(15 min)** Verifica routine 79c verdict (link automatico per le 22:31 CET)
2. **(30-45 min)** Audit Area 2 fresh CC (vedi §8)
3. **(30-45 min)** Sito pubblico narrativa TF — "dal dottore" → "on Tier 1-2" (catch del Board §6)
4. **(opzionale)** Brief 77c admin Sentinel widgets se vuoi visualizzare regime su /admin

**Window osservativa Sentinel Sprint 2:** scadenza naturale 21-22 maggio (5-7 gg da S77 restart 2026-05-14). Dopo, sequenza Sentinel-first prosegue con step 4 (Sherpa LIVE su testnet, sell_pct primo parametro).

**TF parallelo:** counterfactual rate + eventuali allocazioni T1/T2 da osservare per ~1 settimana prima di valutare se la cornice "fear → no entries" è solida o se serve allargare distance filter / RSI threshold.

---

## 10. Note finali

- **Sessione produttiva** grazie a brief CEO auto-contenuti + dipendenze ortogonali (79a/79b/79c non si toccano). Modello da ripetere.
- **Drift FIFO** scoperto per fortuna durante una spiegazione. Lezione: memorie 13-14gg vanno SEMPRE verificate prima di asserire come fatti correnti. Sistema reminders del runtime ha funzionato.
- **PROJECT_STATE.md compattato** da 60KB → 38.6KB (sotto cap 40KB). Spostati header narrativi pre-S78 che erano ridondanti con §10. Il file era cronicamente in drift size.

**Pronto per il diario.** Suggerisco arco narrativo: "tre brief in una sera + un drift cognitivo sanato in tempo reale" — i lettori amano vedere il debug di noi stessi, non solo del bot.
