# BUSINESS_STATE.md

**Last updated:** 2026-05-11 — Session 71 chiusura (brief 71a pending cleanup shipped + BONK fee-in-base-coin diagnosticato → brief 71b separato + approccio sequenziale go-live)
**Updated by:** CEO
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-11 (S71 chiusura, commits 6021230 + 67614bd + 8a158dc + db3c6c1 + 5f2bcea)

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

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Sessioni 53–71 in accumulo, **nessun lavoro attivo** (Board: "prima i fondamentali"). Stima grezza chiusura: sessioni 75–80. Arco narrativo: Clean Slate → Testnet → FIFO Divorce → Fee Reckoning.

**Sessione corrente:** 71 BUILDING (pending cleanup + diagnosi BONK fee-in-base-coin → brief 71b). S70 COMPLETE su Supabase.

**Check di congruenza diary↔DB:** nessun check automatico attivo. **Reconciliation gate (nightly script)** proposto come task Validation System: verifica ogni notte che `Realized_avg_cost + Unrealized = Total P&L` chiuda al centesimo, alert se gap > $0.01. Da implementare insieme a brief 60b respec.

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-11 (S71) | **Go-live slips, approccio sequenziale** | Roadmap a fasi: (1) pending cleanup, (2) fee brainstorming + fix, (3) Sentinel/Sherpa analisi, (4) TF. Nessuna data fissa |
| 2026-05-11 (S71) | **P&L hero = NET fees ovunque** | Formula canonica: `cash + holdings_mtm + skim − fees − budget`. grid.html aveva ragione, pagine pubbliche fixate |
| 2026-05-11 (S71) | **Due numeri P&L etichettati** | Total P&L (include unrealized) + Net Realized Profit (storico, post-fees). Raccontano cose diverse, servono entrambi |
| 2026-05-11 (S71) | **Backfill solo testnet, paper resta as-is** | I 458 trade paper non avevano fee reali. Correggere con formula fee = "fixare" dati mai veri. Strada 2 ridotta a ~42 trade testnet (~1-1.5h) |
| 2026-05-11 (S71) | **Fee: brainstorming prima di codice** | BONK InsufficientFunds (gap 12.280 BONK fee-in-base-coin tra DB e Binance) dimostra che le fee toccano il core trading. Brief 71b scoped ma aspetta design session |
| 2026-05-10 (S70) | **FEE_RATE = 0.001 hardcoded** | Worst-case Binance. Se BNB discount, guadagno extra senza toccare codice |
| 2026-05-10 (S70) | **Sell graduale a scala (sell ladder)** | Speculare ai buy DCA. Ogni sell richiede +sell_pct% sopra l'ultimo. `_last_sell_price` traccia la scala |
| 2026-05-10 (S70) | **Sentinel ricalibrato + Sentinel/Sherpa DRY_RUN riaccesi** | 3 bug calibrazione fixati. Telegram OFF di default. 7 giorni raccolta dati |
| 2026-05-10 (S70) | **Reconciliation Binance Step A+B shipped** | 26/26 matched zero drift. Script manuale + pannello /admin + tabella pubblica |
| 2026-05-10 (S70c) | **"The story is the process, not the numbers"** | Board: cambi contabili retroattivi = materiale narrativo, non rischio reputazionale |
| 2026-05-10 (S70c) | **Net Realized Profit parcheggiato** | Bug strutturale realized_pnl gross scoperto. Brief dedicato "Strada 2" pre-mainnet |
| 2026-05-09 (S69) | **Avg-cost trading puro deployed + Strategy A simmetrico** | Chiusura completa del debito FIFO. Buy guard "no buy above avg" + sell guard "no sell below avg" specular |
| 2026-05-09 (S69) | **Budget testnet $500 confermato (no passaggio a $10K)** — Board | Niente vantaggio tangibile a scalare. Allocazioni invariate (BTC $200, SOL $150, BONK $150) |
| 2026-05-09 (S68) | **Filosofia "Trading minimum viable"** — Board | Solo Grid attivo, TF/Sentinel/Sherpa stay-but-off. 67 sessioni accumulate debt strutturale, restart concettuale del trading subsystem |
| 2026-05-08 (S67) | **Brief 67a SHIPPED: testnet live + fee design opzione A (USDT-equivalent canonical)** | Prima connessione reale a Binance, ccxt set_sandbox_mode. Una sola fonte di verità in USDT per dashboard/P&L/reconciliation |

---

## 5. Domande Aperte per CC (idee tech non ancora in brief)

**[S71 Board — URGENTE]**

- **Brief 71b — BONK holdings fee-in-base-coin**: `state.holdings += amount` gross, Binance dà net. Gap 12.280 BONK (0.74%), 31 sell rifiutati. Schema fix in report CC S71 §5. ~1-2h. **Aspetta design session "fee brainstorming"** (Board), poi primo task post-brainstorming.
- **Strada 2 ridotta (solo testnet)**: realized_pnl gross→net + avg_buy_price fix + backfill ~42 trade testnet + verifica identità. ~1-1.5h. Dopo 71b. Decisione S71: paper trade NON backfillati (non avevano fee reali).
- **Reconciliation Step C cron Mac Mini**: wrapper pronto in `scripts/cron_reconcile.sh`. Manca install crontab + TCC Full Disk Access quando Mac Mini torna online. ~10 min.

**[Aperte da S65-S70, ancora attive]**

- **BNB-discount fee future-proof** (S67) — se mainnet usa BNB per sconto 25%, `fee_usdt = 0` quando fee_currency=BNB. Trascurabile su €100, da risolvere pre-scale-up. Cross-tema con brief 71b + Strada 2.
- **Slippage_buffer parametrico per coin** (S70) — BONK testnet slippage 2.46% vs BTC/SOL ~0%. Brief separato pre-mainnet.
- **exchange_order_id null su sell** (S67) — sell OP/USDT non popola il campo. Fix: fallback clientOrderId. ~30min.
- **Recalibrate-on-restart** (S67) — buy_pct cambia spontaneamente a ogni restart. Da indagare: Sherpa scrive in bot_config durante DRY_RUN?
- **Phase 2 split di `bot/grid_runner.py`** (S68) — 1591 righe, di cui ~830 in `run_grid_bot()`. Split proposto in 5-6 moduli. ~3-4h. **DOPO go-live €100**.
- **Rename `manual` → `grid` su tutto il sistema** (S65) — superata parzialmente in S70 (DB + frontend); resta codice Python con riferimenti legacy.
- **Tradermonty full-repo scan** (S65) — solo 5/15+ skill valutate. Riprendere per Sentinel Phase 3 / TF improvements.
- **Esposizione pubblica Validation System** (S65) — milestone viva su /roadmap, contenuto interno. Decidere quanto esporre.
- **TF distance filter 12% fisso** (S63) — paralizza TF in mercato rialzista. Soglia dinamica regime-aware? Cross-tema Sentinel/Sherpa.
- **Rework comm Telegram post-`/admin`** (S63) — solo errori critici + buy/sell real-time in Telegram, tutto il resto in DB. Report serale aggregato. Da brief-are dopo Sentinel/Sherpa analisi.
- **Sherpa Sprint 2/3** (S63) — slow loop F&G+CMC + news feed CryptoPanic. Pre-requisito: replay counterfactual Sprint 1.
- **Surface coherence checks + schema verification + log file size monitor** (S65) — task Validation System, brief separato pre-mainnet o post.
- **Sito mobile review reale** (S70c) — smoke test desktop OK, audit statico CSS in S71 (1 fix recon table), ma test su device reale non eseguito.

---

## 6. Vincoli / Deadline Non-Tecnici

**Go-live €100 — target variabile, non più 21-24 maggio.** Approccio sequenziale: fee cleanup → Sentinel/Sherpa → TF → Board approval. Stima realistica: **fine maggio / inizio giugno 2026**.

**Pre-live gates aggiornate S71:**
- ✅ Contabilità avg-cost (S66)
- ✅ Fee USDT canonical (S67)
- ✅ Dust prevention (S67)
- ✅ Sell-in-loss guard avg_cost (S68a)
- ✅ DB schema cleanup (S68 + S69 DROP COLUMN)
- ✅ FIFO contabile via dashboard (S69)
- ✅ Avg-cost trading completo + Strategy A simmetrico + IDLE recalibrate guard (S69)
- ✅ sell_pct net-of-fees (S70)
- ✅ Reconciliation Binance Step A+B (S70)
- ✅ Sentinel ricalibrazione (S70b)
- ✅ Sito online con disclaimer testnet (S70c)
- ✅ P&L hero unificato (S71)
- ✅ LAST SHOT lot_step_size (S71)
- ✅ Reason bugiardo fixato (S71)
- ⬜ **Brief 71b BONK fee-in-base-coin** (gating — bot non può vendere BONK senza)
- ⬜ Strada 2 ridotta (P&L netto canonico solo testnet)
- ⬜ Reconciliation Step C cron (wrapper pronto, install pending Mac Mini)
- ⬜ Mobile smoke test reale
- ⬜ Sentinel/Sherpa analisi DRY_RUN
- ⬜ Board approval finale (Max)

**Multi-macchina:** MBP (sviluppo Max) ↔ Mac Mini (runtime `/Volumes/Archivio/bagholderai`). Sempre `git pull` + mount Archivio prima di test/audit.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee, Stripe + PayPal). LemonSqueezy rifiutato (crypto risk flag). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché no |
|---|---|
| **TF trading attivo** | In "osservazione" (dal dottore). Fase 4 della roadmap sequenziale |
| **Volume 3 in lavorazione** | Materiale S53–S71 si accumula. Chiusura quando l'arco narrativo ha un finale naturale |
| **Marketing outreach** | Pre-traction. Sito testnet online è step 1, mainnet è step 2 |
| **Sentinel/Sherpa LIVE** | In DRY_RUN dal S70. Analisi ~17 maggio, poi decisione Board |
| **Phase 2 grid_runner split** | Post go-live (1591 righe, brief 62b parcheggiato) |
| **Go-live €100 mainnet** | Fee cleanup in corso. BONK sell bloccati dal bug fee-in-base-coin. Pre-live gates non superate |
| **Sherpa Sprint 2/3 (slow loop + news feed)** | Pre-requisito: Sprint 1 counterfactual replay. Sentinel/Sherpa analisi prima |
| **Partnership / sponsorship / nuove piattaforme** | Pre-traction, prodotto in costruzione. Nessuna urgenza |
| **Nuovo prezzo volumi Payhip** | €4.99 prezzo di lancio. Nessun dato di vendita su cui ragionare (0/30 views) |
| **Audit esterni formali** | Protocollo introdotto S63. Primo audit pianificato post brief 71b + Strada 2 (numeri certificati) |

---

*Prossimo aggiornamento: post S72 (fee cleanup session — brief 71b + Strada 2 ridotta).*
