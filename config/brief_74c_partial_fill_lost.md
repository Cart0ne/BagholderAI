# BRIEF 74c — Partial fills lost: expired-with-filled-qty treated as no-op

**Scoperto:** 2026-05-12 durante audit S74, investigando un drift BONK orphan
**Priorità:** ALTA — bug di canonical state. Gating per mainnet €100.
**Stima effort:** 30-60 min (fix + test + smoke run su testnet)

---

## Smoking gun (log evidence)

```
12:30:12 [bagholderai.orders] WARNING: [orders] BUY BONK/USDT: order not filled
   (status='expired', filled=1368998.0). Treating as no-op. Order id=21190.
12:30:13 [bagholderai.telegram] INFO: Telegram message sent.
```

Conseguenze immediate:
- Binance ha eseguito 1.37M BONK reali (vedi `fetch_my_trades` order=21190)
- DB del bot NON ha registrato il trade
- Reconciliation Binance via `reconcile_binance.py --write` ha flaggato `DRIFT_BINANCE_ORPHAN` su BONK

## Root cause

**File:** `bot/exchange_orders.py:189-202`

```python
def _normalize_order_response(order: dict, symbol: str, side: str) -> Optional[dict]:
    """Extract the fields we care about from a ccxt order response.
    Returns None if the order did NOT actually fill (status != closed
    or filled <= 0). The caller treats this as a no-op.
    """
    status = (order.get("status") or "").lower()
    filled = float(order.get("filled") or 0)
    if status != "closed" or filled <= 0:   # ← BUG: OR-condition
        logger.warning(
            f"[orders] {side.upper()} {symbol}: order not filled "
            f"(status={status!r}, filled={filled}). Treating as no-op. "
            f"Order id={order.get('id')}."
        )
        _alert_rejection(...)
        return None
    ...
```

La condizione `status != "closed" OR filled <= 0` è troppo aggressiva. Su Binance, un ordine può tornare con `status='expired'` E `filled > 0`: è un **partial fill**. La quantità riempita è reale, accreditata sul conto. Buttare via questa risposta significa perdere un trade vero.

Pattern frequente su Binance testnet con book sottile (BONK in particolare, vedi `project_bonk_testnet_slippage.md`). Possibile anche su mainnet durante pump/dump o quando il bot lotta contro market makers veloci.

## Fix proposto

**Concettuale (3-4 righe modificate):**

```python
def _normalize_order_response(order: dict, symbol: str, side: str) -> Optional[dict]:
    status = (order.get("status") or "").lower()
    filled = float(order.get("filled") or 0)

    # Real no-op: zero fill regardless of status.
    if filled <= 0:
        logger.warning(
            f"[orders] {side.upper()} {symbol}: order not filled "
            f"(status={status!r}, filled={filled}). Treating as no-op. "
            f"Order id={order.get('id')}."
        )
        _alert_rejection(...)
        return None

    # Partial fill (status='expired'/'canceled' but filled > 0): the
    # coins ARE in the account. Log it differently and proceed as a
    # real (partial) trade. Binance testnet often returns 'expired'
    # when book liquidity can't absorb the full order; the partial
    # fill is still settled.
    if status != "closed":
        logger.warning(
            f"[orders] {side.upper()} {symbol}: PARTIAL FILL "
            f"(status={status!r}, filled={filled}/{order.get('amount')}). "
            f"Order id={order.get('id')}. Recording as real trade."
        )

    # ... proceed with avg_price, cost, fee extraction as before ...
```

Implementation notes:
- Comportamento attuale per `filled <= 0` resta identico
- Nuovo branch "partial fill": logga ma procede con il normalize → trade va in DB
- Eventuale Telegram alert per partial fill può essere aggiunto (decisione cosmetica)

## Test plan

1. **Unit test** (se esiste suite, altrimenti smoke locale):
   - Mock ccxt response con `{status: 'expired', filled: 100, amount: 200, cost: 10, average: 0.1}` → verificare che `_normalize_order_response` ritorna dict (non None) con `filled=100, cost=10, ...`
   - Mock ccxt response con `{status: 'expired', filled: 0, amount: 200}` → verificare che ritorna None (no-op corretto)
   - Mock ccxt response con `{status: 'closed', filled: 200, ...}` → caso happy path attuale, non deve regredire

2. **Smoke run testnet:**
   - Deploy il fix
   - Restart bot
   - Aspettare 1-2 partial fill naturali su BONK (succedono spesso testnet)
   - Verificare che il trade compare in `trades` table
   - Run `reconcile_binance.py --write` → verificare `binance_orphan=0` su BONK

3. **Reconciliation cleanup post-fix:**
   - Esiste già un orfano in produzione (order 21190, qty 1,368,998 BONK, prezzo $0.00000758, ts 2026-05-12T10:30:11Z)
   - Decidere: inserire manualmente questo trade in `trades` (per ripulire reconciliation), oppure lasciarlo come "antico drift" documentato
   - Raccomandazione: insert manuale, così la reconciliation torna OK e non sporca le metriche

## Mainnet impact

- **Probabilità:** Bassa-media. Sui mainnet con book profondi (BTC/USDT, ETH/USDT), un market order non si "expire" tipicamente. Più raro ma possibile in flash crash / liquidation cascade.
- **Severità se accade:** ALTA. Holdings DB diverge da Binance reale → calcolo P&L sbagliato, avg_buy sbagliato, decisioni sell-side sbagliate. Il bot potrebbe vendere a un avg_buy stale e perdere soldi.
- **Mitigazione attuale:** `holdings=fetch_balance()` post-S72 fa sì che il bot conosca le quantità reali. Ma `avg_buy_price` e P&L cumulativo restano calcolati dai trades in DB → divergono dal reale.

**Verdetto:** ❌ NON SHIP MAINNET senza questo fix.

## Vincoli

- Modifica isolata a `bot/exchange_orders.py` — non toccare grid_bot.py, sentinel, sherpa
- Mantenere backwards-compat con il path `filled=0` (alert_rejection comportamento identico)
- Aggiungere a `bot_events_log` un nuovo event type tipo `partial_fill` (se non esiste) per tracciare frequenza in produzione

## Decisioni delegate a CC

- Wording del nuovo log warning (PARTIAL FILL prefix, oppure semantica diversa)
- Se aggiungere alert Telegram dedicato per partial fill o riusare `_alert_rejection` con motivo diverso
- Stile del manual cleanup del trade orphan esistente (script ad hoc vs INSERT diretta)

## Decisioni che CC DEVE chiedere

- Se la suite di test del bot ha già pattern simili da copiare (per il mock di ccxt order)
- Se modifica della firma di `_normalize_order_response` rompe altri callsite (probabile no, ma verificare prima)

## Roadmap impact

**Mainnet €100 (target fine maggio/inizio giugno):** BLOCKING. Fix prima del go-live.
**Testnet:** non blocca operazioni (bot sopravvive con drift fee-in-base + reconcile script che cattura tutto), ma riduce qualità dei dati raccolti S+S nelle prossime settimane.

---

## Riferimenti

- Log evidence: `/Volumes/Archivio/bagholderai/logs/grid_BONK_USDT.log` linea ~1365 (tail -3000 mostra il pattern)
- Reconcile evidence: `~/cron_reconcile.log` su Mac Mini, run 2026-05-12T16:18:01Z
- Binance order: id=21190, qty=1,368,998 BONK, side=buy, price=$0.00000758, ts=2026-05-12T10:30:11Z
- Memorie correlate:
  - `project_bonk_testnet_slippage.md` (BONK testnet book sottile)
  - `project_s72_fee_unification_diagnosis.md` (holdings=fetch_balance() design)
  - `feedback_one_source_of_truth.md` (DB vs broker discrepanza)
