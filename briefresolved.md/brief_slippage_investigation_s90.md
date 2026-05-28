# BRIEF CC — Investigazione slippage anomalo BTC/USDT

**Data**: 28 maggio 2026  
**Priorità**: ALTA — possibile violazione Strategy A  
**Stima**: < 1h (investigazione, non coding)

---

## Contesto

Il 27 maggio alle 21:44 UTC il grid bot BTC/USDT ha eseguito un SELL in live con **P&L negativo (-$1.31, -2.74%)**. La Strategy A per grid manuali vieta vendite in perdita.

Trade ID in Supabase: `a45b08b2-0e2c-4cf3-aca7-89ba069c7506`

Il campo `reason` del trade dice:

```
Pct sell: check $82,143.07 is 1.5% above avg cost $79,454.40
→ fill $77,352.53 (slippage -5.83%)
```

**Il trigger era corretto** (check price sopra avg cost), ma il fill è stato $4,800 sotto il check price. Per un ordine da $46 su BTC/USDT Binance, -5.83% di slippage è impossibile in condizioni normali.

---

## Cosa investigare

1. **Timing check → order**: quanto tempo è passato tra il check price ($82,143) e l'invio dell'ordine market a Binance? Cercare nei log del bot (stdout/file) e in `bot_events_log` il timestamp esatto del tick e dell'order submission.

2. **Prezzo reale di BTC alle 21:44 UTC del 27 maggio**: verificare su Binance klines (1m candle) se BTC era davvero a $82,143 o se era già a ~$77,000. Se era a $77K, il check price era stale.

3. **Origine del check price**: nel codice, `check_price_and_execute` riceve `current_price` — da dove arriva? È il prezzo del tick corrente o è cachato/ritardato? Verificare il flusso: `grid_runner` → `price fetch` → `check_price_and_execute`.

4. **Il buy successivo** (21:45 UTC, trade `8a28f71b`) usa `$82,143.07` come "last buy" reference, ma l'ultimo buy reale era a $78,009 il 16 maggio. Da dove viene il valore $82,143? Verificare se `_pct_last_buy_price` è stato sovrascritto in modo anomalo.

5. **Post-fill guard**: il codice (S70a Parte 4) ha un warning per slippage che porta il fill sotto avg_buy_price. Verificare se questo warning è stato loggato in `bot_events_log` per questo trade.

---

## Decisioni delegate a CC

- Scegliere il metodo di investigation (log, klines API, replay)
- Determinare la root cause

## Decisioni che CC DEVE chiedere

- Se la root cause richiede un fix di codice, NON fixare: produrre un report con diagnosi e proposta. Il fix va in un brief separato approvato dal Board.

---

## Output atteso

Un report in italiano (`investigations/slippage_btc_20260527.md`) con:

1. Timeline esatta (tick → check → order → fill) con timestamp
2. Prezzo reale BTC al momento del trade (da klines Binance)
3. Root cause identificata o ipotesi ranked
4. Se è un bug: quale file/funzione, con proposta di fix (senza implementarla)
5. Se NON è un bug: spiegazione del perché e valutazione se il comportamento è accettabile

---

## Vincoli

- **NON modificare codice** — solo investigazione
- **NON riavviare il bot** — è live
- Puoi leggere `bot_events_log`, `trades`, `bot_state_snapshots`, log stdout
- Puoi chiamare Binance klines API per verificare il prezzo storico
