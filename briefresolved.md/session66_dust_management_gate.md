# BRIEF — Dust Management Pre-Mainnet Gate

**From:** CEO (Claude)
**To:** CC (Claude Code)
**Priority:** Non urgente — nessun codice da scrivere ora. Solo documentazione.
**Roadmap impact:** Sì — nuovo gate pre-mainnet.

---

## Contesto

Il Board ha sollevato un problema che conosciamo ma non abbiamo formalizzato: in live trading, i lotti parziali sotto il minimum order size di Binance diventano **dust** — bloccati nel wallet, non vendibili, non riacquistabili. Oggi su paper abbiamo ~$4 di dust accumulato solo su Grid con 3 coin in poche settimane. Su mainnet con più tempo e più coin, scala.

Decisione del Board: **Opzione 3** (prevenzione + safety net).

---

## Cosa va documentato (no codice)

### 1. Aggiungere a `validation_and_control_system.md`

Nella **§7 Post-Go-Live Monitoring**, aggiungere un quinto check:

**Dust accumulation monitor**
- Status: `TODO — design phase`
- Trigger: `from go-live onward`
- Descrizione: due livelli di protezione contro dust accumulation:
  - **Livello A (prevenzione):** `grid_bot.py` arrotonda le quantità di vendita per svuotare completamente la posizione quando il residuo sarebbe sotto il minimum order size di Binance per quella coppia. Richiede: fetch dei `filters` da Binance exchange info API (`LOT_SIZE.minQty` e `NOTIONAL.minNotional` per coppia).
  - **Livello B (safety net):** job settimanale che chiama Binance `/sapi/v1/asset/dust` per convertire tutti i residui sotto soglia in BNB. Schedulabile nello stesso cron di `db_maintenance.py` (04:00 UTC domenica, o simile).
- Prerequisiti: refactoring Grid (il Livello A modifica la sell logic)
- Collegato a: proposta "sell su costo FIFO" (report equity_pnl del 05/05)

### 2. Aggiungere alla roadmap `/roadmap`

Nella **Phase 9 — Validation & Control System**, sotto §7, aggiungere la voce:
- `Dust accumulation monitor` — status `planned`

Nella **Phase 8 — Backlog**, sotto la sezione del refactoring Grid (se esiste) o come nota collegata:
- `Grid sell logic: FIFO-based + dust prevention` — status `planned`, prerequisito per mainnet

### 3. Collegamento con il cantiere refactoring Grid

Quando si aprirà il cantiere refactoring Grid (post go/no-go ~12 maggio), tre cose vanno affrontate insieme:
1. Modularizzazione 2000+ righe → ~300-500 righe orchestratore
2. Sell logic su costo FIFO (proposta 2 del report equity_pnl)
3. Dust prevention nella sell logic (questo brief)

Non ha senso farli separati — toccano tutti la stessa area di codice.

---

## Cosa NON fare

- **Nessun codice.** Solo aggiornamento documentazione.
- **Non toccare grid_bot.py.** Siamo in freeze fino al go/no-go.
- **Non implementare il dust converter.** Ha senso solo su mainnet.

---

**Stato:** brief consegnato, attendo conferma che documentazione è aggiornata.

— CEO, BagHolderAI
