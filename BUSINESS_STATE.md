# BUSINESS_STATE.md

**Last updated:** 2026-05-12 — Session 74 chiusura (S73: dead zone + dust trap + phantom holdings + managed_holdings. S74: partial fill mainnet-gating chiusa, bot_runtime_state primitiva canonical, dashboard stop-buy + trigger fix, DEAD_ZONE_HOURS parametrico)
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-12 (S74b chiusura, ultimo commit 2f67533)

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 9 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, terms, privacy).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

**Sito online (S70c + S71):** TestnetBanner globale, Reconciliation table pubblica su /dashboard, TF "dal dottore" SVG inline, Sentinel/Sherpa badge TEST MODE colorati. Public dashboard certificata vs Binance. **S71:** P&L hero unificato sulle 3 superfici via formula canonica `netWorth = cash + holdings_mtm + skim − fees`. Due metriche etichettate: Total P&L (oscilla, include unrealized) + Net Realized Profit (storico fisso, post-fees).

**Post X:** thread S69+S70 da verificare se pubblicato. Nessun nuovo post in coda da S71.

**Post X:** nessun post in coda (`pending_x_posts` vuoto). Scanner X automatizzato a cron settimanale dal 2026-05-04. Strategia: "variable reinforcement" — pubblica quando succede qualcosa di vero, mai calendar-driven. Posting Strategy v1.1 in `Posting_Strategy_v1_1.docx`.

**Payhip:** Volume 1 + Volume 2 live, **0/30 views totali** (segnalato da Board S68 come problema di invisibilità — sito offline + zero canale promozionale, non difetto del prodotto).

**Blog/contenuto:** il contenuto pubblico è il diary sul sito (/diary) e i volumi Payhip. Nessun blog esterno. Daily CEO's Log via Haiku + X posting (OAuth 1.0a) attivo.

**Ads/monetizzazione:** A-Ads live sul sito (crypto-native, revenue trascurabile). Buy Me a Coffee attivo (buymeacoffee.com/bagholderai). Nessuna sponsorship in pipeline.

**SEO/Analytics:** Umami Cloud (cookieless, GDPR) + Vercel Web Analytics. Progetto pre-traction, nessun dato di traffico significativo.

**Partnership/eventi:** nessuno in corso né in pipeline.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, 96 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, 108 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

Preview rimosse da entrambi i volumi.

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53–74 in accumulo. Stima grezza chiusura: sessioni 78–85. Arco narrativo: Clean Slate → Testnet → FIFO Divorce → Fee Reckoning → The Stress Test (S73–74).

**Sessione corrente:** 74 BUILDING su Supabase, 73 COMPLETE. Diary .docx S73 e S74 prodotti.

**Check di congruenza diary↔DB:** nessun check automatico attivo. Reconciliation gate nightly proposto ma non implementato.

**Draft in coda:**
- `drafts/2026-05-07_howwework_v3.md` — ready for review, deferred a sessione "sito pubblico"
- `drafts/2026-05-07_diary_vol3_state_files.md` — seed draft, da sviluppare col CEO per Volume 3

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
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
| **Stop-buy time-limit** | Parcheggiata S74 PROJECT_STATE §6 | Proposta Max: dopo 24h di stallo, compra per abbassare avg. Trading logic, brief dedicato |
| **HWW v3 "3 entities" prose inconsistency** | Aperta | Draft aggiorna badge ma non hero prose. Da decidere in sessione sito pubblico |
| **Phantom BONK 1.37M composizione** | Bassa priorità | Molto più grande dell'initial gift stimato. Non bloccante |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **Go-live €100 mainnet** | Fine maggio / inizio giugno | Gate canonical state TUTTE CHIUSE. Restano: mobile smoke test, Sentinel/Sherpa 7gg DRY_RUN analysis, Board approval. 7 giorni clean run si resettano a zero se fix logic-changing deployato |
| **Sentinel/Sherpa data collection** | ~25 maggio | 14 giorni di DRY_RUN da brainstorming 11 maggio. 3 bug calibrazione noti (speed_of_fall, opportunity_score, risk_score binario) — decisione aperta: fixare ora e resettare, o aspettare 14gg con dati imperfetti |
| **Volume 3 pubblicazione** | Nessuna deadline | In accumulo. Arco narrativo si sta formando |
| **How We Work v3 sito** | Nessuna deadline | Draft pronto, deferred a sessione dedicata "sito pubblico" |
| **Blog section sito** | Nessuna deadline | 2-3 diary entries gratis come funnel a Payhip (0/30 views = invisibilità) |

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
