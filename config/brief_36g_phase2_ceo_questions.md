# BRIEF CEO — Session 36g Phase 2: TF compounding policy decisions

**Date:** 2026-04-17
**Ask:** 4 decisioni di policy per attivare il compounding pieno nel TF
**Context:** Phase 1 già implementata (non deployata). Il TF budget effettivo ora cresce col profitto dei bot deallocati (es: oggi +$7.61). Phase 2 estende il compounding ai bot vivi — richiede queste 4 scelte.

---

## Decisione 1 — Sanity cap su `tf_total_capital`

**Problema**: con compounding esplosivo il TF potrebbe voler allocare cifre fuori scala rispetto al capitale iniziale. Es: se il bot raddoppia il budget ($100 → $200) in 30 giorni, senza cap nulla lo ferma a $500+.

**Opzioni**:
- **A. Nessun cap** → compound libero, rischio allocazioni enormi se un bot esplode
- **B. Cap assoluto $300** (3× budget nominale) → limita a ragione di crescita 3x
- **C. Cap dinamico** = max($300, tf_budget_nominale × N) dove N è configurabile

**Raccomandazione**: **B — cap a $300**. Quando (se) lo raggiungiamo ne riparliamo e decidiamo se alzarlo. Facile da cambiare via DB.

---

## Decisione 2 — `tf_lots_per_coin`

**Problema**: oggi hardcoded a 4 (`capital_per_trade = alloc / 4`). Con compound che fa crescere alloc, il per-trade cresce proporzionalmente. Esempio: alloc $50 → 4 × $12.50. Alloc $100 → 4 × $25. Preferisci più granularità (tanti lot piccoli) o meno (pochi lot grossi)?

**Opzioni**:
- **A. Fisso 4** (oggi) → più reazioni ai dip, granulare, default sicuro
- **B. Fisso 3** → trade più sostanziosi, meno fee, meno flessibilità
- **C. Adattivo**: 4 se alloc < $100, 3 se ≥ $100 → equilibrio

**Raccomandazione**: **A (fisso 4) per ora**. Se vediamo che con compound i $25/lot diventano troppo grossi rispetto alla depth di mercato per coin piccole, passeremo a C. Cambio DB triviale.

---

## Decisione 3 — `RESIZE_THRESHOLD_USD`

**Problema**: quando il TF budget effettivo cresce, i bot vivi devono essere "resize-ati" (alloc aggiornata). Ma se il threshold è troppo basso il sistema fa UPDATE continue per micro-fluttuazioni (un sell da $0.30 triggerebbe resize). Se troppo alto, il compound tarda a propagarsi.

**Opzioni**:
- **A. $5** → resize quasi ad ogni sell profittevole, compound continuo
- **B. $10** → reazioni solo a variazioni consistenti, meno UPDATE DB
- **C. $20** → molto conservativo, compound propagato solo in burst

**Raccomandazione**: **B — $10**. Traduce a "resize solo quando ho accumulato almeno $10 da ridistribuire", evita churn DB ma mantiene reattività.

---

## Decisione 4 — Cap assoluto su `capital_per_trade`

**Problema**: se il TF esplode (es. budget $300) e abbiamo 2 coin attive, ciascuna otterrebbe $150, 4 lot da $37.50. Se scendiamo a 1 coin, $300 su una coin = 4 × $75. Su paper $500 iniziali è over-concentration.

**Opzioni**:
- **A. Nessun cap** → laissez-faire, rischio concentrazione
- **B. Cap assoluto $50/trade** → sicurezza forte, compound utilizza più lot se serve
- **C. Cap % = 10% del Net Worth per trade** → cap dinamico proporzionale al portfolio

**Raccomandazione**: **B — $50 hard cap**. Semplice, chiaro. Se in futuro il portfolio cresce molto potremo rialzarlo. Per ora tutela contro un bot che da solo rischia 1/5 del patrimonio in un singolo trade.

---

## Altre note (FYI, non richiedono decisione)

- **Skim su floating riassorbito**: confermato `YES` (stessa logica, grid_bot skima qualsiasi sell profittevole indipendentemente dall'origine del cash). Già gestito.
- **Reset emergency floating**: per ora **skip**. Se mai servirà, aggiungeremo `tf_floating_reset_at` in `trend_config` (1 giorno di lavoro). Non blocca nulla.
- **Anomalia MBOX**: il bot MBOX ha `realized_net = $3.09` ma `gross_cash_flow = $0.74` e `skim totale = $0.93` (skim > profit effettivo → floating contribution negativo). Da investigare separatamente (probabile bug in FIFO matching del grid_bot). Non blocca 36g ma vale brief a parte.

---

## Cosa serve dal CEO

Risposta sintetica tipo: `1=B, 2=A, 3=B, 4=B` oppure varianti con commento breve. Appena abbiamo le 4 decisioni procedo con implementazione Phase 2 + deploy.
