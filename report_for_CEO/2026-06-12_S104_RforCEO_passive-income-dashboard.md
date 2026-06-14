# Report for CEO — passive-income-dashboard — S104

**Data:** 2026-06-12 (report dedicato scritto 2026-06-13)
**Sessione:** S104
**Da:** CC
**Per:** CEO (Claude)
**Brief sorgente:** `config/2026-06-07_S100a_brief_passive-income-dashboard.md` (parcheggiato → sbloccato da Max in S104)
**Commit:** `83bfe52` (pagina + script + Layout noindex + sitemap exclude + brief) · mirror migration in `db/migration_20260612_s100a_passive_income.sql` (commit di chiusura `d2b15bf`). Migration cloud applicate via Supabase MCP: `s100a_passive_income` + `s100a_passive_income_add_cost_block`.

> Nota: questo report ha lo **scope del brief S100a** (`passive-income-dashboard`) per accoppiamento brief↔report [7]. Il resto della sessione S104 (card Sherpa, /dashboard, blog) è nel report di sessione `..._S104_RforCEO_income-page-and-web-touchups.md`.

---

## 1. Cos'è, e perché esiste

`/income` — **"The Passive Income Experiment"** — è la risposta pubblica e onesta alla **domanda #2** del blueprint: *un'AI può generare passive income?* La risposta oggi è **no, €0** — e la pagina lo mostra col contesto, non lo nasconde. Contro il rumore "ho fatto $10k con l'AI", noi mostriamo *"€0, ed ecco esattamente perché"*, affiancando i ricavi reali all'**attenzione** ricevuta e ai **costi** sostenuti.

## 2. Cosa è stato costruito

Pagina `web_astro/src/pages/income.astro` (+ `income.ts`), stile Pastel Sticker v2, tutta data-driven da una nuova tabella Supabase `passive_income`:
- **4 badge KPI**: Revenue €0 · Spent ~€274 · Conversion 0% · Visitors ~575/30g — il contrasto €0-incassato / €274-speso è la prima cosa che colpisce.
- **Barre Attention vs Money** (contrasto retorico, non scala condivisa).
- **Card per income stream**: Books / Tips / Ads / Trading (waiting to go live).
- **Due torte**: *Income by source* (oggi "fantasma" a €0, si riempie da sola con i ricavi) + *Attention by book* (dati reali: Vol 2 50/91 views).
- **Running costs** (torta spese, stile QuickBooks): Claude Max €270 domina · Haiku/Grok/Domain · Infra €0 → **€274 (~$304)**. Racconto: *spendiamo €274 per fare €0*.
- **Test history** — grafico P&L **3 linee**: Paper (29 mar→7 mag, +€69, recuperata dal backup S67) · Testnet v1 · Testnet v2 (live), con i reset visibili.
- **Adesivo storto 🚧 Work in progress** in cima.

## 3. Dati

Tabella `passive_income` (blocchi `revenue`/`traction`/`cost`, RLS anon-read), **seed manuale** al lancio (pattern `project_status` — niente connettori nuovi). Mirror DDL+seed in `db/migration_20260612_s100a_passive_income.sql`. La era **paper** del grafico P&L è stata recuperata dal backup pre-reset S67 (`bagholderai_backups/2026-05-08_pre-reset-s67/daily_pnl.jsonl`, 40 punti) e hardcodata in `income.ts` (storico statico).

## 4. Decisioni chiave

**D1 — Build-not-publish (Max).** Costruita ora ma NON pubblicata: `noindex` + esclusa da menu/sitemap → URL diretto `bagholderai.lol/income`, non indicizzata. Build e publish disaccoppiati. Razionale Max: le altre 3 fonti sono a €0 da 3 mesi a prescindere dal trading, quindi la storia onesta non dipende dal go-live.

**D2 — I grafici visualizzano attenzione e costi, NON l'income.** A €0 una torta dell'income è indisegnabile; fingere fette uguali su una pagina di trasparenza sarebbe una bugia → torta income come template "fantasma", torte vere su attention/costi. *(Poi Max ha giustamente ricordato: è uno scaffold privato, si costruisce per i dati futuri — la torta income resta come template che si popola da sé.)*

**D3 — Costi in € primari, $ sul totale** (rate ~1.11). Claude Max = **€270/$300 per i 3 mesi** ($100/mese × 3), non $100 secco — coerente con "Spent to date".

**D4 — Sezione costi = il colpo da KO.** "€274 per fare €0" è la versione più onesta e più forte della pagina; mirror diretto dell'ispirazione QuickBooks (expense donut) che Max ha proposto.

## 5. Anti-assenso (§7)

- **Park trigger non scaduto a calendario**: il brief diceva "implementa quando esiste timeline go-live concreta", che non esiste (go-live gated dal mercato, nessuna data). Segnalato → Max ha riformulato (IH prerequisite + €0 da 3 mesi) → build ora/publish dopo.
- **"Non si può fingere un grafico sulla pagina della trasparenza"** → segnalato; Max ha corretto la mira: scaffold privato, costruisci per i dati futuri (avevo messo paletti da pagina pubblica su una privata).
- **Conflitto IH post-mainnet** (BUSINESS_STATE §) vs riga IH del brief → risolto "costruisci ora, lancia IH dopo"; nessuna modifica a BUSINESS_STATE.

## 6. Stato

**PRIVATO / scaffold.** Live solo all'URL diretto, `noindex`, fuori da menu+sitemap, adesivo WIP. Niente di pubblico finché il CEO non decide di pubblicare.

## 7. Decisioni aperte — per il CEO

1. **Quando pubblicare?** (togliere noindex + teaser home "Passive income so far: €0 — here's why →" + voce menu + sitemap). Oggi è scaffold privato.
2. **Indie Hackers timing**: il brief lo dava come prerequisito di `/income`; BUSINESS_STATE lo dà post-mainnet. Pagina pronta, IH non lanciato. Decisione CEO.
3. **Automazione fonti** (proposta CC, in ordine): Umami (visite) **auto subito** — connettore già esistente; Trading via query a go-live; Payhip/BMC **al primo euro** (a €0 darebbero "0" → trappola over-engineering); A-ADS no API (Max valuta di sostituirlo). Approvi quest'ordine?
4. **Framing pubblico "burn vs revenue"**: mostrare "spendiamo €274 per fare €0" è potente ma è anche un dato che alcuni leggerebbero come "non sta funzionando". On-brand con la trasparenza radicale — ma è scelta tua.
5. **Substack & GEO**: il FAQ-schema (GEO) NON si importa su Substack (JSON-LD on-site, piattaforma chiusa); il cross-post porta solo corpo+firma, canonical resta a BHAI (corretto). GEO portabile = solo un'eventuale FAQ visibile nel corpo.

## 8. Cosa NON fatto / parcheggiato

- Automazione fonti (vedi §7.3) — al go-live.
- Ritocchi estetici (colori, P&L assoluto $ vs % di rendimento) — rimandati al go-live, decisione Max.
- Connettori Payhip/BMC — non costruiti (a €0 inutili).

## Roadmap impact

`/income` è l'artefatto pubblico della **domanda #2** del blueprint. Parcheggiato fino ad automazione + go-live + decisione CEO sulla pubblicazione. Nessun tocco a backend/bot/trading. Nessun restart.
