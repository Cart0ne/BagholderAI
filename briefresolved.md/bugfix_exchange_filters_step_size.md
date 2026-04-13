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

## Impatto

- SOL e BTC non hanno potuto vendere per tutta la giornata (da quando i filtri sono stati attivati)
- BONK aveva step troppo piccolo (0.1 vs 1), potenzialmente causando ordini invalidi su Binance
- Dopo il fix + riavvio: vendite riprese correttamente

## Lesson learned

Il caching dei filtri al primo avvio + nessun reload periodico ha reso il bug persistente. I filtri sbagliati venivano anche ri-cachati su Supabase ad ogni restart, sovrascrivendo qualsiasi fix manuale sul DB.
