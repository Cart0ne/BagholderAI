# Nota per il CEO — Kraken Fase 3: piano operativo

**Data:** 2026-08-06 (S124)
**Tipo:** piano operativo — **NON eseguito**, in attesa di approvazione Board
**Origine:** decisioni di Max in sessione, dopo il rilevamento del reset Binance testnet
**Commit di riferimento:** `f98afbc` (fix T.4), `0152a86` (PROJECT_STATE S124)

---

## 1. Il fatto che ha innescato tutto

Il **Binance testnet si è azzerato** fra il 5-ago 01:00 UTC e il 6-ago 01:00 UTC (finestra ricavata dal cron di riconciliazione: il 5 chiudeva `OK matched=79`, il 6 `WARN_BINANCE_EMPTY matched=0`).

Il wallet è tornato alla dotazione di default; il database continua a contare posizioni che sull'exchange non esistono più:

| | wallet reale | database |
|---|---|---|
| BTC | 0,99844 | 0,00077689 |
| SOL | 6,0 | 0,812187 |
| BONK | 18.446 | 33.137.599 |
| ETH | 1,0 | 0,016184 |

I bot non se ne accorgono e continuano a operare senza errori, perché il wallet post-reset è più *ricco* di quanto il database creda. Il ciclo `testnet_2` (Day 63, dal 5 giugno) è di fatto finito.

**Kraken non è stato toccato**: venue separato, riga separata, saldi reali intatti.

---

## 2. La decisione del Board (Max)

Invece di aprire un `testnet_3` — che ricomincerebbe una contabilità finta destinata a essere azzerata di nuovo — **si abbandona il testnet e si va tutti su Kraken con denaro reale**.

Decisioni prese:

1. **Binance resta come fonte dati** (prezzi, klines per Sentinel, proxy di volatilità per Sherpa). Si spengono solo i bot che *operano* su testnet.
2. **Live su Kraken con BTC e SOL.**
3. **BONK fuori dal primo giro** (motivazione al §3).
4. **Il Trend Follower si ferma**, per essere ripreso più avanti.
5. **La Fase 2b diventa Fase 3**: i $100 già investiti restano dove sono, si aggiunge capitale sopra. Nessun azzeramento, nessuna interruzione della storia del denaro reale.
6. **Sequenza successiva**: mentre il sistema gira con soldi veri su Kraken, si lavora su Sentinel, NewsKeeper e Sherpa. Il TF viene ripreso dopo.
7. **Nuovo esperimento**: un bot su XRP che opera con ordini a prezzo fissato invece che a mercato, per misurare sul campo la tariffa ridotta (§6).

---

## 3. I dati che motivano l'esclusione di BONK

Misurazione diretta sul book Kraken, oggi:

| moneta | spread | volume 24h |
|---|---|---|
| LINK/USD | 0,000% | $1,5M |
| **BTC/USD** | **0,000%** | **$64,3M** |
| ETH/USD | 0,001% | $30,4M |
| XRP/USD | 0,001% | $20,8M |
| **SOL/USD** | **0,014%** | **$9,8M** |
| DOGE/USD | 0,019% | $1,8M |
| ADA/USD | 0,066% | $20,0M |
| **BONK/USD** | **0,667%** | **$29K** |

Il numero che decide non è lo spread: è il **volume giornaliero di $29.000**. Le altre monete stanno fra il milione e i sessanta milioni. BONK su Kraken è praticamente deserta — lo spread largo è la conseguenza.

Conseguenza economica: fra commissioni (0,80% × 2) e spread (0,84%), ogni ciclo di BONK partirebbe con circa **2,44% di costi** contro un obiettivo di guadagno del 2,38%. Il bot non ci rimetterebbe — il meccanismo di vendita è già tarato per coprire i costi — ma **alzerebbe l'asticella**: aspetterebbe un movimento del ~4% invece del ~2,6% che gli bastava su Binance. Tradotto: BONK resterebbe fermo per lunghi periodi.

**Il rischio non è perdere i $50, è non ottenere alcun dato.**

Metodologia proposta come criterio stabile per la scelta futura degli asset: **spread e volume vanno letti insieme, mai lo spread da solo** (una moneta morta ha due prezzi vicinissimi solo perché nessuno scambia). Posso trasformare questa classifica in uno script ricorrente.

---

## 4. Il piano operativo

Tutto in **una finestra sola**, perché il punto 4 richiede comunque un riavvio.

**Passo 1 — spegnere i bot su testnet** *(nessun riavvio necessario)*
`is_active = false` sulle 4 righe Binance: `BTC/USDT`, `SOL/USDT`, `BONK/USDT`, `ETH/USDT`.
L'orchestratore rilegge questo campo ogni 30 secondi e i processi si chiudono da soli.

*Verificato*: il meccanismo che "resuscita" i bot spenti con posizioni residue filtra su `managed_by='tf'`, mentre la riga ETH è `managed_by='tf_grid'` — **non verrà riaccesa**.

**Passo 2 — portare BTC/USD a regime**
`capital_allocation`: $100 → **$250**. Il ciclo resta `kraken_2b`, la posizione aperta resta.

**Passo 3 — aprire SOL/USD**
Nuova riga: venue `kraken`, ciclo `kraken_2b`, `capital_allocation` **$150**, gestita da Sherpa come BTC.

**Passo 4 — riavvio dell'orchestratore** con `ENABLE_TF=false`
Ferma il Trend Follower (è un flag d'ambiente, richiede il riavvio) e porta in volo il fix del report P&L di oggi, che è già nel repository ma non ancora nei processi attivi.

**Passo 5 — verifiche**
Processi attivi = 2 grid Kraken + Sentinel + Sherpa (niente TF, niente grid Binance); primo tick di ciascun grid a buon fine; nessun ordine inatteso; report serale coerente.

---

## 5. Decisioni ancora da prendere

**a) Capitale totale e disponibilità.** Il piano richiede **$400 sul conto Kraken** ($250 + $150), contro i $100 attuali. Servono **$300 aggiuntivi** — più l'eventuale dotazione per l'esperimento XRP. *Non ho interrogato il saldo dell'account*: la chiave è la stessa che il bot sta usando per operare con denaro reale, e una mia chiamata rischiava di far fallire una sua operazione. Da verificare insieme.

**b) Granularità dei lotti.** Oggi BTC lavora con $100 divisi in 3 lotti da $33,33. Portandolo a $250, mantenendo 3 lotti si arriva a ~$83 l'uno; mantenendo il lotto a ~$33 si passa a 7 livelli. **Raccomandazione: mantenere il lotto piccolo e aumentare i livelli** — più granularità significa più occasioni di ciclo, che è ciò di cui il grid vive. Da decidere anche per SOL.

**c) Parametri di acquisto e vendita per SOL su Kraken.** Su Binance SOL girava con acquisto −3% e vendita +1,27%. Con le commissioni Kraken il margine netto va rivisto: è il "nodo 5" già aperto in PROJECT_STATE §6 (`profit_target_pct` sulle righe Kraken, proposta a 0,4% netto oltre le commissioni). Da chiudere in tabella prima dell'inserimento.

**d) Etichetta del ciclo.** Raccomandazione tecnica: **lasciare `kraken_2b` com'è** e chiamarla Fase 3 solo nella narrazione. Quella stringa è usata come filtro su molte superfici (sito, report serale, snapshot giornalieri) e rinominarla è un'operazione cosmetica dal costo sproporzionato. Se il Board vuole l'etichetta allineata, si fa con un aggiornamento in blocco — va detto ora, non dopo.

---

## 6. L'esperimento XRP (lavoro separato)

**Idea di Max.** Oggi tutti i bot comprano e vendono "a mercato", cioè senza indicare un prezzo: dicono *"compra 50 dollari"* e accettano qualunque prezzo esca. Un bot che invece indica il prezzo massimo che accetta ottiene due cose:

1. **Sicurezza**: se il mercato si sposta fra la decisione e l'esecuzione, l'ordine semplicemente non viene eseguito, invece di eseguire a qualsiasi prezzo.
2. **Commissione ridotta** — ma solo se l'ordine *aspetta* nel mercato invece di eseguire subito.

Sono due modifiche diverse e va detto chiaramente: la prima è contenuta, la seconda richiede una macchina che oggi non esiste (tenere traccia degli ordini in attesa, cancellarli quando scadono, gestire le esecuzioni parziali, rifarli ogni volta che Sherpa cambia i parametri).

**Perché vale la pena**: il listino che la nostra libreria riporta dice commissione ridotta allo 0,25%, ma sul fill reale abbiamo pagato **0,7999%** contro lo 0,40% dichiarato — quel listino è già stato smentito una volta. Il numero vero **non lo sappiamo**, e l'unico modo di scoprirlo è fare un ordine di quel tipo e leggere l'addebito. L'esperimento produce un dato che oggi non esiste, e che vale su tutte le monete.

**Perché XRP**: spread 0,001% con $20,8M di volume. ADA è l'alternativa (0,066%, $20,0M): volume paragonabile, ma spread sessanta volte più largo.

**Nota di merito**: il grid è la strategia più adatta a questo modo di operare. Sa già in anticipo a che prezzo vuole comprare ("il 3% sotto"); oggi aspetta che il prezzo ci arrivi e poi compra di corsa, mentre potrebbe semplicemente lasciare l'offerta a quel prezzo e attendere di essere servito.

---

## 7. Cosa serve dal CEO

**Il reveal pubblico.** La Fase 3 lo comprende, e chiude un problema aperto: il finding **H1 dell'audit A2** segnala che il sito dichiara ovunque "testnet / no real money" mentre il denaro reale gira dal 22 luglio. Il caso peggiore è la pagina legale `/terms` ("*no real money is traded by our bots at this stage*"), un'affermazione al presente oggi falsa. Il meccanismo per il cambio è già pronto in codice (`DisclaimerGate` + `site_flags.disclaimer_mode`).

**La narrazione del passaggio.** Va raccontato che il testnet è finito per un reset dell'exchange e non per una nostra scelta estetica, e che il portafoglio Binance mostrato finora smette di esistere. Il sito è guidato dai dati del ciclo: nel momento in cui i bot Binance si spengono, quei numeri vanno gestiti — o archiviati come storia chiusa, o rimossi.

**Le otto superfici ancora legate a Binance** elencate in PROJECT_STATE §3 (prezzi in homepage, pannello prezzi admin, report serale cross-venue, disclaimer sugli asset e altre) vanno migrate o dichiarate. È lavoro mio, ma l'ordine di priorità è una scelta editoriale.

---

## 8. Rischi noti, dichiarati

- **Si perde il banco di prova gratuito.** Da qui in avanti ogni errore costa soldi. È il motivo per cui l'esperimento XRP va tenuto separato dai bot che lavorano.
- **Resta aperto il difetto del prezzo fasullo** (PROJECT_STATE §5): il bot decide sull'ultimo scambio avvenuto, che può essere vecchio o anomalo, e non lo confronta con i prezzi realmente disponibili. Sul book Kraken di BTC e SOL — profondo milioni di dollari — il rischio è basso, e il report dell'incidente lo dice esplicitamente. **Non è più un gate**, ma resta manutenzione da fare.
- **Il backtest pubblico ha girato a metà della commissione reale** (0,40% invece di 0,80%, PROJECT_STATE §5). Con capitale reale in campo, quel materiale va corretto o annotato: è già una decisione editoriale in sospeso.
- **Nessun dato storico di riferimento su Kraken**: si riparte da 15 giorni di operatività su una sola moneta.

---

## 9. Cosa non è stato fatto

Nessuna riga di configurazione modificata, nessun capitale spostato, nessun bot fermato o riavviato. Il sistema è esattamente com'era: 4 grid Binance su numeri ormai fittizi, 1 grid Kraken con $100 reali, TF e cervelli attivi.

Resta inoltre in sospeso, indipendente da questo piano: il riavvio per portare in volo il fix del report P&L (`f98afbc`) e una bozza X in attesa di approvazione.

---

*Fonti: book e volumi Kraken misurati il 2026-08-06; `cron_reconcile.log` sul Mac Mini; tabelle `bot_config`, `trades`, `daily_pnl`; `report_for_CEO/2026-07-22_eth-bad-tick-slippage_report_for_ceo.md`; PROJECT_STATE §3/§5/§6.*
