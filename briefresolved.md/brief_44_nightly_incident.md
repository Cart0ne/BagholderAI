# BRIEF — Session 44: Nightly incident (2026-04-21 notte)

**Date:** 2026-04-21 (da discutere col CEO)
**Priority:** HIGH per Bug 1 (spam Telegram), MEDIUM per Bug 2 (consistenza DB), LOW per Bug 3 (policy)
**Prerequisito:** nessuno — tre fix indipendenti
**Target branch:** `main` (commit separati, 44a/44b/44c)

---

## Cosa è successo

Nella notte tra il 20 e il 21 aprile 2026, il Mac Mini ha avuto una **finestra di ~45 minuti di problemi di rete** (04:25–05:09 locale, `[Errno 60] Operation timed out` sui chiamate `httpx` verso Supabase). L'infra ha gestito il blackout **male su un fronte, silenziosamente su un altro**:

- **Orchestrator:** ~20-25 messaggi Telegram `🚨 Orchestrator error` identici durante i 45 min di blackout. Nessun retry/backoff.
- **TF scanner:** 3 decisioni ALLOCATE loggate in `trend_decisions_log` come applicate ma i rispettivi `bot_config` non sono mai stati creati (INSERT fallito silenziosamente).
- Bonus: una di queste ALLOCATE era per `币安人生/USDT` con `signal_strength=8.94` — un valore molto basso che fa pensare che il TF stesse allocando "qualunque cosa" pur di deployare.

Per contesto, **EDU/USDT** ha funzionato correttamente durante la notte: multi-lot entry + greed decay + stop-loss + re-allocate + nuove sell. Chiusura ciclo in profit (+$1.36). 42a non ha causato problemi.

---

## Bug 1 — Orchestrator spamma Telegram durante i blackout di rete

### Sintomo

Durante i ~45 min di blackout rete, il log dell'orchestrator ([`~/bagholder-orchestrator.log`](/Users/max/bagholder-orchestrator.log) su Mac Mini) ha accumulato ~20-25 righe:

```
04:25:10 [bagholderai.orchestrator] ERROR: Orchestrator error: [Errno 60] Operation timed out
httpcore.ConnectTimeout: [Errno 60] Operation timed out
httpx.ConnectTimeout: [Errno 60] Operation timed out
04:25:59 [bagholderai.orchestrator] ERROR: Orchestrator error: [Errno 60] Operation timed out
...
```

Ogni volta il codice al [bot/orchestrator.py:251-256](bot/orchestrator.py#L251-L256) manda un Telegram:

```python
except Exception as e:
    logger.error(f"Orchestrator error: {e}", exc_info=True)
    try:
        notifier.send_message(
            f"🚨 <b>Orchestrator error</b>\n<code>{str(e)[:300]}</code>"
        )
    except Exception:
        pass
```

Risultato: circa 20-25 messaggi Telegram identici nel cuore della notte.

### Causa

Il main loop dell'orchestrator non distingue tra **errori transienti** (timeout rete, Supabase temporaneamente giù) e **errori strutturali** (bug di codice, permessi, state corrotto). Ogni `Exception` viene trattata nello stesso modo:
1. Logga
2. Manda Telegram
3. Prosegue il loop (quindi ritenta a breve)

Il pattern corretto per i transienti esiste già in altre parti del codebase — per esempio [`SupabaseConfigReader.refresh`](config/supabase_config.py:140) gestisce Supabase unreachable facendo warning + keep last known config. L'orchestrator non ha l'equivalente.

### Fix proposto

**Opzione A (minimale, raccomandata):** rate-limit sul Telegram alert, invariato il log behavior.

```python
# Stato in-module
_orchestrator_alert_last_sent: float = 0.0
ORCHESTRATOR_ALERT_COOLDOWN = 15 * 60  # 15 minuti tra alert identici consecutivi

except Exception as e:
    logger.error(f"Orchestrator error: {e}", exc_info=True)
    now = time.time()
    if (now - _orchestrator_alert_last_sent) >= ORCHESTRATOR_ALERT_COOLDOWN:
        try:
            notifier.send_message(
                f"🚨 <b>Orchestrator error</b>\n<code>{str(e)[:300]}</code>"
            )
            _orchestrator_alert_last_sent = now
        except Exception:
            pass
    # Aggiungi backoff prima del prossimo cycle per ridurre CPU spam
    time.sleep(30)
```

Pro: safe, non rompe nulla, un solo alert ogni 15 min anche in blackout persistente, log intatto per debug post-hoc.

**Opzione B (più intrusiva):** classificare l'exception. Se è `httpx.ConnectTimeout` / `httpx.ReadTimeout` / `ConnectionError` → warning only, no Telegram. Altri exception → alert immediato.

Pro: messaggi migliori. Contro: rischio di inghiottire errori che vorresti sapere; ogni tanto qualche `ConnectionError` nasconde un bug vero.

**Raccomandazione:** A. Semplice, sicuro, restituisce a 0-1 Telegram per incidente di rete.

### Dubbio da discutere

- **15 min di cooldown è il valore giusto?** Se la rete cade per 6 ore, vuoi 24 Telegram (1 ogni 15 min) o 1 solo messaggio + uno di "risolto" al ritorno? Il primo approccio rassicura che l'orchestrator è ancora vivo, il secondo è più pulito ma rischi di dimenticare che sta ancora down. La mia preferenza è il primo.

---

## Bug 2 — ALLOCATE non è atomico rispetto a `bot_config`

### Sintomo

Nella notte, `trend_decisions_log` registra 3 ALLOCATE applicate che non hanno la corrispondente row in `bot_config`:

```
2026-04-21T03:09:53  ALLOCATE  PORTAL/USDT      str=24.5
2026-04-21T03:09:53  ALLOCATE  XLM/USDT         str=11.02
2026-04-21T03:09:53  ALLOCATE  币安人生/USDT      str=8.94
```

Nessuno di questi symbol ha una row in `bot_config`. Significa che **il grid_runner per loro non è mai partito** — erano bot fantasma.

### Causa

Nel flusso [`apply_allocations`](bot/trend_follower/allocator.py:517) a [riga 542-612](bot/trend_follower/allocator.py#L542-L612):

1. L'allocator costruisce `row_fields` completo
2. Fa `supabase.table("bot_config").insert(...)` — se esiste già la row, fa `update(...)`
3. Se l'INSERT/UPDATE fallisce → `except Exception as e: logger.error(...)` e la row non viene creata

Ma **prima** di tutto questo, [`_make_decision`](bot/trend_follower/allocator.py) ha già inserito la row in `trend_decisions_log` con `action_taken="ALLOCATE"`. Quindi dal punto di vista del log sembra che l'ALLOCATE sia stato applicato; nella realtà il grid_runner non partirà mai perché non c'è bot_config.

Ipotesi su cosa è andato storto alle 03:09: il blackout di rete è iniziato ~04:25, quindi non è la causa diretta. Più probabile: il POST su bot_config ha avuto un altro errore (forse lock transient, duplicazione, qualche RLS policy) che il codice ha ingoiato senza creare alert. Le righe `Failed to apply ALLOCATE for BIO/USDT` mostrano che l'handler esiste, ma produce solo un `logger.error`. Nessun Telegram, nessuna retrocessione del `trend_decisions_log`.

### Fix proposto

**Opzione A (raccomandata):** fare l'ALLOCATE in due fasi logiche.

1. Insert bot_config PRIMA, log_decision DOPO
2. Se bot_config fallisce → log_decision marca l'azione come `ALLOCATE_FAILED` (nuovo action_taken) con il `reason` che riporta l'errore

```python
# allocator.py apply_allocations, sezione ALLOCATE
try:
    supabase.table("bot_config").insert({"symbol": symbol, **row_fields}).execute()
    # ... log INFO come oggi
except Exception as e:
    logger.error(f"[ALLOCATOR] Failed to apply ALLOCATE for {symbol}: {e}")
    # Retrocedere la decision: aggiornare il trend_decisions_log
    supabase.table("trend_decisions_log").update({
        "action_taken": "ALLOCATE_FAILED",
        "reason": f"bot_config INSERT failed: {str(e)[:200]}"
    }).eq("scan_ts", scan_ts).eq("symbol", symbol).execute()
    # Telegram alert (dipende se Bug 1 è stato fixato, usare lo stesso
    # rate limiter di conseguenza)
    notifier.send_message(f"🚨 <b>ALLOCATE FAILED: {symbol}</b>\n<code>{str(e)[:200]}</code>")
```

**Opzione B (più radicale):** introdurre una vera transazione DB usando PostgreSQL savepoint. Ma Supabase JS/Python client non esponeno transazioni facilmente — serve una stored procedure RPC. Overkill per il problema attuale.

**Raccomandazione:** A. Manteniamo lo stile "log first, correct after" coerente col resto del codebase.

### Dubbio da discutere

- Il nuovo action `ALLOCATE_FAILED` richiede aggiornamento del CHECK constraint su `trend_decisions_log.action_taken` (se esiste uno). Da verificare lo schema prima di implementare, altrimenti l'UPDATE fallisce a sua volta. Se il CHECK c'è, migration + valore aggiunto.
- Alternativa: invece di nuovo action, marcare con `reason = "ALLOCATE_FAILED: ..."` lasciando `action_taken="ALLOCATE"`. Meno pulito ma no-schema-change.

---

## Bug 3 — TF alloca candidati con signal_strength molto bassi

### Sintomo

`币安人生/USDT` è stato proposto ALLOCATE con `signal_strength=8.94`. Per contesto, normalmente gli ALLOCATE avvengono su strength ≥ 15. 8.94 è una soglia "disperata" — pattern di "allocare per allocare", non "trovare un forte bullish".

La riga nel log:
```
2026-04-21T03:09:53  ALLOCATE  币安人生/USDT  BULLISH  str=8.94
                     reason:   BULLISH T3 — $10 (equal-split 4/5)
```

"4/5" suggerisce che l'allocator aveva 5 slot e ne ha piazzati 4 tra PORTAL (str 24.5), XLM (str 11.02), 币安人生 (str 8.94), più un quarto non identificato. Il tier C (small cap) aveva evidentemente pochi bullish decenti quella notte e il TF ha raschiato il barile.

### Causa

L'allocator non ha un **minimum signal_strength threshold**. Prende tutti i coin con `signal="BULLISH"` e li ordina per strength, assegnando capitale finché ci sono slot. Se il mercato è in laterale-negativo, la coda bullish è piatta e bassa → comunque alloca.

### Fix proposto

Aggiungere in `trend_config` un nuovo campo `min_allocate_strength` (default 15.0). L'allocator skippa candidati con `signal_strength < min_allocate_strength` con reason "strength below threshold".

```sql
ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS min_allocate_strength NUMERIC NOT NULL DEFAULT 15.0;
```

Nel codice allocator, dopo il `for coin in sorted_bullish`:

```python
min_strength = float(config.get("min_allocate_strength", 15.0))
if coin.get("signal_strength", 0) < min_strength:
    decisions.append(_make_decision(
        scan_ts, coin["symbol"], coin, "SKIP",
        f"signal_strength {coin['signal_strength']:.1f} below threshold {min_strength}",
    ))
    continue
```

Admin UI: aggiungere il campo al panel TF Safety Parameters come gli altri.

### Dubbio da discutere

- **15 è il valore giusto di default?** Guardando il log di oggi, gli ALLOCATE "onesti" sono stati 28.7 (GUN), 18.0 (SPK), 17.9 (BLUR), 16.5 (CHZ), 30.96 (EDU), 24.5 (PORTAL), 11.0 (XLM). Con threshold 15, PORTAL e XLM non sarebbero state allocate. 11 è borderline — XLM era bullish ma debole.
- Alternativa: **threshold scalato per tier** (T1 large cap più permissivo, T3 small cap più stretto). Più complesso ma più difendibile.
- Alternativa #2: non fissare un threshold minimo ma **non deployare capitale se non c'è un candidato forte**. Cioè: se il miglior bullish è str 8.94, meglio cash fermo che una scommessa debole. Richiede che il TF abbia "pazienza". Il tuo "budget TF idle" è già un problema che hai toccato — qui però invece di forzare ALLOCATE, si preferisce aspettare.
- **La mia opinione:** Alternativa #2 è la più sana ma andrebbe discussa col CEO come choice di strategia. Il threshold 15 è un compromesso safe per iniziare.

---

## Osservazioni bonus (non sono bug, solo note)

1. **EDU ha funzionato bene.** Due stop-loss + 2 greed decay sell + ciclo chiuso in profit. 42a regge.
2. **Gli errori BIO/ORDI "grid_levels NOT NULL"** che vedo nel log di `trend_follower.log` alle 22:25/22:29 sono del log pre-restart di ieri sera (prima di `a97f1ca` dove avevo aggiunto i placeholder `grid_levels=10, grid_lower=0, grid_upper=0`). Righe residue, già fixate. Non un nuovo bug.
3. **`SupabaseConfigReader` ha gestito il blackout bene.** Le WARN "Supabase unreachable during refresh, keeping last known config" sono il comportamento corretto. Vale come reference per il Bug 1.

---

## Proposta di packaging

Tre commit separati:

- **44a** — Bug 1 orchestrator rate limit (priorità alta, ~30 min)
- **44b** — Bug 2 ALLOCATE atomic/retrocedi decision (~45 min, migration opzionale)
- **44c** — Bug 3 min_allocate_strength (~45 min, migration obbligatoria + UI)

Deploy: raccomando 44a stanotte (stoppa spam Telegram), 44b + 44c insieme dopo discussione col CEO sulle scelte di default.

---

## Out of scope

- **Retry logic strutturata** (retries + exponential backoff come libreria dedicata) — overkill per ora, il rate limit su alert basta
- **Monitoraggio di rete dal Mac Mini** (ping Supabase ogni N min, alert se down) — serve un sistema di osservabilità h24 che non abbiamo ancora
- **Rollback automatico delle decisions_log** su errore — lo tracceremo come commento nel reason, non come stato strutturato
- Riforma di come il TF decide "quante coin allocare": oggi è `max_grids` hard limit. Brief separato se vorremo una policy più dinamica.

---

## Test pre-deploy

**Bug 1:**
1. Disconnettere la rete del Mac mentre l'orchestrator gira, verificare che dopo il primo Telegram non arrivano altri per 15 min.
2. Riconnettere, verificare che al prossimo errore (se succede) il cooldown reset consente un nuovo alert.

**Bug 2:**
1. Simulare fallimento INSERT bot_config: patch manuale di una RLS policy temporanea per rifiutare INSERT su bot_config solo per un symbol specifico; scatenare un ALLOCATE su quel symbol; verificare che `trend_decisions_log.reason` contenga l'errore e Telegram arrivi.

**Bug 3:**
1. Settare `min_allocate_strength=50.0` via UI (valore alto, ragionevolmente nessuna coin lo supera).
2. Aspettare il prossimo scan, verificare che tutti i bullish con strength < 50 vengano SKIP'd.
3. Rimettere 15.0 dopo la verifica.

---

## Rollback plan

Standard pattern:
```bash
git revert <commit>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# restart orchestrator
```

Per 44c, la migration va revertita solo se rompe qualcosa — la colonna ha default safe, può restare.
