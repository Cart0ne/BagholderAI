# Decisione Board + CEO — S65, 8 maggio 2026

## 1. FIFO dashboard: Opzione A approvata

**Decisione:** Opzione A — tutte le 4 dashboard (home, /dashboard, /grid, /tf) smettono di fare FIFO replay client-side e leggono `SUM(realized_pnl)` da DB, filtrato per `managed_by`.

**Dettagli:**
- Realized P&L ovunque = `SUM(realized_pnl)` dalla tabella `trades` (config_version = 'v3')
- Pagine private (/grid, /tf): "Realized P&L" da DB. "Total P&L" (= Net Worth − budget) resta come label separata, ma va chiaramente etichettato come metrica diversa
- Unrealized e skim continuano a essere mostrati a parte come oggi
- FIFO replay client-side: **rimosso** dalle 3 pagine pubbliche. **Mantenuto solo in /admin** come strumento di audit interno
- Brief 60b (verify_fifo multiset): **parcheggiato** come Fix D opzionale in 62b. Non gating.

**Stima:** 30-60 min. Includere in Phase 2 Grid shipping o prima se possibile.

## 2. Go-live €100: timeline accelerata

**Decisione Board:** andiamo live con €100 su Binance mainnet appena i prerequisiti sono pronti. I 7 giorni di osservazione post-Phase 2 sono **cancellati** — usiamo i dati reali per calibrare.

**Prerequisiti non negoziabili prima del go-live:**
1. ✅ Opzione A shippata (dashboard allineate al DB)
2. ⬜ Phase 2 Grid completa (fix 60c double-call + dust management)
3. ⬜ Board approval finale (Max conferma dopo verifica visiva)

**Prerequisiti rimossi / downgraded:**
- ~~7 giorni clean FIFO drift~~ → cancellato
- ~~7 giorni clean health check~~ → cancellato
- ~~Sell-decision alignment a FIFO globale (proposta 2 CC)~~ → da verificare sul campo con €100 reali, non gating pre-live

**Target realistico:** go-live entro fine prossima settimana (12-16 maggio), dipende da velocità Phase 2.

**Obiettivo go-live:** calibrare e verificare che il gap dashboard↔Binance sia ≤5%. Se supera il 5%, stop e fix.

## 3. Prossimi step per CC

Ordine di priorità:
1. **Brief 65a task 1-3** (navbar, diary homepage, TF capital) — completare se non già fatto
2. **Opzione A** — allineare le 4 dashboard al DB (può essere un commit separato, non serve aspettare Phase 2)
3. **Phase 2 Grid** (brief 62b) — fix 60c + dust management. Questo è il gating item per il go-live

Il brief 65a task 4 (paginazione 60e) resta valido ma è ora meno urgente — con Opzione A il FIFO replay non c'è più sulle pagine pubbliche, e il cap 1000 impatta solo i conteggi e le tabelle trade recenti, non il P&L totale.

— CEO + Board, 2026-05-08
