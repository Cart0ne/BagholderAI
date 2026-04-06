# BagHolderAI — Mini-session recap
**Data:** 2026-04-05

---

## Fix 1 — Spam notifiche "BUY SKIPPED" su Telegram

**Problema:** Quando il capitale di un bot si esaurisce, il sistema manda correttamente un messaggio "Capitale esaurito" una sola volta. Tuttavia continuava a mandare una notifica "BUY SKIPPED" ad ogni ciclo (~20s), spammando il canale Telegram.

**Root cause:** La deduplication esistente usava `(level_price, cash_before)` come chiave — ma il prezzo BONK oscilla tra valori come `$0.00000545` e `$0.00000544`, rendendo la chiave diversa ad ogni ciclo e bypassando il dedup.

**Fix:** `bot/grid_runner.py` — il blocco delle notifiche BUY SKIPPED viene ora saltato interamente quando `_capital_exhausted = True`. L'utente è già stato avvisato; non serve altro fino al prossimo sell.

---

## Fix 2 — "Skim reserved" nel P&L Breakdown della homepage

**Richiesta:** Mostrare il totale dello skim accumulato nella sezione P&L Breakdown di `web/index.html`, dopo "Fees paid" (non nella stats-grid).

**Implementazione:**
- Aggiunta query a `v_reserve_totals` (vista Supabase) con filtro `config_version=eq.v3` nel `Promise.all` del `load()`
- Somma di tutti i simboli in JS (`skimTotal`)
- Aggiunto item "Skim reserved / set aside" nel breakdown, in verde, formato `+$X.XXXX` (4 decimali per gestire i micro-valori di BONK)

---

## File modificati
| File | Tipo |
|------|------|
| `bot/grid_runner.py` | Fix spam notifiche |
| `web/index.html` | Card skim homepage |

## Note operative
- Il bot va riavviato per applicare la fix delle notifiche
- Il deploy della homepage va su Vercel come di consueto
