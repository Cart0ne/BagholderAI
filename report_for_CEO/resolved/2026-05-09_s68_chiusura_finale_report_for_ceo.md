# S68 — Chiusura sessione: bilancio finale + handoff alla nuova chat

**Data**: 2026-05-09
**Autore**: Claude Code (Intern)
**Destinatario**: CEO
**Stato sessione**: **CHIUSA**
**Sostituisce**: `2026-05-09_s68_chiusura_audit_supabase_report_for_ceo.md` (versione precedente, scritta a metà giornata quando il cleanup non era ancora deciso)

---

## 1. TL;DR

Sessione 68 aperta col Board (Max) in dubbio strategico ("mi sa che falliamo"). 4-5 ore di indagine + brainstorming hanno prodotto: 3 commit shipped, audit Supabase completo, pulizia DB eseguita, debt incurabile riconosciuto e pivot strategico verso "**trading minimum viable**" formulato come filosofia per le prossime sessioni. Bot live continua a girare Grid-only, refactor 68b in attesa di apply.

---

## 2. Cosa è stato shipped

### 2.1 Brief 68a — Fix sell-in-loss guard (commit `a8e91a0`)

`bot/grid/sell_pipeline.py`: guard "Strategy A no sell at loss" cambia da `price < lot_buy_price` a `price < bot.state.avg_buy_price` in entrambe `execute_sell` (fixed mode) e `execute_percentage_sell` (pct hot path). Reason string e log BLOCKED aggiornati a "avg cost". Test 8/8 verdi (`test_h_guard_blocks_sell_below_avg_even_above_lot_buy` aggiunto).

**Bot Mac Mini restartato** Grid-only post-fix (orchestrator PID 96199 + 3 child). Fix attivo nel codice live.

Risolve il doppio standard tra S57a (guard su lot_buy) e S66 (realized su avg_cost). Evidenza viva: BONK sell 2026-05-08 22:56 UTC con realized −$0.152.

### 2.2 Brief 68b — Refactor folder + Python managed_by (commit `39e05b7`)

- `bot/strategies/` → `bot/grid/` via `git mv` (7 file, history preservata)
- 23 import statements aggiornati cross-codebase
- Replace bulk `'trend_follower'` → `'tf'` (61 occorrenze, 14 file)
- Replace selettivo `'manual'` → `'grid'` (24 occorrenze, eccezioni preservate per stop reason Telegram)
- `bot/orchestrator.py:456` label "manual" → "Grid" per coerenza UI
- Test 8/8 verdi
- **NON ancora applicato sul Mac Mini**: bot continua a girare con folder `bot/strategies/` su commit `a8e91a0`. Apply rimandato per scelta Board (cosmetico, non urgente).

### 2.3 Cleanup database Supabase (eseguito 2026-05-09 ~14:00 UTC)

Dopo audit + decisione Board tabella-per-tabella, eseguite:

| Operazione | Target |
|------------|--------|
| `DROP TABLE` | `feedback` (vuota), `sentinel_logs` (vuota legacy v1), `portfolio` (vuota legacy v1) |
| `DROP VIEW` | `v_portfolio_summary` (legge da portfolio vuota), `v_reserve_totals` (orfana, nessuno la legge) |
| `DELETE selettivo` | 54 row `bot_config WHERE is_active=false` (TF legacy allocations) |

**Niente backup** (Board: capitale paper, tabelle vuote o dichiarate temporanee).

**Stato post-cleanup**:
- Tabelle pubbliche: 22 → **19** (-3)
- View pubbliche: 2 → **0**
- bot_config inactive: 54 → **0** (3 active preservate: BTC, SOL, BONK)
- Nessun errore, bot continua a girare

**`agent_rules` lasciata** (vuota ma "peso zero" per Board).
**`trend_scans` lasciata** (Board: "storico per analisi", retention cron 14gg gestisce naturalmente).

---

## 3. Decisioni Board prese in S68

| # | Decisione | Stato |
|---|-----------|-------|
| 1 | Filosofia: "Trading minimum viable. Complessità solo se valore aggiunto" | ✅ Acquisita |
| 2 | Solo Grid attivo. TF/Sentinel/Sherpa stay-but-off (no codice cancellato) | ✅ |
| 3 | Bot non si spegne, al limite si riavvia | ✅ |
| 4 | 3 monete (BTC + SOL + BONK), Grid only | ✅ |
| 5 | Refactor 68b apply sul Mac Mini: stand-by (cosmetico, decideremo) | ⏸️ |
| 6 | Pulizia 5 oggetti DB (3 tabelle + 2 view) + 54 row bot_config | ✅ Shipped |
| 7 | `trend_scans` rimane (storico per analisi, retention 14gg) | ✅ |
| 8 | `agent_rules` rimane (vuota, peso zero) | ✅ |
| 9 | Mainnet target invariato: €100, target 21-24 maggio 2026 | ✅ |

## 4. Decisioni Board ancora aperte (in valutazione)

| # | Tema | Stato |
|---|------|-------|
| 1 | Budget testnet $10K vs $500 (allinea wallet ↔ DB?) | ⏳ |
| 2 | `capital_per_trade` se $10K: $200/$100/$100 ipotesi | ⏳ |
| 3 | Apply 68b sul Mac Mini (quando + se) | ⏳ |
| 4 | Rimozione fixed mode (~500-800 righe codice morto) | ⏳ |
| 5 | Eliminazione `main_old.py` gemello | ⏳ |
| 6 | Phase 2 split `grid_runner.py` (BUSINESS_STATE §28) | ⏳ post-go-live |
| 7 | Reset mensile testnet Binance (verifica empirica) | ⏳ |

## 5. Scoperte tecniche fatte oggi

1. **Wallet testnet ≠ "$500"**: Binance Testnet ti regala 446 asset preassegnati + ~$10K USDT. Il "$500" è una convenzione interna nostra, Binance non lo conosce. → Implica che **Total P&L è DB-only**, Binance è fonte di verità solo per order ID/fill price/fee/timestamp.
2. **History Binance persistente**: i 12 trade live + buy nuovo BONK 09:30 UTC sono in `fetch_my_trades` e `fetch_orders`. Reconciliation `nostro_DB ↔ Binance` è fattibile via script periodico.
3. **Reset mensile testnet**: non confermato in 60s, da verificare. Se vero, finestra reconciliation = 30gg.
4. **Trigger sell sta in `grid_bot.py:749-752`**, NON in `sell_pipeline.py`. Vincolo CEO "NON toccare grid_bot.py" ha bloccato il fix esteso del trigger (che sarebbe stato un cambio strategico per-lot → all-or-nothing).
5. **Health check FIFO drift $0.28 ≈ slippage testnet**: comportamento atteso post-S66 (avg-cost vs FIFO replay), non regressione. Riclassificare come "audit informativo" in S69.
6. **`grid_runner.py` 1627 righe** di cui 833 in una sola funzione `run_grid_bot()`. Phase 2 split candidato post-go-live.
7. **Fixed mode Grid è codice morto**: 0 record DB lo usa (57 bot_config tutti `grid_mode='percentage'`). ~500-800 righe rimovibili + 4 colonne DB.
8. **`config_changes_log`**: scritto dalla dashboard `/admin` (grid.html / tf.html), letto solo da Haiku commentary. Il bot legge `bot_config` direttamente in hot-reload ogni ciclo. **I cambi parametri sulla dashboard arrivano al bot entro 1 minuto.**
9. **`exchange_filters`** (48 row): tabella infrastrutturale critica. Cache `lot_step_size`, `min_qty`, `min_notional` Binance. Il bot la legge prima di ogni order.
10. **Le 2 view DB (`v_portfolio_summary`, `v_reserve_totals`) erano orfane**: definite in passato con SQL diretto, mai documentate, nessuno le leggeva → DROP shipped.

## 6. Riconoscimento del debt strutturale (frase Board)

Citazione testuale di Max in chiusura giornata:

> "L'AI complica tutto, e nonostante le lamentele guarda dove siamo arrivati? Un botto di dati che interferiscono e variabili incontrollate. Decine di tabelle che non sappiamo se funzionano, problemi a fare calcoli di 4° elementare."

Riconoscimento storico onesto. CC concorda: la complessità accumulata in 67 sessioni era ridondanza per "robustezza" che era diventata overhead. La filosofia "minimum viable" che il Board ha formulato oggi è la correzione di rotta per le prossime sessioni.

**Cosa Max ha esplicitato che NON va toccato**: Volumi 1+2 Payhip, sito Astro, /diary, brand visivo, X automation, Telegram public channel, narrativa. Il restart è solo del **trading subsystem**, non dell'intero progetto.

## 7. Stato runtime al termine sessione

- Bot Mac Mini: **LIVE** su commit `a8e91a0` (fix 68a + folder ancora `bot/strategies/`)
- 4 processi: orchestrator 96199, BONK 96200, SOL 96201, BTC 96202
- Brain flags: `TF=False SENTINEL=False SHERPA=False` (Grid-only)
- Trade da restart: 1 nuovo (BONK buy 09:30 UTC, durante observation 2-3h)
- Total P&L approssimativo: stabile in zona +$0.10 / +$0.30 (variabile col prezzo)
- Sito: in maintenance da S65, decisione riapertura ferma in attesa testnet pulito
- DB: 19 tabelle pubbliche, 0 view, 100% pulito da debt esplicitamente dichiarato

## 8. Handoff alla nuova chat

La prossima sessione (S69 o S68 continua su nuova chat) coprirà 3 macro-temi in sequenza:

### Tema 1 — `grid.html` rebuild card-by-card
- 3 anomalie già identificate sulla dashboard `/admin/grid.html`:
  - Label "fees not deducted in paper mode" obsoleta (siamo live testnet)
  - Formula skim "0.01% of net worth" sbagliata (skim è 30% del realized, non % del net worth)
  - Drift Total P&L $0.11 visibile vs Realized+Unrealized teorico $0.45
- Definire dati che il Board vuole vedere (primo task della prossima sessione)
- Eventuale sezione "Reconciliation Binance" (script periodico DB ↔ `fetch_my_trades`)
- Pattern trovato → portato anche sulla dashboard pubblica `grid.html` di `/grid`

### Tema 2 — Pulizia codice
- Rimozione fixed mode (~500-800 righe + 4 colonne DB)
- Rimozione `main_old.py` gemello
- Apply 68b sul Mac Mini (con riavvio bot)
- Phase 2 split `grid_runner.py`: parcheggiato post-go-live

### Tema 3 — Decisione budget + (eventuale) restart
- $10K vs $500 budget testnet
- Se $10K: aggiornare `MAX_CAPITAL`, `capital_allocation`, `capital_per_trade`
- Eventuale TRUNCATE post-decisione + restart bot da zero su nuova baseline
- Pattern reconciliation Binance ↔ DB

## 9. Roadmap impact

- **Pre-live gate Phase 9 V&C**: aggiunto "sell-in-loss guard verificato su avg_buy_price" come gate. ✅
- **Pre-live gate**: aggiunto "DB schema cleanup pre-mainnet" → considerato eseguito post-S68 cleanup
- **Target go-live €100 mainnet**: confermato 21-24 maggio 2026 (Board: invariato).
- **Brief 68c (DB schema cleanup managed_by + brain CHECK constraint)**: PARCHEGGIATO. Verrà ripreso solo se Board sceglie scenario TRUNCATE+ALTER post-decisione budget $10K.
- **24h observation post-fix 68a**: passata, nessun errore, 1 trade nuovo (BONK buy clean).

## 10. Cosa NON è stato fatto in S68

- ❌ Step 5 reconciliation gate (parcheggiato)
- ❌ Fix `exchange_order_id=null` su sell (BUSINESS_STATE §24, debt cosmetico)
- ❌ Fix `reason` bugiardo su slippage (BUSINESS_STATE §27)
- ❌ Fix `recalibrate-on-restart` (debt aperto da S63)
- ❌ Apply 68b sul Mac Mini (Board pending)
- ❌ Rimozione fixed mode (rimandato)
- ❌ Phase 2 split `grid_runner.py` (BUSINESS_STATE §28, post-go-live)
- ❌ Update test_pct_sell_fifo.py legacy (debt S66, non gating)
- ❌ Backup completo DB pre-cleanup (Board: niente backup, capitale paper)

## 11. Domande aperte per il CEO (non bloccanti)

1. **Apply 68b**: lo facciamo nella nuova chat all'inizio (con riavvio bot) o lo lasciamo locale?
2. **Budget testnet $10K**: vuoi dare un input strategico ora o ne discutiamo nella nuova chat?
3. **Reset mensile testnet Binance**: vale verificarlo formalmente?
4. **Phase 2 split `grid_runner.py`**: confermi parking post-go-live €100?

---

*CC, S68 chiusura finale, 2026-05-09 ~14:30 UTC. Sessione next-action: nuova chat dedicata a (1) grid.html, (2) pulizia codice, (3) decisione budget+restart.*
