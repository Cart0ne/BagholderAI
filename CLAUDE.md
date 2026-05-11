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

Se c'è discrepanza tra il brief ricevuto e i file di stato (es. il brief 
assume codice in uno stato superato), FERMA e segnala a Max.

A FINE ogni sessione, prima di chiudere:
- Rigenera PROJECT_STATE.md con lo stato aggiornato (vedi sezione [2])
- Committa nel repo con messaggio: "docs: update PROJECT_STATE.md (session XX)"

Questa è la regola n.1: NON chiudere una sessione senza aggiornare 
PROJECT_STATE.md. È più importante del report finale per il CEO.

Inoltre, quando rigeneri PROJECT_STATE.md, controlla la sezione 9 
(Audit esterni). Per ciascuna area, se l'ultimo audit chiuso è più 
vecchio della cadenza suggerita, segnalalo a Max nel report finale 
della sessione come riga separata:

- Area 1 (tecnica): cadenza 30 giorni
- Area 2 (coerenza progetto): cadenza 90 giorni o fine-volume Diary
- Area 3 (strategy & marketing): cadenza 90 giorni

Formato del segnale: "⚠️ Audit Area X dovuto: ultimo era YYYY-MM-DD 
(N giorni fa). Proponi a Max di pianificarlo."

Se non c'è MAI stato un audit di un'area, considera l'età come 
"infinita" e segnala.

═══════════════════════════════════════════
 [2] PROJECT_STATE.md — formato fisso
═══════════════════════════════════════════

Il file vive in root del repo. Max 40 KB. Sezioni canoniche (sempre stesse,
sempre nello stesso ordine):

1. Stato attuale (max 5 righe): fase, prossimo deploy, vincolo del momento
2. Architettura attiva (max 30 righe): mappa moduli + responsabilità
3. In-flight (max 15 righe): cosa stai toccando questa settimana, file:linea
4. Decisioni recenti (ultime 10-15, formato: data — decisione — why)
5. Bug noti aperti (con TODO marker e file:linea, riga per bug)
6. Domande aperte per CEO (cosa hai parcheggiato perché serve input strategico)
7. Vincoli stagionali / deadline tecniche
8. Cosa NON è stato fatto e perché (1 paragrafo)
9. Audit esterni (sintesi): tabella data/area/topic/verdetto/findings/report
   (vedi AUDIT_PROTOCOL.md; aggiungere riga ad ogni audit chiuso)

Per popolare le sezioni leggi: git log ultimi 30 giorni, ultimi 5 file in 
report_for_CEO/, ultimi 10 file in briefresolved.md/, TODO inline (62a/63a/...).

NON includere nel file: codice intero, log verbose, output di test, 
contenuto dei brief vecchi (basta linkarli).

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

═══════════════════════════════════════════
 [6] PROJECT CONTEXT
═══════════════════════════════════════════

- Trading bot crypto con paper trading su Binance testnet
- 3 grid instances: BTC/USDT, SOL/USDT, BONK/USDT
- Stack: Python, Supabase (DB), Telegram (notifications), Vercel (dashboard)
- Lingua preferita per la comunicazione: italiano
