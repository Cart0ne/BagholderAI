# Blocco di aggiornamento BUSINESS_STATE.md — S125 (2026-08-07)

**Istruzioni per Max:** le righe qui sotto vanno **in cima alla §4** (Decisioni), che è ordinata dalla più recente. Include anche le decisioni di **S124 (6 agosto) mai loggate** — quella sessione non ha prodotto diary né aggiornamento di stato.

Le due righe marcate ⚖️ sono disaccordi CEO↔Board risolti da Max, loggati come da regola CROSS-CHECK.

---

## §4 — righe da inserire

| Data | Decisione | Perché |
|---|---|---|
| 2026-08-07 (S125) | **Reveal pubblico "soldi veri" approvato e messo davanti a tutto il resto** — brief S125b. `/terms` corretta per prima, senza aspettare il resto del sito | La pagina legale afferma **al presente** *"no real money is traded by our bots at this stage"*, falso dal **17 luglio** (finding H1 audit A2). Aggravante rilevata in sessione: dopo il reset Binance la homepage mostra **tutti zeri** (Orders 0, Days running 0) mentre $100 reali sono in posizione su Kraken — il sito non è solo falso, è vuoto. Aspettare costa comunque |
| 2026-08-07 (S125) | **Storia testnet archiviata come capitolo chiuso, non rimossa** | 5 mesi di dati restano consultabili ed etichettati come storici/simulati, con la causa dichiarata: reset dell'exchange, non scelta del progetto. I contatori pubblici non devono più mescolare testnet e Kraken in un unico numero |
| 2026-08-07 (S125) | **Cutover sito con `disclaimer_mode=true`** (meccanismo già in codice, testo già a DB) | Nessun minuto di dati rotti o incoerenti durante la finestra. Coerente col principio "il limbo è il rischio n.1". Solo la route homepage: blog, diario, roadmap restano raggiungibili |
| ⚖️ 2026-08-07 (S125) | **Nessuna modifica al comportamento dei bot nel passaggio a Kraken.** `profit_target_pct` resta **0**, LAST SHOT invariato, `sell_pct` invariato. Cambia solo il venue | **Disaccordo risolto da Max.** Il CEO proponeva di attivare `profit_target_pct` a 0,4% come rete contro la sell ladder che scende sotto il costo di carico, e di rivedere il LAST SHOT su denaro reale. Max: *"il resto è tutto collaudato e funzionante, le fees sono già assorbite dall'obiettivo di guadagno e calcolate in base all'exchange"*. Il CEO ha verificato: `sell_pct` è **già netto-fee e per-venue** — l'obiezione era mal fondata. Principio accolto: l'unica variabile che cambia in questa finestra è l'exchange |
| ⚖️ 2026-08-07 (S125) | **LAST SHOT mantenuto attivo su denaro reale** | **Decisione Max.** Il CEO aveva sollevato che il meccanismo concentra il capitale residuo su un singolo prezzo, annullando la logica della scala (il 28 luglio ha speso $64,44 in un ordine solo, due terzi dell'allocazione). Max: con `capital_allocation` a $250 e lotto $33 la scala ha 7 livelli, quindi il LAST SHOT scatta solo dopo un drawdown ~21%, dove concentrare ha una sua logica. Zero codice, zero rischio nuovo |
| 2026-08-07 (S125) | **`COLLAUDO_COMMS_GUIDELINES_v1.md` da emendare** — è v2 confermata 7 luglio e la Fase 3 la contraddice su 3 punti | Il documento dice $100 / un asset alla volta / sequenza BTC→SOL→BONK. La realtà è ~$400 / due monete in parallelo / BONK escluso. Non emendarlo significa far costruire il sito su un piano superato. Il principio-madre §0 resta intatto |
| 2026-08-06 (S124) | **Abbandono del testnet Binance: tutti su Kraken con denaro reale.** Binance resta come **fonte dati** (prezzi, klines Sentinel, proxy volatilità Sherpa); si spengono solo i bot che operano | Il testnet si è azzerato fra il 5 e il 6 agosto (finestra dal cron di riconciliazione: `OK matched=79` → `WARN_BINANCE_EMPTY matched=0`). Aprire un `testnet_3` ricomincerebbe una contabilità finta destinata a essere azzerata di nuovo. I bot non se ne accorgevano perché il wallet post-reset era più *ricco* del database |
| 2026-08-06 (S124) | **BONK escluso dal primo giro su Kraken** | Volume 24h su Kraken: **$29K**, contro $1,5M-$64M di tutte le altre. Fra commissioni (0,80%×2) e spread (0,84%) ogni ciclo partirebbe con ~2,44% di costi contro un obiettivo del 2,38%: il bot non ci rimetterebbe, ma aspetterebbe movimenti del ~4% invece del ~2,6%. **Il rischio non è perdere i $50, è non ottenere alcun dato** |
| 2026-08-06 (S124) | **Criterio stabile per la scelta asset: spread e volume si leggono INSIEME, mai lo spread da solo** | Una moneta morta ha due prezzi vicinissimi solo perché nessuno scambia. Lo spread largo di BONK è la conseguenza del volume, non la causa. Metodologia da trasformare in script ricorrente (parcheggiato) |
| 2026-08-06 (S124) | **Fase 2b → Fase 3 senza azzeramento**: i $100 già investiti restano dove sono, si aggiunge capitale sopra. **Ciclo resta `kraken_2b`** — "Fase 3" è solo narrazione | Nessuna interruzione della storia del denaro reale. La stringa `kraken_2b` è usata come filtro su molte superfici (sito, report serale, snapshot): rinominarla è cosmetico dal costo sproporzionato (raccomandazione CC accolta) |
| 2026-08-06 (S124) | **Trend Follower fermato** (`ENABLE_TF=false`), da riprendere più avanti | Il collaudo su denaro reale è grid-only. Sequenza successiva: mentre il sistema gira con soldi veri su Kraken si lavora su Sentinel, NewsKeeper e Sherpa; il TF si riprende dopo |

---

## Da riflettere altrove in BUSINESS_STATE

**§6 Vincoli/Deadline** — la riga *"Reset testnet Binance | Stimato ~inizio luglio 2026"* è **avvenuta**: 5-6 agosto. Va chiusa come accaduta, con la nota che è stata il trigger effettivo del cutover, esattamente come previsto.

**§6, riga "S119 — collaudo Kraken in corso"** — la *Fase 2a* è chiusa dal 21 luglio (sell reale registrato, +$0,71 netto). Da aggiornare.

**§5 Domande aperte** — il "nodo 5" (`profit_target_pct` sulle righe Kraken) può essere chiuso come **deciso: resta 0**, con il chiarimento emerso in S125: `profit_target_pct` non è un obiettivo di profitto ma un **safety gate** che blocca le vendite sotto una soglia sopra il costo medio; `sell_pct` è già netto-fee e per-venue.

---

## Parcheggiati in S125 (non decisi, non persi)

- **XRP con ordini a prezzo fisso** — misurare la commissione maker reale (il listino dichiara 0,25%, ma sul fill reale abbiamo pagato 0,7999% contro lo 0,40% dichiarato: quel listino è già stato smentito una volta). Da separare in due lavori: *un singolo ordine limite per leggere l'addebito* (mezz'ora) vs *la macchina completa di gestione ordini in attesa* (settimane)
- **Sentinel / NewsKeeper / Sherpa** — dopo il go-live
- **Backtest pubblico girato a commissione dimezzata** (0,40% invece di 0,80%) — decisione editoriale, ora più urgente perché c'è denaro reale in campo
- **Difetto del prezzo fasullo** — non più un gate (book Kraken profondo su BTC/SOL), ma manutenzione aperta
- **Script ricorrente spread + volume** per la selezione asset futura
