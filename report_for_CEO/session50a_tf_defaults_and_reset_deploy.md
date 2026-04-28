# Session 50a — TF Defaults & Re-Allocate Reset Deploy

**From:** Intern (Claude Code) → CEO
**Date:** 2026-04-28
**Brief di riferimento:** [config/brief_50a_tf_defaults_and_reset.md](../config/brief_50a_tf_defaults_and_reset.md)
**Predecessore:** [report 49c](session49c_tf_behavior_analysis_post_deploy.md) (TF behavior analysis post 49a/49b)

---

## TL;DR (3 righe)

1. Tutti i 6 punti del brief 50a sono in produzione: SQL applicate, codice committato (`12d6376`), pull + restart sul Mac Mini fatto.
2. Il deploy ha smascherato un **bug pre-esistente** sul mid-tick DEALLOCATE writer: PENGU stop-loss appena partito ha mancato la scrittura della DEALLOCATE per CHECK constraint violato. Hot-fix immediato (`d0c6e44`), restart, ora pulito.
3. Una mia mossa **da segnalare**: ho ridefinito il Punto 3 da "appiattire i parametri a valori fissi" a "ricalcolare tutto da zero senza ereditare valori stale". Confermato con Max in chat — ma qui lo metto in chiaro perché è una scelta di policy.

---

## 1. Cosa era richiesto (brief 50a)

Il CEO ha letto il report 49c e ha deciso 6 modifiche:

1. Default globale `tf_exit_after_n_positive_sells` = **4** (era 0)
2. Rimuovere override N=2 da SPELL e TURTLE
3. Reset completo dei parametri al re-allocate (allocator)
4. `skim_pct` = 0 su tutti i record TF
5. Fix stop_reason inconsistente (proactive_tick → `gain_saturation`)
6. Fix `managed_by` NULL nel reserve_ledger

In aggiunta durante la sessione, il CEO ha esteso il Punto 2: **rimuovere anche gli override di PENGU e LUMIA** per farle ricadere sul default globale (4).

---

## 2. Cosa è stato fatto

### 2.1 SQL diretti su Supabase

| # | Cosa | Effetto |
|---|---|---|
| 1 | `UPDATE trend_config SET tf_exit_after_n_positive_sells = 4` | Default globale attivo |
| 2 | `UPDATE bot_config SET tf_exit_after_n_override = NULL WHERE symbol IN ('SPELL','TURTLE','PENGU','LUMIA')` | 4 coin tornano al default |
| 4 | `UPDATE bot_config SET skim_pct = 0 WHERE managed_by='trend_follower'` | 35 record TF a skim 0 |

**Stato post-SQL** (verificato):
- `trend_config.tf_exit_after_n_positive_sells` = 4 ✅
- `tf_exit_after_n_enabled` = true (kill-switch on)
- 0 record TF con skim_pct ≠ 0 (35/35 a zero)
- Override residui: solo ALGO=4 e LUNC=4 (entrambe inattive, valore = default → nessun effetto pratico)

### 2.2 Modifiche al codice (commit `12d6376`)

**[bot/trend_follower/allocator.py](../bot/trend_follower/allocator.py)**
- `skim_pct: 30` → `skim_pct: 0` nel dict scritto ad ogni ALLOCATE (Board decision: skim disattivato finché il pool non è capitalizzato)
- Aggiunto `stop_buy_drawdown_pct: 15` nel dict (prima non veniva scritto: i re-allocate ereditavano valori stale)
- Nuova funzione `_close_orphan_period()`: prima di un re-allocate, se trova un period orfano (ALLOCATE senza DEALLOCATE successiva), scrive una **synthetic-DEALLOCATE** in `trend_decisions_log` con timestamp = NOW − 1s. Questo risolve il bug PENGU della 49c: il counter delle pos sells non leakerà più tra cicli successivi.

**[bot/grid_runner.py](../bot/grid_runner.py)**
- Fix Punto 5: il proactive_tick ora scrive `stop_reason = "gain_saturation"` invece di `"liquidation"` (prima andava perso nel reporting)
- Fix Punto 6: `log_skim()` al force-liquidate ora propaga `managed_by`

**[bot/strategies/grid_bot.py](../bot/strategies/grid_bot.py)**
- Skim mid-trade: `log_skim()` ora propaga `managed_by`

**[db/client.py](../db/client.py)**
- `ReserveLedger.log_skim()` accetta nuovo parametro `managed_by` e lo include nell'insert

### 2.3 Deploy

- `git commit -m "feat(tf): 50a — TF defaults & re-allocate reset"` (`12d6376`)
- `git push origin main`
- `ssh max@Mac-mini-di-Max.local` → `git pull` + `kill <orchestrator_pid>` + restart in venv
- Verifica processi: orchestrator + trend_follower + 4 grid_bot (BTC, SOL, BONK manuali + LUMIA TF) attivi

---

## 3. Una decisione che ho preso in autonomia (e poi confermata con Max)

### Il Punto 3 nel brief diceva:

> | Campo | Valore al re-allocate |
> |---|---|
> | `buy_pct` | 2.0 |
> | `sell_pct` | 1.5 |
> | `skim_pct` | 0 |
> | `initial_lots` | 0 |
> | `stop_buy_drawdown_pct` | 15 |

Letto alla lettera, significava **disattivare due meccanismi esistenti**:
- L'**ATR-adaptive** su `buy_pct` (oggi calcola buy_pct in base alla volatilità della coin via `_adaptive_steps`)
- Il **post-greed-decay salvage** su `sell_pct` (la regola 45b che il CEO stesso ha disegnato il 23/04)

E avrebbe forzato `initial_lots = 0` cancellando la 42a (multi-lot entry tier-aware).

### Cosa ho fatto

Prima di scrivere codice ho mostrato a Max le opzioni e gli ho chiesto. Lui ha confermato: il brief vuole dire **"ricalcolare tutto da zero senza ereditare valori stale"**, non **"appiattire a costanti"**.

In pratica: l'allocator continua a usare `_adaptive_steps()`, `_compute_sell_pct_salvage()` e `tier_initial_lots` come prima — ma scrive **fresh data** al re-allocate, non eredita valori stale. I soli valori "fissi" sono `skim_pct=0` e `stop_buy_drawdown_pct=15`.

**Lo segnalo al CEO** perché il brief letto alla lettera avrebbe portato a una scelta diversa, e voglio che sia visibile che ho deviato (con autorizzazione) per preservare 45b/ATR-adaptive/42a.

---

## 4. Il bug imprevisto smascherato dal restart

### Cosa è successo

Dopo il primo restart con il codice 50a, **PENGU è uscita immediatamente in stop-loss** (era già a -3% sul lotto residuo) e il flow mid-tick ha cercato di scrivere la DEALLOCATE in `trend_decisions_log`. La INSERT ha fallito con HTTP 400:

```
violates check constraint "trend_decisions_log_signal_check"
Failing row contains: ..., signal='', signal_strength=0, action_taken='DEALLOCATE'
```

### La diagnosi

`trend_decisions_log.signal` accetta solo `('BULLISH','NO_SIGNAL','SIDEWAYS')`. Il **mid-tick DEALLOCATE writer** in [bot/grid_runner.py:854](../bot/grid_runner.py#L854) (riga "39f Section B") passava stringa vuota.

Era **lo stesso identico bug** che il commit 49b/`030b328` aveva già fixato per il proactive flow — ma quel fix non aveva coperto il path mid-tick (il quale fortunatamente raramente si triggera nei primi tick post-restart, da qui la latenza di scoperta).

### Hot-fix

Una riga: `"signal": ""` → `"signal": "NO_SIGNAL"`.

Commit `d0c6e44`, push, pull Mac Mini, restart pulito. PENGU ha confermato lo shutdown corretto, il bot ora è inattivo (signal post-SL ancora valido, tornerà in pool al prossimo scan se BULLISH).

### Perché lo segnalo al CEO

**Il bug era pre-esistente al 50a** — c'è da prima del 49b. È stato latente perché il mid-tick DEALLOCATE writer si triggera solo in scenari specifici (stop-loss / take-profit / profit-lock / gain-saturation che chiudono il cycle nello stesso tick) e nessuna coin di recente lo aveva fatto su una sessione fresh-start. Il 50a non l'ha causato — l'ha solo **esposto**, perché ogni restart scatena nuovamente le condizioni in cui il path è raggiungibile presto.

**Conseguenze finora**: nessun impatto operativo sui PnL — il bot si fermava lo stesso, solo che la riga DEALLOCATE non era loggata in `trend_decisions_log`. Ma quando la riga manca, il `get_period_start()` del 45g può vedere counter "leaked" da cicli precedenti — esattamente il pattern PENGU del 27/04 → 28/04 che il CEO aveva chiamato fuori nel report 49c.

Ora chiuso. Va però considerato come **una conferma indipendente** della tesi 49c: il bug "PENGU doppio trigger" non era solo synthetic, c'era anche questo ulteriore tassello che impediva la scrittura corretta della DEALLOCATE.

---

## 5. Test checklist (dal brief 50a)

| Test | Stato |
|---|---|
| `trend_config.tf_exit_after_n_positive_sells = 4` | ✅ verificato post-SQL |
| SPELL e TURTLE `tf_exit_after_n_override = NULL` | ✅ verificato |
| Tutti i record TF `skim_pct = 0` | ✅ verificato (35/35) |
| Re-allocate riscrive `skim_pct=0`, `stop_buy_drawdown_pct=15` | ⏳ verificabile alla prossima ALLOCATE live |
| 45g via proactive_tick scrive `stop_reason=gain_saturation` | ⏳ verificabile al prossimo trigger live |
| Nuove entry in `reserve_ledger` con `managed_by` popolato | ⏳ verificabile al prossimo skim live (ora skim=0, quindi non ne arriveranno) |

I 3 test runtime non sono falsificabili senza far partire il TF in produzione. Il prossimo scan TF (default 30min) e i prossimi tick dei grid_bot li copriranno automaticamente.

---

## 6. Cosa è cambiato concretamente per il bot a partire da ora

1. **Tutte le coin TF non-override sono ora protette dal 45g a N=4** (prima nessuna lo era — SPK aveva fatto 30 buy / 30 sell / 8 stop-loss consecutivi)
2. **Nessun re-allocate erediterà più valori stale**: `skim_pct` e `stop_buy_drawdown_pct` vengono sempre forzati ai default Board, indipendentemente da cosa il record aveva prima
3. **Niente più "double trigger" 45g** dopo riallocazione: la synthetic-DEALLOCATE garantisce che il counter delle positive sells parta sempre da zero in un period nuovo
4. **Stop-reason coerente**: ogni 45g triggerato (post_sell o proactive_tick) appare come `gain_saturation` in `bot_events_log`, dashboard e reporting saranno onesti
5. **reserve_ledger correttamente taggata**: lo skim, quando arriverà, sarà attribuibile via SQL/dashboard a Grid o TF

---

## 7. Cosa NON è stato cambiato (esplicitamente, su istruzione CEO/Max)

- **Niente differenziazione buy_pct/sell_pct per tier** — `_adaptive_steps` (ATR) e `_compute_sell_pct_salvage` (45b) restano come sono
- **Niente "fissi" su buy_pct/sell_pct/initial_lots** — ricalcolati ogni ALLOCATE da fresh data (ATR, tier, signal, greed_decay_tiers)
- **stop_buy_drawdown_pct dei record esistenti non toccato** — solo l'allocator scrive 15 ai prossimi re-allocate (i record manual hanno il loro valore)
- **PENGU/LUMIA override = NULL ricadono sul default 4** (CEO add-on) — non sono "spente" dal 45g, sono "uniformate" al resto

---

## 8. Domande aperte / cose da osservare nei prossimi giorni

1. **Default globale a 4 in produzione**: sui 4 closed periods post-49a/49b deploy, il backtest replicato non si replicava (vedi report 49c §4). Ora con default attivo system-wide, vedremo se tutte le coin escono "presto" perdendo upside, o se la regola difende davvero. Aspettarsi 2-3 settimane per un dataset onesto.

2. **47a counterfactual ancora vivo**: lo abbiamo allargato a 5000 nel batch (vedi roadmap entry Phase 9 di oggi). Conviene rivedere se la 45e (entry distance filter) sta tagliando ricavi mentre il 45g taglia perdite — i due filtri sono ortogonali.

3. **45g vs 45f**: il caso LUNC della 49c (45g $1.37 + 45f $2.73 + SL −$1.63 in cascata) resta una domanda di design aperta. Brief follow-up `49d` se il pattern si ripresenta.

4. **PENGU/LUMIA con default 4 vs override 7/4 prima**: avevamo dati su PENGU=7 (2 trigger). Ora PENGU sarà su default=4: probabilmente uscirà prima. Vale la pena tracciare se il PnL aggregato peggiora o migliora — caveat campione piccolo, ma è il segnale più diretto.

5. **Telegram/dashboard**: con il 45g attivo system-wide e lo stop_reason fixato, mi aspetto più eventi "GAIN-SATURATION" nei daily report e nell'admin. Se vedi spam notifiche, dimmelo che le calmiamo.

---

## 9. File toccati / commit

**Commit di sessione (2 totali):**
- `12d6376` — feat(tf): 50a — TF defaults & re-allocate reset
- `d0c6e44` — fix(tf): mid-tick DEALLOCATE signal '' violates CHECK constraint

**File modificati:**
- [bot/trend_follower/allocator.py](../bot/trend_follower/allocator.py) — skim_pct, stop_buy_drawdown_pct, _close_orphan_period
- [bot/grid_runner.py](../bot/grid_runner.py) — stop_reason fix, managed_by skim, signal '' → NO_SIGNAL
- [bot/strategies/grid_bot.py](../bot/strategies/grid_bot.py) — managed_by su skim
- [db/client.py](../db/client.py) — log_skim accetta managed_by
- [web/roadmap.html](../web/roadmap.html) — v1.35, 10 nuove voci (sessioni 48-50a)

**Roadmap aggiornata** alla v1.35, last_updated 2026-04-28.

🏳️ Bandiera bianca su brief 50a.
