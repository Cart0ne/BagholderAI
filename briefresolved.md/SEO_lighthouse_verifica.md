# Brief di ottimizzazione — bagholderai.lol (report Lighthouse)

> Convertito da `config/SEO_verifica.md` (in realtà un file RTF) e archiviato il 2026-05-29.
> Brief sorgente ricevuto da Max. Stato di esecuzione in coda al documento.

## Contesto

Sito Astro + Tailwind, dati live da Supabase + Binance, analytics Umami, ad da a-ads.
Report Lighthouse del 29 mag 2026 (Lighthouse 13.3.0).

Punteggi attuali:

| Categoria      | Desktop | Mobile |
|----------------|---------|--------|
| Prestazioni    | 99      | 81     |
| Accessibilità  | 87      | 87     |
| Best Practice  | 96      | 96     |
| SEO            | 100     | 100    |

Metriche mobile: FCP 3,0s · LCP 3,8s · TBT 0ms · CLS 0 · Speed Index 4,5s
Obiettivo: Mobile Performance >90 e Accessibilità >95 senza regressioni.

---

## 1. Performance (priorità mobile)

### 1.1 Ottimizzare le immagini cover — ~211 KiB risparmiabili (ALTA)
- `cover_vol1/2/3_square.jpg` servite come JPG, dimensioni reali 600x451 ma visualizzate a 378x378.
- Azioni: convertire in WebP/AVIF (o usare `<Image>` / `astro:assets`); servire dimensioni
  corrette + `srcset`/`sizes`; verificare se la cover above-the-fold deve restare `loading="lazy"`
  (se è LCP, togliere e usare `fetchpriority="high"`).

### 1.2 Ridurre la catena di richieste critiche / LCP (ALTA)
- LCP mobile dominato dal "render delay" (2340 ms) — l'h1 attende molte chiamate.
- ~13 chiamate Supabase partono in cascata, ~950-1167 ms ciascuna.
- Azioni: `<link rel="preconnect">` verso `https://pxdhtmqfwjwjhtcoacsn.supabase.co`
  (risparmio LCP ~300 ms); valutare idratazione differita (`client:idle`/`client:visible`);
  accorpare le query in una sola RPC/view.

### 1.3 Richieste che bloccano il rendering
- `Layout.*.css` (10,7 KiB, 320 ms) e Google Fonts CSS (750 ms).
- Azioni: inline del CSS critico above-the-fold; font con `display=swap` + `preload` woff2;
  valutare self-hosting dei font.

### 1.4 Animazione non composita (impatto CLS)
- `#bot-grid-losses-bar` anima `width` → non compositabile.
- Azione: animare con `transform: scaleX()`.

---

## 2. Accessibilità (87 → target >95)

### 2.1 Contrasto colori insufficiente (ALTA)
Testi a basso contrasto: badge "LIVE · BAGHOLDERAI.LOL", header, "LIVE SNAPSHOT", label/valori
del pannello stats (ORDERS, TOTAL P&L, DAYS RUNNING, BUDGET, TODAY P&L, TODAY TRADES, "(Tier 1-2)").
- Azione: aumentare contrasto di `text-text-muted`/`text-text-dim` fino a ≥4,5:1 (≥3:1 testo grande).

### 2.2 Markup `<dl>` non corretto
- Il `<dl>` contiene un `<div>` ("$500 Grid · $100 TF (Tier 1-2)") che rompe la sequenza dt/dd.
- Azione: ristrutturare così che `<dl>` contenga solo coppie `<dt>`/`<dd>`.

### 2.3 iframe senza title
- `<iframe data-aa="2431743" ...>` (banner a-ads) privo di `title`.
- Azione: aggiungere `title="Advertisement"`.

---

## 3. Best Practice (96)

### 3.1 Errore console CORS (Binance)
- Chiamata a `api.binance.com/api/v3/ticker/price` bloccata da CORS → `net::ERR_FAILED`.
- Azione: instradare via proxy/edge function lato server.

### 3.2 Header di sicurezza mancanti
- CSP, HSTS (`includeSubDomains`+`preload`), COOP, X-Frame-Options/`frame-ancestors`, Trusted Types.

---

## 4. SEO (link identici — non penalizzante ma da sistemare)
- I tre link "Get on Payhip →" (v1/v2/v3) hanno testo identico ma destinazioni diverse.
- Azione: differenziare il testo o aggiungere `aria-label` distinti.

---

## Ordine di esecuzione suggerito (dal brief)
1. Immagini WebP/AVIF + sizing (1.1).
2. Preconnect Supabase + idratazione differita (1.2).
3. Contrasto colori (2.1) + fix `<dl>` (2.2) + iframe title (2.3).
4. Header di sicurezza (3.2) e proxy Binance (3.1).
5. Animazione transform (1.4) e link Payhip (4).

## Note di verifica
- Ri-eseguire Lighthouse mobile dopo ogni gruppo di modifiche.
- Attenzione a non introdurre CLS togliendo il lazy-load (riservare spazio con width/height).

---

## Stato di esecuzione (sessione 2026-05-29)

**FATTO** (WP1 + WP2):
- 2.2 fix `<dl>` (index.astro) — il sotto-testo "$500 Grid…" spostato dentro il `<dd>`.
- 2.3 iframe `title="Advertisement"` (SiteFooter.astro).
- 4. aria-label distinti sui link Payhip (index.astro + library.astro).
- 2.1 contrasto: `--color-text-muted` schiarito #5d6680 → #828aa0 (~5,1:1, passa AA testo piccolo).
- (extra non nel brief) redirect `/sitemap.xml` → `/sitemap-index.xml` in vercel.json.
- File verifica Bing creato in public/.

**NON FATTO** — vedi `config/SEO_deferred.md`:
- WP3 performance mobile (1.1, 1.2, 1.3, 1.4) — saltato (Vercel RUM ~96, non urgente).
- WP4 proxy Binance (3.1) + header sicurezza (3.2) — rimandato a task dedicato pre-mainnet.
