# Session Report — 2026-04-06

## Bug #1: Vendita SOL bloccata (bot non vendeva fino al riavvio)

### Sintomo
Il bot SOL/USDT non eseguiva la vendita nonostante il prezzo avesse raggiunto la soglia corretta. La vendita è avvenuta solo dopo il riavvio manuale del bot (e in quel momento ha venduto 4 lotti in blocco, tutti fermi dalla sessione precedente).

### Causa identificata
Divergenza di stato in-memory: `_pct_open_positions` (la coda FIFO dei lotti aperti) risultava vuota, mentre `state.holdings` era > 0. Il sell check in `_check_percentage_and_execute` verifica `if self.state.holdings > 0 and self._pct_open_positions:` — se la lista è vuota, fallisce silenziosamente senza nessun log, bloccando tutte le vendite per l'intera sessione. Al riavvio, `init_percentage_state_from_db()` ricostruisce correttamente lo stato dal DB e le vendite partono immediatamente.

### Fix applicato — `bot/strategies/grid_bot.py`

**Self-healing automatico**: prima del sell check, se `holdings > 0` ma `_pct_open_positions` è vuota, il bot logga un warning e chiama `init_percentage_state_from_db()` per risincronizzarsi con il DB senza bisogno di riavvio.

**Log diagnostico**: quando i lotti esistono ma nessuno raggiunge il trigger, viene loggato (livello DEBUG) il prezzo attuale vs il trigger più vicino, con sell_pct e numero di lotti — per diagnosi rapida in futuro.

```python
# Aggiunto prima del sell check esistente:
if self.state.holdings > 0 and not self._pct_open_positions:
    logger.warning(
        f"[{self.symbol}] WARN: holdings={self.state.holdings:.6f} ma _pct_open_positions è vuota. "
        f"Re-init dal DB..."
    )
    self.init_percentage_state_from_db()
```

---

## Bug #2: Dashboard admin — valori di riepilogo apparentemente non aggiornati

### Sintomo
Dopo la vendita SOL, i valori di Portfolio Overview (Total P&L, Skim Reserve) sembravano non aggiornarsi nemmeno dopo reload manuale della pagina.

### Verifica DB
Query diretta su Supabase confermava che i dati erano **corretti e aggiornati**:
- Ultima sell SOL alle 14:52:01 con `realized_pnl = +$0.1946` ✓
- Total P&L (26 sell v3) = `$7.6693` → dashboard mostrava `$7.67` ✓
- Ultimo skim SOL alle 14:52:01 con `amount = +$0.0584` ✓
- Total skim (16 entries) = `$1.9596` → dashboard mostrava `$1.9596` ✓

Il dashboard era corretto. La confusione era dovuta al fatto che il cambiamento (+$0.19 su $7.47) era avvenuto nel breve intervallo tra la notifica Telegram e il refresh automatico (che era a 30s).

### Fix preventivo applicato — `web/admin.html`

**`Promise.all` → `Promise.allSettled`**: se una delle query Supabase fallisce, non blocca più il render. L'errore viene mostrato visivamente nella refresh bar ("⚠ errore caricamento — riprovo") con retry automatico dopo 5s.

**Auto-refresh: 30s → 10s**: ridotto per minimizzare la finestra temporale in cui i dati mostrati sono stale.

```javascript
// Prima: una query fallita bloccava tutto silenziosamente
var results = await Promise.all([...]);

// Dopo: fallimenti parziali visibili + retry automatico
var settled = await Promise.allSettled([...]);
if (failed.length > 0) {
    // mostra errore in UI + retry dopo 5s
}
```

---

## Commit

```
7d5ef20  fix(bot+dashboard): sell self-healing + dashboard resilienza
```

Files modificati:
- `bot/strategies/grid_bot.py`
- `web/admin.html`
