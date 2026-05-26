# Brief 86a — Status badge dinamico nell'hero homepage

**Autore:** CEO, 2026-05-26  
**Priorità:** MEDIA  
**Stima:** ~1h  
**Scope:** Supabase migration + homepage Astro + JS fetch  

---

## Contesto

La homepage ha un indicatore "SESSION 83 · IN PROGRESS" in basso nell'hero — puntino verde, font 11px, colore grigio, praticamente invisibile. Il Board vuole trasformarlo in uno **status badge visibile** che comunica ai visitatori cosa sta succedendo nel progetto in questo momento.

Il testo sarà aggiornabile da CEO, Max o CC via query Supabase — zero deploy richiesto.

---

## Task 1 — Tabella Supabase `project_status`

```sql
CREATE TABLE project_status (
  id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  status_text text NOT NULL DEFAULT 'Building in public — follow along',
  status_emoji text NOT NULL DEFAULT '🔬',
  updated_by text NOT NULL DEFAULT 'CEO',
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Singola riga, sempre e solo 1
INSERT INTO project_status (status_text, status_emoji, updated_by)
VALUES ('Collecting brain data before deploying real capital', '🔬', 'CEO');

-- RLS: anon può leggere, nessuno scrive via client
ALTER TABLE project_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon read" ON project_status FOR SELECT TO anon USING (true);
```

Il campo `updated_at` deve aggiornarsi automaticamente ad ogni UPDATE:

```sql
CREATE OR REPLACE FUNCTION update_project_status_timestamp()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_status_updated
  BEFORE UPDATE ON project_status
  FOR EACH ROW
  EXECUTE FUNCTION update_project_status_timestamp();
```

---

## Task 2 — Homepage hero: sostituire "SESSION X · IN PROGRESS"

In `web_astro/src/pages/index.astro`, trovare il blocco che mostra "SESSION XX · IN PROGRESS" (puntino verde + testo).

Sostituirlo con un **box status** che:
1. Fa fetch da `project_status` (stessa Supabase JS client già usata nella homepage)
2. Mostra: `[emoji] [status_text]` come testo principale
3. Sotto: `Updated [tempo relativo] ago` in grigio dimesso (es. "Updated 2d ago")
4. Il numero di sessione corrente (opzionale, va bene in secondaria)

### Stile

Il box deve avere:
- Background: `rgba(94, 202, 165, 0.06)` (teal trasparente, coerente col testnet banner sopra)
- Border: `1px solid rgba(94, 202, 165, 0.12)`
- Border-radius: 8px
- Padding: 14px 16px
- Emoji: font-size 20px
- Testo principale: font-size 14px, colore teal (`#5DCAA5`), font-weight 500
- Timestamp: font-size 11px, monospace, colore dim

Il box occupa tutta la larghezza dell'hero (same width del sottotitolo).

### Fallback

Se la query Supabase fallisce o `status_text` è vuoto: nascondi il box completamente (nessun fallback testuale, meglio niente che rotto).

### Tempo relativo

Calcolare client-side dalla differenza `now() - updated_at`:
- < 1h → "Updated just now"
- 1-24h → "Updated Xh ago"
- 1-30d → "Updated Xd ago"
- > 30d → "Updated [date]"

---

## Task 3 — Aggiornare session counter (se presente)

Se il codice attuale legge il numero di sessione da Supabase per mostrare "SESSION 83", quel fetch resta. Il numero di sessione può essere incluso nella riga secondaria del badge: `Session 85 · Updated 2d ago`.

Se il numero di sessione era hardcoded, rimuoverlo — il badge lo sostituisce.

---

## Decisioni delegate a CC

- Posizionamento esatto del box nel layout Astro (deve stare sotto i 3 CTA button, sopra la sezione Blog)
- Come gestire il fetch (inline `<script>` o modulo in `src/scripts/`)
- Se raggruppare con il fetch Supabase già esistente nell'hero (live snapshot)

## Decisioni che CC DEVE chiedere

- Niente — scope chiaro, nessuna ambiguità

---

## Test

- [ ] Tabella `project_status` creata con RLS anon read
- [ ] Homepage mostra il badge con emoji + testo + timestamp relativo
- [ ] Aggiornare `status_text` via Supabase → refresh pagina → nuovo testo visibile
- [ ] Se Supabase non risponde → box nascosto, nessun errore visibile
- [ ] Mobile: box responsive, leggibile su 375px

---

## Commit

```
feat(homepage): dynamic status badge from Supabase project_status
```

---

## Roadmap impact

None.
