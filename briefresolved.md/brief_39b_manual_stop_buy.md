# BRIEF — 39b: Manual bots stop-buy + safety params exposed in UI

**Date:** 2026-04-18
**Priority:** MEDIUM — feature request, not a fire
**Prerequisito:** 39a deployato ✅
**Target branch:** `main` (push diretto)
**Deploy:** Mac Mini via git pull + restart orchestrator

---

## Problema

I bot manuali (BTC/SOL/BONK) operano con Strategy A — `never sell at loss`. È la scelta giusta: sono asset scelti dal CEO, li vogliamo tenere, mai crystallizzare perdite.

Ma Strategy A copre solo l'**uscita**. Sull'**entrata** il GRID è impaziente: compra ad ogni dip, meccanicamente, finché ha capitale. In un bear prolungato questo produce un problema:

**Esempio reale (BONK, 18 apr):** prezzo in discesa, unrealized attuale ~-3% della allocation ($5.80 su $200 circa). Se BONK continua a scendere, il bot continuerà a comprare lot dopo lot fino a esaurire `capital_allocation`. Ogni buy aggiuntivo:

1. Blocca più capitale sotto il livello di sell originale
2. Sposta `avg_buy_price` giù ma aumenta le `holdings` totali
3. Richiede un rimbalzo più lungo prima che anche un lot solo torni in profit
4. In caso di bear prolungato, congela il 100% dei $X allocati senza possibilità di uscire (Strategy A blocca la sell)

Il CEO vuole la coppia simmetrica di Strategy A: **quando il drawdown totale è grave, smetti di comprare**. Il capitale residuo resta disponibile, i lot già aperti continuano a essere "vendibili in profit" via Strategy A normale. Quando il prezzo risale abbastanza da liberare almeno un lot (sell in profit), il ciclo è digerito e si ricomincia a comprare.

Questo non è uno stop-loss — non vende mai in perdita. È uno **stop-buy**: blocca solo nuove entrate sotto una certa soglia di drawdown.

---

## Principio di design

- **Solo bot manuali** (`managed_by IS NULL` o diverso da `'trend_follower'`). I bot TF hanno già lo stop-loss di 39a: se perdono troppo vengono liquidati, quindi non gli serve uno stop-buy.
- **Drawdown sull'intera posizione**, non per-lot. Coerente con lo stop-loss TF di 39a.
- **Isteresi event-based, non price-based**. Lo stop-buy si disattiva solo quando una sell in profit scatta naturalmente (Strategy A digerisce il ciclo). Questo evita whipsaw: un rimbalzo parziale del prezzo non riattiva i buy, servono vendite reali.
- **Parametro per-coin**, non globale. BTC oscilla diversamente da BONK.
- **0 = disabilitato**. Stesso pattern di `profit_target_pct`.

---

## Fix 1 — Logica stop-buy in `grid_bot.py`

### Nuovo attributo

Il `GridBot` riceve dal `grid_runner` un nuovo attributo:

```python
self.stop_buy_drawdown_pct = cfg.get('stop_buy_drawdown_pct', 15)
```

E mantiene un flag di stato in memoria:

```python
self._stop_buy_active = False  # set in check_percentage_grid, reset on profitable sell
```

### Check in `check_percentage_grid` (stessa funzione dove 39a ha messo lo stop-loss)

Aggiungi DOPO il blocco stop-loss TF (non in alternativa):

```python
# Stop-buy check for MANUAL bots — evaluate on entire position
if (self.managed_by != "trend_follower"
    and self.stop_buy_drawdown_pct > 0
    and self.state.holdings > 0
    and self.state.avg_buy_price > 0):

    unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
    threshold = -(self.capital * self.stop_buy_drawdown_pct / 100)

    if unrealized <= threshold and not self._stop_buy_active:
        logger.warning(
            f"[{self.symbol}] STOP-BUY TRIGGERED: unrealized ${unrealized:.2f} "
            f"≤ -{self.stop_buy_drawdown_pct}% of allocation ${self.capital:.2f} "
            f"(threshold: ${threshold:.2f}). New buys blocked until profitable sell."
        )
        self._stop_buy_active = True
```

### Gate nel buy path

Nel metodo che esegue i buy percentuali (es. `_execute_percentage_buy` o equivalente), aggiungi come PRIMA cosa:

```python
if self._stop_buy_active:
    logger.info(
        f"[{self.symbol}] BUY BLOCKED: stop-buy active "
        f"(drawdown > {self.stop_buy_drawdown_pct}% of allocation). "
        f"Waiting for profitable sell to reset."
    )
    return None
```

### Reset event-based nel sell path

Nel metodo che esegue le sell (es. `_execute_percentage_sell`), DOPO che la sell va a buon fine e `realized_pnl > 0`:

```python
if realized_pnl > 0 and self._stop_buy_active:
    self._stop_buy_active = False
    logger.info(
        f"[{self.symbol}] STOP-BUY RESET: profitable sell ${realized_pnl:.2f} "
        f"cleared the block. Buys re-enabled."
    )
```

### Boot reconstruction

Al boot, il flag `_stop_buy_active` è sempre `False`. Lascia che sia il primo ciclo di `check_percentage_grid` a ricalcolarlo dallo stato corrente (holdings + avg_buy_price + current_price). Non serve persistenza in DB.

---

## Fix 2 — Schema DB

```sql
-- Parametro per-coin, solo per bot manuali (ma presente su tutte le righe per uniformità)
ALTER TABLE bot_config ADD COLUMN stop_buy_drawdown_pct numeric DEFAULT 15;

-- Backfill: tutti i bot esistenti ricevono 15 di default (default ALTER applica, ma esplicito per chiarezza)
UPDATE bot_config SET stop_buy_drawdown_pct = 15 WHERE stop_buy_drawdown_pct IS NULL;
```

Default 15% per TUTTI i bot. Per i TF il valore è irrilevante (la logica non legge il campo se `managed_by = 'trend_follower'`), ma tenerlo uniforme semplifica la UI.

---

## Fix 3 — Admin UI: sezione "⚠️ Safety" per ogni coin manuale

### File: `web/admin.html`

In ogni coin card (BTC/SOL/BONK), aggiungi una NUOVA sezione sotto la `Percentage Grid` esistente, chiamata `⚠️ Safety`.

### Layout

Usa lo stesso stile di `param-group-label` e `config-grid` già presente. Il label deve essere visivamente distinto — colore leggermente ambrato/giallo per suggerire "roba seria".

```javascript
// Dentro il rendering della coin card, dopo il blocco 'Percentage Grid':
'<div class="param-group-label safety-label">⚠️ Safety</div>' +
'<div class="config-grid">' +
  configField(short, 'stop_buy_drawdown_pct', 'Stop-buy drawdown %', cfg.stop_buy_drawdown_pct) +
'</div>' +
```

### Stile CSS per `.safety-label`

Aggiungi in `<style>`:

```css
.param-group-label.safety-label {
  color: #eab308;  /* giallo warning, già usato nel sito */
}
```

### Sublabel (riga descrittiva sotto il campo)

Seguendo il pattern già usato in `session32f` (MIN PROFIT %, sublabel helper text):

```
Stop-buy drawdown %
Blocks NEW buys when total unrealized loss exceeds this % of allocation.
Existing lots unaffected (Strategy A still applies). Re-enables after
first profitable sell. Set 0 to disable.
```

### Behavior

- Input libero (tipo text con `inputmode="decimal"`, come gli altri)
- Save standard via bottone "Save changes" esistente
- Scrive su `bot_config.stop_buy_drawdown_pct`
- Logga in `config_changes_log` come ogni altro parametro

---

## Fix 4 — TF dashboard: parametri editabili per safety TF

### File: `web/tf.html`

Oggi `tf.html` è sola-lettura. Va esteso con editing per due parametri già esistenti in `trend_config` (da 39a) ma non editabili da UI.

### Dove collocarli

Nuova sezione in fondo alla pagina (sotto "Recent trades"), prima del refresh bar. Titolo: `⚠️ TF Safety parameters`.

### Parametri da esporre

```
tf_stop_loss_pct        — Force-sell threshold. Default 10. Current: <value from DB>
                          Sublabel: "TF bots force-sell when unrealized loss
                          exceeds this % of allocation. Applies only to
                          TF-managed bots, never to manual."

scan_interval_hours     — TF scan frequency. Default 1. Current: <value from DB>
                          Sublabel: "How often the TF evaluates rotation
                          opportunities. Lower = faster reaction to bearish
                          signals but more API calls."
```

### Implementazione

Riusa lo stesso pattern di `admin.html` per gli input + save. In particolare:

1. Fetch dei valori da `trend_config` (singola riga, la LIMIT 1 che già usa)
2. Render come input text con `inputmode="decimal"`
3. Bottone "Save TF params" che fa `PATCH /rest/v1/trend_config?id=eq.<id>` con il body aggiornato
4. Logga in `config_changes_log` manualmente (insert con `changed_by: 'manual-ceo'`, symbol NULL per config globali, parameter/old_value/new_value)

### Password gate

`tf.html` ha già SHA-256 password gate come `admin.html`. Nessuna aggiunta, basta che il save avvenga dopo login.

### NO campi da toccare in questa sessione

- `dry_run`, `trend_follower_enabled` — rimangono read-only (sono toggle delicati, brief separato se servirà)
- `tf_budget`, `tf_max_coins` — già modificabili in altro contesto, out of scope

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/strategies/grid_bot.py` | Stop-buy check in `check_percentage_grid`; gate nel `_execute_percentage_buy`; reset in `_execute_percentage_sell` |
| `bot/grid_runner.py` | Passare `stop_buy_drawdown_pct` al `GridBot` constructor (leggerlo da `bot_config`) |
| `web/admin.html` | Nuova sezione "⚠️ Safety" per BTC/SOL/BONK + CSS giallo + sublabel descrittiva |
| `web/tf.html` | Nuova sezione "⚠️ TF Safety parameters" editabile (tf_stop_loss_pct, scan_interval_hours) |
| DB (`bot_config`) | `ALTER TABLE ADD COLUMN stop_buy_drawdown_pct numeric DEFAULT 15` |

## Files da NON toccare

- `config/settings.py` — Strategy A resta invariata
- `reserve_ledger` — nessun impatto (lo stop-buy non tocca le sell, solo le buy)
- Logica TF esistente (39a) — nessuna modifica
- `index.html` — la homepage pubblica non mostra i parametri safety

---

## Test pre-deploy

### Unit test logica stop-buy
- [ ] Bot manuale (managed_by IS NULL) con capital=$200, holdings=10, avg_buy=$100, current_price=$83 → unrealized -$170, threshold -$30 (15%) → STOP-BUY TRIGGERED
- [ ] Stesso bot, current_price=$95 → unrealized -$50, threshold -$30 → no trigger
- [ ] Bot TF con stesso scenario → stop-buy NOT checked (ramo if skippato)
- [ ] Bot manuale con `stop_buy_drawdown_pct = 0` → never triggers (disabilitato)
- [ ] `_stop_buy_active = True` → qualsiasi buy ritorna None con log "BUY BLOCKED"
- [ ] `_stop_buy_active = True` → sell in profit ($5 realized) → flag resetta a False, log "STOP-BUY RESET"
- [ ] `_stop_buy_active = True` → sell in profit $0 (pareggio tecnico) → flag NON resetta (serve profit > 0)

### Integration test
- [ ] Simulare sequenza BONK: buy a $0.0000057, price scende progressivamente a $0.0000046 (-19%) → stop-buy triggered
- [ ] Price rimbalza a $0.0000050 (-12%, sopra threshold ma sotto avg) → buy resta bloccato (event-based, no sell in profit scattata)
- [ ] Price sale a $0.0000058 → lot venduto in profit → flag reset → nuovo buy al prossimo ciclo se trigger percentuale soddisfatto

### UI test admin
- [ ] La sezione "⚠️ Safety" appare sotto BTC/SOL/BONK
- [ ] Label giallo visibile
- [ ] Campo `stop_buy_drawdown_pct` modificabile, save funziona, scrive in `bot_config`
- [ ] Change loggato in `config_changes_log` con parameter='stop_buy_drawdown_pct'
- [ ] Valore di default 15 visibile al primo load

### UI test tf.html
- [ ] Sezione "⚠️ TF Safety parameters" appare in fondo
- [ ] `tf_stop_loss_pct` e `scan_interval_hours` modificabili
- [ ] Save scrive su `trend_config` e logga in `config_changes_log`
- [ ] Password gate impedisce il save senza auth

---

## Test post-deploy

- [ ] Controlla che BONK attuale (a -3% circa) NON sia in stop-buy (15% è ancora lontano)
- [ ] Monitorare log `grid_runner`: nessun "STOP-BUY TRIGGERED" spurio nelle prime ore
- [ ] Nessun impatto sui bot TF (MOVR/TST o chi sarà attivo al deploy)
- [ ] Cambiare via admin `stop_buy_drawdown_pct = 50` per BONK → verificare che il valore arrivi al bot entro il config refresh (300s)
- [ ] Cambiare via tf.html `tf_stop_loss_pct` da 10 a 12 → verificare log `config_changes_log`

---

## Edge cases

1. **Stop-buy + stop-loss contemporanei (impossibile per design)**: i bot TF non leggono stop-buy, i bot manuali non hanno stop-loss. Mutuamente esclusivi per `managed_by`.

2. **Holdings = 0 (bot appena allocato o appena liquidato)**: `if holdings > 0` skippa il check → stop-buy non può attivarsi. Il primo buy parte normale. Corretto.

3. **Stop-buy attivo, bot riavviato**: il flag `_stop_buy_active` non persiste. Al primo ciclo post-boot, se le condizioni sono ancora soddisfatte (holdings > 0 + unrealized sotto threshold), il flag si riattiva da solo. Log apparirà come se fosse un nuovo trigger — accettabile.

4. **Stop-buy attivo mentre scatta `idle_reentry_hours`**: idle re-entry riallinea il `last_buy_price` al prezzo corrente. Questo non ha effetto sullo stop-buy (che è calcolato su avg_buy_price, non last_buy_price). Lo stop-buy rimane attivo — corretto.

5. **Modifica a caldo di `stop_buy_drawdown_pct` via admin**: alla prossima lettura config (300s), il bot legge il nuovo valore. Il flag corrente NON viene resettato automaticamente — continuerà finché una sell in profit non scatta. Coerente con event-based design.

6. **Flash crash -30% in 5 minuti**: stop-buy trigger al primo ciclo dopo il crash. Nessun buy eseguito nel crash. Se il prezzo risale subito senza vendite, stop-buy resta attivo finché una sell scatta. Potenzialmente il capitale resta inutilizzato fino al recovery completo. Accettabile: è il comportamento richiesto dal CEO.

7. **`stop_buy_drawdown_pct` settato a 5 (molto stretto)**: trigger facile, molti cicli di "buy blocked". Scelta consapevole del CEO via admin — il sistema non si mette a protestare.

---

## Interazione con brief precedenti

- **39a (TF stop-loss)**: indipendente. I due meccanismi vivono su bot diversi (`managed_by != 'trend_follower'` vs `== 'trend_follower'`). Stesso calcolo drawdown, azione opposta (block buy vs force sell).
- **32f (profit_target_pct)**: indipendente. Il profit_target_pct blocca le sell, lo stop-buy blocca le buy. Speculari ma ortogonali.
- **Idle re-entry**: nessun conflitto (vedi edge case 4).
- **Reserve ledger / skim**: nessun impatto (lo skim avviene solo su sell, il stop-buy tocca solo buy).

---

## Calibrazione default — nota per il CEO

Default 15% è un **punto di partenza arbitrario**, non ottimizzato. La logica:

- Troppo stretto (5-10%): stop-buy scatta spesso, molto capitale congelato
- Troppo largo (25%+): il sistema protegge solo in scenari estremi
- 15% cattura circa il bear "medio" delle altcoin (correzione salutare non è bear)

Dopo 2-4 settimane di osservazione, il CEO può calibrare per-coin via admin senza deploy. Suggerimento retrospettivo a tre settimane dal deploy: chiedere a CC uno script di backtest che simuli "quale soglia avrebbe prodotto il miglior outcome sui dati storici di BONK/SOL/BTC". Out of scope per questo brief.

---

## Rollback plan

```bash
git revert <commit_hash>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator
```

Rollback riporta comportamento pre-39b (Strategy A pura, compra fino a esaurimento). La colonna DB resta ma inutilizzata — innocua.

Fallback rapido senza rollback: via admin, settare `stop_buy_drawdown_pct = 0` su ogni coin manuale → disabilita lo stop-buy.

---

## Commit format

```
feat(grid-bot): manual bots stop-buy on drawdown + safety params in UI

Manual bots (BTC/SOL/BONK) now block new buys when total unrealized
loss exceeds stop_buy_drawdown_pct (default 15%) of capital_allocation.
Existing lots keep following Strategy A (no forced sell). Block
auto-releases on first profitable sell (event-based hysteresis).

UI: admin.html gets a per-coin Safety section for stop_buy_drawdown_pct.
tf.html becomes editable for TF safety params (tf_stop_loss_pct,
scan_interval_hours) that were already in DB but UI-less since 39a.
```

---

## Out of scope

- Stop-buy per bot TF (non serve, hanno già lo stop-loss di 39a)
- Backtest retrospettivo per calibrare il default (brief separato, dopo 2-4 settimane di dati reali)
- Toggle on/off dedicato per stop-buy (ridondante: 0 = disabilitato)
- Esposizione UI per `dry_run` / `trend_follower_enabled` in tf.html (brief separato se/quando serve)
- Persistenza del flag `_stop_buy_active` in DB (non serve, ricostruibile al boot)

---

## Note finali

Il brief lega 4 modifiche architetturalmente coerenti ma di natura diversa (logica bot + schema DB + due UI). CC può farle in un singolo commit (consigliato) o spezzarle. Se spezzate, l'ordine suggerito è:

1. Schema DB prima (ALTER TABLE)
2. Logica bot dopo (grid_bot.py + grid_runner.py)
3. UI admin in contemporanea o subito dopo
4. UI tf.html per ultima (indipendente, può anche essere commit separato)
