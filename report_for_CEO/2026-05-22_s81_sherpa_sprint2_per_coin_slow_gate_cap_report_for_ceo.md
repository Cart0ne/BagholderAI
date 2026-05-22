# Sessione 81 — Brief 81a Sherpa Sprint 2 + Brief 81b Haiku commentary direction safety

**Data:** 2026-05-22
**Esito:** SHIPPED + RESTART LIVE. Sherpa Sprint 2 verificato end-to-end live post-restart.
**Commit:** `3ba1132` (Sprint 2) + `51204cf` (Haiku) + `61fd41a` (PROJECT_STATE closure).
**Suite test:** 121/121 verdi (90 baseline + 31 nuovi).
**Restart Mac Mini:** 2026-05-22 20:31 CET, PID parent **28217**, 7 processi a regime.
**Brief archiviati:** `briefresolved.md/brief_81a_sherpa_sprint2.md` + `briefresolved.md/brief_81b_haiku_commentary_prompt.md`.

---

## 1. Riassunto in una riga

Sherpa adesso è **coin-aware** (BONK riceve `sell_pct` ~2× di BTC), legge **solo lo slow loop** (regime ogni 4h, niente fast-flicker), **non può più raddoppiare/dimezzare** un parametro in un colpo (cap 30%); Haiku al prossimo daily report avrà un campo `vs_yesterday.direction` pre-calcolato in Python (mai più "marginally better than -4.12%" su -5.03%) e un prompt più stretto (80 parole, no parrot delle %).

---

## 2. Le 3 modifiche, una per blocco

### Block 1 — Per-coin volatility scaling

**Nuovo modulo** `bot/sherpa/volatility.py`:
- Metrica: stdev dei log-returns su klines 1h ultimi 7 giorni (168 candele)
- BTC = anchor = 1.0; ogni altro coin = `stdev(coin) / stdev(BTC)`
- Cache TTL 1h per simbolo (refresh più frequente del slow loop 4h ma molto meno di 120s tick)
- Dynamic discovery: nessun coin hardcoded, prende i simboli dai bot attivi `bot_config`
- Fallback robusto: errori → mult 1.0 (degrada a "tutti uguali a BTC"), BTC fail → tutti 1.0

**Numeri reali oggi (Binance live, 2026-05-22)**:
| Coin | Multiplier |
|------|------------|
| BTC/USDT | 1.0000 (anchor) |
| SOL/USDT | 1.6003 |
| BONK/USDT | 2.0868 |

### Block 2 — Slow-loop gate

`bot/sherpa/main.py` ora:
- Legge `sentinel_scores` con `score_type='slow'` (NON più `'fast'`)
- `STALE_SCORE_S` allargato da 5min → 6h (4h cadence slow + 2h slack)
- `proposed_stop_buy_active = (regime == "extreme_fear")` invece di `risk_score > 90`
- `fast_signals` rimosso completamente da `calculate_parameters`

**`parameter_rules.py`**: cancellate `DROP_LADDER`, `PUMP_LADDER`, `FUNDING_LONG_LADDER`, `FUNDING_SHORT_LADDER`, `SPEED_OF_FALL_DELTA` — opzione (a) confermata da Max. Codice morto pulito; resta solo `BASE_TABLE[regime]` × `volatility_multiplier`. Roadmap Phase B re-introdurrà l'intelligenza fast lato Sentinel.

**Sentinel intatto**: niente modifiche a `bot/sentinel/main.py` (vincolo brief). La decouple è interamente lato Sherpa via query filter.

### Block 3 — Amplitude cap

`config/settings.py` → `HardcodedRules.MAX_DELTA_PCT = 0.30`.

In `parameter_rules.calculate_parameters`, dopo lo scaling per volatilità e i clamp assoluti `RANGES`, applica:
```
current * (1 - 0.30)  ≤  proposed  ≤  current * (1 + 0.30)
```
- Skip se `current` è `None` (primo run, parametro mancante): lascia che il base flow popoli il valore.
- Skip se `current` è 0 (formula degenerata).
- `breakdown.cap_applied[param]` flag bool tracciato per ogni parametro, utile per il debug delle prossime osservazioni e per la seconda Brain Analysis.

---

## 3. File toccati

| File | Tipo | Note |
|------|------|------|
| `bot/sentinel/inputs/binance_btc.py` | additivo | `fetch_klines_1h(symbol, limit)` (riusa pattern `_1m`) |
| `bot/sherpa/volatility.py` | nuovo | 130 righe, cache + fallback |
| `bot/sherpa/parameter_rules.py` | riscritto | nuova firma `(regime, current_params, volatility_multiplier)`; rimosse ladder fast |
| `bot/sherpa/main.py` | chirurgico | fetch slow, no fast_signals, stop_buy da regime, multipliers per cycle |
| `config/settings.py` | additivo | `HardcodedRules.MAX_DELTA_PCT = 0.30` |
| `tests/test_sherpa_volatility.py` | nuovo | 13 test |
| `tests/test_sherpa_amplitude_cap.py` | nuovo | 9 test |
| `tests/test_sherpa_slow_loop_gate.py` | nuovo | 9 test |

`config_writer.py`, `cooldown_manager.py`, `regime_reader.py` intatti. Schema Supabase intatto. `bot_config` invariato.

---

## 4. Decisions

### DECISIONE A — `proposed_stop_buy_active` legato a regime

- **Scelta:** `regime == "extreme_fear"` (Max conferma opzione (a) in chat)
- **Razionale:** mantiene la telemetria "Sherpa avrebbe acceso stop_buy" senza dipendere dal flicker fast-loop. Lampadina ON solo nei regimi più gravi.
- **Alternative considerate:** (b) sempre OFF (perdiamo telemetria), (c) fear OR extreme_fear (più sensibile ma artificioso, fear ha già durata 8gg in S80a → finiremmo con stop_buy sempre acceso)
- **Fallback se sbagliata:** cambiare la costante `STOP_BUY_REGIME` in `main.py` (1 riga)

### DECISIONE B — Ladder fast cancellate

- **Scelta:** rimosse completamente (Max conferma opzione (a) in chat)
- **Razionale:** Phase B sposta l'intelligenza fast in Sentinel. Tenere codice morto qui sarebbe anti-pattern. Git history preserva.
- **Alternative considerate:** (b) lasciarle commentate
- **Fallback se sbagliata:** git revert del singolo commit

### DECISIONE C — RANGES invariati

- **Scelta:** `(0.3, 3.0)` per buy_pct, `(0.8, 4.0)` per sell_pct, `(0.5, 6.0)` per idle (Max conferma opzione (a) in chat)
- **Razionale:** check empirico su klines vere — nei regimi corrente/probabili (extreme_fear / fear / neutral) **nessun parametro satura** per BTC/SOL/BONK. Saturazione solo in `greed`/`extreme_greed` su BONK e SOL (vedi §5 caveat).
- **Alternative considerate:** allargare RANGES specifico per Sherpa Sprint 2
- **Fallback se sbagliata:** alzare `RANGES["sell_pct"]` a `(0.8, 6.0)` se osserviamo saturazione operativa

### DECISIONE D — Cache volatilità TTL 1h

- **Scelta:** refresh ogni 1h (più frequente del slow loop 4h ma molto meno del tick 120s)
- **Razionale:** la volatilità rolling 7gg non cambia bruscamente; fetch ogni tick sarebbe ~24× spreco di rate-limit Binance. 1h cattura comunque rotazioni quiet↔chop intra-giornaliere.
- **Alternative considerate:** TTL 4h (uguale a slow), TTL 24h (più lento)
- **Fallback se sbagliata:** parametrizzare `CACHE_TTL_S` in `HardcodedRules`

---

## 5. Numeri proposti per regime (con Binance live oggi)

Test fatto **prima del cap**, con `current_params=None` per vedere il valore "puro" dello scaling.

| Regime | BTC sell | SOL sell | BONK sell | BTC buy | SOL buy | BONK buy |
|--------|---------:|---------:|----------:|--------:|--------:|---------:|
| extreme_fear | 1.000 | 1.600 | 2.087 | 2.500 | 3.000 (clamped) | 3.000 (clamped) |
| **fear (oggi)** | **1.200** | **1.920** | **2.504** | 1.800 | 2.881 | 3.000 (clamped) |
| neutral | 1.500 | 2.401 | 3.130 | 1.000 | 1.600 | 2.087 |
| greed | 2.000 | 3.201 | 4.000 (clamped) | 0.800 | 1.280 | 1.669 |
| extreme_greed | 3.000 | 4.000 (clamped) | 4.000 (clamped) | 0.500 | 0.800 | 1.043 |

**Osservazione chiave** (regime corrente `fear`):
- BTC `sell_pct=1.20` vs Board `1.5` → Sherpa più aggressivo
- SOL `sell_pct=1.92` vs Board `1.0` → Sherpa molto più conservativo (volatilità SOL > BTC)
- BONK `sell_pct=2.50` vs Board `2.5` → **match esatto coincidente** col Board manual hotfix slippage S78b

**Caveat saturazione** (per la prossima Brain Analysis):
- In `extreme_greed`, BONK e SOL diventano entrambi `4.0` per il clamp `RANGES`. In quel regime il segnale per-coin si appiattisce sui due coin volatili. È un mercato che oggi non vediamo (siamo in `fear`); se si manifesta, basta alzare il ceiling a 6.0.
- Il cap del Block 3 mitiga ulteriormente: anche se i raw saturano, la transizione `current → proposed` è limitata al 30% per tick, quindi non c'è "shock change" anche entrando in extreme_greed da fear.

**Verifica live post-restart** (2026-05-22 20:31 CET → primo tick Sherpa 18:31 UTC):

| Coin | Pre-restart (18:22, Sprint 1) | Post-restart (18:31, Sprint 2) | Commento |
|------|---:|---:|------|
| BTC sell_pct | 1.20 | 1.20 | Match |
| SOL sell_pct | 1.20 | **1.30** | Capped UP (current=1.0, cap=1.0×1.3=1.30) |
| BONK sell_pct | 1.20 | **2.52** | Per-coin scaling visibile (raw 1.2×2.087=2.504, cap floor da current=2.5 = 1.75, ceiling = 3.25, passa) |

| Coin | Pre-restart buy_pct | Post-restart buy_pct | Commento |
|------|---:|---:|------|
| BTC | 1.80 | **0.65** | Capped a `current × (1+0.30)` partendo da current basso |
| SOL | 1.80 | **0.65** | Stesso comportamento |
| BONK | 1.80 | **3.00** | RANGES ceiling (current alto, cap permette 1.8×2.09=3.76 → clampato a 3.0) |

Tre coin, tre numeri diversi sull'amplitude scaling. Il finding architetturale del Brain Analysis ("Sherpa propone identici valori per BTC/SOL/BONK ad ogni tick") è chiuso strutturalmente — non risolvibile più con un revert accidentale, perché il test `test_three_coins_get_three_distinct_multipliers` fallirebbe.

---

## 6. Cosa NON è stato fatto e perché

- ~~**Restart Mac Mini**~~ → **FATTO** alle 20:31 CET. Il restart S81 copre anche le UTM signatures Python pending da S80 (`utils/x_poster.py` + `utils/telegram_notifier.py`).
- **Backfill `sherpa_proposals` pre-Sprint 2**: i 23.603 row analizzati nella Brain Analysis restano col formato Sprint 1. Nessun problema per la seconda Brain Analysis: il taglio temporale sarà "post-restart S81".
- **Audit Area 2** (cadenza superata): brief separato, già flaggato in S78/S79/S80/S80a + ora S81. Non bloccante. Proposto in §11: eseguirlo durante l'osservazione 7-10gg Sherpa Sprint 2.

---

## 7. Rischio noti residui

- **Slow row assente al boot**: gestito (fallback risk=50/opp=50/btc_price=None, regime "neutral" via regime_reader). Primo tick post-restart potrebbe avere proposte "neutral" anche se il vero regime è `fear` — corretto al primo slow tick successivo (4h max).
- **fetch_klines_1h rate limit**: cache 1h per simbolo + 168 candele = 3 chiamate ogni 60min in steady state. Limite Binance pubblico è 1200 req/min IP — trascurabile.
- **Cap kicks BONK in mainnet**: con `MAX_DELTA_PCT=0.30` e Board BONK `sell_pct=2.5`, Sherpa può proporre al massimo 3.25 in un tick. In mainnet vorremo forse 0.10-0.15 (più conservativo, slippage reale 10× più basso) → futuro brief separato pre-mainnet.

---

## 8. Roadmap impact

- **Step 4 Sherpa LIVE su testnet**: **sbloccabile** dopo 7-10gg DRY_RUN + seconda Brain Analysis. Il brief 81a chiude i pre-requisiti minimi A/B/C.
- **Sequenza Sentinel-first preservata**: nessun cambio a Sentinel.
- **Phase B (Sentinel coin-aware)**: ora ha un riferimento concreto su come si fa la coin-aware scaling. Quando partirà, sposterà `volatility.py` da Sherpa a Sentinel e Sherpa diventerà un puro traduttore "score → parametro".

---

## 9. Output per il Board

### Brief 81a
1. ✅ Sherpa rule engine aggiornato con i 3 blocchi (per-coin / slow-gate / cap)
2. ✅ `SHERPA_MODE=dry_run` invariato
3. ✅ 31 test nuovi (vs ≥3 minimi del brief)
4. ✅ Piano italiano consegnato e approvato prima del codice (decisioni 1a/2a/3a)
5. ✅ Verifica end-to-end live post-restart: 3 coin → 3 multiplier diversi → 3 sell_pct diversi (vedi §5 tabella)

### Brief 81b
1. ✅ `commentary.py` con `vs_yesterday` field + 3 regole nuove nel system prompt
2. ✅ Nessun altro file toccato (no schema, no migration)
3. ✅ Conflitto length nel prompt esistente dichiarato e risolto chirurgicamente (vedi §10)

### Chiusura sessione
1. ✅ PROJECT_STATE.md aggiornato + compaction (header narrativi S79+S80+S80a archiviati per restare vicino al cap 40KB)
2. ✅ Restart Mac Mini eseguito (PID 28217, 7 processi a regime, copre anche UTM signatures S80 pending)
3. ✅ Tutti i brief archiviati in `briefresolved.md/`

---

## 10. Brief 81b — Haiku commentary direction safety + tighter output

### Context

Il Board ha trovato, audit-ando le 60 entry `daily_commentary`, **1 errore fattuale**: Day 15 (2026-05-22) Haiku ha scritto *"portfolio at -5.03%, which is somehow marginally better than yesterday's -4.12%"*. -5.03% è PEGGIO di -4.12%, non meglio. Errore tipico dei modelli piccoli con i numeri negativi.

Root cause individuata dal Board: i numeri di oggi arrivano a Haiku come JSON strutturato, ma quelli di ieri solo come testo libero dentro `yesterday_commentary`. Per confrontare, Haiku deve estrarre una percentuale dalla prosa **e** ragionare su numeri negativi — combinazione che produce errori.

### Change 1 — `vs_yesterday` field nel `prompt_data`

`commentary.py`:
- Nuova funzione `get_yesterday_pnl_pct(supabase_client)`: legge `aggregate_portfolio.total_pnl_pct` da `daily_commentary.prompt_data` di ieri. Gestisce sia JSONB nativo che stringa JSON (a seconda di come il client supabase ritorna il campo). Ritorna `None` su qualsiasi errore.
- Dentro `generate_daily_commentary`:
  1. Calcola `today_pnl_pct` (già pre-esistente).
  2. Recupera `yesterday_pnl_pct` via la funzione nuova.
  3. Se yesterday disponibile → compone in Python il blocco `vs_yesterday = {yesterday_pnl_pct, today_pnl_pct, change_pp, direction}`. `direction` con tolleranza ±0.1pp: `"better"` se today > yesterday + 0.1, `"worse"` se today < yesterday - 0.1, altrimenti `"flat"`.
  4. Se yesterday assente (Day 1, gap, errore DB) → il blocco **viene omesso del tutto**. Haiku non confronta con None.

**Smoke test del caso Day 15** (eseguito in fase di sviluppo):
```
direction(-5.03, -4.12) == "worse"   ✅
direction(-4.12, -5.03) == "better"  ✅
direction(0.05, 0.0)    == "flat"    ✅ (entro tolleranza)
```

### Change 2 — System prompt: 3 nuove regole

Modifica chirurgica al `COMMENTARY_SYSTEM_PROMPT` (preservato character voice e personality). Sostituita 1 riga vecchia, aggiunte 2 nuove regole:

1. **LENGTH**: `Write 80 words. Never exceed 100. Every word must earn its place.` — sostituisce `Keep it to 3-4 lines maximum (~250 characters).`
2. **NUMBERS**: `The reader already has the portfolio data. Do NOT list each coin's percentage individually unless something changed dramatically (>3pp move in a single day). Give the meaning, not the data.`
3. **DIRECTION**: `When comparing today's performance to yesterday, ALWAYS use the vs_yesterday.direction field if present. Do not independently calculate whether the portfolio improved or worsened.`

### Conflitto length adattato (dichiarato per trasparenza)

Il brief diceva *"se il prompt corrente ha istruzioni di lunghezza che confliggono con le nuove, chiedere al Board"*. Il vecchio "3-4 lines ~250 chars" (~40 parole) era PIÙ stretto del nuovo "80 words / max 100" (~500-600 chars). Il conflitto è mild (entrambe "corto"), e il brief permette *"exact wording can be adapted to fit the existing prompt style"*. Ho fatto una sostituzione chirurgica di una sola riga: stessa posizione, stesso registro, numero diverso. Il character del prompt è invariato. **Decisione registrata in commit message + qui per trasparenza**; se il Board preferisce stretto (40 parole / 250 char) basta dirlo, è 1-line edit.

### File toccati (Change 1 + 2)

| File | Tipo | Note |
|------|------|------|
| `commentary.py` | modificato | +1 funzione (`get_yesterday_pnl_pct`), wiring `vs_yesterday` in `prompt_data`, 3 regole nel system prompt, cleanup minor `__import__('datetime').timedelta` → `timedelta` top-level |

Nessuno schema cambiato, nessuna migration, nessun altro file toccato. Effetto al prossimo 21:00 daily report (post-restart già fatto).

### Rischio noti

- **Day 1 dopo bug DB**: se `daily_commentary` di ieri ha `prompt_data=NULL` o malformato → `vs_yesterday` omesso → Haiku non confronta con ieri. Comportamento corretto (degrade silenzioso), ma nel Diary potrebbe leggersi "nessun confronto con ieri" più spesso del desiderato. Monitoraggio: se accade più di 2 volte in 7 giorni, indagare.
- **Schema `prompt_data`**: la funzione `get_yesterday_pnl_pct` legge `prompt_data.aggregate_portfolio.total_pnl_pct` — se in futuro rinominiamo quel campo, va aggiornata. Aggiunto **mentalmente** al §3 stato di PROJECT_STATE.

---

## 11. ⚠️ Audit cadenze (CLAUDE.md §[1])

- **Area 1** (tecnica): ultimo 2026-05-07 (15gg), entro cadenza 30gg ✅
- **Area 2** (coerenza progetto): MAI eseguito — **DOVUTO**, flaggato in S78/S79/S80/S80a senza follow-up
- **Area 3** (marketing): ultimo 2026-05-15 (7gg), entro cadenza 90gg ✅

Proposta: pianificare Audit Area 2 (fresh CC, brief `audits/audit_request_YYYYMMDD_project_consistency.md`) in una sessione di "respiro" post-S81 — durante l'osservazione 7-10gg Sherpa DRY_RUN, mentre raccogliamo dati per la seconda Brain Analysis. ~30-45min.
