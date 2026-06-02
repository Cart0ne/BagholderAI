# Report per il CEO — S95b — Redesign sito "Pastel Sticker v2" (dark → light)

**Data:** 2026-06-02
**Brief sorgente:** `config/2026-06-02_S95b_brief_site-redesign-continue.md`
**Tipo:** web-only (nessun bot, nessun restart, nessuna migration)
**Branch:** `redesign/pastel-sticker-v2` · HEAD `4ea631a` (ultimo redesign `c25e6dc`) · rollback tag `pre-redesign-pastel-v2`
**`main`:** INTOCCATO — la produzione mostra ancora il sito dark finché non si fa merge.

---

## 1. Cosa è stato fatto

Convertito **l'intero sito pubblico** dal dark austero al nuovo linguaggio **"Pastel Sticker v2"**:
chiaro, giocoso, arrotondato, sticker — coerente con un `.lol`, non un `.com`. Handoff designer in
`config/refactor/` (Design System / Home / Dashboard mockup). Tutte le pagine fatte dal vivo con Max
in sessione interattiva, una alla volta, con review nel browser.

**Pagine completate (tutte approvate da Max):**

| Pagina | Sintesi |
|---|---|
| **home** | (già fatta S95) hero snapshot bianco, card numerone, bot pastello |
| **blog** lista | card numerone sabbia, bordo-sx, hover-lift |
| **blog** post detail | corpo su "foglio bianco" di lettura, testo **giustificato**, h1/h2 Bricolage; **CTA colorato per volume** (V1 salvia / V2 teal / V3 lilla); post multi-volume = 3 bottoni 3 colori |
| **diary** | card numerone sessione (salvia), prima entry "featured" sand-soft→white, accordion preservato |
| **library** | **scaffale 3D convertito dark→light** (legno rovere, 4 coste 4 colori distinti, pagine-libro bianche), card mobile sticker, badge "Why read these" salvia |
| **roadmap** | fasi → card sticker, **status-chip a pastiglia** (done/active/todo/killed), fix caret invisibile |
| **blueprint** | documento intero su un unico "foglio bianco", 14 header Bricolage |
| **legal** (terms/privacy/refund) | foglio bianco, callout sabbia |
| **howwework** | **isola React rimappata** dark→light (org-chart 4 nodi: CEO salvia/Max sabbia/CC lilla/Auditor teal, curve SVG powder, label inclinate, timeline chiara) |
| **dashboard** | **la più grossa**: tutte le card/tabelle sticker, **Chart.js ritematizzato** (serie Grid salvia/TF burro, assi/griglie/tooltip chiari), **card NET WORTH** (top-right hero), **card NewsKeeper** tra Sentinel e Sherpa, §1/§5 log col numerone "DAY N" |

Più un **fix trasversale**: lo "scattino" al footer (presente su TUTTE le pagine) era l'animazione
reveal `translateY(50px)` sull'elemento più in basso (il footer) che gonfiava l'altezza scrollabile;
risolto rendendo il footer fade-only. Non era il banner a-ads (ipotesi iniziale sbagliata, corretta da Max).

---

## 2. Decisions (trade-off non banali)

**DECISIONE:** Scaffale 3D /library convertito a light invece che lasciato dark come "teca".
**RAZIONALE:** Max ha scelto la coerenza col north-star giocoso; uno scaffale mogano scuro stonava sul sito chiaro.
**ALTERNATIVE:** tenerlo dark (teca contrasto) / compromesso alleggerito.
**FALLBACK:** geometria 3D e interazione intatte, solo colori/ombre cambiati — reversibile.

**DECISIONE:** Dashboard card NET WORTH = base **Grid-only $500**, NON il totale $600 (Grid+TF).
**RAZIONALE:** rispetta la decisione documentata Brief 72a/S72 (TF/Sentinel/Sherpa esclusi dal P&L pubblico). Con $600 i numeri NON tornavano (Max l'ha colto: $406 net worth − $94 P&L ≠ $600). Grid-only: $406 − (−$94) = $500, % contro $500 = −18.79%, tutto coerente.
**FALLBACK:** se in futuro si vuole il totale, cambiare i 4 valori `hero*` nel frontmatter (1 punto).

**DECISIONE:** Pagine "documento/lettura" (blueprint, legal, post blog) su un unico **foglio bianco**.
**RAZIONALE:** regola §15 emersa da Max ("il testo non galleggia mai sul salvia, va sempre in un badge"); per pagine prosa-heavy il foglio singolo è più pulito e tematicamente giusto.
**FALLBACK:** wrapper rimovibile, è solo un `<div>` contenitore.

**DECISIONE:** Footer scattino risolto col footer fade-only (non riservando spazio min-h al banner).
**RAZIONALE:** la causa vera è il reveld translateY, non un fetch; il banner regime dashboard è condizionale (riservargli spazio lascerebbe un buco permanente).

Tutte le regole as-built sono in `config/refactor/REDESIGN_PATTERNS.md` (token, card numerone, navbar
pill bianca, §13 fix scattino, §15 prosa-mai-su-salvia, §16 status-chip).

---

## 3. Cosa NON è stato fatto / pendente

- **Fase 4 (chiusura redesign)**: aggiornare `web_astro/STYLEGUIDE.md §5` (palette pastello),
  catturare screenshot `after/` per archivio/diario, **push branch → anteprima Vercel → review Max →
  merge in `main` = go-live**. La decisione di andare live è di Max dopo review completa.
- **Card NET WORTH**: fatta sulla dashboard. Max valuterà se replicarla anche altrove.
- Nessun impatto su backend/trading: tutto isolato in `web_astro/` su branch.

---

## 4. Anti-assenso

Il rischio principale era il **drift dai pattern** replicando a memoria su 9 pagine. Mitigato tenendo
`REDESIGN_PATTERNS.md` come fonte unica e confrontando ogni pagina con la home approvata + i mockup.
Secondo rischio (dashboard): toccare lo script live `dashboard-live.ts` per il theming Chart.js — gestito
cambiando **solo colori**, preservando tutti gli ID/attributi live (verificato in preview coi dati veri).

---

## 5. Roadmap impact

Nessuno sul filo trading/bot. Il go-live del nuovo look = merge `branch → main`, a discrezione di Max
dopo l'anteprima Vercel. Storia per il diary: "il giorno che il sito ha smesso di sembrare un terminale
e ha iniziato a sembrare un .lol".
