# Report per CEO — kraken-2b-bundle — 2026-07-22 (S122)

**Brief sorgente:** `config/2026-07-21_S121_brief_kraken-2b-bundle.md`
**SCOPE (ereditato identico):** `kraken-2b-bundle`
**Esito:** SHIPPED (codice + test), **no restart** — va live alla finestra 2b coordinata (Max, sul Mini). **Invariante Binance:** i 4 grid testnet cambiano di ~0,1% al restart (Strada A, scelta di Max) — quantificato sotto.
**Commit:** `ed1933d` (inserito al commit)
**Test:** 340/340 verdi (`venv/bin/python3.13 -m pytest -q`); +10 nuovi `tests/test_kraken_fase2b_s121.py`.

> Nota numerazione: il brief è etichettato S121 (creato il 21-lug); l'implementazione è il 22-lug → l'ho trattata come **S122** (S121 risulta chiusa dal commit `75e59c1`). Da confermare con Max alla chiusura per PROJECT_STATE/diary. Il pairing brief↔report regge sullo SCOPE `kraken-2b-bundle`, invariato.

---

## Obiezione tecnica al brief (anti-assenso)

**Un mio errore di lettura, corretto verificando il codice — che rafforza la scelta A.** All'inizio ho pensato che sul testnet Binance l'avg *escludesse* la fee di buy (il che avrebbe reso la Strada A sbagliata sulla flotta viva). **Falso**: avevo confuso `total_invested` con `avg_buy_price`. La riga eseguibile è [buy_pipeline.py:304](../bot/grid/buy_pipeline.py#L304): `cost_for_avg = cost + fee` quando `synth_fee OR quote_fee_live` → **l'avg include 1× fee di buy su ogni venue** (testnet synth *e* Kraken). Quindi la premessa del brief (Strada A: sovra-protezione anche su Binance) **regge**, ed è quella che ho implementato.

**Obiezione che resta in piedi (minore, ma reale):** il fix #1 sul trigger è la **prima modifica di comportamento di trading** alla flotta Binance da tempo; le altre modifiche in coda per il restart (fee-fix `1251609`, T.2/T.3) sono solo display/reporting. Su una notte di primo-denaro-vero avrei preferito isolare ogni cambio-comportamento alla sola riga Kraken (principio Board "una variabile alla volta"). **Max ha scelto A consapevolmente** (semplicità nei file, 0,1% su soldi finti) → implementata A, ma il diff è quantificato qui sotto perché sia visibile a chi legge i numeri Binance dopo il restart.

**Distinzione trigger vs floor (non nel brief):** il doppio-conteggio *vero* è nel **trigger** (`+fee` al numeratore, su entrambi i venue). Il **floor** invece doppia-contava **solo su Kraken** (`+2×fee`); su Binance il floor non ha termine fee (dormiente, `fee_floor=0`). Quindi Strada A pulita = trigger corretto **ovunque** + floor Kraken da `+2f` a `/(1−f)`, **floor Binance lasciato byte-identico** (non era rotto). Così evito di attivare per sbaglio un blocco-vendita nuovo su BONK ad alto slippage.

---

## #1 — Fix doppio-conteggio (floor + trigger) 🔴

**Formula corretta.** L'avg-cost include già la fee di buy → per realizzare un margine `m` **netto** post-fee basta recuperare la sola fee di vendita:

```
trigger = avg × (1 + m) / (1 − fee)          (era: avg × (1 + m + fee) / (1 − fee))
floor   = avg × (1 + m_floor) / (1 − fee)     (era, Kraken: avg × (1 + m_floor + 2×fee))
```

Trigger e floor condividono la stessa forma → si muovono insieme: **trigger ≥ floor ⇔ sell_pct ≥ profit_target_pct** (niente stallo silenzioso). Verificato numericamente e comportamentalmente (test `test_no_stall_trigger_clears_floor_on_kraken`).

**Prova numerica (baseline reale 2a: avg $63.991, sell_pct 2%, Kraken 0,8%):**

| | trigger |
|---|---|
| vecchio (buggy) | **$66.313,25** |
| nuovo (S121/A) | **$65.797,20** |
| delta | **−$516,06** (≈ 1× fee di troppo) |

Coincide con la caccia al trigger del 21-lug (il bot NON vendeva a $65.600 perché il trigger reale era ~$66.3k). Col fix, un lotto da $25 con margine 2% realizza **+2,0% netto esatto** (prima +2,8%, cioè 0,8% regalato = la fee doppia).

**File:**
- [grid_bot.py](../bot/grid/grid_bot.py) — nuovo helper puro `grid_sell_trigger_price()` (fonte unica) + trigger di esecuzione che lo usa.
- [sell_pipeline.py:298-312](../bot/grid/sell_pipeline.py#L298) — floor Kraken `+2f` → `/(1−f)`; Binance byte-identico.

---

## Diff-Binance del #1 quantificato + Strada scelta

**Strada A** (scelta di Max): fix ovunque, una formula sola, nessun `if venue` nel trigger. Effetto sui 4 grid testnet vivi (fee 0,1%), al prossimo restart:

| grid | sell_pct | trigger prima → dopo | Δ |
|---|---|---|---|
| BTC | 1,20% | 101,4014 → 101,3013 | **−0,099%** |
| SOL | 1,61% | 101,8118 → 101,7117 | −0,098% |
| BONK | 2,53% | 102,7327 → 102,6326 | −0,097% |
| ETH | 1,00% | 101,2012 → 101,1011 | −0,099% |

= i grid vendono **~0,1% prima** (correzione, erano sovra-protettivi). Su soldi finti, nell'ordine di grandezza atteso (`fee/(1−fee)` ≈ 0,1%), nessun test/invariante rotto. **Floor Binance NON cambia** (resta dormiente, byte-identico → test `test_floor_binance_formula_unchanged` verde).

---

## #2 — Helper unico + display 🟡

Estratto **una sola fonte** del trigger, chiamata da esecuzione *e* da tutti i display → il target mostrato = dove il bot vende davvero.

- `grid_sell_trigger_price(reference, threshold_pct, fee_rate)` — matematica pura.
- `GridBot.current_sell_trigger()` — ramo grid (fee-buffered su ladder/avg + Adaptive Sell Penalty) vs TF (greed-decay TP, invariato).
- Chiamanti riallineati: esecuzione ([grid_bot.py:876 area](../bot/grid/grid_bot.py)), **`get_status`** (→ terminale [lifecycle.py:153](../bot/grid_runner/lifecycle.py#L153) + daily_report [daily_report.py:96](../bot/grid_runner/daily_report.py#L96), a valle), **Range print** all'init. Etichette: "(+X% net, fee-buffered)".
- Frontend **card paper** [grid.html:1171](../web_astro/public/grid.html#L1171): tolto il `+FEE_RATE` doppio (venue=binance, FEE 0,1% corretta). La sezione **Kraken collaudo** non mostra trigger → nessun fix fee-Kraken necessario lì.

**Bug pre-S121 esposto:** `get_status` mostrava il numero **ingenuo** `avg×(1+sell_pct/100)` (nessun cuscino fee, ignorava penalty e ladder). Ora coincide con l'esecuzione — coperto da `test_get_status_matches_execution_trigger` (display==esecuzione, con probe sopra/sotto trigger) e `test_get_status_reflects_penalty_not_naive_avg`.

**⚠️ Flag (verificato, NON corretto — fuori scope):** [tf.html:1459](../web_astro/public/tf.html#L1459) usa la formula grid fee-buffered (`+FEE_RATE`) per i bot **TF**, che invece eseguono `avg×(1+threshold)` senza cuscino. È un'incoerenza **pre-esistente e separata** (non il doppio-conteggio grid): togliere solo il `+FEE_RATE` lo lascerebbe comunque sbagliato (avrebbe ancora il `/(1−FEE)` che il TF non ha). Va sistemato con la semantica TF corretta in un micro-brief dedicato — non alla cieca dentro il bundle grid (vincolo "non toccare calibrazione TF"; TF non trada in v3).

---

## #3 — Processo grid Kraken 🔴 → **orchestrator-managed, ZERO codice nuovo**

Scelta: **orchestrator-managed** (converge con la preferenza del CEO), e — sorpresa — richiede **niente cablaggio**:

- L'orchestrator è **venue-agnostico** ([orchestrator.py:379-410](../bot/orchestrator.py#L379)): spawna *qualsiasi* riga `is_active=true`; il runner sceglie l'exchange dalla propria riga (Fase 1). Al flip `is_active=true` la riga Kraken viene presa da sola.
- **Log per-simbolo già gratis**: [orchestrator.py:65-74](../bot/orchestrator.py#L65) fa `grid_BTC_USD.log` (stdout/stderr rediretti) — risolve il "senza log" del babysitter 2a.
- **Restart-su-crash + SIGTERM uniformi** (MAX_RESTART_ATTEMPTS) — risolve il loop-respawn ad-hoc.
- `KRAKEN_TEST_MODE` **non serve** in 2b: serviva solo a tenere vivo un runner su riga `is_active=false` ([grid_runner/__init__.py:130,545](../bot/grid_runner/__init__.py#L130)). Con `is_active=true` il runner resta vivo da solo.

**Requisiti per la finestra coordinata (Max, sul Mini — NON oggi):**
1. Solo la riga Kraken voluta `is_active=true` (memo §6: il BUY reale **non** è gatato da `is_active` → una riga di prova viva potrebbe ricomprare denaro vero).
2. Orchestrator rilanciato con `ALLOW_REAL_MONEY=true` (ereditato dai figli via `Popen`).
3. Verificare che il babysitter 2a standalone (pid 46585) sia **morto** prima, per non doppiare la riga.

**Reboot del Mini:** il grid Kraken eredita lo stesso comportamento dei 4 grid (l'orchestrator va rilanciato a mano da Max dopo un reboot) — comunque **meglio** del babysitter 2a, che aveva un suo problema di reboot separato.

---

## Test — 340/340 verdi

**Nuovi** (`tests/test_kraken_fase2b_s121.py`, 10): funzione pura no-double-count + prova numerica 2a ($65.797 non $66.313) + shift Binance ~0,1% + `current_sell_trigger` grid/TF + folding penalty+ladder + **display==esecuzione** + guardia anti-stallo trigger≥floor.

**Aggiornati** (cristallizzavano la formula col doppio-conteggio → ri-puntati su quella corretta, con nota S121 — elencati per trasparenza auditor):
- `test_kraken_fase1_s118.py`: floor Kraken `blocks/allows/margin` ai valori corretti (break-even $100,806 non $101,6; margine floor $101,21 non $102,0) + docstring. Aggiunto un **regression assert**: 101,0 (bloccato pre-S121 pur essendo in utile netto) ora **passa**.
- `test_accounting_avg_cost.py`: `test_l`/`test_m` trigger + ladder (5 formule) `(1+0.02+FEE)` → `(1+0.02)`.
- `test_sell_penalty_s98a.py`: `test_c` base/penalty trigger.
- `test_spike_guard.py`: commento stale del trigger.

Nessun test rinominato è referenziato da runner manuali (verificato). Binance resta byte-identico sul floor; sul trigger cambia dello 0,1% documentato.

---

## Cosa NON ho fatto (scope)

- Nessun valore di parametro Kraken toccato (margine/floor/sell_pct → Sherpa + tabella con Max al setup 2b).
- Nessun insert riga, nessun flip `is_active`, nessun restart.
- Ancora-buy-dopo-sell (Blocco 2 del brief): **non riaperta** — letto il codice, non ho trovato prove che contraddicano la chiusura del CEO (`state_manager.py:202` usa il last-buy legittimo; idle recalibrate/re-entry si ri-ancorano). Nessun fix d'iniziativa.
- `tf.html:1459` (flag sopra) → micro-brief TF separato.

---

*Cita: brief `2026-07-21_S121_brief_kraken-2b-bundle.md` + commit `ed1933d`.*
