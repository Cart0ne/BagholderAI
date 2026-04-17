# BRIEF — Session 36d: Unit mismatch fix per `profit_target_pct`

**Date:** 2026-04-16
**Priority:** MEDIUM — non urgente operativamente (tutti i bot hanno valore 0), ma è un bug strutturale latente che esploderebbe al primo bot creato con valore ≠ 0
**CC working machine:** MacBook Air (locale)
**Production machine:** Mac Mini (deploy via git pull SSH)
**Prerequisito:** 36c deployato ✅
**Scope rule:** SOLO fix del contratto unit di `profit_target_pct`. NON toccare buy_pct/sell_pct, NON aggiungere logica ATR (→ brief 36e).

---

## Problema

Il campo `profit_target_pct` ha **tre interpretazioni diverse** nello stesso sistema:

| Livello | Interpretazione |
|---|---|
| Admin UI (`admin.html`) | Numero in %, es. `1` = 1% |
| DB `bot_config.profit_target_pct` | Default `1.0`, ambiguo non documentato |
| `grid_bot._execute_percentage_sell` | Frazione, es. `0.01` = 1%. Calcolo: `min_price = avg_buy * (1 + min_profit_pct)` |

**Conseguenza concreta**: se Max imposta da admin UI il valore `1` su un bot, il DB salva `1.0`, il grid_bot legge `1.0` e calcola `min_price = avg_buy * (1 + 1.0)` = avg_buy × 2 → richiede **+100%** per vendere → sell bloccato per sempre.

È esattamente quello che è successo a BIO/ORDI prima dell'hotfix S36 (commit `0695972`) che forza `profit_target_pct=0` negli INSERT del TF.

## Stato attuale (verificato in DB il 16 aprile 2026)

Tutti i 5 bot attivi hanno `profit_target_pct=0`:
- BTC, SOL, BONK (manuali)
- AXL, MBOX (TF, via hotfix forzato)

**Quindi il fix è NO-OP sull'operatività attuale.** Nessun bot cambia comportamento. Il valore in uso continua a richiedere `min_price = avg_buy * (1 + 0) = avg_buy` → nessun min profit, esattamente come oggi.

Il fix serve a **rendere il campo utilizzabile in futuro** (es. quando 36e introdurrà valori ATR-derivati, o se Max vorrà mai settare un min profit reale via admin).

## Decisione di design

**Opzione scelta: A** — il codice si adegua alla UI, il DB diventa "1 = 1%".

Motivi:
1. **Coerenza con `buy_pct` e `sell_pct`**, che sono già trattati come percentuali (il codice usa `/100` per convertire)
2. **User-friendly**: chi imposta da admin pensa in percentuali, non in decimali
3. **Migration zero**: con tutti i valori attuali a 0, lo zero in entrambe le interpretazioni dà lo stesso risultato. Nessun dato da convertire

Opzione B (label UI "decimal 0.01") **scartata** — controintuitiva e richiederebbe migration dei dati esistenti se in futuro fossero valorizzati.

## Fix puntuale

### File principale: `bot/grid_bot.py`

Funzione `_execute_percentage_sell` (o ovunque `min_profit_pct` venga usato per calcolare `min_price`).

**Before:**
```python
min_price = avg_buy * (1 + min_profit_pct)
```

**After:**
```python
min_price = avg_buy * (1 + min_profit_pct / 100)
```

### Cambio default DB

Cambiare il default della colonna `bot_config.profit_target_pct` da `1.0` a `0`:

```sql
ALTER TABLE bot_config
ALTER COLUMN profit_target_pct SET DEFAULT 0;
```

Motivo: con la nuova interpretazione, il default `1.0` significherebbe "+1% sopra avg_buy" — un comportamento inaspettato per chi crea un bot senza specificare il valore. Default `0` = "no min profit" è la baseline sicura.

**Apply via Supabase MCP** (CC può chiedere a Claude di farlo) o via migration nel repo se preferisci tracciare. Suggerimento: `apply_migration` con nome `set_profit_target_pct_default_to_zero`.

### Allocator del TF

In `bot/trend_follower/allocator.py` c'è l'hotfix `profit_target_pct=0` forzato nell'INSERT (commit `0695972`).

**Decisione:** **lascia in place**. Il forzato a 0 ora ha senso semantico (con la nuova interpretazione), prima era un patch difensivo. Non è ridondante: rende esplicito che il TF non vuole min profit, indipendentemente dal default DB.

## Scoperta preventiva (richiesta a CC)

**PRIMA di applicare il fix**, CC deve cercare nel codebase tutti i punti che leggono o scrivono `profit_target_pct` o `min_profit_pct`:

```bash
grep -rn "profit_target_pct\|min_profit_pct" bot/ admin/ web/
```

Per ogni occorrenza, verificare:
- È una **lettura** dal DB → applicare `/100` se viene usato come fattore moltiplicativo
- È una **scrittura** dal DB → assicurarsi che il valore inserito sia in percentuale (es. `1` per 1%, non `0.01`)
- È nel **frontend** → verificare che label e input siano coerenti con la nuova convenzione

CC riporta a Max le occorrenze trovate **prima** di committare, così confermiamo che nessun punto è stato dimenticato.

## Files probabili (da confermare con grep sopra)

| File | Probabile cambio |
|---|---|
| `bot/grid_bot.py` | Fix calcolo `min_price` |
| `admin/admin.html` o equivalente | Verificare che l'input mostri "% (es. 1 = 1%)" e non sia ambiguo |
| `bot/trend_follower/allocator.py` | Lasciare hotfix `profit_target_pct=0` |
| Eventuali altri punti che assumono frazione | Adeguare |

## Files da NON toccare

- `buy_pct`, `sell_pct` (già coerenti come %)
- BTC/SOL/BONK e AXL/MBOX (bot attivi, non serve cambiare config)
- Logica TF di selezione coin (→ 36e)
- Tabelle `coin_tiers`, `trend_config`

## Test pre-deploy

Test isolato di `_execute_percentage_sell` con vari valori:

- [ ] `profit_target_pct=0` → `min_price == avg_buy` (no min profit, comportamento attuale)
- [ ] `profit_target_pct=1` → `min_price == avg_buy * 1.01` (richiede +1%)
- [ ] `profit_target_pct=2.5` → `min_price == avg_buy * 1.025` (richiede +2.5%)
- [ ] `profit_target_pct=100` → `min_price == avg_buy * 2` (richiede +100%, edge case ma deve funzionare)

## Test post-deploy

Verifiche in produzione:

- [ ] Nessun bot attivo cambia comportamento (tutti hanno valore 0 → calcolo identico)
- [ ] Settare manualmente `profit_target_pct=1` su BONK via admin (o SQL): nei prossimi 24h deve vendere solo se il prezzo supera `avg_buy * 1.01`. **Se test ok, riportare a 0.**
- [ ] Verificare con SELECT che il default DB sia 0:
  ```sql
  SELECT column_default FROM information_schema.columns 
  WHERE table_name='bot_config' AND column_name='profit_target_pct';
  ```

## Rollback plan

Se rompe qualcosa (ma è difficile, dato lo stato 0 ovunque):

```bash
# Da MacBook Air
git revert <commit_hash>
git push origin main

# Su Mac Mini via SSH
ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull'
# + restart processi (VNC o SSH come da brief 36c)
```

ALTER TABLE rollback (se hai cambiato il default):
```sql
ALTER TABLE bot_config ALTER COLUMN profit_target_pct SET DEFAULT 1.0;
```

## Deploy workflow

Identico a 36c (vedi brief precedente). Riassunto:
1. Dev + test su MacBook Air
2. Commit + push su `main`
3. `ssh mac-mini 'cd /Volumes/Archivio/bagholderai && git pull'`
4. Restart processi (VNC by Max, o SSH by CC)

## Commit format

```
fix(grid-bot): correct profit_target_pct unit semantics

DB and admin UI use percentage (1 = 1%). grid_bot was
treating the value as fraction (0.01 = 1%), causing 
profit_target_pct=1 to require +100% above avg_buy.
Fix: divide by 100 in min_price calculation.
Also: change DB default from 1.0 to 0 to match the
new semantics (0 = no min profit, safe baseline).
```

---

## Out of scope (brief successivi)

- **36e**: rotazione coin TF (logica ibrida — swap solo se coin attivo in profit + nuovo candidato +15 strength + cooldown) + **adaptive buy_pct/sell_pct via ATR**
- **36f**: trailing stop per cavalcare pump >5%
