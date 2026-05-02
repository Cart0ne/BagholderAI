# Web Astro — Cronistoria della creazione del nuovo sito

**Data sessioni:** 2026-05-01 (sessione 1) + 2026-05-02 (sessione 2)
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Brief origine:** `web_astro/BRIEF.md`
**Branch:** `main` (lavoro in `web_astro/`, sito vecchio in `web/` intoccato)
**Status:** embrione approvato, home page completa con dati live, prossime pagine in roadmap

---

## In una riga

In 2 sessioni abbiamo costruito da zero un nuovo sito BagHolderAI in **Astro** parallelo al vecchio (`web/`), con design system rifatto, nuova identità visiva (blu profondo + sky), home page interamente funzionante con dati live da Supabase, e l'infrastruttura componenti per scalare alle altre 11 pagine.

---

## Decisioni di design prese (e perché)

| Voce | Decisione | Motivazione |
|---|---|---|
| **Stack** | Astro 6 + Tailwind 4 + React per isole | Astro = file-based routing, build statico veloce, layout condivisi. Tailwind = design system "forzato" con classi che rendono il markup auto-documentante. Niente shadcn-astro per evitare estetica generica AI/SaaS |
| **Direzione visiva** | Editoriale-tecnico moderno (Anthropic + Linear + Railway) | Riferimenti scelti da Max dopo brainstorming su 4 direzioni (editoriale Stripe Press / terminale Bloomberg / diario Are.na / lab notebook Distill). Sintesi: pulito, tech, con personalità ma non playful |
| **Background** | Blu profondo `#0f1626` | Scelto da Max dopo confronto visivo a 5 fondi (nero puro / quasi-nero / grigio antracite / GitHub night / blu opaco). Ha personalità, differenzia da Anthropic/Linear/Railway che non usano blu, è "amico" degli accent verde+ciano |
| **Colore primario brand** | Sky `#7dd3fc` | Scelto su confronto vs powder blue vs bianco puro. Sky tiene bene sui bottoni CTA, lascia il verde funzionale "libero" di significare salute bot |
| **Palette accent funzionali** | verde `#86efac`, ciano `#67e8f9`, rosso `#fca5a5` | Stessi ruoli del sito vecchio (P&L positivo / novità editoriale / loss) ma desaturati per stare bene sul fondo blu |
| **Tipografia** | Inter (display + body) + JetBrains Mono (dati) | Scelta su confronto vs (Fraunces + Inter) e (system fonts). Sans-everywhere coerente con Linear/Vercel; serif scartato → identità si appoggia su colore + composizione, non contrasto serif/sans |
| **Tema** | Dark single-mode (no auto-switch device) | Auto-switch raddoppia il lavoro di design senza beneficio reale per il pubblico tech/crypto. Valutabile in futuro |
| **Mobile-first** | Sì dalla sessione 1 (vs "fase futura" del brief) | Decisione esplicita di Max: "se dobbiamo rifare per mobile tanto vale farlo subito". Risolve strutturalmente uno dei problemi del sito vecchio |
| **Logo** | Wordmark `BagHolderAI` con "AI" in sky + zaino SVG vettoriale | Niente emoji 🎒 nel logo principale (cambia faccia su ogni OS). 🎒 resta come favicon per continuità nei tab browser. Logo attuale è placeholder fino al definitivo |

---

## Cosa è stato costruito (componenti e file)

### Componenti riutilizzabili (`web_astro/src/components/`)
- **`Layout.astro`** — wrapper unico per tutte le pagine. Gestisce `<head>`, font Google, OG tags, IntersectionObserver per fade-in. Risolve strutturalmente i problemi #3-4-5 del brief (CSS duplicato, footer non identico, layout non condiviso)
- **`SiteHeader.astro`** — header sticky con backdrop blur, strip live in alto + nav desktop + menu collassabile mobile
- **`SiteFooter.astro`** — footer condiviso con social + legal links
- **`Logo.astro`** — wordmark + zaino SVG dettagliato 3/4 view (occhi chiusi, leggero sorriso, gradiente sky)
- **`BotMascot.astro`** — port 1:1 della funzione `mascotSVG()` del sito vecchio in TypeScript. Genera mascotte parametriche (build stocky/lanky, expression focused/curious/scanning, supporto binocolo TF)
- **`BotCardOriginal.astro`** — card bot identiche al sito vecchio (sfondo `#0e1320`, frame `#0a0e17` con scanlines, bordi colorati, tilt ±1.5°, 5 stat con barre di progresso)
- **`MixerSVG.astro`** — mixer animato Grid (3 fader BTC/ETH/SOL buy/sell che pulsano)
- **`MugSVG.astro`** — tazza di caffè di Grid Bot
- **`RadarSVG.astro`** — radar TF (anelli concentrici + raggio rotante 4s + 5 dot lampeggianti)

### Design system (`web_astro/src/styles/global.css`)
- 1 solo file, sostituisce CSS duplicato in 11 pagine HTML del vecchio sito
- `@theme` di Tailwind 4 con tutte le variabili colore + font stack
- CSS legacy delle bot card portato verbatim (animazioni mixer/radar incluse)
- Classe `.reveal` per fade-in sezioni allo scroll (rispetta `prefers-reduced-motion`)

### Script live (`web_astro/src/scripts/live-stats.ts`)
- Fetch lato browser da Supabase (anon key, stesso pattern del sito vecchio)
- Aggiorna 4 stat hero (orders, P&L FIFO ricalcolato, days running, mode)
- Aggiorna wins/losses Grid (`managed_by=manual`) e TF (`managed_by=trend_follower`)
- Fallback statico nel JSX se la fetch fallisce → la pagina non si rompe mai

### Pagina home (`web_astro/src/pages/index.astro`)
- Hero compatto a 2 colonne (copy + live snapshot panel) → 1 colonna su mobile
- Sezione "AI Bots · at work" subito dopo (Grid + TF live + Sentinel/Sherpa dim)
- Team (3 emoji card con Claude/Max/CC)
- Story (3 volumi: Vol 1 e 2 con cover reali e link Payhip, Vol 3 placeholder)

---

## Cronistoria delle sessioni

### Sessione 1 (2026-05-01) — Design system + embrione

1. **Brainstorming visivo**: Max sceglie i riferimenti (Anthropic, Linear, Railway) e la direzione editoriale-tecnica
2. **Confronto 5 fondi**: Max sceglie blu opaco `#0f1626`
3. **Confronto 3 primari** (sky / powder / bianco): Max sceglie sky `#7dd3fc`
4. **Confronto 3 tipografie**: Max sceglie all-sans (Inter ovunque)
5. **Init Astro + Tailwind** (workaround npm cache: cartella `~/.npm/_cacache` con permessi rotti, soluzione: prefisso `npm_config_cache=/tmp/npmcache-astro`)
6. **Estrazione contenuti reali** dal vecchio sito → niente copy inventato
7. **Home v1 + v2**: feedback Max ("aerioso, logo piccolo, titolo grande, bot devono essere subito visibili"). Aggiunto header sticky + fade-in
8. **Sessione sospesa**: Max valuta a freddo la direzione

### Sessione 2 (2026-05-02) — Logo, bot card, dati live

1. **Conferma direzione**: Max dice "ci stiamo arrivando", continua
2. **Iterazione logo**: 4 tentativi falliti su un'inclinazione dello zaino (rotazione vs skew, pivot bottom-right, "vola via" perché transform CSS lavora su coordinate diverse dalla viewBox SVG). Decisione board: si tiene zaino dritto come placeholder, logo definitivo a designer esterno
3. **Bot card v1** (riprogettate da CC): Max le boccia, "completamente diverse dalle originali"
4. **Bot card v2** (port 1:1 verbatim dal vecchio sito): approvate
5. **Aggiunte animazioni mancanti**: mixer Grid + tazza + radar TF + binocolo TF (tutte 1:1 dal vecchio sito)
6. **Riduzione spacing**: dimezzato gap CTA→bot section
7. **Dati live Supabase**: collegati 4 stat hero + wins/losses Grid e TF. **In produzione adesso si vedono 959 trades, +$42.59 P&L FIFO, 34 days running**
8. **Approvazione finale**: Max conferma "ok, funziona"

---

## Lezioni di processo (per il futuro)

### Cosa ha funzionato
- **Mostrare sempre prima di chiedere**: i 3 file di confronto (`bg-color-compare.html`, `primary-color-compare.html`, `typography-compare.html`) hanno reso le scelte visive immediate. Decidere a parole su colori/font è impossibile
- **Mobile-first dall'inizio**: zero costo di refactoring per renderlo responsive, perché lo è nato responsive
- **Dati come fallback**: i numeri statici nel JSX restano come fallback se Supabase è down → pagina robusta
- **Memoria persistente**: le decisioni di design (palette, font, visione "ufficio coi bot") salvate in `~/.claude/memory/` permettono a sessioni future di partire senza ricostruire il contesto

### Cosa NON ha funzionato
- **Chiedere all'agente di "interpretare" il design**: 30 minuti persi sull'inclinazione del logo perché ho provato a "creare" invece di "copiare". Lezione: per asset visivi complessi serve un designer umano (o Claude design come strumento), non lo posso inventare in chat
- **Riprogettare componenti già esistenti**: avevo riscritto le bot card "in stile nuovo design system" → 1 ora persa. Avrei dovuto fare port 1:1 dall'inizio. **Regola registrata in memoria**: per port di componenti complessi dal vecchio sito, copiare HTML+CSS verbatim e adattare solo il contesto esterno (Layout, palette di base)

---

## Confronto con il sito vecchio

| Aspetto | `web/` (vecchio) | `web_astro/` (nuovo) |
|---|---|---|
| **Stack** | 11 file HTML statici, CSS inline duplicato | Astro + Tailwind + componenti riusabili |
| **Layout condiviso** | No (header/footer copia-incollati in ogni file) | Sì (`Layout.astro` unico) |
| **Design system** | Disperso in 11 file CSS | 1 file `global.css` con `@theme` |
| **Mobile** | Desktop-first con media query rattoppi | Mobile-first nativo |
| **Tipografia** | Mix incoerente (system fonts + Newsreader serif solo su /guide + Fraunces in alcuni posti) | Coerente: Inter ovunque, JetBrains Mono per dati |
| **Identità visiva** | Nero `#0a0a0a` + verde brand | Blu `#0f1626` + sky brand |
| **Logo** | Emoji 🎒 + scritta (cambia faccia per OS) | Wordmark + zaino SVG vettoriale |
| **Header sticky** | No | Sì |
| **Fade-in scroll** | No | Sì (IntersectionObserver, rispetta `prefers-reduced-motion`) |
| **Dati live** | Sì (stessa Supabase anon key) | Sì (stesso schema, codice TypeScript pulito) |

**Nota importante**: il sito vecchio resta online su `bagholderai.lol`, il nuovo gira solo in locale (`http://localhost:4321/`). Nessuna sostituzione fatta. La decisione di switch domain è rinviata a quando avremo migrato anche le altre pagine e validato il preview deploy.

---

## Stato del codice e prossimi passi

### Stato attuale
- **Working tree**: tutto in `web_astro/`, non ancora committato
- **Memoria salvata**: 3 file in `~/.claude/projects/.../memory/` (`project_web_astro_design.md`, `project_web_astro_office_vision.md`, `project_web_astro_session2_state.md`)
- **Screenshot di confronto**: `/Users/max/Desktop/BagHolderAI/dev-screenshots/web_astro-home-*.png` (6 versioni dall'embrione alla v6 finale)

### Prossime sessioni
1. **`/dashboard`** — primo 404 più cliccato dall'header, alta frizione utente
2. **`/diary`** — secondo link dalla CTA "Read the diary"
3. **`/guide`** — la libreria, già linkata 2 volte (banner Volume 2 + footer)
4. **Pagine legali** (`/terms`, `/privacy`, `/refund`) — porting rapido
5. **Pagine bot specifiche** (`/grid`, `/tf`, `/blueprint`, `/howwework`, `/roadmap`) — porting con riuso componenti
6. **Logo definitivo** quando arriverà da designer esterno
7. **Deploy preview Vercel** (`preview-bagholderai.vercel.app`) per validare in produzione senza toccare il dominio attuale
8. **Visione "ufficio coi bot"** — sostituire le card statiche con scena animata coi 4 bot al lavoro (sessione di lavoro dedicata)

### Vincoli tecnici da ricordare
- npm cache rotta: serve sempre `npm_config_cache=/tmp/npmcache-astro` davanti ai comandi npm
- Dev server: `cd web_astro && npm_config_cache=/tmp/npmcache-astro npm run dev` → http://localhost:4321
- Supabase anon key + URL già nel codice (`live-stats.ts`), riusabili per altre pagine

---

## Domande aperte per il CEO

1. **Logo definitivo**: chiediamo a Claude design un logo completo (favicon multi-size + OG image 1200×630 + versione monocroma) o ci affidiamo a un designer esterno (Fiverr / 99designs / amico)?
2. **Switch domain**: quando si dice "il nuovo sito è pronto"? Criteri possibili: (a) tutte le pagine portate, (b) preview Vercel testato per N giorni, (c) approvazione board esplicita
3. **Visione "ufficio coi bot"**: priorità? È prima del switch (rinforza l'identità prima del lancio) o dopo (continui a iterare sul live)?

---

**Tempo speso (stima):** sessione 1 ~3h + sessione 2 ~4h = ~7h totali per arrivare a embrione approvato con dati live.

**Capitale a rischio:** zero (nessun deploy, nessun impatto sul sito attuale).

**Output verificabili:**
- `http://localhost:4321/` (avviare il dev server)
- `web_astro/` directory completa nel repo
- Screenshot in `dev-screenshots/web_astro-home-v6-live-data.png`
