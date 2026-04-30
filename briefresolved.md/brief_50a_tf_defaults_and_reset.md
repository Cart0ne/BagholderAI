# Brief 50a — TF Default Parameters & Reset on Re-Allocate

**From:** CEO → Intern (Claude Code)
**Date:** 2026-04-28
**Priority:** HIGH — va in produzione oggi, i bot girano di notte senza supervisione
**Predecessori:** report 49c (TF behavior analysis), sessione 50 brainstorming CEO+Board

---

## Contesto

L'analisi post-deploy di 49c e l'audit completo dei dati TF (34 symbol, ~320 trades) hanno evidenziato tre problemi collegati:

1. **Parametri stale al re-allocate.** Quando il TF rialloca un symbol (anche dopo deallocation), `period_started_at` e il counter delle sell positive NON vengono resettati. Risultato: PENGU riallocato il 28/04 alle 15:17, il 45g spara dopo 1 secondo perché il counter era ancora 7 dal ciclo precedente (19h prima).

2. **Parametri inconsistenti tra symbol.** I symbol vecchi (pre-volume_tier) hanno parametri di un'era geologica: MOVR buy_pct=0.80/sell_pct=3.00, TST 0.80/0.50, MET 1.00/1.50. I symbol nuovi (post-tier) hanno tutti 2.00/1.50 e performano meglio. Non esiste un meccanismo di standardizzazione.

3. **`tf_exit_after_n` non ha un default globale attivo.** Il valore in `trend_config` è 0 (disattivato). Symbol senza override esplicito (es. SPK, APE) non hanno limite di uscita → SPK ha fatto 30 buy, 30 sell, 8 stop-loss consecutivi.

---

## Modifiche richieste

### 1. Default globale `tf_exit_after_n_positive_sells` = 4

**Dove:** tabella `trend_config` (o dove vive il default globale di questa regola)

**Cosa:** cambiare il valore da 0 a **4**.

**Logica:** N=4 è il valore con il migliore edge nel backtest pre-deploy (+$35.07 su 28 periodi). Non ancora confermato nei dati live (campione insufficiente), ma lasciare 0 equivale a nessuna protezione — SPK docet.

**Effetto:** tutti i symbol TF senza override esplicito avranno un limite a 4 sell positive prima di deallocazione automatica. I symbol con override (PENGU N=7, LUMIA N=4) continuano con il loro valore.

---

### 2. Rimuovere override N=2 da SPELL e TURTLE

**Dove:** tabella `bot_config`, colonna `tf_exit_after_n_override`

**Cosa:** impostare a NULL per SPELL/USDT e TURTLE/USDT

**Logica:** N=2 è dimostrato inutile — nessuna coin con N=2 ha mai triggerato il 45g. Entrambe sono uscite in stop-loss prima di accumulare 2 sell positive. Con il default globale a 4, torneranno automaticamente sotto quella protezione.

```sql
UPDATE bot_config 
SET tf_exit_after_n_override = NULL 
WHERE symbol IN ('SPELL/USDT', 'TURTLE/USDT') 
  AND managed_by = 'trend_follower';
```

---

### 3. Reset completo dei parametri al re-allocate

**Dove:** nel codice del TF allocator — il punto dove scrive `bot_config` per un symbol appena allocato (o riallocato)

**Cosa:** quando il TF alloca un symbol (nuovo o rientro su coin precedentemente deallocata), DEVE sovrascrivere TUTTI questi campi:

| Campo | Valore al re-allocate |
|---|---|
| `buy_pct` | 2.0 |
| `sell_pct` | 1.5 |
| `skim_pct` | 0 |
| `initial_lots` | 0 |
| `stop_buy_drawdown_pct` | 15 |

Inoltre, DEVE resettare lo stato del ciclo:

| Campo | Valore al re-allocate |
|---|---|
| `period_started_at` | NOW() (o il timestamp dell'allocazione) |
| counter sell positive (ovunque sia tracciato) | 0 |

**NON toccare:** `tf_exit_after_n_override` (se esiste un override esplicito per quel symbol, mantenerlo; altrimenti il default globale fa il suo lavoro), `volume_tier` (viene dal scanner), `allocated_capital` (viene dall'allocator).

**Il punto chiave:** il reset deve avvenire sia per allocazioni nuove che per riallocazioni su symbol già presenti in `bot_config`. Nessun parametro stale deve sopravvivere da un ciclo precedente.

---

### 4. `skim_pct` = 0 su tutti i config TF attivi

**Dove:** tabella `bot_config`

**Cosa:** UPDATE globale su tutti i record con `managed_by = 'trend_follower'`

```sql
UPDATE bot_config 
SET skim_pct = 0 
WHERE managed_by = 'trend_follower';
```

**Nota:** questo è il valore "per ora" (decisione del Board). Verrà rivalutato quando il pool di trading sarà più capitalizzato. Il default al punto 3 è già 0, quindi le nuove allocazioni lo erediteranno automaticamente.

---

### 5. Fix stop_reason inconsistente (dal report 49c §7.2)

**Dove:** nel codice del flow `proactive_tick` di 45g

**Cosa:** quando il 45g triggera via `proactive_tick`, il `bot_stopped` deve scrivere reason=**`gain_saturation`** (non `liquidation`).

**Attuale:**
- 45g via `post_sell` → reason = `gain_saturation` ✅
- 45g via `proactive_tick` → reason = `liquidation` ❌

**Atteso:** entrambi i path scrivono `gain_saturation`.

**Logica:** `liquidation` è usato per le deallocazioni normali del TF (swap, lifecycle). Il 45g è specificamente una gain saturation — il motivo va distinto per reporting/dashboard/forensics.

---

### 6. Fix `managed_by` NULL nella reserve_ledger (bassa priorità)

**Dove:** nel codice che scrive in `reserve_ledger` al momento dello skim

**Cosa:** assicurarsi che il campo `managed_by` venga popolato con il valore corretto (`trend_follower` per TF, `grid` per manual).

**Stato attuale:** le entry recenti (post ~25 aprile) hanno `managed_by = NULL`. Le entry precedenti sono correttamente taggate. Probabilmente un refactor recente ha perso il passaggio di questo campo.

**Impatto:** solo reporting/analytics. Lo skim funziona correttamente, è solo il tagging che manca.

---

## Ordine di esecuzione

1. **SQL diretto:** punto 4 (skim a 0) — può partire subito, è un UPDATE
2. **SQL diretto:** punto 2 (rimuovere override N=2) 
3. **Config:** punto 1 (default globale exit_after_n = 4)
4. **Codice:** punto 3 (reset al re-allocate) — questo è il cambio più importante
5. **Codice:** punto 5 (fix stop_reason)
6. **Codice:** punto 6 (fix managed_by) — bassa priorità, può aspettare

---

## Test checklist

- [ ] Verificare che `trend_config.tf_exit_after_n_positive_sells` = 4
- [ ] Verificare che SPELL e TURTLE hanno `tf_exit_after_n_override` = NULL
- [ ] Verificare che tutti i record TF in `bot_config` hanno `skim_pct` = 0
- [ ] Simulare un re-allocate su un symbol esistente (es. PENGU) e verificare che:
  - `buy_pct` = 2.0, `sell_pct` = 1.5, `skim_pct` = 0
  - `period_started_at` = timestamp dell'allocazione (non il vecchio valore)
  - counter sell positive = 0
  - `tf_exit_after_n_override` invariato (se aveva override, lo mantiene)
- [ ] Verificare che il 45g via proactive_tick scrive reason=`gain_saturation`
- [ ] Verificare che nuove entry in `reserve_ledger` hanno `managed_by` popolato

---

## Cosa NON fare

- **NON differenziare buy_pct/sell_pct per tier** — per ora sono uguali per tutti (2.0/1.5). La differenziazione per tier è un'ottimizzazione futura per il Sentinel.
- **NON toccare il `tf_exit_after_n_override` di PENGU (7) e LUMIA (4)** — sono override manuali intenzionali.
- **NON modificare `stop_buy_drawdown_pct`** — il SL cooldown di 4h è già stato impostato dal Board via dashboard.

---

🏳️ Bandiera bianca.
