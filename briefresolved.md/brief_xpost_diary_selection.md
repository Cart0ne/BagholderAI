# BRIEF — X post bugs (diary selection + link preview)

**Date:** 2026-04-15
**Priority:** medium — affects public-facing posts

---

## Context

Sessione 35b ha confermato che il cron x_poster funziona (permessi TCC concessi, Telegram arriva). Ma il post pubblicato su X ha due difetti.

## Bug 1 — Diary sbagliato (sessione 34 invece di 35)

Il post di oggi ha usato il diario della **sessione 34**, non della 35 che è quella recente.

Selezione attuale (`utils/x_poster.py:162-172`):
```python
sb.table("diary_entries")
  .select("session, title, summary")
  .eq("posted_to_x", False)
  .order("session", desc=True)
  .limit(1)
```

Ipotesi:
- La diary entry della sessione 35 non era ancora scritta quando il cron è partito (scritta più tardi quel giorno?)
- **OPPURE** sessione 34 aveva `posted_to_x=False` da un precedente fallimento → ha superato la 35 nella query perché la 35 non esisteva ancora → quando la 35 è stata aggiunta, il cron aveva già postato la 34.

**Da verificare su Supabase:**
```sql
SELECT session, title, posted_to_x, created_at
FROM diary_entries
ORDER BY session DESC
LIMIT 5;
```

**Fix possibile:** invece di `ORDER BY session DESC`, ordinare per `created_at DESC` e postare la diary più recente in assoluto. Oppure: aggiungere check "session > last_posted_session" dentro `get_latest_unposted_diary()`. Decidere quale semantica preferire.

## Bug 2 — Link preview vuoto dentro X in-app browser

Il post contiene link a `bagholderai.lol/diary.html?session=XX` (la firma). Aprendo il link dal browser interno di X:
- La card preview è brutta (nessuna OG image, nessun titolo custom)
- La pagina si apre ma i dati da Supabase non vengono caricati (solo HTML statico)

**Cause plausibili:**
- **Card**: `web/diary.html` non ha i meta tag `og:title`, `og:description`, `og:image`, `twitter:card`. Aggiungerli migliora la preview.
- **Dati mancanti nel webview X**: il fetch Supabase fallisce probabilmente per CORS del webview in-app, oppure per JS bloccato. Verificare:
  - Apri devtools su browser desktop → vedi se il fetch va a buon fine normalmente
  - Controlla la console dentro il webview X (Safari → Develop → in-app X webview) per errori CORS / 401 / 403
  - La anon key Supabase è embedded nel JS della pagina? Se no → il fetch ha 401

**Fix probabili:**
1. Aggiungere OG/Twitter meta tag a `web/diary.html` (titolo dinamico per sessione, immagine statica placeholder se manca)
2. Se il fetch non carica nei webview X: valutare pre-rendering server-side del contenuto (al momento tutto client-side via Supabase anon key)

## Files coinvolti

- `utils/x_poster.py` — funzione `get_latest_unposted_diary`
- `x_poster.py` — cron mode
- `web/diary.html` — pagina pubblica

## Tests

- Dopo fix Bug 1: lanciare `python3.13 x_poster.py --once` (o equivalente dry-run) e verificare che la sessione selezionata sia la più recente reale
- Dopo fix Bug 2: condividere il link su X (anche in un draft privato), aprire da app mobile e da browser desktop per vedere la card e il rendering
