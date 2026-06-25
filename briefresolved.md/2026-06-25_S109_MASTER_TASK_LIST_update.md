# Master Task List Update — S109 (2026-06-25)

**Istruzioni per CC:** aggiornare `config/MASTER_TASK_LIST_2026-06-18.md`
(o rinominare a `_2026-06-25.md` se preferisci, stessa regola).

---

## FASE 0 — IN OSSERVAZIONE

Chiudere entrambe le voci:

| # | Cosa | Stato |
|---|---|---|
| 0.1 | Barometro v2 shadow validation | ✅ CHIUSO (S108). PASS qualità, INCONCLUSIVE prezzo |
| 0.2 | Sherpa 7-day observation | ✅ CHIUSO (S109). PASS per go-live dopo 15gg |

## FASE 1 — PRE-MAINNET OBBLIGATORI

Aggiornare stato di ogni riga:

| # | Cosa | Stato S109 |
|---|---|---|
| 1.1 | Verdetto barometro | ✅ CHIUSO (S108) |
| 1.2 | Verdetto Sherpa | ✅ CHIUSO (S109) — PASS, flicker cosmetico |
| 1.2b | Verifica breadth tier → Sentinel | ✅ CHIUSO (S109) — PARCHEGGIATO, dati insufficienti per risk-on |
| 1.3 | Sessione go-live experiment | **PROSSIMO** — unico task CEO+Board rimasto |
| 1.4 | DUST write-off | ✅ PARZIALE (S109) — evento + stub shippati, reconcile → mainnet |
| 1.5 | sell_pct + slippage_buffer per coin | ✅ INFRA (S109) — colonna + hot-reload, taratura → mainnet |
| 1.6 | Integration test config reader chain | ✅ CHIUSO (S109) — 8 test e2e |
| 1.7 | Mobile smoke test | ❌ ELIMINATO (S109) — Max lo fa già |
| 1.8 | Board approval call | **PENDING** — dopo 1.3 + annuncio Binance MiCA |

## FASE 2 — BLOG PIPELINE

Nessun cambiamento.

## FASE 3 — SUBITO DOPO GO-LIVE

Nessun cambiamento.

## FASE 4 — POST GO-LIVE

Nessun cambiamento.

## BUG APERTI

Tutti chiusi in S109 (report CC `tasklist-cleanup-pre-mainnet`):

| Bug | Stato |
|---|---|
| Fix exchange_order_id null su sell OP/USDT | ✅ CHIUSO — commit `e38fdf0` |
| DeprecationWarning datetime.utcnow() | ✅ CHIUSO — commit `2552110`, 409→0 |
| PortfolioManager istanziato mai usato | ✅ CHIUSO — commit `9042e03` |
| Aggiornare validation_and_control_system.md §2 | ✅ CHIUSO — commit `f818654` |

## CONGELATO

Aggiungere:
```
| Breadth T3 come segnale Sentinel | PARCHEGGIATO (S109). Analisi 6 mesi negativa in regime fear. Re-test dopo risk-on sostenuto. Script riutilizzabile |
```

Rimuovere la riga generica:
~~| Sentinel market breadth da TF scanner | Phase B/C |~~
(sostituita dalla riga specifica sopra)

## DIARIO

Aggiornare:
```
- S109 inserita in Supabase (COMPLETE). Docx prodotto.
```
