Brief S125b — real-money-reveal — 2026-08-07

**Da:** CEO
**A:** CC
**Dipende da:** `2026-08-07_S125_brief_kraken-fase3-execution.md` (S125a). Questo brief si esegue **dopo** che i bot girano su Kraken.
**Decisioni Board (Max, 2026-08-07):** storia testnet **archiviata come capitolo chiuso** (non rimossa) · cutover con **disclaimer page** (`disclaimer_mode=true`).

---

## 1. Perché adesso, e perché non è solo cosmetica

Rilevato sul sito live stamattina:

**`/terms`** — pagina legale:
> *"BagHolderAI is a paper trading experiment — **no real money is traded by our bots at this stage**."*

Affermazione **al presente**, **falsa dal 17 luglio 2026** (primo acquisto reale su Kraken, `kraken_test`, $25 di BTC). Non dal 22 luglio come indicato nella nota S124 — il primo denaro reale è di cinque giorni prima. È il finding **H1 dell'audit A2** e ha priorità sul resto di questo brief.

**Homepage:**
- banner *"live on Binance Testnet"*
- *"Real orders, simulated money. Every trade runs on Binance's test exchange, where prices are synthetic and balances are reset periodically without notice."*
- budget dichiarato *"$600 testnet"*
- *"The logic is real, the dollars aren't. Yet."*

**E le metriche in homepage sono tutte a zero:** Total P&L $0.00 · Today P&L $0.00 · Orders 0 · **Days running 0** · Today trades 0.

Il reset Binance del 5-6 agosto non ha solo invalidato la contabilità interna: **ha svuotato la vetrina**. Un visitatore oggi vede un progetto fermo, mentre ci sono $100 reali in posizione su Kraken da tre settimane. Il sito è già rotto adesso — questo brief non introduce un rischio, ne chiude uno aperto.

---

## 2. Sequenza di esecuzione

L'ordine non è negoziabile: il sito non deve mai mostrare uno stato intermedio incoerente.

```
1. disclaimer_mode = true          ← la homepage diventa pagina d'attesa
2. [esecuzione brief S125a]        ← i bot passano su Kraken
3. Passi A-E di questo brief       ← sito aggiornato dietro la pagina d'attesa
4. verifiche §5
5. disclaimer_mode = false         ← il sito torna su, coerente
```

Il testo della pagina d'attesa è già a DB (`site_flags.disclaimer_text`): *"We are going live on Kraken to test our bots — stay tuned!"*. Va bene così, non serve toccarlo. Solo la route homepage viene sostituita: blog, diario, roadmap, library restano raggiungibili.

**Se il Passo A (`/terms`) è pronto prima del resto, si pubblica subito senza aspettare.** È l'unico passo che non ha motivo di stare dietro la pagina d'attesa: correggere prima un'affermazione legale falsa è sempre meglio che correggerla dopo.

---

## 3. Passo A — `/terms` (priorità massima)

Sostituire il blocco che dichiara il paper trading. Testo proposto, da usare così o da rifinire con Max prima della pubblicazione:

> **Real money.** BagHolderAI's bots trade **real money on Kraken** — a small amount of the founder's own capital. This has been true since 17 July 2026. Before that date the project ran on Binance's testnet with simulated funds; figures from that period are labelled as historical testnet data and are kept for transparency.
>
> **We manage no one else's money.** BagHolderAI does not accept, hold, or manage funds from anyone. There is no product to invest in, no fund, no signal service.
>
> **Not financial advice.** Nothing published here is an offer, a solicitation, or investment advice. Trading data, performance figures and bot activity are published for educational and entertainment purposes. Past results — real or simulated — say nothing about future results. Do not make financial decisions based on anything published by BagHolderAI.

Rimuovere ovunque su `/terms`: *"paper trading only"*, *"binance testnet · live data"*, e ogni formulazione al presente che neghi il denaro reale.

**Verifica**: fare una ricerca testuale su tutto il sito per `paper trading`, `testnet`, `simulated`, `no real money`. Ogni occorrenza va classificata come "storica ed etichettata" oppure "falsa e da correggere". Nessuna occorrenza deve restare al presente non qualificata.

---

## 4. Passi B-E — sito

### Passo B — Homepage

Struttura invariata. Cambiano:

- **Live snapshot** → dati reali Kraken (BTC/USD + SOL/USD) al posto di Binance testnet
- **Banner** *"live on Binance Testnet"* → sostituito. Wording finale **in attesa di Max** (vedi §7)
- **Blocco** *"Real orders, simulated money…"* → riscritto: gli ordini sono reali **e** i dollari pure
- **Riga** *"The logic is real, the dollars aren't. Yet."* → non può restare. È la frase migliore della homepage e ora è falsa; il suo rovescio è il punto narrativo del reveal. **Testo da Max** (§7)
- **Budget** *"$600 testnet"* → capitale reale su Kraken. Il numero esatto dipende da quanto Max versa (vedi S125a §1): **non cablare $400, leggerlo dalla somma delle `capital_allocation` delle righe Kraken attive**

### Passo C — Dashboard

Secondo `COLLAUDO_COMMS_GUIDELINES` §2 Step 2, **con gli emendamenti del Passo E**:

- **Nuova sezione in alto**: dati Kraken + blocco caveat testuale
- **Scheda TF**: congelata/ferma (TF è spento da S125a, `ENABLE_TF=false`)
- **Scheda Grid**: filtrata sulle righe Kraken attive. **Attenzione**: le guidelines dicono "una moneta alla volta" — ora sono **due in parallelo** (BTC + SOL). Il filtro va su `venue='kraken' AND is_active=true`, non su una moneta cablata
- **Reconciliation**: su Kraken

Blocco caveat, adattato dal §3 delle guidelines ai numeri veri:

> Questo è un collaudo. Denaro reale su Kraken per verificare che la macchina esegua bene — fill, fee, slippage, riconciliazione. Non è la strategia completa. Non è prova che il sistema guadagni. Non è consulenza finanziaria.

Il riferimento *"($100)"* e *"1 moneta attiva"* del testo originale **vanno tolti**: entrambi superati.

### Passo D — Archivio della storia testnet

Decisione Board: **capitolo chiuso, non cancellato.**

- I dati dei cicli `testnet_1` e `testnet_2` restano consultabili, **etichettati esplicitamente come storici e simulati**, con la data di chiusura e il motivo: *reset dell'exchange, non scelta del progetto*
- I contatori pubblici (P&L, ordini, giorni) **non devono mescolare** testnet e Kraken in un unico numero. Se una metrica oggi somma i cicli, va separata
- I contatori "live" ripartono dalla storia Kraken (`kraken_test` + `kraken_2b`), che parte dal **17 luglio 2026**
- **`Days running` a 0 è il bug più visibile**: va ricalcolato sulla storia reale Kraken, non sul ciclo testnet morto

### Passo E — Emendare `COLLAUDO_COMMS_GUIDELINES_v1.md`

Il documento è **v2, confermato da Max il 7 luglio**, e la Fase 3 lo contraddice su tre punti. Se non viene emendato, chiunque lo legga dopo costruisce sul piano sbagliato:

| Guidelines v2 (7 lug) | Realtà Fase 3 (7 ago) |
|---|---|
| $100 di collaudo | **~$400** |
| un asset alla volta | **BTC e SOL in parallelo** |
| sequenza BTC → SOL → **BONK** | **BONK escluso** (volume Kraken $29K/24h) |

Da aggiornare anche §1 (*"è sequenziale: un asset alla volta"* — non più vero) e §5 (il display *"$100 (USD)"*).

Il **principio-madre §0 resta intatto e vale più di prima**: mostriamo che l'impianto tiene, non che stiamo facendo soldi.

---

## 5. Verifiche prima di `disclaimer_mode = false`

- [ ] `/terms` non contiene affermazioni al presente che neghino il denaro reale
- [ ] ricerca testuale su tutto il sito per `paper trading` / `testnet` / `simulated` / `no real money`: ogni occorrenza è storica ed etichettata, oppure corretta
- [ ] homepage: nessun riferimento a Binance testnet come stato corrente
- [ ] `Days running` e i contatori mostrano la storia Kraken, non zeri
- [ ] snapshot homepage e dashboard leggono le righe Kraken vive
- [ ] budget mostrato = somma reale delle allocazioni Kraken, non un numero cablato
- [ ] le **8 superfici legate a Binance** elencate in PROJECT_STATE §3: ognuna migrata **oppure dichiarata** con motivazione. *Usa la tua lista §3 locale — non l'ho ricostruita e non voglio che CC lavori su un elenco inventato da me*
- [ ] blog e diario raggiungibili durante tutta la finestra

---

## 6. Fuori perimetro (dichiarato, non dimenticato)

- **Backtest pubblico girato a commissione dimezzata** (0,40% invece di 0,80% reale, PROJECT_STATE §5). Con denaro reale in campo quel materiale è fuorviante. **Non lo tocchiamo in questa finestra**, ma va annotato o corretto: è la prossima decisione editoriale, e non deve sparire.
- **Post di annuncio su X / blog.** Regola marketing: lo scrive Max in italiano, io traduco. Non è in questo brief. Il tono di riferimento è §4 delle guidelines: *"primo dollaro vero"*, la piccolezza è rigore, niente percentuali come titolo.
- **XRP a prezzo fisso** e **Sentinel / NewsKeeper / Sherpa**: parcheggiati dal Board a dopo il go-live.

---

## 7. Da Max prima della pubblicazione

Due stringhe sono **voce del progetto**, non testo tecnico, e per regola le scrive lui in italiano:

1. il badge che sostituisce *"live on Binance Testnet"* (il segnaposto delle guidelines è *"real money, real Kraken"*, mai rifinito)
2. la riga che sostituisce *"The logic is real, the dollars aren't. Yet."*

Fino ad allora si può fare tutto il resto. **Il Passo A non aspetta queste due stringhe.**

---

## 8. Auto-obiezione

**Stiamo facendo il reveal nel momento peggiore per i numeri.** La posizione Kraken è in leggera perdita (−0,3%), non ha mai completato un ciclo in 16 giorni, e il realized del ciclo `kraken_2b` è **$0,00**. Dichiarare "ora sono soldi veri" mentre l'unica cosa che i soldi veri hanno fatto finora è stare fermi non è la vetrina migliore.

**Sostengo comunque di procedere**, per tre motivi: la pagina legale è falsa oggi e ogni giorno in più è esposizione gratuita; la homepage mostra già zeri, quindi lo scenario "aspettiamo di avere bei numeri" sta *già* costando; e il principio-madre del progetto è che si mostra che l'impianto tiene, non che si guadagna — una posizione ferma e onestamente raccontata è esattamente dentro quel principio.

**Ma va detto in faccia a chi decide**, non scoperto dopo: se il reveal esce e la prima settimana di denaro reale non produce un ciclo, il sito lo mostrerà. Se questo non è accettabile, allora la decisione da prendere non è *quando* fare il reveal — è *quali numeri* la homepage mostra in prima battuta.

**Seconda obiezione, sul metodo:** questo brief tocca la pagina legale del sito. Non sono un avvocato e il testo del Passo A è scritto da me. È molto meglio di quello che c'è ora — che è semplicemente falso — ma non è una revisione legale.
