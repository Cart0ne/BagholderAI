# BRIEF — Session 36e: TF rotation + ATR-adaptive buy/sell

**Date:** 2026-04-16 (da raffinare con CEO 2026-04-17)
**Priority:** MEDIUM-HIGH — blocca il TF dal catturare le coin più promettenti quando quelle attive diventano mediocri
**Prerequisito:** 36c deployato ✅, 36d deployato ✅
**Scope rule:** SOLO allocator + classifier. NON toccare grid_bot (continua a leggere buy_pct/sell_pct da bot_config), NON toccare tf_budget/skim.

---

## Problema 0 — Gap nella valutazione delle coin attive (edge case critico)

Oggi in [allocator.py:76-82](bot/trend_follower/allocator.py#L76-L82):

```python
coin = coin_lookup.get(sym)
if not coin:
    # Non in scan top-50 → HOLD senza vedere il signal
    decisions.append(_make_decision(..., "HOLD", "Not in current scan top — keeping existing grid"))
    continue
```

Se una coin attiva **esce dalla top-50 E diventa BEARISH** nello stesso ciclo, il TF non può decidere DEALLOCATE perché non ha dati sui suoi indicatori. La posizione resta appesa anche se stiamo andando a fondo.

### Fix 1b — On-demand rescan per coin attive fuori-top

Prima del loop di valutazione HOLD/DEALLOCATE/SWAP, per ogni coin attiva non presente in `coin_lookup` → forzare un piccolo rescan mirato (OHLCV + EMA/RSI/ATR) per quel simbolo:

```python
def _rescan_active_if_missing(exchange, coin_lookup, active_symbols, config):
    """
    For each active symbol not in the scan top-N, fetch fresh OHLCV +
    indicators on-demand. Returns an augmented coin_lookup that includes
    them, so downstream logic can always decide HOLD/DEALLOCATE/SWAP
    with fresh signal/strength data — never blindly holding a coin
    we lost sight of.
    """
    from bot.trend_follower.scanner import fetch_indicators_for_symbol
    from bot.trend_follower.classifier import classify_signal

    augmented = dict(coin_lookup)
    for sym in active_symbols:
        if sym in augmented:
            continue
        try:
            coin = fetch_indicators_for_symbol(exchange, sym)
            classify_signal(coin, config)
            augmented[sym] = coin
        except Exception as e:
            logger.warning(f"Rescan failed for {sym}: {e} — falling back to HOLD")
    return augmented
```

(Richiede un helper `fetch_indicators_for_symbol` nello scanner — estrazione della logica esistente di `scan_top_coins` per 1 singolo simbolo.)

Con questo, il loop successivo (Problema 1 — rotation) può sempre contare su dati freschi per ogni coin attiva, eliminando il caso "out-of-top → HOLD cieco". Il costo è 1 extra API call per ogni attivo fuori-top (max tf_max_coins ≈ 2 oggi).

### Files extra da modificare (oltre a Fix 1/2)

| File | Azione |
|---|---|
| `bot/trend_follower/scanner.py` | Estrarre `fetch_indicators_for_symbol(exchange, sym)` dalla logica di `scan_top_coins` |
| `bot/trend_follower/allocator.py` | Chiamare `_rescan_active_if_missing` prima del loop HOLD/DEALLOCATE/SWAP |

### Decisione aperta

- **Fallback in caso di rescan fallito**: logs warning + HOLD conservativo (come oggi), o DEALLOCATE preventivo se la coin è fuori-top da ≥ N scan consecutivi? Prima opzione sicura, seconda aggressiva.

## Problema 1 — Il TF non ruota

Oggi [bot/trend_follower/allocator.py:71-94](bot/trend_follower/allocator.py#L71-L94) decide sulle coin attive così:
- Signal diventato `BEARISH` → DEALLOCATE
- Coin uscita dalla top-50 scan → HOLD ("Not in current scan top — keeping existing grid")
- Altrimenti → HOLD

Esempio reale (16 apr 2026, 16:51 UTC):
```
Active: AXL strength 35.5, MBOX non più in top-2
Top candidato large-cap: ORDI strength 49.2
Top candidato mid-cap: PNUT strength 37.4
```

ORDI è +13.7 punti più forte di AXL ma il TF **non sostituisce**. Conseguenza: il budget resta parcheggiato su coin mediocri mentre migliori passano inosservate.

## Problema 2 — buy_pct / sell_pct fissi ignorano la volatilità

Oggi l'allocator scrive:
```python
if signal == "BULLISH": buy_pct, sell_pct = 1.5, 1.2
elif signal == "BEARISH": buy_pct, sell_pct = 2.0, 0.8
else: buy_pct, sell_pct = 1.5, 1.0
```

Un coin volatile tipo BIO (ATR ~6% del prezzo) venderebbe al +1.2% perdendo quasi tutto il movimento. Un coin stabile tipo ETH (ATR ~1.5%) userebbe la stessa soglia e catturerebbe bene il range. Step fissi → trattamento uniforme di cose eterogenee.

## Obiettivo

1. **Rotazione ibrida**: il TF sostituisce una coin attiva con un candidato più forte, **solo** se soddisfa tutte le condizioni di sicurezza (profit + delta strength + cooldown). Evita flip-flop e salvaguarda il TF dal venderedown in perdita solo per inseguire il trend.

2. **ATR adaptive steps**: `buy_pct` e `sell_pct` vengono scalati sull'ATR del coin al momento dell'allocation, con range di safety hardcoded.

## Fix 1 — Rotation (hybrid swap rule)

### Logica

In [allocator.decide_allocations](bot/trend_follower/allocator.py), aggiungere un blocco **dopo** il check BEARISH e **prima** dello loop sui nuovi BULLISH:

```python
# Hybrid rotation: swap a weaker active TF coin for a stronger candidate
SWAP_STRENGTH_DELTA = 15.0     # new candidate must be +15 strength stronger
SWAP_COOLDOWN_HOURS = 12       # active coin must have been held at least 12h
SWAP_MIN_PROFIT_USD = 0.01     # active must be in unrealized profit (>= ~break-even)

for alloc in current_allocations:
    if not alloc.get("is_active"): continue
    sym = alloc["symbol"]
    active_coin = coin_lookup.get(sym)
    if not active_coin or active_coin["signal"] == "BEARISH":
        continue  # already handled

    # Find the best NEW bullish candidate (not currently active)
    best_new = next((c for c in bullish if c["symbol"] not in active_symbols), None)
    if not best_new:
        continue

    delta = best_new["signal_strength"] - active_coin["signal_strength"]
    if delta < SWAP_STRENGTH_DELTA:
        continue

    # Cooldown check: when was this coin allocated?
    allocated_at = alloc.get("updated_at") or alloc.get("created_at")
    if _hours_since(allocated_at) < SWAP_COOLDOWN_HOURS:
        continue

    # Profit check: unrealized PnL must be non-negative
    unrealized = _fetch_unrealized_pnl(supabase, sym)  # new helper
    if unrealized < SWAP_MIN_PROFIT_USD:
        continue

    # All gates passed → SWAP
    decisions.append(_make_decision(
        scan_ts, sym, active_coin, "DEALLOCATE",
        f"SWAP: replaced by {best_new['symbol']} (+{delta:.1f} strength, held {_hours_since(allocated_at):.1f}h)",
    ))
    # The new candidate will be picked up naturally by the existing bullish loop
    # (mark it with a flag so it's prioritized)
```

### Decisioni aperte (da raffinare col CEO)

1. **SWAP_STRENGTH_DELTA = 15**: baseline. Se troppo basso → flip-flop, se troppo alto → quasi mai scatta. Suggerito calibrare dopo 2-3 swap reali.
2. **SWAP_COOLDOWN_HOURS = 12**: evita che una coin appena allocata venga già sostituita. Alternativa: 24h, più conservativo.
3. **SWAP_MIN_PROFIT_USD = 0.01**: "non in perdita". Alternative:
   - `>= 0` (break-even, tollera piccole fluttuazioni negative)
   - `>= tf_budget * 0.005` (almeno 0.5% in profit per evitare swap su posizioni appena aperte)
4. **Ordine delle operazioni**: se lo stesso scan fa SWAP + nuova ALLOCATE, quando viene letto `unallocated` il DEALLOCATE è già contato? Va testato: `unallocated` si aggiorna dopo che `grid_runner` processa il `pending_liquidation` (minuti dopo). Probabile serve un flag per "budget virtualmente liberato in questo scan".

### Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Aggiungere blocco SWAP + helper `_hours_since`, `_fetch_unrealized_pnl` |

### Files da NON toccare

- `bot/strategies/grid_bot.py` (il grid esistente si auto-liquida su `pending_liquidation` come sempre)
- `bot/trend_follower/trend_follower.py` (solo chiama allocator)

## Fix 2 — ATR-adaptive buy_pct / sell_pct

### Dati disponibili

Il classifier già calcola `atr` (ATR 14) e `atr_avg` per ogni coin, visibili in `trend_scans` e nel dict passato all'allocator.

### Formula proposta

```python
def _adaptive_steps(coin: dict, signal: str) -> tuple[float, float]:
    """
    Returns (buy_pct, sell_pct) scaled by coin volatility.
    Falls back to fixed steps if ATR unavailable.
    """
    atr = coin.get("atr", 0)
    price = coin.get("price", 0)
    if atr <= 0 or price <= 0:
        # Fallback to legacy fixed steps
        if signal == "BULLISH":  return 1.5, 1.2
        if signal == "BEARISH":  return 2.0, 0.8
        return 1.5, 1.0

    atr_pct = (atr / price) * 100  # ATR as % of price

    # Sell step: slightly below 1x ATR so we catch most of the move
    #   e.g. BIO ATR 6% → sell_pct 4.8
    #        ETH ATR 1.5% → sell_pct 1.2
    sell_pct = max(1.0, min(8.0, atr_pct * 0.8))

    # Buy step: slightly above 1x ATR to let dips breathe before catching them
    #   e.g. BIO ATR 6% → buy_pct 7.2
    #        ETH ATR 1.5% → buy_pct 1.8
    buy_pct  = max(1.0, min(10.0, atr_pct * 1.2))

    # Signal-based tweak: bearish allocations (rare for TF) widen buys slightly
    if signal == "BEARISH":
        buy_pct = min(10.0, buy_pct * 1.1)

    return round(buy_pct, 2), round(sell_pct, 2)
```

### Where to call

In [allocator.apply_allocations](bot/trend_follower/allocator.py) prima di costruire `row_fields`, rimpiazzare il blocco `if signal == "BULLISH"...` con:

```python
buy_pct, sell_pct = _adaptive_steps(coin, signal)
# coin qui è il classified_coins dict corrispondente al decision
```

Serve passare il coin dict dentro `config_snapshot` oppure fare lookup symbol→coin nel caller.

### Range di safety (hardcoded)

- `sell_pct` ∈ [1.0, 8.0] — mai sotto 1% (sweep noise) né sopra 8% (perde troppo se falsi pump)
- `buy_pct` ∈ [1.0, 10.0] — più largo lato buy perché le discese sono più rapide

### Decisioni aperte (da raffinare col CEO)

1. **Coefficienti k_sell=0.8 e k_buy=1.2**: da calibrare su dati reali. Partenza prudente; se il TF perde opportunità, alzare k_sell verso 1.0.
2. **Fallback ATR=0**: cosa fare se per qualche motivo ATR mancante? Oggi → fisso 1.5/1.2. OK.
3. **Rilettura ATR a ogni scan**: ricalcolare buy/sell_pct a ogni scan TF (4h) oppure solo al primo allocate? Preferibile il secondo (altrimenti il grid viene resettato 6 volte al giorno).

### Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Helper `_adaptive_steps`, chiamarlo in `apply_allocations` al posto del blocco signal-fisso |
| `bot/trend_follower/trend_follower.py` | Garantire che `coin` dict raggiunga l'allocator (già accade via `classified_coins`) |

## Test pre-deploy

### Rotation

- [ ] Mock scan: 2 coin attive con strength bassa (30) + candidato strength 50 → SWAP scatta su entrambe
- [ ] Mock scan: candidato delta +10 (sotto soglia 15) → HOLD
- [ ] Mock scan: attivo allocato 6h fa (sotto cooldown 12h) → HOLD anche se delta +20
- [ ] Mock scan: attivo unrealized_pnl = -$2 → HOLD
- [ ] Mock scan: 2 candidati >+15, ma solo 1 coin attiva da sostituire → quella sostituita è la più debole

### ATR adaptive

- [ ] Coin sintetico ATR=6%, price=100 → sell_pct 4.8, buy_pct 7.2
- [ ] Coin sintetico ATR=0.5% → sell_pct clamp a 1.0
- [ ] Coin sintetico ATR=15% → sell_pct clamp a 8.0
- [ ] Coin sintetico ATR=0 → fallback 1.5/1.2

## Test post-deploy

- [ ] 24h post deploy: almeno 1 swap eseguito in prod se lo scan trova candidati +15 strength
- [ ] Verifica `bot_config` su AXL/MBOX/nuovi → buy_pct e sell_pct riflettono ATR del momento dell'allocation
- [ ] Nessun grid resettato durante scan successivi (i bot continuano con la config iniziale)
- [ ] Tail log allocator: righe SWAP vengono loggate con delta/cooldown/profit

## Rollback plan

```bash
git revert <commit_hash>
git push origin main
ssh max@<mac-mini> 'cd /Volumes/Archivio/bagholderai && git pull'
# restart orchestrator come in 36c
```

Nessuna migration DB. I bot attivi restano come sono, le allocate future tornano al sistema fisso 1.5/1.2.

## Commit format

```
feat(trend-follower): hybrid rotation + ATR-adaptive grid steps

Allocator now rotates an active TF coin when: (a) a new candidate
has signal_strength +15 over it, (b) the active is in unrealized
profit, (c) it has been held at least 12h. Prevents flip-flop and
loss-selling.

buy_pct / sell_pct computed from the coin's ATR/price ratio at
allocation time, clamped to [1.0, 10.0] / [1.0, 8.0]. Fixed fallback
when ATR missing. grid_bot config is NOT recomputed on subsequent
scans — allocation-time snapshot is the source of truth.
```

## Quando lanciarlo

Brief 36c ha detto "quando abbiamo 4-6 ore di dati AXL/MBOX per tarare i parametri ATR sensatamente". Alle 16:51 del 16 apr siamo a ~3.5h. Tra domani mattina e pomeriggio avremo >12h di dati reali sui 2 TF attuali, sufficienti per calibrare k_sell / k_buy / SWAP_STRENGTH_DELTA con qualche esempio concreto.

---

## Out of scope

- **36f**: trailing stop su pump (brief separato)
- **36g**: TF compounding / floating cash (brief separato, draft pronto)
- **36h**: Haiku legge dati TF (brief separato, draft pronto)
- Tunare `scan_interval_hours` (resta 4h)
- Aggiungere nuovi indicatori al classifier (MACD, Volume-weighted trend, ...)
