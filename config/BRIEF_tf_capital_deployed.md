# BRIEF — TF: Capital Deployed vs Capital Allocated

**Status:** PARCHEGGIATO — valutare dopo qualche giorno di dati shadow
**Origine:** Session 31 (13 aprile 2026) — analisi primo report TF
**Priorità:** LOW — shadow mode, non impatta operatività

---

## Problema

Il TF mostra "Capital deployed: $500 / $500" perché legge `capital_allocation` da `bot_config` (budget assegnato). Ma i grid bot non hanno necessariamente deployato tutto il budget — parte del capitale è cash non investito.

## Stato attuale

- `sum_total_capital()` → somma tutte le `capital_allocation` = $500
- `load_current_allocations()` → somma le `capital_allocation` dei bot attivi = $500
- Risultato: il TF vede $0 disponibili, anche se i bot hanno cash libero

## Cosa servirebbe

Calcolare il capitale **realmente deployato** leggendo `total_invested` e `total_received` dai trade (come fa `_build_portfolio_summary` nel grid_runner per il daily report). Così il TF saprebbe quanto cash è effettivamente libero nel sistema.

## File coinvolti

- `bot/trend_follower/trend_follower.py` → `sum_total_capital()` e report
- `bot/trend_follower/allocator.py` → `decide_allocations()` usa `total_capital` e `allocated_capital`
