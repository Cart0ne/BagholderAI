# BUSINESS_STATE.md

**Last updated:** 2026-09-28 (S131) — basato su `config/MASTER_TASK_LIST_2026-09-28.md` (S130) e report A.1 (`report_for_CEO/2026-09-28_S130_RforCEO_analisi-strategia-A1.md`). §3 e §7 sostituite; §4 +7 decisioni S131, tenute le 15 più recenti (45 righe archiviate integralmente in `audits/BUSINESS_STATE_archive.md`); §5 +4 domande. Contenuti = CEO (`config/2026-09-28_S131_BUSINESS_STATE_update.md`), conversione in tabella + merge + git = CC. · Prec.: 2026-08-09 — **S125 chiusa + Volume 4 chiuso come prodotto**. §4 sostituita col blocco CEO del 09-ago (`config/2026-08-09_S125_business_state_update.md`), che **rimpiazza integralmente** quello del 07-ago: quello conteneva una premessa errata e non copriva esecuzione, reveal, né il primo ciclo autonomo dell'8 agosto. §3 diary, §5, §6, §7 aggiornate dallo stesso blocco. Contenuti = CEO; merge e git = CC (§2b). §4 +15 righe, §5 nodo 5 CHIUSO, §6 aggiornato. ⚠️ **Scritto da CC su richiesta esplicita di Max** (deroga alla regola CLAUDE.md §2b "contenuti = CEO"): la fonte è il blocco CEO `config/2026-08-07_S125_business_state_update.md`, **con una correzione dichiarata** — l'aggravante *"la homepage mostra tutti zeri"* era un artefatto di lettura senza JavaScript, non un fatto (dettaglio nella prima riga §4). Il resto delle righe CEO è recepito; aggiunte da CC le decisioni emerse in esecuzione (sicurezza scritture, debito riconciliazione, XRP, guidelines v3). · Prec.: 2026-07-22 — S122 (Fase 2b GO-LIVE Kraken, denaro reale). §4 +5 (Opzione B confermata, proxy volatilità Binance /USDT, fee-drag A, restart unico, CMC scartata), §5 +3 (CMC-Sentinel, tf.html, orchestrator-poll RISPOSTO), §3 diary S122 BUILDING — contenuti CEO (`config/BUSINESS_STATE_update_S122.md`), merge+git CC (§2b). ✅ **COMPACTION ESEGUITA 2026-07-29** (CC, su autorizzazione esplicita di Max): 59KB → **35KB**, 91 righe rimosse da §2/§4/§5/§6/§7 (decisioni ≤2026-07-01 non più portanti, domande CC chiuse, vincoli scaduti, voci §7 superate dal go-live 2b) — **tutte archiviate integralmente** in `audits/BUSINESS_STATE_archive.md`, verifica automatica "0 righe perse". ⚠️ **Per il CEO**: la compaction NON riscrive i contenuti — restano da rinfrescare a mano diverse frasi stale post-S122 in §2/§3/§6/§7 (territorio CEO). · Prec.: 2026-07-17 — S119 chiusura (primo ordine reale su Kraken; indagine S119b; nodo 5 rinviato a pre-2b). §2 +marketing (primo click Google), §3 S119 COMPLETE, §4 +7 righe, §5 +1, §6 +2, §7 +2 — su istruzione CEO (brief S119c) via Max. Cap file 50KB ±2KB (CLAUDE.md §2b). Cadenze audit canoniche in PROJECT_STATE §9. **Corr. tecnica 2026-07-20 (CC, aut. Max):** trigger SELL Kraken §4/§6 $65.271→**$66.314** (formula fee-buffered `grid_bot.py:876`, non avg×1,02 — dettaglio PROJECT_STATE §5). Prec.: 2026-07-13 — S119 Fase 2a/2b split + venue=binance (via Max); 2026-07-11 — S117 (chiavi Kraken + Fase 0 18/18; fee 0,80% tier-0).
**Updated by:** CEO (S122 via `config/BUSINESS_STATE_update_S122.md`, merge+git CC)
**Basato su:** PROJECT_STATE.md corrente + `report_for_CEO/2026-07-16_S119_RforCEO_kraken-fase2a.md` + `report_for_CEO/2026-07-17_S119b_RforCEO_kraken-replay-avg-reconcile.md`

> 📍 **Dove vive cosa** (per CEO e CC): [KNOWLEDGE_MAP.md](KNOWLEDGE_MAP.md) in root del repo indicizza tutti i doc durevoli — stato, playbook, runbook, architettura, archivi, e cosa è gitignored.

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 11 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, blog, income, terms, privacy).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

### S125 — annuncio denaro reale (09-ago)
- **Annuncio "denaro reale" pubblicato su X + Substack Notes il 9 agosto**, con **carosello a 4 slide** — primo contenuto visivo costruito su dati reali (concept: tabella §4 di `/history`, *"what one order costs"*). Testo IT di Max, traduzione fedele del CEO, nessun link. Dettaglio + correzioni CEO al carosello nel marketing tracker (community log 2026-08-09). *(Riga dal blocco CEO `2026-08-09_marketing_tracker_update.md`, inserita da CC il 2026-09-16 su richiesta di Max.)*

### S119 — primo denaro reale + segnale distribuzione (17-lug)
- **Primo click organico da Google (17-lug).** GSC 3 mesi: **1 click · 417 impressioni · posizione media 15,1 · CTR 0,2%**. È il primo in assoluto. Lettura onesta: da pagina 2 lo 0,2% è il CTR atteso — il click dice più di chi ha scrollato che di noi. **Ma è il secondo strumento indipendente** che conferma la diagnosi S116: Payhip 247 view / 0 checkout, Google 417 impressioni / 1 click. Due misure, una diagnosi: **non arriva nessuno**. Il buco è a monte, non nel prodotto.
- **Nessun annuncio del test da $25** (vedi §4). Deroga alla regola no-post-ven/sab/dom: **valutata e non usata**.

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No"
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money"
- Post 3 LIVE 2026-05-19: "When Your AI CEO Lies About the Numbers"
- **Post 4 LIVE 2026-05-28: "How Three Claudes Run a Company"** — bagholderai.lol/blog/how-three-claudes-run-a-company. Volume:3 / type:lesson. Meta/workflow post (CEO + intern + Haiku + Max). Pubblicato S90 commit `1b28e2a`
- **Post 5 LIVE 2026-05-31: "AI Is Useful. But It Doesn't Think Like We Do."** — bagholderai.lol/blog/ai-is-useful-but-it-doesnt-think-like-we-do. Ripubblicato da Dev.to (`noRss:true`), chiude drift blog↔Dev.to (audit A3)
- **Post 6 LIVE 2026-06-01: "The Solution Was One Sentence. My AI Took Two Days."** — bagholderai.lol/blog/the-solution-was-one-sentence. Type lesson, saga audit/overengineering (Human + CEO)
- **Post 7 LIVE 2026-06-02 — SEO+GEO POST 1: "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works."** — bagholderai.lol/blog/claude-code-crypto-trading-bot. Primo dei 5 post SEO+GEO (brief S95a), FAQPage schema. Vedi sub-sezione "Strategia SEO+GEO" sotto
- _(→ **10 post pubblicati** totali, coerente con §3. I "Post 6/7 PLANNED" qui sotto sono titoli di backlog, numerazione non sequenziale)_
- Post 6 PLANNED: "Why We're Not Live Yet" — a ridosso go-live
- Post 6 PLANNED: "We Built an Accounting System That Didn't Need to Exist" — FIFO saga, V3. ~inizio giugno.
- Post 7 PLANNED: "45 Sessions With an AI Co-Founder: The Unfiltered Version" — prefazione V2 adattata, voce Max. ~90% pronto.
- **Pipeline (aggiornata S85):** 13 post schedulati + 11 in backlog (Apple Note "BagHolderAI — Blog Content Pipeline"). Backlog V3 include: Operation Clean Slate, 4 Bugs in 60 Seconds, The Intern Runs the Office, Brain Can't Tell BONK from Bitcoin, The One Where Nobody Writes Code.
- Idea futura: "Cover Evolution" (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
- **Ordine editoriale NON cronologico** (S85): ogni post autonomo, pescato da qualsiasi punto della timeline — vetrina, non racconto lineare.
- **Frequenza ~1 post ogni 7-10 giorni** (S85), pubblicazione a raffiche con distribuzione attiva. No calendario fisso ("variable reinforcement").
- **RSS feed live** (S85, commit `8c9c2fc` + `18eaa24`): `https://bagholderai.lol/rss.xml` con `<content:encoded>` (body completo). Autodiscovery `<link rel="alternate">` nel Layout.
- **(S96)** Blog post "32 hours" pronto per pubblicazione con nuovo sito.
- **(S96)** Post scrappato da agdal.tech (trovato via Bing Webmaster Tools) — monitorare nel prossimo audit A3, nessuna azione immediata.

### Payhip
- Volume 1 + Volume 2 + **Volume 3 LIVE**: https://payhip.com/b/hCWNX (€4.99, "From Brain to Eyes", Sessions 53–82)
- Payhip store: https://payhip.com/BagHolderAI
- Redirect `/buy` ora punta allo store (non più a V1 singolo) — vercel.json aggiornato S87
- 39 views maggio (pre-V3 launch), 0 vendite, 0 ordini

## 3. Diary Status

- **Volume 4 ("From Eyes to Live")**: chiuso come prodotto il 9-ago (S125). **Capitolo di chiusura ancora da scrivere**, a due mani, in sessione dedicata. Nessun Volume 5.
- **Diary entries Supabase**: S125 (7-ago) → S131 (28-set). **S126–S130 non hanno entry**: sessioni solo Max+CC (manutenzione, A.1). Non si scrivono retroattivamente: la entry S131 dichiara il buco.
- **Regola da S131**: la entry Supabase si scrive solo nelle sessioni con il CEO. Le sessioni solo-CC restano tracciate nel MASTER_TASK_LIST. Emenda la SEQUENZA §2 ("sessione per sessione").
- Poster X: fermo di fatto dal 7-ago (legge `diary_entries`, ultima S125). Diagnosi in brief S131b.

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-09-28 (S131) | **Principio: decide tutto il bot, nessun intervento umano. Scartata la "quota-base" (capitale mai venduto dal bot).** | se la quota la gestisce Max a mano, il bot non aggiunge nulla su quella metà ("tanto vale tenere i coin su Coinbase"). Vale come filtro per ogni idea futura di strategia. |
| 2026-09-28 (S131) | **Il bug della zona morta non si corregge come da progetto: diventa regola esplicita.** Scala azzerata solo in paura/paura estrema; spenta in neutrale/avidità/avidità estrema; il reset non tocca il riferimento acquisti (D2). Brief S131a. | a 0,8% di commissione il bug ha fruttato +$6,5–7,8 su BTC (circa un quarto del guadagno, robusto su 20 disturbi), nulla di robusto su SOL; nello storico la BASE senza riavvii batte tutte le varianti (6/11). **Regola nata da un bug, tenuta perché i numeri la preferiscono a 0,8%: da riverificare dopo X.1**, perché a commissioni più basse le piccole vendite tornano convenienti (F vince nel laterale). |
| 2026-09-28 (S131) | **Il divario dal compra e tieni è esposizione, non taratura.** Stima: SOL ≈ −$67 su −$76 spiegati dal 26% investito in media; BTC ≈ −$19 su −$36 (da verificare, Q4 in S131a). Nessuna variante A–G di A.1 toccava l'esposizione. | cambia dove si guarda: A.2 lavora sul lato acquisti (rientro dopo vendita totale), non sulle soglie di vendita. |
| 2026-09-28 (S131) | **A.2 (rientro dopo vendita totale) dopo X.1, non prima.** Sequenza: S131a → X.1 → A.2 → cervelli. | X.1 è mezz'ora e cambia il valore delle piccole vendite; A.2 senza il numero delle commissioni ottimizzerebbe la cosa sbagliata. |
| 2026-09-28 (S131) | **H2 (vendita a metà lotto), H3 (uscita a inseguimento), H4 (esposizione minima per regime): non si testano ora.** Il Trend Follower come "secondo motore" per i rialzi è questione di Board da riprendere quando tocca ai cervelli. | sono risposte alternative alla stessa domanda, con rischi diversi; non si mescolano con la taratura del grid. |
| 2026-09-28 (S131) | **Numerazione sessioni: ogni sessione in cui si lavora prende un numero, anche solo-CC; i buchi di calendario non contano.** | S126–S130 esistevano nei file di CC ma non nel diario; il contatore conta sessioni, non giorni. `CLAUDE.md` "Numerazione sessioni (S108)" da allineare (edit di Max). |
| 2026-09-28 (S131) | **L'ammortizzatore vale meno della tesi S113.** Dallo storico A.1: protegge nei cali lenti ($6–16/mese) e nel −37% BTC 2022 ($35); in un crollo vero (SOL 2022, −57%) finisce i contanti al primo −20% e salva $5. Nei rialzi perde $38–70/mese senza tetto. | è l'argomento più forte per rivedere la protezione nel crollo (K1/K2) prima di qualunque aumento di esposizione. |
| 2026-08-09 (S125) | **Volume 4 si chiude come PRODOTTO. Il diario continua a essere scritto, smette di essere qualcosa che proviamo a vendere.** Il progetto, i bot e il sito continuano | **Decisione Max.** Zero vendite Payhip. Anticipa di tre settimane la deadline che il Board si era dato a giugno (fine agosto: zero trazione → il diary diventa contenuto gratuito, non prodotto). **Nota del CEO messa a verbale**: la tesi dichiarata del progetto è *"non falliamo se il bot perde soldi, falliamo se smettiamo di raccontare la storia"*; il diario era fermo da 16 giorni, il poster X aveva smesso di attingerne e generava dai config-change, e 69 bozze erano pronte dal 3 luglio col campo "pubblicato" vuoto su tutte. L'audit A3 dice da due cicli che il collo di bottiglia è la **distribuzione**, non il prodotto. Non è un argomento per riaprire: è la versione accurata del perché finisce. **Capitolo di chiusura a due mani — sessione dedicata** (voci alternate, convenzione `author`) |
| 2026-08-08 (post-S125) | **Primo ciclo completo scelto dalla macchina su denaro reale — su SOL, in 27 ore** | BUY $73,48 (7 ago 10:55) → SELL $76,00 (8 ago 14:35, **+$0,36 netto**) → rientro $76,22. Secondo giro completo della storia del progetto dopo il +$0,71 di BTC in Fase 2a, **primo deciso interamente dal bot**. Smentisce l'auto-obiezione del CEO nel brief S125b (*"se la prima settimana non produce un ciclo, il sito lo mostrerà"*): la risposta è arrivata il giorno dopo il reveal. **E conferma l'altra**: SOL era la riga con meno evidenza sotto, ed è quella che ha ciclato — BTC, con 22 giorni di denaro reale, non ha ancora chiuso un giro. Lordo ~$0,69, netto $0,36: **le commissioni si sono prese metà**. È la tesi da tenere: il vincolo sono le fee, non la strategia |
| ⚠️ 2026-08-07 (S125) | **CORREZIONE a una motivazione del reveal.** Il brief S125b sosteneva che la homepage mostrasse tutti zeri (Orders 0, Days running 0) — **falso**: erano segnaposto renderizzati lato server, riscritti dal browser. I valori reali erano **255 ordini, −$30,47, 64 giorni** | Il CEO ha concluso da un fetch HTML che non esegue JavaScript. È lo stesso inciampo del finding **M1 dell'audit A2**, e la regola era già in PROJECT_STATE §9 (*verificare un finding contro la fonte viva prima di remediarlo*). **La decisione resta giusta ma poggiava su una gamba sola** — `/terms` falsa, verificata nel codice — non su tre. Correzione tenuta in chiaro invece di rimossa in silenzio: fra sei mesi la differenza conta |
| 2026-08-07 (S125) | **Reveal "denaro reale" ESEGUITO** — sito pubblico dalle 19:15 UTC, `/terms` corretta, storia testnet archiviata in `/history`, 8 superfici migrate | `/terms` affermava **al presente** *"no real money is traded by our bots at this stage"*, falso dal **17 luglio** (non dal 22: il primo denaro reale è di 5 giorni prima). Finding H1 audit A2 chiuso. **Il rischio vero era l'opposto di quello previsto**: non vetrina vuota ma vetrina piena coi numeri sbagliati — le superfici erano inchiodate a `venue='binance' AND is_active=true`, e spegnendo le righe Binance il fallback mostrava **255 ordini simulati sotto il badge "denaro reale"**. La pagina d'attesa non era eleganza, era necessità |
| 2026-08-07 (S125) | **`/history`: pubblicati ENTRAMBI i numeri dell'era paper** — +$69,05 come fu riportato allora, **+$47,57** ricalcolato con la formula di oggi | **Scelta Max.** I $21 di differenza non sono il passato che cambia: sono tre bug nel FIFO di allora e le commissioni non sottratte con coerenza. Un archivio che mostra solo i numeri vecchi è nostalgia; uno che mostra la correzione è un metodo. Dato che nessuna era da sola poteva mostrare: **30 ordini/giorno a $0,0144 di fee sul paper, 0,2 ordini/giorno a $0,2702 su Kraken** |
| 2026-08-07 (S125) | **Storia testnet archiviata come capitolo chiuso, non rimossa** | 5 mesi consultabili ed etichettati come storici/simulati, con la causa dichiarata: reset dell'exchange, non scelta del progetto. I contatori pubblici non mescolano più testnet e Kraken in un unico numero |
| ⚖️ 2026-08-07 (S125) | **Nessuna modifica al comportamento dei bot nel passaggio a Kraken.** `profit_target_pct` resta **0**, LAST SHOT invariato, `sell_pct` invariato. Cambia solo il venue | **Disaccordo risolto da Max.** Il CEO proponeva `profit_target_pct` a 0,4% come rete contro la sell ladder sotto il costo di carico, e una revisione del LAST SHOT. Max: *"il resto è tutto collaudato e funzionante, le fees sono già assorbite dall'obiettivo di guadagno e calcolate in base all'exchange"*. Verificato nel codice: `sell_pct` è **già netto-fee e per-venue** — obiezione mal fondata. Chiarimento emerso: `profit_target_pct` non è un obiettivo di profitto ma un **safety gate** che blocca le vendite sotto una soglia sopra il costo medio. **Nodo 5 chiuso: resta 0** |
| ⚖️ 2026-08-07 (S125) | **LAST SHOT mantenuto attivo su denaro reale** | **Decisione Max.** Il CEO obiettava che concentra il capitale residuo su un singolo prezzo (28 luglio: $64,44 in un ordine solo, due terzi dell'allocazione). Con `capital_allocation` a $250 e lotto $33 la scala ha 7 livelli → scatta solo dopo un drawdown ~21%, dove concentrare ha una logica. Zero codice |

> Decisioni **dal 2026-06-11 al 2026-08-07 (XRP a prezzo fisso e precedenti, 45 righe) archiviate il 2026-09-28** su istruzione CEO S131 ("tenere le 15 più recenti") → [audits/BUSINESS_STATE_archive.md](audits/BUSINESS_STATE_archive.md). Decisioni **2026-07-01 e precedenti archiviate nella compaction 2026-07-29** (tenute qui solo le portanti ancora in vigore: verdetto strategico grid=ammortizzatore S113, USD+lineup Kraken S112b, allocazione €600 S110, ownership parametri Board/Sherpa S102, marketing S115); **S88→S96 archiviate in S105** (2026-06-13); S81→S87 in S92; S80 e precedenti in S82 — tutte in `audits/BUSINESS_STATE_archive.md`. Storico completo anche in git history.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **[S131] K1/K2 — protezione nel crollo** | 🆕 S131 | (primo item del lavoro Sentinel): blocco perdita che in paura estrema resta chiuso finché il prezzo non recupera X%; lotto proporzionale ai contanti residui. Oggi il blocco si riapre da solo ogni 6h e compra nel crollo. |
| **[S131] Sherpa nel laterale** | 🆕 S131 | i parametri fissi (C) vincono in 3 finestre laterali su 11. Sospetto da guardare dopo X.1. |
| **[S131] Zona morta post-X.1** | 🆕 S131 | se la commissione scende a 0,25%, rifare D vs BASE con F' (Q3) prima di tenere la regola S131a. |
| **[S131] SOL sotto-investito** | 🆕 S131 | rientro con un lotto solo dopo ogni vendita totale + passo d'acquisto allargato da Sherpa in avidità (2,25→2,45). Base dati Q5 (S131a) → piano A.2 (lo scrive il CEO). |
| 🔴 **Riconciliazione su Kraken: non esiste** | **Debito n.1** | È il controllo che prova che i numeri a DB corrispondono agli ordini veri dell'exchange. Sul testnet era una formalità; sul denaro reale è l'unica cosa fra "i conti tornano" e "crediamo che tornino". Già scritto dentro `/admin` |
| 🟡 **Sherpa allarga SOL senza sosta** | Da osservare | 39 riscritture in 48h (`buy_pct` 2,25→2,67, `sell_pct` 1,50→1,78), **BTC fermo su 1,80/1,20**. Con `sell_pct` a 1,78 + 0,80% di fee, SOL deve salire ~2,68% per vendere, contro ~2,3% di due giorni prima. Se fra una settimana è a 2,2 senza cicli, verificare se il clamp di Sherpa sia tarato per un venue allo 0,80% |
| 🟡 **`/tf` ha il Save spento** | Bassa | Finché `trend_config` non passa dal portiere. Il TF è fermo, non urge |
| **Lezione di processo** | — | Il brief **S122b** era stato archiviato come chiuso con metà del lavoro non fatto: il pannello riportava un trigger di vendita **$524 sotto** quello reale, nella direzione che fa credere imminente una vendita che non lo è. Trovato per caso, archiviando. Chiuso in S125b (`7325b39`). **Un brief si chiude verificando tutte le sue richieste, non la data** |
| **[S118→S125] Nodo 5 — `profit_target_pct` sulle righe Kraken** | ✅ **CHIUSA: resta 0** | Deciso da Max il 7-ago. Chiarimento emerso in sessione e utile a chiunque riapra il tema: `profit_target_pct` **non è un obiettivo di profitto** ma un **cancello di sicurezza** che blocca le vendite sotto una soglia sopra il costo medio. Non serviva perché `sell_pct` è già netto-fee e per-venue: il floor c'è già, altrove |
| **[S119→S125] `trades` non ha colonna `venue`** | 🔺 **Promossa: è costata due volte** | La separazione denaro reale ↔ testnet regge solo sulla **stringa del ciclo**. Il 7-ago questo ha prodotto due guasti veri: il report serale ha misurato il portafoglio testnet morto, e le superfici pubbliche sarebbero rimaste congelate sui numeri finti. Scoperto anche che `mode` **non** serve a distinguere: vale `live` per tutte e 319 le operazioni, testnet incluso (significa "mandato a un exchange", non "soldi veri"). Oggi il sito conta come denaro reale ciò che si chiama `kraken*` — una **convenzione sui nomi, non un dato**. Da risolvere alla prossima modifica di schema |
| **[S125 NEW] Sostituire il backtest pubblico girato a fee dimezzata** | 🟠 Decisione editoriale, ora più urgente | `params.py` usava 0,40% contro lo 0,80% reale: grafici e conclusioni sottostimano di **2×** il costo dominante, nella direzione che favorisce il grid. Con denaro vero in campo quel materiale è fuorviante. Rigirare il backtest o mettere una nota editoriale sul post — non l'ho toccato di iniziativa, è territorio editoriale |
| **[S122] CoinMarketCap free API come sorgente dati Sentinel** | 🆕 Parcheggiata (non gate go-live) | dominance BTC, market cap totale, ampiezza su molte monete. Account attivo (15.000 crediti/mese, 50 req/min, 40+ endpoint). Vicino al **Breadth Tier 3 parcheggiato S109**. Prerequisito: verificare cosa copre il piano free prima di progettare |
| **[S122] `tf.html:1459`** | 🆕 Micro-brief, priorità bassa | formula trigger grid applicata ai bot **TF** (incoerenza pre-esistente, verificata CC S122, fuori scope sherpa-on-kraken). TF non trada in v3 |
| **[S119 NEW] `trades` non ha colonna `venue`** | 🆕 Da valutare — fase sistema-pieno | La separazione Kraken ↔ testnet regge **solo** su `cycle` (`kraken_test` vs `testnet_2`) + il simbolo (`BTC/USD` vs `BTC/USDT`). Funziona oggi. Ma è **accoppiamento implicito**, stessa famiglia dei bug che ci hanno già morso: cycle-fetch (S118 🟠) e superfici sito (S119 🟠). Valutare colonna `venue` esplicita quando Kraken passa a 3 monete. **Non blocca la 2b** |
| **[S119] Timeout/retry del poll `fetch_order`** | Da definire nel fix critico 2a | Comportamento se il fill non è confermato entro il timeout (ordine in volo ma non ancora leggibile) — caso limite più pericoloso del fix critico |
| **[S112 NEW] Guard anti-blackout lato Kraken** (idea Max) | Post-cutover | Soglie di uscita larghe piazzate sull'exchange, più in alto di Sherpa, per proteggere in caso di downtime del bot (crash Mac Mini / connessione giù) — quando Sherpa non può agire perché è giù col bot. Parente del Portfolio Guardian, angolo specifico = resilienza al downtime |
| **[S112 NEW] CMC come 2ª fonte F&G** (emerso nel Passo 0) | Post-cutover, brief separato | Brief parcheggiato `config/parked/PARKED_cmc_fear_greed_second_source.md` (verifica chiave S112: F&G latest+historical disponibili sul nostro piano) |
| **[S107 NEW] Blog post Cluster 1 "AI as CEO"** | PARCHEGGIATO | Il differenziatore massimo non ha ancora un post dedicato. Da scrivere quando il sistema ha risultati reali da raccontare (post-mainnet?) |
| **[S107 NEW] Meta tag blog post esistenti** | BASSA PRIORITÀ | Retrofit title/tags dei 9 post live per includere keyword cluster 1-3. Impatto modesto, rischio reset ranking |
| **[S105 NEW] Monitor "griglia silenziosa"** | DA DECIDERE (Apple Notes vs brief) | Alert quando una griglia non registra trade da X ore. Buco osservabilità S105: un bot fermo non emette ERROR né Telegram, SOL morta 5gg invisibile. Il fix dust impedisce *questo* freeze, non la classe generale. Trigger: prossima sessione o pre-mainnet |
| **[S105 NEW] Caso degradato no-filtri** (is_dust fallback $0,50) | Da valutare | Se `fetch_filters` fallisce al boot, il bot gira col fallback $0,50 < minNotional reale → un residuo in [$0,50, $5) potrebbe ri-congelarsi. Valutare se in quel caso il bot debba allertare invece di operare con soglia errata. Collegato al monitor sopra |
| **[S104 NEW] Automazione spese Haiku — Anthropic Admin API** | PARKED | Endpoint `/v1/organizations/usage_report/messages` + `/v1/organizations/cost_report`. Serve Admin API key (Max genera da console.anthropic.com). Script mensile: chiama API → filtra Haiku → scrive in Supabase `project_expenses`. Insieme a scheduled €90 il giorno 4 di ogni mese |
| **[S102 NEW] Regime stickiness innesto barometro↔Sherpa** | Post-verdetto T+14 (~23 giu) + primo regime non-bear | Fattibilità confermata CC: opzione (a)+(c), ~5-7h, 4 file. Barometro modula la velocità del cap, non la destinazione. NON costruire prima del verdetto |
| **[S99b NEW] Monitoraggio anti-slippage v2 su BONK testnet** | Osservazione | Soglia 1% con slippage strutturale 3-4%: BONK sarà penalizzato quasi sempre. Se si congela (deadlock), alzare soglia o renderla per-coin |
| **[S91 NEW] Integrità dati — `bot_state_snapshots` saldo grezzo** | 🆕 Da verificare | `bot_state_snapshots` fotografa il **saldo grezzo testnet (pre-funded)**, non la posizione €500 → verificare che **nessuna superficie pubblica** lo peschi. Minori: fallback `1,0×` non cappato in Sentinel; dead-band scritture Sherpa ✅ DONE (S102a write guard `a867179`) |
| **[S90 NEW] Option C — slippage buffer su percentage sell path** | TODO pre-mainnet, brief separato | Brief separato pre-mainnet. Estendere il pattern `SLIPPAGE_BUFFER_PCT=0.03` (già attivo su SWEEP/LAST_SHOT path da brief 78b) anche al path `_execute_percentage_sell` per chiudere completamente la finestra di rischio post-fix A+B |
| **[S90 NEW] Calibrazione parametri spike guard** (threshold 4% / confirm 50% / pause 5s) | Osservazione 7-14gg, poi decidere | Oggi i 3 parametri sono default argument della funzione `fetch_price_with_spike_guard`. Post osservazione: valutare se servono tunable per-coin via `bot_config` (BTC vs SOL vs BONK volatilità diverse). Voto CC: tenerli fissi finché dati live non suggeriscono altrimenti |
| **[S81 NEW] Cross-post automation Dev.to + Indie Hackers** | Decisione rimandata post-weekend | Quando un post va live su `web_astro/src/content/blog/`, script che pubblica su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. ~2-3h stimato |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **NewsKeeper v2 Barometro verdetto** | Nessuna data fissa (era ~23 giu) | T+14 raggiunto, esito: PASS qualità / INCONCLUSIVE prezzo (N=2 flip insufficiente). Esteso fino a regime change sostenuto (neutral/bullish >24h). Non blocca go-live grid. Dettagli in diary S108 |
| **Apple Notes pulizia: cancellare 8 note obsolete (Max)** | A discrezione Max | 4 note attive da mantenere, 8 obsolete da cancellare manualmente |
| ✅ **Volume 4** | **CHIUSO come prodotto** (09-ago) | L'arco narrativo ha trovato il suo finale col go-live. Il diario continua a essere scritto, smette di essere in vendita. Resta il **capitolo di chiusura a due mani**, sessione dedicata |
| ✅ **Reset testnet Binance** | ~~Stimato inizio luglio~~ → **AVVENUTO 5-6 agosto 2026** | Chiuso come accaduto. È stato il **trigger effettivo** del cutover completo, esattamente come previsto: non abbiamo deciso di lasciare il testnet, il testnet ha deciso per noi |
| ✅ **Collaudo Kraken Fasi 2a/2b/3** | **CHIUSE** (2a il 21-lug, 2b il 22-lug, 3-bot il 7-ago) | Denaro reale dal 17 luglio; sistema interamente su Kraken dal 7 agosto ($250 BTC + $150 SOL) |
| 🔴 **Riconciliazione Kraken** | Nessuna data — **debito aperto** | Il controllo che prova che i numeri a DB corrispondono all'exchange non esiste su Kraken. Sul testnet era formalità, sul denaro reale è sostanza. Vedi §4 |
| ✅ **Deadline marketing organico "fine agosto"** | **Superata dai fatti** | Il Board si era dato fine agosto: zero trazione → il diary diventa contenuto gratuito. Chiusa in anticipo di tre settimane con la decisione del 09-ago sul Volume 4 |
| 🟡 **Post di annuncio "denaro reale"** | A discrezione Max | Regola marketing: lo scrive Max in italiano, il CEO traduce. Tono: "primo dollaro vero", la piccolezza come rigore, niente percentuali nel titolo |
| 🟡 **Verifica T+24h Sherpa su SOL** | 8 agosto | Il brief chiedeva di controllare che Sherpa non riscriva i parametri di SOL in modo inatteso. Alle prime 6 ore li stava già allargando: buy 2,25→2,45, sell 1,50→1,63 |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). PID/runtime dettagliati in PROJECT_STATE §1+§7.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

- **La macchina dei contenuti è ferma da 7 settimane.** Nessun post da nessuna parte; le 69 bozze X del 3 luglio mai pubblicate; il poster Haiku ripete la stessa bozza (ipotesi: input fermo, verifica in S131b); Volume 4 senza capitolo di chiusura; prompt audit A3 ancora con Umami (S131b). **Blocco 1 della prossima sessione CEO: riapertura contenuti.** Il Board ha detto che il valore del progetto non è il P&L: questo è il rischio più grande in lista.
- **Post di annuncio "denaro reale"**: ancora non scritto. Materiale pronto: report A.1 §8 + la storia "stesse regole, strade diverse" (BTC/SOL). Lo scrive Max in italiano, il CEO traduce.
- **CEO assente S126–S130**: sette settimane. Il piano A.1 (S129) l'ha scritto CC. Da S131 i piani strategici tornano al CEO (A.2 in primis).

---

## Parcheggiati (non decisi, non persi)

- **XRP con ordini a prezzo fisso** — misurare la commissione maker reale. Il listino dichiara 0,25% ma sul fill reale abbiamo pagato 0,7999% contro lo 0,40% dichiarato: già smentito una volta. **Da separare in due lavori**: un singolo ordine limite per leggere l'addebito (mezz'ora) vs la macchina completa di gestione ordini in attesa (settimane). Sul ciclo appena chiuso quella differenza è il lavoro col maggior effetto sui numeri fra tutti quelli in coda
- **Sentinel / NewsKeeper / Sherpa** — dopo il go-live, ora sbloccati
- **Difetto del prezzo fasullo** — non più un gate (book Kraken profondo su BTC/SOL), resta manutenzione
- **Script ricorrente spread + volume** per la selezione asset futura
- ~~`COLLAUDO_COMMS_GUIDELINES_v1.md` da emendare~~ ✅ **FATTO in S125 (07-ago)**: emendate a **v3** con cappello "v2 vs realtà" e correzioni a §1/§2/§3/§5; il testo superato è barrato accanto al nuovo, non cancellato. Tolto anche `_v1` dal nome del file, che era falso da quando era v2. Il principio-madre §0 è intatto. *(Voce presente come "da fare" nel blocco CEO del 09-ago — segnalata da CC come già chiusa due giorni prima.)*
