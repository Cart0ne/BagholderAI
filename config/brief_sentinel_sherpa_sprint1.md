# BRIEF — Sentinel + Sherpa Sprint 1

**Da:** CEO (Claude)  
**A:** CC (Claude Code)  
**Data:** May 6, 2026  
**Tipo:** Implementazione — Sprint 1 di 3  
**Modalità:** DRY_RUN (default) — Sherpa calcola e logga tutto, ma NON scrive in `bot_config`. Switch a LIVE solo dopo conferma Board.

---

## Obiettivo

Costruire lo scheletro funzionante di Sentinel (fast loop) e Sherpa (parameter writer) in **modalità osservazione**. Alla fine dello sprint, il sistema deve:

1. Leggere il prezzo BTC e i funding rates da Binance ogni 1-2 minuti
2. Calcolare un **risk/opportunity score** (0-100)
3. Scrivere lo score in una nuova tabella Supabase `sentinel_scores`
4. Sherpa legge lo score, calcola i nuovi parametri per i Grid bot
5. **DRY_RUN (default):** Sherpa logga le modifiche proposte in `sherpa_proposals` senza toccare `bot_config`
6. **LIVE (dopo Board approval):** Sherpa scrive in `bot_config` e logga in `config_changes_log`
7. Se il Board ha modificato un parametro manualmente nelle ultime 24h, Sherpa NON lo tocca (cooldown)

**NON incluso in Sprint 1:** Fear & Greed, CMC dominance, news, LLM — tutto Sprint 2+.

---

## Architettura — regole inviolabili

### Multifile da giorno zero

```
bot/sentinel/
    __init__.py
    main.py                # Entry point: loop asincrono, gestisce fast loop
    price_monitor.py       # Fetch BTC price da Binance, calcola variazione % su finestre temporali
    funding_monitor.py     # Fetch funding rates da Binance
    score_engine.py        # Combina segnali → risk_score (0-100) + opportunity_score (0-100)

bot/sentinel/inputs/
    __init__.py
    binance_btc.py         # Wrapper Binance API: GET /api/v3/ticker/24hr?symbol=BTCUSDT
    binance_funding.py     # Wrapper Binance API: GET /fapi/v1/fundingRate?symbol=BTCUSDT

bot/sherpa/
    __init__.py
    main.py                # Entry point: loop che legge score e scrive parametri
    parameter_rules.py     # Logica: score → nuovi valori buy_pct, sell_pct, idle_reentry_hours
    config_writer.py       # Scrive in bot_config via Supabase, logga in config_changes_log
    cooldown_manager.py    # Controlla se il Board ha toccato un parametro nelle ultime 24h
```

**NON creare monoliti.** Un file per responsabilità. Se un file supera le 200 righe, spezzalo.

### Tre processi indipendenti

| Processo | Entry point | Ruolo | Se crasha |
|----------|-------------|-------|-----------|
| `sentinel` | `bot/sentinel/main.py` | Legge dati, scrive score | Sherpa usa ultimo score noto, Grid continua |
| `sherpa` | `bot/sherpa/main.py` | Legge score, scrive parametri | Grid continua con parametri correnti |
| `orchestrator` | `bot/orchestrator.py` (esistente) | Lancia e monitora tutto | Restart automatico |

**Comunicazione SOLO via Supabase.** Nessuna connessione diretta tra processi. Se Sentinel è giù, Sherpa legge l'ultimo score dalla tabella. Se Sherpa è giù, Grid va avanti coi parametri attuali.

### Integrazione con Orchestrator

L'orchestrator esistente deve lanciare Sentinel e Sherpa come processi managed, con lo stesso pattern di restart/retry già usato per i grid bot. Dettagli:

- `orchestrator.py` lancia `bot/sentinel/main.py` e `bot/sherpa/main.py` come subprocess
- Se crashano, retry con backoff (stesso pattern dei grid bot)
- Log di avvio/stop in `bot_events_log`

---

## Supabase — nuova tabella

### `sentinel_scores`

```sql
CREATE TABLE sentinel_scores (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    score_type text NOT NULL,           -- 'fast' (Sprint 1) o 'slow' (Sprint 2)
    risk_score integer NOT NULL,        -- 0-100, dove 100 = massimo rischio
    opportunity_score integer NOT NULL, -- 0-100, dove 100 = massima opportunità
    btc_price numeric,
    btc_change_1h numeric,              -- % variazione BTC ultima ora
    btc_change_24h numeric,             -- % variazione BTC ultime 24h
    funding_rate numeric,               -- ultimo funding rate
    raw_signals jsonb,                  -- dump completo segnali per debug/analisi
    notes text                          -- commento leggibile (opzionale)
);

-- Index per query veloci su ultimi score
CREATE INDEX idx_sentinel_scores_type_created 
ON sentinel_scores (score_type, created_at DESC);

-- RLS
ALTER TABLE sentinel_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sentinel_scores_select" ON sentinel_scores FOR SELECT TO anon USING (true);
CREATE POLICY "sentinel_scores_insert" ON sentinel_scores FOR INSERT TO anon WITH CHECK (true);
```

**Retention:** per ora nessun cleanup automatico. Lo valuteremo quando la tabella cresce.

### `sherpa_proposals` (counterfactual tracker)

Tabella dedicata al DRY_RUN. Ogni riga = "cosa Sherpa avrebbe fatto in quel momento". Serve per l'analisi post-hoc: incrociando queste proposte con i trade effettivi in `trades`, possiamo calcolare se i parametri di Sherpa avrebbero migliorato o peggiorato i risultati.

```sql
CREATE TABLE sherpa_proposals (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    symbol text NOT NULL,                    -- es. 'BTCUSDT'
    risk_score integer NOT NULL,             -- score Sentinel al momento della proposta
    opportunity_score integer NOT NULL,
    -- Parametri CORRENTI (quelli che Grid sta usando)
    current_buy_pct numeric,
    current_sell_pct numeric,
    current_idle_reentry_hours numeric,
    -- Parametri PROPOSTI (quelli che Sherpa avrebbe scritto)
    proposed_buy_pct numeric,
    proposed_sell_pct numeric,
    proposed_idle_reentry_hours numeric,
    -- Regime calcolato
    proposed_regime text,                    -- 'very_bullish', 'bullish', 'neutral', 'defensive', 'very_defensive'
    -- Cooldown
    cooldown_active boolean DEFAULT false,   -- true se almeno un parametro era in cooldown
    cooldown_parameters text[],              -- lista parametri in cooldown, es. {'buy_pct'}
    -- Flag per analisi
    would_have_changed boolean NOT NULL,     -- true se almeno un parametro proposto ≠ corrente
    btc_price numeric                        -- prezzo BTC al momento della proposta
);

CREATE INDEX idx_sherpa_proposals_symbol_created 
ON sherpa_proposals (symbol, created_at DESC);

CREATE INDEX idx_sherpa_proposals_changed
ON sherpa_proposals (would_have_changed, created_at DESC);

ALTER TABLE sherpa_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sherpa_proposals_select" ON sherpa_proposals FOR SELECT TO anon USING (true);
CREATE POLICY "sherpa_proposals_insert" ON sherpa_proposals FOR INSERT TO anon WITH CHECK (true);
```

**Come useremo questa tabella per l'analisi:**

1. Prendiamo le fasce temporali dove `would_have_changed = true`
2. In quelle fasce, confrontiamo i trade effettivi (con parametri correnti) con cosa sarebbe successo con i parametri proposti
3. Esempio: se Sherpa proponeva `buy_pct = 2.5%` (defensive) ma Grid stava usando `1.0%`, quanti buy in quel periodo sarebbero stati skippati? E quelli skippati avrebbero poi perso valore?
4. L'analisi la facciamo noi (CEO) via SQL dopo ~7 giorni di dati

---

## Sentinel — logica fast loop

### Ciclo principale (`main.py`)

```
ogni 60 secondi:
    1. Fetch BTC price (binance_btc.py)
    2. Fetch funding rate (binance_funding.py) — NB: si aggiorna ogni 8h, cacheare
    3. Calcola variazioni % su finestre: 5min, 15min, 1h, 4h, 24h
    4. Passa segnali a score_engine.py
    5. score_engine produce risk_score + opportunity_score
    6. INSERT in sentinel_scores
    7. Log evento in bot_events_log: event_type = 'SENTINEL_SCAN'
```

### Price monitor (`price_monitor.py`)

- Mantiene un buffer circolare in memoria degli ultimi N price points (almeno 24h di dati a 1 tick/min = 1440 punti)
- Calcola:
  - `btc_change_5m`: variazione % ultimi 5 minuti
  - `btc_change_15m`: variazione % ultimi 15 minuti
  - `btc_change_1h`: variazione % ultima ora
  - `btc_change_4h`: variazione % ultime 4 ore
  - `btc_change_24h`: variazione % ultime 24 ore
  - `speed_of_fall`: derivata — quanto velocemente sta cadendo (non solo quanto è caduto)
- **Al primo avvio** il buffer è vuoto → le finestre più lunghe non sono disponibili. Il monitor deve gestirlo con grazia (score = 50/neutral finché non ha abbastanza dati).

### Funding monitor (`funding_monitor.py`)

- Binance funding rate si aggiorna ogni 8h (00:00, 08:00, 16:00 UTC)
- Fetch una volta, cachea per 8h
- Segnale: funding rate > 0.03% → mercato over-leveraged (bearish signal); funding rate < -0.01% → short squeeze potential (bullish signal)

### Score engine (`score_engine.py`)

Input: dizionario di segnali dal price monitor e funding monitor.

Output: `risk_score` (0-100) e `opportunity_score` (0-100).

**Logica di scoring (Sprint 1 — solo fast signals):**

| Segnale | Contributo a risk_score | Contributo a opportunity_score |
|---------|------------------------|-------------------------------|
| BTC -3% in 1h | +30 risk | +0 |
| BTC -5% in 1h | +50 risk | +0 |
| BTC -10% in 1h | +80 risk | +0 |
| BTC +3% in 1h | +0 | +25 opportunity |
| BTC +5% in 1h | +0 | +40 opportunity |
| Speed of fall accelerating | +20 risk | +0 |
| Funding rate > 0.03% | +15 risk | +0 |
| Funding rate > 0.05% | +25 risk | +0 |
| Funding rate < -0.01% | +0 | +15 opportunity |
| Funding rate < -0.03% | +0 | +25 opportunity |
| Nessun segnale forte | base 20 | base 20 |

I contributi si sommano, poi si clampano a 0-100. Questi pesi sono **proposte iniziali** — li calibreremo coi dati reali. Per ora li mettiamo come costanti in cima al file, ben commentate, facili da modificare.

**NOTA CRITICA:** lo score NON deve mai essere binario (go/stop). Lo scopo è la modulazione graduale. Anche un risk_score di 60 non significa "ferma tutto" — significa "rallenta".

---

## Sherpa — logica base

### Modalità DRY_RUN (counterfactual tracker)

Variabile d'ambiente `SHERPA_MODE` controlla il comportamento:

- `SHERPA_MODE=dry_run` (default): Sherpa calcola tutto, logga le proposte in `sherpa_proposals`, ma **non tocca `bot_config`**. I Grid bot continuano con i parametri correnti.
- `SHERPA_MODE=live`: Sherpa scrive in `bot_config` e logga in `config_changes_log`. Solo dopo conferma Board.

In DRY_RUN, Sherpa salva ogni proposta nella tabella `sherpa_proposals` con i parametri correnti (quelli che Grid sta usando) e i parametri proposti (quelli che Sherpa avrebbe scritto). Questo ci permette di analizzare dopo: "con i parametri di Sherpa, avremmo fatto meglio o peggio?"

### Ciclo principale (`main.py`)

```
ogni 120 secondi:
    1. Leggi ultimo sentinel_score (WHERE score_type = 'fast' ORDER BY created_at DESC LIMIT 1)
    2. Se lo score ha più di 5 minuti → stale, logga warning ma usa comunque
    3. Se non esiste nessuno score → non fare niente, logga e aspetta
    4. Passa risk_score a parameter_rules.py
    5. parameter_rules calcola nuovi valori per buy_pct, sell_pct, idle_reentry_hours
    6. Per ogni bot Grid attivo (managed_by = 'manual' AND is_active = true):
       a. Leggi parametri correnti da bot_config
       b. Controlla cooldown (cooldown_manager.py)
       c. Se SHERPA_MODE == 'dry_run':
          - INSERT in sherpa_proposals (parametri correnti + proposti + score)
          - Log evento SHERPA_PROPOSAL in bot_events_log
       d. Se SHERPA_MODE == 'live':
          - Se parametro NON è in cooldown E il nuovo valore è diverso dal corrente:
            - Aggiorna bot_config
            - Logga in config_changes_log con changed_by = 'sherpa'
            - Log evento SHERPA_ADJUSTMENT in bot_events_log
    7. Telegram: notifica proposta (dry_run) o modifica (live)
```

### Parameter rules (`parameter_rules.py`)

**Mapping risk_score → parametri Grid (Sprint 1 — solo fast loop):**

| Risk Score | buy_pct | sell_pct | idle_reentry_hours | Regime |
|-----------|---------|----------|-------------------|--------|
| 0-20 | 0.5% | 2.5% | 0.5h | Very bullish |
| 20-40 | 0.8% | 2.0% | 0.75h | Bullish |
| 40-60 | 1.0% | 1.5% | 1.0h | Neutral |
| 60-80 | 1.8% | 1.0% | 2.0h | Defensive |
| 80-100 | 2.5% | 0.8% | 4.0h | Very defensive |

**Interpolazione:** NON usare step function. Interpolare linearmente tra i breakpoint. Esempio: risk_score = 50 → a metà tra Neutral e Bullish, non uno step netto.

**Importante:** i parametri calcolati devono rispettare i range assoluti:
- `buy_pct`: min 0.3%, max 3.0%
- `sell_pct`: min 0.8%, max 4.0%
- `idle_reentry_hours`: min 0.5h, max 6.0h

### Config writer (`config_writer.py`)

Per ogni modifica:

1. Leggi valore corrente da `bot_config`
2. Se nuovo valore == vecchio valore (con tolleranza 0.01) → skip, non loggare
3. Se cooldown attivo su quel parametro per quel bot → skip, logga "cooldown active"
4. Scrivi nuovo valore in `bot_config`
5. INSERT in `config_changes_log`:
   - `symbol`: dal bot
   - `parameter`: nome del parametro (es. 'buy_pct')
   - `old_value`: valore precedente (come text)
   - `new_value`: nuovo valore (come text)
   - `changed_by`: `'sherpa'`

### Cooldown manager (`cooldown_manager.py`)

1. Query `config_changes_log` per il bot/parametro specifico
2. Cerca l'ultimo record dove `changed_by = 'manual-board'` (o qualsiasi valore diverso da 'sherpa')
3. Se trovato E `created_at` è nelle ultime 24 ore → cooldown attivo
4. Return `True` (bloccato) o `False` (libero)

**Attenzione:** quando il Board modifica un parametro dalla dashboard `grid.html`, il `changed_by` corrente è `'max'`. Quindi il cooldown deve cercare `changed_by NOT IN ('sherpa')` — qualsiasi modifica non-Sherpa attiva il cooldown.

---

## Binance API — endpoint specifici

### BTC Price

```
GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT
```

Risposta (campi utili): `lastPrice`, `priceChangePercent` (24h), `highPrice`, `lowPrice`.

Per le finestre < 24h, usare il buffer in memoria del price_monitor, oppure:

```
GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=60
```

per ottenere i klines dell'ultima ora.

### Funding Rate

```
GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1
```

Risposta: `fundingRate` (decimale, es. 0.0001 = 0.01%), `fundingTime`.

**NB:** questo è l'endpoint futures. Il bot attuale usa l'API spot. Verificare che la rete del Mac Mini acceda anche a `fapi.binance.com`.

---

## Bot events — nuovi event types

Aggiungere questi `event_type` in `bot_events_log`:

| event_type | Quando | Dettagli in `details` (jsonb) |
|------------|--------|-------------------------------|
| `SENTINEL_START` | Avvio processo Sentinel | `{"version": "sprint1"}` |
| `SENTINEL_STOP` | Stop processo Sentinel | `{"reason": "..."}` |
| `SENTINEL_SCAN` | Ogni ciclo di scan completato | `{"risk_score": N, "opportunity_score": N, "btc_price": X}` |
| `SENTINEL_ERROR` | Errore nel ciclo | `{"error": "...", "source": "price_monitor/funding_monitor/score_engine"}` |
| `SHERPA_START` | Avvio processo Sherpa | `{"version": "sprint1"}` |
| `SHERPA_STOP` | Stop processo Sherpa | `{"reason": "..."}` |
| `SHERPA_ADJUSTMENT` | Sherpa modifica un parametro (LIVE mode) | `{"symbol": "...", "parameter": "...", "old": X, "new": Y, "risk_score": N}` |
| `SHERPA_PROPOSAL` | Sherpa propone modifica (DRY_RUN mode) | `{"symbol": "...", "mode": "dry_run", "proposed": {"buy_pct": X, "sell_pct": Y, "idle_reentry_hours": Z}, "current": {...}, "risk_score": N}` |
| `SHERPA_COOLDOWN` | Sherpa trova cooldown attivo | `{"symbol": "...", "parameter": "...", "manual_change_at": "..."}` |
| `SHERPA_STALE_SCORE` | Score Sentinel troppo vecchio | `{"score_age_seconds": N, "last_score_at": "..."}` |

---

## Telegram — notifiche

Sentinel e Sherpa devono inviare notifiche Telegram (stesso bot già configurato):

| Evento | Messaggio | Canale |
|--------|-----------|--------|
| `risk_score > 70` | `🛡️ Sentinel: Risk score {score}/100 — BTC {change}% in 1h. Sherpa switching to defensive.` | Private bot |
| `risk_score > 90` | `🚨 SENTINEL ALERT: Risk {score}/100 — BTC crash detected. Full defensive mode.` | Private bot + public channel |
| `Sherpa propone modifiche (DRY_RUN)` | `🏔️ Sherpa [DRY_RUN]: Would adjust {bot} — buy_pct {current}→{proposed}, sell_pct {current}→{proposed}` | Private bot |
| `Sherpa modifica parametri (LIVE)` | `🏔️ Sherpa: Adjusted {bot} — buy_pct {old}→{new}, sell_pct {old}→{new}` | Private bot |
| `Sherpa in cooldown` | `⏸️ Sherpa: Skipping {parameter} on {bot} — Board override active (expires {time})` | Private bot |
| Errore Sentinel/Sherpa | `❌ {process} error: {message}` | Private bot |

**Throttling:** massimo 1 messaggio Telegram per tipo per bot ogni 10 minuti. Non spammare.

**NB in DRY_RUN:** le notifiche di proposta Sherpa vanno inviate solo quando `would_have_changed = true` — se i parametri calcolati sono uguali a quelli correnti, non mandare niente.

---

## Test checklist

### Sentinel

- [ ] `binance_btc.py` ritorna prezzo BTC valido
- [ ] `binance_funding.py` ritorna funding rate valido
- [ ] Price monitor calcola variazioni % corrette su tutte le finestre
- [ ] Price monitor gestisce buffer vuoto al primo avvio (score neutro)
- [ ] Score engine produce risk_score e opportunity_score nel range 0-100
- [ ] Score viene scritto in `sentinel_scores` con tutti i campi
- [ ] Evento `SENTINEL_SCAN` loggato in `bot_events_log`
- [ ] Sentinel gestisce errori API Binance senza crashare (retry con backoff)
- [ ] Se Binance non risponde, Sentinel logga errore e riprova al ciclo successivo

### Sherpa

- [ ] Legge ultimo score da `sentinel_scores`
- [ ] Se nessuno score esiste → non modifica niente, logga e attende
- [ ] Se score è stale (>5 min) → logga warning, usa comunque
- [ ] Calcola parametri interpolati correttamente (non step function)
- [ ] Parametri rispettano range min/max assoluti
- [ ] Cooldown: se Board ha toccato un parametro <24h fa, Sherpa lo salta
- [ ] Cooldown: dopo 24h, Sherpa riprende il controllo

### Sherpa — DRY_RUN mode (deploy iniziale)

- [ ] `SHERPA_MODE=dry_run` è il default (non serve settare nulla per partire in dry_run)
- [ ] In DRY_RUN, `bot_config` NON viene mai toccato (verificare con query prima/dopo)
- [ ] Ogni proposta viene scritta in `sherpa_proposals` con tutti i campi compilati
- [ ] `would_have_changed` è `true` solo se almeno un parametro proposto ≠ corrente
- [ ] Notifica Telegram con prefisso `[DRY_RUN]` solo quando `would_have_changed = true`
- [ ] Evento `SHERPA_PROPOSAL` loggato in `bot_events_log`

### Sherpa — LIVE mode (post Board approval)

- [ ] `SHERPA_MODE=live` attiva la scrittura in `bot_config`
- [ ] Scrive in `bot_config` solo se il valore è diverso dal corrente
- [ ] Logga ogni modifica in `config_changes_log` con `changed_by = 'sherpa'`
- [ ] Evento `SHERPA_ADJUSTMENT` loggato in `bot_events_log`
- [ ] Notifica Telegram quando modifica parametri

### Integrazione

- [ ] Orchestrator lancia Sentinel e Sherpa come processi managed
- [ ] Se Sentinel crasha, Sherpa usa ultimo score noto
- [ ] Se Sherpa crasha, Grid continua con parametri correnti
- [ ] Se entrambi crashano, Grid continua invariato
- [ ] Orchestrator riavvia Sentinel/Sherpa dopo crash

---

## File da creare

| File | Azione |
|------|--------|
| `bot/sentinel/__init__.py` | CREATE |
| `bot/sentinel/main.py` | CREATE |
| `bot/sentinel/price_monitor.py` | CREATE |
| `bot/sentinel/funding_monitor.py` | CREATE |
| `bot/sentinel/score_engine.py` | CREATE |
| `bot/sentinel/inputs/__init__.py` | CREATE |
| `bot/sentinel/inputs/binance_btc.py` | CREATE |
| `bot/sentinel/inputs/binance_funding.py` | CREATE |
| `bot/sherpa/__init__.py` | CREATE |
| `bot/sherpa/main.py` | CREATE |
| `bot/sherpa/parameter_rules.py` | CREATE |
| `bot/sherpa/config_writer.py` | CREATE |
| `bot/sherpa/cooldown_manager.py` | CREATE |

## File da modificare

| File | Azione | Cosa |
|------|--------|------|
| `bot/orchestrator.py` | MODIFY | Aggiungere lancio Sentinel e Sherpa come processi managed |

## File da NON toccare

- `bot/strategies/grid_bot.py` — Grid legge già da `bot_config`, non serve nessuna modifica
- `bot/trend_follower/*` — TF è indipendente da Sentinel Sprint 1
- `config/settings.py` — nessun parametro manuale da aggiungere
- `web/*` — nessuna modifica dashboard in Sprint 1

---

## DB migration da eseguire

La migration crea `sentinel_scores` + `sherpa_proposals`. **Usare Supabase MCP** (non farlo a mano):

```sql
-- Tabella sentinel_scores (Brief Sentinel Sprint 1)
CREATE TABLE sentinel_scores (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    score_type text NOT NULL,
    risk_score integer NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    opportunity_score integer NOT NULL CHECK (opportunity_score >= 0 AND opportunity_score <= 100),
    btc_price numeric,
    btc_change_1h numeric,
    btc_change_24h numeric,
    funding_rate numeric,
    raw_signals jsonb,
    notes text
);

CREATE INDEX idx_sentinel_scores_type_created 
ON sentinel_scores (score_type, created_at DESC);

ALTER TABLE sentinel_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sentinel_scores_select" ON sentinel_scores FOR SELECT TO anon USING (true);
CREATE POLICY "sentinel_scores_insert" ON sentinel_scores FOR INSERT TO anon WITH CHECK (true);

-- Tabella sherpa_proposals (DRY_RUN counterfactual tracker)
CREATE TABLE sherpa_proposals (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now(),
    symbol text NOT NULL,
    risk_score integer NOT NULL,
    opportunity_score integer NOT NULL,
    current_buy_pct numeric,
    current_sell_pct numeric,
    current_idle_reentry_hours numeric,
    proposed_buy_pct numeric,
    proposed_sell_pct numeric,
    proposed_idle_reentry_hours numeric,
    proposed_regime text,
    cooldown_active boolean DEFAULT false,
    cooldown_parameters text[],
    would_have_changed boolean NOT NULL,
    btc_price numeric
);

CREATE INDEX idx_sherpa_proposals_symbol_created 
ON sherpa_proposals (symbol, created_at DESC);

CREATE INDEX idx_sherpa_proposals_changed
ON sherpa_proposals (would_have_changed, created_at DESC);

ALTER TABLE sherpa_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sherpa_proposals_select" ON sherpa_proposals FOR SELECT TO anon USING (true);
CREATE POLICY "sherpa_proposals_insert" ON sherpa_proposals FOR INSERT TO anon WITH CHECK (true);
```

**NOTA:** la migration va eseguita da Claude (CEO) via Supabase MCP, non da CC. CC deve solo leggere/scrivere dalle tabelle.

---

## Regole CC (dal Board)

- **Multifile da giorno zero.** Niente monoliti. Un modulo per responsabilità.
- **Direct push to main.** No PR, no feature branch. Se qualcosa si rompe → `git revert`.
- **Ogni commit aggiorna la roadmap** se impattata.
- **Sentinel e Sherpa sono processi separati.** Mai fonderli.
- **Attivare venv** prima di qualsiasi operazione: `source venv/bin/activate`
- **DRY_RUN è il default.** Sherpa parte in `dry_run` senza bisogno di configurazione. Lo switch a `live` avviene solo con variabile d'ambiente `SHERPA_MODE=live` e conferma Board.
- **CC può deployare e avviare subito** — in DRY_RUN non tocca nulla dei Grid bot.

---

## Dopo Sprint 1

Sprint 2 aggiungerà:
- Slow loop (Fear & Greed Index + CMC BTC dominance/market cap/volume)
- Regime detection (bull/bear/lateral) basato su slow signals
- Il mapping parametri attuale (solo fast) diventa il "layer di aggiustamento" sopra la base del regime

Sprint 3 aggiungerà:
- News feed (CryptoPanic e/o CMC content)
- Classificazione LLM (Haiku) delle news
- Score combinato fast + slow + news
