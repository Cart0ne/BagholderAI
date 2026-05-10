# Brief 69a — avg-cost trading + fixed-mode removal + DB schema cleanup + apply 68b

**Stato**: PENDING (decisione Board, deploy in finestra unica)
**Autore**: Claude Code (Intern), 2026-05-09
**Trigger**: chiusura debt strutturale FIFO/fixed mode pre-go-live €100 mainnet
**Pre-requisiti già shipped**: BLOCCO 1 (B+C: FIFO contabile via dalle dashboard), BLOCCO 2 parziale (main_old.py + sync grid_runner fixed via)

---

## 1. Scope

Migrazione del bot da **FIFO trading logic** ad **avg-cost trading**, in coerenza con la contabilità avg-cost canonica già live (post-S66). Insieme: rimozione fixed mode (codice morto), apply refactor 68b sul Mac Mini, DROP COLUMN DB delle 5 colonne fixed-mode, TRUNCATE testnet baseline e restart bot da zero.

**Non incluso**: cambio strategia di vendita rispetto al concetto base "Strategy A: vendi quando price > avg + sell_pct, blocca se < avg". Lo skim 30% resta. Le 3 coin restano BTC/SOL/BONK con allocazioni invariate ($200/$150/$150). Budget testnet **$500 confermato** (decisione Board 2026-05-09).

## 2. Decisione strategia avg-cost (cosa cambia operativamente)

**Oggi (FIFO)**:
- Bot mantiene `_pct_open_positions` queue dei buy aperti
- Trigger sell: scansiona ogni lot, se `current_price >= lot.price × (1 + sell_pct/100)` lo vende
- Sell consuma il lot oldest (FIFO drain)
- Guard S68a (post): blocca se `current_price < state.avg_buy_price`

**Post-69a (avg-cost)**:
- Bot NON mantiene più la queue
- Stato persistente: `holdings`, `avg_buy_price` (running weighted)
- Trigger sell: `current_price >= state.avg_buy_price × (1 + sell_pct/100)`
- Sell amount: `capital_per_trade / current_price` (target round-to-min_qty)
- Realized = `(current_price - state.avg_buy_price) × sell_amount`
- avg_buy_price invariato sui sell, reset a 0 quando holdings → 0
- Identità contabile chiude per costruzione: Realized + Unrealized = Total P&L

**Conseguenze trading attese** (vedi audit S69 dettagliato):
- Recovery più veloce dopo brutto buy (avg < oldest in mercato che scende)
- Niente più lot fantasma (caso BONK 22:56 in DB v3)
- Niente più bug 60c queue init
- Codice ~400-600 righe in meno

## 3. File da toccare

### 3.1 Bot Python (`bot/grid/`)

| File | Cosa |
|---|---|
| `grid_bot.py` | Rimuovere `_pct_open_positions` (linea 177). Riscrivere trigger sell (linee 749-752): da scan-per-lot a `current_price >= state.avg_buy_price × (1 + sell_pct/100)`. Rimuovere tutto il codice fixed mode (~200 righe: `_create_levels`, `lower_bound/upper_bound/num_levels` da dataclass, branch `if grid_mode == "fixed"`). `__init__` semplificato (no `grid_mode` param, no `lower_bound`, ecc.). |
| `sell_pipeline.py` | Riscrivere `_execute_percentage_sell`: niente più consume del lot oldest, calcola `sell_amount = capital_per_trade / current_price` (con round_to_step Binance), aggiorna holdings senza toccare avg. `execute_sell` (fixed path) → eliminare. |
| `state_manager.py` | `init_percentage_state_from_db` → riscrivere come avg-cost replay (running weighted) invece di FIFO replay. La nuova funzione si chiamerà `init_avg_cost_state_from_db`. |
| `fifo_queue.py` | **Eliminare il file**. `verify_fifo_queue` non serve più. |
| `buy_pipeline.py` | Rimuovere `if grid_mode == "fixed"` branch. La parte avg_buy_price weighted update resta com'è. |
| `dust_handler.py` | Verificare riferimenti FIFO residui. Probabile cleanup commenti. |

### 3.2 Bot Python (`bot/`)

| File | Cosa |
|---|---|
| `grid_runner.py` | Rimuovere `bot.verify_fifo_queue()` chiamata (linea ~670). Rimuovere logger.info su Levels/Range/grid_mode (linee 470-478, già morti post-BLOCCO 2). |
| `orchestrator.py` | Verificare commenti FIFO (linee 35, 123, 348). |

### 3.3 Allocator TF

| File | Cosa |
|---|---|
| `bot/trend_follower/allocator.py:1183-1188` | Rimuovere 4 dummy keys (`grid_mode`, `grid_levels`, `grid_lower`, `grid_upper`) dall'INSERT bot_config. **Pre-requisito**: DDL DROP COLUMN su DB (sotto). |

### 3.4 Schema DB Supabase

```sql
ALTER TABLE bot_config DROP COLUMN grid_mode;
ALTER TABLE bot_config DROP COLUMN grid_levels;
ALTER TABLE bot_config DROP COLUMN grid_lower;
ALTER TABLE bot_config DROP COLUMN grid_upper;
ALTER TABLE bot_config DROP COLUMN reserve_floor_pct;
```

Verificare anche `bot_state_snapshots` se ha colonne `lower_bound`, `upper_bound`, `grid_mode` da rimuovere.

### 3.5 Test

| File | Cosa |
|---|---|
| `tests/test_accounting_avg_cost.py` | Verificare 8/8 verdi DOPO il refactor. Possibili aggiornamenti per la nuova `_execute_percentage_sell`. |
| `tests/legacy/test_pct_sell_fifo.py` | Già archiviato in BLOCCO 1.10. |
| `tests/test_verify_fifo_queue.py` | **Spostare in `tests/legacy/`** (testa `verify_fifo_queue` rimossa). |
| Nuovi test | `test_avg_cost_state_init_from_db` (replay avg-cost al boot), `test_avg_cost_sell_trigger` (gate su avg + sell pool a price), `test_avg_cost_sell_amount` (capital_per_trade / current_price round_to_step). |

### 3.6 Apply 68b sul Mac Mini

Il refactor folder `bot/strategies/` → `bot/grid/` (commit `39e05b7`) non è ancora stato applicato sul Mac Mini. Visto che 69a richiede comunque restart bot, applichiamo 68b nello stesso slot.

**Mac Mini steps**:
1. SSH `max@Mac-mini-di-Max.local`
2. `cd /Volumes/Archivio/bagholderai && git pull`
3. Stop orchestrator + 3 child grid_runner
4. Eseguito `git pull`, codice ora su latest commit (post-69a)
5. Restart `python3.13 -m bot.orchestrator`

## 4. Sequenza esecutiva (deploy day)

1. **Pre-deploy** (1h):
   - Snapshot DB Supabase pre-deploy via export
   - Verificare branch git pulito + tutti i test 8/8 verdi
   - CEO Board approval finale

2. **Stop bot** (5 min):
   - Mac Mini: `pkill -f orchestrator`
   - Verificare tutti i 4 processi terminati

3. **TRUNCATE testnet baseline** (10 min):
   ```sql
   DELETE FROM trades WHERE config_version = 'v3';
   DELETE FROM reserve_ledger WHERE config_version = 'v3';
   DELETE FROM daily_pnl;
   DELETE FROM bot_state_snapshots;
   DELETE FROM bot_events_log WHERE created_at < NOW();  -- log pulito
   ```

4. **Schema DDL** (5 min): le 5 ALTER TABLE DROP COLUMN sopra.

5. **Codice deploy** (su Mac Mini, ~5 min):
   - `git pull` su `/Volumes/Archivio/bagholderai`
   - `python3.13 -m bot.orchestrator` (Grid-only, brain off)

6. **Smoke test prima ora** (1h):
   - Verificare 1° buy reference per BTC/SOL/BONK
   - Health check passa (senza Check 1 FIFO via, ora 3 check totali)
   - Telegram report serale OK

7. **24h observation** (giorno seguente):
   - Verificare almeno 1 trigger sell coerente con avg
   - Identità contabile chiude al centesimo (Total P&L = Realized + Unrealized − Fees)
   - Niente errori "verify_fifo_queue" residui (la funzione non esiste più)

## 5. Test plan

**Pre-deploy**:
- Test esistenti 8/8 verdi (avg-cost accounting)
- 3 test nuovi (sopra § 3.5)
- Sintassi `python -c "import ast; ast.parse(...)"` su tutti i file Python toccati
- Astro build pulito (10 pagine)

**Post-deploy**:
- Smoke test (§ 4.6)
- 24h observation con bot live
- Reconciliation manuale: confrontare DB realized totale vs Telegram report

## 6. Rollback plan

Se a 1h dal deploy il bot fa qualcosa di strano:

1. Stop orchestrator (`pkill -f orchestrator`)
2. `git revert <commits 69a>` su Mac Mini
3. Re-CREATE colonne DB rimosse (DDL inverse, accettare valori default)
4. Re-INSERT bot_config + reserve_ledger da snapshot pre-deploy
5. Restart bot
6. **Tempo stimato rollback: 30 min**

Backup pre-deploy obbligatorio (Supabase export su `audits/2026-MM-DD_pre-69a/`).

## 7. Stima

| Voce | Tempo |
|---|---|
| Riscrittura `_execute_percentage_sell` | 2-3h |
| Riscrittura `state_manager.init_avg_cost_state_from_db` | 1-2h |
| Riscrittura trigger sell `grid_bot.py:749-752` | 1h |
| Rimozione `fifo_queue.py` + `verify_fifo_queue` callers | 1h |
| Rimozione fixed mode `grid_bot.py` (~200 righe) | 2-3h |
| DDL DROP COLUMN DB + allocator dummy keys via | 30 min |
| Test suite riscrittura (3 nuovi + revisione esistenti) | 2-3h |
| Apply 68b + smoke test Mac Mini | 1h |
| Brief review + decisione Board | 1h |
| Deploy + 1h smoke + 24h observation | giornata extra |
| **Totale sviluppo** | **~10-14h** |
| **Totale wall-clock incl. observation** | **~3 giornate** |

## 8. Roadmap impact

- **Pre-live gate Phase 9 V&C**: aggiungere "avg-cost trading verified" + "DB schema cleanup post-fixed-mode"
- **Target go-live €100 mainnet**: confermato 21-24 maggio se 69a deploy entro 17-18 maggio. Slip a 24-27 se deploy slitta a 19-20.
- **Brief 67a Step 5 (reconciliation gate nightly)**: ancora aperto, va shipped post-69a (richiede nuova baseline pulita).
- **Brief Reconciliation Binance** (DB ↔ `fetch_my_trades`): post go-live €100 (vedi PROJECT_STATE §6).

## 9. Domande aperte / decisioni Board

- ✅ **Budget testnet $500** (decisione Board 2026-05-09 confermata).
- ⏳ **Data deploy 69a**: a discrezione Board. Earliest possible: domani 2026-05-10. Latest sensato: 2026-05-15 (per non slittare go-live mainnet).
- ⏳ **Reset mensile testnet Binance**: verifica formale opportuna prima del deploy?
- ⏳ **Brief 67a Step 5 (reconciliation gate nightly)**: shipped insieme a 69a o sessione separata?

## 10. Decision log dichiarato

DECISIONE: rimozione completa FIFO trading logic (Strategy A passa da per-lot a avg-pool).
RAZIONALE: coerenza totale bot ↔ dashboard ↔ Binance, codice -400-600 righe, sparizione bug 60c queue init / lot fantasma / FIFO drift health-check, recovery più veloce dopo brutto buy.
ALTERNATIVE CONSIDERATE: (B) tenere FIFO trading + dashboard avg-cost (incoerente, già scartato in S69 BLOCCO 1); (C) rifare Strategy A come "vendi LIFO" (rifiutato — niente vantaggi misurabili).
FALLBACK SE SBAGLIATA: rollback git + DB DDL inverse + bot restart pre-69a. Tempo 30 min.

---

*Brief 69a, 2026-05-09. Pronto per Board approval.*
