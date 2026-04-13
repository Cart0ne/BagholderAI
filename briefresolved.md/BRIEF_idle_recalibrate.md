# BRIEF — Idle Recalibrate (holdings > 0)

**Status:** PARCHEGGIATO — da schedulare in una sessione futura
**Origine:** Session 31a (12 aprile 2026) — discussione su SOL fermo 3+ giorni
**Priorità:** MEDIUM — quality of life, non è un bug

---

## Problema

Quando il bot ha holdings > 0 ma il prezzo resta in una "terra di nessuno":
- Non scende abbastanza per triggerare un buy (`-buy_pct%` dal last buy)
- Non sale abbastanza per triggerare un sell (`+sell_pct%` dal lotto)
- L'idle re-entry non scatta perché `holdings > 0`
- Risultato: il bot resta fermo per giorni

## Comportamento attuale

| Stato | Dopo N ore idle | Cosa fa |
|-------|-----------------|---------|
| holdings = 0 | Resetta reference, ricompra a mercato | ✅ funziona |
| holdings > 0 | Niente | ❌ fermo |

## Proposta

Dopo N ore di inattività con holdings > 0, resettare `_pct_last_buy_price` al prezzo corrente. Questo sblocca nuovi buy senza toccare i lotti esistenti (che si vendono sempre in profitto).

### Opzione A (semplice)
Stesso parametro `idle_reentry_hours`, ramo aggiuntivo nel check:
- holdings = 0 → comportamento attuale (force buy)
- holdings > 0 → resetta solo il buy reference (non forza un buy)

### Opzione B (granulare)
Parametro separato `idle_recalibrate_hours` in `bot_config`:
- `idle_reentry_hours` → per holdings = 0
- `idle_recalibrate_hours` → per holdings > 0

## Nota importante

I lotti già aperti NON vengono toccati. Un lotto comprato a $130 si vende solo quando il prezzo arriva a $130 + sell_pct%. Il recalibrate sblocca solo i nuovi acquisti.

## File coinvolti

- `bot/strategies/grid_bot.py` → `_check_percentage_and_execute()`, sezione IDLE RE-ENTRY CHECK
- `config/supabase_config.py` → aggiungere campo se Opzione B
- Supabase `bot_config` → aggiungere colonna se Opzione B
