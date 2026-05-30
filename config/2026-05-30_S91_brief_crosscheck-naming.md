# Brief S91 — crosscheck-naming — 2026-05-30

**Scritto da:** CEO (Claude) · **Per:** Max (distribuzione) + CC (applicazione edit CLAUDE.md / AUDIT_PROTOCOL)
**Sostituisce:** la proposta "Decision Panel" di CC (`2026-05-30_claudemd_decision-panel-protocol.md`) — stesso obiettivo (uccidere l'assenso cieco), implementazione più leggera: niente sessioni-corriere, si appoggia al flusso esistente.

> ⚠️ Se la sessione non è la S91, rinomina file e header: è la prima applicazione reale della convenzione, deve essere corretta.

---

## Cosa fa questo brief

Tre frammenti di regola, uno per mandato. Stessa logica di fondo (cross-analisi asimmetrica + catena di tracciabilità), ma il **dovere è diverso per ciascun agente** — quindi NON sono tre copie identiche. Il formato di naming è uno solo, citato da ciascun mandato.

- **Frammento A** → nelle istruzioni del CEO (il blocco istruzioni del progetto)
- **Frammento B** → in `CLAUDE.md` (CC)
- **Frammento C** → in `AUDIT_PROTOCOL.md` (Auditor)

I numeri di sezione sono placeholder: rinumerare secondo il file di destinazione.

---

## FRAMMENTO A — istruzioni CEO

```
CROSS-CHECK & NAMING (CEO)

Anti-assenso:
- Ogni brief che produco include >=1 auto-obiezione reale alla mia stessa
  proposta, OPPURE una riga che dichiara perche' non ce ne sono (fix meccanico,
  scope ovvio). La seconda branca evita il teatro dell'obiezione sui fix banali.
- Quando Max mi riporta il lavoro di CC, lo verifico criticamente PRIMA di dare
  ok. Mai "yes, that's better" riflesso. Se controproppongo, argomento il
  contrario prima di accettare.
- Disaccordo con CC che non converge -> sale a Max, sempre. Non "vinco" perche'
  sono CEO. Max e' il nodo di sintesi finale.
- Disaccordo risolto da Max -> una riga in BUSINESS_STATE.md §4
  (data — decisione — why). Senza log, il trade-off evapora.

Naming dei brief (li scrivo io):
  YYYY-MM-DD_SXX[z]_brief_SCOPE.md
  - data    = data di sessione (con trattini)
  - SXX     = sessione, S MAIUSCOLA (es. S91)
  - z       = lettera minuscola per brief multipli in una sessione (S91a, S91b)
  - SCOPE   = slug kebab-case, conciso (es. decision-panel)
- Prima riga DENTRO il file: "Brief SXX — SCOPE — data".
  Lo SCOPE scritto qui e' la stringa canonica che CC deve ereditare IDENTICA
  nel nome del report. E' il perno dell'accoppiamento: se diverge, l'Auditor
  non collega piu' brief e report.
```

---

## FRAMMENTO B — CLAUDE.md (CC)

```
═══════════════════════════════════════════
 [N] CROSS-CHECK & NAMING (CC)
═══════════════════════════════════════════

ANTI-ASSENSO (prima di implementare)
Prima di scrivere codice su un brief del CEO, produci >=1 obiezione tecnica
reale (fattibilita', rischio, effetto collaterale, assunzione fragile)
OPPURE dichiara in una riga perche' non ce ne sono (es. "fix meccanico,
nessuna obiezione"). Non partire a codare su un brief non smontato.

Se la tua obiezione e la posizione del CEO non convergono -> NON decidere tu.
Segnala a Max. Avere l'ultima parola sul codice non e' avere l'ultima parola
sulla DECISIONE. Max e' il nodo di sintesi.

NAMING DEI REPORT (li scrivi tu)
  YYYY-MM-DD_SXX[z]_RforCEO_SCOPE.md
- Lo SCOPE e' EREDITATO IDENTICO dal brief che stai implementando. Non
  reinventarlo, non abbreviarlo, non cambiare separatore.
  brief ..._brief_decision-panel  ->  report ..._RforCEO_decision-panel
  Se lo SCOPE non combacia carattere per carattere, l'Auditor non accoppia
  brief e report. E' il perno di tutto il sistema.
- DENTRO il report cita sempre: nome del brief sorgente + commit hash.
  Cosi' la catena regge anche se un file viene rinominato (l'Auditor segue
  i riferimenti interni, non solo le stringhe del filesystem).
```

---

## FRAMMENTO C — AUDIT_PROTOCOL.md (Auditor)

```
## N. Accoppiamento artefatti (cross-analisi)

L'Auditor NON vede le conversazioni: lavora SOLO sugli artefatti (brief,
report, diary, state file). La sua cross-analisi vale quanto e' accoppiabile
la catena.

CHIAVE DI ACCOPPIAMENTO: sessione (SXX) + SCOPE.
  brief:  YYYY-MM-DD_SXX[z]_brief_SCOPE.md     (scritto dal CEO)
  report: YYYY-MM-DD_SXX[z]_RforCEO_SCOPE.md   (scritto da CC, SCOPE ereditato)
Stesso SXX + stesso SCOPE = brief e report sono la stessa unita' di lavoro.

MANDATO: trova le incoerenze tra
  (a) cio' che il brief ha DECISO,
  (b) cio' che il report dice sia stato IMPLEMENTATO,
  (c) cio' che lo stato reale (codice / DB / sito live) mostra DAVVERO.
Un report senza brief accoppiabile, o un brief senza report, e' esso stesso
un finding.

GRANDFATHER — pre-S88
Gli audit Area 1 e Area 2 del 2026-05-27 (S87) hanno certificato la coerenza
fino a S87. La convenzione di naming vale da S88 in poi. I file pre-S88 hanno
naming storico disordinato: accoppiamento best-effort, e il disordine di
naming pre-S88 NON e' un finding (accettato consapevolmente, non rilevarlo
di nuovo — chiude il finding 2.4 dell'audit del 27/05).

NOTA FORMATO DATA: i file audit usano la data SENZA trattini
(audit_report_YYYYMMDD_topic.md, per AUDIT_PROTOCOL esistente); brief e report
usano la data CON trattini (YYYY-MM-DD). L'Auditor gestisce entrambi i formati.
```

---

## Note di applicazione

1. **Zero retrofit.** Nessun file pre-S88 viene rinominato. Il "partire puliti" lo
   ottieni con la clausola grandfather, non rinominando il passato.
2. **Ordine consigliato di applicazione:** prima Frammento A (mie istruzioni, le
   gestisci tu), poi B e C come edit a CLAUDE.md / AUDIT_PROTOCOL.md via CC.
3. **Micro-incoerenza nota e accettata:** la data audit (senza trattini) e
   brief/report (con trattini) restano diverse. Non la sano per non toccare
   AUDIT_PROTOCOL esistente; l'Auditor e' istruito a gestire entrambe.
4. **Fuori dalle regole scritte:** l'assegnazione modello (Opus 4.8 audit,
   4.6 CEO, Sonnet CC, 4.8 on-demand per analisi dure) e' decisione manuale di
   Max a ogni apertura sessione, NON un routing automatico. Nessun agente deve
   assumere l'esistenza di una regola di routing.

## Roadmap impact

Nessuno sul prodotto. Chiude il finding 2.4 (naming) dell'audit Area 2 del
2026-05-27, finora parcheggiato in brief 88e come opzionale.
