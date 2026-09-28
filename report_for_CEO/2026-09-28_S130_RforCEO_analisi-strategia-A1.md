# A.1 — Analisi della strategia dopo 2 mesi a denaro reale

**Per:** CEO e Board · **Da:** CC (S130, 2026-09-28)
**Piano sorgente:** [`config/2026-09-26_S129_piano_A1_analisi-strategia.md`](../config/2026-09-26_S129_piano_A1_analisi-strategia.md) (scritto S129, approvato da Max il 28-set con D2 aggiunta e staking SOL in riga separata, commit `0567f3c`)
**Codice dell'analisi:** `scripts/backtest/a1_*.py` (commit `b386b1f`) · numeri grezzi in `audits/backtest/a1/` (non versionati)
**Nessun bot toccato durante l'analisi.** Nessun parametro cambiato, nessun riavvio.

---

## In breve

1. **Il fatto vero:** su $400 caricati il grid ha guadagnato **+$44,7 (+11,2%)** in 2 mesi (BTC +$30,3 / +12,1%, SOL +$14,4 / +9,6%), commissioni incluse, ai prezzi di oggi. Il semplice "compra e tieni" avrebbe fatto **+$157 (+39%)**. Era atteso: sono stati 2 mesi di forte rialzo (BTC +27%, SOL +62%) e un grid vende a pezzi mentre il prezzo sale. SOL ha tenuto investito in media solo il **26%** del capitale.
2. **Il simulatore rifà la realtà:** ripartendo dallo stato vero dopo ogni operazione, rifà **54 operazioni reali su 62 (87%)** allo stesso modo. Ma basta un'operazione diversa all'inizio (per pochi centesimi di scarto tra borse) per cambiare tutta la storia dopo. Quindi un confronto conta **solo se regge su molte varianti di prezzo e su molte date**, non su un singolo giro.
3. **Il bug della zona morta** ha bloccato almeno **9 vendite su BTC e 5 su SOL**, tutte in regime di avidità o neutrale. **Correggerlo e basta (D) avrebbe fatto peggio su BTC** (−$8, costante dal 19-ago) e circa nulla su SOL: nel rialzo la "scala" delle vendite ha tenuto in mano lotti comprati bassi. È l'ipotesi opposta che il piano chiedeva di verificare, e i dati la confermano.
4. **In paura il bug non esiste**, per come è costruita la tabella di Sherpa: in paura il bot aspetta 2h prima di ricalcolare il riferimento e la zona morta scatta dopo 1h, quindi arriva prima. L'ipotesi di Max ("si perdono vendite soprattutto in paura o laterale") non è confermata: in paura il bug non c'è, e nel laterale con indice neutrale correggerlo peggiora (§5).
5. **Sherpa aggiunge valore:** nei 2 mesi reali i parametri fissi di partenza (C) perdono in tutti i disturbi, −$12/−$19 rispetto alla strategia reale. Nello storico perdono in 6 finestre su 11 e vincono in 3 laterali.
6. **Sui tratti storici** (8 mesi BTC, 3 SOL, dal 2021 al 2026):
   - il grid batte il "compra e tieni" nel laterale e nei cali lenti (5 finestre BTC su 8) e perde nei rialzi: è l'ammortizzatore già visto in S113;
   - nessuna modifica della zona morta batte in modo solido il comportamento attuale;
   - la **commissione maker (X.1)** è l'unica alternativa che non perde mai in modo netto (vince in 6 finestre su 11);
   - ⚠️ in un crollo vero (SOL, novembre 2022, −57%) il grid finisce i contanti nella prima settimana e perde quasi quanto il compra e tieni.

---

## 1. Cosa è successo davvero (passo 1)

| | BTC/USD | SOL/USD | Totale |
|---|---|---|---|
| Capitale | $100 dal 22-lug, $250 dal 7-ago | $150 dal 7-ago | $400 |
| Guadagno vero (prezzi di oggi) | **+$30,31 (+12,1%)** | **+$14,41 (+9,6%)** | **+$44,72 (+11,2%)** |
| Calo massimo dal punto più alto | −$20,62 | −$6,00 | |
| Quota del capitale investita (media) | 72% | **26%** | |
| Compra e tieni, stesso capitale | +$66,71 (+26,7%), calo max −$26,94 | +$90,25 (+60,2%), calo max −$28,85 | +$156,96 |
| Acquisti a rate settimanali | +$39,42 | +$36,97 | +$76,39 |

- **I conti tornano:** la riconciliazione R.1 (27-set) ha confrontato ogni operazione a database con gli ordini su Kraken: 65 su 65, 0 differenze; il controllo notturno è attivo dal 28-set.
- **Staking SOL (riga separata, come deciso):** ricevuti 0,000948 SOL ≈ **$0,11** tenendo in media 0,40 SOL. Chi avesse tenuto 2,02 SOL per tutto il periodo ne avrebbe ricevuti circa **$0,57**. Irrilevante per il confronto.
- **Curva del guadagno (BTC+SOL, fine giornata):** 22-lug −$0,07 · 29-lug −$1,29 · 5-ago −$0,22 · 12-ago −$2,00 · 19-ago +$5,66 · 26-ago +$23,34 · 2-set +$19,43 · 9-set +$24,45 · 16-set +$17,05 · 23-set +$47,50 · oggi +$44,72.
- **Il perché del distacco dal "compra e tieni" è strutturale, non un errore:** SOL vende l'unico lotto a +2,5-3% e riparte da capo. In un rialzo del 62% ha tenuto in media tre quarti del capitale in contanti. È il comportamento per cui il grid è fatto (ammortizzatore, non motore: vedi backtest S113). Il confronto dice quanto abbiamo lasciato sul tavolo in un rialzo, non che il grid sia sbagliato.

**Regimi nei 2 mesi reali** (indice Fear & Greed usato da Sherpa): BTC 55% avidità, 27% paura, 6% neutrale, 4% paura estrema; SOL 71% avidità, 21% paura, 8% neutrale. Nessun crollo vero.

## 2. Il simulatore rifà la realtà? (passo 2 — il passaggio che decide tutto)

Il simulatore (`a1_sim.py`) copia il ciclo decisionale del bot live: parametri di Sherpa minuto per minuto dal registro modifiche (663 righe), commissione 0,80%, vendita del residuo col lotto, blocco perdita, attesa tra acquisti, fermi (blackout 5→16 set, riavvii del Mini del 26 e 27 set, blocchi Supabase del 17 set) e **riavvii ricostruiti come fa il bot** (al riavvio il riferimento torna all'ultimo acquisto vero: è così che la zona morta scattava solo ai riavvii).

**Prezzi.** Kraken dà solo le ultime ~720 candele al minuto. Scaricare lo storico completo delle sue compravendite (~7 milioni) avrebbe usato lo stesso indirizzo internet dei bot per 2-3 ore, col rischio di togliere richieste al denaro vero: **non fatto**. Si usano due fonti indipendenti:
- Binance BTC/USDT, SOL/USDT: i nostri eseguiti Kraken stanno in mediana **−0,06/−0,09%** sotto, con scarto medio ±0,14%;
- Coinbase BTC-USD, SOL-USD: mediana **−0,02/−0,04%**, scarto medio ±0,13%. È la fonte principale di questo report.

**Prova ancorata** (si riparte dallo stato vero dopo ogni operazione reale e si guarda la prima operazione simulata):

| | Coinbase | Binance |
|---|---|---|
| BTC | 18/23 | 18/23 |
| SOL | 36/39 | 33/39 |
| **Totale** | **54/62 (87%)** | 51/62 (82%) |

Le differenze controllate nei log sono tutte **soglie sfiorate per pochi centesimi**. Esempio: il 19-ago la soglia d'acquisto SOL era $81,06, Binance è sceso a $81,02, Kraken no. Oppure riferimenti ricalcolati ogni 45 minuti a un prezzo leggermente diverso. Nessuna regola sbagliata trovata. Una sola correzione: un fermo che finiva un minuto troppo tardi.

**Sul totale:** la copia della strategia reale fa BTC +$29,2 contro +$30,3 veri; SOL +$22,2 contro +$14,4 veri. Su SOL il simulatore non ricompra in cima il 25-set, mentre il bot vero sì: sono 4 lotti a $118-121, oggi sotto costo.

**Il limite che conta:** lo stesso simulatore, con un disturbo di prezzo di appena ±0,07%, dà per BTC risultati tra **+$7 e +$29** (Binance; su Coinbase tra +$23 e +$29). Il grid è sensibile all'ordine delle operazioni. Per questo:
- **ogni variante gira su 20 disturbi**, sempre confrontata con la strategia reale sullo stesso disturbo;
- **si guarda la differenza giorno per giorno**, non solo alla data di oggi;
- **"migliore" vuol dire:** vince in almeno ~90% dei disturbi **e** per la maggior parte dei giorni.

## 3. Il bug della zona morta: quanto è costato davvero

**Misura diretta, senza simulatore (passo 0b).** Momenti in cui il bot era bloccato dalla scala e una zona morta funzionante avrebbe venduto, al massimo uno per intervallo tra due operazioni vere (stesso risultato su Coinbase e su Binance):

| | Vendite mancate (almeno) | Guadagno del lotto in quel momento | Regime |
|---|---|---|---|
| BTC | 9 | ~$15,4 | 7 avidità, 2 neutrale |
| SOL | 5 (+2 in cui il bot vero ha venduto comunque entro 5 minuti) | ~$5,2 | tutte avidità |

Non sono soldi persi. Diverse volte il bot vero ha venduto dopo, e più in alto: il 19-ago a $70.937 invece di $67.898, il 18-set a $84.381 invece di $79.250. Altre volte il prezzo è sceso: il 21-set mancata a $86.775 (+12% sulla media), vendita vera solo il 26-set a $84.003.

**Effetto netto (simulazione, D contro la strategia reale):**

| | 20 disturbi, Binance | 20 disturbi, Coinbase | Giorno per giorno (ultimi 30) |
|---|---|---|---|
| BTC | −$7,8, meglio solo nel 10% | −$6,5, meglio nello 0% | sopra la reale **0 giorni su 30** |
| SOL | +$2,3, meglio nel 95% | +$5,2, meglio nel 95% | sopra la reale 11 giorni su 30 → **nel rumore** |

**Perché su BTC fa peggio.** Con la zona morta funzionante BTC vende i lotti comprati a $76.000 già a +3-5%. Poi il 21-set esce del tutto nel rialzo, rientra a mercato a ~$85.400 e compra in discesa. Chiude con una posizione pagata in media ~$85.000, contro i lotti da $77.000 della strategia reale. **Nel rialzo la scala ha protetto.**

**D2** (il reset non tocca il riferimento d'acquisto, il punto sollevato oggi su BTC): **risultati uguali a D** su tutte e due le monete. Nei 2 mesi reali la scelta sul punto 2 non ha impatto economico misurabile. Nello storico c'è un indizio a favore di D2 nel crollo BTC 2022 (§5).

## 4. Le alternative (passo 3)

Ogni cella: differenza mediana rispetto alla strategia reale (BASE) · % dei 20 disturbi in cui la batte. In grassetto quando vince in almeno il 90% dei disturbi. "Giorni sopra" = giorni, negli ultimi 30, in cui la variante vale più di BASE (Coinbase, prezzi non disturbati).

| Variante | BTC Binance | BTC Coinbase | BTC giorni sopra | SOL Binance | SOL Coinbase | SOL giorni sopra |
|---|---|---|---|---|---|---|
| **BASE** (guadagno mediano) | +$26,2 | +$27,2 | — | +$21,5 | +$20,4 | — |
| A compra e tieni | **+$39,8 · 100%** | **+$39,6 · 100%** | | **+$67,8 · 100%** | **+$69,7 · 100%** | |
| B rate settimanali | **+$12,5 · 100%** | **+$12,2 · 100%** | | **+$14,7 · 100%** | **+$16,6 · 100%** | |
| C parametri fissi | −$19,0 · 0% | −$19,8 · 0% | | −$12,3 · 0% | −$10,5 · 0% | |
| D zona morta corretta | −$7,8 · 10% | −$6,5 · 0% | 0/30 | **+$2,3 · 95%** | **+$5,2 · 95%** | 11/30 |
| D2 = D + riferimento fermo | −$7,8 · 10% | −$6,5 · 0% | 0/30 | **+$2,4 · 95%** | **+$4,6 · 90%** | 11/30 |
| E1 zona morta 6h | −$8,5 · 10% | −$10,0 · 0% | 0/30 | **+$3,5 · 95%** | **+$5,6 · 90%** | 11/30 |
| E2 tabella Sherpa ×3 | −$8,5 · 10% | −$10,0 · 0% | 0/30 | **+$3,5 · 95%** | **+$5,6 · 90%** | 11/30 |
| E3 zona morta 24h | −$1,1 · 35% | −$1,7 · 25% | 4/30 | **+$3,2 · 100%** | **+$4,2 · 95%** | 29/30 |
| F commissione 0,25% | −$10,4 · 20% | −$9,0 · 5% | 1/30 | +$0,7 · 60% | +$4,2 · 80% | 13/30 |
| G vendita +1 punto | +$1,6 · 70% | +$1,0 · 85% | 2/30 | −$0,3 · 45% | +$0,7 · 55% | 20/30 |

E1 ed E2 coincidono perché nei 2 mesi reali il regime è stato quasi sempre avidità o neutrale, dove le due varianti usano entrambe 6 ore.

Lettura:
- **A e B battono sempre il grid** in questo rialzo. È la domanda "quanto abbiamo lasciato sul tavolo": ~$40 su BTC e ~$68-70 su SOL rispetto al compra e tieni.
- **C (niente Sherpa) perde in tutti i disturbi** nei 2 mesi reali → Sherpa ha aggiunto valore.
- **D, D2, E1, E2 (zona morta corretta a 2-6h):** peggio su BTC. Su SOL vincono alla data di oggi ma stanno sopra la strategia reale solo 11 giorni su 30: nel rumore.
- **E3 (zona morta a 24h):** su BTC circa pari alla strategia reale; su SOL meglio (+$3-4, sopra la reale 29 giorni su 30). Nei 2 mesi reali è la sola variante della zona morta che non danneggia nessuna delle due monete, ma nello storico perde $14 nel crollo BTC 2022 (§5).
- **F (commissione maker 0,25%)** su BTC fa *peggio*: con commissioni più basse le soglie di vendita si abbassano, il bot vende prima nel rialzo e ricompra più in alto (stessa dinamica di D). In un rialzo, meno commissioni = più giri = peggio. Il valore di X.1 va letto nel laterale → §5.
- **G (margine di vendita +1 punto):** nel rumore su entrambe.

## 5. Regimi diversi: discesa, laterale, salita (passo 4)

Non esiste uno Sherpa storico. I parametri sono ricostruiti dalle due tabelle di Sherpa col regime Fear & Greed di ogni giorno: è la stessa fonte che Sentinel usa oggi (vedi Decisions). 11 finestre di un mese, capitale come oggi (BTC $250, SOL $150), 10 disturbi di prezzo ciascuna, nessun fermo.

**La nostra strategia contro le alternative passive:**

| Finestra | Prezzo | Regimi (F&G) | Compra e tieni | Rate settimanali | Grid (nostra strategia) |
|---|---|---|---|---|---|
| BTC giu 2022 | −37% | 100% paura estrema | −$94,6 | −$55,8 | **−$60,1** |
| BTC feb 2023 | 0% | 93% neutrale | −$1,9 | −$2,9 | **+$11,6** |
| BTC apr 2023 | +3% | 67% avidità | +$4,6 | +$4,6 | **+$15,5** |
| BTC lug 2023 | −4% | 84% neutrale | −$12,1 | −$10,3 | **−$5,9** |
| BTC ago 2023 | −11% | 65% neutrale, 35% paura | −$29,8 | −$23,7 | **−$13,2** |
| BTC set 2023 | +4% | 73% neutrale, 27% paura | **+$7,9** | +$4,1 | +$2,9 |
| BTC set 2024 | +7% | 43% paura, 37% neutrale | +$16,4 | **+$16,5** | +$7,8 |
| BTC nov 2024 | +37% | 60% avidità, 40% av. estrema | **+$90,1** | +$42,9 | +$51,8 |
| SOL nov 2022 | −57% | paura / paura estrema | −$85,2 | **−$33,7** | −$80,2 |
| SOL apr 2026 | 0% | paura / paura estrema | −$1,3 | −$3,9 | **−$0,2** |
| SOL feb 2021 | +208% | 68% avidità estrema | **+$308,4** | +$139,8 | +$112,8 |

**Le varianti contro la nostra strategia** (differenza mediana $ · % dei disturbi in cui vince; grassetto = vince in almeno il 90%):

| Finestra | C | D | D2 | E1 | E2 | E3 | F | G |
|---|---|---|---|---|---|---|---|---|
| BTC giu 2022 | −19,1 · 0% | = | **+11,6 · 90%** | +7,2 · 60% | +7,2 · 60% | −14,2 · 0% | **+14,1 · 100%** | −13,1 · 0% |
| BTC feb 2023 | −10,9 · 0% | −7,7 · 0% | −8,2 · 0% | −10,3 · 0% | −10,3 · 0% | −5,3 · 0% | **+4,6 · 100%** | −0,8 · 30% |
| BTC apr 2023 | −14,3 · 0% | −10,6 · 0% | −10,6 · 0% | −6,3 · 10% | −6,3 · 10% | −2,6 · 20% | −0,6 · 30% | −2,1 · 10% |
| BTC lug 2023 | **+3,1 · 100%** | **+1,6 · 100%** | +0,5 · 70% | +0,9 · 70% | +0,9 · 70% | **+1,9 · 90%** | **+5,9 · 100%** | −1,2 · 40% |
| BTC ago 2023 | **+3,7 · 100%** | +1,4 · 50% | +2,0 · 60% | **+2,7 · 90%** | **+2,7 · 90%** | −2,0 · 30% | **+4,1 · 90%** | −2,0 · 10% |
| BTC set 2023 | −1,2 · 30% | +0,4 · 70% | −0,2 · 20% | 0,0 · 30% | 0,0 · 30% | −0,1 · 40% | **+1,5 · 90%** | **+1,3 · 100%** |
| BTC set 2024 | −4,1 · 0% | −2,8 · 0% | −3,1 · 0% | −3,6 · 0% | −3,5 · 0% | −3,5 · 10% | +1,2 · 70% | −0,8 · 40% |
| BTC nov 2024 | −38,7 · 0% | −18,2 · 0% | −19,6 · 0% | −13,6 · 0% | −19,4 · 0% | −7,1 · 0% | −1,1 · 50% | −1,7 · 20% |
| SOL nov 2022 | 0,0 · 50% | = | = | **+0,2 · 100%** | **+0,2 · 100%** | **+0,2 · 100%** | **+4,7 · 100%** | **+0,6 · 100%** |
| SOL apr 2026 | **+1,9 · 100%** | = | = | 0,0 · 20% | 0,0 · 20% | 0,0 · 50% | −0,1 · 40% | **+0,3 · 90%** |
| SOL feb 2021 | −78,4 · 0% | −13,3 · 30% | −20,2 · 10% | −7,1 · 20% | −25,6 · 10% | −11,1 · 40% | +6,3 · 70% | −11,3 · 10% |

"=" vuol dire identica alla nostra strategia: in paura il bug non c'è, quindi correggerlo non cambia nulla.

**Conteggio** (finestre in cui la variante vince / perde in modo netto, su 11):

| C | D | D2 | E1 | E2 | E3 | F | G |
|---|---|---|---|---|---|---|---|
| 3 / 6 | 1 / 4 | 1 / 5 | 2 / 4 | 2 / 5 | 2 / 4 | **6 / 0** | 3 / 4 |

**Lettura:**
- **Grid contro compra e tieni:** il grid vince nel laterale e nei cali lenti (BTC feb, apr, lug, ago 2023) e perde meno nel crollo BTC 2022 (−24% contro −38%). Il compra e tieni vince nei rialzi. Conferma S113: ammortizzatore, non motore.
- **⚠️ Crollo SOL novembre 2022 (FTX, −57%):**
  - il grid perde −$80 (−53%), quasi quanto il compra e tieni; le rate settimanali −$34;
  - il grid spende tutti i contanti entro l'8-nov, al primo −20% (resta $1,2), poi subisce il resto fino a −66%;
  - il blocco perdita si accende e si spegne da solo ogni 6 ore (sblocco automatico in paura) e tra uno sblocco e l'altro lascia passare acquisti.
- **Zona morta corretta (D)** è identica alla nostra strategia in paura e peggiora nei mesi neutrali e di avidità: feb 2023 −$7,7, apr −$10,6, nov 2024 −$18,2, SOL feb 2021 −$13,3. Migliora solo di poco nel calo lento di luglio 2023 (+$1,6). **Anche nel laterale con indice neutrale (feb 2023) peggiora: l'ipotesi di Max non è confermata.** Con un cronometro tutto suo la zona morta scatta dopo 2 ore e vende lotti che la scala avrebbe venduto più in alto; poi il bot ricompra e paga di nuovo lo 0,8% in entrata e in uscita.
- **D2** nel crollo BTC 2022 fa +$11,6 (90%). Non spostare il riferimento d'acquisto sopra la media fa comprare meno durante la discesa. Altrove si comporta come D. Un solo tratto: indizio, non prova.
- **Zona morta per regime (E1-E3):** nessuna regge. E3 perde $14 nel crollo 2022; E1 ed E2 aiutano solo ad agosto 2023.
- **Commissione maker (F):** vince in modo netto in 6 finestre su 11 e non perde mai in modo netto. Guadagna soprattutto in discesa e nel laterale (+$4-14 su $250); nei rialzi forti è circa pari. Nel rialzo reale su BTC aveva fatto peggio: commissioni più basse abbassano le soglie di vendita, quindi più giri.
- **Parametri fissi (C)** perdono in 6 finestre nette e vincono in 3 laterali: la tabella di Sherpa aiuta soprattutto nei trend.

## 6. Raccomandazioni (con livello di fiducia)

1. **Non correggere il bug della zona morta nel modo diretto (D). Fiducia: alta.**
   - 2 mesi reali: BTC peggio nel 90-100% dei disturbi, in modo costante dal 19-ago; SOL nel rumore giorno per giorno.
   - Storico: D perde in modo netto in 4 finestre e vince in 1.
   - Il bug ha prodotto per caso una regola sensata: in avidità e neutrale la scala non si azzera (si aspetta il gradino successivo); in paura la zona morta funziona come progettata.
2. **Rendere questo comportamento una scelta esplicita invece di un effetto collaterale. Fiducia: media, da provare prima.**
   - Oggi dipende dal cronometro condiviso e dai riavvii: il 26 e 27-set BTC ha venduto solo perché il Mini si era riavviato.
   - Proposta: zona morta spenta (o molto lunga) in avidità e neutrale, attiva in paura. Così un riavvio non cambia più cosa fa il bot.
   - **Non era nell'elenco fissato prima di vedere i numeri:** va provata con gli stessi script (mezz'ora) prima di decidere, non adottata sulla base di questo report.
3. **Il punto sollevato il 28-set (il reset porta il riferimento d'acquisto sopra la media): se si tocca la zona morta, adottare la regola D2. Fiducia: bassa-media.**
   - Nessun effetto nei 2 mesi reali; +$11,6 nel crollo BTC 2022 (un solo tratto).
   - È coerente con la regola S70 già esistente ("non ricalcolare il riferimento sopra la media") e toglie la dipendenza dai riavvii.
4. **Zona morta variabile col regime (idea di Max, E1-E3): no. Fiducia: media.** Nessuna delle 3 varianti fissate prima regge nei regimi diversi. E3 aiuta SOL nei 2 mesi reali ma perde $14 nel crollo 2022.
5. **X.1, ordini limite a commissione maker: procedere (è già il prossimo passo della sequenza). Fiducia: media-alta.**
   - È l'unica alternativa che non perde mai in modo netto nello storico: vince in 6 finestre su 11, soprattutto in discesa e laterale.
   - Da verificare dentro X.1: con commissione più bassa le soglie di vendita si stringono da sole e nei rialzi forti il bot fa più giri (su BTC reale −$9). Probabilmente il margine di vendita va riallineato insieme alla commissione.
6. **Sherpa resta. Fiducia: media-alta.** I parametri fissi perdono in tutti i disturbi dei 2 mesi reali e in 6 finestre storiche nette, con Sherpa ricostruito.
7. **Margine di vendita più largo (G): no. Fiducia: media.** Perde più spesso di quanto vinca.
8. **Per il Board, questioni di mandato, non di taratura:**
   - **(a) Il rialzo lasciato sul tavolo.** SOL ha tenuto investito in media il 26% del capitale: ~$76 in meno del compra e tieni in 2 mesi. Tenere una quota fissa e far girare il grid sopra è una scelta di mandato **non provata qui** (non era nell'elenco).
   - **(b) Il crollo vero.** In un crollo di settimane il grid non protegge (SOL novembre 2022: −53%, quasi come il compra e tieni). Finisce i contanti al primo −20% e il blocco perdita si riapre da solo ogni 6-12 ore. Va deciso se in paura estrema il blocco debba restare chiuso più a lungo, o se la dimensione dei lotti debba scendere. Fiducia media: parametri ricostruiti, un solo crollo nello storico.

## 7. Limiti da tenere presenti

- **Campione piccolo:** 29 vendite reali. I risultati sono indizi, non prove.
- **Due mesi quasi tutti rialzo**, nessun crollo. Le conclusioni su discesa e laterale vengono dallo storico (§5), con parametri Sherpa **ricostruiti** dalla tabella, non registrati.
- **Prezzi non Kraken:** scarto medio ±0,13-0,14% sugli eseguiti. Coperto con due fonti e 20 disturbi, non eliminato.
- **Sensibilità alla data:** i risultati del grid cambiano di diversi dollari a seconda del giorno in cui si fanno i conti (vedi SOL-D). Per questo il criterio "giorno per giorno".
- **Buchi nei dati:** blackout 5→16 set e ore di fermo. Nella simulazione sono fermi anche per le alternative; nell'attribuzione per regime sono conteggiati a parte ("fermo").

## 8. Materiale per un post

Numeri onesti e piccoli, già verificati:
- "+11% in 2 mesi a denaro reale, contro +39% di chi avesse solo comprato e tenuto";
- "su BTC il nostro bug ci ha fatto guadagnare";
- "SOL ha tenuto investito in media un quarto del capitale".

La storia vera è il metodo: controllare che il simulatore rifaccia le operazioni vere prima di credergli, e scoprire che basta un centesimo per cambiare tutto.

---

## Decisions

DECISIONE: niente scaricamento dello storico compravendite Kraken; prezzi Binance + Coinbase.
RAZIONALE: stesso indirizzo internet dei bot (verificato) → rischio di togliere richieste ai bot a denaro reale per 2-3 ore.
ALTERNATIVE CONSIDERATE: scaricare a velocità ridotta (~7 ore, di notte); solo Binance.
FALLBACK SE SBAGLIATA: lo scaricamento si può fare di notte a velocità ridotta e rifare i conti con gli stessi script (`a1_data.prices` accetta una nuova fonte).

DECISIONE: criterio di "migliore" = confronto appaiato su 20 disturbi di prezzo + controllo giorno per giorno.
RAZIONALE: un singolo giro è dominato dal caso (BTC da +$7 a +$29 con ±0,07% di disturbo); il piano chiedeva di non premiare chi vince una volta.
ALTERNATIVE CONSIDERATE: un solo giro per fonte; spostare la data di partenza.
FALLBACK SE SBAGLIATA: i CSV per disturbo sono in `audits/backtest/a1/` e si possono rileggere con un criterio diverso.

DECISIONE: nello storico i parametri Sherpa sono ricostruiti dalle sue tabelle col regime Fear & Greed del giorno, con cambi istantanei.
RAZIONALE: non esiste uno Sherpa storico; è la migliore approssimazione di "la nostra strategia in un altro regime".
ALTERNATIVE CONSIDERATE: parametri di oggi fissi per tutti i regimi (ignorerebbe proprio la differenza tra paura e avidità).
FALLBACK SE SBAGLIATA: `a1_history.py` accetta tabelle diverse.

## Come rifare i conti

```
cd scripts/backtest
python a1_missed.py coinbase                 # passo 0b
python a1_calib.py <log BTC utc> <log SOL utc> coinbase   # passo 2 (log grid del Mini con data UTC)
python a1_run.py coinbase                    # passo 3, un giro
python a1_robust.py coinbase 20              # passo 3, 20 disturbi
python a1_history.py 10                      # passo 4
```
