# INTERN BRIEF 19a — Chiusura Phase 1

**Sessione:** 19
**Data:** 4 aprile 2026
**Priorità:** ALTA — Questi task chiudono Phase 1
**Contesto:** Il brief 18b (campi buy_pct/sell_pct su admin dashboard) è ancora valido e va completato. Questo brief aggiunge i task rimanenti.

---

## Task 1: "Last Shot" Buy (task 1.57)

**Problema:** Quando il cash rimasto scende sotto `capital_per_trade` ma è ancora sopra un minimo utile (es. $5), il bot smette di comprare. Quel cash resta fermo per sempre.

**Dove:** `bot/strategies/grid_bot.py` → `_execute_buy()`

**Logica:**
```python
# Calcolo cash disponibile (esiste già nel codice)
available_capital = max(0.0, self.capital - self.state.total_invested + self.state.total_received)

# Rispetta il reserve floor (campo già esistente in bot_config, attualmente 0%)
reserve = self.capital * (self.reserve_floor_pct / 100)
spendable = available_capital - reserve

# Nuova logica
if spendable >= capital_per_trade:
    actual_cost = capital_per_trade  # buy normale, come adesso
elif spendable >= MIN_LAST_SHOT_USD:
    actual_cost = spendable  # LAST SHOT: compra con quello che hai
else:
    # skip, non vale la pena
    return None
```

**Dettagli implementazione:**
- `MIN_LAST_SHOT_USD = 5.0` come costante in `config/settings.py` → `HardcodedRules`
- L'amount nel token = `actual_cost / current_price`
- Log chiaro: `"LAST SHOT: buying with remaining $X.XX (reduced from standard $Y.YY)"`
- Dopo un last-shot buy il bot è "pieno" — nessun altro buy finché un sell non libera capitale
- NON aggiungere campi a Supabase, è una costante hardcoded

**Test:** Imposta un bot con $25 capital e $10 capital_per_trade. Dopo 2 buy ($20 spesi), il bot deve fare un last-shot buy con i $5 restanti invece di restare fermo.

---

## Task 2: Fix errori Binance API (task 1.58)

**Problema:** Errore ricorrente nel terminale su tutte e tre le monete:
```
12:40:53 [bagholderai.runner] ERROR: Error in main loop: binance GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT
```
Non è rate limiting (usiamo ~12 weight/min su un limite di 6000/min). Sono timeout di rete / errori transitori Binance.

**Tre fix:**

### Fix 2a: Retry con backoff in `fetch_price()`

File: `bot/grid_runner.py`

Sostituire:
```python
def fetch_price(exchange, symbol: str) -> float:
    ticker = exchange.fetch_ticker(symbol)
    return ticker["last"]
```

Con:
```python
def fetch_price(exchange, symbol: str, max_retries: int = 3) -> float:
    """Fetch current price with retry logic."""
    for attempt in range(max_retries):
        try:
            ticker = exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                logger.warning(
                    f"Price fetch failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                raise  # il main loop gestisce l'errore
```

### Fix 2b: Abilitare rate limiter ccxt

File: `bot/exchange.py` → `create_exchange()`

Aggiungere `enableRateLimit: True` nella configurazione ccxt:
```python
exchange = ccxt.binance({
    'apiKey': ...,
    'secret': ...,
    'enableRateLimit': True,  # AGGIUNGERE QUESTO
    ...
})
```

### Fix 2c: (opzionale, solo se 2a+2b non bastano) Endpoint più leggero

Se dopo 2a e 2b l'errore persiste, valutare di sostituire `fetch_ticker` con una chiamata diretta a `/api/v3/ticker/price` che restituisce solo `{"symbol":"BTCUSDT","price":"84000.50"}` — meno dati, risposta più veloce. Ma provare prima con 2a+2b.

---

## Task 3: Logger.warning su silent failures Telegram (task 1.30)

**Problema:** Se l'invio Telegram fallisce silenziosamente (timeout, errore API Telegram, bot bloccato), il runner continua senza segnalare nulla. I failure vanno loggati.

**Dove:** `utils/telegram_notifier.py`

**Cosa fare:** Verificare che ogni metodo della classe `SyncTelegramNotifier` loggi un warning quando il return value è `False` o quando cattura un'eccezione. Pattern:

```python
def send_trade_alert(self, trade: dict) -> bool:
    try:
        result = _run_async(self._async.send_trade_alert(trade))
        if not result:
            logger.warning(f"Telegram trade alert failed silently for {trade.get('symbol', '?')}")
        return result
    except Exception as e:
        logger.warning(f"Telegram trade alert exception: {e}")
        return False
```

Applicare lo stesso pattern a TUTTI i metodi sync: `send_message`, `send_trade_alert`, `send_daily_report`, `send_bot_started`, `send_bot_stopped`, `send_grid_reset`, `send_private_daily_report`, `send_public_daily_report`.

**Non deve mai crashare il bot.** Solo warning nel log.

---

## Task 4: Fallback colori per nuovi simboli su dashboard (task 1.34)

**Problema:** La dashboard pubblica (`index.html`) e l'admin (`admin.html`) hanno colori hardcoded per BTC/SOL/BONK. Se aggiungiamo un quarto simbolo, non ha colore e si rompe visivamente.

**Dove:** `web/index.html` e `web/admin.html`

**Cosa fare:** Aggiungere un fallback nel mapping colori. Cercare dove i colori sono definiti per symbol (probabilmente un oggetto/switch) e aggiungere un default:

```javascript
// Esempio di pattern
var COLORS = {
    'BTC/USDT': '#F7931A',
    'SOL/USDT': '#9945FF', 
    'BONK/USDT': '#F5A623'
};

function getColor(symbol) {
    return COLORS[symbol] || '#888888';  // fallback grigio
}
```

Cercare TUTTI i punti dove i colori dipendono dal simbolo e assicurarsi che ci sia sempre un fallback. Controllare sia index.html che admin.html.

---

## IMPORTANTE — Regole operative

1. **Non lanciare il bot.** Mai. Non hai accesso alla produzione.
2. **Non fare connessioni esterne** oltre a quelle strettamente necessarie (Supabase).
3. **Testa localmente** dove possibile.
4. **Quando hai finito, fermati.** Aggiorna memory.md e chiudi.
5. **Il brief 18b è ancora valido** — completalo insieme a questo.
6. **Ordine suggerito:** 18b (admin fields) → Task 3 (Telegram logger) → Task 4 (colori) → Task 2 (Binance fix) → Task 1 (last shot buy)
