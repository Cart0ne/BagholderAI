# Sessione 81 — Brief 81a Sherpa Sprint 2: per-coin rules + slow-loop gate + amplitude cap

**Data:** 2026-05-22
**Esito:** SHIPPED (codice + test). Mac Mini restart **PENDING** — Sherpa DRY_RUN, niente urgenza.
**Suite test:** 121/121 verdi (90 baseline + 31 nuovi).
**Brief:** archiviato in `briefresolved.md/brief_81a_sherpa_sprint2.md`.

---

## 1. Riassunto in una riga

Sherpa adesso è **coin-aware** (BONK riceve `sell_pct` ~2× di BTC), legge **solo lo slow loop** (regime ogni 4h, niente fast-flicker), e **non può più raddoppiare/dimezzare** un parametro in un colpo (cap 30%).

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

---

## 6. Cosa NON è stato fatto e perché

- **Restart Mac Mini**: non eseguito. Sherpa è in DRY_RUN, il cambio entra a runtime solo dopo restart, ma non c'è urgenza operativa (Sherpa non scrive `bot_config`). Da raggruppare con eventuali altri restart pending (UTM signatures di S80 ancora non applicate).
- **Backfill `sherpa_proposals` pre-Sprint 2**: i 23.603 row analizzati nella Brain Analysis restano col formato Sprint 1. Nessun problema per la seconda Brain Analysis: il taglio temporale sarà "post-restart S81".
- **Audit Area 2** (cadenza superata): brief separato, già flaggato in S78/S79/S80/S80a. Non bloccante.

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

1. ✅ Sherpa rule engine aggiornato con i 3 blocchi
2. ✅ `SHERPA_MODE=dry_run` invariato
3. ✅ 31 test nuovi (vs ≥3 minimi del brief)
4. 🟡 `PROJECT_STATE.md` da aggiornare (faccio nello stesso commit)
5. ✅ Piano italiano consegnato e approvato prima del codice

---

## 10. ⚠️ Audit cadenze (CLAUDE.md §[1])

- **Area 1** (tecnica): ultimo 2026-05-07 (15gg), entro cadenza 30gg ✅
- **Area 2** (coerenza progetto): MAI eseguito — **DOVUTO**, flaggato in S78/S79/S80/S80a senza follow-up
- **Area 3** (marketing): ultimo 2026-05-15 (7gg), entro cadenza 90gg ✅

Proposta: pianificare Audit Area 2 (fresh CC, brief `audits/audit_request_YYYYMMDD_project_consistency.md`) in una sessione di "respiro" post-S81 — durante l'osservazione 7-10gg Sherpa DRY_RUN, mentre raccogliamo dati per la seconda Brain Analysis. ~30-45min.
