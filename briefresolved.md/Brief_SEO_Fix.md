# Brief — SEO Fix (pre-launch HN)

**Priorità:** Alta (blocker per lancio Show HN previsto domani)
**Tempo stimato:** 30–45 min
**Ramo:** main (push diretto come da prassi)

---

## Contesto

Il sito **bagholderai.lol** non è attualmente indicizzato da Google. Cercando `site:bagholderai.lol` o "bagholderai" come keyword non escono risultati. Veniamo oscurati da una newsletter Substack non correlata che si chiama "Bagholder".

Stiamo per lanciare un Show HN che potrebbe portare 2–5k visitatori in 24h. Senza meta tag e Open Graph corretti:
- Il post HN apparirà senza preview card decente
- Il traffico long-tail post-picco sarà perso (nessuno potrà ritrovarci tramite ricerca organica nelle settimane successive)

Questo brief è infrastruttura SEO base, va fatto **prima** del lancio.

---

## Obiettivo

Dopo questo brief, il sito deve avere:
1. `sitemap.xml` valido e raggiungibile
2. `robots.txt` che permette indicizzazione e punta al sitemap
3. Meta tag base (title, description, canonical) su tutte le pagine pubbliche
4. Open Graph tags (per anteprime su X, HN, Reddit, Slack)
5. Twitter Cards
6. Una `og:image` 1200x630 disponibile

---

## Task — esecuzione

### Step 0 — Verifica framework

Prima di iniziare, ispeziona la struttura del repo per capire il framework:
- Se Next.js (App Router): meta tag in `app/layout.tsx` + `app/[page]/page.tsx` (function `generateMetadata` o export `metadata`)
- Se Next.js (Pages Router): in `pages/_document.tsx` + `<Head>` per pagina
- Se Astro: in `<head>` di `Layout.astro`
- Se HTML statico: direttamente nei file `.html`

Adatta gli esempi sotto al framework effettivo.

---

### Step 1 — `robots.txt`

Crea/aggiorna `/public/robots.txt` (o equivalente per il framework):

```
User-agent: *
Allow: /

Sitemap: https://bagholderai.lol/sitemap.xml
```

**Test:** `curl https://bagholderai.lol/robots.txt` deve restituire il contenuto sopra.

---

### Step 2 — `sitemap.xml`

Crea `/public/sitemap.xml` con tutte le pagine pubbliche. Pagine note (verifica che esistano):
- `/` (home)
- `/buy`
- `/guide`
- `/diary` (e singole entry se esistono come URL distinti)
- `/howwework`
- `/roadmap` (se esposto pubblicamente)

Esempio minimo:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://bagholderai.lol/</loc>
    <lastmod>2026-04-24</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://bagholderai.lol/buy</loc>
    <lastmod>2026-04-24</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- ripeti per ogni pagina pubblica -->
</urlset>
```

**Nota:** se Next.js, valuta `app/sitemap.ts` con generazione dinamica — più manutenibile. Se preferisci statico, va bene.

**Test:** `curl https://bagholderai.lol/sitemap.xml` deve restituire XML valido.

---

### Step 3 — Meta tags base (per ogni pagina)

Ogni pagina pubblica deve avere:

```html
<head>
  <title>[Titolo pagina-specifico] — BagHolderAI</title>
  <meta name="description" content="[Descrizione 150–160 caratteri, page-specific]">
  <link rel="canonical" href="https://bagholderai.lol/[path]">
  <meta name="robots" content="index, follow">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
```

**Titoli/descrizioni suggeriti per pagina:**

| Pagina | Title | Description |
|--------|-------|-------------|
| `/` | BagHolderAI — An AI runs a crypto trading startup. In public. | An architect with no coding skills lets Claude run a real crypto trading startup. Live diary, public dashboard, every mistake documented. |
| `/buy` | Volume 1: From Zero to Grid — BagHolderAI | The book that documents the first 23 sessions of an AI-run trading startup. €4.99. Every decision, every bug, every loss. |
| `/guide` | How to follow the experiment — BagHolderAI | Quick guide to the BagHolderAI project: what it is, what to read first, how to follow updates. |
| `/diary` | Development Diary — BagHolderAI | Session-by-session log of decisions made by an AI CEO running a crypto trading startup. |
| `/howwework` | How we work — BagHolderAI | The three-role setup: AI CEO (Claude), AI intern (Claude Code), human co-founder (veto power). |

Adatta se i titoli o i path effettivi sono diversi.

---

### Step 4 — Open Graph tags

Nel `<head>` di ogni pagina, aggiungi:

```html
<meta property="og:type" content="website">
<meta property="og:site_name" content="BagHolderAI">
<meta property="og:title" content="[stesso del <title>]">
<meta property="og:description" content="[stessa della meta description]">
<meta property="og:url" content="https://bagholderai.lol/[path]">
<meta property="og:image" content="https://bagholderai.lol/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_US">
```

---

### Step 5 — Twitter Cards

```html
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@BagHolderAI">
<meta name="twitter:title" content="[stesso di og:title]">
<meta name="twitter:description" content="[stessa di og:description]">
<meta name="twitter:image" content="https://bagholderai.lol/og-image.png">
```

---

### Step 6 — `og-image.png` (1200×630)

Serve una immagine 1200×630 px in `/public/og-image.png`.

**Opzione veloce:** usa la copertina libro Volume 1 con padding/letterbox per arrivare a 1200×630, sfondo nero o grigio scuro.

**Opzione migliore (se hai 10 min):** card semplice con:
- Sfondo: nero o grigio scuro (#0a0a0a)
- Testo grande bianco: "BagHolderAI"
- Testo piccolo sotto: "An AI runs a crypto trading startup. In public."
- URL piccolo in basso: "bagholderai.lol"

Se non hai tool grafici, puoi generare con HTML+CSS e screenshot, oppure usare una libreria tipo `@vercel/og` se siamo su Next.js (genera al volo da JSX, una manna).

**Nota Max:** se preferisci, posso passarti un brief separato per generare og-image.png con un semplice tool — fammi sapere.

---

### Step 7 — JSON-LD structured data (optional ma consigliato)

Nella home, aggiungi nello `<head>`:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "BagHolderAI",
  "url": "https://bagholderai.lol",
  "description": "An architect with no coding skills lets Claude run a real crypto trading startup. Live diary, public dashboard, every mistake documented.",
  "author": {
    "@type": "Organization",
    "name": "BagHolderAI"
  }
}
</script>
```

---

## Test checklist

Dopo deploy, verificare in ordine:

- [ ] `curl https://bagholderai.lol/robots.txt` → contenuto corretto
- [ ] `curl https://bagholderai.lol/sitemap.xml` → XML valido
- [ ] `curl -I https://bagholderai.lol/og-image.png` → 200 OK
- [ ] Apri https://bagholderai.lol e ispeziona `<head>` con DevTools → tutti i meta tag presenti
- [ ] Test preview Open Graph: paste URL su https://www.opengraph.xyz/ → deve mostrare card corretta
- [ ] Test preview Twitter Card: https://cards-dev.twitter.com/validator (se ancora attivo) o paste su X in modalità draft
- [ ] Validare sitemap: https://www.xml-sitemaps.com/validate-xml-sitemap.html

---

## Follow-up manuale (per Max, post-deploy)

Questi step richiedono accesso account, non li può fare CC:

1. **Google Search Console**: aggiungere proprietà `bagholderai.lol`, verificare ownership (DNS o meta tag), submit del sitemap
2. **Bing Webmaster Tools**: stesso procedimento (meno traffico ma 5 min di lavoro)
3. **Indicizzazione richiesta**: in GSC, inspect URL `https://bagholderai.lol/` → Request Indexing

I primi indicizzati appaiono in 24–72h dopo questi step.

---

## Commit message suggerito

```
feat(seo): add sitemap, robots.txt, meta tags, OG/Twitter cards

- Create /public/sitemap.xml with all public pages
- Create /public/robots.txt allowing all + sitemap reference
- Add page-specific title/description/canonical to all pages
- Add Open Graph + Twitter Card meta tags
- Create og-image.png (1200x630) for social previews
- Add JSON-LD WebSite schema on home

Pre-launch SEO baseline before Show HN announcement.
```

---

## Note finali

- Non spaccare niente: tutte queste modifiche sono additive (meta tags, file statici nuovi). Zero rischio di regressione su funzionalità esistenti.
- Se trovi qualcosa di strano nella struttura del sito durante l'esecuzione (es. pagine duplicate, redirect malformati, URL canonical sbagliati), **segnalalo nel commit message ma non risolvere senza chiedere** — non è scope di questo brief.
- Se il framework richiede pattern diversi da quelli sopra (es. Astro ha `astro:content` per metadata, Next.js App Router preferisce `generateMetadata`), adatta liberamente. Gli esempi sono indicativi.
