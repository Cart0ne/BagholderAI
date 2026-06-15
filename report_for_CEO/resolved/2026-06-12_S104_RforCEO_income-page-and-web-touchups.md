# Report for CEO — S104 — income experiment page + web touch-ups

**Data:** 2026-06-12
**Sessione:** S104 (web/marketing, guidata da Max in diretta — non monobrief)
**Da:** CC
**Per:** CEO (Claude)

**Brief sorgente:**
- `config/2026-06-07_S100a_brief_passive-income-dashboard.md` (parked → sbloccato da Max)
- `config/2026-06-12_S103b_brief_blog-noncoder-5brains.md` (CEO) — ⚠️ etichettato S103b ma lo scope S103b era già usato (`..._dashboard-brain-cards`); essendo questa S104, il presente report è S104.
- Ritocchi Sherpa-card e /dashboard: richieste estemporanee di Max (nessun brief).

**Commit:** `83bfe52` (/income) · `0c95507` (Sherpa card + dashboard) · `a4c8676` (blog publish) · `c456833` (blog table→list + nomi) · (+ `9826026` docs S103a, era rimasto da pushare). Tutti su `main`, pushati.

---

## TL;DR

Sessione web/marketing. Costruita la pagina **/income "The Passive Income Experiment"** come **scaffold privato** (noindex, fuori da menu/sitemap, adesivo WIP) — da riempire/automatizzare e pubblicare al go-live. Aggiornata la **card Sherpa** in home alla realtà LIVE (S102b/S103a). Sistemata la **numerazione + spaziatura** del /dashboard. **Pubblicato** il post blog two-voice "How a Non-Coder Manages 5 AI Brains" e reso **portabile per il cross-post** (tabella→lista, nomi reali). + verifica dati su 4 vendite testnet.

---

## 1. /income — "The Passive Income Experiment" (scaffold privato)

Sblocco del brief S100a parcheggiato. **Decisione Max**: costruire ora, **pubblicare quando decidiamo** (al go-live / automazione). Le altre fonti di reddito sono a €0 da 3 mesi a prescindere dal trading, quindi la storia onesta non dipende dal go-live.

**Cosa c'è (tutto data-driven da nuova tabella Supabase `passive_income`, blocchi `revenue`/`traction`/`cost`, RLS anon-read):**
- 4 **badge KPI**: Revenue €0 · Spent ~€274 · Conversion 0% · Visitors ~575/30g
- barre **Attention vs Money** (contrasto, non scala condivisa)
- **card per income stream** (Books/Tips/Ads/Trading)
- 2 **torte**: *Income by source* (oggi €0 → "fantasma" della struttura futura, si riempie da sola) + *Attention by book* (dati reali: Vol2 50/91 views)
- **Running costs** (torta spese stile QuickBooks): Claude Max €270 domina · Haiku/Grok/Domain · Infra €0 → totale **€274 (~$304)**. È il colpo: *spendiamo €274 per fare €0*.
- **Test history** — grafico 3 linee P&L: **Paper** (29 mar→7 mag, +€69, recuperata dal backup S67) · **Testnet v1** · **Testnet v2 (live)**, con i reset visibili.
- adesivo storto **🚧 Work in progress** in cima.

**Stato:** `noindex` + fuori da menu/sitemap → URL diretto `bagholderai.lol/income`, non indicizzata. Migration applicate al cloud via MCP (`s100a_passive_income`, `s100a_passive_income_add_cost_block`); **non ancora specchiate in `db/*.sql`** (vedi §Non fatto).

## 2. Card Sherpa (home) — allineata a LIVE

Era stale (DRY_RUN, 3 params, look "locked"). Aggiornata: **MODE LIVE**, **PARAMS 7** (3 tuning + 4 freni S103a), **ADJUST live** (conteggio cambi parametro da `config_changes_log`, oggi 55/7d), look **promosso ad ACTIVE** (via dim + "?") **mantenendo il badge TEST** (decisione Max: "attivo ma in test", coerente: opera ma su testnet).

## 3. /dashboard — numerazione + spaziatura

- **Numerazione gerarchica** (scelta Max): 1 · 2.1 traders · 2.2 brains · 3 · 4 · 5 · 6 Reconciliation (prima due "§ 2" duplicati e Reconciliation senza numero).
- **Bug spaziatura**: l'header "2.2 brains" era incollato alla box NET REALIZED PROFIT — `.db-sec-h { margin: 0 0 18px }` azzerava l'`mt-14` voluto. Fix: `margin-bottom: 18px`.

## 4. Blog "non-coder-5-brains" — pubblicato + reso cross-post-safe

Eseguito brief CEO (intro Max, riga Tuner senza "dry-run", firma "— Max & Claude", `draft:false`, data 12-giu). **Poi**, su richiesta Max: **tabella → lista** (le tabelle markdown si rompono su Substack/Medium) e **nomi generici → reali** ("Tuner"→**Sherpa**, "News classifier"→**NewsKeeper**, tenute le funzioni come keyword). Allineata FAQ #3.

---

## Decisioni (le non-banali)

**D1 — /income: i grafici visualizzano attenzione e costi, NON l'income.**
RAZIONALE: a €0 una torta dell'income è indisegnabile; fingere fette uguali su una pagina di trasparenza radicale sarebbe una bugia. → torta income come "template fantasma", torte vere su attention/costi. *(Nota: Max ha poi giustamente ricordato che è uno scaffold privato → costruire per i dati futuri, non auto-castrarsi; la torta income resta come template che si popola.)*
FALLBACK: la pagina è data-driven, tutto si riempie da sé all'arrivo dei numeri.

**D2 — Claude Max a €270/$300 per i 3 mesi** ($100/mese × 3), non $100 secco. Coerente con "Revenue/Spent to date". Confermato da Max.

**D3 — Sherpa card: ACTIVE ma badge TEST.** Coerente con "opera davvero su testnet, non ancora mainnet". (Alt scartate: promozione piena LIVE; lasciare solo i dati.)

**D4 — Blog: override degli OFF-LIMITS del brief CEO** (corpo + FAQ) per portabilità cross-post. Fatto su **autorità Max (veto)**, segnalato qui per la catena. Senza, la tabella si sarebbe rotta su Substack e i lettori non avrebbero riconosciuto Sherpa/NewsKeeper.

---

## Anti-assenso (§7)

- **Park S100a non scaduto a calendario**: il trigger era "timeline go-live concreta", che non esiste (go-live = nessuna data, gated dal mercato). Segnalato → Max ha riformulato (IH prerequisite + €0 da 3 mesi) → build ora/publish dopo.
- **"Non si può fingere un grafico sulla pagina della trasparenza"** → Max ha corretto: è scaffold privato, costruisci per i dati futuri. Avevo messo paletti da pagina pubblica su una privata.
- **Conflitto IH post-mainnet** (BUSINESS_STATE) vs riga IH del brief → risolto "costruisci ora, lancia IH dopo": nessuna modifica a BUSINESS_STATE.
- **Verifica 4 vendite testnet** (BONK×3 + SOL): display ✓ combacia col DB al centesimo. Le 3 BONK in perdita (−$1.07) sono **slippage testnet ~4%** su book sottile (trigger di profit-taking corretto, fill sotto avg), **non un bug**. Su mainnet (slippage 0,1-0,3%) sarebbero profitti. È esattamente il TODO **[S90 Option C — slippage buffer sul percentage-sell path]**, evidenza fresca pre-mainnet.
- **Collisione naming S103b** (due brief stesso tag) segnalata.

---

## Aperto per il CEO

- **Quando pubblicare /income?** (togliere noindex + teaser home + menu + sitemap). Oggi è scaffold privato.
- **Indie Hackers**: il brief lo dava come prerequisito di /income; BUSINESS_STATE lo dà post-mainnet. Per ora /income costruita ma IH non lanciato. Decisione CEO sul timing.
- **Automazione fonti /income**: solo il connettore **Umami** esiste già; Payhip/BMC andrebbero costruiti (a €0 darebbero "0" → trappola over-engineering). Proposta CC: Umami auto subito, Payhip/BMC al primo euro. A-ADS no API (Max valuta di sostituirlo).
- **Substack & GEO**: il FAQ-schema (GEO) **non** si importa su Substack (è JSON-LD on-site, piattaforma chiusa). Il cross-post porta solo corpo+firma; canonical resta a bagholderai.lol (corretto). Eventuale GEO portabile = sezione FAQ visibile nel corpo (oggi è solo frontmatter) — scelta di contenuto CEO.

## Roadmap impact

- /income = artefatto pubblico della **domanda #2 ("un'AI genera passive income?")**, parcheggiato fino ad automazione + go-live.
- Post blog LIVE (marketing). Nessun tocco a backend/bot/trading. Nessun restart.

## Non fatto / housekeeping

- **PROJECT_STATE** non ancora rigenerato per S104 (CLAUDE.md [1]) — da fare a chiusura.
- **Migration `passive_income`** applicate al cloud (MCP) ma non specchiate in `db/*.sql`.
- **Brief S103b/blog** da archiviare in `briefresolved.md/` (+ sanare la collisione nome).
- Ritocchi estetici /income (colori, % vs $ sul P&L) rimandati al go-live (decisione Max).
