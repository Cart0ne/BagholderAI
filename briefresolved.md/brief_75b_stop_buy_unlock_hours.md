# Brief 75b — Stop-buy unlock hours (timer-based auto-reset)

**Basato su:** PROJECT_STATE.md 2026-05-12 (sessione 74b)  
**Richiesto da:** Board (Max)  
**Priorità:** pre-mainnet

---

## Contesto

Il flag `_stop_buy_active` (Brief 39b) è "latched": scatta quando il drawdown supera `stop_buy_drawdown_pct` e si resetta **solo** su una sell in profitto (`sell_pipeline.py`). In pratica, se il prezzo scende e resta sotto, il bot resta bloccato indefinitamente — nessun modo di sbloccare senza intervento codice o restart con workaround config.

**Richiesta Board:** aggiungere un timer configurabile che auto-resetti il flag dopo N ore. Se impostato a 0, il timer non scatta (comportamento attuale preservato).

---

## Cosa fare

### 1. Nuova colonna `bot_config`

```sql
ALTER TABLE bot_config
ADD COLUMN stop_buy_unlock_hours REAL DEFAULT 0;

COMMENT ON COLUMN bot_config.stop_buy_unlock_hours IS
  'Hours after stop-buy activation before auto-reset. 0 = disabled (only profitable sell resets).';
```

### 2. `bot/grid/grid_bot.py` — tracciare timestamp attivazione

Nell'`__init__` (dove si inizializzano gli altri flag):

```python
self._stop_buy_activated_at: Optional[datetime] = None  # 75b: timestamp for timeout
self.stop_buy_unlock_hours: float = 0.0                # 75b: 0 = disabled
```

Nel blocco 39b (stop-buy trigger, riga ~dove `self._stop_buy_active = True`):

```python
self._stop_buy_active = True
self._stop_buy_activated_at = datetime.utcnow()  # 75b
```

### 3. `bot/grid/grid_bot.py` — auto-reset check in `check_price_and_execute`

Inserire **PRIMA** del blocco buy (così se il timer scade, il buy dello stesso tick è già sbloccato). Posizione: subito dopo il blocco 39b (stop-buy check), prima del sell check.

```python
# --- 75b: stop-buy unlock hours auto-reset ---
# If stop_buy_unlock_hours > 0 and enough time has passed since
# activation, auto-reset the flag. The bot resumes buying at market
# (DCA logic). This prevents indefinite lockout in prolonged drawdowns
# where no profitable sell is possible.
if (self._stop_buy_active
        and self.stop_buy_unlock_hours > 0
        and self._stop_buy_activated_at is not None):
    elapsed_sb = (datetime.utcnow() - self._stop_buy_activated_at).total_seconds() / 3600
    if elapsed_sb >= self.stop_buy_unlock_hours:
        logger.info(
            f"[{self.symbol}] STOP-BUY UNLOCK: {elapsed_sb:.1f}h >= "
            f"{self.stop_buy_unlock_hours}h threshold. Auto-resetting buy block."
        )
        self._stop_buy_active = False
        self._stop_buy_activated_at = None
        log_event(
            severity="info",
            category="safety",
            event="stop_buy_unlock_reset",
            symbol=self.symbol,
            message=f"Stop-buy auto-reset after {elapsed_sb:.1f}h unlock window",
            details={
                "elapsed_hours": float(elapsed_sb),
                "unlock_hours": float(self.stop_buy_unlock_hours),
            },
        )
```

### 4. `bot/grid/sell_pipeline.py` — reset anche il timestamp

Dove `_stop_buy_active` viene resettato dalla profitable sell:

```python
if bot._stop_buy_active and realized_pnl > 0:
    bot._stop_buy_active = False
    bot._stop_buy_activated_at = None  # 75b: clear timestamp
```

### 5. `bot/grid_runner.py` — hot-reload da Supabase

In `_sync_config_to_bot`, aggiungere dopo il blocco `stop_buy_drawdown_pct`:

```python
if "stop_buy_unlock_hours" in sb_cfg and sb_cfg["stop_buy_unlock_hours"] is not None:
    bot.stop_buy_unlock_hours = float(sb_cfg["stop_buy_unlock_hours"])
```

### 6. `bot/grid_runner.py` — mirror in `_upsert_runtime_state`

Aggiungere `stop_buy_activated_at` al payload UPSERT di `bot_runtime_state`, così la dashboard può mostrare da quanto è attivo:

```python
"stop_buy_activated_at": bot._stop_buy_activated_at.isoformat() if bot._stop_buy_activated_at else None,
```

### 7. Dashboard `grid.html` — mostrare countdown (opzionale, low priority)

Se `stop_buy_active = true` e `stop_buy_activated_at` presente e `stop_buy_unlock_hours > 0`:
mostrare "BLOCKED · resets in Xh Ym" invece di solo "BLOCKED".

---

## Decisioni delegate a CC

- Posizione esatta del blocco 75b dentro `check_price_and_execute` (prima del buy check, dopo il 39b check)
- Formato log/evento

## Decisioni che CC DEVE chiedere

- Nessuna — brief è completo

## Output atteso

- 1 migration SQL (colonna `stop_buy_unlock_hours`)
- Codice modificato in: `grid_bot.py`, `sell_pipeline.py`, `grid_runner.py`
- Test: stop-buy scatta → dopo finestra unlock → auto-reset → buy riprende
- Opzionale: countdown su `grid.html`

## Vincoli

- **NON toccare** sell_pipeline logic (tranne aggiunta `_stop_buy_activated_at = None`)
- **NON toccare** TF/Sentinel/Sherpa
- **NON cambiare** la soglia drawdown logic (39b resta com'è)
- Il timer è aggiuntivo, non sostitutivo: una profitable sell resetta PRIMA della finestra unlock

## Test checklist

- [ ] `stop_buy_unlock_hours = 0` → comportamento identico a oggi (no auto-reset)
- [ ] `stop_buy_unlock_hours = 24` → dopo 24h auto-reset, buy riprende
- [ ] Profitable sell prima della finestra unlock → reset immediato (timestamp cleared)
- [ ] Hot-reload: cambio valore su Supabase → bot lo legge al tick successivo
- [ ] Restart bot: `_stop_buy_activated_at` è None → se drawdown ancora sopra soglia, re-trigger con nuovo timestamp

## Roadmap impact

- Chiude la decisione parcheggiata in PROJECT_STATE S74: "stop-buy time-limit (24h then buy anyway to lower avg cost)"
- Pre-mainnet: consente sblocco senza restart
- Default `0` (disabled) → comportamento attuale preservato; opt-in per-coin via dashboard `bot_config`
