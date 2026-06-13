# Brief S105a — newskeeper-homepage-dedup — 2026-06-13

## Contesto

NewsKeeper v1 (pid 10899) e v2 shadow (pid 97566) girano in parallelo sugli stessi feed RSS e scrivono entrambi nella tabella `newskeeper_signals`. Ogni articolo produce DUE righe:

- **v1**: `polarity = NULL`, `event_key = NULL` (vecchio schema Haiku S94a)
- **v2**: `polarity` impostata (-1/0/1), `event_key` pieno (barometro Haiku v2)

Nelle ultime 24h: 207 righe, 107 articoli unici. Pattern 100% consistente: 103 v1 + 104 v2.

Questo è BY DESIGN (shadow comparison period, finestra ~2 settimane, verdetto barometro ~23 giugno). I duplicati nel DB sono accettati fino a spegnimento v1. Ma il frontend e il barometro devono gestirli correttamente.

## Task 1 — Fix homepage NewsKeeper card (MUST)

La card NewsKeeper in homepage (`/`, sezione 2.2 "The Brains") mostra le ultime headline classificate. Attualmente mostra ENTRAMBE le righe v1 e v2 per lo stesso articolo → duplicati visibili.

**Fix**: la query Supabase che alimenta la card deve filtrare SOLO le righe v2:

```sql
WHERE polarity IS NOT NULL
```

oppure equivalente nel client Supabase JS (`.not('polarity', 'is', null)`).

Questo esclude le righe v1 dal display senza toccare i dati.

**Verifica**: dopo il fix, la card deve mostrare headline tutte diverse. I bullet colorati (severità) devono riflettere la classificazione v2.

## Task 2 — Verifica barometro v2 (MUST)

Il barometro 24H (box in basso nella card NewsKeeper, mostra "Bearish"/"Neutral"/"Bullish") deve usare SOLO le righe v2 per il calcolo.

**Verifica**: controlla il codice del barometro (probabilmente in `web_astro/` o in un endpoint/function) e conferma che la query filtra per `polarity IS NOT NULL`. Se lo fa già → ok, segnala nel report. Se NON lo fa → è un bug: il barometro doppia-conta ogni articolo e il risultato è sbilanciato.

**Se bug trovato**: applica lo stesso filtro `polarity IS NOT NULL` alla query del barometro.

## Task 3 — Dashboard `/dashboard` (CHECK)

Se anche la pagina `/dashboard` ha una sezione NewsKeeper che mostra headline, applicare lo stesso filtro. Se non ce l'ha, segnalare nel report.

## OFF-LIMITS

- NON toccare il codice Python di NewsKeeper v1 o v2 (nessun bot file)
- NON spegnere v1 — la finestra di shadow comparison è ancora aperta
- NON modificare la tabella `newskeeper_signals` (no migration, no DDL)
- NON riavviare nessun processo sul Mac Mini

## Scope

Solo frontend Astro + eventuale endpoint barometro. Nessun bot, nessun restart, nessun DB change.

## Output atteso

Report con:
1. File modificati e diff
2. Conferma/smentita: il barometro v2 filtrava già correttamente?
3. Stato `/dashboard` (ha headline NewsKeeper? se sì, fixato?)
