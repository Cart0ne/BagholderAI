# Brief 88c — State Files Cleanup: Compaction + Drift Fixes

**Author:** CEO (Claude)
**Date:** 2026-05-27
**Baseline:** PROJECT_STATE.md aggiornato 2026-05-27 (S87 closure, commit `e1a6634`)
**Audit ref:** `audits/audit_report_20260527_area2_coherence.md` — findings 5.1, 5.2, 5.3, 5.5, 5.7, 1.6
**Estimated time:** ~1 hour
**Priority:** Execute after Brief 88b

---

## Context

PROJECT_STATE.md è a 54KB, sopra il cap di 40KB da CLAUDE.md §[2]. Il PENDING di compaction è in §3 da 2 sessioni senza data. Inoltre, 5 sezioni del file contengono informazioni stale o in contraddizione con BUSINESS_STATE.

---

## Task 1 — Compaction sotto 40KB (finding 5.1)

**Obiettivo:** portare PROJECT_STATE.md sotto 40KB. Procedura standard:
1. Estrarre le sezioni compattabili (header sessioni vecchie, dettagli esecuzione pre-S84)
2. Appendere il contenuto estratto a `audits/PROJECT_STATE_archive.md` (con sezione datata)
3. In PROJECT_STATE, lasciare solo riferimenti sintetici (es. "S82-S83: vedi archive")
4. Verificare che il file risultante sia < 40KB

**Cosa compattare (suggerimenti):**
- §10 voci sessioni S70→S81 — sono dettagliatissime (molte > 500 parole). Comprimere a 1-2 righe ciascuna con riferimento all'archive
- §3 storico in-flight pre-S86 — può diventare un riferimento
- Header sessioni precedenti (ultimo aggiornamento precedente², precedente³) — spostare in archive, tenere solo l'ultimo

**Cosa NON compattare:**
- §1 (overview — serve sempre)
- §2 (architettura — serve a CC per ogni sessione)
- §6 (domande aperte — servono attive)
- §9 (audit — storico leggero, serve)
- Ultime 3-4 sessioni in §10 (S84→S87 — recenti, servono)

CC ha autonomia sulla strategia di compaction. L'unico vincolo è: sotto 40KB, nessuna informazione persa (tutto va in archive).

---

## Task 2 — §1 + §7: rimuovere go-live date (findings 5.2 + 4.2)

**§1** (riga ~21): la riga `"Target go-live €100: fine giugno / inizio luglio (decisione S76 CEO 2026-05-14)"` va sostituita con:
```
Go-live €100: nessuna data fissa. Dipende da condizioni di mercato osservate (bear + bull + lateral), non da calendario (decisione S82 Board 2026-05-23, sovrascrive S76).
```

**§7** (riga ~162): stessa modifica. Cercare ogni riferimento a "fine giugno / inizio luglio" o "target late June / early July" e sostituire con la formulazione S82.

---

## Task 3 — §2: fix TF DISABLED → LIVE (finding 5.3)

**§2 mappa moduli** (riga ~58): cambiare:
```
trend_follower/          Brain #4 — TF (DISABLED via ENABLE_TF=false)
```
in:
```
trend_follower/          Brain #4 — TF (LIVE Tier 1-2 only, ENABLE_TF=true, tf_tier3_weight=0, da S79b 2026-05-18)
```

---

## Task 4 — §5: rimuovere bug fossile OP/USDT (finding 5.5)

**§5 bug noti**: la voce `🔴 [S67] exchange_order_id=null su sell OP` si riferisce a una coin non più nel sistema (OP rimossa). Spostare in archive con nota "coin rimossa dal sistema, bug non più riproducibile". Rimuovere da §5.

---

## Task 5 — §1 + §7: disambiguare "Mac Mini su commit X" (finding 5.7)

Ovunque §1 e §7 dicano `"Mac Mini orchestrator su 51204cf"`, adottare il formato esplicito:
```
Mac Mini orchestrator runtime commit `51204cf` (restart 2026-05-22 20:31 CET post 81a+81b);
HEAD git locale `e1a6634` (S87 closure, nessun restart richiesto S82→S87 = solo UI/docs).
```

**Nota:** il commit HEAD potrebbe essere diverso al momento dell'esecuzione se altri brief sono stati eseguiti prima. CC usa il HEAD attuale, non quello scritto qui.

---

## Task 6 — §2: documentare pagine admin (finding 1.6)

Aggiungere in §2 (mappa moduli), sotto `web_astro/`:
```
web_astro/public/admin.html   Admin dashboard (auth-gate SHA-256, non indicizzato). Sentinel+Sherpa charts, regime overlay.
web_astro/public/grid.html    Grid admin panel (auth-gate SHA-256). Config + P&L dettaglio per coin.
web_astro/public/tf.html      TF admin panel (auth-gate SHA-256). Config + scans + portfolio.
```

---

## Decisioni delegate a CC

- Strategia di compaction (quali sezioni comprimere, quanto sintetizzare)
- Ordine delle operazioni
- Wording esatto delle sostituzioni (il senso è vincolante, le parole esatte no)

## Decisioni che CC DEVE chiedere

- Se la compaction porta il file a 39KB ma richiede di tagliare informazioni delle ultime 3 sessioni — chiedere prima
- Se trova altri drift non coperti da questo brief durante la compaction — flaggare, non fixare autonomamente

## Output atteso

1. `PROJECT_STATE.md` compattato (< 40KB) con tutti i fix applicati
2. `audits/PROJECT_STATE_archive.md` aggiornato (contenuto estratto dalla compaction)
3. §3 in-flight: rimuovere il PENDING compaction (è stato fatto)
4. Commit, push origin/main

## Vincoli

- NON toccare codice bot, trading logic, tabelle Supabase
- NON toccare BUSINESS_STATE.md
- NON toccare web_astro/ (è coperto da Brief 88b e 88d)
- Tutto il contenuto rimosso da PROJECT_STATE DEVE finire in archive — niente si cancella

## Roadmap impact

Nessuno. Housekeeping interno, zero impatto su roadmap.ts.
