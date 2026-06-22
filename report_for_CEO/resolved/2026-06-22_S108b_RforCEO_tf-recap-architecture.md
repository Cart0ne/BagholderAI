# Report for CEO — S108b — tf-recap-architecture

**Data:** 2026-06-22
**Brief sorgente:** `config/2026-06-20_S108b_brief_tf-recap-architecture.md`
**Commit:** `b701771` (solo documentazione, nessun codice toccato — da brief)
**Esito:** ✅ SHIPPED (2/2 deliverable)

---

## Deliverable

1. **`docs/tf_recap_S108.md`** — recap del Trend Follower per Max, in italiano
   accessibile, basato sui **valori LIVE** di `trend_config` (non i default del
   codice). Copre: cosa scansiona, classificazione segnali, indicatori, ALLOCATE
   vs HOLD + handoff TF→Grid, i parametri della dashboard, meta-parametri vs output
   (confine di proprietà Sherpa), stop-loss e greed decay.
2. **`docs/grid_mainnet_tf_testnet_assessment.md`** — assessment architetturale
   B1-B6 con verdetti verificati a codice.

---

## Risposta alla domanda del Board (Task 2)

> Possiamo andare live su **mainnet solo con i grid**, TF su testnet, insieme?

**Il go-live grid-only su mainnet NON è bloccato da nulla.** Il sistema *non*
supporta *as-is* grid-mainnet **+** TF-testnet **contemporaneamente**, perché oggi
l'ambiente (mainnet/testnet) è una scelta **unica per tutta la macchina**, non
per-bot.

- **Via semplice (zero codice, sblocca subito):** durante il mainnet spegnere il TF
  (`ENABLE_TF=false`). Il Grid gira pulito. — *Già prevista nell'auto-obiezione del
  brief.*
- **Via pulita (convivenza simultanea):** env per-processo nell'orchestrator (scope
  **basso**, abilita la separazione chiavi) + colonna `environment` in
  `trades`/`bot_config` + filtri nei lettori (scope **medio**). Una sessione dedicata.

| # | Tema | Verdetto |
|---|---|---|
| B1 | Chiavi API (env globale) | RICHIEDE MODIFICA |
| B2 | Supabase / `cycle` (no col. environment) | OK con cautela |
| B3 | `bot_config` per simbolo | RICHIEDE MODIFICA *(non BLOCCA)* |
| B4 | Env per-processo (`Popen` senza `env=`) | RICHIEDE MODIFICA — **scope basso** |
| B5 | Sentinel/Sherpa/NewsKeeper | OK |
| B6 | Report giornaliero (filtra per `cycle`) | RICHIEDE MODIFICA |

**Nessun "BLOCCA GO-LIVE".**

---

## Verifica adversariale dell'analisi automatica (valore aggiunto)

Il primo passaggio è stato fatto da un agente di ricerca; ho verificato a codice e
**corretto** diversi punti prima di consegnarli:
- **`scan_interval`**: il TF scansiona **ogni 30 minuti** (`0.5h` live), non ogni 4
  ore (l'agente leggeva il default del codice).
- **Fascia 3 spenta** (`tf_tier3_weight=0`): ogni allocazione TF diventa un handoff
  al Grid (`tf_grid`). Spiega "il TF non trada in proprio in questo ciclo".
- **Filtri di sicurezza ATTIVI** (distanza 12%, RSI-1h 75, cooldown 4h), non
  disabilitati.
- **Finding "BLOCCA GO-LIVE" su `bot_config` sovrastimato** → declassato a "richiede
  modifica, solo per la convivenza simultanea".
- **NewsKeeper esiste** (l'agente diceva di no): è in modalità shadow, non ancora
  cablato nelle decisioni di trading → neutro per la separazione.

---

## Note per il Board
- Implicazione strategica: il percorso mainnet **non ha prerequisiti tecnici
  bloccanti**. La decisione resta di mercato/Board (bear+bull+lateral, verdetto
  barometro ~23-giu), non di architettura.
- Greed decay live: TP **10%→7%→5%→3%** (avidità che decade nel tempo), SL fisso
  2,5%; le posizioni `tf_grid` usano la protezione del Grid (Profit Lock 8% +
  trailing 1,5/2%), non lo stop TF.

## Pendenze
Nessuna per S108b. Eventuale lavoro "via pulita" → brief separato se il Board
decide di tenere i due ambienti accesi insieme.
