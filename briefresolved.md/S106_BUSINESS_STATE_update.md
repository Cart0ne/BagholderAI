# Aggiornamento BUSINESS_STATE.md — S106 (2026-06-15)

**Istruzione per CC:** applicare le modifiche sotto alle sezioni indicate. Non toccare le sezioni non menzionate.

---

## Header — SOSTITUIRE

**Last updated:** 2026-06-15 — Session 106 (CEO + Board: site upgrade planning, brief S106a). Cap file 50KB (Max S95, CLAUDE.md §2b). Cadenze audit canoniche in PROJECT_STATE §9. Prec.: S105 (SOL grid frozen by dust → grid re-entry logic fix).
**Updated by:** CEO (sessione di lavoro con Max, site review + planning)
**Basato su:** PROJECT_STATE.md aggiornato 2026-06-14; report S104 (income-page) + S106 (office-page); screenshot live homepage/dashboard/office/income; document `bagholderai_website_architecture_v1.docx` (concept esterno)

---

## §2 Marketing In-Flight — AGGIUNGERE IN CIMA (prima di "S104 —")

### S106 — site upgrade planning (NUOVO)
- **Brief S106a `site-upgrade-v1`** scritto e approvato da Board. Caso 2 (non blocca mainnet). Contenuto:
  - **Nav ristrutturata**: `Dashboard · Diary · Blog · News · Under the hood ▾ · Library`. Dropdown "Under the hood" contiene: How we work, Blueprint, Roadmap, The experiment (/income)
  - **Homepage nuova**: hero = scena ufficio animata (componente da /office), status bar, bot cards (NewsKeeper linka a /news), manifesto block nuovo ("This is not a crypto project"), latest posts, diary, volumi. Eliminate: sezione "The team", banner V3
  - **Bot nella scena linkano a pagine reali**: Bag→/howwework, Board→/dashboard, NewsKeeper→/news, Grid/TF/Sentinel/Sherpa→/dashboard#anchor
  - **Live snapshot sotto hero**: formato TBD — CC prepara strip compatta vs card ridotta, Max sceglie su visual
  - **/office eliminata** come pagina standalone → redirect 301 a /. Componente scena spostato in homepage
  - **/income pubblicata**: noindex rimosso, aggiunta a sitemap + dropdown, adesivo WIP rimosso
  - **/dashboard riordinata**: Brains prima di Traders (pipeline logica), CEO observation log spostato dopo Recent activity, chart `type="linear"` (fix curva smooth)
  - **/news pianificata** (nav principale) — costruzione post-verdetto barometro ~23 giugno. Due scenari (validato/bocciato) documentati nel brief. Link anche dalla card NewsKeeper in homepage
  - CC produce piano italiano per Max prima di codare (task > 1h)

---

## §3 Diary Status — SOSTITUIRE la riga "Sessione corrente"

**Sessione corrente: S106 BUILDING** (site upgrade planning CEO + Board, brief S106a scritto). Nessun diary per questa sessione — interludio sito pianificato post-completamento upgrade.

---

## §4 Decisioni Strategiche Recenti — AGGIUNGERE IN CIMA

| Data | Decisione | Perché |
|---|---|---|
| 2026-06-15 (S106) | **Site upgrade brief S106a approvato** — homepage con scena ufficio hero, nav a 6 voci con dropdown, manifesto block, eliminazione /office, pubblicazione /income, riordino dashboard, /news post-verdetto | Concept esterno (ChatGPT IA v1) usato come spunto, mediato con materiale esistente. Principio: "evolvere, non ricostruire". Caso 2 (non blocca mainnet) |
| 2026-06-15 (S106) | **Nav: dropdown "Under the hood ▾"** con How we work, Blueprint, Roadmap, The experiment | 7 voci → 6 voci. Le 4 pagine "meta" (spiegano il progetto) separate dalle pagine "prodotto" (Dashboard, Blog, Diary, News, Library) |
| 2026-06-15 (S106) | **/news in nav principale** post-verdetto barometro | Contenuto live differenziante (headline + sentiment AI + barometro), motivo per visite ripetute. Competitor tbot mostra stesse fonti senza label AI. Due scenari: validato (claim predittivo) o bocciato (trasparenza) |
| 2026-06-15 (S106) | **/income pubblicata** (noindex off, sitemap, dropdown, no WIP) | "€274 spesi per fare €0" è più potente ora che a €5. Il target audience (indie hackers, AI enthusiasts) apprezza l'onestà, non il successo. Il €0 è il contenuto |
| 2026-06-15 (S106) | **/office eliminata** come pagina standalone | Scena ufficio spostata in homepage hero. Pagina duplicata non aggiunge valore. Easter egg serio = progetto futuro a sé, non copia |
| 2026-06-15 (S106) | **Library resta "Library"** — NO rename a Logbook/Mission Logs | "Logbook" collide con Diary. "Library" non è rotto, è una libreria con libri |
| 2026-06-15 (S106) | **Sezione "The team" rimossa dalla homepage** | La scena ufficio mostra il team visivamente, /howwework lo spiega testualmente. Tre fonti per la stessa info = ridondanza |
| 2026-06-15 (S106) | **Dashboard: chart `type="linear"`** (fix curve smooth) | Curve spline inventano valori intermedi mai esistiti. In finanza si usano segmenti dritti. Contraddizione su sito di trasparenza radicale |
| 2026-06-15 (S106) | **Brave Creators (BAT tip jar) TAGLIATO** dalla lista | Zero urgenza, zero trigger prevedibile. Se serve, il setup è documentato |
| 2026-06-15 (S106) | **Post Haiku su X: NON paused** — sistema attivo, Max filtra manualmente (approve/discard via Telegram) | Memoria CEO era sbagliata ("paused"). Il sistema gira, Max scarta quando vuole. Nessuna azione richiesta |

---

## §7 Cosa NON Sta Succedendo e Perché — MODIFICHE

### RIMUOVERE la riga Brave Creators (tagliata dalla lista, S106)

### AGGIUNGERE
| Cosa | Perché |
|---|---|
| **/news pubblica** | Pianificata ma bloccata dal verdetto barometro v2 (~23 giugno). Brief S106a documenta struttura e due scenari. Non costruire prima |
| **Easter egg /office interattivo** | L'idea di una pagina dove clicchi ogni bot ed entri nella sua "stanza" con dati dettagliati è parcheggiata. Se si fa, è un progetto a sé — non una pagina duplicata della homepage |

### AGGIORNARE la riga "Post Haiku X"
Sostituire qualsiasi riferimento a "Haiku posts paused" con: **Post Haiku X: sistema attivo**, Max approva/scarta via Telegram. Non paused, non schedulato — proposta automatica con filtro umano.

---

*Fine aggiornamento. Sezioni §1, §5, §6 invariate.*
