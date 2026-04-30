# Brief 49a — TF Exit-After-N-Positive-Sells (Gain-Saturation Circuit Breaker)

**From:** CEO (Claude, Projects) → CC (Intern)
**Via:** Max (board)
**Date:** 2026-04-27
**Session:** 49
**Priority:** Alta. Si chiude il TF prima di passare alla narrativa Phase 2 → Phase 3.
**Stima:** ~2-3h di lavoro

---

## 1. Contesto

Hai già fatto il backtest (proposal `exit_after_n_positive_sells_proposal.md` + script `backtest_exit_after_n_positive_sells.py`). Ottimo lavoro, in particolare l'insight metodologico che la regola **non è un take-profit smart**: è un **circuit breaker per saturazione**. Le coin che riescono a fare 4 sell positive consecutive sono statisticamente quelle che poi seppelliscono il PnL nel resto del soggiorno (vedi caso emblematico MOVR: −$13.39 reale → +$4.70 controfattuale, +$18 di edge solo da quella coin).

Il CEO ha rivisto i numeri:
- Edge totale a N=4: **+$35.30** su 27 soggiorni chiusi
- Sweep coerente N=2/3/4/5 (tutti positivi, beat ≥ worse)
- Concentrazione del segnale sui top performer (MOVR da solo = 51%)
- Ma profilo di rischio **asimmetrico favorevole**: vincita media ~$3.83, sconfitta media ~$0.73, ratio ~5×
- Worst case singolo: −$1.80 (MBOX). Trascurabile.

**Decisione:** implementare ON-by-default a N=4. Telemetria forte. Revisione tra una settimana.

---

## 2. Obiettivo

Aggiungere al TF un **gain-saturation circuit breaker** che si attiva quando una coin gestita TF ha completato N sell con `realized_pnl > 0` nel soggiorno corrente. Al trigger:

1. **Forced sell** del residuo di posizione (se >0) al prezzo di mercato corrente
2. Coin **flaggata "saturated"** per il resto del soggiorno → grid TF non rientra
3. **Reset** del counter al prossimo ALLOCATE (nuovo soggiorno)

La regola **non sostituisce** SL / TP / greed decay. Si **aggiunge** come layer di sicurezza dedicato alla saturazione del gain.

---

## 3. Specifiche

### 3.1 Schema — DUE tabelle, due livelli

#### 3.1.a Default globale — `trend_config`

```sql
ALTER TABLE trend_config
  ADD COLUMN tf_exit_after_n_positive_sells INTEGER DEFAULT 4,
  ADD COLUMN tf_exit_after_n_enabled BOOLEAN DEFAULT TRUE;
```

- `tf_exit_after_n_positive_sells`: il default globale di **N** (default **4**)
- `tf_exit_after_n_enabled`: kill-switch globale (default **TRUE** — la regola parte attiva)

Razionale del kill-switch: vogliamo poterla disattivare in 1 SQL senza redeploy se i dati live divergono troppo dal backtest. Naming coerente con `tf_profit_lock_enabled` già presente.

#### 3.1.b Override per coin — `bot_config`

```sql
ALTER TABLE bot_config
  ADD COLUMN tf_exit_after_n_override INTEGER NULL;
```

- `tf_exit_after_n_override`: override per la singola coin. **NULL = usa il default globale** di `trend_config`. Valore non-null = sostituisce il default solo per quella coin.
- Il kill-switch resta globale: NON aggiungere un override per-coin di `enabled`.

**Razionale dell'override per-coin:** il backtest mostra comportamenti molto diversi per coin. MOVR ha richiamato +$18 di edge con 4 sell positive (caso disastroso); MBOX ha solo perso edge perché era un trend pulito che la regola ha tagliato corto. Avere un valore unico per tutte le coin è subottimale. Il CEO vuole poter calibrare via SQL su base per-coin senza redeploy.

**Esempi d'uso (per il CEO, non per te):**

```sql
-- MOVR esce prima
UPDATE bot_config SET tf_exit_after_n_override = 3 WHERE symbol = 'MOVR/USDT';

-- MBOX più tollerante (è un trend buono)
UPDATE bot_config SET tf_exit_after_n_override = 6 WHERE symbol = 'MBOX/USDT';

-- Reset al default
UPDATE bot_config SET tf_exit_after_n_override = NULL WHERE symbol = 'MOVR/USDT';
```

### 3.2 Counter — soluzione preferita: stateless

**Opzione preferita:** calcolare il counter on-the-fly da `trades`, senza colonne nuove. Pseudocodice:

```python
def get_tf_positive_sells_count(symbol: str, since: datetime) -> int:
    """
    Conta i sell con realized_pnl > 0 dalla data di apertura del soggiorno corrente.
    `since` = timestamp del primo trade TF del soggiorno corrente
              (= timestamp dell'ultimo ALLOCATE per quel symbol).
    """
    return supabase.table("trades") \
        .select("id", count="exact") \
        .eq("symbol", symbol) \
        .eq("managed_by", "trend_follower") \
        .eq("side", "sell") \
        .gt("realized_pnl", 0) \
        .gte("created_at", since.isoformat()) \
        .execute().count
```

**Pro stateless:** la "verità" sta sempre nelle `trades`. Niente state da tenere sincronizzato. Niente bug "counter desync".

**Contro:** una query DB per ogni decisione del bot. Trascurabile su scala attuale (decine di check al minuto), ma se preferisci cachare il valore in memoria del bot tra una decisione e l'altra (invalidato a ogni nuovo sell), procedi pure — è scelta tua.

**`since` come si recupera?** Il timestamp dell'ALLOCATE corrente. Le strade:
- `trend_decisions_log` ha `action_taken='ALLOCATE'` con `scan_timestamp`. Prendi il MAX scan_timestamp di ALLOCATE per quel symbol.
- In alternativa, MIN(`created_at`) dei trade TF di quel symbol con `created_at >= ultimo DEALLOCATE` — se non c'è dealloc precedente, MIN(`created_at`) di tutti i trade TF su quel symbol.

Preferisci l'opzione che ti sembra più robusta. Documenta la scelta nel commit message.

### 3.3 Saturated flag — soluzione preferita: in-memory

Lo stato "saturated" vive solo per il soggiorno corrente, non deve persistere tra restart del bot in modo critico (un restart ricalcola da `trades` se il counter è già al massimo, e se sì al primo check post-restart la regola scatta di nuovo — innocuo perché il forced-sell è idempotente: vende solo se holdings>0).

**Opzione preferita:** flag in-memory nel bot runner per coin TF. Reset al restart (ricalcolato dai trades), reset al next ALLOCATE.

**Pro:** zero schema changes per lo stato.
**Alternativa più conservativa:** aggiungere `tf_saturated BOOLEAN DEFAULT FALSE` alla tabella `bot_config` (se esiste un record per coin TF) o creare `tf_managed_state(symbol, saturated_at, allocated_at)`. Procedi così se ti senti più sicuro — è una scelta di trade-off operativo che lascio a te.

### 3.4 Logica di trigger — dove va il check

Nel main loop del grid_bot.py / TF runner, il check va eseguito **dopo ogni sell completato con successo**, prima di valutare il prossimo buy/hold/sell.

Pseudocodice:

```python
# Resolve effective N: override per-coin se presente, altrimenti default globale
effective_n = (
    bot_config.tf_exit_after_n_override
    if bot_config.tf_exit_after_n_override is not None
    else trend_config.tf_exit_after_n_positive_sells
)

# Dopo aver eseguito un sell con realized_pnl > 0 su una coin TF managed:
if tf_managed and config.tf_exit_after_n_enabled and last_sell_was_positive:
    pos_count = get_tf_positive_sells_count(symbol, since=current_period_start)
    if pos_count >= effective_n:
        # TRIGGER
        if holdings > 0:
            execute_forced_sell(symbol, holdings, price=current_price)
        mark_saturated(symbol)  # blocca buy fino a prossimo ALLOCATE
        log_event_saturated(..., n_threshold_used=effective_n, was_override=(bot_config.tf_exit_after_n_override is not None))
```

**Nota su `effective_n` nei log:** quando emetti l'evento `tf_exit_saturated`, includi nei `details` sia il valore usato (`n_threshold`) sia un flag che indica se è venuto da override per-coin o dal default globale. Serve al CEO per fare audit e capire post-hoc se gli override stanno funzionando.

**Posizionamento nel codice:** accanto ai filtri 39a/39c/45f in `bot/strategies/grid_bot.py` (sai dove sono — sono i filtri introdotti tra Session 39 e 45). La nuova logica si chiama `filter_45g_gain_saturation` (continuo la numerazione esistente).

**Comportamento del flag saturated nei buy:** quando `is_saturated(symbol) == True`, il bot deve skippare ogni buy decision per quel symbol con event log specifico (vedi 3.5). Nessun forced sell ulteriore — il sell finale è già stato fatto al trigger. Solo i buy vanno bloccati.

**Reset del flag:** quando arriva un nuovo ALLOCATE TF per quel symbol (prossimo scan TF che decide di ri-allocare), il flag torna a False, counter torna a 0. È il TF stesso che sblocca, non un timer.

### 3.5 Telemetria — `bot_events_log`

**Evento principale al trigger:**

```python
{
  "severity": "INFO",
  "category": "TF_GAIN_SATURATION",
  "symbol": "MOVR/USDT",
  "event": "tf_exit_saturated",
  "message": "TF exit after N=4 positive sells",
  "details": {
    "n_threshold": 4,                 # valore di N effettivamente applicato
    "was_override": false,            # true se veniva da bot_config.tf_exit_after_n_override
    "positive_sells_count": 4,
    "period_started_at": "2026-04-27T10:30:00+00:00",
    "residual_holdings": 159.5,
    "residual_avg_buy_price": 0.03665,
    "exit_price": 0.0368,
    "liq_value_usd": 5.87,
    "liq_pnl_usd": 0.02,
    "total_period_realized_pnl_usd": 5.80
  }
}
```

**Evento secondario al buy bloccato (per debug, opzionale ma utile):**

```python
{
  "severity": "DEBUG",  # tienilo basso, può essere rumoroso
  "category": "TF_GAIN_SATURATION",
  "symbol": "MOVR/USDT",
  "event": "tf_buy_skipped_saturated",
  "message": "Buy skipped: coin saturated until next ALLOCATE",
  "details": { "saturated_since": "2026-04-27T10:30:00+00:00" }
}
```

Il primo è il segnale per il CEO alla revisione settimanale. Il secondo è per debug — se vuoi tenerlo a INFO va bene ma rischia di affollare il log.

### 3.6 Notifiche Telegram

Al trigger, mandare **una sola** notifica al canale privato (no canale pubblico):

```
🛑 TF GAIN SATURATION
{symbol}
N positive sells reached: {n_threshold}{" (override)" if was_override else ""}
Exit price: ${exit_price}
Residual sold: {residual_qty} @ {residual_avg_buy} → ${liq_value_usd}
Period total realized: ${total_period_realized_pnl_usd}
```

Una per trigger, niente spam. Nessuna notifica per i buy skippati (sono nel log, basta).

---

## 4. Test checklist

Prima di pushare a main, verifica con un mini test in `tests/` (o uno script ad hoc che giri offline contro Supabase):

- [ ] **Counter conta correttamente** solo i sell con `realized_pnl > 0` del soggiorno corrente (non cumulativo storico)
- [ ] **`since` è corretto**: trade TF del soggiorno corrente, non quelli di soggiorni passati sulla stessa coin
- [ ] **Lookup override per-coin funziona**: con `bot_config.tf_exit_after_n_override = 3` per MOVR/USDT (test symbol), il trigger scatta alla 3ª sell positiva non alla 4ª
- [ ] **Fallback al default funziona**: con `bot_config.tf_exit_after_n_override = NULL`, usa il valore di `trend_config.tf_exit_after_n_positive_sells`
- [ ] **Trigger fires** alla N-esima sell positiva (effective_n), non prima e non dopo
- [ ] **Forced sell esegue** quando `holdings > 0` al trigger, e non esegue quando `holdings == 0` (caso 7/14 nel backtest — coin già flat)
- [ ] **Saturated flag blocca buy** finché non arriva un nuovo ALLOCATE
- [ ] **Reset funziona** al prossimo ALLOCATE: counter torna a 0, flag a False
- [ ] **L'override NON si resetta** quando il TF fa ALLOCATE di una coin che ha già un override impostato (vedi sezione 7 — è critico)
- [ ] **Kill-switch funziona**: con `tf_exit_after_n_enabled=FALSE` la regola è inerte, comportamento legacy
- [ ] **Restart-safe**: se il bot si riavvia con holdings>0 e counter già al massimo, il primo check post-restart triggera correttamente (idempotenza del forced-sell)
- [ ] **No false positive sui core**: BTC/SOL/BONK NON sono `managed_by='trend_follower'`, quindi non devono mai triggerare. Verifica con un check esplicito.
- [ ] **Evento telemetria** scritto correttamente in `bot_events_log` con tutti i campi `details` (incluso `n_threshold` e `was_override`)
- [ ] **Notifica Telegram** parte al trigger (testa una volta in dry-run o con symbol fake)

---

## 5. Roll-out

1. Branch off main per implementazione + test (opzionale, se ti senti, anche direttamente su main per le piccole modifiche — sai tu, regola standard)
2. Apply migration: i due nuovi campi su `trend_config`
3. Deploy del codice
4. Verifica che `tf_exit_after_n_enabled=TRUE` e `tf_exit_after_n_positive_sells=4` in produzione
5. **Push diretto a main** (regola standard del progetto: no PR)
6. `git pull` su Mac Mini, restart orchestrator + bot

**Nessun cooldown post-trigger esterno**: se TF al prossimo scan ri-alloca, si riparte. Decisione del CEO. Non aggiungere `tf_saturated_cooldown_hours` o simili.

---

## 6. Revisione settimanale (per il CEO, non per te)

Tra 7 giorni il CEO interroga `bot_events_log` con `category='TF_GAIN_SATURATION'` e `event='tf_exit_saturated'` per:
- Quanti trigger sono scattati?
- Distribuzione per symbol
- Confronto residual_holdings reali vs simulati nel backtest
- Edge stimato live (richiede stima counterfactual del "cosa avrebbe fatto TF senza la regola" — query separata)

Se l'edge live diverge troppo dal backtest, il CEO può:
- Disattivare con `UPDATE trend_config SET tf_exit_after_n_enabled=FALSE`
- O modificare N con `UPDATE trend_config SET tf_exit_after_n_positive_sells=3` (o altro)

Tu non devi fare nulla per la revisione — solo assicurarti che la telemetria sia completa.

---

## 7. Open questions

Se incontri dubbi durante l'implementazione, **chiedi prima di decidere arbitrariamente**. In particolare:

1. **PRESERVAZIONE OVERRIDE durante ALLOCATE — critico.** Quando il TF fa un nuovo ALLOCATE su una coin, probabilmente fa UPSERT/UPDATE su `bot_config` per resettare campi di sessione (`allocated_at`, `is_active=true`, `entry_price`, ecc.). **Il campo `tf_exit_after_n_override` NON deve essere toccato dall'ALLOCATE** — è un setting di policy del CEO, non uno stato di sessione. Verifica nel codice del TF allocator che le UPDATE/UPSERT su `bot_config` listino esplicitamente i campi da modificare e non includano `tf_exit_after_n_override`. Se l'ALLOCATE fa un INSERT (perché coin nuova mai gestita), `tf_exit_after_n_override` parte NULL e va bene così.
2. **Edge case "coin che torna a 0 e poi rientra dentro lo stesso soggiorno"**: se holdings vanno a 0 ma `since` è ancora quello dell'ALLOCATE originale, e il counter è a 3, e poi un nuovo buy + sell positivo lo porta a 4 → la regola scatta giustamente. Ma in pratica: il TF non dovrebbe ri-buyare se holdings=0 a meno che non sia un nuovo ALLOCATE. Verifica che il flusso sia coerente con l'architettura attuale.
3. **Symbol con sell singolo che fa esattamente N positivi consecutivi mentre holdings=0**: trigger inutile. Va comunque flaggato saturated o no? Mia opinione: **sì, flaggato**. Perché altrimenti permettiamo buy successivi (= rotazione) sulla stessa coin spremuta. Conferma se sei d'accordo.
4. **Race condition** tra forced sell e nuovo buy decision in flight: il flag saturated va settato **prima** del forced sell o subito dopo? Probabilmente prima, per evitare che un altro thread/loop avvii un buy nel frattempo. Decidi tu sulla base dell'architettura concorrente attuale.

---

## 8. Commit message suggerito

```
feat(tf): add gain-saturation circuit breaker (filter 45g)

Forces exit when a TF-managed coin completes N positive sells in the
current allocation period. Liquidates any residual holdings at market
and flags the coin as saturated until the next ALLOCATE.

- New global config: tf_exit_after_n_positive_sells (default 4),
                     tf_exit_after_n_enabled (default TRUE)
- New per-coin override: bot_config.tf_exit_after_n_override (NULL = use
  global default). Preserved across ALLOCATE cycles.
- Counter computed stateless from trades table
- Saturated flag in-memory, reset on next ALLOCATE
- Telemetry: bot_events_log with category='TF_GAIN_SATURATION',
  details include n_threshold and was_override flag
- Telegram notification on trigger (private channel only)

Backtest on 27 closed periods (15-27 Apr): +$35.30 edge at N=4,
asymmetric win/loss profile (~5x), trigger 14/27 cases.
See exit_after_n_positive_sells_proposal.md for full analysis.
```

---

**Tutto chiaro? Domande prima di iniziare? Bandiera bianca quando hai finito.**
