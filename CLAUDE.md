# BagHolderAI - Project Instructions

═══════════════════════════════════════════
 [0] AUDIT DELLE ISTRUZIONI — al volo
═══════════════════════════════════════════

Se durante una sessione noti che una di queste istruzioni — o una sezione 
di un brief ricevuto — riferisce un file/path che non esiste più, 
contraddice lo stato reale del repo, o è ambigua, NON ignorarlo. 
Ferma il task corrente e segnala a Max:

"⚠️ Drift istruzioni: la sezione [X] dice Y, ma il repo dice Z. 
Propongo modifica: [testo]. Vuoi che aggiorni CLAUDE.md prima di procedere?"

Aspetta conferma prima di scrivere codice basato su istruzioni potenzialmente stale.

═══════════════════════════════════════════
 [1] FILE DI STATO — leggi all'inizio, scrivi alla fine
═══════════════════════════════════════════

ALL'INIZIO di ogni sessione, leggi:
- PROJECT_STATE.md (lo aggiorni tu, ti dice dove eri rimasto)
- BUSINESS_STATE.md (lo aggiorna il CEO, ti dice vincoli strategici 
  e deadline non-tecniche)
- la Master Task List più recente (`config/MASTER_TASK_LIST_*.md`; la 
  data nel nome del file = ultimo aggiornamento) — l'elenco vivo dei task 
  aperti/chiusi (Fasi 0-4 + backlog congelato + bug aperti). Regola 
  formalizzata 2026-07-01.

Se c'è discrepanza tra il brief ricevuto e i file di stato (es. il brief 
assume codice in uno stato superato), FERMA e segnala a Max.

A FINE ogni sessione, prima di chiudere:
- Rigenera PROJECT_STATE.md con lo stato aggiornato (vedi sezione [2])
- Committa nel repo con messaggio: "docs: update PROJECT_STATE.md (session XX)"

Questa è la regola n.1: NON chiudere una sessione senza aggiornare 
PROJECT_STATE.md. È più importante del report finale per il CEO.

ROADMAP CHECK (formalizzato S108, audit A2 recidiva H1):
A fine sessione, PRIMA di committare PROJECT_STATE.md, verifica:
- Hai shippato qualcosa che tocca una Phase della roadmap?
- Se sì: aggiorna `web_astro/src/data/roadmap.ts` (version bump + lastUpdated + task done).
- Se non sei sicuro: `git diff --name-only` della sessione e controlla se qualche 
  file tocca funzionalità tracciate in roadmap.
- Questo check è AGGIUNTIVO rispetto alla sezione "Roadmap impact" nei brief CEO. 
  Il brief può dimenticarsi di listare l'impatto; tu no.

Inoltre, quando rigeneri PROJECT_STATE.md, controlla la cadenza degli 
audit esterni. Per ciascuna area, se l'ultimo audit chiuso è più 
vecchio della cadenza suggerita, segnalalo a Max nel report finale 
della sessione come riga separata:

- Area 1 (tecnica): cadenza 30 giorni
- Area 2 (coerenza progetto): trigger event-based — vedi AUDIT_PROTOCOL.md §2 per la lista completa (pre-mainnet / pre-Volume / pre-nuovo-brain). Backstop 60gg.
- Area 3 (strategy & marketing): cadenza 30 giorni (mensile; era bisettimanale fino al 2026-06-01, allineata al task schedulato Cowork) — dati via `scripts/marketing_data_refresh`, template `audits/requests/audit_request_A3.md`

Formato del segnale: "⚠️ Audit Area X dovuto: ultimo era YYYY-MM-DD 
(N giorni fa). Proponi a Max di pianificarlo."

Se non c'è MAI stato un audit di un'area, considera l'età come 
"infinita" e segnala.

**REGOLA ANTI-DRIFT (formalizzata 2026-05-15)** — la conta della cadenza 
si fa sui FILE `audits/reports/YYYYMMDD_audit[AX].md`, NON sulle righe 
di PROJECT_STATE.md §9. Motivo: prima di questa regola CC popolava §9 
con le proprie sessioni di sviluppo etichettandole "Area 1", e il check 
di cadenza risultava sempre fresco anche se nessun audit vero era mai 
stato eseguito (conflitto di interessi strutturale: chi esegue il task 
si auto-certifica come Auditor).

Operativamente:
1. `ls audits/reports/*.md` → estrai la data più recente per area
2. Confronta con la cadenza
3. Se vecchio o assente → segnala

E NON scrivere mai una riga in §9 per la sessione che stai chiudendo 
se hai shippato codice (commit + restart bot + migration). Quella riga 
va in §10 "Sessioni shipped". Solo un Auditor (CC fresh con brief 
`audits/requests/*.md`, vedi `AUDIT_PROTOCOL.md` per il protocollo completo + `WORKFLOW.md §G`) 
ha titolo per aggiungere riga §9, e solo dopo aver depositato il file 
`audits/reports/*.md` corrispondente.

### Numerazione sessioni (formalizzata S108, 2026-06-20)

- **Sessioni di lavoro** (CEO + Board): prendono numero progressivo
  (S108, S109...). Hanno diary, summary Supabase, possono avere brief.
- **Sessioni marketing**: niente numero, niente diary, niente brief.
  Solo aggiornamento marketing tracker.
- **Audit automatici** (Cowork): niente numero sessione. Se producono
  brief, naming: `YYYY-MM-DD_audit[Area]_brief_SCOPE.md`.
  Esempio: `2026-06-18_auditA2_brief_remediation.md`.

═══════════════════════════════════════════
 [2] PROJECT_STATE.md — formato fisso
═══════════════════════════════════════════

Il file vive in root del repo. Max 50 KB. Sezioni canoniche (sempre stesse,
sempre nello stesso ordine):

1. Stato attuale (max 5 righe): fase, prossimo deploy, vincolo del momento
2. Architettura attiva (max 30 righe): mappa moduli + responsabilità
3. In-flight (max 15 righe): cosa stai toccando questa settimana, file:linea
4. Decisioni recenti (ultime 10-15, formato: data — decisione — why)
5. Bug noti aperti (con TODO marker e file:linea, riga per bug)
6. Domande aperte per CEO (cosa hai parcheggiato perché serve input strategico)
7. Vincoli stagionali / deadline tecniche
8. Cosa NON è stato fatto e perché (1 paragrafo)
9. Audit esterni (sintesi): tabella data/area/topic/verdetto/findings/report.
   **Solo audit veri**: una riga §9 esiste se e solo se esiste il file
   `audits/reports/YYYYMMDD_audit[AX].md` corrispondente, prodotto da un
   Auditor (sessione CC fresh con brief `audits/requests/*.md`).
   Vedi `AUDIT_PROTOCOL.md` + `WORKFLOW.md §G`.
10. Sessioni shipped (storico): tabella delle sessioni di sviluppo che 
    hanno chiuso brief CEO con SHIPPED + commit + (eventuale) restart.
    Stesse colonne data/area/topic/esito/sintesi. È QUI che CC scrive 
    quando ha shippato codice — MAI in §9.

Per popolare le sezioni leggi: git log ultimi 30 giorni, ultimi 5 file in 
report_for_CEO/, ultimi 10 file in briefresolved.md/, TODO inline (62a/63a/...).

NON includere nel file: codice intero, log verbose, output di test, 
contenuto dei brief vecchi (basta linkarli).

**REGOLA COMPACTION (formalizzata S79; isteresi 50/40 da S99 2026-06-07)** — il file ha 
DUE soglie: **trigger 50KB** (quando scatta la compaction) e **target 40KB** (dove 
deve rientrare), con **tolleranza ±2KB** (confermato Max 2026-06-28: la compaction non 
è obbligatoria finché il file resta ≤52KB). Quando a fine sessione il file supera 50KB 
oltre la tolleranza, compatta riportandolo a **≤40KB** — NON solo "appena sotto 50". Motivo: con trigger=target a 50KB il file 
restava sempre al limite e serviva compattare ogni sessione; il margine di ~10KB copre 
più sessioni. NON cancellare in toto le sezioni vecchie. Workflow:

1. Identifica le sezioni da rimuovere (di solito header narrativi di 
   sessioni passate + voci §3 in-flight di sessioni shipped + voci §4 
   decisioni più vecchie di ~15 righe)
2. **PRIMA** di cancellare, appendi il loro contenuto in 
   `audits/PROJECT_STATE_archive.md` con header:
   ```
   ## Rimosso in sessione SXX (YYYY-MM-DD) — <ragione compaction>
   ```
3. Poi cancella le stesse sezioni da `PROJECT_STATE.md`
4. Commit unico con messaggio che cita entrambi i file

L'archive cresce nel tempo (single growing file, non viene letto a ogni 
sessione, solo on-demand quando serve il "perché abbiamo deciso X in S65?"). 
Mai eliminare in toto. Sempre archiviare prima.

═══════════════════════════════════════════
 [2b] BUSINESS_STATE.md — stessa regola di compaction
═══════════════════════════════════════════

Anche `BUSINESS_STATE.md` vive in root del repo e ha **cap/trigger 50KB → target 40KB, 
tolleranza ±2KB** (stessa regola di PROJECT_STATE §2; confermato Max 2026-06-28). È il file 
che il CEO (Claude su claude.ai) usa per i vincoli strategici, decisioni 
Board, deadline non-tecniche, marketing, diary status.

Il file è AGGIORNATO da CC SOLO SU ISTRUZIONE ESPLICITA di Max o del CEO 
(in chat o via brief .md). NON modificare BUSINESS_STATE di propria 
iniziativa, nemmeno per "manutenzione". Il contenuto è territorio strategico, 
non tecnico.

**Sezioni canoniche** (tipiche, possono variare leggermente nel tempo):
1. Header (last updated, basato su)
2. Marketing in-flight (sito, X, blog, Dev.to, Payhip)
3. Diary status (volumi, sessioni in accumulo)
4. Decisioni strategiche recenti (~15 voci max, formato data — decisione — why)
5. Domande aperte per CC (idee tech non ancora in brief)
6. Vincoli / deadline non-tecnici (go-live, multi-macchina, audit)
7. Cosa NON sta succedendo e perché

**REGOLA COMPACTION — richiede autorizzazione di Max**

A differenza di PROJECT_STATE (dove la compaction è autonoma di CC), per 
BUSINESS_STATE la compaction NON va eseguita di iniziativa, nemmeno quando 
il file supera 50KB. Anche se durante un'update authorized noto che il 
file è sopra soglia, segnalo a Max:

> "⚠️ BUSINESS_STATE è a 53KB (oltre la tolleranza di 2KB), vuoi che compatti adesso?"

Procedo SOLO se Max conferma. La compaction è atto strategico (decide 
cosa resta visibile a chi legge il file vivo) e va autorizzata.

**Quando autorizzato**, workflow identico a PROJECT_STATE:

1. Identifica le sezioni da rimuovere (di solito voci §4 decisioni più 
   vecchie di ~15 righe + voci §5 chiuse/superate con strikethrough + 
   header narrativi di sessioni passate + voci §7 duplicate)
2. **PRIMA** di cancellare, appendi il contenuto in 
   `audits/BUSINESS_STATE_archive.md` con header:
   ```
   ## Rimosso in sessione SXX (YYYY-MM-DD) — <ragione compaction>
   ```
3. Poi cancella le stesse sezioni da `BUSINESS_STATE.md`
4. Commit unico che cita entrambi i file

L'archive è stato creato in S85 (2026-05-25) ricostruendo retroattivamente 
le compaction S71 e S79 dalla git history (commit `0ae0610` e `7945b54`).

**Caso speciale — istruzioni CEO tipo "rimuovi le voci più vecchie di Sxx"**: 
quando il brief CEO ti dice esplicitamente di tagliare/rimuovere/comprimere 
righe, è già un'autorizzazione implicita. NON cancellarle senza archiviare: 
estrai prima il contenuto da cancellare, appendilo all'archive, poi applica 
il cleanup. Il CEO si fida che tu mantenga lo storico.

═══════════════════════════════════════════
 [3] PROTOCOLLO PER TASK NON BANALI
═══════════════════════════════════════════

Se un task ha stima > 1h di lavoro o > 50 righe di codice da modificare:

1. Produci PRIMA un piano in italiano leggibile da Max:
   - Cosa cambierà (file:linea o sezione)
   - Perché in questo modo
   - Cosa NON cambierà
   - Rischi noti
2. Attendi conferma di Max prima di scrivere codice
3. Se durante l'esecuzione devi prendere una decisione non prevista nel 
   piano, FERMATI e flagga: "Decisione non prevista: [X]. Opzioni: A/B/C. 
   Procedo con A?"

Per task piccoli (fix puntuale, edit < 50 righe, refactor banale): 
puoi procedere direttamente.

═══════════════════════════════════════════
 [4] DECISION LOG durante la sessione
═══════════════════════════════════════════

Quando prendi una decisione tecnica non triviale (trade-off architetturale, 
scelta tra approcci alternativi, deviazione dal brief), registralo inline 
nel report finale in una sezione "Decisions" con formato:

DECISIONE: [scelta]
RAZIONALE: [why]
ALTERNATIVE CONSIDERATE: [B, C]
FALLBACK SE SBAGLIATA: [come si torna indietro]

Queste decisioni finiranno poi sintetizzate in PROJECT_STATE.md sezione 4
(Decisioni recenti). Senza decision log, il CEO non sa che esistevano 
trade-off — vede solo il risultato.

═══════════════════════════════════════════
 [5] WORKFLOW GIT — multi-macchina
═══════════════════════════════════════════

All'inizio di ogni conversazione, chiedere sempre: "Dobbiamo fare un 
git pull per partire con la versione più aggiornata?"

Il progetto viene sviluppato su 2 macchine (MacBook Air + Mac Mini), 
quindi il repo remoto potrebbe avere commit più recenti.

**HEALTH-SWEEP PROCESSI — inizio sessione (formalizzata 2026-07-01)**: 
insieme alla domanda sul pull, verifica che **TUTTI** i processi attesi sul 
Mac Mini siano up — non solo orchestrator + grid bot. Fai `ssh 
max@Mac-mini-di-Max.local 'ps aux'` (+ `launchctl list | grep bagholderai`) 
e confronta con l'inventario atteso:
- **Orchestrator-managed**: orchestrator + figli (4 grid BTC/SOL/BONK/ETH + 
  TF + Sentinel + Sherpa)
- **Standalone (non-managed)**: NewsKeeper v2; listener `x_poster_approve` 
  (LaunchAgent `com.bagholderai.xposter-approve`)
- **Cron sani** (crontab presente + ultimo run non in errore nei log): 
  x_poster `--cron` 20:30 Rome, reconcile_binance 03:00 Rome
- **In-process (no crontab)**: db_maintenance 04:00 UTC gira dentro 
  l'orchestrator (`bot/db_maintenance.py`, chiamato da `orchestrator.py`) — 
  verificare riga `[maintenance]` recente nel log orchestrator, non il crontab
Riporta a Max **cosa è su e cosa è giù**. Un processo mancante lo **segnali**, 
non lo riavvii d'iniziativa (la regola restart qui sotto resta). Motivo: il 
listener `/approve` è rimasto morto ~1 mese perché il check era 
orchestrator-centrico (caccia bug 2026-07-01, `bfe3433`).

**RESTART DEI BOT — regola (formalizzata S105b, 2026-06-13)**: CC riavvia 
l'orchestrator / i bot sul Mac Mini **SOLO se Max lo chiede esplicitamente**. 
Pull e push restano autonomi di CC; il restart no — è Max a deciderne il 
momento. Questa regola supera sia il divieto assoluto "CC non riavvia" (usato 
in alcuni brief) sia l'autonomia piena della vecchia nota. Quando Max chiede 
il restart: catturare prima il comando di lancio corrente (`ps -p <pid> -o 
command=`) per replicare gli env flag esatti, fare shutdown graceful 
(SIGTERM all'orchestrator, che propaga ai figli), NON toccare i processi 
standalone NewsKeeper v1/v2, rilanciare daemonizzato (`nohup caffeinate … &`), 
verificare i processi su + l'effetto a DB.

═══════════════════════════════════════════
 [6] PROJECT CONTEXT
═══════════════════════════════════════════

- Trading bot crypto con paper trading su Binance testnet
- 3 grid instances: BTC/USDT, SOL/USDT, BONK/USDT
- Stack: Python, Supabase (DB), Telegram (notifications), Vercel (dashboard)
- Lingua preferita per la comunicazione: italiano

═══════════════════════════════════════════
 [7] CROSS-CHECK & NAMING (CC)
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
