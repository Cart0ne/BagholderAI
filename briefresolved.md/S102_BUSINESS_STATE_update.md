# BUSINESS_STATE.md — Aggiornamento S102 (2026-06-11)

Istruzione per CC: aggiorna le seguenti sezioni di BUSINESS_STATE.md. Lascia invariato tutto il resto.

---

## §3 Diary Status — SOSTITUIRE il blocco sessione corrente

**Sessione corrente: 102 BUILDING** (Sherpa coherence audit + go-live testnet + NewsKeeper v2 shadow check T+36h). S101 → COMPLETE. S100 → COMPLETE.

(il resto di §3 invariato)

---

## §4 Decisioni Strategiche Recenti — AGGIUNGERE in cima alla tabella

| 2026-06-11 (S102) | **Principio ownership parametri: Board = soldi, Sherpa = strategia** | Max: "Io controllo allocation, $/trade, skim. Sherpa controlla tutto il resto. Se sovrascrivo, cooldown 24h." Tre frasi che risolvono idle, circuit breaker, sell penalty |
| 2026-06-11 (S102) | **Sherpa GO LIVE su testnet** (brief S102b, env flag `SHERPA_MODE=live`, deploy pending restart). Scrive buy_pct, sell_pct, idle_reentry_hours | DRY_RUN non produceva dati utili (cap ±30% su config congelata = 50K righe identiche). Testnet = zero rischio finanziario. CC report S102: tutti e 5 regimi implementati, coin-agnostic confermato |
| 2026-06-11 (S102) | **idle_reentry_hours: Opzione C** — Sherpa riporta idle dentro il range di design (0.5-6h). L'8h attuale era un default mai rivisto | Il cap ±30% rende la transizione graduale (8→5.6→...→target in 2-7 tick). In extreme_fear stop_buy=ON rende idle irrilevante |
| 2026-06-11 (S102) | **4 parametri restano Board-only**: stop_buy_drawdown_pct e min_profit_pct universali (uguali per tutti i coin); dead_zone_hours e stop_buy_unlock_hours per-coin ma statici (microstructura, non regime). Default automatici per coin nuovi | Nessuno dei 4 ha una tesi forte per diventare dinamico per regime. Sicurezza ≠ strategia |
| 2026-06-11 (S102) | **Write guard Sherpa shippato** (commit `a867179`, deploy pending restart). Volume atteso: ~18 righe/gg (-99%) | Filtro write-on-change esisteva (S79c) ma bypass su stop_buy in extreme_fear. Fix: gate flip-based + heartbeat 4h |
| 2026-06-11 (S102) | **NewsKeeper v2 "Barometro" shadow check T+36h: sano** | 203 segnali, 0 fallback Haiku, flip neutral→bearish a T+4h, stabile bearish 31h. abstain_frac=0. Verdetto T+14 ~23 giugno |

---

## §5 Domande Aperte per CC — AGGIORNARE queste righe

- **[S83] NewsKeeper S2** → cambiare stato a: ✅ DONE (S94 + T+7 quality review S100). V2 Barometro in shadow, verdetto T+14 ~23 giugno
- **[S91] dead-band scritture Sherpa** dentro la riga integrità dati → cambiare a: ✅ DONE (S102a write guard `a867179`)
- **AGGIUNGERE:** | **[S102 NEW] Formalizzare parametri Board-only + default automatici coin nuovi** | S103 | Brief S103: documentare che stop_buy_dd, stop_buy_unlock, dead_zone, min_profit sono Board-only. Implementare default automatici (universali o per-coin basati su volatility multiplier) per quando si aggiunge un coin nuovo |
- **AGGIUNGERE:** | **[S102 NEW] Regime stickiness innesto barometro↔Sherpa** | Post-verdetto T+14 (~23 giu) + primo regime non-bear | Fattibilità confermata CC: opzione (a)+(c), ~5-7h, 4 file. Barometro modula la velocità del cap, non la destinazione. NON costruire prima del verdetto |

---

## §6 Vincoli — AGGIORNARE queste righe

- **NewsKeeper T+7 quality review** → ✅ DONE (S100, report shipped). V2 Barometro in shadow, T+14 ~23 giugno
- **Sherpa LIVE su testnet** → ✅ DONE (S102, deploy pending restart Mac Mini). Scrive buy_pct, sell_pct, idle_reentry_hours. Prossimo: S103 parametri Board-only + default
- **AGGIUNGERE:** | **NewsKeeper v2 Barometro T+14 verdetto** | ~23 giugno 2026 | Validare flip barometro vs ritorno prezzo BTC 24h. Se 14gg solo-bear: verdetto parziale, estendere. Esiti: promuovere (cablaggio Sentinel) o bocciare (→ /news, blog "esperimento fallito") |
- **Go-live mainnet** — aggiornare la sequenza a: Sherpa LIVE testnet ✅ → osservazione → S103 parametri Board-only → barometro verdict → Board approval → mainnet €100

---

## §7 Cosa NON Sta Succedendo — AGGIORNARE queste righe

- **Sherpa non controlla i grid bot** → SOSTITUIRE CON: **Sherpa controlla 3/7 parametri strategici** | LIVE su testnet (deploy pending restart). Scrive buy_pct, sell_pct, idle_reentry_hours. I 4 rimanenti (stop_buy_dd, stop_buy_unlock, dead_zone, min_profit) restano Board-only con default automatici (S103). Il principio ownership: Board=soldi, Sherpa=strategia |
