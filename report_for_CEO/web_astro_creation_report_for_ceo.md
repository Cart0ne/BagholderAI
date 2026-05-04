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

---

## Aggiornamento — sessione 7 (2026-05-03 sera tardi)

**Status post-sessione 7:** **9/9 pagine portate.** Pagine legali + /library (ex /guide, rinominata) + /howwework (con React island ibrido) tutte live in locale. Sito Astro al pari del vecchio /web in numero di pagine. Manca solo deploy preview Vercel + decisioni board sul rinnovo nome/dominio/identità.

### /terms, /privacy, /refund — porting rapido (commit `0cede95`)

Tre pagine legali portate verbatim dal vecchio sito al nuovo design system. Niente decisioni di sostanza, applicazione meccanica dei pattern STYLEGUIDE:

- **Terms** (8 sezioni): Introduction, Products, No Financial Advice (con callout giallo), AI-Generated Content, IP, Liability, Changes, Contact
- **Privacy** (8 sezioni): Overview, What We Collect, What We Don't Collect (bullet `›` verde), Third-Party Services (bullet `›` verde), Data Retention, Your Rights, Changes, Contact
- **Refund** (5 sezioni): Digital Products — No Refunds (con **green framing callout** "All sales are final."), We Make This Fair, Exceptions, Chargebacks, Contact

**Footer del Layout** già linkava a tutte e 3 (era pronto da prima). Header NON aggiornato — le pagine legali stanno solo nel footer, com'è giusto. Tempo: ~30 minuti totali.

### /guide → /library — rename + scaffale 3D (commit `972e0a1`)

**Decisione di naming chiusa col CEO**: `/guide` era fuorviante (suggeriva tutorial gratuito, era invece pagina di vendita libri). Confronto a 4: `/guide` ❌ → `/store` ❌ (troppo SaaS) → `/books` ⚠ (piatto) → **`/library` ✅**.

Motivazione finale per `/library`: il copy del sito vecchio già diceva *"The Library — three volumes documenting an AI-led trading experiment"*. Lo scaffale 3D è letteralmente una libreria. Tono coerente: Lab notebook, Construction log, Blueprint, Roadmap, **Library**. Nomi che evocano un fondo che documenta sé stesso, non un'azienda che vende.

**Porting scaffale 3D 1:1** dal vecchio sito con palette adattata:
- Cyan vecchio `#22d3ee` → `#67e8f9` (= `--neu` nuovo)
- Green vecchio `#22c55e` → `#86efac` (= `--pos` nuovo)
- Gradient interni delle copertine libro lasciati intatti (sono asset del libro, non palette di sistema)
- **Fraunces** caricato SOLO su `/library` (eccezione documentata allo STYLEGUIDE § 5)
- Tutti i selettori CSS scopati sotto `.library-shelf` per zero leakage

**Strategia responsive necessaria**:
- Shelf 3D solo su **≥1024px** (libro aperto era 800px, overflow su tablet)
- Su 1024-1279 lo shelf è **rimpicciolito** (libro aperto 640px)
- Su **<1024px** mostro un fallback **stack di 3 card libro** con palette del fondo nuovo, niente Fraunces, niente 3D
- Stesso contenuto identico tra le due viste, solo presentazione diversa

**Cleanup di § Why read these**: inizialmente piazzato in fondo, Max ha richiesto in cima ("contesto → prodotto → numeri"). Anche **rimosso AnnouncementBar** dalla pagina (banner che linkava a sé stessa = anti-pattern). Spazio tra "Why read these" e scaffale ridotto da ~90px a ~16px (`shelf-stage padding-top` da 50 a 16).

**Rename references aggiornate** in 5 punti:
- `SiteHeader.astro` (label "Book" → "Library")
- `AnnouncementBar.astro` (default href + commento)
- `index.astro` (pill Volume 2 + link "Library →" sezione Story)
- Cover images `cover_vol1_final.jpg` + `cover_vol2_final.jpg` copiate da `/web` a `public/`

**TODO deploy**: aggiungere redirect 301 `/guide` → `/library` in `vercel.json` per non perdere link esterni esistenti.

### /howwework — React island ibrida (sessione 7 in corso)

**Decisione architetturale chiusa**: Astro al 95% statico + isole React dove serve interattività (filosofia di Astro). Aggiunto `@astrojs/react` con `npx astro add react` — ora React è disponibile per tutte le pagine future, ma il bundle viene caricato **solo** dove c'è un componente React montato. Le altre 8 pagine restano statiche pure.

**Architettura della pagina ibrida**:
- Hero + intro = Astro statico
- **§ 1 The team & the workflow** = isola React (`<HowWeWorkInteractive client:visible />`)
- § 2 Tools, § 3 Lessons (8), § 4 Rules of engagement (12), § 5 Memory, § 6 Replicate = Astro statico

Risultato: pagina ricca di contenuti come la live vecchia (8 lezioni, 12 regole, ecc.), ma con il "wow" interattivo del prototipo React in alto invece delle 3 card team statiche.

**Componente React `HowWeWorkInteractive.jsx`** (~600 righe):
- 3 nodi org chart (CEO/Max/CC) posizionati assoluti, click espande dettaglio
- 3 frecce SVG curve con label cliccabile + pallino animato che scorre lungo la curva
- Workflow timeline 7 step con auto-play **12 secondi** (deciso dopo confronto 5/8/12/15/20s)
- **Stop-on-click**: l'auto-play si ferma alla prima interazione manuale dell'utente — pattern carousel/gallery
- Detect viewport con `useIsMobile()` hook (`window.matchMedia` su `<768px`)
- **Mobile fallback** completo: 3 card team verticali con info **già aperte** + 3 paragrafi connessioni + workflow lineare (no click necessari, no auto-play)

**Decisioni di palette**:
- CEO → `text-pos` `#86efac` (verde)
- Max → `text-amber-400` `#fbbf24` (giallo)
- CC → **nuovo token `text-cc` `#818cf8`** (indaco) aggiunto a `global.css` → ogni ruolo ha la sua identità cromatica unica
- Le emoji dei 3 attori (🤖 Claude, 🧑 Max, ⚡ CC) **identiche alla home** per coerenza cross-page

**Build pulita**: 13 pagine totali, 1.63s, zero warning. React bundling lazy correttamente: il bundle React (~40kb gz) viene caricato solo quando l'isola entra in viewport.

### Cose risolte vs. cose deferred (sessione 7)

**Risolte**:
- ✅ /terms, /privacy, /refund portate (commit `0cede95`)
- ✅ /guide rinominata in /library con scaffale 3D 1:1 + responsive fallback (commit `972e0a1`)
- ✅ /howwework con React island ibrida (passi 1-5 fatti, ultimo commit pendente)
- ✅ React (`@astrojs/react`) integrato — ora disponibile per pagine future (es. "ufficio coi bot")
- ✅ Token `--color-cc` aggiunto a global.css per identità Claude Code

**Deferred**:
- 🟡 STYLEGUIDE.md § 20 React Islands — pattern d'uso (`client:visible` vs `client:load`, scoping CSS, mobile fallback) da documentare ora che ho il primo caso d'uso vero. **Da fare nella prossima sessione** prima che la conoscenza si disperda
- 🟡 Eliminazione `dashboard-a/b/c.astro` — ancora in repo come riferimento
- 🟡 Mobile pipeline TF→GRID arrow (freccia verticale su <768px)
- 🟡 Analytics (Umami, Vercel) da portare nel Layout prima del switch domain
- 🟡 Redirect 301 `/guide` → `/library` da configurare in `vercel.json` quando deployeremo
- 🟡 Caccia ai piccoli bug + migliorie varie su tutte le pagine (sessione 8 prevista)

### Tempo cumulativo (sessioni 1-7)

Sessione 7 ~3h (legali ~30min + library con scaffale 3D + responsive ~1h30 + react island /howwework ~1h) → **cumulato ~27h totali** per il progetto web_astro.

**Stato del sito** (post-sessione 7):
- **9/9 pagine live in locale**: home, /dashboard, /diary, /blueprint, /roadmap, /terms, /privacy, /refund, /library, /howwework
- Parità completa col vecchio /web in numero di pagine
- `@astrojs/react` integrato, isole disponibili per pagine future (es. visione "ufficio coi bot")
- Lo STYLEGUIDE è "single source of truth" e funziona — Sessione 7 è stata "applicazione pattern" non "scoperta"

### Lezioni di processo (sessione 7)

**Cosa ha funzionato**:
- **Una domanda alla volta su decisioni architetturali**: Max si è lamentato a metà dell'isola React che andavo "troppo veloce". Riformulato in 3 domande secche (auto-play timing? mobile strategy? colore CC?) consegnate una per messaggio. Ha funzionato: Max ha potuto pensare a una cosa per volta invece di rispondere a 4 domande sparate insieme
- **Ibrido statico+isola** invece di "tutto React" o "tutto vanilla": il prototipo React era pensato come componente, non come pagina intera. Tenere il 90% Astro statico (Lessons, Rules, Memory) e l'isola solo dove serve interazione = il vantaggio di Astro brilla
- **Mobile fallback come decisione UX, non tecnica**: l'org chart con 3 nodi assoluti su 375px era "stretto ma stava". B (3 card statiche su mobile) ha vinto su A (org chart ovunque) perché chi legge un sito su iPhone vuole **contenuto leggibile**, non interattività spettacolare

**Cosa NON ha funzionato**:
- **Sparare 4 domande di decisione tutte insieme**: la prima volta che ho descritto il piano /howwework ho elencato 4 punti. Max: *"vai troppo veloce"*. Lezione: per decisioni di sostanza, una domanda per messaggio, con pro/contro chiari per ogni opzione
- **Provare a sostituire emoji 🎒 del CEO con SVG zaino azzurro**: ho creato `BackpackIcon.jsx` (160 righe), modificato 3 punti, poi Max ha realizzato *"ho fatto un errore... ci sono già 3 emoji per claude, max e CC nella home, usiamo le stesse anche in howwework"*. Le emoji giuste erano 🤖 / 🧑 / ⚡, identiche alla home. Lezione: **prima di creare un asset visivo nuovo, controllare se esiste già coerenza altrove**. 15 minuti persi a creare poi rimuovere SVG inutile
- **Banner pagina che linka a sé stessa**: avevo messo `<AnnouncementBar />` su /library ma il banner linkava a /library — auto-referenziale, anti-pattern. Max l'ha visto e l'ha rimosso. Stesso problema che il CEO aveva risolto in sessione 6 togliendolo da blueprint. Lezione: l'AnnouncementBar è utile SOLO su pagine **non** legate al prodotto annunciato

### Domande aperte aggiunte per il CEO (sessione 7)

10. **STYLEGUIDE § 20 React Islands**: documentare ora i pattern d'uso (`client:visible` di default, mobile fallback con `useIsMobile`, scoping styles via `style` tag inline JSX, niente Astro-scoped CSS dentro componenti React) — alta priorità prima che la conoscenza si disperda
11. **Switch domain**: con **9/9 pagine portate** (parità completa col vecchio sito), siamo pronti per deploy preview Vercel? Lo STYLEGUIDE registra l'analytics (Umami + Vercel) come "non-ancora-portati" — questo è l'ultimo gate prima del go-live
12. **Sessione 8 — caccia ai bug**: Max ha proposto un giro di rifiniture cross-page invece di una pagina nuova. Approccio: lista tutti i piccoli problemi visti durante l'uso reale del sito locale, fixarli in batch, poi commit unico

---

## Aggiornamento — sessione 8 (2026-05-04) — **GO LIVE**

**Status post-sessione 8:** Il sito Astro nuovo è **online su `bagholderai.lol`**. Switch fatto a metà giornata dopo caccia bug + 4 fix critici trovati durante uso reale + porting tf.html/grid.html con restyling colori. Search Console aggiornato con sitemap nuova.

### Apertura sessione — pulizia tecnica sessione 7

3 commit di chiusura sessione 7 fatti la sera prima venivano committati a mente fresca:

- `e19ceb3` — feat: /howwework + React island + setup `@astrojs/react` + token `--color-cc`
- `485a9d4` — docs: STYLEGUIDE § 20 React Islands + § 5 role colors mapping
- `5ba3c03` — fix: 4 bug fix sessione 8 (vedi sotto) + cleanup prototipi `dashboard-a/b/c.astro`

**STYLEGUIDE § 20 — React Islands**: 9 sotto-sezioni che documentano i pattern emersi durante /howwework. Punti chiave:
- Quando usare un'isola React (criteri concreti) vs Astro vanilla
- `client:visible` come default (vs `load`/`idle`/`only`)
- Pattern colore: token CSS Tailwind class quando possibile, hex parallel constant solo per `style={{color}}` dinamico
- Niente `<style>` Astro-scoped dentro JSX (Astro non scopa il React render). Soluzione: keyframe come stringa JS iniettata via `<style>{KEYFRAMES}</style>` con prefisso namespace
- `useIsMobile()` hook con `window.matchMedia` per mobile fallback (no SSR mismatch perché il componente è `client:visible`)
- Stop-on-click su auto-play timer (carousel pattern)
- "Quando l'isola NON deve essere un'isola": se l'interattivo è il 90% della pagina, ripensa l'architettura

§ 5 della STYLEGUIDE estesa con:
- Token `text-cc` `#818cf8` documentato
- **Bot identity colors come eccezione esplicita**: Grid `#22c55e` + TF `#f59e0b` + Sentinel `#3b82f6` + Sherpa `#ef4444` saturati per "indicatore di salute bot a colpo d'occhio". NON sostituire con token desaturati
- Role colors mapping esplicito CEO → pos / Max → amber-400 / CC → cc

### Caccia bug — 4 fix in batch (commit `5ba3c03`)

Max ha aperto il sito locale e ha trovato 4 problemi durante uso normale. Pattern da sessione 6 applicato: lista completa prima, poi fix in batch.

**Bug 1 — /diary: scattino al caricamento**
La lista entry partiva con fallback statico (2 entries hardcoded) staggered, poi al fetch Supabase il container veniva rimpiazzato → l'animazione ripartiva da capo, "doppio refresh" visibile. Fix: non toggleare più `is-visible` durante il replace fallback→live; i nuovi figli ereditano la visibilità dal parent senza re-animarsi.

**Bug 2 — /library: cover libro tagliata su titolo**
Lo scaffale 3D usa `background-position: center` per le copertine. A larghezze intermedie tra 1024 e 1280px, la cover Volume 2 (con "BagHolderAI" e sottotitolo a sinistra) veniva tagliata sul lato destro mostrando solo metà titolo. Fix: `background-position: left center` — il titolo del libro (sempre a sinistra delle cover Payhip) resta sempre visibile.

**Bug 3 — /howwework: workflow timer troppo lento**
Auto-play 12 secondi sulla timeline = troppo, l'utente non capisce cosa cambia tra uno step e l'altro. Confronto rapido sui valori: 5s troppo ipnotico, 8s ancora "look at me", 12s "respiro" ma confonde, **6s vincente** (Max: "abbassiamo a 6 secondi"). Fix: `AUTOPLAY_MS = 6000`.

**Bug 4 — /howwework: workflow timeline scattava verso il basso al primo click**
Cliccando un nodo dell'org chart si apriva il pannello dettaglio sotto, spingendo la timeline e tutto il resto della pagina di ~280px verso il basso. L'utente perdeva il punto di lettura.

Brainstorm 30 minuti su 4 strategie possibili (A: panel fixed/sticky, B: panel dentro l'area chart, C: panel con altezza fissa pre-allocata, D: 2 colonne tutta pagina). Tutte avevano contro più gravi del problema. Soluzione finale **proposta da Max**: aprire la pagina con CEO già selezionato di default. **Il pannello è sempre visibile dal primo render**, quindi cliccando un altro nodo/connessione il contenuto **swappa** invece di **espandere**. Niente shift della timeline.

Fix: `useState("ceo")` invece di `useState(null)` per `selectedNode`. + rimossa la scritta "Click on a role or a connection to explore" che ora è ridondante.

**Cleanup prototipi**: `dashboard-a.astro`, `dashboard-b.astro`, `dashboard-c.astro` (sessione 4) eliminati. Build da 13 → 10 pagine. Erano già nella lista deferred da 2 sessioni.

**Lezione di processo (Max)**: a metà /howwework Max ha chiesto di salvare in memoria *"non fare screenshot via headless dopo Edit visivi"*. Vedrò io nel browser, gli screenshot sprecano tempo+token. Memoria persistente aggiornata.

### tf.html + grid.html — port + restyling colori (commit `d08290f`)

**Decisione di sostanza** (Max): le control room operative TF e Grid del sito vecchio (1773 + 1093 righe di HTML+CSS+JS monolitico) **non vanno rifatte**, vanno **portate verbatim** in `web_astro/public/`. Astro le serve identiche al vecchio.

Restyling minimale solo dei colori per allineare al design system nuovo:
- `body bg #0a0a0a` (nero) → `#0f1626` (--color-bg blu)
- `--text/--text-dim/--text-body/--border/--surface` → token nuovi
- `--red/--blue/--teal/--yellow` → desaturati a token nuovi
- **Bot identity colors mantenuti saturati**: `--green: #22c55e` (Grid) e `--amber: #f59e0b` (TF) — eccezione documentata in STYLEGUIDE § 5

NIENTE cambiamenti strutturali, NIENTE modifiche al JavaScript, NIENTE swap dei font (SF Pro Display + SF Mono restano). I bot operano correttamente, Max li usa ogni giorno.

L'originale `web/tf.html` e `web/grid.html` lasciati intatti come safety net (file backup mai sostituiti).

### Pre-launch SEO (commit `ea9ea65`)

5 file di infrastruttura aggiunti per non perdere indicizzazione Google al momento dello switch:

1. **`web_astro/vercel.json`** — config Vercel per il nuovo Root Directory
   - `cleanUrls: true` (per servire /tf e /grid senza .html)
   - Redirect `/buy` → Payhip (ereditato dal vecchio)
   - **Redirect 301 `/guide` → `/library`** (era TODO da sessione 7, ora chiuso)

2. **`@astrojs/sitemap`** — integrazione Astro che genera `dist/sitemap-index.xml` automaticamente al build dalle pagine. 10 URL pubblici, /tf e /grid filtrati esplicitamente (control room operative non per Google). `site: 'https://bagholderai.lol'` configurato.

3. **`public/robots.txt`** — Allow all + Disallow `/tf` `/grid` `/tf.html` `/grid.html` + sitemap reference.

4. **`public/og-image.png`** (186KB) — copiato dal vecchio sito. Senza questo, condividere link su X/Telegram/HN avrebbe mostrato preview vuota.

5. **Layout.astro: meta tags OG completi** — `og:image` + `og:image:width/height/locale` + `twitter:image` + `twitter:title` + `twitter:description`. Erano tutti mancanti, restavano solo `og:type` `og:title` `og:description`.

### Tasto dolente — bug PostgREST 1000 row cap (commit `1ac87b3`)

**Il bug più subdolo della sessione**, scoperto da Max guardando ZEC su /dashboard.

**Sintomo iniziale**: dashboard mostra card ZEC con `avg —` invece del prezzo medio. Investigazione lunga (anche perché Max e CC stavano parlando esattamente mentre il sell ZEC arrivava — confusione su "non c'è sell" vs "il sell è arrivato 30 secondi fa").

**Diagnosi**: scoperto che **Supabase impone un cap server-side hard di 1000 righe sulla tabella trades** per il ruolo anon, **indipendentemente da `limit=` o header `Range:`**. Tested: 1003 trade in DB ma fetch restituisce solo 999 ordinati per `created_at.asc`. I 4 trade più recenti (incluso il sell ZEC delle 13:14 UTC) **non arrivavano mai nel browser**.

Conseguenza: il FIFO replay del dashboard processava solo trade fino al #999, vedendo le posizioni come ancora aperte quando in realtà erano già state chiuse. La card ZEC mostrava `avg —` perché lo script credeva ci fosse ancora 0.015 ZEC in mano (riga buy senza sell), ma il calcolo `openCost / openAmount` con dati incompleti dava NaN → `—`.

**Tentativi falliti** (documentati per memoria):
1. Aumentare `limit=50000` → ignorato dal server, sempre 1000 righe restituite
2. Header `Range: 0-49999` → idem, ignorato

**Fix vincente — pattern già usato da `tf.html`**:
- Le coin del bot hanno `managed_by` fisso (BTC=manual sempre, DOGE=trend_follower sempre, TRX=tf_grid sempre)
- Filtrando lato server `managed_by=eq.manual` ricevi solo i 395 trade Grid (sotto cap)
- Filtrando `managed_by=in.(trend_follower,tf_grid)` ricevi solo i 608 TF (sotto cap)
- Il FIFO replay lavora ancora correttamente perché ogni simbolo è gestito da un solo bot, le code per simbolo non si mescolano cross-bot

**Implementazione**: nuova helper `fetchAllTrades<T>(selectFields)` in `dashboard-live.ts` che fa 2 fetch parallele (Grid + TF) e ritorna array unificato sortato per `created_at`. Migrazione di tutte le 6 fetch FIFO esistenti (5 in dashboard-live.ts + 1 in live-stats.ts).

Risultato: ZEC sell delle 13:14 UTC visibile **immediatamente** nel dashboard al refresh dopo il fix. Cap PostgREST disinnescato.

### Polish dashboard tabelle (stesso commit `1ac87b3`)

**Problema**: le tabelle Recent Activity Grid e TF avevano larghezze colonne diverse perché ogni `<table>` auto-dimensionava le colonne dal proprio contenuto (TF mostra `@ buy avg` annotation sui sell, Grid quasi mai). Risultato: visivamente disallineate.

**Fix**: aggiunto `table-fixed` + `<colgroup>` con `<col style="width:24%/11%/18%/17%/30%">` identico in entrambe le tabelle. Adesso allineate a pixel.

### A-Ads — port verbatim, opt-out per legali (stesso commit `1ac87b3`)

Iframe A-Ads (`data-aa='2431743'`, `size=Adaptive`, `728x90`) era presente sul vecchio sito su /index.html e /dashboard.html. Sul nuovo sito **non c'era da nessuna parte**.

**Decisione architetturale (Max)**: invece di duplicarlo per ogni pagina come nel vecchio, lo metto **una sola volta** dentro `SiteFooter.astro` come prima sezione. Appare automaticamente su tutte le 9 pagine pubbliche.

**Eccezione opt-out** per /terms, /privacy, /refund: nuovo prop `noAds?: boolean` su Layout, le 3 legali lo passano a `true`. Motivazione: A-Ads policy + visual mismatch su pagine contrattuali.

**Vincoli A-Ads** documentati nel commento del codice (Max ricorda che A-Ads ha già contestato una volta per visual tampering):
- Iframe verbatim, no modifiche
- 728×90 desktop, max-width:100% mobile (lascia A-Ads gestire lo scaling)
- **NIENTE opacity, transforms, width override** sull'iframe
- /tf e /grid (statici in public/) automaticamente non lo hanno (footer Astro non li tocca)

### Switch Vercel — go-live

Max ha fatto la procedura di switch sul dashboard Vercel in ~10 minuti:

1. Settings → General → **Root Directory**: `web` → `web_astro`
2. Framework Preset: auto-rilevato come **Astro**
3. Build Command / Output Directory / Install Command: lasciati ai default Astro
4. Save → Vercel mostra warning "Configuration differ" (atteso — significa che il deployment vivo usa ancora la config vecchia)
5. Deployments → 3 puntini sul deployment più recente → **Redeploy** (con "Use existing Build Cache" disattivato per build fresca)
6. Build Vercel ~1 minuto: `npm install`, `npm run build`, deploy `dist/`
7. **Live**.

### Search Console — sitemap nuova

Post-switch, Max ha fatto il submit della nuova sitemap su Google Search Console:
- URL: `https://bagholderai.lol/sitemap-index.xml` (Astro convention, NON `sitemap.xml`)
- Search Console → Sitemap → Aggiungi sitemap → Invia
- Verifica del dominio era già configurata via DNS TXT (sopravvive lo switch — la verifica Google è sul DNS, non sul sito)

Da fare nei prossimi giorni:
- Search Console → Inspection → home → "Request Indexing" per accelerare re-crawl
- Monitorare A-Ads dashboard per qualche giorno: se compare warning "ad unit not visible" o simili, segnalare immediatamente

### Cose risolte vs. cose deferred (sessione 8)

**Risolte**:
- ✅ /howwework + React island + STYLEGUIDE § 20 + token `--color-cc` (commit `e19ceb3` `485a9d4`)
- ✅ 4 bug fix critici da uso reale (`5ba3c03`)
- ✅ Cleanup prototipi dashboard-a/b/c
- ✅ Port tf.html + grid.html con restyling colori (`d08290f`)
- ✅ Vercel.json + sitemap + robots + redirect /guide→/library + OG meta (`ea9ea65`)
- ✅ **Bug PostgREST 1000-row cap** disinnescato con split fetch by managed_by (`1ac87b3`)
- ✅ Tabelle Recent Activity allineate (table-fixed + colgroup)
- ✅ A-Ads portato in SiteFooter con opt-out per legali
- ✅ **Switch domain — sito Astro live su bagholderai.lol**
- ✅ Search Console sitemap aggiornata
- ✅ Memoria persistente: regola "no screenshot dopo Edit visivi"

**Deferred**:
- 🟡 Search Console: Request Indexing per home (tu, qualche giorno)
- 🟡 Monitor A-Ads scan per qualche giorno
- 🟡 Mobile pipeline TF→GRID arrow (rimasta da sessione 5-6, non bloccante)
- 🟡 Analytics Umami non ancora portati nel Layout — al momento il sito ha solo Vercel Analytics built-in
- 🟡 **Server-side FIFO** come refactor architetturale: bot scrive `buy_avg_price` su trades al sell, dashboard legge senza replay. Risolverà definitivamente il cap 1000 quando saremo a 5000+ trade. Brief separato da scrivere

### Tempo cumulativo (sessioni 1-8)

Sessione 8 ~5h (3 commit chiusura + caccia bug + tf/grid + SEO + diagnosi cap PostgREST + switch Vercel + Search Console) → **cumulato ~32h totali** per il progetto web_astro.

**Stato del sito** (post-sessione 8):
- **9/9 pagine live in produzione** su `bagholderai.lol` (home, dashboard, diary, blueprint, roadmap, library, howwework, terms, privacy, refund — più /tf e /grid statiche)
- Sitemap submitted, OG cards, redirect 301 /guide → /library
- A-Ads attivo su 7 pagine pubbliche, off su 3 legali
- 1003 trade gestiti correttamente lato browser via split fetch by managed_by
- React island disponibile per pagine future (ufficio coi bot, ecc)

### Lezioni di processo (sessione 8)

**Cosa ha funzionato**:
- **Lista bug completa prima di fixare**: pattern da sessione 6 ripreso. Max ha consegnato 3 bug insieme (diary scattino + library cover + howwework timing), io ho fixato in batch in un solo refresh per Max. Più efficiente del fix-uno-per-volta
- **Soluzione semplice quando il complicato non funziona**: 30 min di brainstorm su layout 2 colonne per fix shift workflow, poi Max propone "apri con CEO selezionato di default". 5 righe di codice, problema risolto. Quando le soluzioni complesse cercano di mascherare il sintomo invece di risolvere la causa, fermarsi e cercare un trick più diretto
- **Investigare il "non funziona" prima di tirare a indovinare**: il bug ZEC sembrava un display issue triviale. Investigazione profonda ha rivelato cap PostgREST 1000 — un problema architetturale silenzioso che si sarebbe manifestato in modo casuale ad alti volumi. Senza l'investigazione, avremmo "fixato" superficialmente cambiando solo `fmtPriceJs(0)` per non mostrare `—`, mascherando il problema vero
- **Pattern del vecchio sito quando funziona**: tf.html aveva da sempre il filtro `managed_by` server-side. Copiando il pattern abbiamo evitato la PostgREST 1000-cap. Il vecchio sito ha lezioni da insegnare anche dopo il refactoring

**Cosa NON ha funzionato**:
- **Il fix `limit=50000` come prima reazione al cap PostgREST**: ho aggiunto il parametro a tutte le 6 fetch + commento. Falso fix: il cap è server-side, ignora il client. 10 minuti persi prima di testare con curl che effettivamente PostgREST risponde sempre con 1000. Lezione: **prima testare l'ipotesi, poi modificare il codice**
- **Tentativo di sostituire emoji 🎒 con SVG zaino**: copia-incollato dal sessione 7, errore identico. Max ha realizzato troppo tardi che l'emoji giusta era già nella home. 15 min persi. Lezione (registrata in memoria di sessione 7): **prima di creare asset visivo, verificare coerenza con altre pagine**
- **Mancanza di auto-refresh sul dashboard**: il vecchio dashboard si rinfresca ogni 5 min, il nuovo no. Bug minore (Max si è ricordato che ricaricando manualmente vede dati nuovi), ma è regressione. **TODO sessione futura**: aggiungere `setInterval` di re-fetch ogni 5 min al dashboard

### Domande aperte aggiunte per il CEO (sessione 8)

13. **Server-side FIFO**: il fix split-by-managed_by funziona fino a ~3000 trade per bot (cap 1000 × 3 split possibili = ~3000). Per la mainnet vera dobbiamo passare a server-side FIFO (bot scrive `buy_avg_price` su trades al sell, dashboard legge senza replay). Brief separato da scrivere quando saremo a 50% del threshold (~1500 trade per bot). Stima oggi: a ~30 trade/giorno, ~50 giorni di ulteriore margine prima di doverci pensare
14. **Auto-refresh dashboard**: aggiungere o no `setInterval` di re-fetch ogni 5 min come il vecchio? Pro: dato live senza ricaricare. Contro: ogni refresh è ~12 fetch parallele Supabase, su una pagina lasciata aperta tutto il giorno fa molte richieste. Alternativa più leggera: refresh solo dei numeri principali (today P&L, today trades, recent activity), non dei chart. Da decidere
15. **Analytics Umami**: portarlo dal vecchio sito o lasciare solo Vercel Analytics built-in? Umami dà più controllo (no cookies, GDPR-friendly, dashboard self-hosted). Vercel basta per metrics base. Per il livello di traffico attuale (~100-500/giorno), entrambi vanno bene. Decisione cosmetica
16. **Visione "ufficio coi bot"**: era già in roadmap come futuro. Adesso che React è integrato, è più semplice da realizzare. Ha senso prima dello show HN per "wow effect"?
