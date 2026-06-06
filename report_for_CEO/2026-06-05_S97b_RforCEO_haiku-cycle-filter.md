# Report per CEO — S97b — haiku-cycle-filter — 2026-06-05

**Da:** CC (Claude Code) · **A:** CEO
**Brief sorgente:** `briefresolved.md/2026-06-05_S97b_brief_haiku-cycle-filter.md`
**Commit:** `feaf61d` (bot+regen) · `efbd196` (dashboard cycle+600) · `827db88` (post) · `2e056a4` (cycle-start = Jun 5) · `3880d56` (era-aware archive day)
**Runtime Mac Mini:** orchestrator riavviato 2026-06-05 22:52 con codice bot `feaf61d` (= commentary fix, già in `827db88` pullato pre-restart); i commit successivi sono solo frontend. Repo allineato a session HEAD col pull finale. (Drift §1 `2167c37` corretto.)
**Esito:** SHIPPED + restart orchestrator + commentary di oggi rigenerato e verificato

---

## Cosa chiedeva il brief
Il daily commentary di Haiku scriveva dati cross-ciclo dopo il clean slate S96a
("Day 29", "$400 underwater", "-24.89%"): leggeva testnet_1 + testnet_2 insieme.
Gap nel perimetro S96a (che aveva coperto grid bot/reserve/reconcile/dashboard
ma non il generatore del commentary).

## Cosa ho fatto (scope esteso oltre il brief, vedi sotto)

### 1. Commentary Haiku (brief core) — `commentary.py` + `bot/grid_runner/daily_report.py`
- **Filtro ciclo** su tutte le query P&L/skim: `get_grid_state`, `get_tf_state`
  e i rispettivi `reserve_ledger` ora filtrano `cycle = get_current_cycle()`.
- **Day-count data-driven** (nuovo `get_cycle_start_date`): Day 1 = primo trade
  del ciclo corrente, non più ancorato a date hardcoded (Mar 30 / May 8).
- **Prompt facts data-driven**: gli anchor "Day 1 = May 8 / TF paused since May 8"
  ora sono iniettati dalla data d'inizio ciclo → si auto-aggiornano al prossimo
  reset. **Tono invariato** (territorio S93a).

### 2. Dashboard (flag tuoi/Max in chat) — `dashboard.astro` + `dashboard-live.ts`
- **NET REALIZED PROFIT**: la query inline non filtrava il ciclo → sommava
  testnet_1+2 (+$9.02 stale). Aggiunto `cycle=eq.testnet_2` (come grid.html).
- **Badge NET WORTH su basis 600** (Grid $500 + TF $100), supera la scelta S72
  "Grid-only $500". TF è fermo nel ciclo (0 trade) → il P&L in $ è identico,
  cambia solo il denominatore %; net worth mostra l'aggregato, self-consistente
  (netWorth − P&L = started).
- **Grafico §3 cycle-scoped**: il grafico performance riparte dal ciclo corrente
  (era cross-ciclo).
- **"DAY N" per CONTESTO** (regola Max, dopo 2 tentativi sbagliati — vedi sotto):
  i numeri SOLDI ripartono col ciclo (card NET WORTH/Grid/TF, grafico, home
  LIVE SNAPSHOT → oggi ≈ Day 2); i numeri PROGETTO/diario restano progressivi
  dal lancio v3 (CEO-log "Earlier from the log" → oggi ≈ Day 69, archivio
  Apr 3 = Day 5). Ancore separate `CYCLE_START_ISO` vs `V3_LAUNCH_ISO`.

### 3. Post blog
- `thirty-two-hours` pubblicato (`draft:false`). Build verde, 19 pagine.

## Verifica
- `scripts/regen_commentary_now.py` (nuovo, solo-commentary no Telegram) eseguito
  sul Mac Mini → commentary di oggi rigenerato:
  `Cycle=testnet_2 · Day 1 · Grid NW $488.45 · P&L −$11.55`, aggregato −1,93%
  (= −11,55/600, coerente col basis dashboard). Haiku ha pure narrato il salto
  come "reset the clock", non come recovery.
- Orchestrator riavviato (procedura documentata, flag identici) → 7 brain attivi,
  runtime `2e056a4` → il report schedulato delle 20:00 userà il codice corretto.

## Anti-assenso (obiezione reale sollevata)
Il brief diceva "fix meccanico, non toccare il prompt". **Non era solo meccanico**:
gli anchor di data nel prompt ("Day 1 = May 8") sono *fatti*, non tono — anche
filtrando le query, Haiku avrebbe continuato a dire "Day 29" perché il valore
glielo passavamo noi e il prompt lo confermava. Su tua conferma (Max) ho reso
quei fatti data-driven, lasciando intatto il tono.

## Decisioni delegate a Max (confermate in chat)
1. **Anchor day**: data-driven da inizio ciclo (vs fix-forward minimale).
2. **Grafico §3**: incluso nel cycle-filter (coerenza con resto pagina).
3. **Regen**: solo commentary, niente re-send Telegram.
4. **"DAY N" per contesto** (chiarito da Max in revisione): SOLDI → riparte col
   ciclo; PROGETTO/diario → progressivo dal lancio sito. Contraddice il brief
   S97b ("Day 1 ovunque") → Max ha l'ultima parola. Ho sbagliato 2 volte prima
   (tutto-ciclo, poi tutto-progetto) → versione finale = per-contesto.

## Scoperta inattesa
La data d'inizio ciclo NON è il 4 giugno (clean slate) ma il **5 giugno**: il
primo trade testnet_2 è atterrato oggi, perché il first-buy gate è stato sbloccato
solo in S96b (5/6). Quindi Day 1 = oggi. Ho allineato la costante frontend
`CYCLE_START_ISO` al primo trade reale (Jun 5), così bot/home/dashboard concordano.

## Note minori (non bloccanti)
- Il commentary di oggi confronta "ieri −19,83% → oggi −1,93%": ieri era il dato
  cross-ciclo (codice vecchio), quindi lo "swing" è artefatto del fix, non vero
  recupero. Si auto-corregge da domani (entrambi i giorni cycle-filtered). La
  riga vecchia resta in DB ma nascosta dalla dedup-per-data della dashboard.
- CEO-log archivio: ora i numeri diario sono progressivi di progetto (V3_LAUNCH),
  quindi le voci vecchie tornano coerenti col loro testo (Apr 3 = Day 5). Risolto.

## Roadmap impact
Nessuno. Fix interno + coerenza dashboard, nessun cambio di funzionalità pubblica.
