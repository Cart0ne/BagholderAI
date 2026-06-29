# Piano S112 — Kraken adapter (dormiente dietro flag)

> **Brief sorgente:** `config/2026-06-29_S112_brief_kraken-adapter.md` (SCOPE `kraken-adapter`).
> **Passo 0 (mappa):** `config/2026-06-29_S112_passo0_kraken-coupling-map.md` (approvato).
> **Stato:** PIANO in attesa di approvazione Max/CEO. **Nessun codice scritto finché non approvato** (CLAUDE.md §3).

---

## 1. Obiettivo (e cosa NON è)

Costruire l'**adapter Kraken** come capacità **dormiente** selezionata dal flag `EXCHANGE` (default `binance`). Il bot continua a girare su Binance testnet, **identico a prima**. Questo brief **non è il cutover**: niente flip in produzione, niente ordine reale, niente collaudo €100, niente frontend.

## 2. Decisioni consolidate (Max + CEO, 2026-06-29)

| # | Decisione | Effetto sul piano |
|---|---|---|
| D1 | USDC **solo** su Kraken; Binance resta USDT | La valuta-quote diventa funzione del flag, mai un cambio globale |
| Funding | Resta su **Binance** (dato pubblico, EU-ok) | `binance_funding.py` e `binance_btc.py` **NON si toccano** |
| Regime/meteo | Sentinel/Sherpa continuano a leggere il mercato da Binance | L'astrazione copre solo il **path di trading**, non il regime |
| D3 exit | **Bot-side** (soglie S110d). Guard nativi Kraken solo come rete anti-blackout futura | Nessun exit nativo Kraken. Il "dead-man switch" (`cancel_all_after`) si **costruisce** ma resta **disarmato** = è la casa tecnica della futura idea anti-blackout |
| CMC F&G | Brief separato | Fuori da S112 |
| Frontend | Cutover | Mappato, fuori da S112 |

## 3. Architettura

Interfaccia `ExchangeClient` (classe base) + `ExchangeFactory.create(EXCHANGE)`. Due implementazioni:
- **`BinanceClient`** — **delega** alle funzioni Binance esistenti (`bot/exchange.py`, `bot/exchange_orders.py`, `utils/exchange_filters.py`) **senza riscriverle**. Con `EXCHANGE=binance` gira lo stesso identico codice di oggi.
- **`KrakenClient`** — **tutto nuovo**: ccxt.kraken + REST/WS dove serve. Fee reali (no `synth_fee`), USDC quote, naming via `AssetPairs`.

**Layout proposto** (interno, delegato a CC dal brief §6): package `bot/exchanges/` con `base.py` (ABC), `binance_client.py`, `kraken_client.py`, `__init__.py` (factory). `bot/exchange.py` e `bot/exchange_orders.py` **restano dove sono** (li chiama `BinanceClient`).

**Cosa NON entra nell'astrazione** (resta Binance sempre, per scelta Max): `bot/sentinel/inputs/binance_btc.py`, `bot/sentinel/inputs/binance_funding.py`. Il "meteo" si legge da Binance a prescindere dal flag.

---

## 4. DECISIONE CHIAVE — quanto cablare ORA (A vs B)

Questo è il punto che la auto-obiezione del CEO (brief §9) anticipava: l'astrazione può essere conservativa o invasiva. Due approcci:

**Approccio A — "adapter pronto ma non cablato sull'hot-path" (RACCOMANDATO da CC).**
Costruisco factory + `BinanceClient` (delega) + `KrakenClient` **completo** + test. **NON tocco** l'hot-path live (`buy_pipeline`, `sell_pipeline`, `grid_bot`, `state_manager`, `reconcile_binance`, `grid_runner`, `orchestrator`). Il flag seleziona il client; `KrakenClient` è costruito e testato **in isolamento**; il collegamento del grid live al client avviene nel **brief cutover** (quando si testano ordini veri).
- ✅ Invariante a **rischio ~zero per costruzione**: l'hot-path non viene proprio toccato → `git pull` con `EXCHANGE=binance` non può cambiare nulla.
- ✅ Coerente con "adapter dormiente, non cutover".
- ⚠️ "Funzionante dietro flag" è vero a livello di **client** (testabile, completo), non ancora a livello di "grid che trada via Kraken" — quello è il cutover.

**Approccio B — "adapter cablato dietro flag" (lettura letterale del brief §7.3).**
Oltre ad A, **rifaccio passare l'hot-path attraverso l'astrazione** (le pipeline chiamano `client.place_market_buy()` invece della funzione diretta; `BinanceClient` delega identico). Flippando `EXCHANGE=kraken` il grid traderebbe davvero via Kraken (con le chiavi).
- ✅ Più vicino alla lettera del brief.
- ⚠️ Tocca l'**hot-path live** = rischio invariante **reale**, mitigato da delega-identica + suite test + diff comportamentale, ma è il punto dove "si infila il rischio di rompere il testnet" (parole del CEO §9).

**Raccomandazione CC: Approccio A.** Costruiamo e collaudiamo tutta la capacità Kraken adesso, lasciando il cablaggio rischioso dell'hot-path al cutover, dove lo verifichiamo insieme al primo ordine reale e alla scelta del modello-grid (punto 5). Se tu/CEO preferite B, lo faccio — ma allora il restart del bot per testare l'invariante diventa parte del lavoro.

---

## 5. DECISIONE CHIAVE — modello-grid su Kraken (market vs limite)

Il brief §4 elenca `AddOrderBatch` (scale del grid in un colpo), `EditOrder` (riposiziona livelli), `cancel_all_after`. Questi hanno senso pieno solo con un grid a **ordini limite a riposo** (ladder), che è un modello **diverso** da quello attuale (oggi il grid spara **ordini a mercato** quando il prezzo tocca un trigger).

- **Modello 1 — porting attuale:** Kraken replica market-order-on-trigger. Semplice, stesso comportamento di oggi. Paga fee **taker** (0,40%).
- **Modello 2 — grid nativo a limiti:** ladder a riposo via `AddOrderBatch`, riposizionato con `EditOrder`, protetto da `cancel_all_after`. Fee **maker** (0,25%), usa tutti i primitivi del brief. Ma è un **nuovo modello di trading** (cambia il comportamento del grid).

**Proposta CC per S112:** in `KrakenClient` **costruisco TUTTI i primitivi** (market *e* limit/batch/edit/cancel/cancel_all_after) così la cassetta degli attrezzi è completa, ma **NON scelgo il modello-grid ora** — è una decisione di trading-logic che appartiene al cutover (e impatta la ricalibrazione fee, punto 7). Così non ci leghiamo le mani e non cambiamo comportamento di trading in un brief che deve restare dormiente.

---

## 6. Piano per fasi (Approccio A)

**Fase 0 — Flag + env (additivo, default invariato).**
- `config/settings.py` — aggiungo `EXCHANGE` (default `"binance"`) + lettura `KRAKEN_API_KEY`/`KRAKEN_API_SECRET`. Con default `binance` → zero diff. (file toccato: 1, additivo)

**Fase 1 — Scaffolding astrazione (tutto nuovo).**
- `bot/exchanges/base.py` — ABC `ExchangeClient`.
- `bot/exchanges/binance_client.py` — `BinanceClient` che **delega** alle funzioni esistenti.
- `bot/exchanges/__init__.py` — `ExchangeFactory`.

**Fase 2 — `KrakenClient` (il grosso, tutto nuovo).**
- Auth: ccxt.kraken (HMAC-SHA512 + nonce gestiti da ccxt; nonce window alto per multi-thread).
- `AssetPairs`: risolve `BTC/USDC`, `SOL/USDC`, `BONK/USDC` → nome canonico Kraken + `pair_decimals`/`lot_decimals`/`ordermin`. Implementa `fetch_filters` e `get_all_symbols` lato Kraken.
- Order layer REST: `AddOrder` (market+limit), `AddOrderBatch` (≤15), `EditOrder`/amend, `CancelOrder`/`CancelAll`, `cancel_all_after` (dead-man switch, costruito ma disarmato).
- Fee: lette dal fill (reali, in quote); lettura fee-tier + volume 30gg. **`synth_fee` NON esiste in questo path.**
- `fetch_balance`/`fetch_my_trades` lato Kraken (quote = USDC).

**Fase 3 — WS `executions` (add-on più pesante; vedi nota sotto).**
- Feed WebSocket `executions` per i fill in tempo reale (auth via `GetWebSocketsToken`). **Non esiste WebSocket oggi** (tutto polling) → è codice nuovo a sé.

**Fase 4 — Test + verifica invariante.**
- Test `KrakenClient` (mock per l'order layer — Kraken non ha testnet; live read-only sugli endpoint pubblici `AssetPairs`/`Depth` dove possibile senza chiave).
- Test invariante: con `EXCHANGE=binance` la suite attuale (257 test) resta verde + `ExchangeFactory` di default ritorna `BinanceClient`.

> **Nota su Fase 3 (WS):** il brief la elenca nell'order layer, ma per un adapter **dormiente** che oggi userebbe comunque polling, il feed WS è l'unico pezzo davvero "nuovo di paradigma". **Proposta:** la includo in S112 se vuoi l'adapter completo; oppure la marco come **fast-follow** subito dopo, per tenere S112 più stretto e a minor rischio. **Dimmi tu.** (Tutto il resto — Fasi 0/1/2/4 — è il cuore e lo faccio comunque.)

---

## 7. Fee Kraken + ricalibrazione step

- Path Kraken: fee **reali** lette dal fill, niente `synth_fee`. Isolato in `KrakenClient` → non tocca il path Binance.
- **Ricalibrazione step grid / soglie profitto** (brief §5): lo step minimo profittevole si allarga (fee 0,25–0,40% vs 0,10%). **Ma** questi parametri su testnet sono **Sherpa-managed** (dinamici, regime×tier), non costanti — proporre numeri fissi collide con l'ownership Sherpa (Board=soldi, Sherpa=strategia). Inoltre dipende dal modello-grid (punto 5: maker 0,25% vs taker 0,40%).
- **Proposta:** in S112 **non hardcodo** nuovi step. Documento la formula del break-even fee-aware e propongo che, al cutover, il **floor min-profit** diventi fee-aware (≥ 2× fee del modello scelto) — da affidare a Sherpa o al Board. Numeri concreti → brief cutover, con il modello-grid deciso.

## 8. Cosa NON cambia (invariante) + verifica

- **Non tocco** (Approccio A): `buy_pipeline`, `sell_pipeline`, `grid_bot`, `state_manager`, `grid_runner`, `orchestrator`, `reconcile_binance`, `exchange.py`, `exchange_orders.py`, `exchange_filters.py`, e i due input Sentinel.
- **Verifica invariante:** suite 257 test verde con default; nessun file dell'hot-path nel diff; `git pull` con `EXCHANGE=binance` = no-op sul testnet vivo. **Niente restart del bot in S112** (regola §5: il restart lo chiedi tu; e con A non serve nemmeno).

## 9. Rischi noti

1. **ccxt.kraken copertura parziale:** `AddOrderBatch`, `EditOrder`, `cancel_all_after`, `GetWebSocketsToken` potrebbero non essere tutti esposti da ccxt → in quei casi REST raw. Lo verifico in Fase 2; se un primitivo richiede REST raw lo isolo nel client.
2. **Niente testnet Kraken:** l'order layer si testa con mock; la prova "ordine vero" è il cutover (per disegno). Lo dichiaro, non lo nascondo.
3. **`ordermin`/precision BONK/USDC:** book sottile; da risolvere via `AssetPairs` (no hardcode). Eventuale floor specifico → cutover.
4. **Se si sceglie Approccio B:** rischio invariante reale sull'hot-path → mitigato da delega-identica + test + diff, ma richiede restart di verifica.

## 10. Env vars + permessi chiave (per quando Max le genera — NON ora)

- Nomi var proposti: `EXCHANGE` (binance|kraken), `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`. In `config/.env` (gitignored, verificato).
- Permessi chiave Kraken (da impostare alla generazione): Query Funds · Query Open/Closed Orders & Trades · Modify Orders · Cancel/Close Orders · Access WebSockets API. **Withdraw Funds → OFF.**
- **CC non genera né maneggia le chiavi** (brief §8): le mette Max nel `.env` del Mac Mini. Io definisco solo i nomi.

## 11. Output attesi (mapping brief §7)

1. ✅ Passo 0 (mappa) — fatto, approvato.
2. ⏳ Piano (questo documento) — da approvare.
3. Adapter Kraken dietro flag, invariante `EXCHANGE=binance` verificato (Approccio A: capacità completa + testata; cablaggio hot-path al cutover).
4. `AssetPairs` per le 3 coppie con precisioni/minimi.
5. Order layer completo (place/batch/amend/cancel/cancel-after-x/fee-tier; WS = da decidere punto 6).
6. USDC + fee reali sul path Kraken + formula ricalibrazione step (proposta, non hardcoded).
7. Report `2026-06-29_S112_RforCEO_kraken-adapter.md` con commit hash.

---

## 12. Cosa mi serve per partire col codice

1. **Approvazione del piano.**
2. **A vs B** (punto 4) — io vado con **A** salvo tuo stop.
3. **WS executions** (punto 6, Fase 3) — dentro S112 o fast-follow?
4. Modello-grid (punto 5) lo lascio **deciso al cutover**, salvo tu voglia anticiparlo.
