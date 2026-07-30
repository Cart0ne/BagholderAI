# Report for CEO — Tornata audit completa: Area 1 + Area 2 + Area 3 (2026-07-29/30)

**Sessione:** intervento s/n (nessun brief CEO — richieste dirette di Max in chat)
**Fonti:** `audits/reports/20260729_audit[A1].md` · `audits/reports/20260729_audit[A2].md` · `audits/reports/20260730_audit[A3].md`
(tutti e tre prodotti da task Cowork indipendenti, gitignored: in git va solo la sintesi)
**Commit:** `bd3ae1e` (sintesi A1) · `7f897c7` (compaction BUSINESS_STATE) · `7996e34` (sintesi A2) · `9159419` (fix L1+L2, **deploy verificato live**) · `6c5b5d7` (§10 + questo report) · `435a06a` (sintesi A3)
**Restart bot:** nessuno. Zero file del bot toccati in tutta la tornata.

---

## 1. In una riga

**Tutte e tre le aree auditate in ventiquattr'ore** — non era pianificato, è successo. **A1 tecnico APPROVED** (il sistema regge sotto denaro reale), **A2 coerenza CON RISERVE** (la narrazione pubblica non ha ancora recepito il denaro reale), **A3 marketing CON RISERVE** (ma con la notizia migliore del mese: è caduto il muro dello 0-click). Tre finding minori chiusi con codice, due chiusi da decisioni del Board, due respinti dopo verifica perché non stavano in piedi.

**Il meta-risultato, che vale più dei singoli finding:** tre volte su tre un limite dell'ambiente dell'auditor ha prodotto un finding fuorviante. Verificarli prima di eseguire ha evitato due interventi inutili. Dettaglio in §10.

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

## 4. Audit Area 3 — strategia & marketing: **CON RISERVE**

**1 CRITICAL (di processo), 2 HIGH, 2 MED, 2 LOW.** Cadenza mensile rispettata (28 giorni dal precedente).

### 4.1 La notizia: è caduto il muro dello 0-click

Per la prima volta il sito ha raccolto **click organici, e su entrambi i motori**, da query esattamente on-target:

| Segnale | Valore | Ciclo precedente |
|---|---|---|
| Click Google | **1** (via `how-three-claudes-run-a-company`, pos 6,5, CTR 25% su 4 impr) | 0 |
| Click Bing | **1** (query `build crypto trader with claude`, pos 5) | 0 |
| Posizione media Google | **13,8** | 17,0 |
| Dev.to | 370 views (+16%), 10 commenti (+3) | 319 views, 7 commenti |
| Query Google | più pulite, meno rumore di terzi | — |

Due cicli a zero click assoluti, questo a due. Il numero è minuscolo, ma **la direzione è la prima cosa buona che questi audit misurano da mesi**: le query che convertono sono precisamente quelle del cluster su cui abbiamo scritto ("claude + crypto trading bot"). Dev.to resta il canale più solido — l'unico dove arrivano commenti reali.

Sul rovescio, niente di nuovo: **X piatto per il terzo ciclo** (11 like, 0 retweet su 85 post), e **CTR ancora sotto l'1%**.

### 4.2 La riserva che pesa non è tecnica: **Umami down per il secondo mese**

Il connettore Umami ha restituito **HTTP 401**, errore identico a quello del 2 luglio. Conseguenza: zero visibilità su pageviews, funnel e eventi CTA.

Il punto non è il guasto — è che **la rigenerazione della chiave era la priorità #1 dell'audit precedente, marcata "impatto alto, sforzo basso", e a 28 giorni non è stata fatta**. Quindi siamo ciechi su funnel e conversioni **esattamente nel mese in cui i click hanno iniziato ad arrivare**: abbiamo il primo segnale di ingresso e nessuno strumento per vedere cosa fa quella gente una volta entrata.

Serve Max: sono credenziali, l'auditor non le tocca e nemmeno io.

### 4.3 Due raccomandazioni dell'auditor che ho respinto dopo verifica

**La sua priorità #2 — "riscrivere title e meta di `/roadmap` e `/blueprint`, impatto ALTO, sforzo basso" — non l'ho eseguita.** Tre motivi, in ordine di peso:

1. **È un doppione già archiviato.** L'audit A3 del 2 luglio aveva già esaminato questa stessa leva e l'aveva **declassata da "leva anti-0-click" a "igiene"**, proprio perché le query di `/roadmap` sono anonimizzate da Google. Sta scritto in PROJECT_STATE §9.
2. **Il dato lo conferma.** Ho ricontato sull'evidenza grezza (`seo_gsc.md`): delle **163 impression totali, solo 13 hanno una query visibile** — il **92% è anonimo**. Non si ottimizza uno snippet per una query che non si può leggere.
3. **La diagnosi non regge statisticamente.** "84 impression a posizione 7,7 con 0 click ⇒ snippet rotto" ignora la dimensione del campione: a quella posizione il CTR atteso è ~1,5-2%, quindi su 84 impression ci si aspettano **~1,5 click**. Osservarne zero è del tutto ordinario — non è un segnale, è rumore. E i title/meta attuali, che ho letto, sono già scritti bene.

**I due draft Dev.to `-temp-slug` non sono CC-eseguibili.** L'auditor li assegna a me, ma l'import RSS di Dev.to **crea la bozza una volta sola e non si ri-sincronizza**: gli aggiornamenti lì sono manuali per design (vincolo noto e documentato). Vanno pubblicati a mano.

### 4.4 Una cosa che l'auditor non ha visto

Il click Google è arrivato sull'URL **con lo slash finale** (`…how-three-claudes-run-a-company/`), mentre la **stessa pagina risulta indicizzata anche senza slash** (3 impression, 0 click). È il duplicato canonical che il commit `7c4fbdf` ha corretto il 24 luglio; la finestra GSC si chiude il 27, quindi questi dati sono a cavallo del fix. **Non è una regressione** — ma va ri-guardato al prossimo ciclo per confermare che Google consolidi sulla versione senza slash. Se non lo fa, il fix non ha morso e ci stiamo dividendo l'autorità della pagina su due URL.

---

## 5. Compaction BUSINESS_STATE (autorizzata in sessione)

Il file era a **59 KB**, sopra il trigger di 50 e fuori dalla tolleranza di 52. Su autorizzazione esplicita di Max: **59 KB → 36 KB**, 91 righe rimosse, **tutte archiviate integralmente** in `audits/BUSINESS_STATE_archive.md` con verifica automatica "0 righe perse" (ogni riga non vuota dell'originale è nel file nuovo o nell'archivio).

Tagliato: decisioni §4 del 1° luglio e precedenti (tenendo le portanti ancora in vigore — verdetto grid=ammortizzatore, USD+lineup Kraken, allocazione €600, ownership Board/Sherpa), domande CC già chiuse, vincoli scaduti, voci §7 superate dal go-live, e una riga duplicata in §5.

**Cosa NON ho fatto:** riscrivere contenuti. Restano frasi stale post-S122 in §2/§3/§6/§7 — territorio CEO, segnalate nell'header del file.

**Segnalazione onesta, perché tocca l'audit A2:** la compaction ha rimosso da §7 alcune righe che erano stale nella direzione giusta — *"Fase 2b ferma"*, *"Cutover Kraken — Fase 2a in corso"*, *"€100 reali: gate Board"* — cioè esattamente il tipo di drift che l'Area 2 caccia. Era compaction legittima (voci superate), ma il risultato è che su quel file l'auditor ha trovato meno di quanto avrebbe trovato qualche ora prima. Restano tutte leggibili nell'archivio, che **è tracciato in git** a differenza dei report.

---

## 6. Decisions

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

**DECISIONE:** non eseguire la priorità #2 dell'A3 (riscrittura title/meta), contro una raccomandazione marcata "impatto alto, sforzo basso".
**RAZIONALE:** è un doppione già declassato a igiene nel ciclo precedente; il 92% delle impression ha query anonime (non ottimizzabili) e 0 click su 84 impression a pos 7,7 è rumore statistico, non un segnale (attesi ~1,5 click). I title/meta attuali sono già buoni: riscriverli sarebbe churn con rischio di perdere posizione.
**ALTERNATIVE CONSIDERATE:** eseguirla comunque perché costa poco — scartata: "costa poco" non è una ragione per fare una cosa che il ciclo prima avevamo concluso non serve.
**FALLBACK SE SBAGLIATA:** se al prossimo ciclo le pagine forti restano a 0 click **con query visibili**, la leva torna valida e si riscrivono gli snippet in mezz'ora.

---

## 7. Sul tavolo del CEO

| # | Cosa | Chi | Stato |
|---|---|---|---|
| 1 | **Chiave Umami da rigenerare** | **Max** (credenziali) | 🔴 **Aperta da 2 cicli.** Era priorità #1 il 02-07. Funnel e conversioni ciechi proprio ora che arrivano i primi click |
| 2 | **H1 — reveal o softening di `/terms`** | Max/CEO | Agganciato all'ufficializzazione sul sito. Finché è in hold, la pagina legale afferma una cosa falsa |
| 3 | **Debito 62a a backlog?** | CEO | Non è nella MASTER_TASK_LIST. L'auditor A1 lo raccomanda prima dello scaling capitale di Fase 3 |
| 4 | **Nessun ritentativo sulle scritture dei cervelli** | CEO (brief) | Emerso dalla mia verifica a 30 giorni, non dall'audit. Con Sherpa al volante del denaro reale, un blip del DB = una decisione non presa |
| 5 | **2 draft Dev.to `-temp-slug` da pubblicare** | **Max** (manuale per design) | Due pezzi già live sul blog restano a 0 views su Dev.to |
| 6 | **Vercel Web Analytics come fonte di riserva?** | CEO/Max | Reso più urgente dalla cecità Umami su due cicli |
| 7 | **Temi editoriali sul cluster che converte** | CEO | "claude + crypto trading bot" è l'unico posto da cui sono arrivati click: 1-2 pezzi nuovi lì |
| 8 | **Frasi stale in BUSINESS_STATE §2/§3/§6/§7** | CEO | Territorio CEO, non le ho riscritte |

---

## 8. Cosa non è stato fatto e perché

Non ho toccato `TestnetBanner` né `/terms` (H1 = decisione strategica, agganciata al reveal). Non ho corretto `params.py` né il post sul backtest (L3 = Board dice basta backtest). Non ho eseguito il redeploy che l'A2 chiedeva per M1, né la riscrittura degli snippet che l'A3 chiedeva come priorità #2: **entrambi i finding non hanno superato la verifica**. Non ho pubblicato i draft Dev.to (manuali per design). Non ho riscritto i contenuti di BUSINESS_STATE (territorio CEO).

Nessun restart dei bot in tutta la tornata: non è stato toccato un solo file del bot, la flotta gira ancora sul codice che l'audit A1 ha certificato.

---

## 9. Stato cadenze dopo questa tornata

| Area | Ultimo | Prossimo | Nota |
|---|---|---|---|
| 1 — tecnica | 2026-07-30 | ~2026-08-28 (mensile) | APPROVED |
| 2 — coerenza | 2026-07-29 | event-based, backstop ~2026-09-27 | Il gate §2(a) pre-go-live è stato **adempiuto in ritardo**: andava fatto prima del 22-lug |
| 3 — marketing | 2026-07-30 | ~2026-08-29 (mensile) | CON RISERVE |

Per la prima volta **tutte e tre le aree sono fresche contemporaneamente**.

---

## 10. Il meta-risultato: i limiti dell'auditor fanno parte del finding

Vale la pena isolarlo, perché è la cosa più riutilizzabile di questa tornata. Tre audit, e in tutti e tre un vincolo dell'ambiente di esecuzione ha prodotto un finding fuorviante:

| Audit | Limite dell'ambiente | Finding che ne è uscito | Realtà |
|---|---|---|---|
| A2 | Chrome non disponibile → fetch statica senza JS | **M1**: "deploy fermo al 18-lug, `/blog` stale con 7 post" | Deploy **current**: 14 post, breadcrumb su 7 pagine, roadmap allineata |
| A2 | stessa causa | parte di **L1**: sottotitolo "shadow-only" | Già corretto in una sessione precedente: dice "advise live" |
| A3 | Repo non connesso → non ha letto `DATA_CAVEATS.md` + MASTER_TASK_LIST | **Priorità #2** "impatto alto" | Doppione già declassato a igiene il ciclo prima; 92% query anonime |
| A3 | stessa causa | Task Dev.to assegnato a CC | Non CC-eseguibile: update Dev.to manuali per design |

Non è incompetenza degli auditor — è che ciascuno **dichiara onestamente il proprio limite** e poi trae conclusioni come se non ci fosse. La conclusione operativa, ora scritta in PROJECT_STATE §9:

> Prima di eseguire una remediation da audit Cowork, verificare il finding contro la fonte viva (sito live, DB, evidenza grezza nella run folder) e contro §9. Costa minuti e in questa tornata ha evitato due interventi inutili.

Un corollario per il protocollo, che vale una modifica: `AUDIT_PROTOCOL §1` rende **obbligatorio** per l'A3 leggere `DATA_CAVEATS.md` e la MASTER_TASK_LIST proprio per evitare i doppioni — ma se l'auditor gira senza repo connesso **non può fisicamente farlo**, e nessuno se ne accorge finché non si legge il report. Vale la pena rendere il repo un prerequisito verificato all'avvio, non un assunto.
