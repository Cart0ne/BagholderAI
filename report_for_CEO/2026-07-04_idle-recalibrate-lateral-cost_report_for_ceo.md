# Mini-report — Costo dell'IDLE recalibrate in mercato laterale

**Data:** 2026-07-04
**Origine:** sessione di studio con Max (non deriva da un brief CEO)
**Autore:** CC
**Riproducibilità:** `scripts/backtest/recal_sweep_experiment.py` — harness fedele in `scripts/backtest/` (grid_sim.py modella idle-recalibrate + dead-zone + guard sopra-avg), dati Binance 1m in cache `audits/backtest/data/`, fee modellata Kraken taker 0.40%, bot variante `repaired` (fix Piano A). Nessun codice di produzione toccato.

---

## Domanda

Il grid, dopo `idle_reentry_hours` di inattività, **riavvolge il riferimento d'acquisto al prezzo corrente** (idle recalibrate). Max ha ipotizzato che in mercato laterale questo faccia **inseguire il buy senza mai raggiungerlo**: se il prezzo scende più lentamente di `buy_pct` per finestra, ogni recalibrate riabbassa la soglia e il buy non scatta mai → guadagni laterali persi. Verificato con un backtest controfattuale.

## Esperimento

Sweep del solo `idle_reentry_hours` ∈ {0(off), 2, 4=baseline dei report, 8, 24, 720(off su finestra mensile)}, **tutti gli altri parametri congelati** ai valori dei report grid-regime. 4 dataset laterali (BTC ago23, BTC set23, SOL, BONK) + 2 di controllo (BTC bear, BTC bull). Variante extra `NO-RECAL` = idle off **+** dead-zone off.

## Risultati (P&L netto %, fee Kraken 0.40%)

| Dataset | drift | HOLD | baseline idle=4h | recalibrate OFF | Δ (off − base) |
|---|---|---|---|---|---|
| **SOL laterale** | −0,1% | −0,52% | **+0,64%** | **+2,55%** | **+1,9 pt** |
| **BONK laterale** | −2,3% | −2,72% | **+2,49%** | **+11,85%** | **+9,4 pt** |
| BTC lat Ago23 | −11,3% | −11,61% | −5,56% | −5,71% | ~0 |
| BTC lat Set23 | +3,9% | +3,52% | +0,60% | +0,65% | ~0 |
| *BTC BEAR (ctrl)* | −37,3% | −37,54% | −28,44% | −31,68% | **−3,2 pt** |
| *BTC BULL (ctrl)* | +37,2% | +36,60% | +5,36% | +1,47% | **−3,9 pt** |

## Tre findings

1. **Confermato: in laterale "vero" il recalibrate costa, e parecchio.** SOL piatto → edge su hold ~quadruplica (+1,2→+3,1 pt) spegnendolo; BONK → il recalibrate lasciava sul tavolo ~9 pt (+2,5%→+11,9%). Il meccanismo è quello ipotizzato: con recalibrate OFF il riferimento resta "appiccicato" all'ultimo buy vero e la scaletta cattura i rimbalzi di mean-reversion.

2. **Non è un pasto gratis — nei trend il recalibrate AIUTA.** BULL: spegnerlo crolla il grid +5,36%→+1,47% (−3,9 pt). BEAR: no-recal peggiora −28,4%→−31,7% (−3,2 pt, perde la protezione dal mediare in caduta). È il trade-off momentum-guard vs mean-reversion.

3. **Il colpevole è solo l'IDLE recalibrate (lato buy), NON la dead-zone (lato sell).** Confronto `idle=0` (dead-zone attiva) vs `NO-RECAL` (dead-zone spenta): su BONK la dead-zone valeva **+6 pt**, in bear aiutava. Quindi la dead-zone recalibrate è utile e va lasciata; l'unico meccanismo da ridiscutere è l'idle recalibrate.

## Caveat (importante)

**Parametro fragile / n=1 per regime.** Lungo lo sweep il segno si ribalta per piccoli cambi (BONK: idle=2h → −5,72%, idle=4h → +2,49%, idle=24h → +11%). Classico segnale di overfit su una singola finestra mensile. **Su questi numeri non si ritara nulla.**

## Gancio Sherpa (possibile mistaratura)

Sherpa già modula `idle_reentry_hours` per regime, ma il regime `neutral` (proxy del laterale) riceve idle = **1,0h (corto)**, mentre il dato dice che il flat vuole idle **lungo/spento**. Se regge su più finestre, Sherpa dà la medicina sbagliata proprio dove il grid dovrebbe rendere di più.

## Raccomandazione

**Nessuna modifica ora.** Prima uno **studio di robustezza multi-finestra** (4–6 mesi laterali per coin, stesso sweep). Se "idle lungo/off batte idle corto in flat" tiene stabile, allora proporre di ritarare la mappa `idle_reentry_hours` di Sherpa (lunga nel neutral/laterale), lasciando la dead-zone invariata. Coerente con il filone trend-gate già aperto (commit `876e4b4`).
