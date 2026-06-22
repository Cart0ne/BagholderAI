# BUSINESS_STATE update — S108 finale (CEO)

Istruzioni per CC: applicare queste modifiche a BUSINESS_STATE.md.
Include i 3 fix della prima parte di S108 (audit remediation) + nuovi aggiornamenti dalla sessione PC.

---

## Fix 1 — Nav descrive /news come se fosse live (§2 S106)

**Nella sezione S106 — site upgrade planning**, la riga nav dice:

```
Nav ristrutturata: Dashboard · Diary · Blog · News · Under the hood ▾ · Library
```

Sostituire con:

```
Nav ristrutturata: Dashboard · Diary · Blog · Under the hood ▾ · Library (5 voci + dropdown). /news pianificata come 6ª voce post-verdetto barometro (~23 giugno) — non ancora costruita né in nav
```

**Stessa sezione**, la riga:

```
/news pianificata (nav principale) — costruzione post-verdetto barometro ~23 giugno. Due scenari (validato/bocciato) documentati nel brief. Link anche dalla card NewsKeeper in homepage
```

Sostituire con:

```
/news pianificata (non ancora costruita) — costruzione post-verdetto barometro (~23 giugno). Due scenari (validato/bocciato) documentati nel brief S106a. Sarà aggiunta alla nav e linkata dalla card NewsKeeper quando costruita
```

---

## Fix 2 — Conteggio pagine sottostima (§1)

**In §1 Brand & Messaging**, la riga:

```
10 pagine live
```

Sostituire con:

```
11 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, blog, income, terms, privacy)
```

---

## Fix 3 — Header BUSINESS_STATE

Aggiornare l'header:

```
**Last updated:** 2026-06-22 — Session 108 (barometro verdict prep + haiku fix + TF architecture check + audit A2 remediation).
**Updated by:** CEO (update S108 via Max)
```

---

## Update 4 — §4 Decisioni strategiche recenti: aggiungere

```
- **2026-06-22 (S108) — Verdetto barometro v2: PASS qualità, INCONCLUSIVE come indicatore di trading**. N=2 flip in 13gg è insufficiente per validare il gate "flip vs BTC 24h forward return" (S100). Il barometro ha cross-validato con Tier B breadth (flash neutral 15-giu coincide con 19.6% bullish Tier B). NON blocca go-live grid. Sentinel wiring rimandato a dopo regime change sostenuto. Alternativa scartata: dichiarare PASS completo su dati insufficienti.
- **2026-06-22 (S108) — Dashboard label: "Net realized profit" → "Realized profit from sells (post-fees)"**. Disambigua margine realizzato dal Total P&L. Shipped da CC (commit `c2598df`).
```

---

## Update 5 — §5 Domande aperte per CC: aggiungere

```
| **[S108 NEW] CMC Fear & Greed come seconda fonte Sentinel** | Brief futuro | Nuovo file `cmc_fng.py` accanto a `alternative_fng.py`. Usa API key CMC già in `.env` (endpoint `v3/fear-and-greed/historical`). Logga valore in `sentinel_scores.raw_signals`, nessuna modifica a `regime_analyzer`. Osservare e confrontare con Alternative.me per settimane prima di decidere. Binance F&G non ha API pubblica; CMC (Binance-owned dal 2020) è il proxy più vicino |
```

---

## Update 6 — §6 Vincoli/Deadline: aggiornare riga barometro

La riga:

```
**NewsKeeper v2 Barometro T+14 verdetto** | ~23 giugno 2026 | Validare flip barometro vs ritorno prezzo BTC 24h...
```

Sostituire con:

```
**NewsKeeper v2 Barometro verdetto** | Nessuna data fissa (era ~23 giu) | T+14 raggiunto, esito: PASS qualità / INCONCLUSIVE prezzo (N=2 flip insufficiente). Esteso fino a regime change sostenuto (neutral/bullish >24h). Non blocca go-live grid. Dettagli in diary S108 |
```

---

## Update 7 — §10 PROJECT_STATE (istruzioni per CC)

Aggiungere riga sessioni shipped:

```
| 2026-06-22 | 1 | **S108a** brief haiku-fix-housekeeping (5/5 task + 2 extra) + **S108b** tf-recap-architecture (2/2 deliverable, zero codice) | SHIPPED `17334d4` (codice) + `b701771` (docs) + restart PID 18032 | Haiku prompts testnet-aware, footer mode dinamico, duplicato 15-giu cancellato, CLAUDE.md naming rule. TF recap + grid-mainnet assessment: nessun blocco tecnico go-live, ENABLE_TF=false è la via semplice. Dashboard label "Realized profit from sells" (commit `c2598df`). Runbook restart creato (`a7815c2`). |
```
