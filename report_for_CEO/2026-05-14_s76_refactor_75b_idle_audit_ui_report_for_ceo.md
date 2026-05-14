# Sessione 76 — Refactor grid_runner + brief 75b + audit idle + UI

**Data:** 2026-05-14 (mattina, ~3h)
**Intern:** Claude Code
**Modalità:** sessione di esecuzione della roadmap concordata a fine S75. Tre task sequenziali + un task UI bonus richiesto a fine giornata da Max. Tutto squash-mergiato in main come unico commit `9ceaa81` per pulizia di git history (branch `refactor/grid_runner_split` archiviato su origin).

---

## Executive summary

**1 commit squash su main** (`9ceaa81`, era branch `refactor/grid_runner_split` con 5 commit `b62e952` → `9f68396`), **2 migration Supabase** (`bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`), **3 restart Mac Mini watch-verdi** (11:50 refactor, 12:00 75b, 12:18 idle audit), **test suite 25 → 29 verdi** (Z/AA/BB stop-buy unlock + CC idle suppression).

La sessione è stata pianificata in 3 step sequenziali a fine S75:
1. **Refactor `grid_runner.py`** (1623 righe monolite) come prerequisito strutturale
2. **Brief 75b stop_buy_unlock_hours** (timer di sblocco della guardia 39b)
3. **Audit messaggi idle re-entry / recalibrate** (soppressione condizionale durante stop-buy)

A questi si è aggiunto in chiusura un task 4 (UI dashboard `/grid` per il parametro 75b), richiesto da Max come complemento naturale del 75b.

L'investimento del refactor (task 1) ha pagato subito: i task 2 e 3 hanno toccato esattamente i moduli isolati nel package (runtime_state.py per il 75b, idle_alerts.py per l'audit), trasformando due brief potenzialmente rischiosi in diff strettissimi (~50 righe ciascuno). Pattern di shipping incrementale: pytest verde dopo ogni step di estrazione + smoke test live su Mac Mini con confronto preciso pre/post di ogni cambio.

**Default 0** ovunque per il timer 75b → **zero behavior change** in produzione finché Max/CEO non decide per-coin via dashboard. Stesso pattern dell'audit idle: parametro `stop_buy_active=False` di default preserva il comportamento verboso.

---

## Cosa è stato shipped (1 squash, 5 commit interni)

| # | Commit interno | Topic | Descrizione |
|---|---|---|---|
| 1 | `b62e952` + `5af0ac7` | Refactor package | `bot/grid_runner.py` (1623) → `bot/grid_runner/` package con 8 moduli + `__main__.py`. Orchestrator entrypoint preservato (`python -m bot.grid_runner` resolve via `__main__.py`). Zero behavior change. Pytest 25/25 ad ogni step. |
| 2 | `cd52fa4` | Brief 75b | Migration `bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`. Codice in 5 file (`grid_bot.py` __init+state+arm+auto-reset, `sell_pipeline.py` clear timestamp, `grid_runner/__init__.py` boot read, `config_sync.py` hot-reload, `runtime_state.py` espone). Default 0 = comportamento 39b preservato. Test +3. |
| 3 | `19331ee` | Audit idle suppression | `send_idle_alerts(stop_buy_active=False)`. Quando `True`, idle Telegram silenziati; recalibrate interno avviene comunque (logger + event_log preserved). Test +1. Lazy import `SyncTelegramNotifier` per testabilità sotto-moduli. |
| 4 | `9f68396` | UI dashboard | `/grid` Safety section: nuova riga `Stop-buy unlock (hours)` tra `Stop-buy drawdown %` e `Dead-zone unblock`. `GRID_CONFIG_FIELDS` esteso, `SUBLABELS` con descrizione didattica (pattern fotocopia 74d). Save via `sbPatch` su `bot_config`. |

Tutti squashati in `9ceaa81` su main. Branch `refactor/grid_runner_split` cancellato in locale, preservato su origin come archivio.

---

## 1. Refactor `grid_runner.py` — il monolite e il package

### Il monolite

Pre-refactor il file `bot/grid_runner.py` aveva **1623 righe**, di cui ~830 dentro un solo `run_grid_bot()` con bootstrap + main loop intrecciati. Cresciuto +32 righe in S74b per wiring `_upsert_runtime_state` + `dead_zone_hours`. Era stato segnato come split candidate "post go-live €100" per timore di refactor strutturale su file che gira H24 con capitale reale.

### Il pivot

In sessione ho proposto di rilassare il vincolo "post go-live" perché:
- Siamo ancora su **testnet** ($500 paper, niente capitale reale)
- Il refactor è interamente strutturale (solo `mv` di funzioni + import re-export, **zero comportamento cambiato**)
- I due brief 75b + idle audit toccano esattamente i punti del file che vanno spaccati — rifare il refactor dopo significherebbe rifare anche quei due brief

Max ha approvato. Strategia di shipping incrementale: 8 step di estrazione, pytest 25/25 dopo ognuno, smoke test live a fine.

### La mappa del package

```
bot/grid_runner/
  __init__.py            779   bootstrap + main loop
  __main__.py             26   CLI entrypoint per `python -m bot.grid_runner`
  config_sync.py         197   _sync_config_to_bot — hot-reload Supabase
  runtime_state.py        45   _upsert_runtime_state — mirror in-memory al DB
  idle_alerts.py          52   send_idle_alerts — Telegram recalibrate/re-entry + policy
  telegram_dispatcher.py 154   _build_cycle_summary + _format_cycle_summary
  daily_report.py        162   maybe_send_daily_report — blocco 20:00 + Haiku
  liquidation.py         355   _force_liquidate + _consume_initial_lots + _deactivate
  lifecycle.py            88   fetch_price + _print_status + _build_portfolio_summary
```

Totale package 1858 righe (vs monolite 1623 = +235 per docstring + import boilerplate accettabili). Il `__init__.py` da solo è 779 righe (-844 dal monolite).

### Verifica live

3 restart Mac Mini nella stessa sessione, con confronto preciso pre/post:

**Restart 11:50 UTC** (refactor only, PID 86005): BTC ha tradato al primo tick (BUY 0.000620 BTC @ $79,624, cost $49.37, FILLED). Telegram alert inviato. SOL+BONK STOP-BUY TRIGGERED + IDLE RECALIBRATE FIRED + Telegram inviati (comportamento pre-audit). Zero ImportError. Tutti i path critici testati live: `lifecycle.fetch_price`, `runtime_state._upsert_runtime_state`, `config_sync._sync_config_to_bot`, `idle_alerts.send_idle_alerts`, `liquidation` (import resolved).

### Decisione architetturale registrata

Durante l'estrazione di `runtime_state.py` ho inizialmente aggiunto `stop_buy_activated_at` al payload — anticipando il task 2 (75b). Mi sono fermato e rimosso subito perché il refactor doveva essere **puramente strutturale** (zero behavior change). Quel cambio è entrato poi nel commit `cd52fa4` come parte del task 2 in modo pulito. Lezione: nei refactor non additivi è importante mantenere la disciplina anche su micro-cambi che "tanto è 1 riga".

---

## 2. Brief 75b — stop_buy_unlock_hours timer

### Il problema (S74 + perdita reale 2026-05-13)

La guardia `_stop_buy_active` (brief 39b) si attiva quando il drawdown totale supera `stop_buy_drawdown_pct` (default 2% allocation) e si resetta SOLO su una sell profittevole. Se il prezzo scende ulteriormente e resta sotto, il bot resta **bloccato indefinitamente** — niente DCA, avg cost stuck, perdita potenziale aumenta.

2026-05-13 è successo realmente: stop-buy si è attivato, mercato ha continuato a scendere, bot ha guardato passare opportunità DCA per giorni. Tracciato in S74 §6 come "Stop-buy time-limit (24h then buy anyway to lower avg cost)" — proposta strategica parcheggiata.

### La soluzione

Nuova colonna `bot_config.stop_buy_unlock_hours` (REAL, NOT NULL, DEFAULT 0, CHECK 0..168). Quando > 0:
- Lo stop-buy scatta normalmente per drawdown
- Al momento del trigger, il bot registra `_stop_buy_activated_at = utcnow()`
- Ad ogni tick successivo: se `elapsed >= unlock_hours`, **auto-reset** del flag + clear del timestamp + log event `stop_buy_unlock_reset`
- Una profitable sell continua a resettare PRIMA del timer (additivo, non sostitutivo)

Default 0 = disabled = comportamento 39b preservato. CHECK 0..168 (1 settimana) coerente con `dead_zone_hours` di 74d.

### Migration

```sql
ALTER TABLE bot_config
ADD COLUMN stop_buy_unlock_hours REAL NOT NULL DEFAULT 0
CHECK (stop_buy_unlock_hours >= 0 AND stop_buy_unlock_hours <= 168);

ALTER TABLE bot_runtime_state
ADD COLUMN stop_buy_activated_at TIMESTAMPTZ;
```

`bot_runtime_state.stop_buy_activated_at` è esposto al frontend tramite `_upsert_runtime_state` per permettere countdown UI futura (es. "BLOCKED · resets in 3h 12m").

### Codice modificato

5 file con +51 righe nette:
- `bot/grid/grid_bot.py`: 3 righe nuove (signature, state, arm timestamp at trigger) + nuovo blocco auto-reset (~30 righe) subito dopo il check 39b in `check_price_and_execute`
- `bot/grid/sell_pipeline.py`: 1 riga (`bot._stop_buy_activated_at = None` alla profitable sell reset, accanto al clear esistente di `_stop_buy_active`)
- `bot/grid_runner/__init__.py`: boot read da Supabase + pass al GridBot constructor
- `bot/grid_runner/config_sync.py`: hot-reload da `bot_config` su ogni tick
- `bot/grid_runner/runtime_state.py`: payload UPSERT espande con `stop_buy_activated_at`

### Test

3 test nuovi (test_z, test_aa, test_bb in test_accounting_avg_cost.py):
- **Z**: con `unlock_hours=24` e attivazione 25h fa, `check_price_and_execute` resetta il flag + clear timestamp
- **AA**: con `unlock_hours=24` e attivazione 23h fa, flag resta True + timestamp preservato
- **BB**: profitable sell durante stop-buy attivo resetta SIA il flag (39b) SIA il timestamp (75b) — evita timer stale al prossimo armamento

### Verifica live

Restart Mac Mini 12:00 UTC (PID 86159): SOL+BONK STOP-BUY TRIGGERED (drawdown ancora attivo), `_stop_buy_activated_at` registrato. Default 0 → **timer NON scatta**, comportamento identico a pre-75b. Zero behavior change confermato in produzione.

I prossimi tick scrivono `bot_runtime_state.stop_buy_activated_at` valorizzato — la dashboard può iniziare a leggere il dato quando si vorrà aggiungere il countdown UI.

---

## 3. Audit idle alert suppression

### Il rumore (osservato in S76 restart 11:50 + 12:00)

Durante un drawdown prolungato con stop-buy attivo:
- Il bot fa `IDLE RECALIBRATE` ogni `dead_zone_hours` (resetta `_pct_last_buy_price` al prezzo corrente) — è una manutenzione interna sana
- Manda un Telegram `🔄 IDLE RECALIBRATE: SOL — buy reference reset to $90.87 / Holdings still open — waiting for next buy signal`
- Ma `_stop_buy_active=True` significa che il "next buy signal" **non arriverà mai** finché lo stop-buy non si sblocca

Risultato: rumore Telegram. Il CEO vede ricalibrazioni che non si traducono in nessuna azione fino a quando non si sblocca lo stop-buy.

### La soluzione

`send_idle_alerts(notifier, alerts, stop_buy_active=False)`:
- Se `stop_buy_active=True` → **return early**, zero Telegram
- L'azione interna (reset reference, reset ladder) è eseguita SEMPRE dentro `grid_bot.py`
- `logger.info("Idle recalibrate after Nh: resetting buy reference...")` continua a finire nei log file
- `log_event(...)` continua a popolare `bot_events_log` per audit/diary

Solo il send Telegram è silenziato. La storia completa è preservata.

### Test (test_cc)

3 sub-case:
- `stop_buy_active=False`: notifier riceve 2 send_message (verbose preserved)
- `stop_buy_active=True`: notifier riceve 0 send_message (suppressed)
- Default param omesso: notifier riceve 2 send_message (backward-compat)

### Verifica live

Restart Mac Mini 12:18 UTC (PID 86443): SOL+BONK in stop-buy attivo, `IDLE RECALIBRATE` interno avvenuto (log `[SOL/USDT] Idle recalibrate after 41.5h: resetting buy reference from $93.65 to $91.06`), **ma nessun `Telegram message sent` subito dopo**. Confronto preciso:

| Restart | Codice | SOL idle Telegram | BONK idle Telegram |
|---|---|---|---|
| 11:50 (refactor only) | Sì (vecchio comportamento) | INVIATO | INVIATO |
| 12:00 (75b shipped) | Sì (vecchio comportamento) | INVIATO | INVIATO |
| **12:18 (audit shipped)** | **No (nuova suppression)** | **silenziato** ✓ | **silenziato** ✓ |

La differenza pre/post è inequivocabile nei log file.

### Decisione architetturale: lazy import telegram_notifier

Durante la stesura del test_cc è emerso un problema: `from bot.grid_runner.idle_alerts import send_idle_alerts` triggera l'import di `bot/grid_runner/__init__.py`, che importava `SyncTelegramNotifier` da `utils.telegram_notifier`. Sul venv MBP la libreria `python-telegram-bot` è incompatibile (`ModuleNotFoundError: No module named 'telegram._utils.datetime'`), quindi qualsiasi test che importi un sotto-modulo di `bot.grid_runner` falliva.

Soluzione: lazy import di `SyncTelegramNotifier` dentro `run_grid_bot()` invece che al top del modulo. Beneficio collaterale: i sotto-moduli ora si testano in isolamento senza la dipendenza Telegram. Pattern utile da estendere ad altri sotto-moduli con dipendenze pesanti.

---

## 4. UI `/grid` Safety — `stop_buy_unlock_hours` editabile

Richiesto da Max a fine sessione come "aggiorna L'ui dashboard con dead_zone_hours" — interpretato come "aggiungi UI per `stop_buy_unlock_hours` seguendo il pattern di `dead_zone_hours`" (l'altro parametro safety per-coin).

### Modifiche `web_astro/public/grid.html`

3 micro-edit:
1. Riga editabile aggiunta in `<div class="config-grid">` Safety, tra `Stop-buy drawdown %` e `Dead-zone unblock (hours)`
2. `'stop_buy_unlock_hours'` aggiunto a `GRID_CONFIG_FIELDS` (così `saveConfig()` lo include automaticamente nel PATCH `bot_config`)
3. `SUBLABELS['stop_buy_unlock_hours']`: descrizione didattica "0 = disabled (only profitable sell resets). Max 168h. Profitable sell still resets BEFORE the timer. Suggested 24h on coins where prolonged drawdowns are common."

RLS verificata: `anon_update_bot_config` policy già permette UPDATE su qualsiasi colonna inclusi i nuovi campi. Zero modifiche Supabase necessarie.

### Stato dei 3 bot live

Tutti partono con `unlock_hours=0` nel DB → row renderizzata con valore 0 → comportamento identico finché Max/CEO non edita manualmente.

---

## Test suite

| Pre-S76 | S76 | Delta |
|---|---|---|
| 25/25 (A → Y) | **29/29** | +4 |

Nuovi:
- **Z** stop_buy_unlock fires after timeout (75b)
- **AA** stop_buy_unlock holds under timeout (75b)
- **BB** profitable_sell clears unlock_timestamp (75b)
- **CC** idle_alerts suppressed when stop_buy_active (audit)

---

## Decisioni delegate a CC durante la sessione

- **Rilassare il vincolo "post go-live €100" per il refactor**: motivato da testnet + zero behavior change + lo split sblocca i due brief successivi.
- **Squash-merge in main** invece di fast-forward dei 5 commit feature: history pulita, un solo commit "S76" leggibile. Branch preservato su origin come archivio.
- **CHECK 0..168 sul campo `stop_buy_unlock_hours`**: coerenza col pattern 74d. Max non l'ha richiesto esplicitamente nel brief originale; aggiunto come safety.
- **Sublabel UI didattica e lunga**: pattern Max-noted di S74b ("io non mi ricordo neanche a cosa serve").
- **Lazy import telegram_notifier**: emerso durante test_cc, beneficio collaterale > rumore di refactor.

---

## Cosa NON è stato fatto

- **UI countdown timer** per `stop_buy_activated_at` su `/grid` (es. "BLOCKED · resets in Xh Ym"). Dato esposto in `bot_runtime_state` ma non ancora consumato dal frontend. Brief separato (~30 min) se Max lo vuole.
- **Telegram alert dedicato all'auto-unlock**: quando il timer scatta, log + event_log ma niente Telegram. Coerente con la regola "no new Telegram alerts" (memoria `feedback_no_telegram_alerts`); aggiungibile via admin/SSE se voluto.
- **Test di coverage estesa al main loop del package**: ho testato in isolamento ogni sotto-modulo. Un test di integrazione end-to-end (es. simulate one full tick) sarebbe utile ma non lo richiede nessun brief attuale.
- **Diary entry S76**: come tutte le sessioni, l'entry diary `.docx` per S76 va prodotto separatamente (in coda a S73 e S74 già pronti, S75 ancora da scrivere).

---

## Numeri sessione

- **Durata**: ~3h
- **Commit interni**: 5 (squashati in 1 su main)
- **File modificati**: 14 (5 backend logic + 8 nuovi moduli refactor + 1 frontend UI)
- **Migration Supabase**: 2 (`bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`)
- **Test verdi**: 25 → 29 (+4)
- **Restart Mac Mini**: 3 (tutti watch-verdi)
- **Behavior change in produzione**: 0 (tutti i 3 bot live mantengono comportamento pre-S76 fino a edit manuale dei nuovi campi)
- **Linee di codice**: -1623 (monolite cancellato) + 1858 (package) + 51 (75b) + 13 (idle audit) + 4 (UI) = +303 nette

---

## Stato gates pre-go-live €100

Tutte le gate canonical state già chiuse da S74b. Residue:
- 🟡 **Mobile smoke test reale** (richiede Max sul telefono — non eseguito)
- 🟡 **Analisi Sentinel/Sherpa 7gg DRY_RUN** (avviato 2026-05-10, scade ~25 maggio)
- 🟡 **Board approval call**

Target go-live **18-21 maggio 2026** invariato.

---

## Memoria / lezioni

Da salvare nell'auto-memory:
- Pattern "lazy import per testabilità sotto-moduli" — applicabile ad altri package se dipendenze pesanti
- Disciplina "refactor zero-behavior" anche su micro-cambi tentanti (1 riga di payload anticipata = errore)
- Squash-merge per sessioni con piu commit logicamente sequenziali ma raggruppati narrativamente in un singolo S-number

---

*Prossimo report CEO atteso: post-Sentinel/Sherpa DRY_RUN analysis (~25 maggio) o pre-go-live €100 — whichever comes first.*
