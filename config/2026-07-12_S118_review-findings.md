# S118 — Review avversaria del diff Fase 1 (esito) — 2026-07-12

> Workflow `wf_0ca1c13f-278`, 24 agenti su **Sonnet** (zero Fable), 3,384,485 token, 960 tool call.
> Disegno: 4 revisori (lenti: invariante-binance, matematica-fee, lifecycle, sito+DB) → per ogni candidato 2 verificatori adversariali; sopravvive solo ciò che regge a entrambi.

**Contesto chiave: NESSUN finding rompe la Fase 1 shippata.** Sono tutti sul percorso `venue=kraken` (dormiente). L'invariante binance regge — i candidati-invariante più pericolosi sono nei RESPINTI. Il critical + high sono **blocker Fase 2** (da fixare prima di flippare `ALLOW_REAL_MONEY`).

## Confermati (ranked)

### [CRITICAL] KrakenClient normalizza SEMPRE un ordine reale come "non filled" — ogni buy/sell live su Kraken esegue per davvero ma il bot lo tratta come fallito e non lo registra mai
**File:** `bot/exchanges/kraken_client.py:320` · **lente:** contabilita-fee

Difetto: `_normalize_order_response` (righe 313-329, invariata da S112, ma da questo diff wired nel hot-path via buy_pipeline.py:177/192 e sell_pipeline.py:407) fa `filled = float(order.get("filled") or 0)` e se `filled<=0` ritorna None. Ma la risposta grezza di Kraken.AddOrder (verificato nel venv locale, ccxt 4.5.50, stessa versione citata nel docstring del file: `venv/lib/python3.13/site-packages/ccxt/kraken.py:1651-1666`) è SOLO `{"descr":{...}, "txid":[...]}` — nessuna chiave `vol_exec`/`fee`/`status`. `parse_order()` di ccxt legge `filled = safe_string(order, 'vol_exec')` (kraken.py:1948): quella chiave esiste solo nelle risposte di fetchOpenOrders/fetchClosedOrders/fetchMyTrades (viste ai commenti kraken.py:1857/1891/2255/2617/2697), MAI in quella di create_order/create_market_buy_order_with_cost. Quindi per QUALSIASI ordine reale (non-validate) `filled` è sempre None→0.0, e la riga 321 ritorna None SEMPRE, anche quando Kraken ha eseguito l'ordine per davvero (i market order eseguono quasi istantaneamente: soldi/coin già mossi). Scenario concreto: Fase 2, riga BTC/USD flippata a venue='kraken', ALLOW_REAL_MONEY=true. Il trigger di buy scatta → buy_pipeline.py:177 `_client.place_market_buy_base(...)` → Kraken esegue davvero (spende USD reali) → la risposta torna senza fill → kraken_client.py:321 ritorna None → buy_pipeline.py vede `res is None` → "no state change, retry on next tick" (nessuna riga in `trades`, avg/holdings/_available_cash invariati). Al tick successivo la stessa condizione di trigger è ancora vera (stato non cambiato) → il bot ripete l'ordine reale, di nuovo senza registrarlo. Il loop si ripete ad ogni check_interval (20-60s per BTC/SOL/BONK) finché il saldo Kraken non si esaurisce o l'operatore se ne accorge, con zero righe DB a spiegare dove sono finiti i soldi e con `_alert_rejection` (riga 326) che manda un Telegram "rejected" fuorviante mentre l'ordine in realtà passa. Prove indipendenti che confermano il gap: (1) `tests/test_exchange_adapter_s112.py::test_kraken_market_buy_uses_native_cost_order`/`test_kraken_market_sell_uses_create_order` mockano la risposta ccxt con `"filled": 0.001` GIA' popolato — forma che il vero AddOrder Kraken non restituisce mai; (2) i 19 test nuovi S118 (`tests/test_kraken_fase1_s118.py`) che verificano avg/invested/received mockano `bot.exchange_client` direttamente, bypassando KrakenClient; le uniche chiamate dirette a `KrakenClient.place_market_*` nei test passano sempre `params={"validate": True}` (righe 361-387), che salta `_normalize_order_response` per costruzione (kraken_client.py:140-141/160-161/180-181); (3) lo stesso "prova generale" del diff (`scripts/kraken_cutover_check.py` step 6) testa solo `validate=True` per lo stesso motivo → dà falsa fiducia ("28 check, 0 FAIL" nel report S118) mentre il percorso realmente usato in produzione non è mai stato eseguito nemmeno una volta (il report S118 stesso dichiara "Nessun ordine reale"). Nessun punto del codice chiama fetch_order/fetch_my_trades come follow-up per recuperare il fill reale (verificato via grep sull'intero repo).

_Verificatori (estratto):_ Bug CONFERMATO con percorso concreto, verificato leggendo sia il codice del repo sia il sorgente ccxt realmente installato (venv, 4.5.50 — stessa versione pinnata in requirements.txt e citata nel docstring del file).

Catena di verifica:

1. RAGGIUNGIBILITÀ HOT-PATH (confermata, non ipotetica): bot/...

---

### [HIGH] Il cycle-fetch 'riga grid attiva più recente' non aggrega multi-venue: al primo grid Kraken attivato il sito salta silenziosamente sul cycle sbagliato
**File:** `web_astro/src/scripts/live-stats.ts:57` · **lente:** web-sql

Difetto: le 7 superfici bonificate (live-stats.ts:57-59, dashboard-live.ts:48-49, dashboard.astro:444-446, admin.html:1150, grid.html:538, LabRoom.jsx:63, CleanSlateSticker.astro:58) e get_current_cycle globale (db/client.py:57-65) scelgono UN SOLO cycle per l'intero sito con la regola 'riga managed_by=grid, is_active=true, con updated_at più recente'. Ho verificato in prod (Supabase MCP) che bot_config ha un trigger DB `bot_config_updated` (BEFORE UPDATE ... EXECUTE FUNCTION update_bot_config_timestamp()) che ribalta updated_at=now() ad OGNI UPDATE su QUALSIASI colonna della riga — non solo su cambi di cycle. Dati odierni: BTC/USDT updated_at 04:01:59, BONK/USDT 04:32:31, SOL/USDT 12:42:06 (gap di ore), tutte cycle='testnet_2': oggi il risultato coincide col vecchio comportamento (invariante rispettata), ma è coincidenza dovuta all'uniformità dei cycle, non a una vera aggregazione multi-riga. Sherpa scrive bot_config SOLO quando un parametro cambia davvero (bot/sherpa/main.py: `if decision.state_changed:`, loop 120s ma scritture sporadiche — coerente con i gap di ore osservati), quindi 'la riga più di recente aggiornata' NON è una proxy affidabile di 'la riga con l'ultimo cambio di cycle'. 

Scenario concreto (Fase 2, già pianificata in config/2026-07-11_S118_piano_kraken-fase1.md §Residui — 'girerà UN grid alla volta con $100 veri'): si inseriscono righe bot_config venue='kraken' con un cycle NUOVO (diverso da testnet_2), poi si fa UPDATE is_active=true sulla riga BTC/USD kraken. Quell'UPDATE è, per costruzione, l'ULTIMA scrittura cronologica sulla tabella → la riga BTC/USD kraken vince su SOL/USDT e BONK/USDT (che restano is_active=true, ancora operativi su binance con dati reali, ma con updated_at più vecchio). Risultato: CQ (`&cycle=eq....`) su TUTTE le 7 superfici passa silenziosamente al cycle Kraken appena creato → homepage/dashboard/admin/grid/office smettono di mostrare i trade SOL/BONK in corso e mostrano solo il dataset Kraken (quasi vuoto, 0-1 trade, P&L ~$0). CleanSlateSticker in particolare mostrerebbe il badge pubblico '✨ Fresh start' proprio nel momento del go-live reale, cioè il messaggio pubblico più fuorviante possibile nel momento di massima visibilità. La finestra non si autocorregge finché Sherpa non ritocca una riga binance — nei dati odierni questo può richiedere ore, non minuti. Questo contraddice lo scopo dichiarato della bonifica ('ogni superficie del sito segue' un solo UPDATE di cycle) e il claim 'resa venue-robusta' del piano S118 nodo 2: la query sceglie 'l'ultima riga toccata', non 'il cycle del fleet che sta effettivamente generando i dati pubblici'.

_Verificatori (estratto):_ Bug CONFERMATO con percorso concreto. Verifica effettuata su codice reale (diff completo 6a3c8ac..HEAD, tutti i 7 file citati) e su prod via Supabase MCP.

Fatti verificati (non assunti):

1. Trigger DB reale: `bot_config_updated` (BEFORE UPDATE, EXECUTE FUNCTION update_bot_config_timestamp()) esist...

---

### [MEDIUM] _alert_rejection scatta anche su validate=true, prima del check is_validate
**File:** `bot/exchanges/kraken_client.py:134` · **lente:** lifecycle-runtime

In place_market_buy (righe 131-139), place_market_buy_base (151-159) e place_market_sell (171-179) il branch `except Exception` chiama _alert_rejection(...) PRIMA che il codice arrivi al check `self._is_validate(params)` (righe 140-141 / 160-161 / 180-181), che sta a valle del try/except. Scenario concreto: una chiamata con params={'validate': True} che Kraken rifiuta lato validazione (es. importo vicino al minimo di coppia — comportamento già osservato ed esplicitamente documentato come 'atteso/informativo' per il cost-order fallback nello step 5c dello stesso script scripts/kraken_cutover_check.py) fa sollevare un'eccezione a ccxt prima del check is_validate. _alert_rejection invia un vero Telegram '⚠️ BUY/SELL ... rejected' sul canale privato di produzione (stesso config/.env della macchina live) e scrive una riga ORDER_REJECTED reale in bot_events_log, per un ordine che non è mai stato realmente tentato. tests/test_kraken_fase1_s118.py::test_kraken_validate_failure_returns_none esercita esattamente questo path (ex.create_order.side_effect = RuntimeError('EOrder:Insufficient funds')) ma verifica solo che il ritorno sia None: non controlla né blocca l'effetto collaterale sull'alerting, quindi nulla oggi lo intercetta. Il report CEO S118 dichiara questa 'prova generale' (step 6, aggiunta da questo diff) 'rilanciabile prima della Fase 2' — un rerun su una coppia/quantità che tocca un minimo Kraken (es. BONK, book più sottile) produce falsi allarmi in produzione e inquina il log forense.

_Verificatori (estratto):_ Bug CONFERMATO — non refutato. Ho letto per intero bot/exchanges/kraken_client.py, bot/exchange_orders.py (_alert_rejection), utils/telegram_notifier.py, db/client.py, db/event_logger.py, scripts/kraken_cutover_check.py e tests/test_kraken_fase1_s118.py, più la storia del repo (audits/PROJECT_STATE_...

---

### [MEDIUM] Fallback asimmetrico: il sito congela su un letterale hardcoded dove get_current_cycle avrebbe ancora dati DB validi
**File:** `db/client.py:63` · **lente:** web-sql

Difetto: get_current_cycle (path globale, symbol=None) ha un fallback a due livelli — db/client.py:63 `pool = active or tagged` — se nessuna riga è is_active ripiega su TUTTE le righe con cycle valorizzato, prima di arrendersi al literal 'testnet_1' (riga 67). Le 7 query lato sito introdotte nello stesso diff (es. live-stats.ts:57-62, dashboard-live.ts:48-54, dashboard.astro:444-451, admin.html:1150-1153, grid.html:538-541, LabRoom.jsx:63-65, CleanSlateSticker.astro:57-61) NON hanno questo secondo livello: filtrano solo `managed_by=eq.grid&is_active=eq.true` e, se la risposta è un array vuoto (200 OK con 0 righe — non un errore di rete, quindi il `.catch()` non scatta), ricadono direttamente sul letterale hardcoded `CYCLE_FALLBACK='testnet_2'`. 

Scenario concreto: durante un incident-response in Fase 2/3 (es. Max ferma temporaneamente tutta la flotta grid — is_active=false su BTC/SOL/BONK — mentre indaga un problema sul lato Kraken appena attivato), il codice pre-diff avrebbe comunque trovato la riga BTC/USDT (nessun filtro is_active nella query originale) e mostrato il suo cycle reale; il codice post-diff, nello stesso istante, ottiene 0 righe dal filtro is_active=eq.true su TUTTE le 7 superfici e ricade silenziosamente sul letterale 'testnet_2' — che può non essere più il cycle corrente se nel frattempo è stato aperto un cycle nuovo (Kraken) — mostrando dati stantii/incoerenti con lo stato reale del DB invece di riflettere la situazione vera (o di fallire in modo visibile). È la stessa classe di bug ('lexical drift' / dato-sbagliato-mostrato-senza-errore) che la bonifica S118 doveva eliminare, reintrodotta qui solo lato sito perché manca il secondo livello di fallback che db/client.py ha invece guadagnato nello stesso commit.

_Verificatori (estratto):_ CONFERMATO (refuted=false). Ho letto i file interi (non solo il diff) e verificato ogni claim del reviewer:

1. db/client.py:63 `pool = active or tagged` è reale — confermato leggendo il file corrente e il diff (commit 7c2edb7). Il path globale (symbol=None) di get_current_cycle è stato riscritto in...

---

### [LOW] get_current_cycle path globale (db/client.py): selezione per updated_at invece che per unione — usato da commentary/daily_report/daily_pnl
**File:** `db/client.py:65` · **lente:** invariante-binance

Variante Python dello stesso cambio del Finding 2. get_current_cycle(client, symbol=None) — usato da commentary.py (4 call-site), bot/grid_runner/daily_report.py:57, scripts/regen_commentary_now.py:35, DailyPnLTracker.save_daily_snapshot (db/client.py:268) — passa da `max(cycle su TUTTE le righe bot_config)` (lessicografico, robusto per costruzione dato che un cycle-bump è un solo UPDATE su tutte le righe managed_by='grid') a 'cycle della riga più di recente aggiornata tra le righe is_active=true, fallback su tutte le righe taggate' (righe 57-65), SENZA filtro managed_by (a differenza delle query lato sito del Finding 2). Il path per-symbol usato dalla scrittura realmente critica (TradeLogger.log_trade:119, ReserveLedger.log_skim:328 e get_reserve_total:349, scripts/reconcile_binance.py:134) resta identico pre-diff — il trade logging non è a rischio. Il rischio residuo è solo sul path globale (testo di commentary generato, contenuto del daily Telegram report, tag cycle sullo snapshot daily_pnl) e richiede una precondizione non banale: una riga bot_config ATTIVA con cycle non allineato al resto — possibile se il best-effort read in bot/trend_follower/allocator.py (righe ~1140-1156, non toccato da questo diff) fallisse al momento di un'ALLOCATE TF (la riga nuova erediterebbe il default colonna 'testnet_1' invece del cycle corrente) e quella riga risultasse la più di recente aggiornata tra le righe attive. Nessun test copre get_current_cycle né prima né dopo questo diff. Segnalato per completezza (LENS 1 lo cita esplicitamente: 'get_current_cycle nuovo su tutte le call-site esistenti incl. daily_report/commentary/reconcile') ma con confidenza più bassa dei primi due: non ho evidenza che la precondizione si sia mai verificata in produzione.

_Verificatori (estratto):_ Ho letto il codice reale (non solo il diff) e ricostruito un percorso concreto, end-to-end:

1. `db/client.py:32-72` — confermato il diff esatto: il path globale (symbol=None) di `get_current_cycle` è passato da `max()` lessicografico su TUTTE le righe con `cycle` non-nullo, a "riga con `updated_at`...

---

### [LOW] state.total_fees conta due volte la fee di buy ad ogni sell (fee reale già sommata al buy + buy_fee ricostruito sommato di nuovo al sell)
**File:** `bot/grid/sell_pipeline.py:685` · **lente:** contabilita-fee

Difetto: buy_pipeline.py:269 fa `bot.state.total_fees += fee` (fee REALE di acquisto). sell_pipeline.py:469 ricostruisce `buy_fee = cost_basis * bot.fee_rate` (una STIMA della fee di acquisto sulla quota venduta) e la riga 685 la risomma: `bot.state.total_fees += fee + buy_fee` (fee = sell fee reale). Per un ciclo Kraken completo (buy $25 fee reale ~$0.20, poi sell integrale fee reale ~$0.20), `state.total_fees` finisce a ~$0.60 invece del reale ~$0.40 pagato — overstatement del 50%, perché la fee di buy è contata sia al momento del buy sia ricostruita di nuovo al sell. Il pattern esiste da prima di S118 (con FEE_RATE Binance=0.1% l'errore era ~8x più piccolo, quindi trascurabile in valore assoluto); questo diff lo eredita invariato limitandosi a sostituire la fonte da `bot.FEE_RATE` (costante) a `bot.fee_rate` (istanza per-venue, sell_pipeline.py:469) — con fee Kraken ~0.8% l'overstatement diventa materiale in valore assoluto (8x). Impatto verificato limitato: NON tocca `_available_cash`, `avg_buy_price`, `realized_pnl` né `daily_pnl.total_fees_today` (quest'ultimo somma `trades.fee` direttamente dal DB in daily_report.py:62, indipendente da `state.total_fees`, quindi corretto); l'unico consumer trovato è `GridBot.get_status()["fees"]` (grid_bot.py:1202), non risulta letto da report/Telegram/dashboard nel codice attuale. Nessun test verifica `state.total_fees` (i test S118 su avg/invested/received/realized_pnl non lo asseriscono mai). Blast radius oggi minimo, ma il numero è sbagliato se in futuro viene esposto (es. un pannello "fee pagate su Kraken" per giudicare la sostenibilità del cutover).

_Verificatori (estratto):_ Confermo il bug con percorso concreto, verificato leggendo i file interi (non solo il diff).

CATENA VERIFICATA nel codice reale:
1. buy_pipeline.py:269 — `bot.state.total_fees += fee` (fee reale di acquisto, sempre eseguita in execute_percentage_buy).
2. sell_pipeline.py:468-469 — `cost_basis = amo...

---

## Respinti (i verificatori li hanno smontati — corroborano la verifica manuale)

- **(invariante-binance)** Floor min-profit: `not force_all` non è gated su venue — su binance blocca/sblocca sell diversamente da pre-diff
  - perché respinto: Ho letto il file intero bot/grid/sell_pipeline.py (925 righe), il diff completo 6a3c8ac..HEAD su quel file, grid_bot.py (righe 368-950, 1120-1164), config_sync.py (intero), allocator.py (righe 900-1400), web_astro/public/tf.html (righe 1600-1830) e tests/test_kraken_fase1_s118.py.

Fatti tecnici ver
- **(invariante-binance)** Cycle-fetch lato sito (6 file): il fallback hardcoded 'testnet_2' ora scatta anche senza errori di rete
  - perché respinto: Il diff (query change in live-stats.ts:57-59, e identico pattern negli altri 5 file) è confermato: `symbol=eq.BTC/USDT` → `is_active=eq.true&order=updated_at.desc&limit=1`, e il fallback `rows?.[0]?.cycle || CYCLE_FALLBACK` scatta anche su fetch riuscito con 0 righe — questa parte della descrizione 
- **(contabilita-fee)** Trigger di vendita grid (reference=last_sell_price) può scendere sotto il floor fee-aware (reference=avg_buy_price) dopo uno slippage avverso — lo "stallo silenzioso" che il commit dichiara di aver eliminato ha un caso residuo
  - perché respinto: Ho letto per intero bot/grid/grid_bot.py e bot/grid/sell_pipeline.py (non solo il diff) e ho riprodotto lo scenario con codice reale eseguito, non solo algebra.

Cosa il reviewer ha letto correttamente: il floor (sell_pipeline.py:298-305) è SEMPRE avg-based (`min_price = avg*(1+min_profit_pct/100+2*
- **(lifecycle-runtime)** sb_cfg può restare unbound se Supabase è irraggiungibile al boot: venue forzato a 'binance' invece del fallback EXCHANGE dichiarato
  - perché respinto: Ho verificato la meccanica Python del finding ed è corretta: `sb_cfg` (bot/grid_runner/__init__.py:89) è assegnata solo dentro il try che include anche `config_reader.load_initial()` (riga 88), la cui docstring dichiara esplicitamente "Raises if Supabase is unreachable" (config/supabase_config.py:12