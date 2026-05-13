# BUSINESS_STATE.md

**Last updated:** 2026-05-13 — Session 75 chiusura (sito pubblico: howwework v3 + Auditor entity, brief 75a blog infrastructure shipped, fix description Dashboard. Sitemap reinviata. Audit SEO meta tags completo).
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-13 (S75 chiusura, ultimo commit cd8ce65)

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 10 pagine live post-S75 (home, diary, dashboard, library, howwework, roadmap, blueprint, terms, privacy, **blog** infrastruttura pronta in attesa contenuti).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

**Sito online (S70c + S71 + S75):** TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE colorati. Public dashboard certificata vs Binance. **S71:** P&L hero unificato sulle 3 superfici via formula canonica `netWorth = cash + holdings_mtm + skim − fees`. Due metriche etichettate: Total P&L (oscilla, include unrealized) + Net Realized Profit (storico fisso, post-fees). **S75:** howwework v3 con Auditor entity (4° attore narrativo + diagramma React) + blog infrastructure pronta + dashboard meta description fix.

**Post X:** thread S69+S70 da verificare se pubblicato. Nessun nuovo post in coda da S71.

**Post X:** nessun post in coda (`pending_x_posts` vuoto). Scanner X automatizzato a cron settimanale dal 2026-05-04. Strategia: "variable reinforcement" — pubblica quando succede qualcosa di vero, mai calendar-driven. Posting Strategy v1.1 in `Posting_Strategy_v1_1.docx`.

**Payhip:** Volume 1 + Volume 2 live, **0/30 views totali** (segnalato da Board S68 come problema di invisibilità — sito offline + zero canale promozionale, non difetto del prodotto).

**Blog:** infrastruttura Astro Content Collections shippata da CC (brief 75a, commit `67f1f57`). Pagina /blog live in locale con 1 post placeholder (`draft: true`, escluso dalla build production). Deploy Vercel alla prossima push. CTA Payhip volume-aware (V1/V2 box dedicato; lesson cross-volume box generico con entrambi i volumi). Prossimo step: sessioni dedicate selezione contenuti V1 e V2 (riscritture discorsive, non copia-incolla del diary). Cadenza: irregolare ("variable reinforcement", coerente con strategia X).

**Ads/monetizzazione:** A-Ads live sul sito (crypto-native, revenue trascurabile). Buy Me a Coffee attivo (buymeacoffee.com/bagholderai). Nessuna sponsorship in pipeline.

**SEO/Analytics:** Umami Cloud (cookieless, GDPR) + Vercel Web Analytics. Progetto pre-traction, nessun dato di traffico significativo. **S75 — Sitemap Google Search Console:** reinviata (sitemap-index.xml + sitemap-0.xml). Stato ancora "Impossibile recuperare" — monitorare 24-48h. Sito comunque indicizzato (8 pagine, posizione media 8.6). **S75 — Audit SEO meta tags:** tutte le pagine coperte (title, description, OG, Twitter card). Unico fix: description Dashboard duplicava la homepage → SHIPPED da CC in commit `cd8ce65` (Layout.astro propaga unico prop a meta + og + twitter card).

**Partnership/eventi:** nessuno in corso né in pipeline.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, 96 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, 108 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

Preview rimosse da entrambi i volumi.

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53–74 in accumulo. Stima grezza chiusura: sessioni 78–85. Arco narrativo: Clean Slate → Testnet → FIFO Divorce → Fee Reckoning → The Stress Test (S73–74).

**Sessione corrente:** 75 COMPLETE (sito pubblico: howwework v3 Auditor + blog infra + dashboard meta description). 74 + 73 COMPLETE. Diary .docx S73 e S74 prodotti; S75 in coda di diary writing.

**Check di congruenza diary↔DB:** nessun check automatico attivo. Reconciliation gate nightly proposto ma non implementato.

**Draft in coda:**
- `drafts/2026-05-07_howwework_v3.md` — ready for review, deferred a sessione "sito pubblico"
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft, da sviluppare col CEO per Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-13 (S75) | **Blog: partire da V1/V2, non V3** | Chi arriva non ha contesto. V1/V2 chiusi = materiale stabile. V3 solo dopo pubblicazione |
| 2026-05-13 (S75) | **Blog: due tipi di post (highlight + lesson)** | Highlight = momento da una sessione. Lesson = tema trasversale. Alternare per varietà |
| 2026-05-13 (S75) | **Blog: cadenza irregolare (variable reinforcement)** | Coerente con strategia X. No calendario fisso |
| 2026-05-13 (S75) | **Sitemap: reinviata + sitemap-0.xml diretto** | Tentativo di sbloccare problema persistente da mesi |
| 2026-05-13 (S75) | **Project Knowledge > GitHub web_fetch per state files** | PK aggiornato a S74b, GitHub fermo a S63. Invertita priorità di lettura |
| 2026-05-13 (S75) | **howwework v3: coerenza piena (opzione B), non solo badge** | L'inconsistenza prose 3-vs-4 entities catturata in audit S75. Coerenza completa hero + meta + diagramma React (Auditor entity nuova) — il sito pubblico racconta esattamente il workflow attuale, niente drift cosmetico |
| 2026-05-13 (S75) | **CC autonomia operativa estesa: pull/push/restart/SSH** | Max esplicito: "oramai abbiamo sdoganato che pull e lanciare orchestrator e i bot lo fai tu, io non lo faccio più". Reflected nelle Rules of engagement 03/04 nuove formulazioni. Salvato in [[feedback_cc_runs_orchestrator]] |
| 2026-05-12 (S74b) | **bot_runtime_state come primitiva canonical** | Il bot scrive il suo stato in-memory ogni tick in 1 riga per symbol. Dashboard legge da lì, non più dai trades/events. Pattern stabile per ogni futuro "il dashboard non racconta la verità" |
| 2026-05-12 (S74b) | **Partial fill = trade reale (brief 74c)** | `status='expired'` con `filled>0` è un partial fill, non un no-op. Mainnet-gating chiusa. Fix 3 righe in exchange_orders.py |
| 2026-05-12 (S74b) | **DEAD_ZONE_HOURS per-coin in bot_config** | Migrato da hardcoded a parametro configurabile. BONK può avere 8h, BTC 2h. Sherpa-ready |
| 2026-05-12 (S74b) | **Dashboard stop-buy badge + trigger fix** | Badge rosso quando guardia attiva. Trigger calcolato da bot reference, non da trades |
| 2026-05-12 (S74) | **English everywhere (Telegram)** | 9 stringhe IT residue → EN. Più veloce che tradurre tutto IT, consistente cross-canale |
| 2026-05-12 (S74) | **Private-first, public later** | HWW v3 deferred. Prima sistemare ciò che vede l'operatore (admin, Telegram), poi il sito pubblico |
| 2026-05-12 (S73) | **Tutti i 4 cervelli su testnet prima del go-live** | Rischio operativo: restart per fix Sentinel può fermare trade reali. Team troppo piccolo per due ambienti. Go-live spostato a fine maggio/inizio giugno |
| 2026-05-12 (S73c) | **managed_holdings = wallet − phantom** | 9 punti hot path ora usano managed. Su mainnet phantom=0 → no behavior change |
| 2026-05-12 (S73c) | **Base amount per market buy** | Elimina LOT_SIZE rejection su book sottili. ccxt flag per impedire auto-conversione |
| 2026-05-12 (S73a) | **Dead Zone recalibration** | Dopo N ore idle con 1 lotto, forza reset ladder al prezzo corrente |
| 2026-05-11 (S72) | **Holdings = fetch_balance() golden source** | Wallet Binance unica verità. Replay DB solo per avg e realized |
| 2026-05-11 (S72) | **Frontend canonical refactor** | `pnl-canonical.js` shared. 4 superfici stessa funzione |
| 2026-05-11 (S72) | **TF sparisce da totali pubblici** | Homepage, dashboard, grid: solo Grid $500 |

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **Buy trigger anchor (A/B/C)** | Parcheggiata S74 PROJECT_STATE §6 | A=last_buy, B=avg, C=hybrid. Simulazione mostra trade-off spread vs compressione. Decisione strategica |
| **Stop-buy time-limit → brief 75b** | **PROGRAMMATA 2026-05-14** | Da "proposta parcheggiata" a brief concreto: timer parametrico `stop_buy_unlock_hours` in `bot_config` (pattern 74d). Default 24h. Motivazione empirica: perdita reale 2026-05-13. Refactor `grid_runner.py` come prerequisito strutturale (stesso giorno) |
| **Audit messaggi idle re-entry / recalibrate** | **PROGRAMMATA 2026-05-14** | Idle msgs sono rumore quando stop_buy attivo (mercato crollato → bot bloccato per ragione strutturale, non per assenza opportunità). Soppressione condizionale `if not stop_buy_active`. Trigger in grid_bot.py:854/878/906, send in grid_runner.py:964 |
| ✅ **HWW v3 "3 entities" prose inconsistency** | CHIUSA in S75 | Shipped opzione B (coerenza completa hero + meta + badge + diagramma React con 4° entity Auditor). Commit `f62f781` |
| ✅ **Fix description Dashboard** | CHIUSA in S75 | Shipped commit `cd8ce65`. Layout.astro propaga prop singolo a meta + og + twitter card |
| 🆕 **Monitorare sitemap Search Console post-24h** | Aperta | Se ancora "Impossibile recuperare" provare ping Google. Reinvio S75 |
| **Phantom BONK 1.37M composizione** | Bassa priorità | Molto più grande dell'initial gift stimato. Non bloccante |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **Go-live €100 mainnet** | Fine maggio / inizio giugno | Gate canonical state TUTTE CHIUSE. Restano: mobile smoke test, Sentinel/Sherpa 7gg DRY_RUN analysis, Board approval. 7 giorni clean run si resettano a zero se fix logic-changing deployato |
| **Sentinel/Sherpa data collection** | ~25 maggio | 14 giorni di DRY_RUN da brainstorming 11 maggio. 3 bug calibrazione noti (speed_of_fall, opportunity_score, risk_score binario) — decisione aperta: fixare ora e resettare, o aspettare 14gg con dati imperfetti |
| **Volume 3 pubblicazione** | Nessuna deadline | In accumulo. Arco narrativo si sta formando |
| **How We Work v3 sito** | Nessuna deadline | Draft pronto, deferred a sessione dedicata "sito pubblico" |
| **Blog section sito** | Infrastruttura pronta (S75), contenuti TBD in sessioni dedicate V1/V2 | 2-3 diary entries gratis come funnel a Payhip (0/30 views = invisibilità). Infra shippata brief 75a |

**Multi-macchina:** MBP (sviluppo Max) ↔ Mac Mini (runtime `/Volumes/Archivio/bagholderai`). Sempre `git pull` + mount Archivio prima di test/audit.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee, Stripe + PayPal). LemonSqueezy rifiutato (crypto risk flag). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Go-live mainnet** | Board decision S73: tutti i 4 cervelli devono girare insieme su testnet. Gate canonical chiuse, ma Sentinel/Sherpa DRY_RUN analysis non fatta |
| **Trend Follower riattivazione** | Necessita sessione brainstorming dedicata. Problemi strutturali: win/loss asymmetry, death spiral T3, distance filter paralysis. ENABLE_TF=false |
| **Sentinel/Sherpa fix calibrazione** | Decisione aperta: fixare subito (e resettare 14gg) o raccogliere dati imperfetti. CEO propende per fix ora |
| **How We Work v3 + blog + roadmap sito** | Deferred a sessione "sito pubblico" dedicata. Private-first |
| **Partnership / sponsorship** | Pre-traction. 0/30 views Payhip |
| **Phase 2 grid_runner split** | Post go-live. 1623 righe post-S74b (+32 da S68 per wiring `_upsert_runtime_state` + `dead_zone_hours`). Nessun brief formale — il vecchio riferimento "brief 62b" era stale (62b era sul refactor `grid_bot.py`, shipped + archiviato). Brief da redigere quando si apre la sessione |
| **HN outreach (dang email)** | Da fare, ma non urgente pre-go-live |

---

*Prossimo aggiornamento: post sessione Sentinel/Sherpa calibration fix, o post go-live decision — whichever comes first.*
