# BUSINESS_STATE.md

**Last updated:** 2026-05-14 — Session 76 (CEO session: S76 diary prodotto, roadmap Sentinel-first definita, decisione mainnet posticipata a sistema completo, visione TF Tier 3 + Sentinel Sprint 3 parcheggiata, blog weekend pianificato).
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-14 (S76 chiusura, ultimo commit `fe58388`)

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

**Blog weekend (17-18 maggio):** 2 post pianificati:
- **Post 1 — "Why We're Not Live Yet (And When We Will Be)"**: decisione strategica di oggi — perché mainnet è posticipato, roadmap Sentinel-first, timeline onesta.
- **Post 2 — Highlight da V1 o V2**: pezzo standalone per lettori nuovi (candidati: "The Day the Bot Ran Out of Money", "How We Taught an AI to Write Its Own Daily Log").

Cadenza blog: irregolare ("variable reinforcement"), coerente con strategia X.

**Post X:** nessun post in coda. Scanner X cron settimanale attivo. Strategia: pubblica quando succede qualcosa di vero.

**Payhip:** Volume 1 + Volume 2 live, 0/30 views totali.

**Ads/monetizzazione:** A-Ads live (revenue trascurabile). Buy Me a Coffee attivo. Nessuna sponsorship.

**SEO/Analytics:** Umami Cloud + Vercel Web Analytics. Sitemap reinviata S75, monitorare.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

**Volume 3** — in accumulo. Sessions 53+. Arco narrativo: Clean Slate → Testnet → Fee Reckoning → Stress Test → Sentinel-First Roadmap. Stima chiusura: sessioni 80-90.

**Sessione corrente:** S76 BUILDING. S75 COMPLETE. Diary .docx S73/S74/S76 prodotti. S75 .docx prodotto.

**Check di congruenza diary↔DB:** nessun check automatico attivo.

**Draft in coda:**
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-14 (S76 CEO) | **Mainnet €100 posticipato a sistema completo (Grid + Sentinel testato + Sherpa attivato)** | Sherpa scriverà `bot_config` con soldi veri — va testato prima su testnet con Grid attivo. Grid-only mainnet avrebbe valore narrativo ma rischia quando Sherpa si accende. Sequenza: Sentinel fix → Sprint 2 → observe → Sherpa graduale su testnet → mainnet |
| 2026-05-14 (S76 CEO) | **Roadmap Sentinel-first in 5 step** | Step 1: audit+fix Sprint 1. Step 2: build Sprint 2 (F&G, regime). Step 3: osservazione 1 settimana. Step 4: Sherpa LIVE su testnet (1 parametro alla volta). Step 5: mainnet con sistema rodato. Timeline: fine giugno / inizio luglio |
| 2026-05-14 (S76 CEO) | **Sherpa attivazione graduale: un parametro alla volta** | Primo candidato: `sell_pct`. Osservare proposte per giorni prima di lasciar scrivere. Poi `buy_pct`. Permette di isolare problemi e bloccare fix |
| 2026-05-14 (S76 CEO) | **TF non abbandonato, ridefinito per tier** | Tier 1-2: stesso motore tecnico, regole swap più snelle, nessun Sentinel. Tier 3 (shitcoin): TF scout + Sentinel Sprint 3 valida catalyst → entry con timeout. Post-mainnet, richiede Sprint 3 funzionante |
| 2026-05-14 (S76 CEO) | **Blog weekend 17-18 maggio: 2 post** | Post strategico "why not live yet" + highlight V1/V2. Queste decisioni SONO il contenuto del blog |
| 2026-05-14 (S76 CC) | **Refactor grid_runner.py → package 8 moduli** | 1623 righe monolite → package modulare. Prerequisito per 75b/75c. Zero behavior change |
| 2026-05-14 (S76 CC) | **Brief 75b + 75c stop-buy unlock con baseline** | Timer per-coin che sblocca stop-buy dopo N ore + baseline reset al current price per evitare re-arm immediato. 2 bug trovati da Board testing live |
| 2026-05-13 (S75) | **Blog: partire da V1/V2, non V3** | Chi arriva non ha contesto. V1/V2 chiusi = materiale stabile |
| 2026-05-13 (S75) | **Project Knowledge > GitHub web_fetch per state files** | PK aggiornato, GitHub fermo a S63 |
| 2026-05-12 (S74b) | **bot_runtime_state come primitiva canonical** | Bot scrive stato in-memory ogni tick. Dashboard legge da lì |
| 2026-05-12 (S74b) | **Partial fill = trade reale (brief 74c)** | Mainnet-gating chiusa |
| 2026-05-12 (S73) | **Tutti i 4 cervelli su testnet prima del go-live** | Confermata e rafforzata nella S76 CEO session |
| 2026-05-11 (S72) | **Holdings = fetch_balance() golden source** | Wallet Binance unica verità |
| 2026-05-11 (S72) | **Frontend canonical refactor** | `pnl-canonical.js` shared, 4 superfici stessa funzione |

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **Sentinel Sprint 1 audit + fix** | PROSSIMA SESSIONE CC | Verifica empirica 3 bug S63 (speed_of_fall, risk binario, opp morta). Dashboard /admin disponibile per osservazione live |
| **Sentinel Sprint 2 build** | Post fix Sprint 1 | F&G API + CMC dominance + regime detection. 2-3 sessioni CC stimate |
| **Integration test config reader chain** | Pre-prossimo brief bot_config | Gap strutturale scoperto S76. ~30-60 min |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |
| **Monitorare sitemap Search Console** | Aperta | Reinvio S75. Se ancora "Impossibile recuperare" provare ping |
| **Phantom BONK 1.37M** | Bassa priorità | Non bloccante |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **Go-live mainnet** | Fine giugno / inizio luglio | Posticipato da "18-21 maggio" a sistema completo: Grid + Sentinel testato + Sherpa attivato su testnet |
| **Sentinel Sprint 1 fix** | Prossima sessione CC | Gate per tutto il resto della sequenza |
| **Sentinel Sprint 2** | Post Sprint 1 fix | 2-3 sessioni CC |
| **Sherpa LIVE su testnet** | Post osservazione Sentinel 1 settimana | Un parametro alla volta (sell_pct primo) |
| **Blog primo post** | Weekend 17-18 maggio | 2 post pianificati con CEO |
| **Volume 3** | Nessuna deadline | In accumulo, arco narrativo si forma |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). Allineati su commit `9ceaa81` (S76 squash) + commit successivi S76 (fix + 75c + cleanup).

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Go-live mainnet €100** | Decisione S76 CEO: Sherpa scriverà bot_config con soldi veri, va testato prima su testnet. Sequenza Sentinel-first definita. Fine giugno target |
| **Sentinel Sprint 2** | Sprint 1 ha 3 bug noti. Fix prima, build dopo |
| **Sherpa LIVE** | Dipende da Sentinel funzionante. Senza sensore affidabile, l'attuatore muove cose a caso |
| **TF riattivazione** | ENABLE_TF=false. Tier 1-2 da testare su testnet quando ci si arriva. Tier 3 (shitcoin) richiede Sentinel Sprint 3. Post-mainnet |
| **Blog contenuti** | Infrastruttura pronta (S75). Primo contenuto weekend 17-18 maggio |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Cambio prezzo volumi** | Nessun dato di vendita su cui ragionare |

---

*Prossimo aggiornamento: post blog weekend, o post Sentinel Sprint 1 fix — whichever comes first.*
