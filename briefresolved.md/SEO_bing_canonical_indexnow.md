# SEO — Canonical tag + Bing/IndexNow (guida sorgente)

> Convertito da `config/SEO_bing.html` (export Cocoa HTML) e archiviato il 2026-05-29.
> Brief sorgente ricevuto da Max. Stato di esecuzione in coda al documento.

## 1. Canonical tag in Astro

Astro ha il supporto nativo. Nel componente `<head>` (tipicamente in un layout base
tipo `BaseLayout.astro` o `Layout.astro`) si aggiunge:

```astro
---
const canonicalURL = new URL(Astro.url.pathname, Astro.site);
---
<link rel="canonical" href={canonicalURL} />
```

Perché funzioni serve `site` configurata in `astro.config.mjs`:

```js
export default defineConfig({
  site: 'https://bagholderai.lol',
  // ...
})
```

Se `site` è già configurata (lo è, perché la sitemap funziona), basta aggiungere il
`<link>` nel layout: si applica automaticamente a tutte le pagine.

## 2. IndexNow / verifica Bing in Astro

**Step 1 — File chiave** in `public/`:

```
public/
  9c24a4b24e964c1d936ec89875463cb7.txt
```

Contenuto del file (solo la stringa):

```
9c24a4b24e964c1d936ec89875463cb7
```

Tutto ciò che sta in `public/` viene servito staticamente dalla root, quindi sarà
raggiungibile a `https://bagholderai.lol/9c24a4b24e964c1d936ec89875463cb7.txt`.

**Step 2 — Notifiche automatiche** (opzionale): endpoint Astro o step CI/CD post-deploy
che chiama l'API IndexNow a ogni pubblicazione:

```
https://api.indexnow.org/indexnow?url=https://bagholderai.lol/&key=9c24a4b24e964c1d936ec89875463cb7
```

Per ora la cosa più semplice è il file in `public/` + URL Submission manuale.

---

## Stato di esecuzione (sessione 2026-05-29)

- **Canonical tag**: GIÀ PRESENTE prima di questa sessione — `Layout.astro:38` ha
  `<link rel="canonical">` dinamico. Nessuna azione necessaria (brief stale su questo punto).
- **File verifica Bing/IndexNow**: ✅ creato `web_astro/public/9c24a4b24e964c1d936ec89875463cb7.txt`.
- **Notifiche IndexNow automatiche (Step 2)**: non implementate — submission manuale per ora.
