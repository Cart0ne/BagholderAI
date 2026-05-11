# Aggiornamento BUSINESS_STATE.md — post Session 71

**Sezioni cambiate:** §2, §3, §4, §5, §6, §7. Heavy cleanup incluso.

---

## 2. Marketing In-Flight

**Post X S69+S70 (S70):** ~~thread 2 post in coda~~ → verificare se pubblicato. Nessun nuovo post in coda da S71.

**Sito online (S70c):** confermato attivo. TestnetBanner globale. P&L hero unificato S71 (formula canonica: cash + holdings_mtm + skim − fees − budget). Due metriche: Total P&L (oscilla) + Net Realized Profit (fisso, post-fees).

*(resto invariato)*

---

## 3. Diary Status

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53–71 in accumulo. Stima grezza chiusura: sessioni 75–80 (arco narrativo: Clean Slate → Testnet → Fee Reckoning).

**Sessione corrente:** 71 BUILDING. S70 COMPLETE su Supabase.

*(resto invariato)*

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-11 (S71) | **Go-live slips, approccio sequenziale** | Roadmap a fasi: (1) pending cleanup, (2) fee brainstorming + fix, (3) Sentinel/Sherpa analisi, (4) TF. Nessuna data fissa |
| 2026-05-11 (S71) | **P&L hero = NET fees ovunque** | Formula canonica: cash + holdings_mtm + skim − fees − budget. grid.html aveva ragione, pagine pubbliche fixate |
| 2026-05-11 (S71) | **Backfill solo testnet, paper resta as-is** | I 458 trade paper non avevano fee reali. Correggere con formula fee = "fixare" dati mai veri. Strada 2 ridotta a ~42 trade testnet (~1-1.5h) |
| 2026-05-11 (S71) | **Fee: brainstorming prima di codice** | BONK InsufficientFunds dimostra che le fee toccano il core trading. Brief 71b scoped ma aspetta design session |
| 2026-05-11 (S71) | **Due numeri P&L etichettati** | Total P&L (include unrealized) + Net Realized Profit (storico, post-fees). Raccontano cose diverse, servono entrambi |
| *(mantenere ultime 10-12 voci da S70 indietro, eliminare le più vecchie di S67)* |

---

## 5. Domande Aperte per CC (idee tech non ancora in brief)

**[S71 Board — URGENTE]**

- **Brief 71b — BONK holdings fee-in-base-coin**: state.holdings += amount gross, Binance dà net. Gap 12,280 BONK (0.74%), 31 sell rifiutati. Schema fix in report CC S71 §5. ~1-2h. Primo task S72.
- **Strada 2 ridotta (solo testnet)**: realized_pnl gross→net + avg_buy_price fix + backfill ~42 trade testnet + verifica identità. ~1-1.5h. Dopo 71b.

**Chiuse/superate in S71:**
- ~~Open question 19 rename manual→grid~~ — CHIUSA S70
- ~~Brief 65c migrazione paper→testnet~~ — SUPERATA S67
- ~~Brief 60b respec avg-cost~~ — SUPERATA S66

*(rimuovere tutte le voci con strikethrough, tenere solo quelle attive)*

---

## 6. Vincoli / Deadline Non-Tecnici

**Go-live €100 — target variabile, non più 21-24 maggio.** Approccio sequenziale: fee cleanup → Sentinel/Sherpa → TF → Board approval. Stima realistica: fine maggio / inizio giugno 2026.

**Pre-live gates aggiornate S71:**
- ✅ sell_pct net-of-fees (S70)
- ✅ P&L hero unificato (S71)
- ✅ LAST SHOT lot_step_size (S71)
- ✅ Reason bugiardo fixato (S71)
- ⬜ Brief 71b BONK fee-in-base-coin (gating — bot non può vendere BONK)
- ⬜ Strada 2 ridotta (P&L netto testnet)
- ⬜ Reconciliation Step C cron (wrapper pronto, install pending)
- ⬜ Mobile smoke test reale
- ⬜ Sentinel/Sherpa analisi DRY_RUN
- ⬜ Board approval finale

---

## 7. Cosa NON Sta Succedendo e Perché

*(CLEANUP: rimuovere tutte le voci duplicate. Tenere solo una voce per tema, la più aggiornata)*

| Cosa | Perché no |
|---|---|
| **TF trading attivo** | In "osservazione" (dal dottore). Fase 4 della roadmap sequenziale |
| **Volume 3 in lavorazione** | Materiale S53–S71 si accumula. Chiusura quando l'arco narrativo ha un finale naturale |
| **Marketing outreach** | Pre-traction. Sito testnet online è step 1, mainnet è step 2 |
| **Sentinel/Sherpa LIVE** | In DRY_RUN dal S70. Analisi ~17 maggio, poi decisione Board |
| **Phase 2 grid_runner split** | Post go-live (1591 righe, brief 62b parcheggiato) |
| **Go-live €100 mainnet** | Fee cleanup in corso. BONK sell bloccati. Pre-live gates non superate |

---

*Prossimo aggiornamento: post S72 (fee cleanup session).*
