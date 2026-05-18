# Brief 79c — Riduzione Write IO Supabase: Write-on-Change + Heartbeat

**Date:** May 18, 2026  
**Author:** CEO (Claude)  
**Based on:** PROJECT_STATE.md aggiornato 2026-05-15 (S78 chiusura)  
**Priority:** Alta — Supabase ha inviato warning "Disk IO Budget depleting"  
**Estimated effort:** 1–1.5 ore  
**Origine idea:** Memo_Brainstorming S68 §3 ("scan fast in memory, write only on significant change")  

---

## Context

Supabase (free tier, Nano compute) ha inviato email di warning: il progetto sta esaurendo il Disk IO Budget giornaliero. Conseguenze se esaurito: response time alti, CPU in IO wait, istanza potenzialmente non responsiva.

Causa: le tre tabelle più pesanti in scrittura non hanno alcun filtro di significatività.

| Tabella | Write/giorno | Problema |
|---|---|---|
| sherpa_proposals | ~1.795 | Scrive per ogni bot ogni 120s, anche se `would_have_changed=false` |
| sentinel_scores | ~1.208 | Scrive ogni 60s, anche se risk/opp identici da ore |
| bot_state_snapshots | ~497 | Scrive ogni tick, anche se nessun valore è cambiato |

**Totale: ~3.500 write/giorno inutili in mercato piatto.**

Il principio di design è già nel Memo Brainstorming S68 §3: "High scan frequency, low write frequency." Scan veloce in memoria per crash detection, write su DB solo su cambiamento significativo.

---

## What to change

### Principio generale

Ogni componente mantiene in memoria l'ultimo record scritto su Supabase. Prima di un INSERT, confronta il nuovo record con l'ultimo scritto. Scrive solo se:
1. **Cambiamento significativo** (definito per tabella, vedi sotto), OPPURE
2. **Heartbeat** scaduto (tempo minimo tra write anche senza cambiamenti, per confermare "sono vivo")

---

### 1. Sentinel fast loop — `bot/sentinel/main.py`

**Stato attuale:** INSERT in `sentinel_scores` a ogni tick (ogni `SCAN_INTERVAL_S` = 60s).

**Modifica:**

Aggiungere variabili di stato nel loop:
```python
_last_written_risk = None
_last_written_opp = None
_last_write_ts = 0
SENTINEL_HEARTBEAT_S = 600  # 10 minuti
```

Prima dell'INSERT esistente, aggiungere guard:
```python
score_changed = (risk != _last_written_risk or opp != _last_written_opp)
heartbeat_due = (time.time() - _last_write_ts) >= SENTINEL_HEARTBEAT_S

if score_changed or heartbeat_due:
    # INSERT esistente (invariato)
    supabase.table("sentinel_scores").insert({...}).execute()
    _last_written_risk = risk
    _last_written_opp = opp
    _last_write_ts = time.time()
else:
    logger.debug("sentinel write skipped: no change (risk=%s opp=%s)", risk, opp)
```

**Scan loop NON rallentato.** Il tick ogni 60s resta identico — `price.tick()`, `funding.get_rate()`, `score()` girano normalmente. Solo la write è condizionale.

**Impatto stimato:** In mercato piatto (risk=20, opp=20 costanti), da ~1.440 write/giorno a ~144 (solo heartbeat). In mercato volatile, write salgono naturalmente.

**Attenzione slow loop:** Il slow loop scrive `score_type='slow'`, che ha un path separato (`slow_loop.py`). NON applicare questo filtro al slow loop — gira già solo ogni 4h (6 write/giorno), trascurabile.

---

### 2. Sherpa — `bot/sherpa/main.py`

**Stato attuale:** INSERT in `sherpa_proposals` per ogni bot a ogni tick (ogni `LOOP_INTERVAL_S` = 120s), con flag `would_have_changed` che indica se i parametri proposti differiscono da quelli correnti. Scrive anche quando `would_have_changed=false`.

**Modifica:**

Aggiungere variabili di stato nel loop:
```python
_last_write_ts_per_symbol: dict[str, float] = {}
SHERPA_HEARTBEAT_S = 600  # 10 minuti
```

Prima dell'INSERT per ogni bot:
```python
now = time.time()
heartbeat_due = (now - _last_write_ts_per_symbol.get(symbol, 0)) >= SHERPA_HEARTBEAT_S

if would_have_changed or heartbeat_due:
    # INSERT esistente (invariato)
    supabase.table("sherpa_proposals").insert({...}).execute()
    _last_write_ts_per_symbol[symbol] = now
else:
    logger.debug("sherpa write skipped for %s: no change", symbol)
```

**Impatto stimato:** Da ~2.160 write/giorno a ~432 (solo heartbeat per 3 bot). Quando Sherpa propone cambi reali, le write avvengono immediatamente.

---

### 3. Bot state snapshots — `bot/grid_runner/__init__.py` (o dove il snapshot viene scritto)

**Stato attuale:** INSERT in `bot_state_snapshots` a ogni tick del grid_runner per ogni bot.

**Modifica:**

CC deve prima identificare dove lo snapshot viene scritto (potrebbe essere in `grid_runner` o in `orchestrator`).

Aggiungere confronto con ultimo snapshot scritto:
```python
_last_snapshot_per_symbol: dict[str, dict] = {}
SNAPSHOT_HEARTBEAT_S = 300  # 5 minuti

def _snapshot_changed(current: dict, last: dict) -> bool:
    """True if any meaningful field changed."""
    COMPARE_KEYS = [
        "holdings", "avg_buy_price", "cash_available", 
        "unrealized_pnl", "realized_pnl_cumulative",
        "open_lots_count", "stop_loss_active", "stop_buy_active"
    ]
    return any(current.get(k) != last.get(k) for k in COMPARE_KEYS)
```

Prima dell'INSERT:
```python
last = _last_snapshot_per_symbol.get(symbol, {})
heartbeat_due = (now - last.get("_write_ts", 0)) >= SNAPSHOT_HEARTBEAT_S

if _snapshot_changed(current_snapshot, last) or heartbeat_due:
    # INSERT esistente
    ...
    _last_snapshot_per_symbol[symbol] = {**current_snapshot, "_write_ts": now}
```

**Impatto stimato:** Da ~497 write/giorno a ~864 (heartbeat 5min × 3 bot) — in realtà MENO perché in drawdown i valori non cambiano tra tick. Realismo: ~300-400/giorno.

---

## Riepilogo impatto atteso

| Tabella | Prima | Dopo (piatto) | Dopo (volatile) |
|---|---|---|---|
| sentinel_scores | ~1.440/giorno | ~144 | ~500-1.000 |
| sherpa_proposals | ~2.160/giorno | ~432 | ~800-1.500 |
| bot_state_snapshots | ~497/giorno | ~300 | ~400 |
| **Totale** | **~4.100** | **~876** | **~1.700-2.900** |

Riduzione in mercato piatto: **~80%.** In mercato volatile: **~40-55%.** Il comportamento è corretto: scriviamo di più quando succede qualcosa.

---

## Decisions delegated to CC

- Dove esattamente vivono le write di `bot_state_snapshots` (quale file/funzione)
- Se usare variabili di modulo o attributi di classe per lo stato "ultimo scritto"
- Heartbeat constants: possono essere definite come costanti di modulo o spostate in config. CC decide
- Se il confronto snapshot necessita di tolleranza numerica (es. `abs(new - old) > epsilon` per float) o basta `!=`

## Decisions CC MUST ask Board

- Se durante l'implementazione emerge che il slow loop Sentinel o altri path di scrittura critica usano lo stesso INSERT path del fast loop, FERMARSI e chiedere — non vogliamo filtrare accidentalmente le write del slow loop
- Se qualche altro componente legge `sentinel_scores` aspettandosi una riga ogni 60s (es. stale check con threshold basso), segnalare — potrebbe servire aggiustare il threshold

---

## Expected output at end of session

1. Modified `bot/sentinel/main.py` con write-on-change guard (solo fast loop)
2. Modified `bot/sherpa/main.py` con write-on-change guard
3. Modified file snapshot (identificato da CC) con write-on-change guard
4. Commit + push
5. Restart orchestrator su Mac Mini
6. Verifica dopo 30 minuti: contare righe scritte nelle 3 tabelle nel periodo, confrontare con la media pre-fix (~2.8 righe/minuto → atteso ~0.6 righe/minuto in mercato piatto)

---

## Constraints

- Do NOT modificare la frequenza di scan (il tick ogni 60s per Sentinel e 120s per Sherpa resta invariato)
- Do NOT modificare la logica di score, regime detection, o parameter calculation
- Do NOT toccare il slow loop di Sentinel (6 write/giorno, irrilevante)
- Do NOT aggiungere cron job di retention (li faremo dopo aver analizzato i dati)
- Do NOT eliminare dati esistenti
- Il heartbeat è OBBLIGATORIO — senza heartbeat, un Sentinel silenzioso per ore è indistinguibile da un Sentinel crashato. La dashboard e il monitoring si aspettano righe recenti.
- I log `debug` per "write skipped" NON devono essere `info` (altrimenti il log diventa rumore)

---

## Roadmap impact

Aggiornare PROJECT_STATE.md: "Supabase IO: write-on-change pattern attivo su sentinel_scores, sherpa_proposals, bot_state_snapshots. Heartbeat 10min/10min/5min."

---

## Test verification

Dopo restart:
1. Query `SELECT COUNT(*) FROM sentinel_scores WHERE created_at > NOW() - INTERVAL '30 minutes'` — atteso ~3 (heartbeat ogni 10 min) in mercato piatto, vs ~30 pre-fix
2. Query `SELECT COUNT(*) FROM sherpa_proposals WHERE created_at > NOW() - INTERVAL '30 minutes'` — atteso ~9 (3 bot × heartbeat 10 min), vs ~45 pre-fix
3. Forzare un cambiamento score (se possibile via test) e verificare che la write avvenga immediatamente, non al prossimo heartbeat

---

## Relazione con retention futura

Questo brief riduce il FLUSSO di write. La retention (cron job per cancellare righe vecchie) riduce lo STOCK. Servono entrambi:
- Brief 79c (questo) → riduce IO giornaliero del ~80%
- Retention (futuro, post-analisi dati) → libera spazio e riduce dimensione indici

Ordine: prima 79c (urgente, Supabase warning attivo), poi retention (quando abbiamo finito le analisi Sentinel/Sherpa).
