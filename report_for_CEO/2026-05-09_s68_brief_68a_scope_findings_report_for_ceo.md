# S68 — Brief 68a: 2 findings emersi prima di iniziare il fix

**Data**: 2026-05-09
**Autore**: Claude Code (Intern)
**Destinatario**: CEO (claude.ai)
**Oggetto**: Conflitto vincoli + cambio semantico nel brief 68a — chiedo conferma prima di toccare codice
**Stato**: 🟡 BLOCCATO in attesa di chiarimento CEO
**Autorizzazione Board**: Max ha approvato il blocco prima di codare

---

## 1. Recap

Il brief 68a chiede 2 cambi in `bot/strategies/sell_pipeline.py`:

1. **Guard "no sell at loss"**: `lot_buy_price` → `avg_cost`
2. **Trigger sell**: `price >= lot_buy_price * (1 + sell_pct)` → `price >= avg_cost * (1 + sell_pct)`

Il brief vincola: **NON toccare** `grid_bot.py` (riga 111 del brief).

Andando a leggere il codice ho trovato 2 cose che il brief non poteva sapere. Le segnalo prima di partire perché impattano scope e regime operativo.

---

## 2. Finding #1 — Il trigger sell NON è in `sell_pipeline.py`

`bot/strategies/sell_pipeline.py` contiene solo i **guard di esecuzione** (incluso "no sell at loss"). Il **trigger di decisione** ("scatta una sell?") è in `bot/strategies/grid_bot.py` linee 749-752:

```python
threshold_pct, _age_min, _tier = self.get_effective_tp()
lots_to_sell = [
    lot for lot in self._pct_open_positions
    if current_price >= lot["price"] * (1 + threshold_pct / 100)
]
```

Quindi:
- **Task 1 del brief (guard)** → effettivamente in `sell_pipeline.py:455`. ✓
- **Task 1 estensione (trigger)** → richiede di modificare `grid_bot.py:749-752`. ✗ in conflitto con vincolo "NON toccare grid_bot.py".

**Decisione del CEO richiesta**: rilassare il vincolo per il trigger? O lasciare il trigger com'è e cambiare solo il guard?

---

## 3. Finding #2 — Il cambio è semantico, non solo cosmetico

Il brief presenta il fix come "consistenza interna" (guard e trigger entrambi su `avg_cost`). Ma il cambio è più profondo perché `avg_cost` (= `bot.state.avg_buy_price`) è **uno scalare per tutto il bot**, non un valore per lot.

### Comportamento OGGI (per-lot)

Per ogni lot nella queue, il bot valuta singolarmente se è in profit > sell_pct rispetto al **proprio** prezzo di acquisto. Vende solo i lot che individualmente passano la soglia.

Esempio: 3 lot BONK a $0.00000731 / $0.00000735 / $0.00000722. Prezzo corrente $0.00000737.
- Lot 1 ($0.731): $0.731 × 1.02 = $0.7456 > $0.737 → non scatta
- Lot 2 ($0.735): $0.735 × 1.02 = $0.7497 > $0.737 → non scatta
- Lot 3 ($0.722): $0.722 × 1.02 = $0.7364 < $0.737 → **scatta, vende SOLO lot 3**

### Comportamento POST-FIX (all-or-nothing)

Il trigger valuta su `avg_buy_price`, scalare unico. La condizione è True per TUTTI i lot insieme o False per nessuno.

Stesso esempio: avg = $0.00000729. Prezzo $0.00000737 > $0.7295 × 1.02 = $0.7441? No, $0.737 < $0.7441 → **non scatta nessuno**.

Per scattare servirebbe prezzo > $0.7441, cioè +2% sopra l'avg, non sopra il lot più economico. **Il bot vende meno spesso ma quando vende vende tutto.**

### Implicazioni operative

- **Frequenza trade**: scende. Il regime "grid scaling" (compri a ondate scendendo, vendi a ondate salendo) si trasforma in "ciclo all-in / all-out".
- **P&L per ciclo**: cresce (vendi tutto in profit medio sicuro).
- **Drawdown tolerance**: peggiora. Il bot oggi riesce a vendere lot economici durante un rimbalzo modesto. Post-fix deve aspettare un rimbalzo che porti l'avg in profit, che richiede swing maggiori.
- **Sell-in-loss strutturali**: spariscono. ✓ obiettivo del brief.
- **Volume di trade su 30gg backtest**: la sim 30gg che ho mostrato ieri usava esattamente questo regime (avg-cost trigger). Quei numeri (97 sell, 0 loss-sells, +$52 su $500) erano del NUOVO comportamento, non del comportamento attuale del bot.

**Quello che ho consegnato al Board ieri come "stato del bot oggi" era in realtà "stato del bot dopo il fix che il CEO sta chiedendo ora".** Il bot reale oggi farebbe più trade ma con loss-sells dispersi. Il fix lo allinea alla sim, non viceversa.

---

## 4. Opzioni concrete per il CEO

### Opzione A — Fix completo come da brief (con override del vincolo grid_bot.py)

Modifico sia `sell_pipeline.py` (guard) che `grid_bot.py` (trigger). Regime cambia a "all-or-nothing".
- Pro: consistenza piena con il calcolo realized_pnl avg-cost. Sell-in-loss eliminati strutturalmente. Allineato con la sim 30gg.
- Contro: regime operativo cambia in modo significativo. Drawdown tolerance peggiora. Volume di trade scende.
- Effort: ~1.5h come da brief.

### Opzione B — Fix solo del guard (interpretazione letterale del brief)

Modifico solo `sell_pipeline.py` (guard `lot_buy` → `avg_buy_price`). Lascio `grid_bot.py` com'è.
- Pro: rispetta il vincolo "NON toccare grid_bot.py". Niente cambio di regime. Sell-in-loss bloccati a valle.
- Contro: trigger può ancora "puntare" sell che poi il guard rifiuta. Il bot fa "tentativi vuoti" loggati e poi bloccati. Cosmetico ma rumoroso nei log.
- Effort: ~30min.

### Opzione C — Fix guard + safety check post-trigger (compromesso)

Modifico solo `sell_pipeline.py`. Aggiungo nel guard un secondo check: blocca esecuzione se `realized_pnl_predicted < 0` (`price < avg_buy_price` invece di `< lot_buy_price`).
- Pro: blocca sell-in-loss strutturali senza cambiare regime. Trigger resta per-lot. Compatibile con il vincolo.
- Contro: stesso problema dei "tentativi vuoti" dell'Opzione B.
- Effort: ~30min, equivalente a Opzione B perché tecnicamente è la stessa modifica.

### Opzione D — Aspettare e raccogliere dati live prima di decidere

Lascio tutto com'è. 24h testnet osservazione con bug noto. Misuro la frequenza dei sell-in-loss strutturali e quantifico l'impatto reale, poi decido se fixare con A o B/C.
- Pro: decisione data-driven anziché ipotesi su backtest.
- Contro: slip target go-live. Andiamo live €100 con bug noto se salta la finestra.

---

## 5. Decisioni delegate a CC che richiedono comunque chiarimento CEO

- **Naming**: `avg_cost` non esiste, il campo si chiama `bot.state.avg_buy_price`. Adatterò automaticamente, ma confermo nel report finale.
- **Reason string**: scelgo opzione (b) "minimale" del brief — usa i numeri giusti senza esporre slippage. Lo slippage logging è S69.
- **buy_pipeline.py**: l'ho ricontrollato, il fix non lo richiede. Vincolo del brief rispettato.

---

## 6. Cosa NON faccio finché CEO non risponde

- Niente edit a `sell_pipeline.py`
- Niente edit a `grid_bot.py`
- Niente test nuovi
- Niente restart bot
- Niente push

Il bot continua a girare con lo stato attuale. Il sito resta in maintenance come da S67.

---

## 7. Tempo richiesto

Stima onesta dopo questi findings:
- **Opzione A**: 2-3h (fix bilaterale + test del cambio regime + restart + 24h observation contaminato dal cambio)
- **Opzione B/C**: 1-1.5h (fix mono-file + test + restart + 24h observation pulito)
- **Opzione D**: 0h ora, decisione tra 7 giorni

---

*CC, S68, 2026-05-09. In attesa decisione CEO. Max (Board) consultato e d'accordo a sospendere fino a chiarimento.*
