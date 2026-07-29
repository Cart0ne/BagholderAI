# BUSINESS_STATE.md

**Last updated:** 2026-07-22 — S122 (Fase 2b GO-LIVE Kraken, denaro reale). §4 +5 (Opzione B confermata, proxy volatilità Binance /USDT, fee-drag A, restart unico, CMC scartata), §5 +3 (CMC-Sentinel, tf.html, orchestrator-poll RISPOSTO), §3 diary S122 BUILDING — contenuti CEO (`config/BUSINESS_STATE_update_S122.md`), merge+git CC (§2b). ✅ **COMPACTION ESEGUITA 2026-07-29** (CC, su autorizzazione esplicita di Max): 59KB → **35KB**, 91 righe rimosse da §2/§4/§5/§6/§7 (decisioni ≤2026-07-01 non più portanti, domande CC chiuse, vincoli scaduti, voci §7 superate dal go-live 2b) — **tutte archiviate integralmente** in `audits/BUSINESS_STATE_archive.md`, verifica automatica "0 righe perse". ⚠️ **Per il CEO**: la compaction NON riscrive i contenuti — restano da rinfrescare a mano diverse frasi stale post-S122 in §2/§3/§6/§7 (territorio CEO). · Prec.: 2026-07-17 — S119 chiusura (primo ordine reale su Kraken; indagine S119b; nodo 5 rinviato a pre-2b). §2 +marketing (primo click Google), §3 S119 COMPLETE, §4 +7 righe, §5 +1, §6 +2, §7 +2 — su istruzione CEO (brief S119c) via Max. Cap file 50KB ±2KB (CLAUDE.md §2b). Cadenze audit canoniche in PROJECT_STATE §9. **Corr. tecnica 2026-07-20 (CC, aut. Max):** trigger SELL Kraken §4/§6 $65.271→**$66.314** (formula fee-buffered `grid_bot.py:876`, non avg×1,02 — dettaglio PROJECT_STATE §5). Prec.: 2026-07-13 — S119 Fase 2a/2b split + venue=binance (via Max); 2026-07-11 — S117 (chiavi Kraken + Fase 0 18/18; fee 0,80% tier-0).
**Updated by:** CEO (S122 via `config/BUSINESS_STATE_update_S122.md`, merge+git CC)
**Basato su:** PROJECT_STATE.md corrente + `report_for_CEO/2026-07-16_S119_RforCEO_kraken-fase2a.md` + `report_for_CEO/2026-07-17_S119b_RforCEO_kraken-replay-avg-reconcile.md`

> 📍 **Dove vive cosa** (per CEO e CC): [KNOWLEDGE_MAP.md](KNOWLEDGE_MAP.md) in root del repo indicizza tutti i doc durevoli — stato, playbook, runbook, architettura, archivi, e cosa è gitignored.

---

## 1. Brand & Messaging

BagHolderAI è un progetto sperimentale dove un'AI (Claude) gestisce un micro-business di crypto trading con supervisione umana (Max, Board). Il prodotto reale non è il bot — è la storia documentata del processo. "Crypto is the lore, not the product."

**Positioning:** AI-runs-a-startup narrative + radical transparency. Ogni decisione, fallimento e pivot è documentato pubblicamente.

**Tone of voice:** self-deprecating, honest, technical-but-accessible. Il CEO (Claude) dubita più di quanto riporti. Personalità definita in `Personality_Guide.docx`.

**Target audience:** tech-curious readers, AI enthusiasts, indie hackers. Non crypto traders professionisti.

**Domain:** bagholderai.lol (Porkbun). Sito Astro su Vercel. 11 pagine live (home, diary, dashboard, library, howwework, roadmap, blueprint, blog, income, terms, privacy).

**Social:** X @BagHolderAI (22+ post, posting organico non schedulato). Telegram @BagHolderAI_report (canale pubblico, report giornalieri).

---

## 2. Marketing In-Flight

### S119 — primo denaro reale + segnale distribuzione (17-lug)
- **Primo click organico da Google (17-lug).** GSC 3 mesi: **1 click · 417 impressioni · posizione media 15,1 · CTR 0,2%**. È il primo in assoluto. Lettura onesta: da pagina 2 lo 0,2% è il CTR atteso — il click dice più di chi ha scrollato che di noi. **Ma è il secondo strumento indipendente** che conferma la diagnosi S116: Payhip 247 view / 0 checkout, Google 417 impressioni / 1 click. Due misure, una diagnosi: **non arriva nessuno**. Il buco è a monte, non nel prodotto.
- **Nessun annuncio del test da $25** (vedi §4). Deroga alla regola no-post-ven/sab/dom: **valutata e non usata**.

### Blog
- Post 1 LIVE 2026-05-15: "An AI That Can't Trade, a Human That Can't Say No"
- Post 2 LIVE 2026-05-16: "The Day Our Bot Ran Out of Money"
- Post 3 LIVE 2026-05-19: "When Your AI CEO Lies About the Numbers"
- **Post 4 LIVE 2026-05-28: "How Three Claudes Run a Company"** — bagholderai.lol/blog/how-three-claudes-run-a-company. Volume:3 / type:lesson. Meta/workflow post (CEO + intern + Haiku + Max). Pubblicato S90 commit `1b28e2a`
- **Post 5 LIVE 2026-05-31: "AI Is Useful. But It Doesn't Think Like We Do."** — bagholderai.lol/blog/ai-is-useful-but-it-doesnt-think-like-we-do. Ripubblicato da Dev.to (`noRss:true`), chiude drift blog↔Dev.to (audit A3)
- **Post 6 LIVE 2026-06-01: "The Solution Was One Sentence. My AI Took Two Days."** — bagholderai.lol/blog/the-solution-was-one-sentence. Type lesson, saga audit/overengineering (Human + CEO)
- **Post 7 LIVE 2026-06-02 — SEO+GEO POST 1: "I Used Claude Code to Build a Crypto Trading Bot. 94 Sessions Later, Here's What Works."** — bagholderai.lol/blog/claude-code-crypto-trading-bot. Primo dei 5 post SEO+GEO (brief S95a), FAQPage schema. Vedi sub-sezione "Strategia SEO+GEO" sotto
- _(→ **10 post pubblicati** totali, coerente con §3. I "Post 6/7 PLANNED" qui sotto sono titoli di backlog, numerazione non sequenziale)_
- Post 6 PLANNED: "Why We're Not Live Yet" — a ridosso go-live
- Post 6 PLANNED: "We Built an Accounting System That Didn't Need to Exist" — FIFO saga, V3. ~inizio giugno.
- Post 7 PLANNED: "45 Sessions With an AI Co-Founder: The Unfiltered Version" — prefazione V2 adattata, voce Max. ~90% pronto.
- **Pipeline (aggiornata S85):** 13 post schedulati + 11 in backlog (Apple Note "BagHolderAI — Blog Content Pipeline"). Backlog V3 include: Operation Clean Slate, 4 Bugs in 60 Seconds, The Intern Runs the Office, Brain Can't Tell BONK from Bitcoin, The One Where Nobody Writes Code.
- Idea futura: "Cover Evolution" (memo in `drafts/cover_evolution_memo.md`). Timing: quando V3 è vicino a chiusura.
- **Ordine editoriale NON cronologico** (S85): ogni post autonomo, pescato da qualsiasi punto della timeline — vetrina, non racconto lineare.
- **Frequenza ~1 post ogni 7-10 giorni** (S85), pubblicazione a raffiche con distribuzione attiva. No calendario fisso ("variable reinforcement").
- **RSS feed live** (S85, commit `8c9c2fc` + `18eaa24`): `https://bagholderai.lol/rss.xml` con `<content:encoded>` (body completo). Autodiscovery `<link rel="alternate">` nel Layout.
- **(S96)** Blog post "32 hours" pronto per pubblicazione con nuovo sito.
- **(S96)** Post scrappato da agdal.tech (trovato via Bing Webmaster Tools) — monitorare nel prossimo audit A3, nessuna azione immediata.

### Payhip
- Volume 1 + Volume 2 + **Volume 3 LIVE**: https://payhip.com/b/hCWNX (€4.99, "From Brain to Eyes", Sessions 53–82)
- Payhip store: https://payhip.com/BagHolderAI
- Redirect `/buy` ora punta allo store (non più a V1 singolo) — vercel.json aggiornato S87
- 39 views maggio (pre-V3 launch), 0 vendite, 0 ordini

## 3. Diary Status

**S119 COMPLETE** — *"The One Where Everyone's Numbers Were Wrong"* (13–17 luglio). `.docx` prodotto, `diary_entries` aggiornata dal CEO via MCP. Diario S118 scritto (.docx, "The One Where 28 Out of 28 Wasn't Enough"). **Volume 4 "From Eyes to Live": l'arco è passato dalla porta — S119 è il primo denaro reale.** ⚠️ **S110 ancora in BUILDING (mai chiusa) — da risolvere.**
**Interludio scritto:** "Thirteen Impressions" (copre S106-S107: visual identity per umani + SEO identity per macchine).
- Volume corrente pubblico: V3 "From Brain to Eyes" (live). **V4 "From Eyes to Live" in corso** (arc: NewsKeeper → go-live → results).
- Ultima entry diary: **S121 COMPLETE** (Supabase); **S122 "The One Where the Board Just Asked Why" — BUILDING**. Volume 4 "From Eyes to Live" in corso (S122 = 2b go-live, primo denaro reale su Kraken).
- Prossimo check di congruenza diary: invariato.

**Volumi pubblicati:**
- Volume 1 "From Zero to Grid" (S1–S23, €4.99) → https://payhip.com/b/a4yMc
- Volume 2 "From Grid to Brain" (S24–S52, €4.99) → https://payhip.com/b/NHw53
- Volume 3 "From Brain to Eyes" (S53–S82, €4.99) → https://payhip.com/b/hCWNX (lanciato 27 maggio 2026)

**Volume corrente: 4** — "From Eyes to Live" (S83+, €4.99 planned). Aperto a S83. Arco narrativo: NewsKeeper build → go-live → primi risultati reali.

**Blog post pubblicati: 10** (ultimo: "Vibe Coding a Real Business", 2026-06-18 commit `acbed3b`; prec. "How a Non-Coder Manages 5 AI Brains", S104)
**Draft blog in coda: 2** (POST 2/5; vibe-coding **PUBBLICATO** 2026-06-18, commit `acbed3b`): `why-most-ai-trading-bots-fail.md` (**SEO già forte** — head keyword "ai trading bot" + FAQ completo + intro GEO; serve SOLO intro umana two-voice [+ eventuale reframe closing] → **priorità pubblicazione**), `ai-crypto-trading-bot-real-testnet-results.md` (parcheggiato, pieno di TODO, post-mainnet). Cadenza 1 ogni 1-2 settimane.

**Sessioni pendenti di diary:** S73/S74/S77/S78/S79 da verificare docx (V3, bassa priorità). S111 diary scritto e inserito in Supabase (2026-06-29).

**Draft diary seed in coda:** nessuno (seed V3 rimosso a S87).

---

## 4. Decisioni Strategiche Recenti

| Data | Decisione | Perché |
|---|---|---|
| 2026-07-22 (S122) | **Opzione B CONFERMATA — Fase 2b = $100 BTC/USD su Kraken Sherpa-driven.** ⚠️ **Revisione esplicita della decisione S119 del 2026-07-13** ("$100 sequenziale grid-only → sistema pieno SOLO dopo") | La 2a ha già eseguito un round-trip reale completo a parametri statici (BUY $25 17-lug → SELL 21-lug, +$0,7069 netto). Ripetere lo stesso test con $100 non produce informazione nuova. Costo accettato consapevolmente: **diagnosticabilità** — se la 2b va male non sapremo di primo acchito se ha sbagliato la meccanica o la scelta di Sherpa. Accettabile perché il fix `ed1933d` garantisce che ogni singola vendita sia in utile netto: il caso peggiore è "guadagna poco", non "perde" |
| 2026-07-22 (S122) | **Sorgente volatilità Sherpa su Kraken = proxy Binance /USDT** (non OHLC nativo Kraken) | BTC/USD e BTC/USDT hanno volatilità realizzata praticamente sovrapponibile; riusa infra Binance esistente, zero superficie API nuova su un path che gira di continuo sui 4 grid vivi. Coerente con S112 (funding-rate resta su Binance, dato pubblico read-only EU-ok). **Limite noto registrato**: su SOL/BONK in Fase 3 la divergenza tra venue può essere maggiore — non blocca la 2b, va ritrovato quando ci arriviamo |
| 2026-07-22 (S122) | **Fee-drag: opzione (A) osservare**, NON minimo `sell_pct` Kraken-aware adesso — ma con **obbligo di misura** (4 numeri a fine 2b: n° trade, fee totale, P&L lordo vs netto, `sell_pct` medio Sherpa) | Fissare ora una tara significherebbe inventare un numero senza dati e poi difenderlo. Il collaudo serve a produrlo. Ma "osservare" senza strumenti equivale a non fare niente: la misura è nello scope del brief `sherpa-on-kraken` (script `kraken_fee_drag_report.py` shipped) |
| 2026-07-22 (S122) | **Restart unico** per la finestra 2b — codice nuovo e accensione Kraken live insieme. Proposta CEO di restart in due tempi **ritirata dal CEO stesso** dopo obiezione del Board | Il CEO proponeva una notte di osservazione sui soli grid testnet prima del denaro vero. Max ha chiesto perché. Motivo del ritiro: in T0 la riga Kraken sarebbe stata `is_active=false`, quindi il codice davvero nuovo (Sherpa che legge la riga Kraken + fix volatilità) **non sarebbe stato esercitato**. 24h per osservare la parte già coperta dai 340 test, accendendo comunque al buio il giorno dopo. **Obiezione del Board superiore alla proposta del CEO** |
| 2026-07-22 (S122) | **CoinMarketCap Pro API (piano free) scartata come sorgente volatilità** | Il free dà prezzo live ogni minuto, non serie storica (a pagamento). Costruirsi la serie campionando = codice nuovo + giorni di accumulo + gestione buchi, per ciò che Binance dà già pronto e gratis. **Parcheggiata** invece come possibile sorgente Sentinel (dominance, market cap, breadth) — vedi §5 |
| 2026-07-21 (S121) | **Fase 2b = Opzione B: $100 Sherpa-driven su BTC** (non parametri statici). Poi scaling capitale *man mano* (BTC→$250, SOL ~$150, BONK ~$100 **subordinata a check book/spread Kraken**), **senza** collaudo per-coin cerimoniale — ma ogni moneta NUOVA si becca la sua finestra di primi-cicli osservati. **Gate 2b**: fix nodo-5 (doppio-conteggio fee) + decisione ancora-buy dopo-sell (memo Fase 2b §4) + solo le righe volute `is_active=true` + processo daemonizzato con log + criterio di accettazione concreto PRIMA di scalare capitale. **Supera** la decisione S119 (13-lug: "$100 grid-only sequenziale BTC→SOL→BONK, sistema pieno solo dopo") | Spot cap $100 → rischio-soldi **identico** static vs Sherpa: il trigger fee-buffered protegge ogni singola vendita a prescindere dal guidatore. Testare direttamente la config di produzione evita un giro a vuoto su parametri che poi si buttano. **Obiezione CEO sul lato-buy ritirata** (cap spot la chiude); residuo "osservabilità con 2 parti mobili" = preferenza, non gate. Il fix nodo-5 diventa **gate DURO**: con Sherpa al volante l'intenzione (`sell_pct`) deve = margine realizzato, oggi non lo è (1% → 1,8%). BONK: liquidità/book Kraken è il punto interrogativo (storico slippage 2,46% testnet) → decide il dato, non pre-impegno |
| 2026-07-17 (S119) | **Primo ordine reale eseguito** — $25 BTC/USD su Kraken, riga isolata `is_active=false` + `KRAKEN_TEST_MODE`, sorvegliato. `OCILGP-2GRMI-D3WSNK`: 0,00039379 BTC @ $63.483,50, costo $24,99917, fee $0,19999 USD | `fill confirmed via fetch_order after 3.1s` = **il fix critico S119 in azione**: un solo BUY, nessun loop. Kraken non ha testnet → il fix poteva essere certificato **solo** da denaro vero; 297 test verdi non bastavano. Tripla conferma incrociata log / API Kraken / DB. **Fee live 0,7999% = tier EU 0,80% ri-confermata** (già chiusa in S117b/Fase 0 con 2 fonti; questa è la terza). **Fase 2a resta APERTA**: un buy è mezzo ciclo, serve un SELL registrato |
| 2026-07-17 (S119) | **Funding path corretto: deposito EUR → conversione manuale EUR→USD → trading /USD** | I "$100" caricati erano **€97,80**. Le coppie `/USD` si tradano solo con USD reali sul conto: il toggle EUR/USD dell'interfaccia Kraken è una **vista**, non converte l'asset. Scoperto sul campo, non nel design. Costo: spread di conversione ad ogni rabbocco. **Va nel runbook Fase 2b** |
| 2026-07-17 (S119) | **Nessun annuncio pubblico del test da $25 — la carta "primo denaro reale" resta per il collaudo** | `COLLAUDO_COMMS_GUIDELINES` §1: la milestone si gioca **una volta sola**. Il test è Fase 2a su una riga che il sito pubblico non vede; il collaudo è Fase 3 ($100, K.3, badge "real money, real Kraken"). Annunciare ora brucia la carta e contraddice una homepage pinnata a `venue=binance` → incoerenza narrazione↔codice (territorio audit Area 2) |
| 2026-07-17 (S119) | **Status line pubblica corretta** (non "aggiornata"): da *"Phase 1 wired, still asleep · before any real trade"* a *"One supervised $25 order on Kraken · real money, real fill, no loop · the sell hasn't come yet"* 🔬 | Alle 18:45 la riga precedente è diventata **falsa** sulla superficie più pubblica del progetto. Il post è opzionale, la verità del badge no. Distinzione: **push** (annuncio, rivendica) vs **cronaca** (dice dove siamo). **Nessuna automazione**: quando il SELL arriva la riga torna falsa, va rifatta a mano. *(CC: confermato live sul sito da Max, 17-lug — nessun drift doc↔sito.)* |
| 2026-07-17 (S119) · *corr. 2026-07-20* | **Trigger SELL reale ≈ $66.314** (avg fee-inclusive $63.991 × (1+2%+fee)/(1−fee), fee Kraken 0,8%), **non $65.271 né $64.753**. Il lotto da $25 alla vendita vale **~$26,11 lordi** → netto ~$25,90, profitto **~+$0,71 / +2,8%** | **Tre errori in fila sullo stesso numero:** (1) report S119 usava il prezzo puro ($64.753); (2) S119b corresse a $65.271 leggendo però il **commento** `sell_pipeline.py:316` invece della formula **eseguibile** `grid_bot.py:876`, che è **fee-buffered**; (3) verificato dal vivo 2026-07-20 — BTC ha toccato $65.600 e il bot NON ha venduto = trigger reale più alto, comportamento corretto. Il "2% lordo" inteso dal Board è giusto **come intento**; il codice però lo tratta come **2% netto** e ci somma le fee. Setup lasciato com'è (Max) |
| 2026-07-17 (S119) | **Nodo 5 (margine floor) rinviato a PRIMA della Fase 2b, non durante** | CC ha trovato che il floor **doppia-conta la fee di buy**: `min_price = avg × (1 + min_profit + 2×fee)` mentre l'avg include già 1× fee → floor a avg×1,016 contro un break-even reale di avg×1,008. **Sovra-protettivo di ~0,8%**, non pericoloso, ma blocca vendite già in utile netto. Il margine si sceglie **sopra il break-even vero**: la formula va corretta prima di tararlo. *(Nota: inerte sul test corrente — trigger reale avg×1,036 ≈ $66.314 > floor avg×1,016 ≈ $65.015.)* |
| 2026-07-17 (S119) | **Riavvio del processo di test: sicuro INCONDIZIONATAMENTE** (non prezzo-dipendente) | Tre gate indipendenti: replay sano (trova il trade su `symbol`+`v3`+`cycle`) · reconcile Kraken corretto (interroga Kraken, "Binance" è solo un'etichetta hardcoded) · **capitale esaurito** (`_available_cash` clampato a $0 < $5 min) → nessun DCA a nessun prezzo. Il caveat "$63.293" del corpo del report S119b è **superato per concessione di CC** dopo obiezione del CEO |
| 2026-07-13 (S119) | **Fase 2 cutover Kraken spezzata in 2a + 2b** — 2a (fix bug + ordine-prova reale sorvegliato), 2b (switch reale sui $100 già sul conto) | Kraken non ha testnet: il codice che legge la risposta di un ordine reale non è esercitabile a costo zero, e il bug critico vive proprio lì. La sola certificazione onesta è un ordine reale minimo guardato a mano |
| 2026-07-13 (S119) | **Sito pubblico resta su `binance` durante test interno e collaudo** → venue canonico = binance | Rende invisibile il test da $25 e sblocca il fix cycle-fetch venue-aware (senza, il sito salterebbe sulla riga Kraken mostrando "Fresh start" al pubblico) |
| 2026-07-13 (S119) | **Floor (`profit_target_pct`) lasciato a 0** = "non vendere sotto il break-even dopo le fee" (già sicuro, non "spento"). Trigger test $25 = 2% manuale; Sherpa spento sulle righe Kraken durante i test | Separare "quando vendere" (trigger) da "mai in perdita" (floor); per i test i parametri sono statici a mano. Il 2% copre il round-trip Kraken 1,6% + cuscino slippage |
| 2026-07-13 (S119) | **Fix-fee Sherpa 0,1%→0,80% = prerequisito SOLO per il sistema pieno (fase €600), FUORI scope Fase 2a** | Sherpa oggi calcola i trigger sulle fee Binance; su Kraken produrrebbe sell_pct sotto il floor → stallo. Nei test manuali Sherpa è spento, quindi non serve subito |
| 2026-07-13 (S119) | **Staging collaudo confermato**: $25 BTC (meccanica grid) → $100 sequenziale grid-only BTC→SOL→BONK (segnale pulito, una variabile alla volta) → sistema pieno (Sentinel + Sherpa fee-fixed + NewsKeeper wired) SOLO dopo | "Tutti i brain insieme" è il passo dopo il collaudo, non il collaudo; accenderli sul primo denaro reale perde il segnale pulito e impila integrazione non testata sul momento di rischio massimo |
| 2026-07-13 (S119) | **Cuscino slippage dentro `sell_pct` per ora**; colonna `slippage_buffer_pct` resta NULL | Micro-decisione, rivedibile |
| 2026-07-11 (S117) | **Chiavi API Kraken generate** (Withdraw OFF, WebSocket ON, nonce window 10000ms) + **Fase 0 plumbing test PASS** (18 check, 0 fail; script riusabile `scripts/kraken_cutover_check.py`) | Auth OK, 3 coppie risolvono, ordermin verificati (BTC ~$3,21 / SOL ~$4,68 / BONK ~$4,94 → griglia non rada con $25/trade) |
| 2026-07-11 (S117) | **Cutover K.1 RISEQUENZIATO in Fasi 0-4** (Board) | Le chiavi = test di plumbing, il cutover = operazione coordinata (disclaimer window + stop bot, comms guidelines) che il brief S117 saltava. Fase 0 chiusa; Fase 1 (cablaggio+floor+isolamento venue) = brief dedicato |
| 2026-07-11 (S117) | **Modello grid collaudo = A (market on-trigger), Board-confirmed** | B (ladder maker) rimandato a deployment, da ri-esaminare coi numeri fee veri |
| 2026-07-11 (S117) | **Floor min-profit fee-aware ma Sherpa HANDS-OFF su righe Kraken durante collaudo** (colonna venue, Fase 1) | BOARD_TABLE ha profit_target_pct=0 → Sherpa live azzererebbe il floor; machine-test vuole parametri statici deterministici |
| 2026-07-11 (S117) | ⚠️ **FEE KRAKEN VERIFICATE** (2 fonti indipendenti, post-dubbio CEO): risposta API **grezza** (`TradeVolume`, no parsing) = taker 0,80% / maker 0,40% a tier-0; listino ufficiale kraken.com conferma identico (0,40/0,25 era il listino VECCHIO) | Floor si calibra su 0,80% taker letto live; ri-esame Modello B in Board pre-deployment coi numeri veri (maker = metà del taker). Residuo: conferma visiva UI account (Max, cosmetica) |
| 2026-07-07 (S116) | **Exchange go-live = Kraken (provvisorio, "per ora")** | OKX e Kraken entrambi MiCA-compliant; OKX ha fee più basse ma volumi/liquidità osservati (Max, controllo informale online) nettamente inferiori. A scala $100–$600 la liquidità è ininfluente → fattore decisivo pratico: Kraken già integrato (adapter + testnet) e API live in creazione lì. Rivedibile se lo scale cresce |
| 2026-07-02 (S115) | **Umami declassato a fonte manuale negli audit A3** | API key riservate ai piani a pagamento (401 dal ~giu); pagare $9-20/mese per automatizzare la lettura di ~600 pv/mese non regge il costo/beneficio in fase collaudo |
| 2026-07-02 (S115) | **PostHog parcheggiato come candidato analytics-con-API** | rivalutare a >5.000 pv/mese o quando i funnel diventano decisionali; migrare ora = free-but-complicated |
| 2026-07-02 (S115) | **Metriche-ratio del sito (bounce, funnel %, CTR) fuori dal cruscotto fino a massa critica** | traffico esterno reale ~3 visitatori/mese: le percentuali su questo campione non significano nulla; si misurano solo valori assoluti per canale (Dev.to views/commenti, X impr/reply, Reddit karma/referral) |
| 2026-07-02 (S115) | **Fix title/meta declassato da "leva anti-0-click" a igiene** | /roadmap ha query 100% anonime (non ottimizzabile), il post Kraken-bot ha 18 impr/mese (ranking ok, volume irrilevante) |
| 2026-07-01 | **X-poster `/approve` rotto dal 2 giugno — riparato** (caccia bug, richiesta da Max). Il listener `x_poster_approve.py` (unico che pubblica su X) era spento da ~1 mese senza supervisore: ogni bozza serale del cron moriva in attesa di un `/approve` mai consumato. Fix: LaunchAgent launchd (RunAtLoad+KeepAlive; log in home per TCC sul volume esterno). Corregge la riga S106 qui sotto | Ultimo post reale 2/6 (session 94). Test `/approve` end-to-end ancora da fare (verifica anche salute API X, ferma da 1 mese) |
| 2026-07-01 | **Retention `newskeeper_signals` fissata a 90gg** (era assente dal RETENTION_POLICY) | Stesso principio di trend_scans/trend_decisions_log (S110e): track record per confronto sui cambi di regime. Da rivedere al prossimo cambio di regime osservato |
| 2026-06-30 (S113) | **Verdetto strategico: il grid puro è un ammortizzatore di volatilità, non un motore di rendimento.** Prossimo progetto: categoria diversa, non un altro bot | Passive income come obiettivo dichiarato: **in fallimento** (ricavi €0 su tutti i canali, costi ~€274). Backtest grid-regime (3 regimi BTC, fee Kraken): batte hold solo nel laterale vero e di poco (cattura ~15% del rialzo, ~76% del ribasso). Onesto = differenziante per la narrativa |
| 2026-06-30 (S112b) | **USD per tutto su Kraken** (ribalta "USDC per i tre"). Binance testnet resta USDT | Dati live: BONK/USDC è mercato SINTETICO (badge S, controparte PEDSL-CY, vol API 0,00, "Unknown asset pair" → irraggiungibile dall'API bot); il "113K" era BONK/USD. Universo /USDC = solo 3 coppie liquide (BTC/ETH/SOL) → svuota il TF. /USD profondo (19 liquide ≥$2M, BONK/USD reale ~$120K, verificato via API). USD è fiat → fuori dalle regole MiCA sulle stablecoin; Kraken offre /USD spot ai clienti EU licenziati. Costo: conversione EUR→USD una tantum (= fatica EUR→USDC) |
| 2026-06-30 (S112b) | **Lineup = piano originale confermato** (grid BTC/SOL/BONK, BONK rientra), unica modifica quote USD. Opzione "TF €200 sceglie da 19 coppie" SCARTATA | Era il fallback per l'assenza di BONK; BONK/USD reale → presupposto decaduto. Niente scope creep |
| 2026-06-27 (S110) | **Go-live experiment approvato** | Collaudo €100 sequenziale BTC→SOL→BONK (solo grid, stesso €100 riciclato). Allocazione €600 post-collaudo: BTC €250 fisso + SOL €150 fisso + 2 slot TF €100+€100 (Tier 1-2, con exit thresholds). TF = grid-selector, niente fondo shitcoin separato. Clone TF Tier 3 in paper post-mainnet = CASO 2. Cancelli rampa: a intuito di Max. Bug vs perdita: divergenza da spec = bug (rabbocco), regola eseguita = perdita (resta). Verdetto: -50% scrive capitolo, ciclo completo = verdetto vero. Victory Lap: C→B→A. **[agg. S112b: venue = Kraken USD; lineup BTC $250 / SOL $150 / BONK $100 (grid) / TF $100 (/USD); collaudo ora su Kraken USD]** |
| 2026-06-11 (S102) | **Principio ownership parametri: Board = soldi, Sherpa = strategia** | Max: "Io controllo allocation, $/trade, skim. Sherpa controlla tutto il resto. Se sovrascrivo, cooldown 24h." Tre frasi che risolvono idle, circuit breaker, sell penalty |

> Decisioni **2026-07-01 e precedenti archiviate nella compaction 2026-07-29** (tenute qui solo le portanti ancora in vigore: verdetto strategico grid=ammortizzatore S113, USD+lineup Kraken S112b, allocazione €600 S110, ownership parametri Board/Sherpa S102, marketing S115); **S88→S96 archiviate in S105** (2026-06-13); S81→S87 in S92; S80 e precedenti in S82 — tutte in `audits/BUSINESS_STATE_archive.md`. Storico completo anche in git history.

---

## 5. Domande Aperte per CC

| Tema | Stato | Note |
|---|---|---|
| **[S122] CoinMarketCap free API come sorgente dati Sentinel** | 🆕 Parcheggiata (non gate go-live) | dominance BTC, market cap totale, ampiezza su molte monete. Account attivo (15.000 crediti/mese, 50 req/min, 40+ endpoint). Vicino al **Breadth Tier 3 parcheggiato S109**. Prerequisito: verificare cosa copre il piano free prima di progettare |
| **[S122] `tf.html:1459`** | 🆕 Micro-brief, priorità bassa | formula trigger grid applicata ai bot **TF** (incoerenza pre-esistente, verificata CC S122, fuori scope sherpa-on-kraken). TF non trada in v3 |
| **[S119 NEW] `trades` non ha colonna `venue`** | 🆕 Da valutare — fase sistema-pieno | La separazione Kraken ↔ testnet regge **solo** su `cycle` (`kraken_test` vs `testnet_2`) + il simbolo (`BTC/USD` vs `BTC/USDT`). Funziona oggi. Ma è **accoppiamento implicito**, stessa famiglia dei bug che ci hanno già morso: cycle-fetch (S118 🟠) e superfici sito (S119 🟠). Valutare colonna `venue` esplicita quando Kraken passa a 3 monete. **Non blocca la 2b** |
| **[S119] Timeout/retry del poll `fetch_order`** | Da definire nel fix critico 2a | Comportamento se il fill non è confermato entro il timeout (ordine in volo ma non ancora leggibile) — caso limite più pericoloso del fix critico |
| **[S112 NEW] Guard anti-blackout lato Kraken** (idea Max) | Post-cutover | Soglie di uscita larghe piazzate sull'exchange, più in alto di Sherpa, per proteggere in caso di downtime del bot (crash Mac Mini / connessione giù) — quando Sherpa non può agire perché è giù col bot. Parente del Portfolio Guardian, angolo specifico = resilienza al downtime |
| **[S112 NEW] CMC come 2ª fonte F&G** (emerso nel Passo 0) | Post-cutover, brief separato | Brief parcheggiato `config/parked/PARKED_cmc_fear_greed_second_source.md` (verifica chiave S112: F&G latest+historical disponibili sul nostro piano) |
| **[S107 NEW] Blog post Cluster 1 "AI as CEO"** | PARCHEGGIATO | Il differenziatore massimo non ha ancora un post dedicato. Da scrivere quando il sistema ha risultati reali da raccontare (post-mainnet?) |
| **[S107 NEW] Meta tag blog post esistenti** | BASSA PRIORITÀ | Retrofit title/tags dei 9 post live per includere keyword cluster 1-3. Impatto modesto, rischio reset ranking |
| **[S105 NEW] Monitor "griglia silenziosa"** | DA DECIDERE (Apple Notes vs brief) | Alert quando una griglia non registra trade da X ore. Buco osservabilità S105: un bot fermo non emette ERROR né Telegram, SOL morta 5gg invisibile. Il fix dust impedisce *questo* freeze, non la classe generale. Trigger: prossima sessione o pre-mainnet |
| **[S105 NEW] Caso degradato no-filtri** (is_dust fallback $0,50) | Da valutare | Se `fetch_filters` fallisce al boot, il bot gira col fallback $0,50 < minNotional reale → un residuo in [$0,50, $5) potrebbe ri-congelarsi. Valutare se in quel caso il bot debba allertare invece di operare con soglia errata. Collegato al monitor sopra |
| **[S104 NEW] Automazione spese Haiku — Anthropic Admin API** | PARKED | Endpoint `/v1/organizations/usage_report/messages` + `/v1/organizations/cost_report`. Serve Admin API key (Max genera da console.anthropic.com). Script mensile: chiama API → filtra Haiku → scrive in Supabase `project_expenses`. Insieme a scheduled €90 il giorno 4 di ogni mese |
| **[S102 NEW] Regime stickiness innesto barometro↔Sherpa** | Post-verdetto T+14 (~23 giu) + primo regime non-bear | Fattibilità confermata CC: opzione (a)+(c), ~5-7h, 4 file. Barometro modula la velocità del cap, non la destinazione. NON costruire prima del verdetto |
| **[S99b NEW] Monitoraggio anti-slippage v2 su BONK testnet** | Osservazione | Soglia 1% con slippage strutturale 3-4%: BONK sarà penalizzato quasi sempre. Se si congela (deadlock), alzare soglia o renderla per-coin |
| **[S91 NEW] Integrità dati — `bot_state_snapshots` saldo grezzo** | 🆕 Da verificare | `bot_state_snapshots` fotografa il **saldo grezzo testnet (pre-funded)**, non la posizione €500 → verificare che **nessuna superficie pubblica** lo peschi. Minori: fallback `1,0×` non cappato in Sentinel; dead-band scritture Sherpa ✅ DONE (S102a write guard `a867179`) |
| **[S90 NEW] Option C — slippage buffer su percentage sell path** | TODO pre-mainnet, brief separato | Brief separato pre-mainnet. Estendere il pattern `SLIPPAGE_BUFFER_PCT=0.03` (già attivo su SWEEP/LAST_SHOT path da brief 78b) anche al path `_execute_percentage_sell` per chiudere completamente la finestra di rischio post-fix A+B |
| **[S90 NEW] Calibrazione parametri spike guard** (threshold 4% / confirm 50% / pause 5s) | Osservazione 7-14gg, poi decidere | Oggi i 3 parametri sono default argument della funzione `fetch_price_with_spike_guard`. Post osservazione: valutare se servono tunable per-coin via `bot_config` (BTC vs SOL vs BONK volatilità diverse). Voto CC: tenerli fissi finché dati live non suggeriscono altrimenti |
| **[S81 NEW] Cross-post automation Dev.to + Indie Hackers** | Decisione rimandata post-weekend | Quando un post va live su `web_astro/src/content/blog/`, script che pubblica su Dev.to via API (canonical URL, tags, serie) + prepara testo adattato per IH. ~2-3h stimato |
| **Counterfactual tracker: aggiungere regime Sentinel** | 🆕 Nice-to-have post-osservazione | `counterfactual.py` non logga regime. Utile per correlare skip ↔ regime. ~30-45min. CEO decide se vale dopo 1-2 settimane di dati |
| **Verifica identità accounting** (residuo Strada 2) | Post-go-live €100 | ~30 min check empirico Realized + Unrealized = Equity P&L. FIFO cancellato come canonical |
| **Buy trigger anchor (A/B/C)** | Parcheggiata | A=last_buy, B=avg, C=hybrid. Decisione strategica |

---

## 6. Vincoli/Deadline Non-Tecnici

| Vincolo | Scadenza | Note |
|---|---|---|
| **NewsKeeper v2 Barometro verdetto** | Nessuna data fissa (era ~23 giu) | T+14 raggiunto, esito: PASS qualità / INCONCLUSIVE prezzo (N=2 flip insufficiente). Esteso fino a regime change sostenuto (neutral/bullish >24h). Non blocca go-live grid. Dettagli in diary S108 |
| **Apple Notes pulizia: cancellare 8 note obsolete (Max)** | A discrezione Max | 4 note attive da mantenere, 8 obsolete da cancellare manualmente |
| **Volume 4** | Nessuna deadline | In accumulo da S83, arco narrativo NewsKeeper build → go-live |

**Multi-macchina:** MBP (sviluppo) ↔ Mac Mini (runtime). PID/runtime dettagliati in PROJECT_STATE §1+§7.

**Piattaforma pubblicazione:** Payhip (free plan, 5% fee). Nessuna urgenza di cambiare.

---

## 7. Cosa NON Sta Succedendo e Perché

| Cosa | Perché |
|---|---|
| **Nessun post pubblico sul primo ordine reale** | Non è prudenza: la milestone si annuncia al **collaudo**, con il sito allineato. Oggi diventerà la **prova di rigore** dentro quel post ("prima dei $100 ne abbiamo messi 25, uno solo, guardato a mano"), non una notizia autonoma |
| **Ottimizzazione on-site (SEO, funnel, CTR)** | Il sito non ha un pubblico proprio (~3 visitatori esterni/mese, verifica audit A3 2026-07-02): la trazione, piccola, vive dentro Dev.to/X/Reddit. Nessuna ottimizzazione on-site è prioritaria finché non cambia questo. Il collo di bottiglia è la **distribuzione**, non lo snippet |
| **Revenue automation completa (/income)** | La pagina /income esiste come scaffold privato, ma l'automazione fonti (Payhip, BMC, Umami API) è rinviata al primo euro: a €0 darebbero "0" → over-engineering. Solo Umami ha già un connettore. Haiku costs: soluzione Admin API trovata, parcheggiata |
| **Pagina /news pubblica** | Pianificata (nav principale, brief S106a) ma bloccata dal verdetto barometro v2 (~23 giugno). Il brief documenta struttura e due scenari (validato/bocciato). Non costruire prima. Fonte moat: analisi tbot S98 (lui mostra gli stessi 3 feed RSS ma senza label AI → quando esponiamo, lo battiamo con sentiment/severità) |
| **Easter egg /office interattivo** | L'idea di una pagina dove clicchi ogni bot ed entri nella sua "stanza" con dati dettagliati è parcheggiata. Se si fa, è un progetto a sé — non una pagina duplicata della homepage (la scena ufficio va nell'hero, /office standalone eliminata in S106a) |
| **Tabella performance per regime su dashboard** | Parked fino a profondità dati sufficiente (testnet_2 ha ~2 giorni). Fonte: analisi tbot S98 |
| **Sherpa controlla 7/7 parametri Grid** | LIVE su testnet. I 3 strategici (buy/sell/idle) scalano con volatility multiplier continuo. I 4 protettivi (stop_buy_dd/unlock, dead_zone, min_profit) usano lookup discreto per (regime × volatility tier) con debounce 24h. Board-only restano SOLO: allocation, $/trade, skim |
| **Paper trade re-import** | Backup esiste (`/Volumes/Archivio/bagholderai/audits/2026-05-08_pre-reset-s67/`, 51.943 righe JSONL) ma non serve re-importarlo nel DB. Disponibile per narrativa/diary quando serve |
| **Audit Area 2 manuale on-demand** | Non più necessario: Area 2 è automatizzata (Cowork mensile, S104) come Area 1 e Area 3. Tutte e 3 le aree girano schedulate + notifica Gmail/Apps Script. Vedi §4 (S104) + PROJECT_STATE §9 |
| **NewsKeeper v1** | ✅ SPENTO (S110e, 27 giugno). Righe v1 archiviate e cancellate. Runbook corretto |
| **TF-Scout (Tier 3 shitcoins)** | Post-mainnet. TF clone in paper/testnet (CASO 2). trend_scans retention estesa a 90gg (S110e) |
| **Grok/X scanner module** | Post-mainnet. Richiede API X premium (~$200/mese), giustificabile solo con MRR positivo |
| **Nessuna nuova fonte dati per NewsKeeper** | API news gratuite morte (CryptoPanic, CoinDesk). RSS + Haiku resta il piano. Niente budget per news API paid pre-mainnet |
| **Nessun cross-post automatico** | Dev.to e IH manuali. Automazione in valutazione post-baseline |
| **HN come canale** | Shadowban Cart0ne. Nuovo account non urgente — altri canali prioritari |
| **Futures/hedging** | Parcheggiato S90+. Capitale >€100, stack separato, KYC aggiuntivo. Post-mainnet |
| **Partnership / sponsorship** | Pre-traction |
| **Breadth Tier 3 come segnale Sentinel** | PARCHEGGIATO (S109). Analisi 6 mesi non supporta l'ipotesi (contrarian debole, ridondante con F&G). Ri-test dopo regime risk-on sostenuto. Script deterministico riutilizzabile (`scripts/breadth_analysis_s109.py`) |

---

*Prossimo aggiornamento: post verdetto barometro NewsKeeper v2 (~23 giugno) o pre-go-live mainnet, whichever comes first.*
