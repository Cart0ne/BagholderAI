# Bug Report: Exchange Filters — lot_step_size errato

**Severity:** HIGH — bloccava tutte le SELL su SOL e BTC
**Discovered:** April 13, 2026
**Fixed:** same day

---

## Sintomo

SOL/USDT spammava `SELL order rejected: amount=0 <= 0` ogni 45 secondi. Il bot aveva 0.145 SOL in profit (+2.26%) ma non riusciva a vendere. BONK aveva un problema simile: `amount 3878984.8 not aligned to step_size 0.1`.

## Root cause (2 bug in `utils/exchange_filters.py`)

### Bug 1 — Step size calcolato sbagliato (riga 38)

```python
# PRIMA (sbagliato)
lot_step_size = 10 ** (-int(amount_precision))
```

Il codice trattava `precision.amount` come "numero di decimali" (es. 3 → 0.001). Ma ccxt per Binance restituisce **direttamente lo step size** (es. 0.001). Facendo `int(0.001)` → `0` → `10^0` → **1**. Risultato: il bot pensava di poter tradare solo quantità intere di SOL e BTC.

| Symbol | Step calcolato | Step reale |
|---|---|---|
| BTC/USDT | `1` (= 1 BTC intero!) | `0.00001` |
| SOL/USDT | `1` | `0.001` |
| BONK/USDT | `0.1` | `1` |

### Bug 2 — Floating point in `round_to_step()` (riga 115)

```python
# PRIMA (floating point artifacts)
math.floor(amount / step_size) * step_size
# → 3878984.8000000003 invece di 3878984.8
```

L'amount arrotondato aveva garbage decimale, poi `validate_order()` lo rifiutava perché non era allineato allo step.

## Fix applicato

```python
# Bug 1: precision.amount È già lo step size
lot_step_size = float(amount_precision)

# Bug 2: Decimal per evitare floating point
from decimal import Decimal, ROUND_DOWN
result = (Decimal(str(amount)) / Decimal(str(step_size))).to_integral_value(rounding=ROUND_DOWN) * Decimal(str(step_size))
```

### Bug 3 — Dust spam dopo vendita (grid_bot.py)

Dopo una vendita, il residuo (dust) troppo piccolo per lo step size restava nella coda dei lot. Il bot riprovava a venderlo ogni ciclo, spammando `SELL order rejected: amount=0 <= 0` all'infinito.

Fix: se dopo `round_to_step` l'amount è 0, il lot viene rimosso dalla coda e loggato una sola volta.

```python
if amount <= 0:
    # Dust — rimuovi lot dalla coda, smetti di riprovare
    self._pct_open_positions.pop(0)
    return None
```

### Dust: analisi impatto

Il dust è inevitabile (rounding per difetto) ma trascurabile:

| Symbol | Step size | Dust max | Prezzo | Valore |
|---|---|---|---|---|
| SOL/USDT | 0.001 | ~0.001 SOL | $83 | $0.08 |
| BTC/USDT | 0.00001 | ~0.00001 BTC | $85,000 | $0.85 |
| BONK/USDT | 1 | ~1 BONK | $0.0000057 | $0.000006 |

Il dust non si accumula: resta al massimo 1 step per asset.

## Impatto

- SOL e BTC non hanno potuto vendere per tutta la giornata (da quando i filtri sono stati attivati)
- BONK aveva step troppo piccolo (0.1 vs 1), potenzialmente causando ordini invalidi su Binance
- Dopo il fix + riavvio: vendite riprese correttamente, dust gestito silenziosamente

## Lesson learned

- Il caching dei filtri al primo avvio + nessun reload periodico ha reso il bug persistente. I filtri sbagliati venivano anche ri-cachati su Supabase ad ogni restart, sovrascrivendo qualsiasi fix manuale sul DB.
- Dopo una vendita, validare sempre che il residuo sia vendibile prima di reinserire nella coda.
