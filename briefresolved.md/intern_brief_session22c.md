# BagHolderAI — Intern Brief Session 22c: Idle Re-Entry
**Data:** 2026-04-06  
**Priorità:** ALTA — BTC e BONK sono CLOSED, capitale fermo, il bot non rientra

---

## Contesto

Quando un bot vende tutti i lotti (holdings = 0), resta in attesa che il prezzo scenda di `buy_pct` sotto `_pct_last_buy_price` per rientrare. Se il prezzo non scende mai (nuova resistenza, trend rialzista), il capitale resta fermo indefinitamente. Serve un meccanismo di timeout che forzi il re-entry dopo N ore di inattività.

**Situazione attuale:** BTC e BONK sono fully closed. Il capitale ($200 + $150) è fermo finché il prezzo non scende — potrebbe non succedere per giorni/settimane.

---

## Prerequisito DB

Già fatto. Colonna `idle_reentry_hours` (numeric, default 24) aggiunta a `bot_config`.

---

## Implementazione

**File:** `bot/strategies/grid_bot.py`

### 1. Tracciare il timestamp dell'ultimo trade

Al boot, in `init_percentage_state_from_db()`, dopo il replay FIFO:
- Leggere il `created_at` dell'ultimo trade v3 per questo symbol dal DB
- Salvarlo in `self._last_trade_time` (datetime UTC)

Ad ogni trade eseguito (buy o sell):
- Aggiornare `self._last_trade_time = datetime.utcnow()`

### 2. Check idle nel loop principale

In `_check_percentage_and_execute()` (o equivalente), DOPO i check buy/sell normali, aggiungere:

```python
# Idle re-entry check
if state.holdings <= 0 and self._last_trade_time:
    idle_hours = cfg.get('idle_reentry_hours', 24)
    if idle_hours > 0:
        elapsed = (datetime.utcnow() - self._last_trade_time).total_seconds() / 3600
        if elapsed >= idle_hours:
            # Re-entry: reset reference and buy at market
            logger.info(
                f"[{symbol}] Idle re-entry after {elapsed:.1f}h: "
                f"resetting reference from ${self._pct_last_buy_price} to ${current_price}"
            )
            self._pct_last_buy_price = current_price
            # Execute first buy at market (same logic as initial "first buy at market")
            self._execute_percentage_buy(symbol, current_price, cfg, state, 
                reason=f"Idle re-entry after {elapsed:.1f}h: new reference ${current_price}")
```

### 3. Leggere il parametro dal config refresh

Il parametro `idle_reentry_hours` deve essere incluso nel SELECT che il config refresh fa su `bot_config`. Verificare che il campo venga letto e passato al check.

### 4. Telegram notification

Quando avviene un idle re-entry, deve mandare una notifica Telegram specifica:
```
⏰ IDLE RE-ENTRY: BONK
After 24.0h idle, new reference: $0.00000586
Buying at market...
```

Seguito dalla notifica BUY standard.

---

## Parametri suggeriti

| Coin | idle_reentry_hours |
|------|--------------------|
| BTC  | 24 |
| SOL  | 24 |
| BONK | 24 |

Non servono UPDATE SQL — il default è già 24 per tutti.

---

## Regole

- L'idle check si attiva SOLO se `holdings == 0` (non per posizioni parziali)
- Se `idle_reentry_hours = 0`, il meccanismo è disabilitato
- Il parametro si legge da `bot_config` e si aggiorna via config refresh (modificabile dall'admin dashboard senza restart)
- Dopo il re-entry, il bot torna a operare normalmente con il nuovo reference

---

## Admin dashboard

Aggiungere il campo `idle_reentry_hours` alla coin card in `admin.html`:
- Label: `Idle re-entry (hours)`
- Posizione: nella sezione "Percentage Grid" dei parametri, dopo `sell_pct`
- Editabile e salvabile come gli altri parametri

---

## Test di validazione

- [ ] Bot con holdings=0 e ultimo trade > 24h fa → esegue buy at market e logga "Idle re-entry"
- [ ] Bot con holdings=0 e ultimo trade < 24h fa → non fa nulla
- [ ] Bot con holdings > 0 → idle check non si attiva mai
- [ ] `idle_reentry_hours = 0` → meccanismo disabilitato
- [ ] Telegram riceve notifica idle re-entry
- [ ] Admin dashboard mostra e salva `idle_reentry_hours`
- [ ] Dopo re-entry, `_pct_last_buy_price` = prezzo corrente, bot opera normalmente
