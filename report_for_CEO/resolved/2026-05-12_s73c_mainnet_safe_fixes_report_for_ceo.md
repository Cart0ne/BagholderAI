# CEO Report — Session 73c: 2 mainnet-safe fixes

**Data:** 2026-05-12 13:05 UTC
**Sessione:** S73 (continua da S73a + S73b di ieri sera/stamattina)
**Verdict:** SHIPPED, live, verificato. 22/22 test verdi.

---

## TL;DR

Identificati e risolti 2 bug emersi durante l'osservazione live post-S73a/b:

1. **BONK BUY rejected -2010 LOT_SIZE** (6 volte tra 10:30-10:32 UTC) — `quoteOrderQty` di Binance ricalcolava il base amount sul fill_price slipped, violando lot_step compliance su book sottile. **Su mainnet** sarebbe scattato lo stesso pattern su coin a basso prezzo o book sottili.
2. **BTC stop_buy fantasma** — calcolo `unrealized = (current−avg) × state.holdings` includeva 1 BTC fantasma testnet (gifted al boot), drogando il numero per ordini di grandezza ("$-5,308" mostrato vs ~$-0.50 reale). **Su mainnet** lo stesso pattern sarebbe scattato in caso di deposito manuale di coin esterni al bot.

Entrambi i fix sono **mainnet-safe by construction**: stesso codice si comporta identico (o meglio) su mainnet.

---

## Diagnosi 1 — BONK LOT_SIZE rejection loop

### Sintomo
6 tentativi di BUY BONK tra 10:30:24-10:32:11 UTC tutti rejected con:
```
InvalidOrder: code -2010, Order book liquidity is less than LOT_SIZE filter minimum quantity
```
Poi il 7° tentativo (LAST SHOT path) FILLED a 10:32:32 (id=20997, 3,324,468 BONK @ $0.00000752).

### Root cause
Il bot usava `quoteOrderQty=$25` per dire a Binance "compra $25 USDT di BONK". Su book sottile (BONK lot_step=1, depth ~$50), Binance:
1. Riceve quote-order da $25
2. Computa `amount = $25 / fill_price_slipped` (es. $25 / $0.00000752 = 3,324,468.085...)
3. amount non divisibile per lot_step=1 → rejection

Il pre-rounding pre-esistente in [buy_pipeline.py:147-154](bot/grid/buy_pipeline.py#L147-L154) era cosmetico: arrotondava `cost` PRIMA di inviare, ma il `quoteOrderQty` finale lasciava ancora Binance libero di ricalcolare amount sul fill price.

### Fix mainnet-safe
Nuova funzione [`place_market_buy_base(exchange, symbol, base_amount)`](bot/exchange_orders.py) in `exchange_orders.py` che invia direttamente `amount=base_amount` (deterministico, lot-step compliant per costruzione). [buy_pipeline.py](bot/grid/buy_pipeline.py#L139-L170) preferisce questo path quando `_exchange_filters["lot_step_size"]` è noto.

**Twist tecnico** (commit follow-up `5061a29`): ccxt default per Binance MARKET BUY converte `amount` (base) in `quoteOrderQty` (quote) sotto il cofano — vanificando il fix. Aggiunta opzione `createMarketBuyOrderRequiresPrice=False` in [`bot/exchange.py`](bot/exchange.py) per forzare il passaggio diretto del `quantity` a Binance.

### Validazione live
Restart 12:55:37 UTC. Primo BUY BONK post-fix a 13:04:43 UTC: 4,032,258 BONK @ $0.00000620, FILLED **al primo tentativo**, nessun rejected.

### Mainnet safety
Identico comportamento su mainnet. Anzi, su mainnet con liquidità maggiore il problema sarebbe stato meno frequente ma comunque presente per coin a basso prezzo + lot_step grossolano (es. SHIB, PEPE, DOGE).

---

## Diagnosi 2 — BTC stop_buy fantasma

### Sintomo
2026-05-11 14:09 UTC: Telegram alert "STOP-BUY TRIGGERED: BTC, unrealized $-5,308.99 ≤ threshold $-4.00". Snapshot pubblico contemporaneo mostrava netRealized +$969 (gross positivo).

### Root cause
Post-S72 (Fee Unification), `state.holdings = fetch_balance()` golden source. Su testnet Binance dona ~1 BTC, ~5 SOL, ~18K BONK al boot (initial gift). Quel balance finisce su `state.holdings` ma NON è stato comprato dal bot.

`unrealized = (current_price − avg_buy_price) × state.holdings` quindi:
- managed: (current − $80,843) × 0.000609 BTC = ~$-0.50 (realistico)
- raw drogato: (current − $80,843) × 1.000606 BTC = ~$-5,300 (fantasma)

Il check stop_buy con threshold 2% del capital ($-4) si attivava su $-5,300, bloccando i buy BTC fino al successivo restart in-memory.

### Fix mainnet-safe
[`state_manager.py`](bot/grid/state_manager.py) `_reconcile_holdings_against_exchange` ora registra:
```python
bot._phantom_holdings = max(0, real_qty - replayed_qty)  # solo wallet_surplus
```

Nuova property [`bot.managed_holdings`](bot/grid/grid_bot.py):
```python
return max(0, state.holdings - _phantom_holdings)
```

Applicata in **9 punti** del hot path in `grid_bot.py`:
- Stop-loss unrealized + open_value (TF)
- Trailing-stop unrealized
- Take-profit unrealized + open_value
- Profit-lock unrealized
- Stop-buy unrealized (il bug)
- Sell amount cap (per non vendere fantasma in partial sell)

`state.holdings` resta golden source per gating `>0` checks e boot reconcile.

### Validazione live
Restart 12:55:37 UTC. Boot reconcile logga per i 3 simboli:
```
[BTC/USDT]  Holdings synced from Binance: BTC=1.0006063  (phantom=0.999997, managed=0.000609)
[SOL/USDT]  Holdings synced from Binance: SOL=5.631314  (phantom=4.999356, managed=0.631958)
[BONK/USDT] Holdings synced from Binance: BONK=14.81M   (phantom=1.37M,    managed=13.45M)
```

BTC con current $80,684 < avg $80,843: nessun STOP-BUY TRIGGERED post-restart. Pre-fix sarebbe scattato (unrealized raw = (80,684−80,843) × 1.0006 = ~$-159, ben sotto soglia $-4).

### Mainnet safety
Su mainnet pulito: `real_qty == replayed_qty` al boot → `phantom_holdings = 0` → `managed_holdings == state.holdings`. **Zero behavior change.**

Su mainnet con deposito manuale dell'utente: il deposito viene catturato come phantom, isolato dai calcoli economici. Il bot continua a operare su quello che ha effettivamente comprato. È esattamente il comportamento desiderato.

---

## Test

[`tests/test_accounting_avg_cost.py`](tests/test_accounting_avg_cost.py) ora 22 test verdi (era 21 dopo S73b).

**Test V nuovo** dimostra concretamente il bug 2:
- BTC scenario: state.holdings=1.000606, phantom=0.999997, managed=0.000609
- Current $80,000 vs avg $80,843
- Raw unrealized: $-844 (drogato, scatterebbe stop_buy)
- Managed unrealized: $-0.51 (reale, sotto threshold)
- Counter-test mainnet: phantom=0 → managed == raw (no behavior change)

---

## Stato bot live (snapshot 13:05 UTC)

| Bot | Wallet | Phantom | Managed | Stato |
|---|---|---|---|---|
| BTC | 1.0006063 BTC | 0.999997 | 0.000609 ($49 a $80,684) | idle, sell trigger $81,974 |
| SOL | 5.841104 SOL | 4.999356 | 0.841748 ($80 a $95) | 1 lotto + 1 buy aggiuntivo notturno + 1 sell, ladder attivo $97.64 |
| BONK | 14.81M BONK | 1.37M | 13.45M ($83 a $0.0000062) | post-BUY 13:04, attesa sell trigger |

Capital at risk reale (Grid only): ~$212 / $500 budget Board. Target go-live €100: invariato **18-21 maggio**.

---

## Commit & deploy

- `d10b5ad`: feat(s73c) — BONK lot_size + BTC phantom (5 files, +172/-20)
- `5061a29`: fix(s73c) — ccxt option (1 file, +10/-0)
- `df3ac52`: docs(s73b) — PROJECT_STATE refresh (precedente)

Push: `origin/main`. Mac Mini su `5061a29`, restart 12:55:37 UTC, 6 processi vivi (orchestrator + 3 grid + sentinel + sherpa, TF off).

---

## Cosa NON è stato fatto e perché

- **Telegram branching bug** (skipped → "Buying at market" sbagliato): identificato in conversazione con Max, fix cosmetico ~10 min. Differito perché non bloccante e questa sessione era già densa di codice.
- **DEAD_ZONE_HOURS dashboard param**: rimandato come da accordo S73a.
- **Approfondimento phantom BONK 1.37M**: il valore è molto più grande dell'initial gift testnet stimato (~18K). Probabile contributo da fee accumulate o reset testnet. Non bloccante per il fix (formula è corretta: phantom = wallet − replayed). Da indagare se serve precisione contabile sui report retroattivi.

---

## Decisioni recenti

**DECISIONE:** introduzione di `_phantom_holdings` + `managed_holdings` property, decoupling completo tra wallet truth (state.holdings) ed economic exposure (managed_holdings).
**RAZIONALE:** una sola riga di fix per tutta una famiglia di bug (stop_buy, unrealized P&L drogato, sell amount cap su fantasma). Mainnet-safe by construction perché su wallet pulito phantom=0 e managed==raw.
**ALTERNATIVE CONSIDERATE:** (a) fix puntuale sullo stop_buy con proxy `(total_invested-total_received)/avg`; (b) brief separato managed_holdings ampio post-S73; (c) ignorare e affidarsi al restart in-memory.
**FALLBACK SE SBAGLIATA:** rimuovere managed_holdings, ripristinare state.holdings nei 9 punti. Backout pulito perché la property è additiva.

**DECISIONE:** sostituire `quoteOrderQty` con `amount` per MARKET BUY quando lot_step_size noto, + ccxt option.
**RAZIONALE:** root cause è l'auto-conversione ccxt amount→quote. Setting l'option è 1 riga e fixa una classe intera di bug.
**ALTERNATIVE CONSIDERATE:** (a) retry loop con backoff; (b) pre-calcolare cost più conservativo; (c) usare params custom esplicito.
**FALLBACK SE SBAGLIATA:** rimettere `createMarketBuyOrderRequiresPrice = True` (default) e usare quote-order ovunque. Però perdiamo il fix.

---

## Pipeline aperta

- Brief follow-up: Telegram branching cosmetic fix (10 min)
- Brief follow-up: DEAD_ZONE_HOURS in dashboard per-coin (1-2h)
- Eventuale: indagare composizione phantom BONK 1.37M se serve contabilità retroattiva precisa
