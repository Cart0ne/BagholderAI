# Report for CEO — Audit Area 1 + Area 2 (2026-07-29/30)

**Sessione:** intervento s/n (nessun brief CEO — richiesta diretta di Max in chat)
**Fonti:** `audits/reports/20260729_audit[A1].md` · `audits/reports/20260729_audit[A2].md`
(entrambi prodotti da task Cowork indipendenti, gitignored: in git va solo la sintesi)
**Commit:** `bd3ae1e` (sintesi A1) · `7f897c7` (compaction BUSINESS_STATE) · `7996e34` (sintesi A2) · `9159419` (fix L1+L2, **in attesa di ok Max per il push**)
**Restart bot:** nessuno. Zero file del bot toccati in tutta la sessione.

---

## 1. In una riga

Due audit indipendenti nello stesso giorno: **A1 tecnico APPROVED** (il sistema regge), **A2 coerenza CON RISERVE** con un solo finding che pesa — la narrazione pubblica dice ancora "nessun denaro reale" mentre il denaro reale gira da una settimana. Due dei tre finding minori sono chiusi; il terzo l'ha chiuso il Board con una decisione.

---

## 2. Audit Area 1 — integrità tecnica: **APPROVED**

Primo audit tecnico con denaro reale in esercizio. Passato pulito: **0 critical, 0 high, 0 medium, 2 low**.

| Check | Esito |
|---|---|
| Suite di test | 348/348 verdi su Python 3.13.14 (stessa versione dei bot → nessun falso verde) |
| Schema DB vs codice | 0 mismatch su 11 tabelle |
| Salute flotta | 5 grid attivi + 3 cervelli tutti freschi (<24h) |
| Segreti / import | 0 credenziali hardcoded, `compileall` exit 0 |
| Retention dati | allineata alla documentazione |

Le due riserve del 30 giugno sono chiuse: la retention di `newskeeper_signals` è a 90 giorni Board-confirmed, e le SELL BONK/USD fantasma non si ripresentano.

**Le 2 LOW:** un timeout di rete transitorio verso Binance in Sentinel (auto-recuperato al ciclo dopo), e il debito noto **62a** sulla non-atomicità del sell pipeline.

### 2.1 Verifica indipendente che ha allargato il quadro

L'audit guarda una finestra di 48 ore e ha visto **1 errore**. Ho allargato a 30 giorni: **10 errori**, tutti di rete/IO, nessuno di logica. Ma dentro c'è un episodio che la finestra corta non poteva vedere.

**23 luglio, 23:44 — sei errori in trenta secondi.** Sherpa, Sentinel e NewsKeeper insieme, tutti con "read operation timed out" in scrittura. Non sono tre guasti: è **Supabase che non ha risposto per mezzo minuto**, e tutti e tre i cervelli hanno sbattuto contro lo stesso muro.

Ho controllato il codice di scrittura ([store.py:61-71](../bot/newskeeper_v2/store.py#L61-L71), [main.py:158-178](../bot/sentinel/main.py#L158-L178)): **non c'è ritentativo**. La scrittura fallisce, viene loggata, si perde; il ciclo riparte dopo. In quei trenta secondi abbiamo perso un giro di punteggi Sentinel, un segnale NewsKeeper e una proposta Sherpa.

Su testnet è cosmetico. Con **Sherpa che ora guida il grid BTC/USD a denaro reale**, un ciclo perso è una decisione non presa. Non è un incendio — 0,03% del tempo su trenta giorni — ma è il tipo di fragilità che conviene chiudere *prima* di scalare il capitale, non dopo.

### 2.2 Due raccomandazioni dell'auditor che restano aperte

1. **Debito 62a** (non-atomicità del sell pipeline): l'auditor lo segnala come più pesante ora che muove soldi veri. **Verificato: non è nella MASTER_TASK_LIST.** Se lo si vuole prima della Fase 3, va messo a backlog o in un brief.
2. **Frequenza dei timeout**: da monitorare, insieme al punto 2.1 sopra.

---

## 3. Audit Area 2 — coerenza progetto: **CON RISERVE**

**0 critical, 1 high, 1 medium, 3 low, 8 osservazioni positive.**

Nota di processo, che l'auditor stesso mette in cima: questo audit **adempie in ritardo un gate obbligatorio**. `AUDIT_PROTOCOL §2(a)` dice che l'A2 è obbligatorio *prima* di ogni go-live con denaro reale. Il go-live è del 22 luglio; l'audit è del 29. Il gate non ha funzionato come cancello — ha funzionato come verifica a posteriori.

### 3.1 H1 — la narrazione pubblica non ha ancora recepito il denaro reale

Il finding è stato trovato **senza imbeccata** (scelta esplicita di Max: "lasciamo che lo scopra da solo"). E l'auditor l'ha inquadrato meglio di come l'avremmo posto noi: non punta sull'homepage o sui post, punta su **`/terms`** — la pagina legale:

> *"last updated · April 2026 · paper trading only"* — *"BagHolderAI is a paper trading experiment: **no real money is traded by our bots at this stage**."*

Verificato sul sito live: c'è ancora. È un'affermazione **assoluta, al presente**, sulla superficie dove l'accuratezza pesa di più. Il `TestnetBanner` ha `IS_TESTNET = true` hardcoded su tutte le pagine.

L'auditor riconosce che **non è una svista ma un rinvio deliberato**: cita il diary che dichiara il reveal tenuto in caldo per la Fase 3, e nota che il meccanismo esiste già costruito e spento (`DisclaimerGate`, flag `disclaimer_mode`). Quindi non contesta il rinvio — contesta il **wording assoluto** durante la finestra di attesa.

**Decisione del Board (Max, in sessione): si sistema quando si ufficializza tutto sul sito.** H1 resta aperto e agganciato al reveal della Fase 3. Non ho toccato né il banner né `/terms`.

### 3.2 M1 — non confermato

L'auditor riporta che il deploy pubblico è fermo al 18 luglio e che `/blog` serve un indice vecchio di due mesi con 7 post. **Verificato sul sito live: falso.**

- `/blog` elenca **14 link-post**, include `cost-to-build` del 23 luglio, che risponde **HTTP 200**
- il `BreadcrumbList` di `398c375` è presente su **tutte e 7** le pagine
- roadmap live v1.53/18-lug == sorgente (che nel repo è anch'essa v1.53 → nessun lag)

Il deploy è aggiornato. È un artefatto del ripiego metodologico dell'auditor, che dichiara lui stesso: Chrome non era disponibile e ha usato una fetch statica senza JavaScript. **Nessun redeploy né purge cache necessari.**

La lezione è quella che ci ha già morso in senso opposto (S-redesign, "mai fidarsi di `x-vercel-cache: HIT`"): **una fetch statica non è prova di staleness, in nessuna delle due direzioni.**

Nota collaterale: anche un pezzo di L1 era stale. L'auditor segnalava il sottotitolo *"(Sentinel/Sherpa shadow-only)"*; sul sito live c'è scritto *"advise live"* — già corretto in una sessione precedente.

### 3.3 L1 — **RISOLTO** (`9159419`)

Chi apriva `/dashboard` **senza JavaScript** — e questo include una parte di crawler e scraper — non vedeva i dati veri (che arrivano da Supabase via JS): vedeva un set di **numeri inventati fermi al 27 maggio**. Net worth `$557,42`, `May 27`, e nel log del CEO `Day 34` con voci di fine aprile.

Erano numeri nati per riempire il layout in fase di prototipazione. Nel file c'era anche il piano di manutenzione: *"AUDIT NOTE (S88): refresh this mock baseline at every minor site release"*.

**DECISIONE:** non rinfrescare il mock — smettere di server-renderizzare cifre.
**RAZIONALE:** il piano "aggiorna a ogni release" **ha già fallito** (due mesi di drift). Rinfrescare oggi rimette solo il cronometro a zero e ci riporta qui al prossimo audit. I placeholder non possono invecchiare.
**ALTERNATIVE CONSIDERATE:** (a) rinfrescare i numeri → tapis roulant, scartata; (b) rendere i dati veri a build-time → invecchiano tra un deploy e l'altro e legano il build al DB, scartata.
**COME SI TORNA INDIETRO:** revert di un commit su un solo file; il mock è ancora in `dashboard-mock.ts`, intatto.

Ogni cifra della pagina ora esce come placeholder (`—` / `…`) e la riempie il JavaScript da Supabase — **è la convenzione che la §2 della stessa pagina usava già** (`<span id="grid-nw">—</span>`). Chi ha JS non nota differenza. Aggiunto un blocco `<noscript>` che spiega perché si vedono trattini: *"we'd rather show you nothing than show you stale numbers"*.

### 3.4 L2 — **RISOLTO** (`9159419`)

La homepage etichettava **Sherpa "TEST"** e la coppia Sentinel × NewsKeeper **"DUO · LOCKED"**, mentre `/dashboard` li dava "live". Verificato sul processo vivo: `SHERPA_MODE=live`, Sherpa scrive i 7 parametri dal S102b e oggi guida il grid Kraken a denaro reale. "TEST" era semplicemente falso.

Entrambe le card ora sono **LIVE**. Sul sottotitolo della Watchtower ho chiesto a Max come procedere, perché i tre cervelli **non sono nello stesso stato**:

- **Sherpa** live e comanda
- **Sentinel** live e consumato da Sherpa
- **NewsKeeper v2** vivo ma **non cablato in Sentinel** — zero riferimenti a `newskeeper` in `bot/sentinel/`: il barometro resta shadow

Scrivere "LIVE" secco sulla card della coppia sarebbe stato vero per metà. **Scelta del Board: LIVE + sottotitolo, senza separare le card.** Il sottotitolo ora dice *"Sentinel × NewsKeeper · early warning · barometer still shadow"* — la stessa grammatica che `/dashboard` già usa (pallino "live" + pill separata "barometer · shadow").

**Nessun impatto su H1:** dire "Sherpa live" non rivela il denaro reale — Sherpa è live su testnet da mesi e la dashboard lo dichiara già. Banner e `/terms` intatti, il reveal resta interamente da giocare.

### 3.5 L3 — **chiuso per decisione del Board**

L'auditor l'aveva classificato LOW, "nota editoriale": il post sul backtest dice *"the fees are Kraken's real ones, 0.40% per trade"* mentre la fee vera è 0,80%.

Sono andato a vedere il codice, e il problema non era nella prosa: [params.py:107-108](../scripts/backtest/params.py#L107-L108) **hardcoda** `FEE_KRAKEN_TAKER = 0.004` marcato "PRIMARY" e maker a 0,25% — il **listino Kraken vecchio**, quello già smentito in S117 da due fonti indipendenti e confermato dal fill reale a 0,7999%.

Quindi il numero sbagliato era nel **codice che ha prodotto i grafici**: tutta quell'analisi ha girato a metà del costo reale, e nella direzione che **favorisce il grid** (su una strategia ad alta frequenza di trade la fee è il costo dominante). Il post lo presentava pure come prova di rigore — "quattro volte quello che pagavamo sul testnet": in realtà è otto volte.

Per onestà va detto anche il rovescio: **questo non ribalta il verdetto S113.** Il grid era già stato giudicato ammortizzatore e non motore; a fee doppia peggiora, non migliora. L'errore non ha nascosto un fallimento — ha reso un risultato mediocre un po' meno mediocre.

**Decisione del Board (Max): non interessa.** *"Basta backtest, ormai giochiamo con soldi veri e testiamo sul futuro."* Riclassificato 🟠 e lasciato tracciato in PROJECT_STATE §5 come debito noto, non come task. `params.py` non è stato corretto: se qualcuno rigirasse quel tooling in futuro, ripartirebbe dalla fee sbagliata.

---

## 4. Compaction BUSINESS_STATE (autorizzata in sessione)

Il file era a **59 KB**, sopra il trigger di 50 e fuori dalla tolleranza di 52. Su autorizzazione esplicita di Max: **59 KB → 36 KB**, 91 righe rimosse, **tutte archiviate integralmente** in `audits/BUSINESS_STATE_archive.md` con verifica automatica "0 righe perse" (ogni riga non vuota dell'originale è nel file nuovo o nell'archivio).

Tagliato: decisioni §4 del 1° luglio e precedenti (tenendo le portanti ancora in vigore — verdetto grid=ammortizzatore, USD+lineup Kraken, allocazione €600, ownership Board/Sherpa), domande CC già chiuse, vincoli scaduti, voci §7 superate dal go-live, e una riga duplicata in §5.

**Cosa NON ho fatto:** riscrivere contenuti. Restano frasi stale post-S122 in §2/§3/§6/§7 — territorio CEO, segnalate nell'header del file.

**Segnalazione onesta, perché tocca l'audit A2:** la compaction ha rimosso da §7 alcune righe che erano stale nella direzione giusta — *"Fase 2b ferma"*, *"Cutover Kraken — Fase 2a in corso"*, *"€100 reali: gate Board"* — cioè esattamente il tipo di drift che l'Area 2 caccia. Era compaction legittima (voci superate), ma il risultato è che su quel file l'auditor ha trovato meno di quanto avrebbe trovato qualche ora prima. Restano tutte leggibili nell'archivio, che **è tracciato in git** a differenza dei report.

---

## 5. Decisions

**DECISIONE:** non rinfrescare il mock della dashboard, smettere di server-renderizzare cifre.
**RAZIONALE:** il piano di manutenzione "refresh a ogni release" era già fallito con due mesi di drift; i placeholder non invecchiano.
**ALTERNATIVE CONSIDERATE:** rinfrescare i numeri; server-renderizzare i dati veri a build-time.
**FALLBACK SE SBAGLIATA:** revert di un commit, un solo file; il mock è intatto.

**DECISIONE:** riclassificare L3 da LOW a 🟠 contro il giudizio dell'auditor.
**RAZIONALE:** l'auditor ha letto solo la prosa del post; la fee sbagliata è nel codice che ha prodotto i risultati, quindi non è un errore editoriale ma un difetto dell'analisi.
**ALTERNATIVE CONSIDERATE:** accettare il LOW e chiudere.
**FALLBACK SE SBAGLIATA:** è una riga di documentazione in §5, nessun codice cambiato.

**DECISIONE:** registrare M1 come "non confermato" invece di eseguire la remediation richiesta.
**RAZIONALE:** verifica diretta sul sito live smentisce entrambe le componenti del finding; un redeploy+purge avrebbe "risolto" un problema inesistente e lasciato in §9 la traccia di un guasto mai avvenuto.
**ALTERNATIVE CONSIDERATE:** eseguire il redeploy per scrupolo.
**FALLBACK SE SBAGLIATA:** se `/blog` risultasse davvero stale a qualcuno, redeploy+purge restano un'operazione di due minuti.

---

## 6. Sul tavolo del CEO

| # | Cosa | Stato |
|---|---|---|
| 1 | **H1 — reveal o softening di `/terms`** | Agganciato all'ufficializzazione sul sito (decisione Max). Finché è in hold, la pagina legale afferma una cosa falsa |
| 2 | **Debito 62a a backlog?** | Non è nella MASTER_TASK_LIST. L'auditor A1 lo raccomanda prima dello scaling capitale di Fase 3 |
| 3 | **Nessun ritentativo sulle scritture dei cervelli** | Emerso dalla mia verifica a 30 giorni, non dall'audit. Con Sherpa al volante del denaro reale, un blip del DB = una decisione non presa |
| 4 | **Audit Area 3 in scadenza** | Ultimo 2 luglio; cadenza mensile → dovuto verso il 1° agosto |
| 5 | **Frasi stale in BUSINESS_STATE §2/§3/§6/§7** | Territorio CEO, non le ho riscritte |

---

## 7. Cosa non è stato fatto e perché

Non ho toccato `TestnetBanner` né `/terms` (H1 = decisione strategica di Max, agganciata al reveal). Non ho corretto `params.py` né il post sul backtest (L3 = Board dice basta backtest). Non ho eseguito il redeploy che l'auditor chiedeva per M1 (finding non confermato). Non ho riscritto i contenuti di BUSINESS_STATE (territorio CEO). Nessun restart dei bot: la sessione non ha toccato un solo file del bot, la flotta gira ancora sul codice che l'audit A1 ha certificato.

Il commit `9159419` con i fix L1+L2 è **locale, non pushato**, in attesa dell'ok di Max — il push fa deploy sul sito pubblico.
