# RforCEO — phantom-holdings-audit (S97a)

**Da:** CC (Claude Code) · **A:** CEO + Max (Board) · **Data:** 2026-06-05 · **Sessione:** S97a
**Brief sorgente:** `briefresolved.md/2026-06-05_S97a_brief_phantom-holdings-audit.md`
**Commit:** `6ff7d6f` (audit core) + `068fe7c` (2 punti aggiuntivi) · **Esito:** ✅ FIXATO & deployato · ⏳ round-trip sell-side da confermare al primo sell reale

---

## Sintesi

Audit sistematico richiesto dal CEO dopo che in S96b i bug phantom (`state.holdings` usato al posto di `managed_holdings`) erano emersi uno alla volta. Fixati **tutti** i punti dove `state.holdings` (saldo wallet, include il regalo testnet) guidava decisioni economiche o calcoli P&L. **Regola applicata:** decisioni/calcoli → `managed_holdings`; mutazioni + snapshot holdings (event-detail, bot_state_snapshots) + log diagnostici → `state.holdings` (verità wallet). Su mainnet phantom=0 → tutti i cambi sono no-op per il go-live.

## Punti fixati (🔴)

**sell_pipeline.py:** unrealized P&L; pending-liquidation detection; **cluster sell-amount 250-342** (skip guard, `force_all`, fallback, dust-prevention residual) — vedi sotto; fully-sold detection (535/537); holdings_value_before.

**grid_bot.py:** 7 gate liquidazione/stop (`and state.holdings>0`); gate posizione nel main loop (791); **force-liquidate sell_amount (838)** — ora managed, **commento 73c aggiornato**; cycle_closed detection; RE-ENTRY-vs-RECALIBRATE (managed); log liquidazione.

**buy_pipeline.py:** gate Strategy A "non comprare sopra avg" (63).

**liquidation.py:** l'intero handler — una sola variabile (`holdings`, riga 214) alimenta guard "niente da liquidare" + cost basis + sell_amount + realized. Era il punto più pericoloso: con phantom vendeva il regalo e calcolava realized spazzatura **identico all'incidente S96b**, ma nel handler standalone.

## Punti trovati OLTRE il brief (segnalati come da brief)

1. **Cluster sell-amount sell_pipeline 250-342** — il brief §2 copriva solo la fully-sold detection, non la *determinazione* del sell amount. Confermato da Max+CEO: stessa famiglia del bug avg-cost di S96b ma sul lato sell. Incluso.
2. **`grid_runner/__init__.py:335`** (gate+log boot "Sell trigger") e **`dust_handler.py:23`** (log write-off over-riportava il dust con phantom) — trovati con un grep più largo dello scope del brief. Cosmetici (gate mascherato da `avg>0`; log), nessun cambio comportamento. Fixati (`068fe7c`).

## Decisione 73c aggiornata (force-liquidate)

Il brief 73c (S73) faceva vendere `state.holdings` su force-liquidate ("chiude l'esposizione totale"). S96b ha dimostrato che vendere il phantom = realized spazzatura. Max+CEO: la 73c era pre-scoperta del problema phantom, la S97a la aggiorna. Commento nel codice allineato così non resta una trappola.

## Verifica

- ✅ **Nessuna regressione**: boot pulito, 3 grid attivi, posizioni managed ricaricate correttamente.
- ✅ **Split managed/phantom corretto** (es. BTC managed 0.003167 / phantom 1.0008 / wallet 1.00396; avg $62.616).
- ✅ **Logica re-entry/recalibrate su managed**: log mostra `managed=X (wallet=Y)`, modalità RECALIBRATE corretta (managed>0).
- ✅ **Grep finale**: ogni `state.holdings` residuo è mutazione, definizione `managed_holdings`, snapshot wallet o log diagnostico voluto.
- ⏳ **Round-trip sell-side (realized realistico, fully-sold a managed=0, re-entry)**: richiede un sell reale. Mercato bearish = i grid accumulano, un sell può richiedere tempo. Per la **regola S96b non dichiaro questa parte "fatta" senza un trade vero** — la confermo al primo sell e aggiorno. Il rischio è basso: realized = (price−avg)×managed con sell_amount capato su managed, e managed+avg sono verificati corretti con dati reali.

## Vincoli rispettati

Non toccati: `state_manager.py`, definizione `managed_holdings`, mutazioni `+=/-=`, Sentinel/Sherpa/TF/NewsKeeper.

## Riferimenti

- Catena: S96a clean slate → S96b avg-cost+fee → **S97a audit** (chiude la famiglia phantom)
- File: `bot/grid/{sell_pipeline,grid_bot,buy_pipeline,dust_handler}.py`, `bot/grid_runner/{__init__,liquidation}.py`
