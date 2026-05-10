# Decisione Board — Gap riconciliato (S65, 8 maggio 2026)

CC, ottimo lavoro sulla riconciliazione. La diagnosi è chiara, il Board approva 
le 3 azioni che proponevi. Procedi così:

## 1. Opzione 3 — Dashboard mostrano solo Total P&L

Sulle 4 dashboard (home, /dashboard, /grid, /tf):
- **Rimuovere** "Realized P&L" come metrica primaria
- **Mostrare** "Total P&L" (= Net Worth − Budget) come numero principale
- Total P&L è l'unico numero matematicamente coerente e identico a quello 
  che Binance mostrerà su mainnet

Su `/admin` aggiungere una sezione "Reconciliation" (audit interno):
- Realized DB (sovrastimato)
- Realized strict-FIFO (matematico)
- Bias = differenza
- Identità: Realized_FIFO + Unrealized = Total ✓

Stima: ~30 min.

## 2. Schema drift skim — fix minimo solo `reserve_ledger`

NON rinominare `manual` → `grid` ora (troppo rischioso durante DRY_RUN Sherpa, 
tocca 4 tabelle, contamina il counterfactual).

**Limite del fix in S65:** script SQL one-shot che porta i `reserve_ledger` 
con `trade_id` legacy alla label coerente con `trades.managed_by`:

```sql
UPDATE reserve_ledger rl
SET managed_by = t.managed_by
FROM trades t
WHERE rl.trade_id = t.id
  AND rl.managed_by IS DISTINCT FROM t.managed_by;
```

(verifica conteggio prima/dopo, no surprise)

**Rename `manual` → `grid` su tutto il sistema:** parcheggiato come task 
post-go-live + post-Phase 2 stabile. Aggiungerlo a BUSINESS_STATE §5 come 
"NEW".

Stima: 15 min.

## 3. Bias avg_buy_price → brief 60b diventa gating per go-live €100

Documentare in PROJECT_STATE.md §5 (bug noti) e §6 (domande aperte CEO):

> **Bias DB realized_pnl Grid: +$20.44 (28%)** — il bot scrive 
> `trades.realized_pnl` usando `avg_buy_price` (media mobile dei buy aperti) 
> invece del cost basis del lotto specifico in uscita. Su Grid in regime 
> volatile sovrastima del 20-30%. Su TF il bias è ~$0 perché TF gestisce 
> tipicamente 1 lotto per coin (verificare).

**Brief 60b** (verify_fifo multiset / strict-FIFO accounting nel bot): 
- Stato: era parcheggiato post-Opzione A. **Riportato a gating per go-live €100.**
- Pre-requisiti aggiornati per il go-live: 
  1. ✅ Opzione A shippata (DB-based dashboards) — già fatto
  2. ⬜ Opzione 3 implementata (dashboards mostrano Total P&L)
  3. ⬜ Schema drift skim fixato
  4. ⬜ Brief 60b shippato (bot scrive realized_pnl matematicamente corretto)
  5. ⬜ Phase 2 Grid completa (fix 60c + dust)
  6. ⬜ Board approval finale

**Target go-live aggiornato:** slitta di qualche giorno per il brief 60b. 
Da 12-16 maggio → realistico 16-20 maggio. Decisione Board: accettiamo lo 
slittamento perché il fix del bias è essenziale per dire "gap dashboard ↔ 
Binance ≤ 5%" su dati matematicamente coerenti.

## Ordine di esecuzione consigliato

1. Schema drift skim (15 min) — pulizia DB, indipendente dal resto
2. Opzione 3 (30 min) — dashboard pubbliche al posto di Realized
3. /admin Reconciliation section (~30 min) — la "scatola interna" per audit
4. Brief 60b — pianificare separatamente, può iniziare in parallelo a Phase 2

PROJECT_STATE.md e BUSINESS_STATE.md vanno aggiornati alla fine della sessione 
con le decisioni di oggi.

— CEO + Board, 2026-05-08
