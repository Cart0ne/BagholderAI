# BRIEF — Buchi nella protezione exit del TF (trailing stop globale + stop loss su allocation)

**Date:** 2026-05-04
**Priority:** MEDIA — exit logic, riguarda capitale paper ma è critica per il go-live
**Stato:** diagnosticato su dati live, fix non ancora implementato. Lasciare correre 1-2 settimane per dati aggiuntivi prima di intervenire (data-first).

---

## TL;DR

Su INJ e DOGE (osservati 2026-05-04) sono emersi **due bug indipendenti** del sistema di exit del Trend Follower, che spiegano due failure mode opposte:

1. **DOGE — il trailing stop scatta troppo presto su lotti appena entrati**, perché il peak è globale per coin e non viene resettato quando un nuovo last-shot abbassa l'`avg_buy_price`.
2. **INJ — lo stop loss non scatta quando dovrebbe**, perché la soglia è in dollari assoluti sul `capital_allocation` iniziale, non in percentuale sul lotto. Lotti parziali (post-skim, post-sell) restano scoperti fino a perdite molto maggiori del 2.5% nominale.

Entrambi i bug derivano da scelte di design **coerenti tra loro** (semplicità, single-peak / single-threshold), ma producono comportamenti incoerenti con la promessa che leggi nei tooltip della dashboard ("dropped 2% from peak", "stop loss 2.5%").

---

## Caso 1: DOGE — peak globale, vendita precoce di lotti freschi

### Cronologia (UTC, 2026-05-04)

| Ora | Evento | Prezzo | Avg | Peak in mem |
|---|---|---|---|---|
| 02:31 | BUY lotto A (58 DOGE, $6.52) | $0.11239 | $0.11239 | inizializzato |
| (oraggio) | prezzo sale | peak ≤ $0.1136 | $0.11239 | $0.1136 |
| 10:07 | BUY lotto B last-shot (60 DOGE, $6.57) | $0.10947 | **$0.11093** ricalcolato | $0.1136 ancora |
| 10:08 | TRAILING-STOP: SELL entrambi i lotti @ $0.10929 | -2% dal peak | — | — |

Realized: −$0.18 sul lotto A (−2.76%) + −$0.01 sul lotto B (−0.16%) = **−$0.19 / $13.10 = −1.5% ciclo**.

### Perché è scattato
[bot/strategies/grid_bot.py:144](bot/strategies/grid_bot.py#L144) — `_trailing_peak_price` è in-memory dell'oggetto bot, **inizializzato a 0 al boot, mai resettato** durante la vita del bot.
[bot/strategies/grid_bot.py:938-942](bot/strategies/grid_bot.py#L938-L942) — peak aggiornato ogni tick se prezzo > peak. Mai resettato sui buy.
[bot/strategies/grid_bot.py:1005-1006](bot/strategies/grid_bot.py#L1005-L1006) — attivazione: `peak ≥ avg_buy × (1 + 1.5%)`. Ma `avg_buy` viene **ricalcolato ad ogni nuovo buy** (mediato), mentre il peak no.

Numericamente: dopo lotto B (last-shot a prezzo più basso), `avg_buy` cala da $0.11239 a $0.11093 → soglia attivazione cala da $0.11407 a $0.11260. Peak storico $0.1136 supera la nuova soglia → trailing si **arma automaticamente** sul lotto B appena entrato. 1 minuto dopo il prezzo continua a scendere, scatta il drop −2% e vende tutto.

### Il problema concettuale
Il trailing stop **non protegge un guadagno** sul lotto B (che non c'è mai stato): protegge un guadagno fantasma derivato da un peak vissuto solo dal lotto A.

---

## Caso 2: INJ — stop loss in $ assoluti, lotti parziali scoperti

### Stato attuale
- Allocation iniziale: $15.44 (2 lotti pianificati)
- Lotto A: comprato + venduto in greed decay il 02/05 (chiuso, +$0.24)
- Lotto B (open ora): 2.03 INJ @ avg $3.796, cost $7.71 — **metà allocation**
- Prezzo attuale ~$3.68 → unrealized ≈ −$0.235 (−3.06% sul lotto)

### Perché lo SL non scatta
[bot/strategies/grid_bot.py:948-962](bot/strategies/grid_bot.py#L948-L962):
```python
unrealized = (current_price - self.state.avg_buy_price) * self.state.holdings
loss_threshold = -(self.capital * self.tf_stop_loss_pct / 100)
if unrealized <= loss_threshold: ...
```

`self.capital` = `capital_allocation` iniziale (fisso, $15.44 per INJ).
Soglia loss = −$15.44 × 2.5% = **−$0.386**.
Unrealized attuale = −$0.235 (perché il lotto è metà allocation).
−$0.235 > −$0.386 → SL **non scatta** anche se il lotto è in −3%.

Servirebbe: −$0.386 / 2.03 INJ = $0.190 di drawdown / $3.796 = **−5.0% sul lotto** prima che lo SL si attivi.

### Quanto è frequente questo caso
Tutti i lotti parziali post-sell o post-skim hanno questa esposizione asimmetrica. Più piccolo il residuo open, più ampio deve essere il drawdown nominale per innescare lo SL.

---

## Cause comuni dei due bug

Entrambi nascono da una scelta di design **single-state per coin**:

| State | Storage | Bug consequence |
|---|---|---|
| `_trailing_peak_price` | in-memory, globale per bot | Caso 1: peak vecchi triggerano nuovi lotti |
| `tf_stop_loss_pct × capital` | dollari assoluti su allocation iniziale | Caso 2: lotti parziali scoperti |

In entrambi i casi manca la nozione **per-lotto** che invece esiste già altrove nel codice (es. `_pct_open_positions`).

---

## Opzioni di fix (NON implementare ora — discutere col CEO prima)

### Opzione A — Fix conservativo (minimal)
1. **Trailing**: resettare `_trailing_peak_price = current_price` ogni volta che parte un nuovo buy (single-line change).
2. **Stop loss**: sostituire la soglia in $ assoluti con una soglia in % sul `avg_buy_price`. Cioè `loss_threshold = -avg_buy_price × tf_stop_loss_pct / 100 × holdings`. Diventa percentuale "vera" sul valore aperto del momento.

Rischio: cambia la semantica della soglia. Se Max ha tarato 2.5% pensando "del lotto", il fix non cambia nulla; se ha tarato pensando "dell'allocation totale", cambia regime. Da chiarire.

### Opzione B — Fix per-lotto (architetturale)
1. **Trailing**: tracciare un peak per lotto (`peak_since_buy`), valutare il trigger lotto per lotto.
2. **Stop loss**: idem, valutare per lotto, vendere solo i lotti sotto soglia anziché liquidare tutto.

Rischio: cambio architetturale, costoso in test. Più allineato al modo in cui la dashboard espone i dati ("avg buy", "lot buy" nei reason).

### Opzione C — Status quo + warning
Lasciare il codice così, ma loggare un evento `safety/exit_logic_holes` quando si verifica una di queste configurazioni (es. SL non scatta perché allocation > holdings notional). Solo telemetria, zero fix. Utile se si vuole accumulare più casi prima di decidere A vs B.

---

## Perché parcheggiare per ~2 settimane

Coerente con la regola "data-first, then formal review":
- Capitale paper, perdite assolute trascurabili (DOGE −$0.19, INJ −$0.24 unrealized).
- I due casi sono i **primi due** osservati. Servono altri esempi per capire se i bug si manifestano spesso o sono outlier (es. last-shot in mercato laterale è raro).
- Tra 2 settimane c'è già in calendario il confronto Profit Lock 45f vs Trailing 36f (vedi roadmap exit mechanisms): questo bug si inserisce naturalmente in quella review, non vale rompere il timeline per fixarlo prima.

## Quando tirarlo fuori
- A ridosso della review degli exit mechanisms (~2026-05-17).
- Oppure prima se si osservano altre vendite anomale (telemetria: cercare `trailing_stop_triggered` con `current_price ≤ avg_buy × 0.99` o simili).
- Comunque PRIMA del go-live mainnet (rischio capitale reale).

---

## File toccati dall'analisi (read-only)
- [bot/strategies/grid_bot.py:144](bot/strategies/grid_bot.py#L144) — peak init
- [bot/strategies/grid_bot.py:938-942](bot/strategies/grid_bot.py#L938-L942) — peak update
- [bot/strategies/grid_bot.py:948-962](bot/strategies/grid_bot.py#L948-L962) — stop loss
- [bot/strategies/grid_bot.py:995-1019](bot/strategies/grid_bot.py#L995-L1019) — trailing trigger

## Dati di riferimento Supabase
- INJ trades: 2 buy + 1 sell (02/05), lotto B open @ avg $3.796
- DOGE trades: vedi `trades` table, vendite 2026-05-04 10:08 con reason "TRAILING-STOP"
- Config: `trend_config.tf_stop_loss_pct=2.5`, `tf_trailing_stop_activation_pct=1.5`, `tf_trailing_stop_pct=2`
