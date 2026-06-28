# Report per il CEO — S110 (2026-06-27)

**Scope:** NewsKeeper cleanup + retention (S110e SHIPPED) · triage e correzione
brief S110c (USDC) e S110d (exit thresholds) · housekeeping go-live design + state files
**Brief sorgenti:** `config/2026-06-27_S110c_brief_usdt-to-usdc.md`,
`…_S110d_brief_tf-grid-exit-thresholds.md`, `…_S110e_brief_newskeeper-cleanup-retention.md`
(S110e ora in `briefresolved.md/`; S110d corretto)
**Commit:** `80cd25e` (BUSINESS_STATE) · `5067fcb` (golive APPROVED) · `6ef3acf` +
`67b5148` (S110e) · `c232df3` (S110d corretto) + commit di chiusura (report/archivio).

---

## Sintesi esecutiva

Sessione operativa di sabato. **Un solo brief eseguito (S110e)**; gli altri due
**spiegati, decisi e rimandati** su scelta di Max (task impattanti, non da sabato sera).
Eseguito anche un giro di housekeeping (go-live design APPROVED tracciato, state files,
archiviazione report/brief chiusi). **Restart Mac Mini eseguito in chiusura** per attivare
la nuova retention.

---

## S110e — NewsKeeper cleanup + retention — ✅ SHIPPED

Tre task, tutti chiusi (zero codice di trading toccato):

1. **NewsKeeper v1 è ridondante → spento.** Verificato che nessun consumer di
   produzione legge le righe v1: la dashboard pubblica filtra `polarity NOT NULL`
   (= solo v2, fix S105a), Sentinel/Sherpa non leggono affatto la tabella. v1
   **killato** sul Mac Mini (pid 3520+3522); v2 (il barometro che ha passato il
   verdetto) intatto.
2. **Retention `trend_scans` + `trend_decisions_log` 14gg → 90gg** (commit `6ef3acf`).
   Motivo: accumulare track record per il futuro clone TF Tier-3 (CASO 2). I dati
   ci sono (203 coin small-cap, tier C). Sostenibile: DB resta ~28% del free tier
   (500MB). Nessun impatto sul trading (la tabella è un log, mai riletta sull'hot path).
3. **Pulizia righe v1.** 3.182 righe (`polarity NULL`) **archiviate** in `audits/`
   (backup gitignored) e poi **cancellate**. Verifica finale: v1 = 0, v2 = 2.022 intatte.

   **Decisioni di Max:** (a) retention estesa anche a `trend_decisions_log`, non solo
   `trend_scans`; (b) **nessun** vincolo `NOT NULL` su `polarity` (più flessibile,
   riaccensione v1 possibile se mai servisse).

   **Bonus anti-drift:** il runbook di restart (`67b5148`) istruiva ancora a
   **rilanciare v1** ad ogni cold-start → l'avrebbe resuscitato. Corretto: v1 = RITIRATO.

---

## S110c — USDT → USDC — ⏸️ spiegato, RIMANDATO

Migrazione della valuta di conto da USDT a USDC (requisito MiCA, prerequisito go-live EU).
**Verifiche fatte (sola lettura):**
- I pair USDC **esistono già** su testnet (290) e mainnet (332), inclusi tutti e 4 i
  coin nostri (BTC/SOL/ETH/**BONK**). → migrazione fattibile e collaudabile sul testnet.
- "USDT" appare in ~86 righe nel codice bot (~20 file), 98 nelle dashboard, 52 negli
  script: **non** un find-replace innocuo (symbol hardcoded + lista stablecoin nello
  scanner TF).

**Rischio n.1:** liquidità BONK/USDC su mainnet (il pair esiste, ma il book potrebbe
essere più sottile di BONK/USDT). Da misurare prima di fidarsi.
**Raccomandazione CC:** parametrizzare la valuta-base in un punto solo, invece di
spargere "USDC" in 20 file. **Rimandato** da Max (task impattante). È un task da piano scritto.

---

## S110d — tf-grid exit thresholds — ✅ deciso + brief CORRETTO, esecuzione RIMANDATA

**Drift trovato:** il brief partiva da "oggi il TF non guarda il P&L". **Falso** —
verificato a DB + codice che le coin tf_grid hanno già 3 uscite P&L-aware attive:
DEALLOCATE-su-bearish (esce anche in perdita), SWAP con profit gate, Profit Lock +8%.
Quindi il task non è "aggiungere regole", ma **riconciliarle**.

**Decisioni Board + Max (2026-06-27):**
- **D1** Profit Lock → SOSTITUITO (disattivato); le nuove regole sono l'unico exit.
- **D2** soglia "in verde" = **netta** (copre le fee, ~+0.3-0.5%), non +0.1% lordo.
- **D3** "mai uscire in perdita" = **assoluto** (no paracadute; lo coprirà il Portfolio Guardian).
- **D4** sopra +5% = **let winners run**: si ruota solo per un upgrade vero, non si vende sempre.
- **D5** RUOTA e SWAP **unificati** (un solo meccanismo, riusa cooldown 48h + esclude la coin venduta).
- **D6** soglie come **parametri di `trend_config`** (hot-reload): cambiare es. 5%→8% in
  test = update DB, **nessun restart**.

**Risultato:** brief riscritto (`c232df3`) con implementazione **minimale** (gate verde-netto
sul dealloc + soglia rotazione parametrica + Profit Lock off + logging), non una riscrittura.
**Esecuzione rimandata** di qualche giorno. Non è un gate per la fase collaudo €100.

---

## Decisions log

- **DECISIONE:** spegnere v1 + cancellare le sue righe, senza constraint NOT NULL.
  **RAZIONALE:** v1 ridondante (v2 PASS), nessun lettore; constraint bloccherebbe
  un'eventuale riaccensione. **ALTERNATIVE:** constraint per sigillare (scartata, meno
  flessibile). **FALLBACK:** archivio JSONL in `audits/` per ripristino.
- **DECISIONE:** S110c/d rimandati, non eseguiti oggi. **RAZIONALE:** impattanti, sabato
  sera; S110d richiedeva prima decisioni di riconciliazione (prese). **FALLBACK:** brief
  pronti per esecuzione a mente fresca.
- **DECISIONE:** retention 90gg anche su `trend_decisions_log`. **RAZIONALE:** è il track
  record delle decisioni TF, più diretto degli scan grezzi. **FALLBACK:** reversibile (è solo un numero).

---

## Aperti per il CEO

- **S110c (USDC):** decidere quando eseguirlo + è legato alla scelta exchange (verificato
  solo Binance; Kraken da controllare). Rischio liquidità BONK/USDC da misurare.
- **S110d:** brief pronto; eseguibile nei prossimi giorni. Le soglie saranno tunabili a
  caldo (D6) durante il collaudo.
- **Retention:** attiva dal restart di oggi. Il DB cresce lentamente verso ~140MB a regime (90gg).

---

*Restart Mac Mini in chiusura sessione per attivare la retention 90gg — dettagli (PID/runtime) in PROJECT_STATE §1/§7.*
