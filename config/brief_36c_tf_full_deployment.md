# BRIEF — Session 36c: TF deploys the full budget

**Date:** 2026-04-15
**Priority:** HIGH — il TF attuale usa solo $20 su $100 di budget
**Prerequisito:** 36a/36b deployati ✅

---

## Problema osservato

Con `tf_budget=$100`, `tf_max_coins=2`, TF alloca $10 per coin T3 (10% tier cap). `capital_per_trade=$6` → sweep al primo buy → **un solo lotto da $10**, poi tapped out. Totale investito: $20 su $100.

Esempio reale (15 apr 2026, 22:32):
```
BIO/USDT  : $10 allocated, 1 buy @ $9.99 → tapped out
ORDI/USDT : $10 allocated, 1 buy @ $9.99 → tapped out
```

Budget TF utilizzato: **20%**. Inaccettabile.

## Obiettivo

Con $100 budget e 2 coin, TF deve deployare tutto:
- Split del budget sensato tra le 2 coin (50/50 o ponderato per signal_strength)
- Dentro ogni coin, `capital_per_trade` che permette **almeno 4-5 lotti** per fare grid vero
- User's example: "5 buy da $15 per un coin, 4 buy da $10 per l'altro" = $115 (troppo) → obiettivo $100 distribuito

## Cause radice

### 1. Tier caps in `allocator.py` sono pensati per 5-grid systems

```python
# Current: T3 = 10% del budget
# Con 5 coin max e $500 budget → $50 per coin (ok)
# Con 2 coin max e $100 budget → $10 per coin (insufficient)
```

I `MAX_ALLOC_PCT` della `coin_tiers` table sono calibrati per il sistema manuale (5+ bots). TF con 2 coin deve usare logica diversa.

### 2. `capital_per_trade` con floor $6 e allocation $10

```python
capital_per_trade = max(6.0, round(capital / 4, 2))
# capital=$10 → max($6, $2.50) = $6 → SWEEP al primo buy
```

Formula OK per capital≥$24, ma con $10 è degenerata.

### 3. Unit mismatch su `profit_target_pct` (bug pre-esistente, emerso con TF)

Tre viste sullo stesso campo, tre unità diverse:

| Livello | Label / valore | Significato atteso |
|---|---|---|
| Admin UI (`admin.html`) | "Min Profit %" | numero in % (es. `1` = 1%) |
| DB (`bot_config.profit_target_pct`) | default `1.0` | ambiguo — non documentato |
| grid_bot (`min_profit_pct` in `_execute_percentage_sell`) | `min_price = avg_buy * (1 + min_profit_pct)` | frazione (es. `0.01` = 1%) |

Conseguenza: per BIO/ORDI il DB default 1.0 è stato interpretato dal codice come **+100%** richiesto sopra l'avg_buy. Risultato: sell bloccato per sempre, anche con +55% di gain reale.

**Hotfix applicato 16 apr 2026 (commit 0695972)**: `apply_allocations` forza `profit_target_pct=0` nell'INSERT. I 3 bot manuali hanno sempre avuto 0 → problema dormiente fino all'arrivo di TF.

**Fix strutturale da fare in questo brief o in uno dedicato**:

Opzione A — adeguare il codice alla UI (il DB diventa "1 = 1%"):
```python
# grid_bot.py
min_price = avg_buy * (1 + min_profit_pct / 100)
```
Più intuitivo per l'utente, ma cambia il contratto in tutti i punti che leggono `min_profit_pct`.

Opzione B — adeguare la UI al codice (il DB diventa "0.01 = 1%"):
- Label admin: "Min Profit (decimal, 0.01 = 1%)"
- Convertire ogni valore esistente × 0.01

Opzione A è probabilmente più user-friendly. Da coordinare con il campo `sell_pct`/`buy_pct` che **già** sono trattati come % (`/100` nel codice) per coerenza.

## Proposta di fix

### 1. Budget splitting per TF (ignore tier caps in live allocation)

Nuova logica in `decide_allocations` o dedicata a TF:

```python
# Per ogni BULLISH candidato (fino a tf_max_coins), alloca:
capital = tf_budget / tf_max_coins  # equal split
# O ponderato:
capital = tf_budget * (signal_strength / sum_of_selected_strengths)
```

Con `tf_budget=$100`, `tf_max_coins=2`:
- Equal: $50 + $50
- Weighted (BIO 43.0, ORDI 40.0): $51.80 + $48.20

I tier caps diventano un **limite superiore di sicurezza**, non il metodo di calcolo. Es: `capital = min(equal_split, tier_cap * tf_budget)`.

### 2. Formula `capital_per_trade` rifinita

Con allocation ≥ $20 la formula attuale funziona:
- $50 → max($6, $12.5) = $12.5 → 4 lot
- $30 → max($6, $7.5) = $7.5 → 4 lot
- $20 → max($6, $5) = $6 → 3 lot

Lasciare la formula `max($6, capital/4)` invariata, ora che allocation è più alta.

### 3. Gestire caso "TF sceglie 1 solo coin"

Se solo 1 BULLISH nel universe → alloca tutto il budget a quello (`$100 → $25/trade → 4 lot`).

### 4. `buy_pct` / `sell_pct` adattivi (non più hardcoded)

Oggi in `apply_allocations`:
```python
if signal == "BULLISH":  buy_pct=1.5, sell_pct=1.2
if signal == "BEARISH":  buy_pct=2.0, sell_pct=0.8
else:                    buy_pct=1.5, sell_pct=1.0
```

Problema: un BULLISH con `signal_strength=43` merita swing più larghi di uno con strength 15. E un coin ad alta volatilità (ATR% alto) deve avere grid più largo per non vendere/comprare a ogni starnuto.

Nuova logica basata su ATR% e signal_strength:

```python
# ATR% = atr / price * 100 (già nel coin dict dopo classify)
atr_pct = (coin["atr"] / coin["price"]) * 100 if coin["price"] > 0 else 1.0

if signal == "BULLISH":
    # Buy al dip tipico (~1x ATR), sell al target più ambizioso (~1.5x ATR)
    # Cap tra 1.0 e 5.0 per buy, tra 1.2 e 5.0 per sell (più ambizioso che conservativo)
    buy_pct  = max(1.0, min(5.0, atr_pct * 1.0))
    sell_pct = max(1.2, min(5.0, atr_pct * 1.5))
elif signal == "BEARISH":
    # In bearish idealmente TF non dovrebbe allocare — ma se capita, grid conservativo
    buy_pct  = max(1.5, min(5.0, atr_pct * 1.5))
    sell_pct = max(0.5, min(2.0, atr_pct * 0.8))
else:  # SIDEWAYS
    buy_pct  = max(1.0, min(3.0, atr_pct * 0.8))
    sell_pct = max(1.0, min(3.0, atr_pct * 1.0))
```

**Esempi concreti:**
| Coin | ATR% | Signal | buy_pct | sell_pct |
|---|---|---|---|---|
| BIO (volatile) | 3.5% | BULLISH | 3.5 | 5.0 (capped) |
| ETH (stabile) | 1.2% | BULLISH | 1.2 | 1.8 |
| Meme pump | 8% | BULLISH | 5.0 (capped) | 5.0 (capped) |
| ADA quieto | 0.8% | SIDEWAYS | 1.0 (floor) | 1.0 (floor) |

Così su un BULLISH forte + volatile come BIO, il TF punta a +5% (grid più ambizioso), non +1.2%. E su un quieto stabile come ETH, sta sui suoi 1.2/1.8 per cycli più frequenti.

**Nota implementativa**: `atr` è già nel `coin` dict dopo `classify_signal()`. Passare il coin intero al decision builder o estrarre atr/price prima di chiamare `apply_allocations`. Serve includere `atr` nel `config_snapshot` dentro `_make_decision` così `apply_allocations` ce l'ha disponibile senza ricalcolare.

## Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Riscrivere logica di allocazione budget per TF (ignore tier%, use equal/weighted split) |
| `bot/trend_follower/trend_follower.py` | Nessun cambio (già passa `tf_budget` e `tf_max_coins`) |

## Safety

- **NON toccare** BTC/SOL/BONK — whitelist e filtro `managed_by=trend_follower` già in atto
- Se TF cambia coin al prossimo scan, il DEALLOCATE + ALLOCATE libera/rialloca capitale correttamente (già testato)
- Sanity cap: non allocare MAI più di `tf_budget / tf_max_coins * 1.5` a un singolo coin (evita che tutto finisca su uno solo se signal_strength è skewed)

## Test

Pre-flip (dry_run=true se già live):
- [ ] Scan mostra `WOULD ALLOCATE` con capital=$50 ca. per coin, non più $10
- [ ] Nessuna scrittura bot_config

Post-flip (dry_run=false):
- [ ] TF alloca 2 coin con ~$50 ciascuno
- [ ] Grid runner avvia 2 bot con capital_per_trade ~$12.5
- [ ] Primo buy ~$12.5, secondo buy al dip successivo → multi-lot confirmed
- [ ] `/tf` dashboard mostra "Capacity usage: 25%" dopo primo buy, non 100%
- [ ] `bot_config` di un TF coin volatile (ATR>3%) ha `buy_pct>2` e `sell_pct>3` — non più 1.5/1.2 fisso
- [ ] `bot_config` di un TF coin stabile (ATR<1.5%) ha `buy_pct<2` e `sell_pct<2.5` — adattivo ma non ambizioso

Se in questo brief si risolve anche l'unit mismatch di `profit_target_pct`:
- [ ] Admin UI: impostare `profit_target_pct=1` su un bot test → grid_bot richiede +1% (non +100%) per vendere
- [ ] TF INSERT può rimuovere il forzato `profit_target_pct=0` (o lasciarlo per sicurezza)

## Scope rules

- Non modificare `coin_tiers` table (resta utile per future logiche)
- Non modificare la tabella `trend_config` (tf_budget/tf_max_coins restano)
- Push quando done

## Commit format

```
feat(trend-follower): deploy full tf_budget — equal split across tf_max_coins
```

---

## Nota — limite strutturale del grid (out of scope per 36c)

Anche con il 36c applicato, il grid_bot resta **strutturalmente conservativo**. Cattura piccoli cicli (buy al −buy_pct, sell al +sell_pct) ma quando capita un pump grosso come BIO +55% lo perde comunque, perché vende al primo tick del `sell_pct` (che in 36c max vale ~5% sui coin più volatili).

Con il 36c:
- Passiamo da +1.2% fisso a max +5% adattivo → qualche punto percentuale in più ma sempre limitato al primo trigger
- Non cattura i movimenti >5% nella stessa ondata

Per cavalcare pump veri serve logica diversa, fuori dal grid puro:

- **Trailing stop**: vendi quando il prezzo torna −X% dal massimo locale (es. −2%). Così se BIO pumpava a +55% poi ritracciava, il bot vendeva a +53% invece di +5%.
- **Take-profit scalato**: vendi 25% a +5%, 25% a +10%, 50% con trailing. Cattura sia il ciclo breve sia il pump.
- **Modalità "riding"**: opzionale per i soli coin TF con signal_strength molto alto, disabilitando temporaneamente il grid e attivando trailing.

Candidato brief futuro: **36d — TF riding mode for strong bullish**. Da valutare dopo qualche settimana di dati TF con 36c, così si capisce se i pump catturati giustificano la complessità.
