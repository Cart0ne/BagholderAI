# Report per il CEO — Il grid può "cavalcare" un bull? (esperimento trend-capture)

**Da:** CC (Intern) · **A:** CEO (Claude) · **Data:** 2026-07-02 (follow-up S115, richiesta di Max)
**Tooling:** `scripts/backtest/trend_gate_experiment.py` + flag `trend_gate` in `grid_sim.py` (default off) · **Dati:** cache 1m BTC/SOL/BONK già scaricata (fee Kraken 0.40%).

---

## La domanda

I backtest hanno mostrato che nel **bull** il grid lascia sul tavolo quasi tutto il rialzo (cattura 10–42% del hold). Max ha chiesto: **si può far "holdare" il grid in bullish per avvicinarsi al rendimento del semplice hold?** L'ho testato: quando un rilevatore di regime dice "uptrend", il grid smette di vendere a scaglioni e **cavalca** con un trailing stop (esce a −X% dal picco), poi torna grid normale.

## TL;DR — verdetto

**No, non come tweak del grid.** Non esiste una taratura robusta: lo stesso settaggio **triplica** la cattura su SOL (+21%→+71%), la **peggiora** su BONK (+51%→+39%) e **non muove** BTC (~+5%). Il numero balla 9× a seconda di una manopola → firma dell'**overfitting**, non di un edge. La cattura del trend **non appartiene al grid**: appartiene al **Trend Follower**. Prossimo passo raccomandato: backtestare l'hand-off **Sentinel BULLISH → TF** (sotto).

---

## Metodo (onestà prima dei numeri)

- **Rilevamento regime CAUSALE** (niente lookahead): uptrend = prezzo > media mobile 24h **e** MM in salita, calcolata solo sul passato. È il caso reale-time.
- **Soffitto "crystal-ball"**: trailing sempre acceso (detection perfetta) — il massimo teorico, per misurare il costo del ritardo di detection.
- **Trailing** testato a 4 / 10 / 20 / 30 / 50% dal picco.
- **Regression check superato**: il grid puro (flag off) riproduce *esattamente* i numeri già committati (BTC −28.44/+5.36/+0.60, SOL −52.19/+21.21/+0.64, BONK −42.00/+50.84/+2.49) → le modifiche non hanno toccato il comportamento validato.

## Risultati

**1. La versione ingenua (trailing stretto 4%) è una TRAPPOLA** — peggiora *ovunque*, bull incluso (SOL +21%→+18%, BONK +51%→+39%). Anche con detection *perfetta*, SOL bull crolla a +8%. Un trailing 4% viene sbattuto fuori dalla volatilità crypto, e la guardia "non comprare sopra l'avg" (Strategy A) impedisce di rientrare nel rally → resti in cash mentre sale.

**2. Con trailing LARGO (20–30%) + detection causale — bull, quanto cattura:**

| Coin | Grid puro | Trend-gate (trail 30%) | Hold |
|---|---|---|---|
| BTC (+37%) | +5.4% | **+4.1%** ⬇️ nessun aiuto | +37% |
| SOL (+207%) | +21% | **+71%** ⬆️ 3,3× | +206% |
| BONK (+122%) | +51% | **+39%** ⬇️ peggiora | +121% |

**Costo nel laterale** (campo di casa del grid), trail 30%: trascurabile (BTC +0.60→+0.46, SOL +0.64→+0.38, BONK +2.49→+2.79 — a trail largo non scatta quasi mai nel piatto). **Bear:** ~invariato.

**3. Nessuna taratura robusta.** Lo stesso identico settaggio aiuta SOL, danneggia BONK, è neutro su BTC. E la sensibilità è enorme: SOL bull va da +8% (trail 4%) a +71% (trail 20%). Con **un solo bull per coin** (N=1 per regime) non distinguo il colpo di SOL dalla fortuna. È la stessa disciplina che applichiamo sul guard anti-surge del TF (p=0.092 → *non* implementare).

## Due findings solidi (questi reggono)

1. **La cattura del trend è strutturalmente tappata nel grid.** Il grid può cavalcare **solo la posizione accumulata in basso** — Strategy A gli vieta di comprare in salita. BTC lo dimostra: resta a ~7% *anche* con detection perfetta e trailing larghissimo. Non riderà mai il 100% come hold.
2. **Il trade-off è inaggirabile a livello di grid:** ogni meccanismo che cattura più rialzo (trail più largo) o è "hold travestito" (trail 50% = non più grid) o whipsaw nel laterale. Non si può essere ammortizzatore e motore con lo stesso strumento.

## Raccomandazione

**Non scrivere questa strategia come feature del bot.** Il modo corretto di prendere il bull non è ritoccare il grid: è l'**architettura three-brain che già abbiamo** — **Sentinel** rileva il risk-on, il capitale passa al **TF**, che *può* comprare in salita ed è nato per cavalcare. Il grid resta l'ammortizzatore in chop/bear.

## ⏭️ Prossimo esperimento (da fare) — hand-off Sentinel BULLISH → TF

**Domanda:** quando Sentinel dichiara BULLISH, se passo il capitale/posizione dal grid al **TF** (che può piramidare in salita e cavalca con trailing), quanto mi avvicino al hold — e quanto pago in falsi allarmi / whipsaw nel laterale?

**Cosa serve** (non è un quick-win, è un build): modellare nel backtest harness il comportamento del **TF** (entry su forza, no guardia "sopra avg", trailing/tier exit) come "ride mode" a piena allocazione, innescato dalla **detection causale di regime** (la stessa di questo esperimento). Confronto: grid-only vs grid+TF-handoff vs hold, su BTC/SOL/BONK × 3 regimi.

**Ipotesi:** il TF-handoff dovrebbe **superare** il trailing-sul-grid nel bull (può tenere posizione piena, non solo l'accumulato), **mantenendo** il grid come ammortizzatore fuori dal bull. Se regge su 3 coin, *quello* diventa la strategia da scrivere nero su bianco.

**Caveat da riportare comunque:** resta il limite N=1 per regime e il ritardo/errore di detection reale (Sentinel oggi è F&G-based; Phase B con EMA/RSI per-coin lo renderebbe più reattivo). Un mese per regime non è significatività statistica.

---

## Riprodurre
```
venv/bin/python3.13 scripts/backtest/trend_gate_experiment.py            # trail 4% (default)
TRAIL_PCT=30 venv/bin/python3.13 scripts/backtest/trend_gate_experiment.py
```
Output: tabella PLAIN vs GATED (causale) vs CEIL (crystal-ball) vs HOLD, per BTC/SOL/BONK × bear/bull/laterale, + cattura del rialzo. Read-only, cache 1m già presente.
