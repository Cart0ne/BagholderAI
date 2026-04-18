# BRIEF — 39a: TF stop-loss + bearish exit + scan/idle tuning

**Date:** 2026-04-18
**Priority:** HIGH — capitale bloccato in produzione (MOVR zombie)
**Prerequisito:** 36g Phase 2 deployato ✅
**Target branch:** `main` (push diretto)
**Deploy:** Mac Mini via git pull + restart orchestrator

---

## Problema

MOVR è una trappola perfetta che espone un bug di design:

```
MOVR/USDT — allocata 17 apr 10:36 UTC
  capital_allocation: $50
  4 lot aperti: $3.88, $3.70, $3.61, $3.53
  Prezzo attuale: ~$2.46
  Unrealized: -$17.58 (-35% della allocation)
  Cash: $0 (tapped out)
  Signal TF: ancora BULLISH (strength 20, in calo)
  pending_liquidation: false
```

Tre problemi sovrapposti:

1. **Strategy A blocca la vendita**: `price < lot_buy_price → BLOCKED`. Anche se il TF flippasse BEARISH e settasse `pending_liquidation=true`, il grid_bot rifiuterebbe la sell perché tutti i lot sono underwater.

2. **Nessun stop-loss**: il bot può perdere il 50%, 80%, 100% della allocation senza mai uscire. Il capitale resta bloccato indefinitamente.

3. **Scanner troppo lento**: scan ogni 4h = il TF scopre il crollo con ore di ritardo. Idle reentry 24h = un bot stallato aspetta un giorno intero prima di riallinearsi.

**Risultato**: $50 (10% del portfolio) bloccati in un bot che non può comprare, non può vendere, e non può essere riallocato.

---

## Principio di design

Il TF è un **rotatore**, non un holder. Il capitale fermo in una coin che perde è capitale che non lavora altrove. Anche perdere un rimbalzo del 40% su una coin è accettabile se quei $50 liberati producono il 15-20% su un'altra coin bullish.

**Per i bot TF, "never sell at loss" viene sostituito da regole di uscita consapevoli.**
I bot manuali (BTC/SOL/BONK) restano con Strategy A originale.

---

## Fix 1 — Stop-loss per bot TF (10% della allocation)

### Regola

Se l'unrealized loss dell'**intero bot** (non del singolo lot) supera il 10% della `capital_allocation`, vendere TUTTI i lot — anche in perdita.

```
unrealized_loss = (current_price - avg_buy_price) * holdings
if managed_by == 'trend_follower' AND unrealized_loss < -(capital_allocation * tf_stop_loss_pct / 100):
    → VENDI TUTTO, override Strategy A
```

Con MOVR: 10% di $50 = $5. Avrebbe venduto a -$5 invece di arrivare a -$17.58.

### Parametro

Aggiungere `tf_stop_loss_pct` in `trend_config` (default 10). Modificabile via DB senza deploy.

### Implementazione

In `grid_bot.py`, nel metodo `_execute_percentage_sell` (e `_execute_sell`), il blocco Strategy A diventa:

```python
# Strategy A never sells at a loss — UNLESS this is a TF-managed bot
# with stop-loss override
if self.strategy == "A" and price < lot_buy_price:
    if self.managed_by == "trend_follower" and self._stop_loss_triggered:
        logger.warning(
            f"STOP-LOSS OVERRIDE: Selling {self.symbol} at {fmt_price(price)} "
            f"< lot buy {fmt_price(lot_buy_price)}. "
            f"Unrealized loss exceeds {self.tf_stop_loss_pct}% threshold."
        )
        # Allow the sell to proceed
    else:
        logger.info(
            f"BLOCKED: Sell at {fmt_price(price)} < lot buy {fmt_price(lot_buy_price)}. "
            f"Strategy A never sells at loss."
        )
        return None
```

Il check `_stop_loss_triggered` viene calcolato nel metodo `check_percentage_grid`:

```python
# Stop-loss check for TF bots — evaluate on entire position, not per-lot
if (self.managed_by == "trend_follower"
    and self.tf_stop_loss_pct > 0
    and self.state.holdings > 0
    and self.state.avg_buy_price > 0):

    unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
    loss_threshold = -(self.capital * self.tf_stop_loss_pct / 100)

    if unrealized <= loss_threshold:
        logger.warning(
            f"[{self.symbol}] STOP-LOSS TRIGGERED: unrealized ${unrealized:.2f} "
            f"exceeds -{self.tf_stop_loss_pct}% of allocation ${self.capital:.2f} "
            f"(threshold: ${loss_threshold:.2f})"
        )
        self._stop_loss_triggered = True
        # Force sell ALL lots
        for lot in list(self._pct_open_positions):
            trade = self._execute_percentage_sell(current_price)
            if trade:
                trades.append(trade)
```

### Skim sulle vendite in perdita

Le sell in perdita hanno `realized_pnl < 0`. Il grid_bot skimma solo profitti positivi (`if realized_pnl > 0: skim`). Quindi nessun problema: vendite in perdita → zero skim → corretto.

---

## Fix 2 — Exit on BEARISH (override Strategy A per TF)

### Regola

Se `pending_liquidation = true` E `managed_by = 'trend_follower'`, vendere tutti i lot **a qualsiasi prezzo** — anche in perdita.

Oggi `pending_liquidation` viene settato quando il TF classifica una coin come BEARISH. Ma la vendita è bloccata da Strategy A se il prezzo è sotto il buy.

### Implementazione

Stesso punto del Fix 1 — il blocco Strategy A accetta un secondo override:

```python
if self.strategy == "A" and price < lot_buy_price:
    if self.managed_by == "trend_follower" and self._stop_loss_triggered:
        logger.warning(f"STOP-LOSS OVERRIDE: ...")
    elif self.managed_by == "trend_follower" and self.pending_liquidation:
        logger.warning(
            f"BEARISH EXIT OVERRIDE: Selling {self.symbol} at {fmt_price(price)} "
            f"< lot buy {fmt_price(lot_buy_price)}. "
            f"TF signal BEARISH, pending liquidation."
        )
    else:
        logger.info(f"BLOCKED: Strategy A never sells at loss.")
        return None
```

Il `pending_liquidation` è già letto dal `grid_runner` ad ogni ciclo. Basta che il grid_bot lo riceva come attributo.

### Interazione Fix 1 + Fix 2

- Stop-loss (Fix 1) scatta **indipendentemente** dal segnale TF — anche se BULLISH
- Bearish exit (Fix 2) scatta **indipendentemente** dalla % di perdita — anche se -2%
- Possono scattare entrambi (bearish + oltre 10% = vendi comunque)
- Se nessuno dei due scatta (es: -5% e ancora bullish) → comportamento attuale (hold)

---

## Fix 3 — Scan interval a 1h

### Modifica

```sql
UPDATE trend_config SET scan_interval_hours = 1 WHERE id = (SELECT id FROM trend_config LIMIT 1);
```

**Impatto**: il TF valuta rotazioni ogni ora invece che ogni 4h. Un segnale BEARISH viene rilevato 4× più velocemente. Combinato col Fix 2, il TF può uscire in perdita entro 1h dal flip del segnale.

**Costo**: ~4× più API call exchange per scan (ticker + OHLCV per top-50 coin). Binance rate limit generoso per paper trading, non dovrebbe essere un problema.

### Nota su Telegram

Oggi il report TF va su Telegram ad ogni scan. Con scan ogni 1h → 24 report/giorno. Potrebbe essere troppo rumore.

**Proposta**: il report Telegram resta ogni 4h (o 6h), ma la logica decisionale gira ogni 1h. Implementare con un check:

```python
# Report to Telegram only every N scans
scans_since_last_report = ...  # contatore
if scans_since_last_report >= 4:  # report every 4 scans = 4h
    send_telegram_report()
    scans_since_last_report = 0
```

Oppure, più semplice: NON toccare il report adesso. Se diventa rumoroso, brief separato.

**Raccomandazione CEO**: per ora lascia il report ad ogni scan (1h). Se troppo rumore, lo limitiamo dopo. Meglio avere troppa visibilità all'inizio.

---

## Fix 4 — Idle reentry default a 1h per TF

### Modifica

In `bot/trend_follower/allocator.py → apply_allocations`, nel `row_fields` di ALLOCATE:

```python
"idle_reentry_hours": 1,  # TF: re-enter fast (vs 24h manual default)
```

**Effetto**: se un grid TF non fa trade per 1h, resetta il reference price al prezzo corrente. Così il prossimo buy parte dal livello attuale, non dal vecchio reference.

**Combinazione con scan 1h**: scan ogni ora + idle reentry ogni ora = il sistema è reattivo. Se una coin sale senza dippare del buy_pct, dopo 1h il bot si riallinea e compra al nuovo livello.

### Applicazione alle allocation esistenti

Come da 36i: SOLO le nuove ALLOCATE/SWAP usano 1h. MOVR/TST attuali mantengono il loro valore corrente. Se vuoi applicare subito, UPDATE manuale via admin:

```sql
UPDATE bot_config SET idle_reentry_hours = 1
WHERE managed_by = 'trend_follower' AND is_active = true;
```

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/strategies/grid_bot.py` | Stop-loss check in `check_percentage_grid` + override Strategy A in `_execute_percentage_sell` e `_execute_sell` per TF bots |
| `bot/grid_runner.py` | Passare `pending_liquidation`, `managed_by`, `tf_stop_loss_pct` al GridBot constructor; leggere `tf_stop_loss_pct` da `trend_config` |
| `bot/trend_follower/allocator.py` | `idle_reentry_hours: 1` nel `row_fields` |
| DB (`trend_config`) | Aggiungere `tf_stop_loss_pct numeric DEFAULT 10`; UPDATE `scan_interval_hours = 1` |

## Files da NON toccare

- `config/settings.py` — `STRATEGY_A_SELL_AT_LOSS = False` resta per i bot manuali
- `reserve_ledger` — vendite in perdita non generano skim, nessun impatto
- `commentary.py` / Haiku — brief separato (36h)
- Telegram report frequency — valutare dopo

## Schema DB

```sql
-- Aggiungere parametro stop-loss a trend_config
ALTER TABLE trend_config ADD COLUMN tf_stop_loss_pct numeric DEFAULT 10;

-- Scan interval a 1h
UPDATE trend_config SET scan_interval_hours = 1;
```

---

## Test pre-deploy

### Unit test stop-loss
- [ ] Bot TF con avg_buy $3.70, holdings 14.55, capital $50, price $3.35 → unrealized -$5.09 > -$5.00 (10%) → STOP-LOSS TRIGGERED → sell all lots
- [ ] Bot TF con avg_buy $3.70, holdings 14.55, capital $50, price $3.40 → unrealized -$4.36 < -$5.00 → no trigger, normal behavior
- [ ] Bot manuale (BTC) con same numbers → Strategy A blocks sell, stop-loss NOT checked
- [ ] Bot TF stop-loss triggered → skim = $0 (no profit to skim on losing sells)

### Unit test bearish exit
- [ ] Bot TF con pending_liquidation=true, price < lot_buy_price → sell proceeds (override)
- [ ] Bot manuale con pending_liquidation=true (shouldn't happen, but safety) → sell BLOCKED by Strategy A
- [ ] Bot TF con pending_liquidation=true, price > lot_buy_price → sell proceeds (normal, no override needed)

### Integration test
- [ ] MOVR scenario replay: simulate price sequence $3.14 → $4.01 → $2.46, verify stop-loss fires at ~$3.34 (when unrealized hits -$5)
- [ ] After stop-loss sell: bot_config `is_active` remains true, `pending_liquidation` remains false — the TF handles deallocation at next scan
- [ ] Or: stop-loss sell empties holdings → grid_runner detects holdings=0 → marks for TF cleanup

### Config test
- [ ] Scan interval = 1h → TF runs scan approximately every hour (check logs)
- [ ] New ALLOCATE → idle_reentry_hours = 1 in bot_config
- [ ] Existing bots unaffected unless manually updated

---

## Test post-deploy

- [ ] Applicare immediatamente a MOVR (o attendere che il nuovo codice la liquidi automaticamente)
- [ ] Monitorare primo ciclo: TF scanna ogni 1h, MOVR venduta (stop-loss o bearish, whichever first)
- [ ] Capitale liberato → TF riallocca nel giro di 1-2 scan
- [ ] Bot manuali BTC/SOL/BONK non impattati (verificare log: nessun "STOP-LOSS" o "BEARISH EXIT" su di loro)
- [ ] Telegram report: verificare frequenza (ogni ora ora) e decidere se ridurre

---

## Edge cases

1. **Stop-loss durante un sell profittevole**: il bot ha 4 lot, 1 è in profit e 3 sono underwater. Stop-loss triggered → vende tutti e 4. Il lot in profit genera skim normalmente, i 3 in perdita no. Corretto.

2. **Stop-loss + pending_liquidation contemporanei**: entrambi gli override sono attivi. Non importa quale viene loggato — il risultato è lo stesso (vendi tutto).

3. **Stop-loss su bot con $0 holdings**: niente da vendere, niente da fare. Skip.

4. **Rientro sulla stessa coin**: dopo stop-loss, MOVR viene deallocata. Al prossimo scan, se MOVR è ancora nei top bullish → TF può ri-allocarla a prezzo più basso. Il design lo permette naturalmente.

5. **Flash crash + recovery**: prezzo crolla 10%, stop-loss vende, prezzo risale 20 minuti dopo. Perdita cristallizzata. Accettabile: il TF rientrerà sulla stessa coin al prossimo scan se ancora bullish, a prezzo più basso. Il costo è la fee + lo spread della vendita in perdita.

6. **tf_stop_loss_pct = 0**: disabilita lo stop-loss (nessun trigger). Safety: trattare 0 come "disabilitato".

7. **Stop-loss su un bot che ha appena comprato il primo lot**: unrealized loss calcolata sull'intero bot (non per-lot). Con 1 lot da $12.50, serve un calo del 10% di $50 = $5 → calo del 40% dal buy price. Molto improbabile su un singolo lot, ma possibile su shitcoin. OK — se perde il 40% sul primo buy, è giusto uscire.

---

## Interazione con brief precedenti

- **36f (trailing stop)**: indipendente. Il trailing stop cattura i pump in salita; lo stop-loss taglia le perdite in discesa. Possono coesistere.
- **36g (compounding)**: le vendite in perdita riducono il floating cash (meno profitti da riassorbire). Corretto.
- **36h (Haiku vede TF)**: le vendite stop-loss appariranno nei trade con `reason` contenente "STOP-LOSS". Haiku potrà commentare.
- **Scan interval 1h**: le vendite stop-loss avvengono nel grid_runner (check ogni 20-60s), NON nello scan TF. Lo scan 1h serve solo per la classificazione BEARISH (Fix 2) e la rotazione.

---

## Post stop-loss: chi fa cleanup?

Dopo un sell stop-loss, il bot ha holdings=0 e cash = (quanto ha ricevuto dalla vendita in perdita). Due opzioni:

**A.** Il grid_runner setta `pending_liquidation=true` quando rileva holdings=0 dopo stop-loss. Il TF al prossimo scan fa DEALLOCATE.

**B.** Il grid_bot si auto-segnala con un campo `stop_loss_triggered_at` in bot_config. Il TF lo legge e fa DEALLOCATE.

**Raccomandazione: A** — più semplice. Il grid_runner già gestisce il lifecycle. Se holdings=0 e il bot è TF-managed, il TF lo noterà al prossimo scan (entro 1h) e lo dealloca.

Attenzione: il cash dalla vendita in perdita è inferiore alla capital_allocation originale. Il floating cash del TF diminuirà. Corretto: abbiamo perso soldi, il budget effettivo scende.

---

## Rollback plan

```bash
git revert <commit_hash>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator
```

Rollback riporta Strategy A piena per tutti i bot. MOVR resterebbe zombie ma almeno non si rompe nient'altro.

Fallback rapido senza rollback: `UPDATE trend_config SET tf_stop_loss_pct = 0` → disabilita stop-loss. Scan interval: `UPDATE trend_config SET scan_interval_hours = 4` → torna a prima.

---

## Commit format

```
feat(grid-bot): TF stop-loss + bearish exit override Strategy A

TF-managed bots can now sell at a loss under two conditions:
1. Unrealized loss exceeds tf_stop_loss_pct (default 10%) of
   capital_allocation → immediate full liquidation
2. pending_liquidation=true (BEARISH signal) → sell at any price

Strategy A "never sell at loss" remains unchanged for manual bots
(BTC/SOL/BONK). Also: scan_interval_hours=1, idle_reentry_hours=1
for faster TF reaction.
```

---

## Azione immediata post-deploy

Una volta deployato, MOVR verrà liquidata automaticamente al primo check del grid_runner (unrealized -35% >> threshold 10%). I ~$35 recuperati tornano nel floating TF e vengono riallocati al prossimo scan.

Se vuoi forzare prima del deploy: `UPDATE bot_config SET pending_liquidation = true WHERE symbol = 'MOVR/USDT'` — ma col codice attuale Strategy A la bloccherà comunque. Quindi: deploy first, MOVR si liquida da sola.

---

## Out of scope

- 36f: trailing stop pump (brief separato, dopo stabilizzazione)
- 36h: Haiku vede TF (brief separato, dopo 1 settimana stabile)
- Telegram report frequency tuning (valutare dopo qualche giorno a 1h)
- Stop-loss per bot manuali (non richiesto, Strategy A holder resta)
- Stop-loss dinamico basato su skim/profit (idea originale di Max — parcheggiata per v2 se il 10% fisso non basta)
