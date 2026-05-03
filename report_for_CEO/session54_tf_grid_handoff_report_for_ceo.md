# Session 54 — TF→GRID Handoff for Tier 1-2 (tf_grid)

**Data:** 2026-05-02
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Commit:** `502e88a` — pushed to `main`
**Brief origine:** `briefresolved.md/brief_tf_grid_handoff.md` (archiviato dopo deploy)

---

## In una riga

TF ora **sceglie** le coin Tier 1-2 ma le **affida a GRID** per la gestione: niente stop-loss, niente uscite forzate su BEARISH, profit lock come unica uscita automatica. Tier 3 resta gestito da TF come prima.

---

## Cosa è stato deciso in brainstorming (vs brief originale)

Il brief originale è stato deployato **integralmente**, con 3 raffinamenti aggiunti durante la review board:

| # | Punto del brief | Decisione board | Motivazione |
|---|---|---|---|
| 1 | Capitale stuck su sideways prolungato | **Nessun meccanismo aggiuntivo** | Lo SWAP attivo (punto 2) è di per sé il meccanismo di rotazione. Con 1 slot per tier, se lo SWAP funziona, lo stuck si risolve da solo |
| 2 | SWAP disabilitato per tf_grid | **SWAP abilitato con soglie strette** (vs disabilitato come da brief) | Disabilitare lo SWAP creerebbe coin "zombie" indefinitamente bloccate. Soglie: delta strength ≥25 (vs 20), cooldown 48h (vs 8h), breakeven richiesto (vs −1% ammesso) |
| 3 | BEARISH ignorato senza floor di drawdown | **Nessun circuit breaker** | Allocazioni piccole ($40 Tier 1, $35 Tier 2) e siamo in paper trading. Il "costo di apprendimento" è zero. Si rivaluterà al go-live mainnet |
| Bonus | (non nel brief) | **Telegram report con tag mode + età allocazione** | Visibilità giornaliera per spotare a colpo d'occhio coin che stanno aspettando il profit lock da troppo tempo |

---

## Cosa è cambiato a livello operativo

### Per le coin Tier 1 e Tier 2 (≥$20M volume) — `managed_by = 'tf_grid'`

**Disabilitato:**
- Stop-loss su drawdown
- Uscita forzata su signal flip BEARISH
- Trailing stop
- Take-profit (sostituito dal profit lock)
- Gain saturation (exit dopo N sells)
- SWAP "facile" — ora richiede vantaggio di strength molto alto e posizione in profitto

**Abilitato:**
- Greed decay sells (vendita per-lot a soglie decrescenti col tempo)
- Buy-the-dip su grid percentage
- `stop_buy_drawdown` (blocca nuovi buy su freefall, non liquida)
- Profit Lock al +5% del net PnL — **forzato attivo** per tf_grid indipendentemente dal toggle globale `tf_profit_lock_enabled`

### Per le coin Tier 3 (<$20M volume) — `managed_by = 'trend_follower'`
**Nessun cambiamento.** Stop-loss, trailing, BEARISH exit, gain saturation, SWAP a soglie originali (delta ≥20, cooldown 8h, profit ≥−1%). Comportamento identico a session 53.

---

## Modifiche tecniche (sintesi)

### File Python (4)
- **`bot/strategies/grid_bot.py`** — gate del profit lock e greed decay estesi a `('trend_follower', 'tf_grid')`; `force_liquidate` cascade aggiornato; reason del trade differenziato per tf_grid (PROFIT-LOCK / MANUAL EXIT)
- **`bot/trend_follower/allocator.py`** — `apply_allocations()` setta `managed_by` per tier (1-2 → tf_grid, 3 → trend_follower); BEARISH→DEALLOCATE skippato per tf_grid; SWAP usa soglie distinte per tf_grid (`SWAP_TF_GRID_STRENGTH_DELTA=25`, `SWAP_TF_GRID_COOLDOWN_HOURS=48`, `SWAP_TF_GRID_MIN_PROFIT_PCT=0.0`)
- **`bot/trend_follower/trend_follower.py`** — Telegram TF scan report ora include sezione "Active allocations" con tag 🟢 GRID / 🔵 TF, capital deployato, età posizione (ore o giorni)
- **`bot/grid_runner.py`** — hot-reload TF safety params + initial_lots cycle + dealloc_reason + cycle summary tutti estesi a tf_grid

### File Web (3)
- **`web/tf.html`** — query bot_config + trades estese a `(trend_follower, tf_grid)`; coin card con badge verde "GRID" sui tf_grid
- **`web/dashboard.html`** — query TF section estese a entrambi i mode; query home (manual) escludono entrambi
- **`web/grid.html`** — query admin esclude entrambi i mode TF

### DB
**Nessuna migrazione.** `bot_config.managed_by` è una colonna text che già accetta valori arbitrari. L'unica novità è la stringa `'tf_grid'`.

---

## Smoke test eseguiti

- `python3.13 -m py_compile` su tutti i 4 file Python → OK
- Import `bot.strategies.grid_bot` + `bot.trend_follower.allocator` → OK
- Costanti SWAP tf_grid lette correttamente: `STRENGTH_DELTA=25.0`, `COOLDOWN_HOURS=48`, `MIN_PROFIT_PCT=0.0`
- `bot.grid_runner` e `bot.trend_follower.trend_follower` non importabili in test isolato per un problema preesistente del venv (`telegram._utils.datetime` mancante con la versione di python-telegram-bot installata in `venv/`). Sintassi verificata via `py_compile`. Sul Mac Mini con il venv di produzione il bot dovrebbe importare normalmente — Max conferma al primo restart.

---

## Cosa monitorare (data-first, ~2 settimane)

Ai sensi della regola "data-first then formal review" (memory feedback), si raccolgono dati live per ~2 settimane prima di valutare modifiche aggiuntive. Punti di attenzione:

1. **Profit Lock fire rate** sui tf_grid: quante coin raggiungono +5% net PnL? In quanto tempo medio?
2. **Coin "zombie"**: ci sono tf_grid che restano allocate >2 settimane senza fire del profit lock? Se sì, l'opzione SWAP a soglia 25 sta liberando lo slot o no?
3. **Drawdown massimo osservato** su tf_grid: senza floor, qual è il peggior PnL toccato? Avvicina la soglia "−15% per più di 5 giorni" che avevamo discusso?
4. **BEARISH ignorato su trend reali**: se una tf_grid va BEARISH e poi continua a salire (caso SPK) → confermiamo l'ipotesi. Se va BEARISH e continua a scendere → quanto perdiamo?
5. **SWAP attivati**: il delta=25 + cooldown 48h + breakeven è troppo restrittivo? Quanti SWAP scattano in 2 settimane?

---

## Limiti noti / Cose NON fatte

- **Min_notional check** sulle sell verificato durante brainstorming: validate_order() controlla solo i buy, non i sell. Per tf_grid non è un problema (profit lock svuota tutto, eventuale dust <$5 viene marcato `cycle_closed`). Confermato safe da brief 45c v2 che ha già corretto l'allocazione 40/35/25 per dare margine.
- **Nessun alert Telegram dedicato "tf_grid stuck"** (es. "coin X in tf_grid da 7 giorni senza profit lock fire"). Non implementato perché lo scan report già mostra l'età di ogni allocation. Se in 2 settimane risulta poco visibile, si aggiunge.
- **Nessuna migrazione di coin già attive**: se al momento del deploy una Tier 1-2 è già allocata come `trend_follower`, resta `trend_follower` finché non viene de-allocata e ri-allocata. La migrazione avverrà naturalmente al primo SWAP/BEARISH/profit lock.
- **`web_astro` non toccato**: il nuovo sito Astro è ancora WIP (sessione 2 chiusa il 2026-05-02), non ha ancora le query bot_config. Quando il dashboard live verrà portato lì, andrà replicato lo stesso filtro.

---

## Per il go-live mainnet (memo)

Quando si passerà da paper trading a mainnet con allocazioni 10x, riconsiderare:
- Aggiungere un **circuit breaker estremo** su tf_grid (es. liquida se PnL ≤ −30% secco, una sola soglia non un trailing)
- Eventuale **time-based review** sulle posizioni stuck >14 giorni
- Riconsiderare il profit lock al 5%: con allocazioni più grandi, una soglia più alta o decadente nel tempo potrebbe essere più appropriata

---

## Diff statistico
```
8 files changed, 648 insertions(+), 38 deletions(-)
```

Il grosso delle insertions è il brief stesso archiviato in `briefresolved.md/` (~500 righe). Le modifiche di codice nette sono ~150 righe.

---

**Stato:** ✅ Deployato su `main`, in attesa di restart bot sul Mac Mini per andare live.
