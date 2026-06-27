# Brief S110e — newskeeper-cleanup-retention — 2026-06-27

## Contesto

Due processi NewsKeeper girano in parallelo sul Mac Mini (v1 e v2). Entrambi scrivono nella stessa tabella `newskeeper_signals`. V2 ha superato il verdetto (PASS qualità), v1 potrebbe essere ridondante. Separatamente, `trend_scans` sembra avere un purge automatico che cancella dati oltre ~14 giorni — questo ostacola l'accumulo di track record per il futuro TF Tier 3.

## Scope

Tre verifiche + azioni conseguenti. Nessun codice di trading toccato.

## Task 1 — NewsKeeper v1: serve ancora?

**Verifica:** qualcosa nel sistema legge le righe di `newskeeper_signals` che NON hanno `polarity` (= righe v1)?

Come controllare:
- Grep nel codice per query su `newskeeper_signals` — verificare se filtrano per `polarity IS NOT NULL` (= leggono solo v2) oppure leggono tutto indiscriminatamente
- Sentinel, Sherpa, dashboard, qualsiasi consumer: leggono da `newskeeper_signals`? Se sì, distinguono v1 da v2?

**Dati attuali (CEO ha verificato via Supabase):**
- v1 (polarity NULL): 3.175 righe, dal 24 maggio a oggi — ANCORA ATTIVA
- v2 (polarity NOT NULL): 2.009 righe, dal 9 giugno a oggi

**Azioni in base all'esito:**
- Se NULLA legge v1 → segnalare a Max che può spegnere il processo v1 sul Mac Mini (il kill del PID è azione Max, non CC). Documentare quale PID/processo è v1.
- Se QUALCOSA legge v1 → segnalare cosa, e proporre come migrare quel consumer a v2.

## Task 2 — trend_scans: retention e purge

**Verifica:** esiste un meccanismo di pulizia automatica su `trend_scans`? I dati più vecchi risalgono solo al 13 giugno (14 giorni), nonostante TF giri da prima.

Come controllare:
- Cercare nel codice TF/trend qualsiasi DELETE, TRUNCATE, o pulizia periodica su `trend_scans`
- Verificare se c'è un cron, un trigger Supabase, o logica nel bot che cancella righe vecchie
- Controllare se il 13 giugno coincide con un restart/reconfig del TF (in quel caso non c'è purge, ma un reset)

**Dati attuali:**
- 33.450 righe, oldest 2026-06-13, newest oggi

**Azioni in base all'esito:**
- Se c'è un purge → quanto è configurabile la retention? Alzarla ad almeno 90 giorni (serve track record per validare TF Tier 3 clone post-mainnet)
- Se non c'è purge ma TF è stato riavviato il 13 giugno → nessun problema di retention, documentare
- In entrambi i casi: stimare la crescita della tabella (~33K righe / 14 giorni = ~2.4K righe/giorno). A 90 giorni sarebbero ~216K righe — verificare che sia sostenibile su Supabase free tier

## Task 3 — newskeeper_signals: cleanup righe v1

**Dipende dal Task 1.** Solo se v1 risulta non letta da nessuno:

- Archiviare le 3.175 righe v1 (export JSON o CSV in `audits/`) prima di cancellarle
- Cancellare le righe con `polarity IS NULL` dalla tabella
- Valutare: serve aggiungere un vincolo `NOT NULL` su `polarity` per impedire che un processo v1 residuo sporchi i dati in futuro?

## Test checklist

- [ ] Task 1: elenco completo dei consumer di `newskeeper_signals` con indicazione v1/v2
- [ ] Task 2: meccanismo di purge identificato (o confermato assente)
- [ ] Task 2: se purge presente, retention alzata a >=90 giorni
- [ ] Task 3: se v1 non letta, righe archiviate ed eliminate

## File OFF-LIMITS

- `bot/grid_runner/` — non coinvolto
- `bot/sherpa/` — non coinvolto (ma verificare se legge newskeeper_signals)

## Auto-obiezione

Il Task 2 potrebbe rivelare che la cancellazione dei trend_scans è intenzionale per ragioni di performance (tabella troppo grande = query lente per TF). Alzare la retention a 90 giorni senza verificare l'impatto sulle query di scan potrebbe rallentare il TF. CC deve misurare il tempo di query con la retention attuale vs proiettata prima di cambiare.
