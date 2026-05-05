# Brief 46b — Logica contabile TF → Grid (coin promosse)

**Session:** 46  
**Priority:** Alta (bloccante per Brief 46a)  
**Scope:** Logica budget/P&L per coin con `managed_by = 'tf_grid'`

---

## Principio

**I soldi sono sempre di TF.** Grid è solo l'esecutore.

TF compra una coin, la passa a Grid per il trading, ma il capitale resta di proprietà TF. Grid applica la sua logica (buy dip / sell rally) ma non alloca fondi propri. Profitti e perdite vanno a TF.

---

## Flusso completo

### 1. TF compra una coin
- TF ha `tf_budget = $100`
- TF compra TRX, alloca $22.75 → `bot_config.capital_allocation = 22.75`, `managed_by = 'trend_follower'`
- Cash libero TF: $100 - $22.75 = $77.25

### 2. TRX viene promossa a Grid
- `managed_by` cambia da `'trend_follower'` a `'tf_grid'`
- `capital_allocation` resta $22.75 — **non cambia**
- Grid inizia a gestire il trading su TRX con la sua logica (griglia percentuale)
- I $22.75 restano **impegnati nel budget TF** — TF non riprende i soldi

### 3. Grid opera su TRX
- Grid compra dip / vende rally secondo la sua logica
- Ogni profitto realizzato (sell) va al P&L di **TF**, non di Grid
- Le fee di trading vanno al conteggio fee di **TF**
- Lo skim (se applicabile) va allo skim di **TF**

### 4. Grid deallocca TRX
- Quando Grid decide di deallocare (o viene forzato), vende tutto
- I $22.75 ± P&L realizzato tornano al **cash libero di TF**
- `managed_by` torna a `'trend_follower'` oppure la riga viene rimossa da `bot_config`
- TF può usare quei soldi per una nuova coin

---

## Regole contabili

| Cosa | Dove va |
|------|---------|
| `capital_allocation` di coin tf_grid | Conta come budget impegnato di **TF** |
| Profitto realizzato da Grid su coin tf_grid | P&L di **TF** |
| Perdita realizzata da Grid su coin tf_grid | P&L di **TF** |
| Fee di trading su coin tf_grid | Fee di **TF** |
| Skim su coin tf_grid | Skim di **TF** |

---

## Calcoli budget

### TF
```
cash_libero_tf = tf_budget 
                 - SUM(capital_allocation) WHERE managed_by = 'trend_follower'
                 - SUM(capital_allocation) WHERE managed_by = 'tf_grid'
```
Le coin promosse **restano** nel budget impegnato di TF.

### Grid
```
budget_grid = SUM(capital_allocation) WHERE managed_by = 'manual'
```
Grid **non include** le coin tf_grid nel suo budget. Le gestisce operativamente ma non le possiede.

---

## Calcoli Net Worth (dashboard)

### TF Net Worth
```sql
-- Include TUTTE le coin di TF: sia trend_follower che tf_grid
SELECT SUM(valore_posizioni_aperte) 
FROM trades 
WHERE symbol IN (
  SELECT symbol FROM bot_config 
  WHERE managed_by IN ('trend_follower', 'tf_grid')
)
AND config_version = 'v3';
```

### Grid Net Worth
```sql
-- Include SOLO le coin manuali
SELECT SUM(valore_posizioni_aperte) 
FROM trades 
WHERE symbol IN (
  SELECT symbol FROM bot_config 
  WHERE managed_by = 'manual'
)
AND config_version = 'v3';
```

---

## Calcoli P&L (dashboard)

### TF P&L
```sql
-- Realized: profitti da sell su coin trend_follower + tf_grid
SELECT SUM(realized_pnl) 
FROM trades 
WHERE side = 'sell' 
AND config_version = 'v3'
AND symbol IN (
  SELECT symbol FROM bot_config 
  WHERE managed_by IN ('trend_follower', 'tf_grid')
);
```

### Grid P&L
```sql
-- Realized: profitti da sell SOLO su coin manual
SELECT SUM(realized_pnl) 
FROM trades 
WHERE side = 'sell' 
AND config_version = 'v3'
AND symbol IN (
  SELECT symbol FROM bot_config 
  WHERE managed_by = 'manual'
);
```

---

## Impatto sulla dashboard (Brief 46a)

Nella sezione **TF** (sopra):
- Net Worth include coin tf_grid ✓
- P&L include coin tf_grid ✓
- Cash allocation include coin tf_grid ✓
- TRX appare con tag "→ grid" (gestita da Grid, soldi di TF)

Nella sezione **Grid** (sotto):
- Net Worth **esclude** coin tf_grid
- P&L **esclude** coin tf_grid
- Cash allocation **esclude** coin tf_grid
- TRX appare con tag "from TF" (gestita da Grid, soldi di TF)
- Grid mostra TRX come coin operativa ma **non nei suoi totali finanziari**

---

## Vincoli

- Max **2 coin** con `managed_by = 'tf_grid'` in contemporanea
- TF tiene **1 sola coin** attiva come `trend_follower` (per ora)
- `tf_budget` in `trend_config` resta **$100**, non viene mai modificato
- Il campo `managed_by` in `bot_config` è l'unica fonte di verità per la contabilità
- Non servono nuove tabelle o colonne — la logica si basa su `managed_by` esistente

---

## Checklist

- [ ] Cash libero TF calcolato correttamente (include tf_grid come impegnato)
- [ ] TF Net Worth include coin tf_grid
- [ ] Grid Net Worth esclude coin tf_grid
- [ ] TF P&L include realized da coin tf_grid
- [ ] Grid P&L esclude realized da coin tf_grid
- [ ] Alla deallocazione, il budget torna correttamente a TF
