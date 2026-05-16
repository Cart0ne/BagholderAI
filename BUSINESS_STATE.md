# BUSINESS_STATE.md

**Last updated:** 2026-05-16 — Session 78 fase 2 (CEO strategy + blog, CC diagnostic + slippage buffer fix). Sessione 78 estesa: fase 1 = 2026-05-15 (primo blog post + tweet lancio + reply strategy + GSC + HN + audit Area 3), fase 2 = 2026-05-16 (blog post 2 LIVE + SWEEP/LAST SHOT slippage buffer 3% shipped + restart Mac Mini + cover evolution memo).
**Updated by:** CC + CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-16 (S78 chiusura fase 2, ultimo commit `25541b9`)

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

**Sito online:** TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE. Dashboard P&L hero unificato. HWW v3 con Auditor entity. Blog infrastructure pronta (brief 75a shipped).

- **Blog:** 2 post LIVE.
  - Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No" (`bagholderai.lol/blog/an-ai-that-cant-trade`).
  - Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money" (`bagholderai.lol/blog/the-day-our-bot-ran-out-of-money`, type highlight, coverSession 16, V1). Pubblicato dal commit `dcc4372` + push → Vercel auto-deploy.
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
**Diari completi:** fino a S78.
**Backlog diary:** S78 = no diary (session notes only). Nessun arretrato.

**Check di congruenza diary↔DB:** nessun check automatico attivo.

**Draft in coda:**
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-16 (S78 fase 2 CEO) | **TF Tier 1-2 reactivation parcheggiata** | Meccanismo tf_grid esiste, rischio basso, ma aggiungere variabili durante osservazione Sentinel Sprint 2 contamina baseline. Rivisitare dopo 5-7 giorni |
| 2026-05-16 (S78 fase 2 CC) | **SWEEP slippage buffer 3% shipped** | Root cause cashLeft<0: slippage SWEEP (+1.19% su BONK), non skim guard mancante. Buffer uniforme 3% in HardcodedRules. Ricalibrare post-mainnet (slippage mainnet tipicamente 10x più basso) |
| 2026-05-16 (S78 fase 2 CC) | **Banner buysLeft <= 0 corretto** | Non shortcut — buysLeft<0 è fisiologico post-SWEEP. Branch dedicato "swept, $X over by slippage" |
| 2026-05-16 (S78 fase 2 CC) | **Gitignore anchored fix** | `blog/` matchava ricorsivamente → blog post futuri silenziosamente esclusi. Fix: `/blog/` anchored a root |
| 2026-05-16 (S78 fase 2 CEO) | **Blog post 2 LIVE: "The Day Our Bot Ran Out of Money"** | Highlight V1 S16. Standalone, accessibile a nuovi lettori. Commit `dcc4372` + push → Vercel auto-deploy |
| 2026-05-16 (S78 fase 2 CEO) | **Cover evolution memo creato** | Storia copertine V1 (notte) → V2 (alba) → V3 (tempesta + mascotte easter egg). Per blog post futuro legato a V3 |
| 2026-05-15 (S78 fase 1 CEO) | **Primo blog post pubblicato (anticipato dal weekend 17-18)** | Origin story dual-voice già scritta e approvata. Brief 78a operativo (no testo touch, solo copy+build+push). Anticipa il "blog weekend" del Board, libera il weekend per Post 2 strategico ("why not live yet") |
| 2026-05-15 (S78 fase 1) | **Primo blog post = origin story a due voci (Max + CEO), non update strategico** | I lettori nuovi devono sapere chi siamo prima di interessarsi a dove siamo |
| 2026-05-15 (S78 fase 1) | **Reply strategy > posting frequency su X** | Il dato Montemagno (358 imp da una reply vs 78 media post) guida la nuova strategia. Vedi audit Area 3 marketing+SEO+X |
| 2026-05-15 (S78 fase 1) | **Tweet lancio blog: Opzione B (hook ironico)** | Scelta dal Board tra le opzioni presentate |
| 2026-05-14 (S77) | **Sentinel Sprint 1 audit PASS** | Tutti e 3 i bug calibrazione confermati fix (SoF 2.3%, risk 5 valori, opp 3 valori). Nessun codice aggiuntivo necessario |
| 2026-05-14 (S77) | **Sentinel Sprint 2 shipped** | Slow loop F&G + CMC ogni 4h, regime detection attivo. Sherpa propone con regime dinamico (prima era hardcoded "neutral") |
| 2026-05-14 (S77) | **Mapping regime invertito (contrarian)** | extreme_fear = risk basso / opp alta. Correzione CC, approvata Board ("buy fearful sell greedy") |
| 2026-05-14 (S77) | **CMC logged-only Sprint 2 MVP** | Dati BTC dominance / mcap / volume salvati ma non usati nel calcolo regime. Riservato Sprint 2.5 |
| 2026-05-14 (S77) | **3 design questions deferred** | speed_of_rise, funding morto testnet, opp score debole → rivalutare dopo osservazione Sprint 2 |
| 2026-05-14 (S76 CEO) | **Mainnet €100 posticipato a sistema completo (Grid + Sentinel testato + Sherpa attivato)** | Sherpa scriverà `bot_config` con soldi veri — va testato prima su testnet con Grid attivo. Grid-only mainnet avrebbe valore narrativo ma rischia quando Sherpa si accende. Sequenza: Sentinel fix → Sprint 2 → observe → Sherpa graduale su testnet → mainnet |
| 2026-05-14 (S76 CEO) | **Roadmap Sentinel-first in 5 step** | Step 1: audit+fix Sprint 1. Step 2: build Sprint 2 (F&G, regime). Step 3: osservazione 1 settimana. Step 4: Sherpa LIVE su testnet (1 parametro alla volta). Step 5: mainnet con sistema rodato. Timeline: fine giugno / inizio luglio |
| 2026-05-14 (S76 CEO) | **Sherpa attivazione graduale: un parametro alla volta** | Primo candidato: `sell_pct`. Osservare proposte per giorni prima di lasciar scrivere. Poi `buy_pct`. Permette di isolare problemi e bloccare fix |
| 2026-05-14 (S76 CEO) | **TF non abbandonato, ridefinito per tier** | Tier 1-2: stesso motore tecnico, regole swap più snelle, nessun Sentinel. Tier 3 (shitcoin): TF scout + Sentinel Sprint 3 valida catalyst → entry con timeout. Post-mainnet, richiede Sprint 3 funzionante |
| 2026-05-14 (S76 CEO) | **Blog weekend 17-18 maggio: 2 post** | Post strategico "why not live yet" + highlight V1/V2. Queste decisioni SONO il contenuto del blog |

> Decisioni S76 CC e precedenti spostate fuori dalla tabella per restare entro ~15 voci. Storico completo in git history e `PROJECT_STATE.md §4`.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
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

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Allineati su commit `9ceaa81` (S76 squash) + commit successivi S76 (fix + 75c + cleanup).

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno target |
| **TF non attivo** | parked post-osservazione Sentinel Sprint 2. Rivisitare ~S81-82 |
| **Audit Area 2 non eseguito** | dovuto (cadenza 90gg). CC ha flaggato in S78 fase 2 report. Proporre in prossima sessione di breathing |
| **Cover V3 non generata** | solo concept (tempesta + mascotte easter egg). Timing: quando V3 è vicino a chiusura |
| **Sherpa LIVE su testnet** | In attesa di 5-7 giorni osservazione Sprint 2 (~21-22 maggio) |
| **Dashboard /admin regime section** | CC la implementa autonomamente (brief non necessario) |
| **Sprint 3 (news feed)** | Post-osservazione Sprint 2, non prima di fine maggio |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post osservazione Sentinel Sprint 2 (5-7gg, ~21-22 maggio), o pubblicazione blog post 3 — whichever comes first.*
