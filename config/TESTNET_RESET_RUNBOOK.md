# Runbook — Reset mensile Binance Testnet

**Creato:** 2026-06-05 (S96b), con la procedura collaudata tra S96a (4 giu) e S96b (5 giu).
**Scopo:** il testnet Binance azzera i wallet ~1 volta/mese senza preavviso. Questo runbook trasforma la gestione del reset da "giornata di debug" a checklist. **La macchina è già pronta** (cycle tagging + phantom-safe avg-cost + fee opzione B): il prossimo reset è quasi solo un'operazione DATI.

> Convenzione ciclo: i cicli si chiamano `testnet_1`, `testnet_2`, … Al prossimo reset si passa a `testnet_3`. In questo runbook chiamo **N** il ciclo che si chiude e **N+1** quello nuovo. Sostituisci con i numeri reali.

---

## 0. Cosa è GIÀ risolto (NON ri-debuggare)

Questi bug sono stati chiusi in S96a/S96b — il prossimo reset NON li ripresenta:
- **Phantom holdings** (il "regalo" di baseline del testnet): `avg-cost`, gate primo-acquisto e cap-vendite usano `managed_holdings` → il bot bootta pulito (managed=0), compra con avg corretto, e la guardia 72a **passa** (surplus, non deficit). Vedi `buy_pipeline.py:237`, `grid_bot.py:910`.
- **Fee testnet = 0**: il testnet post-reset non addebita commissioni; il bot **sintetizza** `FEE_RATE` 0,1% (opzione B) → P&L realistico. Vedi `buy_pipeline.py` (`synth_fee`), `sell_pipeline.py`.
- **Spam orchestrator** dopo i 5 restart: guard `if info.gave_up: continue` (`orchestrator.py`).
- **Reconcile**: `reconcile_binance.py` non segnala falso DRIFT quando Binance torna fee=0.

**Conseguenza:** al prossimo reset spesso basta **bumpare il ciclo** e riavviare. Niente migration (la colonna `cycle` esiste già), niente fix di codice.

---

## 1. Riconoscere il reset (2 min)

Sintomi: i grid non comprano ("skipping first buy" sparito ora, ma controlla), un coin bloccato dalla guardia 72a, fee=0, P&L strani.

Conferma (read-only):
```bash
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && ./venv/bin/python3.13 scripts/reconcile_binance.py'
```
→ Se tutti i symbol sono `WARN_BINANCE_EMPTY` con **0 drift, 0 binance_orphan** = è il reset (benigno, nessun furto/corruzione).

Saldi wallet post-reset (il "regalo" di baseline) — opzionale, già visibili nei boot log come `Boot reconcile NOTE (surplus)`.

---

## 2. Stop orchestrator (1 min)

```bash
ssh max@Mac-mini-di-Max.local 'PID=$(pgrep -f "python.* -m bot.orchestrator" | head -1); echo "stop $PID"; kill -TERM $PID; pkill -f "caffeinate.*bot.orchestrator"; sleep 9; ps aux | grep grid_runner | grep -v grep | grep -oE "symbol [A-Z]+/USDT" || echo FERMI'
```
(NewsKeeper e x_poster NON vanno fermati — non c'entrano col reset.)

---

## 3. Foto ricordo del ciclo che si chiude (2 min)

Legge l'ultimo stato del ciclo N e logga un evento `testnet_reset_clean_slate` (materiale per diary/Volume). Via Supabase MCP (project `pxdhtmqfwjwjhtcoacsn`):

```sql
-- 3a. Leggi i valori (per ciascun grid symbol)
SELECT s.symbol, s.holdings, s.avg_buy_price, s.realized_pnl_cumulative, s.cash_available,
       (SELECT count(*) FROM trades t WHERE t.symbol=s.symbol AND t.cycle='testnet_N') trades_n,
       (SELECT COALESCE(sum(amount),0) FROM reserve_ledger r WHERE r.symbol=s.symbol AND r.cycle='testnet_N') reserve
FROM bot_state_snapshots s
WHERE s.cycle='testnet_N' AND s.symbol IN ('BTC/USDT','SOL/USDT','BONK/USDT')
  AND s.created_at = (SELECT max(created_at) FROM bot_state_snapshots s2 WHERE s2.symbol=s.symbol AND s2.cycle='testnet_N');

-- 3b. Inserisci 1 evento per symbol (category='lifecycle', severity='warn').
-- Vedi il template completo in report_for_CEO/2026-06-04_S96a_RforCEO_clean-slate-testnet.md
INSERT INTO bot_events_log (severity,category,symbol,event,message,details)
VALUES ('warn','lifecycle','<SYM>','testnet_reset_clean_slate','...', jsonb_build_object('cycle_closed','testnet_N','new_cycle','testnet_N+1', ...));
```

---

## 4. Apri il nuovo ciclo — lato DB (1 min)

I trade/snapshot/reserve del ciclo N restano taggati `testnet_N` (archiviati, consultabili). Si apre il nuovo:
```sql
UPDATE bot_config SET cycle = 'testnet_N+1' WHERE managed_by = 'grid';
```
Questo è l'unica cosa che il **bot** ha bisogno di sapere: `get_current_cycle()` lo legge da qui. Il replay al boot filtrerà `testnet_N+1` (vuoto) → stato pulito.

> **NON cancellare** i dati del ciclo N. (Se per un bug fosse stata scritta spazzatura, vedi §7.)

---

## 5. Apri il nuovo ciclo — lato sito (5 min)

Le dashboard hanno il ciclo **hardcoded** in una costante (vedi memoria "site redesign" / la `const CYCLE`). Bumpa `testnet_N` → `testnet_N+1` in:
- `web_astro/src/scripts/live-stats.ts` → `const CYCLE = "testnet_N+1"`
- `web_astro/src/scripts/dashboard-live.ts` → `const CYCLE = "testnet_N+1"`
- `web_astro/public/grid.html` → 3× `cycle=eq.testnet_N+1`
- `web_astro/src/components/CleanSlateSticker.astro` → aggiorna la data ("✨ Fresh start · <nuova data>")
- `web_astro/src/pages/dashboard.astro` → "Clean slate since <nuova data>"

Poi: `cd web_astro && npm run build` → commit → push su `main` (Vercel auto-deploy).

> **Miglioria futura** (toglie questo passo): far leggere alle dashboard il ciclo corrente da `bot_config` (come fa il bot) → il reset diventa puro DB, niente redeploy.

---

## 6. Restart + verifica (3 min)

```bash
# pull del codice (se ci sono fix nuovi) + restart
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull --ff-only origin main; nohup caffeinate -i -s -- env ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=dry_run SENTINEL_TELEGRAM_ENABLED=false SHERPA_TELEGRAM_ENABLED=false /Volumes/Archivio/bagholderai/venv/bin/python3.13 -m bot.orchestrator >> logs/orchestrator.out 2>&1 & echo "PID $!"'
```

**Verifiche (queste sono quelle che oggi sono costate tempo — falle SEMPRE):**
1. **3 grid attivi**, nessun loop di restart, niente spam Telegram.
2. **Boot pulito**: nei log `grid_<SYM>_USDT.log` → `Boot reconcile NOTE (surplus)` (NON `FAILED`), `holdings=0`, `Cash restored ... = <capitale pieno>`.
3. **Primo buy con avg e fee corretti** (il bug di oggi era qui!):
```sql
SELECT symbol, side, cost, fee, ROUND((fee/cost*100)::numeric,4) AS fee_pct
FROM trades WHERE cycle='testnet_N+1' ORDER BY created_at DESC LIMIT 6;
```
   → `fee_pct` deve essere **0.1000** (non 0). E l'avg-cost deve essere ≈ prezzo di acquisto (il sell trigger nei log ≈ +2.7% sopra, **non** un valore assurdo tipo $50 su BTC).
4. **Round-trip reale**: al primo SELL vero, `realized_pnl` deve essere realistico (centesimi), **non** ~l'intero costo. (Regola CC: su modifiche al core P&L, verificare un trade reale, non solo "per costruzione".)
5. `reconcile_binance.py` dry-run → pulito.

---

## 7. Se ci fosse spazzatura da un bug (cleanup, raro)

Solo se trade/skim/snapshot palesemente sbagliati sono finiti nel nuovo ciclo (es. un bug nuovo). Sono artefatti, non storia → si cancellano:
```sql
DELETE FROM trades WHERE cycle='testnet_N+1';
DELETE FROM reserve_ledger WHERE cycle='testnet_N+1';
DELETE FROM bot_state_snapshots WHERE cycle='testnet_N+1';
DELETE FROM daily_pnl WHERE cycle='testnet_N+1';
-- bot_config.cycle resta testnet_N+1. Poi restart → ri-bootta pulito.
```
(Ogni cleanup+rebuy accumula un po' di coin nel wallet come phantom — innocuo, è testnet.)

---

## 8. Close-out

- **PROJECT_STATE §10**: riga "Sessione shipped" col reset gestito + commit + restart.
- **BUSINESS_STATE**: solo su istruzione Max/CEO (territorio strategico).
- **Report CEO** se il reset ha richiesto decisioni (naming `YYYY-MM-DD_SXX_RforCEO_<scope>`).
- Memoria: aggiorna [[reference_binance_testnet_reset]] se cambia qualcosa.

## Riferimenti
- Storia completa: `report_for_CEO/2026-06-04_S96a_RforCEO_clean-slate-testnet.md` (clean slate) + `2026-06-05_S96b_RforCEO_avgcost-dilution-and-fees.md` (avg-cost + fee).
- Migration originale: `db/migration_20260604_s96a_clean_slate_cycle.sql`.
- Codice phantom-safe: `bot/grid/buy_pipeline.py`, `bot/grid/state_manager.py`, `bot/grid/grid_bot.py`.
