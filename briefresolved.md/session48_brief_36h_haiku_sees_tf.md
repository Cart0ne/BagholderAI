# BRIEF — Session 36h: Haiku vede anche il TF nel commentary serale

**Date:** 2026-04-16
**Priority:** LOW — aspettare che il TF sia stabile prima di lanciarlo "in grande stile" nel commentary. Nel frattempo il report Haiku può continuare a vivere sui 3 bot manuali.
**Scope rule:** SOLO estendere l'input dati per il commentary Haiku. NON toccare prompt, modello, frequenza, pubblicazione Telegram.

---

## Problema

[commentary.py](commentary.py) riceve un `portfolio_data` costruito da `_build_portfolio_summary` in [bot/grid_runner.py:634](bot/grid_runner.py#L634). Quella funzione itera su `GRID_INSTANCES` hardcoded in [config/settings.py](config/settings.py) — contiene solo BTC/SOL/BONK.

Conseguenza:

- Le `positions` passate a Haiku non includono AXL, MBOX (TF vivi) né BIO, ORDI (TF morti con storia)
- I `today_trades_count` / `today_buys` / `today_sells` / `today_realized` sono aggregati globali su `trades` — quindi i numeri totali includono il TF, ma senza **attribuzione** per symbol né distinzione manuale vs TF
- `config_changes_log` loggato nelle ultime 24h cattura le modifiche manuali via admin UI, ma le ALLOCATE/DEALLOCATE del TF non passano da lì (scrivono direttamente `bot_config` con `managed_by='trend_follower'`)

Risultato serale: Haiku parla come se il TF non esistesse. Nessuna menzione di rotazioni coin, capital deployment TF, skim TF, nuovi simboli allocati oggi.

## Quando farlo

Quando il TF sarà stabilizzato (post 36e rotazione + 36g compounding), e avremo voglia di "lanciarlo in grande stile" nel commentary. Fino ad allora il silenzio su TF è accettabile: il TF è in rodaggio, far commentare Haiku ogni sera su rotazioni dubbie creerebbe rumore che invecchia male.

**Trigger per lanciare**: almeno 1 settimana di TF con comportamento atteso (budget deployato, rotazioni sensate, niente tapped-out).

## Obiettivo

Il report serale di Haiku deve poter dire, se rilevante:

- "Oggi il TF ha ruotato: dismesso BIO, MBOX entrata" (rotazioni del giorno)
- "AXL ha fatto +3 lotti, +$2.40 realizzati, skim $0.72" (attività TF del giorno)
- "Capital deployed TF: $95 / $100 — budget quasi pieno" (salute TF)

Senza forzare Haiku a parlarne quando non c'è nulla di notabile (coerente con la regola "quiet day is valid").

## Fix proposto

### 1. Estendere `_build_portfolio_summary` (grid_runner.py)

Oggi itera su `GRID_INSTANCES` (costante). Modificarlo per includere ANCHE i bot TF letti da `bot_config`:

```python
# Manual bots (from GRID_INSTANCES, come oggi)
for inst in GRID_INSTANCES:
    ...

# TF bots attivi: query bot_config WHERE managed_by='trend_follower' AND is_active=true
tf_active = supabase.table("bot_config").select(
    "symbol, capital_allocation"
).eq("managed_by", "trend_follower").eq("is_active", True).execute()

for row in tf_active.data or []:
    sym = row["symbol"]
    if any(p["symbol"] == sym for p in positions):
        continue  # già nel loop manuali (non dovrebbe succedere ma safety)
    # stessa logica di prima: pos, live_price, value, unrealized
    ...
    positions.append({
        ..., "managed_by": "trend_follower"
    })
```

Per i bot manuali marcare `managed_by: "manual"` nel dict positions, così Haiku può distinguere.

### 2. Aggiungere sezione TF-specific al `prompt_data` di Haiku

In [commentary.py](commentary.py) `generate_daily_commentary`:

```python
tf_activity = get_tf_activity_today(supabase_client)

prompt_data["tf_activity"] = {
    "active_symbols": [...],      # lista coin TF vive a fine giornata
    "allocations_today": [...],   # symbols allocated oggi dal TF
    "deallocations_today": [...], # symbols deallocated oggi dal TF
    "tf_realized_today": ...,     # realized PnL dei soli trade TF di oggi
    "tf_skim_today": ...,         # skim totale TF di oggi (da reserve_ledger filtrato per TF symbols)
    "tf_capital_deployed": ...,   # sum(capital_allocation) dei TF attivi
    "tf_budget": ...,             # tf_budget corrente da trend_config
}
```

### 3. Helper `get_tf_activity_today` (nuovo)

Query mirate su `trades`, `bot_config`, `reserve_ledger`, `trend_config` filtrando per `managed_by='trend_follower'` e data odierna.

### 4. Aggiornare COMMENTARY_SYSTEM_PROMPT

Aggiungere 1-2 righe per istruire Haiku che ora esistono bot manuali (BTC/SOL/BONK) E bot TF (rotazione, lista variabile), e che può menzionarli quando rilevanti. Esempio:

```
- Trading runs two tracks: a fixed manual portfolio (BTC/SOL/BONK) and
  an adaptive TF that rotates into smaller alts. Mention rotations,
  TF deployments, or TF skim ONLY when the day had meaningful activity
  there. Otherwise don't force it.
```

## Files da modificare

| File | Azione |
|---|---|
| `bot/grid_runner.py` | Estendere `_build_portfolio_summary` per includere bot TF attivi |
| `commentary.py` | Aggiungere helper `get_tf_activity_today` + sezione TF nel prompt_data + update system prompt |

## Files da NON toccare

- `config/settings.py` GRID_INSTANCES (resta come lista manuali, è la fonte giusta per quelli)
- `bot/trend_follower/*` (zero impatto sulla logica TF)
- `bot_config`, `trades`, `reserve_ledger` (solo lettura)
- Frequenza/orario del commentary (resta alla 20:00)

## Test pre-deploy

- [ ] Test isolato di `_build_portfolio_summary` con bot TF attivi → le loro positions appaiono nel result
- [ ] Test isolato di `get_tf_activity_today` con dati seed → verifica filtri date + managed_by
- [ ] Test `generate_daily_commentary` con `portfolio_data` esteso → Haiku produce commento coerente (almeno 3 run per vedere variabilità)
- [ ] Caso "giornata quieta TF" (zero attività) → Haiku non forza menzione TF

## Test post-deploy

- [ ] Il report serale del giorno dopo il deploy cita almeno una voce TF se c'è stata attività
- [ ] In giornata senza attività TF, il commento resta pulito (come oggi)
- [ ] Nessun errore Haiku API (logs `daily_commentary` table popolato come sempre)

## Rollback plan

Se il prompt Haiku scade di qualità o cita TF impropriamente:

```bash
git revert <commit_hash>
git push origin main
# git pull Mac Mini + restart orchestrator
```

Nessuna migration DB, rollback pulito.

## Commit format (al momento del fix)

```
feat(commentary): include TF activity in Haiku daily report

_build_portfolio_summary now merges TF-managed bot_config rows with
the manual GRID_INSTANCES. commentary prompt_data gains a tf_activity
section summarizing today's allocations, deallocations, realized PnL
and skim for the TF universe, so the evening log can speak to both
tracks.
```

---

## Out of scope

- Refactor generale di `_build_portfolio_summary` (è già fragile, ma fuori scope)
- Telegram formatting del report (quello lo fanno le funzioni `notifier.send_*_daily_report`, non Haiku — se servisse, brief separato)
- Cambi al modello Haiku (resta `claude-haiku-4-5-20251001`)
- Traduzione/localizzazione (resta in inglese come oggi)
