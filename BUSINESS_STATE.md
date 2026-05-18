# BUSINESS_STATE.md

**Last updated:** 2026-05-18 — Session 79 (CEO strategy + 3 brief shipped da CC + drift FIFO sanato + Supabase IO warning + cleanup). 3 brief CEO ortogonali shipped: 79a idle suppression on capital exhausted, 79b TF reactivation Tier 1-2 only (Tier 3 weight=0 in DB), 79c Supabase write-on-change + heartbeat su 3 tabelle pesanti. 2 restart Mac Mini.
**Updated by:** CC + CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-18 (S79 chiusura, ultimo commit `69cb33a`)

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

**Sito online:** TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline (**⚠️ STALE post-S79:** TF è LIVE dal 2026-05-18 21:14 CET, Tier 1-2 only, Tier 3 weight=0. Narrativa pubblica da aggiornare prossima sessione — "TF on, no Tier 3" o cornice equivalente, ~30-45min), Sentinel/Sherpa badge TEST MODE. Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped).

- **Blog:** 2 post LIVE + 1 pianificato.
  - Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No" (`bagholderai.lol/blog/an-ai-that-cant-trade`).
  - Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money" (`bagholderai.lol/blog/the-day-our-bot-ran-out-of-money`, type highlight, coverSession 16, V1). Pubblicato dal commit `dcc4372` + push → Vercel auto-deploy.
  - **Post 3 PIANIFICATO S80**: "why not live yet" — piece strategico sul perché posticipiamo go-live mainnet. Sequenza Sentinel-first, Sherpa LIVE testnet graduale, mainnet €100 a sistema rodato.
  - Idea futura: "Cover Evolution" — storia di come le copertine V1→V2→V3 evolvono (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
  - Cadenza irregolare ("variable reinforcement").
- **X:** tweet lancio blog postato e pinnato. Reply strategy definita (doc: `reply_strategy_target_accounts.md`). Prossime 2 settimane: 2-3 reply/giorno, tracking risultati. Scanner X cron settimanale attivo.
- **HN:** email a `hn@ycombinator.com` per unflag account Cart0ne. In attesa risposta.
- **GSC:** 4 sitemap rimossi 2026-05-15 (cached failure da aprile, vedi audit Area 3). Reinvio `/sitemap-index.xml` da verificare (deadline 17 maggio scaduta — controllare se fatto).
- **Payhip:** Volume 1 + Volume 2 live, 0/30 views totali.
- **Ads/monetizzazione:** A-Ads live (revenue trascurabile). Buy Me a Coffee attivo. Nessuna sponsorship.
- **Analytics:** Umami Cloud + Vercel Web Analytics.

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
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno / inizio luglio target |
| **Sherpa LIVE su testnet** | Ancora in DRY_RUN. Osservazione Sprint 2 in corso (scadenza naturale 21-22 maggio). Proposte visibili ma non applicate. Un parametro alla volta (sell_pct primo) |
| **Blog post 3 ("why not live yet")** | Pianificato per S80 (blog day). Sequenza Sentinel-first + mainnet target è il contenuto. Drawdown + drought trades come setup narrativo |
| **Audit Area 2 non eseguito** | Dovuto (cadenza 90gg). CC ha flaggato in S78 fase 2 + S79. Proporre in prossima sessione di breathing |
| **Retention cron jobs** | Deliberatamente rimandati: prima analizzare dati Sentinel/Sherpa, poi pulire. Brief separato post-osservazione |
| **X reply strategy 0 fatte** | Definita 15 maggio ma non ancora eseguita con costanza. Weekend in mezzo + 3 brief shipped hanno consumato la finestra |
| **Cover V3 non generata** | Solo concept (tempesta + mascotte easter egg). Timing: quando V3 è vicino a chiusura (~S85-90) |
| **Sprint 3 (news feed)** | Post-osservazione Sprint 2, non prima di fine maggio |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post osservazione Sentinel Sprint 2 (~21-22 maggio), o pubblicazione blog post 3 — whichever comes first.*
