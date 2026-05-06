# Session 55 — Unified Grid + TF Accounting (FIFO, dashboard-aligned)

**Data:** 2026-05-03 (notte)
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Commits:** `b9348a0` + `584ebe2` — pushed to `main`, deployati sul Mac Mini
**Brief origine:** brief notturno di Max — "Daily Report bugs (Grid skim + TF total fisso)"

---

## In una riga

Dashboard, report Telegram privato e report pubblico ora mostrano **gli stessi numeri al centesimo**, perché tutti e tre leggono dalla stessa funzione (`commentary.get_grid_state` / `get_tf_state`) che fa FIFO replay come la dashboard.

---

## Sintomo iniziale (cosa Max aveva visto)

Il report Telegram del 03/05 sera era incoerente con la dashboard:

| Voce Grid | Dashboard | Report | Δ |
|---|---:|---:|---:|
| Net Worth | $549.10 | $563.19 | +$14 |
| Cash | $205.25 | $239.96 | +$35 |
| Skim mostrato? | sì ($20.53 separato) | **sezione sparita** | — |
| P&L | +$49.10 | +$63.19 | +$14 |

E il TF total era **$89.74 identico in 2 giorni di fila** (02/05 e 03/05) nonostante prezzi e composizione diversi.

Il brief del CEO ipotizzava: skim contato due volte nel cash + bug del Binance prices URL.

---

## Cosa abbiamo scoperto investigando

L'ipotesi del CEO era **parzialmente corretta** ma il fix proposto era insufficiente. Dopo aver interrogato il DB live e confrontato 3 percorsi diversi di calcolo, abbiamo trovato il vero problema.

### Esistevano TRE formule diverse per "stessi numeri Grid"

1. **Bot orchestrator** (`bot/grid_runner._build_portfolio_summary`):
   `cash = $500 − bought + received`. Non sottrae lo skim, non considera FIFO.

2. **Script manuale** (`scripts/send_daily_reports_now.py`):
   `cash = budget − cash_used_in_holdings + total_realized`. Formula diversa, anche lei senza skim, basata su `realized_pnl` letto dal DB.

3. **Dashboard** (`web_astro/src/scripts/dashboard-live.ts`):
   `netWorth = budget + realized_FIFO + unrealized; cash = netWorth − holdings − skim`. **L'unica corretta.**

Le 3 formule davano 3 numeri diversi. Il record `daily_pnl` di stasera ($524) era diverso ancora dal report Telegram ($563), entrambi diversi dalla dashboard ($549).

### La causa profonda — `realized_pnl` biased nel DB

Il bot scriveva `trades.realized_pnl` usando `avg_buy_price` come cost basis invece del FIFO stretto. Su 458 SELL pre-53a (commit di fix 2026-05-01), questo bias accumulato vale:

- **Grid**: +$14.88 di realized fasullo (DB dice $69.21, FIFO vero $54.33)
- **TF**: +$3.82 di realized fasullo (DB dice −$6.45, FIFO vero −$10.27)

La dashboard si era già accorta del problema mesi fa e ricalcolava tutto client-side con FIFO. I percorsi backend invece leggevano la colonna biased.

---

## Cosa abbiamo deciso e applicato

Max ha richiamato il principio chiave:

> "Quando andremo live con soldi veri, anche se pochi, non possiamo avere queste discrepanze. Non posso aprire una dashboard pensando di aver guadagnato 40 e se vado su Binance ho guadagnato 5."

Da qui la scelta di **non patchare** i 3 percorsi separatamente, ma di **collassare tutti in uno**:

### Architettura risultante

```
┌─────────────────────────────────────────────────┐
│   commentary.py (single source of truth)        │
│                                                 │
│   _analyze_coin_fifo()  ← FIFO replay puro      │
│        ↑                                        │
│        ├── get_grid_state()                     │
│        └── get_tf_state()                       │
└─────────────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
   bot_orchestrator   send_daily   dashboard
   (20:00 daily)      _reports     (legge via
                      _now.py      scripts/
                      (manuale)    dashboard-live.ts)
```

### Cambiamenti per file

1. **`commentary.py`** (+200 righe nette)
   - Nuovo helper `_analyze_coin_fifo` — port Python esatto di `analyzeCoin` della dashboard.
   - `get_tf_state` riscritta: usa il FIFO helper invece di leggere `realized_pnl` dal DB. Formula identica alla dashboard: `netWorth = budget + realized + unrealized`.
   - `get_grid_state` nuova (gemella di `get_tf_state`, filtro `managed_by='manual'`, simboli BTC/SOL/BONK).

2. **`bot/grid_runner.py`** (−60 righe nette)
   - `_build_portfolio_summary` ora è un thin delegate a `get_grid_state`. Stessa firma, stessa shape di output, formula nuova. L'orchestrator e il render Telegram non hanno bisogno di sapere che la formula è cambiata.

3. **`scripts/send_daily_reports_now.py`** (−80 righe nette)
   - Cancellata tutta la logica di calcolo inline + il fetch ccxt dei prezzi. Una sola chiamata a `get_grid_state`. Ora è 30 righe invece di 110.

4. **`utils/telegram_notifier.py`** (+10 righe)
   - Sezione Grid ora mostra "Realized total · Skim · Fees" (gemella della sezione TF).
   - Sezione TF aggiunge "Fees" (era assente).
   - Sezione "🏦 Grid Reserve" legge `skim_by_sym` direttamente da `get_grid_state` (sempre presente, non dipende dal bundle esterno `reserves`).

---

## Verifica numerica (post-deploy)

Numeri del privato Telegram ricevuto stasera ~21:30 vs dashboard nello stesso minuto:

| Voce | Telegram | Dashboard | Δ |
|---|---:|---:|---|
| Grid Net Worth | $549.43 | $549.57 | $0.14 (movimento prezzi tra fetch) |
| Grid Cash | $205.25 | $205.25 | **identico** |
| Grid Holdings | $323.64 | $323.87 | $0.23 (prezzi) |
| Grid Realized | **+$54.33** | **+$54.33** | **identico al cent** |
| Grid Skim | $20.53 | $20.5336 | **identico** |
| Grid Fees | $7.64 | $7.64 | **identico** |
| TF Net Worth | $89.72 | $89.71 | $0.01 |
| TF Realized | **−$10.27** | **−$10.27** | **identico al cent** |
| TF Skim | $25.85 | $25.85 | **identico** |
| TF Fees | $6.46 | $6.46 | **identico** |
| TF Cash | $27.00 | $27.00 | **identico** |

**Tutti i numeri statici matchano al centesimo.** Le sole differenze sono $0.14–$0.23 sul Net Worth, dovute al fatto che la dashboard e il bot interrogano i prezzi live di Binance in momenti leggermente diversi.

---

## Inciampo intermedio (per onestà)

Il primo deploy stasera ha fatto fallire il report **privato** con "Message too long" (>4096 char Telegram). Causa: avevo fatto iterare `get_tf_state` su tutte le 44 coin storiche di `bot_config` invece delle 3 attive (DOGE/INJ/TRX). Il pubblico è invece passato perché il limite di Telegram non viene applicato uguale.

Fix di 4 righe in commit `584ebe2`: filtro `is_active=True` nel loop delle posizioni TF (il realized aggregato continua a includere le coin deallocate, così il match con la dashboard regge).

Secondo run: privato OK, pubblico OK, numeri allineati.

---

## Cosa NON abbiamo fatto (deliberatamente)

- **Non abbiamo riscritto i 458 `realized_pnl` storici nel DB.** Il bias resta lì come "fossile". Tutti i percorsi user-facing ora ignorano quella colonna per gli aggregati e ricalcolano FIFO. Una migrazione one-shot per riscrivere quei valori sarebbe pulita ma rischiosa (se sbaglia il FIFO durante il rewrite, perdiamo l'unica base buona). Decisione: lasciare la storia immutabile, fixare i percorsi.

- **Non abbiamo fatto restart dei bot in produzione.** Il fix è solo nel reporting, non nel trading. I bot continuano a girare con la logica corretta che già avevano (53a). Il prossimo report automatico delle 20:00 di domani userà il codice nuovo senza bisogno di intervento.

- **Non abbiamo toccato la dashboard.** Era e resta la sorgente di verità. Sono i percorsi backend che si sono allineati a lei.

---

## Memoria salvata

Aggiunto `feedback_one_source_of_truth.md` in memoria CC:

> I numeri visibili all'operatore (dashboard, report Telegram privato + pubblico) devono sempre corrispondere alla stessa formula canonica. In paper la verità è ricostruita da DB con FIFO; in live sarà la verità del broker (Binance). Una sola formula scritta una volta, esposta come funzione, chiamata da tutti i percorsi. NON fidarsi mai di `trades.realized_pnl` per aggregati storici (biased pre-53a). Quando andremo live: aggiungere un layer che riconcilia con `Binance.fetch_my_trades()` come ground truth e segnala drift.

---

## Diff statistico

```
 5 files changed, 333 insertions(+), 231 deletions(-)
 commentary.py                     | +257 / −86
 bot/grid_runner.py                |  +13 / −60
 scripts/send_daily_reports_now.py |  +28 / −86
 utils/telegram_notifier.py        |  +15 / −5
 (commit 584ebe2 hotfix TF active filter: +7 / −4)
```

Codice netto rimosso: **−98 righe**. Funzioni in più: 2 (`_analyze_coin_fifo`, `get_grid_state`). Sorgenti di verità per il P&L: da 3 → 1.

---

## Da fare nelle prossime sessioni (eredità)

1. **Verificare il report automatico delle 20:00 di domani 04/05** — deve dare gli stessi numeri di stasera al netto dei movimenti di giornata.

2. **Layer di riconciliazione live → Binance** (quando andremo a soldi veri): un job che fetcha gli ordini Binance reali via API e segnala se il P&L ricostruito da DB diverge da quello del broker oltre soglia. Da pianificare quando ci avviciniamo al go-live mainnet.

3. **Migrazione opzionale dei `realized_pnl` storici** — una tantum, in caso si voglia avere coerenza tra DB e dashboard a livello di colonna. Non urgente; nessun percorso oggi legge quella colonna per gli aggregati.

---

**Stato:** ✅ Deployato su `main` (commit `584ebe2`), tested via `send_daily_reports_now.py` da Mac Mini, numeri verificati contro dashboard. Pronto per la rotazione automatica delle 20:00 di domani.
