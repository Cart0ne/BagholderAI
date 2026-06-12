Brief S103a — sherpa-board-params — 2026-06-12

Basato su: PROJECT_STATE.md e BUSINESS_STATE.md letti da PK in data odierna.
Decisione Board S103: i 4 parametri "Board-only" diventano Sherpa-managed
con la stessa logica degli altri (regime change → write, cooldown 24h su
override manuale). Ownership: Board controlla ancora allocation, $/trade,
skim. I 4 parametri protettivi sono strategia operativa → Sherpa.

---

## Contesto

Sherpa oggi scrive 3 parametri in `bot_config` al cambio regime:
`buy_pct`, `sell_pct`, `idle_reentry_hours`.

Ora deve scrivere anche 4 parametri aggiuntivi:
`stop_buy_drawdown_pct`, `stop_buy_unlock_hours`, `dead_zone_hours`,
`min_profit_pct` (quest'ultimo = 0 in tutti i regimi, presente per
completezza e per futura attivazione senza refactor).

---

## Design: BOARD_TABLE + volatility tiers

A differenza di buy_pct/sell_pct (scala continua × multiplier), questi
4 parametri usano valori discreti (interi) e non si prestano a scaling
continuo. Si usa un sistema a **3 fasce di volatilità**:

| Tier | Condizione                  | Coin di riferimento |
|------|-----------------------------|---------------------|
| LOW  | volatility_multiplier < 1.3 | BTC (mult ~1.0)     |
| MID  | 1.3 ≤ multiplier < 1.65    | SOL (mult ~1.53)    |
| HIGH | multiplier ≥ 1.65          | BONK (mult ~1.75)   |

Le soglie sono i punti medi tra i multiplier attuali delle 3 coin.
Una nuova coin si classifica automaticamente per tier dal suo
multiplier calcolato da `volatility.py`.

### BOARD_TABLE — valori per (regime, tier)

Formato: `stop_buy_dd / stop_buy_unlock_h / dead_zone_h / min_profit`

| Regime         | LOW (BTC-like) | MID (SOL-like) | HIGH (BONK-like) |
|----------------|----------------|----------------|-------------------|
| extreme_fear   | 3 / 12 / 2 / 0 | 4 / 12 / 2 / 0 | 5 / 12 / 2 / 0  |
| fear           | 4 / 6 / 1 / 0  | 5 / 6 / 1 / 0  | 6 / 6 / 1 / 0   |
| neutral        | 1 / 2 / 2 / 0  | 2 / 2 / 2 / 0  | 2 / 1 / 2 / 0   |
| greed          | 1 / 2 / 2 / 0  | 1 / 2 / 2 / 0  | 1 / 1 / 2 / 0   |
| extreme_greed  | 1 / 2 / 3 / 0  | 1 / 2 / 3 / 0  | 1 / 1 / 3 / 0   |

Logica strategica dietro i numeri:
- **stop_buy_dd**: più alto in fear/extreme_fear (dare spazio all'accumulo
  in panico); scalato per tier (coin volatili hanno drawdown normali più ampi)
- **stop_buy_unlock_h**: 12h in extreme_fear come valvola anti-deadlock,
  6h in fear, 2h/1h in mercati positivi (1h per HIGH perché coin volatili
  rimbalzano/crollano più in fretta)
- **dead_zone_h**: bassa in fear (1h: resetta la ladder veloce), media in
  neutral/greed (2h), alta in extreme_greed (3h: non resettare durante un pump)
- **min_profit_pct**: 0 ovunque (il sell_pct già gestisce la soglia profitto;
  tenere la colonna per futura attivazione senza refactor)

---

## Cosa deve fare CC

### 1. Nuova tabella in parameter_rules.py (o file dedicato)

Creare `BOARD_TABLE` e `VOLATILITY_TIERS` con i valori sopra.
Funzione `calculate_board_parameters(regime, volatility_multiplier)`
che ritorna il dict dei 4 parametri. Nessun amplitude cap su questi
parametri (sono valori discreti interi, il cap sarebbe rumore).
Nessun clamp — i valori sono già nel range sensato.

### 2. Sherpa main loop: scrivere 7 parametri invece di 3

In `main.py`, dopo aver calcolato i 3 parametri Sherpa esistenti,
chiamare `calculate_board_parameters()` e scrivere i 4 risultati
aggiuntivi in `bot_config` (se SHERPA_MODE=live).

Il cooldown 24h si applica identico: se il Board tocca manualmente
uno di questi 4 dalla dashboard, Sherpa non lo sovrascrive per 24h.
Riutilizzare `cooldown_manager.py` senza modifiche — già generico
(controlla `changed_by != 'sherpa'`).

### 3. sherpa_proposals: loggare anche i Board params

Aggiungere colonne a `sherpa_proposals` per i 4 parametri proposti
(proposed_stop_buy_dd, proposed_stop_buy_unlock_h, proposed_dead_zone_h,
proposed_min_profit_pct) + i corrispondenti current_* per audit.
Aggiungere anche `volatility_tier` (text: 'LOW'/'MID'/'HIGH') per
tracciabilità.

**Questo richiede una migration Supabase.** CC la propone nel piano,
il Board (Max) la approva prima dell'esecuzione.

### 4. Dashboard: separazione visiva

Nella tabella "Last proposals" di `/admin`, separare visivamente:
- Riga superiore: parametri Sherpa (buy / sell / idle) — come oggi
- Riga inferiore: parametri Board (stop_dd / unlock / dead_zone / min_profit)

Stessa logica di colori (⚠ diff, 🔒 cooldown, ✓ aligned).

### 5. Default per nuove coin

Quando una nuova coin entra in `bot_config` (via TF o manualmente),
Sherpa al primo tick:
1. Calcola il volatility_multiplier
2. Determina il tier (LOW/MID/HIGH)
3. Scrive tutti e 7 i parametri secondo regime corrente + tier

Non serve logica speciale — è il comportamento standard se `current`
per quei parametri è NULL (Sherpa popola al primo giro).

---

## Decisioni delegate a CC

- Dove mettere BOARD_TABLE: nello stesso `parameter_rules.py` o in file
  separato `board_parameter_rules.py` — CC decide in base a leggibilità
- Nomi esatti delle colonne migration (CC propone nel piano)
- Gestione del caso `min_profit_pct` = 0 fisso: se CC preferisce un
  semplice hardcode 0 senza lookup, va bene

## Decisioni che CC DEVE chiedere

- Schema della migration Supabase (nuove colonne su sherpa_proposals)
- Qualsiasi modifica a `config_writer.py` che cambi il formato di
  scrittura dei 3 parametri esistenti
- Se i tier boundaries (1.3, 1.65) devono vivere in settings.py o
  inline nel modulo — CC propone, Board approva

---

## Output atteso

1. Piano in italiano (task > 50 righe) — PRIMA di scrivere codice
2. Migration Supabase per le nuove colonne
3. Codice: BOARD_TABLE + calculate_board_parameters + integration in main.py
4. Dashboard aggiornata con separazione visiva
5. Report S103a con decisioni prese

## Vincoli — OFF-LIMITS

- NON modificare BASE_TABLE né RANGES dei 3 parametri Sherpa esistenti
- NON toccare `volatility.py` (il calcolo multiplier è corretto)
- NON toccare la logica Sentinel (score_engine, regime_analyzer)
- NON restartare il bot (Max restarta manualmente su Mac Mini)
- NON modificare allocation, capital_per_trade, skim_pct — restano
  Board-only, Sherpa non li legge né li scrive

## Impatto roadmap

Nessuno. Questo è backend operativo, non visibile sulla roadmap pubblica.
La separazione visiva in `/admin` è miglioramento interno.

---

## Auto-obiezione CEO

Il sistema a tier introduce una discontinuità: una coin con multiplier
1.29 prende valori LOW, a 1.31 prende MID. È un cliff. Perché lo
accettiamo: i valori target sono interi (1%, 2%, 3%...) — non c'è
precisione utile da interpolare. La discontinuità è un costo minore
rispetto alla complessità di un sistema di interpolazione continua per
valori che cambiano di 1 unità alla volta. Se in futuro aggiungiamo
coin con multiplier vicino alle soglie e il cliff crea problemi,
la fix è spostare la soglia — non rifare l'architettura.
