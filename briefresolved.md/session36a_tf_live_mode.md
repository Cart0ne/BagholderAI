# INTERN BRIEF — Session 36a: Trend Follower Live Mode (v2 — corrected)

**Date:** April 15, 2026
**Priority:** HIGH — abilita TF autonomy reale
**Prerequisito:** Brief 35b (orchestrator) deployato e funzionante ✅

---

## Context

Il Trend Follower gira in shadow mode (`dry_run=true`). Scansiona, classifica, decide — ma non scrive su `bot_config`. L'orchestrator è live.

Questo brief fa quattro cose:
1. Corregge `decide_allocations` per usare il budget reale di TF (`tf_budget=$100`, `tf_max_coins=2`) invece del capitale totale del sistema
2. Implementa `apply_allocations()` — la funzione che scrive su `bot_config` (con `capital_per_trade` derivato dal capitale allocato)
3. Collega tutto nel main loop
4. Allinea i messaggi Telegram (scan report + avvio TF) ai nuovi valori TF-only

**Budget TF:** `tf_budget = 100` (in `trend_config`)
**Max coin TF:** `tf_max_coins = 2` (in `trend_config`)
**Whitelist manuale (NON toccare MAI):** `{'BTC/USDT', 'SOL/USDT', 'BONK/USDT'}`

---

## File da modificare

| File | Azione |
|------|--------|
| `bot/trend_follower/allocator.py` | Aggiungere `MANUAL_WHITELIST`, fix `decide_allocations`, aggiungere `apply_allocations` |
| `bot/trend_follower/trend_follower.py` | Fix chiamata a `decide_allocations`, import + call `apply_allocations` |

Nessun nuovo file. Zero modifiche a `grid_runner.py` o `grid_bot.py`.

---

## 1. `bot/trend_follower/allocator.py`

### 1a. Whitelist — aggiungere dopo gli import

```python
# Symbols managed manually by Max — TF must NEVER touch these
MANUAL_WHITELIST = {"BTC/USDT", "SOL/USDT", "BONK/USDT"}
```

### 1b. Fix `decide_allocations` — leggere `tf_max_coins`

Trova questa riga all'inizio di `decide_allocations`:

```python
max_grids = config.get("max_active_grids", 5)
```

Sostituisci con:

```python
max_grids = config.get("tf_max_coins") or config.get("max_active_grids", 5)
```

Questo è l'unico cambiamento necessario in `decide_allocations`. Il capitale TF corretto (`tf_budget`) viene passato dall'esterno — vedi sezione 2b.

### 1c. Aggiungere `apply_allocations()` — in fondo al file

```python
def apply_allocations(supabase, decisions: list[dict], config: dict) -> None:
    """
    Apply TF allocation decisions to bot_config.
    Called only when dry_run=False.

    ALLOCATE  → INSERT or UPDATE bot_config (is_active=True, managed_by='trend_follower')
    DEALLOCATE → SET pending_liquidation=True (grid_runner forza vendita + si ferma)

    NEVER tocca simboli in MANUAL_WHITELIST.
    """
    for d in decisions:
        symbol = d["symbol"]
        action = d["action_taken"]

        # Safety: mai toccare i bot manuali
        if symbol in MANUAL_WHITELIST:
            logger.warning(f"[ALLOCATOR] Skipping {symbol} — in MANUAL_WHITELIST")
            continue

        if action == "ALLOCATE":
            snapshot = d.get("config_snapshot", {})
            capital = snapshot.get("capital_allocation", 0)

            if capital <= 0:
                logger.warning(f"[ALLOCATOR] {symbol}: capital=0, skipping ALLOCATE")
                continue

            # Grid params basati sul segnale
            signal = d.get("signal", "SIDEWAYS")
            if signal == "BULLISH":
                buy_pct = 1.5
                sell_pct = 1.2
            elif signal == "BEARISH":
                buy_pct = 2.0
                sell_pct = 0.8
            else:  # SIDEWAYS / NO_SIGNAL
                buy_pct = 1.5
                sell_pct = 1.0

            # capital_per_trade: 1/4 del capitale con floor $6 (> min_notional Binance $5)
            # Evita che il grid parta con $25 default BTC quando TF ha allocato solo $10
            capital_per_trade = max(6.0, round(capital / 4, 2))

            try:
                existing = supabase.table("bot_config").select("symbol").eq("symbol", symbol).execute()

                if existing.data:
                    supabase.table("bot_config").update({
                        "is_active": True,
                        "managed_by": "trend_follower",
                        "pending_liquidation": False,
                        "capital_allocation": capital,
                        "capital_per_trade": capital_per_trade,
                        "buy_pct": buy_pct,
                        "sell_pct": sell_pct,
                        "grid_mode": "percentage",
                    }).eq("symbol", symbol).execute()
                    logger.info(f"[ALLOCATOR] UPDATED {symbol} in bot_config (${capital:.0f}, per_trade=${capital_per_trade:.2f})")
                else:
                    supabase.table("bot_config").insert({
                        "symbol": symbol,
                        "is_active": True,
                        "managed_by": "trend_follower",
                        "pending_liquidation": False,
                        "capital_allocation": capital,
                        "capital_per_trade": capital_per_trade,
                        "buy_pct": buy_pct,
                        "sell_pct": sell_pct,
                        "grid_mode": "percentage",
                    }).execute()
                    logger.info(f"[ALLOCATOR] INSERTED {symbol} in bot_config (${capital:.0f}, per_trade=${capital_per_trade:.2f})")

            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply ALLOCATE for {symbol}: {e}")

        elif action == "DEALLOCATE":
            try:
                existing = supabase.table("bot_config").select(
                    "symbol, managed_by"
                ).eq("symbol", symbol).execute()

                if existing.data:
                    if existing.data[0].get("managed_by") != "trend_follower":
                        logger.warning(
                            f"[ALLOCATOR] {symbol}: managed_by={existing.data[0].get('managed_by')}, "
                            f"skipping DEALLOCATE (not TF-managed)"
                        )
                        continue

                    supabase.table("bot_config").update({
                        "pending_liquidation": True,
                    }).eq("symbol", symbol).execute()
                    logger.info(f"[ALLOCATOR] SET pending_liquidation=True for {symbol}")
                else:
                    logger.warning(f"[ALLOCATOR] {symbol}: not in bot_config, nothing to deallocate")

            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply DEALLOCATE for {symbol}: {e}")

        # SKIP / HOLD / altri → nessuna scrittura
```

---

## 2. `bot/trend_follower/trend_follower.py`

### 2a. Import `apply_allocations`

Trova:

```python
from bot.trend_follower.allocator import decide_allocations
```

Sostituisci con:

```python
from bot.trend_follower.allocator import decide_allocations, apply_allocations
```

### 2b. Fix chiamata a `decide_allocations` nel main loop

Trova questo blocco nel main loop (righe circa 100-110):

```python
# Decide allocations
decisions = decide_allocations(
    coins, current_allocs, coin_tiers,
    exchange_filters, config, total_capital,
)
```

Sostituisci con:

```python
# TF opera SOLO sul suo budget e sulle sue allocazioni
# I coin manuali (BTC/SOL/BONK) vengono esclusi da current_allocs
tf_allocs = [a for a in current_allocs if a.get("managed_by") == "trend_follower"]
tf_total_capital = float(config.get("tf_budget", 100))

decisions = decide_allocations(
    coins, tf_allocs, coin_tiers,
    exchange_filters, config, tf_total_capital,
)
```

**Perché:** `current_allocs` include i 3 bot manuali ($500 totale). Passando solo `tf_allocs` e `tf_budget=$100`, `decide_allocations` vede il capitale e i grid corretti per TF. I coin manuali non vengono mai considerati per DEALLOCATE.

### 2c. Aggiungere chiamata `apply_allocations` nel main loop

Trova questo blocco (subito dopo il loop `send_tf_decision`):

```python
            for d in decisions:
                if d["action_taken"] in ("ALLOCATE", "DEALLOCATE"):
                    send_tf_decision(notifier, d, is_shadow=config.get("dry_run", True))

            scan_interval = config.get("scan_interval_hours", 4)
```

Inserisci tra i due blocchi:

```python
            for d in decisions:
                if d["action_taken"] in ("ALLOCATE", "DEALLOCATE"):
                    send_tf_decision(notifier, d, is_shadow=config.get("dry_run", True))

            # Apply allocations se live mode
            if not config.get("dry_run", True):
                apply_allocations(supabase, decisions, config)

            scan_interval = config.get("scan_interval_hours", 4)
```

### 2d. Fix cosmetico — scan report usa numeri TF-only

Nel file trova `send_scan_report` (righe ~210-263). Due cambi:

Riga `max_grids = config.get("max_active_grids", 5)` → sostituire con:
```python
max_grids = config.get("tf_max_coins") or config.get("max_active_grids", 5)
```

Alla chiamata a `send_scan_report` nel main loop trova:
```python
send_scan_report(notifier, coins, current_allocs, config)
```
Sostituisci con:
```python
send_scan_report(notifier, coins, tf_allocs, config)
```

(`tf_allocs` è già definito nella sez. 2b.) Così il contatore "Active grids" e "Capital deployed" mostrano solo il mondo TF, coerente con la logica decisionale.

### 2e. Fix cosmetico — messaggio di avvio TF

Nel messaggio di avvio esistente, trova la riga:
```python
f"Max grids: {config.get('max_active_grids', 5)}"
```
Sostituisci con:
```python
f"Max grids: {config.get('tf_max_coins') or config.get('max_active_grids', 5)}"
```

### 2f. Aggiungere messaggio di avvio LIVE

Trova il messaggio di avvio TF (già esistente). Subito dopo, aggiungi:

```python
    if not config.get("dry_run", True):
        notifier.send_message(
            f"⚡ <b>TF LIVE MODE</b>\n"
            f"Budget: ${config.get('tf_budget', 100):.0f} | Max coins: {config.get('tf_max_coins', 2)}"
        )
```

---

## 3. Flip `dry_run` — eseguito da Max dopo il deploy

Dopo aver verificato il deploy, Max esegue manualmente:

```sql
UPDATE trend_config SET dry_run = false WHERE id = '04b4a3d2-a4ae-4fb1-8381-dcad370018f0';
```

**CC non esegue questa query.**

---

## Test — PRE flip (dry_run=true ancora)

```bash
cd /Volumes/Archivio/bagholderai
source venv/bin/activate
python3.13 -m bot.trend_follower.trend_follower
```

- [ ] Nessun errore di import
- [ ] `apply_allocations` NON viene chiamata (dry_run=true)
- [ ] Il Telegram scan report mostra `Active grids: 0/2` (tf_allocs filtrate) invece di `3/5`
- [ ] Il capitale nel report è `$100` non `$500`

## Test — POST flip (Max esegue SQL)

- [ ] Telegram riceve: "⚡ TF LIVE MODE — Budget: $100 | Max coins: 2"
- [ ] Dopo la prima scansione, verifica:

```sql
SELECT symbol, is_active, managed_by, capital_allocation, buy_pct, sell_pct
FROM bot_config ORDER BY managed_by, symbol;
```

- [ ] BTC/SOL/BONK: `managed_by='manual'` — invariati ✅
- [ ] Nuovi coin TF: `managed_by='trend_follower'`, `capital_allocation <= 100` ✅
- [ ] L'orchestrator spawna un grid bot per il nuovo coin entro 30s ✅
- [ ] Se TF decide DEALLOCATE → `pending_liquidation=true`, grid bot si ferma ✅

---

## Scope rules

- **NON modificare** scanner, classifier, o il resto del main loop oltre quanto indicato
- **NON toccare** `bot_config` per BTC/SOL/BONK — la whitelist è inviolabile
- **NON eseguire** il flip `dry_run=false` — lo fa Max
- Push a GitHub quando deploy completo e test pre-flip passato
- Stop quando done

---

## Commit format

```
feat(trend-follower): live mode — tf_budget/tf_max_coins, apply_allocations
```
