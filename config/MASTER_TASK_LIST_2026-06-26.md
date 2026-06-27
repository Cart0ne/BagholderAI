# BagHolderAI — Master Task List

**Data:** 18 giugno 2026
**Regola:** da oggi niente nuovi task. Solo bug fix. Si finisce quello che c'è.

---

## FASE 0 — IN OSSERVAZIONE (nessuna azione, solo aspettare)

Queste cose girano da sole. Non toccare, non aggiungere scope.

| # | Cosa | Scadenza / trigger | Chi |
|---|---|---|---|
| 0.1 | Barometro v2 shadow validation | ✅ **CHIUSO (S108)** — PASS qualità, INCONCLUSIVE prezzo | Automatico |
| 0.2 | Sherpa observation (7 parametri + debounce) | ✅ **CHIUSO (S109)** — PASS per go-live dopo 15gg | Automatico |

**Nota:** entrambi i verdetti dati (barometro S108, Sherpa S109). **FASE 0 chiusa.**

---

## FASE 1 — PRE-MAINNET OBBLIGATORI (in ordine di esecuzione)

Senza questi non si va live. Sequenza logica, non parallelo.

| # | Cosa | Dipende da | Chi | Stima |
|---|---|---|---|---|
| 1.1 | **Verdetto barometro** | 0.1 | CEO + Max | ✅ **CHIUSO (S108)** |
| 1.2 | **Verdetto Sherpa** | 0.2 | CEO + Max | ✅ **CHIUSO (S109)** — PASS, flicker cosmetico (fix A/B/C → post regime change) |
| 1.2b | **Verifica breadth tier → Sentinel** (read-only) | dati S109 | CEO + Max | ✅ **CHIUSO (S109)** — PARCHEGGIATO, dati insufficienti per risk-on (report `..._tier-breadth-regime-signal.md`) |
| 1.3 | **Sessione go-live experiment** — formalizzare rampa/rabbocco/verdetto/Victory Lap (da `PARKED_golive_experiment_design.md`) | 1.1 + 1.2 ✅ | CEO + Max | **PROSSIMO** — unico task CEO+Board rimasto |
| 1.4 | **DUST write-off** — ✅ **EVENTO+STUB done S109** (write-off ora evento persistito `DUST_WRITEOFF` + `convert_dust_to_bnb` guarded mainnet-only); reconcile wallet↔DB → go-live | Pre-mainnet | CC | ✅ S109 (parziale) |
| 1.5 | **sell_pct + slippage_buffer parametrico per coin** — ✅ **INFRA done S109** (colonna `bot_config.slippage_buffer_pct` + hot-reload + default 0.03 = identico a oggi); taratura per-coin → mainnet (dati reali) | Pre-mainnet | CC | ✅ S109 |
| 1.6 | **Integration test config reader chain** — ✅ **DONE S109** (8 test end-to-end, gap S76 chiuso) | Pre-mainnet (gap da S76) | CC | ✅ S109 |
| 1.7 | **Mobile smoke test** | — | Max | ❌ **ELIMINATO (S109)** — Max lo fa già quotidianamente |
| 1.8 | **Board approval call** | dopo 1.3 + annuncio Binance MiCA | Max | **PENDING** |

---

## FASE 2 — BLOG PIPELINE (parallela a Fase 1, non bloccante)

Questi possono avanzare tra una sessione tecnica e l'altra.

| # | Cosa | Stato | Chi | Note |
|---|---|---|---|---|
| 2.1 | **Cross-post "non-coder-5-brains" → Substack** | Pronto, solo da fare | Max | 15min, copia+adatta |
| 2.2 | **Pubblicare "vibe-coding-a-real-business.md"** | ✅ **PUBBLICATO 18-giu** (commit `acbed3b`) | CC | two-voice, /blog/vibe-coding-a-real-business |
| 2.3 | **Pubblicare "why-most-ai-trading-bots-fail.md"** ⭐ **priorità** | SEO già forte (head keyword "ai trading bot" + FAQ + intro GEO); serve SOLO intro umana | CEO rivede → Max intro → CC pubblica | Applicare standard two-voice |
| 2.4 | **"ai-crypto-trading-bot-real-testnet-results.md"** | PARKED — placeholder data | Nessuno finché non ci sono dati reali | Sblocca dopo go-live |
| 2.5 | **"Thirty-Two Hours" Dev.to cross-post** | Draft su Dev.to, primo del nuovo standard | Max intro + lezione tecnica in cima | Da PARKED_blog_voice_strategy |

**Ordine consigliato:** 2.1 (5min) → **2.3** (più pronto: serve solo la tua intro) → 2.5 (2.2 ✅ pubblicato 18-giu; 2.4 aspetta dati).

---

## FASE 3 — SUBITO DOPO GO-LIVE (le prime settimane live)

| # | Cosa | Note |
|---|---|---|
| 3.1 | **Monitor "griglia silenziosa"** — alert quando una griglia non trada da X ore | Brief da scrivere. Nasce da buco S105. Dettaglio critico: soglia X |
| 3.2 | **Verifica commenti Haiku** | Da todo Board |
| 3.3 | **Verifica acquisto Ethereum + dashboard** | ✅ 18-giu: restart Mac Mini → ETH su `testnet_2` (tf_grid), causa-radice (cycle stale) risolta. Resta conferma visiva dashboard pubblica |
| 3.4 | **Fix copy /library** — frase "Read Volume II if you only care about the brain" datata | ✅ RISOLTO 18-giu (commit `1e22c87`), copy future-proof, in deploy |
| 3.5 | **BNB-discount fee future-proof** — colonna fee_native_amount | Pre scale-up |

---

## FASE 4 — POST GO-LIVE / QUANDO SERVE (backlog ordinato)

Non toccare fino a che Fase 1-3 non sono chiuse.

| # | Cosa | Trigger |
|---|---|---|
| 4.1 | Sentinel: espandere oltre F&G Index (Phase B) | Dopo stabilità mainnet |
| 4.2 | TF distance filter + regime-awareness (12% fisso paralizza TF) | Post Brain Analysis |
| 4.3 | Calibrare BASE_TABLE Sherpa se troppo distante | Post-analysis |
| 4.4 | Pagina /news pubblica con label AI (NewsKeeper maturo) | Post verdetto barometro |
| 4.5 | Tabella "Performance per regime" in dashboard | Serve profondità dati mainnet |
| 4.6 | History paper mode sito/blog | Quando ha senso |
| 4.7 | Guida all'uso | Quando ha senso |
| 4.8 | Patience timer per sell ladder | Serve dati reali testnet cycle 2 |
| 4.9 | Script replay counterfactual Sherpa | Da brief 80a |
| 4.10 | Decidere TRUNCATE tabelle Sentinel/Sherpa/TF paper-era | Quando si ricollega brain |
| 4.11 | Investigare recalibrate-on-restart (buy_pct cambia al boot) | CEO |
| 4.12 | **Last-shot floor per-coin (BONK)** — `MIN_LAST_SHOT_USD=$5` fisso vs `min_notional` reale Binance: coincide per BTC/SOL/ETH ($5), diverge su **BONK ($1)** → oggi BONK lascia $1–5 di cassa non spendibili che Binance accetterebbe. Decidere: convertire il trigger a `max($5, min_notional)` per-coin **oppure** tenere $5 come floor anti-micro-buy (book BONK sottile, slippage 2-3%). Bot oggi è corretto, è una scelta di design. | CEO decision · intervento bot |
| 4.13 | **TF dashboard — card per-coin mode-aware (Path 2)** — oggi tutte le coin sulla pagina TF sono `tf_grid` (TF le sceglie, grid le gestisce) → la card di grid basta (Path 1, fatto S110). Quando/se TF traderà una coin **direttamente** (`managed_by='tf'` > 0) serve una card TF dedicata: trailing stop / SL / TP / status (SCANNING · IN POSITION · TRAILING), **senza** buy/sell %, stop-buy, sell-ladder. | TF trada diretto (`managed_by='tf'` > 0) |
| 4.14 | **Compounding policy (grid)** — col lotto fisso + skim, il profitto aumenta la *capacità d'acquisto* solo a scatti interi: ~$36 lordi/coin (o ~$107 distribuiti su 3 coin) per aggiungere **1 lotto** → compounding grumoso e conservativo. Reinvestimento **per-coin** (silos indipendenti, verificato S110: nessun pooling cross-coin). Decidere: **(A)** lotto fisso oggi, **(B)** lotto cresce col profitto (+rischio/trade), **(C)** allocazione cresce col profitto (+lotti, +esposizione totale). Indicatore "profitto-cassa inattivo · al prossimo lotto" aggiunto al dashboard in S110 (110a) per rendere visibile il fenomeno. | CEO decision · strategia |

---

## CONGELATO (non toccare, non pianificare)

Roba che esiste ma NON entra in pipeline fino a nuova decisione Board.

| Cosa | Perché congelato |
|---|---|
| X automated Haiku posts | Paused, riprendere in sessione dedicata (X_STRATEGY_REVISION.md) |
| X Scanner automazione weekly cron | Manuale on-demand per ora |
| IG/Canva | Post risultati cambio tono Haiku X (2-3 sett) |
| Anthropic Admin API (costi Haiku) | Parked |
| Security audit (headers, CSP, RLS) | Parked |
| Breadth Tier 3 come segnale Sentinel | PARCHEGGIATO (S109). Analisi 6 mesi negativa in regime fear (contrarian debole, ridondante con F&G). Re-test dopo risk-on sostenuto. Script `scripts/breadth_analysis_s109.py` riutilizzabile |
| Newsletter/mailing list blog | Post-lancio V3, valutare |
| Reddit r/ClaudeAI post | Serve 50 karma, Max karma building |
| HN | Account shadowbannato, serve nuovo account |
| Canale pubblico Telegram espansione | Da decidere |
| Post Show HN / X su Sentinel+Sherpa | Post go-live |
| NewsKeeper modulo 2 Grok/X scanner | Post-mainnet, API X premium |
| Anthropic Financial Services Agents repo | Reference, non task |
| ImMike kill-switch pattern | Reference per Sentinel mainnet |
| Brain Analysis round 2 | Serve NewsKeeper maturo |

---

## BUG APERTI (questi entrano sempre, unica eccezione alla regola)

| Bug | Priorità | Chi | Stato |
|---|---|---|---|
| Fix exchange_order_id null su sell OP/USDT | Cosmetico | CC | ✅ S109 (fallback info.orderId + warning) |
| DeprecationWarning datetime.utcnow() | Low | CC | ✅ S109 (helper naive-UTC, 409→0 warning) |
| PortfolioManager istanziato ma mai usato | Low | CC | ✅ S109 (rimosso + classe orfana) |
| Aggiornare validation_and_control_system.md §2 | Low | CC | ✅ S109 |

---

## DIARIO

- Volume 4 "From Eyes to Live" (S83+): in corso, arco narrativo
  NewsKeeper → go-live → primi risultati. Nessun task — si scrive
  sessione per sessione.
- **S109 inserita in Supabase (COMPLETE). Docx prodotto.** (update CEO)
- S106 risulta BUILDING in Supabase. S107 menzionata in memoria
  ma non presente in DB — da verificare con Max.

---

*Compilata: CEO, 18 giugno 2026. Fonti: Apple Notes todo, PARKED briefs
(PK), BUSINESS_STATE, memoria CEO. Regola: zero nuovi task, solo bug fix,
fino a chiusura Fase 1.*

*Aggiornato: CC, 18 giugno 2026 — 3.3 (restart Mac Mini → ETH su `testnet_2`)
e 3.4 (/library) risolti; aggiunto 1.2b (verifica breadth tier → Sentinel,
read-only, sessione del ~23). 1.2b è misura/analisi per decidere, non nuovo
scope di build — coerente con la regola "solo bug fix".*

*Aggiornato: CC, 25 giugno 2026 (S109) — chiusi tutti i task CC-only eseguibili
senza dati mainnet: 1.6 (config-chain test), 1.5 (slippage infra), 1.4 parziale
(dust evento persistito + stub convert-to-BNB; reconcile→go-live) + i 4 bug
aperti (exchange_order_id, datetime.utcnow, PortfolioManager, validation §2).
T8/monitor griglia silenziosa parcheggiato (Max decide la soglia). I fix che
toccano `bot/` sono committati ma diventano LIVE solo al prossimo restart.
250/250 test verdi.*

*Aggiornato: CC, 26 giugno 2026 (S110) — aggiunto 4.12 (last-shot floor per-coin),
verifica emersa rivedendo grid.html: il `min_notional` reale Binance è $5 per
BTC/SOL/ETH ma $1 per BONK, mentre il bot usa il floor fisso $5 → su BONK restano
$1-5 di cassa non spendibili. Verifica/decisione CEO, non bug. Max (S110): "per ora
non modifichiamo", solo tracciare. Aggiunto anche 4.13 (TF dashboard card mode-aware,
Path 2): la pagina TF viene uniformata a grid in S110 (Path 1, valido finché tutte le
coin sono `tf_grid`); la card TF dedicata si fa solo quando TF traderà diretto. Aggiunto
4.14 (compounding policy grid): col lotto fisso il profitto compone a scatti interi e il
reinvestimento è per-coin (silos, no pooling — verificato nel codice); decisione
strategia A/B/C → CEO. In 110a si aggiunge solo l'indicatore di visibilità a dashboard,
non si cambia il meccanismo.*
