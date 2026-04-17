# BRIEF — Session 36c: TF deploya tutto il budget

**Date:** 2026-04-16
**Priority:** HIGH — il TF attuale usa solo $20 su $100 di budget
**CC working machine:** MacBook Air (locale)
**Production machine:** Mac Mini (deploy via git pull SSH)
**Prerequisito:** 36a/36b deployati ✅
**Scope rule:** SOLO budget splitting. Profit target, step adattivi, rotazione coin → brief separati (36d, 36e).

---

## Problema osservato

Con `tf_budget=$100` e `tf_max_coins=2`, il TF alloca solo **$10 per coin** (10% tier cap T3). Con `capital_per_trade=$6`, il primo buy sweepa quasi tutta l'allocation → bot tapped out al primo trade.

Esempio reale (15 apr 2026, 22:32):
```
BIO/USDT  : $10 allocated, 1 buy @ $9.99 → tapped out
ORDI/USDT : $10 allocated, 1 buy @ $9.99 → tapped out
```

Budget TF utilizzato: **20%**. Inaccettabile.

## Obiettivo

Con $100 budget e 2 coin, TF deve allocare **$50 per coin** e fare **almeno 4 lot** per coin prima di esaurirsi.

Risultato atteso:
- BIO/USDT: $50 allocated, capital_per_trade ~$12.50, 4 lot disponibili
- ORDI/USDT: $50 allocated, capital_per_trade ~$12.50, 4 lot disponibili
- Capital deployed dopo primo buy ciclo: ~25% (non 100%)

## Causa radice

`allocator.py` calcola allocation usando i `MAX_ALLOC_PCT` della tabella `coin_tiers` (T3 = 10% del budget). Questi tier sono pensati per il sistema manuale a 5 grid con $500 di budget, dove $50 per coin ha senso. Per il TF con 2 coin e $100, lo stesso 10% diventa $10 → degenere.

## Fix

### 1. Budget splitting equal in TF (bypass tier caps)

In `bot/trend_follower/allocator.py`, nella funzione che calcola allocation per i coin selezionati dal TF, sostituire la logica tier-based con:

```python
# Per i coin selezionati dal TF:
capital_per_coin = tf_budget / tf_max_coins  # equal split

# Sanity cap: max 1.5x equal share su un singolo coin
# (caso limite: se solo 1 BULLISH disponibile, alloca tutto a quello)
sanity_cap = (tf_budget / tf_max_coins) * 1.5
if num_selected_coins == 1:
    capital_per_coin = tf_budget  # alloca tutto al singolo coin
else:
    capital_per_coin = min(tf_budget / num_selected_coins, sanity_cap)
```

I tier caps della tabella `coin_tiers` restano per il sistema manuale, **non si toccano**.

### 2. Verifica formula `capital_per_trade`

Lasciare invariata la formula esistente `max($6, capital/4)`.

Verifica che con allocation $50 produca 4 lot da $12.50:
- $50 → max($6, $12.50) = **$12.50 → 4 lot** ✅
- Caso "1 coin solo" → $100 → max($6, $25) = $25 → 4 lot da $25 ✅

## Deploy workflow

CC lavora in locale su MacBook Air:

1. **Sviluppo + test locali** su MacBook Air (`source venv/bin/activate` nella cartella repo locale)
2. **Test pre-deploy** con `dry_run=true` (vedi sezione Test pre-deploy sotto)
3. **Commit + push su `main`** quando tutti i test passano
4. **Deploy su Mac Mini via SSH:**
   ```bash
   ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull'
   ```
5. **Restart processi su Mac Mini** (scegliere una):
   - **Opzione A**: Max riavvia manualmente via VNC
   - **Opzione B**: CC riavvia via SSH usando il venv del Mac Mini:
     ```bash
     ssh mac-mini 'cd /Volumes/Archivio/bagholderai && source venv/bin/activate && <comando restart orchestrator>'
     ```

CC, decidi tu opzione A o B in base a quanto sei sicuro del comando di restart. In dubbio → opzione A (Max via VNC).

## Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | Riscrivere logica allocation per TF: equal split + sanity cap, bypass tier% |

## Files da NON toccare

- `bot/trend_follower/trend_follower.py` (già passa `tf_budget` e `tf_max_coins`)
- Tabella `coin_tiers` (resta valida per sistema manuale)
- Tabella `trend_config` (tf_budget/tf_max_coins restano)
- BTC/SOL/BONK e qualsiasi bot manuale (whitelist + filtro `managed_by=trend_follower` già attivo)
- `profit_target_pct` (brief 36d separato)
- `buy_pct`/`sell_pct` (brief 36d separato)

## Test pre-deploy

Prima del flip live, lanciare con `dry_run=true`:

- [ ] Scan mostra `WOULD ALLOCATE` con capital ~$50 per coin (non $10)
- [ ] Caso "1 BULLISH solo": `WOULD ALLOCATE` mostra $100 al singolo coin
- [ ] Nessuna scrittura su `bot_config`
- [ ] Nessun bot manuale (BTC/SOL/BONK) appare nei log allocator

## Test post-deploy

Dopo flip live:

- [ ] TF alloca 2 coin con ~$50 ciascuno (verificare in `bot_config` con query: `SELECT symbol, capital_allocated, capital_per_trade FROM bot_config WHERE managed_by='trend_follower'`)
- [ ] `capital_per_trade` ~$12.50 per ogni TF coin
- [ ] Primo buy ~$12.50, NON sweep dell'intera allocation
- [ ] Dopo primo buy: `/tf` dashboard mostra capacity usage ~25% (non 100%)
- [ ] Bot continua a fare buy successivi al dip (verificare in `trades` table dopo qualche ora)

## Rollback plan

Se rompe qualcosa (da MacBook Air):

```bash
# 1. Revert in locale
git revert <commit_hash>
git push origin main

# 2. Pull su Mac Mini via SSH
ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull'

# 3. Restart processi (opzioni):
#    a) Max via VNC riavvia manualmente
#    b) CC via SSH: ssh mac-mini 'cd /Volumes/Archivio/bagholderai && source venv/bin/activate && <restart command>'
```

I bot manuali NON sono toccati, quindi un rollback del TF non impatta BTC/SOL/BONK.

## Telemetria continua (per misurare il fix)

Aggiungere al `/tf` dashboard (può essere brief micro a parte se preferisci) un campo:
- `Capital deployed: $X / $100 (Y%)` — dovrebbe stare tra 25% e 100% in operatività normale, NON fisso a 20%

## Commit format

```
feat(trend-follower): equal budget split across tf_max_coins

Bypass tier% caps for TF allocation. With tf_budget=$100 and
tf_max_coins=2, alloca $50/coin instead of $10/coin (T3 cap).
Fixes tapped-out-at-first-buy issue.
```

## Push

Push diretto su `main` quando done. Niente PR (siamo solo io e te).

---

## Out of scope (brief successivi)

- **36d**: fix unit mismatch `profit_target_pct` (DB 1.0 letto come 100%) + step vendita adattivi via ATR
- **36e**: rotazione coin TF (logica ibrida — swap solo se coin attivo in profit + nuovo candidato +15 strength + cooldown)
- **36f**: trailing stop per cavalcare pump grossi (>5%)
