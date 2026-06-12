# BUSINESS_STATE.md — Aggiornamento S103 (2026-06-12)

Istruzione per CC: aggiorna le seguenti sezioni di BUSINESS_STATE.md. Lascia invariato tutto il resto.

---

## §3 Diary Status — SOSTITUIRE il blocco sessione corrente

**Sessione corrente: 103 BUILDING** (Sherpa Board params + dashboard brain pipeline + memory compaction). S102 → COMPLETE. S101 → COMPLETE.

---

## §4 Decisioni Strategiche Recenti — AGGIUNGERE in cima alla tabella

| 2026-06-12 (S103) | **4 parametri protettivi → Sherpa-managed dinamici** (ribalta S102 "statici Board-only"). BOARD_TABLE per (regime × volatility tier LOW/MID/HIGH). Debounce 24h su coppia (regime,tier) persistito in `sherpa_board_state` (aggiunta CC, non nel brief). Cooldown 24h su override manuale invariato |
| 2026-06-12 (S103) | **Dashboard §2 pubblica redesign: brain pipeline verticale** (NewsKeeper→Sentinel→Sherpa). Card live full-width con connettori BAROMETER(shadow)/REGIME. Polling 5min. Anche TF/Grid trader cards ridisegnate. Token nuovo `--color-bot-news`. Sherpa pill: DRY_RUN→LIVE |
| 2026-06-12 (S103) | **Dashboard privata grid.html: 3 sezioni per coin** — Trading by Board / Grid by Sherpa / Security by Sherpa. Min Profit spostato da Grid a Security |
| 2026-06-12 (S103) | **Memoria CEO compattata**: da 29 a 21 voci (su 30 max). 4 rimosse, 4 fuse, 2 aggiornate. Slot fisso #21 per agenda prossima sessione |

---

## §6 Vincoli — AGGIORNARE queste righe

- **Sherpa LIVE su testnet** → ✅ DONE (S102+S103). Scrive TUTTI E 7 i parametri: buy_pct, sell_pct, idle_reentry_hours + stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours, profit_target_pct. Debounce 24h sui 4 protettivi

---

## §7 Cosa NON Sta Succedendo — AGGIORNARE queste righe

- **Sherpa controlla 3/7 parametri strategici** → SOSTITUIRE CON: **Sherpa controlla 7/7 parametri Grid** | LIVE su testnet. I 3 strategici (buy/sell/idle) scalano con volatility multiplier continuo. I 4 protettivi (stop_buy_dd/unlock, dead_zone, min_profit) usano lookup discreto per (regime × volatility tier) con debounce 24h. Board-only restano SOLO: allocation, $/trade, skim |
