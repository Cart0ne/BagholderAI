# Report sessione 84 — SEO audit fix (Search Console)

**Data:** 2026-05-24 (pomeriggio, stessa giornata di S83)
**Brief:** [config → ] briefresolved.md/brief_s84_seo_audit_fix.md — SEO Audit Fix: Sitemap + Meta Tags + Indexing (Board-approved)
**Scope sessione:** chiusura findings audit GSC del CEO. Title/description rewrite, sitemap `lastmod`, JSON-LD WebSite+Article, diagnosi "Page with redirect".
**Esito:** SHIPPED. Commit `c89c8cc` pushato su origin/main. Deploy Vercel verificato end-to-end live.

---

## TL;DR — cosa è successo

1. **Title + description riscritti su 8 pagine pubbliche** (index, roadmap, blueprint, diary, howwework, blog/, library, dashboard). Legal (privacy, terms, refund) intatte per brief. Tutte sotto 60 char title + 100-160 char description. OG/Twitter cards auto-aggiornate (Layout deriva dagli stessi props).

2. **JSON-LD `WebSite` su home** con SearchAction. Chiude drift S47: il file `web_astro/src/data/roadmap.ts:434` claimava che questo schema esisteva già "from Brief SEO Fix (2026-04-24)" — `grep` e `curl` sul live HTML hanno smentito. Probabilmente era stato shippato e poi sovrascritto dal redesign S82. Ora c'è davvero.

3. **JSON-LD `Article` su template blog post** (3 post live: an-ai-that-cant-trade, the-day-our-bot-ran-out-of-money, when-your-ai-ceo-lies-about-the-numbers). Include `headline`, `datePublished` ISO 8601, `publisher` con logo, `image`, `keywords` da tags del frontmatter. Auto-generato — ogni post futuro lo eredita gratis.

4. **`lastmod` nel sitemap** via `@astrojs/sitemap` config. Build-time `new Date()`, ogni deploy refresha la data. Output live verificato: `<lastmod>2026-05-24T13:33:56.566Z</lastmod>` su tutti i 14 URL. Era uno dei sintomi del "Couldn't fetch sitemap" GSC.

5. **"Page with redirect" identificato e archiviato come legittimo.** Curl loop sui 14 URL del sitemap → tutti HTTP 200, zero redirect interni. Il redirect che Google segnala viene da `www.bagholderai.lol/` → `bagholderai.lol/` (308 Permanent, gestito da Vercel). È canonicalizzazione SEO standard, non un bug.

6. **Aggiunta architetturale al Layout.** Nuova prop `jsonLd?: Record<string, unknown>` in `web_astro/src/layouts/Layout.astro` che, se passata, emette uno `<script type="application/ld+json">` nel `<head>`. Single injection point riusabile per future schemi (Organization, FAQPage, ecc.).

---

## Verifica live post-deploy

Build locale (1.81s, 14 pagine) + deploy Vercel auto. Tre check curl sul prod:

| Endpoint | Atteso | Esito |
|----------|--------|-------|
| `bagholderai.lol/sitemap-0.xml` | `<lastmod>` ISO 8601 su ogni URL | ✓ presente, build-time del deploy |
| `bagholderai.lol/` | new title + WebSite/Organization/SearchAction JSON-LD | ✓ tutti e 3 i `@type` presenti |
| `bagholderai.lol/blog/an-ai-that-cant-trade/` | Article JSON-LD con headline | ✓ presente |
| `bagholderai.lol/roadmap/` | new title | ✓ "BagHolderAI Roadmap: From Grid Bot to 5-Brain System" |

---

## Drift istruzioni rilevato (chiuso in-sessione)

Il brief affermava: *"The home page already has WebSite schema (from Brief SEO Fix, S47)."* Falso. Per CLAUDE.md §[0] questa è proprio la situazione da flaggare prima di scrivere codice basato su istruzioni stale. Max ha autorizzato di chiudere il drift come parte di S84 invece di farne un brief separato. Operazione: 0 codice trading, 5 minuti netti, JSON-LD aggiunto via la stessa prop `jsonLd` del Layout (riusabile gratis).

Roadmap.ts riga 434 sarà tecnicamente onesta a partire da S84 — non rinominata, non corretta nel testo (è storica), ma ora il claim corrisponde finalmente a realtà.

---

## Decisioni delegate (decise da CC, no Board input)

| Decisione | Scelta | Razionale | Fallback |
|-----------|--------|-----------|----------|
| Where to define meta tags | `<Layout>` props (già esistente) | Pattern coerente con il resto del sito, single-edit per pagina aggiorna anche OG/Twitter | n/a |
| `lastmod` implementazione | globale `new Date()` a build time, NON per-page via `serialize` | Minimo intervento, ogni deploy refresha la data, copre il problema GSC "Couldn't fetch" | Se Google segnalerà blog post con lastmod stale, aggiungere `serialize` callback per usare `post.data.date` |
| JSON-LD injection method | Prop riusabile `jsonLd?` nel Layout (Opzione B di 2) | Single injection point in `<head>`, evita duplicazione, prepara terreno per Organization/FAQ futuri | n/a |
| "80+ sessions" invece di "82+" (brief) | arrotondare in difetto | Siamo a S84 ma usare un numero conservativo evita figuracce se qualcuno re-fetcha cache pre-S82 | Bump a "85+" tra ~5 sessioni |
| Title/description char limits | Tutti sotto 60/160. Tutti aderenti al brief con micro-aggiustamenti per coerenza tono (es. aggiunte "automated", "Binance Testnet", "fully transparent") | Brief autorizzava CC ad adjust per char limits | n/a |

---

## Cosa NON è stato fatto

- **`serialize` per per-page blog lastmod.** Brief permetteva implementazione globale o per-page; ho preso globale per minimo intervento. Se Google si lamenterà di lastmod identico su blog post pubblicati in date diverse, aggiungiamo `serialize` callback (~15 min).
- **Backfill JSON-LD `Article` retroattivo nei MD.** Non serve — il template `blog/[...slug].astro` lo genera da frontmatter esistente.
- **Aggiornamento `roadmap.ts:434`.** Il testo storico resta com'era; ora però è finalmente vero.
- **Test/staging URL inspection.** Le azioni manuali in Search Console le farà Max post-report.

---

## Action richieste a Max (post-deploy, manuale)

Dal brief, punti 2-4:

1. **Search Console → Sitemaps**: re-submit `https://bagholderai.lol/sitemap-0.xml` (NON l'index file — bypass dell'index "Couldn't fetch" status).
2. **URL Inspection tool**: richiedere indexing su top 5 pagine (priorità: home, roadmap, blueprint, diary, blog homepage).
3. **Check CTR tra 7-14 giorni** in Search Console → Performance. Baseline pre-fix: 0 clicks / 256 impressions / position 10.7. Aspettative: position dovrebbe migliorare (1-2 punti) con il nuovo keyword targeting; CTR dovrebbe finalmente diventare > 0% sui top performer (roadmap, blueprint, diary).
4. **Opzionale**: dopo il primo crawl post-fix, verificare in Search Console → Enhancements se compaiono "Articles" detected (i nuovi JSON-LD) — segnale che lo schema è valid e indicizzato.

---

## Roadmap impact

**Nessuno.** Marketing/SEO only, zero touch su bot architecture o sequenza go-live. Brief Roadmap impact: "None."

---

## Audit cadenza (segnalazione automatica fine sessione, CLAUDE.md §[1])

Conteggio sui file `audits/audit_report_*.md`:

- **Area 1** (tecnica, cadenza 30gg): ultimo 2026-05-07 → 17gg → entro cadenza ✓ (scade 2026-06-06)
- **Area 2** (coerenza progetto, cadenza 90gg o fine-volume): **mai eseguito** → ⚠️ DOVUTO da sempre, già flaggato in S78 fase 2 + S79 + S80 + S80a + S81 + S83. Finestra utile: 7-10gg osservazione Sherpa Sprint 2 (~29 maggio - 1 giugno).
- **Area 3** (strategy & marketing, cadenza 90gg): ultimo 2026-05-15 → 9gg → entro cadenza ✓ CON RISERVE (vedi report A3-S78 raccomandazioni §5). Quest'audit ha originato il brief S84 (findings GSC), che oggi chiude le raccomandazioni "fix 5min zero-codice" + ne aggiunge di nuove (rewrite meta + JSON-LD).

**Proposta:** quando avvii Area 2 audit (proponibile a breve), include nel brief un check di coerenza retroattiva su quanto S84 dice vs cosa è effettivamente live (5min, low-effort, alto valore di precedente).

---

## Footnote

Sessione molto breve: ~35 minuti dal git pull al push verificato. Brief chiaro, scope chirurgico, decisioni delegate pre-autorizzate. Drift S47 chiuso in extra senza brief separato grazie a Board ok in-sessione.
