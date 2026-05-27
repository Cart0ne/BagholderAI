# Brief 88a — Audit Meta-Decisions: Protocol + Area 2 Rule + RSS Pivot Doc

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Baseline:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commit `e1a6634`)
**Audit ref:** `audits/audit_report_20260527_area2_coherence.md` — findings 6.1, 6.2, 2.2
**Estimated time:** ~45 min (all text, no code changes)
**Priority:** Execute after Brief 88b (public site catch-up)

---

## Context

L'audit Area 2 (primo mai eseguito) ha trovato 3 problemi meta-processo:

1. `AUDIT_PROTOCOL.md` è un vecchio audit request del 7 maggio, non un protocollo. Ma CLAUDE.md e WORKFLOW.md lo citano come fonte autoritativa.
2. La regola "audit Area 2 ogni 90gg" non è mai stata applicata in pratica (6 settimane di inerzia). Il Board ha approvato una riformulazione event-based.
3. Il pivot CryptoPanic → RSS (decisione S83) non è documentato come brief — il brief originale NewsKeeper descrive un'architettura che il codice non implementa più.

---

## Task 1 — Scrivere AUDIT_PROTOCOL.md vero

Sostituire il contenuto attuale (1382 bytes, audit request del 7 maggio) con un protocollo vero che consolida ciò che oggi vive sparso in:
- WORKFLOW.md §G (procedura audit)
- CLAUDE.md §[1] (chi scrive §9, regola Auditor)
- Prassi dei 3 audit già eseguiti (Area 1 del 7/5, Area 3 del 15/5, Area 2 di oggi)

**Struttura del nuovo AUDIT_PROTOCOL.md:**

```
# Audit Protocol — BagHolderAI

## 1. Aree di audit
- Area 1: Integrità tecnica (bot, agenti, DB)
- Area 2: Coerenza progetto (narrazione pubblica vs codice vs state files)
- Area 3: Strategia e marketing

## 2. Trigger (event-based, approvato Board 2026-05-27)
Audit Area 2 è obbligatorio prima di:
  (a) ogni go-live mainnet
  (b) ogni lancio nuovo Volume su Payhip
  (c) ogni introduzione nuovo brain o macro-feature
  (d) se audit Area 1 o Area 3 trova ≥1 finding HIGH che tocca documentazione/state files
Backstop temporale: 120 giorni se nessun trigger sopra è scattato.

Area 1: dopo ogni feature significativa o mensile (backstop 30gg).
Area 3: trimestrale + pre-lancio prodotto (backstop 90gg).

## 3. Chi può essere Auditor
Sessione CC FRESH (nessun task di sviluppo prima nella stessa chat).
L'Auditor NON shipa codice, NON tocca brief in corso, NON esegue il lavoro che sta auditando.

## 4. Procedura
1. CEO crea `audits/audit_request_YYYYMMDD_topic.md`
2. Max apre sessione CC FRESH e passa il brief
3. CC crea `audits/audit_in_flight_YYYYMMDD_topic.md` (NEW — stage intermedio con ETA)
4. CC esegue e produce `audits/audit_report_YYYYMMDD_topic.md`
5. Auditor aggiorna PROJECT_STATE.md §9 (unico autorizzato)
6. CC cancella `audit_in_flight_*.md` (stage chiuso)

## 5. Output dell'Auditor
- Findings con severity (CRITICAL > HIGH > MED > LOW) e file:linea
- Verdetto: APPROVED / CON RISERVE / REJECTED
- File `audits/audit_report_YYYYMMDD_topic.md`
- Riga §9 in PROJECT_STATE.md

## 6. Alert in chiusura sessione CC
Quando un trigger è scattato, CC propone:
"⚠️ Audit Area X dovuto (motivo: trigger Y). Brief draft disponibile.
Vuoi che lo generi ora? [yes/no/later]"
Se Max dice yes → CC genera audit_request_*.md nella stessa sessione.

## 7. Storico audit
- 2026-05-07: Area 1 — V1 Calibration (S63). APPROVED.
- 2026-05-15: Area 3 — Strategy review (S78). [verdetto].
- 2026-05-27: Area 2 — Coerenza progetto (S88). CON RISERVE.

Last updated: 2026-05-27 — riscrittura completa post audit Area 2.
```

**Note per CC:** il contenuto sopra è una traccia. Adattalo se ci sono dettagli in WORKFLOW.md §G che ho omesso, ma la struttura (7 sezioni) è vincolante.

---

## Task 2 — Aggiornare CLAUDE.md e WORKFLOW.md

**CLAUDE.md §[1]** — la riga che cita `AUDIT_PROTOCOL.md` è corretta nel riferimento ma va aggiornata per riflettere il nuovo contenuto (non è più "vedi AUDIT_PROTOCOL.md per dettagli" come se fosse un audit request — è "vedi AUDIT_PROTOCOL.md per il protocollo completo").

**CLAUDE.md §[1]** — la regola sulla cadenza Area 2. Sostituire:
```
Area 2 (coerenza progetto): cadenza 90 giorni o fine-volume Diary
```
con:
```
Area 2 (coerenza progetto): trigger event-based — vedi AUDIT_PROTOCOL.md §2 per la lista completa. Backstop 120gg.
```

**WORKFLOW.md §G** — aggiornare il riferimento alla procedura (aggiungere il passo `audit_in_flight_*.md`) e rimuovere eventuali riferimenti alla cadenza "90 giorni".

---

## Task 3 — Archiviare mini-brief RSS pivot

Creare file `briefresolved.md/brief_s83b_newskeeper_rss_pivot.md` con questo contenuto:

```markdown
# Brief S83b — NewsKeeper Sprint 1: RSS Pivot

**Author:** CEO (Claude)
**Date:** 2026-05-27 (documentato retroattivamente)
**Decision date:** 2026-05-23 (S83, durante implementazione brief S83 NewsKeeper Architecture)
**Status:** SHIPPED (S83)

## Decision

CryptoPanic free tier discontinued (2026-04-01). Paid tier ($49/month) fuori budget.
Dopo ricerca alternative, Board+CEO decidono: RSS feeds zero-auth come fonte primaria per NewsKeeper Sprint 1.

## What changed vs original brief (brief_s83_newskeeper_architecture.md)

- `bot/newskeeper/readers/cryptopanic.py` → NON implementato (API morta)
- `bot/newskeeper/readers/etf_flows.py` → deferito a Sprint 2+
- `bot/newskeeper/readers/macro_calendar.py` → deferito a Sprint 2+
- `bot/newskeeper/readers/rss_feeds.py` → UNICA fonte Sprint 1
- NewsKeeper è standalone (PID 78098), NON orchestrator-managed
- 3 RSS feeds: CoinDesk, CoinTelegraph, Decrypt
- Classificatore regex (non Haiku) — ~60% false positives, sufficiente per Sprint 1 observation

## References

- BUSINESS_STATE §4 voce 2026-05-24
- PROJECT_STATE §10 voce S83
- Audit Area 2 finding 2.2

## Roadmap impact

Nessuno (Sprint 1 era già "todo" nel roadmap; il cambio è nella fonte, non nello scope pubblico).
```

---

## Task 4 — Aggiungere header al brief NewsKeeper resolved

In `briefresolved.md/brief_s83_newskeeper_architecture.md`, aggiungere in cima al file (prima della prima riga):

```markdown
> ⚠️ **PARTIAL SHIP:** Session 1 of 4 SHIPPED (S83 — RSS feeds only, standalone).
> Sessions 2-4 pending — see PROJECT_STATE §10 S83 + §6.
> Sprint 1 scope changed vs this brief: see `brief_s83b_newskeeper_rss_pivot.md`.

```

---

## Decisioni delegate a CC

- Adattare la struttura di AUDIT_PROTOCOL.md se mancano dettagli da WORKFLOW.md §G
- Formattazione e wording dei file

## Decisioni che CC DEVE chiedere

- Se la sezione §7 "Storico audit" di AUDIT_PROTOCOL.md ha informazioni incomplete sui verdetti passati (es. Area 3 del 15/5 — CC verifica nel repo se esiste il report e riporta il verdetto)
- Qualsiasi modifica a CLAUDE.md oltre le 2 righe specificate sopra

## Output atteso

1. `AUDIT_PROTOCOL.md` riscritto (root del repo)
2. `CLAUDE.md` aggiornato (2 righe)
3. `WORKFLOW.md` aggiornato (§G procedura + cadenza)
4. `briefresolved.md/brief_s83b_newskeeper_rss_pivot.md` nuovo
5. `briefresolved.md/brief_s83_newskeeper_architecture.md` con header aggiunto
6. PROJECT_STATE.md rigenerato (§9 audit cadence updated, §3 task completato)
7. Commit unico, push origin/main

## Vincoli

- NON toccare codice bot, trading logic, tabelle Supabase
- NON modificare BUSINESS_STATE.md (lo fa solo il CEO su istruzione esplicita)
- Il contenuto di AUDIT_PROTOCOL.md è la traccia sopra — CC può adattare wording ma NON cambiare la struttura a 7 sezioni né i trigger approvati dal Board

## Roadmap impact

roadmap.ts Phase 9 §3 (audit cadence): aggiornare la riga "As of 2026-05-19" con stato attuale post-audit + nuova regola event-based. Vedi anche Brief 88b task dedicato al refresh completo di roadmap.ts — se eseguiti nella stessa sessione, coordinare per evitare conflitti.
