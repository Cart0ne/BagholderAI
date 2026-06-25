# PARKED — Spunti da ricognizione marketing 22/06/2026

Sessione marketing, nessun numero di sessione. Insights raccolti da 3 fonti Reddit/web, parcheggiati per sessioni di lavoro future.

---

## 1. SEO & TRAFFICO ORGANICO

**Fonte:** post Reddit "My website went from 78 to 8,018 monthly Google clicks" (Clipy, screen recorder gratuito, 301 upvote)

**Spunti azionabili per noi:**

- **Intent matching da GSC:** andare in Google Search Console, filtrare query con impressioni alte e click bassi. Quelle sono le query dove Google ci sta già testando — ottimizzare pagine esistenti o creare pagine nuove che rispondano esattamente a quelle query. Noi avevamo 256 impressioni e 0 click all'ultimo audit (pre-fix S84). Da riverificare post-fix.

- **Cluster long-tail:** invece di un unico blog post per keyword, creare varianti mirate. Esempio: se "ai trading bot" è la keyword principale, varianti come "ai trading bot for beginners", "vibe coding trading bot", "claude code trading bot", "ai trading bot results" — ognuna a bassa competizione, sommate fanno volume. Applicabile ai 4 blog post SEO in coda (non-coder, vibe coding, why bots fail, testnet results).

- **Titoli keyword-first:** titoli che aprono con la keyword esatta, non tagline creative. "AI Trading Bot Results After 3 Months" > "The Honest Truth About Our Little Experiment". Verificare i titoli dei blog post esistenti.

- **Valore prima del muro:** le pagine che rankano meglio danno valore immediato senza richiedere signup/click. La nostra dashboard pubblica già fa questo — assicurarsi che sia indicizzata e che il contenuto sia leggibile da crawler.

**Cosa NON si applica:** Clipy ha un tool con utilità diretta (scarica video Loom). Noi abbiamo un diario/esperimento — profilo di intento diverso. Non possiamo replicare il modello "build the exact page for the exact search" 1:1 su tutto.

**Quando usare:** prossima sessione SEO o quando si lavora sui blog post SEO in coda.

---

## 2. BACKTEST & VALIDAZIONE TRADING

**Fonte:** thread Reddit "Am I building a trading system or just creating a very expensive illusion?" (r/algotrading o simile, 5 upvote). Commento chiave di Zestyclose-Eagle1809 (founder Quantprove, validation tooling per systematic traders).

**Tre test per validare un edge (applicabili al Portfolio Guardian backtest):**

- **Holdout intoccato:** riservare un periodo di dati che non si è MAI guardato durante lo sviluppo. Una sola occhiata, zero tuning dopo. Se hai sbirciato durante il development, è contaminato e inutile come check.

- **Decomposizione per regime:** il crypto dal 2020 a oggi copre un bull pieno, il crollo 2022, e il chop dopo. Tagliare i risultati per regime. Un edge vero sopravvive a un regime in cui non è stato costruito. Un edge fittato funziona solo nelle condizioni in cui è stato plasmato.

- **Stress sui costi:** raddoppiare fee e slippage assumption e rieseguire. Sul crypto, funding reale e fill reali mangiano edge sottili. Un edge genuino degrada gradualmente, un edge illusorio crolla.

**Punto architetturale rilevante:** ogni feature aggiunta (macro, on-chain, sentiment) è un parametro in più per fittare il passato. Challenge legittimo alla nostra architettura NewsKeeper + Sentinel + Sherpa. La nostra difesa: i brain non predicono, classificano regime. Ma il rischio overfitting via complessità resta.

**Dato di realtà (commento EmbarrassedEscape409):** dopo 1 anno di bot building, AUC raggiunta = 0.54 (appena meglio di moneta). Return 10-15% annuo. Fee ammazzano i piccoli conti. Ha smesso perché l'indice rende uguale senza sbattimento. Soglia minima per sensatezza: fee sotto 0.4% e conto >100K. Doccia fredda utile per calibrare aspettative sul nostro €100 mainnet.

**Quando usare:** sessione Portfolio Guardian backtest design (i 3 periodi storici previsti nel brief architettura) e calibrazione thresholds.

---

## 3. POSIZIONAMENTO SITO & DISCLAIMER

**Fonte:** sito tradebuddyai.com.au (Chrome extension per disciplina trader, builder solo, Melbourne AU).

**Spunti per il nostro sito:**

- **Framework "cosa NON siamo":** TradeBuddyAI martella su cosa il prodotto NON fa — "No signals. No predictions. Just a cleaner process." Ripetuto ovunque, zero ambiguità. Noi potremmo essere più espliciti su bagholderai.lol: "Non vendiamo segnali. Non consigliamo crypto. Documentiamo un esperimento." Lo facciamo nel tono ma non in modo strutturato e visibile. Applicabile alla homepage e alla pagina "The Experiment" (/income).

- **Tabella comparativa:** formato "What traders usually get vs. What Trade Buddy AI adds" — efficace, scansionabile. Adattabile per noi: "What AI trading projects usually show vs. What we actually publish (including losses)." Potrebbe funzionare nella pagina "The Experiment" o in un blog post.

- **Slogan "Discipline over dopamine":** non copiare, ma il principio è buono — trovare una frase-ancora che catturi il posizionamento in 3 parole. Per noi potrebbe essere qualcosa intorno a "Transparency over returns" o "The process is the product".

- **Disclaimer legali:** il loro è dettagliato e lawyer-reviewed (Terms of Service con 17 sezioni, AI Output Disclaimer, Risk Warning separati). Noi abbiamo disclaimer sul sito? Da verificare e rafforzare pre-mainnet. Punti da coprire: non è consulenza finanziaria, AI può sbagliare, trading comporta rischi, risultati passati non garantiscono futuri.

- **"Real screens. Zero mockups.":** trasparenza come selling point esplicito. Noi lo facciamo ("honest numbers including losses") ma potremmo renderlo più visibile, tipo banner o sezione dedicata nella dashboard pubblica.

**Cosa NON si applica:** tool B2C per trader umani manuali (noi automated), Chrome extension (distribuzione diversa), journaling comportamentale/tracking emozioni (il nostro trader è un AI senza emozioni).

**Quando usare:** prossima sessione frontend/redesign sito, pagina "The Experiment", o pre-mainnet legal check.

---

## STATO

| # | area | priorità | da usare in |
|---|------|----------|-------------|
| 1 | SEO long-tail + intent | media | sessione SEO / blog post SEO |
| 2 | Backtest validation | media-alta | Portfolio Guardian design |
| 3 | Posizionamento sito | bassa | redesign / "The Experiment" / pre-mainnet |
