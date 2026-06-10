# SEO_RULES.md — regole operative SEO/GEO del sito

**Owner:** Claude Code (Intern). **Nato:** 2026-06-10 (S101), alla chiusura del caso GSC "Couldn't fetch".
**Scopo:** un posto solo per le regole SEO di `web_astro/`. Da rileggere PRIMA di toccare
sitemap, robots, redirect, meta — e prima di aprire (ri-aprire) indagini su Search Console.
Cap: 15 KB. I dettagli vivono nei file linkati, qui solo le regole e il perché.

---

## 1. Sitemap

- Generata da `@astrojs/sitemap` in `web_astro/astro.config.mjs` → `sitemap-index.xml` + `sitemap-0.xml`.
- **`lastmod` solo con date vere per pagina** (S101): i post prendono `date:` dal frontmatter
  via `serialize()`, `/blog` la data del post più recente, le pagine statiche NESSUN lastmod
  (meglio omettere che mentire). **MAI `lastmod: new Date()` globale**: un timestamp di build
  su tutte le URL a ogni deploy è il pattern che Google documenta come inaffidabile→ignorato.
  (Supera il fix S84, la cui motivazione era legata al "Couldn't fetch" — diagnosi poi superata, vedi §4.)
- `/tf` e `/grid` esclusi via `filter` — control room private, non indicizzare.
- `/sitemap.xml` → 307 a `/sitemap-index.xml` (`vercel.json`).
- I post `draft: true` restano fuori dal build di produzione = fuori sitemap (automatico).

## 2. URL e canonical

- **`trailingSlash: 'never'`** (astro.config) + **`"trailingSlash": false`** (vercel.json → 308
  reale `/diary/`→`/diary`). Decisione S99a (audit Semrush: `/path` e `/path/` contati come URL
  distinti). Non regredire: il build è statico, senza la riga in vercel.json Astro NON redirige a runtime.
- `www` → apex in 308 (gestito dai domain settings Vercel).
- `site: 'https://bagholderai.lol'` in astro.config = origine canonica di sitemap e `<link rel="canonical">`.

## 3. robots.txt + llms.txt

- `robots.txt`: Allow tutto tranne `/tf`, `/grid` (+ varianti `.html`); direttiva
  `Sitemap: https://bagholderai.lol/sitemap-index.xml`. **È questo il canale con cui Google
  scopre la sitemap**, a prescindere dal pannello Sitemaps di GSC.
- `llms.txt` (GEO, S99a): summary orientata agli answer engine; tenere i link interni vivi
  (caso storico: `/about` 404 → corretto in `/howwework`).

## 4. GSC — il caso "Couldn't fetch" (CHIUSO 2026-06-10 — non riaprire da zero)

**Sintomo:** righe sitemap rosse "Couldn't fetch", "Last read" vuoto. Da aprile 2026, 6+ submit, ~2 mesi.

**Diagnosi (2 audit + S101, evidenze):**
- Server-side PERFETTO, verificato due volte (15/05 e 10/06): HTTP 200 + `application/xml`,
  UA Googlebot ok, robots ok, DNS/TLS ok, XML valido, nessun redirect.
- Google indicizza comunque: URL Inspection **live test OK sulle pagine HTML**, `/roadmap` in
  SERP, 381 impressions / pos 8,8 (audit 31/05).
- Vercel Firewall pulito (10/06): Bot Protection **inactive**, 0 custom rules, 0 denied/challenged.

→ **La riga rossa è un artefatto del report Sitemaps di GSC** (failure cached del primo submit +
retry a bassissima priorità sui domini piccoli/nuovi). NON blocca l'indicizzazione.

**Playbook se ricapita (in quest'ordine, niente panico):**
1. Guardare le metriche vere: Indexing→Pages e Performance. Se vivono, il resto è cosmetica.
2. URL Inspection **live test su una pagina HTML** — non sull'XML: sugli XML il live test dà
   spesso "Something went wrong" generico, non è diagnostico.
3. Resubmit con cache-buster **`?v=YYYYMMDD`**: URL mai visto = fetch fresco obbligato; doppia
   funzione di tracciante nei log Vercel (nessun altro conosce quell'URL).
4. Vercel **Observability → Edge Requests**, path `/sitemap-index.xml` — retention Hobby ~1
   giorno: controllare entro 24-48h dal resubmit.
5. Ancora rossa dopo ~1 settimana col dossier pulito → post su Google Search Central community
   (i Product Expert escalano i bug veri) e **STOP energie**: la SEO funziona già.

**Stato:** resubmit tracciante `?v=20260610` eseguito il 10/06. Evidenze complete:
`audits/reports/20260515_audit[A3].md` §3.1 (prima diagnosi) + sessione S101 (chiusura).

## 5. Contenuti / post nuovi

- Checklist per ogni post: `config/SEO_GEO_post_checklist.md`.
- Il frontmatter **`date:` è il lastmod che Google vedrà**: aggiornarla quando si rivede
  sostanzialmente un post (non per typo fix).
- JSON-LD `Article` sempre; `FAQPage` se il post ha `faq:` nel frontmatter (S95a).
- `noRss: true` per i post nati su dev.to e ripubblicati qui (evita re-import del guid).

## 6. Deferred + verifica cadenzata

- Backlog interventi rimandati (Lighthouse 29/05): `config/SEO_deferred.md`.
- La verifica SEO/GSC passa dall'**audit A3 bisettimanale** (dati `scripts/gsc_stats.py` ecc.) —
  la riga sitemap si guarda lì, non ossessivamente.
- Aperto, non urgente: **Bing 54 errori crawl** (31/05) — non spiegati dal firewall (pulito);
  da indagare in un A3.
