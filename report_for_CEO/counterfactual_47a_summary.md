# Counterfactual Tracker (47a) — Analisi prima

**Data analisi:** 2026-05-01
**Periodo coperto:** 2026-04-23 → 2026-04-30 (**6.5 giorni di dati validi**)
**Sample size:** 451 skip validi (con baseline + check 24h completato)
**Pre-47a (senza baseline):** 144 righe — ignorate nell'analisi

## Domanda di partenza

Il distance filter (deployed 45e v2) blocca le entry TF quando una coin è > `tf_entry_max_distance_pct` sopra l'EMA20. **Le coin bloccate sarebbero state profittevoli o no?**

## Risposta sintetica

**Il filtro sta funzionando bene.** Su 451 skip validi:

- **77% sarebbero state perdite** entro 24h (349/451)
- **22% sarebbero state profitti** (101/451)
- **15% sarebbero stati profitti rilevanti (>5%)** — il "costo" di vere occasioni perse: 69/451
- **57% delle perdite evitate erano grosse (>−10%)** — il filtro sta proteggendo da entry disastrose: 257/451

## Numeri chiave

| Metrica | Valore |
|---|---|
| Avg delta 24h post-skip | **-9.99%** |
| Avg peak 24h post-skip | **+16.20%** |
| Worst skip (skip_avoided) | **-49.94%** |
| Best skip (occasione persa) | **+70.92%** |
| Skip che hanno bloccato un guadagno >+5% | 69 = 15.3% |
| Skip che hanno evitato una perdita >−10% | 257 = 57.0% |

## Lettura

L'avg delta a 24h è **−10%**: in media, le coin che il filtro ha skippato sono scese del 10% nelle 24h successive. Questo significa che il filtro **sta evitando perdite reali**, non semplicemente rinunciando a trade neutrali.

L'avg peak a 16% però dice che molte di queste coin hanno avuto un picco intermedio prima di scendere — un trader "in finestra" perfetto avrebbe potuto entrare e uscire con profitto. Ma il TF non è un trader in finestra: punta a entrare su trend stabili, non picchi pump-and-dump.

**Il 15.3% di occasioni perse (>+5%)** è il prezzo da pagare. Per ogni 10 entry bloccate, 1.5 sarebbero state un ottimo trade. Le altre 8.5 erano pericolose o neutre.

## Per-coin top 10 (skip count)

| Symbol | Skips | Avg Δ24h | % Profitable |
|---|---|---|---|
| ORCA/USDT | 89 | -10.89% | 34.8% |
| ZBT/USDT | 75 | +2.65% | 38.7% |
| HYPER/USDT | 50 | -23.18% | 0.0% |
| AXS/USDT | 42 | -9.12% | 4.8% |
| D/USDT | 35 | -1.14% | 37.1% |
| BIO/USDT | 29 | -3.53% | 31.0% |
| BROCCOLI714/USDT | 23 | -13.22% | 0.0% |
| ENSO/USDT | 20 | -19.48% | 0.0% |
| LUMIA/USDT | 13 | -4.40% | 69.2% |
| ZKP/USDT | 13 | -13.52% | 0.0% |

## Coin pattern

- **HYPER, BROCCOLI, ENSO, KAT, AI**: 0% profitable. Filtro spot-on.
- **LUMIA, LUNC**: 69% e 100% profitable. Il filtro forse troppo aggressivo per queste due (specie LUNC con +9% medio).
- **ORCA, D, BIO, ZBT**: profittevoli al 30-40%. Borderline — il threshold attuale del 12% è tarato bene per questa fascia.

## Raccomandazione preliminare

Il distance filter al **12% sopra EMA20** sta facendo il suo lavoro. Su 6.5 giorni di dati:

- **Mantieni il threshold a 12%** per ora
- Considera un **whitelist override** per coin con storia profittevole (LUMIA, LUNC) se il pattern persiste su 30+ giorni
- **Non abbassare** sotto il 10%: i dati mostrano che a >10% il rischio di rovesciamento è dominante

## Limiti di questa analisi

- 6.5 giorni sono pochi: sample size 451 è statisticamente limitato
- Periodo coincide con un trend di mercato globale specifico — i dati possono cambiare in mercato bullish
- Counterfactual checkato a 24h: alcune coin scendono ma poi salgono dopo 48h+. Il check a 24h è conservativo
- Il `peak_24h_pct` di +16% medio mostra che molte coin pumpano poi dumpano — sarebbe utile aggiungere un check a 7d per vedere se davvero il filtro evita o solo ritarda

## CSV completo

`counterfactual_47a.csv` (allegato): 595 righe, una riga per ogni skip dal 2026-04-23. Apribile in Excel/Sheets.
