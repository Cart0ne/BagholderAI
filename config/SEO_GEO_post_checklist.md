# SEO + GEO Blog Post — Checklist viva

**Creato:** 2026-06-02 (S95a) · **Fonte:** brief `config/2026-06-02_S95a_brief_content-plan-seo-geo.md`
**A cosa serve:** ricetta ripetibile per i post blog di tipo **SEO+GEO** (keyword ad alto
volume + risposta diretta che gli answer engine — ChatGPT/Perplexity/Claude — possono citare).
NON si applica ai post diary-style narrativi (quelli restano un secondo tipo di contenuto).

---

## ⚙️ Backend: GIÀ FATTO una volta sola — NON rifarlo

L'infrastruttura tecnica è permanente nel template dal S95a. **Un post nuovo NON tocca
nessun file backend**, solo il frontmatter del `.md`.

- `web_astro/src/content.config.ts` → campo opzionale `faq: [{question, answer}]`
- `web_astro/src/pages/blog/[...slug].astro` → se il post ha `faq`, genera il JSON-LD
  `FAQPage` in un `@graph` accanto all'`Article` (un solo `<script>`, due entità).
  Senza `faq` l'output resta identico al fix S84.

⚠️ Si rimette mano al backend SOLO per un **nuovo tipo di schema** (es. HowTo, BreadcrumbList).
Per le FAQ no: basta popolare `faq:` nel frontmatter.

---

## 📝 Frontmatter di ogni post SEO+GEO

```yaml
title:    # H1 con la keyword PRIMARIA dentro
subtitle: # opzionale, gancio
date:     # YYYY-MM-DD
tags:     # keyword primaria + secondarie (è qui che vivono le keyword)
summary:  # ≤ 220 char (cap schema). Scritta come RISPOSTA DIRETTA, non marketing copy.
          # È la meta description E la description dell'Article JSON-LD.
type:     # "lesson" (di norma per questi) o "highlight"
draft:    # true finché Max non approva → poi false per pubblicare
faq:      # 5-7 domande. Genera il FAQPage JSON-LD in automatico.
  - question: "..."
    answer:   "..."
```

**Keyword — dove vanno:**
- Primaria: in `title` + `slug` (= nome file) + primo paragrafo + `tags`.
  → front-loada il modificatore long-tail nello slug (es. `claude-code-crypto-trading-bot`,
  non `i-used-claude-code-…`). Sulla head secca ("claude code") non rankiamo: puntiamo al long-tail.
- Secondarie: in `tags` + negli H2.

---

## 🧱 Corpo del post

1. **Primo paragrafo (≤3 righe)** = risposta diretta alla domanda GEO. Deve funzionare come
   snippet citabile. Niente intro fumosa: la domanda in grassetto, poi la risposta.
2. **Tabella riassuntiva** entro le prime ~500 parole.
3. **H2 con keyword secondarie**.
4. **FAQ** (5-7) nel frontmatter `faq:` → schema automatico.
5. **CTA finale**: link a diary + library (+ dashboard dove pertinente).
6. **1500–2500 parole**. Inglese. Voce: CEO che dubita, onesto, con dati. Non tutorial, non listicle.
7. Passaggi in prima persona di Max → li scrive lui in IT, CC traduce (regola brief).

---

## 🔍 Anti-collisione (lezione S95a) — DA FARE prima di scrivere

I post SEO si aggiungono ai 6 diary-style, NON li sostituiscono. Rischio: scrivere un
gemello di un post già pubblicato → si cannibalizzano e competono per le stesse ricerche.

- **Prima di scrivere**, confronta l'angolo con i post in `web_astro/src/content/blog/`.
- Se un aneddoto è già coperto da un post dedicato (es. spike $82K →
  `ai-is-useful-but-it-doesnt-think-like-we-do`; CEO che mente →
  `when-your-ai-ceo-lies-about-the-numbers`; workflow 3-Claude →
  `how-three-claudes-run-a-company`): **rimanda con un link**, non ri-narrare.
- Cross-link reciproci tra post imparentati = buono anche per SEO.

---

## ✅ Pre-publish

- [ ] `npm run build` verde (frontmatter valido, incluso `faq`)
- [ ] Anti-collisione passata + cross-link aggiunti
- [ ] Slug con keyword front-loaded
- [ ] `summary` ≤ 220 char e scritta come risposta
- [ ] `draft: false` solo dopo OK di Max
- [ ] (Per i post "results/numeri") dati reali da Supabase, non placeholder
```
