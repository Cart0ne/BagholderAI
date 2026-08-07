# MEMO — Kraken Fase 2b (switch reale sui $100)

**Data:** 2026-07-21 · **Autore:** CC · **Stato:** draft da rifinire con Max/Board
**Contesto:** Fase 2a **CHIUSA** ✅ — round-trip reale completo su Kraken (BUY $25 → SELL) registrato correttamente dal bot. Questo memo raccoglie tutto quello che è emerso attorno al test e che va gestito **prima/durante** la 2b. Vedi anche PROJECT_STATE §3/§5, BUSINESS_STATE §4, memoria `reference_grid_sell_trigger_fee_buffered`.

---

## 0. Round-trip 2a — numeri reali (baseline verificata)
- BUY 17-lug: 0,00039379 BTC @ $63.483,50 · costo $24,999 · fee $0,200 · order `OCILGP-2GRMI-D3WSNK`
- SELL 21-lug: stessa qty @ **$66.317,10** · revenue lordo **$26,115** · fee $0,209 · **realized +$0,70693** · order `ORBVLH-VSYWS-AMEMH5`
- Cash finale sul conto: **~$25,71 USD** disponibili (parte dei ~$100 caricati) → **contarli nella matematica di funding 2b**.
- ✅ Ha validato dal vivo: fix critico su path SELL (fill via `fetch_order`, un solo ordine), fee 0,8% taker, trigger fee-buffered reale.

## 1. Trigger SELL = fee-buffered (sell_pct è NETTO, non lordo) 🔴 da tenere a mente nel settaggio
- Formula eseguita: `grid_bot.py:876` → `sell_trigger = avg × (1 + sell_pct/100 + fee) / (1 − fee)`.
- Su Kraken (fee 0,8%) → trigger ≈ **avg × 1,036** (~3,6% sopra avg), NON avg×1,02.
- **Implicazione settaggio 2b:** `sell_pct` è il margine **netto post-fee**. Se per una moneta vuoi "vendi a +X% lordo", devi impostare `sell_pct` PIÙ BASSO sapendo che il codice ci aggiunge il round-trip. Non impostare i sell_pct delle 3 monete col modello mentale "lordo".

## 2. Nodo 5 — formula del floor va corretta PRIMA di tarare il margine 🟠
- `sell_pipeline.py`: `min_price = avg × (1 + min_profit/100 + 2×fee)`. Ma da S118 l'avg **include già 1× fee** → il floor doppia-conta la fee di buy (~0,8% troppo protettivo su Kraken).
- Il margine collaudo (proposta 0,4%) va scelto **sopra il break-even vero** `avg×(1+fee)`, non `avg×(1+2×fee)`.
- **Azione 2b:** correggere la formula del floor + poi tarare `profit_target_pct` delle righe Kraken. Trigger (§1) e floor (§2) condividono il `fee_rate`: devono muoversi insieme o il bot chiede vendite che il floor blocca (stallo silenzioso).

## 3. Bug display/log del trigger — fix da bundle-are col restart 2b 🟡
- `get_status` (`grid_bot.py:1179-1180`) e Range print (`:342`) MOSTRANO `avg×(1+sell_pct/100)` = numero ingenuo ($65.271 sul test), etichetta "(+2% above avg)". L'ESECUZIONE usa il fee-buffered (§1). → terminale/dashboard/Telegram **mentono** sul target.
- **Fix:** un helper unico del trigger (branch grid vs TF, identico a :876) chiamato sia dall'esecuzione sia da tutti i display + etichetta "net, fee-buffered". Verificare anche daily_report + sito. Display-only, effetto al restart → **farlo nel bundle 2b**.

## 4. Ancora del BUY dopo un sell completo + divergenza al restart 🟠 da capire prima della 2b
- Al restart, `state_manager.py:202` riporta `_pct_last_buy_price` = **ultimo BUY** ($63.483) → buy trigger −0,3% = $63.293.
- Ma il processo VIVO pre-restart aveva `buy_reference_price` recalibrato al **sell price** ($66.317) in `bot_runtime_state` (recalibrate a sell-time, 10:11:08).
- → **un restart CAMBIA dove il bot ricomprerebbe** (66.317 → 63.483). Nella 2b il grid vende e ricompra in continuazione: bisogna decidere qual è l'ancora *intenzionale* del prossimo BUY dopo un sell (last_buy / sell_price / current). Collegato al nodo aperto "buy trigger anchor A/B/C". Stessa famiglia dei bug di persistenza già incontrati.

## 5. Gestione processo — il babysitter 2a era FRAGILE, la 2b va fatta bene 🔴
- Il babysitter 2a girava: **standalone in foreground in un Terminal**, dentro un **loop di respawn** (`while`/keep-alive), **senza file di log**, e **non riparte al reboot del Mini**. Ciecità totale (diagnosi solo via DB) + un kill del figlio veniva rigenerato dal loop.
- **Per la 2b il grid Kraken deve essere:** orchestrator-managed (o daemonizzato pulito `nohup caffeinate`), **con file di log** (`logs/grid_BTC_USD.log`), **niente loop ad-hoc in terminale**. Il babysitter/loop 2a è stato ucciso il 21-lug — **verificare che non resti nessun terminale con quel loco aperto** prima della 2b.

## 6. Sicurezza re-buy: il path di BUY NON è gatato da `is_active` ⚠️
- Con holdings 0 e cassa disponibile, un grid vivo può **ricomprare denaro reale** su un dip anche con `is_active=false` (dimostrato: il BUY del 17-lug è avvenuto con `is_active=false`). Solo dead-zone recalibrate e idle re-entry sono gatati da `is_active`, non il BUY ordinario.
- **Azione 2b:** assicurarsi che SOLO le righe delle monete che vogliamo tradare siano `is_active=true`, e che nessuna riga "di prova" possa eseguire ordini reali. Se una posizione va chiusa e lasciata ferma, **spegnere il processo**, non fidarsi di `is_active=false`.

## 7. Runbook finestra coordinata 2b (già noto, da eseguire)
Sequenza: nodo 5 chiuso → insert righe Kraken (BTC/SOL/BONK su /USD coi parametri decisi) → flip `is_active` sulla moneta attiva → **TF off** → disclaimer page on → `ALLOW_REAL_MONEY=true` → **restart** (che porta LIVE anche i fix §2/§3 + T.2/T.3 già coded) → grid lavora sui ~$100. Poi Fase 3 collaudo BTC→SOL→BONK.

## 8. Contorno / minori
- `trades` **non ha colonna `venue`**: separazione Kraken↔testnet regge su `cycle` + simbolo. Valutare colonna `venue` quando Kraken va a 3 monete (BUSINESS_STATE §5).
- Reconcile logga "Binance" anche su venue kraken (`state_manager.py:339/417`, etichetta hardcoded; fonte dati corretta) → micro-fix cosmetico.
- Riga `bot_config` BTC/USD Kraken ($25, is_active=false, cycle=kraken_test): il ciclo ora è **chiuso** (holdings 0) → non è più pericoloso cancellarla, ma decidere se tenerla come storico o rimuoverla nel setup 2b.

---
*Da rivedere con Max/Board prima di aprire la finestra 2b. Fonti: sessione 21-lug (chiusura 2a + caccia al trigger), PROJECT_STATE §5, memoria `reference_grid_sell_trigger_fee_buffered`.*
