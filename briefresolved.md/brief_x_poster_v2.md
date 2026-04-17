# INTERN BRIEF — X Poster Redesign (v3 — CEO-reviewed)

**Date:** 2026-04-16
**Priority:** MEDIUM
**Prerequisito:** cron x_poster già funzionante ✅

---

## Cosa cambia rispetto a oggi

1. Ogni giorno alle 20:30 ora italiana il cron gira (invariato)
2. Legge **sempre l'ultimo diary** per `session DESC` — niente più filtro `posted_to_x=False` che causava post di sessioni vecchie quando la più recente aveva `status!='COMPLETE'`
3. Aggiunge al contesto di Haiku le modifiche a `bot_config` delle ultime 24h (`config_changes_log`)
4. Se il diary più recente è vecchio (≥36h), ignora il diary e usa solo le config changes. Se anche le config changes sono vuote → skip totale con Telegram "nulla di nuovo oggi"
5. Il pending draft viene salvato su **Supabase `pending_x_posts`** invece che su `/tmp/pending_x_post.json` → sopravvive a riavvii e non dipende dal filesystem
6. La firma fissa diventa `🤖 AI · bagholderai.lol` (senza `https://`) → X non genera la card brutta del webview

**Cosa NON cambia** (esplicitamente):
- Il messaggio Telegram con `/approve · /discard · /rewrite` come oggi — link blu cliccabili, zero bottoni inline nuovi
- `x_poster_approve.py` resta (solo migrato a leggere da `pending_x_posts` invece che da file)
- `SYSTEM_PROMPT` attuale in `utils/x_poster.py` resta come voce — aggiungiamo solo il blocco config changes al `user_msg`
- `already_posted_today()` check resta (anti-dupe giornaliero)

---

## Firma fissa

Ogni post termina con:

```
🤖 AI · bagholderai.lol
```

- `bagholderai.lol` scritto **senza** `https://` → appare come testo, X non genera card
- Nessun link alla sessione del diary nel tweet
- Hardcoded, non generata da Haiku
- Variabile: `DEFAULT_SIGNATURE` in `utils/x_poster.py` (già esiste — solo verificare contenuto)

---

## Tabella Supabase `pending_x_posts`

Crea via migration SQL:

```sql
CREATE TABLE IF NOT EXISTS pending_x_posts (
    key TEXT PRIMARY KEY,
    session INTEGER,
    title TEXT,
    summary TEXT,
    draft TEXT NOT NULL,
    signature TEXT NOT NULL DEFAULT '🤖 AI · bagholderai.lol',
    generated_at TIMESTAMPTZ DEFAULT now()
);
```

Unico record in tabella, chiave fissa `pending_x_post`. Upsert a ogni generate, delete dopo approve/discard.

---

## 1. `utils/x_poster.py`

### 1a. `get_latest_diary()` — rimpiazza `get_latest_unposted_diary`

```python
def get_latest_diary() -> dict | None:
    """Legge sempre l'ultimo diary per session. Nessun filtro su posted_to_x o status.
    Il filtro posted_to_x=False causava bug quando una session più recente aveva
    status='DRAFT' — il poster prendeva la precedente già postata."""
    sb = get_client()
    result = (
        sb.table("diary_entries")
        .select("session, title, summary, created_at")
        .order("session", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
```

### 1b. `get_recent_config_changes()`

```python
def get_recent_config_changes() -> list[dict]:
    """Modifiche a bot_config nelle ultime 24h. Campi reali del DB:
    symbol, parameter, old_value, new_value, created_at."""
    from datetime import datetime, timezone, timedelta
    sb = get_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        result = (
            sb.table("config_changes_log")
            .select("symbol, parameter, old_value, new_value, created_at")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"config_changes_log read failed: {e}")
        return []
```

### 1c. Aggiornamento `generate_post` — riuso del `SYSTEM_PROMPT` esistente

Tieni il `SYSTEM_PROMPT` attuale pari pari (voce, tono, limiti). Cambia solo il `user_msg` per includere contesto delle config changes e l'età del diary:

```python
def generate_post(
    diary: dict | None,
    config_changes: list[dict],
    use_diary: bool,
    max_retries: int = 3,
) -> str:
    """Generate an X post using Haiku. Keeps existing SYSTEM_PROMPT voice."""
    client = anthropic.Anthropic(api_key=SentinelConfig.ANTHROPIC_API_KEY)

    # Build context block
    parts = []
    if use_diary and diary:
        parts.append(f"Session title: {diary['title']}\n\nSession summary:\n{diary['summary']}")
    elif diary:
        parts.append(
            f"(Diary is stale — last session too old to feature. Keep it in mind only as background.)\n"
            f"Old session title: {diary['title']}"
        )
    if config_changes:
        changes_lines = [
            f"- {c['symbol']} {c['parameter']}: {c['old_value']} → {c['new_value']}"
            for c in config_changes
        ]
        parts.append("Bot config changes (last 24h):\n" + "\n".join(changes_lines))
    if not parts:
        # Defensive fallback (caller should have skipped already)
        parts.append("Quiet day. No session, no config changes.")

    user_msg = "\n\n".join(parts)

    for attempt in range(1, max_retries + 1):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        draft = response.content[0].text.strip()
        if len(draft) <= MAX_POST_CHARS:
            return draft
        logger.warning(
            f"Draft too long ({len(draft)} > {MAX_POST_CHARS}), retry {attempt}/{max_retries}"
        )
        user_msg += f"\n\nYour last draft was {len(draft)} chars. Max {MAX_POST_CHARS}. Shorter."

    logger.warning(f"Could not get draft under {MAX_POST_CHARS} after {max_retries} retries")
    return draft
```

**Nota breaking change**: la firma di `generate_post` cambia. `x_poster_approve.py` nel `cmd_rewrite` chiama il vecchio `generate_post(summary, title)` → va aggiornato coerentemente.

### 1d. `pending_x_posts` helpers

```python
PENDING_KEY = "pending_x_post"
DIARY_STALE_HOURS = 36  # diary più vecchio di questo → usa solo config changes

def save_pending_draft(session: int | None, title: str | None, summary: str | None,
                       draft: str, signature: str) -> None:
    sb = get_client()
    try:
        sb.table("pending_x_posts").upsert({
            "key": PENDING_KEY,
            "session": session,
            "title": title,
            "summary": summary,
            "draft": draft,
            "signature": signature,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"save_pending_draft failed: {e}")

def get_pending_draft() -> dict | None:
    sb = get_client()
    try:
        r = sb.table("pending_x_posts").select("*").eq("key", PENDING_KEY).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_pending_draft failed: {e}")
        return None

def clear_pending_draft() -> None:
    sb = get_client()
    try:
        sb.table("pending_x_posts").delete().eq("key", PENDING_KEY).execute()
    except Exception as e:
        logger.error(f"clear_pending_draft failed: {e}")
```

---

## 2. `x_poster.py` — `cmd_cron` ridisegnato

```python
def cmd_cron(args):
    """Cron mode: read diary + config changes → generate → save pending → notify."""
    notifier = SyncTelegramNotifier()

    # 1. Anti-dupe check (kept as-is)
    if already_posted_today():
        logger.info("Already posted today. Skipping.")
        notifier.send_message("⏸ <b>X post skip</b> — già postato oggi.")
        return

    # 2. Pending still waiting?
    pending = get_pending_draft()
    if pending:
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(pending["generated_at"].replace("Z","+00:00"))
                 ).total_seconds() / 3600
        if age_h < 24:
            logger.info(f"Pending draft exists ({age_h:.1f}h). Skipping regeneration.")
            notifier.send_message(
                f"⏸ <b>X post skip</b> — bozza Session {pending.get('session','?')} "
                f"ancora in attesa ({age_h:.1f}h).\n"
                f"Comandi: /approve · /discard · /rewrite"
            )
            return
        else:
            logger.info("Pending draft stale (>24h). Regenerating.")
            clear_pending_draft()

    # 3. Load inputs
    diary = get_latest_diary()
    config_changes = get_recent_config_changes()

    # 4. Decide diary freshness
    use_diary = False
    if diary:
        diary_age_h = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(diary["created_at"].replace("Z","+00:00"))
                       ).total_seconds() / 3600
        use_diary = diary_age_h < DIARY_STALE_HOURS

    # 5. Skip if nothing to say
    if not use_diary and not config_changes:
        logger.info("Stale diary + no config changes. Skipping.")
        notifier.send_message(
            "ℹ️ <b>X post skip</b> — diary vecchio e nessuna modifica config nelle ultime 24h. "
            "Nulla di nuovo oggi."
        )
        return

    # 6. Generate draft
    draft = generate_post(diary, config_changes, use_diary)

    # 7. Save + notify
    save_pending_draft(
        session=(diary["session"] if diary and use_diary else None),
        title=(diary["title"] if diary and use_diary else None),
        summary=(diary["summary"] if diary and use_diary else None),
        draft=draft,
        signature=DEFAULT_SIGNATURE,
    )
    full_text = f"{draft}\n\n{DEFAULT_SIGNATURE}"
    session_tag = (f"Session {diary['session']}" if diary and use_diary else "Config summary")
    notifier.send_message(
        f"🐦 Bozza post X ({session_tag}):\n\n"
        f"{draft}\n\n"
        f"{DEFAULT_SIGNATURE}\n\n"
        f"📏 {len(full_text)}/270 chars\n\n"
        f"Comandi: /approve · /discard · /rewrite"
    )
    logger.info(f"Draft sent to Telegram ({len(full_text)}/270 chars). Awaiting approval.")
```

---

## 3. `x_poster_approve.py` — migrazione da file a DB

Sostituisci `load_pending()`, `delete_pending()` con chiamate a `get_pending_draft()` e `clear_pending_draft()`. Elimina `PENDING_FILE` e `import os/json` non più necessari per quel fine.

I 3 handler (`cmd_approve`, `cmd_discard`, `cmd_rewrite`) restano con la stessa UX — solo il backend cambia.

`cmd_rewrite` deve ora ricostruire un `diary` dict fittizio dai campi salvati in `pending_x_posts` (session, title, summary) per poter richiamare il nuovo `generate_post`. Config changes si ri-leggono fresche (potrebbero essere cambiate nel frattempo).

---

## 4. File da modificare

| File | Azione |
|---|---|
| `utils/x_poster.py` | Rimpiazza `get_latest_unposted_diary`, aggiungi `get_recent_config_changes`, `save/get/clear_pending_draft`. Nuova firma di `generate_post`. Costante `DIARY_STALE_HOURS=36`. |
| `x_poster.py` | `cmd_cron` ridisegnato (sopra). `cmd_generate_only` aggiornato per la nuova firma. |
| `x_poster_approve.py` | `load_pending`/`delete_pending` → DB. `cmd_rewrite` con nuova firma. `PENDING_FILE` rimosso. |
| Supabase migration | `CREATE TABLE pending_x_posts` (SQL sopra) |

---

## 5. Test

```bash
cd /Volumes/Archivio/bagholderai
source venv/bin/activate

# Genera draft senza mandare a Telegram, per ispezione
python3.13 x_poster.py --generate-only
```

- [ ] Draft < 250 chars (limite MAX_POST_CHARS attuale)
- [ ] Firma aggiunta correttamente senza `https://`
- [ ] Row in `pending_x_posts` dopo `--cron`
- [ ] Telegram arriva con `/approve · /discard · /rewrite` cliccabili
- [ ] `/approve` pubblica su X, `posted_to_x=true` sul diary (se usato), row `pending_x_posts` cancellata
- [ ] `/discard` cancella solo la row pending, nessun post
- [ ] `/rewrite` genera nuovo draft (stesso diary/config) e aggiorna la row
- [ ] Caso "diary > 36h vecchio" + config_changes vuote → skip, nessun post, Telegram informativo
- [ ] Caso "diary fresco + config_changes vuote" → funziona come oggi
- [ ] Caso "diary vecchio + config_changes presenti" → post sulle config changes, `session` nullo in pending_x_posts

---

## 6. Scope rules

- **Non toccare** la logica dei bot o dell'orchestrator
- **Non aggiungere** `https://` nella firma — è testo puro per evitare la card Twitter
- Tabella `pending_x_posts` via migration SQL, non `execute_sql`
- Push quando done
- Stop quando done

---

## Commit format

```
feat(x-poster): latest diary + config changes context, DB pending, 36h staleness
```
