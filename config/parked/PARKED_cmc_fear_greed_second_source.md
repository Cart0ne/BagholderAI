# PARKED — CMC Fear & Greed come Seconda Fonte Sentinel

**Origine:** S108 (2026-06-22), analisi barometro + domanda Board su Binance F&G
**Tipo:** Caso 2 (non blocca go-live)
**Stima:** Scope basso, ~1h lavoro CC

---

## Contesto

Il Sentinel slow loop legge il Fear & Greed index da Alternative.me (`bot/sentinel/inputs/alternative_fng.py`). In S108 è emerso che:

- Alternative.me e CoinMarketCap danno letture significativamente diverse (8 giugno: Alt.me = 8, CMC = 15)
- Binance ha un proprio F&G su Binance Square ma NON ha API pubblica
- CoinMarketCap è Binance-owned (acquisita 2020) → proxy più vicino al F&G Binance
- Noi abbiamo GIÀ la chiave API CMC in `.env` (usata per BTC dominance in `cmc_global.py`)

## Cosa fare

1. Nuovo file `bot/sentinel/inputs/cmc_fng.py` — analogo a `alternative_fng.py`
2. Endpoint: `GET https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical` (limit=1 per ultimo valore)
3. Autenticazione: header `X-CMC_PRO_API_KEY` (stessa chiave già in `.env`)
4. Return: `{"cmc_fng_value": int, "cmc_fng_label": str, "cmc_fng_timestamp": str}`
5. Contratto: NEVER raise (come tutti gli input Sentinel). Su errore → return None + log warning.
6. In `slow_loop.py`: chiamare `cmc_fng.fetch()` accanto a `alternative_fng.fetch()`, loggare entrambi i valori in `sentinel_scores.raw_signals`
7. **NON modificare `regime_analyzer.py`** — il regime continua a essere determinato da Alternative.me. CMC è solo osservazione parallela.

## Cosa NON fare

- Non cambiare la logica di regime (nessuna media, nessun switch di fonte)
- Non creare nuove tabelle Supabase
- Non fare alert/notifiche sulla divergenza tra i due indici

## Dopo il deploy

Osservare per 2-4 settimane, poi valutare:
- CMC anticipa Alternative.me ai bordi dei bucket? (es. CMC supera 25 prima di Alt.me)
- I due indici sono ridondanti o complementari?
- Vale la pena fare una media pesata, o uno è strettamente migliore dell'altro?

## Costo

Zero aggiuntivo — stessa API key, stesso tier gratuito CMC (10K credits/mese, attualmente usati solo per global metrics).
