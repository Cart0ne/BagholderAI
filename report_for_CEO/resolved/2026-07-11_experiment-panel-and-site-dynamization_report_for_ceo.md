# Report for CEO — S117: Experiment data panel + sito interamente data-driven

**Data:** 2026-07-11 · **Sessione:** S117 (estemporanea, guidata da Max — nessun brief CEO sorgente)
**Commit:** `a616e13` → `b674eb7` (9 commit, tutti pushati) + 3 migration cloud Supabase
(`s117_passive_income_anon_update`, `s117_books_block_and_data_refresh`, + policy UPDATE)
**Bot/processi Mac Mini:** NON toccati. Nessun restart. Lavoro solo web/admin/DB-policy.

---

## TL;DR

Il filo conduttore della sessione: **eliminare ogni label statica dalle superfici pubbliche**.
La pagina The Experiment (/income) ora si aggiorna interamente da Supabase tramite un
pannello manuale in admin.html (con conversione USD→EUR automatica a cambio BCE); il
grafico "Test history" è stato sostituito da un burn chart money-out-vs-money-in (codice
vecchio archiviato); la homepage è stata ripulita dai fossili; l'ufficio ha una mini-board
"Overhead" (monito per i bot) e la board del CEO è stata ridisegnata (fine mele-e-pere);
il ciclo (`testnet_2`) non è più cablato in 6 file — il sito legge `bot_config.cycle`.
**Rituali mensili eliminati: 2** (aggiornamento cifre /income via CC; bump del cycle in 6 file).

## 1. Cosa è stato shippato

| Commit | Cosa |
|---|---|
| `a616e13` | **Experiment data editor** in fondo ad admin.html: le 11 righe di `passive_income` (costi/revenue/traction) editabili con Save per riga. Policy `anon UPDATE` (solo UPDATE: INSERT/DELETE verificati bloccati), stesso pattern di trend_config/bot_config, guardia anti-RLS-silenzioso (lezione 39i). |
| `cd2752f` | **Conversione USD automatica**: `$1.75` nel campo Value → EUR a cambio BCE live (frankfurter.dev, fallback 1,11), Displayed auto-compilato. Elimina la conversione a mano dei costi API. |
| `13011ef` | **/income 100% DB-driven**: nuovo block `books` (views per volume 25/69/39 → donut), KPI Conversion calcolato (133 views → 0 sales, sales letti dal detail della riga Books), label Visitors generica + sotto-etichetta dal DB ("Umami · All time"), didascalie ricostruite dai dati, totali $ a cambio BCE, fallback HTML neutralizzati (GEO: i crawler non leggono più cifre di giugno). Riga traction rinominata "Store views" (272). |
| `9c09be1` | **Burn chart** "Money out vs money in" sostituisce Test-history P&L: 2 linee cumulative dal 18 mar (costi diluiti uniformemente — convenzione dichiarata in didascalia; revenue piatta a €0, può andare sotto zero col trading live). Zero tabelle nuove: deriva dai totali `passive_income`. **Il vecchio grafico è conservato** con istruzioni di rigenerazione in `web_astro/archive/2026-07-11_income_test-history-pnl-chart.md` (inclusa la serie PAPER irrecuperabile) — indicizzato in KNOWLEDGE_MAP §9. |
| `dd53b74` | **Homepage**: rimossa costante placeholder morta (147 trades/+$84.21/182d), fallback bot-card neutralizzati (era il record testnet_1 visibile ai crawler), **sticker "Fresh start" automatico** (data = primo trade del ciclo corrente da DB, visibile 42gg post-reset poi si ritira e si ri-arma da solo al prossimo reset). |
| `0ddb2cd` | **Ufficio — mini-board "Overhead"** (idea Max): parete fondo-sinistra, totale spese fisse live da `passive_income` (−€368 · ~€97/mo) + monito *"Earn it back, bots." — CEO*. Click → /income. |
| `35b453a` | **Ufficio — board CEO ridisegnata**: una sola metrica (Total P&L $ su base $600), riga di riferimento "net worth · basis", colonna "by fund" (GRID/TF in $, somma esatta al titolo), gruppo "unrealized" per coin separato ed etichettato, sparkline scoped "grid fund · 7d" con ampiezza minima $12. Risolve i 5 problemi di chiarezza (mele-e-pere in primis, confermati da Max). |
| `bc77a0e` | Sticker: non copre più la riga "TF +$x", rotazione −5°, emoji+testo su baseline unica (pulci di Max da screenshot). |
| `b674eb7` | **Cycle data-driven**: `testnet_2` era cablato in live-stats.ts, dashboard-live.ts (+`CYCLE_START_ISO`), LabRoom.jsx, dashboard.astro, grid.html, admin.html → tutti leggono ora `bot_config.cycle` (riga grid BTC, fallback all'ultimo ciclo noto se il fetch fallisce). **Un solo `UPDATE bot_config SET cycle=...` muove l'intero sito.** |

**Dati aggiornati da Max col nuovo pannello** (primo collaudo reale, riuscito): Claude Max
€270→€360 (4° mese), Haiku €5.07, Grok €1.07 (entrambi via conversione $ automatica),
visite → all-time 1.730, store views 272. Totale esperimento: **~€368 spesi / €0 incassati**.

## 2. Decision log (sintesi — dettaglio in PROJECT_STATE §4)

1. **Write-path admin = anon UPDATE policy** (pattern grid/tf esistente), non RPC con password server-side. Obiezione sicurezza ritirata dopo verifica del precedente: i parametri bot (già anon-writable) sono più sensibili delle cifre di una pagina vetrina. INSERT/DELETE restano chiusi. Rollback: `DROP POLICY`.
2. **Views per volume = righe DB (block `books`)**, non costanti nel codice: editabili dal pannello, Vol 4 futuro = 1 migration.
3. **Burn chart a diluizione uniforme** (niente tabella mensile): i totali cumulativi bastano, convenzione dichiarata sulla pagina; se un giorno servisse il dettaglio mese-per-mese si aggiunge un ledger senza rompere nulla.
4. **Cycle dalla riga grid BTC di bot_config** (deterministica), non da una tabella nuova: la fonte esiste già, il bot la usa già; fallback letterali = solo paracadute.

## 3. ⚠️ Da sapere PRIMA del test live Kraken di domani

1. **Il sito pubblico ora segue `bot_config.cycle` in tempo reale.** Se il test cambia il
   cycle sulle righe grid, homepage/dashboard si agganciano subito al ciclo nuovo
   (contatori da Day 1, sticker "Fresh start" che riappare). Test "in sordina" ⇒ righe/tag
   separati. Da decidere esplicitamente in fase di setup del collaudo.
2. **Flip manuali che restano** (per il cutover comunicativo, cfr. `COLLAUDO_COMMS_GUIDELINES_v1.md`):
   `IS_TESTNET` in TestnetBanner.astro, tile "budget $600 testnet" in homepage, basi fondi
   500/100 nei file. Candidato naturale al primo brief post-collaudo.
3. **Audit Area 2 — trigger event-based**: l'ultimo A2 è del 19-giu (22 giorni, backstop 60 ok),
   ma il collaudo Kraken è vicino alla categoria "pre-mainnet" di AUDIT_PROTOCOL §2.
   Segnalo al CEO/Board la valutazione se schedularlo prima del cutover vero (non del
   test di domani).

## 4. Roadmap impact

**Nessuno.** Il lavoro di sessione è site/admin tooling non tracciato come task di fase in
roadmap.ts (verificato: nessun task Go Live/Marketing/Dashboard toccato; "Switch from
paper to live" resta correttamente todo). Versione roadmap invariata (1.50).

## 5. Cosa NON è stato fatto

- Il refactor cycle NON tocca tf.html (non filtra per cycle) né i consumer Python lato bot
  (già data-driven da S97b).
- Nessun intervento su Validation & Control System (nessun check nuovo da registrare).
- Le label residue di /income segnalate come "ok così" (budget $600, card volumi, hero):
  cambiano solo con eventi (mainnet, pubblicazione volume) che passano comunque da un deploy.
