# Report per il CEO — Sessione 42 (20 aprile 2026)

Caro CEO,

nove commit in giornata, due feature nuove e sette fix — di cui cinque tuoi, trovati perché tu guardi Telegram e la /tf con occhio allenato mentre io guardo solo codice e DB. Tre bug grossi erano mimetizzati dentro le due nuove feature: uno li avrei pescati al primo test reale, ma tu li hai visti prima di me. Ti racconto cosa è successo in ordine di importanza.

---

## Commit 1 — `82ed613` feat(tf): hot-reload dei TF safety params nei grid_runner (39j)

**Il problema di base:** modificavi `tf_stop_loss_pct` o `tf_take_profit_pct` via `/tf`, il DB veniva aggiornato, il Telegram di conferma arrivava (grazie a 39g della sessione precedente), ma i **grid_runner TF già vivi** continuavano a usare il valore vecchio finché non venivano riavviati o deallocati/riallocati. Solo i nuovi bot allocati dopo la modifica vedevano il valore fresco. Disallineamento strano e incoerente col resto del sistema, dove `bot_config` si hot-reloada automaticamente ogni 300s via `SupabaseConfigReader`.

**Cosa ho fatto:**
1. Esteso `SupabaseConfigReader` per pollare anche `trend_config` (tre campi: `tf_stop_loss_pct`, `tf_take_profit_pct`, `greed_decay_tiers` — quest'ultimo preparato per 42a che arrivava dopo).
2. Aggiunto `_sync_config_to_bot` nel grid_runner: ad ogni tick, per i bot TF, rilegge dal reader i due safety params e aggiorna in RAM se diversi. Log INFO sui cambi, nessun Telegram duplicato (quello lo manda già il TF scan loop).
3. **Migration 42a anticipata** — ho dovuto includere anche le colonne di 42a (`tf_initial_lots`, `initial_lots`, `greed_decay_tiers`, `allocated_at`) perché il nuovo polling legge `greed_decay_tiers` che altrimenti non sarebbe esistito.
4. **Fix collaterale scoperto per caso:** `stop_buy_drawdown_pct` mancava da `_CONFIG_FIELDS` dal commit di 39b. Il reader non lo aveva mai letto. Significa che da quando hai attivato 39b (~2 giorni fa), l'hot-reload di `stop_buy_drawdown_pct` non ha **mai funzionato**. Lo aggiungo qui mentre tocco i campi.

**Latenza:** fino a 5 minuti tra il save UI e l'applicazione live su tutti i bot TF. Post-restart post-42a non serve più toccare niente manualmente.

---

## Commit 2 — `a97f1ca` feat(grid-bot): multi-lot entry + greed decay take-profit (42a)

**Due feature insieme**, entrambe dal tuo brief 42a basato sull'analisi dei 102 trade TF: le entry sono troppo lente (il TF alloca una coin bullish ma il grid_bot aspetta un dip per comprare, se la coin pumpa subito perdiamo la finestra) e le uscite sono troppo tardive (le posizioni aperte oltre 20h drenano tutto il profitto accumulato nelle prime ore).

**Feature A — Multi-lot entry.** Sul primo ciclo dopo un ALLOCATE, invece di aspettare i dip della grid, il bot fa **N market buy aggregati** (N = `trend_config.tf_initial_lots`, default 3). Size = `capital_per_trade × N`. Dopo il primo tick il flag `initial_lots` torna a 0 in DB e il bot continua con la grid logic normale. Manual bot intatti (hanno sempre `initial_lots = 0`).

**Feature B — Greed decay take-profit.** Per i TF bot, il sell threshold **non è più `sell_pct`**. È il `tp_pct` del tier corrente di `greed_decay_tiers`, che decade nel tempo dal momento dell'ALLOCATE. Default tuo: 12% nei primi 15 min, 8% entro 1h, 5% entro 3h, 3% entro 8h, 1.5% da lì in avanti. Più la coin resta ferma, più il bot diventa impaziente di uscire. Stop-loss e take-profit totali rimangono controlli sovrapposti.

**Admin UI:**
- `tf_initial_lots` aggiunto alla sezione TF Safety (integer input)
- Nuovo editor "Greed decay tiers" con add/remove row, validation strict-ascending-by-minutes, audit log completo come i safety params.

**`allocated_at`** viene scritto dall'allocator su ogni ALLOCATE (anche SWAP re-allocation, quindi il clock della greed decay si resetta quando una coin rientra). Manual bot hanno `allocated_at=NULL` → fallback a `sell_pct` come sempre.

**Test unitari:** 5 casi coperti — no allocated_at, pre-first-tier (in fix 2179420 cambia semantica), tier match, oltre-ultimo-tier, manual bypass. Tutti passano.

---

## Commit 3 — `2179420` fix(42a): single aggregated buy + greed decay da t=0

Qui entrano i **due bug grossi** che hai trovato guardando GUN.

**Bug 1 — La multi-lot entry mandava 3 Telegram ma faceva 1 sola buy reale.** Sintomo che hai notato: "mi sono arrivati 3 messaggi assieme con lo stesso importo di acquisto". Avevi ragione solo in parte. In DB c'era **1 sola INSERT**. Come mai?

Il mio `_consume_initial_lots` chiamava `_execute_percentage_buy` **3 volte di seguito** nello stesso tick. Ma `_execute_percentage_buy` **muta lo state del bot prima di provare l'INSERT**: se l'INSERT fallisce, `holdings`, `_pct_open_positions`, `avg_buy_price`, `total_invested` restano avanti rispetto al DB. E nel DB c'è un trigger anti-dedup che rifiuta due trade identici (stesso symbol/side/price/amount) entro 5 secondi. Quindi:
- 1° chiamata: state updated, INSERT OK → 1 trade nel DB, 1 Telegram
- 2° chiamata: state updated (holdings += 428, posizione duplicata in FIFO), INSERT **rifiutata** dal trigger → nessun trade DB, ma `logger.info("BUY...")` e l'alert Telegram partono comunque
- 3° chiamata: identica alla 2°

Risultato: in paper il DB trigger ci ha salvato. **In live su Binance** avresti avuto 3 ordini market reali (cfg capital per trade = $9.9 × 3 = $29.7 spesi invece di $9.9). Poi al momento della sell, il bot vedeva `holdings` in-memory con 3 lotti ma DB con 1, provava a vendere 3 volte, e un altro trigger anti-short-sell respingeva le 2 sell spurie. Altri 2 Telegram spurii.

**Fix:** su tua indicazione esplicita, **1 buy = 1 ordine, anche per 3 lotti**. Il `_consume_initial_lots` ora fa una singola chiamata a `_execute_percentage_buy` con `capital_per_trade` temporaneamente scalato a N×. Risultato: 1 ordine Binance, 1 INSERT DB, 1 Telegram, 1 lotto (grosso) in FIFO. Il comportamento di exit è identico a un lotto normale, solo il size è maggiore.

Aggiunto anche un **latch in-memory** (`bot._initial_lots_done`) perché il cache del config reader si aggiorna ogni 300s: dopo la UPDATE di `initial_lots=0` sul DB, il reader continuava per 5 minuti a leggere il vecchio valore "3" dalla sua cache e a rifirare l'entry. Il latch è autoritativo per la sessione del processo.

**Bug 2 — Greed decay dormiva nei primi 15 minuti.** Sempre su GUN, hai visto una sell alle 14:06 con `tier 6.0%` (il `sell_pct` ATR-adaptive) invece del 12% del primo tier. Il motivo: nel mio `get_effective_tp` originale, se `age < tier[0].minutes`, il codice fallbackiava a `self.sell_pct`. "Safe fallback", pensavo io. "È sbagliato," hai detto tu: "se ho configurato 12% a 15min, voglio 12% **anche** a 5min — greed decay è la strategia, non un override che inizia a tempo".

**Fix:** rimosso il fallback. Per TF bot con `allocated_at` valido e `tiers` non vuoti, si usa **sempre** il tier appropriato, e per age < primo-tier si usa direttamente `tier[0].tp_pct`. Solo i manual bot e i TF bot senza `allocated_at` cadono su `sell_pct`.

---

## Commit 4 — `2d53a04` fix(tf-ui): idle-cash alert

**Il tuo sintomo:** in `/tf` il banner dice "$60 TF budget unallocated (60% of $100 idle)" ma poco sotto "Cash to reinvest $84.32". Due numeri contraddittori.

**Cosa succedeva:** il banner faceva `TF_BUDGET - sum(capital_allocation delle ACTIVE rows)`. Solo GUN era attiva con $39.59 → banner mostrava $60 idle. Ma tutte le ~15 coin deallocate nelle sessioni precedenti avevano restituito il loro capital al pool operativo insieme ai realized_pnl — $84 reali in cassa. Il banner ignorava completamente il cash *operativo* e guardava solo l'etichetta `capital_allocation` delle coin vive.

Poi tu, da degno CEO, hai osservato che **anche il mio primo fix era sbagliato**: "non sono gli unallocated, sono i persi". Avevi ragione. Tra cash e skim reserve abbiamo $98.28 netti su $100 iniziali, cioè −$1.72 in perdite. Di cui $44.73 realmente liberi (non pinnati a bot TF attivi) e $39.59 pinnati su GUN.

**Fix:** nuovo banner = "$44.73 TF cash idle (53% of $84.32 operational cash not deployed)". Formula allineata a quella della card "Cash to reinvest", threshold di alert invariato (>50% idle → giallo). Non più contraddizioni.

---

## Commit 5 — `760e6b0` + `b123f10` fix(web): banner AADS visibile + layout

**Il sintomo:** il banner a-ads.com nel footer del sito era taggato come "Ad Unit Is Partly or Fully Hidden", zero impression pagate. Tu lo vedevi bene, il crawler no.

**Causa:** tre red flag nel mio CSS originale:
1. `opacity: 0.85` sul parent — il crawler di A-ADS tratta opacity < 1 come "semi-hidden"
2. `width: 70%` + `height: auto` sull'iframe — prima che l'ad payload arrivi, il box computato è (viewport-dependente) × 0px. Il crawler headless misura spesso prima del caricamento.
3. Con `size=Adaptive`, l'ad aspetta un container con dimensioni esplicite; l'auto-sizing che avevo previsto era proprio ciò che non doveva avere.

**Fix:** rimossa l'opacity, dimensioni esplicite `728×90` con `max-width:100%` per mobile. Rinominato l'id da `frame` (troppo generico) a `aads-frame`.

**Poi, tua osservazione:** "togli il banner da roadmap" — giusto, la roadmap la legge chi già ti segue, non serve monetizzare lì. Lasciato solo sulla dashboard, più `margin: 3rem` sotto per staccarlo dai bottoni Telegram/GitHub/BuyMeACoffee.

---

## Commit 6 — `1e36fbf` fix(tf): scan Telegram teaser solo bullish

**Il tuo sintomo:** report del scan delle 16:01 UTC. "Top 2 per tier" mostrava GUN (BULLISH 28.7) + AAVE (BEARISH 22.2), poi ZRO (BEARISH) + BLUR (BULLISH), poi FET (NO_SIGNAL) + PLUME (BULLISH). E subito dopo "🟢 ALLOCATE — CHZ/USDT" che non compariva da nessuna parte. "Da dove arriva CHZ?"

**Risposta:** il "Top 2 per tier" ordinava per `signal_strength` **senza filtrare per signal**. Mischiava bullish/bearish/no_signal. L'allocator invece lavora solo sui bullish (ordinati per strength): GUN (HOLD, già allocato), SPK (SKIP per filter_fail), BLUR (SKIP per filter_fail), CHZ (ALLOCATE). CHZ era il 4° bullish in classifica, il primo non skippato.

**Fix:** teaser filtra ora solo `signal="BULLISH"`, header rinominato "Top 2 bullish per tier", rimossa la ripetizione del signal per riga (è sempre BULLISH). Se un tier ha 0 bullish, mostra `(no bullish candidates)` invece di sezione vuota.

---

## Commit 7 — `978893b` fix(tf): allocator pre-rounding prima del filter check

**Collegato al precedente.** Nel scan delle 16:01 UTC, SPK (strength 18.01) e BLUR (17.97) sono stati saltati con `FILTER_FAIL: amount 287.6043617... not aligned to step_size 1.0`. Il tuo commento preciso: "sembra follia, skippiamo monete forti per uno stupido arrotondamento di qualche centesimo".

**Causa:** l'allocator simulava `per_level_amount = per_level_usd / price` e controllava se era multiplo esatto dello step_size Binance. SPK a $0.1356 con $7.80 per level = 57.52 SPK. Step_size = 1.0. Non aligned → SKIP. Ma il grid_bot al momento del buy reale avrebbe chiamato `round_to_step(57.52, 1.0) = 57`, e 57 × $0.1356 = $7.73 notional, ben sopra il min_notional di $5. L'ordine sarebbe passato senza problemi.

**Fix:** nell'allocator, `per_level_amount = round_to_step(per_level_amount, step_size)` **prima** del `validate_order`. Così il filter check simula quello che Binance vedrebbe davvero. Ora SPK (in quelle condizioni) verrebbe allocato al posto di CHZ.

---

## Commit 8 — `2a934d7` fix(grid-runner): no Telegram spam su restart

**Il tuo sintomo:** ogni restart orchestrator, per ogni bot tapped out (SOL, BTC, BONK in tipico giorno trading), arrivavano due Telegram: "⚠️ BUY SKIPPED SOL/USDT Cash $0.07 → Servono $20" seguito da "⚠️ SOL/USDT Capitale esaurito".

**Causa:** i latch `_capital_exhausted` (True se già avvertito) e `_last_skip_notification` (dedup) erano variabili locali al loop. Restart → resetta a False/{}. Primo tick post-restart → il bot tenta un buy (cash esaurito dal giorno prima), `_execute_percentage_buy` lo aggiunge a `skipped_buys`, il grid_runner lo vede per la "prima" volta → spara Telegram. Poi verifica `available < MIN_LAST_SHOT` → `_capital_exhausted=False` → spara anche quello.

**La tua domanda intelligente in corso d'opera:** "ma se non avesse il capitale esaurito, comprerebbe una quota di moneta a prescindere solo perchè hai riavviato?" — NO, è garantito da un check a monte in grid_bot: se al restart ci sono `holdings > 0`, il primo buy viene saltato e `_pct_last_buy_price` viene settato a `avg_buy_price` restored dal DB. Nessun buy spurio possibile.

**Fix:** al boot del `run_grid_bot`, leggo `bot.get_status().available_capital` e se è sotto MIN_LAST_SHOT setto `_capital_exhausted = True` **prima** del loop. Così il bot sa già che è esaurito e non riavverte. Alerts continuano a funzionare sui veri **transition**: una sell che ripristina il cash manda "✅ Capitale ripristinato", una successiva ri-esaustione manda di nuovo "⚠️ Capitale esaurito".

---

## Stato GUN — piccola nota di bilancio

Hai chiesto: "se anche esce con lo stop loss, dovrebbe comunque chiudere in positivo, corretto?" 

Sì. Fatto il calcolo: GUN ha cristallizzato **+$1.92 realizzato netto** (prima sell +$0.64 al 6%, seconda +$1.28 al 12%). Attualmente holdings=0, non c'è posizione in pericolo. Se si rialloca e triggera stop-loss pieno (-3% di $39.59 = -$1.19), il ciclo TF complessivo chiude comunque a **+$0.73**. Il $0.96 skim reserve è già al sicuro, non intacca il calcolo.

---

## Brief archiviati

Spostati in `briefresolved.md/`:
- `brief_39j_trend_config_hot_reload.md`
- `brief_42a_multilot_greed_decay.md`

Rimangono in `config/` due brief non ancora toccati:
- `brief_36f_tf_trailing_stop.md`
- `brief_36h_haiku_sees_tf.md`

---

## Da testare in produzione al prossimo ALLOCATE

Il **prossimo ALLOCATE di una coin TF** sarà la prima volta che vedrai tutto il flusso 42a funzionare insieme:

1. `allocated_at` scritto in bot_config (verifichi via `/tf` o DB)
2. `initial_lots = 3` scritto
3. All'avvio del nuovo grid_runner: 1 singolo "🚀 Multi-lot entry: bought 3 lots at market ($X total)"
4. Poi normale grid logic + greed decay al 12% dal primo tick
5. Prima sell avrà reason "Greed decay sell: ... tier 12.0%" (non più 6%)
6. Dopo 15 min, nuova sell eventuale al 12% (tier identico), a 60min al 8%, ecc.

Al prossimo restart orchestrator: niente più doppio Telegram "BUY SKIPPED + Capitale esaurito" per BTC/SOL/BONK.

---

In testing,
Il tuo intern
