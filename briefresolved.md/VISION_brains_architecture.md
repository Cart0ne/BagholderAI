# VISION — Architettura multi-cervello BagHolderAI

**Date:** 2026-04-16 (brainstorming appunti, da discutere col CEO)
**Stato:** NON un piano, NON uno spec. Sono appunti per una sessione di allineamento sulla visione di medio periodo (3-6 mesi).
**Prerequisiti attuali (16 apr):** TF deployato su rotation alt (36a/b/c/d). 36e/f/g/h in config come draft.

---

## Il principio di fondo

Un singolo "AI CEO" monolitico che decide tutto (allocazioni + parametri + reazioni a news + safety) è fragile: troppa logica in un unico punto, troppi trade-off incompatibili da comporre in un solo prompt/policy.

La direzione che emerge dal brainstorming: **specializzazione**. Ogni cervello ha uno scope ristretto e un output limitato. La composizione dei loro output produce il comportamento complessivo del sistema.

## I 4 cervelli (stato + ruolo proposto)

### 1. GRID Bot — **esecutore meccanico** (oggi attivo)

- **Scope**: un singolo symbol, parametri fissi (buy_pct, sell_pct, capital_per_trade, idle_reentry)
- **Decide**: se/quando comprare o vendere in base al movimento di prezzo locale vs ultimo buy
- **Non decide**: quale coin tradare, quanto budget riceve, se il contesto di mercato è favorevole
- **Rule set**: Strategy A (never sell at loss), grid percentuale, skim 30% a reserve_ledger
- **Stato**: stabile, in produzione da mesi su BTC/SOL/BONK e (via TF) su AXL/MBOX

### 2. TF Trend Follower — **allocatore di alt** (oggi attivo, in refinement)

- **Scope**: universo "rotation" (oggi top-50 Binance meno manual whitelist, futuro: top-50 meno anchor coins)
- **Decide**: quali N coin (tf_max_coins) tenere, con quale budget (tf_budget), buy_pct/sell_pct iniziali (ATR adaptive in 36e), quando ruotare
- **Non decide**: parametri delle anchor coin, reazioni a eventi esogeni (news, hack, regolamenti)
- **Stato**: live su 2 coin, stabilizzazione tramite 36e/36g/36h in arrivo

### 3. MiniTF — **tuner dei parametri anchor** (concetto, futuro)

- **Scope**: le 2-3 "anchor coin" (scelte da top-10 CMC per volume, escluso BTC/ETH che il CEO detiene IRL)
- **Decide**: modulare dinamicamente `buy_pct` / `sell_pct` / `capital_per_trade` / `idle_reentry_hours` in base ai signal TF (BULLISH/BEARISH/SIDEWAYS + strength)
- **Non decide**: quale coin è anchor (regola statica: top-10 CMC stickiness), né swap (mai, salvo eccezione rarissima con alert + conferma CEO)
- **Filosofia**: il GRID sulle anchor continua a comportarsi come un GRID classico, ma "respira" col mercato. Esempio: in trend leggermente bullish (+0.3%/die senza dip), il MiniTF potrebbe abbassare `buy_pct` da 0.5% a 0.3% per catturare più entries, e alzare `sell_pct` per catturare più movimento
- **Perché separato dal TF**: il TF è ottimizzato per ruotare, il MiniTF per **preservare** e modulare. Logiche opposte, policy diverse
- **Stato**: brief non ancora scritto; dipende da TF maturo post 36e/36g (riuso 70% della codebase TF esistente)

### 4. AI Sentinel — **meta-brain di contesto** (roadmap Phase 3, futuro)

- **Scope**: mondo esterno — news, eventi macro, hacks, regolamenti, sentiment social
- **Decide**: risk score + opportunity score globali; in casi estremi, può proporre **override** (pause allocation, forza DEALLOCATE di emergenza, alza soglie di sicurezza)
- **Non decide**: trade individuali, parametri granulari, coin selection (quello è del TF)
- **Output tipico**: "Regolamento EU annunciato oggi → risk score 75/100, suggerisco pause nuove allocate TF per 24h"
- **Modello**: Claude Haiku (già previsto in roadmap per cost efficiency)
- **Feed**: CryptoPanic, RSS selezionati, potenzialmente Twitter/X scraping
- **Autorità**: limitata — può **proporre** e **alertare**, ma override reali richiedono conferma CEO via Telegram (salvo eccezioni hardcoded tipo "exchange compromise → emergency stop")

### 4b. Layer macro-tecnico — **scudo anti-bear deterministico** (da affiancare al Sentinel)

Il Sentinel come progettato sopra legge **news** — cioè eventi discreti, testuali, raccontabili. Ma buona parte dei grandi bear market NON viene annunciata da una news: parte silenziosamente sui grafici prima che qualcuno scriva un titolo. Un Sentinel solo-news è fondamentale ma copre ~60% del rischio sistemico. Per arrivare al 90% serve un **secondo livello** basato su segnali macro-tecnici deterministici.

Questo secondo livello è **codice puro, zero LLM**: formule su dati di prezzo. Il suo output è un `macro_risk_score` che il Sentinel LLM combina con il `news_risk_score` per decidere.

**Segnali macro-tecnici proposti:**

- **BTC weekly trend (EMA 50/200)**: death cross settimanale = segnale di bear primario. Golden cross = fine bear. Segnale lento ma quasi infallibile per macrocicli.
- **Volume / total market cap divergence**: se il market cap totale sale ma i volumi cumulati scendono → movimento instabile, tipico della coda di un bull prima dell'inversione.
- **BTC dominance**: se sale rapidamente (+3-5 punti in una settimana), i capitali stanno fuggendo dalle altcoin verso BTC. Per un TF che tradea alt, è un early warning critico — le alt perderanno valore anche se BTC resta stabile.
- **Fear & Greed index aggregato**: entrate prolungate in "Extreme Fear" (<20) o "Extreme Greed" (>80) come contrarian signal secondario.

Ogni segnale produce un contributo numerico al macro risk score. Il Sentinel LLM riceve poi in input **entrambi**:

```
news_risk_score       = 30/100   (tutto tranquillo sul fronte news)
macro_risk_score      = 80/100   (BTC weekly death cross + dominance +4 points)
combined_risk         = LLM decide come pesarli (spesso: il più alto vince)
```

Vantaggio architetturale: il layer macro-tecnico è **testabile offline** (backtest su dati storici), non dipende da feed esterni flaky, e continua a funzionare se l'LLM fosse down. Il Sentinel LLM aggiunge il giudizio contestuale ("questa news EU è veramente grave o boilerplate?"); il macro layer aggiunge la visione grafica oggettiva.

**Perché contano insieme e non separati**: un bear crypto classico ha un preannuncio grafico (macro) + un catalyst testuale (news). Catturarne uno solo lascia buchi. Il Sentinel completo è l'AND delle due viste.

**Files/moduli ipotetici** (per il brief futuro):
- `bot/sentinel/macro_signals.py` — calcolo score deterministico (pandas su OHLCV settimanale BTC + CMC global)
- `bot/sentinel/news_reader.py` — ingest CryptoPanic + classificazione LLM
- `bot/sentinel/combined_decision.py` — il Sentinel LLM che unisce i due score e produce azione

### 4c. Brainstorming session 45 (2026-04-23) — raffinamento del ruolo Sentinel

Durante la sessione 45 (deploy 45a/b/c/d + analisi delle 11 perdite v3), è emersa una visione più stratificata del Sentinel rispetto al draft iniziale di aprile 16. Appunti da integrare al brief esecutivo quando sarà il momento:

**Livelli operativi proposti** (dal più leggero al più pesante):

1. **Livello A — Sanity check pre-ALLOCATE (sincrono, per-coin)**
   Quando il TF sta per allocare una coin che ha già passato tutti i filtri deterministici, Sentinel dà un ultimo "ok/pausa/veto" con giudizio olistico. Costo basso (1 call per ALLOCATE effettivo, ~3-5/giorno). Cattura segnali non catturabili da formule: "team ha venduto 10% supply 48h fa", "rug pull pattern nel chart", "delisting annunciato".
   Prompt-template tipo:
   ```
   Sto per allocare $X su KAT/USDT su grid paper-trading.
   4h chart + last 24h news + order book snapshot.
   Red flags? JSON: {verdict: GO|PAUSE|VETO, confidence: 0-100, reasons: [...]}
   ```

2. **Livello B — Post-mortem asincrono**
   Ogni sera, Sentinel analizza le allocazioni perdenti del giorno. Non decide, **propone** al CEO filtri nuovi da aggiungere. "Oggi MOVR e MET hanno perso. Pattern comune: entry +20% sopra EMA20. Suggerisco nuovo filtro deterministico." È il ciclo di apprendimento automatizzato: quello che Max/CEO/intern hanno fatto a mano nelle sessioni 45a-e, Sentinel lo fa ogni notte.

3. **Livello C — Monitoring operativo**
   Ogni N ore, Sentinel scansiona lo stato del sistema e segnala anomalie via Telegram: "bot X non vende da 48h sopra greed decay target", "due bot hanno stesso signal_strength ma PnL divergente — perché?", "unrealized è sceso del Y% dall'ALLOCATE, flusso anomalo". Non interviene, illumina.

4. **Livello D — Context summarizer per il CEO**
   Quando il CEO apre una sessione Projects, Sentinel gli passa un brief automatico: "Ultime 24h: 2 SL, 1 SWAP, compound −$X. Decisioni pendenti: ...". Evita che il CEO ricostruisca lo stato da zero.

**Risk score graduale (non binario):**

Il ruolo del Sentinel non è "veto / go" ma **modulazione dell'aggressività**:

```
risk_score 0-30   → alloca normale (nessun intervento Sentinel)
risk_score 30-60  → alloca ma dimezza capital_allocation (cautela)
risk_score 60-80  → alloca solo su Tier 1 blue chip (skip T2/T3)
risk_score 80-100 → non allocare niente (emergency pause)
```

Questo permette al TF di **adattarsi gradualmente** invece di spegnersi in bianco/nero. Esempio: news di regolamentazione UE moderata → risk 55 → TF continua ma con posizioni più piccole. Exchange hack in corso → risk 90 → TF si ferma fino a conferma CEO.

**Scelta del modello LLM — non un blocco unico:**

- **Livello A (per-coin pre-ALLOCATE)**: Sonnet 4.6 o Opus 4.7 (qualità elevata, pochi call/giorno)
- **Livello B (post-mortem)**: Opus 4.7 (ragionamento profondo, 1 call/giorno)
- **Livello C (monitoring)**: Haiku 4.5 (economico, tanti check/giorno)
- **Livello D (context summary)**: Sonnet 4.6 (bilanciato)
- **Macro signals (scudo deterministico 4b)**: nessun LLM, solo codice

Non è necessario scegliere uno modello "Sentinel". Diversi livelli, diversi modelli, diversi costi.

**Integrazione col TF — il pattern di decisione:**

```
Scanner → 50 coin classificate (BULLISH/BEARISH/SIDEWAYS + strength)
   ↓
Filtri deterministici TF (tier volume, strength, distance EMA, SL cooldown)
   → riducono a ~3-5 candidati per tier
   ↓
[Sentinel Livello A] guarda i 3-5 candidati con occhio olistico
   → emette risk_score_coin per ciascuno
   ↓
[Macro layer 4b] calcola risk_score_market (deterministico, no LLM)
   ↓
risk_score_final = combine(macro, per-coin) — regola di combinazione da definire
   ↓
Allocator applica regole graduali (normale / dimezzato / T1-only / pause)
   → decisione finale ALLOCATE/SWAP/SKIP
```

Sentinel vede **solo** coin che hanno già superato tutto il resto. Costo basso, valore alto. Non sostituisce i filtri deterministici, li completa.

**Filtri deterministici candidati da esplorare prima di Sentinel** (raccolti durante brainstorming session 45, non ancora validati storicamente tutti):

| Categoria | Segnale | Note |
|-----------|---------|------|
| Timing/Momentum | RSI slope (non livello) | Cattura reversal veri, più robusto di "RSI > 70" plain |
| Timing/Momentum | Stochastic RSI | Oscilla più rapido, classico top-spotter |
| Timing/Momentum | Bollinger Band upper touch | "Non comprare al BB upper" |
| Timing/Momentum | **Distance from EMA20** | ✅ VALIDATO (45e) — il più potente, 92.4% delle perdite v3 |
| Volatilità | ATR spike | Ultime candele ATR >> media = whipsaw imminente |
| Volatilità | Volume spike | Entry a picco volume = entry a picco prezzo |
| Volatilità | Wick analysis | Upper shadow >> body = distribution |
| Contesto | BTC correlation | Se BTC BEARISH, non allocare alt (validato 0/11 in bull phase — re-validare in bear) |
| Contesto | Total market BEARISH ratio | Se maggioranza top 50 è BEARISH, pausa |
| Contesto | Recent DEALLOCATE stesso cluster | Settore in crollo → skip coin stesso settore |
| Microstruttura | Order book depth asymmetry | Sell-wall >> buy-wall = coin "pesante" |
| Microstruttura | Realized volatility recente | std/mean elevato = casinò |

**Filosofia di base che unisce questi segnali**: il TF attuale è **rank-based** ("la più forte del pool"). Il livello Sentinel + distance filter aggiungono il punto di vista **absolute-based** ("anche se è la più forte, è assolutamente sbagliata comprarla ora").

**Roadmap suggerita per non fare tutto insieme:**

1. ✅ **Deploy 45e** (distance filter — validato 92%)
2. **Osservazione 1-2 settimane** — quanto salva davvero in prospettiva vs ipotesi storica?
3. Se distance filter funziona → **esplorare uno-due filtri deterministici extra** (BTC correlation in bear phase, volume spike) — sempre con validazione storica prima del deploy
4. **Sentinel Livello B (post-mortem)** — il più economico, il più sicuro (non interviene, solo propone). Da fare prima degli altri livelli.
5. **Sentinel Livello A (per-coin pre-ALLOCATE)** — solo dopo che il TF è stabile con tutti i filtri deterministici maturi
6. **Livelli C e D** — ultimi, opzionali

**Costo-bozza in API LLM:**

- Livello A: 3-5 call/giorno × $0.01 Sonnet = **$0.03-0.05/giorno**
- Livello B: 1 call/giorno × $0.05 Opus = **$0.05/giorno**
- Livello C: 24 call/giorno × $0.001 Haiku = **$0.024/giorno**
- Livello D: 2-3 call/giorno × $0.01 Sonnet = **$0.02-0.03/giorno**

Totale stimato Sentinel completo: **~$0.13/giorno** (≈ $4/mese). Rispetto al capitale gestito, trascurabile.

**Approccio data-driven (lezione session 45):**

La sessione 45 ha mostrato il valore di **validare storicamente** ogni idea prima di codificarla. Il brief originale 45e (di Sonnet) proponeva 2 gate (EMA + RSI). La validazione storica ha mostrato che Gate 1 era inutile e Distance era migliore di RSI. Questo metodo — misurare prima, codificare dopo — va replicato per ogni segnale candidato di Sentinel.

**Regola operativa:** nessun nuovo filtro/livello Sentinel senza backtest su dati v3 prima del deploy.

## La gerarchia proposta

```
          ┌────────────────────────┐
          │   AI Sentinel          │  "Watch the world"
          │   (Phase 3)            │  Risk/opp score globale
          └────────────┬───────────┘
                       │ può proporre override
        ┌──────────────┼──────────────┐
        ▼                             ▼
┌─────────────────┐           ┌─────────────────┐
│   TF (rotation) │           │ MiniTF (tuner)  │
│   scope: alts   │           │ scope: anchor   │
│   ALLOCATE/SWAP │           │ UPDATE params   │
└────────┬────────┘           └────────┬────────┘
         │ scrive bot_config           │ scrive bot_config
         ▼                             ▼
┌─────────────────────────────────────────────────┐
│             GRID Bots (eseguono)                 │
│  BTC  SOL  BONK  (manual) │ AXL  MBOX  (TF-mgd)  │
└──────────────────────────────────────────────────┘
                       ▲
                       │
              ┌────────────────┐
              │   CEO (Max)    │  Override finale, sempre
              └────────────────┘
```

## I dubbi aperti (per la sessione col CEO)

### A. Quante "anchor coin"?
- **2**: conservativo, rischio concentrato, facile da monitorare
- **3**: diversificazione migliore, più capitale parcheggiato
- **0 (full TF)**: massima autonomia ma zero safety net
- **Proposta**: 2, restrette a top-10 CMC volume escluso BTC/ETH. Se TF dimostra >6 mesi di outperformance netta, valutare drop a 1 o 0.

### B. Universo anchor: CMC top-10 o Binance top-10?
- **CMC**: market-cap globale, più "vera" misura di forza di mercato
- **Binance**: disponibilità immediata per trading testnet
- **Proposta**: intersezione — top-10 CMC filtrati per disponibilità Binance. Escluso BTC/ETH (già IRL).

### C. Criterio di "uscita" dalle anchor
- N scan consecutivi fuori top-10 CMC prima di swap? (evita rumore rank)
- Combinazione: fuori top-10 + BEARISH strong → swap; fuori top-10 da solo → alert ma no azione?
- **Proposta**: 3 scan consecutivi fuori top-10 (= 12h a scan_interval=4h, 3h a scan=1h). Swap scatta solo con conferma Telegram al CEO.

### D. Chi gestisce le transizioni?
- Scenario: SOL era anchor, esce dalla top-10 → diventa TF rotation universe? O resta in limbo?
- **Proposta**: MiniTF scrive `managed_by='anchor'` su bot_config. Se promossa ad anchor → `anchor`. Se declassata → DEALLOCATE via pending_liquidation (come fa TF oggi). Se TF la rivede BULLISH tra gli alt più forti, può re-ALLOCATE come TF-managed. Flusso anchor → alt → anchor possibile nel tempo.

### E. Dove sta la linea tra MiniTF e TF?
- Tenere 2 codebase separate o 1 codebase con modalità configurabile (`mode=rotation` vs `mode=anchor_tuner`)?
- **Proposta**: 1 codebase, 2 configurazioni. 80% della logica (classifier, scanner, ATR) è condivisa.

### F. Sentinel: quanto potere gli dai?
- **Advisor**: scrive risk score in DB, alert Telegram, zero override automatici
- **Moderate**: può temporaneamente settare `trend_config.trend_follower_enabled=false` in emergency, sempre con alert CEO
- **Aggressive**: può deallocare bot individualmente, alzare skim, mettere grid in pause
- **Proposta**: partenza Advisor, upgrade a Moderate solo dopo dimostrato affidabilità su news comprensione

### G. Due cervelli separati o uno solo?
Il CEO ha sollevato il dubbio: meglio TF + MiniTF separati o un singolo cervello più complesso?
- **Separati**: policy più leggibili, bug più localizzati, specialisti migliori dei generalisti. Contro: 2 processi, 2 config, 2 luoghi in cui qualcosa può rompersi
- **Unico**: tutto in un posto. Contro: il prompt/logica diventa obeso, compromessi interni tra "ruota aggressivo" e "preserva conservativo"
- **Proposta (bias)**: separati. Il costo operativo è basso (riuso della stessa codebase), il beneficio di chiarezza policy è alto

## Cosa NON sto proponendo

- Non sto proponendo di scrivere MiniTF o Sentinel ora. Prima serve TF maturo (36e/g/h deployati + 2-4 settimane di monitoring)
- Non sto proponendo di rimpiazzare BTC/SOL/BONK manuali *subito*. La migrazione a "anchor from top-10 CMC" è un passo futuro, fatto dopo la visione è condivisa col CEO
- Non sto proponendo cambi architetturali acuti. Ogni passo è additivo: nuova funzionalità = nuovo bot, non riscrittura dei precedenti

## Ordine di implementazione suggerito

1. **Ora → +2 settimane**: stabilizzare TF con 36e (rotation + ATR) + 36g (compounding) + 36h (Haiku reads TF). Raccogliere dati di performance.
2. **+2 → +6 settimane**: brief MiniTF (riuso codebase TF), implementare su BTC/SOL/BONK come esperimento (i manuali diventano i primi "anchor"). Se funziona, migrare a selection top-10 CMC.
3. **+6 → +12 settimane**: brief Sentinel (Phase 3 roadmap esistente). Partenza Advisor-mode (zero override). Integrazione feed CryptoPanic.
4. **+3 mesi+**: valutare upgrade Sentinel → Moderate mode, riduzione anchor da 2 a 1 o 0 se TF+MiniTF dimostrano maturità.

---

## Note per la sessione col CEO

- I numeri (2 anchor, 3 scan di cooldown, 1h scan interval, strength delta +15, etc.) sono **placeholder** — da calibrare con dati reali
- Il sistema complessivo deve restare **fault-tolerant**: se uno dei 4 cervelli va down, gli altri continuano. Nessun cervello deve essere "necessario" al funzionamento base (il GRID da solo sa fare trading, gli altri aggiungono intelligenza)
- Il CEO conserva sempre il diritto di override manuale via admin UI. Non è una regola di sicurezza, è una regola di dignità: è il suo progetto, i suoi soldi
- Il principio di "conservatorismo sulle anchor" è **razionale**, non emotivo: dato che BTC/ETH sono già IRL e le 2 anchor sono il cuscinetto paper, tenerle stabili è gestione del rischio corretta. Un sistema autonomous-only è più interessante narrativamente ma più rischioso operativamente

---

## Status

Questo documento è un **appunto per brainstorming**, non un piano. Andrà rivisto dopo la sessione col CEO, probabilmente riscritto in forma più sintetica come sezione della roadmap.html o come `ROADMAP.md` al root del repo.
