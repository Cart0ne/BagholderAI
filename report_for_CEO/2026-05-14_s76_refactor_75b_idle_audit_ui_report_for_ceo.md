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

## 5. Bug 75b shipped silenziosamente — diagnosi + fix live (post-pubblicazione)

Dopo la pubblicazione del report e del commit di chiusura S76, Max ha provato il timer dal vivo: ha settato `BONK.stop_buy_unlock_hours = 1` da dashboard. Dopo 1.7h `bot_runtime_state.stop_buy_active` era ancora `true`, l'auto-reset non era scattato (avrebbe dovuto scattare alla 1h).

### Diagnosi

`bot_config` aveva il valore corretto (1) ma il bot non lo stava leggendo. Root cause: `config/supabase_config.py` definisce una stringa `_CONFIG_FIELDS` che enumera *esplicitamente* le colonne richieste alla query Supabase. Durante S76 task 2 ho esteso 2 punti che consumano il dict ritornato (`sb_cfg.get("stop_buy_unlock_hours")`):
- `grid_runner/__init__.py` bootstrap read
- `grid_runner/config_sync.py` hot-reload

…ma ho dimenticato di estendere `_CONFIG_FIELDS` stesso. Quindi `sb_cfg["stop_buy_unlock_hours"]` era *sempre* None per omissione lato server, e l'hot-reload era un no-op silenzioso. Il valore in memoria di `bot.stop_buy_unlock_hours` restava all'`__init__` default `0.0` → guard `unlock_hours > 0` falsa → blocco auto-reset mai eseguito.

**Perché pytest 29/29 non ha catturato:** la fixture `make_bot()` setta `bot.stop_buy_unlock_hours` direttamente sull'istanza, bypassando completamente il path `SupabaseConfigReader → config_sync → bot`. Punto cieco strutturale: nessun test di integrazione che esercita la catena reader-vera + config_sync su un payload Supabase realistico. Salvato come lezione.

### Fix

Commit `a780314` — 1 file, +6/-1: aggiunta `stop_buy_unlock_hours` a `_CONFIG_FIELDS` in `config/supabase_config.py`. Pytest 29/29 ancora verdi (la modifica è solo data fetching, nessun comportamento testato cambia).

### Deploy + verifica live

Restart Mac Mini 12:08:48 UTC (PID 87296). Stop-buy 39b ri-armato al primo tick post-restart con timestamp nuovo. Aspettativa: auto-reset entro le ~13:08:48 UTC (1h dal nuovo armamento). Verifica della reader chain via `bot_runtime_state`: `updated_at` corrisponde al timestamp del bot (UPSERT ogni tick), `stop_buy_activated_at` registrato correttamente al primo trigger post-restart.

**Stato in attesa al momento della stesura:** ~0.6 min elapsed dal nuovo restart, manca ~58 min al trigger. Si verifica naturalmente entro 1h. Nessun Telegram di unlock previsto (by design — memoria `feedback_no_telegram_alerts`). Conferma implicita arriverà via Telegram di BUY se il prezzo sarà sotto trigger al momento dello sblocco, oppure via dashboard `/grid` quando il badge tornerà a `Next buy if ↓`.

---

## 6. Badge UI con countdown timer 75b

Dopo il fix Max ha chiesto di rendere il badge dashboard "STOP-BUY ACTIVE · BLOCKED · drawdown > 2%" rappresentativo dello stato reale, incluso il timer 75b se armato. Il dato era già in `bot_runtime_state.stop_buy_activated_at` + `bot_config.stop_buy_unlock_hours` ma il frontend non lo consumava.

### Modifica `web_astro/public/grid.html` (commit `8c2698f`)

Tre stati del badge ora differenziati:

| Configurazione coin | Badge value | Esempio BONK ora |
|---|---|---|
| `unlock_hours=0` (default) | `BLOCKED · drawdown > X%` (immutato) | (SOL/BTC oggi) |
| `unlock_hours>0`, timer armato | `BLOCKED · drawdown > X% · resets in Yh Zm` | `BLOCKED · drawdown > 2% · resets in 58m` |
| `unlock_hours>0`, soglia raggiunta non ancora applicata | `BLOCKED · drawdown > X% · unlock pending` | edge case 1 tick |

Tooltip esteso correttamente cita entrambi i meccanismi di reset (profitable sell *vs* timer). Quando `unlock_hours=0` il tooltip dice esplicitamente "Auto-unlock disabled, only a profitable sell will clear the guard."

Refresh: il badge si re-renderizza ad ogni poll `/grid` (~30s) — countdown a granularità di minuto è sufficiente, niente JS per-secondo lato client.

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

- **Telegram alert dedicato all'auto-unlock**: quando il timer scatta, log + event_log ma niente Telegram. Coerente con la regola "no new Telegram alerts" (memoria `feedback_no_telegram_alerts`); aggiungibile via admin/SSE se voluto.
- **Test di integrazione SupabaseConfigReader → config_sync → bot**: la mancanza di questo strato di coverage è la causa del bug 75b shipped silenziosamente (vedi §5). Brief separato (~30-60 min) per aggiungere fixture mock-payload realistici. Importante prima di altri brief che estendono `bot_config`.
- **Test di coverage estesa al main loop del package**: ho testato in isolamento ogni sotto-modulo. Un test di integrazione end-to-end (es. simulate one full tick) sarebbe utile ma non lo richiede nessun brief attuale.
- **PROJECT_STATE.md cleanup post-S76**: shipped in fase di chiusura sessione (commit `3d62942`), 78KB → 27KB con archivio in `audits/PROJECT_STATE_archive_pre-S76.md`. Soglia di taglio S70+. Tracked via eccezione `.gitignore` `!audits/PROJECT_STATE_archive_*.md` per preservare la storia leggibile delle compaction future.
- **Diary entry S76**: come tutte le sessioni, l'entry diary `.docx` per S76 va prodotto separatamente (in coda a S73 e S74 già pronti, S75 ancora da scrivere).

---

## Numeri sessione

- **Durata**: ~4.5h (inclusi diagnosi bug post-pubblicazione + fix + badge UI countdown + cleanup PROJECT_STATE)
- **Commit su main**: 6 (`9ceaa81` squash refactor+75b+audit+UI · `3e7bc58` docs S76 closure · `3d62942` chore state cleanup · `a780314` fix 75b config_fields · `8c2698f` badge countdown)
- **Commit interni feature-branch**: 5 (`b62e952`, `5af0ac7`, `cd52fa4`, `19331ee`, `9f68396`) squashati in `9ceaa81`
- **File modificati totali**: 16 (5 backend logic + 8 nuovi moduli refactor + 2 frontend UI + 1 config reader)
- **Migration Supabase**: 2 (`bot_config.stop_buy_unlock_hours` + `bot_runtime_state.stop_buy_activated_at`)
- **Test verdi**: 25 → 29 (+4) — il bug 75b silenzioso ha rivelato un punto cieco strutturale (config reader chain non testata)
- **Restart Mac Mini**: 4 (3 nella prima parte + 1 post-fix bug 75b alle 12:08:48 UTC PID 87296)
- **Behavior change in produzione**: 0 finché Max non setta unlock_hours>0; BONK è il primo caso reale del timer (settato a 1h post-deploy)
- **Linee di codice**: -1623 (monolite cancellato) + 1858 (package) + 51 (75b) + 13 (idle audit) + 4 (UI) + 6 (fix _CONFIG_FIELDS) + 30 (badge countdown) = +339 nette
- **PROJECT_STATE.md compaction**: 78 KB → 27 KB (-65%) con archivio 9.5 KB tracked

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
- **Pattern "lazy import per testabilità sotto-moduli"** — applicabile ad altri package se dipendenze pesanti (telegram_notifier, ccxt, etc.)
- **Disciplina "refactor zero-behavior"** anche su micro-cambi tentanti (1 riga di payload anticipata = errore — l'ho rifiutata in tempo durante runtime_state extraction)
- **Squash-merge** per sessioni con più commit logicamente sequenziali ma raggruppati narrativamente in un singolo S-number
- **🆕 Tripletta di modifica per nuova colonna bot_config**: ogni nuovo parametro per-coin (75b ne è l'esempio doloroso) richiede modifiche in **TRE punti** sincroni, non due:
  1. Migration SQL (`ALTER TABLE bot_config ADD COLUMN…`)
  2. `config/supabase_config.py` → `_CONFIG_FIELDS` (la SELECT esplicita)
  3. `bot/grid_runner/config_sync.py` → hot-reload branch
  Più (4) il bootstrap read in `bot/grid_runner/__init__.py` se il valore va passato al GridBot constructor. Saltare #2 produce un bug silenzioso: pytest verde, hot-reload no-op, comportamento al default `__init__`. Test fixture che setta l'attributo direttamente NON copre questo path.
- **🆕 Test gap rivelato**: nessuna integration test esercita `SupabaseConfigReader → _sync_config_to_bot → bot` su payload realistici. Brief separato consigliato prima del prossimo brief che estende `bot_config`.

---

*Prossimo report CEO atteso: post-Sentinel/Sherpa DRY_RUN analysis (~25 maggio) o pre-go-live €100 — whichever comes first.*

*Aggiornamento report: 2026-05-14 pomeriggio (post-bug 75b live + fix + badge countdown + state cleanup).*
