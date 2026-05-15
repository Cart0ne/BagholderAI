# Brief 77b — Primo blog post: publish

**Data di riferimento:** PROJECT_STATE.md aggiornato 2026-05-14 (S76 chiusura)
**Basato su:** BUSINESS_STATE.md sezione 2 (blog weekend), STYLEGUIDE.md § 22 (Blog Content Collections)

---

## Obiettivo

Pubblicare il primo blog post di BagHolderAI. Il file markdown è già scritto e approvato dal Board. CC deve solo posizionarlo nel repo, verificare il build, e deployare.

---

## File da committare

**Sorgente:** il file `an-ai-that-cant-trade.md` allegato a questo brief.

**Destinazione:** `web_astro/src/content/blog/an-ai-that-cant-trade.md`

### Frontmatter del post

```yaml
title: "An AI That Can't Trade, a Human That Can't Say No"
subtitle: "How an architect with no trading experience handed the keys to an AI with no trading ability — and why they're writing about it"
date: 2026-05-15
tags: ["origin", "introduction", "behind-the-scenes"]
summary: "BagHolderAI is what happens when an architect gives an AI a $500 budget and says 'you're the CEO now.' This is how it started — told from both sides."
volume: 1
type: "lesson"
draft: false               # ← pubblicazione immediata confermata dal Board
```

---

## Step di esecuzione

1. `git pull origin main`
2. Copiare il file in `web_astro/src/content/blog/an-ai-that-cant-trade.md`
3. `cd web_astro && npm run dev` — verificare:
   - `/blog` mostra la card del post (titolo, summary, data)
   - `/blog/an-ai-that-cant-trade` renderizza correttamente (h2, hr, blockquote, em, strong, link)
   - CTA Payhip a fondo post punta a Volume 1
   - Nessun errore console
4. `npm run build` — verificare build success, no errori
5. Se `draft: false`: commit + push → Vercel re-deploya automaticamente
6. Verificare live su `bagholderai.lol/blog` e `bagholderai.lol/blog/an-ai-that-cant-trade`

---

## Decisioni delegate a CC

- Fix di eventuali problemi di rendering markdown (spaziature, heading levels)
- Se il CTA Payhip non renderizza correttamente, debug e fix

## Decisioni che CC DEVE chiedere a Max

- Qualsiasi modifica al testo del post (è approvato dal Board così com'è)
- Cambio di data nel frontmatter
- Aggiunta di elementi non previsti (immagini, callout, ecc.)

---

## Output atteso a fine sessione

- File committato e pushato in `main`
- Post visibile su `bagholderai.lol/blog`
- Nessuna regressione sulle altre pagine del sito

## Vincoli

- NON modificare il testo del post
- NON toccare altri file del blog (schema, componenti, layout) a meno che non serva per un bug
- NON toccare codice dei bot o altri sistemi

## Roadmap impact

- BUSINESS_STATE.md § 2: "Blog primo post" passa da "weekend 17-18 maggio" a DONE
- Todo Apple Notes: voce "Blog: sessione dedicata selezione contenuti V1" può essere aggiornata (primo post fatto, prossimi TBD)
