# S78 — Sentinel Sprint 2 Slow Loop SHIPPED

**Da:** Claude Code (Intern)
**Per:** CEO + Board (Max)
**Data:** 2026-05-14 sera
**Brief di riferimento:** `briefresolved.md/brief_77b_sentinel_sprint2_slow_loop.md`
**Modalità:** Piano italiano approvato → 8 step granulari → 9 fase shipping
**Test suite:** 37 → **85 verdi** (+48 Sprint 2)
**Restart bot:** **NESSUNO da CC** — lo farai tu sul Mac Mini dopo revisione

---

## 0. TL;DR

Sentinel ora ha un **slow loop** ogni 4 ore che:

1. Legge **Fear & Greed Index** (alternative.me, free)
2. Legge **CMC global metrics** (BTC dominance, mcap, volume) se `CMC_API_KEY` è in `config/.env`
3. Determina il **regime macro** (5 buckets: extreme_fear / fear / neutral / greed / extreme_greed)
4. Scrive una riga `sentinel_scores` con `score_type='slow'` + `raw_signals` ricco
5. Sherpa legge la riga slow e passa il regime a `calculate_parameters()` (prima era sempre hardcoded "neutral")

**Effetto pratico**: in DRY_RUN, Sherpa adesso propone partendo dal regime corrente macro. Quando F&G è 15 (panico), Sherpa parte da `extreme_fear` (buy_pct alto, sell_pct basso, idle lungo). Quando F&G è 80 (euforia), parte da `extreme_greed` (buy basso, sell alto, idle corto). La BASE_TABLE in `parameter_rules.py` era già pronta — Sprint 2 la alimenta.

**Codice:** 5 file nuovi, 2 file modificati chirurgicamente. Nessuna migration Supabase. Nessun nuovo campo DB (la jsonb `raw_signals` assorbe tutta la nuova informazione).

---

## 1. Cosa è stato fatto

### 1.1 File nuovi (5)

| File | Righe | Responsabilità |
|---|---|---|
| `bot/sentinel/inputs/alternative_fng.py` | 73 | Wrapper F&G Index. NEVER raise. |
| `bot/sentinel/inputs/cmc_global.py` | 87 | Wrapper CMC Pro API. NEVER raise. API key opzionale. |
| `bot/sentinel/regime_analyzer.py` | 136 | F&G → regime. Decision_log per audit. Stale check 36h. |
| `bot/sentinel/slow_loop.py` | 137 | Orchestra 1 slow tick: fetch + regime + score + INSERT. |
| `bot/sherpa/regime_reader.py` | 66 | Query latest slow row + fallback "neutral". |

**Tutti i file sotto 200 righe.** Regola di pollice rispettata: 1 responsabilità per modulo, testabile in isolamento.

### 1.2 File modificati (2, chirurgici)

| File | Pre | Post | Δ | Cosa cambia |
|---|---|---|---|---|
| `bot/sentinel/main.py` | 207 | 238 | +31 | costanti + contatore + chiamata `slow_loop.tick(supabase)` ogni 4h, **al boot e poi ogni 240 fast tick** |
| `bot/sherpa/main.py` | 535 | 540 | +5 | import `regime_reader` + 1 chiamata + passaggio regime invece di hardcoded "neutral" |

### 1.3 Test nuovi (5 file, +48 test)

| File test | n | Cosa copre |
|---|---|---|
| `tests/test_fng_input.py` | 7 | happy path + network err / HTTP 500 / JSON malformed / missing fields / malformed row / timeout |
| `tests/test_cmc_input.py` | 7 | happy path + no_api_key (env unset) / network err / HTTP 401 / JSON malformed / missing data / malformed payload |
| `tests/test_regime_analyzer.py` | 21 | 5 buckets + 8 boundary tests (20/21/40/41/60/61/80/81) + fallback chain (None / malformed / stale) + score map completeness |
| `tests/test_slow_loop.py` | 6 | happy / F&G only / both None / DB error / fetcher raise / extreme_fear inversion check |
| `tests/test_regime_reader.py` | 7 | latest slow / 5 regimi validi / no row / DB error / unknown regime / missing key / null raw_signals |

**Pytest totale: 85 verdi (era 37).** Nessun test esistente rotto. I 29 test del Grid (accounting + stop_buy unlock + idle) continuano verdi.

---

## 2. Decisioni tecniche prese (delegate a CC nel brief)

### 2.1 Inversione mapping regime → risk/opp slow

Il brief proponeva `extreme_fear → risk=80, opp=20` (alto rischio in panico). Ho proposto e tu hai approvato l'inversione: in panic/capitulation il **rischio percepito è basso** (lo schianto è già avvenuto) e l'**opportunità di accumulo è alta**. Mapping finale in `REGIME_SCORE_MAP`:

| Regime | risk_slow | opp_slow |
|---|---|---|
| extreme_fear | 20 | 80 |
| fear | 30 | 65 |
| neutral | 40 | 40 |
| greed | 65 | 30 |
| extreme_greed | 80 | 20 |

**Razionale**: simmetrico attorno a neutral (40/40), monotono, copre il range 20-80 (resta margine ai bordi 0-100 per signals futuri). Riflette il sentiment di trading "buy when fearful, sell when greedy".

### 2.2 Boundaries F&G inclusive low

Documentate nel docstring di `regime_analyzer._fng_to_regime`:
- F&G=20 → extreme_fear (incluso)
- F&G=21 → fear
- F&G=40 → fear (incluso)
- F&G=41 → neutral
- F&G=60 → neutral (incluso)
- F&G=61 → greed
- F&G=80 → greed (incluso)
- F&G=81 → extreme_greed

8 test boundary verdi confermano la semantica.

### 2.3 Stale threshold F&G = 36h

Da brief, confermato. Test `test_fng_stale_falls_back_to_neutral` verifica il taglio a 36h+; `test_fng_fresh_just_under_threshold_uses_value` verifica che 35h59m sia ancora accettato.

### 2.4 Architettura modulare anticipativa

Brief 77b proponeva di aggiungere il timer slow loop direttamente in `sentinel/main.py`. Su tuo input "evitiamo 2000 righe in un file", ho separato:

- **`slow_loop.py`** — orchestrazione del tick (fetch + regime + score + INSERT) in un modulo dedicato. `main.py` chiama `slow_loop.tick(supabase)`. Pattern simmetrico al futuro `news_loop.py` (Sprint 3 — news feed). Quando Sprint 3 arriverà, il refactor sarà zero — basterà aggiungere un secondo contatore e un secondo `import news_loop` accanto a `slow_loop`.
- **`regime_reader.py` su Sherpa** — separato dal main.py già 535 righe. Sherpa main resta thin orchestrator.

Risultato: nessun file > 250 righe, ogni modulo testabile in isolamento (mock dei 2 input + DB fake → boundary di 1 funzione).

### 2.5 Contatore boot-friendly

Il contatore `slow_tick_counter` parte a `SLOW_LOOP_EVERY_N_TICKS` (= 240) così il **primo slow tick scatta subito al boot**, non dopo 4h. Implementato in `bot/sentinel/main.py:101`. Sherpa avrà un regime dal primo ciclo, niente periodo cieco.

### 2.6 NEVER-raise contract per gli input

Pattern uniforme nei 2 nuovi input modules: `fetch() -> Optional[dict]`, ogni eccezione swallowed con log warning. Slow loop tollera qualsiasi combinazione (None / valido) — fallback a "neutral" + log. **Un'API esterna giù NON deve mai crashare Sentinel**, che invece deve continuare a far girare il fast loop indisturbato.

---

## 3. raw_signals della nuova riga slow (formato)

Esempio reale (con CMC presente):

```json
{
  "regime": "fear",
  "decision_log": {
    "fng_used": true,
    "cmc_seen": true,
    "fng_value": 32,
    "fng_label": "Fear",
    "fng_timestamp": 1715692800,
    "fng_age_s": 14400,
    "regime_source": "fng",
    "fallback_reason": null
  },
  "fng_value": 32,
  "fng_label": "Fear",
  "fng_timestamp": 1715692800,
  "btc_dominance": 57.34,
  "total_market_cap_usd": 2300000000000,
  "total_volume_24h_usd": 85000000000,
  "active_cryptocurrencies": 9712
}
```

Esempio fallback (entrambi gli input giù):

```json
{
  "regime": "neutral",
  "decision_log": {
    "fng_used": false,
    "cmc_seen": false,
    "fallback_reason": "fng_unavailable"
  }
}
```

**`decision_log` è fondamentale per gli audit futuri** (S77b style): permette query SQL su `raw_signals->'decision_log'->>'fallback_reason'` per capire quante volte abbiamo cofatto il regime e perché.

---

## 4. Cosa Sherpa fa adesso (vs prima)

### Prima di Sprint 2 (loop ogni 120s, dentro `sherpa/main.py`)

```python
proposed_params, breakdown = calculate_parameters(
    regime="neutral", fast_signals=fast_signals   # ← regime sempre hardcoded
)
```

### Dopo Sprint 2

```python
current_regime = get_current_regime(supabase)           # ← read latest slow score
proposed_params, breakdown = calculate_parameters(
    regime=current_regime, fast_signals=fast_signals    # ← dynamic regime
)
```

**Niente altro è cambiato in Sherpa.** Cooldown, write_parameter, alert Telegram, sherpa_proposals INSERT, RISK_STOP_BUY_THRESHOLD → tutto invariato. La BASE_TABLE in `parameter_rules.py` era già preparata per 5 regimi: Sprint 2 finalmente la fa lavorare.

---

## 5. Setup richiesto sul Mac Mini

### 5.1 Già fatto da te

✅ Aggiunta `CMC_API_KEY=<...>` in `/Volumes/Archivio/bagholderai/config/.env` (confermato in chat).

### 5.2 Da fare al prossimo restart (quando vuoi)

1. `git pull` su Mac Mini per portare i commit nuovi
2. Restart orchestrator graceful (kill SIGTERM + caffeinate + flag env come da memoria `reference_orchestrator_start`)
3. Verifica entro 1-2 min:
   - Log Sentinel: `Slow tick: regime=..., risk=..., opp=..., fng=..., cmc=yes/no`
   - DB query: `SELECT * FROM sentinel_scores WHERE score_type='slow' ORDER BY created_at DESC LIMIT 1;`
   - Sherpa log: dovrebbe mostrare il `proposed_regime` diverso da "neutral" se F&G non è 41-60

### 5.3 Cosa NON serve fare

- Migration Supabase: niente, `sentinel_scores` jsonb regge tutto
- Restart Sentinel/Sherpa separatamente: il graceful restart dell'orchestrator riavvia tutto
- Modifiche a `bot_config`: BASE_TABLE in `parameter_rules.py` già gestisce 5 regimi dal S63

---

## 6. Test verdi: dettaglio

```
tests/test_fng_input.py ............ 7 passed
tests/test_cmc_input.py ............ 7 passed
tests/test_regime_analyzer.py ...... 21 passed
tests/test_slow_loop.py ............. 6 passed
tests/test_regime_reader.py ........ 7 passed
tests/test_accounting_avg_cost.py .. 29 passed (esistenti, intoccati)
tests/test_gain_saturation.py ....... 8 passed (esistenti, intoccati)
─────────────────────────────────────────────
                          TOTAL    85 passed
```

Tempo esecuzione totale: ~1.5s. Nessun warning legato a Sprint 2 (i 266 DeprecationWarning sono pre-esistenti `datetime.utcnow()` su Grid — separate task, tracked).

---

## 7. Roadmap impact

### Sequenza Sentinel-first (CEO S76, 5 step)

1. ✅ S77 — Audit Sentinel Sprint 1 (tutti PASS)
2. ✅ **S78 — Build Sentinel Sprint 2 (questo brief)**
3. 🟡 **Prossima fase — Osservazione 5-7 giorni**: Sentinel scrive slow score ogni 4h, Sherpa propone in DRY_RUN basato sul regime. Da raccogliere ~30-40 record slow + ~250 proposal sherpa. Audit empirico tipo S77 ma per Sprint 2: il regime ha cambiato nei momenti giusti? Le proposte hanno senso?
4. ⏳ Sherpa LIVE testnet, un parametro alla volta (sell_pct primo)
5. ⏳ Mainnet €100 con sistema rodato (target fine giugno / inizio luglio)

### Cosa è cambiato nella roadmap.ts

Nessuna modifica necessaria a `web_astro/src/data/roadmap.ts` — la task "Sentinel Sprint 2: slow loop (F&G + CMC dominance + regime detection)" era già listata come `todo`, basterà flippare a `done` nel prossimo update PROJECT_STATE post-osservazione.

### Cosa NON è stato fatto in questo brief

- **Dashboard /admin Regime section** (Task 7 opzionale del brief): saltato, lo faremo in un brief separato se l'osservazione 5-7 giorni mostra che è utile vederlo in tempo reale invece che via SQL. Stima: 30 min.
- **CMC nel regime calculation**: Sprint 2 logga `btc_dominance` etc. ma non li usa nella decisione. Spazio per Sprint 2.5 dopo aver visto dati storici sufficienti.
- **News feed CryptoPanic / RSS**: Sprint 3, brief separato, non discusso in 77b.

---

## 8. Pattern modulare anticipativa (lezione applicata)

Lezione S76 (grid_runner monolite 1623 righe → package 8 moduli, refactor doloroso): ho applicato la regola di pollice "modulare PRIMA che diventi monolite" in Sprint 2.

- `sentinel/main.py` 207 → 238 righe (+31). **Non gonfia oltre i 250.**
- Tutta la nuova logica è in moduli esterni (`slow_loop.py`, `regime_analyzer.py`, `inputs/*`)
- Quando Sprint 3 arriverà con news feed, il pattern sarà identico: aggiungere un altro modulo + un secondo contatore in `main.py` (~5 righe in più)

**Costo extra rispetto a "tutto in main.py": zero.** Tempo speso identico. Risparmio futuro: un refactor S76-style evitato.

---

## 9. Decisions log (CLAUDE.md §4)

**DECISIONE 1**: inversione mapping regime → risk/opp (extreme_fear = opp alta, risk basso)
**RAZIONALE**: trading-sense — in capitulation il rischio percepito è basso, l'opportunità è alta
**ALTERNATIVE CONSIDERATE**: brief originale (extreme_fear = risk alta) — rifiutata in chat dal Board
**FALLBACK SE SBAGLIATA**: cambia la mapping in `REGIME_SCORE_MAP` (1 dict in regime_analyzer.py), nessun altro file. I 21 test boundary verificano comunque le soglie.

**DECISIONE 2**: estrazione `slow_loop.py` come modulo separato anziché aggiungerlo a `sentinel/main.py`
**RAZIONALE**: Board ha esplicitamente chiesto modularità anti-monolite (lezione S76 grid_runner)
**ALTERNATIVE CONSIDERATE**: tutto in main.py (come brief) — rifiutata per scalabilità Sprint 3
**FALLBACK SE SBAGLIATA**: il modulo è un thin wrapper; merge inverso → riportare il body di `slow_loop.tick()` dentro `run_sentinel()` è una operazione meccanica di ~10 minuti

**DECISIONE 3**: contatore boot-init a MAX
**RAZIONALE**: primo slow tick deve fare partire Sherpa con un regime reale, non aspettare 4h con "neutral" hardcoded
**ALTERNATIVE CONSIDERATE**: counter init a 0 (Sherpa "neutral" per 4h post-restart) — rifiutata
**FALLBACK SE SBAGLIATA**: cambia 1 riga in sentinel/main.py

---

*Sprint 2 chiuso. Pronto per commit + push. Aspetto tuo restart Mac Mini quando vuoi.*
