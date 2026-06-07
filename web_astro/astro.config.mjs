// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

import sitemap from '@astrojs/sitemap';

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
         not for the public. Google should not index them. */
      filter: (page) => !page.includes('/tf') && !page.includes('/grid'),
      /* <lastmod> on every URL. Build-time Date — refreshed on each
         deploy. Required signal for Google to re-crawl; missing lastmod
         was a contributing factor to the "Couldn't fetch sitemap"
         status reported in Search Console (S84 SEO audit fix). */
      lastmod: new Date(),
    }),
  ],
});