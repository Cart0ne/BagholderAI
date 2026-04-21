# BRIEF — Session 43: Observability v1 (events + snapshots + decisions)

**Date:** 2026-04-20 (sera, da raffinare col CEO)
**Priority:** MEDIUM — non blocca trading, ma sblocca visibilità post-hoc senza dipendenza da Telegram/SSH
**Prerequisito:** nessuno; compatibile con tutto lo stato attuale post-42a
**Target branch:** `main` (push diretto incrementale, feature-by-feature)

---

## Problema

Oggi il CEO (Claude su claude.ai) ha tre fonti per capire "cosa è successo col bot":

1. **Telegram** — push-based, passa dal filtro umano di Max (screenshot), non queryable, niente storia strutturata
2. **Log file** (`/Volumes/Archivio/bagholderai/logs/grid_*.log`) — richiede SSH + grep, formato non strutturato, sepolti in httpx chatter
3. **Tabelle `trades` / `bot_config` / `trend_decisions_log`** — strutturate ma coprono solo eventi "finanziari", non il comportamento del bot

**Manca:** una *single source of truth queryable* su "cosa ha fatto il bot / cosa stava pensando / com'era lo stato", leggibile dal CEO via semplici SELECT su Supabase all'inizio di ogni sessione.

Esempio pratico da oggi (GUN post-restart alle 17:00):
- CEO si chiede "perché GUN non ricompra?" — serve 20 min di ping-pong Max↔CEO per capire che ha holdings=0, cash $40 ma `_pct_last_buy_price` in un limbo dopo idle recalibrate
- Nessuna delle 3 fonti sopra lo dice da sola

---

## Obiettivo

Tre tabelle complementari che coprono tre domande diverse:

| Tabella | Risponde a | Granularità | Esempio query |
|---|---|---|---|
| `bot_events_log` | **COSA** è successo | Eventi discreti notevoli | "Quante volte è scattato stop-loss stanotte?" |
| `bot_state_snapshots` | **COM'ERA** lo stato | Ogni 15 min per bot | "Qual era l'avg_buy_price di CHZ alle 14:30?" |
| `decisions_trace` | **PERCHÉ** sta facendo X (o non facendo) | Continuous, dedup'd | "Perché CHZ non compra da un'ora?" |

---

## Design

### Tabella 1 — `bot_events_log`

Single source of truth per eventi discreti che il CEO vuole sapere.

```sql
CREATE TABLE bot_events_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  timestamptz NOT NULL DEFAULT now(),
  severity    text NOT NULL CHECK (severity IN ('info','warn','error','critical')),
  category    text NOT NULL CHECK (category IN ('lifecycle','trade','safety','tf','config','error')),
  symbol      text,         -- NULL per eventi globali (orchestrator)
  event       text NOT NULL,
  message     text NOT NULL,
  details     jsonb
);
CREATE INDEX ON bot_events_log(created_at DESC);
CREATE INDEX ON bot_events_log(symbol, created_at DESC);
CREATE INDEX ON bot_events_log(severity, created_at DESC) WHERE severity IN ('error','critical');
```

**Eventi al MVP (che già esistono come Telegram ma non come riga DB):**

| Evento | Severity | Category | Call-site |
|---|---|---|---|
| `orchestrator_started` | info | lifecycle | `bot/orchestrator.py` startup |
| `orchestrator_stopped` | info/critical | lifecycle | SIGTERM handler |
| `bot_started` | info | lifecycle | `grid_runner.run_grid_bot` entry |
| `bot_stopped` | info | lifecycle | `grid_runner` exit con `stop_reason` |
| `capital_exhausted` | warn | safety | transizione `_capital_exhausted=True` |
| `capital_restored` | info | safety | transizione `_capital_exhausted=False` |
| `stop_loss_triggered` | warn | safety | grid_bot linea ~1374 |
| `take_profit_triggered` | info | safety | grid_bot linea ~1377 |
| `stop_buy_activated` | warn | safety | 39b flag set |
| `stop_buy_cleared` | info | safety | 39b flag reset |
| `tf_allocate` | info | tf | allocator `apply_allocations` |
| `tf_deallocate` | info | tf | idem |
| `tf_swap` | info | tf | idem |
| `multi_lot_entry_fired` | info | tf | `_consume_initial_lots` success |
| `config_changed_bot_config` | info | config | `SupabaseConfigReader` diff detected |
| `config_changed_trend_config` | info | config | TF loop diff detected (39g) |
| `error_loop` | error | error | `grid_runner` exception handler |
| `error_log_trade` | error | error | `_execute_percentage_buy`/`_sell` fallisce INSERT |

**Helper:**
```python
# db/event_logger.py
from db.client import get_client
import logging
_logger = logging.getLogger("bagholderai.events")

def log_event(severity, category, event, message, symbol=None, details=None):
    try:
        get_client().table("bot_events_log").insert({
            "severity": severity, "category": category,
            "symbol": symbol, "event": event,
            "message": message, "details": details,
        }).execute()
    except Exception as e:
        # MUST NOT crash the bot — degraded logging is acceptable,
        # missing trades is not.
        _logger.warning(f"bot_events_log insert failed: {e}")
```

**Call-site decoration**: ~20 punti nel codice, ognuno 1-3 righe. Niente refactor invasivo.

---

### Tabella 2 — `bot_state_snapshots`

Timeline dello stato operativo di ogni bot, così "com'era X 3 ore fa" diventa una SELECT.

```sql
CREATE TABLE bot_state_snapshots (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at               timestamptz NOT NULL DEFAULT now(),
  symbol                   text NOT NULL,
  managed_by               text NOT NULL,  -- 'manual' | 'trend_follower'
  holdings                 numeric NOT NULL,
  avg_buy_price            numeric NOT NULL,
  cash_available           numeric NOT NULL,
  unrealized_pnl           numeric NOT NULL,
  realized_pnl_cumulative  numeric NOT NULL,
  open_lots_count          integer NOT NULL,
  pct_last_buy_price       numeric,
  greed_tier_pct           numeric,        -- NULL per manual bot
  greed_age_minutes        numeric,        -- NULL per manual bot
  stop_loss_active         boolean NOT NULL DEFAULT false,
  stop_buy_active          boolean NOT NULL DEFAULT false,
  last_trade_at            timestamptz
);
CREATE INDEX ON bot_state_snapshots(symbol, created_at DESC);
CREATE INDEX ON bot_state_snapshots(created_at DESC);
```

**Cadenza:** ogni 15 min, scritto dal `grid_runner` dentro il main loop:

```python
# grid_runner.py, dentro il while True, dopo il sync
if cycle % SNAPSHOT_INTERVAL_CYCLES == 0:  # es. ogni 15 cicli × 60s = 15 min
    _write_state_snapshot(bot, cfg.symbol)
```

**Query utili:**
```sql
-- Equity curve di un bot nelle ultime 24h
SELECT created_at, holdings * pct_last_buy_price AS value,
       cash_available, unrealized_pnl, realized_pnl_cumulative
FROM bot_state_snapshots
WHERE symbol = 'CHZ/USDT' AND created_at > now() - interval '24h'
ORDER BY created_at;

-- Snapshot "istantaneo" di tutti i bot adesso
SELECT DISTINCT ON (symbol) *
FROM bot_state_snapshots
ORDER BY symbol, created_at DESC;
```

**Retention:** niente purge automatico al MVP. A 15 min × 24h × 365 × 5 bot = ~175k righe/anno. Tranquillamente gestibile. Se crescesse oltre, aggiungere job di rollup mensile.

---

### Tabella 3 — `decisions_trace`

Perché il bot non sta facendo qualcosa (o lo sta facendo). Con dedup per non riempire la tabella di migliaia di "skipped cash_insufficient".

```sql
CREATE TABLE decisions_trace (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  first_seen   timestamptz NOT NULL DEFAULT now(),
  last_seen    timestamptz NOT NULL DEFAULT now(),
  occurrences  integer NOT NULL DEFAULT 1,
  symbol       text NOT NULL,
  decision     text NOT NULL,   -- 'buy_skip' | 'sell_skip' | 'hold' | 'buy_fired' | 'sell_fired' | 'force_liquidate'
  reason       text NOT NULL,   -- token short (cash_insufficient, cooldown_active, no_trigger, ecc)
  context      jsonb            -- {price, cash, holdings, threshold_pct, age_min}
);
CREATE UNIQUE INDEX ON decisions_trace(symbol, decision, reason);
CREATE INDEX ON decisions_trace(symbol, last_seen DESC);
```

**Logica dedup:** upsert (insert-or-update su `(symbol, decision, reason)`).

```python
# db/decisions_trace.py
def trace(symbol, decision, reason, context=None):
    try:
        client = get_client()
        # Supabase upsert con merge sulla chiave univoca
        client.table("decisions_trace").upsert({
            "symbol": symbol, "decision": decision, "reason": reason,
            "last_seen": "now()", "context": context,
            # occurrences += 1 va fatto server-side con RPC o postgres
            # function — vedi nota sotto
        }).execute()
    except Exception as e:
        _logger.warning(f"decisions_trace upsert failed: {e}")
```

**⚠️ Nota implementativa sul dedup/upsert:**
L'incremento di `occurrences` richiede un'operazione atomica server-side. Due opzioni:

- **Opzione A — RPC function:** creare una `postgres function trace_upsert(symbol, decision, reason, context) RETURNS void` che fa INSERT ... ON CONFLICT (symbol, decision, reason) DO UPDATE SET last_seen=now(), occurrences=occurrences+1, context=EXCLUDED.context. Client chiama la function.
- **Opzione B — Trigger DB:** ON INSERT, se (symbol,decision,reason) esiste già, il trigger sposta l'INSERT in UPDATE. Più magico ma più rigido.

Raccomando **A** perché esplicito.

**Purge periodico:** cleanup job ogni ora (cron o pg_cron) che elimina righe con `last_seen < now() - interval '2 hours'`. Così la tabella resta sempre "snapshot vivo dell'ultimo periodo" e non cresce indefinitamente.

**Call-site in `grid_bot.check_price_and_execute`:** ~8-10 punti decisionali, uno per ogni `return None` o branch di decisione. Ogni call-site 1 riga.

**Query chiave:**
```sql
-- Cosa stanno facendo tutti i bot ADESSO
SELECT symbol, decision, reason, occurrences,
       extract(epoch from (last_seen - first_seen))/60 AS minutes_stuck
FROM decisions_trace
WHERE last_seen > now() - interval '10 minutes'
ORDER BY symbol, occurrences DESC;

-- Bot fermi su skip da più di 30 min
SELECT symbol, decision, reason, occurrences
FROM decisions_trace
WHERE last_seen - first_seen > interval '30 minutes'
  AND decision LIKE '%skip%'
ORDER BY occurrences DESC;
```

---

## Miei dubbi (da discutere col CEO)

Questi sono i miei dubbi onesti da stagista, che il CEO è invitato a sciogliere/confermare/ribaltare.

### D1 — Severity/category di `bot_events_log`: tassonomia giusta al primo colpo?

Ho proposto 4 severity × 6 category. Il rischio è che la griglia sia o **troppo fine** (tutto finisce in `info/lifecycle` e la tassonomia non aiuta) o **troppo grossolana** (eventi simili con severity diversa perché li ho classificati a gusto). Due questioni specifiche:

- `config_changed` va in `config` o in `safety` quando cambia un safety param? Oggi è ambiguo.
- `multi_lot_entry_fired` va in `trade` o in `tf`? È entrambe.

**Proposta:** accettare che la tassonomia v1 sarà imperfetta. Al primo brief follow-up (se serve), rinormalizzare. Alternativa: non mettere `CHECK` constraint su `category` al MVP, solo `severity`.

### D2 — `bot_state_snapshots` ogni 15 min: granularità giusta?

15 min × 5 bot = 20 snapshot/ora. Il trade-off:

- Più fine (es. 5 min) → più risoluzione su grafici, ma 3× più INSERT + 3× storage
- Più grossolano (es. 1h) → storage minimo ma rischi di perdere pattern (un pump che dura 20 min non lo vedi nello snapshot)

Raccomando 15 min ma il CEO potrebbe volere 5 min per il debug fine.

**Secondo punto:** lo snapshot dovrebbe scattare ANCHE su eventi (trade eseguito, stop-loss trigger)? Altrimenti se un evento succede a 10 min dallo snapshot precedente, perdi "come era esattamente al momento dell'evento". Soluzione: `log_event` scrive anche uno snapshot ad hoc nella stessa transazione. Ma aumenta complessità.

### D3 — `decisions_trace`: vale il costo?

**Pro:** taglio "perché" che oggi richiede SSH + grep su log. Risolve una vera domanda ricorrente del CEO.

**Contro onesto:**
1. **Dedup RPC richiede una function Postgres.** È la prima volta che il progetto introduce una function lato DB. Aggiunge una dipendenza di "cose da deployare" che fino a oggi erano solo migration di schema.
2. **Può essere ridondante con `bot_events_log`** per alcuni casi. Es. "buy skipped per cash_insufficient" è già parzialmente coperto da `capital_exhausted` event. `decisions_trace` aggiunge "quante volte al minuto sta valutando + quanto dura la situazione", che è info diversa ma non sempre utile.
3. **Richiede disciplina al call-site:** ogni `return None` nei branch decisionali va decorato. Facile dimenticare alcuni call-site → dati incompleti → conclusioni sbagliate.
4. **Il cleanup orario va testato bene:** se la function non gira (cron fallito, ecc), la tabella cresce silenziosamente.

**Alternative a `decisions_trace`:**
- **Più semplice:** aggiungere un campo `last_skip_reason` a `bot_state_snapshots`. Ogni snapshot registra "l'ultimo motivo per cui non ho agito". Perde il conteggio/frequenza ma sta in 1 tabella e non richiede RPC.
- **Più ricco:** mantenere `decisions_trace` come brief separato da fare DOPO, una volta stabilizzato 1+2.

**Il mio voto:** se il CEO non ha mai detto esplicitamente "voglio vedere la frequenza dei non-trade", allora **rinvio** a brief successivo. La value della frequenza è speculativa. Facciamo 1+2 prima, se dopo 1-2 settimane emerge il bisogno reale, brief dedicato 43b.

### D4 — Storage / cost Supabase

Free tier Supabase: 500 MB. I tre tabelloni a regime:

- `bot_events_log`: ~50 eventi/giorno × 365 × ~500 byte = ~9 MB/anno. Irrilevante.
- `bot_state_snapshots`: ~175k righe/anno × ~200 byte = ~35 MB/anno. OK.
- `decisions_trace`: con purge orario resta <50 righe always. Irrilevante.

**Totale:** <50 MB/anno. Siamo larghi su free tier, ma vale controllare periodicamente.

### D5 — Writing to Supabase blocca il bot se la rete cade?

`bot_events_log.log_event()` e `bot_state_snapshots._write_snapshot()` sono chiamate sincrone. Se Supabase è lento (~2-3s latenza), bloccano il main loop del grid_runner. Oggi `SupabaseConfigReader` gestisce già degradation (log warning + keep last known). Dobbiamo fare lo stesso ovunque:

- `try/except` obbligatorio in tutti gli helper (già nel design sopra)
- Timeout esplicito? Supabase Python client non lo espone facilmente — ma in pratica `requests` sotto ha timeout di default ragionevoli

**Raccomando:** logge la latenza degli insert più significativi (es. warning se > 1s) per individuare regressioni future.

### D6 — Un commit unico o tre?

Pacchetto così ampio che sarebbe meglio spezzarlo:
- **43a** = `bot_events_log` + call-site decoration (core MVP, ~1h lavoro, utile anche da solo)
- **43b** = `bot_state_snapshots` + loop integration (indipendente, ~45 min)
- **43c** = `decisions_trace` se il CEO lo conferma dopo D3 (~1h)

In questo modo possiamo fare 43a stanotte e 43b domani, con meno rischio di rompere qualcosa in un commit gigante.

---

## Files da creare

### Nuovi
- `db/migration_20260420_observability_v1.sql` — schema delle 3 tabelle + indici + (se serve) RPC function
- `db/event_logger.py` — helper `log_event()`
- `db/snapshot_writer.py` — helper `write_state_snapshot(bot, symbol)` con tutti i campi derivabili da `bot.get_status()` + `bot._pct_*`
- `db/decisions_trace.py` — helper `trace()` (solo se 43c approvato)

### Modificati
- `bot/orchestrator.py` — `log_event` su startup/shutdown
- `bot/grid_runner.py` — `log_event` su lifecycle, safety; snapshot ogni 15 cicli; `trace()` negli skip path
- `bot/strategies/grid_bot.py` — `log_event` su stop-loss/take-profit/stop-buy triggers
- `bot/trend_follower/allocator.py` — `log_event` su ALLOCATE/DEALLOCATE/SWAP/multi_lot
- `bot/trend_follower/trend_follower.py` — `log_event` su config_changed

---

## Files da NON toccare
- Tabelle esistenti (`trades`, `bot_config`, `trend_config`, `trend_decisions_log`, `config_changes_log`, `reserve_ledger`) — l'observability è additiva, non invasiva
- `SupabaseConfigReader` — non cambia il suo comportamento, semmai riusa `log_event` in futuro
- Frontend `/tf`, `/admin` — non serve ancora una UI per queste tabelle (il CEO queryera via Supabase SQL editor direttamente)

---

## Test pre-deploy

1. Migration locale su DB di staging o via Supabase SQL editor, verifica schema + indici
2. Smoke test: shell Python che chiama `log_event`, `write_state_snapshot`, `trace` con dati finti, verifica INSERT arriva
3. Run grid_runner in paper per ~10 min, controlla che le tabelle si popolino come atteso
4. Stress test: sim 1000 log_event in 10s — verifica che il bot non si blocca anche con Supabase lento

## Test post-deploy

- 24h di orchestrator attivo, poi 3-4 query del CEO stile quelle sopra
- Confronto riga-per-riga: evento Telegram vs riga `bot_events_log`. Devono matchare 1:1.
- `bot_state_snapshots` plottato su Grafana/Metabase/SQL diretto → deve mostrare equity curve coerente con `trades`

---

## Rollback

```bash
git revert <commit_hash>
git push origin main

# DB (opzionale — le tabelle possono restare, sono write-only)
# DROP TABLE bot_events_log CASCADE;
# DROP TABLE bot_state_snapshots CASCADE;
# DROP TABLE decisions_trace CASCADE;

ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# restart orchestrator
```

Rollback safe: il bot non legge mai da queste tabelle, solo scrive. Se rimuoviamo il codice, il bot torna al comportamento attuale senza perdita di dati/funzionalità.

---

## Commit format

Per 43a (solo `bot_events_log`):
```
feat(observability): bot_events_log — structured event source of truth

Adds a new bot_events_log table and a log_event() helper; decorates
~20 call-sites across orchestrator, grid_runner, grid_bot, allocator
and trend_follower to emit structured events on lifecycle, safety,
trade and config changes. Telegram alerts unchanged — this is
additive observability for post-hoc SQL queries.
```

Per 43b (`bot_state_snapshots`):
```
feat(observability): bot_state_snapshots every 15 min per bot

Adds bot_state_snapshots table + 15-min writer integrated into the
grid_runner main loop. Captures holdings, avg_buy, cash, pnl, lots,
greed tier, safety flags. Enables equity-curve queries and
"state-at-time-T" questions without replaying trades.
```

Per 43c (`decisions_trace`): scriviamo il commit quando decidiamo se farlo.

---

## Out of scope

- **Health check heartbeat** (idea 3 iniziale) — rimandato: senza un consumer h24 che reagisce, scrivere heartbeat è inutile. Da valutare insieme a un futuro watchdog.
- **Daily settlement** (`daily_ledger`) — rimandato: utile per tax/accounting futuro, non urgente. Il `daily_pnl_tracker` esistente copre il fabbisogno immediato.
- **Dashboard UI** per queryare le nuove tabelle — il CEO userà Supabase SQL editor direttamente; UI dedicata solo se emerge necessità dopo.
- **Alerting** basato su `bot_events_log` (es. "se ci sono > 5 error nell'ultima ora, ping") — v2, quando avremo un sistema di control h24.
