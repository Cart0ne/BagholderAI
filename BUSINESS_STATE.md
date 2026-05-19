# BUSINESS_STATE.md

**Last updated:** 2026-05-19 — Session 80 (CEO update marketing+blog+HN+SEO+distribuzione + Brief 80a Brain Analysis scritto). Blog Post 3 "When Your AI CEO Lies About the Numbers" LIVE. HN shadowban confermato. Documento strategia distribuzione blog pronto per review. Volume 3 climax candidato = Brain Analysis (CC weekend 23-25 maggio).
**Updated by:** CC + CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-18 (S79 chiusura, ultimo commit `69cb33a`) + brief `config/business_state_update_20260519.md`

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
TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline (**⚠️ STALE post-S79:** TF è LIVE dal 2026-05-18 21:14 CET, Tier 1-2 only, Tier 3 weight=0. Narrativa pubblica da aggiornare prossima sessione — "TF on, no Tier 3" o cornice equivalente, ~30-45min), Sentinel/Sherpa badge TEST MODE. Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped).

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No" (origin story, dual voice) — `bagholderai.lol/blog/an-ai-that-cant-trade`
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money" (highlight V1 S16, standalone) — `bagholderai.lol/blog/the-day-our-bot-ran-out-of-money`
- **Post 3 LIVE 2026-05-19**: "When Your AI CEO Lies About the Numbers" (lesson, V2 S41+S52, tema LLM honesty) — `bagholderai.lol/blog/when-your-ai-ceo-lies-about-the-numbers`
- Post 4 PLANNED: "The Lemon That Squeezed Back" (interlude LemonSqueezy, V2) — ~fine maggio, cadenzato
- Post 5 PLANNED: "Why We're Not Live Yet" (pezzo strategico) — a ridosso go-live
- Idea futura: "Cover Evolution" — storia copertine V1→V2→V3 (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
- **Cadenza irregolare** ("variable reinforcement"): post distanziati di qualche giorno, non pubblicati a raffica.

### X (@BagHolderAI)
- Post promozionale Post 3 pubblicato 2026-05-19 (gancio provocatorio "your ai assistant would rather fabricate a number...")
- Analytics: spike traffico sito stessa sera (21 visitatori, +320% vs giorno precedente, 0% Italia = traffico reale esterno)
- Reply strategy definita (doc: `reply_strategy_target_accounts.md`). Target 2-3 reply/giorno, tracking risultati. Scanner X cron settimanale attivo.

### HN
- **Account Cart0ne: SHADOWBAN COMPLETO confermato 2026-05-19** (test incognito: commenti invisibili)
- Email a dang: nessuna risposta
- Piano: nuovo account da IP diverso (ufficio/telefono), karma building 2-3 settimane, poi Show HN quando abbiamo numeri mainnet

### Distribuzione blog
- Documento strategia distribuzione pronto per review Board (`marketing_strategy_distribution.md`)
- Canali valutati: Dev.to (cross-post), Hashnode, Reddit, Indie Hackers, newsletter aggregator, SEO organico
- Decisione pendente: quale canale attivare per primo, quale strategia cross-post (identico vs adattato)
- Prossima azione: sessione marketing dedicata per decidere

### SEO / Google Search Console
- 230 impressions in 3 mesi, 0 click, posizione media 9.5 — Google ci vede ma siamo troppo in basso
- 7 pagine indicizzate (roadmap 161 imp, blueprint 37, diary 27, howwework 9, home 8, guide 2, dashboard 2)
- **Blog post NON ancora indicizzati da Google** (0 pagine blog in Search Console)
- Bug sitemap: Google restituisce "Sitemap could not be read" su `sitemap-index.xml`. Bing legge tutto OK (3 sitemap, 25 URL, 0 errori). Max ha aggiunto `sitemap-0.xml` direttamente su entrambi. Debug tecnico per CC.
- Bing Webmaster Tools: funzionante, `sitemap-0.xml` submitted con 14 URL

### Payhip
- Volume 1 + Volume 2 live, 0/30 views totali

### Ads & monetizzazione
- A-Ads live (revenue trascurabile). Buy Me a Coffee attivo. Nessuna sponsorship.

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

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Allineati su commit `69cb33a` (S79 chiusura). Mac Mini PID parent **74280** (restart 2026-05-18 21:49 CET post-79c), 7 processi.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Distribuzione blog su altre piattaforme** | Documento strategia pronto (`marketing_strategy_distribution.md`) ma decisione rinviata a sessione dedicata. I 3 post blog sono visibili solo via X e traffico diretto |
| **HN come canale** | Shadowban completo confermato 2026-05-19 rende Cart0ne inutilizzabile. Nuovo account pianificato ma non urgente — altri canali prioritari |
| **Volume 3 packaging** | Materiale esiste (~27 sessioni) ma lettura/valutazione rimandate a post-Brain Analysis, quando c'è tempo di attesa naturale durante raccolta dati Sentinel/Sherpa |
| **Sitemap Google indicizzazione** | Rotta da settimane, blog post non indicizzati. Workaround (`sitemap-0.xml`) inviato 2026-05-19. Debug tecnico per CC in sessione futura |
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno / inizio luglio target |
| **Sherpa LIVE su testnet** | Ancora in DRY_RUN. Osservazione Sprint 2 in corso (scadenza naturale 21-22 maggio). Proposte visibili ma non applicate. Un parametro alla volta (sell_pct primo) |
| **Audit Area 2 non eseguito** | Dovuto (cadenza 90gg). CC ha flaggato in S78 fase 2 + S79. Proporre in prossima sessione di breathing |
| **Retention cron jobs** | Deliberatamente rimandati: prima analizzare dati Sentinel/Sherpa, poi pulire. Brief separato post-osservazione |
| **X reply strategy 0 fatte** | Definita 15 maggio ma non ancora eseguita con costanza. Weekend in mezzo + 3 brief shipped hanno consumato la finestra |
| **Cover V3 non generata** | Solo concept (tempesta + mascotte easter egg). Timing: quando V3 è vicino a chiusura (~S85-90) |
| **Sprint 3 (news feed)** | Post-osservazione Sprint 2, non prima di fine maggio |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post osservazione Sentinel Sprint 2 (~21-22 maggio), o pubblicazione blog post 3 — whichever comes first.*
