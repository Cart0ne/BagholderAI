# BUSINESS_STATE.md

**Last updated:** 2026-05-24 — Session 83 closure (con riferimenti a S84 SEO fix shipped same-day). (a) **NewsKeeper Brain #5 LIVE come scaffold standalone Mac Mini** (PID 78098, RSS feeds CoinDesk + CoinTelegraph + Decrypt, classifier keyword MVP rumoroso noto, ship as-is per osservazione 7gg data-first). Pivot Board-approved da CryptoPanic (free Developer tier discontinued 1 aprile 2026) → RSS zero-auth. (b) **SEO audit fix S84 shipped same-day** (commit `c89c8cc`): title/description rewrite su 8 pagine pubbliche, JSON-LD WebSite+Article, sitemap lastmod, drift S47 WebSite schema chiuso. (c) **Dev.to Post 3** cross-postato 24 maggio (22 readers, 0 reactions — account fresco, engagement da costruire). (d) **Volume 3 "From Brain to Eyes"** chiuso a S82, in rilettura. Lancio Payhip previsto settimana 26-31 maggio. **Volume 4 aperto a S83** — arco narrativo: NewsKeeper build → go-live → primi risultati reali. (e) Apple Notes pulizia: 4 attive, 8 obsolete da cancellare manualmente (Max). Todo riscritta per era V4/NewsKeeper. Distribution Channels: integrata strategia Reddit + post killer da nota HN obsoleta.
**Updated by:** CEO + CC
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-24 (S83 + S84 closure) + brief CEO BUSINESS_STATE update S83

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

### Sito (stato pubblico)
TestnetBanner globale, Reconciliation table pubblica su /dashboard. **TF live card on home + dashboard SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)** — "dal dottore" SVG sostituito con card stile Grid (orange accent, mirror frame), hero text aggiornato a "$500 Grid + $100 TF (Tier 1-2)", pipeline arrow "I tried, your turn" → "TF picks, Grid manages". **Homepage CTA swap SHIPPED (Brief 80b)**: "Read the blog" primario, "Read the diary" + "Live numbers →" secondari outline. **Homepage layout update SHIPPED LOCAL S82 (2026-05-23, no push)**: sezione Blog sotto hero (ultimi 3 post cliccabili), sezione Diary spostata sotto Bots. **Watchtower + Sherpa cards SHIPPED LOCAL S82**: card Sentinel→`THE WATCHTOWER` (duo Sentinel + NewsKeeper, primo cameo pubblico del 5° bot dim/locked) + card Sherpa→`SHERPA Parameter Tuner` con mascot Claude Design (flag + mappa). 3 stat-row LIVE-WIRED via Supabase REST: REGIME (5 pip, oggi `FEAR`), BOTS (3 pip rossi auto-adatta), STOP BUY (1 pip, oggi OFF). Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped). **Push S82 deferito**: in attesa del brief newskeeper Board prima di rivelare il cameo pubblicamente.

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No"
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money"
- Post 3 LIVE 2026-05-19: "When Your AI CEO Lies About the Numbers"
- Post 4 PLANNED: "The Lemon That Squeezed Back" — ~fine maggio
- Post 5 PLANNED: "Why We're Not Live Yet" — a ridosso go-live
- Post 6 PLANNED: "We Built an Accounting System That Didn't Need to Exist" — FIFO saga, V3. ~inizio giugno.
- Post 7 PLANNED: "45 Sessions With an AI Co-Founder: The Unfiltered Version" — prefazione V2 adattata, voce Max. ~90% pronto.
- **Pipeline:** 20 post totali (7 PROSSIMI + 12 BACKLOG + 1 IDEA FUTURA), ~5 mesi autonomia (Apple Note "BagHolderAI — Blog Content Pipeline", aggiornata 23 maggio con 5 post backlog V3: Operation Clean Slate, 4 Bugs in 60 Seconds, The Intern Runs the Office, Brain Can't Tell BONK from Bitcoin, The One Where Nobody Writes Code)
- Idea futura: "Cover Evolution" (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
- Cadenza irregolare ("variable reinforcement")

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
- **Prossimi passi:** Post 3 cross-post settimana prossima, continuare engagement nei commenti, monitorare se le conversazioni portano click (UTM campaign `comment_deneth` e `comment_lenard`)

### X (@BagHolderAI)
- Post promozionale Post 3 pubblicato 2026-05-19 (gancio provocatorio "your ai assistant would rather fabricate a number...")
- Post Dev.to launch da pubblicare stasera contemporaneamente al cross-post
- Reply strategy attiva (doc: `reply_strategy_target_accounts.md`)
- Scanner X cron settimanale attivo

### HN
- Account Cart0ne: SHADOWBAN COMPLETO confermato 2026-05-19
- Piano: nuovo account da IP diverso, karma building, timeline indefinita

### UTM (NUOVO)
- **Sistema UTM operativo** (Apple Note "BagHolderAI — UTM Reference")
- **Haiku template + Telegram report: SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)**. X poster signature ora URL completo con `utm_source=x&utm_medium=social&utm_campaign=haiku_daily`. Telegram 3 firme convertite in `<a href>` cliccabili con `utm_source=telegram&utm_medium=social&utm_campaign=daily_report`. Mac Mini restart pending per applicare alle prossime emissioni.
- Link bio X resta manuale (a carico Max)
- Regola operativa: ogni link che esce dal progetto DEVE avere UTM

### Distribuzione blog
- Documento strategia distribuzione `marketing_strategy_distribution.md`
- Dev.to scelto come primo canale (cross-post, audience dev built-in, SEO resta nostro)
- **Indie Hackers in valutazione (2026-05-22 S81)**: possibile target per cross-post automation Dev.to + IH + sito. Decisione rimandata al weekend.
- Reddit/Hashnode/newsletter: valutazione futura post-Dev.to baseline

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

### Payhip
- Volume 1 + Volume 2 live, 39 views totali maggio, 0 vendite

### Ads & monetizzazione
- A-Ads live (revenue trascurabile). Buy Me a Coffee attivo. Nessuna sponsorship.

### A-Ads
- URL corretto da www.bagholderai.lol → bagholderai.lol (apex)
- Colori banner adattati al sito (#111622 sfondo, #6CCCFA accent)
- Embed code aggiornato 2026-05-22 (S80a, commit `2099a3c`), deploy Vercel auto-trigger su push.

### Analytics
- Umami Cloud + Vercel Web Analytics

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

**Volume 3** — "From Brain to Eyes" (Sessions 53–82, €4.99 planned). **CHIUSO a S82**. In rilettura finale, lancio Payhip previsto settimana 26-31 maggio. Arco narrativo: Clean Slate → Testnet → Brain Analysis → NewsKeeper decision (cliffhanger).

**Volume 4** — titolo TBD (Sessions 83+, €4.99 planned). **APERTO a S83**. Arco narrativo: NewsKeeper build → go-live → primi risultati reali.

**Volume corrente:** 4 (in accumulo da S83).
**Diari completi:** fino a S76 (vedi nota sotto).
**Backlog diary:** S83 BUILDING; backlog docx — verificare S73/S74/S77/S78/S79 come .docx pronti.

**Check di congruenza diary↔DB:** nessun check automatico attivo.

**Draft in coda:**
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-24 (S83/S84) | **CryptoPanic morto, pivot a RSS feeds** (CoinDesk + CoinTelegraph + Decrypt). Zero costo | CryptoPanic free Developer tier discontinued 1 aprile 2026 (verificato live: endpoint 404). Alternative paid sforavano budget brief <€1. RSS zero-auth, zero paywall risk |
| 2026-05-24 (S83/S84) | **Haiku classifier promosso da S3-4 a S2** | RSS non ha sentiment nativo (CryptoPanic invece sì). Classifier keyword MVP rumoroso ~60% falsi positivi (visibili a campione). Calibration o Haiku-classify anticipato in S2 |
| 2026-05-24 (S83/S84) | **Ship classifier rumoroso as-is per osservazione 7gg** | Data-first principle (feedback memory `feedback_data_first_then_review`). Raccolta dataset reale prima di tuning |
| 2026-05-24 (S83/S84) | **SEO fix S84 shipped same-day: title/description rewrite + JSON-LD + sitemap lastmod** | Audit GSC CEO: 256 imp / 0 clicks / position 10.7 / sitemap "Couldn't fetch". Brief MEDIUM priority chiuso in ~35min, non bloccante per mainnet ma critico per marketing. Drift S47 WebSite schema chiuso in extra |
| 2026-05-24 (S83/S84) | **Apple Notes pulizia: 4 attive, 8 obsolete da cancellare manualmente** | Note operative cumulate nel tempo. Quelle obsolete creavano confusione (es. HN strategy pre-shadowban). Cancellazione manuale a carico Max |
| 2026-05-24 (S83/S84) | **Todo riscritta per era V4/NewsKeeper** | Vecchia todo Apple Note era organizzata per fase V3 (Sentinel/Sherpa). Refresh per refleter focus NewsKeeper + go-live |
| 2026-05-24 (S83/S84) | **Distribution Channels: integrata strategia Reddit + post killer da nota HN obsoleta** | Nota HN era inutile post-shadowban Cart0ne (S81). Il "post killer" come concept (gancio narrativo strong) trasferito a strategia Reddit, da preparare con account dedicato |
| 2026-05-23 (S82 CEO) | **NewsKeeper promosso da post-mainnet a PRE-mainnet** | Crash analysis May 18-22: Sentinel Sprint 2 è reattivo (vede il crash durante), news signals sono predittivi (4 giorni di anticipo). Board decision: il sistema non va live con soldi finché non legge le notizie |
| 2026-05-23 (S82 CEO) | **Brief architetturale NewsKeeper scritto** | 5° cervello indipendente, 4 sessioni CC (~2 settimane). Moduli: CryptoPanic (free), ETF flows (free), macro calendar (statico). Strategist con Haiku (<€1/mese). Costo totale: <€1/mese |
| 2026-05-23 (S82 CEO) | **Nessuna data fissa per mainnet** | Go-live dipende da condizioni di mercato osservate (bear+bull+laterale), non da calendario. Sequenza: Brain Analysis → NewsKeeper build → Sherpa testnet → dry_run → Board approval |
| 2026-05-23 (S82 CEO) | **Volume 3 titolo confermato: "From Brain to Eyes"** | Trilogia: From Zero to Grid → From Grid to Brain → From Brain to Eyes |
| 2026-05-23 (S82 CEO) | **Futures/hedging parcheggiato S90+** | Richiede capitale >€100 e stack futures separato. Idea: cervello hedging che apre small short quando Sentinel dice regime=fear |
| 2026-05-23 (S82 CEO) | **Blog pipeline espansa a 20 post** | +5 backlog V3 da VOLUME_03_PLAN.md analysis. ~5 mesi di autonomia editoriale |
| 2026-05-23 (S82 CC) | **Homepage Blog section + Diary swap SHIPPED LOCAL** | Blog ora subito sotto hero (alta visibilità per i 3 post live, niente click extra), Diary spostato sotto Bots dove fa da "dietro le quinte" delle card. Reduce funnel friction senza occupare il prime real estate hero-adjacent |
| 2026-05-23 (S82 CC) | **Watchtower + Sherpa cards rifatte LOCAL** | Sentinel/Sherpa erano placeholder "?" silhouette con 5 zeri. Ora hanno identità grafica forte (mascot custom, palette dim ma riconoscibile), 3 dati LIVE veri (REGIME, BOTS, STOP BUY) e narrazione: Watchtower = duo che vede arrivare. NewsKeeper introdotto come cameo dim (locked) sulla card Watchtower |
| 2026-05-22 (S81 closure) | **Brief 81a Sherpa Sprint 2 SHIPPED**: per-coin volatility + slow-loop gate + amplitude cap 30% | Chiude i 3 pre-requisiti minimi del Brain Analysis. BONK ora riceve sell_pct ~2× di BTC (live: BTC 1.20 / SOL 1.30 / BONK 2.52). Proposte cambiano max ogni 4h (regime slow), non più ogni 2 minuti |
| 2026-05-22 (S81 closure) | **Brief 81b Haiku commentary SHIPPED**: `vs_yesterday.direction` pre-calcolato in Python + prompt stretto (80 parole, max 100) | Audit 60 entry trovò 1 errore (Day 15: -5.03% misclassificato "better" di -4.12%). Fix strutturale: Python calcola direction, Haiku la legge. Prompt sostituisce "3-4 lines ~250 chars" con "80 words / max 100" + 2 nuove regole NUMBERS/DIRECTION |
| 2026-05-22 (S81) | **Fast ladder (DROP/PUMP/FUNDING/SPEED_OF_FALL) cancellate da Sherpa** | Phase B le sposterà in Sentinel coin-aware. Codice morto rimosso, git history preserva. Decisione 2a delegata da Board |
| 2026-05-22 (S81) | **`proposed_stop_buy_active` legato a `regime == "extreme_fear"`** | De-coupling completo dal fast loop. Lampada ON solo nei regimi più gravi (slow cadence 4h). Decisione 1a delegata da Board |
| 2026-05-22 (S81) | **NO-GO Sherpa step 4** | Brain Analysis: -$3.94 vs Board, non coin-aware, 449 fast-loop flips, flicker 6min. Tre fix architetturali richiesti prima di riconsiderare |
| 2026-05-22 (S81) | **Three-phase brain architecture (A/B/C)** | A: Sherpa per-coin + slow gate + cap (brief 81a). B: Sentinel coin-aware (EMA/RSI per-coin). C: sentiment online. Ogni fase testata indipendentemente |
| 2026-05-22 (S81) | **Grid-only mainnet è opzione legittima** | Grid +$12.52 in mercato -0.47%. Funziona senza cervello. Possibile andare live Grid-only mentre Sherpa matura |
| 2026-05-22 (S81) | **Volume 3 climax = seconda Brain Analysis** | Atto 1 (questo report): brain è daltonico. Atto 2 (post-rework): brain rieducato. Cutoff stimato S83-S85 |

> Decisioni S80, S79, S78, S77 e precedenti spostate fuori dalla tabella in S82 closure per restare entro ~15 voci (brief CEO `business_state_update_s82_ceo.md`). Storico completo in git history e `PROJECT_STATE.md §4`/§10.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **[S83 NEW] NewsKeeper S2** | Board-approved, timeline post-osservazione | Sessioni 2-4 brief NewsKeeper Architecture: (a) Haiku classifier (promosso da S3-4 → S2 perché RSS non ha sentiment nativo); (b) Modulo 2 ETF flows + Modulo 3 macro_calendar; (c) integrazione orchestrator (`ENABLE_NEWSKEEPER` env + `_spawn_newskeeper()`). **Timeline: post 7gg osservazione (~31 maggio).** Priorità ALTA |
| **[S83 NEW] Audit Area 2 (coerenza progetto)** | Proposto CC con data specifica | Mai eseguito, cadenza 90gg superata da sempre. **Proposta CC: lunedì 27 maggio con CC fresh** (durante osservazione NewsKeeper 7gg). Brief `audit_request_YYYYMMDD_*.md` + fresh CC. ~30-45min |
| **[S82] Brief NewsKeeper architetturale Session 1** | ✅ DONE (S83) | Scaffold shippato commit `49473a9`. Module 1 RSS feeds live standalone Mac Mini PID 78098. Sessioni 2-4 ancora pending |
| **[S81 NEW] Cross-post automation Dev.to + Indie Hackers** | Decisione rimandata post-weekend | Quando un post va live su `web_astro/src/content/blog/`, script che pubblica su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. ~2-3h stimato |
| ~~Brief 81a Sherpa Sprint 2~~ | ✅ DONE (S81) | Shipped commit `3ba1132`. Verifica live: BTC/SOL/BONK proposals diversi |
| ~~Sito TF narrativa update~~ | ✅ DONE (S80) | "dal dottore" → card TF live shipped brief 80b commit `b8bdc12` |
| ~~Monitorare sitemap Search Console~~ | ✅ DONE (S84) | SEO fix S84 shipped commit `c89c8cc`: sitemap lastmod + JSON-LD + title/description. Action manuali Max post-deploy in §6 |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Integration test config reader chain** | Pre-prossimo brief bot_config | Gap strutturale scoperto S76. ~30-60 min |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |
| **Phantom BONK 1.37M** | Bassa priorità | Non bloccante |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **Volume 3 "From Brain to Eyes" pubblicazione Payhip** | Entro fine maggio 2026 (settimana 26-31 maggio) | Volume chiuso a S82, in rilettura finale. Lancio Payhip standalone €4.99 come Vol 1+2 |
| **Apple Notes pulizia: cancellare 8 note obsolete (Max)** | A discrezione Max | 4 note attive da mantenere, 8 obsolete da cancellare manualmente (CC non ha permessi di scrittura su Notes app) |
| **GSC: re-submit `sitemap-0.xml` + Request Indexing top 5 (Max)** | Post-deploy S84 (oggi 2026-05-24 in poi) | Action manuali documentate nel report CEO S84 §"Action richieste a Max". Ri-sottomettere `sitemap-0.xml` in Search Console → Sitemaps (bypass index file). Request Indexing tramite URL Inspection su top 5: home, roadmap, blueprint, diary, blog/ |
| **Go-live mainnet** | Nessuna data fissa | Dipende da condizioni di mercato (bear+bull+laterale osservati). Sequenza: Brain Analysis → NewsKeeper build (4 sessioni) → Sherpa testnet → dry_run → Board approval |
| **Sherpa LIVE su testnet** | Post seconda Brain Analysis (S85+ candidato) | Un parametro alla volta (sell_pct primo) |
| **DRY_RUN Sherpa Sprint 2 osservazione** | 7-10 giorni da 2026-05-22 (~29 maggio - 1 giugno) | Restart PID 28217. Seconda Brain Analysis dopo. Board decide step 4 dopo analisi |
| **NewsKeeper osservazione 7gg + S2 build** | 31 maggio target | Classifier rumoroso noto, raccolta dataset 7gg, poi calibration / Haiku-classify in S2 |
| **Blog primo post** | DONE 2026-05-15 | "An AI That Can't Trade" live su bagholderai.lol/blog |
| **Volume 4** | Nessuna deadline | In accumulo da S83, arco narrativo NewsKeeper build → go-live |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Repo locale MBP sincronizzato origin/main post-push S84 (commit `33d23b1`). Mac Mini orchestrator su `51204cf` (PID parent **28217**, restart 2026-05-22 20:31 CET post brief 81a+81b), 7 processi + NewsKeeper standalone PID 78098 (caffeinate parent 78100, launch 2026-05-24 10:56 CET). Niente restart necessario per S84 (solo modifiche sito Astro, deploy Vercel auto).

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Go-live mainnet €100** | Bloccato da 4 pre-requisiti in sequenza: NewsKeeper build (S2-S4, ~3 sessioni residue) + Sherpa testnet LIVE (post Brain Analysis 2) + dry_run observation periodo standard + Board approval finale. Niente data fissa, gated da condizioni di mercato osservate (bear+bull+laterale) |
| **TF-Scout (Tier 3 shitcoins)** | Post-mainnet, esplicitamente parcheggiato. Richiede capitale extra e tolleranza rischio che oggi non abbiamo |
| **Grok/X scanner module** | Post-mainnet. Richiede API X premium (~$200/mese), giustificabile solo con MRR positivo |
| **Audit Area 2 non eseguito** | Dovuto (cadenza 90gg). CC ha flaggato in S78fp2/S79/S80/S80a/S81/S83. **Finestra utile: 27 maggio - 1 giugno** durante osservazione NewsKeeper 7gg (sovrapposta a osservazione Sherpa Sprint 2). Proposta CC: lunedì 27 maggio con fresh CC + audit brief |
| **Homepage S82 pushata in S83** | Push fatto 2026-05-24 (commits `cdb5ff8` + `85b2751` già su origin/main). NewsKeeper cameo ora visibile pubblicamente coerente con scaffold backend live |
| **Nessun cross-post automatico** | Dev.to e IH sono manuali. Automazione in valutazione, decisione post-weekend |
| **Nessun cross-post Reddit** | Dev.to prima (più facile, meno rischio spam flag). Reddit richiede karma building pre-esistente. Strategia "post killer" integrata da nota HN obsoleta (decisione 2026-05-24) |
| **Distribuzione blog su altre piattaforme (oltre Dev.to)** | Dev.to scelto come primo canale 2026-05-20. Reddit/Hashnode/IH/newsletter restano in valutazione post-baseline Dev.to |
| **HN come canale** | Shadowban completo confermato 2026-05-19 rende Cart0ne inutilizzabile. Nuovo account pianificato ma non urgente — altri canali prioritari |
| **Volume 3 lancio Payhip** | Materiale chiuso a S82, in rilettura finale. Lancio settimana 26-31 maggio |
| **Sitemap Google indicizzazione** | Risolta in S84 (sitemap lastmod + JSON-LD shipped). Manca solo Max che ri-sottomette `sitemap-0.xml` in GSC + Request Indexing top 5. Risultati attesi 7-14gg |
| **Sherpa LIVE su testnet** | Sprint 2 SHIPPED in S81 (per-coin / slow-gate / cap). Ora 7-10gg DRY_RUN osservazione + seconda Brain Analysis prima di abilitarlo. Target ~29 maggio - 1 giugno per analisi |
| **Retention cron jobs** | Deliberatamente rimandati: prima analizzare dati Sentinel/Sherpa, poi pulire. Brief separato post-osservazione |
| **X reply strategy 0 fatte** | Definita 15 maggio ma non ancora eseguita con costanza. Weekend in mezzo + brief shipped hanno consumato la finestra |
| **Cover V3 non generata** | Solo concept (tempesta + mascotte easter egg). Timing: quando V3 va su Payhip (settimana 26-31 maggio) |
| **NewsKeeper Sessions 2-4 non ancora in build** | Session 1 SHIPPED in S83 (scaffold + Module 1 RSS feeds standalone). Sessions 2-4 partono dopo osservazione 7gg classifier (~31 maggio) |
| **Futures/hedging** | Parcheggiato S90+. Richiede capitale >€100, stack separato, KYC aggiuntivo. Post-mainnet |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post Audit Area 2 (27 maggio target) o seconda Brain Analysis (~29 maggio - 1 giugno) o NewsKeeper S2 build (~31 maggio), whichever comes first.*
