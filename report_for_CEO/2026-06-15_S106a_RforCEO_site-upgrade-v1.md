# Report per CEO — S106a — site-upgrade-v1 (batch 1)

**Da:** CC (Claude Code) · **Per:** CEO (Claude) · **Board:** Max
**Brief sorgente:** `config/2026-06-15_S106a_brief_site-upgrade-v1.md`
**Data:** 2026-06-15 · **Tipo:** Caso 2 (non blocca mainnet)
**Commit:** `45b6603` · `b2a0791` · `2b76991` · `5c6aaf3` · `dbc35bf` · `8256aed` (su `main`, pushati)
**Esito:** SHIPPED batch 1 (web-only) + deploy Vercel · **nessun restart bot**

---

## Contesto

Il brief S106a è composito. Decisione Board (Max): **non** implementarlo tutto, partire da
"alcune cose semplici". Selezione finale del batch 1 (più la richiesta diary emersa in corso):
grafici onesti, anchor ID dashboard, /income pubblicata, nuova nav bar, riordino dashboard, fix
titolo diary, e — fuori brief — ingrandimento del board nella scena /office. Tutto web-only,
commit atomici reversibili (CEO Obiezione 1: anti scope-creep).

## Cosa è stato fatto

1. **Grafici onesti `tension:0`** (`45b6603`) — la linea Portfolio della dashboard §3 e il grafico
   P&L di /income usavano spline smooth (`tension:0.3`), che inventano valori intermedi mai esistiti.
   Portati a segmenti dritti. *Esteso a /income oltre il brief letterale* perché la pagina diventa
   pubblica in questo stesso batch (stesso principio di trasparenza).
2. **/income PUBBLICATA** (`b2a0791`) — rimossi `noindex` + adesivo WIP + esclusione sitemap; voce
   nav "The experiment" nel dropdown. Dati `passive_income` verificati: €0 revenue / ~€274 costi,
   ultimo seed 12-giu, coerenti — il €0 è il contenuto. Nessun teaser in homepage (brief §4).
3. **Nav dropdown "Under the hood ▾"** (`2b76991`) — 7→5 voci. Dropdown: How we work / Blueprint /
   Roadmap / The experiment. `<details>` nativo + chiusura su click-fuori/Esc; mobile collassabile.
4. **Dashboard riordinata** (`5c6aaf3`) — Brains prima dei Traders (pipeline news→risk→exec); CEO
   observation log spostato dalla cima al §4 (today + archivio, sequenziali); anchor ID
   `#grid/#trendfollower/#sentinel/#sherpa/#newskeeper` + `scroll-mt`; rinumero contiguo 1→5.
5. **Fix diary** (`dbc35bf`) — H1 di /diary "Construction log" → "Development diary" (era l'unico
   outlier; il termine è "Development diary" ovunque, incluso il `<title>` SEO della pagina stessa).
   *Fuori scope brief* (richiesta diretta Max).
6. **Board scena /office ingrandito 1.18×** (`8256aed`) — *fuori brief, richiesta Max*. I font erano
   6.5-9px. Scala uniforme (origin top-center) + board alzato (top:124) per non toccare il CEO
   sotto; cornice news `bhBoardFlash` scalata in lockstep; label "CEO active" abbassata 6px.
   Sviluppato in sandbox `/office-lab` usa-e-getta (copia di LabRoom), approvato visivamente da Max,
   poi ripiegato nel `LabRoom.jsx` vero e sandbox rimossa.

## Anti-assenso / flag (CLAUDE.md §0 + §7)

- **Drift brief §5 (segnalato):** il brief dice di cambiare Recharts `type="monotone"`. Lo stack reale
  è **Chart.js** (`tension`). Intento corretto, istruzione stale sul nome libreria/proprietà.
- **News fuori batch (deviazione segnalata):** il brief mette "News" in navbar, ma `/news` non esiste
  (post-verdetto barometro ~23 giu). Includerla ora = link 404. **Voce News rimandata** alla pagina.
- **Rinumerazione dashboard:** il brief lascia ambiguità sui numeri visibili; default scelto =
  contiguo 1→5 (Hero/Today restano senza numero).

## Verifica

`npm run build` verde (22 pagine). Sitemap include `/income`, esclude `/tf /grid /office`. `/income`
senza noindex/WIP. Nav con dropdown completo, News assente. Entrambi i grafici `tension:0`. Nessun ID
duplicato in dashboard. Board /office confermato su dati reali (canonical + `daily_pnl` 7g). Deploy
Vercel su push; verifica live di Max sul sito.

## Domanda aperta / parcheggiata

- **Set dati del board /office** — Max valuta se lasciare l'attuale (net worth + %/coin + sparkline)
  o aggiungere skim/realized/altro. Tutto il resto del motore canonico (skim, realized, unrealized,
  cash, fees) è **già calcolato** e aggiungibile a costo ~zero, restando dato reale; vincolo = spazio.
  Decisione editoriale del Board, non tecnica.

## Batch futuri S106a (NON fatti)

Scena ufficio → hero homepage; /office eliminata + redirect 301; live snapshot strip-vs-card
(richiede scelta visual di Max); manifesto block; pagina /news + voce nav (post-verdetto); rimozione
sezione "The team" + banner V3; link card NewsKeeper → /news.
