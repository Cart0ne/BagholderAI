# Architettura: Grid su MAINNET + TF su TESTNET — Assessment — S108 (2026-06-22)

> Verifica tecnica richiesta dal Board (S108): possiamo andare live su **mainnet
> solo con i grid** (BTC/SOL/BONK), lasciando il **TF su testnet**,
> contemporaneamente sulla stessa macchina? Ogni punto sotto è **verificato a
> codice** (non inferito), con verdetto OK / RICHIEDE MODIFICA / BLOCCA GO-LIVE.

---

## Risposta in breve

**Il go-live grid-only su mainnet NON è bloccato da nulla.** Quello che il sistema
**non** supporta *as-is* è far girare **grid-mainnet e TF-testnet nello stesso
momento, sulla stessa macchina, sullo stesso database**. Il motivo di fondo è uno
solo: oggi **l'ambiente (mainnet vs testnet) è una scelta unica per tutta la
macchina**, non per singolo bot.

Due strade:
- **Via semplice (zero codice):** durante il periodo mainnet, **spegni il TF**
  (`ENABLE_TF=false`). Il Grid gira su mainnet pulito. Riaccendi il TF dopo. È la
  soluzione "bruta" già prevista nel brief — funziona oggi, subito.
- **Via pulita (richiede lavoro):** rendere l'ambiente una scelta *per-bot*. Scope
  complessivo **medio**, dettagliato sotto.

Nessun "BLOCCA GO-LIVE" assoluto: il finding più allarmante (collisione su
`bot_config`) si **aggira spegnendo il TF** e diventa rilevante solo se vuoi i due
ambienti accesi insieme.

---

## I 6 punti

### B1 — Chiavi API: separabili tra mainnet e testnet? → **RICHIEDE MODIFICA**
Oggi sia le chiavi (`BINANCE_API_KEY`/`BINANCE_SECRET`) sia il flag
testnet/mainnet (`BINANCE_TESTNET`) sono **variabili d'ambiente uniche per tutto il
processo** (`config/settings.py:26-28`). Quando un bot si connette a Binance, decide
testnet o mainnet con un'unica regola globale (`bot/exchange.py:32`). **Tutti i bot
avviati insieme usano lo stesso ambiente e le stesse chiavi.** Non c'è modo, oggi,
di dire "il Grid usa le chiavi mainnet, il TF quelle testnet".
→ Per separarli serve dare a ogni bot le proprie chiavi/ambiente (vedi B4).

### B2 — Supabase: i dati dei due ambienti si mescolerebbero? → **OK con cautela**
Le tabelle (`trades`, `bot_config`, `daily_pnl`, ecc.) hanno la colonna **`cycle`**
(es. `testnet_2`), introdotta col clean-slate S96a, e le query filtrano per ciclo.
Questo **separa bene cicli diversi dello stesso ambiente** (testnet_1 vs testnet_2).
**Ma non esiste una colonna `environment`** (mainnet/testnet): la distinzione
mainnet vs testnet oggi *non è rappresentata* nel database. Si potrebbe aggirare
codificandola nel nome del ciclo (`mainnet_1` vs `testnet_2`), ma è una toppa
fragile. → Per una separazione vera serve una colonna dedicata.

### B3 — bot_config: una riga per moneta, senza ambiente → **RICHIEDE MODIFICA**
*(l'analisi automatica iniziale lo segnava "BLOCCA GO-LIVE"; verificando, è
sovrastimato).* `bot_config` ha **una riga per moneta** e il codice la legge **per
simbolo, senza filtro ambiente**. Se il Grid gestisse BTC su mainnet e il TF
toccasse BTC su testnet, le due configurazioni si pesterebbero i piedi (una riga
sola per "BTC/USDT"). **Però:** se il TF è spento su mainnet (via semplice), il
problema non si presenta, perché un solo ambiente scrive `bot_config`. Quindi
**non blocca** il go-live grid-only — diventa un requisito solo per la convivenza
simultanea.

### B4 — Processi: possono avere ambienti diversi? → **RICHIEDE MODIFICA (scope basso)**
L'orchestrator avvia ogni bot come processo separato, ma **non passa variabili
d'ambiente personalizzate** (`bot/orchestrator.py:69,81,93,105`: le `Popen` non
hanno `env=`). Ogni figlio **eredita lo stesso ambiente del padre** → stesso
`BINANCE_TESTNET`, stesse chiavi. È **la radice tecnica** di B1/B3. La buona
notizia: il fix è piccolo — far passare all'orchestrator un set di variabili per
processo (es. al Grid `BINANCE_TESTNET=false` + chiavi mainnet, al TF
`BINANCE_TESTNET=true` + chiavi testnet). Poche righe.

### B5 — Sentinel / Sherpa / NewsKeeper: servono a entrambi? → **OK**
- **Sentinel** e **Sherpa** sono **indipendenti dall'ambiente**: leggono il regime
  di mercato reale e scrivono parametri ai grid. Funzionano per qualsiasi grid sia
  attivo. (Con TF spento su mainnet, Sherpa ottimizza solo il grid mainnet — nessuna
  ambiguità.)
- **NewsKeeper esiste eccome** (`bot/newskeeper/`, v1 + v2 barometro; girano come
  processi standalone — riavviati oggi dopo il blackout). Il loro output
  (`news_signals`/barometro) è oggi **in osservazione "shadow"**: scritto ma **non
  ancora cablato** nelle decisioni di trading. Quindi è **neutro** ai fini della
  separazione mainnet/testnet. *(Correzione: l'analisi automatica iniziale aveva
  erroneamente scritto che NewsKeeper "non esiste nel codebase".)*

### B6 — Report giornaliero: mescolerebbe i numeri? → **RICHIEDE MODIFICA (se due ambienti insieme)**
Il report combina Grid + TF in un unico portafoglio, ma **filtra per ciclo**
(`bot/grid_runner/daily_report.py:57-59`). Se i due ambienti avessero cicli distinti
non si mescolerebbero le righe. **Però** la funzione che decide "il ciclo corrente"
(`get_current_cycle`) restituisce **un valore globale**: il sistema è pensato per
**un ciclo/ambiente attivo alla volta**, non due in parallelo. Con TF spento su
mainnet il report è corretto senza toccare nulla.

---

## Tabella di sintesi

| # | Tema | Verdetto | Scope fix | Serve solo per…|
|---|---|---|---|---|
| B1 | Chiavi API | RICHIEDE MODIFICA | (dipende da B4) | convivenza simultanea |
| B2 | Supabase / cycle | OK con cautela | medio | separazione "vera" mainnet |
| B3 | bot_config per simbolo | RICHIEDE MODIFICA | medio | convivenza simultanea |
| B4 | Env per-processo | RICHIEDE MODIFICA | **basso** | convivenza simultanea |
| B5 | Sentinel/Sherpa/NewsKeeper | OK | — | — |
| B6 | Report giornaliero | RICHIEDE MODIFICA | medio | convivenza simultanea |

**Nessun BLOCCA GO-LIVE.**

---

## Raccomandazione

1. **Per andare mainnet adesso, grid-only:** spegni il TF (`ENABLE_TF=false`) per
   la fase mainnet. **Zero modifiche di codice, zero rischio di contaminazione.**
   È la strada che sblocca il go-live senza prerequisiti.
2. **Se in futuro vorrai i due ambienti accesi insieme** (Grid live + TF che
   continua a "studiare" su testnet), allora vale la pena fare il lavoro pulito, in
   quest'ordine di dipendenza:
   - **B4** (env per-processo nell'orchestrator) — è la chiave che abilita B1;
   - **colonna `environment`** in `trades` + `bot_config` + filtri nei lettori
     (copre B2/B3/B6);
   - test su una moneta prima di generalizzare.
   Scope complessivo: **medio**, una sessione dedicata. Non urgente: la via 1 copre
   il go-live.

> Bug/incoerenze trovate durante l'analisi (NON corrette, fuori scope — da brief
> separato se vorrai): vedi nota su `bot_config.cycle` stale post-reset
> (`allocator.py`, riga ~1139) segnalata dall'analisi automatica — è lo stesso tipo
> di problema che il fix allocator `8afa1b5` (S108) ha già affrontato per ETH.
