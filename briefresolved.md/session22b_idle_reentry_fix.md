# BRIEF SESSION 22b — Bugfix & Cosmetic

**Priority:** HIGH (Bug #3), LOW (cosmetic)
**Scope:** Bot code only — NO external connections, NO launching bots, NO unauthorized modifications

---

## Bug #3: Idle Re-Entry Timer Non Funzionante per SOL

### Contesto
Dopo che SOL ha chiuso tutte le posizioni (ultima sell: 2026-04-06 14:52 UTC), il bot avrebbe dovuto rientrare con un "first buy at market" dopo `idle_reentry_hours` (16h), cioè alle ~06:52 UTC del 7 aprile. Non è successo. Il bot è rimasto in stato "CLOSED — awaiting re-entry" per oltre 15 ore, senza alcun log di tentativo.

### Prova che il meccanismo funziona parzialmente
- **BTC** con idle=16h ha rientrato correttamente (ultima sell 10:02 UTC → buy alle 02:22 UTC, +16h ✓)
- **SOL** con idle=1h ha comprato immediatamente dopo il cambio config → il trigger funziona, è il **calcolo del tempo** che fallisce con valori più alti
- La config era corretta nel DB (idle_reentry_hours=16, verificato via query)
- Il bot ha registrato il cambio config (messaggio Telegram: "idle_reentry_hours: 24 → 16")

### Cosa investigare
1. Trovare la funzione che gestisce idle re-entry (probabilmente in `bot/strategies/grid_bot.py`)
2. Capire come calcola `hours_since_last_trade` — possibile problema di timezone (UTC vs locale)
3. Capire perché BTC (sell alle 10:02 UTC) ha funzionato e SOL (sell alle 14:52 UTC) no
4. Verificare se c'è un check booleano prima del timer che potrebbe fallire silenziosamente

### Fix richiesto
1. **Log diagnostico**: quando il bot valuta la condizione di idle re-entry, loggare SEMPRE il risultato (sia True che False), includendo: `last_trade_time`, `hours_elapsed`, `idle_reentry_hours`, `holdings`, e qualsiasi altra condizione valutata
2. **Fix del calcolo**: una volta identificata la causa, correggere la logica del timer
3. **Test**: verificare che con idle=16h il re-entry scatterebbe correttamente per un trade avvenuto 17h fa

---

## Cosmetic: Testo italiano nel Daily Report Telegram

### Problema
Il daily report Telegram contiene "🏦 Reserve Accumulata" — testo in italiano mescolato con il report in inglese.

### Fix richiesto
Sostituire "Reserve Accumulata" con "Accumulated Reserve" (o "Skim Reserve") nel codice che genera il daily report. Cercare nel file che costruisce il messaggio Telegram del daily report (probabilmente in `bot/reports/` o simile).

---

## Regole
- Fermarsi quando i task sono completati
- Nessuna connessione esterna
- Nessun lancio di bot
- Nessuna modifica non autorizzata
- Formato commit: `fix(bot): idle re-entry timer + report language`
