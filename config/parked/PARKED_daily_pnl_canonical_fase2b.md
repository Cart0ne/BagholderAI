# [PARKED] `daily_pnl` canonico al cutover Kraken (grafico §3 "sul binario dell'hero")

**Data:** 2026-07-18 · **Parcheggiato:** 2026-07-18 (S119b) · **Autore:** Claude Code (Intern)
**Origine:** Max ha notato che il grafico §3 "Performance" della dashboard pubblica mostrava **+$25.27 · +4.21% "if we sold everything today"** mentre l'hero (net worth live, canonico) diceva **−$22** — due numeri sulla stessa pagina che si contraddicono.
**Stato:** **Fix lato sito SHIPPED** (`73de256`, S119b): numerone + fine curva ora sul P&L canonico live (= hero); curva de-biased ($25 Kraken + fee tolti). **Residuo lato bot → questo brief, da fare INSIEME alla Fase 2b.**
**Trigger di sblocco:** **Fase 2b (cutover Kraken go-live)** — quando il grid passa alle righe Kraken, riparte con capitale fresco e il bot viene comunque riavviato.

---

## 0. TL;DR (3 righe)

Il grafico §3 pesca la sua **linea storica** dagli snapshot serali che il bot scrive in `daily_pnl` (una riga/sera, ~20:00). Questi snapshot **non stanno sul binario canonico** dell'hero: (a) contano i **$25 Kraken** nel budget grid (da 17-lug: `initial_capital` 500→525), (b) sono **lordi di fee**, (c) trascinano un **~$8 di deriva dust-reset storica** (pre-S113) incastonata nella cassa del ciclo testnet corrente. Il fix lato sito (già shippato) corregge il **numerone** (ora onesto) e de-biasa la curva, ma il **trail resta sul rail-snapshot** → l'ultimo segmento include quel residuo oltre al calo reale. **La cura definitiva è far nascere il `daily_pnl` già pulito**, e il momento naturale è la **Fase 2b** (restart già dovuto + ciclo nuovo = drift azzerata).

---

## 1. Perché proprio alla Fase 2b (e non ora)

Intervenire ora sul bot in testnet sarebbe **spreco**: tra pochi giorni si va live, il grid riparte sulle righe Kraken con **capitale fresco** e **tutti i contatori ripartono da zero**. Quindi:

- Il **restart** del bot (costo dell'intervento) è **già pagato** dal cutover.
- La **deriva dust-reset storica** (~$8, accumulata **prima** del Piano A S113 e incastonata nella cassa di `testnet_2`) **sparisce da sola** col nuovo ciclo — **niente backfill** dello storico testnet (che diventa storia ritirata; la sua visualizzazione è già gestita dal fix lato sito).
- Le **righe Kraken sostituiscono** le binance → è il momento in cui `initial_capital` va comunque ricalcolato sul lineup nuovo.

**In una riga:** non tocchiamo il testnet; facciamo nascere il `daily_pnl` del ciclo Kraken già canonico.

## 2. Dove nasce il problema (codice)

Il bot scrive lo snapshot in `bot/grid_runner/daily_report.py:147-159` (`pnl_tracker.record_daily(...)`), con i valori di `portfolio_summary` (da `bot/grid_runner/lifecycle.py` `_build_portfolio_summary` / `get_grid_state`). I tre scostamenti dal canonico:

1. **`initial_capital` = Σ `capital_allocation` di TUTTE le righe grid** → il 17-lug ha inglobato i $25 della riga Kraken (`BTC/USD`, `is_active=false`), passando 500→525 (verificato a DB: 42 giorni a 500, 1 a 525). Serve che sommi **solo le righe attive del venue/collaudo in corso** (stesso spirito del pin `venue=binance` messo sul sito in S119b).
2. **`total_value` lordo di fee** — è `cash + holdings + skim`; l'hero canonico fa `... − fees`. Da decidere se allineare (vedi §3 punto B).
3. **Deriva dust-reset (~$8)** — storica pre-S113 nella cassa di `testnet_2`. Il **meccanismo** è già chiuso (Piano A S113 `8d2fdd6`: l'avg operativo non si azzera più sulla polvere). **Da VERIFICARE** che sul ciclo Kraken nuovo il `daily_pnl` nasca senza drift (il churn-fix fu validato su binance; confermarlo su venue kraken).

## 3. Cosa fare alla Fase 2b

**A. `initial_capital` = solo righe attive del collaudo** (fix del leak $25 lato bot). **← punto singolo, alto valore.**
Il leak è UNA riga: `commentary.py:503-514` `get_grid_state` fa `bot_config.select(...).eq("managed_by","grid")` **senza filtro venue/is_active** → `grid_budget = Σ capital_allocation` ingloba la riga collaudo Kraken ($25) → `initial_capital = 525` (il commento in-code dice esplicitamente "Inactive coins still contribute their slice"). Fix = aggiungere `.eq("venue","binance")` alla query (riga 506), **stesso identico fix già fatto sul sito** (`GRID_BUDGET` venue-filtered, commit `f6388b6`).
**⚠️ `get_grid_state` è CONDIVISO**: alimenta sia lo snapshot `daily_pnl` sia il **daily report Telegram** (`_build_portfolio_summary` → `get_grid_state`, `bot/grid_runner/lifecycle.py:122`). Quindi **questa singola riga sana ENTRAMBE le superfici** (grafico §3 storico ciclo-nuovo + report Telegram = MTL **T.3**). Il cycle è già a posto (`get_current_cycle` globale pinnato `venue=binance`, `db/client.py:45`).

**B. Decisione: `daily_pnl.total_value` net-of-fee?**
Se lo allineiamo al canonico (`− fees`), il grafico §3 diventa perfettamente sul binario dell'hero **senza** la toppa frontend. Trade-off: cambia la semantica storica di `total_value` (finora lorda). Decisione CEO/Board. Alternativa: lasciarlo lordo e tenere la de-bias lato sito (già in piedi).

**C. Verifica no-drift sul ciclo Kraken.**
Primo giorno di `daily_pnl` Kraken: confrontare `total_value` con il replay canonico (stesso check della sim S119b). Deve combaciare a meno del rumore prezzo. Se non combacia → il Piano A non copre il path Kraken, da indagare.

**D. Cleanup frontend (opzionale, dopo A–C).**
Con `daily_pnl` pulito alla fonte, la de-bias aggiunta in S119b (`total_pnl − Σ fee` + override endpoint) diventa **ridondante** per il ciclo nuovo: si può semplificare la §3 di `web_astro/src/scripts/dashboard-live.ts` (tornare a `total_value − budget` sul ciclo canonico). Da fare **solo** dopo aver verificato C, e **senza** rompere la visualizzazione dello storico testnet (che resta sul vecchio rail). Valutare se tenere l'override-endpoint-live comunque (è comunque più onesto del "as of ieri sera").

## 4. Cosa NON fare

- **Nessun backfill** dello storico `daily_pnl` di `testnet_2` (storia ritirata; display già gestito dal fix S119b).
- **Nessun intervento sul bot testnet ora** (decisione Max, 2026-07-18): si aspetta il restart del cutover.
- Non confondere con **Fix B** (`PARKED_realized_pnl_avg_cost_fixB.md`): quello è `trades.realized_pnl` a DB avg-cost puro (trigger pre-mainnet, tocca buy-guard/ladder/skim). **Fratello** di questo (stessa famiglia deriva dust-reset), ma superficie diversa (`trades` vs `daily_pnl`). Se si fanno insieme pre-mainnet, coordinare.

## 5. Riferimenti

- Fix lato sito shippato: commit **`73de256`** (S119b §3) + **`f6388b6`** (S119b rimozione $25 dal budget pubblico + grid.html Kraken-aware).
- Piano A churn-avg-fix (meccanismo dust-reset chiuso): `config/2026-06-30_S113_brief_churn-avg-fix.md`, commit `8d2fdd6`.
- Fratello: `config/parked/PARKED_realized_pnl_avg_cost_fixB.md`.
- Fase 2b (contenitore): PROJECT_STATE §3 "Kraken — stato Fasi 0-4 (K.1)"; nodo 5 + runbook finestra coordinata.
- Sim di verifica S119b (curva canonica): logica in `web_astro/src/scripts/dashboard-live.ts` §3 (buildDailySeries + override endpoint).
