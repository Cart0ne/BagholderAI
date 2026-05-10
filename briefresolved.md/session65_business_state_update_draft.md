# Aggiornamento BUSINESS_STATE.md — fine sessione 65

**Last updated:** 2026-05-08 — Session 65 chiusura  
**Updated by:** CEO  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-07 (S63) — CC aggiornerà PROJECT_STATE nella prossima sessione

---

## Sezioni modificate:

### §3. Diary Status (AGGIORNARE)

**Sessione corrente:** 65. Session 64 COMPLETE. Session 65 BUILDING.

**Check di congruenza diary↔DB:** nessun check automatico attivo. Reconciliation gate (nightly script) proposto come task in Validation System — da implementare.

### §4. Decisioni Strategiche Recenti (AGGIUNGERE in cima)

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-08 (S65) | Brief 60b rispecificato: avg-cost pulito (NON strict-FIFO) | Max ha chiesto "Binance mica calcola per lotti?" — corretto. Binance usa avg-cost. Il bot già usa avg-cost, solo implementato male (+28% bias su Grid). Fix = stessa metodo fatto bene, allineato a Binance |
| 2026-05-08 (S65) | Opzione 3 approvata: dashboard mostrano solo Total P&L (Net Worth − Budget) | Total P&L è immune al bias avg-cost, matematicamente verificato, identico a Binance. Realized P&L spostato in /admin Reconciliation come metrica audit |
| 2026-05-08 (S65) | Go-live €100 timeline 16-20 maggio | Prerequisiti: Opzione A ✅ + Opzione 3 + schema drift skim fix + brief 60b (avg-cost fix) + Phase 2 Grid + Board approval. 7gg clean observation cancellati |
| 2026-05-08 (S65) | Mascotte Sentinel (blu) e Sherpa (rosso) approvate | SVG prodotti con Claude Design. Brief 65b per integrazione CC |
| 2026-05-08 (S65) | Schema drift reserve_ledger identificato | Grid bot ha scritto skim con 3 label diverse (grid, manual, null). Fix minimo: normalizzare by trade_id. Rename manual→grid post-go-live |
| 2026-05-08 (S65) | Strict-FIFO replay rimosso da dashboard pubbliche | Era la causa di tutti i gap P&L degli ultimi 5 sessioni. Mantenuto solo in /admin come audit tool |

### §5. Domande Aperte per CC (AGGIORNARE)

**Rimuovere #2** (allineamento sell-decision a FIFO globale) — superata dal cambio a avg-cost.

**Aggiornare #15** (Brief 60e paginazione): shippata da CC in S65 (commit da CC).

**Aggiungere:**
- **[S65] Brief 60b respec: avg-cost accounting nel bot** — il bot scrive realized_pnl con avg_buy_price che non chiude l'identità contabile (bias +28% su Grid). Fix: ricalcolare il cost basis in modo coerente così che Realized + Unrealized = Total P&L al centesimo. NON strict-FIFO. Gating per go-live €100.
- **[S65] Rename managed_by: manual→grid** — da fare post-go-live + post-Phase 2 stabile. Tocca 4 tabelle + tutto il codice dashboard. ~2h. Non urgente ma necessario per coerenza a lungo termine.
- **[S65] Reconciliation gate (nightly script)** — proposto come task Validation System. Script che verifica ogni notte che l'identità Realized + Unrealized = Total P&L chiuda al centesimo. Alert se gap > $0.01.

### §6. Vincoli / Deadline Non-Tecnici (AGGIORNARE)

**Go-live €100 — timeline: 16-20 maggio 2026.** Percorso critico aggiornato:

- Opzione A (dashboard → DB): ✅ completata (commit f143634)
- Opzione 3 (Total P&L unica metrica): ✅ o in corso (da confermare con CC)
- Schema drift skim fix: ✅ o in corso
- Brief 60b avg-cost fix: ⬜ da scrivere e shippare
- Phase 2 Grid (fix 60c + dust): ⬜ in attesa piano CC
- Board approval: ⬜

**DECISIONE PENDENTE Sentinel ricalibrazione:** ancora aperta (opzione a vs b). Deadline ~10-11 maggio.

### §7. Cosa NON Sta Succedendo e Perché (AGGIORNARE)

| Cosa | Perché no |
|---|---|
| **Admin dashboard Sentinel+Sherpa non implementata** | RIMUOVERE — è live da S63 |

**Aggiungere:**
| **Strict-FIFO come metodo contabile** | Abbandonato in S65. Binance usa avg-cost; il nostro bot pure. Il fix è fare avg-cost correttamente, non cambiare metodo |
