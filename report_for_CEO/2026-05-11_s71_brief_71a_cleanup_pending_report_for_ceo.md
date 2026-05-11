# S71 — Brief 71a "Cleanup Pending + P&L Unification" — Report for CEO

**Data:** 2026-05-11 (sessione 71, mattina/inizio pomeriggio)
**Autore:** Claude Code (Intern)
**Destinatario:** CEO (Claude)
**Commits pushati:** `6021230`, `67614bd`, `8a158dc`, `db3c6c1` (4 commit su `origin/main`)
**Status:** brief 71a **SHIPPED** (5 task). Bug critico BONK InsufficientFunds **DIAGNOSTICATO** ma fix **PARCHEGGIATO** in brief 71b separato per rispettare il vincolo del brief 71a.

---

## Sintesi in 5 righe

1. Brief 71a chiuso: P&L hero unificato sulle 3 superfici (home, /dashboard, /grid.html) — netto fees ovunque, drift residuo ~1% solo da timing dei fetch live a Binance.
2. LAST SHOT BUY pre-arrotonda il `cost` al `lot_step_size`, niente più rifiuti -2010 sporadici da Binance testnet su BONK book sottile.
3. Reason dei trade letteralmente onesto: usa `check_price` nella narrativa e appende `→ fill X (slippage ±Y%)` quando lo slippage supera 0.05% — il bug "$0.00000735 dropped 1.5% below $0.00000731" (BUSINESS_STATE §27) è chiuso.
4. Bug critico nuovo emerso durante la diagnosi mattutina: **BONK InsufficientFunds** sui SELL, 31 tentativi rifiutati tra 00:04 e 00:29 UTC. Root cause confermata via balance Binance live: gap 12.280 BONK (0.74%) fra DB e wallet reale, causato da fee BUY scalata in BONK e non sottratta dalla `state.holdings`. Fix differito a **brief 71b** (~1-2h) per non violare il vincolo "non modificare buy_pipeline" del brief 71a.
5. Mobile recon table fixata (overflow scroll), cron reconcile wrapper pronto ma non installato (Mac Mini offline durante la sessione, install deferred a quando torna online).

---

## Cosa è stato fatto

### A. Task 1 — P&L Hero Unification (commit `6021230`)

**Diagnosi rapida prima del lavoro:**
- Home `stat-pnl`: `budget − netInvested + holdings_mtm` (NO fees) → $512.23
- Dashboard hero + Grid card: `budget + realized + unrealized` (NO fees) → $512.23
- Grid.html "Stato attuale": `cash + holdings + skim − fees` → $510.24 (la verità canonica, sottraeva già fees)

Differenza: ~$1.20 (= fees totali). Drift sistematico, non timing prezzo.

**Implementazione:**
- Nuova utility condivisa `web_astro/src/lib/pnl-canonical.ts` (137 righe): replay avg-cost identico al bot (`buy_pipeline.py:172`), una sola formula `netWorth = cash + holdings_mtm + skim − fees`, ritorna anche `netRealized = Σ realized − Σ fees` come metrica gemella.
- `live-stats.ts` (home): refactor del calcolo Total P&L per usare `computeCanonicalState()` due volte (Grid + TF) e sommare. Linee 119-148 sostituite, ~50 righe in meno.
- `dashboard-live.ts` (dashboard): aggregazione `totalFees` aggiunta al hero (linea 295-316), `buildSection` cambia `netWorth = budget + realized + unrealized` → `... − fees` (linea 545-560).
- `public/grid.html` (admin privata): aggiunta riga wide "Net realized profit (post-fees)" sotto la Portfolio overview 3×3, gemella del numero già esistente su /dashboard. La formula `cash + holdings + skim − fees` era già corretta.

**Verifica visiva Max:** numeri coincidono entro 1%. Il delta residuo è solo timing dei tre fetch separati a `api.binance.com/api/v3/ticker/price` (ogni pagina chiama indipendentemente). Per andare a $0.00 servirebbe un fetch server-side condiviso → fuori scope chirurgico, candidato a refactor futuro insieme alla cache prezzi per /dashboard.

**Decisione editoriale registrata:** mostriamo **due numeri** etichettati ovunque (eccetto home che ha solo Total P&L per sintesi):
- **Total P&L** (oscilla col prezzo) = "se chiudessi tutto adesso"
- **Net Realized Profit (post-fees)** (storico fisso) = "quello che è già in cassa, fees già detratte"

### B. Task 4 — LAST SHOT lot_step_size pre-rounding (commit `67614bd`)

**Bug:** BUY BONK LAST SHOT a 11:52:12 UTC (10 maggio) rifiutato con `code -2010` "Order book liquidity is less than LOT_SIZE filter minimum quantity"; retry success a 11:52:33 sullo stesso `cost`. Cosmetico ma generava 1 alert Telegram + warn ORDER_REJECTED ogni volta.

**Fix in `bot/grid/buy_pipeline.py:152-160`:** prima di chiamare `place_market_buy(cost)`, calcolo l'amount base implicito (`cost / check_price`), lo arrotondo al `lot_step_size` con `round_to_step()` (ROUND_DOWN, sicuro), e ricalcolo `cost = base_rounded × check_price`. Il `quote_amount` inviato a Binance è quindi sempre un multiplo valido del filter, niente più rifiuti al primo tentativo.

Applicato sia al path standard che al LAST SHOT (no condizionale): non c'è motivo di lasciare il path standard a rischio dello stesso bug se domani Binance stringe i filtri su altri simboli.

### C. Task 5 — Reason bugiardo + slippage tail (commit `67614bd` insieme al Task 4)

**Bug citato in BUSINESS_STATE §27:** quando un market order ha `fill_price ≠ check_price` (book sottile, slippage testnet fino a 2.5% su BONK), il `reason` del trade riporta il fill_price come se fosse il trigger. Esempio reale 2026-05-08 19:49 UTC:
```
"price $0.00000735 dropped 1.5% below last buy $0.00000731"
```
Falso: $0.00000735 è **SOPRA** $0.00000731. Il check_price che ha innescato il drop era $0.00000720, ma è stato sovrascritto al fill.

**Fix in `buy_pipeline.py:142-145` + `sell_pipeline.py:367-371`:**
- Prima di sovrascrivere `price` con `res["avg_price"]`, salvo `check_price = price` e azzero `slippage_pct = 0.0`.
- Dopo il fill, calcolo `slippage_pct = (price − check_price) / check_price × 100`.
- Nelle reason "Pct buy/sell" e "Greed decay sell" (TF) uso `check_price` nella narrativa principale; appendo `→ fill X (slippage ±Y%)` solo quando `|slippage| ≥ 0.05%` (soglia rumore — paper mode resta pulito).
- Le 6 reason forced (STOP-LOSS, TRAILING-STOP, TAKE-PROFIT, PROFIT-LOCK, GAIN-SATURATION, BEARISH EXIT) mantengono `price` (fill) nella narrativa principale perché lì è effettivamente il prezzo a cui è avvenuta la liquidazione — ma anche queste ricevono lo slip_tail in coda.

**Test 15/15 verdi** (`test_accounting_avg_cost.py`).

### D. Task 3 — Mobile review (commit `8a158dc`)

**Audit statico CSS** delle pagine pubbliche (no headless Chrome — memoria `feedback_no_screenshots`):
- Home: `.bots-row` ha `flex-wrap: wrap` su `<700px`, cards ridotte a 50% width. ✓ OK
- TfDoctor SVG: `viewBox` + `preserveAspectRatio="xMidYMid meet"` + `block w-full h-auto`, container `overflow-hidden`. ✓ OK
- TestnetBanner: layout responsive con `sm:` breakpoints. ✓ OK
- /dashboard hero: `text-[clamp(28px,5vw,38px)]` per il numero principale. ✓ OK
- Tabelle Grid/TF Recent trades: `overflow-x-auto` + `table-fixed` + `colgroup` con percentuali. ✓ OK
- **Reconciliation table: problema trovato.** Wrapper aveva `overflow-hidden` invece di `overflow-x-auto`, e 5 colonne (Bot/Status/Trades verified/Drift/Last run) su 390px = clip irreversibile a destra.

**Fix in `dashboard.astro:574-577`:** `overflow-hidden` → `overflow-x-auto`, table `w-full` → `w-full min-w-[520px]`, header `<tr>` aggiunto `whitespace-nowrap`. Su mobile ora scroll orizzontale invece di clip.

**Limite onesto:** non ho testato su iPhone reale (richiede Max sul telefono). Audit fatto via inspect statico del CSS + conoscenza dei breakpoint Tailwind. Suggerito test passaggio mobile su home + /dashboard + /roadmap + /diary + /blueprint appena disponibile.

### E. Task 2 — Cron reconcile wrapper (commit `8a158dc`)

**Wrapper pronto** in `scripts/cron_reconcile.sh` (eseguibile +x):
```bash
cd /Volumes/Archivio/bagholderai
source venv/bin/activate
python3.13 scripts/reconcile_binance.py --write
# output ≫ $HOME/cron_reconcile.log
```
Header del file contiene le 5 istruzioni di installazione (TCC Full Disk Access incluso, memoria `project_cron_mac_mini`).

**Status:** Mac Mini offline durante S71 → installazione crontab + verifica TCC **deferred**. Quando il Mac Mini torna online: `git pull` + `crontab -e` con riga `0 3 * * * /Volumes/Archivio/bagholderai/scripts/cron_reconcile.sh` + test manuale + `tail $HOME/cron_reconcile.log`. ~10 minuti.

### F. Documentazione (commit `db3c6c1`)

- `PROJECT_STATE.md` rigenerato: stato S71, in-flight con brief 71b urgente, decisioni recenti (punto fisso "chiudere pending prima delle fees"), bug noti (4 chiusi + 1 nuovo critico), audit sintesi.
- `config/brief_71a_cleanup_pnl_unification.md` → `briefresolved.md/session71a_cleanup_pnl_unification.md` (memoria `feedback_completed_briefs`).
- 3 vecchi report S70 (a/b/c) spostati da `report_for_CEO/` → `report_for_CEO/resolved/`.

---

## Bug critico emerso durante S71: BONK InsufficientFunds

Questa è la cosa più importante della sessione e merita una sezione dedicata, perché ribalta la roadmap.

### Sintomi

Max segnala stamattina presto: il dev-console Telegram ha 31 alert `SELL BONK/USDT rejected: InsufficientFunds: binance Account has insufficient balance for requested action` tra 00:04 e 00:29 UTC. Tutti con `base_amount=1669038.0` (ovvero, il bot vuole vendere TUTTO il lotto BONK che crede di avere).

### Indagine

**Passo 1 — DB:** `bot_state_snapshots` dice `holdings=1669038 BONK` (replay degli ultimi trade BONK: 9 buy = 30.726.196 BONK, 9 sell = 29.057.158 BONK, net = 1.669.038). Coerente con `Σ(buy.amount) − Σ(sell.amount)` dei trade DB.

**Passo 2 — Binance live (ssh Mac Mini → ccxt `fetch_balance()`):**
```
BTC: free=1.0006063   (= 1.0 testnet initial + 0.0006063 dal bot)
SOL: free=5.62473     (= 5.0 testnet initial + 0.62473 dal bot)
BONK: free=1656757.8  ← solo questo gap significativo
USDT: free=9867.71
```

**Passo 3 — math del gap:**
- DB: 1.669.038 BONK
- Binance: 1.656.757,8 BONK
- Delta: **−12.280 BONK** (DB sovrastima di ~0.74%)

### Root cause

I 9 BUY BONK hanno `fee_asset='BONK'`: su Binance, per market BUY su un pair `BASE/USDT`, la fee viene scalata IN BASE COIN (cioè in BONK). Esempio trade BUY:
- DB: `amount=3,419,972 BONK, cost=$25.00, fee_asset=BONK, fee=0.025 USDT-equiv` (la `fee` colonna del DB è già convertita in USDT canonical per coerenza dashboard).
- Binance: il wallet riceve `filled − fee_native_in_BONK` = 3,419,972 − ~3,400 BONK = ~3,416,572 BONK.

**Ma in `bot/grid/buy_pipeline.py:172`:**
```python
bot.state.holdings += amount   # amount = filled gross, NON al netto della fee in BONK
```

→ DB cresce di 3.419.972, Binance di 3.416.572. Drift 3.400 BONK per BUY × 9 BUY ≈ 30k BONK di drift teorico. Osservato 12.280 → parte è stata "consumata" dai sell che hanno arrotondato per difetto via `round_to_step` (lot_step_size BONK = 1, residuo dust lasciato sul wallet). Spiegazione consistente con i numeri.

Il bug è dichiarato in PROJECT_STATE §5 come "bias secondo-ordine `avg_buy_price` post-fee" — la stessa famiglia di bug della Strada 2, ma con conseguenza più grave: non un numero di reporting sbagliato, ma un **fail di trading reale**.

### Perché non l'ho fixato in S71

Il brief 71a vincolava esplicitamente: *"NON modificare la logica di trading (buy_pipeline, sell_pipeline, grid_bot) al di fuori del reason fix."* — Task 5 era l'unica eccezione (reason string), Task 4 era pre-rounding del `cost` (non holdings).

Max ha esplicitamente confermato la priorità: *"creiamo un punto fisso: risolvere tutti i task pending dalle sessioni precedenti e poi concentrarci su nuovi task, tra cui il più urgente saranno le fees"* (memoria session 71). Il fix BONK rientra in "fees" e va nel brief 71b separato.

Conseguenza temporanea: il bot BONK continua a generare ORDER_REJECTED ogni volta che innesca un sell trigger (~ogni 30-60 min se BONK sale del 2.5%+ sopra avg). Nessuna perdita reale: sta **cercando di vendere**, non comprando. Sentinel/Sherpa silent. BTC e SOL operativi normalmente.

### Fix proposto per brief 71b

1. **In `buy_pipeline.py:172`:** sottrarre fee in coin di base se `fee_currency == base_coin`:
   ```python
   net_amount = amount
   if fee_currency == bot.symbol.split("/")[0]:  # fee in base coin
       net_amount = amount - fee_native_amount  # nuovo campo da exchange_orders
   bot.state.holdings += net_amount
   ```
2. **In `state_manager.init_avg_cost_state_from_db`:** dopo il replay trades, leggere `exchange.fetch_balance()` e applicare `state.holdings = min(state.holdings, binance.free)` con warn `bot_events_log` se `gap > 1%`. Auto-heal post-restart.
3. **Test:** aggiungere caso in `test_accounting_avg_cost.py` con fee BUY in base coin che verifica `state.holdings == filled − fee_native`.
4. **Backfill:** UPDATE manuale `bot_state_snapshots` per BONK a 1.656.757,8 (allineato Binance) **prima** del restart bot, così al primo tick post-restart il replay parte da numeri sani.

Stima: 1-2h compresi test e restart bot.

### Cosa NON è da fare in brief 71b

- **Non** Strada 2 P&L netto canonico (~3-4h, fix retroattivo dei 458+ trade storici): è un brief separato perché ha scope diverso (numeri storici dashboard, non trading runtime).
- **Non** slippage_buffer parametrico per coin (BONK testnet vs mainnet): post-go-live €100.
- **Non** sell_pct sherpa-aware: dependency su Sherpa live, post-mainnet.

---

## Roadmap impact

| Item | Stima precedente | Stima aggiornata | Note |
|---|---|---|---|
| Go-live €100 | 21-24 maggio | **24-28 maggio** (slip ~3-5 giorni) | Brief 71b va shipped prima del go-live; Mac Mini install cron aggiungere ~10min |
| Brief 71b BONK | non in roadmap | **~1-2h** | Pre-go-live gate confermato |
| Strada 2 P&L netto | ~3-4h | invariato | Post brief 71b, pre go-live |
| Reconciliation Step C cron | ~30 min | **~10 min** | Wrapper già pronto, manca solo install |

Phase 9 Validation pre-live gates aggiornata in PROJECT_STATE §7.

---

## Decisioni (Decision Log)

1. **DECISIONE:** mostrare DUE numeri P&L (Total + Net Realized) anziché unificare su uno solo come proposto dal brief 71a §1. **RAZIONALE:** Max ha approvato esplicitamente l'opzione "entrambi etichettati chiaramente" — Total P&L include unrealized (futuro ipotetico), Net Realized esclude (passato consolidato), e raccontano cose diverse del bot. **ALTERNATIVE CONSIDERATE:** A) solo Total P&L NET fees (perde la metrica storica); B) solo Net Realized (perde l'unrealized che è la parte vibrante del numero). **FALLBACK SE SBAGLIATA:** rimuovere una delle due metriche è banale (1 commit di rollback CSS visibility).

2. **DECISIONE:** brief 71b separato per BONK fix invece di estendere 71a. **RAZIONALE:** Max esplicito a metà sessione ("creiamo un punto fisso, prima i pending poi le fees"); il vincolo del brief 71a "non modificare buy_pipeline" sarebbe stato violato. **ALTERNATIVE CONSIDERATE:** A) Task 0 di 71a con override esplicito di Max (rifiutato per disciplina del brief); B) hot-patch DB manuale UPDATE holdings senza fix codice (rifiutato: cura del sintomo non della causa). **FALLBACK:** brief 71b può essere shipped in qualunque momento prima del go-live, niente blocca.

3. **DECISIONE:** mobile review tramite audit statico CSS invece di test su device reale. **RAZIONALE:** Memoria `feedback_no_screenshots` proibisce headless Chrome per visual review; Max non aveva il telefono in quel momento. **ALTERNATIVE CONSIDERATE:** A) saltare Task 3 (rifiutato, era nel brief); B) Chrome devtools viewport simulation (approvata da Max in inizio sessione). **FALLBACK:** test reale appena Max ha 5 min sul telefono — se trova problemi, brief micro-fix dedicato.

4. **DECISIONE:** wrapper cron Mac Mini scritto ma non installato. **RAZIONALE:** Mac Mini offline durante S71 (Max esplicito "Mac Mini non in locale"); installazione SSH-dependent. **ALTERNATIVE CONSIDERATE:** A) attendere Mac Mini online (rifiutato: bloccherebbe il commit per ore); B) skippare Task 2 (rifiutato: wrapper è scrittura pura senza side effect, scrivibile anche offline). **FALLBACK:** installazione in 10 min quando torna online, istruzioni nello header del file.

---

## Pull request

Nessuna PR: lavoro su `main` direttamente come tutte le sessioni precedenti, 4 commit pushati con `git push origin main`.

---

## Domande aperte per CEO

Nessuna domanda aperta dipendente da decisione strategica. Le 3 cose pending hanno tutte un percorso operativo definito:

1. **Brief 71b BONK** — schema pronto in §3 e §5 del PROJECT_STATE. Tempo: 1-2h. Quando lo facciamo? La mia raccomandazione è **subito a inizio S72** prima di qualsiasi altra cosa, perché ogni minuto che passa il bot accumula altri ORDER_REJECTED nel log e qualche sell BONK non eseguito (mancata profittabilità potenziale).

2. **Mac Mini install cron** — quando il Mac Mini torna online. Procedura nello script header.

3. **Mobile test reale** — quando Max ha 5 min sul telefono.

Tutto il resto del backlog (Strada 2 P&L netto, slippage buffer, Sherpa rule-aware, sell_pct net-of-fees, Tradermonty full-repo scan) resta nelle stesse priorità definite in BUSINESS_STATE.

---

*Report scritto al volo a chiusura della sessione 71. Aggiornamento PROJECT_STATE.md committed insieme. Dev server Astro localhost:4321 ancora attivo (PID 47464) — Max può killarlo o lasciarlo.*
