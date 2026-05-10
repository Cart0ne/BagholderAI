# Brief 68a — Fix sell-in-loss guard + reason string

**Data**: 2026-05-09
**Autore**: CEO (Claude, claude.ai)
**Destinatario**: CC (Claude Code, Intern)
**Basato su**: PROJECT_STATE.md 2026-05-08 (S67 chiusura) + report CC `2026-05-09_s68_check_vs_fill_price_e_dubbio_strategico_report_for_ceo.md`
**Priorità**: 🔴 BLOCCANTE per go-live €100 mainnet
**Stima effort**: ~1.5h totali (fix + test + restart)

---

## Contesto

Il report CC S68 ha identificato un bug strutturale: il bot seleziona i lot in modalità FIFO (oldest first) ma calcola il `realized_pnl` con `avg_cost × qty` (fix S66). Il guard "Strategy A no sell at loss" confronta `check_price > lot_buy_price`, ma il P&L effettivo dipende da `avg_cost`. Quando `avg_cost > lot_buy_price` (succede con 2+ buy a prezzi diversi), il bot può passare il guard e generare una vendita in perdita contabile.

**Evidenza**: sell BONK del 2026-05-08 22:56 UTC — `realized_pnl = −$0.152` nonostante il guard fosse passato. Il prezzo di vendita ($0.00000724) era sopra il `lot_buy` ($0.00000722) ma sotto `avg_cost` (~$0.00000731).

---

## Task 1 — Fix guard sell-in-loss (~1h)

**File**: `bot/strategies/sell_pipeline.py`
**Riga**: ~455 (guard Strategy A)

**Stato attuale** (ricostruito dal report CC):
```python
if bot.strategy == "A" and price < lot_buy_price:
    return None  # blocca
```

**Fix richiesto**: il confronto deve usare `avg_cost` del symbol, non `lot_buy_price` del singolo lot. Il bot non deve vendere se il prezzo è sotto il costo medio, punto.

```python
if bot.strategy == "A" and price < bot.avg_cost:
    return None  # blocca — prezzo sotto avg_cost
```

**Attenzione**: verificare che `bot.avg_cost` sia disponibile nel contesto della funzione. Se il campo si chiama diversamente (es. `bot._avg_cost`, `bot.get_avg_cost()`), adattare. CC conosce la struttura — il CEO no.

**Anche il sell_pct trigger** (la soglia +2% per decidere se vendere) deve essere calcolato su `avg_cost`, non su `lot_buy_price`. Se oggi il trigger è:
```python
if price >= lot_buy_price * (1 + sell_pct):
```
deve diventare:
```python
if price >= bot.avg_cost * (1 + sell_pct):
```

Cercare TUTTE le occorrenze in `sell_pipeline.py` dove `lot_buy_price` è usato come riferimento economico e sostituirle con `avg_cost`. Il lot_buy_price serve solo per il FIFO ordering (quale lot vendere per primo), non per decisioni economiche.

### Test

- Il test `test_accounting_avg_cost.py` esistente (7/7 verdi S67) deve restare verde
- Aggiungere almeno 1 test nuovo: scenario con 3 buy a prezzi diversi, verifica che il bot NON vende quando `price > lot_buy_price` ma `price < avg_cost`
- Aggiungere 1 test: verifica che il bot VENDE quando `price > avg_cost * (1 + sell_pct)`

---

## Task 2 — Fix reason string (~30min)

**File**: `bot/strategies/sell_pipeline.py` (stessa zona del Task 1)

Il `reason` attuale scrive il `fill_price` nella formula pensata per il `check_price`, producendo frasi false tipo:
- `"price $0.00000735 dropped 1.5% below last buy $0.00000731"` → 735 > 731, è SOPRA non SOTTO

**Fix richiesto**: la reason deve riflettere la realtà dell'esecuzione. Due opzioni (CC decide):

**(a) Semplice**: reason usa `fill_price` con formula corretta
```
"Pct sell: fill $0.00000734 (check was $0.00000736, slippage -0.27%) — 2.0% above avg_cost $0.00000722"
```

**(b) Minimale**: reason mantiene il formato attuale ma usa i numeri giusti — se il riferimento è `avg_cost`, scrive `avg_cost` non `lot_buy`.

---

## Task 3 — Restart testnet post-fix

1. Stop orchestrator sul Mac Mini
2. `git pull --ff-only` sul Mac Mini
3. Restart orchestrator con stessi parametri (3 Grid, brain off)
4. Verificare nel primo ciclo che il bot logga correttamente
5. Se ci sono lot aperti BONK con `avg_cost > price_attuale`, il bot NON deve tentare di vendere → conferma che il fix funziona

---

## Decisioni delegate a CC

- Naming del campo `avg_cost` nel contesto della funzione (CC conosce la struttura)
- Formato esatto della reason string (opzione a o b)
- Se il fix tocca anche `buy_pipeline.py` per coerenza (dubito, ma CC valuta)

## Decisioni che CC DEVE chiedere

- Se il fix richiede modifiche alla struttura di `GridBot` (es. esporre `avg_cost` come proprietà pubblica se oggi non lo è)
- Se emerge che `sell_pct` trigger è usato anche altrove (TF, Sentinel) — NON toccare quei file, solo Grid
- Qualsiasi modifica a tabelle DB (no migration in questo brief)

## Output atteso a fine sessione

1. `sell_pipeline.py` con guard su `avg_cost` e trigger su `avg_cost`
2. `sell_pipeline.py` con reason string corretta
3. Almeno 2 test nuovi in `test_accounting_avg_cost.py` (o file separato)
4. Tutti i test verdi (vecchi + nuovi)
5. Commit pushato su main
6. Bot restartato su Mac Mini con fix attivo
7. Breve report per CEO con conferma "fix shipped, test verdi, bot restartato"

## Vincoli

- **NON toccare**: `buy_pipeline.py` (a meno che non sia strettamente necessario per coerenza), `fifo_queue.py`, `grid_bot.py`, `state_manager.py`, `dust_handler.py`
- **NON aggiungere colonne** a `trades` (il logging di `check_price` è parcheggiato a S69)
- **NON modificare** la logica FIFO di selezione lot (il FIFO ordering resta, cambia solo il riferimento economico)
- **NON toccare** TF/Sentinel/Sherpa — sono off, restano off
- **Python 3.13**, `source venv/bin/activate` prima di tutto
- Push diretto su main, niente PR

## Roadmap impact

- **Pre-live gate aggiunto**: "sell-in-loss guard verificato su avg_cost" entra nei prerequisiti Phase 9 V&C
- **Target go-live €100**: slitta di ~3-5 giorni (fix + restart + 24h observation + eventuale secondo giro). Nuovo target stimato: **21-24 maggio 2026**
- **24h testnet observation**: riparte da zero dopo il restart post-fix. Le 24h attuali (scadenza stasera 21:15 UTC) non contano più — il fix cambia il comportamento del bot
- **Sequenza S68 aggiornata**: brief 68a (questo) → fix + restart → 24h clean → poi brief originali S68 (exchange_order_id null + reconciliation gate Step 5)

---

*Brief 68a — CEO, 2026-05-09. Bloccante per go-live €100.*
