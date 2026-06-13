# Board → CEO — Memo decisionale — "Perché SOL non compra più" — 2026-06-13

**Da:** Board (Max) · **A:** CEO · **Estensore tecnico:** CC (intern), su richiesta del Board
**Stato:** testnet, zero capitale reale a rischio — **ma è un gate pre-mainnet**
**Evidenza:** tutta live, query riproducibili in appendice (DB Supabase + Binance public API, 2026-06-13 ~19:00 UTC)

---

## TL;DR (il punto che fa male)

La griglia SOL è **congelata da ~5 giorni**: ultimo acquisto **2026-06-09**, poi solo vendite fino a svuotarsi. Da allora **non compra e non vende più** e — se nessuno interviene — **non lo farà mai più** da sola.

Causa: **una polvere di 0,000096 SOL (≈ $0,006)** rimasta in pancia dopo l'ultima vendita. Il bot la conta come "posizione aperta", e questo **disinnesca il meccanismo anti-blocco che tu stesso hai progettato** (il re-entry forzato che dovrebbe ricomprare un lotto dopo 4h di griglia vuota).

Il dettaglio che brucia: il fix di questa polvere era **già stato scritto e PARCHEGGIATO** come "dust write-off → pre-mainnet, bassa priorità" (`config/parked/`). Non è teorico: ha appena **ucciso una griglia su 3** per 5 giorni, in silenzio. Senza l'occhio del Board ("perché non compriamo più SOL?") non se ne sarebbe accorto nessuno, perché un bot fermo **non genera né errori né alert**.

---

## 1. Il fatto (evidenza live)

| | SOL/USDT | BTC/USDT | BONK/USDT |
|---|---|---|---|
| `managed_holdings` | **0,000096 SOL ≈ $0,006** | 0,00078 BTC ≈ **$50** | 10,77M BONK ≈ **$49** |
| Posizione reale? | **NO — solo polvere** | sì | sì |
| Ultimo **BUY** | **2026-06-09 00:37** (~4,8 gg fa) | 2026-06-12 11:46 | 2026-06-09 22:32 |
| Ultimo SELL | 2026-06-12 16:55 | 2026-06-12 05:56 | 2026-06-12 15:41 |
| BUY / SELL (5 gg) | **3 / 6** (netto: svuotata) | 4 / 5 | 5 / 4 |
| `stop_buy_active` (freno) | **OFF** | OFF | OFF |
| Stato | **CONGELATA** | operativa | operativa |

Prezzo SOL ora: **$68,10** (Binance public). Il bot è **vivo e gira** (runtime aggiornato 45s fa): semplicemente, su SOL, non fa nulla di utile. **Non è un freno** (`stop_buy` è OFF): è un blocco logico.

## 2. La causa radice (con citazioni di codice)

Il trigger d'acquisto della griglia ([grid_bot.py:951-955](bot/grid/grid_bot.py#L951)):

```python
buy_trigger = self._pct_last_buy_price * (1 - self.buy_pct / 100)
if current_price <= buy_trigger:
    trade = self._execute_percentage_buy(current_price)
```

Con `buy_pct = 3,0%` e riferimento ricalibrato a **68,1**, SOL compra solo sotto **~$66,06** — un calo del 3% che in un mercato laterale 67-68 non arriva.

**Ma il bot ha un'ancora di salvezza apposta**, il re-entry forzato ([grid_bot.py:1024-1039](bot/grid/grid_bot.py#L1024)):

```python
elif self.managed_holdings <= 0:        # nessuna posizione → re-entry
    self._pct_last_buy_price = 0         # "first buy at market"
    trade = self._execute_percentage_buy(current_price)   # COMPRA un lotto, subito
```

Dopo `idle_reentry_hours` (= **4h**) a posizione vuota, il bot **dovrebbe comprare un lotto al mercato**, senza aspettare nessun calo. È esattamente il meccanismo che impedisce lo scenario "non compra mai più". Su SOL **non scatta da 26h** (avrebbe dovuto farlo ~6 volte).

**Perché non scatta?** La condizione è `managed_holdings <= 0`. Ma `managed_holdings = 0,000096` → è **> 0**. La polvere fa credere al bot di avere ancora una posizione, quindi prende l'altra strada (Path B: "ricalibra il riferimento e aspetta"), **non** il re-entry forzato. Non c'è alcuna soglia-polvere (epsilon): il confronto è col letterale `0`.

**Il colpo di grazia** — la guardia "no buy above avg" ([buy_pipeline.py:54-90](bot/grid/buy_pipeline.py#L54)): con `holdings > 0` (la polvere) e prezzo **$68,10 > avg cost $66,33** (l'avg della polvere, dall'ultima vendita), **ogni** acquisto normale è comunque bloccato. Quindi SOL è incastrata su due livelli:

1. **Re-entry forzato** → spento dalla polvere (`0,000096 > 0`).
2. **Acquisto normale** → bloccato dalla guardia (prezzo > avg della polvere).
3. **Vendita** → impossibile: 0,000096 SOL è **sotto il lot size minimo** di Binance → polvere non vendibile, resta lì **per sempre**.

Risultato: né compra né vende. Morta. Esattamente la death-spiral prevista dal Board.

## 3. Perché è grave (non è "solo testnet")

- **Disinnesca una safety di design.** Il re-entry forzato esiste *proprio* per evitare questo. Una posizione da **$0,006** lo neutralizza. Su mainnet significa **capitale parcheggiato a morire** in silenzio.
- **Invisibile.** Un bot fermo non emette ERROR né Telegram. Nessun monitor lo prende. Si scopre solo guardando "perché non si muove" — cioè per fortuna.
- **Contamina l'osservazione in corso.** Siamo nella finestra di verdetto barometro (~23 giu) e di osservazione Sherpa LIVE. Una griglia congelata **falsa il P&L e i dati** su cui baseremo decisioni reali (1 coin su 3 a zero attività).
- **È un gate pre-mainnet esplicito.** Il "no cash morto" è già regola Board (SWEEP/LAST SHOT). Il "no coin morto" (dust) è lo stesso principio, non gestito.

## 4. Il dettaglio che fa il culo al CEO 🙂

Questo non è un imprevisto: il fix era **già pronto e parcheggiato** come **"DUST writeoff → trigger pre-mainnet, bassa priorità"** (`config/parked/README.md`). La classificazione "bassa priorità / aspetta il mainnet" è stata **smentita dai fatti**: la polvere non ha aspettato il mainnet — ha congelato una griglia *adesso*, per 5 giorni, durante una finestra di osservazione che ci serve pulita. **Richiesta del Board: si sposta da "parked/pre-mainnet" a "ora".**

## 5. Opzioni

- **A — Dust epsilon nelle condizioni di posizione (fix minimo, chirurgico).** Trattare `managed_holdings` sotto una soglia-polvere (es. < lot size minimo, o < ~$1 di nozionale) come **zero** nelle tre guardie (`<= 0` del re-entry, `> 0` di no-buy-above-avg e dell'idle-recalibrate). Così la polvere non disinnesca più il re-entry. ~mezza giornata + restart.
- **B — Dust write-off attivo (il brief parcheggiato).** Dopo una vendita che lascia polvere non vendibile, azzerare/scrivere-off il residuo → `managed_holdings` diventa 0 davvero → il re-entry riparte. Risolve anche la contabilità.
- **C — Entrambi (raccomandata).** Write-off come fix di pulizia + epsilon come **difesa in profondità**, così *nessun* residuo potrà mai più spegnere l'anti-blocco. È il combinato che chiude il gate pre-mainnet.
- **D — Non fare nulla.** Accettare che le griglie possano morire su una polvere. Il Board la considera **non accettabile** per il mainnet.

**Raccomandazione CC:** **C**, con priorità sull'epsilon del re-entry (è la riga che riapre il flusso). Reversibile: una soglia in `settings`, niente migration. Da fare un brief tecnico dedicato (è codice bot → off-limits senza brief del CEO).

> Nota onestà tecnica: anche con buy_pct più stretto il problema resterebbe, perché a bloccare *adesso* è la coppia polvere + guardia-avg, non l'ampiezza del buy_pct. Quindi **non** è un problema di tuning Sherpa: è un buco logico nelle condizioni di posizione. Stringere buy_pct sarebbe un cerotto, non la cura.

## 6. Decisione richiesta al CEO

1. **Approvi lo sblocco del brief "dust write-off" da parked a attivo** (opzione C)? Sì/No.
2. **In attesa del fix**, vuoi una **rianimazione manuale di SOL** (write-off una-tantum della polvere così il re-entry riparte al prossimo tick) — oppure la lasciamo ferma per **documentare il fallimento** come dato (coerente con "data-first, anche sbagliando")?
3. Confermi che questo **non** è un task di tuning Sherpa/Board-params, ma un fix di **logica bot** (serve brief tecnico al CC)?

---

## Appendice — evidenza riproducibile

```sql
-- Stato runtime 3 griglie (managed_holdings = posizione economica, esclude phantom)
select symbol, managed_holdings, buy_reference_price, stop_buy_active, updated_at
from bot_runtime_state where symbol in ('BTC/USDT','SOL/USDT','BONK/USDT');
-- SOL: managed_holdings 0.000096, buy_ref 68.1, stop_buy_active false

-- Config SOL
select buy_pct, sell_pct, idle_reentry_hours, dead_zone_hours, stop_buy_drawdown_pct
from bot_config where symbol='SOL/USDT';
-- 3.00 / 1.58 / 4.0 / 2 / 4

-- Ultimo BUY/SELL per griglia
select symbol,
       max(created_at) filter (where side='buy')  as last_buy,
       max(created_at) filter (where side='sell') as last_sell
from trades where managed_by='grid' and cycle='testnet_2' group by symbol;
-- SOL last_buy 2026-06-09 00:37, last_sell 2026-06-12 16:55
```

Prezzo live: `curl "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"` → 68.10.

Codice: trigger [grid_bot.py:951](bot/grid/grid_bot.py#L951); re-entry forzato [grid_bot.py:1024](bot/grid/grid_bot.py#L1024) (gate `managed_holdings <= 0`, niente epsilon); guardia no-buy-above-avg [buy_pipeline.py:54](bot/grid/buy_pipeline.py#L54); `managed_holdings` esclude phantom (S97a).
