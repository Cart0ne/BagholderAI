# INTERN BRIEF — Session 36b: TF Monitoring Dashboard

**Date:** April 15, 2026
**Priority:** HIGH — prerequisito prima di flippare dry_run=false
**Prerequisito:** Brief 36a deployato ✅

---

## Context

Prima di abilitare il TF in live mode, Max ha bisogno di una pagina dove vedere cosa fa il TF e cosa gestisce l'orchestrator. Pagina privata — solo per Max, nessun link pubblico dal sito.

**URL:** `bagholderai.lol/tf` (o `/control` — scegli tu, coerente col sito)

---

## Dati disponibili in Supabase

Tutto via REST pubblico (come già fa il dashboard principale). Nessuna auth necessaria lato API — la pagina stessa sarà protetta da password SHA-256 come `admin.html`.

### Sorgenti dati

| Tabella/View | Cosa contiene |
|---|---|
| `tf_capital_summary` (VIEW) | `tf_budget`, `capital_deployed`, `capital_available`, `active_coins`, `tf_max_coins`, `total_realized_pnl` |
| `bot_config` | Tutti i bot, `is_active`, `managed_by`, `pending_liquidation`, `capital_allocation`, `buy_pct`, `sell_pct` |
| `trend_config` | `dry_run`, `trend_follower_enabled`, `scan_interval_hours`, `tf_budget`, `tf_max_coins` |
| `trend_decisions_log` | Ultime decisioni TF: `scan_timestamp`, `symbol`, `signal`, `action_taken`, `reason`, `is_shadow` |

### Query utili

```javascript
// Capital summary TF
GET /rest/v1/tf_capital_summary?select=*

// Bot config — tutti i bot
GET /rest/v1/bot_config?select=symbol,is_active,managed_by,pending_liquidation,capital_allocation,buy_pct,sell_pct&order=managed_by,symbol

// TF config
GET /rest/v1/trend_config?select=dry_run,trend_follower_enabled,scan_interval_hours,tf_budget,tf_max_coins&limit=1

// Ultime 20 decisioni TF (solo ALLOCATE/DEALLOCATE/SKIP — no HOLD)
GET /rest/v1/trend_decisions_log?select=scan_timestamp,symbol,signal,action_taken,reason,is_shadow&action_taken=in.(ALLOCATE,DEALLOCATE,SKIP)&order=created_at.desc&limit=20

// Ultima scan (per sapere quando TF ha girato l'ultima volta)
GET /rest/v1/trend_decisions_log?select=scan_timestamp&order=scan_timestamp.desc&limit=1
```

---

## Layout della pagina

Struttura in 4 sezioni verticali. Pagina protetta da password SHA-256 identica ad `admin.html`.

### Sezione 1 — Header + Status bar

```
BAGHOLDER AI — TF CONTROL ROOM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TF: ● SHADOW MODE    Last scan: 18:39 UTC    Next: ~22:39 UTC    [↻ Refresh]
```

- Indicatore SHADOW / LIVE basato su `dry_run` da `trend_config`
- Se `dry_run=false` → mostra "● LIVE" con colore diverso (attenzione)
- "Last scan" da `trend_decisions_log` ultima `scan_timestamp`
- "Next" calcolato come `last_scan + scan_interval_hours`

---

### Sezione 2 — TF Budget Overview (4 card)

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  BUDGET     │  │  DEPLOYED   │  │  AVAILABLE  │  │  REALIZED   │
│  $100       │  │  $0         │  │  $100       │  │  PnL: $0.00 │
│  max 2 coin │  │  0 / 2 coin │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

Dati da `tf_capital_summary`.

---

### Sezione 3 — Grid Bots Status

Due sottosezioni affiancate:

**TF-managed bots** (managed_by = 'trend_follower')
```
Nessun bot attivo al momento
```
Quando attivi:
```
● ETH/USDT    $50    buy 1.5% / sell 1.2%    ACTIVE
⏳ XRP/USDT   $50    liquidating...           PENDING LIQUIDATION
```

**Manual bots** (managed_by = 'manual')
```
● BTC/USDT    $200    buy 1.8% / sell 1.0%    ACTIVE
● SOL/USDT    $150    buy 1.5% / sell 1.0%    ACTIVE
● BONK/USDT  $150    buy 1.0% / sell 1.0%    ACTIVE
```

Colori: verde = attivo, arancio = pending_liquidation, grigio = inattivo.

---

### Sezione 4 — Recent TF Decisions

Tabella ultime 20 decisioni (solo ALLOCATE/DEALLOCATE/SKIP):

```
TIME          SYMBOL      SIGNAL     ACTION      REASON
18:39 UTC     BTC/USDT    BULLISH    HOLD        Signal: BULLISH (strength=9.9)
17:59 UTC     SOL/USDT    NO_SIGNAL  HOLD        Signal: NO_SIGNAL (strength=6.1)
```

Colori per action: ALLOCATE = verde, DEALLOCATE = rosso, SKIP = giallo, HOLD = grigio dim.
Badge `[SHADOW]` se `is_shadow=true`.

---

## Stile

Il sito usa dark theme su `#0a0a0a`, accenti verdi `#22c55e`, font monospace per dati tecnici. Segui lo stesso stile di `admin.html` e `index.html` esistenti:

- Background: `#0a0a0a` con griglia CSS sottile (già nel sito)
- Card: `rgba(255,255,255,0.03)` con border `rgba(255,255,255,0.08)`
- Accent: `#22c55e` (verde) per valori positivi / attivi
- Warning: `#eab308` (giallo) per SHADOW mode, pending
- Danger: `#ef4444` (rosso) per DEALLOCATE, inattivo
- Font: `SF Mono / Cascadia Code / Menlo` per dati, `SF Pro / system-ui` per testo
- Auto-refresh ogni 60 secondi (come il dashboard principale)

---

## Password gate

Stesso meccanismo di `admin.html`. SHA-256 della password in hardcode come hex. Usa la stessa password e lo stesso hash già presenti in `admin.html` — non inventarne una nuova.

---

## File da creare/modificare

| File | Azione |
|---|---|
| `web/tf.html` | CREATE — pagina completa standalone |
| `web/index.html` | NO — non aggiungere link pubblici alla pagina TF |

La pagina è standalone. Max ci accede direttamente via URL, non da un link nel sito.

---

## Navigazione interna (opzionale)

Se vuoi, aggiungi un link discreto "← Dashboard" in alto a sinistra che porta a `/` — solo quello, nessun altro link nav visibile pubblicamente.

---

## Test

```bash
# Verifica che la pagina carichi
open https://bagholderai.lol/tf
```

- [ ] Password gate funziona
- [ ] Dopo login, le 4 sezioni si caricano senza errori console
- [ ] `tf_capital_summary` mostra $100 budget, $0 deployed (stato attuale corretto)
- [ ] Sezione manual bots mostra BTC/SOL/BONK attivi
- [ ] Sezione TF bots mostra "nessun bot attivo" (corretto — dry_run=true ancora)
- [ ] "Last scan" mostra timestamp reale (es. 18:39 UTC)
- [ ] Decisioni recenti visibili in tabella (HOLD per BTC/SOL/BONK da shadow mode)
- [ ] Auto-refresh ogni 60s funziona
- [ ] Mobile responsive

---

## Scope rules

- **NON modificare** `index.html`, `admin.html`, o altri file esistenti
- **NON aggiungere** link pubblici alla pagina TF
- Push a GitHub quando done
- Stop quando done

---

## Commit format

```
feat(dashboard): TF control room — bot status, budget, decisions log
```
