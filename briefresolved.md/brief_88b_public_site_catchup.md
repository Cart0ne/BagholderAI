# Brief 88b — Public Site Catch-Up: Roadmap + Dashboard + NewsKeeper

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Baseline:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commit `e1a6634`)
**Audit ref:** `audits/audit_report_20260527_area2_coherence.md` — findings 1.1, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4
**Estimated time:** 2-3 hours
**Priority:** FIRST — drift pubblico più visibile, eseguire per primo

---

## Context

Il sito pubblico è in drift di 1-2 settimane rispetto allo stato reale del progetto. I problemi principali:
- `/roadmap` ferma al 19 maggio (9 sessioni non riflesse, 1 brain nuovo, 1 Brain Analysis)
- `/dashboard` dichiara Sentinel e Sherpa "not yet deployed" quando sono LIVE da settimane
- NewsKeeper (5° brain, LIVE dal 24 maggio) non esiste nel roadmap
- Il roadmap cita "Target go-live: late June / early July 2026" — decisione revocata dal Board il 23 maggio

---

## Task 1 — roadmap.ts full refresh (S80→S87)

File: `web_astro/src/data/roadmap.ts`

**1a. Metadata:**
- `version`: da `"Versione 1.39 — Maggio 2026"` a `"Versione 1.48 — Maggio 2026"` (o numero appropriato basato sui cambiamenti)
- `lastUpdated`: da `"2026-05-19"` a `"2026-05-27"`

**1b. Phase 3 — rimuovere target date:**
- Nella description di Phase 3 (riga ~116), RIMUOVERE il testo `"Target go-live: late June / early July 2026."` e sostituire con: `"Go-live depends on observed market conditions (bear + bull + lateral), not a calendar date (Board decision S82, 2026-05-23)."`
- Stesso trattamento per Phase 6 timeframe (riga ~183) se contiene la stessa data target.

**1c. Phase 3 — task Sentinel Sprint 2 observation (riga ~125):**
Lo status è `active` sulla PRIMA finestra di osservazione (chiusa S80a). Spezzare in 3 task:
```typescript
{ text: "Sentinel Sprint 2 observation window 1 (5-7 days)", status: "done", who: "AI", comment: "Completed 2026-05-22. 32 slow records, zero gaps > 6h. Natural window closed, Brain Analysis triggered." },
{ text: "Brain Analysis #1 — Sentinel + Sherpa evaluation", status: "done", who: "AI", comment: "S80a, 2026-05-22. Sentinel: APPROVED (Sprint 2 targets met). Sherpa: NO-GO step 4 (amplitude too conservative for altcoins). → triggered Sherpa Sprint 2 rework." },
{ text: "Sherpa Sprint 2 rework (per-coin volatility scaling + slow gate + amplitude cap)", status: "done", who: "AI", comment: "S81, brief 81a. BTC anchor=1.0, SOL=1.60, BONK=2.09. Commits 3ba1132 + 51204cf." },
{ text: "Sherpa Sprint 2 observation window (7-10 days)", status: "active", who: "AI", comment: "Started 2026-05-22. Second Brain Analysis due ~May 29 – June 1." },
```

**1d. Phase 3 — Sherpa Sprint 2 task (finding 3.2):**
Aggiungere 1-2 task dedicati a Sherpa Sprint 2 se non già coperti da 1c sopra. La voce attuale "Sherpa Sprint 1: rule-based proposals on Grid" (riga ~119) resta `done`. Aggiungere dopo:
```typescript
{ text: "Sherpa Sprint 2: per-coin volatility scaling (BTC anchor, SOL 1.6×, BONK 2.1×)", status: "done", who: "AI", comment: "Brief 81a, S81. Amplitude cap 30%, slow-loop gate. Commits 3ba1132 + 51204cf." },
```

**1e. Phase 3 — description update post-Brain-Analysis (finding 3.3):**
Aggiornare la description per riflettere la sequenza attuale:
- Sentinel Sprint 2 completato e APPROVED
- Sherpa Sprint 2 (per-coin) completato, in osservazione
- Prossimo step: seconda Brain Analysis → step 4 Sherpa LIVE testnet → osservazione → Board approval → mainnet

**1f. Phase 3 — NewsKeeper (finding 3.1):**
RIMUOVERE la riga esistente:
```typescript
{ text: "News feed integration (CryptoPanic, RSS)", status: "todo", who: "AI", comment: "Sentinel Sprint 3, brief in planning." }
```
e SOSTITUIRE con una sezione dedicata (nuova Phase o sub-section di Phase 3):
```typescript
// NewsKeeper — Brain #5 (standalone, not part of Sentinel)
{ text: "NewsKeeper Sprint 1: RSS feed collection + regex classifier", status: "done", who: "AI", comment: "S83, 2026-05-24. 3 feeds (CoinDesk, CoinTelegraph, Decrypt), 15-min loop, standalone process. ~60% false positive rate on regex classifier." },
{ text: "NewsKeeper Sprint 2: Haiku-based classification (replace regex)", status: "planned", who: "AI", comment: "After 7-day observation window. Estimated < €1/month Haiku cost." },
{ text: "Strategy Orchestrator: unified Sentinel + NewsKeeper recommendations via Haiku", status: "planned", who: "AI", comment: "~4 CC sessions estimated. Haiku-unified recommendations across macro signals." },
```

CC decide se fare una Phase separata (es. "Phase 14 — NewsKeeper") o una sub-section di Phase 3. Il vincolo è: NewsKeeper NON deve apparire come "Sentinel Sprint 3" — è un brain separato con il suo package, la sua tabella, il suo processo.

**1g. Phase 9 §3 — audit cadence (finding 4.4):**
Aggiornare la riga "As of 2026-05-19: Area 1 last 2026-05-08…" con:
```
As of 2026-05-27: Area 1 last 2026-05-08 (19d, approaching 30d backstop), Area 2 completed 2026-05-27 (CON RISERVE — public site drift + process gaps, 0 CRITICAL), Area 3 last 2026-05-15 (12d, ok). Cadenza riformulata da temporale a event-based — vedi AUDIT_PROTOCOL.md §2.
```

**1h. Sessioni S80→S87 — aggiungere task corrispondenti:**
Per ogni sessione non ancora riflessa, aggiungere le voci appropriate nelle Phase corrette. CC fa riferimento a PROJECT_STATE §10 per i dettagli. Sessioni principali:
- S80 (homepage funnel + UTM + TF live narrative)
- S80a (Brain Analysis #1)
- S81 (Sherpa Sprint 2 + Haiku 81b)
- S82 (Homepage redesign + NewsKeeper Architecture brief)
- S83 (NewsKeeper Brain #5 scaffold)
- S84 (SEO audit fix)
- S85 (RSS feed + BUSINESS_STATE governance)
- S86 (status badge + regime overlay admin)
- S87 (V3 launch + Umami coverage)

Non serve un task per ogni sessione — raggruppare dove sensato (es. S84+S85 = "SEO + housekeeping", S86+S87 = "launch infrastructure").

---

## Task 2 — Dashboard: Sentinel + Sherpa status fix (finding 1.1)

File: `web_astro/src/data/dashboard-mock.ts`

**mockTools array:** `mockTools[2]` (Sentinel) e `mockTools[3]` (Sherpa) hanno `status: "soon"`. Cambiare:
- Sentinel: `status: "active"` (LIVE da S70/S77)
- Sherpa: `status: "testing"` oppure `"active"` con un qualifier `"DRY_RUN"` nel description — CC decide la label migliore guardando come `dashboard.astro` renderizza i diversi status

File: `web_astro/src/pages/dashboard.astro`

La sezione (riga ~376-395) che filtra `mockTools.filter((t) => t.status === "soon")` e renderizza "⏳ not yet deployed" deve essere adattata. Se Sentinel e Sherpa non sono più `"soon"`, quella sezione non li cattura più — verificare che abbiano una sezione di rendering appropriata (come le altre tool attive).

**Trasparenza livello:** mostrare lo stato reale:
- Sentinel: "LIVE — scoring every 60s (fast) + 4h (slow)"
- Sherpa: "DRY_RUN — observing, proposals logged but not applied"

CC decide il layout e il livello di dettaglio, ma i due brain NON devono più apparire come "not yet deployed".

---

## Decisioni delegate a CC

- Struttura della nuova Phase o sub-section per NewsKeeper in roadmap.ts
- Layout della sezione Sentinel/Sherpa su dashboard (purché non dica "not yet deployed")
- Raggruppamento delle sessioni S80-S87 in task roadmap (purché tutte le sessioni siano rappresentate)
- Numero di versione roadmap.ts (incrementare appropriatamente)
- Se creare status separati per "active" vs "testing/dry_run" in dashboard-mock.ts

## Decisioni che CC DEVE chiedere

- Se durante il refresh roadmap emerge un conflitto con le voci esistenti che non è coperto da questo brief
- Se il rendering dashboard di Sentinel/Sherpa richiede un nuovo componente Astro (vs modifica dell'esistente) — chiedere perché ha implicazioni di scope
- Qualsiasi modifica a file fuori da `web_astro/src/data/` e `web_astro/src/pages/dashboard.astro` che non sia già menzionata in questo brief

## Output atteso

1. `web_astro/src/data/roadmap.ts` aggiornato (catch-up S80→S87 + NewsKeeper + no target date + Phase 3 refresh)
2. `web_astro/src/data/dashboard-mock.ts` aggiornato (Sentinel/Sherpa status)
3. `web_astro/src/pages/dashboard.astro` adattato (rendering Sentinel/Sherpa non più "soon")
4. Build Astro verde (verificare con `npm run build` nella dir `web_astro/`)
5. PROJECT_STATE.md rigenerato
6. Commit, push origin/main → Vercel auto-deploy

## Vincoli

- NON toccare codice bot, trading logic, tabelle Supabase
- NON toccare homepage (`index.astro`) — le card homepage (WatchtowerCard, SherpaLockedCard) sono già corrette
- NON toccare `admin.html`, `grid.html`, `tf.html`
- NON modificare BUSINESS_STATE.md
- I numeri Grid/TF in `botData` homepage sono un debito SEPARATO (vedi Brief 88d) — non fixare qui
- Se Brief 88a viene eseguito nella stessa sessione, coordinare l'update di Phase 9 §3 per evitare conflitti merge

## Roadmap impact

Questo brief È il roadmap update. L'intero Task 1 è il catch-up di roadmap.ts.
