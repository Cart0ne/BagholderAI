# Report S99b — sell-ladder-audit — 2026-06-08

**Brief sorgente:** `config/2026-06-08_S99b_brief_sell-ladder-audit.md`
**Commit repo al momento dell'analisi:** `564ee3f` (main, fast-forward dal Mac Mini — solo chore newskeeper, 0 file codice bot).
**Tipo:** investigativo (nessun codice scritto). Risposte a Q1–Q4 con riferimenti precisi + dati Supabase live dell'8 giugno.
**Fonti dati:** `bot/grid/grid_bot.py`, `bot/grid/sell_pipeline.py`, `web_astro/public/grid.html`, tabelle Supabase `trades`, `bot_events_log`, `config_changes_log`.

> **Nota anti-drift (CLAUDE.md §7).** Il brief al rigo 87 indicava il naming `2026-06-08_S99b_report_sell-ladder-audit.md`. Ho usato la convenzione canonica `YYYY-MM-DD_SXX_RforCEO_SCOPE.md` → questo file. Lo scope `sell-ladder-audit` è ereditato identico dal brief, così l'Auditor accoppia brief↔report.

---

## Risposta sintetica (TL;DR)

| Q | Verdetto |
|---|----------|
| **Q1** | Il trigger è **avg_cost + sell ladder**, NON per-lotto. Il `reason` dei trade è corretto. Il **testo della dashboard è SBAGLIATO** (`grid.html:1102`, retaggio dell'era FIFO pre-S70). Correzione proposta sotto — non applicata (serve OK Board). |
| **Q2** | **Ipotesi CEO confermata al centesimo.** `NEXT SELL IF = reference × (1 + sell_pct/100 + FEE)/(1 − FEE)`, reference = `_last_sell_price` del ciclo. Con last sell SOL = $67.26 → $68.40 esatto. |
| **Q3** | **sell_pct 1.0% → 1.5% su SOL, modifica MANUALE (`changed_by='manual-ceo'`).** DB scritto 11:21:40 UTC, hot-reload applicato dal bot 11:24:16 UTC (~2,5 min di lag = polling config). NON Sherpa (DRY_RUN). |
| **Q4** | **Confermato.** Trigger penalty = `fill < avg` (price-based). BONK 8 giu: 5 sell tutte profittevoli (fill ≥ avg) nonostante slippage −3,45%/−4,08% → penalty mai armata su quelle vendite. È la logica intesa. |

---

## Q1 — Sell trigger: per-lotto o avg_cost?

**Risposta: avg_cost (con sell ladder sul prezzo dell'ultima vendita). NON per-lotto.**

Il bot, dopo la rimozione del FIFO queue in S70 FASE 2, non traccia più i singoli lotti: mantiene **due soli scalari**, `state.avg_buy_price` e `state.holdings`. Non esiste alcuna struttura "per-lotto" nel hot path.

Codice del trigger di vendita Grid — [bot/grid/grid_bot.py:826-835](bot/grid/grid_bot.py#L826-L835):

```python
if self.managed_by == "grid":
    threshold_pct = threshold_pct + self._sell_pct_penalty            # S98a
    reference = self._last_sell_price if self._last_sell_price > 0 else avg_cost
    sell_trigger = reference * (1 + threshold_pct / 100 + self.FEE_RATE) / (1 - self.FEE_RATE)
```

- `avg_cost = self.state.avg_buy_price` ([grid_bot.py:819](bot/grid/grid_bot.py#L819)) → un unico costo medio, non per-lotto.
- `reference` = prezzo dell'**ultima vendita del ciclo** (`_last_sell_price`) se >0, altrimenti l'avg cost (primo sell del ciclo). Questa è la "sell ladder" del brief 70a.
- La guardia Strategy A confronta sempre `price < bot.state.avg_buy_price` ([sell_pipeline.py:288](bot/grid/sell_pipeline.py#L288)).
- Il `reason` scritto sul trade ([sell_pipeline.py:698-701](bot/grid/sell_pipeline.py#L698-L701)) dice testualmente *"is {sell_pct}% above avg cost {sell_avg_cost}"* → **coerente con avg_cost**, come hai osservato.

**Il testo della dashboard è incoerente.** In [web_astro/public/grid.html:1102](web_astro/public/grid.html#L1102):

```js
'sell_pct': 'Per-lot trigger: sells when price rises this % above that lot\'s buy price',
```

Questo è un **fossile dell'era fixed-grid/FIFO** (pre-S70 FASE 2), mai aggiornato quando il bot è passato ad avg-cost. Va corretto.

### Correzione proposta per la dashboard (NON applicata — serve OK Board)

Sostituire `grid.html:1102` con testo accurato e nello stile conciso degli altri SUBLABEL:

```js
'sell_pct': 'Sell trigger: sells a slice when price rises this % (net of fees) above the cycle reference — the average buy cost on the first sell, then each prior sell\'s price (the "sell ladder"). Single average cost, not per-lot.',
```

---

## Q2 — Come viene calcolato NEXT SELL IF?

**Risposta: ipotesi CEO confermata.** La formula JS in [web_astro/public/grid.html:952-956](web_astro/public/grid.html#L952-L956):

```js
var ladderSellRef = botSellRef > 0 ? botSellRef : a.lastSellPrice;   // _last_sell_price dal runtime mirror
var sellRef = ladderSellRef > 0 ? ladderSellRef : a.avgBuyPrice;     // fallback avg cost
var nextSellTrigger = sellRef * (1 + sellPct / 100 + FEE_RATE) / (1 - FEE_RATE);   // FEE_RATE = 0.001
```

È **identica** alla formula del bot (grid_bot.py:833), con `reference = _last_sell_price` del ciclo corrente.

**Verifica numerica con i dati reali SOL dell'8 giugno** (tabella `trades`):

- Ultima vendita SOL prima della lettura dashboard: **12:58:39 UTC @ $67.26** (reason "1.5% above avg cost $65.05").
- `$67.26 × (1 + 0.015 + 0.001) / (1 − 0.001) = 67.26 × 1.016 / 0.999 = `**`$68.40`**.

Torna al centesimo. Il "non torna" del brief ($65.05 × 1.015 = $66.02) nasce dall'assumere `reference = avg_cost`: il reference reale è il prezzo dell'ultimo sell (la ladder), non l'avg.

### ⚠️ Finding secondario (coerenza dashboard ↔ codice)

La formula della dashboard usa **solo `sell_pct`**, NON include `_sell_pct_penalty` (l'Adaptive Sell Penalty S98a). Il bot invece somma la penalty al threshold (grid_bot.py:831). Quando una penalty è attiva (es. BONK dopo un sell in perdita), **la dashboard SOTTOSTIMA il vero trigger del bot**. L'8 giugno su SOL la penalty era 0 → coincidono; su BONK con penalty 3,96% no. Inoltre il runtime mirror (`bot_runtime_state`) non espone affatto il campo penalty, quindi oggi la dashboard non potrebbe mostrarla nemmeno volendo. È lo stesso genere di incoerenza dashboard↔codice di Q1, ma sul lato formula. Segnalato per decisione (eventuale brief separato, non in questo scope).

---

## Q3 — Config change SOL alle 11:24 UTC

**Risposta: era `sell_pct` da 1.0% a 1.5%, modifica MANUALE.** Niente ambiguità.

Tabella `config_changes_log` (audit con attore):

| created_at (UTC) | parameter | old | new | changed_by |
|---|---|---|---|---|
| 2026-06-08 **11:21:40** | sell_pct | 1 | 1.5 | **manual-ceo** |

Tabella `bot_events_log` (evento di hot-reload lato bot):

| created_at (UTC) | event | details.changes |
|---|---|---|
| 2026-06-08 **11:24:16** | config_changed_bot_config | `[{"key":"sell_pct","new":"1.5","old":"1.0"}]` |

Tre punti:

1. **Il campo ERA registrato.** Il messaggio "1 field(s)" è solo il sommario human-readable; il campo specifico è in `details.changes` (e in `config_changes_log`). Quindi non c'è perdita d'informazione, solo un sommario poco esplicito.
2. **Chi: manuale (`changed_by='manual-ceo'`)** — scrittura diretta su `bot_config` via admin panel. **Non Sherpa**: il `config_writer.py` di Sherpa scrive su `bot_config` **solo in LIVE** e taggherebbe `changed_by='sherpa'` ([bot/sherpa/config_writer.py:4,31-43](bot/sherpa/config_writer.py#L31-L43)); Sherpa è in DRY_RUN (PROJECT_STATE §1/§7), quindi scrive solo proposte su `sherpa_proposals`, mai su `bot_config`.
3. **Hot-reload + lag.** Il DB è stato scritto alle 11:21:40; il bot ha rilevato e applicato la modifica alle 11:24:16 (~2,5 min dopo) via `_sync_config_to_bot` ([bot/grid_runner/config_sync.py:22](bot/grid_runner/config_sync.py#L22)), che emette l'evento `config_changed_bot_config` solo quando il valore cambia davvero. Questo spiega perché le prime 2 vendite SOL (02:16 e 09:44) hanno reason "1.0%" e dalla terza (12:58) in poi "1.5%".

---

## Q4 — Adaptive Sell Penalty: trigger su perdita o su slippage?

**Risposta: trigger PRICE-BASED su `fill < avg` (non su slippage, non su realized_pnl). È la logica intesa.** Confermato.

Codice — [bot/grid/sell_pipeline.py:513-521](bot/grid/sell_pipeline.py#L513-L521):

```python
is_grid_strategy_a = (bot.managed_by == "grid" and bot.strategy == "A")
if is_grid_strategy_a and sell_avg_cost > 0:
    if price < sell_avg_cost:                                   # FILL sotto avg
        loss_pct = (sell_avg_cost - price) / sell_avg_cost * 100
        bot._sell_pct_penalty = loss_pct                        # v2: ultima perdita, NON cumulativo
    elif bot._sell_pct_penalty > 0:                             # FILL >= avg
        bot._sell_pct_penalty = 0.0                             # reset
```

Il trigger guarda `price` (= fill post-slippage) vs `sell_avg_cost`, **non** lo slippage in sé e **non** `realized_pnl` (scelta deliberata: una perdita da sola fee darebbe `loss_pct` negativo e abbasserebbe la soglia — vedi commento [sell_pipeline.py:510-511](bot/grid/sell_pipeline.py#L510-L511)).

**Dati BONK 8 giugno** (tabella `trades`, 5 sell in 4 minuti, avg cost $0.00000433):

| Ora UTC | Fill | realized_pnl | Slippage | Fill vs avg | Penalty |
|---|---|---|---|---|---|
| 13:01:09 | $0.00000448 | +$0.76 | −3,45% | **>** avg | reset (era 3,96%) |
| 13:02:12 | $0.00000447 | +$0.71 | −3,66% | **>** avg | resta 0 |
| 13:03:16 | $0.00000447 | +$0.71 | −3,66% | **>** avg | resta 0 |
| 13:04:19 | $0.00000447 | +$0.71 | −3,66% | **>** avg | resta 0 |
| 13:05:28 | $0.00000447 | +$0.30 | −4,08% | **>** avg | resta 0 |

Tutte e 5 le vendite hanno fill **sopra** l'avg cost (profittevoli) → la penalty non si è mai armata, esattamente come descritto nel brief. L'evento `sell_penalty_reset` delle 13:01:09 conferma: la penalty era 3,96% (residuo di una perdita precedente) e il primo sell profittevole l'ha azzerata. Questo è il **comportamento by-design v2** (S98a): "ultima perdita osservata, auto-guarente al ripopolarsi del book". La penalty protegge dai sell **sotto avg**, non da slippage su sell **sopra avg** — coerente con l'intento, ma è il buco che la Proposta Board vuole chiudere.

---

## Contesto bonus — perché SOL spalmata su 15h e BONK in burst

Non era richiesto esplicitamente ma chiude il cerchio del "problema osservato".

**SOL — gated dal dead-zone 4h.** Eventi `dead_zone_recalibrate` su SOL l'8 giugno: 02:15, 09:42, 16:59 UTC. Il meccanismo:
1. Dopo ogni sell la ladder (`_last_sell_price`) alza il trigger successivo sopra l'ultimo fill.
2. Il prezzo non risale abbastanza per toccarlo.
3. Dopo 4h di inattività con prezzo sopra avg, il dead-zone azzera la ladder → il trigger torna a `avg × (1+sell_pct+fee)/(1−fee)`, sotto il prezzo corrente → un sell scatta entro 1-2 minuti.

Sequenza: recalibrate 02:15 → sell 02:16 → recalibrate 09:42 → sell 09:44 → (sell_pct 1.0→1.5 alle 11:24) → sell 12:58 → recalibrate 16:59 → sell 17:00. È letteralmente il dead-zone a cadenzare le vendite ogni ~4h.

**BONK — ladder bypassata dal momentum.** Il prezzo BONK era ~7% sopra l'avg, ben oltre i gradini della ladder a sell_pct 2,5%, quindi ogni tick (~60s) il trigger bumpato era già superato → 5 sell consecutivi. **Sottigliezza:** la ladder si ancora al **fill** (`_last_sell_price = price` post-slippage, [sell_pipeline.py:638](bot/grid/sell_pipeline.py#L638)), non al check price. Lo slippage −3,5% di BONK quindi *abbassa* il gradino successivo della ladder, rendendo il sell seguente ancora più facile — un effetto che accelera il burst su book sottile. Dato utile per la discussione anti-slippage del Board.

---

## Decisioni / cosa serve dal Board

- **Q1-Q4: nessuna decisione delegata a CC** (brief investigativo). Risposte sopra.
- **Fix testo dashboard (Q1):** correzione proposta, **NON applicata**. Una riga in `grid.html:1102`, web-only, no bot/no restart. Aspetto OK per shipparla (eventualmente insieme alla decisione sul finding secondario di Q2).
- **Finding secondario Q2 (penalty non riflessa in NEXT SELL IF):** segnalo, non risolvo. Se il Board vuole allinearla servirebbe esporre `_sell_pct_penalty` nel runtime mirror + sommarla nella formula JS — brief separato.
- **Proposta Board anti-slippage:** ho fornito i dati (Q4 + sezione bonus). La mia obiezione tecnica si allinea all'auto-obiezione del CEO: su testnet lo slippage BONK è strutturale (3-4%), quindi una penalty su-slippage-anche-in-profitto congelerebbe BONK proprio come il deadlock cumulativo che S98 ha corretto. Se si procede, serve la soglia minima (~1%) già ipotizzata dal CEO. Da discutere in sessione dedicata.

---

## Roadmap impact

- Nessuno immediato (brief investigativo).
- Q1 conferma un'incoerenza dashboard pre-mainnet (Phase 9 V&C "dashboard coherence S74b ✅" non copriva i SUBLABEL testuali) → fix testuale 1 riga, gating cosmetico.
- L'evoluzione anti-slippage, se approvata, diventa un brief operativo separato.
