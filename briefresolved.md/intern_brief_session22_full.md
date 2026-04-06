# BagHolderAI — Session 22 Full Recap
**Data:** 2026-04-06

---

## Contesto

Sessione di debug intensiva. I bot erano fermi con 30+ ore di sell mancati. Sono stati risolti 10+ bug in sequenza, alcuni critici, alcuni cosmetic, più un redesign dell'admin dashboard.

---

## Fix 1 — CRITICO: Position reconstruction a boot (mancavano i sell)

**File:** `bot/strategies/grid_bot.py`

**Problema:** `init_percentage_state_from_db()` ricostruiva correttamente la coda FIFO `_pct_open_positions` dal DB, ma non settava `state.holdings`. Il metodo `_check_percentage_and_execute()` controlla `state.holdings > 0` prima di triggerare i sell → con holdings=0 al boot, **zero sell eseguiti** nonostante posizioni aperte su tutti e 3 i bot.

**Fix:** Dopo il replay FIFO, calcola `state.holdings` e `state.avg_buy_price` sommando i lotti aperti.

---

## Fix 2 — TradeLogger crash su `trade_pnl_pct`

**File:** `bot/strategies/grid_bot.py`

**Problema:** `_execute_percentage_sell()` passava `trade_pnl_pct`, `portfolio_realized_pnl`, `portfolio_pnl_pct` a `log_trade()` che non li accetta → crash su ogni sell → trades eseguiti in memoria ma non salvati nel DB.

**Fix:** Aggiunto `_LOG_TRADE_KEYS` allowlist per filtrare i campi prima della chiamata a DB. `trade_pnl_pct` rimane in `trade_data` per Telegram ma non viene passato al logger.

---

## Fix 3 — `min_profit_pct` bloccava i sell di SOL e BONK

**File:** `config/settings.py`

**Problema:** Parametro hardcoded `min_profit_pct` sovrascriveva `sell_pct`:
- SOL: `sell_pct=1%` ma `min_profit_pct=1.5%` → nessun sell fino a +1.5%
- BONK: `sell_pct=1%` ma `min_profit_pct=2%` → nessun sell fino a +2%

**Fix:** Entrambi settati a `0.0` — `sell_pct` da `bot_config` è il solo threshold.

---

## Fix 4 — Race condition sul report giornaliero Telegram

**File:** `db/client.py` + `bot/grid_runner.py`

**Problema:** Due bot in terminal separati mandavano entrambi il report alle 20:00 (doppio messaggio).

**Fix:** `record_daily()` ora usa `INSERT ON CONFLICT DO NOTHING` (`ignore_duplicates=True`). Ritorna `True` solo se è stato il primo a scrivere → solo quel bot manda Telegram.

---

## Fix 5 — Trade P&L % sempre 0.00% su Telegram

**Conseguenza del Fix 2:** rimuovendo `trade_pnl_pct` dal dict, Telegram leggeva `trade.get("trade_pnl_pct", 0)` → sempre 0.

**Fix:** `trade_pnl_pct` rimane nel dict `trade_data` (usato da Telegram), filtrato solo al momento del log DB.

---

## Fix 6 — Reserve label su Telegram senza simbolo coin

**File:** `utils/telegram_notifier.py`

`🏦 Reserve: +$X` → `🏦 BONK Reserve: +$X` per chiarire che il totale è per coin.

---

## Fix 7 — Spam SELL SKIPPED notifications

**File:** `bot/grid_runner.py`

Stesso pattern del BUY SKIPPED spam fix (Session 21). Aggiunta dedup `_last_sell_skip_notification` con chiave `(level_price, holdings)`.

---

## Fix 8 — Last-lot logic (SELL e BUY)

**File:** `bot/strategies/grid_bot.py`

**SELL:** Se `holdings ≤ lot size`, vende tutto in un trade. Dopo aver svuotato tutti i lotti, resetta `_pct_last_buy_price` al prezzo di vendita → il bot riprende a comprare dal riferimento corretto.

**BUY:** Se il cash rimanente dopo il trade standard è < `capital_per_trade`, spende tutto in questo trade (niente cash stranded).

---

## Fix 9 — Admin: posizioni chiuse mostravano valori negativi

**File:** `web/admin.html`

Quando holdings = 0 (posizione fully closed): Invested e Grid capacity diventavano negativi (sells > buys in conteggio grezzo).

**Fix:** Se `netHoldings <= 0`, clamp `netSpent = 0`, `capacityPct = 0`, status = "CLOSED — awaiting re-entry".

---

## Fix 10 — Admin: auto-refresh 30s

**File:** `web/admin.html`

`setInterval(loadAll, 30000)` su `showDashboard()`. Label aggiornato: "Last refresh: HH:MM:SS · auto every 30s".

---

## Fix 11 — Admin: Portfolio Overview redesign (2 righe)

**File:** `web/admin.html`

Rimossa la vecchia riga Portfolio/Deployed/Idle Cash. Sostituita con:

**Riga 1:** Portfolio Value · Total P&L (breakdown realized + unrealized) · Skim Reserve
**Riga 2:** Cash Available · Deployed (solo posizioni aperte) · Unrealized P&L (per coin)

Skim da query diretta `reserve_ledger` v3. Aggiunta RLS policy `anon_read_reserve_ledger` su Supabase (mancava → sempre $0).

---

## Fix 12 — Admin: Portfolio Value live (non più da snapshot giornaliero)

**File:** `web/admin.html`

**Problema:** Portfolio Value leggeva da `daily_pnl` (snapshot delle 20:00) → stale durante il giorno.

**Fix:**
- Fetch prezzi live da `api.binance.com/api/v3/ticker/price` ad ogni refresh
- Fetch tutti i trade v3 senza `limit=50`
- Portfolio Value = cash (ricostruito dai trade) + holdings × prezzo live
- Unrealized P&L = (prezzo live − avg buy) × net holdings per coin

---

## File modificati

| File | Fix |
|------|-----|
| `bot/strategies/grid_bot.py` | 1, 2, 5, 8 |
| `config/settings.py` | 3 |
| `db/client.py` | 4 |
| `bot/grid_runner.py` | 4, 7 |
| `utils/telegram_notifier.py` | 6 |
| `web/admin.html` | 9, 10, 11, 12 |
| Supabase (RLS policy) | 11 |

## Note operative
- Bot va riavviato per applicare fix 1-8
- Admin dashboard ora si auto-aggiorna ogni 30s con prezzi live
- Skim reserve ora visibile in admin (era bloccato da RLS mancante)
