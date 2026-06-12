# BUSINESS_STATE.md

**Last updated:** 2026-06-12 — Session 103 (Sherpa Board params + dashboard brain pipeline + memory compaction). Cap file 50KB (Max S95, CLAUDE.md §2b). Cadenze audit canoniche in PROJECT_STATE §9. Prec.: S102 (Sherpa coherence audit + GO LIVE testnet).
**Updated by:** CEO (update S103 via brief `config/S103_BUSINESS_STATE_update.md`) — applicato da CC
**Basato su:** PROJECT_STATE.md aggiornato 2026-06-12

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 10 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, terms, privacy, blog infrastruttura pronta).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

### Frontend internals (S86, NUOVO)
- **Homepage: status badge dinamico LIVE** — tabella Supabase `project_status` (1 riga, RLS anon-read, trigger `updated_at` auto), aggiornabile via plain SQL UPDATE da CEO/Max/CC. Box full-width sotto l'hero, palette teal `#5DCAA5`, formato `emoji + status_text + Session NN · Updated Xh ago`. Messaggio attuale: 📖 "Collecting brain data before going live · Volume 3 just dropped" (aggiornato CEO S87). Zero deploy per cambiarlo.
- **Admin dashboard: regime overlay bands LIVE** — bande di sfondo colorate fear/greed/neutral sui 3 chart `admin.html` (TREND, Sentinel fast vs Sherpa, Parameters History). Palette finanziaria mirror di Widget A (S77 LIVE — extreme_fear cyan-light → extreme_greed red). Alpha bumped (0.20/0.14/0.10) per visibilità su regime uniforme (testnet "fear" da 5+ giorni). Legenda regime + bonus fix x-axis labels range-aware (HH:MM↔DD/MM).
- **Widget B (77c, standalone regime timeline): KILLED** — regime overlay copre lo stesso bisogno con meno clutter visivo (bande sui chart esistenti invece di un quarto chart dedicato). Brief 77c archiviato in `briefresolved.md/`. Widget A (banner regime istantaneo, S77 LIVE) resta complementare.
- **Prossimo step frontend**: portare grafici Sentinel/Sherpa su dashboard pubblica (`/dashboard` o `/sentinel`). Gated da (1) validazione regime overlay con dati live + (2) Sherpa Sprint 2 verde dopo Brain Analysis 2.

### Audit & Remediation (S88, NUOVO)
- **Audit Area 2 completato** (primo mai eseguito) — verdetto CON RISERVE. 0 CRITICAL · 6 HIGH · 12 MED · 12 LOW. Report: `audits/audit_report_20260527_area2_coherence.md`. Riserve principali: sito pubblico in drift 1-2 settimane (dashboard diceva Sentinel/Sherpa "not yet deployed", roadmap.ts ferma al 19 maggio, NewsKeeper assente), AUDIT_PROTOCOL.md era un vecchio request non un protocollo, regola cadenza Area 2 mai applicata.
- **5 brief di remediation prodotti (88a→88e), ~5-7h CC. 4/5 SHIPPED in S88** (2026-05-27, stessa sessione — non separate come da piano iniziale): 88b public site catch-up (roadmap S80→S87 + NewsKeeper Phase 14 + dashboard Sentinel/Sherpa LIVE/DRY_RUN), 88c state files cleanup (PROJECT_STATE <40KB + 6 drift fix), 88a audit meta (AUDIT_PROTOCOL.md riscritto a protocollo vero + trigger Area 2 event-based), 88e brief hygiene (config/parked). Tracking in `audit_remediation_cover_sheet.md`.
- **Resta solo 88d** (UI debts: botData homepage da Supabase + banner fear regime + fallback diary), sessione dedicata.

### Sito (stato pubblico)
TestnetBanner globale, Reconciliation table pubblica su /dashboard. **TF live card on home + dashboard SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)** — "dal dottore" SVG sostituito con card stile Grid (orange accent, mirror frame), hero text aggiornato a "$500 Grid + $100 TF (Tier 1-2)", pipeline arrow "I tried, your turn" → "TF picks, Grid manages". **Homepage CTA swap SHIPPED (Brief 80b)**: "Read the blog" primario, "Read the diary" + "Live numbers →" secondari outline. **Homepage layout update SHIPPED LOCAL S82 (2026-05-23, no push)**: sezione Blog sotto hero (ultimi 3 post cliccabili), sezione Diary spostata sotto Bots. **Watchtower + Sherpa cards SHIPPED LOCAL S82**: card Sentinel→`THE WATCHTOWER` (duo Sentinel + NewsKeeper, primo cameo pubblico del 5° bot dim/locked) + card Sherpa→`SHERPA Parameter Tuner` con mascot Claude Design (flag + mappa). 3 stat-row LIVE-WIRED via Supabase REST: REGIME (5 pip, oggi `FEAR`), BOTS (3 pip rossi auto-adatta), STOP BUY (1 pip, oggi OFF). Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped). **Push S82 deferito**: in attesa del brief newskeeper Board prima di rivelare il cameo pubblicamente.

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No"
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money"
- Post 3 LIVE 2026-05-19: "When Your AI CEO Lies About the Numbers"
- **Post 4 LIVE 2026-05-28: "How Three Claudes Run a Company"** — bagholderai.lol/blog/how-three-claudes-run-a-company. Volume:3 / type:lesson. Meta/workflow post (CEO + intern + Haiku + Max). Pubblicato S90 commit `1b28e2a`
- **Post 5 LIVE 2026-05-31: "AI Is Useful. But It Doesn't Think Like We Do."** — bagholderai.lol/blog/ai-is-useful-but-it-doesnt-think-like-we-do. Ripubblicato da Dev.to (`noRss:true`), chiude drift blog↔Dev.to (audit A3)
- **Post 6 LIVE 2026-06-01: "The Solution Was One Sentence. My AI Took Two Days."** — bagholderai.lol/blog/the-solution-was-one-sentence. Type lesson, saga audit/overengineering (Human + CEO)
- **Post 7 LIVE 2026-06-02 — SEO+GEO POST 1: "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works."** — bagholderai.lol/blog/claude-code-crypto-trading-bot. Primo dei 5 post SEO+GEO (brief S95a), FAQPage schema. Vedi sub-sezione "Strategia SEO+GEO" sotto
- _(→ **7 post pubblicati** totali, coerente con §3. I "Post 6/7 PLANNED" qui sotto sono titoli di backlog, numerazione non sequenziale)_
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
- **Engagement S81:** commento dettagliato su "AI Agent Failure Modes Beyond Hallucination" (Maxim Saplin) — 6 failure modes mappati all'esperienza BagHolderAI con link UTM al blog. Pubblicato 2026-05-22.
- **Community engagement attivo (storico):**
  - Commento su "Is Writing a Tech Blog Still Worth It?" (Deneth Rajapaksha) → 2 like, risposta dell'autore che chiede il link al blog → reply con link UTM + invito feedback
  - Presentazione nel Welcome Thread v376 → risposta entusiasta di Lenard Francis (FastAPI AlertEngine) → reply dettagliato con 3 errori strategici del CEO, 3 link UTM, domanda di chiusura
  - Reply a Lenard Francis (confidence gating, AlertEngine) + Valentin Monteiro (architect bottleneck shifting). Entrambi nel Welcome Thread v376.
- **Strategia:** engagement first (commenti, risposte, conversazioni), contenuto secondo. L'algoritmo Dev.to premia le relazioni, non i post isolati. I commenti portano più visibilità del post stesso in fase iniziale.
- **Engagement S85:** Rohini Gaonkar (AWS) aggiunta al giro di interazioni attive (oltre Valentin Monteiro già citato).
- **Feed Import RSS da configurare (S85):** `https://bagholderai.lol/rss.xml` da incollare in `dev.to/dashboard/feed_imports`. Dev.to importa i nuovi post come bozze con canonical URL automatica al blog originale (no SEO duplicate penalty). Body completo via `<content:encoded>`.
- **Prossimi passi:** Post 3 cross-post settimana prossima, continuare engagement nei commenti, monitorare se le conversazioni portano click (UTM campaign `comment_deneth` e `comment_lenard`)

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

### Favicon
- **Favicon SVG brand** (S87, commit `eed66f0`): sostituito emoji 🎒 con SVG zaino blu sleepy (mascot brand). Apple-touch-icon 180×180 (bg dark `#0a0e17` + padding 15px) + favicon-32.png fallback per browser legacy.

---

## 3. Diary Status

**Sessione corrente: 103 BUILDING** (Sherpa Board params + dashboard brain pipeline + memory compaction). S102 → COMPLETE. S101 → COMPLETE.

**Volumi pubblicati:**
- Volume 1 "From Zero to Grid" (S1–S23, €4.99) → https://payhip.com/b/a4yMc
- Volume 2 "From Grid to Brain" (S24–S52, €4.99) → https://payhip.com/b/NHw53
- Volume 3 "From Brain to Eyes" (S53–S82, €4.99) → https://payhip.com/b/hCWNX (lanciato 27 maggio 2026)

**Volume corrente: 4** — "From Eyes to Live" (S83+, €4.99 planned). Aperto a S83. Arco narrativo: NewsKeeper build → go-live → primi risultati reali.

**Blog post pubblicati: 8** (ultimo: Post 8 "Thirty-Two Hours", 5 giugno 2026)
**Post SEO+GEO in coda: 4** (POST 2–5, cadenza 1 ogni 1-2 settimane)

**Sessioni pendenti di diary:** verificare su Supabase `diary_entries` se S73/S74/S77/S78/S79 hanno docx pronti. Storico sessioni V4 in PROJECT_STATE §10.

**Draft in coda:** nessuno (seed V3 rimosso a S87).

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
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
| 2026-06-07 (S99) | **Passive Income Dashboard: decisioni B+E approvate, implementazione PARKED** | B: teaser home + pagina dedicata `/income`. E: rischio €0 pubblico accettabile (target premia onestà). Obiezione CEO su timing: costruire il tabellone prima che il trading sia live rischia mesi di "€0 statico". Parked fino a post-analisi NewsKeeper/Brain + timeline go-live concreta |
| 2026-06-06 (S98) | **Adaptive Sell Penalty SHIPPED** (brief S98a, commit `507ebd6` + `a7d644d`) — guardia post-fill: se un sell Strategy A filla sotto avg_cost, il bot alza sell_pct dell'ultimo slippage osservato; sell profittevole resetta a base | Incidente BONK: 7 sell in 6 min, tutti in perdita per slippage testnet (ticker ok, fill −4/−14%). Strategy A checkava pre-fill, non post-fill. Guardia proporzionale, adattiva, auto-guarigione |
| 2026-06-06 (S98) | **Board override: penalty da cumulativa a ultima perdita** | Design v1 (CEO) sommava tutte le perdite → BONK congelato a 31.3%. Max ha identificato il freeze: le 7 perdite non sarebbero mai accadute con la guardia attiva, il cumulativo bootstrappava da storia non guardata. Design v2 (Board): penalty = ultimo slippage osservato. Più semplice, auto-guaribile, nessun deadlock |
| 2026-06-06 (S98) | **tbot competitive analysis completata** (report S93b, read-only). Conferma moat: accounting onesto + multi-brain + news classificata. Tre mosse proposte: /news pubblica PARKED (serve Haiku classifier), tabella regime PARKED (serve più dati), blog accounting trap IN PIPELINE | L'analisi conferma: il competitor ha architettura più stretta (solo trend-follower), numeri rotti (nostro bug S96b), stesso slippage BONK al quadrato (−52% su microcap). Nessun contatto, nessuna modifica al sito |
| 2026-06-05 (S97) | **Phantom-holdings-audit SHIPPED** (brief S97a) | Grep sistematico: 9+ cluster dove `state.holdings` (include phantom testnet) guidava decisioni economiche. Tutti fixati → `managed_holdings`. Sell-side round-trip pendente (regola S96b: serve un trade vero). Su mainnet è no-op (phantom=0) |
| 2026-06-05 (S97) | **Decisione 73c aggiornata** (force-liquidate → managed) | Brief 73c (S73) vendeva `state.holdings` su force-liquidate. S96b ha dimostrato che vendere phantom = realized spazzatura. S97a aggiorna: force-liquidate usa `managed_holdings`, commento 73c nel codice allineato |
| 2026-06-05 (S97) | **NewsKeeper daily digest: concept approvato, scope S3** | Strada A: Haiku riceve tutte le headline 24h, produce risk score 3 livelli (calmo/alert/tempesta). NON produce BUY/SELL. Strada B (clustering) parcheggiata per volume >50 headline/giorno. Timing: post quality review T+7 (~8 giugno) |
| 2026-06-05 (S97) | **Sherpa DRY_RUN durante extreme fear: lasciato intenzionalmente** | BTC -15%, Fear&Greed a 11, grid comprano in extreme_fear perché Sherpa non scrive stop_buy. Board: è testnet, soldi finti, dati gratuiti. La roadmap Sherpa non cambia |
| 2026-06-05 (S97) | **Site redesign "Pastel Sticker v2" LIVE** | Merge e deploy completati da Max. Non più pending |
| 2026-06-04 (S96) | **Clean slate tutti e 3 i grid bot (Opzione C)** — Board+CEO. Shippato: cycle tagging `testnet_1`/`testnet_2`, BONK ripartito pulito | Reset mensile testnet ha azzerato i wallet. Guardia 72a ha bloccato BONK. Invece di ricostruire la posizione, archiviamo i trade come `testnet_1` e ripartiamo come `testnet_2`. Campo `cycle` su trades/daily_pnl/snapshots/reserve_ledger/bot_config. Brief S96a |
| 2026-06-04 (S96) | **Testnet disclaimer obbligatorio su sito** — CEO. Live su home + /dashboard + grid | Banner fisso non dismissibile. Testo chiaro: dati sintetici, no soldi veri, saldi resettabili senza preavviso |
| 2026-06-04 (S96) | **Audit Area 2 backstop 120→60 giorni** — Board | Aggiornato AUDIT_PROTOCOL.md §2 e CLAUDE.md [1] |
| 2026-06-04 (S96) | **Blog check incrementale in audit Area 2** — CEO | Stessa logica diary: ancora "Blog coperto fino a" nel report |
| 2026-06-02 (S95) | **Dual-channel SEO+GEO content strategy adottata.** Brief S95a: 5 post con keyword validate. POST 1 live in produzione | Keyword data: "claude code" 100K–1M +9.900%, "ai trading bot" 10K–100K +900%. Le long-tail narrative proposte dal CEO avevano volume zero. Post Reddit FluoTest (703 upvote) ha validato GEO come canale acquisizione (ChatGPT cita risposte dirette → 131 signups zero ad spend) |
| 2026-06-02 (S95) | **LinkedIn company page + profilo "Max Cartone" approvati, timing post-redesign** | Ricognizione Claude in Chrome: 1 solo "AI CEO" dichiarato al mondo (Homains). Campo vuoto. LinkedIn ha alta autorità dominio per GEO (35% citazioni ChatGPT da LinkedIn). Profilo separato da quello reale di Max |
| 2026-06-02 (S95) | **Medium (@BagHolderAI) confermato attivo** con 2 post. Aggiunto ai canali distribuzione | Cross-post con canonical URL. Audience più ampia e meno tecnica di Dev.to |
| 2026-06-01 (S94a) | **Regex classifier morto per severity/direction, sostituito con Haiku S2 + Python pre-processing** (Brief S94a) | 65% FP, direzioni invertite, inutilizzabile per trading |
| 2026-06-01 (S94a) | **Feed macro aggiunti (BBC→CNBC Economy + MarketWatch).** BBC scartata post-verifica: contenuto general business, zero macro | Serve catturare Fed/tariffe/inflation prima che arrivino su testate crypto |
| 2026-06-01 (S94a) | **Daily macro feed check fino a T+7 (8 giugno)** | Max ha corretto il piano "aspettiamo 7 giorni", verifica attiva batte osservazione passiva |
| 2026-05-30 (S92) | **Protocollo cross-check anti-assenso su tre mandati (CEO / CC / Auditor)**, non un "Decision Panel" separato | La versione panel di CC rendeva Max corriere tra sessioni fresche; cablare un obbligo nel mandato esistente di ogni agente riusa il flusso, zero infrastruttura nuova. CEO: auto-obiezione nei brief + verifica critica del lavoro CC. CC: ≥1 obiezione tecnica prima di implementare. Auditor: caccia incoerenze deciso/implementato/reale |
| 2026-05-30 (S92) | **Convenzione naming brief/report**: `YYYY-MM-DD_SXX[z]_brief_SCOPE` / `YYYY-MM-DD_SXX[z]_RforCEO_SCOPE`. Chiave accoppiamento Auditor = sessione + SCOPE (slug identico ereditato dal brief) | L'Auditor non vede le conversazioni, lavora solo sugli artefatti; senza accoppiamento la cross-analisi è cieca |
| 2026-05-30 (S92) | **Zero retrofit file pre-S88**; grandfather alla baseline degli audit del 27/05 (S87) | Rinominare il passato mentre si pulisce il presente crea nuovo drift |
| 2026-05-30 (S92) | **Disaccordo cross-agente che non converge → sale a Max, sempre.** Risoluzione di Max → una riga in §4 (data — decisione — why) | Nessun agente ha l'ultima parola sulla DECISIONE; Max è il nodo di sintesi finale |
| 2026-05-30 (S92) | **Prodotto-metodologia: DIFFERITO, non bocciato.** Il libro/prodotto arriva DOPO il go-live | 39 views su Payhip misurano traffico, non prodotto sbagliato; cambiare prodotto non risolve un funnel vuoto. Go-live resta gated sui tre regimi di mercato, mai su scadenze esterne (contenuti/libro) |
| 2026-05-29 (S91) | **Brain Analysis 2 completata: 3 fix Sprint 2 validati** (coin-aware, oscillazione domata, amplitude cap). Sherpa tuning-side **pronto** ma **NON mainnet-bound** | L'analisi ha trovato due problemi a monte del tuning: **stop_buy morto** (gap regime extreme_fear — risolto stessa sessione) + **timing Sentinel lento** (slow loop 4h). Il tuning dei parametri è ok, ma il sistema non va a soldi veri finché questi due non sono chiusi |
| 2026-05-29 (S91) | **Fix stop_buy extreme_fear shippato + verificato live** (commit `ea4c7a8`), mapping F&G label-aware. Backfill storico: **NO** | Sentinel non emetteva mai `extreme_fear` (soglia `<=20` vs banda "Extreme Fear" alternative.me ~25) → freno Sherpa morto su tutta la finestra crash (0 righe). Fix label-primary. Verifica live: F&G=23 → `extreme_fear` + `proposed_stop_buy_active=true` su 3 coin. Solo fix-forward, storico non toccato (operativamente conta il futuro) |
| 2026-05-29 (S91) | **Reset testnet parcheggiato** (dopo stop_buy + Sentinel/NewsKeeper; possibile sblocco da rimbalzo di mercato). "Mai capitolare" resta solo per mainnet | Priorità ai fix architetturali prima di azzerare il testnet. Il principio "mai capitolare / no cash morto" si applica solo a mainnet; sul testnet un reset è accettabile dopo i fix |
| 2026-05-28 (S90) | **Spike guard fix A+B shipped** (commit `06a6c7c`). Option A variante Board: double fetch con conferma 50% dopo 5s pausa. Option B: cooldown 1 ciclo post dead-zone recalibrate | Root cause trade BTC 27/05 21:44 UTC: testnet spike $82,143 (mainnet $74,500) + dead_zone_recalibrate + sell trigger nello stesso tick → realized -$1.31. Variante Board doppio fetch è auto-adattiva cross-coin (vs soglia fissa proposta da CC). 129 test verdi, 8 nuovi. Restart Mac Mini 09:15 CET, runtime `673c941` |
| 2026-05-28 (S90) | **Dashboard "days observing" rimosso** (commit `751b18c`) | Contatore legato a ultimo trade, non a inizio regime → fuorviante dopo trade accidentali ("0 days observing" leggeva come informazione spuria). Regime label già comunica posture di watching, basta da sola |
| 2026-05-28 (S90) | **Cover V3 ottimizzate** (commit `b8ed22d`): PNG 4.6MB → JPG 231KB (−95%) | Cover V3 erano in PNG 2.2+2.4 MB (~30× rispetto a vol1/vol2 JPG 54-182KB). Convertite con sips a 424×600 / 600×600 q=85 allineate al formato dei volumi precedenti. Performance + bandwidth/Vercel |
| 2026-05-28 (S90) | **Prima presenza Reddit** (r/ClaudeAI, flair "Claude Workflow"). Zero link, zero sales | Storia del progetto come post di valore per la community, in attesa mod approval. Commento parallelo nel "Build with Claude Megathread" LIVE. Esecuzione della strategia "introduce → engage → earn credibility → mention book" parcheggiata in S87 |
| 2026-05-27 (S89) | **Audit Area 1 automatizzato via Cowork scheduled task** (monthly, sandbox Linux) | Notifica: bozza Gmail con marker `[AREA-XX]`, Apps Script `AutoSendDrafts` (account cartone@gmail.com) la invia automaticamente tra le 4-5am. Git push resta manuale (limite sandbox `.git/`). Primo run 2026-05-27, verdetto CON RISERVE, prossimo ~2026-06-26 |
| 2026-05-27 (S89) | **Brief 89a shipped**: test hygiene (32 legacy → archived + pytest.ini), dead code deprecated (4 metodi, tabelle `portfolio`/`sentinel_logs`), `requirements-scripts.txt` per tweepy | Remediation findings Audit Area 1 (H1/H2/M1/M3/L2). Pytest 121/121 green. Solo housekeeping, zero touch `bot/`, no restart |
| 2026-05-27 (S88) | **Audit Area 2 completato + 5 brief remediation** | Primo audit coerenza mai eseguito. Drift pubblico principale: sito 1-2 settimane indietro. 30 findings, 0 CRITICAL. 5 brief CC (88a→88e) prodotti per la remediation. Diary posticipato a post-remediation per scrivere report completo (candidato blog post) |
| 2026-05-27 (S88) | **Regola Area 2 riformulata: event-based** (Board approved) | Trigger obbligatori: (a) pre go-live mainnet, (b) pre lancio Volume Payhip, (c) nuovo brain/macro-feature, (d) backstop 120gg. Sostituisce "90gg" mai applicata. Owner accountability: Max. Implementazione in Brief 88a |
| 2026-05-27 (S88) | **NewsKeeper reso pubblico nel roadmap** (Board approved) | Phase dedicata in roadmap.ts. Tono onesto: Sprint 1 live (RSS + regex, ~60% FP), Sprint 2 planned (Haiku classifier). Non più nascosto come "Sentinel Sprint 3" |
| 2026-05-27 (S88) | **Trasparenza fear regime sulla dashboard** (Board approved) | Opzione A: banner "Watching market · Last trade May 16 · Fear regime active". On-brand con la storia "AI onesta che dubita". Implementazione in Brief 88d |

> Decisioni S81→S87 archiviate in S92 (2026-05-30) in `audits/BUSINESS_STATE_archive.md`. Decisioni S80 e precedenti archiviate in S82. Storico completo in git history e `audits/BUSINESS_STATE_archive.md`.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **[S102 NEW] Formalizzare parametri Board-only + default automatici coin nuovi** | S103 | Brief S103: documentare che stop_buy_dd, stop_buy_unlock, dead_zone, min_profit sono Board-only. Implementare default automatici (universali o per-coin basati su volatility multiplier) per quando si aggiunge un coin nuovo |
| **[S102 NEW] Regime stickiness innesto barometro↔Sherpa** | Post-verdetto T+14 (~23 giu) + primo regime non-bear | Fattibilità confermata CC: opzione (a)+(c), ~5-7h, 4 file. Barometro modula la velocità del cap, non la destinazione. NON costruire prima del verdetto |
| **[S99b NEW] Monitoraggio anti-slippage v2 su BONK testnet** | Osservazione | Soglia 1% con slippage strutturale 3-4%: BONK sarà penalizzato quasi sempre. Se si congela (deadlock), alzare soglia o renderla per-coin |
| **[S99b] Dashboard penalty in NEXT SELL IF** | ✅ DONE | runtime mirror espone `_sell_pct_penalty`, dashboard la include nella formula |
| **[S91 NEW] Integrità dati — `bot_state_snapshots` saldo grezzo** | 🆕 Da verificare | `bot_state_snapshots` fotografa il **saldo grezzo testnet (pre-funded)**, non la posizione €500 → verificare che **nessuna superficie pubblica** lo peschi. Minori: fallback `1,0×` non cappato in Sentinel; dead-band scritture Sherpa ✅ DONE (S102a write guard `a867179`) |
| **[S90 NEW] Option C — slippage buffer su percentage sell path** | TODO pre-mainnet, brief separato | Brief separato pre-mainnet. Estendere il pattern `SLIPPAGE_BUFFER_PCT=0.03` (già attivo su SWEEP/LAST_SHOT path da brief 78b) anche al path `_execute_percentage_sell` per chiudere completamente la finestra di rischio post-fix A+B |
| **[S90 NEW] Calibrazione parametri spike guard** (threshold 4% / confirm 50% / pause 5s) | Osservazione 7-14gg, poi decidere | Oggi i 3 parametri sono default argument della funzione `fetch_price_with_spike_guard`. Post osservazione: valutare se servono tunable per-coin via `bot_config` (BTC vs SOL vs BONK volatilità diverse). Voto CC: tenerli fissi finché dati live non suggeriscono altrimenti |
| [S83] NewsKeeper S2 | ✅ DONE (S94 + T+7 quality review S100) | V2 Barometro in shadow, verdetto T+14 ~23 giugno. Verdetto T+7: miglioramento netto sul regex (0 righe irrilevanti, 0 fallback, ~€6/mese), ma unità per-item sbagliata → redesign barometro. Bug direzione assorbito nel redesign (opzione C) |
| [S97] NewsKeeper S3 daily digest | Assorbito nel barometro v2 | Il "risk score 24h calmo/alert/tempesta" È l'aggregato del barometro (3 stati). Non più item separato |
| [S100 NEW] NewsKeeper v2 "barometro" — build SHIPPED + shadow LIVE | In attesa: verdetto T+14 (~23 giu) | 185/185 test, 1 bug dedup (rappresentante stale) trovato in review avversariale e fixato. **Committato/pushato `c8774db` + shadow LIVE Mac Mini (pid 97566), accanto a v1, NON in Sentinel** (CC corregge il "NON committato" del draft: Max ha autorizzato commit+push+lancio in S100). Tabella nuova newskeeper_regime; per-item arricchito (relevance/polarity/event_key). SCOPE newskeeper-v2-barometro |
| **[S99 NEW] Passive Income Dashboard** | PARKED (post go-live timeline) | Brainstorm CC+Max completo (`config/2026-06-07_S100a_brief_passive-income-dashboard.md`). Decisioni strategiche prese. Implementazione sospesa fino a timeline go-live concreta. Se manca poco: "coming soon". Se manca molto: aspettare |
| **[S88] Audit Area 2 remediation — 4/5 SHIPPED** | Resta 88d (UI debts) — verificare se il redesign li ha chiusi | Audit 2026-05-27 (CON RISERVE). 88a/88b/88c/88e shippati S88, resta 88d (UI debts). Il redesign Pastel Sticker v2 potrebbe aver risolto parte dei debiti UI → da verificare nella prossima sessione. Tracking: `audit_remediation_cover_sheet.md` |
| **[S82] Brief NewsKeeper architetturale Session 1** | ✅ DONE (S83) | Scaffold shippato commit `49473a9`. Module 1 RSS feeds live standalone Mac Mini PID 78098. Sessioni 2-4 ancora pending |
| **[S81 NEW] Cross-post automation Dev.to + Indie Hackers** | Decisione rimandata post-weekend | Quando un post va live su `web_astro/src/content/blog/`, script che pubblica su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. ~2-3h stimato |
| ~~Brief 81a Sherpa Sprint 2~~ | ✅ DONE (S81) | Shipped commit `3ba1132`. Verifica live: BTC/SOL/BONK proposals diversi |
| ~~Sito TF narrativa update~~ | ✅ DONE (S80) | "dal dottore" → card TF live shipped brief 80b commit `b8bdc12` |
| ~~Monitorare sitemap Search Console~~ | ✅ DONE (S84) | SEO fix S84 shipped commit `c89c8cc`: sitemap lastmod + JSON-LD + title/description. Action manuali Max post-deploy in §6 |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Integration test config reader chain** | Pre-prossimo brief bot_config | Gap strutturale scoperto S76. ~30-60 min |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |
| **Phantom BONK 1.37M** | ~~Bassa priorità~~ → SUPERATA | Clean slate S96 ha resettato tutto. Phantom ora è baseline testnet (1 BTC / 6 SOL / 18.446 BONK), gestito da `managed_holdings` post-audit S97a |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **NewsKeeper T+7 quality review** | ✅ DONE (S100, report shipped) | V2 Barometro in shadow, verdetto T+14 ~23 giugno |
| **NewsKeeper v2 Barometro T+14 verdetto** | ~23 giugno 2026 | Validare flip barometro vs ritorno prezzo BTC 24h. Se 14gg solo-bear: verdetto parziale, estendere. Esiti: promuovere (cablaggio Sentinel) o bocciare (→ /news, blog "esperimento fallito") |
| **Correzione feed CNBC Economy** | ✅ FATTA (S94, commit `8515378`) | BBC→CNBC Economy + MarketWatch. Restart Mac Mini 22:04 CET, CNBC contribuisce `haiku_s2` verificato. (Era "da dare a CC" nel paste, già shippata) |
| **Site redesign "Pastel Sticker v2"** | ✅ FATTO (S97, 2026-06-05) | Merge e deploy completati da Max, LIVE su bagholderai.lol. Rimovibile dalla lista vincoli alla prossima compaction |
| **SEO+GEO POST 2 drafting** | ~metà giugno | "Why Most AI Trading Bots Fail (And What Ours Did Wrong Too)" — keyword: ai trading bot. Cadenza 1 post ogni 1-2 settimane |
| **Apple Notes pulizia: cancellare 8 note obsolete (Max)** | A discrezione Max | 4 note attive da mantenere, 8 obsolete da cancellare manualmente |
| **Go-live mainnet** | Nessuna data fissa | Dipende da condizioni di mercato (bear+bull+laterale osservati). Sequenza: Sherpa LIVE testnet ✅ → osservazione → S103 parametri Board-only → barometro verdict (~23 giu) → Board approval → mainnet €100 |
| **Sherpa LIVE su testnet (7/7 parametri)** | ✅ DONE (S102+S103) | Scrive TUTTI E 7 i parametri: buy_pct, sell_pct, idle_reentry_hours + stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours, profit_target_pct. I 4 protettivi via lookup (regime × volatility tier) con debounce 24h |
| **NewsKeeper — prima analisi** | ~lun 1 giugno | Job 1 anti-rumore Haiku → Job 2 lead/lag vs Sentinel. Decide timing Sentinel (Phase B vs accelerare NewsKeeper) |
| **Volume 4** | Nessuna deadline | In accumulo da S83, arco narrativo NewsKeeper build → go-live |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). PID/runtime dettagliati in PROJECT_STATE §1+§7.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Pagina /news pubblica** | Parked fino a maturità NewsKeeper (Haiku live da S94, ma T+7 quality review ~8 giugno ancora pendente; il vecchio regex aveva ~60% FP → non si espone classificazione non validata). Fonte: analisi tbot S98 (lui mostra gli stessi 3 feed RSS ma senza label AI → quando esponiamo, lo battiamo con sentiment/severità) |
| **Tabella performance per regime su dashboard** | Parked fino a profondità dati sufficiente (testnet_2 ha ~2 giorni). Fonte: analisi tbot S98 |
| **Sherpa controlla 7/7 parametri Grid** | LIVE su testnet. I 3 strategici (buy/sell/idle) scalano con volatility multiplier continuo. I 4 protettivi (stop_buy_dd/unlock, dead_zone, min_profit) usano lookup discreto per (regime × volatility tier) con debounce 24h. Board-only restano SOLO: allocation, $/trade, skim |
| **BONK grid — RISOLTO** | Era bloccato dalla guardia 72a (deficit 99,91% dopo il reset mensile testnet). Sbloccato dal clean slate S96a (cycle tagging `testnet_2`): ripartito pulito il 2026-06-04, $150 cash, holdings 0, guardia passata. _(NB: le righe "Reset testnet — Rimandato" qui sotto sono ora superate.)_ |
| **Paper trade re-import** | Backup esiste (`/Volumes/Archivio/bagholderai/audits/2026-05-08_pre-reset-s67/`, 51.943 righe JSONL) ma non serve re-importarlo nel DB. Disponibile per narrativa/diary quando serve |
| **Sentinel Phase B** | Parcheggiata fino a post T+7 NewsKeeper (8 giugno) |
| **Sherpa testnet activation** | Bloccata da Brain Analysis che dipende da NewsKeeper pulito |
| **Audit Area 2** | Finestra scaduta, riprogrammare post-redesign |
| **Reset testnet** | Rimandato: prima i fix (stop_buy ✅ + Sentinel/NewsKeeper). Possibile sblocco da un rimbalzo di mercato. "Mai capitolare / no cash morto" vale solo per mainnet, non per il testnet |
| **Decisione timing Sentinel (Phase B vs accelerare NewsKeeper)** | Parcheggiata fino a post prima analisi NewsKeeper (lun 1 giugno) |
| **Scheduled task Area 2 non automatizzato** | Area 1 e Area 3 girano come Cowork scheduled task (Area 3 dal 2026-05-31, cadenza bisettimanale — vedi PROJECT_STATE §9). Resta solo Area 2 (on-demand pre go-live/lancio), da configurare in sessione dedicata |
| **Micro-brief `datetime.utcnow()` deprecation + cleanup PortfolioManager** | Low priority, scoperti in S89 (audit Area 1). Parcheggiati in Apple Notes todo. Toccano `bot/` runtime → fuori scope housekeeping. Tracciati in PROJECT_STATE §8 |
| **Go-live mainnet €100** | Bloccato da 4 pre-requisiti in sequenza: NewsKeeper build (S2-S4, ~3 sessioni residue) + Sherpa testnet LIVE (post Brain Analysis 2) + dry_run observation periodo standard + Board approval finale. Niente data fissa, gated da condizioni di mercato osservate (bear+bull+laterale) |
| **TF-Scout (Tier 3 shitcoins)** | Post-mainnet, esplicitamente parcheggiato. Richiede capitale extra e tolleranza rischio che oggi non abbiamo |
| **Grok/X scanner module** | Post-mainnet. Richiede API X premium (~$200/mese), giustificabile solo con MRR positivo |
| **NewsKeeper Sessions 2-4** | Session 1 live (RSS + regex, standalone Mac Mini). S2 priorità: Haiku classifier (RSS non ha sentiment nativo) |
| **Nessuna nuova fonte dati per NewsKeeper** | API news gratuite morte (CryptoPanic, CoinDesk). RSS + Haiku resta il piano. Niente budget per news API paid pre-mainnet |
| **Nessun cross-post automatico** | Dev.to e IH manuali. Automazione in valutazione post-baseline |
| **HN come canale** | Shadowban Cart0ne. Nuovo account non urgente — altri canali prioritari |
| **Futures/hedging** | Parcheggiato S90+. Capitale >€100, stack separato, KYC aggiuntivo. Post-mainnet |
| **Partnership / sponsorship** | Pre-traction |

---

*Prossimo aggiornamento: post prima analisi NewsKeeper (~1 giugno) o decisione Sherpa LIVE testnet, whichever comes first.*
