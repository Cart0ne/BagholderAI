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

## Design DECISO (2026-06-30, S112b) — shadow + failover

> Supera il piano "solo shadow" originale. Deciso da Max/CEO dopo brainstorm + verifiche dati (vedi "Aggiornamento S112b" in fondo): in regime di paura CMC ≈ alt.me sullo stesso bucket → il valore vero ORA è il **failover** (robustezza), non un secondo parere. Quindi shadow-log **+** failover, **NON** fusione.

**Cosa fare:**
1. Nuovo file `bot/sentinel/inputs/cmc_fng.py` — analogo a `alternative_fng.py`, contratto NEVER raise (su errore → `None` + warning).
   - Endpoint: `GET https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest` (1 credit).
   - Auth: header `X-CMC_PRO_API_KEY` (chiave già in `.env`).
   - Return **identico** ad `alternative_fng` per drop-in: `{"fng_value": int(round(value)), "fng_label": str, "fng_timestamp": int}`.
   - ⚠️ `update_time` è ISO 8601 (es. `2026-06-30T09:53:10Z`) → convertilo in **epoch** per il check di staleness (alt.me usa epoch). La label CMC è "Extreme **f**ear" (minuscola) ma `regime_analyzer` fa già `.lower()` → ok.
2. In `slow_loop.py`: chiamare `cmc_fng.fetch()` accanto ad `alternative_fng.fetch()` e loggare **entrambi** in `sentinel_scores.raw_signals` (shadow, per la futura analisi lead-lag al prossimo cambio di regime).
3. In `regime_analyzer.determine_regime`: **failover esplicito**. alt.me resta PRIMARIO; se alt.me è `None` o stale (>36h), invece di cadere subito a `neutral` prova CMC: se CMC è fresco, regime da CMC (stesse soglie `_fng_to_regime`) + log `regime_source="cmc_failover"`. Solo se ANCHE CMC è None/stale → `neutral`. **Aggiungere un parametro distinto** per il F&G CMC (oggi la firma ha `cmc_data` = *global metrics*, NON F&G: non riusare quello).

**Cosa NON fare:**
- **Niente fusione/media pesata** alt.me+CMC nel regime: i due concordano sul bucket il 100% in paura → la media non aggiunge nulla ORA; la fusione è "Phase B", da validare solo a un cambio di regime.
- Nessuna nuova tabella Supabase; nessun alert sulla divergenza; non toccare il fast loop.

**Dopo il deploy:** osservare 2-4 settimane + attendere un cambio di regime (neutral/greed) per giudicare se CMC anticipa alt.me ai bordi dei bucket (il bias +2,5 potrebbe far scattare CMC prima/dopo su una soglia). Solo allora valutare la promozione a fusione.

**Stima aggiornata:** ~1.5h (era ~1h: +failover in `regime_analyzer` + test).

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

---

## Aggiornamento 2026-06-30 (S112b) — brainstorm + verifiche F&G (CMC vs alt.me)

Probe live read-only (CMC `/v3/fear-and-greed` + alt.me `/fng`), 20 giorni allineati per data UTC:

| Metrica | Valore |
|---|---|
| Valori correnti | CMC **17** "Extreme fear" · alt.me **15** "Extreme Fear" |
| Bias medio (CMC − alt.me) | **+2,5** (CMC legge leggermente più alto) |
| Scarto assoluto medio / max | **3,4** / **7** |
| Giorni con **bucket di regime diverso** | **0 / 20** (sempre `extreme_fear`) |

**Conseguenze (smontano un'assunzione del Contesto):** la frase "letture significativamente diverse (8 vs 15)" era un singolo punto che sovrastimava la divergenza. Su 20 giorni i due indici **concordano sul bucket il 100%** in questo semestre fear-dominato. Quindi:
- ADESSO CMC **non è un secondo parere divergente** → il guadagno reale è **failover/robustezza** (oggi il regime dipende al 100% da alt.me: se stale >36h o giù → `neutral`, e si perde il freno `stop_buy` dell'extreme_fear). Da qui il design "shadow + failover" deciso sopra.
- Il "chi anticipa ai bordi" / fusione si può giudicare **solo a un cambio di regime** (come per il barometro: in sola-paura non è valutabile). Lo shadow-log serve esattamente a raccogliere quei dati.

**Struttura payload (per il codice):** `/latest` → `{value, update_time (ISO), value_classification}`; `/historical` → `{timestamp (epoch str), value, value_classification}`. `value` può essere float → `int(round())`. Credits: `/latest` 1/call → ~180/mese a 6 call/giorno, trascurabile su 15K.

**Collegamento `PARKED_sentinel_regime_technical_fallback`:** CMC failover + fallback tecnico (RSI/vol da klines) sono due gambe della stessa robustezza-regime. CMC è la più semplice (stessa metrica, stessa scala) → farla per prima; il fallback tecnico resta gamba successiva.
