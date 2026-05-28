# BRIEF CC — Fix slippage spike: Opzione A (Board) + Opzione B

**Data**: 28 maggio 2026  
**Priorità**: ALTA — pre-mainnet  
**Stima**: ~1h (task non banale → CC produce piano in italiano prima di codare)  
**Riferimento**: `investigations/slippage_btc_20260527.md` (report CC del 28/05)

---

## Contesto

Il Board ha analizzato le 3 opzioni proposte nel report di investigazione e ha deciso: **A (versione rivista dal Board) + B**.

L'opzione A originale (soglia fissa con skip) è stata scartata perché una soglia fissa è impossibile da calibrare su coin diverse (BTC vs BONK). Il Board ha proposto una variante con conferma a doppio fetch.

---

## Opzione A — Variante Board: "doppio fetch con conferma"

Logica in `fetch_price` (o immediatamente a valle):

1. Il bot legge il prezzo (`tick_1`)
2. Confronta con l'ultimo prezzo noto (`state.last_price`)
3. Se il delta supera una soglia (es. ±6%):
   - **Pausa 5 secondi**
   - **Ri-fetch del prezzo** (`tick_2`)
   - Se `tick_2` conferma almeno il **50% del movimento** di `tick_1` rispetto a `state.last_price` → il movimento è reale, procedi con `tick_2` come `current_price`
   - Se `tick_2` NON conferma (es. è tornato vicino a `state.last_price`) → spike, **skip del tick**. Il bot non fa nulla e aspetta il prossimo ciclo normale
4. Se il delta è sotto la soglia → comportamento invariato, nessuna pausa

**Esempio concreto (caso dello spike del 27/05):**
- `state.last_price` = ~$74,500
- `tick_1` = $82,143 → delta = +10.2% → supera soglia 6%
- Pausa 5 secondi
- `tick_2` = $74,600 → conferma solo 0.1% del movimento → sotto 50% → spike → SKIP
- Risultato: nessuna vendita in perdita

**Esempio concreto (pump reale BONK +12%):**
- `state.last_price` = $0.000020
- `tick_1` = $0.0000224 → delta = +12% → supera soglia 6%
- Pausa 5 secondi
- `tick_2` = $0.0000221 → conferma ~92% del movimento → sopra 50% → rally reale → PROCEDI con `tick_2`
- Risultato: il bot vende normalmente

---

## Opzione B — Cooldown 1 ciclo post dead-zone recalibrate

Quando `dead_zone_recalibrate` scatta:

1. Esegue il recalibrate normalmente (reset `_last_sell_price`, update `_pct_last_buy_price`)
2. Setta un flag transitorio (es. `_skip_next_decision = True`)
3. `check_price_and_execute` controlla il flag: se True, logga "post-recalibrate cooldown, skipping decision" e ritorna senza valutare sell/buy
4. Al tick successivo il flag è False → decisioni normali con prezzo fresco

---

## Decisioni delegate a CC

- Dove posizionare la logica di A: dentro `fetch_price` o a valle nel chiamante
- Scelta del campo per `state.last_price` (verificare quale campo dello state già traccia l'ultimo prezzo visto)
- Soglia esatta per A: 6% è l'indicazione del Board, CC può proporre un valore diverso motivandolo
- Nome del flag per B e dove persistere (solo in-memory, non serve DB)

## Decisioni che CC DEVE chiedere

- Se durante l'implementazione emerge che la soglia 6% o la tolleranza 50% creano edge case non previsti su una delle coin attive (BTC, SOL, BONK), FERMARSI e descrivere il caso
- Se il refactor richiede modifiche a `check_price_and_execute` che impattano altri path oltre grid, FERMARSI

---

## Output atteso

1. Codice implementato e testato
2. Aggiornamento `PROJECT_STATE.md` sezione decisioni recenti
3. Commit con messaggio che referenzia questo brief

---

## Vincoli

- NON modificare la logica di `dead_zone_recalibrate` stessa (il recalibrate funziona, il problema è cosa succede DOPO)
- NON modificare soglie di sell/buy percentage
- La pausa di 5 secondi in A è bloccante solo per quel tick, NON deve bloccare altri bot/coin se l'orchestrator gestisce più symbol nello stesso thread (verificare)
- Restart bot necessario dopo deploy — coordinare con Max
