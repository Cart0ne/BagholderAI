# SEO / Performance — interventi RIMANDATI (decisi il 2026-05-29)

Questo file traccia gli interventi del brief Lighthouse (29 mag 2026) che abbiamo
**consapevolmente deciso di NON fare** in sessione, e perché. Quando si riprende il
tema SEO/performance, partire da qui.

Brief sorgente completo: `briefresolved.md/SEO_lighthouse_verifica.md`.
Cosa è stato FATTO in questa sessione: WP1 (quick wins) + WP2 (contrasto) — vedi sotto.

---

## ⏸️ WP3 — Performance mobile — SALTATO

**Perché**: Lighthouse dà Mobile Performance 81, ma è un test sintetico (lab) su una
singola run simulata. Vercel Speed Insights — che misura utenti reali (RUM) — riporta
~96 su mobile. Con dati reali a 96, l'ottimizzazione non è urgente. Si rivaluta se il
punteggio RUM scende o se cresce il traffico mobile.

Item da affrontare quando si riprende (in ordine di impatto):

- **3.1 Immagini cover → WebP/AVIF + dimensioni** (~211 KiB). `cover_vol*_square.jpg`
  (600×451, mostrate 378×378) servite come `<img loading="lazy">` senza `width/height`/`srcset`
  in `index.astro` e come `background-image` in `library.astro`.
  Usare `astro:assets` `<Image>`/`<Picture>`.
  *Nota*: queste cover sono sotto la piega, NON sono l'LCP → guadagno in banda, non in LCP.

- **3.2 Preconnect Supabase + caricamento dati**. `<link rel="preconnect"
  href="https://pxdhtmqfwjwjhtcoacsn.supabase.co" crossorigin>` in `Layout.astro`.
  *Nota*: le ~13 query sono già client-side best-effort con fallback mock → non bloccano
  il primo paint. Il preconnect aiuta solo a popolare i dati live prima.
  Idea più grossa: accorpare le 13 query in una sola RPC/view Supabase (refactor consistente).

- **3.3 Font Google render-blocking** (~750 ms). Inter + JetBrains Mono da
  `fonts.googleapis.com` (`Layout.astro:73-77`). Self-hosting woff2 in `public/` +
  `@font-face` con `font-display: swap` + `preload`. Migliora LCP e privacy.

- **3.4 Animare `transform: scaleX()` invece di `width`** sulla barra losses
  (`global.css:291`, aggiornata da `live-stats.ts:222`).
  *Nota*: CLS è già 0 e TBT 0ms → impatto reale minimo. Priorità bassa.

---

## ⏸️ WP4 — Proxy Binance + Header di sicurezza — RIMANDATO (task dedicato pre-mainnet)

**Perché**: tocca config Vercel e architettura delle chiamate. Il proxy Binance in
particolare va valutato con calma in vista del go-live mainnet (cambia il modo in cui
il sito legge i prezzi). Da fare come task dedicato, non "al volo".

- **4.1 Proxy Binance**. La chiamata `api.binance.com/api/v3/ticker/price` è client-side
  (`pnl-canonical.ts:198`) → bloccata da CORS, errore console `ERR_FAILED`.
  Soluzione: instradare via endpoint server (Astro API route o Vercel edge function).
  Rimuove l'errore e rende affidabile il prezzo spot in dashboard.

- **4.2 Header di sicurezza** (in `vercel.json` sezione `headers`):
  - Facili e sicuri: `X-Frame-Options`/`frame-ancestors`, COOP, upgrade HSTS con
    `includeSubDomains; preload` (HSTS base già presente).
  - **CSP**: ⚠️ una Content-Security-Policy stretta ROMPEREBBE gli script inline esistenti
    (Umami, Vercel Analytics/Speed Insights, font Google, iframe a-ads). NON farla "al volo":
    o task dedicato con test, o si lascia stare.

---

## ✅ Cosa è stato FATTO il 2026-05-29 (per contesto)

- File verifica Bing/IndexNow: `web_astro/public/9c24a4b24e964c1d936ec89875463cb7.txt`.
- iframe a-ads `title="Advertisement"`.
- Fix markup `<dl>` (index.astro).
- aria-label distinti sui 3 link Payhip (index.astro + library.astro).
- Contrasto: `--color-text-muted` #5d6680 → #828aa0 (~5,1:1).
- Redirect `/sitemap.xml` → `/sitemap-index.xml` (vercel.json).

## Nota sitemap "Couldn't fetch" (Google Search Console)
La sitemap NON è rotta: `sitemap-index.xml` e `sitemap-0.xml` rispondono 200/XML valido
anche a Googlebot, SSL ok. Il "Couldn't fetch" è uno stato stale/transitorio tipico dei
domini nuovi. Azioni operative (non codice): in GSC inviare SOLO `sitemap-index.xml`,
verificare che la proprietà sia Domain property (o URL-prefix esatto `https://bagholderai.lol`),
non re-inviare in loop, usare "Richiedi indicizzazione" sulla home e attendere.
