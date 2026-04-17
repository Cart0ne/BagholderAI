# BRIEF — 36e integration: tighter ATR clamps

**Date:** 2026-04-17
**Type:** Mini-patch to brief 36e v2 (already deployed)
**Priority:** MEDIUM — corregge un tuning che in pratica si rivela troppo largo per la filosofia di trading
**Prerequisito:** 36e v2 deployato ✅
**Target branch:** `main` (push diretto, niente PR)
**Deploy:** on-demand
**Working machine:** MacBook Air → Mac Mini via `git pull`

---

## Contesto

Con TST/USDT allocata questa mattina (17 apr) abbiamo visto che i clamp di 36e v2 (`sell_pct ∈ [1.0, 8.0]`, `buy_pct ∈ [1.0, 10.0]`) producono valori troppo larghi per coin volatili:

- TST al momento dell'allocate: ATR% = 13.16% → `sell_pct = 8.0` (clamp), `buy_pct = 10.0` (clamp)
- MOVR appena allocata: `sell_pct = 8.0`, `buy_pct = 10.0` (stesso pattern)
- Grid con ampiezze del 10% sul buy significa che il bot aspetta dip enormi prima di scalare — opposto della filosofia CEO ("compra su piccoli dip, vendi al target")

La filosofia CEO per TF (coin normali + shitcoin, stablecoin escluse perché non entrano nel TF): **buy non sopra 1.5-2%, sell non sopra 6%, sempre. La formula ATR×k modula dentro questi tetti.**

---

## Fix

In `bot/trend_follower/allocator.py`, funzione `_adaptive_steps`:

```python
# PRIMA (36e v2)
SELL_PCT_MIN, SELL_PCT_MAX = 1.0, 8.0
BUY_PCT_MIN,  BUY_PCT_MAX  = 1.0, 10.0

# DOPO (36e integration)
SELL_PCT_MIN, SELL_PCT_MAX = 1.0, 6.0   # CEO filosofia: mai sell > 6%
BUY_PCT_MIN,  BUY_PCT_MAX  = 1.0, 2.0   # CEO filosofia: mai buy > 2%
```

Tutto il resto di `_adaptive_steps` resta invariato: `K_SELL=1.2`, `K_BUY=0.8`, bearish buy-widen +10%, fallback ATR=0 a 1.5/1.2.

### Effetto pratico con i nuovi clamp

| Coin | ATR% | sell_pct (k=1.2) | buy_pct (k=0.8) | Note |
|---|---|---|---|---|
| ETH-like | 1.5% | 1.8 | 1.2 | Variabilità preservata |
| ORDI-like | 3.0% | 3.6 | 2.0 (clamp) | Buy clampato |
| BIO-like | 6.0% | 6.0 (clamp) | 2.0 (clamp) | Entrambi clampati |
| TST-like | 13% | 6.0 (clamp) | 2.0 (clamp) | Entrambi saturati |

**Nota desiderata (CEO-confirmed)**: sopra `ATR% ≈ 2.5%`, il `buy_pct` satura al clamp 2.0% → de facto la modulazione ATR sul buy scompare per coin mediamente/alte volatili. È **voluto**: filosofia CEO è "buy aggressivo sempre, indipendentemente dalla coin". La modulazione ATR resta significativa sui sell, dove il range 1-6% è sfruttabile.

---

## Applicazione alle allocation esistenti

Oggi (17 apr 12:30 UTC) le TF-allocation attive sono:

- **MBOX/USDT** (quasi sicuramente con buy/sell ai vecchi clamp 10/8)
- **MOVR/USDT** appena allocata con buy=10 / sell=8

**Decisione CEO-locked**: **non** fare un mass-update al deploy. Le allocation attive restano sui parametri vecchi finché:
- vengono deallocate per BEARISH
- vengono swappate da una coin più forte (rotation)
- CEO interviene manualmente via admin

Motivo: il mass-update cambia la config di un bot vivo con lot aperti → comportamento potenzialmente strano se un lot ha appena superato il vecchio target. Meglio lasciar completare il ciclo naturale.

CC può lasciare `MOVR` e `MBOX` come sono. Le prossime allocation (swap, nuova ALLOCATE) useranno i clamp nuovi.

Se invece CC ritiene che il mass-update sia safe (i lot si valutano individualmente e il cambio di `sell_pct` in `bot_config` riduce la soglia, quindi semmai ACCELERA sell invece di bloccarli), può proporre una riga SQL one-shot manuale che noi valuteremo — **ma non eseguirla nel deploy**.

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | 2 costanti: `SELL_PCT_MAX=6.0`, `BUY_PCT_MAX=2.0` |

---

## Test

Unit test minimal (o adattare i test 36e v2 esistenti):

- [ ] ATR%=1.5, signal=BULLISH → sell=1.8, buy=1.2 (dentro clamp, variabilità preservata)
- [ ] ATR%=3.0, signal=BULLISH → sell=3.6, buy=2.0 (buy clampato)
- [ ] ATR%=6.0, signal=BULLISH → sell=6.0 (clampato), buy=2.0 (clampato)
- [ ] ATR%=13, signal=BULLISH → sell=6.0 (clampato), buy=2.0 (clampato)
- [ ] ATR%=0 fallback → sell=1.2, buy=1.5 (invariato)

---

## Rollback

```bash
git revert <commit_hash>
git push origin main
ssh max@<mac-mini> 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator
```

Reverting riporta i clamp a 8/10. Nessuna migration DB.

---

## Commit format

```
fix(trend-follower): tighter ATR clamps per CEO trading philosophy

sell_pct max 8.0 → 6.0
buy_pct  max 10.0 → 2.0

The 36e v2 clamps were calibrated on raw ATR range without accounting
for the CEO's trading philosophy ("buy small dips, sell at 5-6% target").
Observed on TST (ATR%=13): both buy and sell saturated at old clamps,
producing a grid with 10%/8% steps — opposite of the small-scale
accumulator the CEO runs manually on BTC/SOL/BONK.

New clamps enforce the ceiling. ATR×k formula and strength-based
variability still operate inside the clamps (significant on sell,
saturated on buy for all coins with ATR% > 2.5% — intentional).

Existing active allocations (MBOX, MOVR) are NOT mass-updated: they
keep their current config until natural rotation/deallocation.
```

---

## Out of scope

- Modulazione strength-based esplicita (lasciata implicita via formula ATR; future brief se si rivela necessaria)
- Mass-update di bot_config su allocation esistenti
- Clamp differenziati per tier (large/mid/small cap)
- Stablecoin pair handling (non allocate dal TF attuale)
