# Report per CEO — Reentry adattivo (regime × morfologia candele): migliora o no?

**Data:** 2026-07-25
**Da:** CC (intern) · **Per:** CEO + Board (Max)
**Origine:** sessione di verifica posizione BTC/USD Kraken (Fase 2b). Non nasce da un brief; è un documento di **discussione strategica** richiesto da Max.
**Scope:** valutare la proposta "incrociare regime (Fear&Greed) + analisi delle candele per modulare `idle_reentry_hours`: discesa lenta → reentry largo (>8h), crollo → reentry stretto". Domanda centrale: **migliora oppure no?**

---

## TL;DR (il verdetto in 5 righe)

1. **Il problema è reale**: oggi in regime *fear* la riga Kraken ricalibra il riferimento di acquisto ogni **2h**, e in una discesa lenta il target di acquisto **insegue il prezzo verso il basso** → il DCA non scatta mai (posizione ferma a 1 solo lotto dal 22 lug).
2. **La direzione "reentry più largo" aiuta, ma solo a metà**: nel mix/salita allungare 2h→12h migliora (~+1,7% sul capitale); **nella discesa persistente PEGGIORA** (~−1,9%), perché medi al ribasso su un trend che continua a scendere.
3. **La parte adattiva su candele NON paga** nel backtest: i "crolli" veri (−3% in 6h) sono lo **0,6% delle ore**, e in quei momenti lo **stop-buy da drawdown già interviene**. Il miglior adattivo ≈ il miglior idle fisso (±0,3–0,8 $ su 100, dentro il rumore del modello).
4. **Contesto**: nella finestra testata (120g, trend ribassista) il grid perde comunque contro il buy&hold (−11,6% vs −6,8%). Il grid è un **ammortizzatore da chop**, non un motore da trend.
5. **Raccomandazione**: **non implementare la regola come formulata** su questo singolo campione. La vera domanda strategica non è tecnica ma di mandato: *vogliamo che il grid medi al ribasso in paura (scommessa mean-reversion) o che si protegga?* Prima di qualsiasi codice, gate = backtest ufficiale multi-finestra.

---

## 1. Il problema osservato (diagnosi 2026-07-25)

Posizione BTC/USD Kraken, cycle `kraken_2b`, denaro reale:
- **1 solo trade** da go-live (22-lug 19:14): BUY 0,00050733 BTC @ $65.695,80. Zero acquisti/vendite da allora.
- Config live (regime *fear*, tier LOW): `buy_pct 1,8%`, `sell_pct 1,2%`, **`idle_reentry_hours 2h`**, `skim 30%`.

**Meccanismo.** Il target di acquisto è `reference × (1 − 1,8%)`. Ogni 2h di inattività, se il prezzo è sotto il costo medio, il bot **ricalibra il reference al prezzo corrente** (`grid_bot.py` idle recalibrate, Path B). Con BTC in discesa lenta, il reference scende inseguendo il prezzo e il target resta sempre ~1,8% *sotto* → non viene mai toccato.

Simulazione oraria sui giorni reali dal primo buy (reference iniziale $65.695,80, buy_pct fisso):

| Recalibrate | BUY addizionali | Esito |
|---|---|---|
| 2h (attuale) | 0 | mancato: minimo $63.740 vs trigger $63.614 (+0,20%) |
| 8h | 0 | mancato per lo stesso soffio (+0,20%) |
| 24h | **1** | BUY il 24-lug @ ~$63.975 |
| reference mai mosso | ✅ subito | target restava $64.513, raggiunto comodamente |

Il contrasto "mai mosso → compra subito" vs "ogni 2h → mai" isola la causa: **è il recalibrate-al-ribasso a mangiare il DCA**. Questa osservazione è ciò che ha originato la proposta.

## 2. Come funziona oggi (per chi legge il report a freddo)

- **Sherpa** legge il regime (Fear&Greed, slow-loop 4h) e scrive in `bot_config` i 3 parametri strategia (`buy_pct`, `sell_pct`, `idle_reentry_hours`) + 4 parametri protettivi (stop-buy drawdown/unlock, dead-zone, profit-target). Tabella (tier LOW):

| Regime | buy_pct | sell_pct | idle_reentry | stop_buy_dd | stop_buy_unlock |
|---|---|---|---|---|---|
| extreme_fear | 2,5% | 1,0% | 4h | 3% | 12h |
| **fear** (oggi) | 1,8% | 1,2% | **2h** | 4% | 6h |
| neutral | 1,0% | 1,5% | 1h | 1% | 2h |
| greed | 0,8% | 2,0% | 0,75h | 1% | 2h |
| extreme_greed | 0,5% | 3,0% | 0,5h | 1% | 2h |

- **Punto non ovvio**: il grid **non legge il regime**. Il "lamp" stop-buy che Sherpa accende in *extreme_fear* è solo un **indicatore** per la dashboard admin; l'unico stop-buy che blocca davvero gli acquisti è quello **da drawdown** interno al grid (scatta quando la perdita non realizzata supera `dd% del capitale allocato`; si sblocca dopo `unlock_hours` o su una vendita in profitto). Quindi il regime cambia solo *parametri* e *sensibilità del freno*, non attiva blocchi da solo.
- **Direzione del design in paura**: più prudenza sull'entrata (buy_pct sale, idle sale), uscita più pronta (sell_pct scende), freno più sensibile. Sistema *difensivo*, non aggressivo.

## 3. La proposta (formalizzata)

Rendere `idle_reentry_hours` funzione **non solo del regime** ma anche della **morfologia recente del prezzo**:
- **Discesa lenta / ordinata** → reentry **largo** (>8h): il reference resta fermo, il DCA scatta sui pullback.
- **Crollo / movimento violento** → reentry **stretto**: il reference insegue, il bot non compra in caduta libera.

Segnale morfologico usato nel test (proxy difendibile): **velocità di discesa** = rendimento sulle ultime 6 ore. `ret6h ≤ −3%` ⇒ "crollo"; altrimenti "lento/normale".

## 4. Obiezioni tecniche (anti-assenso, prima dei numeri)

1. **Ridondanza sul lato crollo.** "Crollo → non comprare" è **già** ciò che fa lo stop-buy da drawdown: nel crollo la perdita supera la soglia e i buy si bloccano. La regola morfologica su questo lato aggiunge poco.
2. **Il lato nuovo è un DCA travestito.** "Discesa lenta → reentry largo → media al ribasso" è comprare mentre il prezzo scende. Il suo rendimento **non è una proprietà del bot**: è una **scommessa sulla mean-reversion** (guadagni se rimbalza, perdi se il trend prosegue).
3. **Complessità/osservabilità.** Aggiungere una dimensione (morfologia) al già intricato sistema Sherpa allarga la superficie di tuning e di bug, e va giustificata da un beneficio misurabile.

## 5. Evidenza empirica (backtest)

**Metodo.** 120 giorni di candele orarie BTC (proxy BTCUSDT, 2881 candele, 27-mar → 25-lug; range $57.800–$82.850, chiusura −6,8%). Modello grid a costo medio: primo buy a mercato, buy su `reference×(1−1,8%)` con Strategy A (mai sopra avg quando si hanno holdings), sell su trigger **fee-buffered** `avg×(1+1,2%+fee)/(1−fee)`, fee 0,8% Kraken, stop-buy dd 4% / unlock 6h. **A parità di tutto tranne la politica di reentry.** Metrica: equity finale su $100.

**Sweep del reentry FISSO** (equity finale):

| Finestra | 2h | 4h | 8h | 12h | 24h | 48h | B&H | miglior fisso |
|---|---|---|---|---|---|---|---|---|
| FULL 120g | 86,7 | 85,2 | 87,7 | **88,4** | 88,2 | 85,9 | 93,2 | 12h |
| UP-leg (fino al picco) | 106,7 | 106,0 | 108,7 | **108,8** | 108,6 | 106,9 | 120,2 | 12h |
| DOWN-leg (dal picco) | **79,8** | 78,6 | 79,0 | 77,9 | 78,3 | 78,3 | 77,5 | **2h** |

**Adattivo (best su griglia di soglie/valori) vs miglior fisso:**

| Finestra | miglior fisso | miglior adattivo | delta |
|---|---|---|---|
| FULL 120g | 12h → $88,4 | $88,7 | **+0,3** |
| UP-leg | 12h → $108,8 | $108,8 | **+0,0** |
| DOWN-leg | 2h → $79,8 | $79,0 | **−0,8** |

**Lettura.**
- **Allungare il reentry aiuta solo dove c'è mean-reversion** (FULL/UP: 12h > 2h di ~1,7–2,1 punti). **Nella discesa vera il reentry stretto vince** (DOWN: 2h > 12h di ~1,9 punti). La regola di Max ("discesa lenta → largo") va quindi **nella direzione sbagliata proprio in discesa**.
- **L'adattività su candele non batte il miglior idle fisso** in nessuna finestra (±0,3–0,8 $ su 100, entro il rumore del modello): i crolli sono troppo rari (0,6% delle ore) e lo stop-buy li copre già. Anche cercando il config migliore *ex-post* (già favorevole all'adattivo), il vantaggio svanisce.
- **Il grid perde vs hold** in questa finestra ribassista — atteso: brilla nel chop, non nel trend.

## 6. Verdetto: migliora?

- **Come formulata: no (o marginale)**, e il lato "discesa lenta → largo" è **attivamente dannoso** nello scenario chiave.
- Il **grosso del beneficio** che esiste (nel mix) viene dall'**allungare il reentry di base** (2h→12h in fear), **non dall'adattività**. Ma quello stesso allungamento **danneggia in discesa** — quindi non è un free lunch: sposta solo dove guadagni e dove perdi.
- Se un'adattività "vera" avesse senso, sarebbe quasi l'**opposto** dell'intuizione: *trend-down persistente → reentry stretto*; *chop/rimbalzo → reentry largo*. Ma distinguere ex-ante "discesa che rimbalza" da "discesa che continua" **è il problema irrisolvibile del trading** (è previsione, non configurazione).

## 7. Opzioni per il CEO (non decido io)

| # | Opzione | Effetto atteso | Costo/rischio |
|---|---|---|---|
| A | **Status quo** (idle da regime, 2h in fear) | Protettivo; miglior comportamento *in discesa* | Nessun DCA in fear/discesa lenta (il "problema" resta by design) |
| B | **Alzare idle di base in fear** (es. 2h→8/12h, via tabella Sherpa) | +~1,7% nel mix/salita | −~1,9% in discesa persistente; UPDATE tabella, tocca tutte le righe fear |
| C | **Adattività morfologica** (proposta Max) | Nel backtest ≈ zero sopra il fisso | Complessità elevata, beneficio non dimostrato |
| D | **Separare le due decisioni**: protezione = stop-buy (già c'è); DCA in paura = scelta *esplicita e consapevole* (scommessa mean-reversion), non un effetto collaterale del reentry | Rende il mandato leggibile | Richiede decisione strategica del Board, non un tuning |

Raccomandazione CC: **D come inquadramento + A come default operativo**, finché un backtest ufficiale non giustifica B. **C sconsigliata** senza evidenza nuova.

## 8. Next step (gate)

Prima di qualsiasi implementazione: **backtest ufficiale multi-finestra** con l'harness `scripts/backtest/` (fedele a sell parziali, skim, fee reali), su **almeno 3 regimi di mercato** (chop laterale, bull, bear) e con la **storia F&G reale** per pilotare i parametri come in produzione. Il presente documento è un **primo segnale direzionale su un singolo campione**, non la parola definitiva.

---

## Appendice — assunzioni e limiti (lettura obbligata)

- **Un solo campione** (120g), per giunta **ribassista** → sfavorevole al grid. Le conclusioni per-finestra (12h nel mix, 2h in discesa) sono coerenti, ma la generalizzazione richiede più finestre.
- **Modello semplificato**: vendita *totale* al trigger (il grid reale può vendere porzioni), **skim omesso**, fee proxy 0,8%, candele **orarie** (non tick → wick intra-ora non catturati; il margine +0,20% del §1 potrebbe colmarsi nella realtà), prezzo **BTCUSDT** ≠ BTC/USD Kraken (differenza di qualche decina di $).
- **Segnale morfologico** = solo `ret6h`; segnali più ricchi (volatilità realizzata, volume, pattern) non testati e potrebbero cambiare il quadro (ma la rarità strutturale dei crolli resta).
- **Metrica** = equity a fine finestra: dipende dal punto di uscita. In un downtrend chi ha più holdings (reentry largo) è penalizzato dal mark-to-market; un rimbalzo finale ribalterebbe il ranking.
- Parametri fissi usati: capital $100, per_trade $33,33, buy_pct 1,8%, sell_pct 1,2%, fee 0,8%, stop-buy dd 4% / unlock 6h (valori live fear tier LOW).
- Fonte prezzi: Binance klines pubbliche 1h. Codice simulazione: scratchpad di sessione (non committato; riproducibile su richiesta).
