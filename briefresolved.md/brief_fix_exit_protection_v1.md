# BRIEF — Fix exit protection holes (trailing peak reset + stop loss %)

**Date:** 2026-05-04
**Priority:** MEDIA — exit logic fix, paper capital ma critico pre go-live
**Richiede restart orchestrator:** SÌ (dopo deploy)

---

## TL;DR

Tre fix chirurgici in `bot/strategies/grid_bot.py`:

1. **Trailing stop:** resettare `_trailing_peak_price` ad ogni nuovo buy, così il trailing riparte da zero per ogni ciclo di acquisto anziché usare un peak storico che non appartiene ai lotti appena comprati.
2. **Stop loss:** calcolare la soglia in % sul **valore aperto corrente** (`avg_buy_price × holdings`) anziché sull'`allocation` iniziale. Così il 2.5% è sempre il 2.5% reale, anche su lotti parziali post-sell/post-skim.
3. **Take profit:** stessa correzione del punto 2, applicata al TP (blocco 39c). Il design originale ha SL e TP simmetrici sulla stessa base — il fix deve preservare la simmetria.

---

## Contesto

### Bug 1 — Trailing stop peak globale (caso DOGE 2026-05-04)

`_trailing_peak_price` è in-memory, inizializzato a 0, aggiornato ogni tick se `price > peak`, ma **mai resettato** quando il bot compra nuovi lotti.

Conseguenza: se il prezzo sale, poi scende, il bot compra un last-shot a prezzo basso → `avg_buy_price` cala → soglia di attivazione cala → il vecchio peak supera la nuova soglia → trailing si arma **istantaneamente** sul lotto appena comprato, che non ha mai visto un guadagno.

Caso reale: DOGE lotto A a $0.1124, peak $0.1136, last-shot lotto B a $0.1095, 1 minuto dopo trailing vende tutto a $0.1093. P&L: −$0.19.

### Bug 2 — Stop loss in $ assoluti sull'allocation (caso INJ 2026-05-04)

La soglia SL è `-(self.capital × tf_stop_loss_pct / 100)` dove `self.capital` = allocation iniziale (fisso).

Se il bot ha venduto metà dei lotti (greed decay, skim), il residuo open è molto più piccolo dell'allocation → serve un drawdown molto maggiore del 2.5% nominale per triggerare lo SL.

Caso reale: INJ allocation $15.44, lotto open $7.71 (metà). SL threshold = −$0.386, ma per raggiungerla serve un drop del **5%** sul lotto, non del 2.5%.

---

## Fix 1 — Peak reset on buy

### Dove intervenire

File: `bot/strategies/grid_bot.py`

Cercare il punto dove il bot **esegue un buy** per il Trend Follower e l'ordine viene confermato. Dopo che il buy è stato processato con successo (ordine eseguito, state aggiornato), aggiungere:

```python
self._trailing_peak_price = current_price
```

**Attenzione:** il reset deve avvenire DOPO che il buy è andato a buon fine (ordine confermato), non prima. Se il buy fallisce, il peak non deve essere toccato.

### Logica

- Ogni nuovo buy resetta il peak al prezzo corrente
- Da quel momento il trailing tracker riparte da zero per quel nuovo ciclo
- Il peak viene comunque aggiornato ogni tick (linee ~938-942) se `price > peak`, quindi dopo il reset ricomincia a salire naturalmente

### Riferimenti nel codice attuale

- Linea ~144: `self._trailing_peak_price = 0` (init)
- Linee ~938-942: peak update ogni tick (`if price > self._trailing_peak_price: ...`)
- Linee ~995-1019: trailing trigger check

---

## Fix 2 — Stop loss in % sul valore aperto

### Dove intervenire

File: `bot/strategies/grid_bot.py`, linee ~948-962 (blocco stop loss check)

Codice attuale (circa):
```python
unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
loss_threshold = -(self.capital * self.tf_stop_loss_pct / 100)
if unrealized <= loss_threshold: ...
```

Sostituire la riga `loss_threshold` con:
```python
open_value = self.state.avg_buy_price * self.state.holdings
loss_threshold = -(open_value * self.tf_stop_loss_pct / 100)
```

### Logica

- `open_value` = quanto vale la posizione aperta al prezzo di acquisto medio
- La soglia diventa: "se perdo il 2.5% del valore che ho in mano ORA, esci"
- Con INJ: open_value = $3.796 × 2.03 = $7.71 → threshold = −$0.193 → SL scatta al −2.5% reale
- Con allocation piena: il comportamento è identico a prima (open_value ≈ capital)

### Aggiornare anche il log message

Nel log/reason della vendita SL, se presente un riferimento a "threshold X% of alloc", aggiornarlo per riflettere che ora è "X% of open value". Cercare la stringa di reason nel codice e adattarla.

---

## Fix 3 — Take profit in % sul valore aperto (simmetrico al Fix 2)

### Dove intervenire

File: `bot/strategies/grid_bot.py`, linee ~1053-1066 (blocco 39c, take profit TF)

Codice attuale (circa):
```python
profit_threshold = self.capital * self.tf_take_profit_pct / 100
```

Sostituire con:
```python
open_value = self.state.avg_buy_price * self.state.holdings
profit_threshold = open_value * self.tf_take_profit_pct / 100
```

**Nota:** la variabile `open_value` potrebbe già esistere nello scope se il blocco SL (Fix 2) la calcola prima. Se SL e TP sono in metodi/blocchi separati, calcolarla di nuovo. Non condividere variabili tra blocchi a rischio di ordine di esecuzione diverso.

### Logica

- Il TP diventa: "se il guadagno unrealized supera il 6% del valore che ho in mano, vendi"
- Su lotto parziale (es. $7.71 di $15.44): TP scatta a +$0.46 di unrealized (+6% reale), non +$0.93 (+12% reale come oggi)
- Su allocation piena: comportamento identico a prima
- Preserva la simmetria SL/TP del design originale (commento 39c nel codice)

### Aggiornare anche il log message

Stessa logica del Fix 2: se il reason string del TP menziona "alloc" o "capital", aggiornare a "open value".

---

## Ordine di esecuzione

1. Leggere `bot/strategies/grid_bot.py` — identificare le posizioni esatte dei tre fix
2. Applicare Fix 1 (peak reset on buy)
3. Applicare Fix 2 (stop loss threshold)
4. Applicare Fix 3 (take profit threshold — stessa formula del Fix 2)
5. Aggiornare i reason string di SL e TP se necessario
6. Test (vedi checklist sotto)
7. `git add -A && git commit -m "fix: reset trailing peak on buy + SL/TP threshold on open value" && git push origin main`
8. Comunicare a Max: "deploy pronto, fare git pull + restart orchestrator sul Mac Mini"

---

## Checklist test

Prima del push, verificare mentalmente:

- [ ] **Fix 1:** Dopo un buy, `_trailing_peak_price` è uguale a `current_price` (non al vecchio peak)
- [ ] **Fix 1:** Il peak continua ad aggiornarsi ogni tick dopo il reset (le linee ~938-942 non sono state toccate)
- [ ] **Fix 1:** Se un buy fallisce, il peak NON viene resettato
- [ ] **Fix 2:** Con allocation piena (2 lotti, nessuna vendita precedente), il threshold SL è praticamente uguale a prima
- [ ] **Fix 2:** Con lotto parziale (es. metà allocation venduta), il threshold SL è proporzionalmente più piccolo → SL scatta prima
- [ ] **Fix 2:** `open_value` non può essere 0 o negativo in condizioni normali (se holdings > 0 e avg_buy > 0, ok)
- [ ] **Fix 2:** Il reason string della vendita SL è aggiornato e coerente
- [ ] **Fix 3:** La formula TP usa `open_value × pct` (stessa base del Fix 2)
- [ ] **Fix 3:** Con allocation piena, il threshold TP è praticamente uguale a prima
- [ ] **Fix 3:** Con lotto parziale, il threshold TP è proporzionalmente più piccolo → TP scatta prima (coerente col Fix 2)
- [ ] **Fix 3:** Il reason string della vendita TP è aggiornato e coerente
- [ ] **Simmetria:** SL e TP usano entrambi `open_value × pct` come base — nessuna asimmetria accidentale
- [ ] Nessun import aggiuntivo necessario
- [ ] Nessun altro file toccato

---

## File toccati

- `bot/strategies/grid_bot.py` — unico file modificato

## NON toccare

- `trend_config` su Supabase (parametri invariati: `tf_stop_loss_pct=2.5`, `tf_trailing_stop_activation_pct=1.5`, `tf_trailing_stop_pct=2`)
- Dashboard (`grid.html`) — i tooltip sono già corretti concettualmente ("dropped X% from peak", "stop loss X%"), il fix allinea il codice a ciò che la dashboard promette
- Nessun altro file del bot
