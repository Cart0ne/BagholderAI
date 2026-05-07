# BUSINESS_STATE.md

**Last updated:** 2026-05-07 — Session 63 (init)
**Updated by:** CEO (Claude, Projects)
**Basato su:** PROJECT_STATE.md committato 2026-05-07 (fine S63 init)

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

**Post X:** nessun post in coda (`pending_x_posts` vuoto). Scanner X automatizzato a cron settimanale dal 2026-05-04. Strategia: "variable reinforcement" — pubblica quando succede qualcosa di vero, mai calendar-driven. Posting Strategy v1.1 in `Posting_Strategy_v1_1.docx`.

**Blog/contenuto:** il contenuto pubblico è il diary sul sito (/diary) e i volumi Payhip. Nessun blog esterno. Daily CEO's Log via Haiku + X posting (OAuth 1.0a) attivo.

**Ads/monetizzazione:** A-Ads live sul sito (crypto-native, revenue trascurabile). Buy Me a Coffee attivo (buymeacoffee.com/bagholderai). Nessuna sponsorship in pipeline.

**SEO/Analytics:** Umami Cloud (cookieless, GDPR) + Vercel Web Analytics. Progetto pre-traction, nessun dato di traffico significativo.

**Partnership/eventi:** nessuno in corso né in pipeline.

---

## 3. Diary Status

**Volume 1** — "From Zero to Grid" (Sessions 1–23, 96 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/a4yMc

**Volume 2** — "From Grid to Brain" (Sessions 24–52, 108 pagine, €4.99). LIVE su Payhip: https://payhip.com/b/NHw53

Preview rimosse da entrambi i volumi.

**Volume 3** — prossimo target di pubblicazione. Coprirà sessions 53+. Nessuna struttura definita ancora. La session 63 è appena iniziata; il volume si chiuderà naturalmente quando un arco narrativo sarà completo (stima grezza: sessioni 70–80).

**Sessione corrente:** 63 (init). Session 62 diary .docx prodotto; entry in `diary_entries` da chiudere a COMPLETE.

**Check di congruenza diary↔DB:** nessun check automatico attivo. È un TODO nel Validation System §3 ("Diary entry in Supabase = diary .docx"). Da automatizzare.

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-05-07 | Audit protocol introdotto: `PROJECT_STATE.md` + `BUSINESS_STATE.md` + cartella gitignored `audits/` | Continuità multi-sessione/multi-macchina. Primo canale formale per audit esterni (commits `57aff52`, `e20704c`) |
| 2026-05-07 | Grid Phase 1 completata: split monolite 2200 righe → 6 moduli, zero cambi di comportamento | Prerequisito per Phase 2 (fix 60c + dust). API pubblica `GridBot` invariata (commit `be45fca`) |
| 2026-05-07 | Dashboard admin Sentinel+Sherpa: design approvato, implementazione bloccata | ~9h frontend, ma toccare costanti Grid durante DRY_RUN invalida il counterfactual. Sbloccato post replay (~13 maggio) |
| 2026-05-07 | FIFO-correct P&L per-row nelle dashboard `/admin`, `grid.html`, `tf.html` (60d/60d-bis) | Le tabelle leggevano `realized_pnl` DB (biased) anziché FIFO client-side (commits `0750027`, `21caff0`) |
| 2026-05-06 | Sentinel + Sherpa Sprint 1 deployed (DRY_RUN) | Terzo e quarto cervello operativi. Raccolta dati per counterfactual. Nessun impatto su trading finché `SHERPA_MODE` resta `dry_run` (commit `83b253c`) |
| 2026-05-06 | Dust management: Opzione 3 (prevenire alla fonte + safety net Binance API) | Grid eviterà di creare dust (Phase 2). Safety net: dust converter settimanale post-go-live |
| 2026-05-06 | Sentinel/Sherpa write rate -70% via dedup + filter + retention 30/60gg | Tabelle nuove rischiavano di esplodere il piano Supabase free (commit `0246b22`) |
| 2026-05-05 | Validation & Control System creato (S59), promosso a living milestone | 8 sezioni, specchiato in Phase 9 roadmap. §7 post-go-live + §8 log hygiene aggiunti |
| 2026-05-05 | Osservazione 7 giorni FIFO + health check avviata | Pre-live gate. Il refactoring Grid resetterà il conteggio dei 7 giorni clean |
| 2026-05-05 | httpx/telegram loggers a WARNING in tutti gli entry-point | 23 MB di log con token Telegram in chiaro per 19 giorni. Root cause: httpx loggava ogni long-poll (commit `bbc8477`) |
| 2026-05-05 | Report Equity P&L vs FIFO realized (CC) | Gap strutturale $4.53. **DECISIONE CEO PENDENTE — vedi §6** |
| 2026-05-04 | Fix exit protection holes (trailing peak reset + SL/TP su open value) | DOGE/INJ venduti per peak/base stale (commit `6dcc56f`) |

---

## 5. Domande Aperte per CC (idee tech non ancora in brief)

1. **Equity P&L nella home** — proposta 1 del report CC 05/05: secondo numero "Equity P&L" affiancato al FIFO realized. Stima CC: 1–2 ore. Aspetta decisione CEO (§6).

2. **Allineamento sell-decision a FIFO globale** — proposta 2 del report CC 05/05: il bot vende basandosi su `avg_buy_price` (media mobile) che diverge dal costo FIFO del lotto in uscita. Su mainnet = vendere lotti in perdita FIFO credendoli in profitto. Stima CC: 1 giorno. **Vero gating tecnico per mainnet**, da posizionare nella timeline post-Phase 2.

3. **Log file size monitor + log rotation** — §8 del Validation System. Stima CC: 2–4 ore. Brief separato, bassa priorità finché Phase 2 Grid è in corso.

4. **Schema verification automatica** — §1 Validation System, TODO. Confronta colonne DB con aspettative codice.

5. **Surface coherence checks** — §2 Validation System: homepage = dashboard = Telegram P&L. Tutto TODO. Da brief-are dopo stabilizzazione numeri post-Phase 2.

6. **Tradermonty full-repo scan** — parcheggiato. Solo 5 skill su 15+ valutate. Riprendere per Sentinel Phase 3 / TF improvements (brief `evaluate_trading_skills.md`).

7. **Esposizione pubblica Validation System** — il documento è milestone viva su /roadmap ma il contenuto è interno. Quanto esporre pubblicamente? Da decidere quando si apre una pagina pubblica dedicata.

---

## 6. Vincoli / Deadline Non-Tecnici

**Go-live €100 — timeline realistica: qualche mese, non settimane.** PROJECT_STATE.md è esplicito: "architettura completa = TF + Sentinel + bot orchestrator superiore, non solo bug-fix". Percorso critico corrente:

- Phase 1 Grid refactoring: ✅ completata (commit `be45fca`)
- Phase 2 Grid (fix 60c + dust): in attesa di piano CC (brief 62b)
- Clean run 7 giorni post-Phase 2
- Sell-decision alignment a FIFO (proposta 2 CC) — da posizionare
- Sentinel Sprint 2 (slow loop) + maturation
- Wallet reconciliation Binance (post go-live)
- Board approval finale (Max)

**Pre-live gates (Validation System §6):**
- FIFO integrity: ✅
- Zero FIFO drift 7 giorni: 🔲 (il conteggio riparte dopo Phase 2)
- Health check 100% 7 giorni: 🔲 (stessa nota)
- DB retention stabile: ✅
- Board approval (Max): 🔲

**⚠️ DECISIONE PENDENTE — Equity P&L vs FIFO realized:**

Dal report CC 2026-05-05 e punto 6.1 di PROJECT_STATE.md: *"Equity P&L Binance ($48.16) vs FIFO realized ($52.69): gap strutturale $4.53. Quale numero diventa canonico nella dashboard pubblica e nel diary? È gating per il go-live €100?"*

**Raccomandazione CEO:**

- **Dashboard pubblica:** mostrare entrambi affiancati. FIFO realized = "quanto abbiamo incassato". Equity P&L = "quanto vedremmo su Binance chiudendo tutto". Proposta 1 di CC (1–2 ore) è la soluzione giusta.
- **Diary:** FIFO realized come numero operativo; citare il gap equity come nota di onestà quando rilevante. Delta del 9%, non un ordine di grandezza.
- **Go-live gating:** il gap numerico non è gating di per sé. **Quello che è gating è la proposta 2 di CC** (allineare la sell-decision a FIFO globale). Senza, il bot su mainnet vende lotti in perdita FIFO pensando di essere in profitto. Da posizionare in Phase 2 o subito dopo.

**DRY_RUN Sherpa:** raccolta dati ~7 giorni (start ~6 maggio, deadline implicita ~13 maggio). Durante questa finestra: NON modificare costanti Grid. Admin dashboard Sentinel+Sherpa read-only fino a post-replay. Decisione `SHERPA_MODE=live` = 1–2 settimane + Board approval. Percorso indipendente dal go-live €100.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee, Stripe + PayPal). LemonSqueezy rifiutato (crypto risk flag). Nessuna urgenza di cambiare.

**Multi-macchina:** MBP (sviluppo Max) ↔ Mac Mini (runtime `/Volumes/Archivio/bagholderai`). Sempre `git pull` + mount Archivio prima di test/audit.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché no |
|---|---|
| **Nessun marketing attivo** | Pre-traction. Il prodotto (story) è in costruzione. Spingere traffico ora = mostrare un cantiere incompleto. Strategia flag-it-when-it-happens |
| **Nessun Volume 3 in lavorazione** | Le sessions 53+ sono in corso. Il volume si chiuderà naturalmente su un arco narrativo chiuso |
| **Nessuna dashboard /sentinel pubblica** | Sprint 2+. DRY_RUN non ha dati sufficienti per un'interfaccia utile. Design approvato, codice bloccato fino a post-replay (~13 maggio) |
| **Nessun Sentinel slow loop (F&G + CMC)** | Sprint 2. Sprint 1 (fast loop BTC + funding) deve raccogliere dati e fare replay counterfactual prima |
| **Nessun go-live €100** | Pre-live gates non superate. Phase 2 Grid ancora da fare. Architettura completa (TF + Sentinel maturo + orchestrator superiore) richiede mesi, non settimane |
| **Nessuna partnership esterna** | Il progetto non ha traction. Prematuro cercare partner senza prodotto finito e traffico organico |
| **Admin dashboard Sentinel+Sherpa non implementata** | Design pronto (~9h frontend). Bloccata: toccare costanti Grid durante DRY_RUN invalida il counterfactual |
| **Nessun cambio prezzo volumi** | €4.99 è il prezzo di lancio. Nessun dato di vendita su cui ragionare |
| **BTC in portafoglio live** | Costi di conversione USDT→BTC troppo alti per budget €100. Decisione differita |
| **Audit esterni** | Protocollo appena introdotto (S63). Primo audit previsto: V1 Calibration su Sentinel↔Sherpa↔Grid post-Phase 1. Nessuno completato ancora |

---

*Prossimo aggiornamento: a fine sessione 63 o alla prossima sessione strategica.*
