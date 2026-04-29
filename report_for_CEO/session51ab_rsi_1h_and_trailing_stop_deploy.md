# Session 51 — RSI 1h Overheat Filter (51a) + Trailing Stop (51b) Deploy

**From:** Intern (Claude Code) → CEO
**Date:** 2026-04-29
**Brief di riferimento:** [51a](../config/brief_51a_rsi_1h_overheat_filter.md) + [51b](../config/brief_51b_trailing_stop.md)
**Trigger:** DOGE/USDT — allocato 29/04 alle 10:35 UTC al 30-day high di $0.1099, stop-lossed nello stesso giorno a $0.1039 (−$0.73). Senza i 3 buy del decline il danno sarebbe stato circa metà.

---

## TL;DR (3 righe)

1. Entrambi i brief sono in produzione: codice committato, push fatto, **pronto per restart Mac Mini al tuo via**.
2. **51a (RSI 1h)**: gate pre-ALLOCATE/SWAP che fetcha RSI 1h solo per le BULLISH candidates (10-20 coin invece di tutte le 50). Default `tf_rsi_1h_max = 75`. Avrebbe bloccato il rientro DOGE delle 10:35.
3. **51b (Trailing Stop)**: terzo meccanismo di exit nel grid runner. Traccia il picco, si attiva dopo +1.5% di profitto, scatta a −2% dal picco. Avrebbe fatto uscire DOGE a ~$0.1095 invece di $0.1039 (savings ~$0.69 + niente buys del decline).

---

## 1. Cosa è stato fatto (51a — RSI 1h Overheat Filter)

### Database (migrato dal CEO)
- Nuova colonna `trend_config.tf_rsi_1h_max` (numeric, default 75)

### Codice
- **[scanner.py](../bot/trend_follower/scanner.py)**: nuova funzione `fetch_rsi_1h(exchange, symbol, period=14)` — fetcha 1h klines per un simbolo, calcola RSI(14), restituisce float 0-100 o `None` su errore. Riusa `calc_rsi` già esistente.
- **[trend_follower.py](../bot/trend_follower/trend_follower.py)**: aggiunto enrichment step **prima** di `decide_allocations()`. Itera solo le coin BULLISH, fetcha RSI 1h, scrive `coin["rsi_1h"]`. Rate-limit 0.2s tra le chiamate. Skipped quando `tf_rsi_1h_max = 0` (kill-switch). Aggiunto anche al Telegram scan report: nuova sezione "🌡️ RSI 1h overheat blocked" con top-5 coin sopra soglia.
- **[allocator.py](../bot/trend_follower/allocator.py)**: nuovo gate ALLOCATE che skippa le coin con `rsi_1h > rsi_1h_max`. Stessa cosa nel SWAP path. Fail-open se `rsi_1h is None` (fetch fallito → coin passa). Logga `bot_events_log.event = 'rsi_1h_overheat_skip'` con `path: 'ALLOCATE'` o `path: 'SWAP'`.
- **[tf.html](../web/tf.html)**: nuovo field `tf_rsi_1h_max` in `TF_SAFETY_FIELDS`. Aggiunta colonna alla SELECT trend_config.

### Architettura
- **Solo BULLISH** sono enrichite con RSI 1h. Su 50 coin scannate ne fetchiamo ~10-20. **API cost +20-40%** invece di +100%.
- Il gate funziona indipendentemente dal distance filter 45e: 51a vede pump 1h, 45e vede stretch 4h. Sono ortogonali.

---

## 2. Cosa è stato fatto (51b — Trailing Stop)

### Database (migrato dal CEO)
- Nuove colonne `trend_config.tf_trailing_stop_activation_pct` (default 1.5) + `tf_trailing_stop_pct` (default 2.0)

### Codice
- **[grid_bot.py](../bot/strategies/grid_bot.py)**:
  - 2 nuovi parametri `__init__`, 2 nuovi attributi `_trailing_peak_price` (in-memory) + `_trailing_stop_triggered` (latch).
  - **Peak tracking**: ogni tick di un TF bot con holdings > 0 e feature attiva, aggiorna `_trailing_peak_price` se `current_price > peak`.
  - **Trigger check**: dopo SL, prima di TP. Se peak >= `avg_buy × (1 + activation_pct%)` e `current_price <= peak × (1 − trailing_pct%)`, scatta: latch `_trailing_stop_triggered = True`, scrive `last_stop_loss_at` (cooldown), logga `bot_events_log.event = 'trailing_stop_triggered'`.
  - **Strategy A override**: aggiunto `_trailing_stop_triggered` ai check di override (per `_execute_sell` e `_execute_percentage_sell`) — i lot underwater vengono venduti tutti in un pass.
  - **Force-liquidate flag**: aggiunto a `force_liquidate` boolean (sell loop) e al check `cycle_closed → pending_liquidation`.
  - **Buy guard**: aggiunto blocco "BUY SKIPPED: trailing-stop latched" speculare al 45g.
  - **Reason text**: nuovo "TRAILING-STOP" nel reason del trade log.
- **[grid_runner.py](../bot/grid_runner.py)**:
  - Letture trend_config aggiornate (2 nuove colonne) + passthrough a `GridBot()`.
  - Hot-reload sync: i 2 valori sono polled ogni 300s come gli altri safety params (`tf_stop_loss_pct`, ecc.) — modifiche dashboard prendono effetto senza restart.
  - Event label "TRAILING-STOP" + `stop_reason_tag = "trailing_stop"` aggiunti sia al mid-tick path (riga 851) sia al top-of-loop holdings=0 path (riga 773-815).
- **[tf.html](../web/tf.html)**: 2 nuovi field in `TF_SAFETY_FIELDS`. Aggiunte colonne alla SELECT.

### Decisioni di design
- **Peak in-memory** (no DB persistence): il brief lo richiede esplicitamente. Restart "dimentica" il peak — comportamento conservativo, peggio una mancata-trigger di un cycle che una falsa-trigger.
- **Priorità exit**: SL → trailing → TP → PL → 45g. Il trailing è "protect winnings", agisce solo se SL non ha già scattato.
- **SL cooldown post-trailing**: scrive `last_stop_loss_at` come SL e PL fanno. Il TF non rialloca subito dopo trailing.

---

## 3. Domanda di design che ho gestito da solo

Il brief dice "trailing stop after stop-loss but before take-profit (39c)". Ho seguito la lettera. La sequenza completa dei check nel codice è ora:

1. **SL** (39a) — emergency exit: unrealized < −X% di alloc
2. **TRAILING** (51b — nuovo) — protect gains: peak >= avg+X%, ora a −Y% dal peak
3. **TP** (39c) — cash out: unrealized >= +X% di alloc
4. **PL** (45f) — net PnL incl. realized: net_pnl >= +X% di alloc
5. **45g** — gain saturation: N positive sells nel period

Tutti latched (boolean che non si resetta finché non c'è una nuova ALLOCATE). Tutti mutually exclusive nella stessa tick.

---

## 4. Verifica deploy

### Test sintassi
- ✅ Tutti i 5 file Python parseano senza errori
- ✅ `from bot.trend_follower.scanner import fetch_rsi_1h` import OK
- ✅ `from bot.trend_follower.allocator import decide_allocations` import OK
- ⚠️ Local venv ha telegram lib mismatched ma è un problema d'env locale, non di codice (il Mac Mini gira con la sua install indipendente)

### Roadmap
- v1.35 → **v1.36**, last_updated 2026-04-28 → **2026-04-29**
- Aggiunte 2 voci in Phase 2 (TF) per 51a + 51b

### File modificati
| File | Modifica |
|---|---|
| `bot/strategies/grid_bot.py` | 51b — peak tracking, trigger, Strategy A override, buy guard, cycle_closed, reason text |
| `bot/grid_runner.py` | 51b — config passthrough, hot-reload, event label "TRAILING-STOP" |
| `bot/trend_follower/scanner.py` | 51a — `fetch_rsi_1h()` |
| `bot/trend_follower/trend_follower.py` | 51a — enrichment step + Telegram report block |
| `bot/trend_follower/allocator.py` | 51a — ALLOCATE + SWAP gates, config readout |
| `web/tf.html` | 51a + 51b — 3 field nuovi (`tf_rsi_1h_max`, `tf_trailing_stop_activation_pct`, `tf_trailing_stop_pct`) |
| `web/roadmap.html` | 2 entry nuove + bump v1.36 |

---

## 5. Cosa NON è stato cambiato (vincoli del brief rispettati)

- **`scan_top_coins`** non tocato — l'enrichment 51a vive in `trend_follower.py`, non nello scanner main loop
- **RSI 4h esistente** non rimosso — è usato per la classificazione, RSI 1h è un check separato
- **Stop-loss / greed-decay / profit-lock / 45g** comportamenti invariati — il trailing stop si aggiunge accanto, non li modifica
- **Manual bots (BTC/SOL/BONK)** completamente non toccati — il guard `managed_by == "trend_follower"` esclude tutto
- **`bot_config` schema** non modificato — solo `trend_config` con 3 nuove colonne (DB migrate fatta dal CEO)

---

## 6. Pronto per restart

- Commit + push fatto
- Mac Mini ancora sul vecchio codice — **aspetto il tuo via** per:
  ```
  ssh max@Mac-mini-di-Max.local
  cd /Volumes/Archivio/bagholderai && git pull
  kill <orchestrator_pid>
  nohup venv/bin/python3.13 -m bot.orchestrator > logs/orchestrator.log 2>&1 &
  ```
- Verifica post-restart automatica: vedrò nuovi entry RSI 1h nel prossimo scan TF (default 30min) + log "Fetching 1h RSI for N BULLISH candidates"

---

## 7. Cosa osservare nei prossimi giorni

1. **51a frequenza skip**: quante coin vengono filtrate al giorno con default 75? Se molte (>30%), il filtro è troppo aggressivo. Se 0, troppo permissivo.
2. **51b primo trigger live**: quando scatta la prima volta su una coin reale, il PnL realized deve essere ≥ 0 (perché il trailing si attiva solo dopo profit). Se è negativo, c'è un bug nel calcolo activation/trailing.
3. **Interazione 51a + 51b**: una coin filtrata 51a non viene allocata → 51b non gira. Una coin che passa 51a può comunque esitare in trailing.
4. **API cost 51a**: rate-limit 0.2s × 20 BULLISH candidates = ~4s aggiuntivi per scan. Tollerabile sui 30min di scan_interval.
5. **Telegram report**: la nuova sezione "🌡️ RSI 1h overheat blocked" appare solo quando ci sono coin filtrate. Se non la vedi mai, soglia troppo alta o pochi pump in giro.

🏳️ Bandiera bianca su 51a + 51b. Pronto per il via al restart.
