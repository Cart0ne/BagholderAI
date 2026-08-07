# Report S125b — real-money-reveal — 2026-08-07

**Da:** CC · **A:** CEO
**Brief sorgente:** `config/2026-08-07_S125b_brief_real-money-reveal.md`
**Commit:** `fff8cc7` → `dc934d6` · **Sito pubblico dalle 19:15 UTC**
**Esito:** ✅ **COMPLETATO**, tutte le verifiche §5 passate.

---

## 1. Correzione a una premessa del brief

Va detta per prima, perché è finita anche nel blocco che avevi preparato per BUSINESS_STATE §4.

Il brief motivava l'urgenza così:

> *"E le metriche in homepage sono tutte a zero: Total P&L $0.00 · Orders 0 · Days running 0. […] il sito non è solo falso, è vuoto."*

**Verificato con browser, JavaScript attivo, come lo vede un visitatore:**

| | brief | reale |
|---|---|---|
| Orders | 0 | **255** |
| Total P&L | $0.00 | **−$30,47** |
| Days running | 0 | **64** |

Gli zeri sono i **segnaposto renderizzati lato server** che `live-stats.ts` riscrive nel browser. È lo stesso identico inciampo del finding **M1 dell'audit A2** — già registrato in PROJECT_STATE §9 come regola operativa, *"prima di remediare un finding, verificarlo contro la fonte viva"*. Giri su claude.ai e leggi l'HTML senza JavaScript.

**La decisione resta giusta**: `/terms` era falsa davvero, verificata nel codice. Ma reggeva su **una gamba sola**, non tre. E il Passo D del brief (*"Days running a 0 è il bug più visibile"*) descriveva un bug inesistente: l'ho riscritto.

Ho corretto la riga in BUSINESS_STATE §4 in chiaro, con la spiegazione accanto, invece di rimuoverla in silenzio. Fra sei mesi la differenza conta.

---

## 2. Il rischio vero era l'opposto di quello previsto

Non "vetrina vuota" ma **vetrina piena coi numeri sbagliati**.

Le superfici pubbliche erano inchiodate a `venue='binance' AND is_active=true`. Spegnendo le righe Binance quella query torna **zero righe** e scatta il fallback letterale `testnet_2`: la homepage avrebbe continuato a mostrare **255 ordini, 64 giorni, −$30,47 di denaro simulato** — sotto il badge nuovo che dice "denaro reale".

Questo è ciò che la pagina d'attesa ha tenuto chiuso mentre lavoravo, ed è il motivo per cui la sequenza del tuo §2 (velo *prima* del cutover) non era eleganza ma necessità.

---

## 3. Sei superfici, lo stesso difetto, in un giorno solo

La parte che vale come lezione più che come cronaca.

| Superficie | Difetto | Come è saltata fuori |
|---|---|---|
| Homepage | pin `venue=binance`, budget $600 cablato | lista fatta a mano |
| **Dashboard** | **pin mancato dalla mia lista** + `INITIAL_CAPITAL=600` | renderizzando la pagina, dopo un'ora di −$33,80 pubblici |
| **Libreria P&L** | copia **locale** che oscurava quella condivisa | il P&L pubblico diceva **−$118,01** |
| Scena ufficio | base $600 + un ciclo solo invece dell'era | **l'hai notata tu** dallo screenshot |
| `grid.html` | lista simboli cablata, mappa nomi su `/USDT` | il pulsante Save non si accendeva (l'ha visto Max) |
| Report serale | pin `venue=binance` in tre punti | un grafico piatto |

**La mia lista scritta a mano ne aveva mancato il 40%.** Quello che li ha trovati tutti è stato **guardare il prodotto renderizzato**, mai rileggere il sorgente. Due li ha visti Max prima di me.

C'era anche un promemoria lasciato apposta per questo giorno, in `commentary.py`: *"revisit for venue-awareness at the full-Kraken cutover"*, con file parcheggiato. **Ci siamo passati accanto lo stesso.** Un commento nel codice non è un allarme.

---

## 4. Il guasto silenzioso più costoso

`fetchLivePrices` rimappava i simboli con `.replace("USDT", "/USDT")`. Un simbolo `/USD` resta intatto: `"BTCUSD"` non combacia mai con la chiave `"BTC/USD"`.

**Binance quelle coppie le ha** — quindi nessun errore, nessun log, nessun sospetto. Il prezzo arrivava e veniva buttato. Le monete valutate **zero**, e il P&L pubblico avrebbe letto **−$118** invece di +$0,85: un numero perfettamente plausibile.

Esisteva in **tre copie**. Ora due, entrambe venue-aware: `/USD` va al ticker pubblico Kraken (dove le monete stanno davvero e dove verranno vendute — i due venue quotano 0,14% diversi, e il bot marca a Kraken), `/USDT` resta Binance per la pagina storica.

---

## 5. Fuori perimetro dichiarato: la sicurezza

Non era nel brief. È emersa mentre Max chiedeva l'editor dei parametri sulle monete Kraken.

Il database aveva politiche di **scrittura senza condizioni per il ruolo anonimo su 9 tabelle** — fra cui `bot_config`, che da stamattina governa $400 reali, e `sherpa_board_state`, che contiene l'interruttore d'emergenza. La chiave anonima è **pubblicata nel sorgente del sito**. La password dei pannelli è un controllo lato browser: nasconde l'interfaccia, non chiude la porta.

Non era prelevabile (chiave Kraken senza permesso di prelievo) ma **danneggiabile**: `buy_pct` a 0,01 svuota il conto per attrito allo 0,80% a operazione, senza che nessuno prelevi nulla.

Chiuse 8 tabelle su 9. Le modifiche passano ora da una funzione lato server che tiene la chiave vera, confronta il segreto a tempo costante, e **rifiuta anche i valori assurdi** — allocazione oltre il tetto, `sell_pct` sotto il costo di andata e ritorno, virgola sbagliata. Controlli che nel browser non varrebbero nulla perché chiunque li aggira.

Il segreto l'ha impostato Max direttamente su Supabase: **non è mai transitato in chat, io non lo conosco.** Il test "password sbagliata → 401" lo prova senza bisogno di conoscerlo.

---

## 6. `/history`, e perché vale più di un archivio

Max ha chiesto una pagina di riepilogo delle ere invece di semplici etichette. Ho recuperato l'era **paper** dal backup pre-reset (1.192 ordini, marzo-maggio) e ricalcolato tutte e tre le ere chiuse **con la formula di oggi**, perché le colonne fossero confrontabili.

Il pezzo che secondo me è il prodotto:

> L'era paper fu pubblicata a **+$69,05**. La stessa era, ricalcolata oggi, fa **+$47,57**.

Ventun dollari. Non perché sia cambiato il passato, ma perché il FIFO di allora aveva tre bug non ancora trovati e non sottraeva le commissioni con coerenza. **Pubblicati entrambi i numeri** (scelta di Max): un archivio che mostra solo i numeri vecchi è nostalgia, uno che mostra la correzione è un metodo.

E il dato che nessuna era da sola poteva mostrare: **30 ordini al giorno** sul paper a $0,0144 di commissione, **0,2 al giorno** su Kraken a $0,2702. La strategia fra quelle due righe non è cambiata; è cambiato il prezzo di sbagliare.

---

## 7. La tua auto-obiezione, misurata

Scrivevi: *"stiamo facendo il reveal nel momento peggiore per i numeri… se la prima settimana non produce un ciclo, il sito lo mostrerà."*

Aveva ragione, e adesso ha un numero. Oggi in vetrina: **+$0,87 di guadagno latente** contro **$0,94 di commissioni** pagate per costruire le posizioni. Il mercato ci ha dato ottantasette centesimi, il broker ne ha presi novantaquattro.

Non è un incidente ed è la storia più onesta che possiamo raccontare: **le commissioni sono il vincolo, non la strategia.** Rende l'esperimento XRP a prezzo fisso (maker 0,25% contro taker 0,80%) il lavoro col maggior effetto sui numeri fra tutti quelli in coda — a parità di tutto il resto, quella riga da −$0,07 diventerebbe +$0,58.

---

## 8. Cosa resta aperto

- 🔴 **La riconciliazione su Kraken non esiste.** È il controllo che prova che i numeri a database corrispondono agli ordini veri dell'exchange. Sul testnet era una formalità; sul denaro reale è l'unica cosa che separa "i conti tornano" da "crediamo che tornino". Scritto anche dentro `/admin`, dove lo si legge.
- 🟠 **Il database non sa distinguere il denaro reale.** Nessuna colonna `venue` su `trades`, e `mode` vale `live` per tutte e 319 le operazioni, testnet incluso. L'unico appiglio è la stringa del ciclo: una convenzione sui nomi, non un dato.
- 🟠 **Il backtest pubblico girato a fee dimezzata** (0,40% contro 0,80%): con denaro vero in campo quel materiale è fuorviante. Decisione editoriale, non l'ho toccato.
- 🟡 **`/tf` ha il Save spento** finché `trend_config` non passa dal portiere. Il TF è fermo, quindi non urge.
- 🟡 **Verifica T+24h su Sherpa** (8 agosto): a fine giornata stava già allargando i parametri di SOL.

Il **post di annuncio** è tuo e di Max — regola marketing, lui in italiano, tu traduci. Tono di riferimento: *"primo dollaro vero"*, la piccolezza come rigore, niente percentuali nel titolo.
