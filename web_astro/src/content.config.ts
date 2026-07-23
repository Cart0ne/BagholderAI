import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

/* ============================================================
   `blog` collection — markdown files under src/content/blog/.
   Posts are listed at /blog and rendered at /blog/<filename>.

   draft: true posts are hidden in production builds but visible
   during `npm run dev` so we can preview before publishing.
   ============================================================ */
const blog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/blog" }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    date: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    summary: z.string().max(220),
    coverSession: z.number().optional(),
    volume: z.number().optional(),
    type: z.enum(["highlight", "lesson"]),
    // author: chi firma il post — convenzione a 2 voci del blog.
    //   "ceo"  = Claude, l'AI CEO (prima persona)
    //   "max"  = Max, co-founder (scritto in italiano e tradotto)
    //   "both" = post a due voci (Max + Claude)
    // Se assente, il template non mostra alcun byline (retro-compatibile
    // con i post già pubblicati). Vedi [...slug].astro per la resa.
    author: z.enum(["max", "ceo", "both"]).optional(),
    // customByline: stringa libera che sovrascrive il byline derivato da
    // `author` (mappa a 2 voci) SOLO per questo post. Serve quando il post
    // non rientra nella convenzione a due voci (es. scritto interamente da
    // Claude e approvato da Max). Se assente, il template usa la mappa
    // `author`, quindi tutti gli altri post restano invariati. Vedi
    // [...slug].astro per la precedenza.
    customByline: z.string().optional(),
    draft: z.boolean().default(false),
    // noRss: true → il post resta sul sito ma viene escluso da /rss.xml.
    // Serve per i post NATI su dev.to e poi ripubblicati qui: senza questo
    // flag dev.to li re-importerebbe come nuovi (il guid bagholderai.lol/...
    // non è mai stato nel suo storico di import). Vedi rss.xml.ts.
    noRss: z.boolean().default(false),
    // faq: lista opzionale di {question, answer}. Se presente, il template
    // blog genera un JSON-LD FAQPage (accanto all'Article) per i rich result
    // di Google e per farsi citare dagli answer engine — GEO. Vedi
    // [...slug].astro. Aggiunto S95a (content plan SEO+GEO).
    faq: z
      .array(z.object({ question: z.string(), answer: z.string() }))
      .optional(),
    // liveFigures: true → il post carica src/scripts/blog-live-figures.ts,
    // che legge i totali live da passive_income (stessa anon-key/RLS di
    // /income) e sovrascrive gli <span data-live-spend>/<span data-live-revenue>
    // col valore corrente. Così una cifra cumulativa nel corpo (es. "€368
    // spesi") non invecchia e resta coerente con /income: quando Max aggiorna
    // i costi da /admin, il post segue. Il fallback statico dentro lo span
    // regge se il fetch fallisce (o per i crawler senza JS). Aggiunto S123.
    liveFigures: z.boolean().default(false),
  }),
});

export const collections = { blog };
