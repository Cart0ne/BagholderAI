# VISION — Architettura multi-cervello BagHolderAI

**Date:** 2026-04-16 (brainstorming appunti, da discutere col CEO)
**Aggiornato:** 2026-04-24 — Session 45 brainstorming esteso
**Stato:** NON un piano, NON uno spec. Sono appunti per una sessione di allineamento sulla visione di medio periodo (3-6 mesi).
**Prerequisiti attuali (24 apr):** TF deployato con 45a/b/c/d/e live. Distance filter attivo. Paper trading attivo.

---

## Il principio di fondo

Un singolo "AI CEO" monolitico che decide tutto (allocazioni + parametri + reazioni a news + safety) è fragile: troppa logica in un unico punto, troppi trade-off incompatibili da comporre in un solo prompt/policy.

La direzione che emerge dal brainstorming: **specializzazione**. Ogni cervello ha uno scope ristretto e un output limitato. La composizione dei loro output produce il comportamento complessivo del sistema.

---

## I 4 cervelli (stato + ruolo proposto)

### 1. GRID Bot — **esecutore meccanico** (oggi attivo)

- **Scope**: un singolo symbol, parametri fissi (buy_pct, sell_pct, capital_per_trade, idle_reentry)
- **Decide**: se/quando comprare o vendere in base al movimento di prezzo locale vs ultimo buy
- **Non decide**: quale coin tradare, quanto budget riceve, se il contesto di mercato è favorevole
- **Rule set**: Strategy A (never sell at loss), grid percentuale, skim 30% a reserve_ledger
- **Stato**: stabile, in produzione da mesi su BTC/SOL/BONK

### 2. TF Trend Follower — **allocatore di alt** (oggi attivo, in refinement)

- **Scope**: universo "rotation" (top-50 Binance meno manual whitelist)
- **Decide**: quali N coin (tf_max_coins) tenere, con quale budget (tf_budget), quando ruotare
- **Non decide**: parametri delle anchor coin, reazioni a eventi esogeni
- **Stato**: live con 45a-e deployati, monitoring attivo

### 3. MiniTF — **tuner dei parametri anchor** (concetto, futuro)

- **Scope**: le 2-3 "anchor coin" (scelte da top-10 CMC per volume, escluso BTC/ETH)
- **Decide**: modulare dinamicamente `buy_pct` / `sell_pct` / `capital_per_trade` / `idle_reentry_hours`
- **Non decide**: quale coin è anchor (regola statica), né swap
- **Filosofia**: il GRID sulle anchor continua a comportarsi come un GRID classico, ma "respira" col mercato
- **Stato**: brief non ancora scritto

### 4. AI Sentinel — **meta-brain di contesto** (roadmap Phase 3, futuro)

- **Scope**: mondo esterno — news, eventi macro, hacks, regolamenti, sentiment social
- **Decide**: risk score + opportunity score globali; può proporre override
- **Output tipico**: "Regolamento EU annunciato oggi → risk score 75/100, suggerisco pause nuove allocate TF per 24h"
- **Modello**: Claude Haiku (cost efficiency), Sonnet per livelli critici
- **Autorità**: limitata — può proporre e alertare, override reali richiedono conferma CEO

### 4b. Layer macro-tecnico — **scudo anti-bear deterministico**

Zero LLM, codice puro. Output: `macro_risk_score` che il Sentinel combina con `news_risk_score`.

**Segnali proposti:**
- BTC weekly EMA 50/200 (death cross = bear primario)
- Volume / total market cap divergence
- BTC dominance spike (+3-5 punti/settimana = fuga dalle alt)
- Fear & Greed index (<20 o >80)

### 4c. Brainstorming session 45 (2026-04-23/24) — raffinamento ruolo Sentinel

**Livelli operativi proposti:**

1. **Livello A — Sanity check pre-ALLOCATE** (sincrono, per-coin): ultimo "ok/pausa/veto" con giudizio olistico prima di allocare
2. **Livello B — Post-mortem asincrono**: ogni sera analizza allocazioni perdenti e propone nuovi filtri. Il ciclo di apprendimento automatizzato.
3. **Livello C — Monitoring operativo**: ogni N ore scansiona anomalie, segnala via Telegram
4. **Livello D — Context summarizer**: brief automatico per il CEO all'apertura sessione

**Risk score graduale (non binario):**
```
risk_score 0-30   → alloca normale
risk_score 30-60  → alloca ma dimezza capital_allocation
risk_score 60-80  → alloca solo su Tier 1 blue chip
risk_score 80-100 → emergency pause
```

**Scelta modelli:**
- Livello A: Sonnet 4.6 / Opus 4.7
- Livello B: Opus 4.7 (1 call/giorno)
- Livello C: Haiku 4.5 (economico)
- Livello D: Sonnet 4.6
- Macro signals 4b: nessun LLM

**Costo stimato Sentinel completo: ~$0.13/giorno (~$4/mese)**

---

## Brainstorming session 45 (2026-04-24) — blue chip, buy pause, TF-as-scout

### Il problema fondamentale emerso dall'analisi dati

Confronto all-time v3:

| Sistema | PnL | Win rate | Note |
|---------|-----|----------|------|
| Grid (BTC/SOL/BONK) | +$49.15 | 99.3% | Nessuno stop loss, mercato laterale |
| TF (coin rotanti) | -$2.21 | 64.4% | Stop loss attivo, stesse condizioni |

**Insight chiave**: la differenza non è solo la strategia — è la **fiducia nella coin**. BTC e SOL "torneranno", è quasi un assioma. Il grid compra i dip, aspetta, vende la recovery. MOVR e BOME potrebbero non tornare mai.

Il Grid senza stop loss in laterale batte il TF con stop loss su coin rotanti. Questo non è un bug — è la dimostrazione empirica che trattare DOGE come KAT è concettualmente sbagliato.

---

### Idea 1 — Stop loss per tier (asset class differentiation)

**Il principio:** coin con profilo di rischio strutturalmente diverso meritano policy di risk management diverse. Nel mondo tradizionale è normale: un Treasury bond non si gestisce come una startup biotech.

**Proposta:**

| Tier | Esempi | Stop loss | Ragionale |
|------|--------|-----------|-----------|
| T1 blue chip | DOGE, XRP, XLM, ADA, LTC, TRX | Disabilitato o molto largo (30-40%) | Mean reversion quasi certa su orizzonti lunghi |
| T2 mid-cap | coin $20-100M volume | Default 15% | Rischio medio, recovery probabile ma incerta |
| T3 small-cap | shitcoin <$20M | Aggressivo 8-10% | Rischio sparizione concreta |

**Il problema tecnico attuale:** il sistema filtra per volume ma non per market cap assoluto. Volume ≠ blue chip — SPK ha $200M volume giornaliero ma non è DOGE. Binance via ccxt non espone market cap (richiede supply × prezzo da fonte esterna).

**Soluzione proposta: whitelist manuale CEO**
Una lista statica di coin "certificabili come blue chip" decisa dal CEO, hardcodata o configurabile in trend_config:
```
tf_blue_chip_whitelist = "DOGE/USDT,XRP/USDT,XLM/USDT,ADA/USDT,LTC/USDT,TRX/USDT,ATOM/USDT"
```
Quando TF alloca una coin da questa lista → stop loss disabilitato, trattamento Grid-like.
Tutto il resto → stop loss normale per tier.

**Perché non CoinGecko API**: richiede mapping simboli Binance ↔ CMC, verifica disponibilità trading, aggiornamento automatico, dipendenza esterna. Complessità non giustificata per una lista che cambia raramente.

**Nota filosofica**: ci chimiamo BagHolderAI. Tenere i bag su XRP ha senso. Tenere i bag su KAT no.

---

### Idea 2 — Buy pause tecnica (stop al riacquisto, non alla posizione)

**Il problema reale identificato**: il grid compra i dip per design — ottimo in laterale, disastroso in downtrend. SPK oggi: 15 sell, 8 in perdita, comprando e ricomprando una coin in calo per tutta la giornata. Lo stop loss attuale è reattivo (aspetta che tu abbia perso), il buy pause è proattivo.

**Come funzionerebbe:**
- Coin attiva + segnale tecnico negativo (distance in calo, BEARISH incipiente) → **buy pause**
- I lotti aperti restano, il grid continua a vendere normalmente
- Quando il segnale si riprende → buy riprendono automaticamente
- Capitale non esposto a nuova esposizione in downtrend

**In sostanza**: è `stop_buy_drawdown_pct` guidato da indicatori tecnici invece che dal calo percentuale. Più intelligente, più anticipatorio. Il capitale non si accumula su una coin in discesa.

**Interazione con take profit esistenti**: poiché il grid ha già sell_pct configurati, in salita i lotti vengono venduti naturalmente strada facendo. Il buy pause serve principalmente a proteggere la fase di discesa, non a sostituire i take profit.

**Status**: da formalizzare come brief. Richiede un nuovo campo in bot_config (es. `buy_pause_until`) e logica nel grid runner.

---

### Idea 3 — TF come scout, Grid come esecutore stabile (visione a lungo termine)

**Il principio:** il TF non dovrebbe tenere a lungo termine le blue chip — dovrebbe **trovarle** e **promuoverle** al Grid.

```
TF seleziona DOGE come BULLISH strong
   ↓
DOGE è in whitelist blue chip
   ↓
TF la passa al Grid come "anchor dinamica"
   ↓
TF libero di cercare la prossima opportunità
   ↓
Grid gestisce DOGE a lungo termine senza stop loss
```

**Il nome nel trading tradizionale**: core-satellite portfolio management. Il "core" (BTC/SOL/BONK + blue chip promosse) gira sempre. I "satellite" (coin rotanti T2/T3) vengono e vanno con stop loss aggressivo.

**Il problema tecnico**: il Grid ha oggi 3 coin fisse manuali. Aggiungere coin dinamicamente significa Grid semi-automatico — cambio architetturale significativo, non triviale.

**Alternativa breve termine**: TF tratta blue chip con comportamento Grid-like direttamente — stop loss molto largo (40%) + buy pause tecnica invece di stop loss classico. Non è il Grid puro, ma si comporta in modo simile.

**Status**: visione a lungo termine. Pre-requisiti: TF stabile + MiniTF concettualizzato + decisione CEO su quante anchor vuole gestire.

---

### Idea 4 — Sentinel come CEO AI (la visione finale)

**Quello che Max ha descritto oggi** è più ambizioso di quanto scritto nella versione precedente di questo documento. Non solo un "meta-brain di contesto" — ma un **sistema che nel tempo sostituisce le decisioni operative del CEO**.

**La gerarchia evolutiva:**

```
OGGI:
Max (CEO) → approva ogni brief → CC implementa → bot eseguono

FASE 2 (Sentinel advisor):
Max (Board) → Sentinel propone modifiche → Max approva → CC implementa

FASE 3 (Sentinel autonomo):
Max (Board puro) → osserva
Sentinel CEO → legge risultati → propone + implementa filtri → valida → adotta
CC → riceve brief dal Sentinel, non da Max

FASE FINALE:
Max → interviene solo per decisioni straordinarie o etiche
Sistema → autonomo, auto-migliorante, genera reddito passivo
```

**Il Sentinel nella visione finale**:
- Legge `bot_events_log` e `bot_state_snapshots` ogni notte
- Identifica pattern di perdita (quello che Max e CEO hanno fatto a mano nelle sessioni 40-45)
- Formula briefs per CC autonomamente
- Valida i risultati post-deploy
- Propone al Board solo le decisioni che superano soglie di rischio o budget

**La lezione della sessione 45**: quello che CC Opus ha fatto (validazione storica 45e v2) — analizzare 11 perdite, identificare il pattern, proporre il filtro migliore — è esattamente quello che il Sentinel Livello B dovrebbe fare ogni notte in automatico. Non è fantascienza, è automazione di un processo già manuale.

**Perché è realistico:**
1. I dati ci sono già (Supabase, trades, bot_events_log)
2. I modelli ci sono già (Opus per ragionamento profondo, Haiku per monitoring)
3. Il framework ci sono già (briefs .md → CC → deploy → verifica)
4. L'unico pezzo mancante: il sistema che fa girare questo loop senza Max nel mezzo

---

## Filtri deterministici — stato validazione

| Segnale | Stato | Risultato |
|---------|-------|-----------|
| Distance from EMA20 > 10% | ✅ DEPLOYATO (45e) | 92.4% perdite v3 bloccate |
| Price above EMA20 | ❌ scartato | 0/11 perdite bloccate |
| RSI > 70 | ❌ scartato | 83.5%, inferiore a distance |
| SL cooldown post-stop | ✅ DEPLOYATO (45a) | operativo |
| Volume tier allocation | ✅ DEPLOYATO (45c/d) | operativo |
| BTC correlation | 🔲 da validare | 0/11 in bull — re-validare in bear |
| Volume spike | 🔲 candidato | non validato |
| RSI slope (reversal) | 🔲 candidato | non validato |
| Buy pause tecnica | 🔲 da formalizzare | idea brainstorming 45 |

---

## La gerarchia proposta (aggiornata)

```
          ┌───────────────────────────────┐
          │        Board (Max)            │  Override finale, sempre
          │  osserva, vincoli strategici  │
          └───────────────┬───────────────┘
                          │
          ┌───────────────▼───────────────┐
          │       AI Sentinel / CEO AI    │  "Watch the world + decide"
          │  Risk score + auto-brief +    │  Phase 3 → Fase finale
          │  validazione + apprendimento  │
          └───────┬───────────────┬───────┘
                  │               │
        ┌─────────▼───┐     ┌─────▼───────────┐
        │  TF          │     │  MiniTF (tuner)  │
        │  rotation    │     │  anchor coin     │
        │  + scout     │     │  UPDATE params   │
        └─────┬────────┘     └──────┬───────────┘
              │                     │
              └──────────┬──────────┘
                         │ scrive bot_config
                         ▼
        ┌────────────────────────────────────────┐
        │           GRID Bots (eseguono)          │
        │  BTC  SOL  BONK  │  blue chip promosse  │
        │  (anchor fissi)  │  (anchor dinamiche)  │
        └────────────────────────────────────────┘
```

---

## Ordine di implementazione suggerito (aggiornato al 24 apr)

1. ✅ **45a-e**: filtri deterministici TF (done)
2. **1-2 settimane**: osservazione distance filter in produzione. Funziona davvero?
3. **Brainstorming formalizzazione**:
   - Blue chip whitelist + stop loss per tier (relativamente semplice)
   - Buy pause tecnica (moderata complessità)
4. **MiniTF**: brief dopo TF stabile + 2-4 settimane monitoring
5. **Sentinel Livello B** (post-mortem asincrono): il più sicuro da iniziare, zero override
6. **Sentinel Livello A** (pre-ALLOCATE): dopo B dimostrato affidabile
7. **Livelli C e D + CEO AI**: fase finale, autonomia progressiva

---

## Dubbi aperti (invariati + nuovi)

### A-G (invariati dal draft 16 apr)
Vedi sezione precedente — anchor coin count, universo anchor, criteri uscita, gestione transizioni, MiniTF vs TF unica codebase, autorità Sentinel.

### H. Blue chip whitelist: statica o semi-automatica?
- Statica (CEO decide): semplice, controllo totale, aggiornamento manuale raro
- Semi-automatica (verifica CMC top-X periodica): più elegante ma dipendenza esterna
- **Proposta**: statica per ora, con campo configurabile dashboard. Se lista > 10 coin → valutare automazione.

### I. Buy pause: basata su quale segnale?
- Distance from EMA scende sotto soglia?
- Classificatore BEARISH per la coin specifica?
- Combinazione di due segnali?
- **Proposta**: BEARISH classificazione è il segnale più naturale — il sistema lo calcola già per ogni coin, sarebbe coerente usarlo anche per la buy pause sulla coin stessa invece che solo per DEALLOCATE.

### J. TF-as-scout: quando scatta la promozione a Grid?
- N scan consecutivi BULLISH strong + in blue chip whitelist?
- Decisione CEO esplicita via dashboard?
- **Proposta**: decisione CEO esplicita nella fase iniziale. Il TF segnala via Telegram "DOGE BULLISH strong da 3 scan — candidata promozione anchor?", CEO approva manualmente.

### K. CEO AI — quanta autonomia e quando?
- Sentinel propone brief → CEO approva sempre (conservativo)
- Sentinel propone brief → CEO approva solo sopra soglia budget (moderato)
- Sentinel propone e implementa → CEO riceve report (autonomo)
- **Proposta**: conservativo nelle prime fasi, upgrade progressivo basato su track record. Il Sentinel deve guadagnarsi la fiducia con dati, non riceverla a priori.

---

## Cosa NON stiamo proponendo ora

- Non riscrivere il TF da zero
- Non rimpiazzare BTC/SOL/BONK manuali subito
- Non dare autonomia piena al Sentinel prima che sia dimostrata
- Non aggiungere filtri non validati storicamente (lezione 45e v1 → v2)

---

## Note filosofiche

- **Fault tolerance**: se uno dei cervelli va down, gli altri continuano. Il Grid da solo sa fare trading.
- **Conservatorismo sulle anchor**: BTC/ETH sono già IRL. Le anchor paper sono il cuscinetto. Tenerle stabili è gestione del rischio corretta.
- **Data-first**: nessun nuovo filtro senza backtest su dati v3 prima del deploy (lezione 45e).
- **Il nome è un manifesto**: BagHolderAI tiene i bag su XRP. Non su KAT.
- **Max come Board**: l'obiettivo finale è che Max osservi, non operi. Ogni sistema che costruiamo oggi è un passo verso quella autonomia. Ogni brief che automatizziamo è un neurone in più nel cervello del sistema.

---

## Status

Documento vivo — aggiornato a ogni sessione con nuove idee validate. Non è un piano esecutivo, è la mappa della destinazione. La roadmap operativa vive in `web/roadmap.html`.
