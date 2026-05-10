# Brief 70a — sell_pct net-of-fees + sell graduale

**Data:** 2026-05-10  
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-09 (S69 chiusura, commit cb21179)  
**Autore:** CEO  
**Priorità:** pre-mainnet gate (gating go-live €100)  
**Stima:** ~3-4h (piano italiano + implementazione + test)

---

## Contesto

Due problemi connessi nel sell attuale:

1. **Le fee mangiano il profitto dichiarato.** Il sell trigger è `price >= avg × (1 + sell_pct/100)` ma non tiene conto delle fee di acquisto e vendita. Con un round-trip di 0.2% (buy fee + sell fee), un sell_pct del 2% rende in realtà ~1.8% netto. Su €100 sono centesimi reali.

2. **Il bot compra gradualmente ma vende tutto in ~3 tick.** I buy sono DCA a scala (ogni -buy_pct% sotto l'ultimo buy). Ma quando il sell trigger scatta, vende `capital_per_trade / price` a ogni tick da 60s finché holdings = 0. Di fatto svuota in 2-3 minuti. Il Board vuole un sell speculare ai buy: graduale, a scala verso l'alto.

---

## Cosa implementare

### Parte 1 — Fee nette nel sell trigger

**FEE_RATE = 0.001** (0.1%) — costante in `config/settings.py`. NON parametro in `bot_config`. È una scelta di business conservativa (worst-case Binance), non un tuning del bot. Se Binance ci fa lo sconto BNB, guadagniamo di più senza cambiare codice.

**Formula sell trigger aggiornata:**

```python
sell_trigger = avg_buy_price * (1 + sell_pct / 100 + FEE_RATE) / (1 - FEE_RATE)
```

Questo garantisce che `sell_pct`% sia il profitto NETTO dopo aver coperto entrambe le fee (buy + sell).

**File da toccare:** `bot/grid/sell_pipeline.py` (condizione sell trigger), `config/settings.py` (costante FEE_RATE se non già a 0.001).

**Attenzione:** `bot.FEE_RATE` esiste già nel codice (oggi a 0.00075). Va portato a 0.001 e usato nella formula del trigger. Verificare che FEE_RATE sia usato coerentemente ovunque (sell_pipeline, buy_pipeline, commentary, dashboard).

### Parte 2 — Sell graduale (speculare ai buy)

**Meccanismo:** il sell diventa una scala verso l'alto, specchio esatto del buy verso il basso.

- **Primo sell** (nessun sell nel ciclo corrente): trigger = `avg × (1 + sell_pct% + fee)` (formula Parte 1)
- **Sell successivi**: trigger = `last_sell_price × (1 + sell_pct%)`
  - Nota: le fee sono già coperte dal primo sell. I gradini successivi possono usare sell_pct% diretto.
- **Reset**: quando `holdings <= 0` (fully sold out), `_last_sell_price = 0`. Ciclo chiuso, pronto per nuovo accumulo.

**Nuovo campo state:** `_last_sell_price` (float, default 0). Speculare a `_pct_last_buy_price`.

- Inizializzato a 0 in `__init__`
- Settato al prezzo di vendita dopo ogni sell riuscito
- Resettato a 0 quando holdings arrivano a 0
- Persistenza: salvato/letto da `state_manager.py` → leggere da ultimo sell in `trades` al boot (come `_pct_last_buy_price` legge dall'ultimo buy)

**Sell amount:** invariato — `capital_per_trade / price` per ogni gradino. L'ultimo sell svuota i residui se holdings < 1 lotto (logica dust già esistente).

**Esempio concreto** (BTC, sell_pct=2%, FEE_RATE=0.001, 3 lotti accumulati):
- avg_buy = $80,000
- 1° sell a $81,762 (avg × 1.02 / 0.999 ≈ +2.2%) → vende 1 lotto, last_sell = $81,762
- 2° sell a $83,397 (last_sell × 1.02) → vende 1 lotto, last_sell = $83,397
- 3° sell a $85,065 (last_sell × 1.02) → svuota, last_sell reset a 0

Se il prezzo sale a $82,500 e poi scende → venduto solo 1 lotto in profitto, 2 lotti in bag. Bagholder by design.

**File da toccare:**
- `bot/grid/sell_pipeline.py` — trigger condition + set `_last_sell_price`
- `bot/grid/grid_bot.py` — `__init__` nuovo campo + reset nel ciclo
- `bot/grid/state_manager.py` — lettura `_last_sell_price` da DB al boot
- `grid.html` — widget "Next sell if ↑" va aggiornato: mostrare il prossimo gradino reale (basato su last_sell_price se > 0, altrimenti su avg)

### Parte 3 — Aggiornamento dashboard grid.html

Il widget "Next sell if ↑" (commit cb21179) va aggiornato per riflettere la nuova logica:
- Se nessun sell nel ciclo: mostra `avg × (1 + sell_pct% + fee) / (1 - fee)`
- Se c'è già stato un sell: mostra `last_sell_price × (1 + sell_pct%)`
- Label: mostrare il gradino corrente (es. "Sell #2 if ↑")

### Parte 4 — Post-fill warning su slippage > buffer (aggiunta CEO 2026-05-10)

**Contesto:** S70 2026-05-10 sell BONK at loss (fill 0.46% sotto avg, slippage 2.46% > sell_pct=2% buffer). La guard pre-trade a [sell_pipeline.py:282](../bot/grid/sell_pipeline.py#L282) ha visto `check_price >= avg × (1+sell_pct/100)` e ha lasciato passare; il fill è poi atterrato sotto avg per slippage testnet (book BONK sottile). Nessun log esplicito ha segnalato l'anomalia post-fill — il `reason` dichiarava persino "above avg" usando il fill_price (open question 27 BUSINESS_STATE). Su mainnet con book denso lo slippage sarà <0.1%, ma uno spike isolato (news, flash crash, withdrawal di market maker) può comunque portare un fill sotto avg.

**Cosa fare:**

Subito dopo ogni sell riuscito (in `sell_pipeline.py`, dopo che il fill è scritto in `trades` e l'event `sell_avg_cost_detail` è loggato), aggiungere un controllo:

```python
if fill_price < sell_avg_cost:  # sell_avg_cost = snapshot avg_buy_price pre-trade
    gap_pct = (fill_price - sell_avg_cost) / sell_avg_cost * 100
    log_event(
        severity="warn",
        category="trade_audit",
        event="slippage_below_avg",
        symbol=bot.symbol,
        message=f"Slippage exceeded: fill {fmt_price(fill_price)} below avg cost {fmt_price(sell_avg_cost)} ({gap_pct:+.2f}%)",
        details={
            "fill_price": float(fill_price),
            "avg_buy_price": float(sell_avg_cost),
            "gap_pct": float(gap_pct),
            "sell_pct_config": float(bot.sell_pct),
            "implied_slippage_pct": float(bot.sell_pct - gap_pct),
            "managed_by": getattr(bot, "managed_by", "grid"),
        },
    )
```

**Non bloccare il trade** — l'ordine market è già eseguito su Binance, non si può annullare. È puro warning informativo.

**File da toccare:** `bot/grid/sell_pipeline.py` (un blocco subito dopo l'event `sell_avg_cost_detail`).

**No Telegram alert.** Il warning vive in `bot_events_log`. Step B reconcile (Sessione futura) renderà visibili anche questi eventi nel pannello /admin (memoria `feedback_no_telegram_alerts`).

**Esclusioni:**
- TF force-liquidate path (`bot.pending_liquidation` o stop-loss/trailing-stop/take-profit/profit-lock/gain-saturation triggered): qui il sell sotto avg è atteso per design, non un'anomalia. Saltare il warning.

**Edge case:** se Binance restituisce 0 fill (molto raro su market order ma possibile in casi limite), il warning non scatta perché non c'è trade scritto.

---

## Decisioni delegate a CC

- Scelta del pattern di persistenza per `_last_sell_price` (stessa strategia di `_pct_last_buy_price`, leggi dall'ultimo sell in `trades`)
- Gestione edge case: se holdings residui < 1 lotto dopo un sell, il prossimo sell svuota tutto (dust logic esistente, non cambiare)
- Naming delle variabili e reason strings

## Decisioni che CC DEVE chiedere

- Se emerge qualche conflitto con greed-decay / gain-saturation / force-liquidation path (TF override): STOP e chiedere al Board
- Se il cambio a FEE_RATE 0.001 rompe qualche test esistente in modo non ovvio

## Output atteso

1. Codice funzionante con test nuovi (almeno 4):
   - test: sell trigger include fee (verifica che il trigger sia più alto del sell_pct% nudo)
   - test: sell graduale — 3 lotti venduti a 3 prezzi crescenti
   - test: reset `_last_sell_price` dopo fully sold out
   - test: post-fill warning loggato quando fill_price < avg_buy_price (Parte 4); NON loggato per TF force-liquidate path
2. `FEE_RATE = 0.001` in settings.py
3. Widget grid.html aggiornato
4. Nessuna regressione sui test esistenti

## Vincoli

- **NON toccare** buy_pipeline.py (i buy non cambiano)
- **NON toccare** il TF path (force-liquidation, greed-decay, trailing stop — quelli vendono tutto, non a gradini)
- **NON aggiungere** colonne DB. `_last_sell_price` si ricostruisce dal DB come `_pct_last_buy_price`
- **NON implementare** il timer patience (TODO futuro, post dati reali)
- **NON bloccare** il trade nel post-fill warning di Parte 4 (l'ordine market è già eseguito su Binance, non annullabile)
- **NO Telegram alert** per il post-fill warning (memoria `feedback_no_telegram_alerts`); solo `bot_events_log`
- **Task > 1h → piano in italiano** leggibile da Max prima di scrivere codice

## Roadmap impact

Chiude il pre-live gate "sell_pct net-of-fees". Apre il sell graduale come nuova feature della Strategy A. Parte 4 (post-fill warning) chiude parzialmente open question 27 BUSINESS_STATE (slippage post-fill non più invisibile, anche se il "reason bugiardo" sulla stringa rimane TODO separato).

---

## Nota implementazione CC (2026-05-10, S70 chat con Max)

Due chiarimenti emersi prima dell'implementazione:

**(A) Scope fee buffer = Grid only.** La nuova formula `(1+sell_pct/100+FEE)/(1-FEE)` si applica solo a `bot.managed_by == "grid"`. TF e tf_grid mantengono la formula vecchia `avg × (1 + threshold_pct/100)` per non alterare la calibrazione greed-decay già fatta sul counterfactual. Da rivisitare quando si ricollegano i brain.

**(B) Formula uniforme primo + gradini.** Il brief originale (Parte 2) proponeva fee buffer solo sul primo sell, gradini successivi in `last_sell × (1+sell_pct/100)` puro. Analisi numerica ha mostrato che il marginale netto sui gradini sarebbe ~1.9% (non 2%) per la fee sell. Decisione Max: **stessa formula per tutti i gradini** con fee buffer:

```python
reference = bot._last_sell_price if bot._last_sell_price > 0 else bot.state.avg_buy_price
sell_trigger = reference * (1 + sell_pct/100 + FEE_RATE) / (1 - FEE_RATE)
```

Pro: 1 sola formula in codice + dashboard, semantica chiara ("sell_pct% netto sopra il riferimento"). Contro: ~0.1% over-buffer ("fee buy fantasma") sui gradini successivi — accettato come buffer micro-slippage. Su €100 / 50 trade l'anno: differenza in centesimi.

*CEO, 2026-05-10 — note CC, 2026-05-10*
