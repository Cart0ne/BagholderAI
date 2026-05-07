# Workflow Operativo — BagHolderAI

Handbook delle azioni manuali di Max (CEO/Direttore Lavori) per orchestrare 
il sistema multi-agente. Questo file è la "checklist da Max stanco alle 23". 

Per il dettaglio dei protocolli a cui questo file si appoggia:
- CLAUDE.md (istruzioni per Claude Code/CC)
- AUDIT_PROTOCOL.md (audit esterni)
- Project Instructions del CEO Claude.ai (sul claude.ai/projects)

---

## Gli attori

| Ruolo | Chi | Dove vive | Cosa fa |
|---|---|---|---|
| **Max** | Tu | MBP + iPhone | Orchestra. Porta i pezzi tra AI. Approva. |
| **CEO** | Claude.ai Opus 4.6 (Project) | claude.ai web/app | Decide strategia. Scrive brief. Aggiorna BUSINESS_STATE. Compila diary. |
| **CC** | Claude Code in VSCode (sessioni) | VSCode su MBP | Esegue codice. Aggiorna PROJECT_STATE. Committa/pusha. |
| **Auditor** | Sessione CC fresh con scope ristretto | VSCode su MBP | Verifica/flagga. Non decide, non esegue task ordinari. |

---

## I 4 file di stato (chi scrive, chi legge, dove vive)

| File | Lo scrive | Lo legge | Posizione |
|---|---|---|---|
| **PROJECT_STATE.md** | CC (fine ogni sessione) | CC + CEO + Max + Auditor | Root del repo |
| **BUSINESS_STATE.md** | CEO (fine ogni sessione strategica) | CEO + CC + Max + Auditor | Root del repo |
| **CLAUDE.md** | Max (raramente, edit guidati) | CC | Root del repo |
| **Project Instructions** | Max (raramente) | CEO | claude.ai Project settings |

Stato fresco = file committato e pushato in main, sincronizzato dal Project 
Knowledge di claude.ai (sync automatica entro 2-5 min dal push).

---

## Routine quotidiane (cosa fai TU)

### A. Inizio chat con CEO

1. **Apri SEMPRE una nuova chat** dentro il Project, non riusare vecchie 
   (le vecchie hanno context stale).
2. Prima domanda di sanity check: *"che data riporta PROJECT_STATE.md?"*
   - Se risponde con la data più recente → tutto OK, procedi.
   - Se dice "non lo trovo" o data vecchia → la sync GitHub non è ancora 
     arrivata. Aspetta 5 min, ricarica chat, riprova.
3. Procedi con l'argomento della sessione.

### B. Fine chat con CEO (sessione strategica)

1. Chiedi al CEO: *"produci un blocco di aggiornamento per BUSINESS_STATE.md 
   con le sezioni cambiate stasera"*. 
2. Lui ti consegna un artifact .md.
3. Salvi l'artifact nel repo come `BUSINESS_STATE.md` (sostituisci il vecchio).
4. Apri sessione CC e dai: *"ho aggiornato BUSINESS_STATE.md, verifica 
   formato, committa, pusha"*. Una sola istruzione, CC fa il resto.

### C. Inizio sessione CC

1. CC ti chiederà *"facciamo git pull?"* (regola in CLAUDE.md). Confermi sì.
2. CC legge PROJECT_STATE.md + BUSINESS_STATE.md (lo fa da solo).
3. Se CC flagga drift/incoerenze (audit clause [0] di CLAUDE.md), STOP — 
   risolvi prima di procedere. Drift comuni: file rinominato non aggiornato 
   nel brief, decisione presa che non si riflette nello state.
4. Passi il brief.

### D. Durante una sessione CC (task non banali)

Per task con stima > 1h o > 50 righe codice:
1. CC produrrà PRIMA un piano in italiano (regola CLAUDE.md sezione [3]).
2. **Tu lo leggi**. Se non capisci, chiedi spiegazioni in italiano. Mai 
   approvare ciò che non capisci.
3. Se vuoi farlo validare dal CEO: copi il piano nella chat CEO, lui ti dà 
   il sign-off, tu lo riferisci a CC.
4. Approvi → CC esegue.

Per task piccoli (fix puntuale, < 50 righe): CC procede direttamente.

### E. Fine sessione CC

1. CC rigenera PROJECT_STATE.md come ULTIMO step (regola CLAUDE.md [1]).
2. CC committa + pusha (regola standard).
3. Tu controlli che il commit sia in `origin/main` (CC te lo conferma).
4. Niente altro. Sync GitHub → Project Knowledge è automatica.

### F. Fine volume del Diary

1. Apri sessione CC pulita per check di congruenza interna del diario 
   (workflow esistente, vedi memoria personale).
2. Considera di richiedere un audit Area 2 (vedi sezione G).

### G. Quando richiedere un audit esterno

Vedi `AUDIT_PROTOCOL.md` per dettagli. Trigger tipici:

- **Area 1 (tech)**: dopo ogni feature significativa o mensile
- **Area 2 (coerenza progetto)**: a fine ogni volume Diary
- **Area 3 (marketing)**: trimestrale + pre-lancio

Procedura:
1. Crei `audits/audit_request_YYYYMMDD_topic.md` (cartella gitignored, 
   resta locale)
2. Apri sessione CC FRESH e gli passi il file come brief
3. CC ti consegna il report
4. Tu salvi in `audits/audit_report_YYYYMMDD_topic.md`
5. Aggiorni PROJECT_STATE.md sezione 9 con la sintesi 1-2 righe (CC può 
   farlo per te se glielo chiedi)

---

## Cose da NON fare (errori che ti costeranno tempo)

| Mai | Perché |
|---|---|
| Riusare una chat vecchia col CEO per nuovi argomenti | Ha context stale, sbaglia decisioni |
| Saltare il git pull a inizio sessione CC | Lavoro multi-macchina, rischi di sovrascrivere |
| Approvare piani CC che non capisci | Vibe coding fa danni se non comprendi |
| Saltare l'update di PROJECT_STATE.md a fine sessione CC | Prossima sessione parte stale, ricomincia il problema da 1.5 mesi |
| Editare CLAUDE.md o Project Instructions a manina senza farlo passare da CC | Rischio di rompere markdown / regole |
| Far passare brief CEO → CC senza controllo del path/file | Roadmap docet (web/roadmap.html → web_astro/src/pages/roadmap.astro) |

---

## Checklist veloce (stampa mentalmente)

**Inizio sessione CC**
- [ ] Confermo git pull
- [ ] CC ha letto PROJECT_STATE + BUSINESS_STATE
- [ ] Eventuali drift flaggati risolti
- [ ] Brief consegnato

**Fine sessione CC**
- [ ] PROJECT_STATE.md rigenerato
- [ ] Commit + push fatto
- [ ] Verifica `origin/main` aggiornato

**Inizio chat CEO**
- [ ] Nuova chat (no riuso)
- [ ] Sanity check: data PROJECT_STATE corretta

**Fine chat CEO strategica**
- [ ] Artifact aggiornamento BUSINESS_STATE prodotto
- [ ] File salvato nel repo
- [ ] CC ha committato + pushato

---

## Quando il sistema fallisce

- **Sync GitHub → Project Knowledge non arriva**: aspetta 5 min, poi 
  forza refresh nel pannello "Manage knowledge" del Project.
- **CEO continua a usare info vecchia anche dopo il refresh**: chiudi la 
  chat e aprine un'altra. La cache della chat è separata dal Knowledge.
- **CC vuole eseguire ma il piano italiano non arriva**: ricordagli 
  CLAUDE.md sezione [3]: *"prima il piano in italiano, conferma poi codice"*.
- **PROJECT_STATE.md è invecchiato senza aggiornamenti**: avvia una 
  sessione CC dedicata: *"rigenera PROJECT_STATE.md leggendo git log + 
  ultimi report e committa"*.

---

**Last updated**: 2026-05-07 — Session 63 (init)  
**Owner**: Max  
**Manutenzione**: aggiorna quando il workflow cambia (raro). Ogni audit 
Area 2 può proporre modifiche.
