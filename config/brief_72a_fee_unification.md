# Brief 72a — Fee Unification

**Stato:** PROPOSAL — attende approval CEO post-S72
**Origine:** Sessione 72 (2026-05-11). Diagnosi BONK drift testnet ha smentito la teoria S71 "fix isolato 71b" e ha ricondotto 3 bug separati (holdings drift, avg_buy gross, realized_pnl gross) a un'unica radice contabile fee.
**Stima:** 4-6h codice + test + rollout. **Pre-go-live €100 gate.**
**Dipendenze:** nessuna. Sostituisce e chiude brief 71b (BONK InsufficientFunds) + Strada 2 (P&L netto canonico) + Open question 27 (reason bugiardo, già chiusa S71). Non tocca paper trade storici (decisione Max 2026-05-11).

---

## 1. Background — perché un brief unico

Nelle sessioni S67-S71 sono emersi 3 bug fee separati, fixati o parcheggiati a brief diversi:

1. **BONK InsufficientFunds** (S71): `state.holdings += filled` lordo. Drift osservato 12.280 BONK vs Binance reale.
2. **avg_buy_price sottostima cost reale** (S70c): `avg = (price × qty_lorda)` ignora la fee di acquisto.
3. **realized_pnl gross** (S70c): `revenue − cost_basis` non sottrae `fee_usdt`.

S72 ha dimostrato che sono **lo stesso bug** visto da 3 angolazioni. Il fix incrementale a fettine (brief 71b + Strada 2 + altro) era condannato a inseguire sintomi senza chiudere la radice.

## 2. Diagnosi S72 — numeri verificati

Run su Mac Mini 2026-05-11 13:54 UTC (`/tmp/diag_bonk_drift2.py` via SSH).

| Voce | Valore | Origine |
|---|---|---|
| Buy lordo cumulato BONK | 30.726.196 | sum executedQty Binance |
| **Fee BONK reale** | **30.726,2** | sum commission per fill = 0.1% lordo esatto |
| Sell cumulato BONK | 29.057.158 | fee in USDT (0.22 totale) |
| Net teorico (lordo − fee − sell) | 1.638.311,8 | quello che avremmo se partivamo da 0 |
| **Binance reale `fetch_balance()`** | **1.656.757,8** | API oggi |
| Initial balance fantasma | **+18.446** | BONK pre-S67 sul testnet, non in fetch_my_trades |
| DB holdings | 1.669.038 | bug: somma lordo, ignora fee BONK |

**Equazione che chiude**: 1.656.757,8 = 30.726.196 − 30.726,2 − 29.057.158 + 18.446 ✓

**Implicazione critica**: il replay deterministico dal DB **non può** ricostruire holdings reali, perché ignora i depositi iniziali testnet (e ogni futuro drift orfano: reset mensile, trasferimenti, errori transient). **Holdings deve venire da Binance, sempre.**

## 3. Le 3 proprietà invariabili (assiomi)

Tutto il sistema (bot, DB, dashboard, replay, reconciliation) rispetta queste regole, sempre:

### P1 — Holdings = `exchange.fetch_balance()` come golden source

- **Al boot**: `state.holdings = balance_binance[base_coin]`. Il replay DB **non scrive holdings**.
- **Dopo ogni BUY/SELL fill**: incremento coerente in-memory:
  - BUY: `state.holdings += filled − fee_base`
  - SELL: `state.holdings -= amount`
- **Sanity check post-trade**: opzionale, off di default. Se on, log warn se gap > 0.5%.
- **Soglie boot reconcile**: warn >0.5%, fail-to-start >2%, **no override env** (decisione Max S72).

### P2 — Avg buy price = cost USDT vero / qty realmente acquisita

Per ogni BUY in `state_manager.init_avg_cost_state_from_db`:
- `cost_usdt = filled × price` (USDT pagati, escluso fee Binance — Binance scala fee in BONK, USDT è solo il valore notional)
- `qty_acquired = filled − fee_base_estimato`
- `avg = (avg_old × qty_old + price × qty_acquired) / (qty_old + qty_acquired)`

dove `fee_base_estimato = fee_usdt / price` se `fee_asset == base_coin`, altrimenti 0.

**Decisione Opzione A su initial balance**: i ~18.446 BONK fantasma testnet sono ignorati nel calcolo `avg`. Avg riflette il vero costo medio sui trade del bot. Non un'ibridazione tra trade e testnet-gift.

### P3 — Realized P&L = (price − avg) × qty − fee_sell_usdt

Per ogni SELL in [sell_pipeline.py:~397](bot/grid/sell_pipeline.py#L397):
- `realized_pnl = (price − state.avg_buy_price) × amount − fee_usdt`

E nel replay (`init_avg_cost_state_from_db`):
- `realized += (price − avg_at_sell) × amount − fee_usdt`

Conseguenza: ogni riga dashboard "Recent trades" mostra il P&L vero (post-fee), e il cumulato dashboard coincide con la differenza wallet Binance.

## 4. Punti di codice

| # | File | Cambio |
|---|---|---|
| 1 | [bot/exchange_orders.py:188-208](bot/exchange_orders.py#L188-L208) | `_normalize_order_response` ritorna anche `fee_base` (= `fee_native` se `fee_currency==base_coin` else 0). BNB-aware: `fee_currency==BNB` → `fee_base=0`, `fee_usdt=0` con warn (Step 5 cross-rate post-mainnet). |
| 2 | [bot/grid/buy_pipeline.py:184-193](bot/grid/buy_pipeline.py#L184-L193) | `state.holdings += filled − fee_base` (P1). `avg = (avg_old × qty_old + price × (filled − fee_base)) / qty_new` (P2). |
| 3 | [bot/grid/sell_pipeline.py:~397](bot/grid/sell_pipeline.py#L397) | `realized_pnl = (price − avg) × amount − fee_usdt` (P3). |
| 4 | [bot/grid/state_manager.py:64-79](bot/grid/state_manager.py#L64-L79) | replay calcola avg + realized + total_invested + total_received con P2/P3. NON scrive `state.holdings`. |
| 5 | [bot/grid/state_manager.py:114-120](bot/grid/state_manager.py#L114-L120) | **NEW**: dopo replay, `balance = exchange.fetch_balance()` → `state.holdings = balance[base_coin].total`. Se gap_pct > 0.5% warn (bot_events_log), > 2% raise `RuntimeError` (refuse-start). Paper mode skippa la chiamata (state.holdings da replay) — invariato. |
| 6 | `tests/test_accounting_avg_cost.py` | 3 casi nuovi: **P** (BUY con fee_asset==base scala holdings netto), **Q** (realized_pnl include fee_sell), **R** (replay vs fetch_balance — ricostruzione corretta di avg ignorando initial fantasma). |

Niente migration DB. `trades.amount` resta lordo (audit trail intatto). `trades.fee` resta USDT-equivalent (già scritto correttamente). `trades.realized_pnl` viene **ricomputato in DB** per trade live testnet (UPDATE post-deploy, vedi §6).

## 5. Test plan

### 5.1 Unit tests (pre-deploy)

Aggiungere a `tests/test_accounting_avg_cost.py`:

- **Test P** — `test_buy_with_fee_in_base_scales_holdings_net`: simulate BUY filled=1000 BONK, fee_native=1 BONK, fee_currency=BONK → assert `state.holdings == 999`, `state.avg_buy_price == price × 1000 / 999` (cost basis vero per coin posseduta).
- **Test Q** — `test_realized_pnl_includes_sell_fee`: BUY @ 1.0 → SELL 100 @ 1.10 con fee_usdt=0.011 → assert `realized_pnl == (1.10 − 1.00) × 100 − 0.011 == 9.989`.
- **Test R** — `test_replay_initializes_avg_ignoring_initial_balance`: mock fetch_balance ritorna 1500. Replay vede solo 1000 BUY. Assert `state.holdings == 1500` (golden source), `state.avg_buy_price` calcolato solo sui 1000 BUY (ignora 500 fantasma).

Target: 18/18 verdi (15 attuali + 3 nuovi).

### 5.2 Dry-run replay (pre-restart bot live)

Script `audits/72a_holdings_dry_run.py`:
1. Per ogni symbol live (BTC, SOL, BONK): replay con nuove formule
2. Confronto qty replayed (netto) + initial fantasma stimato vs `fetch_balance()` reale
3. Output tabella: symbol | replay_net | fetch_balance | gap_pct | passa soglia (warn 0.5%, fail 2%)
4. Aspettativa: BONK gap ~1.1% (warn ok), BTC/SOL gap < 0.1% (silenzioso)

### 5.3 Boot-time integration test

Restart orchestrator su Mac Mini (TF=false, S+S DRY_RUN come oggi) con nuova logica:
- Verificare che `state.holdings` post-init sia identico a `fetch_balance()` per tutti e 3 i symbol
- Verificare che il primo BUY successivo aggiorni holdings al netto della fee
- Verificare che il primo SELL successivo non rigetti più (InsufficientFunds resolved)

## 6. Rollout plan

1. **Pre-deploy**: PR + test suite verde + dry-run audit script
2. **Stop orchestrator Mac Mini**: `kill -TERM <parent_pid>` graceful
3. **Pull** Mac Mini + smoke pytest
4. **Backfill DB testnet**: `UPDATE trades SET realized_pnl = (price - X) * amount - fee WHERE mode='live' AND config_version='v3' AND side='sell'` (X = avg al momento del trade, calcolato dal replay nuovo). **Paper trade NON toccati** (decisione Max 2026-05-11). Diff cumulato atteso: ~−$0.47.
5. **Restart**: `caffeinate -dis env ENABLE_TF=false SENTINEL_TELEGRAM_ENABLED=false SHERPA_TELEGRAM_ENABLED=false python3.13 -m bot.orchestrator &`
6. **Verifica boot logs**: cercare riga `"Holdings synced from Binance: {symbol}={qty}"` per tutti e 3 i symbol. Warn 0.5% atteso solo su BONK (initial fantasma 1.1%), niente fail.
7. **Osservazione 24h**: niente più alert ORDER_REJECTED BONK. Nuovi trade scrivono realized_pnl netto.
8. **Memoria update**: salvare `feedback_holdings_golden_source` se la decisione si conferma stabile.

## 7. Open questions (per CEO)

- ❓ **Backfill paper trade**: confermo decisione S71 "paper resta as-is"? Diary post-fix dovrà spiegare che la cronologia paper ha realized_pnl gross mentre testnet ha netto. Storia divisa.
- ❓ **Soglie 0.5% / 2% adeguate?** Su mainnet (no initial fantasma, no reset) gap dovrebbe essere ~0. Su testnet, BONK avrà sempre ~1.1% post-fix (initial fantasma non recuperabile). Bot partirà sempre con warn. Accettabile?
- ❓ **Sanity check post-trade ON o OFF di default?** Lo abbiamo già al boot. Aggiungere check dopo ogni fill significa 1 chiamata `fetch_balance()` extra ogni trade. Rate limit ok ma costo API non zero.

## 8. Cosa NON si fa con questo brief

- Slippage_buffer parametrico per coin (brief separato pre-mainnet)
- Phase 2 split di `grid_runner.py` (62b parcheggiato post-go-live)
- BNB-discount cross-rate runtime (Step 5 — brief separato quando si abilita BNB mainnet)
- Sherpa rule-aware sulla hotfix slippage BONK (brief separato pre-SHERPA live)

## 9. Roadmap impact

**Phase 9 V&C — Pre-Live Gates**: aggiunge ✅ "Fee unification (holdings = golden source, avg netto, realized netto)" come ultima gate prima del go-live €100. Chiude in unico colpo brief 71b + Strada 2 ridotta.

**Target go-live €100**: dipende dalla complessità del rollout. Stima: 4-6h codice + 24h osservazione + report Max. Realistico **15-18 maggio** per chiudere il brief, **18-21 maggio** per il go-live se osservazione clean. Slip vs target "fine maggio/inizio giugno" del BUSINESS_STATE: ottimistico — possibile ricuperare 1 settimana.

---

*Brief redatto da CC (Intern) post-diagnosi S72. Attende CEO update + approval prima del codice.*
