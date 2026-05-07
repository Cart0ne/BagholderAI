# Analytics Stack — Umami + Vercel Web Analytics

Panoramica dei due tool di analytics attivi sul sito, cosa misurano, perché
coesistono, e cosa aspettarsi di scoprire.

## TL;DR

| Tool                 | Misura                          | Può essere bloccato da adblocker? |
|----------------------|---------------------------------|-----------------------------------|
| Umami (cloud)        | Pageviews + **custom events**   | Sì, spesso                        |
| Vercel Web Analytics | Pageviews + referrer + geo      | No (stesso origin)                |

Entrambi girano in parallelo sulle stesse 10 pagine pubbliche. Forniscono
visioni diverse dello stesso traffico — una incompleta-ma-ricca (Umami),
una completa-ma-meno-dettagliata (Vercel).

## Perché due tool

### Umami (da sempre)

Pro:
- **Custom events**: `data-umami-event="buy-click"` sul CTA Payhip,
  `data-umami-event="preview-download"` sul link del PDF preview.
- Gratuito anche nel piano cloud (no self-hosting).
- Dashboard semplice, privacy-friendly, no cookies.

Contro scoperto in sessione 45:
- Lo script `cloud.umami.is/script.js` è **incluso in molte filter-list**
  di adblocker (EasyPrivacy, uBlock Origin defaults, Brave Shields, Safari
  Content Blockers con liste anti-tracking).
- Il nostro pubblico (crypto / AI / dev / built-in-public) ha **altissima
  penetrazione di adblocker**. Stima: 40-60% di blocco.
- Risultato: Umami sotto-conta visitatori e eventi di un fattore
  stimato 2×.

### Vercel Web Analytics (aggiunto in sessione 45)

Pro:
- Lo script è servito da `/_vercel/insights/script.js` — **stesso
  dominio del sito**. Le filter-list di adblocker non possono bloccarlo
  senza bloccare anche il sito stesso.
- Zero configurazione (1 click nel dashboard Vercel per abilitarlo).
- Dashboard nativa con Top Pages, Top Referrers, Countries, Browsers, OS.
- Free tier Hobby: ~2500 eventi/mese, sufficiente.

Contro:
- **Nessun custom event nel free tier.** Solo pageviews, visitors,
  referrer. Per `buy-click` / `preview-download` serve il tier Pro
  (a pagamento) — oppure si tiene Umami.
- Nessun opt-out nativo per il proprietario → risolto via flag custom
  `localStorage['va.disabled']` (vedi analytics-self-exclusion.md).

### Quindi: convivenza

- **Umami** resta per i custom events (anche se sotto-contati).
- **Vercel** aggiunge la verità sui pageview totali (non bloccabili).
- Confronto Umami vs Vercel = stima empirica del tasso di blocco del
  nostro pubblico.

## Il caso che ha innescato il refactor

Evidenza raccolta il 2026-04-23:

- Payhip (dashboard del libro Volume 1): **13 Total Views** nell'ultimo
  mese, tutte marcate come "Direct" (referrer stripped da Safari/mobile).
- Umami custom events nello stesso periodo: **1 `buy-click`** +
  **2 `preview-download`** sulla pagina `/guide`.
- Umami pageviews di `/guide`: **2 visits, 2 unique visitors**.
- Tesi di Max: "l'unica strada per il link Payhip è il nostro sito".

Gap enorme. Ipotesi discusse:

1. **Adblocker bloccano Umami** sulla maggior parte dei visitatori.
   Plausibile: pubblico tech = adblocker diffusi.
2. Alcune views Payhip arrivano da link diretti (Telegram, chat, tweet)
   che bypassano il sito. Contraddetto dai dati "Direct 100%" e
   dall'asserzione di Max.
3. Safari strippa il `Referer` quando si apre Payhip da `target="_blank"`,
   quindi anche click reali dal nostro sito appaiono "Direct" su Payhip.
   Molto probabile.

Ipotesi 1 + 3 insieme spiegano tutto senza richiedere altro traffico.

Se fosse stata solo ipotesi 3, Umami avrebbe comunque visto N visitors
`/guide` con N > 2. Vedendone solo 2, resta forte il sospetto che Umami
stia perdendo molte visite. Vercel Analytics ci darà l'ordine di
grandezza vero.

## Cosa ci aspettiamo di scoprire

Confronto ideale dopo ~1 settimana di Vercel Analytics attivo:

| Metrica                | Umami  | Vercel | Gap implicito (blocco Umami) |
|------------------------|--------|--------|-------------------------------|
| Pageview totali        | N₁     | N₂     | 1 − N₁/N₂                     |
| Unique visitors        | V₁     | V₂     | idem                          |
| Pageview `/guide`      | G₁     | G₂     | idem                          |

Numeri attesi (stima, settembre 2025 audience tech):
- Gap di blocco Umami: 40-65%
- Cioè Umami vede 35-60% del vero traffico
- Vercel vede ~100%

Se il gap reale sarà ≥ 70% → ripensare se vale ancora la pena tenere
Umami, o migrare tutto a Vercel Pro per custom events.

Se il gap sarà ≤ 30% → Umami è più affidabile di quanto temessimo,
nostro pubblico meno adblocker-eavy del previsto.

## File e commit di riferimento

- `docs/analytics-self-exclusion.md` — procedura passo-passo per escludere
  il proprio browser.
- Commit `e23f3d5` (2026-04-23) — self-exclusion flag `va.disabled`.
- Commit `011e7df` (2026-04-23) — tag Vercel Analytics in 10 pagine.
- Commit in roadmap: Phase 10 "Website Restructure & Analytics" in
  v1.32.

## Cosa NON facciamo

- **Non usiamo Google Analytics.** Cookie-heavy, privacy-ostile, contrario
  alla filosofia del progetto.
- **Non self-hostiamo Umami.** Valutato ma scartato per session 45: il
  costo operativo (manutenzione, update, uptime) non giustifica il
  guadagno (sposterebbe solo il punto di blocco dal dominio `umami.is`
  al nostro sottodominio, ma molti adblocker riconoscono il pattern
  dello script Umami indipendentemente dal dominio).
- **Non tracciamo admin.html / tf.html / buy.html.** Sono pagine
  private (admin, tf) o redirect a zero-latenza (buy).

## Cosa potremmo fare in futuro

- **Server-side click redirect** per il link Payhip: invece di un
  `<a href="payhip.com/...">` cliente-lato, un `/go/buy` che registra
  il click in Supabase e fa 302 a Payhip. Adblocker-proof al 100%.
  Costo: ~20 righe in una edge function.
- **UTM parameters** sui link social (Telegram/X/GitHub) per vedere
  quale canale porta più traffico al sito.
- **Upgrade a Vercel Pro** se i custom events diventano critici e il
  traffico non-adblocker non copre abbastanza del vero dato.

Per ora, lo stack Umami+Vercel è sufficiente. Rivalutare a fine
Volume 2 o al primo spike di traffico significativo.
