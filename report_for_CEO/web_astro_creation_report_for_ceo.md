# Web Astro — Cronistoria della creazione del nuovo sito

**Data sessioni:** 2026-05-01 (sess. 1) + 2026-05-02 mattina (sess. 2) + 2026-05-02 sera (sess. 3)
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Brief origine:** `web_astro/BRIEF.md`
**Branch:** `main` (commit `89c6119`, lavoro in `web_astro/`, sito vecchio in `web/` intoccato)
**Status:** embrione approvato + 2 pagine complete (home + diary) con dati live + animazioni scroll, prossime pagine in roadmap

---

## In una riga

In 3 sessioni abbiamo costruito da zero un nuovo sito BagHolderAI in **Astro** parallelo al vecchio (`web/`), con design system rifatto, nuova identità visiva (blu profondo + sky), **home page** e **pagina /diary** funzionanti con dati live da Supabase + animazioni scroll cross-browser, e l'infrastruttura componenti per scalare alle altre 9 pagine.

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
- Live snapshot: 4 stat con counter animati 0 → valore Supabase (`orders`, `realized P&L`, `days running`, `BUDGET €600 PAPER`)
- Sezione "AI Bots · at work" con stagger animation (le 4 card entrano in sequenza)
- Team (3 emoji card con Claude/Max/CC) con stagger
- Story (3 volumi: Vol 1 e 2 con cover reali e link Payhip, Vol 3 placeholder) con stagger

### Pagina diary (`web_astro/src/pages/diary.astro`)
- Hero "Construction log." con counter live "55 sessions" da Supabase
- Lista delle 55 sessioni (`session #`, titolo, badge `complete`/`● building`)
- Click su una entry espande summary + tag (accordion show/hide nativo, una aperta alla volta)
- Stagger animation sulle prime 11 entries (oltre, tutte insieme con delay max)
- Fallback statico con le 2 entries più recenti se Supabase è down

### Animazioni scroll (`web_astro/src/layouts/Layout.astro` + `global.css`)
- IntersectionObserver per `.reveal` e `.reveal-stagger`
- IntersectionObserver per `[data-count]` (counter 0 → vero)
- API globale `window.__updateLiveStat(id, value)` per animare aggiornamenti live
- WeakMap per cancellare animazioni precedenti sullo stesso elemento
- Listener `pageshow` per re-attivare animazioni dopo bfcache restore
- Tutto rispetta `prefers-reduced-motion: reduce`

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

### Sessione 2 (2026-05-02 mattina) — Logo, bot card, dati live

1. **Conferma direzione**: Max dice "ci stiamo arrivando", continua
2. **Iterazione logo**: 4 tentativi falliti su un'inclinazione dello zaino (rotazione vs skew, pivot bottom-right, "vola via" perché transform CSS lavora su coordinate diverse dalla viewBox SVG). Decisione board: si tiene zaino dritto come placeholder, logo definitivo a designer esterno
3. **Bot card v1** (riprogettate da CC): Max le boccia, "completamente diverse dalle originali"
4. **Bot card v2** (port 1:1 verbatim dal vecchio sito): approvate
5. **Aggiunte animazioni mancanti**: mixer Grid + tazza + radar TF + binocolo TF (tutte 1:1 dal vecchio sito)
6. **Riduzione spacing**: dimezzato gap CTA→bot section
7. **Dati live Supabase**: collegati 4 stat hero + wins/losses Grid e TF. **In produzione adesso si vedono 959 trades, +$42.59 P&L FIFO, 34 days running**
8. **Approvazione finale**: Max conferma "ok, funziona"

### Sessione 3 (2026-05-02 sera) — Diary, animazioni scroll, polish home

1. **Pagina /diary** completa: porting dei contenuti dal vecchio sito, lista delle 55 sessioni da Supabase con accordion show/hide. Lezione applicata da sessione 2: pattern legacy 1:1 (`display: none/block` puro come nel vecchio), niente animazioni CSS sofisticate che si rompono cross-browser
2. **Sistema animazioni scroll** completo:
   - Classe `.reveal` per sezioni singole che entrano in fade+slide
   - Classe `.reveal-stagger` per griglie/liste con figli che animano in sequenza (es. 4 bot card, 3 team card, 55 entries diary)
   - Attributo `[data-count]` per counter animati 0 → valore reale Supabase (orders, P&L, days)
   - Footer con `class="reveal"` → invisibile finché non scrolli in fondo
3. **10 bug fix cross-browser** registrati in memoria (vedi `project_web_astro_scroll_animations.md`):
   - Chrome ignora animazioni su elementi già nel viewport (fix: doppio `requestAnimationFrame`)
   - bfcache di Chrome rompe le animazioni al refresh successivo (fix: listener `pageshow`)
   - "Scatto" all'inizio (fix: rimozione condizionale di `is-visible`)
   - Footer "saltava" su pagine lunghe (fix: `class="reveal"` sul footer)
   - Bot card tilt sovrascritto da translateY animation (fix: 2 CSS custom properties indipendenti)
   - MutationObserver in loop infinito → nav freeze (fix: flag `isAnimating`)
   - Counter sovrapposti scrivevano numeri a caso (fix: `WeakMap<el, frameId>` con cancel)
   - Counter da fallback al valore live mostrava "discesa" (fix: parte sempre da 0, niente fallback ingannevoli)
   - Diary list non animava dopo replace innerHTML (fix: ri-osservare il container)
   - Freccia "▸" della bot card andava a capo (fix: flex con `align-items: baseline`)
4. **Polish copy live snapshot**: cambio `MODE / PAPER` → `BUDGET / €600 PAPER` (Max ha proposto la formulazione, comunica scala del capitale + modo operativo in una cella sola)
5. **Approvazione finale**: Max conferma "ci siamo!" → commit `89c6119` su `main`

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
- **Fixare in parallelo bug multipli prima di avere la lista completa**: in sessione 3, quando Max ha detto "tantissimi problemi sulla home", ho iniziato a fixare il primo che mi è venuto in mente invece di chiedere la lista completa. Risultato: ho perso 30 minuti su un bug (counter loop) e poi ho scoperto che la sua diagnosi sbloccava anche altri 2 bug "fantasma" che si sarebbero risolti da soli. **Regola registrata**: chiedere SEMPRE la lista completa dei bug prima di toccare codice
- **Fallback hardcoded sui counter live**: avevo messo numeri inventati come `data-count="147"` per i counter, pensando che servissero da "valore di partenza visibile". Quando arrivava il vero da Supabase (es. 970), il counter animava da 147 → 970 (sale). Per `days running`, però, il fallback era 182 e il vero era 34 → counter scendeva visibilmente, sembrava un bug. **Regola registrata**: per dati live, una sola sorgente di verità — o hai il vero (animi), o non hai niente (mostri "N.A."). Mai stati intermedi inventati

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
| **Fade-in scroll** | No (solo entrance animation iniziale) | Sì (IntersectionObserver con `.reveal` e `.reveal-stagger`, rispetta `prefers-reduced-motion`) |
| **Counter animati** | No | Sì (counter da 0 → vero quando arriva Supabase) |
| **Dati live** | Sì (stessa Supabase anon key) | Sì (stesso schema, codice TypeScript pulito + API `__updateLiveStat` per animazioni smooth) |
| **Diary** | Lista plain con click/expand | Lista con stagger + accordion + counter "55 sessions" + design coerente |

**Nota importante**: il sito vecchio resta online su `bagholderai.lol`, il nuovo gira solo in locale (`http://localhost:4321/`). Nessuna sostituzione fatta. La decisione di switch domain è rinviata a quando avremo migrato anche le altre pagine e validato il preview deploy.

---

## Stato del codice e prossimi passi

### Stato attuale
- **Working tree**: pulito, tutto in `web_astro/` committato (commit `89c6119` su `main` — 28 file, 7770 righe)
- **Memoria salvata**: 6 file in `~/.claude/projects/.../memory/`:
  - `project_web_astro_design.md` — palette + tipografia + decisioni visive
  - `project_web_astro_office_vision.md` — visione "ufficio coi bot" per sessioni future
  - `project_web_astro_session1_state.md` — checkpoint sessione 1
  - `project_web_astro_session2_state.md` — checkpoint sessione 2
  - `project_web_astro_session3_state.md` — checkpoint sessione 3 (questo)
  - `project_web_astro_scroll_animations.md` — pattern + 10 bug fix cross-browser
- **Screenshot di confronto**: `/Users/max/Desktop/BagHolderAI/dev-screenshots/web_astro-*.png`

### Prossime sessioni (in priorità)
1. **`/dashboard`** — primo 404 più cliccato dall'header, alta frizione utente. La più data-heavy (P&L curve, bar chart trades giornalieri, CEO log Haiku, activity feed)
2. **`/guide`** — la libreria libri, già linkata 2 volte (banner Volume 2 + footer card). Decisione design da prendere: mantenere lo scaffale 3D del vecchio sito o ripensarlo nel nuovo design system?
3. **Pagine legali** (`/terms`, `/privacy`, `/refund`) — porting rapido (~20 min totali)
4. **Pagine bot specifiche** (`/grid`, `/tf`, `/blueprint`, `/howwework`, `/roadmap`) — porting con riuso componenti
5. **Logo definitivo** quando arriverà da designer esterno
6. **Deploy preview Vercel** (`preview-bagholderai.vercel.app`) per validare in produzione senza toccare il dominio attuale
7. **Visione "ufficio coi bot"** — sostituire le card statiche con scena animata coi 4 bot al lavoro (sessione di lavoro dedicata)

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

**Tempo speso (stima):** sessione 1 ~3h + sessione 2 ~4h + sessione 3 ~4h = **~11h totali** per arrivare a 2 pagine complete (home + diary) con dati live, animazioni scroll, e infrastruttura componenti riusabili.

**Capitale a rischio:** zero (nessun deploy, nessun impatto sul sito attuale che continua a girare su `bagholderai.lol`).

**Output verificabili:**
- `http://localhost:4321/` e `http://localhost:4321/diary` (avviare il dev server con `cd web_astro && npm_config_cache=/tmp/npmcache-astro npm run dev`)
- `web_astro/` directory completa committata in `main` (commit `89c6119`)
- Screenshot in `dev-screenshots/web_astro-*.png` (versioning v1→v6 della home + diary)
- Documentazione tecnica completa in `~/.claude/.../memory/project_web_astro_*.md` (6 file)

**Velocità di scaling per le altre 9 pagine:** ora che l'infrastruttura c'è (Layout, design system, componenti, animazioni, pattern porting 1:1), ogni pagina nuova dovrebbe richiedere 30-90 minuti invece delle 2-4 ore della prima. La curva di apprendimento è dietro, da qui in avanti è "applicare lo stesso schema".

---

## Aggiornamento — sessioni 4 + 5 (2026-05-02 sera tardi → 2026-05-03)

**Status post-sessione 5:** /dashboard quasi completa con dati live Supabase, layout horizontal pipeline approvato, soldi delle coin tf_grid contabilizzati secondo brief 46b, recent activity wired per Grid + TF separati. Manca solo § 3 Charts (deferred, vedi `Brief_46c_Charts.md`).

### Sessione 4 — prototipazione /dashboard (commit `0fe001e`)

**Workflow di prototipazione adottato** (replicabile per altre pagine data-heavy):
1. 3 prototipi paralleli (`dashboard-a`, `dashboard-b`, `dashboard-c`) con stesso mock data importato — ognuno una direzione narrativa diversa (Lab notebook / Stato del fondo / Operativo editoriale)
2. Switcher in alto per saltare tra varianti senza tornare all'index
3. Max sceglie pezzi di ciascuna, si fa un merge progressivo (v1 → v5)
4. Solo a layout approvato si sostituiscono mock con query Supabase

**Direzione narrativa scelta**: combinazione 1+4 ("stato del fondo" + "lab notebook" — i 4 strumenti del lab al centro). Trasparenza presente ma non in risalto. Tono editoriale-tecnico coerente con la home.

**File creati**: `dashboard-mock.ts` con dati condivisi + 4 file pages (3 proto + 1 final).

### Sessione 5 — wiring dati reali + layout pipeline (commit `ff08b08`)

**Layout finale approvato — horizontal pipeline** (brief 46a):
- TF a sinistra (card grossa con totali $100 budget)
- SHARED al centro (card delle coin tf_grid promosse)
- GRID a destra (card grossa con totali $500 budget)
- Native sotto: ETH/INJ/DOGE sotto TF, BTC/SOL/BONK sotto GRID
- Freccia animata da TF → GRID con label "I tried, your turn" (gradiente amber→blu→green che scorre)
- Badge "shared" pulsante sulle card centrali

**Decisione di sostanza chiusa col CEO** (brief 46b — TF→Grid Budget Logic):
> Le coin `tf_grid` sono **CAPITALE TF**, **GESTIONE GRID**.

Significa:
- Card grossa TF: totali aggregano `managed_by IN ('trend_follower','tf_grid')`
- Card grossa GRID: totali solo `managed_by='manual'` (BTC/SOL/BONK)
- Le card centrali "shared" sono finanziariamente in TF, visivamente in mezzo come "ponte"

**Dati wired su Supabase** (file nuovo: `dashboard-live.ts`, ~540 righe):
- **Hero meta strip**: day calcolato da V3_LAUNCH (2026-03-30), net worth aggregato fondo, P&L colorato dinamico
- **Today snapshot** (5 metriche del giorno): P&L FIFO oggi, trades, buys, sells, allocated. Filtro UTC midnight → now coerente con bot daily aggregation
- **§ 1 CEO log + § 5 archive**: fetch `daily_commentary` ordinato per data desc, dedup, top 1 in card grossa + scrollable window di tutte le precedenti
- **§ 2 Instruments** (la sezione più complessa): TF totals + GRID totals + per-coin metrics con FIFO replay client-side per allinearsi al vecchio dashboard. Net worth = `budget + realized + unrealized`. Cash% calcolato sul **budget operativo** (= `budget - skim`) perché lo skim è capitale fisicamente messo da parte e non più disponibile
- **§ 4 Recent activity**: 2 tabelle separate (Grid + TF) con 6 trade ciascuna, sells annotati con avg buy price FIFO

**Bug numerici risolti durante il wiring**:
1. Unrealized inizialmente sbagliato (usavo `mtm - netInvested` invece di `mtm - openCost`). Fix: traccio `openCost` come somma cost dei lotti aperti dopo FIFO consumption, allineato al vecchio dashboard
2. Net worth TF mostrava ~$64 invece di ~$89: usavo `SUM(capital_allocation)` delle coin attive come budget, mentre il budget canonico TF è `trend_config.tf_budget = $100` fisso. Fix: separato budget canonico da somma allocations
3. Realized cumulativo TF: dovevo includere anche coin **deallocate** (managed_by tf_grid/trend_follower con is_active=false) perché il loro realized passato deve apparire nei totali. Fix: aggregate realized + fees su tutti i trade del gruppo, non solo sui trade delle coin attualmente attive
4. Unrealized % rispetto a budget vs avg buy: vecchia usa `(livePrice / avgBuy - 1)*100`, io avevo `unrealized / capital_allocation`. Fix: usata `openCost` come base per matchare il vecchio (le 2 formule divergono molto su BONK perché openCost è la metà del budget allocato)

### Cose risolte vs. cose deferred

**Risolte**:
- ✅ Ribaltamento layout: orizzontale TF | SHARED | GRID approvato
- ✅ Brief 46b implementato: tutti i numeri allineati al vecchio dashboard ai centesimi
- ✅ Recent activity divisa per bot per evitare che TF nasconda Grid
- ✅ Pipeline arrow narrativa con gradiente colore + shimmer animato + scritta autoironica "I tried, your turn"
- ✅ § 1 + § 5 CEO log con archivio scrollabile compatto
- ✅ Home: session counter live + Today P&L panel + Today trades
- ✅ Diary: data accanto a "Session XX" su layout 2 righe

**Deferred (Brief 46c scritto)**:
- § 3 Charts (Cumulative + Daily P&L) — la tabella `daily_pnl` ha solo storia Grid. TF richiede ricostruzione da `trades` con MTM approssimato (legacy ~5% margine). Decisioni di sostanza da prendere col CEO prima di codare:
  - Scope chart: solo Grid / Grid + TF aggregato / 2 serie separate
  - MTM TF storico: approssimato come legacy / skippato / fetch klines daily
  - Daily bar chart: realized raw o FIFO ricalcolato
- Animazioni che non hanno funzionato (puntini SVG, ghost card) — secondo round se si vuole

### Numeri concreti del wiring (test 2026-05-03 mattina)

**GRID section** (manual, $500 budget):
- Net worth $549.02 ≈ vecchia $549.00 (delta ~$0.02 per cambi prezzi live tra fetch)
- Realized +$54.33, Unrealized -$5.31, Fees -$7.64, Skim $20.53
- BTC $99.70 (+0.39%), SOL $148.40 (-3.77%), BONK $74.88 (-0.16%)

**TF section** (trend_follower + tf_grid, $100 budget):
- Net worth $89.76 ≈ vecchia $89.73
- Realized -$10.27, Unrealized +$0.03, Fees -$6.46, Skim $25.85
- DOGE, INJ (native trend_follower) + TRX (tf_grid promosso)

### Cosa rimane per chiudere /dashboard

1. **§ 3 Charts** (vedi Brief 46c — discussione col CEO necessaria su 4 punti di sostanza)
2. **Animazioni opzionali** — gli effetti SVG che avevamo provato all'inizio non sono partiti (probabile timing tra DOM ready e rAF). Da debuggare a mente fresca o lasciar perdere se non servono
3. **Sentinel + Sherpa staged** — restano statici (è giusto così, sono coming)
4. **Mobile** — il layout horizontal su schermi stretti dovrà degradare elegantemente. Pensare a media query per cambiare la freccia da orizzontale → verticale

### Tempo cumulativo

Sessione 4 ~3h (3 prototipi + merge v1→v5) + sessione 5 ~5h (layout pipeline + wiring 4 sezioni + debug numerici) = **~8h** per portare /dashboard da mock a quasi-completa con dati live e logica brief 46b.

**Cumulato totale del progetto web_astro** (sessioni 1+2+3+4+5): **~19h** → home + diary + dashboard quasi-completa + tutto il sistema design e infrastruttura.

### Domande aperte aggiunte per il CEO (sessioni 4+5)

4. **Brief 46c — Charts**: 4 decisioni di sostanza prima di poter codare (vedi `web_astro/Brief_46c_Charts.md`)
5. **Layout pipeline su mobile**: la freccia orizzontale TF→GRID dovrà diventare verticale su schermi stretti (≤768px). Il layout intero collassa naturalmente in colonna ma la freccia direzionale va ruotata. Iterazione futura
6. **Eliminare i prototipi A/B/C**? Sono stati utili durante la prototipazione ma ora che dashboard.astro è il vincitore, li teniamo come riferimento o si committa una pulizia?

---

## Aggiornamento — sessione 6 (2026-05-03 sera)

**Status post-sessione 6:** /dashboard chiusa (§ 3 Charts wired), /blueprint + /roadmap portate dal vecchio sito. STYLEGUIDE.md scritto come fonte unica di pattern + palette + lezioni dolorose. Mancano ora solo /howwework (la "difficile" col React) e le pagine legali.

### Brief 46c — Charts chiuso (commit `adfce34`)

**Decisione di sostanza**: replicato il pattern del vecchio dashboard (Grid + TF aggregato, FIFO ricalcolato lato browser, MTM da `daily_pnl.total_value` + ricostruzione TF approssimata ~5%) **rovesciando** le decisioni iniziali del CEO. Motivo: il brief 46c suggeriva al CEO che "raw = come la vecchia", ma la vecchia in realtà ricalcola FIFO. Replicare la vecchia significa fare quello che fa la vecchia, non quello che il brief diceva (sbagliando) che la vecchia facesse.

**Aggiunto** filtro `managed_by=eq.grid` esplicito su `daily_pnl` che la vecchia non aveva (bomba a tempo se mai il bot scrivesse snapshot TF — disinnescata).

**Iterazione UX importante** (1h di brainstorm con Max): le barre giornaliere stacked Grid+TF su 35-90-200-500 giorni di dati diventano illeggibili. Soluzione finale dopo 4 round di mockup standalone HTML:
- **Selettore range** `1M / 3M / All` in alto (sopra entrambi i grafici)
- **Barre weekly di default** (mai daily), monthly se >365 giorni
- **Linea cumulata daily** fino a 365 giorni
- **Etichetta netto sopra ogni barra** posizionata fuori dal canvas (riga HTML allineata via Chart.js API ai centri delle barre) — niente più rosso-su-arancione del primo tentativo con pillole sopra le barre
- **Settimana in corso stilizzata** con opacità ridotta + colore tenue

**Bug numerico fix**: la soglia "settimana flat" usava `Math.abs(net) < 0.5` come trigger di `±$0.00`, ma una settimana con netto -$0.20 (TF -$7.58 + Grid +$7.38) mostrava `±$0.00` mentre il tooltip diceva `-$0.20`. Fix: `if (+net.toFixed(2) === 0)` — solo i veri zero numerici sono flat, tutto il resto mostra il netto reale.

**Mockup esplorativi**: durante le decisioni UX abbiamo creato `web_astro/mockup_46c_charts.html` con dataset finto e toggle di varianti. Eliminato dopo l'approvazione finale (era "palestra", non produzione). Pattern riusabile: per decisioni visive ambigue, mockup standalone HTML > prototipi astro (più veloce, no build, iterazione di secondi).

### Porting /blueprint (commit `a04f1c9`)

**Doppio porting necessario** — il primo è stato un fallimento educativo:

1. **v1**: ho ricostruito blueprint **ignorando i pattern di /diary e /dashboard**. Container `max-w-3xl` invece di `max-w-4xl`. Hero senza meta-strip. Sezioni con `<h2 text-[18px] font-bold>` invece del pattern mono `§ N · title`. Max ha reagito: *"mi vien da piangere e non so se arrabbiarmi con te o con i tuoi predecessori delle vecchie chat... possibile che nessuno dei tuoi predecessori abbia scritto le regole di come impaginare?"*

2. **v2**: rifatto leggendo prima i file esistenti. Container `max-w-4xl`. Hero pattern verbatim da diary. Sezioni `<hr> + § N`. Approvato in 5 minuti.

**Lezione registrata**: leggere il codice esistente PRIMA di scrivere. Non fidarsi della propria interpretazione di un brief — guardare cosa fanno le pagine già approvate.

**Componente nuovo creato e poi non usato**: `AnnouncementBar.astro` (parcheggiato per Volume promo su /guide e /howwework). CEO ha chiesto di toglierlo da blueprint dopo averlo visto. Lasciato nel repo per un futuro uso, regola degli "almeno 3" violata ma volontariamente — c'è già il piano di usarlo.

### Porting /roadmap (commit `a04f1c9`)

**Decisione architetturale**: separare dato e markup. `src/data/roadmap.ts` (490 righe, tipato) + `src/pages/roadmap.astro` (334 righe, render). Editing futuro: tocchi solo il `.ts` per aggiungere task/phase, il template è stabile.

**Native `<details>`** per collapse/expand invece di JS toggle. Zero byte di JavaScript, accessibile, funziona offline. Subsection di Phase 8 (le 207 task del backlog, raggruppate per Phase 1/2/7/9/10/11/Open) usano lo stesso pattern annidato.

**Sequenza dolorosa di 6 round di iterazione UI** che ha portato a forgiare lo styleguide:

1. **Phase 8 invisibile** — sezione con `class="reveal"` alta migliaia di pixel. L'IntersectionObserver con threshold 0.08 non scatta mai per elementi enormi. Fix: rimuovere `reveal` da wrapper di liste lunghe. **Regola registrata**: `.reveal` mai su elementi con altezza data-driven illimitata
2. **Padding richiesto vario**: `py-3` → `py-5` → `py-7` → ecc. Ogni iterazione richiedeva di ricaricare il browser, e Max vedeva ancora la versione vecchia. Per 3 round abbiamo discusso di "la pagina è strettissima" mentre io vedevo padding 28px dal headless screenshot
3. **Diagnosi del vero bug**: avevamo **due dev server attivi** (4321 e 4323). Max guardava il 4321 (codice stale), io modificavo file e Vite rigenerava sul 4323. **Regola registrata**: prima di avviare un nuovo dev server, killare gli orfani (`lsof -ti:4321,4322,4323 | xargs kill -9`)
4. **Dopo il restart pulito**: padding `py-7` finalmente visibile su entrambi. Confermato che `py-5` era il valore giusto
5. **Phase 8 di nuovo invisibile** dopo refactoring che aveva spostato `reveal` su section wrapper con tutte le 9 phase dentro. Stesso bug di prima. Stesso fix
6. **Problema CSS scope**: la regola `details > summary { padding-left: 22px }` per il caret rotante stava colpendo anche il `<details>` del menu mobile in SiteHeader. Fix: scope con `.roadmap-page details > summary`. **Regola registrata**: regole CSS che riguardano `<details>` o altri elementi semantici comuni vanno SEMPRE scoping a una classe pagina-specifica

**Decisione di stato finale**: tutte le phase chiuse di default tranne Phase 8 (la "messy backlog" che il visitatore viene a vedere). Sub-section interne tutte chiuse, click per aprire. `NEW` ambra come prefisso su Phase 9/10/11 (le sezioni post-blueprint del backlog).

### STYLEGUIDE.md (commit `cfc3bb9`)

**File creato**: `web_astro/STYLEGUIDE.md` — 696 righe, 19 sezioni. Ragione di esistenza spiegata in apertura: *"le prime 5 sessioni di sviluppo del sito Astro hanno cristallizzato delle scelte (container width, hero, spaziatura, palette) che vivevano solo nel codice. Ogni nuova pagina veniva ricostruita ex novo, i predecessori erano costretti all'archeologia."*

Sezioni più dense:
- § 5 Design tokens (palette completa, regola "mai hex letterali")
- § 6 Cheat sheet typography (h1, h2, body, badge ecc. con classi esatte)
- § 7 Componenti riutilizzabili (table, callout, lista, badge — snippet copia-incollabili)
- § 8 Reveal & animazioni (3 regole tassative, una di queste è la `.reveal` su wrapper lunghi)
- § 11 Dev workflow (un solo server, cache busting)
- § 12 **8 lezioni dolorose** con sintomo → causa → fix
- § 17 **Checklist nuova pagina** (10 punti)

**Memoria persistente aggiunta**: `~/.claude/.../memory/reference_web_astro_styleguide.md` punta a `web_astro/STYLEGUIDE.md`. Indice MEMORY.md aggiornato. Ogni futuro Claude (CC o CEO) lo trova automaticamente senza dover archeologare.

### Lezioni di processo (sessione 6)

**Cosa ha funzionato**:
- **Mockup standalone HTML per decisioni UX**: per i charts abbiamo creato un file `mockup_46c_charts.html` con dataset finto + toggle varianti. Iterazione di secondi (refresh browser, no build). Decidere a parole su "etichetta sopra o sotto la barra" è impossibile — vedere immediatamente è risolutivo
- **Estrarre dato in `src/data/<page>.ts`**: per /roadmap il file `.ts` è un export tipato. TypeScript notifica se cambi una shape che il template usava. Editing futuro low-friction
- **Memoria reference verso STYLEGUIDE.md**: invece di memorizzare le regole una a una, ho memorizzato un puntatore. Lo styleguide stesso è il "single source of truth" — si aggiorna lì, la memoria resta concisa

**Cosa NON ha funzionato**:
- **Saltare la lettura dei file esistenti**: ricostruito blueprint da zero senza guardare diary/dashboard. 1h sprecata in v1 + rebuild. Lezione: prima di scrivere, leggere
- **Due dev server contemporaneamente attivi**: 30 minuti di "il padding non cambia" mentre io vedevo il padding giusto e Max il vecchio. Procedure operative: prima di `npm run dev`, kill di orfani
- **Fixare in piccoli passi senza visione complessiva**: Max ha chiesto 3 modifiche insieme (`py-5` + Phase 8 aperta + `NEW` ambra). Le ho fatte una alla volta, ognuna con un build/refresh in mezzo. Avrei dovuto fare un'unica Edit a 3 modifiche e un solo refresh
- **Avere fede nei valori del browser senza verificare**: per 2 round di "la pagina è strettissima" ho insistito che `py-7` era applicato (lo era, sul mio server). Avrei dovuto chiedere subito a Max **quale URL stava guardando**. Confermato: era 4321, non 4323

### Cose risolte vs. cose deferred (sessione 6)

**Risolte**:
- ✅ Brief 46c chiuso — § 3 Charts live con range selector + weekly bars + net labels HTML allineati alle barre
- ✅ /blueprint live — 14 sezioni verbatim, allineata a /diary e /dashboard nel design system
- ✅ /roadmap live — 297 task in 9 phase con `<details>` collassabili, dato separato in `src/data/roadmap.ts`
- ✅ STYLEGUIDE.md — fonte unica per pattern + palette + spaziatura + lezioni
- ✅ Memoria persistente: `reference_web_astro_styleguide.md` puntatore allo styleguide
- ✅ Componente `AnnouncementBar.astro` parcheggiato per uso futuro (guide, howwework)

**Deferred**:
- 🟡 /howwework — la "difficile" perché richiede React (`@astrojs/react`) o port JSX→Astro vanilla. Decisione architetturale rinviata: aggiungere React all'Astro o fare port verso vanilla? Lo styleguide ne parla in § 19 ("Roadmap del documento")
- 🟡 Pagine legali (/terms, /privacy, /refund) — porting rapido, ~20min totali
- 🟡 Analytics (Umami, Vercel) non ancora portati nel Layout. Da fare prima del switch domain
- 🟡 Eliminazione `dashboard-a/b/c.astro` (i prototipi della sessione 4) — ancora in repo come riferimento. Il nuovo dashboard.astro è il vincitore stabile
- 🟡 Mobile pipeline TF→GRID arrow (freccia orizzontale che diventa verticale su mobile) — iterazione futura

### Tempo cumulativo (sessioni 1-6)

Sessione 6 ~5h (charts wiring + /blueprint v1 fail + v2 + /roadmap + 6 round di iterazione UI + STYLEGUIDE) → **cumulato ~24h totali** per il progetto web_astro.

**Stato del sito** (post-sessione 6):
- 6 pagine live in locale: home, /dashboard (con § 3 charts live), /diary, /blueprint, /roadmap
- Manca solo /howwework + pagine legali per parità completa col vecchio /web
- Lo styleguide rende ogni pagina nuova un esercizio di **applicazione pattern**, non di scoperta

### Domande aperte aggiunte per il CEO (sessione 6)

7. **/howwework**: aggiungiamo React all'Astro per portare `web_proto/how_we_work_interactive.jsx` 1:1, oppure facciamo port verso Astro vanilla con `<details>` + animazioni CSS? La prima è più fedele al prototipo, la seconda mantiene il bundle leggero. Decisione architetturale che impatta TUTTE le pagine future (se aggiungiamo React, è disponibile ovunque)
8. **Switch domain**: con 6/8 pagine portate, manca /howwework + pagine legali per la parità. Procediamo a deploy preview Vercel adesso (per validare in produzione lentamente) o aspettiamo che TUTTE le pagine siano pronte?
9. **Mockup HTML come pattern di lavoro**: il file `mockup_46c_charts.html` ha dimostrato che per decisioni UX ambigue, un mockup standalone supera per velocità qualunque prototipo Astro. Lo registriamo come metodo da seguire? Lo styleguide può menzionarlo come "tool consigliato" in una sezione dedicata
