# BRIEF (parcheggiato) — Dust write-off accounting

**Date:** 2026-04-21
**Priority:** LOW — da tirare fuori **prima del passaggio a live trading**, non prima
**Stato:** parcheggiato, da rivedere a ridosso del go-live

---

## Problema

Nel tempo, alcuni bot TF accumulano "dust": residui sotto il `min_notional` di Binance che non possono essere venduti. In paper sono solo numeri nel DB, in live sarebbero coin vere nel wallet Binance ma non liquidabili singolarmente.

**Esempio attuale (2026-04-21):** PHB ha `bought - sold = 0.10 units × $0.139 ≈ $0.01` — economic dust. Il reconciler 45 correttamente lo skippa, ma nel report `/tf`:
- il filtro `buyAmt == sellAmt` per "closed cycles" esclude PHB (sembra "mai chiuso")
- il breakdown per-coin del "TF closed-cycles loss" non lo vede
- PHB appare in `Previous coins` con `realized_pnl` valido ma holdings != 0

Micro-disallineamento cosmetico. Valori trascurabili.

---

## Perché parcheggiare (e non fixare ora)

1. **Paper:** dust è solo noise contabile. 0.01% del budget. Non sposta PnL reale.
2. **Live:** il fix giusto cambia. Avremo il wallet Binance come source of truth (non il DB). Ci sarà l'API `sapi/v1/asset/dust` per convertire dust in BNB periodicamente. Parte del fix sarà farci compatibili con queste primitive Binance, non solo con il nostro DB.
3. **Rischio di over-engineering oggi:** qualunque soluzione scritta ora in paper rischia di dover essere rifatta per live.

---

## Opzioni analizzate (2026-04-21)

Discusse con Max al volo, salvate qui per non ripartire da zero:

**Opzione 1 — Tabella `dust_writeoff` dedicata.**
Record per-simbolo che segna "PHB 0.1 units @ $0.139 = $0.01 perso, written-off il YYYY-MM-DD". UI filtra i simboli write-off dalle metriche holdings, somma i valori scritti-off nel "total loss". Lascia i `trades` intatti.
- Pro: pulita, separa audit da "stato operativo"
- Contro: altra tabella + altro codice

**Opzione 2 — Trade sintetico di chiusura.** INSERT fake sell con `amount=0.1 PHB, price=0, cost=0, reason="DUST WRITE-OFF"`. `buyAmt == sellAmt` torna vero automaticamente.
- Pro: zero cambio codice UI
- Contro: **inquina audit con dati falsi**, confonde `realized_pnl`, rischia divergenza col wallet Binance reale in live. Sconsigliata.

**Opzione 3 — Flag `written_off_at` su `trades` (o `bot_config`).**
Il reconciler, quando rileva dust sub-min_notional dopo N giorni, setta un flag che "cancella logicamente" il residuo. Query UI filtrano con `WHERE written_off_at IS NULL` per le "posizioni vive". Audit intatto.
- Pro: reversibile, pochi cambi schema
- Contro: migration + ~5 call-site da decorare

**Raccomandazione per il brief live:** Opzione 3 + integrazione con Binance `sapi/v1/asset/dust` (convert-to-BNB automatico periodico).

---

## Cosa fare quando riprenderemo

1. Prima di go-live, fare un audit completo: quanti simboli hanno dust, valore totale stimato, distribuzione
2. Decidere la strategia dust finale (Opzione 3 + Binance API)
3. Brief esteso con migration, UI impact, test plan
4. Implementare prima del primo scambio live vero

## Cosa NON fare ora

- Non cancellare trade history
- Non creare `dust_writeoff` table in paper — aspettare contesto live
- Non fare micro-fix alla UI per "nascondere il dust" — è dati, non bug visivo

---

## Riferimenti

- Reconciler attuale (45): [config/brief_45_orphan_reconciler.md](brief_45_orphan_reconciler.md) — già skippa dust sub-$5 correttamente
- Binance dust API (per future ref): `POST /sapi/v1/asset/dust` (convert to BNB)
- Dust detection in grid_bot: [bot/strategies/grid_bot.py](../bot/strategies/grid_bot.py) già ha `min_notional` check che elimina lot-level dust dalle FIFO queue — il residuo contabile è un'altra cosa
