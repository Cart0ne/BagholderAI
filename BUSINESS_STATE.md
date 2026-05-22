# BUSINESS_STATE.md

**Last updated:** 2026-05-22 — Session 81 opening (Brain Analysis CONSEGNATA, NO-GO Sherpa step 4, three-phase brain architecture decisa, Dev.to Post 2 LIVE, A-Ads embed refreshed). I 3 attori in parallelo (CEO + CC + Max) sono operativi.
**Updated by:** CEO + CC
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-22 (S80a chiusura) + brief CEO update inline S81

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
TestnetBanner globale, Reconciliation table pubblica su /dashboard. **TF live card on home + dashboard SHIPPED 2026-05-20 (Brief 80b, commit `b8bdc12`)** — "dal dottore" SVG sostituito con card stile Grid (orange accent, mirror frame), hero text aggiornato a "$500 Grid + $100 TF (Tier 1-2)", pipeline arrow "I tried, your turn" → "TF picks, Grid manages". **Homepage CTA swap SHIPPED (Brief 80b)**: "Read the blog" primario, "Read the diary" + "Live numbers →" secondari outline. Sentinel/Sherpa badge TEST MODE. Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped).

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No"
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money"
- Post 3 LIVE 2026-05-19: "When Your AI CEO Lies About the Numbers"
- Post 4 PLANNED: "The Lemon That Squeezed Back" — ~fine maggio
- Post 5 PLANNED: "Why We're Not Live Yet" — a ridosso go-live
- Post 6 PLANNED: "We Built an Accounting System That Didn't Need to Exist" — FIFO saga, V3. ~inizio giugno.
- Post 7 PLANNED: "45 Sessions With an AI Co-Founder: The Unfiltered Version" — prefazione V2 adattata, voce Max. ~90% pronto.
- **Pipeline:** 7 post totali pianificati, ~3 mesi autonomia (Apple Note "BagHolderAI — Blog Content Pipeline")
- Idea futura: "Cover Evolution" (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
- Cadenza irregolare ("variable reinforcement")

### Dev.to (cart0ne)
- **Account creato:** 2026-05-20 (GitHub login, username: `cart0ne`)
- **Profilo completato:** bio, coding section, work section, series "BagHolderAI"
- **Post 1 LIVE:** "An AI That Can't Trade, a Human That Can't Say No" — canonical URL `bagholderai.lol`, UTM footer, serie "BagHolderAI". Pubblicato 2026-05-20 sera. Views/reactions: ancora ~0 (account nuovo, nessun follower, algoritmo non spinge).
- **Post 2 LIVE:** "The Day Our Bot Ran Out of Money" — cross-posted 2026-05-22, canonical URL, UTM footer, serie "BagHolderAI".
- **Community engagement attivo:**
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
- Reddit/Hashnode/Indie Hackers/newsletter: valutazione futura post-Dev.to baseline

### SEO / Google Search Console
- 230 impressions, 0 click, posizione media 9.5
- Blog post NON ancora indicizzati
- Bug sitemap ("Sitemap could not be read"): debug per CC nel todo

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

**Volume 3** — in accumulo. Sessions 53+. Arco narrativo: Clean Slate → Testnet → Fee Reckoning → Stress Test → Sentinel-First Roadmap. Stima chiusura: sessioni 80-90.

**Volume corrente:** 3 (in accumulo).
**Diari completi:** fino a S76 (vedi nota sotto).
**Backlog diary:** S79 BUILDING (CEO sta scrivendo); ~3-4 sessioni di backlog complessivo (S77 audit + S77 sprint 2 + S78 + S79).

**Check di congruenza diary↔DB:** nessun check automatico attivo.

**Draft in coda:**
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-22 (S81) | **NO-GO Sherpa step 4** | Brain Analysis: -$3.94 vs Board, non coin-aware, 449 fast-loop flips, flicker 6min. Tre fix architetturali richiesti prima di riconsiderare |
| 2026-05-22 (S81) | **Three-phase brain architecture (A/B/C)** | A: Sherpa per-coin + slow gate + cap (brief 81a). B: Sentinel coin-aware (EMA/RSI per-coin). C: sentiment online. Ogni fase testata indipendentemente |
| 2026-05-22 (S81) | **Grid-only mainnet è opzione legittima** | Grid +$12.52 in mercato -0.47%. Funziona senza cervello. Possibile andare live Grid-only mentre Sherpa matura |
| 2026-05-22 (S81) | **Volume 3 climax = seconda Brain Analysis** | Atto 1 (questo report): brain è daltonico. Atto 2 (post-rework): brain rieducato. Cutoff stimato S83-S85 |
| 2026-05-22 (S81) | **Blog Post 5 + Post 7 aggiunti a pipeline** | FIFO saga (V3) + prefazione V2 adattata. Pipeline 7 post totali |
| 2026-05-21 (S80) | **Dev.to engagement-first strategy** | I commenti e le conversazioni portano più visibilità di un post su account nuovo con 0 follower. Prima costruisci relazioni, poi l'algoritmo ti aiuta |
| 2026-05-21 (S80) | **UTM nascosti nei link markdown Dev.to** | Formato `[testo visibile](url?utm_...)` — l'utente vede il testo pulito, il tracking funziona |
| 2026-05-21 (S80) | **Bio X: UTM visibile nel campo Website → workaround** | Rimosso UTM dal campo Website (visibile, brutto). Serve redirect `/x → homepage con UTM`, brief CC futuro |
| 2026-05-20 (S80) | **Dev.to come primo canale distribuzione blog** | Cross-post con canonical URL, audience dev built-in, SEO resta nostro. Primo di 6 canali valutati. Account creato, Post 1 in draft, lancio stasera |
| 2026-05-20 (S80) | **UTM su tutti i touchpoint (Apple Note + Brief 80b)** | Senza UTM, 97% del traffico finisce in "Direct" — impossibile misurare cosa funziona. Brief 80b ha cablato Haiku X + Telegram report (commit `b8bdc12`) |
| 2026-05-20 (S80) | **Hero CTA swap: blog primario, diary secondario (Brief 80b shipped)** | Dati Umami: 90% visitatori non trova il blog. Fix minimo prima di ristrutturare layout. SHIPPED commit `b8bdc12` |
| 2026-05-20 (S80) | **NO sezione blog su homepage (Board veto)** | Sposterebbe bot cards sotto la piega. Prima misurare effetto CTA swap per 1 settimana |
| 2026-05-20 (S80) | **Blog Content Pipeline: 12 post mappati, ~3 mesi autonomia** | Backlog V1+V2+V3, nessun contenuto da inventare. Apple Note dedicata |
| 2026-05-20 (S80) | **~30% traffico Umami è bot datacenter** | Falkenstein/Helsinki/Nürnberg: 100% bounce, 0s. Sottrarre un terzo ai numeri grezzi |
| 2026-05-19 (S80) | **Blog Post 3 LIVE + HN shadowban confermato** | Post 3 genera +162% traffico. HN chiuso, Dev.to/Reddit come alternative |
| 2026-05-19 (S80 CEO) | **Blog Post 3 LIVE: "When Your AI CEO Lies About the Numbers"** | Tema LLM honesty da S41+S52, formato lesson standalone. Aumenta credibilità progetto su tema caldo AI |
| 2026-05-19 (S80 CEO) | **HN shadowban confermato (Cart0ne è morto)** | Test incognito: commenti invisibili. Email a dang senza risposta. Piano: nuovo account da IP diverso, karma building 2-3 settimane, Show HN quando avremo numeri mainnet. Non urgente, altri canali prioritari |
| 2026-05-19 (S80 CEO) | **Brief 80a Brain Analysis scritto** | Analisi completa Sentinel+Sherpa: counterfactual, baseline statica, timing analysis, flicker. Esecuzione CC weekend 23-25 maggio |
| 2026-05-19 (S80 CEO) | **Volume 3 climax candidato = Brain Analysis** | Cutoff S82-S83. Decisione formale post-analisi. Packaging V3 può procedere mentre i cervelli raccolgono dati |
| 2026-05-19 (S80 CEO) | **Blog cadenza: distanziare i post** | Non pubblicare a raffica. Variable ratio reinforcement: anticipazione conta più di volume |
| 2026-05-19 (S80 CEO) | **Strategia distribuzione blog: documento pronto** | `marketing_strategy_distribution.md`. Canali Dev.to/Hashnode/Reddit/IH/newsletter/SEO. Decisione in prossima sessione marketing dedicata |
| 2026-05-18 (S79 CEO) | **TF riattivato Tier 1-2, Tier 3 weight=0** | Board reverse della decisione "park" di S78. Regime "fear" + distance filter 12% → TF scansiona senza allocare, counterfactual data a costo zero. Se mercato stabilizza, tf_grid handoff pronto. $100 budget separato dai $500 Grid (pool USDT free testnet = $9.481) |
| 2026-05-18 (S79 CEO) | **Idle recalibration soppresso quando cash esaurito** | Board proposal. Guard in `grid_bot.py`: skip idle entrambi i path (re-entry + recalibrate) quando `_available_cash() < $5`. Riduce rumore operativo durante drawdown. Live verificato 3/3 bot |
| 2026-05-18 (S79 CEO) | **Write-on-change pattern su Supabase** | Supabase warning Disk IO Budget. Sentinel fast / Sherpa proposals / bot_state_snapshots scrivono solo su cambiamento o heartbeat (10min/10min/5min). Atteso ~80% riduzione write in mercato piatto |
| 2026-05-18 (S79 CEO+CC) | **FIFO dichiarato morto, avg-cost canonical** | Bug S70c era già chiuso in S72 (sell_pipeline.py:409 fa `revenue - cost_basis - fee` netto). "Strada 2 ~3-4h" ridotto a verifica identità ~30min. Frame: avg-cost + Equity P&L broker-comparable. 2 memorie aggiornate |
| 2026-05-18 (S79 CEO) | **Haiku daily commentary resta attivo anche senza trade** | "The silence is the story." Drawdown documentato > drawdown ignorato. Day 10 senza trade = contenuto migliore di metà dei giorni con trade |
| 2026-05-18 (S79 CEO) | **State files: Project Knowledge prima, GitHub fallback** | Memory #22 aggiunta lato CEO. GitHub stale a S63 mentre PK aveva S78 — workflow ridefinito |
| 2026-05-16 (S78 fase 2 CEO) | **TF Tier 1-2 reactivation parcheggiata** | Meccanismo tf_grid esiste, rischio basso, ma aggiungere variabili durante osservazione Sentinel Sprint 2 contamina baseline. Rivisitare dopo 5-7 giorni |
| 2026-05-16 (S78 fase 2 CC) | **SWEEP slippage buffer 3% shipped** | Root cause cashLeft<0: slippage SWEEP (+1.19% su BONK), non skim guard mancante. Buffer uniforme 3% in HardcodedRules. Ricalibrare post-mainnet (slippage mainnet tipicamente 10x più basso) |
| 2026-05-16 (S78 fase 2 CC) | **Banner buysLeft <= 0 corretto** | Non shortcut — buysLeft<0 è fisiologico post-SWEEP. Branch dedicato "swept, $X over by slippage" |
| 2026-05-16 (S78 fase 2 CC) | **Gitignore anchored fix** | `blog/` matchava ricorsivamente → blog post futuri silenziosamente esclusi. Fix: `/blog/` anchored a root |
| 2026-05-16 (S78 fase 2 CEO) | **Blog post 2 LIVE: "The Day Our Bot Ran Out of Money"** | Highlight V1 S16. Standalone, accessibile a nuovi lettori. Commit `dcc4372` + push → Vercel auto-deploy |
| 2026-05-16 (S78 fase 2 CEO) | **Cover evolution memo creato** | Storia copertine V1 (notte) → V2 (alba) → V3 (tempesta + mascotte easter egg). Per blog post futuro legato a V3 |
| 2026-05-15 (S78 fase 1 CEO) | **Primo blog post pubblicato (anticipato dal weekend 17-18)** | Origin story dual-voice. Brief 78a (no testo touch, solo copy+build+push). Anticipa "blog weekend" Board, libera weekend per Post 2 |
| 2026-05-15 (S78 fase 1) | **Reply strategy > posting frequency su X** | Dato Montemagno (358 imp da una reply vs 78 media post). Vedi audit Area 3 marketing+SEO+X |
| 2026-05-14 (S77) | **Sentinel Sprint 2 shipped + mapping contrarian** | Slow loop F&G + CMC ogni 4h, regime detection attivo. Mapping invertito: extreme_fear → opp alta/risk basso ("buy fearful sell greedy"). Sherpa propone con regime dinamico |
| 2026-05-14 (S76 CEO) | **Roadmap Sentinel-first in 5 step + mainnet posticipato** | Step 1 audit Sprint 1, step 2 build Sprint 2, step 3 osservazione 1 settimana, step 4 Sherpa LIVE testnet (sell_pct primo), step 5 mainnet. Target fine giugno/inizio luglio. Sherpa scriverà bot_config con soldi veri → test prima |

> Decisioni S76 CC e precedenti, dettagli S77 e S78 fase 1 spostati fuori dalla tabella per restare entro ~15 voci. Storico completo in git history e `PROJECT_STATE.md §4`/§10.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **Brief 81a Sherpa Sprint 2** | HIGH, prossima sessione CC | 3 blocchi: per-coin volatility scaling (dynamic coin discovery), slow-loop gate, amplitude cap 30%. Piano italiano prima del codice. ~3-4h |
| **Sito TF narrativa update** | 🆕 Prossima sessione S80 | "dal dottore" → "on Tier 1-2". SVG + badge. ~30-45min. Apple Note + memoria dedicata |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Audit Area 2 (coerenza progetto)** | 🆕 Mai eseguito, proposta CC | Roadmap vs PROJECT_STATE vs BUSINESS_STATE consistency check. Cadenza 90gg superata da sempre. ~30-45min fresh CC |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Integration test config reader chain** | Pre-prossimo brief bot_config | Gap strutturale scoperto S76. ~30-60 min |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |
| **Monitorare sitemap Search Console** | Aperta | Reinvio S75. Se ancora "Impossibile recuperare" provare ping |
| **Phantom BONK 1.37M** | Bassa priorità | Non bloccante |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **Go-live mainnet** | Fine giugno / inizio luglio | Posticipato da "18-21 maggio" a sistema completo: Grid + Sentinel testato + Sherpa attivato su testnet |
| **Sherpa LIVE su testnet** | Post osservazione Sentinel 1 settimana | Un parametro alla volta (sell_pct primo) |
| **Blog primo post** | DONE 2026-05-15 | "An AI That Can't Trade" live su bagholderai.lol/blog |
| **Volume 3** | Nessuna deadline | In accumulo, arco narrativo si forma |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Repo su commit `0008e4f` (S80a chiusura). Mac Mini ancora su `542b190` (PID parent **74280**, restart 2026-05-18 21:49 CET post-79c), 7 processi. **Restart pending**: S80 UTM signatures (`utils/x_poster.py` + `utils/telegram_notifier.py`) — sarà coperto dal restart S81 post-brief 81a.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Nessuna blog section su homepage** | Board veto: sposterebbe bot cards sotto la piega. Prima misuriamo effetto CTA swap (Brief 80b shipped) per 1 settimana con UTM |
| **Nessun cross-post Reddit** | Dev.to prima (più facile, meno rischio spam flag). Reddit richiede karma building pre-esistente |
| **Distribuzione blog su altre piattaforme (oltre Dev.to)** | Dev.to scelto come primo canale 2026-05-20. Reddit/Hashnode/IH/newsletter restano in valutazione post-baseline Dev.to |
| **HN come canale** | Shadowban completo confermato 2026-05-19 rende Cart0ne inutilizzabile. Nuovo account pianificato ma non urgente — altri canali prioritari |
| **Volume 3 packaging** | Materiale esiste (~27 sessioni) ma lettura/valutazione rimandate a post-Brain Analysis, quando c'è tempo di attesa naturale durante raccolta dati Sentinel/Sherpa |
| **Sitemap Google indicizzazione** | Rotta da settimane, blog post non indicizzati. Workaround (`sitemap-0.xml`) inviato 2026-05-19. Debug tecnico per CC in sessione futura |
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno / inizio luglio target |
| **Sherpa LIVE su testnet** | Brain Analysis NO-GO. Tre fix architetturali richiesti (per-coin, slow-gate, cap). Dopo rework + 7-10gg DRY_RUN + seconda analisi |
| **Audit Area 2 non eseguito** | Dovuto (cadenza 90gg). CC ha flaggato in S78 fase 2 + S79. Proporre in prossima sessione di breathing |
| **Retention cron jobs** | Deliberatamente rimandati: prima analizzare dati Sentinel/Sherpa, poi pulire. Brief separato post-osservazione |
| **X reply strategy 0 fatte** | Definita 15 maggio ma non ancora eseguita con costanza. Weekend in mezzo + 3 brief shipped hanno consumato la finestra |
| **Cover V3 non generata** | Solo concept (tempesta + mascotte easter egg). Timing: quando V3 è vicino a chiusura (~S85-90) |
| **Sprint 3 (news feed)** | Post-osservazione Sprint 2, non prima di fine maggio |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post brief 81a Sherpa Sprint 2 (per-coin rules + slow-gate + cap), o pubblicazione Dev.to Post 3 — whichever comes first.*
