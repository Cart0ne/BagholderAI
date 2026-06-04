# RforCEO — clean-slate-testnet (S96a)

**Da:** CC (Claude Code) · **A:** CEO + Max (Board) · **Data:** 2026-06-04 · **Sessione:** S96a
**Brief sorgente:** `briefresolved.md/2026-06-04_S96a_brief_clean-slate-testnet.md`
**Commit:** `a9aa48b` (lato bot + migration), `7b35a4a` (front-end + disclaimer) · **Esito:** ✅ SHIPPED

---

## Sintesi

Clean slate testnet (Opzione C) shippato e **live in produzione**. I 3 grid bot sono ripartiti puliti sul wallet post-reset; **BONK è sbloccato**. Nessun dato cancellato — tutto il pre-reset è archiviato e consultabile come ciclo `testnet_1`.

## Obiezione CC e scope esteso (approvato CEO)

Il brief prevedeva clean slate sul solo `trades`. Verificando il codice ho trovato che cash/dashboard restano sporchi: il cash al boot sottrae `reserve_ledger` (tabella separata, non derivata dai trade — `state_manager.py:174-180`), e le dashboard leggono `daily_pnl`/`bot_state_snapshots`. **CEO ha approvato l'estensione** del cycle tagging a tutte e 5 le tabelle.

## Cosa è stato fatto

**Lato DB/bot (`a9aa48b`):**
- Migration non-distruttiva: colonna `cycle` su `trades`, `daily_pnl`, `bot_state_snapshots`, `reserve_ledger`, `bot_config`. Righe esistenti → `testnet_1`; i 3 grid aperti su `testnet_2`. Nessuna riga cancellata (64 trades, 27 daily_pnl, 3617 snapshots, 19 reserve preservati).
- Foto ricordo: 3 eventi `testnet_reset_clean_slate` in `bot_events_log` con i numeri del ciclo chiuso (BONK: 21.6M holdings, avg $0.00000725, realized $8.26).
- Sorgente "ciclo corrente" data-driven: `get_current_cycle()` legge `bot_config.cycle` (cached). Replay al boot, reserve total e reconcile filtrano il ciclo corrente; i writer lo timbrano. **Prossimo reset = un solo `UPDATE bot_config`** (no codice, lato bot).
- Validato read-only su prod: 0 trade correnti + 0 reserve per tutti e 3 → boot pulito.

**Lato sito (`7b35a4a`, live su Vercel):**
- Dashboard (home `live-stats`, `/dashboard`, `grid.html`) filtrano `testnet_2` → 0 ordini/P&L, days-running azzerato.
- Disclaimer testnet aggiornato (saldi resettati senza preavviso + prezzi sintetici) con flag `IS_TESTNET`; banner anche su grid.
- STYLEGUIDE §22 + CSS `.prose-blog img` (Part 3).

## Verifica post-restart (live)

| Bot | Esito boot |
|---|---|
| BONK | ✅ holdings 0, cash $150 pieno, guardia 72a **passata** (surplus 18.446), 0 P&L |
| SOL | ✅ cash $150 pieno, stato 0 |
| BTC | ✅ cash $200 pieno, stato 0 |

Nessun loop di restart, nessuno spam Telegram, nessun errore al boot. TF/Sentinel/Sherpa/NewsKeeper non toccati.

## Bonus della sessione (pre-brief)

Trovato e corretto un **bug dell'orchestrator** (commit `722da6a`): un grid bot che esauriva i 5 restart veniva ri-spawnato all'infinito (spam Telegram). Emerso proprio dal blocco BONK post-reset.

## Note / follow-up per il CEO

- **§7 BUSINESS_STATE:** le righe "Reset testnet — Rimandato" (×2, duplicate) sono ora **superate** dalla realtà. Ho aggiunto la riga "BONK — RISOLTO" ma **non ho rimosso** le vecchie (rimozione BUSINESS_STATE richiede autorizzazione). Da decidere se compattarle.
- **Drift brief↔BUSINESS_STATE:** il brief diceva `cycle` intero, l'update BUSINESS_STATE diceva stringa. Ho usato la **stringa** (`testnet_1`/`testnet_2`), più narrativa.
- **Audit Area 2:** il backstop è stato portato 120→60gg (modifiche di Max a AUDIT_PROTOCOL/CLAUDE.md, commit `5520625`).
