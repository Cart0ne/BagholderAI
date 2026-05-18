# Brief 79b — Riattivazione Trend Follower: Tier 1-2 Only, Tier 3 Off

**Date:** May 18, 2026  
**Author:** CEO (Claude)  
**Based on:** PROJECT_STATE.md aggiornato 2026-05-15 (S78 chiusura)  
**Priority:** Media — opportunità di mercato, non urgenza tecnica  
**Estimated effort:** 30–45 minuti  

---

## Context

TF è spento dal ~8 maggio (orchestrator `ENABLE_TF=false`). Il brainstorming S68 (Memo_Brainstorming_2026-05-11.md) ha identificato che i problemi TF (death spiral, win/loss asymmetry, distance filter paralysis) sono **concentrati in Tier 3** (shitcoin). Tier 1-2, gestiti via tf_grid handoff a Grid, non hanno questi problemi.

Situazione attuale:
- Sentinel slow loop: regime **"fear"**, opportunity score **65**
- Sherpa (DRY_RUN) propone parametri più aggressivi (buy_pct 1.8%, idle 2h)
- BTC ~$76.650, -1.7% 24h — il mercato sembra stabilizzarsi
- Grid attivi ma rallentati (SOL fermo da 6 giorni)
- Counterfactual tracker fermo dal 8 maggio — persi 10 giorni di dati

Board decision (Max, S79): "Lo attiverei e basta, al limite senza allocare Tier 3, ma Tier 1 e 2 li passerei a Grid. Magari recuperiamo qualcosa visto che il mercato sembra stabilizzato."

---

## What to change

### 1. Orchestrator: riattivare TF

**File:** `bot/orchestrator.py` (o file config/env dove `ENABLE_TF` è definito)

Impostare `ENABLE_TF = True`. Verificare che il brain flag venga loggato correttamente al boot:
```
Brain flags: TF=True  SENTINEL=True  SHERPA=True
```

### 2. Disabilitare Tier 3 via config

**Table:** `trend_config` su Supabase

```sql
UPDATE trend_config 
SET tf_tier3_weight = 0,
    updated_at = NOW()
WHERE id = (SELECT id FROM trend_config LIMIT 1);
```

Setting `tf_tier3_weight = 0` fa sì che il classifier non assegni mai weight a candidati Tier 3. Il codice di `classifier.py` e `allocator.py` dovrebbe già gestire weight=0 come "non considerare" — **CC deve verificare** che un weight 0 non causi divisione per zero o comportamento inatteso nel ranking.

### 3. Verifica tf_grid handoff

Quando TF seleziona un Tier 1 o Tier 2, lo alloca con `managed_by='tf'` poi lo passa a Grid management come `managed_by='tf_grid'` (commit `502e88a`). Questo flusso è già testato e live pre-spegnimento. CC verifica che il codice non sia stato toccato da refactoring post-S68.

### 4. Verifica counterfactual tracker

Il counterfactual tracker (`bot/trend_follower/counterfactual.py`) deve riprendere a scrivere in `counterfactual_log`. Ci sono 639 record dal 4-8 maggio. Verificare che:
- La tabella non sia stata droppata dalla retention policy
- Il tracker parta automaticamente con TF (dovrebbe)
- I nuovi record abbiano il contesto regime di Sentinel Sprint 2 (se disponibile nel tracker)

---

## Parametri attuali trend_config (non modificare salvo tf_tier3_weight)

| Parametro | Valore | Note |
|-----------|--------|------|
| tf_budget | 100 | Budget allocabile TF |
| tf_max_coins | 3 | Max coin simultanei (T1+T2 ora) |
| tf_tier1_weight | 40 | Mantieni |
| tf_tier2_weight | 35 | Mantieni |
| tf_tier3_weight | **25 → 0** | UNICA MODIFICA |
| tf_tier1_lots | 4 | Mantieni |
| tf_tier2_lots | 3 | Mantieni |
| tf_entry_max_distance_pct | 12 | Distance filter — mantieni |
| tf_stop_loss_pct | 2.5 | Mantieni |
| tf_trailing_stop_pct | 2 | Mantieni |
| tf_trailing_stop_activation_pct | 1.5 | Mantieni |
| dry_run | false | TF opera normalmente su testnet |

---

## Decisions delegated to CC

- Verificare che `tf_tier3_weight = 0` non causi errori (division by zero, empty list, ecc.)
- Se serve un guard esplicito (es. `if weight > 0`) aggiungerlo
- Dove vive `ENABLE_TF` (env var, config file, hardcoded) — il punto esatto da modificare
- Se il counterfactual tracker cattura il regime Sentinel o solo price/EMA

## Decisions CC MUST ask Board

- Se durante la verifica emerge che tf_grid handoff è stato rotto da refactoring post-S68, FERMARSI e chiedere al Board prima di fixare — il fix potrebbe essere non banale
- Se `tf_tier3_weight = 0` causa un crash o comportamento imprevedibile nel classifier, chiedere al Board se preferiamo un valore minimo (es. 1) o un flag esplicito `tf_tier3_enabled = false`

---

## Expected output at end of session

1. `ENABLE_TF = True` nel config dell'orchestrator
2. `tf_tier3_weight = 0` in Supabase `trend_config`
3. Commit + push
4. Restart orchestrator su Mac Mini
5. Verificare nei log:
   - TF avvia scan loop
   - Counterfactual tracker scrive in `counterfactual_log`
   - Se trova candidati T1/T2, li alloca (o logga perché skippati da distance filter)
   - Nessun candidato T3 appare nel ranking

---

## Constraints

- Do NOT modify `tf_tier1_weight`, `tf_tier2_weight`, o qualsiasi altro parametro in `trend_config`
- Do NOT touch Sentinel/Sherpa code
- Do NOT modify Grid bot parameters (`bot_config`)
- Do NOT modify the distance filter threshold (12%) — è un parametro separato da valutare col Board
- Do NOT modify `grid_bot.py` (quello è Brief 79a, separato)

---

## Roadmap impact

Aggiornare PROJECT_STATE.md §7: "Brain TF **on** (Tier 1-2 only, Tier 3 weight=0)".

Il ritorno di TF è un segnale positivo per la narrativa: il cervello #2 riparte dopo la convalescenza ("dal dottore"), ma con una limitazione precisa. Materiale per il diary.

---

## Risk assessment

**Rischio basso.** TF Tier 1-2 via tf_grid è il flusso più testato del Trend Follower. Il distance filter a 12% + stop-loss a 2.5% + trailing stop sono tutti guard attivi. Il worst case è che TF non trovi candidati (distance filter blocca tutto in regime "fear") — il che produce dati counterfactual utili senza rischio.

**Scenario di attenzione:** Se il mercato rimbalza velocemente, TF potrebbe allocare 2-3 coin T1/T2 contemporaneamente, impegnando budget dal tf_budget (100 USDT testnet). Questo è il comportamento atteso, non un bug — ma Max deve esserne consapevole per non allarmarsi vedendo allocazioni multiple in rapida successione.
