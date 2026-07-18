# Report for CEO — kraken-cutover (S118, Fase 1) — 2026-07-12

**Brief sorgente:** `config/2026-07-11_S117_brief_kraken-cutover.md` (SCOPE `kraken-cutover`), risequenziato in Fasi 0-4 (report S117b).
**Piano approvato:** `config/2026-07-11_S118_piano_kraken-fase1.md` (nodi 1-4 sciolti da Max in conversazione).
**Commit:** 8 commit `6a3c8ac..HEAD` (git log). Migration applicate a prod via MCP.
**Restart bot:** nessuno. **Nessun ordine reale.** I bot vivi sul Mini girano codice pre-S118 fino al prossimo restart (zero diff comunque su binance).
**Stato:** Fase 1 SHIPPED. Fase 2 (finestra coordinata + $100) attende Max.

---

## 1. Cosa è stata la Fase 1

I **pre-lavori a bot accesi** del cutover Kraken: tutto ciò che si può fare senza fermare nulla e senza rischiare un dollaro, così che la Fase 2 sia solo "accendi gli interruttori". Ogni pezzo è **gated su `bot_config.venue`**: con `venue='binance'` (tutte le righe di oggi) il comportamento è **byte-identico** a prima — invariante S112 rispettato, **290/290 test verdi** (271 preesistenti + 19 nuovi), verificato anche a mano sui 4 punti a rischio del diff.

## 2. Gli 8 pacchetti

| # | Pacchetto | Cosa fa | Gating |
|---|-----------|---------|--------|
| DB | `venue` + `site_flags` | colonna venue per-riga (default binance) + tabella toggle sito | migration reversibili |
| A | Cablaggio | il grid parla all'exchange tramite la factory `ExchangeClient` (S112); per binance delega verbatim al codice vecchio | `venue` |
| B | Fee dinamica | su Kraken la fee è letta **live** dal tuo tier (0,80% oggi, si adatta quando scende); binance resta 0,1% costante | per-venue |
| C | Floor fee-aware | il grid non vende sotto `avg × (1 + margine + 2×fee reale)`; trigger allineato (niente stallo) | `venue` |
| D | Fix contabile | la fee Kraken (in USD) entra nell'avg, esce dal cash, ed è specchiata nel replay al restart | `venue` |
| E | Hands-off | Sherpa salta le righe Kraken (altrimenti azzererebbe il floor); gate `ALLOW_REAL_MONEY` | `venue` |
| — | Bonifica sito | 7 superfici leggevano il ciclo col letterale `BTC/USDT` → ora "riga grid attiva"; zero diff oggi, Kraken-proof domani | robustezza |
| F | Disclaimer-toggle | overlay homepage per le finestre di collaudo, si accende con una UPDATE SQL (zero deploy) | SPENTO |

## 3. La prova che conta

`kraken_cutover_check.py` step 6 (nuovo): gli **stessi ordini validate=true** della Fase 0, ma questa volta **attraverso i metodi del client che il grid userà davvero live**, a taglie realistiche ($25). Eseguito sul Mac Mini (dove vivono le chiavi):

**28 check, 0 FAIL.** BUY/SELL/cost-order validati su BTC/SOL/BONK-USD via `KrakenClient`, fee dinamica letta correttamente (0,80% → 1,60% a giro). Le 2 righe INFO sono il cost-order fallback rifiutato vicino ai minimi assoluti (atteso, obiezione n.2 confermata in Fase 0) — irrilevante alle taglie da $25.

## 4. Le decisioni (nodi sciolti da Max)

1. **Venue per-riga, non flag globale.** Ogni grid sceglie l'exchange dalla sua riga: la Fase 2 diventa un flip a DB, niente env, niente rischio di deviare il processo sbagliato.
2. **Bonifica sito in Fase 1** (zero diff oggi, robusta al cutover).
3. **Gate real-money esplicito.** Un grid su riga Kraken in live parte SOLO con `ALLOW_REAL_MONEY=true` oltre alle chiavi: Kraken non ha testnet, le chiavi da sole non sono consenso.
4. **`site_flags` nuova** (non estendere project_status).

**Anti-assenso (a verbale):** il piano-memoria diceva "floor = un punto solo". Non bastava: senza allineare anche il trigger di vendita alla stessa fee, il bot chiederebbe vendite che il floor poi blocca → stallo silenzioso. Ho toccato entrambi. Secondo: il gate live Binance-specific è stato reso venue-aware, altrimenti un runner Kraken o non partiva o partiva senza protezione mainnet.

## 5. Nodo 5 — quello che resta per la Fase 2 (spiegazione per Max)

Il grid ha due protezioni: il **trigger** (quando *vuole* vendere) e il **floor** (sotto quale prezzo *non può*). Con la fee dinamica entrambi ora si adattano da soli: su Kraken un ciclo BTC chiederà un rialzo di ~1,2%+1,6% = **~2,8%** invece dell'1,4% del testnet — cicli più rari, ma ognuno margina davvero (i tuoi `sell_pct` attuali — BTC 1,20%, SOL 1,43% — sono **sotto** il costo del giro: sul testnet vincevi nominale, su Kraken perderesti).

L'unica cosa da decidere è **quanto profitto netto minimo pretendere oltre le fee** (`profit_target_pct` sulle righe Kraken, oggi 0). **Proposta: 0,4%** — "non vendere mai per meno di +0,4% veri in tasca". Questo numero e i passi buy/sell delle tre monete si scrivono nelle righe bot_config Kraken, che si inseriscono **solo in Fase 2** → non blocca nulla. Ti porto una tabella coi valori quando prepariamo la finestra.

## 6. Runbook Fase 2 (quando decidi tu)

1. Insert righe `BTC/USD`/`SOL/USD`/`BONK/USD` (venue='kraken', cycle nuovo, parametri collaudo — nodo 5).
2. Flip `is_active` (solo BTC/USD on), TF off via `trend_config`, disclaimer on (UPDATE `site_flags`), `ALLOW_REAL_MONEY=true` nell'env del processo.
3. Restart orchestrator (lo fai tu / me lo chiedi), Max versa $100.
4. Collaudo BTC → SOL → BONK (Fase 3), poi verdetto → deployment $600 (Fase 4).

Restano fuori scope Fase 1 ma mappati per la finestra: superfici sito non-cycle ancora Binance-only (prezzi hero/dashboard, market prices admin, daily report aggregato), asset immagine disclaimer, Nonce Window account-side (K.4). Elenco completo nel piano §Residui.

## 7. Cosa NON è stato fatto

- **Review avversaria multi-agente**: lanciata e fermata (fine sessione, tua richiesta). Sostituita da verifica manuale dell'invariante sui 4 punti a rischio + 290 test + prova generale 28/28. Rilanciabile prima della Fase 2 se vuoi il pass adversariale completo.
- **Modello B (ladder maker 0,40%)**: ri-esame Board pre-deployment coi numeri fee veri — non in Fase 1.
- **BUSINESS_STATE**: non toccato (territorio CEO). Se vuoi loggare Fase 1 + la fee 0,80%, l'update lo fai tu.

## Decisions (log di sessione)

- **DECISIONE:** venue per-riga (nodo 1). **RAZIONALE:** collaudo per-coin = flip a DB, niente env fragile. **ALTERNATIVE:** flag globale EXCHANGE (scartata da Max). **FALLBACK:** `venue='binance'` = identico; DROP migration = rollback pulito.
- **DECISIONE:** gate `ALLOW_REAL_MONEY` oltre alle chiavi (nodo 3). **RAZIONALE:** Kraken senza testnet, le chiavi erano per i test. **ALTERNATIVE:** solo chiavi (scartata: troppo facile partire per sbaglio). **FALLBACK:** flag assente = rifiuto di partire.
- **DECISIONE:** floor E trigger fee-aware insieme. **RAZIONALE:** toccarne uno solo = stallo silenzioso. **ALTERNATIVE:** solo il guard (scartata). **FALLBACK:** su binance fee_floor=0 → identici.
