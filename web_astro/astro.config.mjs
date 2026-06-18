// @ts-check
import { defineConfig } from 'astro/config';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

import sitemap from '@astrojs/sitemap';

/* Per-page <lastmod> for the sitemap: real dates from each post's
   frontmatter (`date:`), read at config time — astro:content is not
   available here, and the YYYY-MM-DD shape is guaranteed by the blog
   collection schema (z.coerce.date). A post whose date doesn't match
   simply gets no lastmod: omission is fail-safe, a wrong date is not. */
const BLOG_DIR = new URL('./src/content/blog/', import.meta.url);
const blogLastmod = new Map(
  readdirSync(fileURLToPath(BLOG_DIR))
    .filter((f) => f.endsWith('.md'))
    .flatMap((f) => {
      const m = readFileSync(fileURLToPath(new URL(f, BLOG_DIR)), 'utf8')
        .match(/^date:\s*["']?(\d{4}-\d{2}-\d{2})/m);
      return m ? [[f.replace(/\.md$/, ''), m[1]]] : [];
    })
);
const newestPostDate = [...blogLastmod.values()].sort().at(-1);

// https://astro.build/config
export default defineConfig({
  /* Canonical origin — used by @astrojs/sitemap to emit absolute
     URLs in sitemap.xml, and by Astro's `Astro.url` for canonical
     <link> tags. Must match the production domain. */
  site: 'https://bagholderai.lol',

  /* Canonical URLs without a trailing slash. Keeps @astrojs/sitemap and
     the <link rel="canonical"> consistent (no /diary vs /diary/ split).
     NOTE: this is a static build (no Vercel adapter) so Astro itself does
     NOT redirect at runtime — the production 308 /diary/ -> /diary is done
     by Vercel via "trailingSlash": false in vercel.json. (S99a SEO fix) */
  trailingSlash: 'never',

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [
    react(),
    sitemap({
      /* Exclude operative control rooms — they're for Max + the CEO,
         not for the public. Google should not index them. (/income was
         published in S106a — it's in the sitemap now.) */
      filter: (page) =>
        !page.includes('/tf') &&
        !page.includes('/grid'),
      /* Honest per-page <lastmod> (2026-06-10, supersedes the S84 global
         `lastmod: new Date()`): a build timestamp on EVERY url at EVERY
         deploy is the pattern Google documents as unreliable-and-ignored.
         The S84 rationale ("missing lastmod contributed to GSC Couldn't
         fetch") was retired on 2026-06-10: that status was a cached UI
         failure in GSC, unrelated to sitemap content — see
         audits/reports/20260515_audit[A3].md §3.1. Blog posts get their
         frontmatter date, /blog the newest post date, static pages none. */
      serialize(item) {
        const path = new URL(item.url).pathname;
        if (path === '/blog' && newestPostDate) item.lastmod = newestPostDate;
        const slug = path.match(/^\/blog\/([^/]+)$/)?.[1];
        if (slug && blogLastmod.has(slug)) item.lastmod = blogLastmod.get(slug);
        return item;
      },
    }),
  ],
});