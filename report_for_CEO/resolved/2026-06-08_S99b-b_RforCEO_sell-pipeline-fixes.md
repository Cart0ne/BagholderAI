# Report S99b-b — sell-pipeline-fixes — 2026-06-08

**Brief sorgente:** `config/2026-06-08_S99b-b_brief_sell-pipeline-fixes.md`
**Report a monte:** `2026-06-08_S99b_RforCEO_sell-ladder-audit.md` (stessa sessione, investigativo).
**Commit base:** `564ee3f` (main, post git pull). Commit di shipping di questa sessione: vedi git log (citato nel messaggio finale a Max).
**Esito:** SHIPPED Parti A + B + C. Suite **160/160** (era 157 + 3 nuovi test). Migration applicata. Restart Mac Mini necessario per Parte C.

---

## Anti-assenso (CLAUDE.md §7)

Una obiezione **bloccante** sollevata prima di codare (restore al restart) + 2 note non bloccanti. Tutte risolte con Max prima dell'implementazione:

- **Obiezione restore (Parte C):** la penalty è in-memory e al restart viene ricostruita dal replay di `trades` ([state_manager.py](bot/grid/state_manager.py)). Il replay sa ricalcolare il **caso-perdita** (`price < avg`, entrambi noti) ma **non lo slippage**: il `check_price` pre-ordine non è una colonna strutturata in `trades` (vive solo nel `reason`, già noto come inaffidabile [S70]). → **Decisione Max/Board: Opzione 1** — non ripristinare la slippage-penalty al restart; si ri-arma da sola al primo sell reale. Diff minimo, rischio minimo, coerente con "penalty = condizione corrente di mercato".
- **Nota segno slippage:** il codice aveva già `slippage_pct = (fill−check)/check` (segno opposto). Ho introdotto `adverse_slippage_pct = (check−fill)/check` (positivo quando il fill è peggiore del check).
- **Nota eventi:** `slippage_below_avg` (fill<avg) e il nuovo `sell_penalty_slippage` (fill≥avg) sono mutuamente esclusivi per costruzione → nessuna duplicazione di log.

---

## Parte A — Fix testo dashboard

- **File:** [web_astro/public/grid.html:1102](web_astro/public/grid.html#L1102). Sostituita la stringa SUBLABEL `sell_pct` (fossile FIFO "Per-lot trigger…") col testo approvato dal Board: *"Sell trigger: sells a slice when price rises this % (net of fees) above the cycle reference — the average buy cost on the first sell, then each prior sell's price (the 'sell ladder'). Single average cost, not per-lot."*
- Web-only, zero logica. Chiude il gap Phase 9 V&C ("dashboard coherence" non copriva i SUBLABEL testuali).

## Parte B — Penalty visibile in NEXT SELL IF

- **Migration applicata:** colonna `sell_pct_penalty numeric` (nullable) in `bot_runtime_state` (`add_sell_pct_penalty_to_bot_runtime_state`). Additiva, zero impatto su righe esistenti.
- **Runtime mirror** — [bot/grid_runner/runtime_state.py:38-43](bot/grid_runner/runtime_state.py#L38): il bot scrive `sell_pct_penalty` nel payload ogni tick (`float(_sell_pct_penalty) or None`).
- **Dashboard** — [web_astro/public/grid.html:954-961](web_astro/public/grid.html#L954): legge `rtState.sell_pct_penalty`, calcola `effectiveSellPct = sellPct + penaltyPct` e lo usa nel trigger. La fetch è `select=*` → nessuna modifica alla query. Su coin senza penalty (SOL 8 giu, penalty 0) il valore mostrato è **identico** a prima.

## Parte C — Penalty anti-slippage (3 casi)

- **Costante** — [bot/grid/sell_pipeline.py:42-51](bot/grid/sell_pipeline.py#L51): `SLIPPAGE_PENALTY_THRESHOLD_PCT = 1.0` a livello modulo (non in bot_config, come da brief — safety parameter, no hot-reload).
- **Logica** — [bot/grid/sell_pipeline.py:524-600](bot/grid/sell_pipeline.py#L524): blocco penalty ristrutturato in 3 rami mutuamente esclusivi (`is_grid_strategy_a` gate, TF escluso):
  1. `fill < avg` → `penalty = loss_pct` (S98a, invariato) + evento `sell_penalty_increased`.
  2. **NUOVO** `elif adverse_slippage > 1.0%` → `penalty = adverse_slippage` + **nuovo evento** `sell_penalty_slippage` (severity warn).
  3. `elif penalty > 0` → reset a 0 + evento `sell_penalty_reset` (ora logga anche lo slippage osservato).
- Penalty **non-cumulativa** (sempre l'ultimo valore), come S98a v2. `check_price`/`slippage` già in scope → nessuna propagazione necessaria.
- **Commenti aggiornati** in [grid_bot.py:179-190](bot/grid/grid_bot.py#L179) (init field) e [state_manager.py:133-148](bot/grid/state_manager.py#L133) (documenta l'Opzione 1: caso-slippage non ripristinato).

---

## Test — i 3 casi sui numeri reali BONK 8 giugno

BONK 8 giu: avg `$0.00000433`, sell_pct 2.5%, FEE 0.001. Le 5 sell delle 13:01-13:05 avevano tutte fill **sopra** avg (profittevoli) con slippage −3.45%/−4.08%.

| Caso | Condizione | BONK 8 giu | Effetto post-fix |
|---|---|---|---|
| **1** (perdita) | fill < avg | non accaduto l'8 giu (tutte profittevoli) | invariato S98a: penalty = perdita |
| **2** (slippage) | fill ≥ avg, slippage > 1% | **tutte e 5** (slippage 3.4-4.1%) | 1° sell 13:01 arma penalty 3.45% → blocca il 2° |
| **3** (reset) | fill ≥ avg, slippage ≤ 1% | mainnet (slippage 0.1-0.3%) | penalty mai armata; reset normale |

**Simulazione del burst spezzato** (1° sell 13:01: check $0.00000464, fill $0.00000448):
- adverse_slippage = (464−448)/464 = **3.45%** > 1% → Caso 2 → penalty 3.45%, effective sell_pct = 5.95%.
- Trigger del 2° sell **pre-fix** (penalty 0): `$0.00000448 × (1+0.025+0.001)/(1−0.001) ≈ $0.00000460` → il check $0.00000464 lo supera → 2° sell immediato (è ciò che è successo: 5 sell in 4 min).
- Trigger del 2° sell **post-fix**: `$0.00000448 × (1+0.05948+0.001)/(1−0.001) ≈ $0.00000476` → il check $0.00000464 **non lo raggiunge** → **2° sell soppresso**. Il burst si rompe finché il prezzo non sale a ~$0.00000476 (≈ +10% su avg) o il dead-zone 4h non resetta la ladder.

**Suite unit test** — `tests/test_sell_penalty_s98a.py` esteso da 7 a 10 test:
- `test_h` — Caso 2: sell profittevole (fill 103 ≥ avg 100) con slippage 1.9% → arma penalty 1.9% + evento `sell_penalty_slippage`, NON logga `sell_penalty_increased`.
- `test_i` — boundary: slippage 0.48% (< 1%) non arma; slippage 1.9% arma; vendita pulita 0.19% resetta.
- `test_h2` — Opzione 1: restart con sell profittevole nello storico → replay penalty = 0 (slippage-penalty NON ricostruita, si ri-arma a runtime).

**Suite completa: `160 passed`** (i 510 warning sono il noto `datetime.utcnow()` deprecato, PROJECT_STATE §8, fuori scope).

---

## Decisioni (CLAUDE.md §4)

**DECISIONE:** restore al restart — Opzione 1 (non ripristinare la slippage-penalty).
**RAZIONALE:** lo slippage richiede `check_price`, assente come colonna strutturata in `trades`; parsare il `reason` sarebbe fragile. La penalty è reattiva al mercato corrente → si ri-arma al primo sell post-restart. I restart sono rari/manuali.
**ALTERNATIVE:** Opzione 2 (restore da `bot_runtime_state`) — scartata: cambierebbe la fonte del restore (oggi `trades`) appoggiandosi a un mirror best-effort.
**FALLBACK:** se in futuro serve restore fedele, leggere `sell_pct_penalty` da `bot_runtime_state` al boot (la colonna esiste già da Parte B) — reversibile, ~5 righe in state_manager.

**DECISIONE:** soglia slippage costante in `sell_pipeline.py`, non in `bot_config` (come da brief). **FALLBACK:** spostarla in bot_config se servisse renderla per-coin o hot-reloadabile (es. se BONK si congela su testnet).

---

## Rischio noto (monitoraggio)

Auto-obiezione CEO confermata: su testnet BONK ha slippage strutturale 3-4% > soglia 1% → sarà penalizzato su quasi ogni vendita. È il comportamento desiderato ("book sottile → vendi meno aggressivamente"), accettato dal Board in fase testnet. **Da monitorare:** se BONK si congela (deadlock come pre-S98), alzare la soglia o renderla per-coin. Su mainnet (slippage 0.1-0.3%) il Caso 2 non scatterà.

---

## Roadmap impact

- Phase 9 V&C: Parte A chiude il gap "dashboard coherence" sui SUBLABEL testuali.
- `slippage_buffer parametrico` (PROJECT_STATE §7, brief separato pre-mainnet) resta distinto e **complementare**: è un buffer fisso pre-fill, questa è una penalty reattiva post-fill. Se entrambi shippano, si sommano.
- Nessun impatto su buy pipeline, dead zone, Sentinel, Sherpa, TF (fuori scope, vincoli rispettati).
