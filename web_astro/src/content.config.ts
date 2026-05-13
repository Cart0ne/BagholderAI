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
  }),
});

export const collections = { blog };
