# Brief S99b-b — sell-pipeline-fixes — 2026-06-08

**Riferimento:** Report `2026-06-08_S99b_RforCEO_sell-ladder-audit.md` (CC, stesso giorno).
**Contesto:** Il report investigativo S99b ha confermato 3 interventi necessari. Questo brief li unifica perché condividono lo stesso contesto (sell pipeline + dashboard) e CC può lavorarli in un'unica sessione.

---

## Parte A — Fix testo dashboard (1 riga, zero rischio)

**Problema:** `web_astro/public/grid.html:1102` dice *"Per-lot trigger: sells when price rises this % above that lot's buy price"*. Il bot usa avg_cost dal S70 FASE 2 — il testo è un fossile FIFO mai aggiornato.

**Azione:** Sostituire la riga con il testo proposto da CC nel report S99b:

```js
'sell_pct': 'Sell trigger: sells a slice when price rises this % (net of fees) above the cycle reference — the average buy cost on the first sell, then each prior sell\'s price (the "sell ladder"). Single average cost, not per-lot.',
```

**Decisioni delegate a CC:** nessuna, testo approvato dal Board. Ship diretto.

---

## Parte B — Dashboard mostra penalty in NEXT SELL IF

**Problema:** (finding secondario Q2 del report S99b). La formula JS in `grid.html:952-956` calcola `NEXT SELL IF` usando solo `sell_pct`, senza sommare `_sell_pct_penalty`. Il bot invece usa `effective_sell_pct = sell_pct + _sell_pct_penalty` (grid_bot.py:831). Quando la penalty è attiva, la dashboard mostra un target più basso di quello reale → fuorviante per il Board.

**Azione in 2 step:**

1. **Runtime mirror:** esporre `_sell_pct_penalty` nel `bot_runtime_state` (o equivalente) che la dashboard legge. CC identifica il punto esatto e lo aggiunge.
2. **Formula JS:** nella dashboard, sommare la penalty al sell_pct prima di calcolare il trigger:
   ```js
   var effectiveSellPct = sellPct + (penaltyPct || 0);
   var nextSellTrigger = sellRef * (1 + effectiveSellPct / 100 + FEE_RATE) / (1 - FEE_RATE);
   ```

**Decisioni delegate a CC:** scelta del campo nel runtime mirror (nome, tipo, posizione). CC propone nel report e implementa.

**Decisioni che CC DEVE chiedere:** se servono modifiche al DB schema (nuova colonna in `bot_runtime_state` o tabella analoga), CC propone la migration e aspetta OK.

---

## Parte C — Evoluzione Adaptive Sell Penalty (anti-slippage)

**Problema:** La penalty attuale (S98a) si attiva solo quando il fill è sotto avg_cost (vendita in perdita). Non protegge da slippage su vendite profittevoli. L'8 giugno BONK ha venduto 5 lotti in 4 minuti con slippage −3.5/−4% su ogni fill, penalty sempre a 0 perché tutte profittevoli. Inoltre (finding bonus CC): lo slippage abbassa `_last_sell_price` (ancorata al fill), il che abbassa il gradino ladder successivo → feedback loop che auto-accelera il burst. La protezione anti-slippage serve a rompere questo loop.

**Logica proposta (approvata dal Board):**

```
Dopo ogni sell Grid Strategy A:

1. IF fill < avg_cost:
     penalty = (avg_cost − fill) / avg_cost × 100     # invariato (S98a v2)

2. ELIF slippage > SLIPPAGE_THRESHOLD:
     penalty = slippage                                 # NUOVO
     # dove slippage = (check_price − fill) / check_price × 100

3. ELSE:
     penalty = 0                                        # reset (invariato)
```

**Parametri:**
- `SLIPPAGE_THRESHOLD`: **1.0%** (soglia unica, tutti i coin). Costante in `sell_pipeline.py`, non in `bot_config` — non serve hot-reload, è un safety parameter che cambia raramente e solo con un brief.
- La penalty resta **non-cumulativa** (design v2 S98a): sempre l'ultimo valore osservato, mai la somma.
- Il reset avviene quando un sell ha slippage ≤ soglia E fill ≥ avg (caso 3).
- **NON si applica ai sell TF** (force-liquidate paths) — invariato da S98a.

**Nota sul `check_price`:** la sell_pipeline deve avere accesso al prezzo al momento della decisione (pre-ordine) per calcolare lo slippage. Verificare che questo valore sia disponibile nel contesto post-fill. Se non lo è, CC deve propagarlo (es. come parametro della funzione di sell, o come attributo temporaneo del bot).

**Auto-obiezione CEO:** Su testnet BONK lo slippage è strutturale (3–4%, order book sottile). Con soglia 1%, BONK sarà penalizzato su quasi ogni vendita. Questo è probabilmente il comportamento desiderato ("se l'order book è sempre sottile, vendi meno aggressivamente"), ma va monitorato: se BONK si congela di nuovo come nel deadlock pre-S98, la soglia va alzata o il parametro va reso per-coin. Il Board è consapevole e accetta il rischio in fase testnet.

**Log/eventi:** CC aggiunge un evento in `bot_events_log` quando la penalty si arma da slippage (distinguibile dal caso perdita), es.:
```
event: "sell_penalty_slippage"
message: "Sell penalty armed from slippage: fill $X vs check $Y (slippage Z%, threshold T%)"
```

---

## Vincoli

- **NO modifiche alla logica di buy** (buy pipeline fuori scope).
- **NO modifiche alla dead zone** (parametro separato, discussione futura).
- **NO modifiche a Sentinel, Sherpa, TF** (fuori scope).
- Il restart dei bot è necessario per Parte C. Parte A e B sono web-only (Vercel auto-deploy) ma se CC shippa tutto insieme, un unico restart.

## Output atteso da CC

1. **Piano in italiano** prima di scrivere codice (task non banale, >1h stimato).
2. Implementazione Parti A + B + C.
3. Report con: modifiche fatte, file/righe toccate, test eseguiti (almeno: simulazione mentale dei 3 casi della Parte C con numeri reali BONK dell'8 giugno).
4. **Naming report:** `2026-06-08_S99b-b_RforCEO_sell-pipeline-fixes.md`

## Roadmap impact

- Phase 9 V&C: "dashboard coherence S74b" non copriva i SUBLABEL testuali → Parte A chiude il gap.
- `slippage_buffer parametrico` (in PROJECT_STATE §7 come "brief separato pre-mainnet") è correlato ma distinto: quello è un buffer fisso aggiunto al sell_pct per compensare lo slippage atteso, questo è una penalty reattiva post-fill. I due meccanismi sono complementari, non alternativi. Se entrambi vengono implementati, la penalty si somma al buffer.
