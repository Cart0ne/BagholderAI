Brief S95b — site-redesign-continue — 2026-06-02

## Contesto

Redesign del sito **dark → light "Pastel Sticker v2"** (giocoso/.lol, lontano dallo stile
austero da dashboard finanziaria). Avviato in S95 (2 giugno) con Max in sessione interattiva.
La **homepage è COMPLETA e approvata** da Max. Restano le altre pagine.

Tutto il lavoro vive sul branch git **`redesign/pastel-sticker-v2`** (checkpoint home: commit
`c681427`). `main` è intoccato → la produzione mostra ancora il sito dark. Tag di rollback:
`pre-redesign-pastel-v2`.

**Fonte delle regole AS-BUILT (leggere PRIMA di toccare codice):**
`config/refactor/REDESIGN_PATTERNS.md` — token, pattern card, logiche colore/sezione, navbar,
bot, hero, footer, regole dati-live e CLS, già concordate con Max.

Handoff originale del designer: `config/refactor/REFACTOR_GUIDE_FOR_CC.md` + `theme.css` +
`bot-cards.css` + mockup HTML (`Design System.html`, `Home — Playful Sticker.html`,
`Dashboard.html`).

## Obiettivo

Applicare lo stesso linguaggio sticker/pastello alle pagine rimaste, **riusando i pattern già
costruiti** (non reinventarli). Ordine consigliato:

1. **/blog** (lista) + **/diary** — riusano IDENTICI i pattern "card numerone + bordo-accento +
   hover-lift" della home. Veloci.
2. **/library** + **/howwework** (React island) + **/roadmap** + **/blueprint** — contenuto,
   sticker + Bricolage.
3. **/dashboard** — la più grossa: ritematizzare i grafici **Chart.js** sul light (gli unici hex
   del data-layer che si possono toccare sono le serie in `dashboard-live.ts`), tabelle, P&L,
   §1–§5. Mockup di riferimento: `Dashboard.html`. La §5 "Earlier from the log" usa la card
   numerone + **citazione** (variante featured per l'ultima).
4. **legal** (terms/privacy/refund) — banali, ultimo giro.

## Workflow (regole Max, rispettarle)

- **Prima mostra dal vivo** (`npm run preview` → localhost:4321), NON screenshot: Max controlla
  nel browser. Screenshot solo per archivio/diario, e su sua richiesta.
- **Sezione per sezione**, build dopo ogni modifica. Non saturare Max di micro-review: quando
  dà autonomia, batch e mostra il risultato intero.
- Reskin, NON relayout — TRANNE dove Max chiede esplicitamente di avvicinarsi al mockup
  (es. la home è stata in parte ricostruita per matchare il mockup).
- **Non rompere il data-layer**: cambiare solo presentazione, preservare gli ID/attributi live
  (vedi REDESIGN_PATTERNS §12). Riservare spazio agli elementi rivelati in ritardo (§13, CLS).

## Vincoli / decisioni già fissate (non rilitigare)

- Navbar attiva = **pill bianca** (no azzurro). Hover = pill bianca piatta.
- Blog + diary = **card bianche** stesso layout, differenziate per accento (blog sand, diary salvia),
  bordo sinistro colorato.
- Bot = bianchi, cornice mascotte soft per-bot, colori pastello, pill LIVE pieno / TEST outline.
- `sand` è un token approvato e va usato come accento caldo dove serve.
- 3 superfici: bianco = dato, pale-sage = lettura, sage = sfondo/gap (ma in pratica le liste
  blog/diary sono bianche con bordo-accento — vedi home).

## A fine redesign (Fase 4)

- Aggiornare `web_astro/STYLEGUIDE.md` §5 (palette pastello + nota override bot).
- Screenshot `after/` (stesso metodo di `dev-screenshots/redesign-pastel-v2/before/`).
- Push branch → anteprima Vercel → review Max → **merge in `main`** = go-live.
- Aggiornare PROJECT_STATE §10 (shipped) + BUSINESS_STATE §2 (su OK Max/CEO).

## Auto-obiezione

Il rischio è il **drift dai pattern**: replicando a memoria su 8 pagine è facile inventare
varianti incoerenti. Mitigazione: `REDESIGN_PATTERNS.md` è la fonte unica; ogni pagina nuova si
confronta con la home (già approvata) e col `Design System.html`. Secondo rischio: la /dashboard
ha logica viva (grafici, tabelle, fetch) — lì il confine "presentazione vs dato" è sottile,
muoversi piano e toccare solo colori/chrome.

## Roadmap impact

Nessuno sul backend/trading. Impatto solo su `web_astro/` (branch isolato). Go-live del nuovo
look = merge branch→main, decisione di Max dopo review completa.
