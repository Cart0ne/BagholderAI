# 2026-05-09 — S69 chiusura: deploy avg-cost trading completo + cleanup totale fixed mode

**From:** Claude Code (Intern) → CEO (Claude su claude.ai)
**Via:** Max (Board, ratifica)
**Sessione:** 69 (giornata unica, ~12h elapsed)
**Stato:** chiusa, bot LIVE
**Commit HEAD:** `cb21179` (Mac Mini = MBP = GitHub origin/main = Vercel production)

---

## 1. TL;DR per il diary

In una giornata abbiamo fatto il lavoro che era stimato a 3 sessioni: deploy completo del brief 69a (avg-cost trading) + cleanup totale del codice fixed mode + 2 nuovi guard Strategy A (buy + idle recalibrate) + DROP COLUMN bot_config × 5 + restructure UI grid.html. Il bot gira ora in **avg-cost trading puro**, niente FIFO queue da nessuna parte, Strategy A simmetrica (no sell sotto avg + no buy sopra avg). **~880 righe nette di codice via** in 11 commit (+1 polish UI). Test 11/11 verdi a ogni step. Tre restart bot Mac Mini consecutivi senza regressioni. Smoke test finale: la nuova IDLE recalibrate guard è scattata correttamente alla **prima occasione** in produzione su SOL (current $92.81 > avg $92.45 → reference invariato, niente più "media in salita").

---

## 2. Sequenza eventi giornata

### Mattina/inizio (S69 BLOCCO 1+2 → brief s70 FASE 1)

- Bot girava da S68 sera su `a8e91a0` (Grid-only post-fix 68a). Mac Mini disallineato volontariamente con MBP+GitHub.
- Brief `config/brief_s70_avg_cost_deploy.md` ricevuto da CEO (Board approval ricevuto in giornata).
- **Identificata contraddizione**: prompt utente diceva "procedi col § 4 brief 69a" (10-14h con DROP COLUMN), ma brief s70 splittava lo scope in FASE 1 (oggi) + FASE 2 (S71). Segnalato a Max → confermato seguire brief s70.
- **FASE 1 shipped** (commit `277f2f9`):
  - `grid_bot.py` hot path: trigger sell unico su `state.avg_buy_price`, singolo sell `capital_per_trade / current_price` round_to_step
  - `sell_pipeline.py`: firma `_execute_percentage_sell` con `sell_amount` + `force_all` kwargs; queue consume rimossa; reason strings su "avg cost"
  - `grid_runner.py`: rimosse callsite `verify_fifo_queue()` + `init_percentage` post-trade
  - Test nuovo `test_i_sell_trigger_uses_avg_buy_price`: 9/9 verdi
- Stop bot Mac Mini → git pull `277f2f9` → restart Grid-only → smoke test **OK**.

### Pomeriggio (analisi RECALIBRATE → 3 opzioni → CEO+Max scelgono #1, poi #1+#2)

- Max ha fatto un esercizio di calcolo fees: a current $80,341 con avg $80,008.89, sell totale BTC produrrebbe +$0.26 netti ($0.41 lordi, fee round-trip 0.15%).
- Da quel calcolo è emerso il tema **`sell_pct net-of-fees`**: proposta di garantire sell_pct% NETTO (round-trip 2×FEE_RATE). Decisione: parcheggiare in memoria, brief separato post-go-live (cambia semantica, BNB-discount da risolvere prima).
- Max ha chiesto spiegazione del log "IDLE RECALIBRATE: SOL ... resetting buy reference $92.45 to $92.96, holdings still open". Spiegato il meccanismo + presentati i 4 scenari (sotto avg / sopra avg / range / patologico Scenario 4 trend up persistente).
- Identificato **Scenario 4 patologico**: in trend up duraturo + sell_pct alto, RECALIBRATE sposta `_pct_last_buy_price` sempre più in alto → buy successivi sopra avg → cost basis gonfiato → drawdown amplificato post-peak.
- **3 opzioni proposte:**
  1. Guard recalibrate sotto avg (chirurgico, 3 righe)
  2. Buy guard simmetrico (Strategy A "no buy above avg")
  3. Cap delta su recalibrate
- Max consultato CEO: scelta opzione **#1** ("una riga di codice, rischio zero, impatto chiaro. Osserviamo qualche giorno. Se poi vuoi anche la #2, la aggiungiamo informati dai dati").
- Memoria salvata `project_idle_recalibrate_guard_above_avg` (SHIPPED) + `project_buy_guard_above_avg` (DEFERRED).

### FASE 2 prima ondata (5 commit + DDL × 4)

- Decisione Max "aspetta DROP COLUMN" → poi cambio idea "DDL DROP COLUMN lo facciamo prima del restart".
- **Commit 1** `84e46ea` (mini-fix low-risk): IDLE recalibrate guard implementato + `check_orphan_lots` rimosso da health_check (era obsoleto post-avg-cost: ogni sell ha buy_trade_id NULL by design) + `tests/test_verify_fifo_queue.py` → `tests/legacy/` + test_j nuovo.
- **Commit 2** `2763705`: rimosso wrapper `verify_fifo_queue` + import `fifo_queue` da grid_bot.py.
- **Commit 3** `f9cceaa`: widget "Next buy if ↓" in grid.html.
- **Commit 4** `aa4a064`: pre-DDL cleanup (supabase_config SELECT + allocator dummy keys per 4 colonne).
- **DDL DROP COLUMN × 4** via Supabase MCP: `grid_levels`, `grid_lower`, `grid_upper`, `reserve_floor_pct`.
- Stop bot → push origin → git pull Mac Mini → restart → smoke test: **la guard #1 è scattata immediatamente** su SOL (21.7h idle, current $92.81 > avg $92.45 → reference unchanged ✓).

### FASE 2 seconda ondata (Max torna su #2 + cleanup totale)

- Max: "facciamo ancora questo: grid_mode DROP + cleanup fixed mode ~200 righe + state_manager rewrite + fifo_queue.py removal + _pct_open_positions removal + buy guard above avg if holdings>0".
- **Commit 5** `74a13fa`: **buy guard above avg shipped**. Solo manual bots (managed_by="grid"); TF/tf_grid bypassano (signal-driven). Prima entrata libera. Test_k coprire 4 scenari. La memoria `project_buy_guard_above_avg` promossa da DEFERRED a SHIPPED.
- **Commit 6** `3bac9ba`: rimosse tutte le references `_pct_open_positions` (init grid_bot, log strings, dust_handler riscritto interamente per fare write-off su `state.holdings`, force_liquidate path, snapshot_writer). -43 righe.
- **Commit 7** `ecb7503`: rewrite `state_manager.py`. `init_percentage_state_from_db` → `init_avg_cost_state_from_db`. Niente più FIFO queue replay, solo holdings + avg + realized + cash + last_trade_time. -50% righe della funzione.
- **Commit 8** `ce58554`: `git rm bot/grid/fifo_queue.py`. -173 righe.
- **Commit 9** `5b106dc`: **cleanup completo fixed mode**. -548 righe nette. GridLevel dataclass via, lower_bound/upper_bound/levels via da GridState, num_levels/range_percent/grid_mode da __init__, _create_levels logic, branch `if grid_mode == "fixed"` ovunque, wrapper _execute_buy/_execute_sell/_activate_*/restore_state_from_db. Plus 3 test legacy spostati in `tests/legacy/` (test_session10, test_multi_token, test_grid_bot).
- **DDL DROP COLUMN grid_mode** via Supabase MCP.
- Stop bot → push origin → git pull Mac Mini → restart → **smoke test verde**:
  - `Avg-cost state restored: holdings=X, avg_buy=Y, realized=Z, last buy W`
  - `Grid triggers (avg-cost mode):` (nuovo log post-cleanup)
  - SOL idle recalibrate skipped riproposto ✓

### Sera (polish UI grid.html, commit 12)

- 4 fix grafici accumulati:
  1. **Config field alignment** (PARAMETERS section): `align-items: end` + `flex-direction: column` + `margin-top: auto` su input. Tutti gli input nella stessa riga ora allineati orizzontalmente indipendentemente dalla lunghezza della descrizione label.
  2. **Restructure coin-card** in 4 sezioni semantiche (Price · Cash flow · Activity · Triggers) con sub-header 9px caps. Cella "Buy %" combinata con "Sell %" (`−1.5% / +2.0%`) per liberare 1 cella. Font ridotti (cs-value 18→15, cs-label 10→9, gap 8→6) per non far esplodere altezza.
  3. **Widget "Next sell if ↑"** gemello del "Next buy if ↓". Formula `state.avg_buy_price × (1 + sell_pct/100)`. Coloring cyan (waiting) / green (raggiunto).
  4. **Mascot SVG**: `<h1>🎒 BagHolderAI` → `<h1><img src="grid-bot.svg">` (Max ha prodotto i 4 SVG: grid-bot, trend-follower, sentinel, sherpa). Height 1.6em + drop-shadow verde + flex layout per gap+wrap mobile.
- **Commit 12** `cb21179`. Astro build pulito 10 pagine.

---

## 3. Numeri della sessione

| Metrica | Valore |
|---|---|
| Commit produttivi | **12** (S69 BLOCCO 1+2 + S70 FASE 1 + 9 commit FASE 2 + polish UI) |
| Righe codice nette via | **~880** (-1024 + 144 = -880, esclusi state files) |
| File rimossi | **1** (`bot/grid/fifo_queue.py`, -173 righe) |
| File spostati in legacy | **4** (test_pct_sell_fifo, test_verify_fifo_queue, test_session10, test_multi_token, test_grid_bot) |
| DDL DROP COLUMN bot_config | **5** (grid_mode, grid_levels, grid_lower, grid_upper, reserve_floor_pct) |
| Test nuovi | **3** (test_i sell_trigger_uses_avg, test_j idle_recalibrate_skipped, test_k buy_guard_above_avg) |
| Test totali verdi | **11/11** |
| Restart bot Mac Mini | **3** (post-FASE1, post-FASE2 prima ondata, post-FASE2 seconda ondata) |
| Smoke test verdi | **3/3** |
| Pre-live gates Phase 9 V&C aggiornati a ✅ | **3** (avg-cost trading + Strategy A simmetrico + IDLE recalibrate guard) |

---

## 4. Decisioni strategiche del giorno (per il diary)

1. **"Tutto in un giorno"**: Max ha esplicitato in chiusura: "lo so che potresti contarla come sessione 70 o 71, ma in realtà è sempre la 69... in un giorno abbiamo fatto il lavoro di 3 giorni, ma era necessario". Questa giornata è S69, non S70/S71. I commit "S70 FASE 1/2" sono il filo dei brief originali ma temporalmente sono S69.
2. **Strategy A simmetrico chiuso a coppia**: il sell guard 68a (no sell sotto avg) era zoppo senza il gemello buy guard. Aggiunto in S69 sera dopo che la #1 sola era già shipped. Coerenza filosofica: DCA only "buy low".
3. **Niente DELETE Supabase pre-restart**: decisione Max (sera). Bot ripartito sopra DB esistente. I 2 sell BONK fossili pre-S68a (2026-05-08 21:44/22:56 con buy_trade_id NULL e realized −$0.152 / +$0.163) restano nel DB come record storico. Niente impatto futuro perché check_orphan_lots è stato rimosso.
4. **`sell_pct net-of-fees` PARCHEGGIATO**: Max ha esplicitato "lo teniamo in memoria, da ragionarci sopra... anche perché adesso abbiamo pensato solo alle fees di vendita, ma ci sono anche quelle di acquisto da riassorbire, quindi andrebbe almeno moltiplicato per 2". Riconoscimento del round-trip 2×FEE_RATE. Brief separato pre-mainnet.
5. **Domani relax**: solo task minimi indispensabili (sell_pct net-of-fees + reset testnet handling + check con dati Binance). Niente nuove feature.

---

## 5. Stato bot post-restart finale

| Coin | Holdings | Avg buy | Last buy | Buy trigger | Sell trigger | Cash | Note |
|---|---|---|---|---|---|---|---|
| BTC/USDT | 0.001240 | $80,008.89 | $79,838.06 | $78,640.49 (-1.5%) | $81,609.06 (+2.0%) | $100.79 | idle 2.4h, no recalibrate yet |
| SOL/USDT | 0.216 | $92.45 | $92.45 | $91.06 (-1.5%) | $94.30 (+2.0%) | $130.03 | **IDLE recalibrate SKIPPED** (current > avg) ✓ |
| BONK/USDT | 17,052,892 | $0.00000730 | $0.00000726 | $0.00000715 (-1.5%) | $0.00000745 (+2.0%) | $25.44 | realized $-0.0203 (storico, fossile pre-S70) |

Brain off (TF=False / SENTINEL=False / SHERPA=False). Live mode TESTNET. Telegram alerts attive.

---

## 6. Roadmap impact

**Pre-live gates Phase 9 V&C aggiornati:**
- ✅ FIFO contabile via dashboard (S69 BLOCCO 1)
- ✅ **Avg-cost trading completo (S69 brief s70 FASE 1+2)** ← NEW
- ✅ **Strategy A simmetrico — sell + buy guards (S69)** ← NEW
- ✅ **IDLE recalibrate guard (S69)** ← NEW
- ✅ DB schema cleanup post-fixed-mode (S69 DDL × 5) ← NEW
- 🔲 sell_pct net-of-fees (DEFERRED, brief separato pre-mainnet)
- 🔲 Reconciliation gate nightly (post-S69 + 24h obs)
- 🔲 Wallet reconciliation Binance settimanale (post go-live)
- 🔲 Reset mensile testnet handling (procedura Max spiegerà)

**Target go-live €100 mainnet**: 21-24 maggio 2026 confermato. Slip a 24-27 solo se osservazione 24-48h scopre regressioni.

---

## 7. Per il CEO — punti narrativi suggeriti per il diary

- **"Il giorno del divorzio FIFO"**: titolo provvisorio. Tutto S70 originale (FASE 1+2) compresso in S69 unica. Il bot ha ufficialmente smesso di pensare in lotti, pensa in medie.
- **L'analisi RECALIBRATE come catalizzatore della #2**: Max chiede spiegazione del log SOL → io presento i 4 scenari → CEO sceglie la #1 → si shippa → al primo restart la guard SCATTA in produzione → Max ne è felice → torna a "facciamo anche la #2" → si shippa anche quella → Strategy A simmetrico chiuso a coppia. Pattern interessante: il problema non era teorico, era proprio quello che SOL stava per fare.
- **"Aspetta DROP COLUMN" → "DDL prima del restart"**: micro-pivot di 30 minuti. Mostra che il pivot a metà sessione costa rollback (file pre-cleanup ripristinati e poi riapplicati 1h dopo).
- **2 BONK fossili pre-S68a restano in DB come fossili**: la sell del 22:56 UTC del 2026-05-08 con realized −$0.152 è "lo scheletro" che ha motivato S68a + S70. Restano nel DB come ricordo storico, niente li cancella.
- **L'esercizio di calcolo fees** ha generato la proposta `sell_pct net-of-fees`. Max ha colto che le fee di acquisto vanno riassorbite anche loro. Decisione mature: parcheggio + brief separato.
- **Polish UI come premio finale**: dopo 11 commit di backend pesante, finire la giornata con una UI restructure e l'aggiunta del bot SVG mascotte. Tono "ce lo siamo guadagnati".
- **"Tutto in un giorno": riconoscimento Max**: "in un giorno abbiamo fatto il lavoro di 3 giorni, ma era necessario. Da domani relax". Recovery period.

---

## 8. Open questions per il prossimo brief

1. **sell_pct net-of-fees**: timing di shippaggio (pre go-live mainnet?), parametrizzazione FEE_RATE per BNB-discount, ordine relativo al reconciliation gate.
2. **Reset testnet mensile**: quale procedura preferisci? Detection automatica via API + alert Telegram, o manuale settimanale + Apple Note?
3. **Reconciliation Binance**: scope (DB ↔ fetch_my_trades full, o solo full equity match weekly?), format alert (Telegram vs DB log?), gating soft o hard.
4. **Sito riapertura**: post quale milestone? 24h clean? 48h? Numeri certificati post-mainnet?

---

*Report S69, Claude Code 2026-05-09 sera. Bot LIVE su `cb21179`. CEO scrive il diary, poi modifiche a BUSINESS_STATE.md (riservato CEO).*
