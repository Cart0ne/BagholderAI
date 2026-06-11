Brief S102b — sherpa-go-live — 2026-06-11

# Brief d'implementazione — Sherpa Go Live (testnet)

**SCOPE canonico:** `sherpa-go-live`
**Basato su:** Report `2026-06-11_S102_RforCEO_sherpa-coherence-audit.md`; decisione Board S102 (oggi).
**Stima:** < 30 min. Modifica config + verifica.

---

## 0. Cosa stiamo facendo, in una riga

Cambiare `SHERPA_MODE` da `DRY_RUN` a `LIVE`. Sherpa inizia a scrivere buy_pct, sell_pct, idle_reentry_hours in `bot_config` per i 3 coin attivi (BTC, SOL, BONK) su testnet_2.

## 1. Decisioni Board già prese (NON da ridiscutere)

1. **Sherpa LIVE su testnet con i 3 parametri attuali** (buy_pct, sell_pct, idle_reentry_hours). I 4 parametri mancanti (stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours, profit_target_pct) verranno aggiunti in un brief separato (S103).
2. **idle_reentry_hours — Opzione C**: accettare che Sherpa riporti idle dentro il range di design (0.5-6h). Nessuna modifica al clamp. L'8h attuale in bot_config verrà portato gradualmente al target dal cap ±30% (8→5.6→...→target).
3. **Principio di ownership**: Board controlla allocation, $/trade, skim. Sherpa controlla tutti i parametri strategici. Cooldown 24h già implementato come salvaguardia sulle override manuali del Board.

## 2. Cosa fare

1. Cambiare `SHERPA_MODE` da `DRY_RUN` a `LIVE` nel file di config appropriato (CC sa dove).
2. Commit, push su main.
3. Fornire a Max i comandi di restart per il Mac Mini (Sherpa + write guard fix della Parte A S102a, restart unico cumulativo).

## 3. Cosa verificare post-restart

- `sherpa_proposals`: volume ≤ ~20 righe/giorno (write guard attivo)
- `bot_config`: i valori di buy_pct, sell_pct, idle_reentry_hours cambiano rispetto ai valori statici attuali
- `config_changes_log`: le modifiche sono loggate con source `sherpa`
- Telegram: notifica di cambio parametri (se implementata)
- Nessun impatto su grid/tf/sentinel/newskeeper

## 4. Vincoli

- **NON toccare** logica Sherpa (regime mapping, parametri, scaling)
- **NON aggiungere** parametri alla whitelist (viene nel prossimo brief)
- **NON restartare** i bot — consegna comandi a Max
- Push diretto su main

## 5. Roadmap impact

Nessuno pubblico. Sherpa LIVE su testnet è un passo interno. La comunicazione avverrà solo dopo osservazione e decisione Board.

## 6. Auto-obiezione CEO

Sherpa ha visto solo regime bear (neutral→fear→extreme_fear). Stiamo attivando in LIVE un sistema che non ha mai operato in greed/extreme_greed. Risposta: è testnet, i soldi sono finti, e l'intero punto è iniziare a osservare il comportamento reale. In DRY_RUN osserveremmo la stessa cosa (cap su config congelata) all'infinito.
