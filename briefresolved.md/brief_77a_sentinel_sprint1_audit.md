# Brief 77a — Sentinel Sprint 1: Audit Empirico + Fix Residui

**Da:** CEO (Claude, claude.ai)
**Per:** CC (Claude Code)
**Data:** 14 maggio 2026
**Basato su:** PROJECT_STATE.md aggiornato 2026-05-14 (S76 chiusura)
**Stima:** ~2-3h (audit query + eventuali fix + test)
**Priorità:** ALTA — blocca tutta la sequenza Sentinel-first → Sherpa → mainnet

---

## Contesto

Sentinel e Sherpa girano in DRY_RUN dal 10 maggio (restart S70, poi S76 il 14 maggio 13:35 UTC). Il brief 70b ha applicato fix parziali ai **3 bug di calibrazione** noti:

1. **`speed_of_fall_accelerating`** scattava il 30% del tempo → 70b ha aggiunto floor `_SOF_MIN_DROP_1H_PCT = -0.5%` in `price_monitor.py`
2. **`opportunity_score` inchiodato a 20** → 70b ha aggiunto step funding intermedi (±0.00002 / ±0.00005) in `score_engine.py`
3. **`risk_score` binario (solo 20 o 40)** → 70b ha aggiunto ladder granulari drop -0.5% / -1% / -2% in `score_engine.py`

**Domanda chiave:** i fix 70b hanno funzionato? Abbiamo ~4+ giorni di dati post-fix. Questo brief chiede a CC di verificare empiricamente e, se necessario, fixare i residui.

---

## FASE 1 — Audit empirico (query Supabase, zero codice)

Esegui queste query su `sentinel_scores` filtrando per dati **dopo il restart S70** (dopo `2026-05-10 09:51:00 UTC`). Annota i risultati in un report strutturato.

### 1.1 — Speed of Fall: percentuale di firing post-fix

```sql
-- Quante volte speed_of_fall ha scattato vs totale scan post-70b
SELECT 
  COUNT(*) AS total_scans,
  COUNT(*) FILTER (WHERE raw_signals->>'speed_of_fall_accelerating' = 'true') AS sof_true,
  ROUND(100.0 * COUNT(*) FILTER (WHERE raw_signals->>'speed_of_fall_accelerating' = 'true') / COUNT(*), 1) AS sof_pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast';
```

**Criterio PASS:** `sof_pct` < 10%. Se ancora > 15%, il floor -0.5% non basta.

### 1.2 — Distribuzione risk_score post-fix

```sql
-- Distribuzione dei valori risk_score (prima era solo 20 o 40)
SELECT 
  risk_score, 
  COUNT(*) AS cnt,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast'
GROUP BY risk_score
ORDER BY risk_score;
```

**Criterio PASS:** almeno 3 valori distinti di risk_score (non solo 20/40). I nuovi step 26/32/40 dovrebbero apparire se le ladder granulari funzionano.

### 1.3 — Distribuzione opportunity_score post-fix

```sql
-- opportunity_score: ancora tutto 20 o si è mosso?
SELECT 
  opportunity_score, 
  COUNT(*) AS cnt,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast'
GROUP BY opportunity_score
ORDER BY opportunity_score;
```

**Criterio PASS:** almeno 1 valore > 20. Se 100% = 20, le soglie funding sono ancora troppo estreme.

### 1.4 — Breakdown delle regole fired

```sql
-- Quali regole hanno effettivamente scattato? (dalla colonna breakdown)
-- Conta quante volte ogni regola diversa da "base" appare
SELECT 
  key AS rule_name,
  COUNT(*) AS times_fired
FROM sentinel_scores,
  jsonb_each(raw_signals) AS kv(key, value)
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast'
  AND key != 'base'
  AND value::text NOT IN ('null', 'false', '0', '0.0')
GROUP BY key
ORDER BY times_fired DESC;
```

> **Nota per CC:** la struttura esatta delle colonne JSON può variare. Se `raw_signals` non contiene il breakdown, prova `breakdown` come colonna separata, oppure ispeziona lo schema con `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'sentinel_scores'` prima di eseguire.

### 1.5 — Range funding reale osservato

```sql
-- Range effettivo del funding rate nell'ultimo periodo
SELECT 
  MIN((raw_signals->>'funding_rate')::numeric) AS min_funding,
  MAX((raw_signals->>'funding_rate')::numeric) AS max_funding,
  AVG((raw_signals->>'funding_rate')::numeric) AS avg_funding
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast'
  AND raw_signals->>'funding_rate' IS NOT NULL;
```

**Scopo:** capire se le nuove soglie funding (±0.00002 / ±0.00005) catturano il range reale.

### 1.6 — Range BTC change_1h osservato

```sql
SELECT 
  MIN((raw_signals->>'btc_change_1h')::numeric) AS min_change,
  MAX((raw_signals->>'btc_change_1h')::numeric) AS max_change,
  PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY (raw_signals->>'btc_change_1h')::numeric) AS p5,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY (raw_signals->>'btc_change_1h')::numeric) AS p95
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z'
  AND score_type = 'fast'
  AND raw_signals->>'btc_change_1h' IS NOT NULL;
```

**Scopo:** verificare se le nuove soglie -0.5% / -1% / -2% cadono effettivamente nel range di mercato attuale.

---

## FASE 2 — Decisioni basate sui risultati

Dopo le query, CC produce un **report per il CEO** (`report_for_CEO/`) con i risultati e il verdetto per ciascun bug:

| Bug | Criterio PASS | Se FAIL → azione |
|-----|--------------|------------------|
| 1. SoF firing rate | < 10% | Alzare floor (es. -1.0%) oppure aggiungere floor anche sul change_20m (es. ≥ -0.15%) |
| 2. Opp score morto | almeno 1 valore > 20 | Abbassare soglie funding short fino al range osservato. Se funding oscilla tra -0.005% e -0.003%, la prima soglia deve stare a ~-0.004% |
| 3. Risk binario | ≥ 3 valori distinti | I nuovi step -0.5/-1/-2 coprono il range? Se p5 di change_1h è solo -0.3%, serve step a -0.3% |

### Decisioni delegate a CC

- Scegliere i valori esatti delle nuove soglie SE il range reale lo rende ovvio (es. funding oscilla tra X e Y → la prima soglia va a ~percentile 30)
- Aggiungere test unitari per ogni nuova soglia (pattern: `tests/test_accounting_avg_cost.py` ma per score_engine)
- Aggiornare la tabella statica scoring rules in `web_astro/public/admin.html` (già fatto in 70b, da estendere se cambiano valori)

### Decisioni che CC DEVE chiedere al Board

- Se il fix richiede di **eliminare** una soglia esistente (non solo aggiungerne)
- Se il fix richiede di cambiare `_SOF_MIN_DROP_1H_PCT` in modo significativo (es. da -0.5 a -2.0)
- Se nessuno dei 3 bug è risolto e serve un redesign più profondo
- Qualunque modifica a Sherpa `parameter_rules.py` — questo brief tocca **solo Sentinel**

---

## FASE 3 — Fix (solo se FASE 2 identifica FAIL)

### File che possono essere toccati

- `bot/sentinel/score_engine.py` — soglie ladder, delta risk/opp
- `bot/sentinel/price_monitor.py` — floor SoF, logica speed_of_fall
- `web_astro/public/admin.html` — tabella statica scoring rules (se cambiano valori)
- `tests/` — nuovi test per score_engine

### File OFF-LIMITS

- `bot/sherpa/` — tutto. Sherpa non si tocca in questo brief
- `bot/grid_runner/` — tutto. Grid non si tocca
- `bot/sentinel/main.py` — il loop non cambia
- `bot/sentinel/inputs/` — le sorgenti dati non cambiano
- `bot/sentinel/funding_monitor.py` — il monitor non cambia, cambiano solo le soglie in score_engine

### Pattern di shipping

1. Query audit → report risultati
2. Se fix necessari: scrivere fix + test
3. Pytest verde (tutti i test esistenti + nuovi)
4. Commit su main
5. **NON restartare il bot.** Il restart lo farà Max sul Mac Mini dopo aver verificato il report

---

## Output atteso a fine sessione

1. `report_for_CEO/2026-05-XX_s77_sentinel_audit_report_for_ceo.md` — risultati query + verdetto per bug + fix applicati (o "tutti PASS, nessun fix necessario")
2. Se fix applicati: commit su main con test verdi
3. PROJECT_STATE.md aggiornato (§3 in-flight, §9 audit)
4. Se tutti e 3 i bug risultano PASS → il dato va in BUSINESS_STATE: "Sentinel Sprint 1 audit PASS, pronto per Sprint 2"

---

## Roadmap impact

- Se **tutti PASS**: sblocca Sprint 2 (slow loop: Fear & Greed + CMC). Timeline: prossima sessione CC
- Se **fix applicati e verificati**: servono altri 2-3 giorni di osservazione post-fix prima di dichiarare Sprint 1 chiuso
- Se **redesign necessario**: Sprint 2 slippa. CEO e Board decidono il percorso

---

## Vincoli

- Nessun restart Mac Mini da questo brief. Solo codice + test + commit
- Non toccare Sherpa. Se i delta di score cambiano significativamente, Sherpa si adatterà automaticamente (legge gli score, non le soglie interne)
- Il report deve essere leggibile da Max (italiano, numeri chiari, niente gergo senza spiegazione)
- Ogni query SQL va eseguita tramite Supabase MCP `execute_sql`, non inventare i risultati
