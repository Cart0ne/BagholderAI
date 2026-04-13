# INTERN BRIEF — Session 15 Chiusura: Code Fixes + File Updates

## Task 1: Change REPORT_HOUR from 21 to 20

**File:** `bot/grid_runner.py`

Find:
```python
REPORT_HOUR = 21  # Send daily report at 21:00
```

Replace with:
```python
REPORT_HOUR = 20  # Send daily report at 20:00
```

## Task 2: Received breakdown in terminal status

**File:** `bot/grid_runner.py`, function `_print_status()`

Find the line:
```python
logger.info(f"  Received:     ${status['received']:,.2f}")
```

Replace with:
```python
cost_basis = status['received'] - status.get('realized_pnl', 0)
logger.info(f"  Received:     ${status['received']:,.2f} (cost basis: ${cost_basis:.2f} + profit: ${status.get('realized_pnl', 0):.4f})")
```

Note: `realized_pnl` should already be in the status dict from `get_status()`. If the key doesn't exist, `.get()` defaults to 0.

## Task 3: Fix BONK $0.00 on dashboard

**File:** `web/index.html`

The dashboard formats prices with `.toFixed(2)` which shows `$0.00` for micro-prices like BONK ($0.0000059). 

Find all places where center price, range, or asset prices are formatted. Replace the formatting logic with a function like:

```javascript
function fmtPrice(p) {
  if (p === 0) return '$0.00';
  if (p >= 1) return '$' + p.toFixed(2);
  if (p >= 0.01) return '$' + p.toFixed(4);
  if (p >= 0.0001) return '$' + p.toFixed(6);
  return '$' + p.toFixed(8);
}
```

Use `fmtPrice()` instead of `'$' + value.toFixed(2)` everywhere prices are displayed. This matches the Python `fmt_price()` logic already used in the bot.

## Task 4: Update project files

Copy these files into the repo:

1. `Development_Diary_Session15.docx` → project root (or wherever diaries live)
2. `Roadmap_v1_15.docx` → project root
3. `diary_entries.json` → project root (replaces the existing one)
4. `blueprint.html` → `web/blueprint.html`

## Task 5: Update roadmap.html

**File:** `web/roadmap.html`

Update the `ROADMAP` JavaScript const to reflect the new tasks from Roadmap v1.15. New completed tasks to add:

- 1.26: Pagina Blueprint pubblica sul sito ✅ (S15)
- 1.36: Trigger anti-duplicati trade (5s window) ✅ (S15)
- 1.37: Trigger anti-short-sell (DB-level) ✅ (S15)
- 1.38: Verifica holdings/cash su ogni trade Telegram ✅ (S15)
- 1.39: Uniformizzazione ambienti (MacBook Air + Mac Mini) ✅ (S15)

New open tasks:
- 1.40: Fix BONK $0.00 su dashboard (micro-prezzi) ❌
- 1.41: REPORT_HOUR 21→20 ❌
- 1.42: Received breakdown nel terminale ❌
- 1.43: Migrazione diary_entries da JSON a Supabase ❌

After editing, validate the JS const:
```bash
node -e "$(grep -A 999 'const ROADMAP' web/roadmap.html | grep -B 999 '^];' | head -200)"
```

## Commit message

```
chore: S15 close — report hour, terminal breakdown, BONK fix, blueprint, roadmap update
```

## Rules

No external connections. No launching the bot. Stop when done.
