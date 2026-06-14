# Report for CEO — office-page — S106

**Data:** 2026-06-14
**Sessione:** S106
**Da:** CC
**Per:** CEO (Claude)
**Brief sorgente:** design handoff `config/bagholderAI dashboard.zip` (→ `design_handoff_office_page/lab-room.jsx` + README) + direzione verbale di Max (titolo + "considerala come /income, privata"). Nessun brief CEO `.md` formale: è un handoff di Claude Design.
**Commit:** `28949f5` (pagina + componente isola + 6 asset SVG + filtro sitemap). Build statica verde, 22 pagine.

---

## 1. Cos'è, e perché esiste

`/office` — **"The AI Lab"** — è la scena animata del **quartier generale dell'azienda**: i 5 agenti (Grid, TrendFollower, NewsKeeper, Sentinel, Sherpa) alle loro scrivanie attorno a **Bag, il CEO**, su un podio. La scena è viva: i bot camminano a confrontarsi, vola un foglio appallottolato Sherpa→Grid, una headline vola alla board che lampeggia, scatta un alert di rischio, l'orologio a muro segna l'ora di Roma reale. È l'incarnazione visiva del claim **"While I sleep, my AI company works."** (titolo voluto da Max, prima persona).

Realizza la vision "ufficio coi bot" che era in roadmap da tempo (memoria `web_astro/office-vision`, sessioni 2-3 mai fatte).

## 2. Cosa è stato costruito

- **Pagina** `web_astro/src/pages/office.astro`: hero (badge + titolo + sottotitolo spostato **sotto** la scena a larghezza piena 1040px, su richiesta Max) + la scena + adesivo 🚧 WIP.
- **Isola React** `web_astro/src/components/office/LabRoom.jsx` (552 righe): port **fedele** del prototipo del handoff — inline-style + keyframes CSS tenuti verbatim. Montata con `client:visible` (stesso pattern di `HowWeWorkInteractive`).
- **6 asset SVG** in `web_astro/public/office/` (i mascot del design, incluso `backpack-sky-40.svg` = Bag CEO, che non era nel sito).
- **Privacy** (identica a /income): `noindex` + riga nel filtro sitemap (`astro.config.mjs`) + nessuna voce di menu. Online solo via URL diretto `bagholderai.lol/office`.

## 3. Dati — cablaggio live (il cuore tecnico)

Su direttiva Max ("tutto quello che si riesce cablato a dati reali"), gli slot dati della scena leggono i **dati veri** via lo **stesso layer canonico** usato da /home e /dashboard (`computeCanonicalState` + `fetchLivePrices`, chiave anon, RLS read-only) — non i numeri-vetrina del mockup:
- **Board "Portfolio Overview"** → net worth reale (Grid+TF ≈ **$607**, identico a /dashboard — non più il `$2.416.892` finto del mockup), per-coin BTC/SOL/BONK con P&L% reale + TOTAL, sparkline da `daily_pnl`. Pallino "live" legato allo stato del fetch.
- **Monitor Sentinel** → `risk_score` reale (= 20). **Monitor Grid** → net realized P&L reale.
- Le altre micro-schermate (candele, radar, news-feed, barre Sherpa) restano decorative (forme astratte, nessuna cifra falsa).
Refresh ogni 60s. Board → link `/dashboard`, Bag-CEO → link `/howwework` (entrambi verificati esistenti); le 5 station → placeholder `#`.

## 4. Decisioni chiave

**D1 — Port fedele, non ricostruzione.** Il README chiedeva esplicitamente di portare `lab-room.jsx` quasi verbatim. Ho tenuto inline-style + `<style>` keyframes così com'erano (zero conversione a Tailwind), adattando solo: import React, token `BH` + keyframes inline, path asset `exports/`→`/office/`, `window.LabRoom`→`export default`. Razionale: massima fedeltà al design approvato, rischio minimo. Fallback: revert `28949f5`.

**D2 — Board cablata al canonico, non al mockup.** Il mockup mostrava `$2.416.892` — su un brand *radical-transparency* è off-brand anche su pagina privata. Cablato al net worth vero (~$607) → coincide col resto del sito (regola one-source-of-truth). Etichetta board "· 24h" → "· live" perché mostro il P&L totale, non un delta 24h (non volevo dichiarare un dato non calcolato).

**D3 — Scaling responsivo + reduced-motion.** La scena è un canvas fisso 1040×630; un `ResizeObserver` la scala alla larghezza della colonna (cap a 1×, mai upscale). Aggiunto un guard `prefers-reduced-motion` (scoped `.office-scene`) che ferma le animazioni non essenziali — era raccomandato dal README e mancava.

**D4 — Bug del handoff corretto.** La IIFE `ROOM` del prototipo ritornava una `s` mai definita (esistono `sx`/`sy`) — nel browser passava per un global residuo, in build SSR lanciava `ReferenceError`. Rimossa (era inutilizzata dai consumer).

## 5. Anti-assenso (§7)

- **CD non conosce i file del repo** e dà nomi inventati (Max lo ha confermato: "io non verifico"). Il valore aggiunto di CC è **tradurre l'intento sui file veri** prima di codare. Sul brief /office: i due link target del README (`/dashboard`, `/howwework`) li ho **verificati esistenti** prima di lasciarli (non rotti).
- **Numero board finto $2.4M**: segnalato come off-brand → cablato al dato reale invece di lasciarlo (vedi D2).
- **Donut/illustrazione a perspective fissa**: su mobile stretto si rimpicciolisce molto; accettabile per una pagina-vetrina, mitigato dallo scaling.

## 6. Stato

**PRIVATO / non lanciato.** Live solo all'URL diretto `bagholderai.lol/office`, `noindex`, fuori menu+sitemap, adesivo WIP. Stesso livello di /income: *non linkata + non indicizzata*, **non** protetta da password (chi conosce l'URL la vede).

## 7. Decisioni aperte — per il CEO

1. **Come strutturare il resto della pagina?** Max non ha ancora deciso (per ora = hero + scena soltanto). Il mockup d'ispirazione aveva anche: barra **ticker live**, striscia valori "One autonomous team. Zero emotions.", footer "Built by AI. Run by AI. For humans." — **non** erano nel handoff (solo la stanza). Le aggiungo quando decidiamo la struttura.
2. **Link delle 5 station**: oggi placeholder `#`. Dove puntano? (es. Grid→/grid? ma è admin-gated; o a sezioni di /howwework?)
3. **Quando pubblicare** (togliere noindex + voce menu + sitemap + eventuale teaser home).
4. **Auth-gate?** Se vogliamo che /office sia davvero riservata (come admin/grid/tf, password SHA-256) invece che solo non-linkata: è lavoro in più, da decidere.

## 8. Cosa NON fatto / parcheggiato

- Ticker live + striscia valori + footer claim del mockup (vedi §7.1) — al momento di decidere la struttura.
- Deep-link delle station (placeholder `#`).
- La sparkline della board usa il net-worth del solo Grid (`daily_pnl`, ~$507) mentre il numero grande è Grid+TF (~$607): la *forma* è corretta, è una mini-spark senza valori assoluti; allineabile se dà fastidio.
- Lo zip del handoff (`config/bagholderAI dashboard.zip`) lasciato untracked (materiale sorgente, non codice sito).

## Roadmap impact

`/office` è l'artefatto pubblico-in-attesa che racconta **come lavora l'azienda** (i 5 brain + il CEO), complementare a `/howwework` (i ruoli). Parcheggiato fino a: struttura del resto della pagina + decisione CEO sulla pubblicazione. Nessun tocco a backend/bot/trading. Nessun restart.
