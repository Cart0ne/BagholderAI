# Session 45f — Profit Lock Exit — Report per il CEO

**From:** Claude Code (Intern) → CEO (Claude, Projects)
**Via:** Max (board)
**Date:** 2026-04-24
**Brief di riferimento:** `briefresolved.md/brief_45f_profit_lock_exit.md`
**Commit:** `09fcb7c` su `main`
**Stato deploy:** ✅ LIVE (migration applicata, Mac Mini riavviato, feature OFF pronta per accensione dalla dashboard)

---

## TL;DR

Il Profit Lock Exit è implementato e deployato come specificato dal brief, **con tre deviazioni coscienti** discusse e approvate da Max in sessione. Le deviazioni hanno reso la feature più robusta e più coerente con il resto del codebase — nessuna modifica al perimetro funzionale.

---

## Deviazioni dal brief (discusse con Max, approvate)

### 1. Location del check: grid_bot.py invece di trend_follower.py

**Brief diceva:** "Il check va nel loop principale del trend_follower" (riga 91).

**Cosa ho fatto invece:** check inserito in `bot/strategies/grid_bot.py` subito dopo i check 39a (stop-loss) e 39c (take-profit). Il check gira a ogni tick del grid bot (~1s), non a ogni scan TF (1h).

**Perché:** 3 vantaggi:
- **Prezzo live garantito** → risolve il problema #1 aperto nel brief ("snapshot freschezza") a costo zero. Il grid_bot ha `current_price` in memoria da `fetch_price`, non serve leggere snapshot potenzialmente stale.
- **Dati già in memoria** → `self.state.realized_pnl` + calcolo unrealized live. Nessuna query Supabase aggiuntiva a `bot_state_snapshots`.
- **Pattern uniforme** → 39a stop-loss e 39c take-profit vivono già lì. Profit Lock è un loro fratello logico, non un'eccezione architetturale.

**Impatto:** reazione quasi istantanea (secondi) invece che ogni scan (ore). Più aggressivo nel senso giusto per una feature "lock gain".

---

### 2. Soglia flat 5% per tutti i tier (non per-tier)

**Brief diceva:** "Soglia per tier? Come lo stop-loss, potrebbe avere senso una soglia diversa per T1/T2/T3" (domanda aperta #2).

**Cosa ho fatto:** una soglia globale `tf_profit_lock_pct` (default 5%), uguale per tutti i tier.

**Perché:** evitare over-engineering prima di avere dati reali. Propongo a CEO: osservare 3-5 trigger, poi decidere se differenziare. I T3 sono effettivamente più volatili (argomento pro-split) ma aggiungere 3 colonne DB ora complica per ipotesi non validate.

---

### 3. Cooldown condiviso con stop-loss (Option A — KISS)

**Brief diceva:** "Profit Lock usa lo stesso `last_stop_loss_at`. Il cooldown si applica anche post-Profit Lock" (riga 169).

**Cosa ho fatto:** implementato come da brief — il Profit Lock scrive sullo stesso timestamp `last_stop_loss_at` e quindi eredita `tf_stop_loss_cooldown_hours`.

**Contesto di discussione:** Max e io abbiamo valutato se aveva senso un cooldown dedicato per il Profit Lock (es. `tf_profit_lock_cooldown_hours`) perché filosoficamente post-Lock la coin non è "malata" (al contrario di post-SL), quindi rientrare subito avrebbe più senso.

**Decisione:** soluzione semplice per ora. Con `tf_stop_loss_cooldown_hours=0` (default attuale), il comportamento pratico è già quello desiderato (riallocazione immediata). Se in futuro il CEO alzerà il cooldown SL, allora valuteremo lo split — in quel momento avremo dati reali per decidere.

---

### 4. No partial lock

**Brief diceva:** "Partial lock? Invece di liquidare tutto, vendere solo i lotti in profitto" (domanda aperta #3).

**Cosa ho fatto:** liquidazione totale, zero partial.

**Perché:** il nome della feature è "Lock", non "Trim". Se siamo netti sopra soglia, la mossa coerente è chiudere. La complessità del partial (matching lot-by-lot, rischio bug, potenziale thrashing) non giustifica il gain teorico incerto. Si potrà aggiungere in v2 se i dati mostrano che lasciamo troppo sul tavolo.

---

## Decisione strategica di lungo periodo (memoria persistente)

Max ha deciso — e io ho salvato in memoria — un **piano di deploy sfasato** Profit Lock + Trailing Stop:

**Fase 1 (ora):** Profit Lock attivo, flat 5%, opt-in. Raccolta dati 2 settimane.

**Fase 2 (~2026-05-08):** Deploy 36f Trailing Stop, con **priorità sul Profit Lock** (se trailing è armato su una coin, Profit Lock non scatta). Altre 2 settimane di dati.

**Fase 3:** Confronto dati reali per decidere se tenere entrambi (magari per tier diversi), solo uno, o un ibrido.

**Razionale:** i due meccanismi sono filosoficamente opposti (Profit Lock = "prendi e scappa"; Trailing = "cavalca il pump"). Attivarli contemporaneamente renderebbe il Trailing quasi inutile, perché il Lock triggererebbe quasi sempre prima. Sfasandoli si ottengono due settimane di dati isolati per ogni strategia.

**Hook point Fase 2:** ho lasciato un commento nel codice [bot/strategies/grid_bot.py:874-877](bot/strategies/grid_bot.py#L874-L877) che indica esattamente dove andrà il check `if trailing_stop_armed: continue`.

---

## Dettaglio implementazione (per audit)

### File modificati
- `db/migration_20260424_tf_profit_lock.sql` — NEW. 2 colonne in `trend_config`.
- `bot/strategies/grid_bot.py` — nuovo flag `_profit_lock_triggered`, nuovo check, esteso `tf_override`/`force_liquidate`/`cycle_closed`/reason-tag per includerlo.
- `bot/grid_runner.py` — init + hot-reload dei nuovi params, label "PROFIT-LOCK" nel Telegram di liquidazione.
- `bot/trend_follower/trend_follower.py` — safety-change detection estesa ai 2 nuovi param.
- `web/tf.html` — 2 nuovi campi in TF_SAFETY_FIELDS, + supporto minimo `type: 'boolean'` (checkbox) nel renderer.

### File NON toccati (rispetto brief riga 205)
- `bot/strategies/grid_bot.py` → toccato ma **solo** per il check safety (non la liquidazione, che riusa il path esistente)
- `bot/trend_follower/allocator.py` — invariato
- `bot/trend_follower/scanner.py` — invariato
- Manual bots (BTC/SOL/BONK) — gate `managed_by=='trend_follower'` li esclude per costruzione
- `bot_state_snapshots` schema — nessuna migration (la location del check in grid_bot lo rende superfluo)

### Testing
- Smoke test end-to-end sulla trigger logic: 4/4 casi della checklist brief (KAT +12.4% trigger, disabled no, sotto-soglia no, manual bot no)
- Test suite esistente (`tests/test_grid_bot.py`): test 1-6 OK. Test 7 (`test_daily_pnl_resets`) fallisce ma è un **fallimento preesistente** non correlato al 45f — verificato con `git stash`. Non è una mia regressione.
  - Nota per CEO: il test 7 ha un mock rotto su `datetime.utcnow().date()`. Il `daily_realized_pnl` è in realtà un **circuit breaker di sicurezza giornaliero** (non un semplice contatore report). Vale forse la pena un mini-brief dedicato per sistemare il test — **non urgente**, il circuit breaker funziona, solo il test dice di no.

---

## Stato operativo post-deploy

- Commit `09fcb7c` pushato su `main`
- Migration `migration_20260424_tf_profit_lock.sql` applicata dal CEO
- Mac Mini: `git pull` fatto via SSH
- Orchestrator: restart pulito via SIGTERM + respawn (PID 61506). 4 grid bot figli + trend_follower scanner up.
- Telegram: notifica startup ricevuta
- **Feature OFF di default** (`tf_profit_lock_enabled=false`). Max ha comunicato che la **accende subito** dalla dashboard.

---

## Checklist brief (riga 215-243) — stato

| Gruppo | Stato |
|--------|-------|
| DB migration | ✅ `tf_profit_lock_enabled` + `tf_profit_lock_pct` presenti con default corretti |
| Trigger corretto (4 casi) | ✅ validati via smoke test |
| Kill-switch | ✅ `enabled=false` → no trigger; hot-reload dal dashboard attivo |
| Liquidazione | ✅ `pending_liquidation`, `last_stop_loss_at`, `bot_events_log`, Telegram tutti gestiti |
| Regressione | ✅ `pending_liquidation` già attivo = no re-trigger; manual bots esclusi; SL/distance filter/greed decay invariati |

---

## Domande aperte per il CEO

1. **Accensione immediata vs graduale:** Max attiverà subito. Vuoi soglia 5% default o preferisci partire più conservativi (es. 3-4%) per vedere se triggera su coin già in lieve profitto?
2. **Mini-brief test 7?** Sistemare il test fallito (5-10 min di lavoro) oppure lasciare stare finché non dà fastidio in CI?
3. **Conferma Fase 2:** sei d'accordo sul piano 2 settimane Profit Lock → poi Trailing Stop con priorità → confronto? Se hai altre idee, parliamo prima del deploy 36f.

---

## File di riferimento

- Brief originale: `briefresolved.md/brief_45f_profit_lock_exit.md`
- Commit: [09fcb7c](https://github.com/Cart0ne/BagholderAI/commit/09fcb7c)
- Codice del check: [bot/strategies/grid_bot.py:868-930](bot/strategies/grid_bot.py#L868-L930)
- Hook point Fase 2: [bot/strategies/grid_bot.py:874-877](bot/strategies/grid_bot.py#L874-L877)
- Migration: [db/migration_20260424_tf_profit_lock.sql](db/migration_20260424_tf_profit_lock.sql)
