# Brief: nuovo sito BagHolderAI in Astro (parallel build)

## Obiettivo
Costruire da zero un nuovo sito BagHolderAI in Astro, con identità visiva
ridisegnata, **in parallelo** al sito attuale che resta online su
bagholderai.lol. Sostituzione solo se il risultato convince.

## Decisioni già prese

- **Stack**: Astro. Componenti React per le isole interattive (dashboard,
  scaffale libreria). Resto statico.
- **Directory**: nuova cartella `web_astro/` accanto a `web/` esistente.
  Sito vecchio (`web/`) resta deployato su Vercel come ora, sito nuovo si
  costruisce e si testa in locale.
- **Scope**: rebrand totale — design nuovo da zero, non porting.
- **Mobile**: secondario, gestito in fase futura.
- **Vite + React**: già in uso in altro progetto del team. Astro è una
  scelta nuova ma compatibile (le isole interattive si scrivono come
  componenti React).

## Architettura tecnica

- Astro 4+ con React adapter per le isole interattive
- Tailwind CSS per lo styling (decidere insieme se sì o vanilla CSS)
- Dati dashboard / Supabase / Umami / Vercel Analytics da migrare
- Build statico → deploy su Vercel quando si decide la sostituzione

## Pagine da ricreare (priorità)

### Sessione 1 — embrione (ambito di questa sessione)
**Fase A: setup + design system**
- Init Astro project in `web_astro/`
- Definire il **design system completo**:
  - Tipografia (display + body + mono)
  - Palette colori
  - Spacing / grid
  - Component primitives (button, card, link, layout container)
- Implementare la **pagina home** con nuovo design system
  → primo "saggio" del nuovo look

**Fase B: 1–2 pagine ad alto valore**
- /guide (hub libreria — ripensare il pattern scaffale 3D nel nuovo
  contesto, oppure pattern diverso se il design system lo suggerisce)
- (opzionale, se c'è tempo) /dashboard

A fine sessione: embrione funzionante che permette a Max di decidere
"mi piace, continuo" o "non mi convince, fermo qui".

### Sessioni successive
- Tutte le altre pagine: /diary, /blueprint, /howwework, /roadmap,
  /tf, /grid, /terms, /privacy, /refund
- Migrazione dati live (dashboard Supabase + Umami + Vercel)
- Test deploy parallelo (es. preview-bagholderai.vercel.app)
- Decisione finale: sostituzione domain.

## Vincoli e principi

- **Nessuna integrazione live nella sessione 1**: il dashboard può essere
  mockato con dati statici per concentrare la sessione su design + struttura
- **Skill obbligatoria**: `frontend-design` (installata in
  `~/.claude/skills/frontend-design/`)
- **Identità da non perdere**: "AI CEO + intern human" è il cuore del
  progetto. Il nuovo design può essere radicalmente diverso ma deve
  comunicare onestà / esperimento documentato / non vendere fuffa.
- **Riferimenti dal sito attuale**:
  - Coppia mono+sans semantica (mono = dati, sans = narrazione)
  - Verde = "salute del bot" / sistema vivo
  - Ciano = novità editoriale (introdotto per Volume 2)
  - Rosso = warning / loss (ora limitato)

## Contesto progetto (per chi non ha la storia)

BagHolderAI è un trading bot crypto su Binance testnet (paper trading)
gestito da un AI come CEO; Max è co-founder umano (board, no codice).
Il progetto ha appena pubblicato Volume 2 ("From Grid to Brain") su Payhip,
2 volumi totali, 3° in scrittura. Stack attuale: Python (bot), Supabase
(db), Telegram (notifiche), Vercel (sito web statico HTML).

## Stato sito attuale (da cui partire come riferimento)

- 11 pagine HTML in `web/`, max-width 880px, dark mode, font sistema
  Apple (SF Pro + SF Mono)
- /guide rifatta in sessione precedente con scaffale 3D libreria
  + Fraunces serif + cover di volumi reali
- Tutte le pagine hanno banner ciano "Volume 2 is live" + nav top bar +
  brand "🎒 BagHolderAI"
- Cover assets in `web/`: cover_vol1_final.jpg, cover_vol1_square.jpg,
  cover_vol2_final.jpg, cover_vol2_square.jpg

## Problemi noti del sito attuale (da non riportare nel nuovo)

1. Allineamento brand-header / banner / container non uniforme tra pagine
2. /guide a 1100px mentre resto a 880px (logo "salta")
3. CSS duplicato in ogni pagina HTML (modifica = N file da toccare)
4. Footer/social non identico tra pagine
5. Tipografia Fraunces in /guide ma non altrove → incoerenza

Il nuovo sito Astro deve **eliminare strutturalmente** questi problemi
(layout component condiviso, design system centralizzato, build unico).

## Cose da decidere all'inizio della nuova sessione (non ora)

- Tailwind CSS sì o no? (preferenza Max: aperta)
- Routing strategy (file-based di Astro è default)
- Component library di base (shadcn-astro? niente?)
- Strategia immagini (Astro Image / OptimizedImage)

## Riferimenti

- Skill `frontend-design`: `~/.claude/skills/frontend-design/`
- Memory rilevante: `feedback_data_first_then_review.md`,
  `project_roadmap_to_mainnet.md`, `feedback_python_venv.md`
- Repo bot: `/Users/max/Desktop/BagHolderAI/Repository/bagholder/`
- Git remote: vedi `git remote -v` nel repo
- Sito live: bagholderai.lol
- Domain check: bagholderai.lol (NON bagholder.lol)

## Cosa NON fare nella sessione 1

- Non toccare `web/` esistente (sito attuale resta intatto)
- Non deployare su Vercel — Astro gira solo in locale finché non si decide
- Non mockare integrazioni live se richiede tempo (dati statici per
  dashboard durante la sessione design)
- Non riportare lo scaffale 3D di /guide come è oggi: il nuovo design può
  rivisitare completamente il pattern. Resta opzione di mantenerlo se il
  design system lo accoglie naturalmente.

## Output atteso a fine sessione 1

- `web_astro/` con progetto Astro funzionante
- Design system documentato (CSS variables, typography scale, spacing,
  colors) in 1 file (es. `web_astro/src/styles/system.css` o equivalente)
- 1–2 pagine implementate (home + guide minimo)
- README in `web_astro/` con come avviare in locale (`npm install && npm
  run dev`)
- Screenshot delle pagine nuove in `dev-screenshots/` per confronto
