Brief S98a — sell-loss-guard — 2026-06-06

Basato su: PROJECT_STATE.md aggiornato 2026-06-05 (sera, S99/brief S97b).

---

## Contesto

Il 6 giugno 2026 alle 09:07–09:15 UTC, il Grid Bot BONK ha eseguito 7 sell
consecutivi in perdita (totale ~−$5.31 realized P&L). Causa: il prezzo ticker
(check) superava la soglia sell_pct (2.5% sopra avg_cost), ma il fill del
market order su testnet arrivava 4–14% sotto il check price a causa del book
vuoto. La guardia Strategy A ("never sell at loss") controlla il prezzo
pre-esecuzione, non il fill — è corretta by design, ma non protegge dallo
slippage post-fill.

Serve un meccanismo **post-fill** che, dopo un sell in perdita, alzi la soglia
di vendita proporzionalmente al danno subìto, impedendo al bot di ripetere
l'errore in ciclo stretto.

## Meccanismo: Adaptive Sell Penalty

### Logica

1. Ogni coin mantiene una variabile in-memory `_sell_pct_penalty` (default 0.0).

2. Dopo ogni sell, il bot controlla il `realized_pnl` del fill:
   - **Se negativo**: calcola la perdita percentuale rispetto all'avg_cost al
     momento del sell, ossia `loss_pct = (avg_cost - fill_price) / avg_cost × 100`.
     Somma `loss_pct` a `_sell_pct_penalty`.
   - **Se zero o positivo**: azzera `_sell_pct_penalty` a 0.0 (reset).

3. La soglia di vendita effettiva diventa:
   `effective_sell_pct = sell_pct + _sell_pct_penalty`

   Esempio: sell_pct base = 2.5%, fill in perdita del 4% → penalty = 4% →
   soglia effettiva = 6.5%. La prossima vendita scatta solo se il prezzo è
   6.5% sopra avg_cost.

4. La penalty si **accumula**: se due sell consecutivi sono in perdita (4% + 3%),
   penalty = 7%, soglia = 9.5%. Questo è corretto: se ogni vendita peggiora,
   il bot alza progressivamente l'asticella.

5. Reset al base: un singolo sell con realized_pnl >= 0 azzera la penalty.
   Razionale (Board S98): un sell profittevole dimostra che il mercato supporta
   l'esecuzione → la situazione è rientrata.

### Persistenza al restart

Al restart del bot, `_sell_pct_penalty` in memoria sparisce. Il bot deve
ricalcolarla dall'ultimo sell nel DB per quella coin+cycle:

- Query: ultimo trade `side='sell'` per la coin nel ciclo corrente.
- Se `realized_pnl < 0`: calcola `loss_pct` dal fill e dall'avg_cost al
  momento del sell. L'avg_cost del sell è ricostruibile dal campo `reason`
  (che già logga "avg cost $X") oppure da un campo dedicato (vedi sezione
  "Decisioni delegate a CC").
- Se `realized_pnl >= 0` o nessun sell nel ciclo: penalty = 0.

**Attenzione**: per il ricalcolo serve conoscere l'avg_cost *al momento
del sell*. Oggi il campo `reason` contiene questa info come testo libero.
Valutare se aggiungere una colonna `sell_avg_cost` alla tabella `trades` per
rendere il ricalcolo robusto (vedi sotto).

### Scope

- **Si applica a**: sell `managed_by = 'grid'` (bot manuali, Strategy A).
- **NON si applica a**: sell da Trend Follower (managed_by in `'tf'`, `'tf_grid'`).
  I sell TF già bypassano Strategy A (stop-loss, trailing, ecc.) — la penalty
  non deve interferire con le uscite di emergenza.

### Dove toccare il codice

| File | Cosa cambia |
|------|-------------|
| `bot/grid/grid_bot.py` | Aggiungere `_sell_pct_penalty` come attributo. Nel SELL CHECK, usare `sell_pct + _sell_pct_penalty` al posto di `sell_pct` nudo. Al `__init__`/restart, ricalcolare penalty dall'ultimo sell DB. |
| `bot/grid/sell_pipeline.py` | Dopo l'esecuzione del sell (post-fill), calcolare `loss_pct` e aggiornare `bot._sell_pct_penalty`. Se profittevole, azzerare. Loggare l'evento via `log_event`. |

### Log e osservabilità

Ogni variazione della penalty deve essere loggata con `log_event`:
- `event="sell_penalty_increased"` — con dettagli: fill_price, avg_cost,
  loss_pct, new_penalty, effective_sell_pct.
- `event="sell_penalty_reset"` — con dettagli: previous_penalty,
  profitable_sell_price.

Questo permette di ricostruire la storia della penalty nel diary/audit.

---

## Decisioni delegate a CC

- **Posizione esatta del check nel sell pipeline**: dove inserire il calcolo
  post-fill (dopo `log_trade`? dopo il return del fill?) — CC valuta il punto
  più pulito nel flusso esistente.
- **Parsing dell'avg_cost dal campo `reason` vs nuova colonna**: se il parsing
  regex dal reason è robusto (il formato è stabile), va bene. Se CC valuta che
  una colonna `sell_avg_cost` in `trades` è più pulita, può proporla — ma deve
  chiedere prima (è DDL, vedi sotto).
- **Nome variabile e struttura dati**: `_sell_pct_penalty` è indicativo. CC può
  rinominare per coerenza con le convenzioni del codebase.

## Decisioni che CC DEVE chiedere

- **Nuova colonna su `trades`**: se CC decide che serve una colonna
  `sell_avg_cost` (o simile) per il ricalcolo al restart, deve proporre la
  migration a Max PRIMA di eseguirla. È DDL.
- **Qualsiasi modifica al comportamento del TF sell path**: off-limits. Se CC
  identifica un'interazione imprevista tra penalty e TF, escalare.
- **Qualsiasi modifica alla formula di `realized_pnl`**: off-limits totale.

## Output atteso

1. Codice modificato e funzionante (test dove applicabile).
2. Log verificabile: almeno un esempio di penalty increase + reset nei log
   post-restart (testabile con i dati BONK di stamattina che sono già nel DB).
3. Report per CEO con decisioni prese e risultato test.

## Vincoli

- **NON restartare il bot.** Il restart lo fa Max manualmente sul Mac Mini.
- **NON modificare** `sell_pipeline.py` nella sezione che calcola
  `realized_pnl` (formula brief 72a P3, righe cost_basis/revenue/realized_pnl).
- **NON modificare** il TF override path in `sell_pipeline.py` (sezione
  `tf_override`).
- **NON modificare** `bot_config` schema — la penalty è runtime, non config.
- **NON modificare** dashboard, commentary, o qualsiasi file frontend.

## Off-limits (file che CC NON deve toccare)

- `bot/grid/buy_pipeline.py` (nessuna ragione di toccarlo)
- `commentary.py`, `daily_report.py`
- `web_astro/` (tutto il frontend)
- `scripts/` (utility scripts)
- Qualsiasi file in `audits/`

## Roadmap impact

Nessuno. Questa è una guardia di sicurezza interna, non una feature pubblica.
Non richiede aggiornamenti alla roadmap del sito.

---

## Auto-obiezione

La penalty si accumula senza cap. In teoria, dopo 10 sell in perdita da 4%
ciascuno, la soglia diventa 2.5% + 40% = 42.5%. Il bot non venderebbe mai
più (in pratica diventa buy-only). **Contro-argomento**: questo è il
comportamento corretto per Strategy A. Se ogni vendita perde soldi, smettere
di vendere *è* la risposta giusta. E il reset scatta al primo sell
profittevole, che arriverà quando il mercato (o il book) si normalizza.
L'assenza di cap è una feature, non un bug.
