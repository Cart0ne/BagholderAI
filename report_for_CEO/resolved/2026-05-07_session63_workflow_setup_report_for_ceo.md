# Session 63 (init) — V&C Workflow Setup
**Date:** 2026-05-07  
**Type:** Process engineering (no trading code touched)  
**Status:** COMPLETE  
**Commits:** e20704c, 57aff52, [PROJECT_STATE], 79a7ff2, 62cd554

---

## Sommario esecutivo

Sessione anomala: zero righe di logica di trading toccate, ma 5 commit 
e un'intera impalcatura organizzativa introdotta. Risolve a livello 
strutturale il problema cronico "il CEO opera con contesto stale" 
che accompagnava il progetto da ~1.5 mesi e impattava direttamente 
la qualità dei brief e delle decisioni strategiche.

Il deliverable è un sistema a 4 file di stato + 2 protocolli + 1 
cartella audit gitignored, completamente operativo dal commit 62cd554.

---

## Contesto e perché ora

- Pre-deploy live €100 in roadmap (qualche mese, non settimane)
- Max non è sviluppatore ma orchestra 4 cervelli (Grid, TF, Sentinel, 
  Sherpa) + 2 AI esecutori (CEO Claude.ai, CC) su 2 macchine (MBP + 
  Mac Mini)
- Pre-mainnet richiede uno standard di rigore che il flusso pre-V&C 
  non garantiva: brief con riferimenti obsoleti, decisioni perse 
  tra sessioni, drift silenti
- Soluzione richiesta: protocolli, non eroismo

---

## Cosa è stato fatto (cronologico)

### 1. Pulizia Project Knowledge (claude.ai)
Da 52% a stima ~32-35% di occupazione. Tagliati: `briefresolved.md/` 
(15%), `web_astro/public + package-lock.json + .vscode` (15%). 
Aggiunti: `db/`, `docs/`, `report_for_CEO/`, file root utili 
(`README.md`, `main.py`, `commentary.py`, `vercel.json`).

### 2. Project Instructions CEO Claude.ai aggiornate
7 sezioni in totale:
- [0] Audit clause (segnalare drift istruzioni)
- [1] Lettura PROJECT_STATE + BUSINESS_STATE all'inizio chat
- [2] Manutenzione BUSINESS_STATE.md a fine sessione
- [3] Formato standard brief per CC (vincoli, decisioni delegate, 
  output atteso, piano italiano per task >1h)
- [4-5] Supabase diary + .docx Diary regole esistenti, riformattate 
  con specifica esplicita "lingua contenuto = inglese, lingua di 
  lavoro = italiano"
- [6] Roadmap path **corretto**: era stale (`web/roadmap.html`, 
  gitignored), ora `web_astro/src/pages/roadmap.astro`

### 3. CLAUDE.md esteso (commit e20704c)
7 sezioni speculari a Project Instructions del CEO. Aggiunte: audit 
clause [0], lettura/scrittura state files [1], formato fisso 
PROJECT_STATE [2], protocollo task non banali con piano italiano [3], 
decision log [4]. Mantenute regole esistenti: git pull multi-macchina 
[5], project context [6].

### 4. AUDIT_PROTOCOL.md + cartella `audits/` gitignored (commit 57aff52)
Definite 3 aree: Tecnica bot/agenti (Area 1, mensile), Coerenza 
progetto (Area 2, fine-volume), Strategy & marketing (Area 3, 
trimestrale). Format request/report standardizzato. Cartella 
`audits/*` gitignored con `!audits/.gitkeep` per preservare la 
struttura. Audit privati, sintesi 1-2 righe pubblica in 
PROJECT_STATE.md sezione 9.

### 5. PROJECT_STATE.md generato (commit dedicato)
9 sezioni canoniche. Dimensione ~7-8 KB, ben sotto il limite 40 KB. 
Popolato da git log, ultimi 5 report_for_CEO, ultimi 10 brief 
risolti, TODO inline. Il file ha **sollevato in superficie** la 
domanda 6.1 sull'equity P&L vs FIFO realized — sepolta nei report 
del 5 maggio, ora visibile nello stato corrente.

### 6. BUSINESS_STATE.md generato (commit 79a7ff2)
7 sezioni canoniche. Decisione strategica resa esplicita sulla 
domanda 6.1: il gap numerico ($4.53) **non è gating**; quello che 
è gating è la proposta 2 di CC (sell-decision alignment a FIFO 
globale). Roadmap go-live dettagliata in 8 step con checklist 
pre-live gates.

### 7. WORKFLOW.md handbook operativo Max (commit 62cd554)
166 righe. Routine quotidiane (inizio/fine sessione CC, inizio/fine 
chat CEO, audit), errori da evitare, checklist veloce, recovery 
in caso di failure. Pensato come "checklist da Max stanco alle 23".

---

## Note meta-circolari (il sistema funziona già)

Tre prove sul campo durante la sessione stessa, prima ancora che 
fosse completato:

1. **Drift roadmap intercettato.** Le Project Instructions del CEO 
   referenziavano `web/roadmap.html` (gitignored dal commit 591d6f3). 
   Tutti i brief roadmap del CEO ai CC venivano ignorati silentemente 
   perché il file legacy non corrisponde più al sito live. Caso da 
   manuale del problema "istruzione obsoleta che fa fallire i task 
   in modo invisibile". Risolto nelle nuove Project Instructions [6].

2. **CC ha applicato l'audit clause spontaneamente.** Nel commit di 
   CLAUDE.md, ha verificato che `PROJECT_STATE.md`/`BUSINESS_STATE.md` 
   non esistessero ancora (atteso, segnalato a Max) e che il path 
   roadmap nel nuovo CLAUDE.md fosse coerente. Nessuna di queste 
   verifiche era nel brief — sezione [0] di CLAUDE.md ha funzionato 
   il giorno stesso della sua introduzione.

3. **CC ha corretto un errore tecnico dell'auditor.** Nel pattern 
   `.gitignore` proposto per `audits/`, il pattern `audits/` (senza 
   wildcard) avrebbe escluso anche `.gitkeep`. CC ha corretto in 
   `audits/*` + `!audits/.gitkeep`, ha verificato con `git check-ignore`, 
   l'ha documentato nella consegna. L'auditor (oggi un Claude esterno) 
   non è infallibile; il contro-controllo CC ha funzionato. 
   Esattamente come da design.

---

## Cosa NON è stato fatto e perché

- **Nessuna modifica al codice di trading.** Voluto: la sessione 
  era process-engineering. La Phase 2 di brief 62b resta in attesa.
- **PROJECT_STATE.md sezione 6.1 ancora flaggata come "domanda aperta"** 
  anche se BUSINESS_STATE.md sezione 6 contiene già la decisione del 
  CEO. Il flag in PROJECT_STATE sarà aggiornato naturalmente alla 
  prossima rigenerazione (fine prossima sessione CC).
- **Proposta 1 di CC (Equity P&L nella home, 1-2h) non implementata.** 
  Decisione del CEO presa, ma è downstream — apri brief separato 
  quando il timing è giusto.
- **Skills (in senso Claude Code) non adottate.** Decisione esplicita: 
  premature optimization. Da rivalutare tra ~2 mesi se emergono 
  pattern davvero ricorrenti (es. "rigenera state files" o "build 
  review packet").
- **Audit V1 di calibrazione** (Sentinel↔Sherpa↔Grid post-Phase 1) 
  preparato come idea ma non avviato. Trigger: post-Phase 2.

---

## Punti aperti da tracciare

| Item | Owner | Quando |
|------|-------|--------|
| Aggiornare PROJECT_STATE.md sezione 6.1 (decisione presa in BUSINESS_STATE) | CC | Prossima sessione CC |
| Implementare Proposta 1 (Equity P&L nella home) | CC | Brief dedicato quando CEO decide il timing |
| Implementare Proposta 2 (sell-decision alignment FIFO) | CC | Phase 2 o immediatamente dopo (gating mainnet) |
| Primo audit V1 calibration (Sentinel↔Sherpa↔Grid) | Auditor | Post-Phase 2 |
| Test end-to-end del nuovo workflow | Max | 5-10 min dopo commit 62cd554: aprire nuova chat CEO e chiedere *"che data riporta BUSINESS_STATE.md?"* |

---

## Stato pre-live gates (Validation System §6)

| Gate | Stato | Note |
|------|-------|------|
| FIFO integrity | ✅ | 57a shipped 2026-05-05 |
| Zero FIFO drift 7 giorni | 🔲 | Conteggio riparte dopo Phase 2 |
| Health check 100% 7 giorni | 🔲 | Idem |
| DB retention stabile | ✅ | 59b shipped 2026-05-05 |
| Board approval | 🔲 | Richiede tutto il sopra ✅ |
| **V&C protocol operativo** | ✅ | **Aggiunto oggi (S63)** |

---

## Blocco diary-ready (per Supabase + .docx Volume 3)

_Sezione da compilare dal CEO. Bozza ~250 parole in inglese, tone Volume 3._
