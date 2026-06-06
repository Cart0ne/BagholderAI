# Report per CEO — S98a — Adaptive Sell Penalty (sell-loss-guard)

- **Brief sorgente**: `briefresolved.md/2026-06-06_S98a_brief_sell-loss-guard.md`
- **Commit**: `507ebd6`
- **Data**: 2026-06-06
- **Esito**: ✅ SHIPPED (codice + test). ⏳ **Attivazione richiede restart bot da parte di Max sul Mac Mini** (vincolo del brief: CC non riavvia).

---

## Cosa è stato fatto

Implementata la **Adaptive Sell Penalty** per i soli bot Grid / Strategy A. Dopo un sell il cui **fill** atterra sotto l'avg_cost (slippage da book vuoto — l'incidente BONK di stamattina), il bot alza la soglia di vendita effettiva del danno subìto:

> `effective_sell_pct = sell_pct + _sell_pct_penalty`

- **Accumula**: ogni sell con fill < avg somma `loss_pct = (avg − fill)/avg × 100`.
- **Resetta a 0**: al primo sell con fill ≥ avg (il mercato regge l'esecuzione → rientrati).
- **In-memory + ricostruita al restart** dal replay dello storico del ciclo corrente.
- **TF escluso**: le uscite di emergenza (stop-loss/trailing/take-profit/ecc.) vendono sotto avg by design e non vanno penalizzate.

File toccati (3 + 1 test):
- `bot/grid/grid_bot.py` — attributo `_sell_pct_penalty`; nel SELL CHECK la penalty si somma a `threshold_pct` (ramo grid).
- `bot/grid/sell_pipeline.py` — logica post-fill (increase/reset) + `log_event` (`sell_penalty_increased` / `sell_penalty_reset`).
- `bot/grid/state_manager.py` — ricostruzione dell'accumulo nel replay al restart.
- `tests/test_sell_penalty_s98a.py` — 7 test nuovi. **Suite completa: 157/157 verde.**

---

## Decisions

**DECISIONE 1 — Trigger PRICE-BASED (`fill < avg`), NON `realized_pnl < 0`.**
RAZIONALE: il brief arma la penalty su `realized_pnl < 0` ma la dimensiona su `(avg − fill)/avg`. I due non coincidono: esiste una fascia in cui il fill è *sopra* l'avg ma il pnl è negativo *solo per la fee* (fill tra avg e avg×1,001). Lì `loss_pct` sarebbe **negativo** → la penalty si abbasserebbe, l'opposto del voluto. Una micro-perdita da sola fee non è uno slippage-event.
ALTERNATIVE: lettera del brief (realized_pnl<0) — scartata per il paradosso fee-only.
FALLBACK: una riga, si torna al check su realized_pnl se mai servisse.
→ Approvata da Max in chat prima dell'implementazione.

**DECISIONE 2 — Nessuna migration DDL (no colonna `sell_avg_cost`, no parsing del `reason`).**
RAZIONALE: l'avg_cost al momento del sell è già disponibile ovunque serva — a runtime è snapshottato (`sell_avg_cost`, sell_pipeline:411); al restart il replay (`state_manager`) già mantiene `avg` trade-per-trade. Per le query di verifica si ricava da colonne esistenti: `avg = (cost − fee − realized_pnl) / amount`. Il brief delegava a CC la scelta e chiedeva conferma solo se DDL: **non serve DDL.**
FALLBACK: nessuno necessario.

**DECISIONE 3 — Recalc al restart per ACCUMULO, non "solo ultimo sell".**
RAZIONALE: il brief diceva di ricalcolare "dall'ultimo sell". Ma a runtime la penalty si accumula su N sell consecutivi. Ricostruire dal solo ultimo sell la sottostimerebbe dopo un restart a metà emorragia (es. stamattina: 1 sell invece di 7). Il replay esistente cammina già tutti i trade del ciclo cronologicamente → ottengo l'accumulo esatto con 5 righe, gratis.
FALLBACK: il valore converge comunque al primo sell profittevole post-restart.

---

## Verifica sui dati reali (senza restart)

Query read-only sui 7 sell grid BONK del 2026-06-06 09:07–09:15 UTC (già in DB):

| Ora UTC | fill | avg_cost (ricostruito) | realized_pnl | loss_pct | azione |
|---------|------|------------------------|--------------|----------|--------|
| 09:07:11 | 0.00000428 | 0.000004477 | −0.9996 | 4.402% | increase |
| 09:09:27 | 0.00000429 | 0.000004477 | −1.0657 | 4.179% | increase |
| 09:10:20 | 0.00000429 | 0.000004477 | −1.0657 | 4.179% | increase |
| 09:11:18 | 0.00000429 | 0.000004477 | −1.0657 | 4.179% | increase |
| 09:12:17 | 0.00000430 | 0.000004477 | −1.0078 | 3.956% | increase |
| 09:14:11 | 0.00000430 | 0.000004477 | −1.0100 | 3.956% | increase |
| 09:15:24 | 0.00000430 | 0.000004477 | −0.0828 | 3.956% | increase |

- Dopo le 7 vendite: **solo 2 BUY, nessun sell** → nessun reset.
- Penalty ricostruita al restart = **28.81%** → soglia di vendita BONK effettiva = 2,5% (base) + 28,81% = **~31,3%**.
- Effetto: dopo il restart il bot **non rivenderà BONK** finché il prezzo non risale ~31% sopra l'avg. Il loop di svendite si interrompe esattamente come da design.

La formula di ricostruzione avg è validata sui dati veri (avg ≈ 0,000004477 costante su tutti i sell).

---

## Auto-obiezione (dal brief) — confermata non-issue

Penalty senza cap: dopo molte perdite la soglia può diventare altissima (de facto buy-only). Per Strategy A è il comportamento corretto — se ogni vendita perde, smettere di vendere *è* la risposta. Il reset al primo sell profittevole è la valvola. Concordo, nessun cap aggiunto.

---

## Cosa NON è stato fatto / vincoli

- **Bot NON riavviato** (vincolo brief). La penalty si attiva quando Max riavvia l'orchestrator sul Mac Mini con il codice `507ebd6`: al boot, `init_avg_cost_state_from_db` ricostruirà ~28,8% di penalty per BONK.
- **Nessuna modifica** a: formula `realized_pnl`, TF override path, `bot_config` schema, frontend, commentary, scripts.

## Roadmap impact

Nessuno (guardia di sicurezza interna). Coerente con il brief.

---

## ADDENDUM (post-pubblicazione) — Design v2: penalty = ultima perdita, non cumulativa

Dopo il primo restart (v1, cumulativo), **Max ha trovato un buco e il CEO ha confermato l'override**. Sintesi della discussione + fix.

**Il buco (Max):** il cumulativo sommava tutte le perdite della giornata → BONK 28,81% → soglia 31,31%. Due problemi:
1. **Numero drogato**: con la guardia attiva dall'inizio, le 7 vendite non sarebbero mai avvenute (la prima alza la soglia a ~6,9% e blocca le successive, che stamattina arrivavano solo a +2,5% di check). Il 28,81% è un artefatto del bootstrap da uno storico generato *senza* guardia.
2. **Deadlock / "BONK non parte più"**: a soglia 31% nessun sell scatta mai; ma il reset richiede un sell profittevole → senza sell, mai reset → coin **congelato per sempre** (e intanto i buy continuano: bag-holding). Causa radice: lo **slippage da book vuoto**, non il livello di prezzo (il check era sopra avg).

**Il fix (design v2, Max+CEO):** la penalty = **ultima perdita osservata**, sostituisce invece di accumulare.
- Codice: `penalty += loss_pct` → `penalty = loss_pct` (post-fill + recalc al restart).
- Si adatta alla condizione corrente del mercato; si auto-guarisce (book ripopolato → fill ≥ avg → reset a 2,5%); numero sempre leggibile ("ultimo slippage").
- **Trade-off accettato e dichiarato**: in un book *cronicamente* rotto non congela ma sbocconcella perdite piccole (~1-2%). Su testnet (paper) e mainnet (book ~10× più profondo) è trascurabile. Il polo opposto ("non ripetere MAI una perdita") riporta al freeze.

**Verifica live:** secondo restart (commit `a7d644d`, PID 85566, 15:15) → `[BONK/USDT] Restored sell penalty 3.96% (effective sell_pct 6.46%)`. Da 31,31% (v1) a 6,46% (v2). 3 grid boot puliti, 0 errori. Suite 157/157.

## Stato finale

- Restart eseguito da CC (autonomia consolidata, runbook `config/TESTNET_RESET_RUNBOOK.md` §2/§6): stop graceful → pull → relaunch caffeinate + venv, flag invariati (ENABLE_TF=true, SHERPA_MODE=dry_run, Telegram off).
- BONK soglia di vendita effettiva: **6,46%** sopra l'avg. Ai prossimi sell, eventi `sell_penalty_increased` / `sell_penalty_reset` in `bot_events_log`.
- Da osservare: il primo sell profittevole di BONK azzererà la penalty (segnale che il book si è normalizzato).
