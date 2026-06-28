# BUSINESS_STATE.md

**Last updated:** 2026-06-28 (estemporanea) — §4 Board ratification 4.12/4.14 + grid-regime-backtest (Caso 2) approvato; §5 brief S111 in coda post-S110d. Cap file 50KB (Max S95, CLAUDE.md §2b). Cadenze audit canoniche in PROJECT_STATE §9. Prec.: 2026-06-27 Session 110 (go-live experiment approvato + 3 brief CC [USDC, exit thresholds, NK cleanup] + dashboard private fixes S110a/b).
**Updated by:** Max (estemporanea 2026-06-28), applicato da CC
**Basato su:** PROJECT_STATE.md aggiornato 2026-06-14; report S104 (income-page) + S106 (office-page); screenshot live homepage/dashboard/office/income; document `bagholderai_website_architecture_v1.docx` (concept esterno)

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

### S106 — site upgrade planning (NUOVO)
- **Brief S106a `site-upgrade-v1`** scritto e approvato da Board. Caso 2 (non blocca mainnet). Contenuto:
  - **Nav ristrutturata**: `Dashboard · Diary · Blog · Under the hood ▾ · Library` (5 voci + dropdown). /news pianificata come 6ª voce post-verdetto barometro (~23 giugno) — non ancora costruita né in nav. Dropdown "Under the hood" contiene: How we work, Blueprint, Roadmap, The experiment (/income)
  - **Homepage nuova**: hero = scena ufficio animata (componente da /office), status bar, bot cards (NewsKeeper linka a /news), manifesto block nuovo ("This is not a crypto project"), latest posts, diary, volumi. Eliminate: sezione "The team", banner V3
  - **Bot nella scena linkano a pagine reali**: Bag→/howwework, Board→/dashboard, NewsKeeper→/news, Grid/TF/Sentinel/Sherpa→/dashboard#anchor
  - **Live snapshot sotto hero**: formato TBD — CC prepara strip compatta vs card ridotta, Max sceglie su visual
  - **/office eliminata** come pagina standalone → redirect 301 a /. Componente scena spostato in homepage
  - **/income pubblicata**: noindex rimosso, aggiunta a sitemap + dropdown, adesivo WIP rimosso
  - **/dashboard riordinata**: Brains prima di Traders (pipeline logica), CEO observation log spostato dopo Recent activity, chart `type="linear"` (fix curva smooth)
  - **/news pianificata** (non ancora costruita) — costruzione post-verdetto barometro (~23 giugno). Due scenari (validato/bocciato) documentati nel brief S106a. Sarà aggiunta alla nav e linkata dalla card NewsKeeper quando costruita
  - CC produce piano italiano per Max prima di codare (task > 1h)

### Site v2 (S106a batch 1 + S107) — SHIPPED & ONLINE

**Homepage v2 (S107, online 18 giugno):**
- Scena ufficio (`LabRoom.jsx`) come hero — sostituisce il vecchio text hero
- Bot cliccabili nella scena: click → sezione dashboard corrispondente (anchor ID)
- Live snapshot (4 label) + Today (2 label) sotto la scena
- Manifesto block con H2: "This is not a crypto project."
- Bot card reinserite tra snapshot e manifesto (testo leggibile dai crawler)
- Rimossi: pill "Volume 3 is live", sezione "The team"
- /office eliminata come pagina standalone (redirect 301 → /)

**Dashboard v2 (S107):**
- Plate per-bot vestiti con colori e scenografie (Grid=mixer, TF=radar, NK=?, Sentinel=pulse, Sherpa=gear)
- Bordi tratteggiati + tint soft per-bot
- Colori bot ripristinati ai vivaci della scena (annullato pastel override S103b)
- Unrealized/fees/skim da 3 colonne → 3 righe; micro-prezzi in notazione scientifica

**Board scena ufficio (S107):**
- Include coin TF (ETH visibile)
- Label "unrealized" sulle coin + "TOTAL P&L"
- Net worth sotto il grafico
- Cornice flash adattiva

**Batch 1 S106a (15 giugno, online):**
- Grafici onesti `tension:0` (dashboard + /income)
- /income pubblicata (noindex off, sitemap, dropdown "The experiment")
- Nav dropdown "Under the hood ▾" (7→5 voci)
- Dashboard riordinata (Brains prima di Traders, CEO log in fondo)
- Anchor ID dashboard (#grid, #trendfollower, #sentinel, #sherpa, #newskeeper)
- Fix H1 diary "Development diary"

### S104 — web/marketing (NUOVO)
- **Blog "How a Non-Coder Manages 5 AI Brains" PUBLISHED** (S104) — post two-voice, portabile per cross-post (tabella→lista, nomi generici→reali: Sherpa, NewsKeeper). Canonical: bagholderai.lol/blog/non-coder-5-brains. Cross-post Dev.to/Substack pendente.
- **Dashboard pubblica §2 redesign LIVE** (S103b→S104) — 5 card statiche → righe full-width pipeline con dati live e polling 5min. THE TRADERS: TF→Grid+sparkline. THE BRAINS: NewsKeeper→Sentinel→Sherpa. Tutti brain LIVE (niente DRY_RUN). Token `--color-bot-news` in STYLEGUIDE §5.
- **Card Sherpa homepage: ACTIVE (badge TEST)** (S104) — aggiornata da DRY_RUN. MODE LIVE, PARAMS 7 (3 strategy + 4 protective S103a), badge TEST mantenuto (opera su testnet).
- **"/income" — The Passive Income Experiment: scaffold PRIVATO** (S104) — pagina combinata revenue+spese+attention+test history. Data-driven da tabella Supabase `passive_income`. KPI: Revenue €0, Spent ~€274, Conversion 0%, Visitors ~575/30d. Running costs breakdown (Claude Max €270 domina 98.5%). noindex, fuori da menu/sitemap. URL: bagholderai.lol/income.

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

### Strategia SEO+GEO (NUOVO S95)
- **Dual-channel content strategy adottata:** ogni post blog serve SEO (keyword head-term nel titolo) + GEO (risposta diretta nei primi 2 paragrafi per citazione LLM)
- **Keyword validate (Google Keyword Planner, US+CN+EU):** "claude code" 100K–1M/mese +9.900% YoY bassa concorrenza, "ai trading bot" 10K–100K +900% media, "vibe coding" 100K–1M stabile media, "crypto trading bot" 1K–10K stabile bassa
- **Brief S95a:** piano 5 post SEO+GEO. Sequenza: POST 1 (claude code) → POST 2 (ai bot fails) → POST 3 (non-coder workflow) → POST 4 (vibe coding) → POST 5 (real results, quando dati pronti)
- **POST 1 SEO+GEO LIVE** (2 giugno 2026, commit `78483dc`): "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works." URL: `/blog/claude-code-crypto-trading-bot`. FAQPage schema attivo (6 FAQ). Pubblicato su `main`, look dark attuale, erediterà pastello al merge redesign.

### Medium (@BagHolderAI) (NUOVO S95)
- **Attivo da giugno 2026, 2 post pubblicati.** Cross-post con canonical URL. Audience più ampia e meno tecnica di Dev.to.

### LinkedIn (parcheggiato, post-redesign) (NUOVO S95)
- **Decisione S95:** creare company page BagHolderAI + profilo personale "Max Cartone" (bagholderai@proton.me)
- **Ricognizione Claude in Chrome:** 1 solo competitor diretto (Bassam Fahmy, "AI CEO of Homains", 30 reazioni). Campo vuoto.
- **Strategia:** doppio canale (profilo per reach, company page per identità/GEO). Voce CEO. Timing: dopo merge redesign.

### Dev.to (cart0ne)
- **Account creato:** 2026-05-20 (GitHub login, username: `cart0ne`)
- **Profilo completato:** bio, coding section, work section, series "BagHolderAI"
- **Post 1 LIVE:** "An AI That Can't Trade, a Human That Can't Say No" — canonical URL `bagholderai.lol`, UTM footer, serie "BagHolderAI". Pubblicato 2026-05-20 sera. Views/reactions: ancora ~0 (account nuovo, nessun follower, algoritmo non spinge).
- **Post 2 LIVE:** "The Day Our Bot Ran Out of Money" — cross-posted 2026-05-22, canonical URL, UTM footer, serie "BagHolderAI".
- **Post 3 LIVE:** "When Your AI CEO Lies About the Numbers" — cross-posted 2026-05-24, canonical URL, UTM footer, serie "BagHolderAI". Stats post-24h: **22 readers, 0 reactions** (account fresco, engagement da costruire).

### X (@BagHolderAI)
- **Post pinnato S87**: lancio V3, link a bagholderai.lol/library. Sostituisce il post blog S78
- Post promozionale Post 3 pubblicato 2026-05-19 (gancio provocatorio "your ai assistant would rather fabricate a number...")
- Post Dev.to launch da pubblicare stasera contemporaneamente al cross-post
- Reply strategy attiva (doc: `reply_strategy_target_accounts.md`)
- Scanner X cron settimanale attivo

### HN
- Account Cart0ne: SHADOWBAN COMPLETO confermato 2026-05-19
- Piano: nuovo account da IP diverso, karma building, timeline indefinita

### Reddit (NUOVO S85, aggiornato S90)
- **Account:** `Cart0neM`
- **Canale di distribuzione primario** (decisione S85): r/ClaudeAI identificato come community più aderente al pubblico-target (architetti/founder che usano AI per progetti tecnici).
- **Primo post S90 (2026-05-28):** r/ClaudeAI, flair "Claude Workflow". **In mod approval**. Strategia: **zero link, zero sales** — solo la storia del workflow tre-Claudes. Sequenza prevista: introduce → engage → earn credibility → mention book in fase successiva
- **Commento LIVE nel "Build with Claude Megathread"** (S90) — engagement nel thread ufficiale della community, no link
- **Storico engagement (S85-S87):** primo commento in thread da 643 upvote (2026-05-25, 1 reply). Strategia parcheggiata S87: primo post NON sales pitch ma presentazione progetto con valore. Sequenza confermata e ora in esecuzione (S90)
- **Aggiornamento S95 (2026-06-01):** karma building completato. Best comment su r/AIAgents: **13 upvote, 2485 views**.

### UTM (NUOVO)
- **Sistema UTM operativo** (Apple Note "BagHolderAI — UTM Reference")
- **Haiku template + Telegram report: SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)**. X poster signature ora URL completo con `utm_source=x&utm_medium=social&utm_campaign=haiku_daily`. Telegram 3 firme convertite in `<a href>` cliccabili con `utm_source=telegram&utm_medium=social&utm_campaign=daily_report`. Mac Mini restart pending per applicare alle prossime emissioni.
- **UTM link bio X abbandonato (S85)**: non mascherabile (X mostra l'URL espanso), referrer X sufficiente per tracking.
- Regola operativa: ogni link che esce dal progetto DEVE avere UTM (dove possibile)

### Distribuzione blog
- Documento strategia distribuzione `marketing_strategy_distribution.md`
- **Stato 2026-05-24:** X + Dev.to attivi, nessun nuovo canale aggiunto. Indie Hackers e Product Hunt confermati come **post-mainnet** (serve storia completa + numeri veri).
- Dev.to scelto come primo canale (cross-post, audience dev built-in, SEO resta nostro)
- **Indie Hackers post-mainnet** (decisione 2026-05-24): community IH vuole numeri veri anche se piccoli, testnet non funziona come prova
- **Product Hunt post-mainnet + risultati reali** (decisione 2026-05-24, aggiunto a Apple Notes Distribution Channels backlog): lancio one-shot, serve storia completa
- Reddit/Hashnode: valutazione futura post-Dev.to baseline. **Reddit ora attivo (S85, vedi sub-sezione Reddit sopra).**

### Newsletter / Mailing list (futuro)
- **Decisione S85**: valutare post-lancio V3 (Buttondown o Substack gratuito). Pre-V3 prematuro: nessuna baseline traffico, nessuna lista naturale da costruire.

### SEO / Google Search Console
- Baseline pre-S84 (audit A3-S78 + audit GSC CEO 2026-05-24): 256 impressions, 0 click, posizione media 10.7
- **SEO audit fix S84 SHIPPED 2026-05-24 (commit `c89c8cc`)**: title/description rewrite su 8 pagine pubbliche (home, roadmap, blueprint, diary, howwework, blog/, library, dashboard) + JSON-LD `WebSite` + `SearchAction` su home (chiude drift S47) + JSON-LD `Article` su template blog post (3 post live coperti, eredità automatica futuri) + `lastmod` ISO 8601 su sitemap-0.xml. Deploy Vercel verificato end-to-end. "Page with redirect" GSC diagnosticato come `www.bagholderai.lol → bagholderai.lol` 308 Vercel (legittimo, no action).
- **Action manuali Max post-deploy** (in §6 Vincoli): (1) GSC → Sitemaps → re-submit `sitemap-0.xml` (bypass index); (2) URL Inspection → request indexing su top 5 pagine; (3) check CTR 7-14gg per validare fix.
- Blog post indicizzazione: in attesa di nuovo crawl Google post-fix.

### Analytics — insight S80
- **Traffico reale ~25 umani/giorno** (30% bot da datacenter: Falkenstein, Helsinki, Nürnberg)
- Pubblico prevalentemente US (47%), attivo 18:00-02:00 CET
- **Funnel rotto:** home 34 visitatori → blog 4 (12%). Entry/exit sempre "/". Brief 80b CTA swap shipped come fix minimo, misurare 1 settimana.
- Payhip: 39 views maggio, 0 vendite, 0 ordini

### Target traffico (definiti S85)
- **3 mesi**: 50-80 visitatori/giorno
- **6 mesi**: 100-150/giorno
- **12 mesi**: 200-400/giorno
- Baseline attuale (~25/giorno) implica ×2 a 3 mesi, ×4-6 a 6 mesi, ×8-16 a 12 mesi. Distribuzione attiva (Dev.to + Reddit + RSS) è la leva primaria.

### Payhip
- Volume 1 + Volume 2 + **Volume 3 LIVE**: https://payhip.com/b/hCWNX (€4.99, "From Brain to Eyes", Sessions 53–82)
- Payhip store: https://payhip.com/BagHolderAI
- Redirect `/buy` ora punta allo store (non più a V1 singolo) — vercel.json aggiornato S87
- 39 views maggio (pre-V3 launch), 0 vendite, 0 ordini

### Ads & monetizzazione
- A-Ads live (revenue trascurabile). Buy Me a Coffee attivo. Nessuna sponsorship.

### A-Ads
- URL corretto da www.bagholderai.lol → bagholderai.lol (apex)
- Colori banner adattati al sito (#111622 sfondo, #6CCCFA accent)
- Embed code aggiornato 2026-05-22 (S80a, commit `2099a3c`), deploy Vercel auto-trigger su push.

### Analytics
- Umami Cloud + Vercel Web Analytics
- **22 data-umami-event su tutti i link Payhip** (S87): homepage Story (6), library shelf (12), library card, blog CTA (4), blog body inline. Source property per breakdown: `home-story-vN`, `library-shelf-vN`, `library-card-vN`, `blog-cta-vN`, `blog-cta-fallback-vN`, `blog-body-<slug>`
- **Pixel Dev.to nel feed RSS** (S87): `<img src="https://cloud.umami.is/p/0nHeF7vMT" .../>` appeso a `content:encoded` di ogni item. Traccia aperture articoli importati su Dev.to
- **5 funnel Umami configurati** (S86 handoff): Homepage→Blog→Articolo, Homepage→Dashboard→Diary, Homepage→Blog→Diary, Homepage→HowWeWork→Blueprint, Homepage→Library
- Documento di reference: `config/umami-session-26-05-2026.md`

### SEO — Semrush (S99 NEW)
- **Primo audit Semrush** (7 giugno 2026, S99): 97% site health, 0 errori, 3 warning (inflated a 13 dal doppio conteggio trailing slash). Fix: `trailingSlash: 'never'` in Astro + `"trailingSlash": false` in vercel.json (308 redirect). `llms.txt` creato (GEO). Commit `9787aa5`.
- **Semrush account attivo** su bagholderai.lol (free tier, piano gratuito). Crawl su 44/100 pagine. Prossimo crawl: schedulato automaticamente.
- **A-ADS banner verificato funzionante** (S99): ad-request regolari (30-400/giorno), fill rate 0% — problema lato network, non lato sito. Nessuna azione.

### SEO — Keyword Repositioning (S107)
- **Bing Webmaster Tools audit S107** (16 giugno 2026): 13 impression in 3 mesi, 0 click, 7 keyword — TUTTE varianti "crypto trading bot with Claude." Zero keyword su AI autonomy, AI CEO, one-person company, non-coder.
- **Gap identificato:** sito classificato dai motori come "crypto trading bot project." L'angolo differenziante (AI-as-CEO, autonomous AI, non-coder) viveva nei meta tag di alcune pagine ma non aveva massa critica di contenuto.
- **4 cluster keyword mappati:** (1) AI-as-CEO / AI running a business — differenziazione massima, (2) one-person company / solo founder + AI agents — topic caldo 2026, (3) non-coder / vibe coding — volume alto, (4) Claude + crypto trading bot — già rankiamo qui.
- **Brief S107 SEO** (brief `c1ee2df`, implementato `593c5fa`→`f2a20aa`, 16 giu): meta tag + micro-contenuto aggiornati su 7 pagine (Homepage, Blog, Diary, Dashboard, Blueprint, Roadmap, Library). Principio: nessuna keyword nel meta che il contenuto della pagina non supporti — per ogni meta tag modificato, aggiunta una riga di contenuto visibile.
- **Invariate:** How We Work (già allineata cluster 1), Income/The Experiment (appena pubblicata, meta già forte).

### Favicon
- **Favicon SVG brand** (S87, commit `eed66f0`): sostituito emoji 🎒 con SVG zaino blu sleepy (mascot brand). Apple-touch-icon 180×180 (bg dark `#0a0e17` + padding 15px) + favicon-32.png fallback per browser legacy.

---

## 3. Diary Status

**Sessione corrente: S107 COMPLETE** (SEO keyword analysis + meta+content su 7 pagine + site v2 redesign).
**Interludio scritto:** "Thirteen Impressions" (copre S106-S107: visual identity per umani + SEO identity per macchine).
- Volume corrente pubblico: V3 "From Brain to Eyes" (live). V4 in lavorazione (arc: NewsKeeper → go-live → results).
- Ultima entry diary: **S107** "The One Where Thirteen Strangers Said Who We Are".
- Prossimo check di congruenza diary: invariato.

**Volumi pubblicati:**
- Volume 1 "From Zero to Grid" (S1–S23, €4.99) → https://payhip.com/b/a4yMc
- Volume 2 "From Grid to Brain" (S24–S52, €4.99) → https://payhip.com/b/NHw53
- Volume 3 "From Brain to Eyes" (S53–S82, €4.99) → https://payhip.com/b/hCWNX (lanciato 27 maggio 2026)

**Volume corrente: 4** — "From Eyes to Live" (S83+, €4.99 planned). Aperto a S83. Arco narrativo: NewsKeeper build → go-live → primi risultati reali.

**Blog post pubblicati: 10** (ultimo: "Vibe Coding a Real Business", 2026-06-18 commit `acbed3b`; prec. "How a Non-Coder Manages 5 AI Brains", S104)
**Draft blog in coda: 2** (POST 2/5; vibe-coding **PUBBLICATO** 2026-06-18, commit `acbed3b`): `why-most-ai-trading-bots-fail.md` (**SEO già forte** — head keyword "ai trading bot" + FAQ completo + intro GEO; serve SOLO intro umana two-voice [+ eventuale reframe closing] → **priorità pubblicazione**), `ai-crypto-trading-bot-real-testnet-results.md` (parcheggiato, pieno di TODO, post-mainnet). Cadenza 1 ogni 1-2 settimane.

**Sessioni pendenti di diary:** verificare su Supabase `diary_entries` se S73/S74/S77/S78/S79 hanno docx pronti. Storico sessioni V4 in PROJECT_STATE §10.

**Draft diary seed in coda:** nessuno (seed V3 rimosso a S87).

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-28 (estemporanea) | **Decision 4.12 — BONK floor $5 confermato** | Anti-micro-buy. Revisione post-mainnet se `min_notional` cambia. Board-approved |
| 2026-06-28 (estemporanea) | **Decision 4.14 — Compounding: Opzione A (lotto fisso)** | Rischio costante e prevedibile a €100 di capitale. Board-approved |
| 2026-06-28 (estemporanea) | **Grid regime backtest approvato (Caso 2)** | Simulazione grid su 3 regimi storici BTC (bear giu-2022, bull nov-2024, laterale ago/set-2023), parametri congelati vs hold. Benchmark pre-deployment + base per contenuto pubblico. Brief `S111_grid-regime-backtest` pronto, CC lo riceve dopo S110d |
| 2026-06-27 (S110) | **Go-live experiment approvato** | Collaudo €100 sequenziale BTC→SOL→BONK (solo grid, stesso €100 riciclato). Allocazione €600 post-collaudo: BTC €250 fisso + SOL €150 fisso + 2 slot TF €100+€100 (Tier 1-2, con exit thresholds). TF = grid-selector, niente fondo shitcoin separato. Clone TF Tier 3 in paper post-mainnet = CASO 2. Cancelli rampa: a intuito di Max. Bug vs perdita: divergenza da spec = bug (rabbocco), regola eseguita = perdita (resta). Verdetto: -50% scrive capitolo, ciclo completo = verdetto vero. Victory Lap: C→B→A |
| 2026-06-27 (S110) | **3 brief CC prodotti** | S110c (USDT→USDC), S110d (tf-grid exit thresholds), S110e (NewsKeeper v1 shutdown + trend_scans retention) |
| 2026-06-27 (S110) | **Dashboard private fixate da CC (S110a/b)** | grid.html, tf.html, admin.html — tutto frontend, zero bot. Due decisioni Board **CHIUSE** (27-giu, racc. CEO confermate da Max, zero-codice): 4.12 floor BONK = **$5 fisso** (anti-rumore micro-buy; rivedere su mainnet), 4.14 compounding = **Opzione A lotto fisso** (rischio/trade costante) |
| 2026-06-25 (S109) | **Verdetto Sherpa 15gg: PASS per go-live** | Parametri protettivi stabili entro 24h. sell_pct flicker cosmetico (1-2bp/tick, 80-101 cambi in 14gg su SOL/BONK). Fix A/B/C rimandato a dopo osservazione regime change reale. Zero transizioni di regime nel periodo (extreme_fear continuo). Non blocca mainnet |
| 2026-06-25 (S109) | **Breadth signal Tier 3 → Tier 1/2: PARCHEGGIATO** | Analisi 6 mesi mainnet (422 coin, survivorship-safe): T3 NON anticipa rimbalzi T1/2 — semmai contrarian debole. F&G domina (corr -0.29 vs forward T1 7g), T3 correla 0.395 con F&G (ridondante). Soglia $2M filtra rumore ma non produce segnale. Ri-testare dopo regime risk-on sostenuto. Gamba 2 del volume framework CHIUSA (esito negativo) |
| 2026-06-25 (S109) | **Bug backlog azzerato + infra pre-mainnet shipped** | 4 bug chiusi (PortfolioManager rimosso, datetime deprecation 409→0 warning, exchange_order_id null fixato, validation_system aggiornato). Infra: slippage_buffer_pct colonna in bot_config (migration applicata), dust write-off come evento persistito, config chain 8 test e2e. Tutto committato + **restart Mac Mini FATTO** (runtime `7df7cca`, 22:03 CET) → fix LIVE |
| 2026-06-25 (S109) | **Mobile smoke test eliminato da Fase 1** | Max lo fa già quotidianamente. Eliminato come gate formale |
| 2026-06-22 (S108) | **Verdetto barometro v2: PASS qualità, INCONCLUSIVE come indicatore di trading** | N=2 flip in 13gg è insufficiente per validare il gate "flip vs BTC 24h forward return" (S100). Il barometro ha cross-validato con Tier B breadth (flash neutral 15-giu coincide con 19.6% bullish Tier B). NON blocca go-live grid. Sentinel wiring rimandato a dopo regime change sostenuto. Alternativa scartata: dichiarare PASS completo su dati insufficienti |
| 2026-06-22 (S108) | **Dashboard label: "Net realized profit" → "Realized profit from sells (post-fees)"** | Disambigua margine realizzato dal Total P&L. Shipped da CC (commit `c2598df`) |
| 2026-06-18 (S107) | **SEO meta + content su 7 pagine** — shift da "crypto bot" a "AI runs a business, crypto is the context" | 13 impression Bing tutte crypto. Principio: niente keyword senza contenuto che la supporti → per ogni meta tag, aggiunta riga contenuto visibile |
| 2026-06-18 (S107) | **Manifesto block con H2** "This is not a crypto project" | Senza heading tag, il testo era invisibile ai crawler. H2 dà peso semantico |
| 2026-06-18 (S107) | **Bot card reinserite in homepage** (tra snapshot e manifesto) | La scena SVG è invisibile ai crawler. Le card sono l'unico testo che spiega cosa fanno i 5 moduli. Scene per umani, parole per macchine |
| 2026-06-18 (S107) | **Draft blog voice strategy confermata**: vibe-coding e why-bots-fail richiedono intro umana (two-voice) prima della pubblicazione. testnet-results parcheggiato post-mainnet | Regola PARKED_blog_voice_strategy.md: tutti i post futuri → intro umana fissa + voce CEO sotto |
| 2026-06-18 (S107) | **Blog post nuovo Cluster 1 parcheggiato** (AI-as-CEO puro) | Nessuno dei 12 file (10 live + 2 draft) targettizza direttamente il cluster a differenziazione massima. Da scrivere in sessione dedicata, nessuna fretta |
| 2026-06-15 (S106) | **Site upgrade brief S106a approvato** — homepage con scena ufficio hero, nav a 6 voci con dropdown, manifesto block, eliminazione /office, pubblicazione /income, riordino dashboard, /news post-verdetto | Concept esterno (ChatGPT IA v1) usato come spunto, mediato con materiale esistente. Principio: "evolvere, non ricostruire". Caso 2 (non blocca mainnet) |
| 2026-06-15 (S106) | **Nav: dropdown "Under the hood ▾"** con How we work, Blueprint, Roadmap, The experiment | 7 voci → 6 voci. Le 4 pagine "meta" (spiegano il progetto) separate dalle pagine "prodotto" (Dashboard, Blog, Diary, News, Library) |
| 2026-06-15 (S106) | **/news in nav principale** post-verdetto barometro | Contenuto live differenziante (headline + sentiment AI + barometro), motivo per visite ripetute. Competitor tbot mostra stesse fonti senza label AI. Due scenari: validato (claim predittivo) o bocciato (trasparenza) |
| 2026-06-15 (S106) | **/income pubblicata** (noindex off, sitemap, dropdown, no WIP) | "€274 spesi per fare €0" è più potente ora che a €5. Il target audience (indie hackers, AI enthusiasts) apprezza l'onestà, non il successo. Il €0 è il contenuto |
| 2026-06-15 (S106) | **/office eliminata** come pagina standalone | Scena ufficio spostata in homepage hero. Pagina duplicata non aggiunge valore. Easter egg serio = progetto futuro a sé, non copia |
| 2026-06-15 (S106) | **Library resta "Library"** — NO rename a Logbook/Mission Logs | "Logbook" collide con Diary. "Library" non è rotto, è una libreria con libri |
| 2026-06-15 (S106) | **Sezione "The team" rimossa dalla homepage** | La scena ufficio mostra il team visivamente, /howwework lo spiega testualmente. Tre fonti per la stessa info = ridondanza |
| 2026-06-15 (S106) | **Dashboard: chart `type="linear"`** (fix curve smooth) | Curve spline inventano valori intermedi mai esistiti. In finanza si usano segmenti dritti. Contraddizione su sito di trasparenza radicale |
| 2026-06-15 (S106) | **Brave Creators (BAT tip jar) TAGLIATO** dalla lista | Zero urgenza, zero trigger prevedibile. Se serve, il setup è documentato |
| 2026-06-15 (S106) | **Post Haiku su X: NON paused** — sistema attivo, Max filtra manualmente (approve/discard via Telegram) | Memoria CEO era sbagliata ("paused"). Il sistema gira, Max scarta quando vuole. Nessuna azione richiesta |
| 2026-06-13 (S105) | **Dust write-off de-parcheggiato + soglia = minimo vendibile Binance** (predicato unico `is_dust`, ~6 gate griglia; `$0,50` di state_manager eliminato, tenuto solo come fallback no-filtri) | Polvere 0,000096 SOL (~$0,006) ha congelato la griglia SOL ~5gg disinnescando il re-entry forzato, in silenzio (no ERROR/alert). GATE A2 (copertura BONK del fix S73) VERDE prima di rimuovere il $0,50. Commit `87eeda9`, 228 test, reversibile. ANTI-ASSENSO: CC ha smontato il brief CEO su 3 punti (predicato già esistente / incoerenza soglie $0,50 vs $5 non vista dal CEO / ~6+6 punti non 3), CEO ha accettato tutte e 3 (addendum) |
| 2026-06-12 (S104) | **Volume-PnL analysis: NESSUNA correlazione** — no filter volume sullo scanner | CEO ha trovato pattern apparente (basso volume → migliori ritorni) su 56 coppie paper trading. CC ha dimostrato che 32/56 erano righe sintetiche (orphan closures, PnL=0). Su 19 trade reali: Pearson 0.03. Validazione esterna (12 mesi Binance, 162 coin): confermata assenza correlazione. TF reale: WR 52.6%, PnL +1.49% (dati puliti). Anti-surge guard (p=0.09) parcheggiato post-barometro |
| 2026-06-12 (S104) | **Spese progetto mappate: ~€274 totali** (Claude Max €270, Haiku $1.77, Grok $1.11, dominio $1.54, infra €0) | 98.5% del costo = abbonamento AI. Tutto il resto su free tier. CEO non ha accesso al billing dashboard Anthropic → gap operativo. Soluzione trovata: Anthropic Admin API (Usage & Cost endpoint). Implementazione parcheggiata |
| 2026-06-12 (S104) | **"The Experiment" = pagina unica revenue+spese+trading journey** | Sostituisce il concept "Passive Income Dashboard". Scaffold privato (noindex). Si popola con dati reali progressivamente. Non pubblicare fino a decisione Board |
| 2026-06-12 (S104) | **Area 2 audit: RISOLTO e automatizzato** (Cowork monthly). Rimosso da parking lot | Era flaggato "mai eseguito" da S78 — memoria CEO stale. In realtà completato e schedulato via Cowork (audit automatico mensile + email via Gmail draft + Apps Script) |
| 2026-06-12 (S103) | **4 parametri protettivi → Sherpa-managed dinamici** (`BOARD_TABLE` per regime × volatility tier LOW/MID/HIGH) | Ribalta S102 "statici Board-only". Debounce 24h su coppia (regime,tier) persistito in `sherpa_board_state` (aggiunta CC, non nel brief). Cooldown 24h su override manuale invariato |
| 2026-06-12 (S103) | **Dashboard §2 pubblica redesign: brain pipeline verticale** (NewsKeeper→Sentinel→Sherpa) | Card live full-width con connettori BAROMETER(shadow)/REGIME. Polling 5min. Anche TF/Grid trader cards ridisegnate. Token nuovo `--color-bot-news`. Sherpa pill: DRY_RUN→LIVE |
| 2026-06-12 (S103) | **Dashboard privata grid.html: 3 sezioni per coin** | Trading by Board / Grid by Sherpa / Security by Sherpa. Min Profit spostato da Grid a Security |
| 2026-06-12 (S103) | **Memoria CEO compattata**: da 29 a 21 voci (su 30 max) | 4 rimosse, 4 fuse, 2 aggiornate. Slot fisso #21 per agenda prossima sessione |
| 2026-06-11 (S102) | **Principio ownership parametri: Board = soldi, Sherpa = strategia** | Max: "Io controllo allocation, $/trade, skim. Sherpa controlla tutto il resto. Se sovrascrivo, cooldown 24h." Tre frasi che risolvono idle, circuit breaker, sell penalty |
| 2026-06-11 (S102) | **Sherpa GO LIVE su testnet** (brief S102b, env flag `SHERPA_MODE=live`). **LIVE dal restart 21:42 CET, orchestrator PID 91177.** Scrive buy_pct, sell_pct, idle_reentry_hours — verificato DB: al primo tick 9 scritture `changed_by='sherpa'` (BTC 0.65/1.05/5.6, SOL 0.65/1.53/5.6, BONK 3.0/1.75/5.6) | DRY_RUN non produceva dati utili (cap ±30% su config congelata = 50K righe identiche). Testnet = zero rischio finanziario. CC report S102: tutti e 5 regimi implementati, coin-agnostic confermato |
| 2026-06-11 (S102) | **idle_reentry_hours: Opzione C** — Sherpa riporta idle dentro il range di design (0.5-6h). L'8h attuale era un default mai rivisto | Il cap ±30% rende la transizione graduale (8→5.6→...→target in 2-7 tick). In extreme_fear stop_buy=ON rende idle irrilevante |
| 2026-06-11 (S102) | **4 parametri restano Board-only**: stop_buy_drawdown_pct e min_profit_pct universali (uguali per tutti i coin); dead_zone_hours e stop_buy_unlock_hours per-coin ma statici (microstructura, non regime). Default automatici per coin nuovi | Nessuno dei 4 ha una tesi forte per diventare dinamico per regime. Sicurezza ≠ strategia |
| 2026-06-11 (S102) | **Write guard Sherpa shippato** (commit `a867179`) + **battito liveness LIVE** (`ce92ed2`). Volume atteso: ~18 righe/gg (-99%) | Filtro write-on-change esisteva (S79c) ma bypass su stop_buy in extreme_fear. Fix: gate flip-based + heartbeat 4h. In LIVE il battito tiene viva la lampada dashboard + distingue "vivo" da "bloccato" |
| 2026-06-11 (S102) | **NewsKeeper v2 "Barometro" shadow check T+36h: sano** | 203 segnali, 0 fallback Haiku, flip neutral→bearish a T+4h, stabile bearish 31h. abstain_frac=0. Verdetto T+14 ~23 giugno |
| 2026-06-10 (S101) | **Dashboard §3 "Portfolio value" redesigned** (commit `8ea0a23` + `ce5602d`). Single MTM line, fill semantico, fix TF $100→$0, big number ancorato a snapshot reale, sticker "Fresh start" su entrambe le card. Scoperto bug snapshot day-1 (cycle-mixing hypothesis) — brief parked pre-reset luglio | Max non capiva il grafico e aveva ragione due volte: confuso E sbagliato. Il chart mostrava −$102.71 invece di −$2.71 (stessa famiglia bug S97b) |
| 2026-06-10 (S101a) | **Two-voice caso-zero shipped su canonical** (commit `944e74d`). `thirty-two-hours` → `author: both`, intro Max verbatim, firma `— Max & Claude`. Dev.to: blocco-tesi + short/long version pronti, in attesa settings | Primo post col nuovo standard. CC ha corretto una contraddizione nel brief CEO (firma singola vs README §3 firma congiunta). Anti-assenso funzionante |
| 2026-06-10 (S101) | **Ordine pubblicazione SEO-GEO invertito: 3→4→2→5** | Reddit comment stats: thread beginner-angle 4× views vs tecnico (4.9K vs 1.1K). Non-coder angle è Max's actual story. Keyword "ai trading bot" (+900%) non scade |
| 2026-06-10 (S101b) | **SEO_RULES.md creato, caso GSC "Couldn't fetch" CHIUSO** | Sitemap red line = cached artifact, non blocco reale. 381 impressions, pos 8.8. Playbook 5 step documentato |
| 2026-06-10 (S101) | **Primo data point GEO: citazione Microsoft Copilot** (Bing Webmaster Tools) | `claude-code-crypto-trading-bot` citato da Copilot in risposta a query utente. Prova empirica che la strategia SEO/GEO S95a funziona meccanicamente |
| 2026-06-09 (S100) | NewsKeeper diventa "barometro" 3-stati (bear/neutral/bull, bidirezionale) | La T+7 review ha provato che l'unità per-item è sbagliata, non solo mal-calibrata: 109 segnali/giorno = ~10 eventi veri + 1 narrativa ripetuta. Il valore è il clima aggregato anticipato sul prezzo, non il singolo articolo. Severità per-item dismessa come driver |
| 2026-06-09 (S100) | Architettura C + voto pesato-confidenza + dedup event-level (terna unica) | C recide l'accoppiamento Python↔Haiku che causava il bug direzione (Haiku legge la polarità, il lexicon perde il veto). La dedup event-level è la chiave di volta: senza, un errore su una storia ripetuta 20× viene amplificato, non mediato (CC, anti-assenso). Confidenza bassa → astiene |
| 2026-06-09 (S100) | Gate falsificabile: shadow ~2 settimane, validazione su prezzo BTC 24h — NON su F&G | Validare sul Fear & Greed è circolare: il F&G è costruito in parte sulle stesse news → si anticiperebbe il proprio riflesso (CC). Niente cablaggio in Sentinel finché lo shadow non prova che i flip anticipano il prezzo. Lente di regime: mercato solo-bear → verdetto parziale |
| 2026-06-08 (S99b) | **Anti-slippage v2 SHIPPED** (brief S99b-b, 3 parti: dashboard text fix + penalty in NEXT SELL IF + slippage penalty su sell profittevoli; commit `e26e67c`) | BONK burst: 5 sell in 4 min, slippage 3-4% ma penalty mai attiva perché tutte profittevoli. Lo slippage abbassa la sell ladder (feedback loop). Nuova regola: slippage > 1% su sell profittevole → penalty si arma. Soglia unica, non-cumulativa |
| 2026-06-08 (S99b) | **Board override: SOL sell_pct 1.0% → 1.5% (manuale)** | Max ha fatto da Sherpa umano: SOL vendeva con profitto troppo piccolo a 1.0%. `changed_by='manual-ceo'`. Conferma che il workflow Sherpa automatico serve |
| 2026-06-08 (S99b) | **Dashboard "per-lot" text corretto** | Fossile FIFO pre-S70. Il bot usa avg_cost dal S70 FASE 2, il testo non era mai stato aggiornato. Fix cosmetico, 1 riga |
| 2026-06-07 (S99) | **Trailing slash + llms.txt SHIPPED** (brief S99a, commit `9787aa5`). Fix SEO: Astro `trailingSlash: 'never'` + Vercel `trailingSlash: false` (308 redirect). `llms.txt` GEO creato in `public/` | Primo audit Semrush: 9 warning erano 4 pagine contate doppio. llms.txt: impatto pratico incerto ma costo ~zero e allineato a posizionamento AI-native |
| 2026-06-06 (S98) | **Adaptive Sell Penalty SHIPPED** (brief S98a, commit `507ebd6` + `a7d644d`) — guardia post-fill: se un sell Strategy A filla sotto avg_cost, il bot alza sell_pct dell'ultimo slippage osservato; sell profittevole resetta a base | Incidente BONK: 7 sell in 6 min, tutti in perdita per slippage testnet (ticker ok, fill −4/−14%). Strategy A checkava pre-fill, non post-fill. Guardia proporzionale, adattiva, auto-guarigione |
| 2026-06-06 (S98) | **Board override: penalty da cumulativa a ultima perdita** | Design v1 (CEO) sommava tutte le perdite → BONK congelato a 31.3%. Max ha identificato il freeze: le 7 perdite non sarebbero mai accadute con la guardia attiva, il cumulativo bootstrappava da storia non guardata. Design v2 (Board): penalty = ultimo slippage osservato. Più semplice, auto-guaribile, nessun deadlock |
| 2026-06-06 (S98) | **tbot competitive analysis completata** (report S93b, read-only). Conferma moat: accounting onesto + multi-brain + news classificata. Tre mosse proposte: /news pubblica PARKED (serve Haiku classifier), tabella regime PARKED (serve più dati), blog accounting trap IN PIPELINE | L'analisi conferma: il competitor ha architettura più stretta (solo trend-follower), numeri rotti (nostro bug S96b), stesso slippage BONK al quadrato (−52% su microcap). Nessun contatto, nessuna modifica al sito |
| 2026-06-05 (S97) | **Phantom-holdings-audit SHIPPED** (brief S97a) | Grep sistematico: 9+ cluster dove `state.holdings` (include phantom testnet) guidava decisioni economiche. Tutti fixati → `managed_holdings`. Sell-side round-trip pendente (regola S96b: serve un trade vero). Su mainnet è no-op (phantom=0) |
| 2026-06-05 (S97) | **Decisione 73c aggiornata** (force-liquidate → managed) | Brief 73c (S73) vendeva `state.holdings` su force-liquidate. S96b ha dimostrato che vendere phantom = realized spazzatura. S97a aggiorna: force-liquidate usa `managed_holdings`, commento 73c nel codice allineato |
| 2026-06-05 (S97) | **NewsKeeper daily digest: concept approvato, scope S3** | Strada A: Haiku riceve tutte le headline 24h, produce risk score 3 livelli (calmo/alert/tempesta). NON produce BUY/SELL. Strada B (clustering) parcheggiata per volume >50 headline/giorno. Timing: post quality review T+7 (~8 giugno) |
| 2026-06-05 (S97) | **Sherpa DRY_RUN durante extreme fear: lasciato intenzionalmente** | BTC -15%, Fear&Greed a 11, grid comprano in extreme_fear perché Sherpa non scrive stop_buy. Board: è testnet, soldi finti, dati gratuiti. La roadmap Sherpa non cambia |
| 2026-06-05 (S97) | **Site redesign "Pastel Sticker v2" LIVE** | Merge e deploy completati da Max. Non più pending |

> Decisioni **S88→S96 archiviate in S105** (2026-06-13); S81→S87 in S92; S80 e precedenti in S82 — tutte in `audits/BUSINESS_STATE_archive.md`. Storico completo anche in git history.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **Brief `2026-06-28_S111_grid-regime-backtest`** | Da assegnare dopo completamento S110d | Non gate per mainnet |
| **[S108 NEW] CMC Fear & Greed come seconda fonte Sentinel** | Brief futuro | Nuovo file `cmc_fng.py` accanto a `alternative_fng.py`. Usa API key CMC già in `.env` (endpoint `v3/fear-and-greed/historical`). Logga valore in `sentinel_scores.raw_signals`, nessuna modifica a `regime_analyzer`. Osservare e confrontare con Alternative.me per settimane prima di decidere. Binance F&G non ha API pubblica; CMC (Binance-owned dal 2020) è il proxy più vicino |
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
| [S100 NEW] NewsKeeper v2 "barometro" — build SHIPPED + shadow LIVE | In attesa: verdetto T+14 (~23 giu) | 185/185 test, 1 bug dedup (rappresentante stale) trovato in review avversariale e fixato. **Committato/pushato `c8774db` + shadow LIVE Mac Mini (pid 97566), accanto a v1, NON in Sentinel** (CC corregge il "NON committato" del draft: Max ha autorizzato commit+push+lancio in S100). Tabella nuova newskeeper_regime; per-item arricchito (relevance/polarity/event_key). SCOPE newskeeper-v2-barometro |
| **[S81 NEW] Cross-post automation Dev.to + Indie Hackers** | Decisione rimandata post-weekend | Quando un post va live su `web_astro/src/content/blog/`, script che pubblica su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. ~2-3h stimato |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **NewsKeeper v2 Barometro verdetto** | Nessuna data fissa (era ~23 giu) | T+14 raggiunto, esito: PASS qualità / INCONCLUSIVE prezzo (N=2 flip insufficiente). Esteso fino a regime change sostenuto (neutral/bullish >24h). Non blocca go-live grid. Dettagli in diary S108 |
| **SEO+GEO POST 2 drafting** | ~metà giugno | "Why Most AI Trading Bots Fail (And What Ours Did Wrong Too)" — keyword: ai trading bot. Cadenza 1 post ogni 1-2 settimane |
| **Apple Notes pulizia: cancellare 8 note obsolete (Max)** | A discrezione Max | 4 note attive da mantenere, 8 obsolete da cancellare manualmente |
| **Go-live mainnet** | Nessuna data fissa | Fase 1 chiusa: tutte le 9 domande esperimento risposte. Restano: 3 brief CC (USDC, exit thresholds, NK cleanup) + annuncio Binance MiCA (entro 30 giugno) + Board approval |
| **Sherpa LIVE su testnet (7/7 parametri)** | ✅ DONE (S102+S103) | Scrive TUTTI E 7 i parametri: buy_pct, sell_pct, idle_reentry_hours + stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours, profit_target_pct. I 4 protettivi via lookup (regime × volatility tier) con debounce 24h |
| **Volume 4** | Nessuna deadline | In accumulo da S83, arco narrativo NewsKeeper build → go-live |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). PID/runtime dettagliati in PROJECT_STATE §1+§7.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Revenue automation completa (/income)** | La pagina /income esiste come scaffold privato, ma l'automazione fonti (Payhip, BMC, Umami API) è rinviata al primo euro: a €0 darebbero "0" → over-engineering. Solo Umami ha già un connettore. Haiku costs: soluzione Admin API trovata, parcheggiata |
| **Pagina /news pubblica** | Pianificata (nav principale, brief S106a) ma bloccata dal verdetto barometro v2 (~23 giugno). Il brief documenta struttura e due scenari (validato/bocciato). Non costruire prima. Fonte moat: analisi tbot S98 (lui mostra gli stessi 3 feed RSS ma senza label AI → quando esponiamo, lo battiamo con sentiment/severità) |
| **Easter egg /office interattivo** | L'idea di una pagina dove clicchi ogni bot ed entri nella sua "stanza" con dati dettagliati è parcheggiata. Se si fa, è un progetto a sé — non una pagina duplicata della homepage (la scena ufficio va nell'hero, /office standalone eliminata in S106a) |
| **Tabella performance per regime su dashboard** | Parked fino a profondità dati sufficiente (testnet_2 ha ~2 giorni). Fonte: analisi tbot S98 |
| **Sherpa controlla 7/7 parametri Grid** | LIVE su testnet. I 3 strategici (buy/sell/idle) scalano con volatility multiplier continuo. I 4 protettivi (stop_buy_dd/unlock, dead_zone, min_profit) usano lookup discreto per (regime × volatility tier) con debounce 24h. Board-only restano SOLO: allocation, $/trade, skim |
| **BONK grid — RISOLTO** | Era bloccato dalla guardia 72a (deficit 99,91% dopo il reset mensile testnet). Sbloccato dal clean slate S96a (cycle tagging `testnet_2`): ripartito pulito il 2026-06-04, $150 cash, holdings 0, guardia passata |
| **Paper trade re-import** | Backup esiste (`/Volumes/Archivio/bagholderai/audits/2026-05-08_pre-reset-s67/`, 51.943 righe JSONL) ma non serve re-importarlo nel DB. Disponibile per narrativa/diary quando serve |
| **Audit Area 2 manuale on-demand** | Non più necessario: Area 2 è automatizzata (Cowork mensile, S104) come Area 1 e Area 3. Tutte e 3 le aree girano schedulate + notifica Gmail/Apps Script. Vedi §4 (S104) + PROJECT_STATE §9 |
| **Micro-brief `datetime.utcnow()` deprecation + cleanup PortfolioManager** | Low priority, scoperti in S89 (audit Area 1). Parcheggiati in Apple Notes todo. Toccano `bot/` runtime → fuori scope housekeeping. Tracciati in PROJECT_STATE §8 |
| **Go-live mainnet €100** | Task 1.3 CHIUSO (S110). Restano solo i 3 brief CC + decisione exchange + Board approval |
| **NewsKeeper v1** | Probabilmente ridondante (v2 PASS). V1 scrive 3.175 righe che nulla legge. Brief S110e chiede a CC di verificare prima di spegnere |
| **TF-Scout (Tier 3 shitcoins)** | Post-mainnet. TF clone in paper/testnet (CASO 2). trend_scans ha solo 14gg di retention — brief S110e chiede fix |
| **Grok/X scanner module** | Post-mainnet. Richiede API X premium (~$200/mese), giustificabile solo con MRR positivo |
| **NewsKeeper Sessions 2-4** | Session 1 live (RSS + regex, standalone Mac Mini). S2 priorità: Haiku classifier (RSS non ha sentiment nativo) |
| **Nessuna nuova fonte dati per NewsKeeper** | API news gratuite morte (CryptoPanic, CoinDesk). RSS + Haiku resta il piano. Niente budget per news API paid pre-mainnet |
| **Nessun cross-post automatico** | Dev.to e IH manuali. Automazione in valutazione post-baseline |
| **HN come canale** | Shadowban Cart0ne. Nuovo account non urgente — altri canali prioritari |
| **Futures/hedging** | Parcheggiato S90+. Capitale >€100, stack separato, KYC aggiuntivo. Post-mainnet |
| **Partnership / sponsorship** | Pre-traction |
| **Breadth Tier 3 come segnale Sentinel** | PARCHEGGIATO (S109). Analisi 6 mesi non supporta l'ipotesi (contrarian debole, ridondante con F&G). Ri-test dopo regime risk-on sostenuto. Script deterministico riutilizzabile (`scripts/breadth_analysis_s109.py`) |

---

*Prossimo aggiornamento: post verdetto barometro NewsKeeper v2 (~23 giugno) o pre-go-live mainnet, whichever comes first.*
