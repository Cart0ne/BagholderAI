# Report CEO — Sessione 91 (2026-05-29)

**Tema**: SEO / Accessibilità — quick wins sito pubblico (web-only, no bot, no restart)
**Origine**: 2 file droppati da Max in `config/` — guida canonical/Bing + brief Lighthouse del 29/05 (Mobile Performance 81, Accessibilità 87).
**Esito**: SHIPPED + pushato (commit `a943d3c`), deploy Vercel live e verificato.

---

## Cosa è stato fatto

**WP1 — quick wins SEO/A11y**
- File di verifica **Bing/IndexNow** in `public/` → ora online (HTTP 200).
- `title="Advertisement"` sull'iframe a-ads (accessibilità).
- Fix markup `<dl>` malformato in home (il sotto-testo "$500 Grid…" spostato dentro il `<dd>`).
- `aria-label` distinti sui 3 link Payhip (home + library) — prima erano testo identico.
- Redirect `/sitemap.xml` → `/sitemap-index.xml` (prima dava 404; ora 307 → 200).

**WP2 — contrasto WCAG**
- `--color-text-muted` schiarito #5d6680 → #828aa0 (~5,1:1 su sfondo, passa AA anche su testo piccolo). Gerarchia colori preservata.

Build verde, 15 pagine. Canonical tag risultava **già presente** (il brief lo dava come urgente — informazione stale).

---

## Il caso sitemap "Couldn't fetch" su Google — chiuso (non è un bug)

Indagine: la sitemap **non è rotta**. Verificato live, anche fingendosi Googlebot:
`sitemap-index.xml` e `sitemap-0.xml` rispondono 200, XML valido, content-type corretto,
SSL valido, nessun blocco robots. Il "Couldn't fetch" è uno **stato stale/transitorio**
tipico dei domini nuovi (il certificato è del 19/05): Google mostra l'esito dell'ultimo
tentativo, caduto al momento dell'invio prima che DNS/SSL fossero propagati.

**Azioni operative per Max (lato Google Search Console, non codice)**:
- Inviare **solo** `sitemap-index.xml` (non anche `sitemap-0.xml`: l'indice lo include già).
- Verificare che la proprietà sia **Domain property** (o URL-prefix esatto apex).
- Non re-inviare in loop; usare "Richiedi indicizzazione" sulla home e attendere.

Coerente con l'audit Area 3 (A3-S78): stesso pattern già osservato ad aprile.

---

## Bing + IndexNow

- **Bing Webmaster Tools**: già configurato da Max (import da Google Search Console).
- **IndexNow**: chiave online e **testata con successo** (ping home → Bing HTTP 202, api.indexnow.org HTTP 200). Operativo. D'ora in poi, per ogni nuovo blog post: ping a `api.indexnow.org` (notifica tutti i motori in un colpo).
- Beneficio: indicizzazione rapida su Bing/Edge, che alimenta anche la ricerca di ChatGPT — canale alternativo a Google.

---

## Cosa NON è stato fatto (e perché) — tracciato in `config/SEO_deferred.md`

- **WP3 performance mobile** (immagini WebP, self-host font, preconnect Supabase): **saltato**. Lighthouse dà 81 in lab, ma Vercel Speed Insights misura ~96 su utenti reali (RUM) → non urgente.
- **WP4 proxy Binance + header sicurezza**: **rimandato a task dedicato pre-mainnet**. Il proxy Binance cambia come il sito legge i prezzi e va valutato con calma in vista del go-live; la CSP completa romperebbe gli script inline (analytics, font, a-ads).

---

## Note di chiusura

- File sorgente convertiti in markdown pulito e archiviati in `briefresolved.md/SEO_*`.
- ⚠️ **Drift aperto (non bloccante)**: `PROJECT_STATE.md` è a ~47KB, sopra il cap di 40KB (debito ereditato da S89/S90). Ridotto da 49,8KB pur aggiungendo S91, ma per scendere sotto serve una compaction più profonda delle voci storiche §4/§5/§9. Max ha deciso di lasciarlo così per ora → da pianificare come mini-sessione dedicata.

---

## Addendum — Fix RSS re-import dev.to (stessa sessione)

**Problema**: dev.to continuava a re-importare il post *"When Your AI CEO Lies About the Numbers"* come contenuto nuovo. Causa: quel post è **nato su dev.to** e poi ripubblicato sul blog; il suo guid nel nostro feed (`bagholderai.lol/...`) non è nello storico di import di dev.to → trattato come articolo nuovo a ogni fetch.

**Perché non bastava "far corrispondere il guid"**: dev.to riconosce un articolo già importato solo se il guid è nel suo storico RSS. Un articolo creato nativamente su dev.to non ha mai avuto un guid in quello storico → nessun guid che mettiamo lo farebbe dedurre come "già visto".

**Soluzione (shippata, commit `d091728`)**: nuovo flag opzionale `noRss` nello schema blog + filtro nel generatore RSS. Applicato al post incriminato → escluso da `/rss.xml` (feed 4→3 item) ma **resta vivo su `/blog`**. Riutilizzabile per ogni futuro post "nato su dev.to". Build verde.

**Azione Max**: cancellare a mano gli eventuali draft duplicati già creati su dev.to dai re-import passati (CC non può toccare dev.to). Da qui in avanti il re-import si ferma da solo.
