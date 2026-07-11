# Piano S118 — Cutover Kraken, FASE 1 (pre-lavori senza fermo)

> **Brief sorgente:** `config/2026-07-11_S117_brief_kraken-cutover.md` (SCOPE `kraken-cutover`),
> risequenziato da Max in Fasi 0-4 (report S117b). Questa è la **Fase 1**.
> **Approvato da Max in conversazione (2026-07-11)** con scioglimento nodi 1-4;
> nodo 5 (valori di ricalibrazione) rinviato alla Fase 2 — non blocca (i valori
> vivono nelle righe bot_config Kraken, che si inseriscono solo in Fase 2).
> **Base:** Fase 0 verde (plumbing check, fee taker reale 0,80% tier-0).

## Nodi sciolti da Max

| # | Nodo | Decisione |
|---|------|-----------|
| 1 | Venue: flag globale `EXCHANGE` vs per-riga | **Per-riga** (`bot_config.venue`); `EXCHANGE` resta solo fallback. Fase 2 = flip a DB, niente env. |
| 2 | Bonifica lexical-drift sito (cycle fetch) in Fase 1 | **Sì** — 7 superfici + `get_current_cycle` rese venue-robuste (zero diff oggi). |
| 3 | Gate real-money | **Sì** — runner `venue=kraken` live parte solo con chiavi Kraken **e** `ALLOW_REAL_MONEY=true` (step del runbook Fase 2). |
| 4 | Disclaimer-toggle | **Tabella nuova `site_flags`** (non estendere project_status); FOUC/fail-mode accettati, piano B = redeploy manuale. |
| 5 | Margine floor + passi collaudo | **Rinviato a Fase 2** (spiegazione nel report S118). Proposta CC: `profit_target_pct=0.4` sulle righe Kraken; passi in tabella al momento dell'insert. |

## Pacchetti (tutti gated: `venue='binance'` = zero diff, invariante S112)

- **DB**: `bot_config.venue` TEXT NOT NULL DEFAULT 'binance' CHECK (binance|kraken) + tabella `site_flags` (riga singola, anon read-only). Applicate a prod via MCP, SQL in `db/migration_20260711_s118_*.sql`.
- **A — Cablaggio**: grid_runner crea il client dalla factory S112 per-riga (`create_client(venue)`); ordini/balance/filtri via client (BinanceClient delega verbatim); `exchange` raw preservato per i call-site read-only. Gate live-mode venue-aware (nodo 3). `KRAKEN_GRID_INSTANCES` separata per le cadenze /USD (GRID_INSTANCES resta Binance-only: daily report, reconcile cron, cache filtri).
- **B — Fee dinamica**: `bot.fee_rate` di istanza, unica sorgente per i 7 punti che usavano la costante 0,1%. Su Kraken = taker tier LIVE via `KrakenClient.taker_fee_rate()` (cache 1h, fallback prudente 0,008 solo su errore API), refresh per tick via config_sync.
- **C — Floor fee-aware**: guard sell (`sell_pipeline`) → `min_price = avg × (1 + profit_target_pct/100 + 2×fee)` su Kraken; trigger sell (`grid_bot`) sullo stesso `fee_rate`. I due punti si muovono insieme (anti-stallo). `force_all` (uscite d'emergenza) esente dal floor.
- **D — Fix contabile fee-in-quote**: fee BUY USD → cost basis + invested; fee SELL USD → received netto; `_available_cash` torna specchio del wallet (anti-overspend SWEEP/LAST SHOT). Mirror identico nel boot replay (`state_manager`).
- **E — Hands-off**: Sherpa salta righe `venue='kraken'` (BOARD_TABLE azzererebbe il floor); `venue` in `_CONFIG_FIELDS`; allocator TF scrive `venue='binance'` esplicito; orchestrator logga il venue allo spawn (resta is_active-driven). **Isolamento collaudo = flip `is_active` a DB, zero codice nuovo** (i runner si spengono senza liquidare; orphan-reconciler non interferisce, tocca solo righe tf).
- **Bonifica (nodo 2)**: query cycle = "riga grid ATTIVA più recente" ovunque (via letterali `BTC/USDT`; CleanSlateSticker non più non-deterministico; `get_current_cycle` non più max() lessicografico).
- **F — Disclaimer-toggle**: `DisclaimerGate.astro` (overlay solo-homepage, nascosto) + fetch `site_flags` in live-stats.ts. Flip = UPDATE SQL, zero deploy, riusabile BTC→SOL→BONK. Spedito SPENTO. Immagine curata = asset pending (Max/CEO).
- **G — Prova generale**: `kraken_cutover_check.py` step 6 — validate=true attraverso i metodi del client che il grid chiama davvero, a taglie $25. **Eseguita sul Mac Mini: 28 check, 0 FAIL.**

## Cosa NON tocca la Fase 1 (off-limits)

TF (congelato, cablaggio post-collaudo), Sentinel (verificato: non legge bot_config), comportamento Binance, restart dei bot (li decide Max), ordini reali, righe bot_config Kraken (inserite in Fase 2), Modello B ladder (ri-esame Board pre-deployment coi numeri fee veri), K.3 completo (solo il toggle), BUSINESS_STATE.

## Residui per Fase 2 (runbook)

1. Insert righe `BTC/USD`/`SOL/USD`/`BONK/USD` con venue='kraken', cycle nuovo, parametri collaudo (tabella da chiudere con Max — nodo 5).
2. Flip `is_active` (solo BTC/USD on), TF off via trend_config, disclaimer on, `ALLOW_REAL_MONEY=true` nell'env del processo.
3. Superfici sito non-cycle ancora Binance-only da gestire nella finestra (mappate, fuori scope Fase 1): prezzi hero/instruments dashboard, market prices admin, mixer label `/USDT`, daily report Telegram aggregato cross-venue, `_force_liquidate` (bookkeeping-only), MANUAL_WHITELIST TF senza /USD, aggregati health_check/cash_audit/TF sum_total_capital.
4. Asset immagine disclaimer.
5. Nonce Window account-side (K.4).
