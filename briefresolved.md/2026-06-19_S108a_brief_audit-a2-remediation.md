# Brief S108a — audit-a2-remediation — 2026-06-19

**Da:** CEO  
**A:** CC (Claude Code)  
**Contesto:** Audit Area 2 del 19/06/2026, verdetto CON RISERVE (1 HIGH dopo review CEO, 3 MED, 6 LOW). Questo brief copre la remediation dei finding che richiedono intervento CC.

---

## Priorità 1 — H1: Roadmap bump (OBBLIGATORIO)

**File:** `web_astro/src/data/roadmap.ts`

La roadmap è ferma a "Versione 1.48 — Maggio 2026, last updated 2026-05-27". È una **recidiva** (stesso finding dell'audit del 27/05). Aggiornare:

1. **Version string** → `"Versione 1.49 — Giugno 2026"` (o la prossima minor sensata)
2. **lastUpdated** → `"2026-06-19"`
3. **Dati Phase da aggiornare** (verificare contro il codice/DB reale, non fidarsi di questa lista):
   - Sherpa LIVE testnet (S102b, 11 giugno) → la Phase corrispondente deve riflettere lo stato LIVE, non solo "ACTIVE" o contatore vecchio
   - NewsKeeper v2 "barometro" build + shadow validation (S100, 9 giugno) → Phase 14 aggiornare il contatore (era "1/3")
   - ETH come 4° coin (S106/S108) → aggiungere dove appropriato
   - Test count 228/228 (S105) → aggiornare se presente
   - Qualsiasi altro task completato tra S88 e S108 che trovi nel git log e non è riflesso

**Come verificare:** `git log --oneline --since="2026-05-27"` e confrontare con i task in roadmap.ts. Se un task shippato non è segnato done, segnalo done.

---

## Priorità 2 — Regola strutturale anti-recidiva roadmap

**File:** `CLAUDE.md` — sezione `[1] FILE DI STATO`

Aggiungere al checklist di fine sessione (dopo la regola su PROJECT_STATE.md):

```
ROADMAP CHECK (formalizzato S108, audit A2 recidiva H1):
A fine sessione, PRIMA di committare PROJECT_STATE.md, verifica:
- Hai shippato qualcosa che tocca una Phase della roadmap?
- Se sì: aggiorna `web_astro/src/data/roadmap.ts` (version bump + lastUpdated + task done).
- Se non sei sicuro: `git diff --name-only` della sessione e controlla se qualche file tocca funzionalità tracciate in roadmap.
- Questo check è AGGIUNTIVO rispetto alla sezione "Roadmap impact" nei brief CEO.
  Il brief può dimenticarsi di listare l'impatto; tu no.
```

Nota: la regola in `validation_and_control_system.md` ("Roadmap impact obbligatorio nei brief") esiste da S59 ma non ha prevenuto la recidiva, perché dipende dal CEO che si ricordi di scriverla. Questa regola complementare mette il check su CC come safety net.

---

## Priorità 3 — Fix cosmetici sito (IF TIME PERMITS)

Tutti LOW dall'audit. Se la sessione è già lunga, parcheggiare senza problemi.

### L1 — Date "fresh start" incoerenti
Homepage dice "Fresh start · Jun 4", dashboard dice "Clean slate since Jun 4", grid card dice "since Jun 5", CEO log Day 1 = Jun 5. Allineare tutto a una data sola. Verificare qual è quella corretta (primo trade del ciclo testnet_2) e usare quella ovunque.

### L2 — Homepage snapshot "total P&L $0.00 / today P&L $0.00"
Verificare se il valore è cablato o se è un problema di caricamento/fallback. Se cablato → collegare al dato reale o rimuovere. Se è un fallback che appare durante il caricamento → accettabile, non fixare.

### L3 — howwework "Nine canonical sections"
**File:** `web_astro/src/pages/howwework.astro` (o equivalente)
PROJECT_STATE ha ora 10 sezioni (§10 "Sessioni shipped" aggiunta dopo). Cambiare "Nine" → "Ten" nel testo pubblico.

### L4 — howwework restart orchestrator
Stesso file. Rule #03 dice "the intern restarts the orchestrator and pushes to git". CLAUDE.md §5 (da S105b) ora dice: CC riavvia **solo se Max lo chiede esplicitamente**. Aggiornare il wording pubblico per riflettere la regola attuale.

### L6 — Label TEST/LIVE incoerenti home vs dashboard
Homepage mostra Sherpa/Watchtower come "TEST", dashboard li mostra come "live". Valutare se serve allineare la label o se la differenza è intenzionale (testnet = test per l'homepage, live = attualmente in esecuzione per la dashboard). Se intenzionale → non fixare, ma aggiungere un commento nel codice che spiega la scelta. Se non intenzionale → allineare.

---

## OFF-LIMITS

- **NON toccare** `bot/` — nessun file di runtime, nessun restart
- **NON toccare** BUSINESS_STATE.md — lo aggiorna il CEO
- **NON toccare** i volumi pubblicati (V1/V2/V3) — artefatti storici
- **NON toccare** PROJECT_STATE §9 e AUDIT_PROTOCOL §7 — li aggiorna CC a fine sessione come da procedura standard dopo aver verificato che il file `audits/reports/20260619_audit[A2].md` esiste nel repo

## Roadmap impact

Il bump IS il task. Version → 1.49, date → 2026-06-19, task shippati S88–S108 → done.

---

## Auto-obiezione CEO

Sto chiedendo a CC di fare un bump roadmap che potrebbe richiedere 30+ minuti di git log archeology per trovare tutti i task shippati. Se il roadmap.ts ha molte Phase con molti task granulari, CC potrebbe perdersi. **Mitigazione:** CC può partire dai finding espliciti dell'audit (Sherpa LIVE, NewsKeeper barometro, ETH, test count) e poi fare un pass veloce sul git log per catturare il resto. Se dopo 20 minuti non ha finito l'archeologia, shippare quello che ha e segnalare il resto nel report.
