# RforCEO — grid-regime-backtest (Fase 1, BTC)

**Data:** 2026-06-30 · **Sessione:** S113 (estemporanea, esecuzione brief S110) · **Autore:** Claude Code (Intern)
**Brief sorgente:** `config/2026-06-28_S110_brief_grid-regime-backtest.md`
**Commit:** nessuno ancora (tooling read-only in `scripts/backtest/`, output gitignored in `audits/backtest/`; committo su tua richiesta).
**Stato:** deliverable COMPLETO + due test aggiuntivi richiesti da Max (vero laterale + maker/taker).

---

## 0. TL;DR (3 righe)

Il backtest doveva mappare il grid nei 3 regimi. Ha fatto di più: **ha scoperto un bug reale** (churn da reset-avg-su-polvere) che è **invisibile su Binance e un perdi-soldi su Kraken** — confermato sui trade veri del testnet. Una volta "riparato" il bot in simulazione, il quadro onesto è che **il grid è un ammortizzatore di volatilità, non un motore di rendimento**: batte hold solo nel laterale vero, e di poco. **Due decisioni per il Board** (sotto).

---

## 1. Metodo (cosa è fedele, cosa è semplificato)

- **Simulatore fedele** del loop reale `grid_runner`/`grid_bot`: stop-buy, dead-zone, idle re-entry, ladder sell net-of-fee, skim 30%, Strategy A. **Validato contro i trade veri** del bot testnet (vedi §2).
- **Parametri congelati** = snapshot `bot_config` BTC del 2026-06-30 (buy 2.5% / sell 1.0% / skim 30% / idle 4h / stop-buy −3% / cooldown 30min / min_profit off). In LIVE Sherpa li muoverebbe: questo è il **caso a freno fisso** (come da brief).
- **Fee = Kraken** (venue mainnet, S112b): **taker 0.40%** primario (i market order del grid sono taker), maker 0.25% come variante. Confronto a 0.10% solo per mostrare l'illusione testnet.
- **Capitale $250** (brief; testnet live è $200, target mainnet S112b è $250). **Risoluzione 1m**, fill sul close (fedele al polling 60s). **Solo grid puro** (no TF/Sentinel/Sherpa/NewsKeeper).
- **Limiti dichiarati:** un mese per regime NON è statisticamente significativo (vale il pattern, non il centesimo); granularità 1m perde i micro-rimbalzi; dati prezzo da Binance (storico profondo), fee modellata su Kraken.

---

## 2. Il finding principale: churn da polvere (un bug, non un'opinione)

Il backtest ha mostrato il grid che **perde in tutti e tre i regimi** a fee Kraken. Indagando: il grid svende fino alla **polvere**, azzera l'avg ma **tiene** le monetine (finding S111, `realized_pnl_avg_cost_fixB`). La polvere accumulata **diluisce l'avg al re-entry** → il trigger di sell risulta già superato → **il bot vende ~1 minuto dopo aver comprato, allo stesso prezzo**, pagando solo le fee.

**Prova sui trade VERI del testnet** (non simulati):

```
buy  65017.60  15:26
sell 65081.19  15:27   realized +$0.545   ← 1 min dopo, +0.10% prezzo, "profitto" $0.55 (fantasma)
```

…ripetuto decine di volte, buy distanziati ~4h (la cadenza idle re-entry). Realized fantasma cumulato $10.63 ≈ il "+$9" del finding S111. **Il simulatore è fedele; il bug è nel bot reale.**

- Su **Binance (0.10%)**: il churn è quasi invisibile e *mascherato* dal realized fantasma (sembra che guadagni).
- Su **Kraken (0.40%, 4×)**: brucia soldi veri, **peggio nei trend** (il grid è fermo → re-entry continuo ogni 4h).

> ⚠️ **Questo cambia l'inquadramento del brief.** Il brief (28/06) diceva "NON è un gate per il mainnet". Era prima di sapere questo: il churn è un **perdi-soldi su Kraken in tutti i regimi**. Proponiamo di **promuoverlo a gate pre-cutover-Kraken**.

---

## 3. Il quadro onesto col bot "riparato" (counterfactual)

"Riparato" = l'avg **operativo** non si azzera sulla polvere (la trattiene al costo vero) → niente diluizione → niente churn. **È più del Fix B parcheggiato** (che sistemava solo il *numero* realized): qui si sistema l'avg che guida le **decisioni di trading**. La guard Strategy A resta esente sulla polvere (S105b) → niente dust-trap.

### Mappa per regime (grid RIPARATO, fee Kraken)

| Regime BTC | Hold | Grid taker 0.40% | Grid maker 0.25% | Lettura |
|---|---|---|---|---|
| **Bull +37%** (nov-2024) | **+36.6%** | +5.4% | +5.4% | cattura solo il **15%** del rialzo (vende presto, si perde il trend) |
| **Bear −37%** (giu-2022) | **−37.5%** | −28.4% | −20.5% | perde, ma ammortizzato (~76% del ribasso a taker, meno a maker) |
| **Laterale-su +3.9%** (set-2023) | +3.5% | +0.6% | +0.5% | sotto hold: c'è un driftino che hold cattura e il grid no |
| **Laterale VERO +0.07%** (feb-2023, 17 swing) | −0.3% | **+0.4%** | **+0.8%** | **batte hold** + drawdown −2% vs −8% |

**Effetto del fix (riparato − attuale, stessa fee Kraken):** Bull **+29 p.p.**, Laterale-set **+16 p.p.**, Bear −9 p.p.* (*nel bear il bot ATTUALE sembra "meglio" solo perché il churn lo svuota in cash il 60% del tempo — de-risk involontario, non una virtù).

### Cosa dicono questi numeri

Il grid è un **ammortizzatore di volatilità**, non un motore di rendimento: **taglia entrambe le code** (meno su, meno giù). L'unico regime dove batte hold è il **laterale genuino**, e di **poco** (sub-1%/mese), con il vero valore nella **riduzione del drawdown** (−2% vs −8%), non nel rendimento assoluto. Nei trend è strutturalmente l'opposto del trend-following (vende i vincenti, tiene i perdenti).

---

## 4. La leva maker/taker

Il grid usa **market order (taker 0.40%)**. Con **ordini limite sulla scala (maker 0.25%)** la fee scende E il trigger di sell si stringe (più raccolta):
- **Bear:** −28.4% → **−20.5%** (+8 p.p., grosso)
- **Laterale vero:** +0.4% → **+0.8%** (raddoppia l'edge)
- Bull/laterale-set: invariati (il grid trada poco lì)

Non ribalta i verdetti bull/laterale-su, ma **dimezza il sanguinamento nel bear e raddoppia l'edge nel chop**. Caveat: assume che i limiti si riempiano (limite superiore del beneficio). Si collega alla domanda di cutover già aperta (`modello-grid: market vs ladder a limiti`, PROJECT_STATE §3).

---

## 5. Decisioni richieste a CEO/Board

1. **[Tecnica, urgente] Fix del churn = gate pre-cutover-Kraken?** Promuovere il Fix B (esteso all'avg operativo) a brief di fix da chiudere **prima** del cablaggio Kraken. Tocca trading logic LIVE (buy guard, ladder, **skim** dipende dal realized) → brief dedicato + test + restart. *Raccomandazione CC: SÌ, è un perdi-soldi reale su Kraken.*
2. **[Tecnica/strategica] Modello-ordini grid su Kraken: market (taker) o limite (maker)?** Già domanda di cutover; il backtest dà evidenza a favore dei limiti. *Raccomandazione CC: valutare maker/limite nel brief di cutover.*
3. **[Strategica, Board] Aspettative sul go-live €600.** I numeri dicono: il grid **non arricchisce** — segue BTC con meno volatilità, sotto nei rialzi, sopra nei ribassi/piatto. Coerente con la tesi del progetto (*"crypto is the lore, not the product"*): i €600 sono banco di prova narrativo, non piano di profitto. **Il Board conferma il go-live come esperimento-storia, con aspettative ricalibrate?**

---

## 6. Anti-assenso / decision log

- **Obiezione al brief:** "non è un gate per il mainnet" non regge più dopo il finding — il churn è un perdi-soldi su Kraken. Flaggato (§2).
- **Obiezione al mio stesso output:** "grid perde ovunque" era dominato da un artefatto (churn). Ho fermato e isolato il problema invece di pubblicare numeri fuorvianti. Poi: "grid dominato da hold" era prematuro senza testare il laterale vero → testato (feb-2023) → il grid lì batte hold. Entrambe le volte ho evitato una conclusione disonesta.
- **DECISIONE (modello "riparato"):** ho modellato il fix come "avg operativo non azzerato sulla polvere", che è **più** del Fix B parcheggiato (solo-reporting). RAZIONALE: il churn nasce dall'avg operativo, non dal numero. ALTERNATIVE: dust write-off su sellout (abbandona ~$2/mese di polvere) — scartato perché perde valore inutilmente. FALLBACK: è un flag isolato nel simulatore, reversibile.
- **Cosa NON ho fatto:** nessun tocco a `bot/`, `bot_config`, DB. Tutto read-only. Nessun commit senza tua richiesta.

---

## 7. Artefatti (locali, gitignored in `audits/backtest/`)

- `report_grid_regime_backtest.md` (3 scenari, attuale vs riparato vs hold) + `report_extra_tests.md` (laterale vero + maker/taker)
- 11 grafici PNG (`charts/`, `charts_extra/`): prezzo+marker e equity per scenario
- `frozen_params_BTC.json` (snapshot congelato) + trade CSV per ispezione
- Tooling riutilizzabile: `scripts/backtest/` (fetch/params/grid_sim/hold_sim/metrics/plots/run_backtest/extra_tests) — pronto per Fase 2 (SOL/BONK) e altri periodi.

*I grafici sono locali (Max li vede nel repo); il CEO legge le tabelle qui sopra, che contengono tutti i numeri.*
