# Report for CEO — S112b — kraken-adapter — 2026-06-30

**Brief sorgente:** `config/2026-06-29_S112_brief_kraken-adapter.md` (SCOPE `kraken-adapter`)
**Commit codice:** `83ad81f` (`feat(S112b): Kraken adapter dormant behind EXCHANGE flag`)
**Doc di supporto:** `config/2026-06-29_S112_passo0_kraken-coupling-map.md` (mappa), `config/2026-06-29_S112_piano_kraken-adapter.md` (piano)
**Esito:** SHIPPED (codice dormiente, **nessun restart**, **nessun cutover**). 271/271 test verdi.

---

## 0. TL;DR

Costruito l'**adapter Kraken dormiente dietro flag `EXCHANGE`** (default `binance`), **Approccio A**: capacità completa + testata, **hot-path NON cablato** (il cablaggio è il brief cutover). Con `EXCHANGE=binance` il comportamento è identico a prima (invariante §3 verificato: 271 test verdi, zero file dell'hot-path toccati). Lungo la strada lo scouting ha smontato due assunti del brief (sotto, §1), che hanno portato il Board a **ribaltare la valuta da USDC a USD**.

## 1. Anti-assenso — cosa lo scouting ha smontato (il vero valore della sessione)

Il brief assumeva "BTC/SOL/BONK tutti su USDC, spot reali, API trading reale". I dati live di Kraken hanno mostrato il contrario su due punti:

1. **BONK/USDC non è spot reale: è un mercato sintetico.** Badge "S", Kraken fa da controparte (entità derivati PEDSL-CY), volume USDC = 0.00. **L'API di trading non lo raggiunge** (`AssetPairs` → "Unknown asset pair"). Il "~113K" del brief era in realtà **BONK/USD** (~$120K). Verificato anche dalla UI di Max (screenshot).
2. **L'universo /USDC è troppo sottile per il TF.** 46 coppie, solo 3 liquide (≥$2M: BTC/ETH/SOL — già le coin del grid). "TF sceglie tra le /USDC" = menù vuoto. L'universo /USD invece è profondo (686 coppie, 19 liquide ≥$2M). L'USDC su Kraken è di fatto un'overlay sul mercato USD.

Inoltre, mischiare USD (BONK) + USDC (BTC/SOL) = due casse separate, e il bot **non converte da solo** → con un saldo USDC non potrebbe comprare in USD. Scartato.

## 2. Decisioni (Board-ratificate via Max, 2026-06-30)

- **USD per tutto su Kraken** (ribalta "USDC per tutti e tre"). USD è fiat → fuori dalle regole MiCA sulle stablecoin; Kraken offre le /USD spot ai clienti EU con licenza. Costo: una conversione EUR→USD una tantum (identica a EUR→USDC). Binance testnet **resta USDT**.
- **Lineup:** grid **BTC/USD + SOL/USD + BONK/USD** (BONK rientra); **TF $100** pesca dalle /USD.
- **Approccio A** (capacità completa dietro flag, hot-path al cutover) — invariante a rischio ~zero per costruzione.
- **Funding-rate resta su Binance** (dato pubblico, EU-ok); `binance_funding.py`/`binance_btc.py` non toccati.
- **Exit bot-side** (soglie S110d); `cancel_all_after` (dead-man switch) costruito ma **disarmato** (futura rete anti-blackout).
- **WebSocket executions = fast-follow** (pezzo a sé, subito dopo). Oggi il modello è polling, regge.
- **CMC F&G** = brief separato (probe S112b: F&G `latest`+`historical` disponibili sul piano da 15K crediti).

## 3. Cosa è stato costruito (commit `83ad81f`)

- **`config/settings.py`** — flag `EXCHANGE` (default `binance`) + `KrakenConfig` (QUOTE=USD, GRID_SYMBOLS BTC/SOL/BONK su USD). Additivo, dormiente.
- **`bot/exchanges/`** (nuovo package):
  - `base.py` — ABC `ExchangeClient` (superficie trading venue-agnostica; primitivi avanzati che su un venue non supportato **lanciano** invece di no-op silenzioso).
  - `binance_client.py` — `BinanceClient` che **delega verbatim** alle funzioni esistenti (`bot.exchange`, `bot.exchange_orders`, `utils.exchange_filters`). Con `EXCHANGE=binance` gira lo stesso codice di prima.
  - `kraken_client.py` — `KrakenClient` nativo ccxt.kraken: auth (nonce microsecondi, vedi rischio §5), risoluzione `AssetPairs`, order layer completo (market by-cost / by-base, limit, **AddOrderBatch**, **editOrder**, cancel/cancelAll, **cancelAllOrdersAfter**, **fetchTradingFee**), fee **reali** in USD (no `synth_fee`), `fee_base=0` (Kraken non preleva fee dal base coin), `fetch_filters`/`get_all_symbols` per il TF.
  - `__init__.py` — `create_client()` (factory dal flag; import Kraken lazy).
- **`tests/test_exchange_adapter_s112.py`** — 14 test (factory default=binance, delega Binance, primitivi Binance che lanciano, routing+fee-model Kraken, no-synth, filtro simboli).

**Verifica pubblica live** (no chiavi): `fetch_filters` risolve BTC/USD (min_qty 5e-05), SOL/USD (0.06), BONK/USD (min_qty 830K ≈ $3.5, step 0.01); `get_all_symbols("/USD")` = 686 coppie; prezzi pubblici ok.

## 4. Invariante §3 — verifica

- **271/271 test verdi** (257 esistenti + 14 nuovi). Nessun file dell'hot-path nel diff (buy/sell_pipeline, grid_bot, state_manager, grid_runner, orchestrator, reconcile, exchange.py, exchange_orders.py — **non toccati**).
- Default `EXCHANGE=binance` → `BinanceClient` che delega identico. Un `git pull` con flag a binance è un no-op sul testnet vivo. **Nessun restart eseguito** (regola §5; con Approccio A non serve).

## 5. Fee Kraken + ricalibrazione step (proposta, non hardcoded)

- Path Kraken: fee reali lette dal fill, in USD; isolate in `KrakenClient` → path Binance intatto.
- **Ricalibrazione step grid:** lo step minimo profittevole si allarga (fee Kraken 0,25% maker / 0,40% taker vs 0,10% Binance). **Non hardcodato**: quei parametri su testnet sono **Sherpa-managed** (regime×tier); proporre numeri fissi collide con l'ownership Sherpa. Proposta per il cutover: il **floor min-profit diventa fee-aware** (≥ 2× la fee del modello scelto), affidato a Sherpa/Board. Numeri concreti col modello-grid deciso (market vs limiti) al cutover.

## 6. Cosa NON è stato fatto (per disegno → cutover / fast-follow)

- **Cablaggio hot-path** (far tradare il grid via Kraken) — cutover, con primo ordine reale.
- **Chiavi API Kraken** — le genera Max nel `.env` Mac Mini (Withdraw OFF) quando serviranno le prove autenticate. Nomi: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`.
- **WebSocket executions** — fast-follow.
- **Frontend** (grafici Binance→Kraken, etichette USDT→USD, wording, pagina dormiente "live su Kraken/MiCA") — cutover. Touchpoint mappati nel Passo 0 §12.
- **Modello-grid** (market vs ladder a limiti) — deciso al cutover (incide sulla ricalibrazione fee).
- **Prova "ordine reale"** — impossibile ora (Kraken non ha testnet); avviene al cutover.

## 7. Rischi noti

- **Nonce multi-processo:** il grid lancia un processo per coin, tutti con la stessa chiave Kraken (nonce per-chiave). Mitigato con nonce a microsecondi; va **alzato anche il "Nonce Window"** lato account Kraken. Da rivalutare al cutover (subaccount per coin?).
- **Order layer non testato live** (mock + endpoint pubblici); prova vera al cutover.
- **`ordermin` BONK/USD** ~830K BONK (~$3.5): floor specifico da valutare al cutover per i micro-buy.

## 8. Output attesi (mapping brief §7)

1. ✅ Passo 0 (mappa) 2. ✅ Piano 3. ✅ Adapter dietro flag + invariante verificato 4. ✅ `AssetPairs` per le 3 coppie (USD) 5. ✅ Order layer completo (WS = fast-follow) 6. ✅ USD + fee reali + formula ricalibrazione (proposta) 7. ✅ Questo report.

## 9. Note per il CEO

- ⚠️ **BUSINESS_STATE §4 da correggere:** le righe S112 che avevo applicato dal tuo blocco dicono ancora "USDC per-exchange / BONK/USDC verificata". Sono **superate** (USD per tutto; BONK/USDC era sintetico). Mandami il blocco aggiornato e lo applico (non tocco BUSINESS_STATE di iniziativa).
- ⚠️ **Cadenza audit:** Area 1 e Area 3 ultime al **2026-06-01** (29 giorni fa, cadenza mensile 30gg) → **dovute a brevissimo (~01/07)**. Proponi di pianificarle. Area 2 ok (06-19, event-based + backstop 60gg).
- **Roadmap pubblica:** non aggiornata — l'adapter è dormiente, nessun cambiamento pubblico. Il pivot Kraken diventa pubblico al cutover (pagina dormiente + dashboard), territorio CEO/marketing.
