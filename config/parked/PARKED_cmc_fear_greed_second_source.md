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

Zero aggiuntivo — stessa API key, stesso tier gratuito CMC (vedi aggiornamento S112: 15K credits/mese, attualmente usati solo per global metrics).

---

## Aggiornamento 2026-06-29 (S112) — verifica live chiave + dati disponibili

Durante lo scouting Kraken (S112) Max ha chiesto di verificare cosa sblocca davvero la nostra chiave CMC. Probe live eseguito (read-only). **Piano: 15.000 credits/mese, 188 usati, ~14.8K liberi.**

**Endpoint TESTATI sul nostro piano:**

| Endpoint | Stato | Cosa dà |
|---|---|---|
| `/v1/global-metrics/quotes/latest` | ✅ 200 (GIÀ in uso) | BTC dominance, market cap totale, volume 24h, # cripto attive |
| `/v3/fear-and-greed/latest` | ✅ 200 | **F&G ultimo valore** (più semplice di `/historical?limit=1`) |
| `/v3/fear-and-greed/historical` | ✅ 200 | F&G storico (per backtest/confronto con Alt.me) |
| `/v1/cryptocurrency/quotes/latest?symbol=BTC` | ✅ 200 | Prezzo/volume/market cap/var% per moneta (fonte prezzo indipendente dall'exchange) |
| `/v1/cryptocurrency/listings/latest` | ✅ 200 | Top coin per ranking |
| `/v1/cryptocurrency/trending/latest` | ❌ 403 | Bloccato dal piano (paywall) |
| `/v2/cryptocurrency/ohlcv/historical` | ❌ 403 | Candele storiche bloccate dal piano (paywall) |

**Conclusioni per la sessione futura:**
- ✅ Il F&G CMC (sia `/latest` che `/historical`) **è disponibile** → lo scope originale di questo brief è eseguibile così com'è. Suggerimento: usare `/v3/fear-and-greed/latest` per il valore corrente (1 credit/call), `/historical` solo se serve backfill.
- ✅ **Bonus disponibili** se mai servissero: quote per-moneta + listings (fonte prezzo/segnale indipendente).
- ❌ **NON disponibili**: trending e candele OHLCV (richiedono upgrade a pagamento). Se in futuro servissero candele da CMC, valutare il costo del tier; per ora le candele continuano ad arrivare dall'exchange.

**Nota collegamento Kraken (S112):** CMC diventa più interessante nel contesto migrazione, perché è un canale dati **non legato all'istanza Binance su cui non possiamo più operare**. MA: CMC è Binance-owned → come "seconda fonte indipendente" è solo mezza-indipendente; il termometro davvero indipendente resta Alternative.me. La triade onesta: Alt.me (indipendente) + CMC (famiglia-Binance) + fallback tecnico (RSI/vol da candele — vedi `PARKED_sentinel_regime_technical_fallback.md`). Questo brief resta **separato da S112**: non mischiare l'ingest CMC col commit dell'adapter Kraken (rischio invariante).
