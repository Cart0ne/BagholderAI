# Brief S106a — site-upgrade-v1 — 2026-06-15

**Da:** CEO (Claude)
**Per:** CC (Claude Code)
**Board:** Max (approvato in sessione)
**Basato su:** PROJECT_STATE.md 2026-06-14, BUSINESS_STATE.md 2026-06-13, screenshot homepage/dashboard/office/income live, document `bagholderai_website_architecture_v1.docx` (concept esterno usato come spunto)
**Tipo:** Caso 2 (non blocca mainnet, non ha deadline)
**Stima:** task composito — CC produce piano italiano per approvazione Max prima di codare

---

## Contesto

Sessione CEO + Board di revisione sito. Obiettivo: evolvere il sito dalla struttura attuale a una versione che comunichi "sede di un'azienda AI autonoma" invece di "sito di un progetto tecnico", riutilizzando al massimo il materiale esistente. Niente stravolgimenti — interventi chirurgici.

---

## 1. NAVIGAZIONE

### Navbar attuale
`Dashboard · Diary · Blog · Blueprint · How we work · Roadmap · Library` (7 voci)

### Navbar nuova
`Dashboard · Diary · Blog · News · Under the hood ▾ · Library` (6 voci, di cui 1 dropdown)

### Contenuto dropdown "Under the hood ▾"
- How we work
- Blueprint
- Roadmap
- The experiment (`/income`)

### Regole
- Il dropdown si apre al click (non hover), chiude al click fuori
- Mobile: stesso comportamento, collassabile
- Label "Under the hood" in nav, NON in maiuscolo caps-lock (stile coerente con le altre voci)
- L'ordine delle voci nel dropdown è quello sopra

---

## 2. HOMEPAGE — nuovo layout sezioni

### Ordine attuale
1. Banner V3
2. Hero (testo + live snapshot card)
3. Status bar
4. Latest posts (3 blog)
5. The AI bots (4 cards)
6. Development diary (3 sessioni)
7. The team (Claude, Max, CC)
8. The story (4 copertine volumi)
9. Footer / A-ADS

### Ordine nuovo
1. **Hero = scena ufficio** (componente da /office → spostato qui)
2. **Live snapshot** (formato da decidere — vedi §2.1)
3. **Status bar** (invariata)
4. **The AI bots** (4 cards, invariate nel contenuto — vedi §2.2 per link)
5. **Manifesto block** (NUOVO — vedi §2.3)
6. **Latest posts** (3 blog, invariato)
7. **Development diary** (3 sessioni, invariato)
8. **The story** (4 copertine volumi, invariato)
9. **Footer** (invariato)

### Eliminato
- Banner V3 (promozionale, invecchia — i volumi si vendono dalla sezione "The story")
- Sezione "The team" (ridondante: la scena ufficio mostra il team, /howwework lo spiega)

### 2.1 — Live snapshot: DECISIONE APERTA (Board sceglie su visual)
CC prepara **due versioni** per Max:
- **Opzione A — strip compatta**: riga orizzontale sotto la scena. Contenuto: `108 orders · +$17.75 P&L · Day 11 · $600 budget · TESTNET`. Stile: monospace, sfondo leggero, una riga.
- **Opzione B — card ridimensionata**: la card attuale (ORDERS / TOTAL P&L / DAYS RUNNING / BUDGET / TODAY P&L / TODAY TRADES) rimpicciolita e spostata sotto la scena, senza il testo hero.

Max sceglie dopo aver visto entrambe. Non procedere con l'integrazione finale finché Max non conferma.

### 2.2 — Bot links dalla scena ufficio
| Elemento scena | Link target |
|---|---|
| Bag (CEO, podio) | /howwework |
| Board (schermo portfolio) | /dashboard |
| NewsKeeper (bot viola) | /news |
| Grid (bot verde) | /dashboard#grid |
| TrendFollower (bot arancione) | /dashboard#trendfollower |
| Sentinel (bot blu) | /dashboard#sentinel |
| Sherpa (bot rosso) | /dashboard#sherpa |

**Prerequisito**: aggiungere `id="grid"`, `id="trendfollower"`, `id="sentinel"`, `id="sherpa"` alle sezioni corrispondenti in `/dashboard`. Oggi non ci sono anchor ID.

Rimuovere il footer attuale di /office ("CLICK THE BOARD → DASHBOARD · CLICK BAG → HOW WE WORK · AGENTS ARE PLACEHOLDERS") — i link sono nei bot stessi, non serve spiegarlo.

### 2.3 — Manifesto block (NUOVO)
Posizione: tra le bot cards e i blog posts.
Contenuto testuale (CEO draft, CC adatta layout):

> **This is not a crypto project.**
>
> Crypto trading is just the first sandbox. This is a public experiment: can AI become productive labor for humans? Every trade, every mistake, every decision — documented.

Stile: blocco visivo distinto (sfondo leggermente diverso o bordo), testo centrato, 3-4 righe max. Niente CTA, niente link — è una dichiarazione, non una sezione di navigazione. Font size più grande del body text. Nessun header tag (è un blocco retorico, non una sezione SEO).

### 2.4 — Card NewsKeeper in homepage
La card NewsKeeper nella sezione "The AI bots" deve linkare a /news. Click sulla card → /news. Comportamento consistente con le altre card se quelle linkano da qualche parte, altrimenti solo NewsKeeper linka.

---

## 3. /OFFICE → ELIMINARE COME PAGINA STANDALONE

- Spostare il componente `LabRoom.jsx` (isola React) dalla pagina /office alla homepage
- Eliminare `web_astro/src/pages/office.astro`
- Redirect 301: `/office` → `/`
- Rimuovere gli asset SVG da `public/office/` SOLO se non servono più alla scena in homepage (probabilmente restano, cambia solo il consumer)
- Rimuovere `/office` dal filtro sitemap in `astro.config.mjs` (non serve più, la pagina non esiste)

---

## 4. /INCOME — PUBBLICAZIONE

### Azioni
1. Rimuovere `noindex` dal `<head>`
2. Aggiungere a sitemap (rimuovere l'esclusione in `astro.config.mjs`)
3. Aggiungere come voce "The experiment" nel dropdown "Under the hood ▾"
4. Rimuovere adesivo 🚧 WIP
5. Verificare che i dati nella tabella `passive_income` siano aggiornati (ultimo seed: 3 giorni fa secondo le card)

### NON fare
- Non aggiungere /income alla nav principale (sta nel dropdown)
- Non creare teaser in homepage per ora (rivalutare dopo il primo round di feedback)
- Non automatizzare le fonti (decisione Board: manuale finché revenue = €0)

---

## 5. /DASHBOARD — RIORDINO SEZIONI

### Ordine attuale
1. Hero (Lab notebook, net worth, today)
2. CEO observation log (Haiku)
3. 2 · Instruments — 2.1 Traders, 2.2 Brains
4. 3 · Performance time series
5. 4 · Recent activity
6. 5 · Earlier from the log
7. 6 · Reconciliation

### Ordine nuovo
1. **Hero** (invariato)
2. **2 · Instruments — 2.1 Brains** (NewsKeeper → Sentinel → Sherpa), **2.2 Traders** (TF, Grid)
3. **3 · Performance time series** (invariato)
4. **4 · Recent activity** (invariato)
5. **5 · CEO observation log + Earlier from the log** (uniti o sequenziali)
6. **6 · Reconciliation** (invariato — il sigillo di fiducia resta in fondo)

### Modifiche
- **Inversione Traders/Brains**: la pipeline reale è NEWS → RISK → PARAMETERS → EXECUTION. Mostrare prima il cervello (2.1 Brains) poi l'esecuzione (2.2 Traders)
- **CEO observation log spostato**: da posizione 2 a posizione 5. È narrazione, non dato operativo. Il visitatore nuovo vuole vedere prima i numeri, poi la voce del CEO
- **Aggiungere anchor ID** alle sezioni: `id="grid"`, `id="trendfollower"`, `id="sentinel"`, `id="sherpa"`, `id="newskeeper"` per consentire deep-link dalla scena homepage

### Fix chart — `type="linear"`
Il grafico Portfolio Value in §3 usa curve smooth (spline cubiche, `type="monotone"` di Recharts). In finanza le time series si disegnano con segmenti dritti punto-a-punto (`type="linear"`). Le curve smooth inventano valori intermedi mai esistiti — contraddizione su un sito di trasparenza radicale.
**Fix**: cambiare `type="monotone"` → `type="linear"` sul componente `<Line>` o `<Area>` di Recharts in `dashboard-live.ts` (o dove vive il chart). Una riga.

---

## 6. /NEWS — NUOVA PAGINA (POST-VERDETTO BAROMETRO)

**ATTENZIONE: NON costruire prima del verdetto barometro v2 (~23 giugno 2026).** Questa sezione è il piano, non un ordine di esecuzione immediato. Brief di costruzione separato post-verdetto.

### Concept
Pagina pubblica con il feed delle headline classificate da NewsKeeper + barometro aggregato. Differenziante vs competitor (tbot): noi mostriamo lo stesso feed RSS ma CON sentiment AI, confidenza, e link causale alle decisioni del bot.

### Struttura prevista (da validare post-verdetto)

**Header**: titolo + badge LIVE + sottotitolo ("What our AI reads, and how it reads the market")

**Barometro**: grafico step-line storico (il componente esiste già nell'admin, brief S106 CC). Mostra barometro↔regime Sentinel su ~14 giorni.

**Feed headline**: lista compatta (NO card con immagini — non abbiamo immagini da RSS). Per ogni evento:
- Titolo headline
- Fonte (CoinDesk / CoinTelegraph / MarketWatch / CNBC)
- Tempo fa (2h ago)
- Label polarità (bullish / bearish / neutral) con colore
- Confidenza (se utile per il lettore)
- Raggruppamento per event_key (dedup): una storia ripetuta da 3 fonti → 1 riga con badge "3 sources"

**Collegamento causale** (in fondo o sidebar): una riga che spiega il flusso "Headlines → Barometer → Sentinel regime → Sherpa parameters → Grid behavior" con link a /dashboard.

### Due scenari post-verdetto

**Se barometro validato**: il grafico storico in cima è la prova empirica. Copy: "This sentiment signal anticipated price movements X% of the time over 14 days."

**Se barometro bocciato**: rimuovere il claim predittivo. Tenere il feed classificato come trasparenza ("Here's what our AI reads and how it classifies market news"). Il grafico diventa illustrativo, non probatorio.

### Navigazione
- Voce in nav principale: `News` (tra Blog e Under the hood ▾)
- Link dalla card NewsKeeper in homepage
- Link dalla card NewsKeeper in /dashboard

---

## 7. PAGES INVARIATE

Le seguenti pagine NON vengono toccate da questo brief:
- /blog (struttura, contenuto, layout)
- /diary (struttura, contenuto, layout)
- /howwework (contenuto invariato, URL invariato)
- /blueprint (contenuto invariato, URL invariato)
- /roadmap (contenuto invariato, URL invariato — aggiornamento contenuto in brief separato se necessario)
- /library (nome confermato: resta "Library", NO rename)
- /terms, /privacy (invariate)
- Pagine admin (grid, tf, etc.)

---

## 8. OFF-LIMITS

- Backend / bot / trading logic: **ZERO TOCCHI**
- Tabelle Supabase esistenti (trades, bot_config, sentinel_scores, etc.): **NON MODIFICARE**
- Tabella `passive_income`: solo verifica dati aggiornati, nessuno schema change
- `NON restartare il bot` — niente in questo brief richiede restart
- Stili custom del diary .docx: non toccare
- File `BUSINESS_STATE.md`: aggiornato da CEO, non da CC di iniziativa

---

## 9. OUTPUT ATTESO

CC produce **PRIMA** un piano in italiano per Max (task > 1h) con:
1. Ordine di esecuzione proposto (quali interventi per primi)
2. File toccati per ogni intervento
3. Stima tempi
4. Rischi / dipendenze
5. Almeno 1 obiezione tecnica reale

Max approva il piano, poi CC implementa.

### Deliverable finali
- [ ] Nav aggiornata (dropdown "Under the hood" funzionante desktop+mobile)
- [ ] Homepage nuova (scena ufficio hero, snapshot TBD, manifesto, senza team, senza banner V3)
- [ ] Bot links nella scena funzionanti (tutti 7, nessun placeholder #)
- [ ] Anchor ID in dashboard (grid, trendfollower, sentinel, sherpa, newskeeper)
- [ ] Dashboard riordinata (Brains prima, CEO log dopo, chart linear)
- [ ] /income pubblicata (noindex rimosso, sitemap, dropdown, no WIP sticker)
- [ ] /office eliminata (redirect 301 → /)
- [ ] Deploy Vercel verificato
- [ ] Nessun /news (è post-verdetto, solo pianificata)

---

## 10. ANTI-ASSENSO (CEO)

**Obiezione 1 — Scope creep risk.** Questo brief tocca 4 pagine (home, dashboard, /income, /office) + nav + 1 componente nuovo (manifesto) + elimina 1 pagina + pubblica 1 pagina. Per "intervento chirurgico" è parecchio. CC deve segmentare in commit atomici reversibili. Se qualcosa si rompe, si reverta solo quel pezzo.

**Obiezione 2 — Lo snapshot TBD blocca l'homepage.** Se Max non sceglie tra strip e card, l'hero non è finibile. CC deve poter procedere con tutto il resto e integrare lo snapshot come ultimo step. Le due opzioni devono essere branch-indipendenti o varianti nello stesso commit.

**Obiezione 3 — Anchor ID fragili.** I deep-link dalla scena (es. /dashboard#sherpa) si rompono se qualcuno rinomina le sezioni della dashboard. Accettabile per ora, ma se in futuro si toccano le sezioni, ricordare di allineare gli ID.
