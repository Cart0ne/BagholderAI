# BagHolderAI — Intern Brief Session 22b
**Data:** 2026-04-06
**Priorità:** CRITICA — bot non vende, dashboard numeri sbagliati

---

## Fix 1 — CRITICO: FIFO sell blocking (il bot non vende SOL)

**File:** `bot/strategies/grid_bot.py`

**Problema:** Il sell loop in `_check_percentage_and_execute()` controlla solo il primo lotto nella coda FIFO (`_pct_open_positions[0]`). Se il lotto più vecchio non ha raggiunto il sell_pct threshold, tutti i lotti successivi — anche se profittevoli — restano bloccati.

**Esempio reale adesso:**
- Lotto 1 (oldest): buy @ $82.37 → sell trigger $83.19 → prezzo attuale $82.30 → **NON vende**
- Lotto 2: buy @ $78.56 → sell trigger $79.35 → prezzo $82.30 → **DOVREBBE vendere ma bloccato**
- Lotto 3: buy @ $77.15 → trigger $77.92 → bloccato
- Lotto 4: buy @ $81.21 → trigger $82.02 → bloccato
- Lotto 5: buy @ $79.67 → trigger $80.47 → bloccato

**Fix richiesto:** Il sell loop deve iterare su TUTTI i lotti in `_pct_open_positions` e vendere ogni lotto il cui `buy_price * (1 + sell_pct) <= current_price`. L'ordine FIFO resta regola contabile: tra i lotti triggerati, vendi prima il più vecchio. Ma NON bloccare i successivi se il primo non triggera.

**Pseudocodice:**
```python
# PRIMA (bug):
if len(self._pct_open_positions) > 0:
    oldest = self._pct_open_positions[0]
    if current_price >= oldest['buy_price'] * (1 + sell_pct):
        sell(oldest)

# DOPO (fix):
lots_to_sell = []
for lot in self._pct_open_positions:
    if current_price >= lot['buy_price'] * (1 + sell_pct):
        lots_to_sell.append(lot)

# Sell in FIFO order (oldest first among triggered)
for lot in lots_to_sell:
    sell(lot)
    # Remove from _pct_open_positions after sell
```

**ATTENZIONE:** Non modificare la lista durante l'iterazione — raccogli prima, vendi dopo. Mantieni cooldown tra sell consecutivi se esiste.

**Dopo vendita di TUTTI i lotti (holdings → 0):** resetta `_pct_last_buy_price` al prezzo dell'ultimo sell (come già nel last-lot logic, Fix 8 Session 22).

---

## Fix 2 — Dashboard: Portfolio Value sottostimato

**File:** `web/admin.html` → funzione `analyzeCoin()`

**Problema:** Righe 499-502:
```javascript
if (positionClosed) netSpent = 0;
var cashLeft = alloc - netSpent;
```
Quando posizione chiusa (BONK), `netSpent` clampato a 0 → `cashLeft = alloc`. Ma il cash REALE è `alloc + realizedPnl`, perché il profitto è tornato come cash.

**Esempio:** BONK allocation $150, realized P&L $3.46. Cash reale ≈ $153.46. Dashboard mostra $150. Portfolio Value sottostimato di ~$5.

**Fix:**
```javascript
if (positionClosed) {
    netSpent = 0;
    cashLeft = alloc + realizedPnl;
} else {
    cashLeft = alloc - netSpent;
}
```

**Nota sullo skim:** Verificare se `realized_pnl` nei trade è lordo o netto dello skim:
- `SELECT SUM(realized_pnl) FROM trades WHERE symbol='BONK/USDT' AND config_version='v3'`
- `SELECT SUM(amount) FROM reserve_ledger WHERE symbol='BONK/USDT' AND config_version='v3'`
Se lo skim non è sottratto da realized_pnl → serve `cashLeft = alloc + realizedPnl - skimForCoin`.

---

## Fix 3 — Dashboard: Unrealized P&L usa avg buy sbagliato

**File:** `web/admin.html` → funzione `renderOverview()`, righe 541-550

**Problema:** Avg buy usa TUTTI i buy trades storici:
```javascript
var avgBuy = totalBoughtCost / totalBoughtAmt;
```
Con FIFO, i lotti venduti sono i più vecchi. L'unrealized deve usare il costo medio dei lotti RIMANENTI.

**Fix:** Ricostruire FIFO nel frontend:

```javascript
var buyQueue = [];
var coinTrades = tradesData
    .filter(t => t.symbol === cfg.symbol)
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

coinTrades.forEach(function(t) {
    if (t.side === 'buy') {
        buyQueue.push({ amount: Number(t.amount), price: Number(t.price), cost: Number(t.cost) });
    } else {
        var remaining = Number(t.amount);
        while (remaining > 0.000001 && buyQueue.length > 0) {
            var lot = buyQueue[0];
            if (lot.amount <= remaining + 0.000001) {
                remaining -= lot.amount;
                buyQueue.shift();
            } else {
                lot.amount -= remaining;
                lot.cost -= remaining * lot.price;
                remaining = 0;
            }
        }
    }
});

var openCost = buyQueue.reduce((s, l) => s + l.cost, 0);
var openAmt = buyQueue.reduce((s, l) => s + l.amount, 0);
var avgBuyOpen = openAmt > 0 ? openCost / openAmt : 0;
var unrealized = openAmt > 0 ? (livePrice - avgBuyOpen) * openAmt : 0;
```

**Nota:** Trade servono ordinati `created_at ASC` per FIFO. Query attuale ordina DESC — riordinare nel frontend.

---

## Fix 4 — Dashboard: display Buy/Sell count confuso

**File:** `web/admin.html` → riga 628

**Problema:** BONK mostra "12 / 14" (più sell che buy). Corretto (vendite parziali) ma confonde.

**Fix:**
```javascript
// PRIMA:
'<div class="cs-label">Buys / Sells</div><div class="cs-value">' + a.buyCount + ' / ' + a.sellCount + '</div>'

// DOPO:
'<div class="cs-label">Trades</div><div class="cs-value">' + a.buyCount + 'B / ' + a.sellCount + 'S</div>'
```

---

## Fix 5 — Grid mode hot-reload senza restart

**File:** `bot/grid_runner.py` (config refresh loop)

**Problema:** Il refresh ogni 5min aggiorna parametri numerici ma non switcha strategia se `grid_mode` cambia. SOL ha girato in fixed mode per 30+ ore nonostante config dicesse `percentage`.

**Fix:** Nel config refresh callback:
```python
new_mode = config.get('grid_mode')
if new_mode != self._current_grid_mode:
    logger.info(f"Grid mode changed: {self._current_grid_mode} → {new_mode}")
    self._current_grid_mode = new_mode
    if new_mode == 'percentage':
        self.init_percentage_state_from_db()
    logger.info(f"Strategy re-initialized for {new_mode} mode")
```

**ATTENZIONE:** `init_percentage_state_from_db()` ricostruisce da DB, safe da chiamare. NON resettare holdings.

---

## Ordine di esecuzione

1. **Fix 1** (FIFO sell) — URGENTE, bot perde profitto ORA
2. **Fix 5** (hot-reload) — previene ricorrenze
3. **Fix 2** (Portfolio Value) — numeri sbagliati
4. **Fix 3** (Unrealized avg) — numeri sbagliati
5. **Fix 4** (display) — cosmetico

## Test

- **Fix 1:** Riavviare bot SOL → deve vendere lotti 2-5 (tutti sopra threshold tranne lotto 1)
- **Fix 2-4:** Ricaricare admin → Portfolio Value ≈ $500 + Total P&L; BONK cash > $150
- **Fix 5:** Cambiare grid_mode in Supabase → log mostra re-init senza restart
