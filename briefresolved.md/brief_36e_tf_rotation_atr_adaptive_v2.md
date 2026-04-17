# BRIEF — Session 36e v2: TF rotation + ATR-adaptive buy/sell

**Date:** 2026-04-17
**Version:** v2 — CEO decisions locked in (draft v1 preserved)
**Priority:** MEDIUM-HIGH — blocca il TF dal catturare le coin più promettenti quando quelle attive diventano mediocri
**Prerequisito:** 36c deployato ✅, 36d deployato ✅
**Scope rule:** SOLO allocator + classifier + scanner. NON toccare grid_bot (continua a leggere buy_pct/sell_pct da bot_config), NON toccare tf_budget/skim.
**Target branch:** `main` (push diretto, niente PR — coerente con 36g)
**Deploy timing:** on-demand quando CEO disponibile (nessun auto-deploy alla merge)
**CC working machine:** MacBook Air (locale)
**Production machine:** Mac Mini (deploy via `git pull` SSH)

---

## Changelog rispetto al draft v1

Tutte le decisioni aperte sono state chiuse dal CEO. Riassunto dei valori finali:

| Parametro | Draft v1 | v2 finale | Motivazione |
|---|---|---|---|
| `SWAP_STRENGTH_DELTA` | 15.0 | **20.0** | Più prudente per evitare flip-flop su rumore di strength |
| `SWAP_COOLDOWN_HOURS` | 12 | **8** | Reattivo (2 cicli scan) — profit gate fa da ulteriore freno |
| `SWAP_MIN_PROFIT_USD` | `$0.01` | **`-1.0%` allocation** | Break-even morbido scalato sulla size |
| `k_sell / k_buy` ATR | 0.8 / 1.2 | **1.2 / 0.8** | Bias bullish: hold più a lungo, buy aggressivo sui dip |
| Fallback rescan fallito | aperto | **HOLD + log warning + retry** | Opzione A: minima sorpresa, nessun contatore di stato |

**Nota forward-looking coefficienti ATR**: `k_sell=1.2` e `k_buy=0.8` sono hardcoded in questa fase. In sessioni successive sono previsti brief per renderli:
- **dinamici** (scalano con `signal_strength`, o con market regime BULL/BEAR globale)
- **percentuali configurabili** via `trend_config` invece che costanti nel codice

Il design di `_adaptive_steps(coin, signal)` deve lasciare facile sostituire i coefficienti hardcoded con lettura da DB. Usare costanti a livello modulo chiaramente annotate come `# TODO: move to trend_config in future session`.

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
            logger.info(f"On-demand rescan succeeded for {sym}: "
                        f"signal={coin['signal']}, strength={coin.get('signal_strength', 0):.1f}")
        except Exception as e:
            logger.warning(
                f"On-demand rescan FAILED for {sym}: {e} — "
                f"falling back to HOLD (will retry next scan)"
            )
            # NO DEALLOCATE preventivo — CEO decision locked at Opzione A
            # The symbol stays absent from augmented → legacy HOLD path takes over
    return augmented
```

(Richiede un helper `fetch_indicators_for_symbol` nello scanner — estrazione della logica esistente di `scan_top_coins` per 1 singolo simbolo.)

Con questo, il loop successivo (Problema 1 — rotation) può sempre contare su dati freschi per ogni coin attiva che il rescan è riuscito a recuperare. Il costo è 1 extra API call per ogni attivo fuori-top (max `tf_max_coins` ≈ 2 oggi, non un problema di rate limit).

### Fallback rescan fallito — Opzione A locked

**Decisione CEO**: se il rescan on-demand fallisce per un simbolo:
1. Logghiamo un warning esplicito con il motivo dell'errore
2. Il simbolo **resta assente** da `augmented` (= dal `coin_lookup` passato al loop decisionale)
3. Il legacy path `coin_lookup.get(sym)` = `None` → HOLD con motivazione `"Not in current scan top — keeping existing grid"`
4. Al prossimo scan TF (4h dopo) si riprova automaticamente

**Motivazione**:
- Principio di minima sorpresa: comportamento identico a oggi in caso di errore
- Errori di rete Binance sono quasi sempre transienti (secondi/minuti)
- Nessun contatore di fallimenti da persistere (evita complessità DB/cache)
- Se i rescan falliscono per 12h+, abbiamo problemi infrastrutturali più grossi e la DEALLOCATE preventiva non è la priorità

### Files extra da modificare (oltre a Fix 1/2)

| File | Azione |
|---|---|
| `bot/trend_follower/scanner.py` | Estrarre `fetch_indicators_for_symbol(exchange, sym)` dalla logica di `scan_top_coins` — rendere la logica riutilizzabile per 1 singolo simbolo |
| `bot/trend_follower/allocator.py` | Chiamare `_rescan_active_if_missing` prima del loop HOLD/DEALLOCATE/SWAP |

---

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

---

## Problema 2 — buy_pct / sell_pct fissi ignorano la volatilità

Oggi l'allocator scrive:
```python
if signal == "BULLISH": buy_pct, sell_pct = 1.5, 1.2
elif signal == "BEARISH": buy_pct, sell_pct = 2.0, 0.8
else: buy_pct, sell_pct = 1.5, 1.0
```

Un coin volatile tipo BIO (ATR ~6% del prezzo) venderebbe al +1.2% perdendo quasi tutto il movimento. Un coin stabile tipo ETH (ATR ~1.5%) userebbe la stessa soglia e catturerebbe bene il range. Step fissi → trattamento uniforme di cose eterogenee.

---

## Obiettivo

1. **Rotazione ibrida**: il TF sostituisce una coin attiva con un candidato più forte, **solo** se soddisfa tutte le condizioni di sicurezza (profit + delta strength + cooldown). Evita flip-flop e salvaguarda il TF dal vendere in perdita solo per inseguire il trend.

2. **ATR adaptive steps**: `buy_pct` e `sell_pct` vengono scalati sull'ATR del coin al momento dell'allocation, con range di safety hardcoded. Bias bullish-friendly: `k_sell=1.2` (teniamo più a lungo) / `k_buy=0.8` (entriamo aggressivi sui dip).

---

## Fix 1 — Rotation (hybrid swap rule) con valori CEO-locked

### Logica

In [allocator.decide_allocations](bot/trend_follower/allocator.py), aggiungere un blocco **dopo** il check BEARISH e **prima** dello loop sui nuovi BULLISH:

```python
# ==================================================================
# Hybrid rotation: swap a weaker active TF coin for a stronger candidate
# All thresholds are CEO-locked (session 36e v2, 2026-04-17).
# Future brief may move these to trend_config for dynamic tuning.
# ==================================================================
SWAP_STRENGTH_DELTA = 20.0         # v1 was 15.0 — raised for flip-flop safety
SWAP_COOLDOWN_HOURS = 8            # v1 was 12 — profit gate is the other brake
SWAP_MIN_PROFIT_PCT = -1.0         # v1 was $0.01 — now scaled % of allocation

for alloc in current_allocations:
    if not alloc.get("is_active"):
        continue
    sym = alloc["symbol"]
    active_coin = coin_lookup.get(sym)
    if not active_coin or active_coin["signal"] == "BEARISH":
        continue  # already handled by BEARISH → DEALLOCATE earlier

    # Find the best NEW bullish candidate (not currently active)
    best_new = next(
        (c for c in bullish if c["symbol"] not in active_symbols),
        None
    )
    if not best_new:
        continue

    delta = best_new["signal_strength"] - active_coin["signal_strength"]
    if delta < SWAP_STRENGTH_DELTA:
        continue

    # --- Cooldown gate: when was this coin allocated?
    allocated_at = alloc.get("updated_at") or alloc.get("created_at")
    held_hours = _hours_since(allocated_at)
    if held_hours < SWAP_COOLDOWN_HOURS:
        logger.debug(
            f"SWAP skip {sym}: held {held_hours:.1f}h < {SWAP_COOLDOWN_HOURS}h cooldown"
        )
        continue

    # --- Profit gate: scaled % of allocation, NOT fixed USD
    capital_allocation = float(alloc.get("capital_allocation", 0))
    min_profit_usd = capital_allocation * (SWAP_MIN_PROFIT_PCT / 100.0)
    unrealized = _fetch_unrealized_pnl(supabase, sym)
    if unrealized < min_profit_usd:
        logger.debug(
            f"SWAP skip {sym}: unrealized ${unrealized:.2f} < "
            f"threshold ${min_profit_usd:.2f} ({SWAP_MIN_PROFIT_PCT}% of ${capital_allocation:.2f})"
        )
        continue

    # --- All gates passed → SWAP
    logger.info(
        f"SWAP triggered: {sym} (strength {active_coin['signal_strength']:.1f}, "
        f"held {held_hours:.1f}h, unrealized ${unrealized:.2f}) "
        f"→ replaced by {best_new['symbol']} (+{delta:.1f} strength)"
    )
    decisions.append(_make_decision(
        scan_ts, sym, active_coin, "DEALLOCATE",
        f"SWAP: replaced by {best_new['symbol']} (+{delta:.1f} strength, "
        f"held {held_hours:.1f}h, unrealized ${unrealized:.2f})",
    ))
    # The new candidate will be picked up naturally by the existing bullish loop
```

### Nota su SWAP_MIN_PROFIT_PCT

Il valore è **negativo** (-1.0%) perché accettiamo fino a -1% di unrealized loss prima di bloccare lo swap. Esempi:

| Allocation | Soglia (-1%) |
|---|---|
| $50 | -$0.50 |
| $100 | -$1.00 |
| $200 | -$2.00 |

Logica: "accettiamo piccole fluttuazioni negative come rumore di mercato ma non vendiamo in perdita sostanziale per inseguire un candidato". Il gate BEARISH già gestisce il caso 'coin moribonda' — questo gate gestisce 'coin viva in oscillazione normale'.

### Helper functions da aggiungere

```python
from datetime import datetime, timezone

def _hours_since(ts) -> float:
    """Return hours elapsed since a datetime/ISO string, or +inf if None/invalid."""
    if not ts:
        return float("inf")
    if isinstance(ts, str):
        # Supabase returns ISO 8601 with Z or timezone offset
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    return delta.total_seconds() / 3600.0


def _fetch_unrealized_pnl(supabase, symbol: str) -> float:
    """
    Compute unrealized PnL for an active symbol:
    (current_price * holdings) - (cost_basis_of_open_lots).

    Holdings and cost basis come from `trades` where side='buy' AND not
    fully offset by subsequent sells (FIFO or average — use whatever
    grid_bot already uses for avg_buy_price).

    If unrealized cannot be computed (no open position, price fetch fails),
    return 0.0 — safe default that lets SWAP_MIN_PROFIT_PCT gate the swap.
    """
    # Implementation detail: CC to match grid_bot's existing cost accounting.
    # Should read `managed_by='trend_follower'` trades for this symbol where
    # state indicates 'open lot', sum cost, compare to (current_price * amount).
    ...
```

### Decisioni implementative lasciate a CC

1. **Ordine delle operazioni quando scan fa SWAP + nuova ALLOCATE**: se lo stesso scan fa SWAP (DEALLOCATE di AXL) + nuova ALLOCATE di ORDI, quando viene letto `unallocated` il DEALLOCATE è già contato? Va testato: `unallocated` si aggiorna dopo che `grid_runner` processa il `pending_liquidation` (minuti dopo). Probabile che serve un flag "budget virtualmente liberato in questo scan" per non bloccare la nuova ALLOCATE.
   - **Approccio suggerito**: nel dict `budget_tracker` locale all'allocator, incrementare `unallocated += alloc.capital_allocation` immediatamente dopo aver deciso lo SWAP, così la subsequent ALLOCATE vede il budget come disponibile.
   - Se CC trova questa assunzione sbagliata, segnalarlo nel report di deploy.

2. **Cosa succede se 2 coin attive meritano SWAP nello stesso scan ma c'è 1 solo candidato**: la logica attuale fa `best_new = next(...)` una volta sola. Se 2 attivi superano tutti i gate contro lo stesso `best_new`, il secondo non trova candidato e si ferma. **Comportamento accettabile** per la prima versione — swappa 1 per scan. Eventualmente iterare con `second_best` in brief successivo.

### Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Aggiungere blocco SWAP + helper `_hours_since`, `_fetch_unrealized_pnl` |

### Files da NON toccare

- `bot/strategies/grid_bot.py` (il grid esistente si auto-liquida su `pending_liquidation` come sempre)
- `bot/trend_follower/trend_follower.py` (solo chiama allocator — nessuna modifica di logica qui)

---

## Fix 2 — ATR-adaptive buy_pct / sell_pct con coefficienti CEO-locked

### Dati disponibili

Il classifier già calcola `atr` (ATR 14) e `atr_avg` per ogni coin, visibili in `trend_scans` e nel dict passato all'allocator.

### Formula con coefficienti CEO-locked

```python
# CEO-locked coefficients (session 36e v2, 2026-04-17)
# Bias: bullish-friendly — hold longer, buy aggressive on dips.
# TODO: move to trend_config.tf_k_sell / tf_k_buy in future session
#       to enable dynamic tuning based on market regime or signal_strength.
K_SELL = 1.2  # v1 was 0.8
K_BUY  = 0.8  # v1 was 1.2
# Safety clamps (unchanged from v1)
SELL_PCT_MIN, SELL_PCT_MAX = 1.0, 8.0
BUY_PCT_MIN,  BUY_PCT_MAX  = 1.0, 10.0


def _adaptive_steps(coin: dict, signal: str) -> tuple[float, float]:
    """
    Returns (buy_pct, sell_pct) scaled by coin volatility (ATR / price).
    Falls back to fixed legacy steps if ATR unavailable.

    Bias (CEO decision 36e v2): k_sell > k_buy means we hold positions
    longer before realizing (catch more of the BULLISH trend) and enter
    dips more aggressively (shorter retracement needed to buy).
    """
    atr = coin.get("atr", 0)
    price = coin.get("price", 0)
    if atr <= 0 or price <= 0:
        # Fallback to legacy fixed steps (unchanged)
        if signal == "BULLISH":  return 1.5, 1.2
        if signal == "BEARISH":  return 2.0, 0.8
        return 1.5, 1.0

    atr_pct = (atr / price) * 100  # ATR as % of price

    # Sell step: wider than ATR so we capture more of the move
    #   e.g. BIO ATR 6% → sell_pct 7.2 (clamped to 8.0 if above)
    #        ETH ATR 1.5% → sell_pct 1.8
    sell_pct = max(SELL_PCT_MIN, min(SELL_PCT_MAX, atr_pct * K_SELL))

    # Buy step: narrower than ATR so we enter dips earlier
    #   e.g. BIO ATR 6% → buy_pct 4.8
    #        ETH ATR 1.5% → buy_pct 1.2
    buy_pct = max(BUY_PCT_MIN, min(BUY_PCT_MAX, atr_pct * K_BUY))

    # Signal-based tweak: bearish allocations (rare for TF) widen buys slightly
    # to avoid catching a falling knife.
    if signal == "BEARISH":
        buy_pct = min(BUY_PCT_MAX, buy_pct * 1.1)

    return round(buy_pct, 2), round(sell_pct, 2)
```

### Esempi numerici con i nuovi coefficienti

| Coin | ATR% | sell_pct | buy_pct | Nota |
|---|---|---|---|---|
| ETH | 1.5% | 1.8 | 1.2 | Range stretto, coin calma |
| ORDI | 3.0% | 3.6 | 2.4 | Range medio |
| BIO | 6.0% | 7.2 | 4.8 | Range largo, coin volatile |
| SOL | 2.0% | 2.4 | 1.6 | Range medio-stretto |
| Shitcoin estrema | 12% | 8.0 (clamp) | 9.6 | Sell cappato a 8% |
| Super-stable | 0.5% | 1.0 (clamp) | 1.0 (clamp) | Entrambi al floor |

### Where to call

In [allocator.apply_allocations](bot/trend_follower/allocator.py) prima di costruire `row_fields`, rimpiazzare il blocco `if signal == "BULLISH"...` con:

```python
buy_pct, sell_pct = _adaptive_steps(coin, signal)
# coin qui è il classified_coins dict corrispondente al decision
```

Serve passare il coin dict dentro `config_snapshot` oppure fare lookup symbol→coin nel caller (`trend_follower.py`).

### Range di safety (invariati dal draft v1)

- `sell_pct` ∈ [1.0, 8.0] — mai sotto 1% (sweep noise) né sopra 8% (perde troppo se falsi pump)
- `buy_pct` ∈ [1.0, 10.0] — più largo lato buy perché le discese sono più rapide

### Ricalcolo: una sola volta per allocation

**Decisione**: `buy_pct` e `sell_pct` sono calcolati **al momento della ALLOCATE** (primo ingresso del coin nel TF) e **non** ricalcolati a ogni scan. Motivo: ricalcolare a ogni scan resetta implicitamente il grid e confonde i lot aperti del bot. L'allocation-time snapshot è la source of truth.

Se in futuro vogliamo resize (p.es. dopo 1 settimana la volatilità è cambiata molto), sarà un brief separato.

### Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Helper `_adaptive_steps`, chiamarlo in `apply_allocations` al posto del blocco signal-fisso |
| `bot/trend_follower/trend_follower.py` | Garantire che `coin` dict raggiunga l'allocator (già accade via `classified_coins`) |

---

## Test pre-deploy

### Rotation (Problema 1)

- [ ] Mock scan: 2 coin attive con strength bassa (30) + candidato strength 55 (delta +25) → SWAP scatta sulla più debole (1 per scan, come da design)
- [ ] Mock scan: candidato delta +15 (sotto nuova soglia 20) → HOLD
- [ ] Mock scan: candidato delta +20 esatto → SWAP scatta (boundary inclusivo in `>=`)
- [ ] Mock scan: attivo allocato 6h fa (sotto cooldown 8h) → HOLD anche se delta +30
- [ ] Mock scan: attivo allocato 8.0h esatti → SWAP scatta (boundary inclusivo)
- [ ] Mock scan: allocation=$50, unrealized=-$0.51 (soglia -$0.50) → HOLD
- [ ] Mock scan: allocation=$50, unrealized=-$0.49 (sopra soglia) → SWAP
- [ ] Mock scan: allocation=$100, unrealized=-$0.90 (soglia -$1.00) → SWAP (passa perché -0.9 > -1.0)
- [ ] Mock scan: 2 candidati >+20, ma solo 1 coin attiva da sostituire → quella sostituita è l'unica (comportamento nominale)
- [ ] Mock scan: 2 attive meritano swap contro stesso candidato → solo la prima fa SWAP, la seconda HOLD

### On-demand rescan (Problema 0)

- [ ] Mock con AXL attiva fuori-top + Binance API che risponde correttamente → `augmented[AXL]` popolato con indicatori freschi
- [ ] Mock con AXL attiva fuori-top + API che solleva Timeout → log warning, `augmented` non contiene AXL, legacy HOLD path
- [ ] Mock con AXL attiva fuori-top + API che ritorna dati malformati → log warning, stesso behavior del timeout
- [ ] Nessun rescan se AXL è già in coin_lookup (no duplicate API calls)

### ATR adaptive (Problema 2)

- [ ] Coin sintetico ATR=6%, price=100 → sell_pct 7.2, buy_pct 4.8
- [ ] Coin sintetico ATR=0.5% → buy_pct e sell_pct clamp a 1.0
- [ ] Coin sintetico ATR=15% → sell_pct clamp a 8.0, buy_pct a 10.0 (se calcolo lo porta sopra)
- [ ] Coin sintetico ATR=0 → fallback 1.5/1.2 (BULLISH) o 2.0/0.8 (BEARISH)
- [ ] Coin BEARISH con ATR=3% → sell_pct 3.6, buy_pct 2.4 * 1.1 = 2.64 (tweak bearish)

---

## Test post-deploy

- [ ] 24h post deploy: almeno 1 swap eseguito in prod se lo scan trova candidati +20 strength (se nessun candidato soddisfa, OK — vuol dire che la soglia +20 sta filtrando correttamente)
- [ ] Verifica `bot_config` su nuove coin allocate → `buy_pct` e `sell_pct` riflettono ATR del momento dell'allocation
- [ ] Nessun grid resettato durante scan successivi (i bot continuano con la config iniziale allocation-time)
- [ ] Tail log allocator: righe `SWAP triggered` loggate con delta/cooldown/profit quando applicable
- [ ] Tail log allocator: righe `SWAP skip` con motivo (cooldown, profit, delta) per i casi bordercase
- [ ] Tail log scanner: righe `On-demand rescan succeeded/FAILED` quando active fuori-top

---

## Rollback plan

```bash
# Da MacBook Air
git log --oneline -5  # identify commit hash
git revert <commit_hash>
git push origin main

# Da Mac Mini (via SSH)
ssh max@<mac-mini> 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator come in 36c (comando detached via tmux/nohup)
```

Nessuna migration DB. I bot attivi restano come sono, le allocate future tornano al sistema fisso 1.5/1.2 e niente rotation.

---

## Commit format

```
feat(trend-follower): hybrid rotation + ATR-adaptive grid steps (36e v2)

Allocator now rotates an active TF coin when: (a) a new candidate
has signal_strength +20 over it, (b) the active is in unrealized
profit above -1% of allocation, (c) it has been held at least 8h.
Prevents flip-flop and loss-selling.

buy_pct / sell_pct computed from the coin's ATR/price ratio at
allocation time, with CEO-locked coefficients k_sell=1.2 / k_buy=0.8
(bullish bias: hold longer, buy aggressive on dips). Clamped to
[1.0, 10.0] / [1.0, 8.0]. Fixed fallback when ATR missing.
grid_bot config is NOT recomputed on subsequent scans — allocation-time
snapshot is the source of truth.

On-demand rescan fills the gap for active coins that fell off the
top-50 scan, so HOLD/DEALLOCATE/SWAP always have fresh signal data.
Failed rescans log a warning and fall back to legacy HOLD.

CEO decisions locked (session 36e v2):
- SWAP_STRENGTH_DELTA=20 (was 15)
- SWAP_COOLDOWN_HOURS=8 (was 12)
- SWAP_MIN_PROFIT_PCT=-1.0 (was $0.01 fixed)
- k_sell=1.2, k_buy=0.8 (was 0.8/1.2 — flipped for bullish bias)
- Rescan fallback: HOLD + log + retry next scan (no preventive DEALLOCATE)
```

---

## Out of scope (ribadito)

- **36f**: trailing stop su pump (brief separato)
- **36g**: TF compounding / floating cash (brief separato, ordine di deploy: dopo 36e)
- **36h**: Haiku legge dati TF (brief separato)
- Tunare `scan_interval_hours` (resta 4h — valutato in nota 36f)
- Aggiungere nuovi indicatori al classifier (MACD, Volume-weighted trend, ...)
- Rendere `k_sell`/`k_buy` dinamici o configurabili via DB (brief futuro)
- Resize delle allocation su cambio di volatilità (brief futuro)
- Supporto di 2+ SWAP nello stesso scan (brief futuro se si rivela necessario)

---

## Execution summary (CEO-locked values at a glance)

```python
# Drop-in constants for allocator.py
SWAP_STRENGTH_DELTA = 20.0   # points
SWAP_COOLDOWN_HOURS = 8      # hours
SWAP_MIN_PROFIT_PCT = -1.0   # percent of allocation (negative = allow small loss)
K_SELL = 1.2                 # ATR multiplier for sell_pct
K_BUY  = 0.8                 # ATR multiplier for buy_pct
```

Buon lavoro CC. Se qualcosa nei file path o nelle assunzioni è cambiato dal draft v1 (es. signature di `decide_allocations` diversa, `trades.managed_by` non esiste, ecc.) segnalalo nel primo report di sviluppo invece di procedere alla cieca.
