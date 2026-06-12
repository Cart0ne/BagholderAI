Brief S103b — dashboard-brain-cards — 2026-06-12

Basato su: design handoff di Claude Design (allegato zip
`bagholderAI_dashboard.zip`) + decisioni S103.

Questo brief copre DUE modifiche alla dashboard, una privata e una
pubblica. Sono indipendenti — CC può farle in ordine qualsiasi.

---

# PARTE 1 — Dashboard privata (`/admin` → `web_astro/public/admin.html`)

## Cosa cambia

Riorganizzare la sezione PARAMETERS di ogni coin in 3 gruppi visivi
con header colorati, al posto dell'attuale layout piatto.

### Nuovo layout (per ogni coin):

**TRADING PARAMETERS** (header con accento Board)
- Allocation ($)
- $/Trade
- Skim % (Profit Reserve)

**GRID PARAMETERS — BY SHERPA** (header con accento Sherpa)
- Buy %
- Sell %
- Idle Re-entry (hours)

**SECURITY** (header con accento warning/giallo)
- Stop-Buy Drawdown %
- Stop-Buy Unlock (hours)
- Dead-Zone Unblock (hours)
- Min Profit %

### Dettagli implementativi

- Stesso stile dei campi esistenti (input editabili, "Save changes")
- I 3 header usano colori coerenti col sito:
  - TRADING PARAMETERS → colore Board/neutral (grigio-verde come il testo
    attuale "TRADING PARAMETERS")
  - GRID PARAMETERS — BY SHERPA → colore accento Sherpa (`--bot-sherpa`
    o il rosso della card corrente)
  - SECURITY → warning/giallo (`--warn` o arancione attuale ⚠ SAFETY)
- Min Profit si SPOSTA dalla sezione Grid a Security
- Le descrizioni testuali sotto ogni campo restano invariate
- L'ordine dei campi dentro ogni gruppo segue l'ordine listato sopra
- Il pulsante "Save changes" resta UNO per coin (in fondo, come oggi)

### Decisioni delegate a CC

- Markup HTML esatto per gli header di sezione (CC decide)
- Se usare `<fieldset>` con `<legend>` o semplici `<div>` con header

### Decisioni che CC DEVE chiedere

- Nessuna — è un refactor puramente cosmetico del layout esistente.
  Se CC incontra ambiguità, la flagga nel piano.

---

# PARTE 2 — Dashboard pubblica (`/dashboard` → `src/pages/dashboard.astro`)

## Cosa cambia

La sezione §2 "Instruments" passa dalle 3 card statiche dei brain bot
a **card live full-width in layout pipeline verticale**, con dati reali
da Supabase e auto-refresh ogni 5 minuti.

## Design reference

**Il design è stato prodotto da Claude Design ed è completo.**
Il file `bagholderAI_dashboard.zip` contiene:
- `README.md` — specifica completa (layout, token, responsive, wiring)
- `reference/Brain Cards Reference.html` — il contratto visivo pixel-perfect
- `reference/*.svg` — mascot per il mockup (usare i componenti Astro esistenti)

**CC: leggi TUTTO il README.md prima di iniziare.** Contiene:
- Grid layout a 3 colonne (134px / 252px / 1fr) con breakpoint
- Specifiche per ogni widget (NewsKeeper headlines + barometer,
  Sentinel gauge + scores, Sherpa regime badge + coin table)
- Connettori tra card con label BAROMETER (shadow) e REGIME
- Mock data shapes per `dashboard-mock.ts`
- Element IDs per il wiring live in `dashboard-live.ts`
- Nota su `is:global` styles (lezione S82)
- Responsive: 375 / 768 / 1280

### Prerequisito: nuovo token colore

```css
--color-bot-news: #6E68B0;
--color-bot-news-soft: #E2E0F2;
```

Da aggiungere a `@theme` in `global.css` e documentare in STYLEGUIDE §5.

### Stato dei brain bot (aggiornare)

- Sherpa: da DRY_RUN a **LIVE** (pill verde, non più grigia)
- Sentinel: **LIVE** (invariato)
- NewsKeeper: **LIVE** (invariato)

### Sorgenti dati Supabase per il live wiring

| Widget | Tabella | Query |
|--------|---------|-------|
| NewsKeeper headlines | `newskeeper_signals` | ultime 4 righe ORDER BY created_at DESC |
| NewsKeeper barometer | `newskeeper_signals` | barometro v2 (campo barometer_state, rolling 24h) |
| Sentinel gauge + scores | `sentinel_scores` | ultima riga score_type='fast' per risk/opp, ultima score_type='slow' per regime |
| Sentinel BTC strip | `sentinel_scores` | raw_signals.btc_change_1h dal fast score |
| Sherpa regime badge | `sherpa_proposals` | ultima riga, campo proposed_regime → mappa a Defensive/Neutral/Aggressive |
| Sherpa coin table | `sherpa_proposals` | ultime 3 righe (1 per coin), proposed_buy/sell/idle |
| Sherpa last adjustment | `sherpa_proposals` | created_at della riga più recente con would_have_changed=true |

### Mapping regime → posture label

| proposed_regime | Badge label | Badge color tokens |
|-----------------|-------------|-------------------|
| extreme_fear, fear | Defensive | primary / primary-soft |
| neutral | Neutral | neu / neu-soft |
| greed, extreme_greed | Aggressive | warn / warn-soft |

### Mapping regime → coin posture text

| proposed_regime | Posture text |
|-----------------|-------------|
| extreme_fear | buy tight, sell fast, wait long |
| fear | buy cautious, sell early, slow pace |
| neutral | balanced grid, standard pace |
| greed | buy often, let profits run, fast pace |
| extreme_greed | buy every dip, hold for pump, rapid fire |

CC può raffinare queste etichette nel piano — sono indicative, non
contratto. L'importante è che siano comprensibili a un non-tecnico.

### Refresh

Polling ogni 300 secondi (5 min). Al primo caricamento, mock data
visibili server-side (nessun flash vuoto).

---

## Output atteso (entrambe le parti)

1. Piano in italiano (task > 50 righe) — PRIMA di scrivere codice
2. Parte 1: `/admin` con 3 sezioni per coin
3. Parte 2: `/dashboard` con brain cards live + connettori pipeline
4. Token `--color-bot-news` aggiunto
5. Mock shapes in `dashboard-mock.ts`
6. Wiring in `dashboard-live.ts`
7. Report S103b con decisioni prese

## Vincoli — OFF-LIMITS

- NON modificare la logica di nessun brain bot (Sentinel, NewsKeeper, Sherpa)
- NON modificare le tabelle Supabase (nessuna migration in questo brief)
- NON toccare §1, §3, §4, §5 di dashboard.astro — solo §2
- NON inventare hex: usare SOLO token dal STYLEGUIDE
- NON restartare il bot (Max restarta manualmente su Mac Mini)
- Le mascotte usano i componenti Astro ESISTENTI, non gli SVG dal reference

## Impatto roadmap

Nessuno diretto. Se la roadmap mostra ancora "Sherpa: DRY_RUN",
aggiornare a "Sherpa: LIVE" — segnalare nel report.

## Allegato

Il file `bagholderAI_dashboard.zip` va passato a CC insieme a questo
brief. Contiene il design reference completo.

---

## Auto-obiezione CEO

Il brief dipende da query Supabase specifiche (es. barometer_state
da newskeeper_signals). Se lo schema non corrisponde esattamente,
CC si blocca. Mitigazione: il piano in italiano PRIMA del codice
obbliga CC a verificare lo schema reale e a segnalare discrepanze
prima di scrivere. Se il barometro v2 non ha un campo barometer_state,
CC propone alternative (calcolo lato client, o fallback mock).
