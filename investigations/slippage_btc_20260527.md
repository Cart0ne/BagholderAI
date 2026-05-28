# Investigazione — Slippage anomalo BTC/USDT del 2026-05-27 21:44 UTC

**Auditor**: Claude Code (intern), sessione del 2026-05-28
**Brief sorgente**: [config/brief_slippage_investigation.md](../config/brief_slippage_investigation.md)
**Trade ID SELL**: `a45b08b2-0e2c-4cf3-aca7-89ba069c7506`
**Trade ID BUY successivo**: `8a28f71b-e15d-4d60-8e74-1753d08a7281`
**Verdetto**: **root cause identificata**, è un comportamento atteso del codice attivato da un evento di mercato anomalo su testnet — il fix richiede un brief separato (Board).

---

## 1. Timeline esatta (UTC)

Tutti gli istanti sono presi da `trades` e `bot_events_log` su Supabase.

| Istante (UTC)         | Evento                                                                                   | Dato chiave |
|-----------------------|------------------------------------------------------------------------------------------|------|
| 2026-05-27 15:31:06   | Ultimo trade BTC della giornata (sell del ciclo precedente). Da qui parte il "dead zone clock". | `last_trade_at = 15:31:06` |
| 2026-05-27 20:10 → 21:41 (8 snapshot 15min) | `bot_state_snapshots`: `pct_last_buy_price = 78009.34`, `avg_buy_price = 79454.40`, `holdings = 1.00254375`, `stop_buy_active` flippa da `true` a `false` alle 21:10 (recovery prezzo). | nessuna anomalia |
| **2026-05-27 21:44:03.959847** | **DEAD ZONE RECALIBRATE**: bot idle da 6.2h (soglia 4h). Setta `_last_sell_price` 81853.66 → 0 e `_pct_last_buy_price` 78009.34 → **82143.07** (= `current_price` di questo tick). | `bot_events_log.event="dead_zone_recalibrate"` |
| 2026-05-27 21:44:04.671969 | **Decisione SELL** nel medesimo tick: trigger = avg×(1+sell_pct+FEE)/(1−FEE) = 79454.40 × 1.016/0.999 ≈ **$80,807**. `current_price=$82,143.07 ≥ $80,807` → market sell 0.0006 BTC. | `event="sell_avg_cost_detail"` |
| 2026-05-27 21:44:04.949264 | **Post-fill warning**: fill effettivo $77,352.53, gap vs avg `-2.65%`, implied slippage `-4.15%` (vs trigger $80,807). | `event="slippage_below_avg"` |
| 2026-05-27 21:44:05.163769 | Riga `trades` SELL: `price=77352.528`, `realized_pnl=-1.3075`. Reason: *"Pct sell: check $82,143.07 is 1.5% above avg cost $79,454.40 → fill $77,352.53 (slippage -5.83%)"*. | `exchange_order_id=7977139` |
| 2026-05-27 21:44:06.287236 | `capital_restored` ($46.53 cash). | normale |
| 2026-05-27 21:45:07.080639 | **LAST SHOT BUY**: check $74,593.64 < `_pct_last_buy_price × (1−0.005) = 82143.07 × 0.995 = $81,732.36` → buy con cash residuo $44.76. Fill a $74,593.65. | `trades` BUY, fee in BTC |
| 2026-05-27 21:45:07.900875 | `capital_exhausted` ($1.78 < floor $5). | atteso |
| 2026-05-27 21:46:08.428199 | `stop_buy_activated`: unrealized −$12.32 ≤ −$4.00. | conseguenza della botta di volatilità |

**Delta SELL = 1.2 secondi tra recalibrate e fill** — qualsiasi spike di un secondo basta a far sì che il tick di check sia 5-6% sopra il fill.

---

## 2. Prezzo reale di BTC alle 21:44 UTC

Verificato con Binance klines 1m, intervallo 21:30–22:00 UTC del 2026-05-27.

| Candle (open_time UTC) | Mainnet (api.binance.com)         | Testnet (testnet.binance.vision)    |
|------------------------|------------------------------------|--------------------------------------|
| 21:42:00               | O 74,708 / H 74,751 / L 74,694 / C 74,751 | O 74,751 / H **81,798** / L 74,751 / C 74,776 |
| **21:43:00**           | O 74,776 / H 74,776 / L 74,698 / C 74,700 | O 74,776 / **H 88,000** / **L 67,914** / C 78,006 |
| **21:44:00**           | O 74,700 / H 74,700 / L 74,428 / C 74,628 | O 78,006 / **H 83,797** / **L 64,714** / C 74,628 |
| 21:45:00               | O 74,628 / H 74,628 / L 74,517 / C 74,597 | O 74,628 / H 74,628 / L 68,114 / C 74,611 |

**Lettura:**
- **Mainnet**: BTC ben ancorato a ~$74,500 in tutta la finestra. Range 21:42–21:45 = $74,428–$74,776, **niente picco $82K**.
- **Testnet**: durante 21:42–21:45 il book è esploso con candele a range $20K+ (H/L sopra/sotto la mainnet di 6-13%). Il check del bot a $82,143.07 cade dentro il range della candle 21:42 (H = 81,798) e a inizio candle 21:44 (open = 78,006 dopo spike previo). Plausibilmente è il `last` printato da un singolo trade di pump sull'orderbook sottile testnet.

In altre parole: **il check price $82,143.07 era reale per Binance testnet, ma era uno spike di liquidità inesistente sul mainnet**. Quando il bot ha sparato il market sell, l'orderbook testnet aveva già consumato la liquidità superiore e il market order ha "mangiato" il book scendendo fino a $77,352.53.

---

## 3. Origine del check price e del valore $82,143.07

`grid_runner/__init__.py:498` → `price = fetch_price(exchange, cfg.symbol)`
`grid_runner/lifecycle.py:21-26`:

```python
def fetch_price(exchange, symbol: str, max_retries: int = 3) -> float:
    for attempt in range(max_retries):
        try:
            ticker = exchange.fetch_ticker(symbol)
            return ticker["last"]
        ...
```

→ `current_price` è **un singolo `ticker["last"]`**, cioè il prezzo dell'ultimo trade eseguito su Binance per quel symbol. **Nessuno smoothing, nessuna median di N tick, nessun confronto col tick precedente, nessun controllo di sanity vs `state.last_price` precedente**. Quel tick viene passato grezzo a `check_price_and_execute(current_price)`.

Da dove arriva il valore $82,143.07 nelle stringhe `reason`:

- `_pct_last_buy_price` era **78009.34** in tutti gli snapshot fino alle 21:41:01 (vedi `bot_state_snapshots`). Sovrascritto a **82143.07** alle 21:44:03 dal `dead_zone_recalibrate` (`grid_bot.py:703`: `self._pct_last_buy_price = current_price`).
- Da quel momento in poi `_pct_last_buy_price = 82143.07` per tutta la durata del tick (e di quello successivo), perché:
  1. Il SELL eseguito 0.7s dopo non resetta `_pct_last_buy_price` (la sell_pipeline tocca `_last_sell_price`, non il buy reference).
  2. Il successivo BUY (LAST SHOT) ha letto questo valore come "last buy" → reason cita `$82,143.07` benché **nessun BUY a quel prezzo sia mai esistito** (ultimo buy reale fu `e22a9d1b` il 2026-05-16 a $78,009.34).

Quindi al sospetto del brief (punto 4 — "_pct_last_buy_price sovrascritto in modo anomalo") la risposta è **sì, ma in modo intenzionale dal dead_zone_recalibrate**. Non è un bug nascosto: è esattamente quello che [grid_bot.py:703](../bot/grid/grid_bot.py#L703) fa per progetto (brief 73a / S73, esteso 74b / S74b con `dead_zone_hours` per-coin).

---

## 4. Post-fill guard

Esiste e ha funzionato. Da [grid/sell_pipeline.py](../bot/grid/sell_pipeline.py) (introdotto da S70a Parte 4) → log `event="slippage_below_avg"` scritto in `bot_events_log` alle 21:44:04.949264:

```json
{
  "gap_pct": -2.6453788650959456,
  "fill_price": 77352.528,
  "avg_buy_price": 79454.39784806188,
  "sell_pct_config": 1.5,
  "implied_slippage_pct": 4.145378865095946
}
```

Quindi la visibilità c'è. Quello che **non c'è** è un *pre-trade guard*: niente impedisce al bot di mandare un market order quando il `current_price` si discosta troppo dal tick precedente o dal book medio. Nei path SWEEP / LAST SHOT esiste `SLIPPAGE_BUFFER_PCT=0.03` (brief 78b, S78 fase 2), ma il path "percentage sell sopra avg" lo bypassa.

---

## 5. Root cause (sintesi)

Concorrenza di **tre fattori, tutti necessari**:

1. **Spike testnet single-tick a $82,143** sopra il prezzo "vero" (~$74,500 mainnet). Su testnet è ordinaria amministrazione: orderbook sottile + reset mensile + nessun arbitraggio market-maker. Documentato in memoria `project_bonk_testnet_slippage` per BONK; qui è successo a BTC.
2. **Dead zone recalibrate fired in quello stesso tick**: bot idle da 6.2h sopra avg-cost (Strategy A blocca la sell) → al primo tick dopo le 4h di idle, `_pct_last_buy_price` viene riallineato a `current_price` (brief 73a, S73). Il design del 73a è "se il prezzo è sopra avg e siamo idle, sblocca il ciclo". Lo sblocco è avvenuto, ma sopra il valore di spike, non sopra il prezzo "vero".
3. **Sell trigger valutato nello stesso tick**: subito sotto il blocco dead-zone (stessa funzione `check_price_and_execute`), il sell check vede `current_price=82143.07 ≥ trigger $80,807` e spara market order. Tra `fetch_price` (21:44:03) e fill (21:44:05) il book testnet è già tornato a $77,352.

Niente bug puntuale. **Il dead_zone_recalibrate è funzionalmente corretto**; assume implicitamente che `current_price` sia rappresentativo del mercato. Su mainnet questa assunzione regge; su testnet no.

---

## 6. Proposta di fix (NON implementata)

Tre opzioni alternative (per il Board), ordinate dalla meno invasiva alla più strutturale. Tutte richiedono brief separato (vincolo del brief sorgente).

### Opzione A — Sanity check sul tick di `fetch_price` (minimal)
Aggiungere a `lifecycle.py:fetch_price` un confronto col tick precedente (`bot.state.last_price`): se il delta supera N×`SLIPPAGE_BUFFER_PCT` (es. N=2 → 6%), considerare il tick "non rappresentativo" e ri-fetchare dopo X secondi (o restituire `state.last_price` come fallback per quel ciclo).
- **Pro**: tappa il problema alla sorgente, vale per tutti i path (sell/buy/recalibrate).
- **Contro**: un single-tick filter può mascherare un movimento di mercato reale; serve calibrare la soglia.

### Opzione B — Cooldown 1 ciclo tra `dead_zone_recalibrate` e sell decision
Se `dead_zone_recalibrate` ha fired in questo tick, posticipare di **un tick** (cioè un'iterazione di main loop, ~15-30s) la valutazione del sell trigger. Il tick successivo ri-fetcha il prezzo "fresco" e, se lo spike era un outlier, il sell semplicemente non scatta.
- **Pro**: chirurgico (tocca solo il path dead-zone), preserva la logica di sblocco.
- **Contro**: aggiunge un branch in `check_price_and_execute`; necessita flag transitorio in `GridState`.

### Opzione C — Pre-trade SLIPPAGE_BUFFER_PCT esteso al path percentage sell
Estendere a `_execute_percentage_sell` la stessa guardia già attiva su SWEEP/LAST_SHOT (brief 78b): se il `current_price` di check si discosta da un mid-price ricavato da `fetch_ticker` (bid/ask medi) di più di `SLIPPAGE_BUFFER_PCT`, skip della sell.
- **Pro**: coerente con il pattern già adottato negli altri due path.
- **Contro**: usa `bid/ask` invece di `last`, leggera complicazione; bisogna decidere policy se il book non ha entrambe le entry.

### Raccomandazione CC
**Opzione B + Opzione A in combo** è il pattern più robusto. B impedisce questo episodio specifico (dead-zone + spike in 1 tick); A protegge tutti gli altri path da single-tick storms futuri. Opzione C è già parcheggiata nel TODO §8 di PROJECT_STATE come "slippage_buffer parametrico per coin" e va comunque chiusa pre-mainnet.

**Decisione Board richiesta**: A, B, C, A+B, o A+B+C.

---

## 7. Esposizione mainnet

Il danno realized è di **$1.31 su capitale testnet** (irrilevante). Ma la stessa sequenza su mainnet con €100 di capitale:

- Single-tick storm $82K su mainnet con liquidità deep: **molto difficile** (vedi mainnet klines, range $300-700 su 5min). Quasi impossibile uno spike del 10%.
- Però **flash crash di liquidità** (es. evento news, exchange outage) può comportare comunque divergenze tra `ticker.last` e prezzo di fill di un market order. Su €100, uno scarto del 2% = €2. Cumulato su decine di cicli, è materiale.

**Verdetto rischio mainnet**: medio-basso ma non zero. Vale comunque la fix prima di go-live, anche perché il path `dead_zone_recalibrate` continuerà a fare snapshot di `current_price` come reference per i prossimi N giorni.

---

## 8. Dati allegati (Supabase queries)

Per riproducibilità, le 4 query usate (project `pxdhtmqfwjwjhtcoacsn`):

```sql
-- 1. Trade SELL + BUY
SELECT id, side, amount, price, cost, fee, fee_asset, realized_pnl,
       reason, created_at, exchange_order_id
FROM trades
WHERE symbol='BTC/USDT'
  AND created_at >= '2026-05-27 21:30:00+00'
  AND created_at <= '2026-05-27 22:00:00+00'
ORDER BY created_at;

-- 2. bot_events_log nell'intorno del trade
SELECT created_at, severity, category, event, message, details
FROM bot_events_log
WHERE symbol='BTC/USDT'
  AND created_at >= '2026-05-27 21:30:00+00'
  AND created_at <= '2026-05-27 22:00:00+00'
ORDER BY created_at;

-- 3. Snapshot stato bot pre/post trade
SELECT created_at, holdings, avg_buy_price, cash_available,
       pct_last_buy_price, stop_buy_active, last_trade_at
FROM bot_state_snapshots
WHERE symbol='BTC/USDT'
  AND created_at >= '2026-05-27 20:00:00+00'
  AND created_at <= '2026-05-27 22:30:00+00'
ORDER BY created_at;

-- 4. Ultimo BUY reale (smentisce "$82,143 come last buy")
SELECT id, side, price, reason, created_at
FROM trades
WHERE symbol='BTC/USDT' AND side='buy'
  AND created_at < '2026-05-27 21:44:05+00'
ORDER BY created_at DESC LIMIT 5;
```

Klines Binance:
- Mainnet: `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime=1779917400000&endTime=1779919200000`
- Testnet: `https://testnet.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime=1779917400000&endTime=1779919200000`

---

## 9. Conclusioni operative

- **Strategy A non è stata violata da un bug**: la guardia "no sell at loss" esiste solo sul *check price*, non sul *fill price*. Il `dead_zone_recalibrate` ha sbloccato il ciclo a un check sopra avg, ma il fill è atterrato sotto avg per via dello slippage testnet.
- **`_pct_last_buy_price = $82,143.07` non è un'anomalia di stato**, è il valore corretto post-recalibrate. Resterà tale finché un nuovo BUY non lo aggiorna (`buy_pipeline.py:242`).
- **Nessuna azione immediata richiesta** (bot già operativo, niente lock state da pulire). Stato attuale `bot_runtime_state`: `buy_reference_price=74593.65`, `last_sell_price=77352.528` — già coerente con il BUY 21:45.
- Per chiudere la finestra di rischio: il Board approvi una delle opzioni del §6 e CC apra un brief separato.
