# BRIEF — 39c: TF take-profit (fixed %) + UI exposure

**Date:** 2026-04-18
**Priority:** MEDIUM — feature request, non urgente. Completa il layer safety TF iniziato con 39a.
**Prerequisito:** 39a deployato ✅, 39b deployato ✅ (la sezione "⚠️ TF Safety parameters" di `tf.html` è creata dal 39b — questo brief vi aggiunge un campo)
**Target branch:** `main` (push diretto, niente PR)
**Deploy:** Mac Mini via `git pull` SSH + restart orchestrator
**CC working machine:** MacBook Air (locale)

---

## Problema

Il 39a ha dato ai bot TF uno **stop-loss** (`tf_stop_loss_pct` = 10%). Il sistema ora sa quando **tagliare le perdite**, ma non ha un meccanismo speculare per **cristallizzare i profitti**.

Scenario tipico che vogliamo evitare:

```
TST/USDT — allocata con buy $3.70, 4 lot pieni ($50 deployed)
  Prezzo sale a $4.20 → unrealized +$6.76 (+13.5% alloc)
  Prezzo scende a $3.95 → unrealized +$3.38 (+6.8% alloc)
  Prezzo torna a $3.75 → unrealized +$0.68 (+1.4% alloc)
  Alla fine il grid vende a $3.77 → profit $1.05
```

Il bot aveva un profit "virtuale" di +13.5% a disposizione ed è uscito con +2%. Il resto è "regret avoidance" mancato: il CEO voleva quell'uscita.

Il TF è un **rotatore**. Il capitale che ha già prodotto X% di ritorno va liberato per cercare la prossima opportunità, non lasciato in attesa del prossimo ciclo grid.

---

## Principio di design

- **Take-profit fisso sulla `capital_allocation`**, non sul deployed. Specchio perfetto del 39a: stessa base di calcolo, segno opposto. R:R 1:1 a default (SL -10% / TP +10%).
- **Solo bot TF** (`managed_by = 'trend_follower'`). I bot manuali mantengono Strategy A pura, che è già un "take-profit opportunistico" per sua natura.
- **All-in exit**: trigger → vende tutti i lot. Niente scale-out (out of scope — eventuale brief futuro).
- **Ignora il signal TF**: se scatta il TP, il bot esce anche se ancora BULLISH. È il punto dell'esercizio ("chissenefrega se potevo guadagnare di più").
- **0 = disabilitato**. Stesso pattern di stop-loss e stop-buy.

---

## Fix 1 — Logica take-profit in `grid_bot.py`

### Nuovo attributo

Il `GridBot` riceve dal `grid_runner`:

```python
self.tf_take_profit_pct = cfg.get('tf_take_profit_pct', 10)
```

E mantiene un flag di stato in memoria:

```python
self._take_profit_triggered = False
```

### Check in `check_percentage_grid`

Aggiungi **DOPO** il blocco stop-loss TF (già installato dal 39a), **PRIMA** del blocco stop-buy manuale del 39b:

```python
# Take-profit check for TF bots — evaluate on entire position
if (self.managed_by == "trend_follower"
    and self.tf_take_profit_pct > 0
    and self.state.holdings > 0
    and self.state.avg_buy_price > 0):

    unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
    profit_threshold = self.capital * self.tf_take_profit_pct / 100

    if unrealized >= profit_threshold:
        logger.warning(
            f"[{self.symbol}] TAKE-PROFIT TRIGGERED: unrealized ${unrealized:.2f} "
            f"≥ {self.tf_take_profit_pct}% of allocation ${self.capital:.2f} "
            f"(threshold: ${profit_threshold:.2f})"
        )
        self._take_profit_triggered = True
        # Force sell ALL lots
        for lot in list(self._pct_open_positions):
            trade = self._execute_percentage_sell(current_price)
            if trade:
                trades.append(trade)
```

**Nota ordine dei check nella funzione:**

```
1. stop-loss TF       (39a) → vende in perdita
2. take-profit TF     (39c) → vende in profit
3. stop-buy manual    (39b) → blocca buy futuri
```

Stop-loss e take-profit sono mutuamente esclusivi per design (unrealized non può essere sia < -10% che ≥ +10% contemporaneamente). L'ordine è irrilevante nella pratica, ma mantienilo coerente.

### Override Strategy A — NON necessario

Il TP vende solo in profit (`price > lot_buy_price`). Strategy A **consente già** queste vendite. Quindi NESSUN override da aggiungere nel blocco `if self.strategy == "A" and price < lot_buy_price` del `_execute_percentage_sell`. Il 39c tocca solo `check_percentage_grid`, non la logica di blocco Strategy A.

### Skim sulle vendite TP

Le vendite TP hanno `realized_pnl > 0` per costruzione → skim normale al 30% va in `reserve_ledger`. Già gestito dal codice esistente, nessuna modifica.

### Post-TP cleanup

Dopo la vendita TP, `holdings = 0` e `cash = $50 + $5 = $55` (allocation + profit cristallizzato). Stessa gestione del 39a (Opzione A):

- `grid_runner` rileva `holdings = 0` al prossimo tick
- TF al prossimo scan fa DEALLOCATE → capitale torna in floating budget
- Il `tf_total_capital` (36g) riassorbe il profit → compound automatico

**Importante**: a differenza dello stop-loss, qui il cash post-sell è **maggiore** della allocation originale. Il compounding 36g lo gestisce già correttamente (somma realized_pnl al budget TF), nessuna modifica richiesta.

---

## Fix 2 — Schema DB

```sql
-- Aggiungere parametro take-profit a trend_config
ALTER TABLE trend_config ADD COLUMN tf_take_profit_pct numeric DEFAULT 10;
```

Default 10% = R:R 1:1 contro stop-loss. Modificabile via UI (Fix 3) o SQL diretto senza deploy.

---

## Fix 3 — UI in `tf.html`

Il 39b aggiunge la sezione **"⚠️ TF Safety parameters"** con `tf_stop_loss_pct` e `scan_interval_hours`. Questo brief **aggiunge un terzo campo** alla stessa sezione:

```
tf_take_profit_pct   — Force full liquidation when unrealized profit
                       reaches this % of allocation. Default 10.
                       Current: <value from DB>
                       Sublabel: "Takes profit on the full position when
                       unrealized P&L exceeds this % of capital_allocation.
                       Only applies to TF-managed bots. Set 0 to disable."
```

### Implementazione

Segue lo stesso pattern degli altri due campi già previsti nel 39b:
1. Input text con `inputmode="decimal"`
2. Fetch iniziale da `trend_config`
3. Save via `PATCH /rest/v1/trend_config?id=eq.<id>`
4. Log in `config_changes_log` con `parameter='tf_take_profit_pct'`, `changed_by='manual-ceo'`, `symbol=NULL`

### Coerenza visuale

Stessa label gialla `.safety-label` del 39b. Ordine dei campi in sezione:

```
tf_stop_loss_pct        (da 39b)
tf_take_profit_pct      (questo brief)
scan_interval_hours     (da 39b)
```

Logica dell'ordine: SL e TP sono il coppia di uscita, li tieni vicini. Scan interval è parametro di cadenza, in fondo.

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/strategies/grid_bot.py` | Take-profit check in `check_percentage_grid` (dopo stop-loss 39a, prima di stop-buy 39b). Nessun override Strategy A. |
| `bot/grid_runner.py` | Passare `tf_take_profit_pct` al GridBot constructor, leggerlo da `trend_config`. |
| `web/tf.html` | Aggiungere campo `tf_take_profit_pct` nella sezione "⚠️ TF Safety parameters" (creata da 39b). |
| DB (`trend_config`) | `ALTER TABLE ADD COLUMN tf_take_profit_pct numeric DEFAULT 10` |

## Files da NON toccare

- `config/settings.py` — Strategy A invariata, nessuna costante globale
- `reserve_ledger` — skim già gestito da codice esistente
- `web/admin.html` — i bot manuali non hanno take-profit
- Logica stop-loss (39a) — non modificare, solo aggiungere accanto
- Logica stop-buy (39b) — brief indipendente, coesiste senza conflitti
- `_execute_percentage_sell` / `_execute_sell` — nessun override Strategy A necessario

---

## Test pre-deploy

### Unit test logica take-profit

- [ ] Bot TF con `capital=$50`, `holdings=14.55`, `avg_buy=$3.70`, `price=$4.05` → unrealized +$5.09 ≥ +$5.00 (10%) → **TP TRIGGERED** → sell all lots
- [ ] Bot TF con stesso scenario, `price=$4.00` → unrealized +$4.37 < +$5.00 → no trigger, normal behavior
- [ ] Bot TF con 1 lot solo (`holdings=3.38`, `avg_buy=$3.70`, `capital=$50`), `price=$5.18` → unrealized +$5.00 ≥ +$5.00 → **TP TRIGGERED** (scatta solo su pump +40%, come da design)
- [ ] Bot manuale (managed_by IS NULL) con same numbers → TP **NOT checked** (ramo if skippato)
- [ ] Bot TF con `tf_take_profit_pct = 0` → never triggers (disabilitato)
- [ ] Bot TF con TP triggered → skim normale al 30% del realized_pnl positivo

### Unit test interazione con altri check

- [ ] Bot TF con unrealized = +$5.00 E pending_liquidation=true → TP scatta (ordine: TP prima di deallocation, ma il risultato è lo stesso: vende tutto)
- [ ] Bot TF con unrealized = -$5.00 E potenziale TP future → stop-loss scatta (mutuamente esclusivo, nessun conflitto)
- [ ] Bot TF appena allocato (`holdings=0`) → TP skippato (`if holdings > 0`)

### Integration test

- [ ] Simulare pump: buy a $3.70, prezzo sale progressivamente fino a $4.10 → verificare che TP scatti quando unrealized tocca $5.00
- [ ] Post-TP: verificare `holdings=0`, bot_config `is_active` ancora true → al prossimo scan TF, DEALLOCATE automatico (stesso flow del 39a)
- [ ] `tf_total_capital` (36g) post-TP: verifica che il profit cristallizzato ($5+) entri nel floating budget del TF (via 36g Phase 2 già deployata)

### UI test

- [ ] Sezione "⚠️ TF Safety parameters" di `tf.html` mostra ora 3 campi (SL, TP, scan_interval)
- [ ] `tf_take_profit_pct` modificabile via UI, save funziona
- [ ] Change loggato in `config_changes_log` con `parameter='tf_take_profit_pct'`
- [ ] Valore di default 10 visibile al primo load post-ALTER TABLE

---

## Test post-deploy

- [ ] Verifica che i bot TF attualmente attivi (se ce ne sono) leggano il nuovo parametro al prossimo config refresh (300s)
- [ ] Nessun TP spurio nei primi minuti di log (nessun bot dovrebbe avere già +10% unrealized al momento del restart)
- [ ] Cambiare via tf.html `tf_take_profit_pct` da 10 a 15 → verificare log `config_changes_log` + applicazione entro 300s
- [ ] Nessun impatto sui bot manuali (BTC/SOL/BONK): no "TAKE-PROFIT" log, comportamento invariato
- [ ] Primo TP reale quando scatta (monitoraggio passivo): verificare che sell avvenga all-in, skim coerente, bot venga deallocato al prossimo scan TF

---

## Edge cases

1. **TP e stop-loss mutuamente esclusivi**: `unrealized ≥ +$5` e `unrealized ≤ -$5` non possono essere veri simultaneamente. Per design, uno dei due ramifica; mai entrambi.

2. **TP con 1 solo lot aperto**: come discusso in sessione, serve pump +40% sul prezzo per triggerare ($5 su $12.50 deployed). È coerente con il design "TP sull'allocation". Se accade, scatta comunque correttamente. Se non accade, il bot continua a fare grid normale — corretto.

3. **TP + pending_liquidation=true contemporanei** (BEARISH sopraggiunto mentre prezzo è in profit): TP scatta, bot vende in profit, holdings=0. La `pending_liquidation` diventa irrilevante (niente da liquidare). Corretto.

4. **Flash spike e ritracciamento**: prezzo schizza a +10.1% per 30 secondi, poi ritorna. Il `check_percentage_grid` gira ogni 20-60s. Se becca lo spike → TP triggered, profit cristallizzato. Se non lo becca → nessuno esce, comportamento normale. Accettabile in entrambi i casi.

5. **TP triggered durante un buy cycle**: il bot sta per comprare il 3° lot quando TP scatta. Il TP vende i primi 2 lot, holdings=0, nessun 3° buy (perché holdings=0 + check TP ha già processato). Corretto.

6. **`tf_take_profit_pct = 0`**: TP disabilitato, bot continua a fare grid + si affida a stop-loss / BEARISH exit / SWAP per uscire. Fallback comportamento pre-39c.

7. **Rientro sulla stessa coin dopo TP**: dopo TP, MBOX (esempio) viene deallocata. Al prossimo scan, se MBOX è ancora top bullish → TF può ri-allocarla a prezzo più alto (post-pump). Il design lo permette. Potenziale "buy high, sell higher" — accettabile se il trend continua; rischio se è top del pump.

8. **TP con skim scenario**: $5 profit → $1.50 skim → $3.50 net profit cristallizzato nel budget TF. Il compounding 36g vede i $3.50 come "realized profit" ed espande `tf_total_capital` di conseguenza. Corretto.

---

## Interazione con brief precedenti

- **39a (TF stop-loss)**: speculare perfetto. Stesso calcolo base, segno opposto. Mutuamente esclusivi per costruzione. Coesistono nello stesso `check_percentage_grid`.
- **39b (manual stop-buy)**: indipendente. 39b tocca bot manuali, 39c tocca bot TF. Si ramificano su `managed_by`. Il 39b crea la sezione UI "⚠️ TF Safety parameters" in tf.html; questo brief vi aggiunge un campo.
- **36e v2 (rotation)**: nessun conflitto. La rotation guarda `signal_strength` e profit; il TP cristallizza il profit prima che rotation o BEARISH decidano. Scatta prima del prossimo scan se il prezzo tocca soglia.
- **36g (compounding)**: il profit TP entra nel `tf_total_capital` via il meccanismo Phase 2 già deployato. Nessuna modifica al compounding. Il compound "gode" dei TP → budget TF cresce più velocemente rispetto a "aspettare che Strategy A venda spontaneamente".
- **36f (trailing stop, parked)**: ortogonale ma sovrapposto concettualmente. Quando 36f verrà implementato, sarà ALTERNATIVA al TP fisso (trailing cattura pump grossi, TP fisso cattura pump medi). Possibile coesistenza: TP fisso come "floor" (vende almeno a +X%), trailing come "ceiling" (cattura il massimo se supera X%). Out of scope adesso.
- **reserve_ledger / skim**: nessun impatto, skim già gestito.

---

## Rollback plan

```bash
git revert <commit_hash>
git push origin main
ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator
```

Rollback torna a comportamento pre-39c: TF bot escono solo via stop-loss (39a), BEARISH signal, o rotation SWAP. Niente take-profit automatico. La colonna DB `tf_take_profit_pct` resta ma inutilizzata — innocua.

Fallback rapido senza rollback: via tf.html UI (o SQL diretto), settare `tf_take_profit_pct = 0` → disabilita il TP. Nessun restart necessario, effetto al prossimo config refresh (300s).

---

## Commit format

```
feat(grid-bot): TF take-profit on allocation drawdown+

TF-managed bots now trigger full liquidation when unrealized profit
exceeds tf_take_profit_pct (default 10%) of capital_allocation. All
lots sold at current price (profit ≥ 0 by definition, so Strategy A
allows naturally — no override needed).

Symmetric to 39a stop-loss: same base calculation (unrealized vs
capital × pct), opposite sign. R:R 1:1 at default (SL -10% / TP +10%).
Mutually exclusive by construction.

Post-TP: holdings=0, skim routes 30% of realized_pnl to reserve_ledger,
TF deallocates at next scan (same flow as 39a stop-loss).

UI: tf.html "⚠️ TF Safety parameters" section (created by 39b) gets
third editable field.
```

---

## Scope rules

- **Non aggiungere** scale-out / laddered TP (out of scope — brief futuro se il fixed 10% si rivela troppo rigido)
- **Non aggiungere** trailing stop (36f parked)
- **Non toccare** la logica buy (questo brief riguarda solo exit)
- **Non toccare** `config/settings.py` o Strategy A globale
- **Non aggiungere** TP per bot manuali (i manuali tengono Strategy A pura)
- Push diretto su `main` quando done
- Stop quando done

---

## Out of scope

- **Scale-out / laddered TP** (es: vendi 50% a +10%, resto con trailing) — brief futuro, serve prima 36f
- **TP dinamico basato su ATR** — il TP resta fisso %; volatilità modula già `sell_pct` del grid via 36e
- **TP per bot manuali** — out of scope, Strategy A è già il loro TP opportunistico
- **Backtest retrospettivo per calibrare il default 10%** — brief futuro dopo 2-4 settimane di dati reali
- **Persistenza del flag `_take_profit_triggered` in DB** — non serve, scatta una volta e basta (holdings=0 impedisce retrigger)
- **Scale-in aggressivo su signal_strength alto** — concetto discusso in sessione, parcheggiato. Entry size resta fissa a 1 lot indipendentemente dal signal, per non concentrare rischio davanti.

---

## Note finali

Brief minimale per scope: 1 check in `grid_bot.py`, 1 pass-through in `grid_runner.py`, 1 campo UI in `tf.html`, 1 colonna DB. CC può farlo in un unico commit atomico. L'unica dipendenza esterna è che il 39b abbia già creato la sezione "⚠️ TF Safety parameters" in `tf.html` — se il 39b non è ancora deployato, **aspetta il 39b prima di iniziare il 39c** (o segnala al CEO che serve mergiarli).
