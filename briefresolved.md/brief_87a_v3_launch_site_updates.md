# Brief 87a — Volume 3 Launch: Site Updates + Umami Tracking

**Session:** 87  
**Date:** May 27, 2026  
**Basato su:** PROJECT_STATE.md del 2026-05-26  
**Stima:** <1h, <50 righe di codice per task. CC può procedere direttamente.

---

## Contesto

Volume 3 "From Brain to Eyes" (Sessions 53–82, €4.99) è LIVE su Payhip:  
**https://payhip.com/b/hCWNX**

Il sito va aggiornato per riflettere il lancio + si bundlano 2 migliorie Umami analytics nello stesso commit.

---

## Task 1 — BlogCTA.astro: aggiungere Volume 3

**File:** `web_astro/src/components/BlogCTA.astro`

Aggiungere Volume 3 alla mappa `VOLUMES`:

```
3: {
  title: "From Brain to Eyes",
  url: "https://payhip.com/b/hCWNX"
}
```

Dopo questa modifica, i blog post con `volume: 3` nel frontmatter mostreranno il box verde con CTA diretto al V3. I post senza volume (o con volume non in {1,2,3}) mostreranno il box neutro con link a tutti e tre i volumi — **verificare che il fallback "If this resonated" mostri anche V3 accanto a V1 e V2**.

---

## Task 2 — Pagina /library: aggiungere card Volume 3

**File:** `web_astro/src/pages/library.astro`

Aggiungere una card per Volume 3, stessa struttura di V1 e V2:

- **Titolo:** Volume 3 — From Brain to Eyes
- **Sessioni:** Sessions 53–82
- **Descrizione breve:** "The bots trade. The numbers don't match. And the Board has had enough."
- **Link:** https://payhip.com/b/hCWNX
- **Prezzo:** €4.99

Ordine: V1, V2, V3 (cronologico).

---

## Task 3 — vercel.json: redirect /buy → store

**File:** `web_astro/vercel.json`

Cambiare il redirect `/buy`:

```json
{
  "source": "/buy",
  "destination": "https://payhip.com/BagHolderAI",
  "permanent": false
}
```

Prima puntava a V1 (`/b/a4yMc`). Con 3 volumi, puntare allo store è più sensato.

---

## Task 4 — Pixel Umami nel feed RSS

**File:** il generatore di `rss.xml` (probabilmente in `web_astro/src/pages/rss.xml.ts` o simile — CC verifica)

Aggiungere alla fine del contenuto HTML di ogni `<item>` (dentro `<content:encoded>` o `<description>`) il tag:

```html
<img src="https://cloud.umami.is/p/0nHeF7vMT" width="1" height="1" alt="" style="display:none" />
```

Scopo: tracciare le aperture degli articoli importati su Dev.to via RSS feed. Pixel generico per tutto il feed, non per singolo articolo.

---

## Task 5 — Eventi Umami sui CTA

Aggiungere attributi `data-umami-event` ai seguenti elementi:

| Elemento | File probabile | Attributo |
|----------|---------------|-----------|
| Bottone "Read the blog" in homepage | `index.astro` | `data-umami-event="cta-read-blog"` |
| Bottone "Read the diary" in homepage | `index.astro` | `data-umami-event="cta-read-diary"` |
| Bottone "Live numbers" in homepage | `index.astro` | `data-umami-event="cta-live-numbers"` |
| Link "Library" nel nav | `SiteHeader.astro` | `data-umami-event="nav-library"` |
| Link "FULL DASHBOARD" sotto Live Snapshot | `index.astro` | `data-umami-event="cta-full-dashboard"` |

Solo aggiunta di attributi HTML, zero logica.

---

## Decisioni delegate a CC

- Identificare il file/funzione esatto del generatore RSS (Task 4)
- Posizionamento esatto del pixel nel template RSS (fine del body HTML)
- Verifica che il fallback BlogCTA mostri 3 volumi (Task 1)

## Decisioni che CC DEVE chiedere

- Se la pagina /library ha struttura diversa da quanto descritto (card per volume), fermarsi e chiedere
- Se il generatore RSS non ha un campo `content:encoded`, chiedere prima di modificare `description`

## Output atteso

- BlogCTA.astro con V3 nella mappa + fallback a 3 volumi
- /library con card V3
- vercel.json con redirect /buy → store
- Feed RSS con pixel Umami
- 5 elementi con data-umami-event
- Build verde
- 1 commit, push, Vercel re-deploy

## Vincoli

- NON toccare componenti blog layout, schema, o content collection
- NON toccare stili CSS globali
- NON toccare codice bot, orchestrator, o qualsiasi file Python

## Roadmap impact

Nessuno. Nessun task roadmap impattato.
