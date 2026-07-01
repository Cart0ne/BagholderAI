# Brief S110c — usdt-to-usdc — 2026-06-27

## Contesto

La normativa EU/EEA MiCA richiede l'uso di stablecoin regolamentate. USDT (Tether) non è conforme; USDC (Circle) sì. Tutti i pair di trading devono passare da *USDT a *USDC. Questo vale indipendentemente dall'exchange (Binance, Kraken, altro).

## Scope

Migrare l'intero sistema da USDT a USDC come stablecoin di denominazione.

## Cosa fare

1. **Audit completo:** trovare TUTTI i punti nel codice, config, dashboard e test che referenziano USDT esplicitamente (grep largo: `USDT`, `usdt`, `_USDT`, pair symbols).
2. **Verificare disponibilità pair USDC** sull'exchange target (Binance E Kraken, per entrambi gli scenari) per tutte le coin che potremmo tradare: BTC/USDC, SOL/USDC, ETH/USDC, BONK/USDC e qualsiasi coin che TF potrebbe selezionare da Tier 1-2.
3. **bot_config:** i symbol (es. `BTCUSDT` → `BTCUSDC`). Verificare se il cambio è solo config o se c'è codice hardcoded.
4. **Dashboard (tutte):** stringhe di display che mostrano "USDT" → "USDC". Homepage pubblica, admin.html, grid.html, tf.html.
5. **Reconciliation script** (`scripts/reconcile_binance.py`): verifica che i pair USDC funzionino.
6. **NewsKeeper / Sentinel / Sherpa:** verificare se referenziano USDT da qualche parte.
7. **Fee structure:** verificare se le fee su pair USDC differiscono da USDT sugli exchange target. Documentare differenze.
8. **Stablecoin per il cash:** il bot tiene cassa in USDT? Deve diventare USDC. Verificare come l'exchange gestisce la conversione (Binance ha convert, Kraken ha pair USDT/USDC).

## Cosa NON fare

- NON cambiare logica di trading, soglie, parametri. Solo la denominazione.
- NON toccare i dati storici in DB (restano USDT, sono testnet/paper).
- NON decidere l'exchange — questo brief funziona per entrambi.

## Test checklist

- [ ] Grep per "USDT" nel repo: zero risultati nel codice attivo (i test e dati storici possono restare)
- [ ] Bot si avvia su testnet con pair USDC senza errori
- [ ] Dashboard mostra USDC correttamente
- [ ] Reconciliation gira su pair USDC
- [ ] Fee registrate correttamente

## File OFF-LIMITS

Nessuno — questo brief tocca config e display, non logica di trading.

## Auto-obiezione

I pair USDC possono avere **liquidità inferiore** ai pair USDT, specialmente per coin più piccole (BONK/USDC potrebbe avere un book molto sottile o non esistere affatto su certi exchange). CC deve verificare la profondità del book per ogni pair USDC che intendiamo usare. Se un pair USDC non esiste o ha liquidità insufficiente per una coin, segnalare al CEO — non inventare workaround.

## Sequenza

Può essere eseguito in parallelo con il brief S110d. Idealmente completato PRIMA del go-live mainnet (è un prerequisito infrastrutturale, non un CASO-1 perché era già nella roadmap).
