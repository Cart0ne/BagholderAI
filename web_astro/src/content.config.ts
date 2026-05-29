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
    draft: z.boolean().default(false),
    // noRss: true → il post resta sul sito ma viene escluso da /rss.xml.
    // Serve per i post NATI su dev.to e poi ripubblicati qui: senza questo
    // flag dev.to li re-importerebbe come nuovi (il guid bagholderai.lol/...
    // non è mai stato nel suo storico di import). Vedi rss.xml.ts.
    noRss: z.boolean().default(false),
  }),
});

export const collections = { blog };
