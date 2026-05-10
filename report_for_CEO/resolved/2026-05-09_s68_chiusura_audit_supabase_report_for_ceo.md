# S68 — Chiusura sessione: audit Supabase + handoff a nuova chat

**Data**: 2026-05-09
**Autore**: Claude Code (Intern)
**Destinatario**: CEO
**Stato sessione**: **CHIUSA** (handoff a nuova chat dedicata: grid.html + pulizia codice + restart)
**Decisioni Board**: nessuna ancora finalizzata; stiamo solo valutando scenari

---

## 1. Cosa è successo in S68

Sessione iniziata 2026-05-09 mattina con apertura forte del Board:

> "mood generale guardando i numeri… mi sa che falliamo"

Tre numeri pesavano: P&L testnet $0.06 in 24h, Payhip 0/30 visualizzazioni, fee > guadagno. CC ha indagato, fixato, brainstormato col Board, e si è arrivati alla chiusura con questo stato:

### Cose shipped in S68

1. **Brief 68a — Fix sell-in-loss guard** (commit `a8e91a0`)
   - `bot/grid/sell_pipeline.py`: guard "Strategy A no sell at loss" ora confronta `price < bot.state.avg_buy_price` (non più `lot_buy_price`).
   - Reason string aggiornata a "avg cost".
   - Test 8/8 verdi (`test_h_guard_blocks_sell_below_avg_even_above_lot_buy` aggiunto).
   - Bot Mac Mini restartato Grid-only, fix attivo.
   - Roadmap: pre-live gate Phase 9 V&C aggiunto.

2. **Brief 68b — Refactor `bot/strategies/` → `bot/grid/` + Python `managed_by` cleanup** (commit `39e05b7`)
   - 7 file rinominati con `git mv` (history preservata).
   - 23 import statements aggiornati.
   - Sostituzioni Python: `'trend_follower'` → `'tf'` (61), `'manual'` → `'grid'` (24, eccetto reason di stop Telegram).
   - Test 8/8 verdi.
   - **NON ancora applicato sul Mac Mini** (bot continua su `a8e91a0` con folder `bot/strategies/`). Apply è in stand-by per scelta Board.

3. **Verifica empirica testnet Binance**
   - Wallet testnet ha 446 asset preassegnati (USDT 9858, BTC 1.00, SOL 5.22, BONK 6.77M, OP 3,758, …). Il "$500" è una convenzione interna nostra, Binance non lo conosce.
   - History trades + orders persistente: i 12 trade live di ieri sera + 1 nuovo BONK buy delle 9:30 UTC stamattina.
   - Reset mensile automatico testnet: non confermato dall'output, da verificare in altra sessione.

4. **Scoperte / debt esposto**
   - Trigger sell in `grid_bot.py:749-752` (vincolo CEO "NON toccare grid_bot.py" lo lasciava intoccabile, scelta sua confermata).
   - Health check FIFO drift $0.28 ≈ slippage testnet ~1% sui BONK trade — comportamento atteso post-S66, non regressione.
   - `grid_runner.py` 1627 righe (di cui 833 in una singola funzione `run_grid_bot()`). Phase 2 split candidato (BUSINESS_STATE §28).
   - `main.py` + `main_old.py` gemelli inutili in root, debt da pulire.
   - **Fixed mode Grid è codice morto**: 0 record DB lo usa (57 bot_config tutti `grid_mode='percentage'`). Stima ~500-800 righe rimovibili.

---

## 2. Decisioni Board ancora aperte (stiamo valutando, NON deciso)

Brainstorming a fine sessione ha portato a queste valutazioni in corso:

| Tema | Posizione attuale Board |
|------|-------------------------|
| Filosofia | "Trading minimum viable. Complessità solo se valore aggiunto." |
| Scope | **Solo Grid attivo**. TF/Sentinel/Sherpa stay-but-off. Niente codice cancellato. |
| Bot live | Non spegnere, al limite riavviare se serve |
| Monete | 3 (BTC + SOL + BONK), Grid only |
| Budget testnet | **In valutazione**: $10K (allinea wallet ↔ DB) o restare $500 (convenzione interna) |
| `capital_per_trade` | Se $10K → ipotesi $200/$100/$100. Se $500 → resta $50/$20/$25 |
| Mainnet target | €100 invariato |
| Refactor 68b apply | Stand-by, valuta nuova chat |
| Audit tabelle Supabase | Fatto in chiusura S68 (vedi §3) |
| Pulizia fixed mode | Da fare in nuova chat insieme a pulizia generale |
| `grid_runner.py` Phase 2 split | Parcheggiato post-go-live (BUSINESS_STATE §28) |

---

## 3. Audit 22 tabelle Supabase

Dati estratti 2026-05-09 ~11:30 UTC.

### TIER 1 — Core Grid (KEEP, scrivono attivamente)

| Tabella | Righe | Ultimo write | Scopo | Verdetto |
|---------|-------|--------------|-------|----------|
| `trades` | 12 | 2026-05-09 09:30 | Log buy/sell del bot | ✅ KEEP |
| `bot_config` | 57 | 2026-05-08 21:49 | Parametri runtime per coin (3 active + 54 inactive TF legacy) | ✅ KEEP |
| `bot_state_snapshots` | 321 | 2026-05-09 11:05 | Snapshot stato bot ogni ciclo (recovery + audit) | ✅ KEEP |
| `bot_events_log` | 133 | 2026-05-09 07:24 | Lifecycle, trade, safety events | ✅ KEEP |
| `daily_pnl` | 1 | 2026-05-08 18:54 | P&L giornaliero aggregato (alimentato dal cron retention) | ✅ KEEP |

### TIER 2 — Sito + automation (KEEP)

| Tabella | Righe | Ultimo write | Scopo | Verdetto |
|---------|-------|--------------|-------|----------|
| `diary_entries` | 67 | 2026-05-08 19:46 | Diary sito pubblico, Volumi Payhip | ✅ KEEP |
| `daily_commentary` | 46 | 2026-05-08 18:55 | Haiku commentary giornaliera per X / dashboard | ✅ KEEP |
| `config_changes_log` | 86 | 2026-05-08 21:49 | Storico cambi parametri (alimenta Haiku context) | ✅ KEEP |
| `pending_x_posts` | 0 | mai | Coda post X (cron settimanale, infrastruttura) | ✅ KEEP |

### TIER 3 — Infrastrutturale (KEEP)

| Tabella | Righe | Ultimo write | Scopo | Verdetto |
|---------|-------|--------------|-------|----------|
| `exchange_filters` | 48 | 2026-05-02 13:27 | lot_step_size, min_notional Binance per coin | ✅ KEEP |
| `reserve_ledger` | 1 | 2026-05-08 21:44 | Skim profit ledger | 🟡 KEEP-IF-SKIM (se eliminate skim_pct, morta) |

### TIER 4 — Brain OFF (TF/Sentinel/Sherpa) — stay-but-off

| Tabella | Righe | Ultimo write | Scopo | Verdetto |
|---------|-------|--------------|-------|----------|
| `trend_decisions_log` | 1,388 | 2026-05-08 15:43 | TF scan decisions log | 🔵 ARCHIVIA (riattiva se accendiamo TF) |
| `sentinel_scores` | 2,827 | 2026-05-08 15:59 | Sentinel risk/opportunity scores | 🔵 ARCHIVIA |
| `sherpa_proposals` | 4,212 | 2026-05-08 15:59 | Sherpa parameter proposals (DRY_RUN dataset) | 🔵 ARCHIVIA |
| `counterfactual_log` | 1,337 | 2026-05-08 15:43 | Counterfactual replay (debt brief 67a Step 5) | 🔵 ARCHIVIA |
| `trend_config` | 1 | 2026-04-11 18:30 | Config singleton TF | 🔵 ARCHIVIA |
| `coin_tiers` | 2 | 2026-04-11 18:30 | Tier classification TF | 🔵 ARCHIVIA |

### TIER 5 — Morte / DROP candidati

| Tabella | Righe | Ultimo write | Scopo dichiarato | Verdetto |
|---------|-------|--------------|------------------|----------|
| `trend_scans` | **31,522** | 2026-05-08 15:43 | "TEMPORARY — full scan data for debugging tier splits. Delete after validation" (commento DB) | 🔴 DROP (più righe di tutto il resto, dichiarata temporanea, validation finita) |
| `portfolio` | 0 | mai | Tabella legacy, sostituita da `bot_state_snapshots` + dati derivati | 🔴 DROP |
| `feedback` | 0 | mai | Sistema feedback Sentinel mai implementato | 🔴 DROP |
| `agent_rules` | 0 | mai | Sistema "regole AI dinamiche" mai implementato | 🔴 DROP |
| `sentinel_logs` | 0 | mai | Vecchia tabella Sentinel (S?), sostituita da `sentinel_scores` | 🔴 DROP |

### Sintesi

- **KEEP**: 11 tabelle (core Grid + sito + automation + infrastrutturale)
- **ARCHIVIA**: 6 tabelle (TF/Sentinel/Sherpa, dati raccolti, mai eliminare in caso accendiamo)
- **DROP candidati**: 5 tabelle (mai usate o esplicitamente temporanee, totale ~31,524 righe morte)

**Risparmio se DROP**: 5 tabelle (-22% del DB attivo) e 31,524 righe rumore. Nessun impatto su Grid/sito/automation.

**Cosa NON fare adesso**: nessuna DROP, nessun TRUNCATE. La decisione su quali eliminare la prende il Board nella prossima sessione, durante la pulizia codice generale.

---

## 4. Stato runtime al momento della chiusura

- Bot Mac Mini: **LIVE** su commit `a8e91a0` (= fix 68a, folder ancora `bot/strategies/`)
- 4 processi: orchestrator 96199, BONK 96200, SOL 96201, BTC 96202
- Brain flags: `TF=False SENTINEL=False SHERPA=False` (Grid-only)
- Holdings BONK aumentate dopo buy 09:30 UTC (`6,829,370` BONK ≈ originali + buy nuovo)
- Total P&L approssimativo dashboard: stabile in zona +$0.10 / +$0.30 (variabile col prezzo)
- Nessun errore in logs, 1 warn (boot health check FIFO drift, già spiegato come comportamento atteso post-S66)

---

## 5. Handoff alla nuova chat

La prossima sessione (S68 continua o S69 nuova) dovrà coprire questi 3 macro-temi:

### Tema 1 — `grid.html` rebuild
- Le 3 anomalie già identificate: (a) label "fees not deducted in paper mode" obsoleta, (b) formula descrittiva skim "0.01% of net worth" sbagliata, (c) drift Total P&L vs Realized+Unrealized
- Card-by-card rebuild con i dati che il Board vuole vedere (NON ancora definiti — primo task della prossima sessione: definire cosa metterci)
- Eventuale sezione "Reconciliation Binance" (confronto periodico DB ↔ `fetch_my_trades`)
- Quando finita, gli stessi pattern andranno portati anche sulla dashboard pubblica

### Tema 2 — Pulizia codice
- **DROP** 5 tabelle morte (`trend_scans`, `portfolio`, `feedback`, `agent_rules`, `sentinel_logs`)
- **Rimozione fixed mode**: ~500-800 righe + 4 colonne DB (decision Board)
- **Rimozione `main_old.py`** gemello inutile
- **Apply 68b** sul Mac Mini (decision Board)
- **Phase 2 split `grid_runner.py`** (parcheggiato post-go-live, vedi §28)

### Tema 3 — Decisione budget + restart
- $10K vs $500 budget testnet (Board decide)
- Se $10K: aggiornare `MAX_CAPITAL`, `capital_allocation`, `capital_per_trade` proporzionalmente
- Eventuale TRUNCATE post-decisione + restart bot da zero su nuova baseline
- Sequenza step originale (8 step) S68 da rivalutare alla luce delle decisioni Board

---

## 6. Domande per il CEO (non bloccanti)

1. **Apply 68b**: lo facciamo nella nuova chat all'inizio (con un riavvio bot) o lo lasciamo locale finché non c'è motivo concreto di restartare?
2. **Audit DROP 5 tabelle**: confermi che possiamo droppare le 5 tabelle "morte" senza fare backup individuali (sono vuote o esplicitamente temporanee)? Backup completo del DB intero ovviamente sì prima di qualsiasi operazione distruttiva.
3. **Budget testnet $10K**: ne discutiamo nella nuova chat o vuoi dare un input strategico ora?
4. **Reset mensile testnet Binance**: vale la pena verificarlo formalmente (leggere docs Binance, monitoraggio ad-hoc) o accettiamo il rischio "1 volta al mese ci si resetta tutto"?

---

## 7. Cosa NON è stato fatto in S68

- ❌ NON shipped Step 5 reconciliation gate (era originalmente in scope, parcheggiato)
- ❌ NON shipped fix bug `exchange_order_id=null` su sell (debt cosmetico, BUSINESS_STATE §24)
- ❌ NON shipped fix `reason` bugiardo (BUSINESS_STATE §27)
- ❌ NON shipped fix `recalibrate-on-restart` (debt aperto da S63)
- ❌ NON aggiornato `BUSINESS_STATE.md` (lo aggiorno dopo questo report)
- ❌ NON aggiornato `PROJECT_STATE.md` (idem)
- ❌ NON ricalibrato Sentinel parametri (3 bug calibrazione, brain off, irrilevante per ora)
- ❌ NON shipped Phase 2 split `grid_runner.py` (rimandato post-go-live, BUSINESS_STATE §28)
- ❌ NON eliminato fixed mode (la nuova chat lo gestisce)

---

## 8. Roadmap impact

- **Pre-live gate Phase 9 V&C**: aggiunto "sell-in-loss guard verificato su avg_buy_price" come gate. ✅
- **Target go-live €100 mainnet**: confermato 21-24 maggio 2026 (Board: invariato).
- **Brief 68c (DB schema cleanup managed_by + brain CHECK constraint)**: PARCHEGGIATO. Verrà ripreso solo se Board sceglie scenario TRUNCATE+ALTER. Se Board sceglie "non TRUNCATE, solo audit DB DROP", il brief diventa più piccolo.
- **24h observation post-fix 68a**: scaduta, status passato (1 trade nuovo, 0 errori, holdings positivi).

---

*CC, S68 chiusura, 2026-05-09 ~12:00 UTC. Sessione next-action: nuova chat dedicata a (1) grid.html, (2) pulizia codice, (3) decisione budget+restart.*
