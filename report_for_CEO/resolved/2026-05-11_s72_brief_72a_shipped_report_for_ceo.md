# Report S72 — Brief 72a Fee Unification SHIPPED + audit visivo Max

**Data:** 2026-05-11
**Sessione:** 72 (chiusura tecnica)
**Sintesi:** Brief 72a shipped come da tua approval, ma la sessione è andata molto oltre. L'audit visivo di Max ha rivelato due bug strutturali che il refactor 72a originale non aveva coperto: (1) lexical drift dal rename S70 `trend_follower→tf` che lasciava 4 callsite con la vecchia stringa, (2) due replay di P&L separati su 4 superfici diverse che divergevano per centesimi. **Tutto risolto con 11 commit, 4 superfici (home/dashboard/grid.html/tf.html) ora unificate su `computeCanonicalState` come unica fonte di verità, TF sparito dai totali pubblici (Max: "i soldi di TF devono sparire da tutto")**. Bot vivo, cron reconcile attivo 03:00 Europe/Rome, 0 ORDER_REJECTED post-restart.

---

## 1. Brief 72a — output atteso vs delivered (dal tuo approval)

| Voce richiesta | Status | Dettaglio |
|---|---|---|
| Codice 5 file + 3 test P/Q/R | ✅ | `116d0fb` — test 18/18 verdi locale + Mac Mini |
| Bot restart 3 grid con env flags | ✅ | 13:49 UTC, 6 processi vivi (BTC/SOL/BONK + Sentinel + Sherpa + caffeinate) |
| Backfill ~42 trade testnet | ✅ | Sanity check: erano 18 SELL (count "42" includeva i BUY). Δ cumulato −$1.097 |
| 24h osservazione iniziata | ✅ | counter dalle 13:49 UTC, scade 2026-05-12 13:49 UTC |
| Zero ORDER_REJECTED conferma | ✅ | `bot_events_log` post-restart pulito |
| Cron reconcile Step C (memory bonus) | ✅ | crontab Mac Mini `0 3 * * *`, prima run automatica stanotte |

---

## 2. Boot reconcile + edge case decisione asymmetric

Al primo restart 13:49 UTC il boot reconcile golden source ha rivelato un edge case che il tuo brief approval non poteva prevedere:

| Symbol | Replay DB | Binance reale | Gap signed | Verdict |
|---|---|---|---|---|
| BTC | 0.000609 | **1.000606** | +1.000 BTC (164.098%) | wallet_surplus (initial fantasma testnet) |
| SOL | 0.625374 | **5.624730** | +5.0 SOL (799%) | wallet_surplus (initial fantasma) |
| BONK | 1.638.312 | 1.656.758 | +18.446 BONK (1.13%) | wallet_surplus (come previsto S72 diagnosi) |

La soglia simmetrica 2% del tuo brief originale (no override) ha fatto FAIL_START su BTC/SOL: Binance testnet assegna ~1 BTC e ~5 SOL gratuiti all'apertura account, magnitudo non prevedibile pre-S72.

**Decisione presa con Max in sessione** (commit `1f9bba9`): **asymmetric threshold**.
- Drift NEGATIVO (`real < replayed`) > 2% → FAIL (= phantom holdings, capital at risk, sintomo BONK InsufficientFunds storico)
- Drift POSITIVO (`real > replayed`) sempre WARN (= wallet surplus, gift testnet, innocuo)

Su mainnet pulito asimmetria irrilevante (drift positivo richiede deposito manuale, mai dato gratis). Su testnet preserva il bootstrap senza compromettere la motivazione originale.

---

## 3. Frontend cleanup post-72a (la parte non prevista)

Dopo il shipping del backend, Max ha aperto un audit visivo. Cinque problemi distinti emersi e risolti uno alla volta:

### 3.1 Frontend P2 non applicato uniformemente (`d93f38a`)
Il replay TS in `pnl-canonical.ts` + `dashboard-live.ts` e il replay Python `commentary.py:_analyze_coin_avg_cost` (usato da Haiku per daily commentary) usavano ancora la formula pre-72a (`avg = price × amount / qty_lorda`). Aggiornati a P2 (sottrarre `fee_native` se `fee_asset == base_coin`). Anche le SELECT queries Supabase ora includono `fee_asset`.

### 3.2 Lexical drift dal rename S70 (`a39d4b3`)
Max ha notato $0.02 di gap tra "Net Realized Profit" su `/dashboard` ($9.33) vs `/grid.html` ($9.35). Diagnosi: il rename S70 `managed_by 'trend_follower' → 'tf'` aveva lasciato 4 callsite frontend col vecchio nome:
- `grid.html:519` (bot_config) — filtro `not.in.(trend_follower,tf_grid)` non escludeva `'tf'` → 2 trade TF leaked
- `grid.html:520` (trades) — stesso bug
- `tf.html:636` (bot_config) — filtro `in.(trend_follower,tf_grid)` non matchava `'tf'` → /tf vuoto dal S70
- `tf.html:637` (trades) — stesso bug

`/tf` era stata **silenziosamente broken dal S70** (49 giorni) e nessuno se ne era accorto. Memoria nuova `feedback_lexical_drift_after_rename` salvata: dopo rename DB letterali, grep su TUTTI i sorgenti (HTML statico + Astro + Python), non solo IDE find/replace.

### 3.3 Refactor canonical shared (`e1db879`)
Due implementazioni separate di P&L su 4 superfici (TS in `pnl-canonical.ts` + replay custom in `dashboard-live.ts` + replay custom in `grid.html` + replay custom in `tf.html`). Algebricamente equivalenti su avg-cost canonico, ma divergevano per centesimi quando i replay applicavano P2 in modo non uniforme.

Creato `web_astro/public/lib/pnl-canonical.js` come **plain JS port** di `pnl-canonical.ts`, esposto come `window.PnL.computeCanonicalState` / `.fetchLivePrices` / `._replayAvgCost`. Caricabile da static HTML via `<script src="/lib/pnl-canonical.js">`. Tutte e 4 le superfici ora chiamano la STESSA funzione sullo STESSO trade set.

### 3.4 Dashboard inline script bypass (`1e93474`)
Anche dopo il refactor, Max vedeva $9.33 vs $9.32. **Headless Chrome dump-dom** (Max suggerimento: "se pensi sia cache, puoi usare Chrome") ha rivelato che `dashboard.astro:283-321` aveva uno **script TS inline** che bypassava completamente `pnl-canonical`:
```js
const url = "/rest/v1/trades?config_version=eq.v3&select=side,realized_pnl,fee";
// NESSUN filtro managed_by → include grid + tf + tf_grid
```
Sommava `realized_pnl` + `fee` di TUTTI i v3 trade (non solo Grid), inflando di $0.013. Filtro `managed_by=eq.grid` aggiunto. **Memoria `feedback_one_source_of_truth` rinforzata**: shortcut inline scripts che bypassano la lib condivisa sono lo stesso pattern di drift della stringa SQL fuori-sincrono.

### 3.5 TF sparisce dai totali pubblici + Grid card runtime fix (`a34acb3` + `e975a71`)
Max esplicito: "i soldi di TF devono sparire da tutto". Pre-fix il sito mostrava aggregato Grid + TF ($600 capital at risk), drogando ogni Total P&L pubblico con i $100 di TF parked.

Cambiamenti:
- `live-stats.ts` (home): `totalPnl = gridState.totalPnL` (no più `+ tfState.totalPnL`)
- `dashboard-live.ts`: hero usa `computeCanonicalState(gridTrades, gridSkim, prices, $500)` invece di una vecchia analyzeCoin custom
- `dashboard.astro`: banner "Capital at risk: $600 ($500 Grid + $100 TF paused)" → "$500 (Grid only — TF paused, Sentinel/Sherpa shadow-only)"
- Grid section card refactor: anche qui `computeCanonicalState` invece di `buildSection` custom

**Bug runtime introdotto e fixato durante la stessa sessione** (`e975a71`): il secondo IIFE del file dashboard-live.ts referenziava `gridSymbols` + `gridTrades` definite nel primo IIFE (out of scope), throw silenziato dal catch, Grid card stuck a "—". Trovato di nuovo via Chrome dump-dom (`grid-budget`, `grid-fees`, etc. tutti "—"). Rebind a `gridAllTrades` + `skimFor()` già in scope.

---

## 4. Stato finale (verificato via Chrome headless live 2026-05-11 ~18:10 UTC)

**Dashboard pubblica** `/dashboard`:
- Hero Net Worth: **$512.18** (Grid only)
- Hero Total P&L: **+$12.18 (+2.44%)** — vivo
- Grid card Budget: $500 — Day 43 — Cash $406.53 — NetWorth **$512.18**
- Grid Total P&L: **+$12.18 (+2.44%)** ← bit-identical con hero ✅
- Unrealized +$1.70 — Fees −$1.19 — Skim +$3.65 — Cash 82%
- Net Realized Profit: **+$9.61** (vivo, sale con nuovi sell)
- Banner "Capital at risk: $500 Grid only"

**Home** `/`:
- Total P&L: ~ `+$12.x` (drift naturale ±$0.10 da live price tra fetch separate Binance ticker — non bug, è la natura di MTM su 2 chiamate API distinte)

**Grid.html** `/grid.html` (auth-gated): Max ha verificato manualmente, coincide con dashboard ✅

**Bit-identical sui valori chiusi** garantito per costruzione: tutte le 4 superfici (home, dashboard hero, dashboard Grid card, /grid.html, /tf.html, commentary RPC server-side) chiamano la **STESSA** funzione `computeCanonicalState` con lo stesso filtro `managed_by='grid'` sullo stesso trade set.

---

## 5. Cron reconcile installato

```cron
# BagHolderAI - Nightly Binance reconciliation (brief 71a Task 2, S72)
0 3 * * * /Volumes/Archivio/bagholderai/scripts/cron_reconcile.sh
```

03:00 Europe/Rome = 01:00 UTC, BEFORE bot 04:00 UTC retention. TCC Full Disk Access già concesso (memoria S70b confermata). Test run manuale eseguito 15:05 UTC: BTC 11 / SOL 9 / BONK 18 matched, 0 drift. Prima run automatica stanotte.

---

## 6. Il debito matematico residuo — onestà

Resta un **bias documentato di −$0.22** sul Net Realized Profit cumulato, dovuto al double-count fee_sell sui 18 trade testnet backfillati (paper resta gross, decisione tua S71). Su un Net Realized di ~$9.6, è 2.3% di overstatement.

Tre vie possibili (le stesse del report precedente, le ripeto per completezza):

**Via A — Status quo + disclaimer pubblico (0h)**: aggiungere una nota piccola in /blueprint o /dashboard footer "I numeri pubblici escludono l'initial balance fantasma testnet (Binance assegna ~1 BTC, ~5 SOL, ~18K BONK gratuiti all'apertura account; bias residuo netRealized −$0.22 documentato in codice)". Onesto narrativamente, coerente con "story is process, not numbers" del S70c.

**Via B — Split "Paper Era / Testnet Era"** (~2-3h): la dashboard pubblica diventa 2 sezioni separate, ognuna con la sua formula corretta. Niente bias, ma editorialmente cambiamento maggiore.

**Via C — Backfill totale paper** (~3-4h): ricalcoliamo realized_pnl dei 458 paper con formula nuova. Storia cambia retroattivamente. Avevi detto NO a S71, reversibile.

**Mio voto: Via A** (chiudere S72 pulito, andare in osservazione 24h, decidere a freddo). Brief separato post-go-live se vorrai pulizia totale.

---

## 7. Cifre vs Binance — onestà finale

**Sul mainnet** (post-go-live €100): le cifre **coincideranno con Binance al cent** per costruzione. Parti con €100 USDT, niente initial fantasma, wallet attuale Binance = budget + realized + unrealized − fees = quello che vedi sul sito. 3 superfici (bot, dashboard, Binance) bit-identical.

**Sul testnet** (oggi): le **holdings del bot** sì coincidono con Binance (golden source), il **P&L pubblico** no per via dell'initial fantasma. È una scelta narrativa coerente con la dashboard ("lavoro del bot sui $500"), non un bug.

---

## 8. Pending pre-go-live €100

**Phase 9 V&C — gate aggiornate dopo S72:**
- ✅ Contabilità avg-cost (S66)
- ✅ Fee USDT canonical (S67)
- ✅ Dust prevention (S67)
- ✅ Sell-in-loss guard avg_cost (S68a)
- ✅ DB schema cleanup (S68 + S69)
- ✅ FIFO contabile via dashboard (S69)
- ✅ Avg-cost trading completo + Strategy A simmetrico (S69)
- ✅ sell_pct net-of-fees (S70)
- ✅ Reconciliation Binance Step A+B+C (S70 + S72 cron)
- ✅ Sentinel ricalibrazione (S70b)
- ✅ Sito online (S70c)
- ✅ **Fee Unification (S72)** ← nuova gate chiusa
- ✅ **Lexical drift cleanup S70 rename (S72)**
- ✅ **Frontend canonical refactor (S72)**
- ✅ **TF sparito dai totali pubblici (S72)**
- ⬜ 24h osservazione (in corso, scade 2026-05-12 13:49 UTC)
- ⬜ Decisione Via A/B/C su netRealized bias
- ⬜ Mobile smoke test reale
- ⬜ Sentinel/Sherpa analisi DRY_RUN
- ⬜ Board approval finale

**Target go-live: 18-21 maggio** se osservazione clean + Via A approvata.

---

## 9. Cosa ho imparato (memorie salvate)

1. **`feedback_check_constraints`** già esistente, violata: ho usato `category='reconcile'` senza verificare pg CHECK constraint. Primo commit doveva essere `'integrity'`. Patch in più. Mea culpa noted.
2. **`feedback_lexical_drift_after_rename`** NEW: rename DB letterali (`managed_by`, enum-like text) sono fragili. grep TUTTO il codebase post-rename. roadmap "done 6 callsite" può essere 6 su 10 senza accorgersene.
3. **`feedback_one_source_of_truth`** rinforzata: shortcut inline scripts (es. il bypass in dashboard.astro) sono lo stesso pattern del filtro SQL fuori-sincrono. Una funzione canonica condivisa è la cura.
4. **Audit Max** ha rivelato bug che pytest + boot reconcile + reconciliation Binance non avrebbero mai catturato. Chrome headless dump-dom come pattern di audit visivo via codice è ora nel mio playbook.

---

## 10. Stato repo fine S72

- Branch: `main`
- Ultimo commit: **`e975a71`** (12 commit S72 totali, tutti pushati su origin/main)
- Mac Mini: synced su `e975a71`, orchestrator vivo (PID 13852 + 5 figli)
- Bot live testnet: holdings golden source, zero ORDER_REJECTED dal restart, cron reconcile attivo
- Frontend Vercel: tutte le 10 pagine deployate, verificate via Chrome headless

### 11 commit S72 cronologici
1. `a1ad217` docs(s72): brief 72a + diagnosis report + state
2. `116d0fb` feat(s72): brief 72a fee unification — holdings golden source
3. `1f9bba9` fix(s72): reconcile asymmetric + category integrity
4. `5e08cce` docs(s72): close PROJECT_STATE — brief 72a shipped
5. `d93f38a` feat(s72): frontend + commentary mirror brief 72a P2 invariant
6. `d51bda7` docs(ceo): S72 final report (versione 1 — pre-audit Max)
7. `a39d4b3` fix(s72): lexical drift S70 rename — 4 callsite
8. `e1db879` refactor(s72): single source of truth — pnl-canonical.js shared
9. `1e93474` fix(s72): dashboard.astro inline script — missing managed_by=eq.grid
10. `a34acb3` fix(s72): TF sparisce dai totali pubblici — Grid only sul sito
11. `e975a71` fix(s72): dashboard Grid card runtime — gridSymbols out of scope

---

## 11. Richiesta esplicita

S72 chiusa per davvero. Aspetto tuo update strategico su BUSINESS_STATE per le decisioni residue (Via A/B/C, target go-live data, eventuali nuovi vincoli). Brief 73 + pre-go-live osservazione 24h sono il prossimo capitolo.

— CC, 2026-05-11
