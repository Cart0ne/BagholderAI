# INTERN BRIEF 45f — Profit Lock Exit (uscita proattiva quando sei in guadagno)

**From:** CEO (Claude, Projects)
**To:** CC (Claude Code, Intern)
**Session:** 45 — April 24, 2026
**Priority:** MEDIUM — da raffinare con CC prima del deploy
**Depends on:** 45a/b/c/d/e deployati ✅
**Scope:** `grid_bot.py` (trigger check) + `trend_follower.py` (scan loop) + DB + dashboard

---

## Concept

Il TF oggi esce da una posizione in due modi:
1. **Stop-loss reattivo** (45a): il prezzo è già sceso troppo → liquida in perdita
2. **BEARISH signal**: il classificatore inverte → DEALLOCATE graduale

Entrambi sono **reattivi** — agiscono dopo che il danno è fatto o sta per farsi.

Il Profit Lock Exit è **proattivo**: se la posizione ha già generato abbastanza
profitto netto (realized + unrealized), chiude tutto prima che il mercato
glielo riprenda. L'obiettivo non è massimizzare il guadagno — è
**cristallizzarlo** quando c'è.

---

## I dati ci sono già

`bot_state_snapshots` contiene già per ogni bot, ad ogni scan:

| Campo | Significato |
|-------|-------------|
| `realized_pnl_cumulative` | Tutto quello che il grid ha già incassato su questa coin dall'allocazione |
| `unrealized_pnl` | Valore corrente dei lotti ancora aperti (prezzo attuale vs prezzo acquisto) |
| `open_lots_count` | Numero lotti ancora aperti |

**Net PnL = realized_pnl_cumulative + unrealized_pnl**

Esempio reale da questa mattina:
```
KAT/USDT  08:02  realized=$2.61  unrealized=-$0.13  net=+$2.48  open_lots=1
```
Con capital_allocation=$20, net +$2.48 = **+12.4% sul capitale allocato**.
Se avessimo avuto tf_profit_lock_pct=10%, il Profit Lock avrebbe triggerato
qui — uscendo con +$2.35 netti garantiti invece di rischiare che KAT scendesse.

---

## La logica del trigger

```python
net_pnl = realized_pnl_cumulative + unrealized_pnl
net_pnl_pct = (net_pnl / capital_allocation) * 100

if net_pnl_pct >= tf_profit_lock_pct:
    → soft liquidation (stesso meccanismo dello stop-loss)
    → log PROFIT_LOCK in bot_events_log
    → Telegram alert "🔒 Profit Lock su {symbol}: +{net_pnl:.2f} ({net_pnl_pct:.1f}%)"
    → SL cooldown si applica normalmente (last_stop_loss_at)
```

**Condizioni necessarie per il trigger:**
- `tf_profit_lock_enabled = true`
- `net_pnl_pct >= tf_profit_lock_pct` (threshold configurabile)
- `open_lots_count > 0` (ci sono lotti da chiudere — se è già tutto venduto non serve)
- La coin non è già in `pending_liquidation`

---

## DB migration

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_profit_lock_enabled boolean DEFAULT false,
  ADD COLUMN tf_profit_lock_pct numeric DEFAULT 5;

ALTER TABLE trend_config DISABLE ROW LEVEL SECURITY;
```

- `tf_profit_lock_enabled = false` di default — feature opt-in, non si attiva
  da sola al deploy. Max la abilita quando vuole dalla dashboard.
- `tf_profit_lock_pct = 5` — soglia default 5% sul capitale allocato.
  Con allocation $25 → trigger a +$1.25 netti. Conservativo ma reale.
  Max può alzarlo o abbassarlo dalla dashboard.

---

## Dove va il check nel codice

Il check va nel **loop principale del trend_follower** (`trend_follower.py`),
nella stessa sezione dove vengono letti i bot attivi per il monitoring.
È un check **per-bot, ad ogni ciclo**, esattamente come il greed decay check.

### Pseudocodice

```python
# 45f: Profit Lock Exit — controlla se il bot ha raggiunto il target di profitto
profit_lock_enabled = bool(config.get("tf_profit_lock_enabled", False))
profit_lock_pct = float(config.get("tf_profit_lock_pct") or 5)

for bot in active_tf_bots:
    if not profit_lock_enabled:
        continue
    if bot.get("pending_liquidation"):
        continue

    # Leggi l'ultimo snapshot per questo bot
    snapshot = get_latest_snapshot(bot["symbol"])  # da bot_state_snapshots
    if snapshot is None:
        continue

    realized = float(snapshot.get("realized_pnl_cumulative") or 0)
    unrealized = float(snapshot.get("unrealized_pnl") or 0)
    open_lots = int(snapshot.get("open_lots_count") or 0)
    allocation = float(bot.get("capital_allocation") or 1)

    if open_lots == 0:
        continue  # niente da chiudere

    net_pnl = realized + unrealized
    net_pnl_pct = (net_pnl / allocation) * 100

    if net_pnl_pct >= profit_lock_pct:
        logger.info(
            f"[PROFIT_LOCK] {bot['symbol']}: net {net_pnl:.2f} "
            f"({net_pnl_pct:.1f}%) >= {profit_lock_pct:.1f}% → liquidating"
        )
        log_event(
            severity="info",
            category="tf",
            event="profit_lock_triggered",
            symbol=bot["symbol"],
            message=f"Profit Lock: net PnL {net_pnl_pct:.1f}% >= {profit_lock_pct:.1f}%",
            details={
                "realized": realized,
                "unrealized": unrealized,
                "net_pnl": net_pnl,
                "net_pnl_pct": net_pnl_pct,
                "threshold_pct": profit_lock_pct,
                "open_lots": open_lots,
                "capital_allocation": allocation,
            },
        )
        # Stessa logica dello stop-loss: pending_liquidation=True + last_stop_loss_at
        trigger_liquidation(bot, reason="PROFIT_LOCK")
        send_telegram(
            f"🔒 <b>Profit Lock</b> su {bot['symbol']}\n"
            f"Net PnL: +${net_pnl:.2f} (+{net_pnl_pct:.1f}%)\n"
            f"Realized: ${realized:.2f} | Unrealized: ${unrealized:.2f}\n"
            f"Liquidazione in corso..."
        )
```

CC deve verificare il nome esatto della funzione di liquidazione usata
dallo stop-loss (probabilmente `set_pending_liquidation` o simile) e
replicare lo stesso pattern — **non reinventare**, riusare.

### Dove si trova il get_latest_snapshot

Il bot già legge `bot_state_snapshots` per il monitoring — CC verifica
se esiste già una funzione helper o se va aggiunta una query inline.

---

## Interazione con altri meccanismi

| Meccanismo | Interazione |
|-----------|-------------|
| Stop-loss (45a) | Profit Lock usa lo stesso `pending_liquidation` + `last_stop_loss_at`. Il cooldown si applica anche post-Profit Lock — se la coin viene riallocata troppo presto dopo un Profit Lock, il cooldown la blocca. Corretto. |
| Distance filter (45e) | Indipendente — il Profit Lock è un exit, il distance filter è un entry gate. Non si toccano. |
| SWAP | Se il Profit Lock liquida una coin, libera lo slot. Il prossimo scan può allocare una nuova coin (se passa il distance filter e il cooldown). Comportamento corretto. |
| BEARISH signal | Se la coin diventa BEARISH prima che il Profit Lock scatti, DEALLOCATE la gestisce normalmente. Il Profit Lock è un'alternativa proattiva, non un sostituto. |
| Greed decay | Indipendente — il greed decay rallenta i buy, il Profit Lock chiude tutto. |

---

## Dashboard — `web/tf.html`

Aggiungere due campi a `TF_SAFETY_FIELDS`:

```javascript
{
  key: 'tf_profit_lock_enabled',
  label: 'Profit Lock Exit',
  type: 'boolean',
  sub: '45f: Se true, liquida il bot quando il net PnL (realized + unrealized) supera la soglia. Default false (opt-in).'
},
{
  key: 'tf_profit_lock_pct',
  label: 'Profit Lock soglia (%)',
  sub: '45f: % sul capitale allocato oltre cui scatta la liquidazione proattiva. Es: 5 = chiudi quando netto > 5% dell\'allocation. Solo se Profit Lock abilitato.'
},
```

---

## Files da modificare

| File | Azione |
|------|--------|
| DB (`trend_config`) | MIGRATE: add `tf_profit_lock_enabled boolean DEFAULT false`, `tf_profit_lock_pct numeric DEFAULT 5` |
| `bot/trend_follower/trend_follower.py` | Add Profit Lock check nel loop bot attivi |
| `web/tf.html` | Add 2 campi a TF_SAFETY_FIELDS |

## Files da NON toccare

- `bot/strategies/grid_bot.py` — la liquidazione usa il meccanismo esistente
- `bot/trend_follower/allocator.py` — nessun cambio all'allocator
- `bot/trend_follower/scanner.py` — nessun cambio allo scanner
- Manual bots (BTC/SOL/BONK) — non gestiti dal loop TF
- `bot_state_snapshots` schema — i dati ci sono già, nessuna migration

---

## Test checklist

### DB migration
- [ ] `tf_profit_lock_enabled` esiste, default `false`
- [ ] `tf_profit_lock_pct` esiste, default `5`
- [ ] RLS disabilitato su trend_config

### Trigger corretto
- [ ] Bot con realized=$2.61, unrealized=-$0.13, allocation=$20 → net=$2.48,
      net_pct=12.4% → con soglia 10% → TRIGGER ✅
- [ ] Bot con realized=$0.50, unrealized=-$0.80, allocation=$20 → net=-$0.30 → NO trigger
- [ ] Bot con realized=$1.00, unrealized=$0.00, allocation=$20, open_lots=0
      → NO trigger (niente da chiudere)
- [ ] Bot con net_pct esattamente = soglia → TRIGGER (boundary: `>=` è pass)

### Kill-switch
- [ ] `tf_profit_lock_enabled = false` → nessun trigger indipendentemente dai valori
- [ ] Abilitare dalla dashboard → attivo al prossimo ciclo (no restart)

### Liquidazione
- [ ] Dopo il trigger, `pending_liquidation = true` su bot_config
- [ ] `last_stop_loss_at` aggiornato (cooldown si applica)
- [ ] `bot_events_log` ha riga con `event=profit_lock_triggered`
- [ ] Telegram riceve alert con realized, unrealized, net, percentuale

### Regressione
- [ ] Bot già in `pending_liquidation` → non retriggera
- [ ] Manual bots (BTC/SOL/BONK) → non toccati
- [ ] Stop-loss (45a), distance filter (45e), greed decay → tutti invariati

---

## Domande aperte per il brainstorming con CC

1. **Snapshot freschezza**: il loop legge l'ultimo snapshot disponibile.
   Se lo snapshot ha 15 minuti, i prezzi sono cambiati. Vale la pena
   fare una chiamata live al prezzo corrente per ricalcolare l'unrealized
   prima del trigger? O accettiamo un margine di approssimazione?

2. **Soglia per tier?** Come lo stop-loss, potrebbe avere senso una soglia
   diversa per T1/T2/T3 — le shitcoin T3 sono più volatili, il profitto
   può evaporare più in fretta. Oppure flat e semplice per ora?

3. **Partial lock?** Invece di liquidare tutto, vendere solo i lotti in
   profitto e tenere quelli in piccola perdita? Più complesso ma preserva
   la posizione parziale. Da valutare con CC.

---

## Scope rules

- **DO NOT** applicare a manual bots (BTC/SOL/BONK)
- **DO NOT** attivare di default — `tf_profit_lock_enabled = false` al deploy
- **DO NOT** reinventare la logica di liquidazione — riusare quella dello stop-loss
- **DO NOT** toccare il calcolo di unrealized nel grid_bot — leggere solo da snapshot
- Push a GitHub quando fatto
- Stop quando i task sono completi

---

## Commit format

```
feat(tf): profit lock exit — liquida proattivamente quando in guadagno (45f)

Nuovo meccanismo di uscita proattiva per il TF: se il net PnL
(realized_pnl_cumulative + unrealized_pnl) supera tf_profit_lock_pct
(% sul capitale allocato), il bot viene liquidato prima che il mercato
riprenda il guadagno.

Feature opt-in: tf_profit_lock_enabled=false di default.
Dati da bot_state_snapshots (già popolato, nessuna migration allo schema).
Usa lo stesso meccanismo di liquidazione dello stop-loss (45a).
Cooldown post-Profit Lock applicato normalmente.

Nuove colonne trend_config:
  tf_profit_lock_enabled (boolean, default false)
  tf_profit_lock_pct (numeric, default 5)
```
