# BRIEF — Session 45: Orphan-lot reconciler

**Date:** 2026-04-21
**Priority:** HIGH — bug attivo, un lotto TF orfano (EDU 119 units) è già presente
**Prerequisito:** nessuno
**Target branch:** `main`

---

## Problema

Quando un trade (buy o sell) viene eseguito dal bot ma il POST su `trades` fallisce (tipicamente `httpx.ConnectTimeout` durante blackout di rete), il bot **modifica lo state in-memory prima di fare l'INSERT su DB**. Se l'INSERT fallisce, lo state locale è avanti, ma al restart il DB replay ricostruisce uno state "indietro" di un trade. Il risultato è una **desincronia permanente** tra ciò che il bot pensa e ciò che il DB sa.

**Caso osservato — EDU/USDT, 2026-04-21 02:30 UTC:**

Durante il blackout di rete delle 04:25–05:09 locale (= 02:25–03:09 UTC), uno stop-loss ha provato a liquidare 2 lotti:

```
04:30:42 INFO:  SELL 119.000000 EDU/USDT @ $0.0720 (pnl: $-1.13)
04:30:42 ERROR: Failed to log trade: [Errno 60] Operation timed out
04:30:51 INFO:  SELL 133.000000 EDU/USDT @ $0.0720 (pnl: $-0.08)   ← questa OK
```

Il primo `log_trade` è andato in timeout. Sul DB c'è solo la seconda sell. Sul bot (che poi è morto) le 119 EDU sono "vendute" ma contabilmente no.

Conseguenza: `bot_config.EDU` è `is_active=False`, `pending_liquidation=False`, e il DB dice `buys - sells = 119 EDU orfani`. A price attuale ~$0.072, ~$8.57 di valore intrappolati in un bot dormiente. Non compaiono nel report `/tf` perché il filtro "fully liquidated" (`buyAmt == sellAmt`) li esclude. Non vengono mai venduti perché nessuno rispawna il bot.

Soluzione user-facing non è "avvisare che c'è un orfano" — è **riprendere automaticamente e liquidare**.

---

## Design

Due hook, stesso scopo:

### Hook A — Reconciler al boot dell'orchestrator

Una volta, all'avvio dell'orchestrator, prima di entrare nel poll loop:

1. Query `bot_config` dove `is_active=False AND managed_by='trend_follower'` (manual bot non sono orfanabili nello stesso modo — li gestisce Max).
2. Per ogni row, calcola `holdings_db = sum(buys.amount) - sum(sells.amount)` dai `trades` v3.
3. Se `holdings_db > 0` E `holdings_db × current_price ≥ min_notional`:
   - UPDATE `bot_config` SET `is_active=True, pending_liquidation=True`
   - Log + Telegram: `🔧 Reconciled orphan: EDU 119 units ($8.57). Liquidating.`
4. Il poll loop standard vedrà `is_active=True` al tick successivo, spawnerà il grid_runner, che al boot `init_percentage_state_from_db` ricostruisce FIFO (ha già la logica), vede `pending_liquidation`, entra in force-liquidate path, vende al prezzo corrente, e si chiude col flow BEARISH EXIT standard.
5. Se `holdings_db × price < min_notional` → vero dust economico, skip (non c'è modo di venderlo su Binance, accetta la perdita).

### Hook B — Check al deallocate

Per prevenire che lo stesso caso si ripeta in futuro: il grid_runner, nel branch che scrive `is_active=False` dopo liquidation, ricontrolla `holdings_db` **subito prima**:

- Se `holdings_db > 0` dopo aver fatto tutti i sell → **non** scrivere `is_active=False`. Mantieni `is_active=True, pending_liquidation=True` così il prossimo spawn riprova.
- Log l'evento come "post-liquidation residual".

Questo copre il caso "il sell è andato, ma l'INSERT no" — il bot non si chiude finché il DB non conferma zero holdings.

**Dove:** nei due path in `grid_runner.py` che fanno `bot_config.update({"is_active": False, "pending_liquidation": False})` dopo liquidation. Attualmente ce ne sono 2 (BEARISH EXIT e stop-loss/take-profit cleanup).

---

## Scope

- **In scope:** Hook A (reconciler al boot) + Hook B (check pre-deactivate).
- **In scope:** Auto-recovery di EDU al prossimo restart.
- **Out of scope:** retry/backoff generico su `log_trade` — il reconciler rende il retry superfluo per il caso d'uso principale (EDU). Se servirà per altri casi d'angolo, brief separato.
- **Out of scope:** reconciler periodico (es. ogni ora). Hook A al boot + Hook B al deallocate coprono i due timing rilevanti; un periodico aggiungerebbe complessità senza valore.
- **Out of scope:** manual bots. Loro sono sotto controllo del CEO/Max, non devono essere auto-rianimati.

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/orchestrator.py` | Nuova funzione `_reconcile_orphan_tf_bots(supabase, notifier)` chiamata una volta prima del main poll loop. Usa ticker live (già-esistente nel client Binance) per stima del valore. |
| `bot/grid_runner.py` | In entrambi i path di `bot_config.update({"is_active": False})` post-liquidation, verifica `holdings_db` prima di scrivere. Se > 0 e valore ≥ min_notional → skip la disattivazione, lascia `pending_liquidation=True`. |
| (nessuna migration) | Lo schema non cambia. |

---

## Miei dubbi

### D1 — Cosa usare come "current_price" nel reconciler?

Due opzioni:
- **Fetch da Binance ticker** — preciso, ma richiede una chiamata in più per ogni orfano. In blackout di rete il reconciler fallisce — ma in quel caso l'orchestrator probabilmente non parte nemmeno, quindi accettabile.
- **Ultimo trade dal DB** — più veloce e offline-friendly, ma può essere stale (il prezzo ora può essere molto diverso).

La soglia `holdings × price ≥ min_notional` serve solo a distinguere "dust vero" da "lotto vendibile". Se il price è 10% off, la decisione borderline può sbagliarsi — ma un lotto da $8 (come EDU) resta vendibile anche con stime imprecise. **Raccomando Binance ticker** perché il reconciler gira solo al boot (non è hot path).

### D2 — Hook B cambia semantica di is_active

Oggi il contratto è: `liquidation branch → is_active=False`. Dopo Hook B, il contratto diventa: `liquidation branch → is_active=False SE E SOLO SE holdings=0`. Un piccolo cambio di semantica che potrebbe confondere debug futuri.

Mitigazione: il log della riga "is_active held True due to residual holdings" è esplicito. E il reconciler ricupererà comunque alla fine (se Hook B lascia is_active=True, il bot resta vivo e liquida al tick successivo).

### D3 — Race condition tra Hook A e bot che si sta chiudendo

Scenario: l'orchestrator riparte mentre un grid_runner TF sta ancora liquidando (processo figlio non ancora morto, DB già ha `is_active=False`). Hook A potrebbe vedere l'orfano e riattivare, ma il vecchio grid_runner è ancora in esecuzione e potrebbe generare trade sovrapposti.

Mitigazione: l'orchestrator non spawna due processi per lo stesso symbol — ha già un dict `grid_processes[symbol]` che gatekeep. L'UPDATE di `is_active` via reconciler farà sì che al poll successivo l'orchestrator trovi un processo già vivo (il figlio che sta chiudendo), non ne spawni uno nuovo. Il figlio chiude, muore, al poll dopo il reconciler l'orchestrator lo rispawna. Un po' di latenza ma niente race.

---

## Test pre-deploy

1. **EDU in particolare:** dopo deploy, restart orchestrator → Hook A trova EDU con `holdings=119`, scrive `is_active=True, pending_liquidation=True`, Telegram arriva, grid_runner EDU spawnato, vende 119 EDU al mercato, Telegram della sell arriva, bot si chiude, `is_active=False` correttamente.
2. **Manual non toccati:** BTC/SOL/BONK non devono essere toccati dal reconciler (filtro `managed_by='trend_follower'`).
3. **Dust economico:** manualmente create un bot_config TF con `is_active=False` e aggiungere un buy sintetico da 0.001 di una shitcoin → il reconciler deve vedere `holdings × price < min_notional` e NON riattivare.

---

## Rollback

```bash
git revert <commit_hash>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# restart orchestrator
```

Nessuna DB migration, rollback pulito.

---

## Commit format

```
feat(orchestrator): auto-reconcile orphan TF holdings (45)

Observed 2026-04-21: EDU/USDT stop-loss liquidation left 119 units
orphaned in DB because the first sell INSERT timed out during a 45-min
network blackout. Bot state proceeded, DB didn't — resulting in
is_active=False on a position still holding ~$8.57 of sellable coin.

Fix: at orchestrator boot, scan bot_config for TF rows with
is_active=False but holdings_db × price ≥ min_notional, flip them to
is_active=True + pending_liquidation=True, let the standard spawn +
liquidation flow close them out.

Also add a defensive pre-deactivate check in the grid_runner's post-
liquidation branches: don't write is_active=False while holdings_db > 0.
Keeps new orphans from being minted when a future network blackout
eats another log_trade INSERT.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
