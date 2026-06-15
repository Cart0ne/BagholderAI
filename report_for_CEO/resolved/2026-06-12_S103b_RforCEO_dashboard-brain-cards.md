# Report S103b — dashboard-brain-cards — 2026-06-12

**Brief sorgente:** `config/2026-06-12_S103b_brief_dashboard-brain-cards.md`
(+ Max ha allargato lo scope: anche le card **TF/Grid**, design nel copia-zip
`Trade Cards Reference.html`)
**Commit:** `638d1e4` (redesign) + `0d6e1a0` (fix post-review)
**Migration:** `s103b_newskeeper_regime_anon_read` (RLS read-only — vedi §3)
**Build:** `npm run build` verde (19 pagine)
**Esito:** SHIPPED — review locale di Max OK → push + deploy live (Vercel)

---

## 1. Cosa è stato fatto

**PART 1 — `grid.html`** (editor per-coin): i 3 gruppi parametri etichettati per
ownership post-S103a — **Trading — by Board** (allocation/$-trade/skim) ·
**Grid — by Sherpa** (buy/sell/idle) · **⚠️ Security — by Sherpa** (stop-buy
dd/unlock, dead-zone, **Min Profit** — spostato qui da Grid). Header Grid
ricolorato col rosso-Sherpa.

**PART 2 — `/dashboard` §2 pubblica**: le 5 card statiche → **righe live
full-width in pipeline** in ordine di flusso. THE TRADERS: TF → Grid + connettore
+ barra "Net realized". THE BRAINS: NewsKeeper → Sentinel → Sherpa + 2 connettori.
Ogni card: mascot-plate + identity + rail/numeri live. Trader: net worth +
**sparkline 7g** + chip monete + empty-state TF onesto. Brain: headlines+barometro,
gauge F&G+risk/opp+strip, badge regime+tabella per-coin. **Polling 5 min.** Tutti
i brain **LIVE** (niente più DRY_RUN). Token nuovo `--color-bot-news` (+soft) in
`global.css` + STYLEGUIDE §5. Grammatica card in `<style is:global>` mappata ai
token (i nodi ricostruiti via JS non portano lo scope Astro — lezione S82).

**Roadmap** Phase 3: Sherpa DRY_RUN → LIVE (S102b 3 strategy + S103a 4 protective).

## 2. Anti-assenso (§7) — drift del brief verificati e corretti

1. **PART 1 file sbagliato**: brief diceva `admin.html`, ma l'editor con "Save"
   è in **`grid.html`** — e **già a gruppi** (non "piatto" come assumeva il brief).
   Delta reale minuscolo (spostare Min Profit + relabel), non una riorganizzazione.
2. **3 query brain del brief errate** (auto-obiezione CEO fondata, verificate a DB):
   barometro = `newskeeper_regime.state` (NON `newskeeper_signals.barometer_state`,
   inesistente); headlines = `summary`+`polarity` (smallint); Sentinel
   `btc_change_1h`/`funding_rate` = colonne (fast), `regime`/`fng_value` in
   `raw_signals` (slow). **Nessuna migration di schema** (come da vincolo).
3. **Ownership labels**: il brief etichettava Security come neutra; post-S103a è
   Sherpa-managed → "by Sherpa" (confermato da Max).

## 3. Decisioni / deviazioni dal brief

**Decisione 1 — riuso del motore dati trader.** I numeri TF/Grid (net worth,
unrealized, fees, skim, cash, chip) restano su `computeCanonicalState` esistente
(id invariati): zero rischio di rompere numeri già corretti, solo presentazione
nuova. RAZIONALE: il brief dava per nuovo il wiring trader, ma esisteva e
funzionava. FALLBACK: revert `638d1e4`.

**Decisione 2 — niente mock objects in `dashboard-mock.ts`.** Uso i **default
server-side inline** nel markup come fallback (stesso scopo "no flash", stesso
pattern dei trader esistenti). Aggiungere oggetti mock = codice morto.

**Decisione 3 — "Last update: X ago"** invece di "Last adjustment" via
`would_have_changed`: in LIVE le righe `sherpa_proposals` sono battiti, quel flag
sarebbe stale → mostro la freschezza dell'ultima riga (≤4h).

**Deviazione autorizzata da Max — RLS su `newskeeper_regime`.** Il brief diceva
"niente modifiche DB", ma il barometro era **morto sul sito pubblico**: la tabella
non aveva policy di lettura anon (a differenza delle 3 sorelle), la query tornava
`[]` → restava il placeholder "Neutral" mentre il valore vero è "Bearish".
Migration `s103b_newskeeper_regime_anon_read`: 1 policy `anon SELECT` read-only,
identica alle sorelle. **Nessun cambio schema.** Verificato: barometro ora serve
"bearish" via chiave anon. (Scovato durante la review locale testando le query
reali con la chiave pubblica.)

**Fix post-review** (`0d6e1a0`): micro-label Sherpa "dd/unlock/window" → "buy/sell/idle"
(i numeri mostrati sono i 3 strategy, non i security).

## 4. Verifica dati (review locale, query reali con chiave anon)

Tutta la §2 è **dati reali e live** (no mockup): trader da trade+prezzi Binance;
headlines reali; Sentinel Extreme Fear/Risk 26/Opp 20/BTC −0.60%; Sherpa
Defensive + parametri per-coin reali; barometro Bearish (dopo il fix RLS).
Sparkline Grid da `daily_pnl` (7g); TF flat (idle, onesto).

## 5. Off-limits rispettati
NON toccati: §1/§3/§4/§5 di dashboard.astro · logica dei brain bot · schema DB ·
mascot (componenti esistenti, colori brand) · nessun hex inventato (solo token) ·
nessun restart bot.

## 6. Per il CEO (non lo tocco io)
`BUSINESS_STATE` da aggiornare a tua iniziativa: (a) §7 stale su Sherpa 3/7→7/7
(già segnalato in S103a); (b) §2 marketing — la dashboard pubblica ora mostra i
5 bot live in pipeline (prima erano card statiche), possibile gancio narrativo.
