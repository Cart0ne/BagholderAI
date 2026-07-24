/* Shared JSON-LD (schema.org) builders.
   Kept in one place so the domain/shape lives in a single source instead
   of being copy-pasted across pages. Pass the returned object straight to
   <Layout jsonLd={...} /> (Layout.astro serializes it into a
   <script type="application/ld+json"> in <head>). */

const SITE = "https://bagholderai.lol";

/* BreadcrumbList for a top-level page: Home › <name>.
   Used on the main sections (library, diary, blueprint, howwework,
   roadmap, dashboard, blog index) so GSC's Breadcrumbs report is
   uniform and the SERP shows a clean trail. Blog *posts* build their own
   3-level breadcrumb inline (Home › Blog › <post>) in [...slug].astro.

   `path` is the page path WITHOUT a trailing slash (e.g. "/library"),
   matching astro.config `trailingSlash: 'never'` so the breadcrumb `item`
   URLs line up with each page's canonical. The home item is the bare
   origin, same as the blog template's breadcrumb. */
export function breadcrumbLd(name: string, path: string) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": SITE },
      { "@type": "ListItem", "position": 2, "name": name, "item": `${SITE}${path}` },
    ],
  };
}
