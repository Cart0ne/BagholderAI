# S68 — Brief 68a SHIPPED + bot restartato

**Data**: 2026-05-09
**Autore**: Claude Code (Intern)
**Destinatario**: CEO
**Riferimenti**: brief 68a `config/brief_68a_fix_sell_in_loss_guard.md` + report findings `2026-05-09_s68_brief_68a_scope_findings_report_for_ceo.md`

---

## Riassunto in 1 paragrafo

Brief 68a shipped come da Opzione B confermata. Guard "Strategy A no sell at loss" ora confronta `price < bot.state.avg_buy_price` invece di `price < lot_buy_price`, in entrambe le funzioni `execute_sell` (fixed mode) e `execute_percentage_sell` (pct hot path). Reason string e log BLOCKED aggiornati a "avg cost". Test 8/8 verdi (7 esistenti immutati + 1 nuovo `test_h` che verifica il blocco quando `price > lot_buy ma price < avg_buy_price`). Commit `a8e91a0` su main, Mac Mini synced. Bot restartato Grid-only (TF/Sentinel/Sherpa off via env flags) — 4 processi attivi, primo ciclo loggato senza errori. **24h observation post-restart in corso.**

---

## Cosa è stato fatto

### Codice (`bot/strategies/sell_pipeline.py`)

- Linea 264 (fixed mode): `price < lot_buy_price` → `price < bot.state.avg_buy_price`
- Linea 451 (pct hot path): stesso change
- Reason string sui sell normali pct mode: ora referenzia "avg cost" invece di "lot buy"
- Log BLOCKED + log TF override allineati allo stesso linguaggio
- Snapshot `sell_avg_cost` preso pre-mutazione per evitare reset a 0 nel reason quando la sell svuota holdings
- Variabile `lot_buy_price` mantenuta perché ancora usata da: (a) FIFO lot selection per quale lot vendere per primo, (b) audit event `sell_fifo_detail` per traceability

### Test (`tests/test_accounting_avg_cost.py`)

- `test_h_guard_blocks_sell_below_avg_even_above_lot_buy` aggiunto
- `test_e` commento aggiornato (non più riferimento a guard lot_buy)
- 8/8 verdi locale

### Vincoli rispettati

- ✅ NON toccato `grid_bot.py` (trigger sell resta per-lot, vincolo CEO confermato)
- ✅ NON toccato `buy_pipeline.py` (CEO confermato non serve)
- ✅ NON aggiunte colonne a `trades` (check_price logging parcheggiato a S69)
- ✅ NON modificata logica FIFO di selezione lot
- ✅ Push diretto su main, niente PR
- ✅ Python 3.13 + venv

---

## Cosa è successo al restart Mac Mini

- Stop orchestrator PID 90409 graceful (SIGTERM, child terminati puliti)
- `git pull --ff-only` → da `8659d8b` (S67) a `a8e91a0` (S68a). Fast-forward 7 file, 699 inserzioni, 130 cancellazioni
- Restart `python3.13 -m bot.orchestrator` con env `ENABLE_TF=false ENABLE_SENTINEL=false ENABLE_SHERPA=false`
- Nuovi PID: orchestrator 96199, BONK 96200, SOL 96201, BTC 96202
- Log conferma: `Brain flags: TF=False  SENTINEL=False  SHERPA=False`
- Tutti e 3 i Grid in idle recalibrate (last trade 8-12h fa, ref_price aggiornato al prezzo corrente)

---

## Health check warning al boot — pre-esistente, non regressione

Boot health check ha riportato 2 fail su BONK:

1. **`fifo_pnl`**: DB (avg-cost) +$0.01, FIFO replay −$0.27, Δ +$0.28
2. **`orphan_lots`**: 2 sell BONK senza `buy_trade_id` populated

**Né l'uno né l'altro è causato da 68a.** Sono debt pre-esistenti dei 3 sell BONK del 2026-05-08 (S67):

- Il drift FIFO vs avg-cost è il **risultato atteso post-S66**: le 2 metriche divergono per slippage testnet (~1% medio sui BONK trade) + non-attribuzione fee al lot. La math è coerente: realized DB +$0.01 + unrealized +$0.10 = total +$0.11 = realized FIFO −$0.27 + unrealized FIFO +$0.38. Identità preservata.
- Gli orphan_lots sono debt strutturale di `sell_pipeline` che non popola `buy_trade_id` (era previsto per brief 67a Step 5 reconciliation, parcheggiato).

**Decisione raccomandata**: il health check FIFO va riclassificato da "fail bloccante" a "audit informativo" in S69 — divergenze attese post-S66 non sono regressioni. Per ora ignoriamo i warn al boot.

---

## Cosa stiamo per fare (decisione Board)

Max (Board) ha approvato la seguente sequenza per le prossime 8-12 ore:

1. **2-3h observation bot** (in corso ora) — nessun edit, solo monitoring
2. **Aggiornamento `grid.html`** (le 3 anomalie già identificate: label "fees not deducted in paper mode", formula skim "0.01% of net worth" sbagliata, drift Total P&L vs Realized+Unrealized)
3. **2-3h observation dashboard aggiornata**
4. **Backup completo DB pre-reset** in `audits/2026-05-09_pre-reset-s68/`
5. **TRUNCATE trades + reserve_ledger + bot_state_snapshots + bot_events_log + daily_pnl** (5 tabelle, identico al pattern S67 Step 4)
6. **Liquidate all + reset wallet testnet a $500 puliti** (Max gestisce manualmente la parte faucet Binance testnet)
7. **Restart bot da zero** (Grid-only)
8. **24h observation su dati puliti** = baseline definitiva pre-go-live €100

Razionale: tutti i 12 trade live attuali sono "contaminati" dal bug pre-fix (1 sell BONK in loss strutturale). Per misurare onestamente se il fix 68a funziona serve dataset pulito dal giorno uno. Capitale paper, nessun motivo di tenere lo storico.

---

## Roadmap impact

- **Pre-live gate (Phase 9 V&C)**: aggiunto "sell-in-loss guard verificato su avg_buy_price" come gate. ✅ Verificato (test_h)
- **Target go-live €100**: **slittamento confermato a 21-24 maggio** (era 16-20). Cause: 24h observation post-fix riparte da zero + reset DB+wallet aggiunge ~6-8h alla sequenza
- **Brief 67a Step 5 (reconciliation gate nightly)**: prossimo nella coda S68/S69, è prerequisito per chiudere health check FIFO drift come "audit informativo" non "fail"
- **Bug `exchange_order_id=null` su sell OP** (PROJECT_STATE §3): ancora aperto, debt cosmetico, NO blocking

---

## Decisioni delegate a CC che CEO non sapeva

Tutte coerenti con il brief 68a:
- Naming: `avg_cost` non esiste come campo, è `bot.state.avg_buy_price` — usato direttamente
- Reason string opzione (b) "minimale" applicata
- `lot_buy_price` mantenuta come variabile per FIFO selection + audit (non più gate economico)

---

## Cosa NON è stato fatto

- ❌ NON aggiornato `PROJECT_STATE.md` (lo aggiorno a fine sessione 68, post step 8 della sequenza Board)
- ❌ NON tolto debt `main_old.py` (gemello inutile in root) — proposto a Max ma deferito a fine sessione
- ❌ NON shipped Step 5 reconciliation gate (era originalmente in scope S68, ora rimandato a post-reset)
- ❌ NON aggiornato `BUSINESS_STATE.md` (aspetto chiusura sessione)

---

## Domande aperte per il CEO (non bloccanti)

1. **Riclassifica health check FIFO** da fail a audit informativo: confermi che la divergenza FIFO-vs-avgcost è "rumore atteso post-S66" e non regressione, e che il warn al boot è OK ignorare?
2. **Reset DB+wallet S68 step 4-7**: confermi la sequenza Board approvata?
3. **Brief 68a chiuso**: posso considerarlo shipped o aspetti che le 24h observation post-reset siano passate prima di archiviarlo?

---

*CC, S68, 2026-05-09. Fix shipped, test verdi, bot restartato Grid-only, 24h observation in corso. In standby per Step 2 (grid.html) della sequenza Board.*
