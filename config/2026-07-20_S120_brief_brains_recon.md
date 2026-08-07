Brief S120 — brains_recon — 2026-07-20

**Tipo:** RICOGNIZIONE — **read-only**. Zero codice, zero refactor, zero restart, zero modifiche a `bot_config`/`trades`. Solo lettura del codice + risposte documentate con path e numero di riga.
**Da:** CEO · **Per:** CC (Intern) · **Esegue:** CC nei prossimi giorni (non urgente, TF non è bloccante per il collaudo Grid).
**Contesto:** stiamo per collaudare il Grid con denaro reale ($100 → $500); **TF si collauda solo dopo**. Prima di disegnare come Sentinel/NewsKeeper/Sherpa/TF si interfacciano, serve sapere **cosa è già cablato oggi**. Non progettare nulla: rispondi solo ai fatti. Il design lo fanno Board + CEO dopo questa ricognizione.

---

## Regola d'ingaggio (importante)

- **NON toccare codice.** Nessun commit, nessun branch, nessun test nuovo. Se ti accorgi di un bug, **annotalo e basta** — non fixarlo in questo giro.
- **Ogni risposta va ancorata a `file:riga`.** Se una cosa non è determinabile dal codice, scrivi **"undeterminato"** con il motivo. Non inferire, non "presumere che". (Anti-invention: vale per te come per il CEO.)
- **Report di risposta** con SCOPE identico: `report_for_CEO/2026-07-XX_S120_RforCEO_brains_recon.md`.
- **Obiezione tecnica obbligatoria** (anti-assenso): se una delle 3 domande è mal posta o presuppone qualcosa di falso, dillo prima di rispondere.

---

## Le 3 domande fattuali

### Q1 — Sherpa tocca le righe `managed_by='tf_grid'`?
Oggi Sherpa modula i parametri delle righe Grid. **Domanda:** modula anche le righe `tf_grid` (es. ETH/USDT su `testnet_2`)?
- **a)** Nel loop di Sherpa, la selezione delle righe da modulare filtra per `managed_by`? Quali valori include/esclude? (`file:riga`)
- **b)** Se sì: quali colonne di `bot_config` scrive su una riga `tf_grid` (es. `buy_pct`, `sell_pct`, `capital_per_trade`…), con quale cadenza/trigger?
- **c)** Se no: le righe `tf_grid` restano a **parametri statici**? Confermalo dal codice (non dal fatto che i valori "sembrano" fermi nei dati).

### Q2 — "Greed decay sell" è tempo-based o regime-based?
Nei `trades` ETH `tf_grid`, ogni vendita ha `reason` tipo:
`"Greed decay sell: check $X >= avg cost $Y * (1 + 2.5%) (age NNNNNmin, tier 2.5%)"`.
- **a)** Dov'è implementata questa logica? (`file:riga`) Come si chiama la funzione/tier.
- **b)** Il "decay" dipende dall'**età della posizione** (age in minuti), dal **regime Fear & Greed**, o da **entrambi**? Mostra la variabile che guida il tier (`file:riga`).
- **c)** Il valore F&G / lo stato Sentinel **entra** in questa formula, sì o no? Se sì, dove; se no, confermalo.

> Perché conta: il Board immagina una modulazione della **cadenza dei lotti guidata dal regime** (fear → più
> pazienza sui buy; greed → più pazienza sui sell). Dobbiamo sapere se "greed decay" **è già** questa cosa, o è
> un meccanismo diverso (tempo puro) che il modello mentale del Board sta scambiando per regime.

### Q3 — Sentinel e NewsKeeper scrivono da qualche parte che Grid/TF leggono?
- **a) Sentinel:** dove pubblica il suo output (tabella Supabase? file? variabile in memoria?). Quali processi lo **leggono** oggi? Sherpa lo legge? Grid/TF lo leggono **direttamente** (bypassando Sherpa)? (`file:riga` per ogni lettore)
- **b) NewsKeeper:** stessa domanda. Dove scrive il suo output; **qualcuno lo legge** oggi, o è standalone-solo-log? (Memoria CEO: NewsKeeper è LIVE ma NON wired a Sentinel, NON orchestrator-managed — **conferma o smentisci dal codice**, non darlo per buono.)
- **c) Mappa 1 riga:** disegna il flusso reale attuale, es. `Sentinel → [tabella X] → Sherpa → bot_config → Grid` e, separatamente, dove sta (o non sta) TF e dove sta (o non sta) NewsKeeper.

---

## Cosa NON ti sto chiedendo (per evitare scope creep)
- ❌ Non progettare la catena di autorità / il wiring futuro. Quello è design Board+CEO, **dopo** questo report.
- ❌ Non validare i filtri EMA/RSI di TF (brief separato, `excess vs hold`).
- ❌ Non toccare il filtro-universo TF né la soglia `> X`. (Se durante la lettura **incontri** quella soglia e la
  sua metrica — market cap vs volume — annotala come bonus, ma non è il compito.)

---

## Auto-obiezione del CEO (dovuta)
Obiezione a questo brief: "già che CC apre il codice, fagli anche proporre l'architettura, si risparmia un giro."
**Respinta.** Non vogliamo che CC progetti mentre Board+CEO non conoscono ancora lo stato reale: torneremmo a
reagire al suo design invece di guidarlo. Prima i fatti (questo brief), poi il design (Board+CEO), poi
l'implementazione (brief separato per CC). Tenere i tre stadi separati È il punto.

---

## Consegna
Report `report_for_CEO/2026-07-XX_S120_RforCEO_brains_recon.md` con: risposte Q1/Q2/Q3 ancorate a `file:riga`,
la mappa-flusso del §Q3c, eventuali "undeterminato" motivati, e la tua obiezione tecnica se il brief zoppica.
Nessun'altra azione.
