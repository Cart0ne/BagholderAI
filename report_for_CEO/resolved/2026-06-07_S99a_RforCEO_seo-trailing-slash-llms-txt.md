# Report per CEO — S99a — seo-trailing-slash-llms-txt — 2026-06-07

**Brief sorgente:** `config/2026-06-07_S99a_brief_seo-trailing-slash-llms-txt.md` (archiviato in `briefresolved.md/`)
**Commit:** `9787aa5` (push su `main`)
**Tipo:** fix infrastrutturale SEO — web-only, **no bot / no restart**
**Origine:** primo audit Semrush su bagholderai.lol (7 giu): 97% health, 0 errori, 13 warning gonfiati dal doppio conteggio `/path` vs `/path/` + segnalazione `llms.txt not found`.

---

## Cosa è stato fatto

**Task 1 — Trailing slash → canonical senza slash**
- `web_astro/astro.config.mjs`: `trailingSlash: 'never'` (coerenza sitemap + `<link rel="canonical">`).
- `web_astro/vercel.json`: aggiunto `"trailingSlash": false` (chiave top-level, **non** ho toccato l'array `redirects` esistente). È questo a produrre il redirect **308** reale in produzione.
- Grep link interni (`web_astro/src/`): 18 href, **zero** con trailing slash → nulla da correggere.

**Task 2 — llms.txt**
- Creato `web_astro/public/llms.txt` (summary GEO-oriented, formato Markdown standard).

## Decisione tecnica chiave (anti-assenso)

Il brief assumeva che `trailingSlash: 'never'` di Astro facesse da solo il redirect 301. **Non è vero nel nostro caso**: il sito è un **build statico** (nessun adapter Vercel) → Astro non ha runtime in produzione. Verificato dal vivo *prima* del fix: `/diary` e `/diary/` rispondevano **entrambi 200** — esattamente il duplicato che Semrush conta doppio.

→ La leva che chiude davvero il warning è lato host: `"trailingSlash": false` in `vercel.json` (Vercel emette il 308). Approvato da Max prima di procedere. Il solo cambio Astro avrebbe lasciato il warning vivo (avrebbe normalizzato solo sitemap e canonical).

## Correzione al contenuto del brief

Il `llms.txt` proposto nel brief linkava `/about`, che è **404** (non esiste). Sostituito con `/howwework` ("Team structure and project philosophy" calza). Micro-aggiustamento esplicitamente delegato a CC. Senza, il file pensato per gli LLM avrebbe contenuto un link rotto.

## Verifica end-to-end (produzione, deploy Vercel già propagato)

| Check | Esito |
|---|---|
| `/diary/` → `/diary` | **308** ✅ |
| `/blog/` → `/blog` | **308** ✅ |
| Pagine canoniche (`/diary`, `/blog`, `/dashboard`, `/howwework`, `/`, blog post) | 200, nessun loop ✅ |
| `/llms.txt` | 200, contenuto corretto (`/howwework`) ✅ |
| `npm run build` | verde, 19 pagine ✅ |
| `sitemap-0.xml` | zero URL con trailing slash ✅ |

## Sull'auto-obiezione CEO (llms.txt)

D'accordo: l'impatto pratico di `llms.txt` oggi è incerto (i crawler AI non lo visitano attivamente, 2025). Lo abbiamo fatto perché costo ~zero, allineato al posizionamento AI-native, e ci troviamo già pronti se/quando verrà adottato. Nessuna illusione che muova qualcosa domani.

## Roadmap impact

Nessuno. Fix infrastrutturale, non una feature.

## Nota operativa

- Al push, il remote era avanti di `ddda84b` (check NewsKeeper macro feed giornaliero — routine Claude schedulata, T+7). Zero overlap → `pull --rebase` pulito, mio commit in cima.
- Su richiesta di Max ho allineato il **repo runtime del Mac Mini** a `9787aa5` (fast-forward, zero file di codice toccati). Nota: il push automatico del NewsKeeper non parte dal repo runtime ma dalla routine schedulata (ambiente separato), che si auto-allinea — l'allineamento del runtime è igiene, non prerequisito.
