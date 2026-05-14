# Brief 77b — Sentinel Sprint 2: Slow Loop + Regime Detection

**Da:** CEO (Claude, claude.ai)
**Per:** CC (Claude Code)
**Data:** 14 maggio 2026
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-14 (S76) + report S77 audit Sprint 1 (tutti PASS)
**Stima:** ~4-5h (infrastruttura input + regime analyzer + wiring Sherpa + test + dashboard)
**Priorità:** ALTA — secondo step della sequenza Sentinel-first → Sherpa → mainnet
**Prerequisito Board:** chiave API CoinMarketCap (free tier) fornita come env var `CMC_API_KEY`

---

## Contesto

Sprint 1 è chiuso con audit PASS (brief 77a). Sentinel ha il fast loop (BTC price + funding, ogni 60s) che produce risk/opportunity score. Sherpa legge questi score ma parte sempre da `regime="neutral"` — il "meteorologo" manca.

Sprint 2 aggiunge il **slow loop**: legge dati macro (Fear & Greed Index + metriche globali CMC), determina in quale dei 5 regimi siamo (extreme_fear → extreme_greed), e passa il regime a Sherpa. Sherpa ha già la BASE_TABLE con tutti e 5 i regimi pronti nel codice (`parameter_rules.py:18-24`) — basta alimentarla.

**Cosa cambia concretamente per il bot**: oggi Sherpa propone sempre partendo da neutral (buy 1.0 / sell 1.5 / idle 1.0h) + delta dal fast loop. Dopo Sprint 2, in un mercato in panico (F&G = 15) Sherpa partirà da extreme_fear (buy 2.5 / sell 1.0 / idle 4.0h) + delta. In un mercato euforico (F&G = 80) partirà da extreme_greed (buy 0.5 / sell 3.0 / idle 0.5h) + delta. Il comportamento del bot diventa adattivo al contesto macro.

---

## ⚠️ TASK NON BANALE — Piano in italiano PRIMA del codice

Stima >1h. CC deve produrre un **piano in italiano leggibile da Max** prima di scrivere qualsiasi codice. Il piano copre: architettura file, sequenza di implementazione, decisioni tecniche (caching, error handling, fallback), test plan. Max approva, poi CC implementa.

---

## Architettura target

### Nuovi file da creare

```
bot/sentinel/inputs/alternative_fng.py    # Fear & Greed Index (alternative.me)
bot/sentinel/inputs/cmc_global.py         # CMC global metrics (BTC dom, mcap, volume)
bot/sentinel/regime_analyzer.py           # F&G + CMC → regime string
```

### File da modificare

```
bot/sentinel/main.py          # aggiungere slow loop (timer ogni 4h nel fast loop)
bot/sentinel/score_engine.py   # aggiungere score_type='slow' con regime
bot/sherpa/main.py             # leggere regime dal latest slow score
```

### File OFF-LIMITS

```
bot/grid_runner/               # tutto
bot/sentinel/price_monitor.py  # il fast loop non cambia
bot/sentinel/inputs/binance_btc.py
bot/sentinel/inputs/binance_funding.py
bot/sherpa/parameter_rules.py  # la BASE_TABLE e calculate_parameters() sono già pronti
bot/sherpa/config_writer.py
bot/sherpa/cooldown_manager.py
```

---

## TASK 1 — Input: Fear & Greed Index

**File:** `bot/sentinel/inputs/alternative_fng.py`

**Sorgente:** `https://api.alternative.me/fng/?limit=1`

**Output:** dict con almeno:
- `fng_value`: int 0-100
- `fng_label`: string ("Extreme Fear" / "Fear" / "Neutral" / "Greed" / "Extreme Greed")
- `fng_timestamp`: quando è stato calcolato (l'API aggiorna ~1x/giorno)

**Specifiche:**
- Endpoint gratuito, no autenticazione, rate limit generoso
- L'API aggiorna il valore ~1x al giorno. Quindi anche se chiamiamo ogni 4h, il valore potrebbe non cambiare — è corretto
- Fallback su errore: ritornare `None` (Sentinel continua col fast loop, Sherpa usa l'ultimo regime noto)
- Cache: non serve in-memory, la frequenza di chiamata è già bassa (ogni 4h)

---

## TASK 2 — Input: CMC Global Metrics

**File:** `bot/sentinel/inputs/cmc_global.py`

**Sorgente:** CoinMarketCap API `/v1/global-metrics/quotes/latest`

**Autenticazione:** header `X-CMC_PRO_API_KEY` da env var `CMC_API_KEY`

**Output:** dict con almeno:
- `btc_dominance`: float (es. 57.3 = 57.3%)
- `total_market_cap_usd`: float
- `total_volume_24h_usd`: float
- `active_cryptocurrencies`: int (utile per context, non per scoring)

**Specifiche:**
- Free tier = 10.000 crediti/mese. 1 call = 1 credito. A 6 call/giorno = 180/mese. Largo margine
- Fallback su errore: ritornare `None` — il regime si decide solo da F&G
- Se `CMC_API_KEY` non è settato: loggare warning a ogni slow tick, ritornare `None`, NON crashare

---

## TASK 3 — Regime Analyzer

**File:** `bot/sentinel/regime_analyzer.py`

**Input:** dict con F&G + CMC data (entrambi opzionali)

**Output:** una delle 5 stringhe regime: `extreme_fear`, `fear`, `neutral`, `greed`, `extreme_greed`

### Logica regime (Sprint 2 MVP — solo F&G)

La mappatura è diretta — F&G è già un indice aggregato che riassume volatilità, volume, social media, dominanza e trend:

| F&G value | Regime |
|-----------|--------|
| 0–20      | extreme_fear |
| 21–40     | fear |
| 41–60     | neutral |
| 61–80     | greed |
| 81–100    | extreme_greed |

**Le soglie sopra sono la proposta CEO.** CC può suggerire alternative se i dati storici F&G (disponibili via `?limit=365`) mostrano una distribuzione che rende queste soglie sbilanciate — ma deve presentare il ragionamento nel piano italiano prima di cambiare.

### CMC data: log only (Sprint 2 MVP)

In Sprint 2, i dati CMC vengono **loggati nel record sentinel_scores** ma **non influenzano il regime**. Motivazione: non abbiamo una teoria validata su come BTC dominance debba pesare. I dati CMC servono per l'analisi futura (Sprint 2.5: "il regime era fear ma la dominanza stava salendo — avremmo dovuto essere in neutral?").

### Fallback

- F&G disponibile → regime da F&G
- F&G non disponibile, CMC disponibile → regime = `neutral` (log warning)
- Entrambi non disponibili → regime = `neutral` (log warning)
- F&G stale (>36h senza aggiornamento) → regime = `neutral` (log warning "F&G stale, fallback neutral")

---

## TASK 4 — Wiring nel Sentinel main loop

**File:** `bot/sentinel/main.py`

Il fast loop (60s) resta invariato. Aggiungere un **timer interno** che ogni `SLOW_LOOP_INTERVAL_S` secondi (proposta: 4 ore = 14400s) esegue il slow loop:

1. Chiama `alternative_fng.fetch()` → F&G data
2. Chiama `cmc_global.fetch()` → CMC data (se CMC_API_KEY presente)
3. Chiama `regime_analyzer.determine_regime(fng_data, cmc_data)` → regime string
4. Computa un slow score (proposta: risk e opp derivati dal regime per coerenza, es. extreme_fear → risk=80, opp=20; extreme_greed → risk=20, opp=80)
5. INSERT in `sentinel_scores` con `score_type='slow'` e `raw_signals` contenente: fng_value, fng_label, regime, btc_dominance, total_market_cap, total_volume_24h

**Timer approach:** contatore interno nel fast loop. Ogni tick fast (60s) incrementa. Quando raggiunge `SLOW_LOOP_INTERVAL_S / FAST_LOOP_INTERVAL_S` → trigger slow. Semplice, niente thread, niente scheduler extra.

**Primo slow tick:** eseguire al boot di Sentinel (non aspettare 4h). Così Sherpa ha un regime dal primo ciclo.

---

## TASK 5 — Wiring in Sherpa

**File:** `bot/sherpa/main.py`

Cambiamento minimo. Dove oggi Sherpa chiama:

```python
calculate_parameters(regime="neutral", fast_signals=...)
```

Deve invece:

1. Leggere l'ultimo record `sentinel_scores` con `score_type='slow'` (query `ORDER BY created_at DESC LIMIT 1`)
2. Estrarre il regime da `raw_signals->>'regime'`
3. Se nessun record slow esiste (Sprint 1 legacy, primo boot) → fallback `"neutral"`
4. Passare il regime a `calculate_parameters(regime=regime_from_db, fast_signals=...)`

**Nessuna modifica a `parameter_rules.py`** — la BASE_TABLE e `calculate_parameters()` supportano già tutti e 5 i regimi.

---

## TASK 6 — Test

### Test unitari (nuovi file)

- `tests/test_regime_analyzer.py`:
  - F&G 15 → extreme_fear
  - F&G 35 → fear
  - F&G 50 → neutral
  - F&G 70 → greed
  - F&G 90 → extreme_greed
  - F&G boundary: 20 → extreme_fear, 21 → fear (o viceversa, dipende da inclusivo/esclusivo — documentare)
  - F&G None → neutral (fallback)
  - F&G stale → neutral

- `tests/test_score_engine_slow.py` (o estensione del test esistente):
  - score() con regime signals produce score_type='slow' coherente

- `tests/test_fng_input.py` (mock della risposta API):
  - Risposta valida → dict corretto
  - Risposta errore → None
  - Risposta malformata → None + log warning

### Test integrazione (manuale, post-commit)

- Restart Sentinel su Mac Mini → primo slow tick al boot
- Verifica record `sentinel_scores` con `score_type='slow'` presente
- Verifica Sherpa legge il regime dal DB e lo usa nel proposal
- Verifica `sherpa_proposals` mostra regime != "neutral" (se F&G non è a 50)

---

## TASK 7 — Dashboard /admin (opzionale ma raccomandato)

Se tempo permette, aggiungere alla pagina `/admin` una sezione "Regime" con:
- Regime corrente (da ultimo slow score)
- F&G value + label
- BTC dominance
- Timestamp ultimo aggiornamento slow

Questo è un nice-to-have. Se CC stima che porta la sessione oltre le 5h, saltare e fare in un brief successivo.

---

## Decisioni delegate a CC

- Struttura interna delle classi/funzioni dei nuovi file (purché mantengano il pattern degli input Sprint 1)
- Gestione errori HTTP/timeout sulle API esterne
- Formato esatto del `raw_signals` jsonb per score_type='slow'
- Se serve una migration Supabase per un nuovo campo/constraint (improbabile — `sentinel_scores` è già flessibile con il jsonb)

## Decisioni che CC DEVE chiedere al Board

- Se le soglie F&G → regime devono essere diverse da quelle proposte
- Se CMC data deve influenzare il regime (in Sprint 2 = log only, ma se CC vede un motivo per cambiare, chieda)
- Se il SLOW_LOOP_INTERVAL deve essere diverso da 4h
- Se serve una tabella Supabase nuova (non prevista)
- Qualunque modifica a `parameter_rules.py` (BASE_TABLE è già approvata, non toccare)

---

## Output atteso a fine sessione

1. Piano in italiano approvato da Max
2. 3 nuovi file input + regime analyzer
3. Modifiche a sentinel/main.py e sherpa/main.py
4. Test verdi (tutti quelli esistenti + nuovi)
5. `report_for_CEO/` con risultati
6. Commit su main
7. **NON restartare il bot** — Max farà il restart sul Mac Mini dopo revisione

---

## Roadmap impact

- Sprint 2 shipped → Sherpa diventa regime-aware. Le proposte DRY_RUN cambieranno in base al sentiment macro
- Prossimo step: **osservazione 5-7 giorni** delle proposte Sherpa con regime attivo — l'audit tipo 77a ma per Sprint 2 (le proposte hanno senso? Il regime cambia nei momenti giusti?)
- Dopo osservazione: decisione su Sherpa LIVE su testnet (un parametro alla volta, partendo da sell_pct)

---

## Vincoli

- **Nessun restart Mac Mini da questo brief.** Solo codice + test + commit
- **Non toccare Sherpa parameter_rules.py.** La BASE_TABLE è approvata. Sprint 2 la alimenta, non la cambia
- **CMC_API_KEY opzionale.** Se Max non l'ha ancora, il sistema funziona solo con F&G. CMC è bonus
- **Regime detection MVP = solo F&G.** CMC data viene loggata per analisi futura. Niente over-engineering
- **Il report deve essere leggibile da Max** (italiano, numeri chiari)
- **Ogni query SQL via Supabase MCP** `execute_sql`, non inventare risultati
