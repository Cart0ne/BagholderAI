# Brief 62a — Grid Bot Refactoring Phase 1: Split del Monolite

**From:** CEO (Claude, Projects) → CC (Intern)
**Via:** Max (Board)
**Date:** 2026-05-07
**Session:** 62
**Priority:** ALTA — prerequisito per fix 60c, dust management, e go/no-go LIVE €100
**Stima:** ~6-8h (1 sessione CC piena)
**Predecessori:** 60c diagnosi finale (double-call), 60d shipped (commits 21caff0+0750027)

---

## 1. Contesto

`grid_bot.py` è cresciuto a 2000+ righe. Ogni sessione da due mesi troviamo un bug nuovo, e ogni fix è una toppa su un monolite che nessuno capisce più al primo colpo. Il 60c ha richiesto 4 ipotesi per trovare la root cause perché il flusso è intrecciato: un pop in un punto produce un audit fantasma in un altro, un double-call nel main loop corrompe state in-memory perché le side-effect avvengono prima del commit DB.

Non possiamo andare live con €100 su questa base. Serve un refactoring strutturato a fasi:

- **Fase 1 (questo brief):** split in moduli, zero cambi di logica
- **Fase 2 (brief separato):** fix 60c + dust management dentro i moduli nuovi
- **Fase 3:** 7 giorni clean run → go/no-go

---

## 2. Obiettivo

Estrarre da `grid_bot.py` moduli logici separati **senza cambiare nessun comportamento**. Dopo questo brief, il bot deve produrre esattamente gli stessi trade, gli stessi log, gli stessi audit, gli stessi eventi DB di prima. Se qualcosa cambia, il refactoring è sbagliato.

---

## 3. Moduli proposti

Proposta di suddivisione — CC può adattare se trova confini migliori, ma deve documentare le scelte nel commit message.

### 3.1 `fifo_queue.py`
- Classe `FIFOQueue` che wrappa `_pct_open_positions`
- Metodi: `add_lot(amount, price)`, `pop_oldest()`, `peek()`, `consume_sell(amount)` (il walk multi-lot FIFO), `to_list()`, `from_trades(trades_list)` (replay da DB)
- `verify_fifo_queue()` si sposta qui
- Nessuna dipendenza da `GridBot` — riceve/restituisce dati puri

### 3.2 `sell_pipeline.py`
- `_execute_percentage_sell()` → diventa funzione o classe qui
- `_build_sell_audit()` (la parte che scrive `sell_fifo_detail`)
- Logica di selezione lotti (Strategy A reorder + trigger check)
- Il loop `for _ in lots_to_sell` si sposta qui

### 3.3 `buy_pipeline.py`
- `_execute_percentage_buy()` → si sposta qui
- Logica first-buy, idle re-entry, multi-lot entry
- Cash guard checks

### 3.4 `dust_handler.py`
- Tutta la logica dust: identificazione lot sotto MIN_NOTIONAL/step_size, pop + log
- Per ora è un extract puro del codice esistente (col bug). Il fix arriva in Fase 2

### 3.5 `state_manager.py`
- `init_percentage_state_from_db()` → si sposta qui
- Self-heal logic (holdings>0 ma queue vuota)
- `restore_state_from_db()`
- State accounting: `total_invested`, `total_received`, `realized_pnl` tracking

### 3.6 `grid_bot.py` (residuo)
- Resta il "coordinatore": main loop, config reader, Telegram notifier wiring
- Chiama i moduli sopra invece di fare tutto inline
- `_check_percentage_and_execute()` resta qui ma diventa un dispatcher

---

## 4. Regole vincolanti

1. **ZERO cambi di comportamento.** Nessun fix, nessuna ottimizzazione, nessun "già che ci sono". Se vedi un bug durante lo split, documentalo in un commento `# TODO 62a: [descrizione bug]` e vai avanti.

2. **Nessun cambio di API DB.** Le stesse query, gli stessi INSERT, gli stessi campi. Se un import cambia path, ok. Se una query cambia logica, no.

3. **Nessun cambio di log format.** Le righe di log devono essere identiche — il Board usa grep sul log per validare.

4. **Test di equivalenza obbligatorio.** Dopo il deploy, le seguenti query SQL devono dare risultati identici alla baseline (numeri sotto). Se anche un centesimo cambia, il refactoring ha introdotto un bug.

---

## 5. Baseline pre-refactoring (snapshot 2026-05-07)

### Trades totali Grid manual (v3)

| Symbol | Side | Count | Total Cost | Sum Realized PnL |
|---|---|---|---|---|
| BONK/USDT | buy | 126 | $2,988.17 | — |
| BONK/USDT | sell | 127 | $2,993.07 | $44.24 |
| BTC/USDT | buy | 49 | $2,375.20 | — |
| BTC/USDT | sell | 48 | $2,257.39 | $31.93 |
| SOL/USDT | buy | 52 | $964.44 | — |
| SOL/USDT | sell | 50 | $953.40 | $16.49 |

### Lotti aperti stimati (buy - sell count)

| Symbol | Open lots estimate |
|---|---|
| BONK/USDT | -1 (last-lot sell-all) |
| BTC/USDT | 1 |
| SOL/USDT | 2 |

### FIFO drift events (ultimi 7 giorni)

| Symbol | Drift count | Last seen |
|---|---|---|
| BONK/USDT | 21 | 2026-05-06 21:38 |
| BTC/USDT | 12 | 2026-05-06 20:02 |
| SOL/USDT | 37 | 2026-05-07 07:33 |

**Post-deploy Fase 1:** i trade count e realized_pnl devono continuare a crescere coerentemente. Se il drift count esplode dopo il deploy → regressione.

---

## 6. Pacchetto Review per validazione esterna

**IMPORTANTE — questo è un requisito del Board, non opzionale.**

Dopo il commit, CC prepara un pacchetto nella cartella `/review/phase1/` del repo:

```
/review/phase1/
├── README.md           # Contesto minimo (vedi sotto)
├── before/
│   └── grid_bot.py     # Copia esatta del file PRE-refactoring
└── after/
    ├── grid_bot.py     # File residuo post-split
    ├── fifo_queue.py
    ├── sell_pipeline.py
    ├── buy_pipeline.py
    ├── dust_handler.py
    └── state_manager.py
```

### README.md del pacchetto review

```markdown
# Grid Bot Refactoring — Phase 1 Review Package

## What this is
Refactoring of a monolithic trading bot (grid_bot.py, 2000+ lines) into 
logical modules. ZERO behavior change intended — pure code reorganization.

## Architecture
- Grid bot for crypto trading (BTC, SOL, BONK on Binance)
- FIFO queue for position management
- Talks to Supabase (Postgres) for trade logging and config
- Paper trading now, live trading imminent

## What to check
1. **Behavioral equivalence**: does the new code do exactly the same thing 
   as the old code? Any logic change = bug.
2. **State management**: is in-memory state (holdings, realized_pnl, 
   open_positions queue) handled identically?
3. **Race conditions**: any new timing issues from the split?
4. **Edge cases**: dust lots, self-heal, last-lot sell-all, empty queue
5. **Import/dependency**: are all cross-module calls wired correctly?

## Known bugs (intentionally NOT fixed in Phase 1)
- Double-call to _execute_percentage_sell (60c)
- Dust pop writes audit but no trade (phantom audit)
- verify_fifo_queue dust filter mismatch (spurious drift)
These are marked with TODO comments and will be fixed in Phase 2.

## How to validate
Compare before/grid_bot.py against after/* — every line of logic in 
the original must exist somewhere in the new modules, unchanged.
```

---

## 7. Deploy e verifica

1. Push diretto a main
2. `git pull` su Mac Mini
3. **NON riavviare il bot subito.** Prima: `python -c "from bot.strategies.grid_bot import GridBot; print('import OK')"` per verificare che gli import funzionino
4. Riavviare orchestrator
5. Monitorare per 2h: trade normali, niente crash, niente drift spike
6. Dopo 48h senza anomalie → Fase 1 validata, si parte con Fase 2

---

## 8. Cosa NON fare

- NON fixare il bug 60c (double-call). Solo `# TODO 62a`
- NON fixare il dust management. Solo `# TODO 62a`
- NON aggiungere test unitari (Fase 2)
- NON cambiare nomi di funzione pubbliche che grid_runner.py chiama
- NON toccare grid_runner.py, orchestrator, o qualsiasi file fuori da `bot/strategies/`
- NON rinominare `GridBot` class

---

## 9. Rollback

```bash
git revert <commit>
git push origin main
# Mac Mini:
cd /Volumes/Archivio/bagholderai && git pull
# restart orchestrator
```

---

## 10. Timeline aggiornata

| Fase | Stima | Target |
|---|---|---|
| Fase 1 — Split (questo brief) | ~6-8h CC | 8-9 maggio |
| Review esterna (Board + Sonnet) | ~1-2 giorni | 9-10 maggio |
| Fase 2 — Fix 60c + dust | ~6-8h CC | 11-12 maggio |
| Review esterna Fase 2 | ~1 giorno | 12-13 maggio |
| Clean run 7 giorni | 7 giorni | 13-20 maggio |
| Go/no-go LIVE €100 | — | ~20 maggio |

Slittamento di ~8 giorni rispetto al target originale del 12 maggio. Il Board lo ha approvato.

---

Buon lavoro. Questo è il brief più importante del progetto — se lo split è pulito, tutto il resto diventa più facile.

— CEO, BagHolderAI
