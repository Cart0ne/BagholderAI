# Brief 75a — Blog Infrastructure (Astro Content Collections)

**Basato su:** PROJECT_STATE.md aggiornato 2026-05-12 (S74b)  
**Autore:** CEO  
**Data:** 2026-05-13  
**Stima:** 2-3 ore  
**Priorità:** non bloccante (nessun gate pre-mainnet). Da eseguire in sessione "frontend pubblico"

---

## Obiettivo

Creare l'infrastruttura blog sul sito Astro (`web_astro/`). Solo plumbing — nessun contenuto. I post verranno scritti in sessioni dedicate successive.

## Contesto

Il sito ha 0 visibilità organica. Il blog serve come funnel gratuito verso i volumi Payhip: 2-3 post selezionati da V1 e V2 (riscritture discorsive, non copia-incolla del diary), più pezzi tematici trasversali. Cadenza: irregolare ("variable reinforcement", come i post X).

## Cosa deve esistere a fine sessione

1. **Content Collection `blog`** in `src/content/blog/` con schema definito in `src/content/config.ts`
2. **Pagina listing `/blog`** — lista dei post dal più recente, design coerente con STYLEGUIDE
3. **Pagina singolo post `/blog/[slug]`** — layout articolo leggibile, con CTA in fondo verso Payhip
4. **Navbar aggiornata** — voce "Blog" in `SiteHeader.astro`
5. **1 post placeholder** di test (lorem o draft reale se disponibile) per verificare che tutto funzioni
6. **STYLEGUIDE.md aggiornato** con sezione blog (pattern, schema, convenzioni)

## Schema post (proposta, CC può adattare)

```typescript
// src/content/config.ts
import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    date: z.date(),
    tags: z.array(z.string()).default([]),
    summary: z.string().max(160),       // meta description + card preview
    coverSession: z.number().optional(), // sessione di riferimento (se diary highlight)
    volume: z.number().optional(),       // 1, 2, 3 — per linkare al volume giusto
    type: z.enum(['highlight', 'lesson']),// diary highlight vs pezzo trasversale
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
```

## Design `/blog` (listing)

- Hero: titolo "Blog." + sottotitolo breve (es. "Selected stories from the development diary. The full story lives in the volumes.")
- Badge: come le altre pagine (pallino verde + metadata)
- Cards post: data + titolo + summary + tag pills + tipo (highlight/lesson). Niente immagini cover — non abbiamo asset e il sito è text-first
- Ordine: cronologico inverso (più recente in cima)
- Se `draft: true`, il post NON appare nella listing (solo in dev)
- Pattern: simile a `/diary` ma con card più ricche (summary visibile, tags)

## Design `/blog/[slug]` (singolo post)

- Layout articolo: `max-w-4xl` come da STYLEGUIDE, prosa leggibile
- Header: titolo + subtitle + data + tags + tipo (badge "From Volume 1" o "Lesson")
- Body: markdown standard (h2, h3, code blocks, blockquote, liste)
- Footer articolo: CTA box con link al volume Payhip corrispondente. Tono: "This story is from Volume 1 — From Zero to Grid. The full diary with all 23 sessions is available for €4.99." + pulsante/link
- Navigazione: link "← Back to blog" in cima o in fondo
- Nessun sistema di commenti, nessuna share button

## Decisioni delegate a CC

- Posizione esatta di "Blog" nella navbar (suggerimento: dopo "Diary", prima di "Blueprint")
- Dettagli CSS delle card nella listing (spaziatura, hover, ecc.)
- Struttura URL: `/blog/titolo-slugificato` (conferma o proponi alternativa)
- Se servono utility Astro aggiuntive (es. `getCollection`, `getEntry`)

## Decisioni che CC DEVE chiedere

- Qualsiasi modifica a pagine esistenti oltre alla navbar
- Aggiunta di dipendenze npm nuove
- Modifiche a `Layout.astro` che impattano tutte le pagine
- Se lo schema proposto non funziona con Content Collections (proponi alternativa)

## Vincoli

- **NON creare post reali** — solo il placeholder di test. I contenuti li scrive il CEO in sessioni dedicate
- **NON toccare** `/diary`, `/dashboard`, o altre pagine oltre a `SiteHeader.astro`
- **Design coerente** con STYLEGUIDE.md (max-w-4xl, px-4 sm:px-6, palette esistente, reveal animations)
- **Nessuna dipendenza nuova** se possibile — Astro Content Collections è built-in
- **Lingua contenuti: inglese** (come tutto il sito pubblico)

## File che verranno toccati (stima)

```
web_astro/
  src/
    content/
      config.ts              ← NUOVO: definizione collection blog
      blog/
        _placeholder.md      ← NUOVO: post di test
    pages/
      blog/
        index.astro          ← NUOVO: listing page
        [...slug].astro      ← NUOVO: dynamic route singolo post
    components/
      SiteHeader.astro       ← MODIFICA: aggiungere voce Blog
      BlogPostCard.astro     ← NUOVO (opzionale): componente card riutilizzabile
      BlogCTA.astro          ← NUOVO (opzionale): componente CTA Payhip
  STYLEGUIDE.md              ← MODIFICA: aggiungere sezione blog
```

## Test checklist

- [ ] `npm run dev` funziona senza errori
- [ ] `/blog` mostra la listing con il post placeholder
- [ ] `/blog/placeholder-slug` mostra il post completo con CTA
- [ ] Post con `draft: true` NON appare in listing
- [ ] Navbar mostra "Blog" e il link funziona
- [ ] Mobile responsive (testare viewport 375px)
- [ ] Build production `npm run build` passa senza errori
- [ ] STYLEGUIDE.md aggiornato con sezione blog

## Roadmap impact

Nessuno. Il blog è infrastruttura marketing, non tocca bot, dashboard, o trading logic. La roadmap sul sito (`roadmap.astro`) potrebbe menzionare il blog come achievement futuro, ma NON in questo brief.

## Piano italiano (per Max)

CC creerà la struttura tecnica per il blog sul sito: una cartella dove mettere i post scritti in markdown, una pagina che li elenca, e una pagina per leggere ogni singolo post. In fondo a ogni post ci sarà un box che invita a comprare il volume completo su Payhip. Per ora nessun contenuto reale — solo l'impalcatura. I post veri li scriviamo noi (CEO) in sessioni future, partendo dai momenti migliori di V1 e V2.
