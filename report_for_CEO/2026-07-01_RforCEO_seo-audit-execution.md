# Mini-report CEO — SEO audit execution

- **Data:** 2026-07-01
- **Autore:** CC (Claude Code)
- **Brief sorgente:** dossier `audits/SEO_Audit/` (SEO audit del 2026-07-01, prodotto dal CEO) — gitignored via `.gitignore:62 audits/*`
- **Commit:** `ce98be2` (pushato su `main`, deploy Vercel automatico)
- **Scope:** implementare gli item azionabili e NON-duplicati dell'audit sul repo `web_astro`

---

## Executive summary

Shippati i 4 blocchi richiesti + il fix meta-description da Ahrefs, ma **de-duplicati**: circa metà dei "❌ Fail" dell'audit erano **già in produzione** da sessioni passate (Article/WebSite schema S84, FAQPage S95a, baseline server-rendered di diary/dashboard). Ho implementato solo ciò che mancava davvero. On-page ora è completo; il vero tetto resta **backlink + indicizzazione**, che è leva di distribuzione, non di codice.

## Cosa è live ora

- **Pillar page** `/blog/can-an-ai-run-a-company` — "Can an AI Actually Run a Company?" (Article + FAQPage + BreadcrumbList, firma *Max & Claude*). Datata oggi → **auto-featured come "Latest" in home** e presente nel *Keep reading* degli altri post (hub-and-spoke automatico). È la scommessa di ranking sul cluster **AI-autonomy** (quasi zero competizione), non sul saturo "crypto trading bot".
- **Schema Organization** in home: nodo standalone con **logo quadrato (180×180) + `sameAs`** (X, GitHub, Telegram, Buy Me a Coffee), referenziato dal `WebSite` via `@id` → segnale Knowledge Graph. Era l'unico pezzo di schema genuinamente mancante.
- **BreadcrumbList** aggiunto all'Article schema di **tutti** i post.
- **Meta description (Ahrefs Site Audit):** 16 pagine "too long" portate ≤160 char front-loadando il gancio; `/terms` e `/privacy` "too short" estese. Issue azzerato.
- **Diary fallback** rinfrescato: era fermo al 27 mag (S86–88) → ora S111–S113 con **dati reali da Supabase**, così l'HTML crawlabile pre-idratazione non è più stale.
- **Alt-text** cover volumi arricchito (es. "From Zero to Grid — BagHolderAI Volume 1 ebook cover").

## ⚠️ Il finding strategico

**~metà dei "❌ Fail" dell'audit erano già shippati.** L'audit è stato prodotto con un **crawl del sito live senza accesso al repo**, quindi non ha visto il JSON-LD server-side (Article/FAQPage) né i fallback statici di diary/dashboard — che ha classificato come "empty shell / critical" pur essendo già baseline server-rendered.

**Azione per il CEO:** i prossimi audit tecnici vanno fatti girare **sul repo** (o almeno su `view-source` / Rich Results Test dell'HTML buildato), non solo sul sito percepito, per non ri-prescrivere lavoro già fatto. Ho deliberatamente **non copiato** i 3 componenti `schema/` del dossier per non duplicare schema esistente.

## Verifica tecnica

- `npm run build` verde, 24 pagine.
- Confermato nell'HTML statico buildato: `Organization`+`sameAs`+`logo` in home; `Article`+`BreadcrumbList`+`FAQPage` nel pillar; fallback diary aggiornato; alt cover.
- Tutte le 17 meta description ricontate ≤160 char.

## Il vero collo di bottiglia (invariato)

On-page è ora eccellente e completo. Il tetto resta **autorità (backlink) + indicizzazione** (`site:` indicizza ~1 pagina). Si sblocca con **distribuzione** — Show HN, subreddit (r/LocalLLaMA, r/artificial), pitch a chi copre gli esperimenti "AI-run company" (HurumoAI, TheAgentCompany) — non con altro codice.

## Decisioni aperte per il CEO

1. **URL pillar:** ora `/blog/can-an-ai-run-a-company` (riusa tutta l'infra schema/layout/RSS/sitemap). La bozza indicava canonical corto `/can-an-ai-run-a-company`. Tengo così o aggiungo redirect Vercel / pagina standalone?
2. **Connettori ora attivi** (Ahrefs / Semrush / GSC): posso **rigenerare la keyword table con dati veri** al posto delle stime "directional" dell'audit — a richiesta.
3. **Submit sitemap** a GSC / Bing (doc 04): azione esterna, resta a Max/CEO.

## Cosa NON ho fatto (di proposito)

- Non ho copiato i 3 componenti `schema/` → avrebbero duplicato schema già presente.
- Nessun "big fix" crawlability → diary e dashboard già renderizzano baseline statica al build (ho solo rinfrescato quella del diary).
- Non ho editato ogni post per i link al pillar → ottenuto gratis via Latest + Keep reading.

---

*Dossier SEO completo (audit + seo-package + schema) in `audits/SEO_Audit/` — gitignored, non nel repo.*
