# Passo 0 — Mappa accoppiamento exchange (Binance → astrazione Kraken)

> **Brief sorgente:** `config/2026-06-29_S112_brief_kraken-adapter.md` (SCOPE `kraken-adapter`).
> **Sessione:** S112 (confermata da Max 2026-06-29).
> **Stato:** DRAFT in attesa di approvazione Max/CEO. Analisi **sola-lettura**, nessun codice modificato.
> **Decisioni Max al 2026-06-29 (tutte chiuse):** D1 = per-exchange (USDC solo su Kraken, Binance resta USDT) ✅ · grafici prezzo → Kraken (cutover) ✅ · funding-rate = **resta su Binance** (opzione a) ✅ · D3 exit = **bot-side** (soglie S110d), eventuali guard nativi Kraken solo come rete anti-blackout futura ✅ · CMC F&G = brief separato ✅.
> **Scopo:** elencare tutti i punti dove il codice è accoppiato a Binance e proporre dove mettere il confine dell'astrazione `ExchangeClient`. È il deliverable #1 del brief (§7).

---

## 0. Sintesi per Max (livello dominio)

L'astrazione **è fattibile**: si introduce un'interfaccia `ExchangeClient` con due implementazioni (`BinanceClient` esistente + `KrakenClient` nuovo), scelte a runtime dal flag `EXCHANGE` (default `binance`). Il path Binance resta intatto; Kraken si aggiunge accanto.

Quattro zone di accoppiamento, in ordine di pericolo per l'invariante "EXCHANGE=binance = comportamento identico":

| Zona | Cosa | Rischio invariante |
|------|------|--------------------|
| 1. Valuta quote (USDT) | `*/USDT` cablato in 50+ punti (config, scanner, whitelist, split) | 🔴 ALTO — tocca codice condiviso (collisione §3↔§5 USDC) |
| 2. Fee handling | fee BUY in base coin (72a) + `synth_fee` testnet 0,1% sparsi tra buy/sell/reconcile | 🔴 ALTO — modello Kraken diverso (fee reali in quote) |
| 3. Sentinel/Sherpa market data | chiamate REST dirette a `api.binance.com` + `fapi.binance.com` (no ccxt) | 🟠 MEDIO — decisione: regime resta su Binance o migra? |
| 4. Client/ordini/filtri | già incanalato in poche funzioni (factory + ccxt) | 🟢 BASSO |

Nessun WebSocket oggi (tutto polling) → il feed `executions` Kraken (§4 brief) è funzionalità nuova, non un rimpiazzo.

---

## 1. Auth / connessione exchange

- **config/settings.py:26-28** — `ExchangeConfig.API_KEY/SECRET/TESTNET` da env `BINANCE_API_KEY`, `BINANCE_SECRET`, `BINANCE_TESTNET`. **ALTO** (prefisso `BINANCE_` hardcoded).
- **bot/exchange.py:24-64** — `create_exchange()`: istanzia `ccxt.binance(...)`, `set_sandbox_mode(True)` se testnet, opzione `createMarketBuyOrderRequiresPrice=False` (brief 73c). **ALTISSIMO** (istanzia direttamente `ccxt.binance`). → punto naturale per la factory.
- **bot/exchange.py:67-111** — `test_connection()`: fetch `BTC/USDT` di prova + `fetch_balance()`. **MEDIO**.
- **bot/orchestrator.py:65-110** — spawn figli via `Popen` senza passare config: i figli leggono le env globali. **BASSO**.
- **bot/grid_runner/__init__.py:146** — `exchange = create_exchange()` per ogni grid. **MEDIO**.

## 2. Naming coppie / quote currency (USDT)

- **config/settings.py:247/261/275** — `symbol="BTC/USDT"`, `"SOL/USDT"`, `"BONK/USDT"`. **ALTISSIMO**.
- **bot/exchange.py:75** — `fetch_ticker("BTC/USDT")`. **ALTISSIMO**.
- **bot/grid_runner/__main__.py:18** — default symbol `"BTC/USDT"`. **ALTISSIMO**.
- **bot/sherpa/volatility.py:39** — `ANCHOR_SYMBOL = "BTC/USDT"`. **ALTISSIMO**.
- **bot/exchange_orders.py:276** — `quote_coin = symbol.split("/")[1].upper() if "/" in symbol else "USDT"`. **MEDIO** (default USDT).
- **scripts/reconcile_binance.py** — assume USDT come quote ovunque. **MEDIO-ALTO**.
- **bot/trend_follower/scanner.py:13-16** — blacklist stablecoin tutte `/USDT`. **ALTISSIMO**.
- **bot/trend_follower/trend_follower.py:134-135** — `[s for s in exchange.markets if s.endswith("/USDT")]`. **ALTISSIMO**.
- **bot/trend_follower/allocator.py:15** — `MANUAL_WHITELIST = {"BTC/USDT","SOL/USDT","BONK/USDT"}`. **ALTISSIMO**.

## 3. Ordini: place / cancel / parse

- **bot/exchange_orders.py:75-104** — `place_market_buy()` con `quoteOrderQty` (Binance-specific). **ALTISSIMO**.
- **bot/exchange_orders.py:107-149** — `place_market_buy_base()` (brief 73c, evita `quoteOrderQty` con filtri noti). **ALTISSIMO**.
- **bot/exchange_orders.py:152-180** — `place_market_sell()`. **ALTISSIMO**.
- **bot/exchange_orders.py:183-338** — `_normalize_order_response()`: parsing risposta ccxt, fallback `info.orderId` (S109), risoluzione fee base-vs-quote. **ALTISSIMO**.
- **bot/grid/buy_pipeline.py:152-194** / **sell_pipeline.py:383-394** — chiamano i wrapper. **MEDIO** (delegato).

## 4. Fee — CRITICO

- **bot/grid/grid_bot.py:85** — `FEE_RATE = 0.001  # 0.1%`. **ALTISSIMO**.
- **bot/grid/buy_pipeline.py:199-201** — `synth_fee = (fee == 0); if synth_fee: fee = cost * bot.FEE_RATE` (S96b option B: testnet Binance non addebita fee). **ALTISSIMO**.
- **bot/grid/buy_pipeline.py:218-220** — paper mode `fee = cost * FEE_RATE`. **ALTISSIMO**.
- **bot/grid/sell_pipeline.py:398-404** — synth fee identico lato sell. **ALTISSIMO**.
- **bot/grid/sell_pipeline.py:431** — `buy_fee = cost_basis * FEE_RATE` (backward-compat). **ALTISSIMO**.
- **bot/exchange_orders.py:243-298** — legge `order["fee"]/["fees"]`, converte a USDT: se fee in quote→tieni, se in base→×fill_price, se in BNB→0+warning. **ALTISSIMO** (Binance: BUY fee in base coin).
- **scripts/reconcile_binance.py:93-102** — `fee_usdt += fcost * price` (BUY fee in base). **ALTISSIMO**.

> ⚠️ **Divergenza comportamentale Kraken (brief §5):** Kraken applica fee **reali** (base tier ~0,25% maker / 0,40% taker) in **quote currency** dal primo ordine, e **non ha testnet a fee-zero**. Quindi su path Kraken: (1) `synth_fee` non si attiva mai; (2) le fee si leggono dal fill; (3) niente conversione base→quote per il BUY. Da isolare in `KrakenClient.normalize_order_response()`.

## 5. Fetch prezzi / candele

- **bot/exchange.py:114-119** — `fetch_ticker(exchange, symbol)`. **MEDIO**.
- **bot/grid_runner/lifecycle.py:25** — wrapper `fetch_ticker`. **BASSO**.
- **bot/sentinel/inputs/binance_btc.py:20** — `_BASE = "https://api.binance.com"` (REST diretto, no ccxt). **ALTISSIMO**.
  - `:24-43` `fetch_ticker_24hr("BTCUSDT")`; `:46-57` `fetch_price`; `:60-73` `fetch_klines_1m`; `:76-89` `fetch_klines_1h`.
- **bot/sentinel/inputs/binance_funding.py:16** — `_BASE = "https://fapi.binance.com"`; `:20-39` `fetch_funding_rate("BTCUSDT")` (futures API). **ALTISSIMO** — segnale Binance-futures, non esiste tale-quale su Kraken.
- **bot/trend_follower/scanner.py:80/110/165** — `fetch_ohlcv` / `fetch_tickers`. **MEDIO**.
- **bot/trend_follower/counterfactual.py:110** — `fetch_ohlcv(symbol,"1h",30)`. **MEDIO**.

## 6. Reconcile / saldi

- **bot/exchange.py:92** — `fetch_balance()` → `balance["USDT"]["total"]`. **ALTISSIMO**.
- **bot/grid/state_manager.py:287/407/411** — `fetch_balance()` boot + post-fill, `balance[coin]["total"]`. **ALTISSIMO**.
- **scripts/reconcile_binance.py:259** — `fetch_my_trades(symbol, limit)`. **ALTISSIMO**.
- **scripts/reconcile_binance.py:72-118** — `aggregate_binance_fills()` per `orderId` (campo Binance). **ALTISSIMO**.

## 7. Lot size / precision / min notional

- **utils/exchange_filters.py:14-49** — `fetch_filters()` via `load_markets()`: min_notional, min_qty, lot_step_size (commento: "for Binance, ccxt precision.amount IS the step size"). **ALTISSIMO**.
- **utils/exchange_filters.py:52-75** — `fetch_and_cache_filters()` → upsert Supabase `exchange_filters`. **ALTISSIMO**.
- **bot/grid/buy_pipeline.py:164-177** / **sell_pipeline.py:344-371** — uso filtri (round a step, dust prevention). **MEDIO / MEDIO-ALTO**.
- **utils/exchange_filters.py:142-162** — `is_dust()` (S105b), fallback `_DUST_NOTIONAL_FALLBACK=0.50`. **MEDIO**.

## 8. WebSocket

Nessuno. Tutto polling (grid tick periodico, Sentinel monitoring passivo). Il feed `executions` Kraken sarebbe **nuovo**.

## 9. Orchestrator / spawn

- **bot/orchestrator.py** — non passa config esplicita; figli leggono env globali (`os.getenv("BINANCE_*")`). **BASSO**.
- **config/settings.py:26-28** — `ExchangeConfig` caricato al module-load da ogni processo. **MEDIO**.

---

## 10. Proposta confine astrazione

Interfaccia `ExchangeClient` (ABC) con i metodi: `test_connection`, `fetch_ticker`, `fetch_price`, `fetch_klines`, `fetch_tickers_all`, `place_market_buy`, `place_market_buy_base`, `place_market_sell`, `normalize_order_response`, `fetch_balance`, `fetch_my_trades`, `fetch_filters`, `load_markets`, `get_all_symbols(quote_suffix)`.

Implementazioni: `BinanceClient` (logica attuale, incl. REST Sentinel + fee base-coin + synth_fee), `KrakenClient` (ccxt.kraken, fee reali in quote, naming AssetPairs, no synth_fee). Selezione via `ExchangeFactory.create(os.getenv("EXCHANGE","binance"))`.

Livelli di isolamento consigliati:
1. **Creazione client** — `bot/exchange.py` → factory. (facile)
2. **Fee handling** — spostare `_normalize_order_response` dentro `ExchangeClient`, override per subclass. (CRITICO)
3. **Filter fetching** — delegare `fetch_filters` al client. (semi-critico)
4. **Sentinel inputs** — wrapper agnostico sopra `binance_btc.py`/`binance_funding.py`, oppure decisione "regime resta su Binance". (isolato/decisione)
5. **Symbol enumeration** — `ExchangeClient.get_all_symbols(quote_suffix)` al posto di `endswith("/USDT")`. (CRITICO per TF)

---

## 11. Rischi per l'invariante §3 + decisioni aperte

**Rischi (engineering):**
1. **Fee conversion (exchange_orders.py:259-298)** — logica base-coin (72a) è Binance-only; Kraken in quote → override totale in `KrakenClient`. ALTA.
2. **Synth fee testnet (buy/sell_pipeline)** — comportamento Binance-only sparso → isolare via flag `supports_zero_fee_testnet`/path client. ALTA: se toccato male rompe Binance.
3. **Quote `/USDT` (50+ punti)** — centralizzare in helper/`get_all_symbols`. ALTA.
4. **Sentinel REST diretto** — wrappare o decidere "regime su Binance". MEDIA.
5. **Filter parsing** — ccxt dovrebbe normalizzare; verificare su Kraken. MEDIA.

**Decisioni che salgono a Max/CEO (non le prende CC):**
- **D1 — USDT→USDC: per-exchange (dietro flag) o globale?** ✅ **DECISO (Max, 2026-06-29): per-exchange.** USDC si accende con `EXCHANGE=kraken`; Binance testnet resta USDT. Preserva l'invariante §3.
- **D2 — Sorgente dati di regime dopo il cutover.** ✅ **PARZIALE (Max, 2026-06-29): i grafici prezzo/moneta migrano su Kraken.** Resta da scegliere il **funding-rate** (segnale futures che oggi Sherpa legge da Binance): (a) lasciarlo su Binance (dato pubblico, EU-ok, zero lavoro) — racc. CC; (b) prenderlo da Kraken Futures (coerenza, lavoro extra). + il F&G aggiunge **CMC** come 2ª fonte (brief parcheggiato a parte, vedi sotto).
- **D3 — Exit nativi Kraken vs bot-side (brief §6).** Trailing/TP nativi Kraken vs soglie S110d già nel bot. CC propone pro/contro nel piano; sceglie Max. APERTA.

---

## 12. Frontend (SCOPE CUTOVER — fuori da S112, mappato su richiesta Max)

Il brief §8 mette esplicitamente le dashboard pubbliche fuori da S112. Mappo qui i touchpoint perché al **cutover** non sfuggano. **Da NON toccare ora.**

**A. Logica dati live (da migrare — prezzi/valuta):**
- `web_astro/src/scripts/live-stats.ts`, `dashboard-live.ts`, `dashboard-reconciliation.ts`
- `web_astro/src/lib/pnl-canonical.ts` + `web_astro/public/lib/pnl-canonical.js` (le 2 copie del P&L)
- `web_astro/src/pages/dashboard.astro`
- `web_astro/src/data/dashboard-mock.ts`

**B. Pannelli privati (grafici prezzo da Binance klines → Kraken):**
- `web_astro/public/admin.html`, `grid.html`, `tf.html` (grafici klines + etichette USDT)

**C. Branding/wording "Binance testnet" → "Kraken live":**
- `web_astro/src/components/TestnetBanner.astro`, `SiteHeader.astro`, `src/layouts/Layout.astro`, `src/components/office/LabRoom.jsx`
- pagine: `howwework.astro`, `income.astro`, `blueprint.astro`, `src/data/roadmap.ts`, `public/llms.txt`

**D. Editoriale/storico — NON migrare (è racconto storico, immutabile):**
- tutti i `web_astro/src/content/blog/*.md` (citano Binance/USDT come fatto del momento in cui furono scritti). Coerente con la regola "the story is the process, non i numeri".

> Distinzione chiave al cutover: **A+B+C** sono funzionali/branding e vanno aggiornati; **D** resta com'è.
