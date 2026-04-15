# INTERN BRIEF — Session 36a: Trend Follower Live Mode

**Date:** April 15, 2026
**Priority:** HIGH — abilita TF autonomy reale
**Prerequisito:** Brief 35b (orchestrator) deployato e funzionante ✅

---

## Context

Il Trend Follower gira già in shadow mode (`dry_run=true`). Scansiona, classifica, decide — ma non scrive nulla su `bot_config`. L'orchestrator è live e gestisce i processi.

Questo brief fa due cose:
1. Implementa `apply_allocations()` nell'allocator — la funzione che scrive su `bot_config`
2. Porta `dry_run=false` in `trend_config` così TF inizia davvero ad agire

**Budget TF:** $100 (già in `trend_config.tf_budget`)  
**Max coin TF:** 2 (già in `trend_config.tf_max_coins`)  
**Whitelist manuale (NON toccare mai):** `['BTC/USDT', 'SOL/USDT', 'BONK/USDT']`

---

## Architecture

Nessun nuovo file. Solo modifiche a esistenti:

```
bot/trend_follower/allocator.py    ← ADD apply_allocations()
bot/trend_follower/trend_follower.py ← UNCOMMENT apply_allocations call
trend_config (Supabase)            ← SET dry_run=false
```

---

## 1. `bot/trend_follower/allocator.py`

### 1a. Costante whitelist

All'inizio del file, dopo gli import:

```python
# Symbols managed manually by Max — TF must NEVER touch these
MANUAL_WHITELIST = {"BTC/USDT", "SOL/USDT", "BONK/USDT"}
```

### 1b. Funzione `apply_allocations()`

Aggiungi questa funzione al file:

```python
def apply_allocations(supabase, decisions: list[dict], config: dict) -> None:
    """
    Apply TF allocation decisions to bot_config.
    Called only when dry_run=False.

    ALLOCATE → INSERT or UPDATE bot_config with is_active=True, managed_by='trend_follower'
    DEALLOCATE → SET pending_liquidation=True (grid_runner handles forced sell + stop)

    NEVER touches symbols in MANUAL_WHITELIST.
    """
    logger = logging.getLogger("bagholderai.trend.allocator")

    for d in decisions:
        symbol = d["symbol"]
        action = d["action_taken"]

        # Safety: never touch manual bots
        if symbol in MANUAL_WHITELIST:
            logger.warning(f"[ALLOCATOR] Skipping {symbol} — in MANUAL_WHITELIST")
            continue

        if action == "ALLOCATE":
            snapshot = d.get("config_snapshot", {})
            capital = snapshot.get("capital_allocation", 0)

            if capital <= 0:
                logger.warning(f"[ALLOCATOR] {symbol}: capital=0, skipping ALLOCATE")
                continue

            # Grid params: reasonable defaults for TF-managed bots
            # Signal-based tuning is a future brief
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

            row = {
                "symbol": symbol,
                "is_active": True,
                "managed_by": "trend_follower",
                "pending_liquidation": False,
                "capital_allocation": capital,
                "buy_pct": buy_pct,
                "sell_pct": sell_pct,
                "grid_mode": "percentage",
                "config_version": "v3",
            }

            try:
                # Check if row exists
                existing = supabase.table("bot_config").select("symbol").eq("symbol", symbol).execute()

                if existing.data:
                    # UPDATE — only update TF-relevant fields, don't wipe manual config
                    supabase.table("bot_config").update({
                        "is_active": True,
                        "managed_by": "trend_follower",
                        "pending_liquidation": False,
                        "capital_allocation": capital,
                        "buy_pct": buy_pct,
                        "sell_pct": sell_pct,
                        "grid_mode": "percentage",
                    }).eq("symbol", symbol).execute()
                    logger.info(f"[ALLOCATOR] UPDATED {symbol} in bot_config (${capital:.0f})")
                else:
                    # INSERT — new symbol TF wants to trade
                    supabase.table("bot_config").insert(row).execute()
                    logger.info(f"[ALLOCATOR] INSERTED {symbol} in bot_config (${capital:.0f})")

            except Exception as e:
                logger.error(f"[ALLOCATOR] Failed to apply ALLOCATE for {symbol}: {e}")

        elif action == "DEALLOCATE":
            # Don't delete — set pending_liquidation=True
            # grid_runner will force-sell + set is_active=False + clear flag
            try:
                # Only deallocate if managed by TF (safety check)
                existing = supabase.table("bot_config").select(
                    "symbol, managed_by"
                ).eq("symbol", symbol).execute()

                if existing.data:
                    row = existing.data[0]
                    if row.get("managed_by") != "trend_follower":
                        logger.warning(
                            f"[ALLOCATOR] {symbol}: managed_by={row.get('managed_by')}, "
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

        # SKIP / HOLD / other actions → no write
```

---

## 2. `bot/trend_follower/trend_follower.py`

### 2a. Import logging nel modulo allocator

Assicurati che `allocator.py` abbia l'import di `logging` in cima al file. Se non c'è, aggiungilo:

```python
import logging
```

### 2b. Import `apply_allocations` nel trend_follower

Trova la riga degli import dall'allocator:

```python
from bot.trend_follower.allocator import decide_allocations
```

Sostituisci con:

```python
from bot.trend_follower.allocator import decide_allocations, apply_allocations
```

### 2c. Sblocca la chiamata nel main loop

Nel main loop, trova questo blocco commentato (esiste già):

```python
# If NOT shadow mode, write to bot_config (FUTURE — not in this brief)
# if not config["dry_run"]:
#     apply_allocations(supabase, decisions)
```

Sostituisci con:

```python
# Apply allocations if live mode
if not config.get("dry_run", True):
    apply_allocations(supabase, decisions, config)
```

### 2d. Update messaggio Telegram di avvio

Trova il messaggio di avvio (già esistente):

```python
notifier.send_message(
    f"🧠 <b>Trend Follower started</b>\n"
    f"Mode: {'SHADOW (dry run)' if config.get('dry_run') else 'LIVE'}\n"
    ...
)
```

Assicurati che in LIVE mode il messaggio sia visivamente distinto. Se non lo è già, aggiungi una riga:

```python
if not config.get("dry_run", True):
    notifier.send_message(
        "⚡ <b>TF is in LIVE MODE</b> — will write to bot_config and start real grids"
    )
```

---

## 3. Supabase — flip `dry_run`

Dopo aver deployato il codice su GitHub, Max eseguirà manualmente questa query:

```sql
UPDATE trend_config SET dry_run = false WHERE id = '04b4a3d2-a4ae-4fb1-8381-dcad370018f0';
```

**NON eseguire questa query tu — la esegue Max dopo aver verificato il deploy.**

---

## Files to modify

| File | Action | Description |
|------|--------|-------------|
| `bot/trend_follower/allocator.py` | MODIFY | Add `MANUAL_WHITELIST` + `apply_allocations()` |
| `bot/trend_follower/trend_follower.py` | MODIFY | Import + call `apply_allocations` when not dry_run |

---

## Test (dry run check — PRIMA del flip)

```bash
cd /Volumes/Archivio/bagholderai
source venv/bin/activate
python3.13 -m bot.trend_follower.trend_follower
```

Con `dry_run=true` ancora attivo:
- [ ] Il codice parte senza errori di import
- [ ] `apply_allocations` NON viene chiamata (dry_run=true)
- [ ] Comportamento identico a prima

## Test (post flip — Max esegue la query SQL)

Dopo `dry_run=false`:

- [ ] Telegram riceve: "⚡ TF is in LIVE MODE"
- [ ] Dopo la prima scansione, se TF decide ALLOCATE su un coin non in whitelist → riga inserita/aggiornata in `bot_config`
- [ ] Verifica con:

```sql
SELECT symbol, is_active, managed_by, capital_allocation, buy_pct, sell_pct
FROM bot_config ORDER BY managed_by;
```

- [ ] BTC/SOL/BONK hanno `managed_by='manual'` — invariati
- [ ] Eventuali nuovi coin hanno `managed_by='trend_follower'`
- [ ] L'orchestrator lancia un grid bot per il nuovo coin entro 30s (già funziona — legge `is_active`)
- [ ] Se TF decide DEALLOCATE → `pending_liquidation=true` sul coin, grid bot si ferma

---

## Scope rules

- **NON modificare** la logica di scanner, classifier, o il loop principale oltre quanto indicato
- **NON toccare** `bot_config` per BTC/SOL/BONK — la whitelist è inviolabile
- **NON eseguire** la query `dry_run=false` — la esegue Max
- Push a GitHub quando il codice è pronto
- Stop quando il codice è deployato e il test pre-flip è passato

---

## Commit format

```
feat(trend-follower): live mode — apply_allocations writes to bot_config
```
