# BRIEF — TF: Capital Deployed vs Capital Allocated

**Status (2026-04-19):** OBSOLETO — assorbito da 36g / 39e / 39f.
Il brief nasceva nel contesto session 31 quando il TF era in shadow
e il "Capital deployed: $500/$500" dei manual bots veniva calcolato
sommando i `capital_allocation` (ceiling) invece che il cost basis
reale dei lotti aperti. Da allora:

  - TF ha un budget separato (`tf_total_capital` = nominal + floating)
    e non usa più quella vista aggregata. 36g Phase 1+2 copre il
    compounding del capitale TF.
  - Manual bots (BTC/SOL/BONK) hanno già la distinzione deployed vs
    allocated su `/admin` (JS client-side, FIFO su trades) e nel daily
    Telegram report (`_build_portfolio_summary`).
  - 39f A ha droppato la vista `tf_capital_summary` che era l'ultimo
    punto in cui il bug "phantom allocated" si manifestava.
  - `sum_total_capital()` in trend_follower.py è codice morto (nessun
    chiamante vivo) — può essere cancellato in una pulizia futura,
    nessuna urgenza.

Nessuna azione residua richiesta. Archiviato senza modifiche al codice.
Se un giorno servisse una vista unificata "deployed vs allocated"
manual, aprire un brief nuovo con scope chiaro — non riesumare questo.

---

**Status originale:** PARCHEGGIATO — valutare dopo qualche giorno di dati shadow
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
