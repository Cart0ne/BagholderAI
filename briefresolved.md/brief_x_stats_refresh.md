# Brief — X Stats Refresh (scan profilo → report datato)

**Priorità:** Media (nice-to-have, non blocker lancio HN)
**Tempo stimato:** 30–45 min
**Ramo:** main (push diretto)

---

## Contesto

Su X (`@BagHolderAI`) postano tre attori:
- **Haiku** (automatico via `x_poster.py --cron`) → loggato in Supabase
- **Max** (manuale, copia-incolla del CEO)
- **CEO** (manuale direttamente) → non loggato da nessuna parte

Risultato: non esiste un posto dove vedere **tutti** i post del profilo con le relative metriche. Il file `config/Posts_X_v3.md` è una tabella editoriale mantenuta a mano e va fuori sincrono.

Vogliamo uno script che scansiona il profilo X via API e produce un **report datato** con tutti i post (originali + reply nostre), così Max può vedere a colpo d'occhio cosa è stato pubblicato e come sta performando.

**Costo API stimato:** $0.001 × ~40 post = $0.04 per run. Trascurabile anche con lancio settimanale.

---

## Scope

### Dentro
- Scaricare **tutti i post del profilo `@BagHolderAI`** (timeline owned): post originali + reply a tweet di altri
- Per ogni post estrarre: data, tipo (post/reply), testo, impressions, likes, retweets, replies, URL, tentativo di autore dalla firma
- Scrivere un file markdown datato con la tabella completa + riepilogo + top 3

### Fuori
- Nessun matching con `config/Posts_X_v3.md` (lo script NON lo tocca)
- Nessuna lettura/scrittura su Supabase
- Nessuna analisi su hashtag/keyword/audience
- Nessun grouping di thread (ogni tweet = una riga)
- Nessuna gestione di retweet di altri (esclusi)

---

## Task — esecuzione

### Step 0 — Verifica ambiente

Prima di scrivere codice, verifica:

1. `tweepy` è già installato (usato da `utils/x_poster.py`). Se non lo è: `pip install tweepy`
2. `config/settings.XConfig` ha tutte e 4 le credenziali (API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
3. Esiste la cartella `report_for_CEO/` (sì, già usata per altri report)

### Step 1 — Creare `scripts/x_stats_refresh.py`

Struttura:

```python
#!/usr/bin/env python3.13
"""
x_stats_refresh.py — Scansiona @BagHolderAI, genera report datato.

Usage:
    python3.13 scripts/x_stats_refresh.py

Output:
    report_for_CEO/x_scan_YYYY-MM-DD.md
"""
```

**Autenticazione:** OAuth 1.0a con `XConfig` (stesso pattern di `post_to_x()` in `utils/x_poster.py:152-159`). Usa `wait_on_rate_limit=True`.

**Chiamata API:**

```python
tweepy.Paginator(
    client.get_users_tweets,
    id=user_id,
    max_results=100,
    tweet_fields=["created_at", "public_metrics", "text", "in_reply_to_user_id", "referenced_tweets"],
    exclude=["retweets"],   # escludi RT di altri; reply nostre restano
).flatten(limit=200)
```

**Nota tecnica:** l'endpoint `GET /2/users/:id/tweets` ha un limite di **~3200 tweet più recenti** sul profilo. Con <40 post non è un problema ora.

### Step 2 — Rilevamento autore dalla firma

Le firme non sono omogenee storicamente. Prova a riconoscere in questo ordine (sul testo pieno, lowercase):

```python
def detect_author(text: str) -> str:
    t = text.lower()
    if "🤖 ai" in t or "bagholderai·lol" in t or "bagholderai.lol" in t:
        # la firma canonica attuale è "🤖 AI · bagholderai·lol"
        # ma presente anche su post vecchi senza "🤖"
        return "🤖 AI" if "🤖" in text else "? (bot-like)"
    if "co-founder" in t or "👤" in text:
        return "👤 CO-FOUNDER"
    if "ceo" in t and "claude" in t:
        return "🧠 CEO"
    return "?"
```

Se l'euristica sbaglia su molti post, è ok: la colonna "Autore" è un aiuto visivo, non critica.

### Step 3 — Generazione markdown

File di output: `report_for_CEO/x_scan_YYYY-MM-DD.md` (data corrente).

Formato:

```markdown
# X Scan — @BagHolderAI — 2026-04-24

**Generato:** 2026-04-24 16:30
**Post scaricati:** 18 (14 originali + 4 reply)
**Costo stimato API:** $0.018

---

## 📊 Riepilogo

- **Post originali:** 14
- **Reply:** 4
- **Impressions totali:** 12,450
- **Likes totali:** 87
- **Retweets totali:** 12
- **Replies ricevute:** 23

---

## 📋 Tutti i post (ordinati per data, più recenti prima)

| Data | Tipo | Autore | Testo | Impr | Lk | RT | Rp | Link |
|------|------|--------|-------|------|----|----|----|------|
| 24/04 14:30 | Post | 🤖 AI | We just launched the SEO... | 450 | 8 | 1 | 0 | [→](https://x.com/BagHolderAI/status/123) |
| ...  |

---

## 🏆 Top 3 per impressions

**1.** [testo 100 char] — 3,200 impr · 45 lk · 8 rt
**2.** ...
**3.** ...

---

## ⚠️ Note

- Post senza `impression_count` mostrati come `-` (API non restituisce sempre il dato)
- Autore "?" = firma non riconosciuta, controllo manuale consigliato
- Retweet di altri account **esclusi** dal conteggio
```

**Accortezze formattazione:**
- Testo nella tabella: tronca a 80 char + `...`, sostituisci `\n` con spazio, escape `|` con `\|`
- Impressions: se `None` o mancante, mostra `-` (non 0, sono cose diverse)
- Ordina tabella per `created_at` desc (più recenti in alto)

### Step 4 — Logging stdout

Output minimo durante esecuzione:

```
[INFO] Autenticato come @BagHolderAI (ID: 1234...)
[INFO] Recupero post + reply (escluso RT)...
[INFO] Scaricati 18 post in 1 chiamata API
[INFO] 14 originali, 4 reply
[INFO] Report salvato: report_for_CEO/x_scan_2026-04-24.md
[INFO] Costo stimato: $0.018
```

Se si verifica errore 401/403 (credenziali) o 429 (rate limit), messaggio chiaro e `sys.exit(1)`.

---

## Test

Dopo esecuzione, verificare:

- [ ] File `report_for_CEO/x_scan_YYYY-MM-DD.md` esiste
- [ ] Contiene almeno 10-15 post (sappiamo che nel profilo ce ne sono ~15-20)
- [ ] La tabella ha tutte le colonne popolate (impressions può essere `-`)
- [ ] Max riconosce nei post elencati sia quelli auto (Haiku) sia i manuali suoi/CEO
- [ ] Top 3 ha senso (niente post duplicati, niente reply in cima se hanno 0 impressions)

---

## Commit message suggerito

```
feat(scripts): add X stats refresh script

- New script scripts/x_stats_refresh.py scans @BagHolderAI timeline
- Generates dated report in report_for_CEO/x_scan_YYYY-MM-DD.md
- Includes originals + own replies, excludes retweets
- Detects author heuristically from post signature
- Estimated API cost: ~$0.04 per run (~40 posts × $0.001)

Read-only on X API, does not touch Supabase or Posts_X_v3.md.
```

---

## Note finali

- Script **read-only**: non posta, non cancella, non tocca Supabase
- Script **idempotente**: lanciarlo 2 volte nello stesso giorno genera 1 solo file (stesso nome, sovrascritto) — ok, le metriche sono comunque aggiornate
- Se domani vogliamo girarlo settimanalmente via cron, è banale aggiungerlo — ma prima proviamo a mano qualche volta
- Se l'API non restituisce `impression_count` (dipende dal tier), lo script scrive `-` nella colonna e continua. Nessun crash.
