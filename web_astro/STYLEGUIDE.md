# web_astro — Style guide

Pattern e convenzioni del sito Astro di BagHolderAI. **Leggere prima di
creare una nuova pagina** o di toccare quelle esistenti. Aggiornato
all'ultima sessione di porting (Session 54 · Maggio 2026).

Questo documento esiste perché le prime 5 sessioni di sviluppo del sito
Astro hanno cristallizzato delle scelte (container width, hero,
spaziatura, palette) che vivevano solo nel codice. Ogni nuova pagina
veniva ricostruita ex novo, i predecessori erano costretti
all'archeologia. **Da qui in poi: leggi questo file, copia gli snippet,
e parti.**

---

## 1. Gerarchia di file

```
web_astro/
  src/
    layouts/
      Layout.astro         ← header + footer + meta + reveal/counter scripts
    components/
      SiteHeader.astro     ← nav + live status strip (top of page)
      SiteFooter.astro     ← social links + disclaimer + Terms/Privacy
      Logo.astro
      AnnouncementBar.astro ← optional Volume promo (parked, not used yet)
      BotCard.astro / BotMascot.astro / SVG icon components
    pages/
      index.astro          ← home
      dashboard.astro      ← live data, § 3 charts
      diary.astro          ← live entries from Supabase
      blueprint.astro      ← static historical doc
      roadmap.astro        ← static, data from src/data/roadmap.ts
    scripts/
      dashboard-live.ts    ← Supabase live wiring for /dashboard
      diary.ts             ← Supabase live wiring for /diary
      live-stats.ts        ← home stats strip
    data/
      dashboard-mock.ts    ← fallback shapes for dashboard
      roadmap.ts           ← single source of truth for /roadmap
    styles/
      global.css           ← Tailwind v4 + design tokens + .reveal/.reveal-stagger
```

**Regola**: dato e markup separati. Se una pagina porta una lista
hardcoded (es. roadmap), il dato vive in `src/data/<page>.ts`, il
template solo si occupa del rendering.

---

## 2. Layout & container

Tutte le pagine **devono** usare `<Layout>` e mantenere il container
unificato.

```astro
<Layout
  title="Page name — BagHolderAI"
  description="One sentence, ≤160 chars (search snippet)."
  current="page-key"   {/* dashboard | diary | blueprint | howwework | roadmap | guide */}
>
  {/* hero section */}
  <section class="mx-auto max-w-4xl px-4 pt-10 pb-6 sm:px-6 sm:pt-14 sm:pb-8">
    {/* h1 + subtitle + meta-strip */}
  </section>

  {/* main content */}
  <main class="mx-auto max-w-4xl px-4 pb-24 sm:px-6">
    {/* sections separated by <hr> */}
  </main>
</Layout>
```

**Container width = `max-w-4xl`** (896px). Sempre. Niente `max-w-3xl`,
niente `max-w-6xl`. Nemmeno per pagine "più strette" come blueprint —
abbiamo provato, sembrava brutto, abbiamo standardizzato su 4xl
ovunque.

**Padding orizzontale = `px-4 sm:px-6`**. 16px su mobile, 24px da `sm`
(640px) in su.

**Pattern hero ↔ main**: hero ha padding verticale generoso
(`pt-10 pb-6 sm:pt-14 sm:pb-8`); main ha solo `pb-24` perché lo
spacing top arriva dal margin bottom dell'hero o dal primo `<hr>`
della main.

---

## 3. Hero (titolo pagina)

Pattern verbatim, copia-incollabile:

```astro
<section class="mx-auto max-w-4xl px-4 pt-10 pb-6 sm:px-6 sm:pt-14 sm:pb-8">
  <h1 class="text-[28px] font-semibold leading-[1.12] tracking-tight
             text-text sm:text-[34px] md:text-[40px] md:leading-[1.08]">
    Lab <span class="text-primary">notebook</span>.
  </h1>

  <p class="mt-3 max-w-2xl text-[14.5px] leading-[1.55] text-text-dim sm:text-[15px]">
    One paragraph subtitle. Keep under 2 lines.
  </p>

  <div class="mt-5 flex flex-wrap items-center gap-3 font-mono text-[10.5px]
              uppercase tracking-[0.16em] text-text-muted">
    <span class="inline-flex items-center gap-1.5">
      <span class="inline-block h-1.5 w-1.5 rounded-full bg-pos
                   shadow-[0_0_8px_rgba(134,239,172,0.7)]"></span>
      <!-- live identifier (date, version, day count, etc.) -->
    </span>
    <span class="text-border">·</span>
    <span><!-- second meta --></span>
    <span class="text-border">·</span>
    <span><!-- third meta --></span>
  </div>
</section>
```

**Regole hero**:

- **h1**: una parola accentata in `text-primary` (ciano `#7dd3fc`).
  Pattern `Lab notebook.` / `Construction log.` / `What we're
  building.` / `The original blueprint.` — frase breve + punto.
- **Subtitle**: max 2 righe, `text-text-dim`, `max-w-2xl` per non
  stenderlo a 4xl interi.
- **Meta-strip**: SEMPRE presente, anche se è una sola informazione.
  È l'ancora visiva che identifica la pagina come "del fondo". Pallino
  verde pulsante a sinistra, separatori `·` tra i campi.

---

## 4. Sezioni dentro main

Pattern: ogni sezione separata da `<hr>` + `<section class="mt-8">`,
con un h2 mono in alto.

```astro
{/* ============ § N — TITLE ============ */}
<hr class="mt-12 border-t border-border-soft" />
<section class="mt-8">
  <h2 class="font-mono text-[12px] uppercase tracking-[0.18em] text-pos mb-5">
    § N · Section title
  </h2>

  {/* content */}
</section>
```

**Perché `§ N · ...`**: convenzione presa da paper accademici, dà
struttura senza essere pesante. Numerazione esplicita in dashboard
(§ 1 fino a § 5) e in roadmap (Phase 0 fino a Phase 8).

**Spaziatura inter-sezione = `<hr class="mt-12">` + `<section class="mt-8">`**:
totale 80px tra il fondo della sezione precedente e l'h2 della
successiva. Si percepisce come un "respiro". Non scendere sotto.

**Eccezione lista densa** (es. roadmap): se la pagina è una sequenza
di card omogenee, non usare `<hr> + <section>`. Pattern:

```astro
<section class="mt-10 border-t border-border-soft">
  {items.map(item => (
    <details class="group border-b border-border-soft
                    transition-colors hover:bg-surface/20">
      <summary class="cursor-pointer list-none ... px-3 py-5">
        ...
      </summary>
    </details>
  ))}
</section>
```

Il `border-b` di ogni `<details>` fa da separatore. Niente margin
esterni tra le card. Il pattern è preso da `/diary` (entries list).

---

## 5. Design tokens (palette + typography)

Definite in `src/styles/global.css` come variabili Tailwind v4.

### Background

| token | hex | uso |
|---|---|---|
| `bg-bg` | `#0f1626` | sfondo della pagina |
| `bg-surface` | `#172037` | card, table, dropdown |
| `bg-surface-hover` | `#1f2a44` | hover su card cliccabili |

### Border

| token | hex | uso |
|---|---|---|
| `border-border` | `#2a3556` | bordo standard di card |
| `border-border-soft` | `#1c2540` | divisori interni, separatori list |

### Testo

| token | hex | uso |
|---|---|---|
| `text-text` | `#e8ecf5` | testo principale |
| `text-text-dim` | `#9aa3b8` | testo secondario, paragrafi body |
| `text-text-muted` | `#5d6680` | etichette mono uppercase, meta |

### Accent (status colors)

| token | hex | uso |
|---|---|---|
| `text-primary` | `#7dd3fc` | accenti h1, link primari |
| `text-primary-hover` | `#38bdf8` | hover stato primary |
| `text-pos` / `bg-pos` | `#86efac` | positivo, completed, gain |
| `text-neu` / `bg-neu` | `#67e8f9` | neutro, "active", info |
| `text-neg` / `bg-neg` | `#fca5a5` | negativo, loss, error |
| `text-yellow-300` | `#fcd34d` | "todo", "open", warning |
| `text-amber-400` | `#fbbf24` | "NEW" tag, sezione TF (vs Grid), Max identity |
| `text-cc` / `bg-cc` | `#818cf8` | Claude Code (CC) identity, on /howwework |

**Regola palette**: mai colori arbitrari (`#22c55e`, `#ef4444`, ecc.).
Sempre token. Se serve un colore nuovo, prima si aggiunge a
`global.css` come variabile, poi si usa.

**Role colors** (su `/howwework` e potenzialmente altri posti dove
appaiono i 3 attori del progetto):
- CEO (Claude) → `text-pos` `#86efac`
- Max (board)  → `text-amber-400` `#fbbf24`
- CC (intern)  → `text-cc` `#818cf8`

**Bot colors — eccezione documentata** (su `/dashboard` e `global.css`
per le `.bot-card`):
- Grid bot   → `#22c55e` (green saturato, NON `--color-pos`)
- TF bot     → `#f59e0b` (amber saturato, NON `--color-amber-400`)
- Sentinel   → `#3b82f6` (blu)
- Sherpa     → `#ef4444` (rosso)

Sono **identità di prodotto** (i bot del fondo), non palette di
design system. Sono saturati per leggere i numeri a colpo d'occhio
sulla dashboard. Vivono in `.bot-card.*-active`, `.bot-pill.live-*`,
e in alcuni inline `style="color:#..."` su `dashboard.astro`.
Non sostituire con i token desaturati — perderebbero la loro
funzione di "indicatore di salute bot".

### Font

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: "JetBrains Mono", "SF Mono", monospace;
```

**Sans**: corpo del testo, h1, h2 sezione (titolo principale).
**Mono**: numeri, etichette uppercase, badge, meta-strip, tabelle.
Convenzione: tutto ciò che è "dato strutturato" → mono.

---

## 6. Sizing typography (cheat sheet)

Valori arbitrari Tailwind (`text-[14px]`) coerenti tra le pagine:

| Elemento | Classi |
|---|---|
| h1 hero | `text-[28px] sm:text-[34px] md:text-[40px] font-semibold leading-[1.12] md:leading-[1.08] tracking-tight` |
| Subtitle hero | `text-[14.5px] sm:text-[15px] leading-[1.55] text-text-dim` |
| h2 sezione (§ N) | `font-mono text-[12px] uppercase tracking-[0.18em] text-pos` |
| h2 documento (paragrafo) | `text-[18px] font-bold text-text` |
| h3 sub-sezione | `font-sans text-[16px] sm:text-[17px] font-semibold text-text` |
| Body paragrafo | `text-[14.5px] leading-[1.7] text-text-dim` |
| Meta-strip / etichetta | `font-mono text-[10.5px] uppercase tracking-[0.16em] text-text-muted` |
| Tabella body | `font-mono text-[12.5px]` |
| Tabella header | `font-mono text-[10px] uppercase tracking-[0.1em] text-text-muted` |
| Badge / chip | `font-mono text-[9px] uppercase tracking-[0.16em]` |
| Footnote | `font-mono text-[10px] italic text-text-muted` |

**Letter-spacing uppercase mono**: usa `tracking-[0.18em]` per h2/§
title, `tracking-[0.16em]` per meta-strip, `tracking-[0.14em]` per
badge piccoli, `tracking-[0.10em]` per tabella header. Mai uppercase
senza tracking — diventa illeggibile.

---

## 7. Componenti riutilizzabili

### Tabelle (pattern di blueprint, dashboard, roadmap)

```astro
<div class="overflow-x-auto rounded-lg border border-border bg-surface">
  <table class="w-full font-mono text-[12.5px]">
    <thead class="border-b border-border-soft">
      <tr class="text-text-muted uppercase tracking-[0.1em] text-[10px]">
        <th class="px-3 py-2.5 text-left">Col 1</th>
        <th class="px-3 py-2.5 text-left">Col 2</th>
      </tr>
    </thead>
    <tbody>
      <tr class="border-t border-border-soft">
        <td class="px-3 py-2.5 text-text">primary cell</td>
        <td class="px-3 py-2.5 text-text-dim">secondary cell</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Convenzioni**:
- Wrapper `overflow-x-auto rounded-lg border border-border bg-surface`
- `font-mono text-[12.5px]` per il body (tutte le tabelle)
- Header in `text-text-muted` uppercase con tracking
- Prima colonna in `text-text` (più chiaro), altre in `text-text-dim`
- Numeri con `tabular-nums` per allineamento
- Riga totale in `font-semibold text-pos` (verde) per evidenziarla

### Callout (warning + framing)

**Yellow callout** (note di attenzione):
```astro
<aside class="my-5 border-l-2 border-yellow-500/60 bg-yellow-500/[0.04]
              py-2.5 pl-4 text-[13px] italic leading-[1.6] text-text-dim">
  Text here.
</aside>
```

**Green framing** (premessa o context block):
```astro
<section class="rounded-lg border border-pos/30 bg-pos/[0.04] p-5 sm:p-6">
  <p class="text-[14.5px] leading-[1.7] text-text-dim">
    <strong class="text-pos">Bold opener.</strong> Rest of text.
  </p>
</section>
```

### Lista con bullet `›` verde

```astro
<ul class="space-y-1.5 text-[14.5px] leading-[1.7] text-text-dim mb-4">
  <li class="relative pl-4 before:absolute before:left-0 before:text-pos before:content-['›']">
    Item text
  </li>
</ul>
```

### Badge / chip status

```astro
<span class="rounded-full border border-pos/30 text-pos bg-pos/5
             px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em]">
  complete
</span>
```

Varianti per le palette:
- Done / Complete → `border-pos/30 text-pos bg-pos/5`
- Active / Building → `border-neu/40 text-neu bg-neu/5` (con `●` davanti)
- Todo / Open → `border-yellow-500/40 text-yellow-300 bg-yellow-500/5`
- Planned / Deferred → `border-border-soft text-text-muted bg-surface`

### Card (per § sections)

```astro
<div class="rounded-lg border border-border bg-surface p-5">
  {/* content */}
</div>
```

`p-5` (20px padding) standard. Per card più dense usa `p-3` o `p-4`.
Per card più ariose `p-6 sm:p-8`.

---

## 8. Reveal & animazioni

Layout fornisce due classi auto-animate (definite in
`global.css`, controllate dallo script in `Layout.astro`):

- `.reveal` — l'elemento parte invisibile, fade-in + slide-up quando
  entra in viewport
- `.reveal-stagger` — i figli direttamente dentro animano uno dopo
  l'altro (250ms tra l'uno e l'altro)

### ⚠️ Regole tassative

**1. Mai `.reveal` su un wrapper che contiene una lista lunga.**
L'`IntersectionObserver` ha `threshold: 0.08` (8% dell'elemento deve
essere in viewport). Se l'elemento è alto migliaia di pixel (es.
roadmap con 9 phase aperte, o Phase 8 con 207 task), l'8% diventa
centinaia di pixel di scroll prima di "attivare" l'animazione →
**l'utente vede una pagina vuota** finché non scrolla a metà.

Sintomo: "non vedo nulla, solo l'header della pagina".

Soluzione: applica `.reveal` solo a hero, stats bar, paragrafi singoli.
Per liste lunghe (table, list di card, ecc.) → niente reveal.

**2. Mai più di una `.reveal-stagger` annidata.**
I `transition-delay` su `nth-child` non si compongono — i figli del
secondo livello partono insieme.

**3. Animazioni testate su Chrome + Safari.**
Storia: `IntersectionObserver` su Chrome a volte salta lo
`opacity: 0` iniziale per elementi già in viewport. Layout.astro ha
un workaround con `requestAnimationFrame` doppio. **Non rimuoverlo.**

---

## 9. Live data wiring

Pagine "live" (`/dashboard`, `/diary`, `/`) servono mock data come
fallback server-side, poi un script lato client li sostituisce.

### Pattern

In `.astro`:
```astro
<dd id="hero-pnl" class="...">
  {fmtSigned(mockTotalPnl)}    {/* fallback shown immediately */}
</dd>

<script>
  import "../scripts/dashboard-live.ts";
</script>
```

In `src/scripts/dashboard-live.ts`:
```ts
const setText = (id: string, value: string) => {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

(async () => {
  try {
    const data = await sbq<...>("table", "select=...");
    setText("hero-pnl", fmtSigned(data.value));
  } catch (err) {
    console.warn("[dashboard-live] failed:", err);
    /* leave the mock fallback in place */
  }
})();
```

**Regole**:
- **No fetch in frontmatter** (`---` block). Solo mock data importato
  da `src/data/<page>-mock.ts`.
- **Live wiring sempre in `.ts` separato**, mai inline nel `.astro`
  (vedi § 10 sotto).
- **Try/catch silente con `console.warn`**: se la fetch fallisce,
  l'utente vede il mock — meglio dato vecchio che pagina rotta.
- **Counter animation**: per numeri animati usa
  `window.__updateLiveStat(id, newText)` definito in Layout.astro.
  Esempio: `window.__updateLiveStat("hero-day", "47")` produce un
  count-up smooth da 0 a 47.

---

## 10. Regola TypeScript: niente TS inline negli `<script>` di `.astro`

**Sintomo**: errori TypeScript nei file `.astro` che usano
`<script>...TS code...</script>` con `as HTMLCanvasElement` o
generics. Astro li compila come moduli separati ma lo strict mode TS
non sempre li type-checka coerentemente.

**Pattern corretto**:
```astro
{/* ❌ NO — TS inline nello script */}
<script>
  const el = document.getElementById("foo") as HTMLCanvasElement;
  el.getContext("2d")!.fillRect(0, 0, 10, 10);
</script>

{/* ✅ SÌ — script importa il modulo .ts */}
<script>
  import "../scripts/foo.ts";
</script>
```

In `src/scripts/foo.ts` puoi usare TypeScript stretto quanto vuoi.

Storia: la sessione 53 ha trascorso ~2h debuggando un cast `as
HTMLCanvasElement` inline che falliva a runtime con un errore opaco.
Spostato in `.ts` esterno, problema sparito.

---

## 11. Dev workflow

### Avvio dev server

```bash
cd web_astro
npm run dev
```

Apre `http://localhost:4321/` (o 4322/4323/... se altre porte sono
occupate).

### ⚠️ Un solo dev server alla volta

**Storia di un dolore**: durante la sessione 54, il browser stava
puntando a `localhost:4321` (server vecchio con codice stale) mentre
io modificavo file e Vite rigenerava sull'altro server attivo. Ore
sprecate a debug "il padding non cambia".

**Prima di avviare un nuovo server, killa gli orfani**:

```bash
lsof -ti:4321,4322,4323,4324 2>/dev/null | xargs kill -9 2>/dev/null
```

E ricontrolla che nessun processo `npm run dev` sia in giro:
```bash
ps aux | grep "astro dev" | grep -v grep
```

### Cache del browser

Chrome/Safari aggressivi su `localhost`. Se modifichi un file e non
vedi il cambiamento dopo `Cmd+R`:
1. **Hard reload**: `Cmd+Shift+R` (Chrome) / `Cmd+Option+R` (Safari)
2. **DevTools aperto + Disable cache**: tab Network → checkbox
   "Disable cache". Mentre DevTools è aperto, niente cache HTTP.
3. **Querystring forzato**: nella console:
   ```js
   location.replace(location.href + "?v=" + Date.now())
   ```

### Build production

```bash
npm run build      # static output → web_astro/dist/
npm run preview    # serve dist/ on localhost:4321
```

`npm run build` fa anche type-check via Astro. Se la build passa,
deployment è sicuro.

---

## 12. Lezioni dolorose (per non rifarle)

Concentrato dei bug che mi hanno fatto perdere tempo nelle ultime
sessioni. Tienili a mente.

### "Vedo una pagina vuota, solo header"
→ `.reveal` su un wrapper troppo grande. Vedi § 8 regola 1.

### "Modifico il file ma non vedo il cambio"
→ Cache browser **o** dev server orfano. Vedi § 11.

### "I numeri lampeggiano / fanno conto alla rovescia strano"
→ Counter animation chiamato due volte sullo stesso elemento.
Usa solo `window.__updateLiveStat(id, value)`, mai
`el.textContent = ...` direttamente su elementi `[data-count]`.

### "TypeScript error opaco da `<script>` in .astro"
→ Sposta il TS in `src/scripts/<file>.ts` e importalo. Vedi § 10.

### "La pagina è troppo larga / stretta su mobile"
→ Hai usato `max-w-3xl` o `max-w-6xl` invece di `max-w-4xl`. Tutte
le pagine usano 4xl. Vedi § 2.

### "Il colore non corrisponde al resto del sito"
→ Hai usato un hex letterale (`#22c55e`) invece di un token
(`text-pos`). Vedi § 5.

### "Le righe di una lista lunga sono troppo strette"
→ Padding `py-N` troppo basso sul `<summary>` o `<li>`. La roadmap
usa `py-5` (=20px sopra+sotto, ~50px tra le righe). Diary usa `py-2.5`
ma ogni entry ha 2 righe di testo che la fanno sembrare alta.

### "Vedo un pulsante 'Menu' con un caret strano"
→ Hai aggiunto una regola CSS `details > summary {...}` global.
**Restringi sempre il selettore** a una classe scope (es.
`.roadmap-page details > summary`). SiteHeader usa `<details>` per il
menu mobile.

### "Build passa ma in dev vedo errori"
→ A volte Vite caches stale. Stoppa dev server, `rm -rf node_modules/.vite`,
riavvia.

---

## 13. Quando creare un nuovo componente in `src/components/`

**Regola degli "almeno 3"**: estrai un componente solo se lo userai
in almeno 3 posti diversi, oppure se ha logica complessa che vorresti
testare/iterare separatamente.

Esempi:
- ✅ `SiteHeader.astro` — usato in tutte le pagine via Layout
- ✅ `BotCard.astro` — riutilizzato in home + dashboard
- ⚠️ `AnnouncementBar.astro` — creato per blueprint+guide+howwework
  ma per ora usato 0 volte (CEO ha detto di toglierlo da blueprint).
  **Lo lasciamo parcheggiato** — se non lo useremo entro 2 sessioni,
  lo rimuoviamo.

Per lista riutilizzata in una sola pagina (es. tabella per blueprint):
**non estrarre**, scrivila inline. Astro ha JSX-like ma non c'è premio
per il riuso prematuro.

---

## 14. Quando il dato va in `src/data/<page>.ts`

**Regola**: separa quando il dato è strutturato e modificabile a
parte, indipendentemente dal markup.

Esempi:
- ✅ `roadmap.ts` — 297 task, 9 phase, modificato ogni sessione.
  Markup separato.
- ✅ `dashboard-mock.ts` — fallback shapes per /dashboard.
- ❌ Le 14 sezioni di blueprint — testo libero, modificato raramente.
  Inline in `blueprint.astro` va bene.

Se il dato è un **export typed** (`export const ROADMAP: RoadmapData = ...`),
puoi farlo crescere senza rompere nulla. TypeScript ti dirà subito se
una pagina dipendeva da una shape che hai cambiato.

---

## 15. SEO & metadata

Layout già gestisce title, description, canonical URL, OG tags. **Non
duplicare** in pagine specifiche. Pass solo `title` e `description`
come props:

```astro
<Layout
  title="Roadmap — BagHolderAI"
  description="What we're building, what's done, what's next. Every task by phase."
>
```

**Regole**:
- Title: ≤60 char, include "BagHolderAI"
- Description: ≤160 char, prima riga della pagina come riassunto
- Canonical URL si genera automaticamente da `Astro.url.pathname`

**Analytics** (Umami, Vercel) sono **non-ancora-portati** dal vecchio
`/web`. Quando torneremo a configurarli, vanno in `Layout.astro`, non
per pagina.

---

## 16. Quando mettere `is:inline` su `<style>`

```astro
<style is:inline>
  /* ... */
</style>
```

`is:inline` impedisce ad Astro di processare/scopare lo stile e lo
emette verbatim. Usalo quando:
- Hai bisogno di selezionare elementi generati dinamicamente
- Stai applicando regole con scope custom (`.roadmap-page details > summary`)
- Lo stile ha pseudo-elementi (`::before`, `::after`) che Astro
  scoping potrebbe rompere

Default Astro scopa gli stili al componente (li prefissa con
`[data-astro-cid-XXX]`). Ottimo per stili locali, problematico per
pseudo-elementi e selettori discendenti.

---

## 17. Checklist per nuova pagina

Prima di creare `src/pages/<nome>.astro`, fai questo:

- [ ] **Leggi questo file** in particolare § 2, § 3, § 5, § 6
- [ ] Aggiungi link in `SiteHeader.astro` (`links` array)
- [ ] Crea il file con il pattern `<Layout>` + hero + main
- [ ] **Container `max-w-4xl`** sia su hero che main
- [ ] Hero con h1 (parola accent in `text-primary`), subtitle,
      meta-strip
- [ ] Sezioni con `<hr> + <section class="mt-8">` + h2 mono `§ N`
- [ ] Solo token palette, niente hex letterali
- [ ] Se c'è dato lungo strutturato → `src/data/<nome>.ts`
- [ ] Se c'è live data → `src/scripts/<nome>.ts` con fetch + try/catch
- [ ] Test visuale a 3 width: 375 (mobile), 768 (tablet), 1280 (desktop)
- [ ] `npm run build` passa senza warning
- [ ] Se hai aggiunto `.reveal` su qualcosa → verifica che non sia un
      wrapper di lista lunga

---

## 18. Riferimenti incrociati

- **Pattern hero**: vedi `src/pages/diary.astro` (più semplice) o
  `src/pages/dashboard.astro` (con counter live)
- **Pattern lista lunga**: vedi `src/pages/diary.astro` (entries) o
  `src/pages/roadmap.astro` (phase con `<details>`)
- **Pattern documento testuale**: vedi `src/pages/blueprint.astro`
  (14 sezioni, tabelle, callout)
- **Pattern live data**: vedi `src/scripts/dashboard-live.ts` (fetch
  Supabase + render con FIFO + Chart.js plugin)
- **Pattern reveal/animazioni**: vedi `src/layouts/Layout.astro`
  (script bottom) e `src/styles/global.css` (CSS rules)

---

## 19. Roadmap del documento

Se aggiungi una pagina nuova e scopri un pattern non descritto qui,
**aggiornalo subito**. Sezioni candidate per crescita futura:

- Analytics (Umami + Vercel): dove vanno gli script, come testare
  l'opt-out per il proprietario
- Internationalization: se mai servirà IT/EN, dove vivono le copy

---

## 20. React Islands

Aggiunto in Sessione 7 (2026-05-03 sera) quando abbiamo portato
`/howwework`. La regola d'oro di Astro: **95% statico, isole React
solo dove serve interattività vera**. Se stai pensando "metto React
così posso usare gli hook", probabilmente non ti serve — Astro +
piccoli `<script>` vanilla copre il 90% dei casi.

### 20.1 Quando usare un'isola React

**Sì, isola React** se hai TUTTO questo:
- Stato condiviso tra componenti che cambia con interazione (es. "se
  clicchi nodo X, gli altri si chiudono")
- Render condizionale complesso che dipende da stato (panel che appare
  in posizione ≠ basata su quale nodo è aperto)
- Layout calcolato dinamicamente (es. SVG paths tra coordinate di DOM
  elements ricalcolati su `resize`)
- Componente parametrico riusabile in più pagine (futuro)

**No React, basta vanilla** se:
- Solo show/hide (`<details>` HTML5 nativo)
- Solo conteggio numerico animato (script TS in `src/scripts/<page>.ts`)
- Interazione locale a singolo elemento (event listener inline)
- Live data fetching (pattern `dashboard-live.ts`)

`/howwework` qualifica come isola perché ha tutti i 4 punti "sì": 3
nodi cliccabili che si influenzano a vicenda, panel con render
condizionale (DetailPanel vs ConnectionPanel), SVG curves calcolate
da DOM rect, e auto-play workflow timer con stop-on-click.

### 20.2 Setup `@astrojs/react`

Una volta sola per tutto il progetto:

```bash
cd web_astro
npm_config_cache=/tmp/npmcache-astro npx astro add react --yes
```

Modifica `astro.config.mjs` (aggiunge `react()` in `integrations`),
`tsconfig.json` (jsx: "react-jsx"), e installa `@astrojs/react` +
`react` + `react-dom`. Reversibile.

### 20.3 Direttive `client:*` — quale scegliere

Sintassi: `<MyComponent client:visible />` nel template Astro.

| Direttiva | Quando | Bundle behavior |
|---|---|---|
| `client:visible` | **Default per noi.** Carica React quando l'isola entra in viewport. | Lazy, ~40kb gz scaricato solo se serve |
| `client:load` | Isola critica above-the-fold che serve hydratata subito | Eager, blocca rendering iniziale |
| `client:idle` | Isola sotto la fold ma da prepare in anticipo | Carica quando il browser è idle |
| `client:only="react"` | Niente SSR, render solo client (uso: componenti che leggono `window`/`localStorage` subito) | No HTML statico nel build |

**Regola**: usa sempre `client:visible` salvo che ci sia un motivo
specifico per scegliere altro. Su `/howwework` l'isola è in §1 ma
spesso fuori dal viewport iniziale (utente vede prima hero), quindi
`client:visible` è ottimale.

### 20.4 Pattern colore: token CSS vs hex inline

**Problema reale**: dentro un componente React puoi usare classi
Tailwind che mappano ai token CSS (`text-pos`, `bg-surface`, ecc.),
ma quando devi applicare un colore **dinamico** via `style={{}}` inline
(es. `borderColor: TEAM[id].color`) Tailwind non funziona — devi
passare un valore literal.

**Soluzione**: parallel hex constant accanto al token name:

```jsx
const TEAM = {
  ceo: {
    accent: "pos",          // for Tailwind classes
    accentHex: "#86efac",   // for inline style props
    // ...
  },
};

// Tailwind utility (palette token, preferred):
<span className="text-pos">CEO</span>

// Inline dynamic (when value is computed):
<div style={{ borderColor: m.accentHex }}>...</div>
```

Sì, è duplicazione. È accettabile perché i colori dinamici nei React
component sono rari, e leggere `getComputedStyle(document.documentElement)
.getPropertyValue('--color-pos')` per ogni render è peggio.

### 20.5 Aggiungere un nuovo design token

Se la pagina React richiede un colore **non** già nello styleguide
(es. CC indigo `#818cf8` su `/howwework`):

1. Aggiungi a `src/styles/global.css` dentro `@theme { ... }`:
   ```css
   --color-cc: #818cf8;
   ```
2. Tailwind v4 lo espone automaticamente come `text-cc`, `bg-cc`,
   `border-cc`, `ring-cc`
3. Documenta in § 5 di questo styleguide
4. Usa il token con preferenza per le classi Tailwind, il `#hex`
   parallel solo dove serve inline style

**Regola**: non aggiungere token "perché magari servirà". Aggiungi
solo quando una pagina lo richiede DAVVERO. Token non usati sono
debito di design system.

### 20.6 Animazioni dentro React: niente `<style>` Astro

Astro scopa gli stili `<style>` dentro `.astro` ai dati `data-astro-cid-*`
delle istanze. Dentro un `.jsx`/`.tsx`, Astro **non vede** il render
React e non può scoping. Quindi:

```jsx
// ❌ Non funziona — Astro non processa questo
function MyComponent() {
  return (
    <>
      <style>{`@keyframes foo { ... }`}</style>
      <div className="animate-[foo_1s_linear]">...</div>
    </>
  );
}

// ✅ Funziona — keyframes globali via plain string injected via <style>
const KEYFRAMES = `
  @keyframes hwwSlideUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

function MyComponent() {
  return (
    <>
      <style>{KEYFRAMES}</style>
      <div style={{ animation: "hwwSlideUp 0.3s ease" }}>...</div>
    </>
  );
}
```

**Prefissa** sempre i nomi keyframe con un namespace della pagina
(`hwwSlideUp`, non `slideUp`) per evitare collisione con classi
globali in `global.css` (che ha già `.reveal` con animazioni).

### 20.7 Mobile fallback con `useIsMobile`

Pattern usato su `/howwework` per scegliere tra org chart desktop
e card stack mobile:

```jsx
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return isMobile;
}
```

**Regole**:
- `useState(false)` come iniziale → su SSR/first paint il render è
  desktop. Subito dopo l'idratazione, `useEffect` aggiorna se
  necessario. Niente flash di contenuto sbagliato perché l'isola è
  `client:visible` e l'utente arriva all'isola scrolling — già
  idratata
- Breakpoint a 767px (`<sm`) per allinearsi a Tailwind `sm` (≥640) /
  `md` (≥768). Per /howwework ho usato 767 perché a 768 (tablet)
  l'org chart entra ancora con margine
- Decidi **prima** se ha senso un fallback statico mobile vs forzare
  il desktop layout responsive. Per interazioni complesse (org chart,
  scaffale 3D di /library) il fallback è quasi sempre meglio

### 20.8 Stop-on-click su auto-play

Pattern carousel: l'utente arriva sulla pagina, il timer avanza. Al
primo click manuale, il timer si ferma (l'utente "ha preso in carico"
il widget).

```jsx
const [autoplayActive, setAutoplayActive] = useState(true);

useEffect(() => {
  if (!autoplayActive) return;
  const id = setInterval(() => { /* advance */ }, 12000);
  return () => clearInterval(id);
}, [autoplayActive]);

const handleStepClick = (i) => {
  setActiveStep(i);
  setAutoplayActive(false);  // <-- stop-on-click
};
```

**Timing**: 12s è il valore deciso su /howwework dopo confronto
5/8/12/15/20s. Sotto 8s = ipnotico. Sopra 15s = "non si muove più".
12s = "respiro" — abbastanza tempo per leggere uno step senza fretta.

### 20.9 Quando l'isola NON deve essere un'isola

Se trovi che l'isola React è il 90% della pagina, **stai sbagliando
direzione**. Quel pezzo dovrebbe essere o:
- Astro statico (se il contenuto non è interattivo)
- Una pagina React app a sé (con SSR off, `output: 'static'` non
  funziona bene per questo)

L'isola è "isola" quando ha attorno terra ferma statica. Su
/howwework, le sezioni Tools/Lessons/Rules/Memory/Replicate
(70% del contenuto della pagina) sono Astro statico. L'isola è solo
§1 The team & the workflow. Se rovesci la proporzione, riconsidera.

---

## 21. Riferimenti incrociati (aggiornato post-sessione 7)

- **Pattern hero**: vedi `src/pages/diary.astro` (più semplice) o
  `src/pages/dashboard.astro` (con counter live)
- **Pattern lista lunga**: vedi `src/pages/diary.astro` (entries) o
  `src/pages/roadmap.astro` (phase con `<details>`)
- **Pattern documento testuale**: vedi `src/pages/blueprint.astro`
  (14 sezioni, tabelle, callout) o `src/pages/howwework.astro`
  (sezioni statiche + 1 isola)
- **Pattern live data**: vedi `src/scripts/dashboard-live.ts` (fetch
  Supabase + render con FIFO + Chart.js plugin)
- **Pattern reveal/animazioni**: vedi `src/layouts/Layout.astro`
  (script bottom) e `src/styles/global.css` (CSS rules)
- **Pattern eccezione visiva pagina** (Fraunces + scaffale 3D): vedi
  `src/pages/library.astro` — eccezione documentata, scoping `.library-shelf`
- **Pattern React island**: vedi `src/components/HowWeWorkInteractive.jsx`
  (usato da `src/pages/howwework.astro` con `client:visible`)

---

*Documento creato 2026-05-03 (Session 54). § 20 React Islands aggiunto
2026-05-04 dopo Sessione 7. Aggiornato dal Claude Code che lavora sul
sito. Quando trovi un pattern utile, aggiungilo. Quando trovi una
lezione dolorosa, scrivila in § 12 prima che svanisca.*
