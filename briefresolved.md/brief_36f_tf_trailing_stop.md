# BRIEF — Session 36f: Trailing stop per pump >X%

**Date:** 2026-04-16 (da raffinare con CEO)
**Priority:** LOW — opzionale, opt-in. Da valutare dopo 1-2 settimane di TF stabilizzato con 36c/36e/36g per capire se i "pump persi" giustificano la complessità.
**Prerequisito:** 36c deployato ✅, 36e deployato (rotation + ATR), 36g deployato (compounding)
**Scope rule:** SOLO grid_bot state machine + bot_config schema. NON toccare logica allocator TF, skim, rotation.

---

## Problema

Oggi `_execute_percentage_sell` vende al primo tick che tocca `avg_buy * (1 + sell_pct/100)`. Se il prezzo poi pumpa al +20% o +50%, il bot ha già venduto al +1.2% e ha perso il resto del movimento.

Esempio storico (BIO, pre-sessione 36):
```
Buy @ $0.10
Price +1.2% → sell $0.1012 (lot chiuso)
Price +55%  → mai più entrato (out of grid)
```

Con trailing stop il bot avrebbe potuto:
```
Buy @ $0.10
Price +5% (activation) → enter trailing mode, local_high = $0.105
Price +55% → local_high = $0.155
Price retrace a $0.150 (-3.2% dal max) → sell $0.150
Profit: +50% invece di +1.2%
```

## Obiettivo

Meccanismo **opt-in** che permette al grid_bot di "cavalcare" un pump invece di venderselo al primo tick di profit. Default disabled per tutti i bot esistenti — abilitabile per-bot via config.

## Design

### Parametri nuovi in `bot_config`

| Colonna | Tipo | Default | Significato |
|---|---|---|---|
| `trailing_activation_pct` | numeric | 0 | % sopra `avg_buy_price` oltre il quale entra in trailing mode. `0` = disabilitato |
| `trailing_stop_pct` | numeric | 1.0 | % di ritracciamento dal massimo locale che triggera la sell |

Se `trailing_activation_pct = 0`, il bot si comporta come oggi (sell_pct puro).

### State machine grid_bot

Aggiungere al `state` (per lot aperto, non globale):

```python
{
    "amount": ..., "price": ...,     # come oggi
    "trailing_active": False,        # False finché il prezzo non supera l'activation
    "trailing_high": 0.0,            # max prezzo raggiunto da quando trailing_active=True
}
```

### Logica in `_execute_percentage_sell`

Per ogni lot aperto, prima della logica esistente:

```python
def _should_sell_lot(self, lot: dict, current_price: float) -> tuple[bool, str]:
    buy_price = lot["price"]

    # If trailing is disabled for this bot, fall back to the legacy path
    if self.trailing_activation_pct <= 0:
        return self._legacy_sell_check(lot, current_price)

    pnl_pct_from_buy = (current_price / buy_price - 1) * 100

    if not lot.get("trailing_active"):
        # Not yet in trailing mode
        if pnl_pct_from_buy >= self.trailing_activation_pct:
            # Activate trailing
            lot["trailing_active"] = True
            lot["trailing_high"] = current_price
            return False, f"trailing activated at {current_price} (+{pnl_pct_from_buy:.2f}%)"
        else:
            # Below activation — use legacy sell_pct gate
            return self._legacy_sell_check(lot, current_price)

    # Already in trailing mode
    if current_price > lot.get("trailing_high", 0):
        lot["trailing_high"] = current_price
        return False, f"new local high {current_price}"

    retrace_pct = (lot["trailing_high"] / current_price - 1) * 100
    if retrace_pct >= self.trailing_stop_pct:
        return True, f"trailing stop hit: retrace {retrace_pct:.2f}% from high {lot['trailing_high']}"
    return False, f"in trailing, price {current_price}, high {lot['trailing_high']}"
```

Legacy fallback == logica attuale di `_execute_percentage_sell` / `_execute_sell`.

### Noise protection

Su exchange testnet i tick sono rumorosi. Un `-1%` da `local_high` su un unico tick può essere micro-dip non reale. Due opzioni:

1. **Usare candele 5m chiuse** come "current_price" per il check trailing. Più lento ma meno rumore.
2. **Richiedere 2+ tick sotto trailing_high * (1 - trailing_stop_pct / 100)** prima di vendere.

Opzione 2 più facile da testare. Opzione 1 richiede caching dei prezzi.

**Raccomandazione**: iniziare con Opzione 2 (require 2 ticks consecutivi) per ridurre la superficie di bug.

## Files da modificare

| File | Azione |
|---|---|
| DB (migration) | `ALTER TABLE bot_config ADD COLUMN trailing_activation_pct numeric DEFAULT 0` + `trailing_stop_pct numeric DEFAULT 1.0` |
| `bot/strategies/grid_bot.py` | State fields per lot + `_should_sell_lot` wrapper + noise-protection counter |
| `bot/grid_runner.py` | Leggere 2 nuove colonne da `bot_config`, passarle al GridBot constructor |
| `bot/trend_follower/allocator.py` | Se vogliamo abilitarlo di default per TF → settare `trailing_activation_pct=5.0, trailing_stop_pct=1.5` in `row_fields` |
| `web/admin.html` + `web/tf.html` | Aggiungere i 2 input nel form config (label: "Trailing activation %", "Trailing stop %") |

## Files da NON toccare

- Allocator rotation/ATR logic (→ 36e)
- Skim (reserve_ledger continua a funzionare per-sell, indipendentemente dal trigger)
- Strategy A hardcoded rules (never-sell-at-loss resta attivo — il trailing_activation_pct > 0 garantisce che quando scatta siamo già in profit di almeno X%)

## Decisioni aperte (da raffinare col CEO)

1. **Default per TF**: `trailing_activation_pct=5.0` (scatta solo su pump reali) + `trailing_stop_pct=1.5` (protezione non troppo stretta). Ma:
   - Se troppo stretto (1.5%) → vendi quasi subito dopo l'activation, perdi poco del movimento
   - Se troppo largo (5%) → su pump+retrace veloce, perdi molto del massimo
   - Alternativa: scala trailing_stop_pct con ATR (ATR/2 per esempio).
2. **Abilitare per bot manuali?**: BTC/SOL/BONK potrebbero beneficiarne su pump rari, ma sono stabili. Meglio lasciarlo off finché non validato su TF per ≥1 settimana.
3. **Noise protection**: Opzione 2 (2-tick rule) vs Opzione 1 (5m close). Raccomando Opzione 2 per iniziare.
4. **Trailing stop reset**: se il lot viene toccato da un nuovo buy (diluisce avg_buy_price), si azzera il trailing? Probabilmente sì — l'avg_buy cambiando, il concetto di "pump vs avg" si sposta.

## Test pre-deploy

Test simulati con sequenza di prezzi sintetici:

- [ ] `trailing_activation_pct=0` → comportamento identico a oggi (regression safety)
- [ ] Prezzi: 100, 102, 103, 104 → nessun trigger (sotto activation 5%)
- [ ] Prezzi: 100, 106, 108, 107.9 → activation al 106, high=108, retrace 0.1% non triggera
- [ ] Prezzi: 100, 106, 108, 106.5 → retrace (108-106.5)/108 = 1.39%, non triggera (sotto 1.5%)
- [ ] Prezzi: 100, 106, 108, 106.4 → retrace 1.48%, primo tick → non vende (Opzione 2 richiede 2 tick)
- [ ] Prezzi: 100, 106, 108, 106.4, 106.3 → 2 tick sotto → vende
- [ ] Multi-lot: 2 buy a prezzi diversi, ognuno con il suo trailing_high indipendente

## Test post-deploy

- [ ] Abilitare su 1 solo symbol TF con parametri prudenti (activation=5, stop=2)
- [ ] Aspettare 1 settimana di trading reale
- [ ] Confrontare realized_pnl vs period equivalente pre-trailing su stesso symbol (se disponibile)
- [ ] Nessun crash / log trace ricorrente sul trailing state

## Rollback plan

```bash
# Codice
git revert <commit_hash>
git push origin main

# DB (opzionale: le colonne possono restare, sono no-op se 0)
# ALTER TABLE bot_config DROP COLUMN trailing_activation_pct;
# ALTER TABLE bot_config DROP COLUMN trailing_stop_pct;

ssh max@<mac-mini> 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator
```

Fallback al comportamento attuale è istantaneo: basta settare `trailing_activation_pct=0` via admin UI (niente deploy necessario se il bug è circoscritto).

## Commit format

```
feat(grid-bot): opt-in trailing stop for pump capture

Lots now track trailing_active and trailing_high when the price
crosses trailing_activation_pct above avg_buy. Sell fires when price
retraces trailing_stop_pct from the local high (with 2-tick
confirmation to filter noise). When trailing_activation_pct=0 the
bot behavior is unchanged.

TF allocator can enable it by default with activation=5, stop=1.5
— disabled for now; opt-in per bot via bot_config.
```

## Quando lanciarlo

Il brief 36c ha detto: "dopo 1-2 settimane di osservazione 36c+e, per capire se i pump persi giustificano la complessità". Quindi:

- ≥ 1 settimana con 36c + 36e stabili
- Almeno 1-2 casi documentati di "pump perso" (log + analisi manuale)
- Volontà del CEO di accettare la complessità aggiuntiva

Se nel mentre il TF diventa profittevole con le sole 36c/e/g, valutiamo se 36f è davvero necessario. È il brief più "speculativo" della serie.

---

## Nota correlata — Ridurre `scan_interval_hours` (LOW, cross-cutting)

Oggi il TF fa scan ogni **4h** (vedi `trend_config.scan_interval_hours`). Implicazione: tra due scan una shitcoin può crollare del 15-30% prima che il TF se ne accorga e faccia DEALLOCATE, perdendo gran parte del capitale allocato a quella coin.

**Proposta**: portare lo scan a **1h** (o 2h come compromesso). Benefici:
- BEARISH rilevato 4× più velocemente → perdite capitale contenute sulle coin che si deteriorano
- Trailing stop (36f) reagisce più vicino al peak reale del pump
- Rotation (36e) cattura candidati nuovi prima che salgano troppo

Costi / rischi:
- 4× più API call exchange (Binance ticker/OHLCV per top-50) → limiti rate
- 4× più entries in `trend_scans` e `trend_decisions_log` → storage DB
- Più rumore nel Telegram report (oggi ogni 4h, diventerebbe ogni 1h) → considerare se condensare report su base 4h ma lasciare la logica decisionale a 1h

**Quando testarlo**: insieme a 36e (on-demand rescan + rotation), così la finestra di rilevazione bearish diventa sia più frequente sia sempre consapevole delle coin attive. Se vediamo che 36e+36g sono stabili, ridurre lo scan è probabilmente il single-highest-impact change per la sicurezza del capitale TF.

**Out of scope di questo brief (36f)**: la modifica di `scan_interval_hours` è una tupla decisione+config, non richiede codice (basta UPDATE su `trend_config`). Questa nota serve solo per non dimenticarlo quando stabilizziamo il resto.

---

## Out of scope

- **36e**: rotation + ATR adaptive (brief separato, pronto in config)
- **36g**: TF compounding (brief separato, draft in config)
- **36h**: Haiku reads TF (brief separato, draft in config)
- Stop loss (opposto del trailing stop — vendere in perdita al -X%). Strategy A non ammette sell in perdita, quindi fuori scope.
- Take profit a soglia fissa (es. +20% assoluto). Ridondante col trailing.
