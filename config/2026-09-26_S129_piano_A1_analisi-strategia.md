# Piano A.1 — Analisi dei 2 mesi a denaro reale su Kraken

**Stato:** ✅ APPROVATO da Max il 2026-09-28 (S130), con D2 aggiunta e staking SOL in riga separata · **Scritto:** 2026-09-26, S129 · **Esecuzione:** S130, 2026-09-28
**Task:** [MASTER_TASK_LIST A.1](MASTER_TASK_LIST_2026-09-28.md) · **Innesco:** BTC a +11–13% sopra il prezzo medio il 23-set che non vende, poi vende al riavvio del 26-set a +7,7%.

> ⚠️ **Salto di sequenza (segnalato):** nell'ordine emendato da Max il 16-set A.1 stava nel blocco 3, dopo R.7 (automatismi Mac Mini) → R.1 → X.1. Max il 26-set la porta in testa. R.7 resta il lavoro successivo: il 26-set i bot sono rimasti fermi ~7 ore dopo l'aggiornamento di macOS, esattamente il caso che R.7 copre.

---

## 1. Le tre domande

1. **Cosa è successo davvero?** Quanto abbiamo guadagnato o perso, contando le commissioni, e come si confronta col semplice "compro e tengo".
2. **Quanto ci è costato il reset "zona morta" che non scattava?** (bug trovato il 26-set, PROJECT_STATE §5.) In quali giorni era bloccato e quali vendite abbiamo mancato.
   **Ipotesi di Max da verificare (26-set):** *soprattutto in regimi di paura o laterali, se il grid non ricalibra si perdono piccole vendite profittevoli.* Va controllata anche l'ipotesi opposta: nei rialzi forti la "scala" delle vendite (vendere solo sopra l'ultima vendita) potrebbe averci **protetto** dal vendere troppo presto. Il risultato conta solo diviso per regime.
3. **Esistevano strategie semplici che avrebbero reso di più?** Solo quelle dell'elenco del §4, fissato **prima** di guardare i risultati.

## 2. Cosa abbiamo in mano (verificato il 26-set)

| Dato | BTC/USD | SOL/USD |
|---|---|---|
| Operazioni reali | 25 (14 acquisti, 11 vendite); le 2 del 17-lug sono l'ordine di prova (`kraken_test`) | 39 (21 acquisti, 18 vendite) |
| Periodo | 22-lug → oggi | 7-ago → oggi |
| Guadagno realizzato (DB) | +$18,13 | +$15,53 |
| Commissioni pagate (DB) | $6,99 | $6,42 |
| Capitale | $100 dal 22-lug, $250 dal 7-ago (da confermare) | $150 dal 7-ago |

- **Registro modifiche parametri:** 636 righe dal 22-lug (634 di Sherpa, 2 manuali). Dice quali parametri erano in vigore in ogni momento: è la base per simulare "la strategia che abbiamo fatto girare davvero". **I cambi di capitale non ci sono**: vanno ricostruiti da PROJECT_STATE e dall'archivio.
- **Resoconto giornaliero:** 54 giorni.
- **Registro movimenti Kraken** (sola lettura): la verità su commissioni, depositi e staking SOL. Serve a controllare che il database dica il vero.
- **Prezzi:** il simulatore esistente (`scripts/backtest/`) scarica candele da 1 minuto da Binance. Kraken ne dà solo le ultime ~720, quindi 2 mesi al minuto non si possono avere. BTC/USDT su Binance e BTC/USD su Kraken differiscono di pochi dollari: va bene per simulare, ma lo misuriamo e lo scriviamo.
- **Periodi da marcare:** 17-lug ordine di prova · 22-lug avvio BTC $100 · 7-ago passaggio a $250 + SOL · **5→16 set blackout** (bot fermi 11 giorni) · 17-18 set blocchi Supabase (4 operazioni SOL ricostruite a mano) · 26-set ~7 ore ferme dopo l'aggiornamento macOS.
- **Accantonamento profitti:** BTC mette da parte il 30% di ogni guadagno. Nel confronto va trattato allo stesso modo in tutte le alternative.

**Dati in scadenza — ✅ SALVATI il 26-set** in `audits/a1_snapshot_20260926/` (fuori da git, **copia sia sul Mini sia sul MacBook**, 10 MB): proposte Sherpa dal 28-lug (716, **col regime di mercato di ogni momento**), punteggi Sentinel dal 27-ago (3.424; agosto prima del 27 era già perso), eventi e fotografie di stato degli ultimi 7 giorni, segnali NewsKeeper dal 28-giu, più una fotografia congelata di operazioni (64), registro modifiche (636), resoconti giornalieri, accantonamenti e config. **Conservazione portata da 30/60 a 120 giorni** (Max, 26-set): **attiva dal riavvio del 27-set** (nessun dato perso dopo la copia).

## 3. Come procediamo

**Passo 0 — Mettere al sicuro i dati. ✅ FATTO il 26-set** (vedi §2).

**Passo 0b — Misura diretta delle vendite mancate** (non serve il simulatore, quindi è la prova più solida). Per ogni ora dei 2 mesi, con moneta in mano: il prezzo era sopra la soglia "prezzo medio + margine" (vendibile col reset) ma sotto la soglia della scala (bloccato), per più delle ore di zona morta in vigore? Quelle sono le vendite che il bug ha impedito. Si contano e si dividono per regime, usando il regime registrato da Sherpa. È il primo numero per l'ipotesi di Max.

**Passo 1 — Ricostruire "il fatto davvero".** Operazione per operazione dal database, confrontata col registro movimenti Kraken. Per ogni giorno: liquidità + moneta posseduta × prezzo = valore del conto. Da qui esce la curva vera. Il controllo database contro Kraken è anche una prima prova della riconciliazione R.1.

**Passo 2 — Tarare il simulatore sulla realtà. È il passaggio che decide tutto.** Facciamo girare nel simulatore la nostra strategia con i parametri che Sherpa ha usato davvero, ora per ora, e controlliamo che rifaccia **le stesse operazioni** che abbiamo fatto. Se non ci riesce entro un margine ragionevole (stesse vendite, prezzi vicini), i confronti del passo 3 non valgono nulla: prima si capisce perché. Qui si misura anche il bug della zona morta: il simulatore deve riprodurlo per ricalcare la realtà.

**Passo 3 — Le alternative, a parità di capitale e commissioni (0,80%).** Tutte quelle del §4, sugli stessi prezzi e periodi.

**Passo 4 — Regimi diversi.** Si spezzano i 2 mesi in tratti per regime (paura, neutrale, avidità) e per andamento (salita, discesa, laterale). Poiché i 2 mesi reali sono quasi tutti rialzo, le stesse alternative girano anche su tratti storici di discesa e di laterale (dati Binance 2022-2024 del simulatore). Un'alternativa conta come "migliore" solo se vince in più tratti, non se vince una volta sul totale.

**Passo 5 — Report per CEO e Board**, più il materiale grezzo per un eventuale post (numeri onesti, anche se sono piccoli).

## 4. Le alternative (fissate ora, prima di vedere i risultati)

| # | Alternativa | Domanda a cui risponde |
|---|---|---|
| A | **Compra e tieni** dal primo acquisto (stesso capitale) | Il grid ha battuto il non fare nulla? |
| B | **Acquisti a intervalli fissi** (stessa cifra ogni N giorni, stesso totale) | Comprare "a rate" era meglio? |
| C | **Grid con parametri fissi**, senza Sherpa (i valori di partenza del 22-lug) | Sherpa ha aggiunto o tolto valore? |
| D | **La nostra strategia con la zona morta funzionante**, stessa tabella per regime | Quanto è costato il bug? |
| D2 | **Come D, ma il reset zona morta NON sposta il riferimento d'acquisto sopra la media** (resta all'ultimo acquisto vero). *Aggiunta S130, 28-set, prima di vedere i numeri*: il 27-set il reset l'ha portato a $84.751 (media $77.363), quindi il prossimo acquisto BTC è diventato "appena tocca la media" invece di $75.392 — e il reset si perde a ogni riavvio | Il reset deve toccare anche gli acquisti? |
| E | **Zona morta con tempi diversi per regime (idea di Max)**: 3 varianti fissate ora — tutto a 6h; tabella attuale ×3 (3–9h); 24h fisso | Il tempo giusto dipende dal regime? |
| F | **Commissione maker 0,25%** invece di 0,80% (stesse regole) | Quanto vale X.1 (ordini limite)? |
| G | **Margine di vendita più largo**: `sell_pct` +1 punto su tutti i valori di Sherpa | Vendiamo troppo presto? |

**Sulla zona morta per regime (E):** Sherpa già oggi la fa variare col regime, ma in una forchetta stretta: **1h** in paura, **2h** in paura estrema, neutrale e avidità, **3h** in avidità estrema ([board_parameter_rules.py:60-66](../bot/sherpa/board_parameter_rules.py#L60-L66)). Le 3 varianti di E servono a capire se la forchetta andrebbe allargata. Non cerchiamo "il numero perfetto": con 2 mesi di dati sarebbe un numero che funziona solo sul passato.

## 5. Cosa NON facciamo

- **Non tocchiamo i bot durante l'analisi**: niente parametri cambiati, niente riavvii.
- **Non correggiamo il bug della zona morta dentro A.1.** La correzione cambia come si trada a denaro reale ed è una decisione separata (Max, eventualmente col CEO). A.1 le dà il numero su cui decidere.
- **Non cerchiamo la combinazione migliore** provando centinaia di valori: con ~30 vendite troveremmo sempre qualcosa che "avrebbe funzionato" e che non funzionerà più (lezione S115).
- Il TF resta fuori: è spento dal 7-ago e non ha mai operato su Kraken.

## 6. Limiti da dichiarare nel report

- **Campione piccolo:** 29 vendite in tutto. I risultati sono indizi, non prove.
- **Due mesi = soprattutto un forte rialzo** (prezzi Kraken, chiusure giornaliere): BTC $66k il 22-lug → minimo $62k il 1-ago → massimo $87,4k il 21-set → $84k oggi. SOL $78 → minimo $70,5 → $123 (+55%). In un rialzo così il "compra e tieni" parte avvantaggiato: il grid vende a pezzi mentre il prezzo sale. **Il confronto A dirà quanto abbiamo lasciato sul tavolo, non se il grid è sbagliato.** Per giudicare il grid servono tratti di discesa e laterale: si usano i dati storici Binance già nel simulatore (2022-2024), con le stesse alternative. Nessun crollo vero nei 2 mesi, quindi nessuna conclusione su un crollo dai soli dati reali.
- **Buchi nei dati:** blackout 5→16 set, blocchi Supabase, ore di fermo. Si marcano e si escludono dai confronti, non si riempiono con ipotesi.
- **Il simulatore non è la realtà:** slittamenti di prezzo e tempi di esecuzione sono approssimati. Il passo 2 misura quanto.

## 7. Stima e prodotto finale

- **Passi 0–3:** una sessione piena (3–4 ore). **Passi 4–5:** mezza sessione in più.
- **Prodotto:** report `report_for_CEO/YYYY-MM-DD_SXX_RforCEO_analisi-strategia-A1.md` con curva vera, tabella delle alternative per regime, costo del bug zona morta e 2–3 raccomandazioni **con il livello di fiducia dichiarato**. Numeri grezzi in `audits/backtest/` (non versionati).

## 8. Da decidere con Max prima di partire

1. **Lo staking di SOL** (qualche centesimo a settimana) entra nel "compra e tieni"? ✅ **Deciso 28-set: sì, in una riga separata.**
2. **L'elenco del §4** va bene, o c'è un'alternativa che vuoi vedere? ✅ **Deciso 28-set: A–G + D2.** Elenco chiuso prima di guardare i numeri.
3. ~~Passo 0~~ — fatto il 26-set.
