# Report per CEO — S119b indagine kraken-replay-avg-reconcile

**Data:** 2026-07-17 · **Brief sorgente:** `config/2026-07-17_S119b_brief_kraken-replay-avg-reconcile.md`
**Tipo:** read-only. **Nessun** codice toccato, **nessun** restart, **nessun** ordine.
**Commit codice esaminato:** `ad39afd` (HEAD) — nulla è stato modificato.

> **TL;DR** — Q1: replay OK (safety confermata). Q2: **il codice include la fee nell'avg → il mio report S119 era sbagliato**, il runbook è giusto. Q3: cosmetico confermato (interroga Kraken, non Binance). **Quarto finding (conta per il nodo 5):** il floor conta la fee di buy 2 volte → ~0,8% troppo protettivo. **Riavvio sicuro: SÌ al prezzo attuale**, con un caveat sul buy-trigger.

> ### ⚠️ CORREZIONE 2026-07-20 — QUESTO REPORT HA SBAGLIATO IL TRIGGER (traccia dell'errore)
> La Q2 qui sotto conclude "trigger ≈ $65.271" citando **`sell_pipeline.py:316`** — ma quella
> riga è un **commento** che semplifica la formula (`price >= avg×(1+sell_pct/100)`). La formula
> **eseguibile** del grid manuale è **`grid_bot.py:876`**:
> `sell_trigger = avg × (1 + sell_pct/100 + fee) / (1 − fee)` → **fee-buffered**. Con avg
> $63.991 e fee Kraken **0,8%** → **trigger reale ≈ $66.314**, non $65.271. Il lotto da $25
> (0,00039379 BTC) alla vendita vale **~$26,11 lordi** (netto ~$25,90, profitto **~+$0,71 /
> +2,8%**, non +1,19%).
> **Errore di metodo da non ripetere:** ho letto un **commento** invece della **riga eseguibile**.
> Su Binance (fee 0,1%) il cuscino è ~0,2% e il numero semplificato coincideva quasi; su Kraken
> (0,8%) diverge di ~1,6 punti. **Regola:** per un trigger, verificare sempre la formula che
> *esegue* (`grid_bot.py` `check_price_and_execute`), non il commento che la descrive.
> Verificato dal vivo 2026-07-20: BTC max $65.600, nessuna vendita → il bot è corretto. Le righe
> Q2 sotto restano **come record dell'errore**.

---

## §8 (dovuto per primo) — Obiezione al brief

Il brief inquadra la Q1 come la domanda di sicurezza ("replay rotto → BUY fantasma da first-entry"). **Ma il replay funzionante NON rende il riavvio sicuro di per sé.** Il vero rischio di un restart non è il first-entry fantasma — è il **buy-trigger ordinario** (DCA): se al momento del restart il prezzo è sotto `last_buy × (1 − buy_pct)`, il bot compra un secondo lotto da $25 *legittimamente, by design*. Il brief non lo nomina. Quindi la risposta a "restart sicuro?" non dipende solo dal replay (D1), ma dal prezzo vs il buy-trigger — e questo l'ho verificato a parte (sotto). È la mia obiezione: la cornice di sicurezza del brief è incompleta.

Seconda: la Q2, una volta risolta, **espone un problema che il brief non chiede** — il floor doppia-conta la fee di buy. È il "quarto punto" invitato dal §8, e per il nodo 5 conta più della Q1.

---

## Q1 — Il replay ritrova il trade Kraken? ✅ **SÌ**

**Verdetto:** il replay trova il trade e ricostruisce lo stato. Nessuno scenario "first entry".

**Codice:** `bot/grid/state_manager.py:64-71` — il replay avg-cost filtra su:
```python
_cycle = get_current_cycle(bot.trade_logger.client, bot.symbol)   # path per-simbolo
client.table("trades").select(...)
  .eq("symbol", bot.symbol)          # 'BTC/USD'
  .eq("config_version", "v3")
  .eq("cycle", _cycle)               # 'kraken_test'
```

**Match verificato a DB (17/07):** il trade `07519506-…` ha `symbol='BTC/USD'`, `config_version='v3'`, `cycle='kraken_test'`, e `get_current_cycle(client,'BTC/USD')` restituisce **`kraken_test`** (path per-simbolo, senza cache → sempre fresco). I tre filtri combaciano tutti.

- **a)** Colonne del filtro: `symbol` + `config_version='v3'` + `cycle` (per-simbolo).
- **b)** Sì: ricostruisce `holdings=0.00039379` + `avg_buy` coerente (+ `_pct_last_buy_price=63483.50`, `state_manager.py:202`). Nessuna condizione mancante.
- **c)** N/A — lo trova. Lo scenario "first entry → buy immediato" del 17/07 valeva **solo** perché a quel boot il trade non esisteva ancora (`No v3 trades found`). Ora esiste.

---

## Q2 — `avg_buy` include la fee di acquisto? 🟠 **SÌ — il report è sbagliato, il runbook è giusto**

**Verdetto:** l'avg **include** la fee di buy. Il trigger SELL reale è **~$66.314** *(corretto 2026-07-20 — questo report scriveva $65.271; vedi box in alto)*, non $64.753.

**Codice:** `bot/grid/buy_pipeline.py:304`
```python
cost_for_avg = cost + fee if (synth_fee or quote_fee_live) else cost
```
Per il buy Kraken `quote_fee_live=True` (`buy_pipeline.py:227-232`: venue=kraken, non-synth, fee>0, fee_base=0). Quindi `cost_for_avg = cost + fee`. Poi `buy_pipeline.py:306-308`:
```python
avg_buy_price = (old_avg*old_managed + cost_for_avg) / managed_after
```
Primo buy: `= (0 + 25.19916) / 0.00039379 ≈ **$63.991**` (non $63.483,50).

**Dove si applica `sell_pct`:** ⚠️ *qui l'errore* — citavo `sell_pipeline.py:316`, che è un **commento** semplificato. La formula **eseguibile** è `grid_bot.py:876` = `avg×(1+sell_pct/100+fee)/(1−fee)`. Con avg=$63.991, sell_pct=2%, fee Kraken 0,8% → **trigger ≈ $66.314** *(non $65.271; corretto 2026-07-20)*.

**Quale documento è sbagliato:** il **report S119** (`…_S119_RforCEO_kraken-fase2a.md`) che citava ~$64.753 (= 63.483,50 × 1,02, prezzo puro). È l'errore. Il **runbook §4** ("avg riflette prezzo + fee reale") è corretto. → il report va corretto (segnalato, non fixo qui).

**Margine netto reale** (con avg fee-inclusive): revenue lordo − cost_basis − sell_fee. *(Corretto 2026-07-20: col trigger reale fee-buffered $66.314 il netto è **~+$0,71 / +2,8%** su $25, non +1,19%; questo report calcolava +1,19% sul trigger sbagliato $65.271. In ogni caso: **la situazione reale è migliore** del numero originale.)*

### Quarto finding (input diretto nodo 5) 🟠 — il floor doppia-conta la fee di buy
`sell_pipeline.py:298-305`: `fee_floor = 2×fee_rate` e `min_price = avg × (1 + min_profit_pct/100 + fee_floor)`. Ma **avg include già 1× fee** (Q2). Il break-even netto vero è `avg × (1+fee) ≈ avg×1,008`; il floor sta a `avg×1,016`. → **il floor è ~0,8% (1× fee) più alto del break-even reale**: sovra-protettivo, non rischioso, ma blocca vendite nella banda [avg×1,008, avg×1,016) che sarebbero già in utile netto. **Per il nodo 5:** un margine netto di 0,4% andrebbe sopra il break-even vero `avg×(1+fee)`, non sopra `avg×(1+2×fee)`. La formula del floor S118 va rivista quando si chiude il nodo 5 (o il margine scelto tenendo conto del +0,8% latente). Verdetto: **finding reale, va in PROJECT_STATE §5.**

---

## Q3 — Il boot reconcile su venue Kraken interroga chi? ✅ **Kraken (etichetta cosmetica)**

**Verdetto:** interroga **Kraken**, non Binance. Le stringhe "Binance" nei log sono etichette hardcoded. **Non è cieco.**

**Codice — dimostrazione (non "0=0"):**
- `bot/grid/state_manager.py:318-319`:
  ```python
  _client = getattr(bot, "exchange_client", None)
  balance = _client.fetch_balance() if _client is not None else bot.exchange.fetch_balance()
  ```
- `bot/grid_runner/__init__.py:328-330`: il GridBot è costruito con `exchange_client=client`, dove `client = create_client(venue)` e per `venue='kraken'` è **KrakenClient** (`bot/exchanges/__init__.py:29-32`). Inoltre `bot.exchange = client.raw` = l'istanza ccxt **kraken**. → in **entrambi** i rami di `state_manager.py:319` la `fetch_balance()` colpisce Kraken.
- Le stringhe fuorvianti: `state_manager.py:339` (`"vs Binance="`) e `:417` (`"Holdings synced from Binance"`) — **letterali hardcoded**, non toccano la fonte dati.

**Non è un finding di correttezza** (fonte dati giusta), **ma l'etichetta va corretta**: è esattamente il pattern "codice che dice Binance implicito" che ci ha morso su cycle-fetch (S118) e superfici sito (S119). Micro-fix cosmetico → lo segnalo, PROJECT_STATE §5 come LOW cosmetico.

---

## Riavvio del processo di test: **SICURO SÌ — al prezzo attuale**

Catena verificata:
1. **Replay** (Q1): ricostruisce holdings + avg + `last_buy=63483.50` → niente first-entry.
2. **Reconcile** (Q3): interroga Kraken, wallet=0.00039379=replayed → gap 0 → OK (nessun FAIL/WARN).
3. **Buy-trigger al restart** = `last_buy × (1 − buy_pct)` = `63483.50 × 0.997 ≈ **$63.293**`. BTC ora ~$63.470 **> trigger** → **nessun buy** al primo tick. La guardia Strategy A (no-buy-above-avg) non entra in gioco (prezzo < avg).

**⚠️ Condizione (l'obiezione §8 resa concreta):** la sicurezza è **prezzo-dipendente**. Se al momento del restart BTC fosse **sotto ~$63.293** (last_buy −0,3%), partirebbe un **secondo BUY reale da $25** (DCA legittimo). Quindi:
> **Restart sicuro finché BTC > ~$63.293.** Non è incondizionatamente neutro. Prima di autorizzare un riavvio, controllare il prezzo vs $63.293 (o accettare/pianificare il DCA).

---

## Cosa NON ho fatto (rispetto del brief §4)
Nessuna modifica a codice / `bot_config` / `trades`; nessun restart; nessun ordine; riga `BTC/USD/kraken` non cancellata (ciclo aperto). Il processo di test acceso (pid 46585) non toccato.

## Escalation (§5)
- **A Max/Board:** la correzione del **report S119** (numero trigger), la revisione **floor** (nodo 5), l'eventuale micro-fix etichetta reconcile → sono **brief separati**, non li eseguo qui.
- **Nessun blocker** che impedisca la Fase 2b: il replay è sano, il reconcile è corretto. Il floor-double-count è una taratura del nodo 5, non un bug bloccante.

---

## Addendum — capitale e DCA (risposta all'obiezione CEO, 2026-07-17)

**Il CEO ha ragione. Il mio caveat prezzo-dipendente era sbagliato. Concedo.**

Avevo verificato che il **buy-trigger di prezzo** sarebbe stato soddisfatto sotto ~$63.293, ma **non ho seguito la catena fino al gate del cash** che gira *dopo* il trigger. Con capitale esaurito, quel gate salta l'ordine a qualsiasi prezzo.

**Q1 — quanto vale `_available_cash` dopo il buy, e la fee entra nell'invested?**
Sì, la fee entra nell'invested — **come credevi**:
- Runtime: `buy_pipeline.py:268` `total_invested += (cost + fee) if quote_fee_live` → 24,99917 + 0,19999 = **$25,19916**.
- Replay al boot: `state_manager.py:129-131` lo rispecchia (`is_kraken and fee_asset==quote → cost_eff = cost + fee_usdt`) → invested identico dopo un restart.
- `_available_cash()` (`grid_bot.py:271`): `base = max(0.0, capital − total_invested + total_received) = max(0.0, 25 − 25,19916 + 0) = max(0.0, −0,19916)` = **$0,00** (clampato a zero; il −$0,199 non diventa mai negativo). Reserve = 0 (skim_pct=0).

**Q2 — al buy-trigger $63.293 può partire un ordine? Quale gate lo ferma?**
**No.** `buy_pipeline.py:99-133`:
- `cash_before = _available_cash() = 0.0`
- `0.0 >= standard_cost (25)` → no
- `0.0 >= MIN_LAST_SHOT_USD (5.0, config/settings.py:198)` → no
- → ramo `else` (`buy_pipeline.py:129-133`): *"Insufficient cash for BUY … Skipping pct buy."* → `return None`, **nessun ordine inviato**.

Il buy-trigger di prezzo può anche scattare: l'ordine viene comunque **skippato** dal gate del cash, che sta *a valle* del trigger. Le munizioni sono zero.

**È un bug del gate?** No — **l'opposto**. Il gate fa esattamente il suo lavoro: a capitale esaurito **non compra**. Non è un buco, non va in §5 come finding. (Sarebbe stato un bug se avesse comprato a `cash=0`; non lo fa.)

### Verdetto finale riformulato
> **Il riavvio del processo di test è sicuro INCONDIZIONATAMENTE** (non prezzo-dipendente).
> Tre gate indipendenti lo garantiscono: (1) il replay ricostruisce lo stato → niente first-entry (Q1); (2) il reconcile Kraken conferma holdings → nessun FAIL (Q3); (3) **capitale esaurito (`_available_cash=0 < $5`) → nessun DCA a nessun prezzo** (questo addendum). Il caveat "$63.293" del corpo del report è **superato**: valeva solo se il capitale fosse stato disponibile, e non lo è.
