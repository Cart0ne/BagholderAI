# Brief S122b — grid-html-fee-inclusive-avg — 2026-07-22

> ## ✅ CHIUSO — 2026-08-07 (S125), commit `7325b39`
>
> **Scelta UX: opzione (A)** — costo medio fee-inclusive ovunque — **con l'etichetta cambiata**.
> La tua obiezione (*"un Avg buy che include la fee non è un prezzo a cui hai comprato"*) era
> fondata, ma il difetto stava nell'etichetta, non nel numero: il riquadro ora dice
> **"Avg cost (incl. fee)"**. Così l'obiezione si dissolve invece di essere scambiata con un
> pannello dove il riquadro mostra una cosa e il calcolo sotto ne usa un'altra (opzione B).
>
> **Fatto:** la fee in valuta quote entra nel costo di carico in **tutte e tre** le
> ricostruzioni JS (`grid.html`, `pnl-canonical.js`, `pnl-canonical.ts`), gated sulla valuta
> della fee per non conteggiarla due volte sul ramo Binance. Verificato contro il motore:
> costo medio $64.231,79 → **$64.745,65**, trigger → **$66.051**, entrambi identici al bot.
>
> **La tua "verifica sibling" era giusta e si è avverata.** Scrivevi: *"se altre ricostruzioni
> JS replicano `cost` senza fee quote hanno lo stesso bug latente; Binance è canonico sul
> pubblico quindi non morde lì oggi, ma annotalo."* Dal 7 agosto il pubblico **è** Kraken:
> mordeva. Corretto anche lì.
>
> ⚠️ **Nota di processo, a mio carico.** Questo brief è rimasto aperto **16 giorni** e la
> mattina del 7-ago l'ho archiviato dichiarandolo chiuso senza che lo fosse: avevo verificato
> la formula fee-buffered del trigger — corretta — e mi ero fermato, senza rileggere che il
> brief chiedeva l'altra metà (il costo medio). L'ha scoperto Max mandando uno screenshot del
> pannello la sera stessa. **Archiviare senza rileggere la richiesta è chiudere un ticket
> guardando solo la parte che ci si ricorda.**

---


**Tipo:** FIX **display-only**. Nessun tocco al motore/bot, nessun DB, **nessun restart**. Solo frontend (`grid.html` + eventuali gemelli JS).
**Da:** CEO · **Per:** CC (Intern) · **Esegue:** CC
**Contesto:** Fase 2b **live** su Kraken (S122). Il fix nodo-5 del **motore** è corretto e verificato dal vivo: `grid_sell_trigger_price()` = `reference × (1+sell_pct/100)/(1−fee)` (niente doppio-conteggio) su avg fee-inclusive → esecuzione reale a **~$67.563** (1,2% netto vero). **Il residuo è SOLO nel cruscotto del collaudo**, che mostra numeri ~0,8% sballati sulla riga Kraken. Trovato leggendo il codice vivo (non copie stantie).

---

## Il difetto (verificato su codice + DB + screenshot)

Il motore costruisce l'avg **fee-inclusive** (`buy_pipeline.py:304` → `cost_for_avg = cost + fee if (synth_fee or quote_fee_live) else cost`). Sul buy 2b reale: cost $33,33153 + fee $0,26665 → **avg motore = $66.225,6**.

`grid.html` ricostruisce l'avg per conto suo nel replay (`grid.html:~679`):
```js
s.avg_buy_price = (s.avg_buy_price * s.holdings + cost) / newHoldings;
```
Usa `cost` (= `t.cost`, fee **esclusa**) e gestisce **solo** la fee in base-coin (Binance: `feeNativeEst` riduce `qtyAcquired`). Sulla riga Kraken la fee è in **USD (quote)** → `feeAsset !== base` → `feeNativeEst = 0` e la fee **non entra né nella qty né nel costo**: sparisce dall'avg. Risultato **avg cruscotto = $65.699,9** (grezzo).

Tutto ciò che deriva dall'avg è quindi ~0,8% off sul collaudo:
- **AVG BUY** tile: $65.699,90 invece di $66.225,6
- **NEXT SELL IF**: `$65.699,9 × 1,012/0,992 = $67.024` invece del reale **$67.563** → il cruscotto dice che vende ~$539 (0,80%) più in basso di dove il bot vende davvero
- **UNREALIZED**: +$0,08 (da avg grezzo) mentre includendo la fee è −$0,19

**Prova visibile sullo screenshot stesso:** `COLLAUDO NET WORTH −$0,19` (fee contata) vs `UNREALIZED +$0,08` (avg grezzo) → differiscono di **$0,27 = la fee di buy**. Stessa causa.

Su Binance il divario è ~0,1% (fee 0,1%, e comunque gestita via base-coin) → invisibile, ecco perché non è mai emerso. Su Kraken 0,8% → materiale.

**Gravità:** sui soldi **zero** (il bot vende più in alto = 1,2% netto corretto, direzione sicura). Ma è il monitor del **denaro reale** su cui Max decide se/quando scalare capitale: mostrare un trigger 0,8% sotto l'esecuzione riproduce il "l'ha sfiorato e non ha venduto". Va sanato prima di fidarsi del cruscotto per il timing.

---

## Il fix

Rispecchiare in `grid.html` (replay avg, ~riga 679) il ramo **quote-fee** di `buy_pipeline.py:304`: quando la fee è in valuta quote (`feeAsset !== base`, es. USD su Kraken), **foldare `feeUsdt` nel numeratore dell'avg** (come fa il motore con `cost + fee`). Il ramo base-coin (Binance) resta invariato. Un solo punto (il replay condiviso) sana insieme AVG BUY, cost basis, unrealized% e il trigger, sia nel widget collaudo Kraken (~849-901) sia in quello generale (~1216-1255), perché entrambi pescano `avgBuyPrice` dallo stesso replay.

**Verifica sibling:** `grep` per altre ricostruzioni JS dell'avg (es. `dashboard-live.ts`, `live-stats.ts` dal ciclo S119) — se replicano `cost` senza fee quote, hanno lo stesso bug latente. Binance è canonico sul pubblico, quindi non morde lì oggi, ma annotalo.

---

## Auto-obiezione del CEO (dovuta)
**Obiezione reale:** "foldare la fee nell'avg" rende il tile **AVG BUY** = $66.225,6, cioè un numero **più alto del prezzo a cui hai comprato** ($65.699,9). Per un umano che legge "Avg buy" è potenzialmente fuorviante (ho comprato a 65.699, non a 66.225). Quindi il fix non è puramente meccanico: c'è una scelta UX. Due strade, **decidi tu e argomenta**:
- **(A)** avg fee-inclusive ovunque (matcha il motore = obiettivo "display==esecuzione" S121; il tile mostra 66.225 con sublabel "incl. buy fee"). Coerenza piena.
- **(B)** tile "AVG BUY" resta il **prezzo grezzo del fill** (leggibile) MA il **reference del trigger** (e unrealized-vs-avg, cost basis) usa l'avg fee-inclusive → il numero che conta (NEXT SELL) matcha l'esecuzione, il tile resta il prezzo reale pagato.
Io propendo per **(A)** (una sola verità = quella del motore), ma se scegli (B) motiva perché il disaccoppiamento è più chiaro per chi guarda.
**Seconda, minore:** assicurati che il fix sia **gated sul quote-fee** e NON tocchi il ramo Binance base-coin (già corretto via `feeNativeEst`) — niente doppia applicazione.

## Cosa NON fare
- ❌ Non toccare il motore/`buy_pipeline`/`grid_sell_trigger_price` — sono **corretti**. Il difetto è solo la reimplementazione JS dell'avg.
- ❌ Niente DB, niente bot, niente restart. È display.

## Consegna
Report `report_for_CEO/2026-07-22_S122b_RforCEO_grid-html-fee-inclusive-avg.md` con: file:riga cambiati + commit, strada A/B scelta e perché, screenshot/numeri prima-dopo sulla riga Kraken (avg + NEXT SELL devono combaciare con `current_sell_trigger()` del motore = $67.563), esito verifica sibling, e la tua obiezione tecnica. SCOPE ereditato identico: `grid-html-fee-inclusive-avg`.
