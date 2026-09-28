# A.1 — Addendum: verifiche Q2-Q5b del Board

**Per:** CEO e Board · **Da:** CC (S132, 2026-09-28)
**Brief sorgente:** [`config/2026-09-28_S131a_brief_zona-morta-regola.md`](../config/2026-09-28_S131a_brief_zona-morta-regola.md), Parte B
**Report di riferimento:** [`2026-09-28_S130_RforCEO_analisi-strategia-A1.md`](2026-09-28_S130_RforCEO_analisi-strategia-A1.md). Stesse convenzioni, stessi script, stessi 20 disturbi, stesse due fonti di prezzo (Coinbase principale, Binance di controllo).
**Codice:** `scripts/backtest/a1_*.py`. Variante F' aggiunta in `9949fca`; variante R (Q1, Parte A) in `a2a8028`. Numeri grezzi in `audits/backtest/a1/s131a_*.csv` (non versionati).
**Nessun bot toccato.** Q1, il gate della Parte A, è nel report [`zona-morta-regola`](2026-09-28_S132_RforCEO_zona-morta-regola.md).

---

## In breve

1. **Commissioni pagate dal 22-lug (registro Kraken): $13,42**, cioè BTC $6,84 e SOL $6,58, esattamente lo 0,800% di $1.677 di volume. Valgono il **23% del guadagno lordo**: senza commissioni i $44,7 sarebbero stati $58,1.
2. **Il divario dal "compra e tieni" è quasi tutto esposizione**, come stimava il CEO. SOL −$75,8 = −$66,4 esposizione, −$2,9 tempismo, −$6,6 commissioni. BTC −$36,4 = −$18,5 esposizione, −$11,1 tempismo, −$6,8 commissioni.
3. **F' (commissione 0,25% con soglie di vendita invariate) è il numero pulito per X.1.** Nello storico migliora il risultato in **tutte le 11 finestre**, in 6 nel 90% dei disturbi o più, e non perde mai in modo netto. Su SOL nei 2 mesi reali vince (+$5,2 / +$4,7). Su BTC nei 2 mesi reali perde (−$12,1 Coinbase in tutti i disturbi, +$0,5 Binance a metà), ma la causa è il percorso e non la commissione (§3).
4. **L'effetto negativo di F in A.1 veniva dalle soglie più strette, non dalla commissione.** F perde in 3 finestre storiche, F' in nessuna.
5. **SOL, rientro dopo vendita totale (dato di partenza per A.2):** 9 rientri con un solo lotto. Il secondo lotto è arrivato solo 3 volte (mediana 5,1 ore); le altre 6 volte SOL ha rivenduto prima di comprarlo.
6. **Il criterio "giorno per giorno" su tutta la finestra conferma le conclusioni di A.1.** La finestra di 30 giorni non aveva un motivo di metodo.

---

## Q2 — Commissioni totali pagate (registro Kraken, dal 22-lug)

| | BTC/USD | SOL/USD | Totale |
|---|---|---|---|
| Ordini | 24 (13 acquisti, 11 vendite) | 40 (22 acquisti, 18 vendite) | 64 |
| Comprato / venduto | $481,44 / $374,00 | $440,28 / $381,72 | |
| Volume | $855,44 | $822,00 | **$1.677,44** |
| **Commissioni** | **$6,84** (0,800%) | **$6,58** (0,800%) | **$13,42** |
| Guadagno netto (A.1, prezzi del 28-set) | +$30,31 | +$14,41 | +$44,72 |
| Guadagno lordo (netto + commissioni) | +$37,15 | +$20,99 | +$58,14 |
| Quota del lordo mangiata dalle commissioni | 18% | 31% | **23%** |

- La fonte è il registro degli ordini di Kraken, non il database. La stessa riconciliazione R.1 (65 ordini su 65) conferma il database.
- **Fuori dal conteggio:** l'ordine di prova di luglio su BTC (1 acquisto e 1 vendita da $25), che ha pagato $0,41 di commissioni prima del ciclo `kraken_2b`.
- Il piano del 26-set stimava $6,99 + $6,42 dal database; il registro dà $6,84 + $6,58.
- **Lettura:** SOL paga le commissioni quasi come BTC con metà del guadagno, perché fa più giri (40 ordini contro 24) con un volume simile. Sul margine di SOL la commissione pesa quasi un terzo: è il motivo per cui X.1 conta di più su SOL.

## Q3 — F': la sola commissione più bassa

F' = commissione 0,25% (listino maker Kraken) con **soglie di vendita calcolate come se la commissione fosse ancora 0,80%**. F in A.1 cambiava invece due cose insieme: commissione più bassa **e** soglie più strette. F' isola il puro effetto commissione.

**2 mesi reali** (differenza mediana contro la strategia attuale; tra parentesi quante volte vince su 20 disturbi):

| | F (A.1) | **F'** |
|---|---|---|
| BTC, Coinbase | −$9,0 (1/20) | **−$12,1 (0/20)** |
| BTC, Binance | −$10,4 (4/20) | +$0,5 (11/20) |
| SOL, Coinbase | +$4,2 (16/20) | **+$5,2 (19/20)** |
| SOL, Binance | +$0,7 (12/20) | **+$4,7 (18/20)** |

**Storico** (10 disturbi per finestra; stesse 11 finestre di A.1):

| Finestra | F (A.1) | **F'** |
|---|---|---|
| BTC crollo giugno 2022 | +$14,1 (10/10) | **+$6,7 (10/10)** |
| BTC febbraio 2023 | +$4,6 (10/10) | +$3,1 (8/10) |
| BTC aprile 2023 | −$0,6 (3/10) | **+$4,5 (7/10)** |
| BTC luglio 2023 | +$5,9 (10/10) | +$2,6 (8/10) |
| BTC agosto 2023, laterale | +$4,1 (9/10) | **+$1,3 (10/10)** |
| BTC settembre 2023, laterale | +$1,5 (9/10) | +$1,3 (9/10) |
| BTC settembre 2024 | +$1,2 (7/10) | **+$4,0 (10/10)** |
| BTC rialzo novembre 2024 | −$1,1 (5/10) | +$9,0 (6/10) |
| SOL crollo novembre 2022 | +$4,7 (10/10) | **+$1,1 (10/10)** |
| SOL laterale aprile 2026 | −$0,1 (4/10) | **+$1,2 (10/10)** |
| SOL rialzo febbraio 2021 | +$6,3 (7/10) | +$4,9 (7/10) |

- **F' è positiva in tutte le 11 finestre** (mediana) e vince nel 90% dei disturbi o più in 6. Non ha nessuna perdita netta.
- F perde in 3 finestre (aprile 2023, novembre 2024, SOL laterale 2026), F' in nessuna. **Le perdite di F venivano dalle soglie più strette:** si vende troppo presto, e nel rialzo la scala perde valore.
- F' guadagna meno di F nei crolli e nei laterali, dove vendere presto aiuta, ma non perde mai: è il prezzo del non stringere le soglie.

**Perché BTC nei 2 mesi reali va in senso opposto.** Ho seguito la simulazione senza disturbi (Coinbase: F' −$14,1 a fine periodo, sopra la strategia attuale 52 giorni su 69):
- F' resta sopra fino al 17-set (+$3,0);
- il **17-set** la strategia attuale compra un lotto a $76.072 e F' no, per un percorso già diverso da settimane (basta un centesimo, vedi A.1 §2);
- il **21-set** F' vende l'ultimo lotto al massimo ($85.991) e, senza più lotti in mano, ricompra subito a mercato a $86.133. Poi compra altri 5 lotti in discesa fino a $83.627;
- a fine periodo (prezzo $83.267) F' tiene 0,0024 BTC con costo medio $84.535, in perdita. La strategia attuale tiene 0,0009 BTC con costo medio $77.142, in guadagno.

F' ha pagato $5,7 di commissioni in meno, ma il percorso diverso (il lotto mancato del 17-set e il rientro in cima del 21-set) ne è costato circa $20. È il meccanismo del "rientro dopo vendita totale", cioè il tema di A.2 (Q5), non un effetto della commissione. Con prezzi Binance lo stesso episodio capita solo in metà dei disturbi: da qui il risultato contraddittorio tra le due fonti.

**Per X.2:** la stima pulita è quella storica. Una commissione dello 0,25%, a parità di tutto il resto, vale **da +$1,1 a +$9,0 per finestra** (mediana), mai negativa.

## Q4 — Scomposizione del divario dal "compra e tieni"

Metodo: **esposizione** = quanto avrebbe reso tenere investita in modo costante la quota media effettiva (BTC 72%, SOL 26%); **commissioni** = Q2; **tempismo** = il resto, cioè quando il grid ha comprato e venduto rispetto a un'esposizione costante.

| | Grid | Compra e tieni | Divario | Esposizione | Tempismo | Commissioni |
|---|---|---|---|---|---|---|
| BTC | +$30,31 | +$66,71 | **−$36,39** | −$18,46 | −$11,09 | −$6,84 |
| SOL | +$14,41 | +$90,25 | **−$75,83** | −$66,35 | −$2,91 | −$6,58 |
| Stima CEO | | | | BTC ≈ −19, SOL ≈ −67 | BTC ≈ −18, SOL ≈ −9 (con le commissioni) | |

La stima del CEO è confermata: tempismo + commissioni vale BTC −$17,9 e SOL −$9,5. **Su SOL il divario è quasi tutto esposizione:** ha tenuto investito in media un quarto del capitale durante un rialzo del 62%. Il tempismo di SOL è quasi neutro (−$2,9): il problema non è quando compra e vende, ma quanto poco tiene investito. Su BTC tempismo e commissioni pesano quanto l'esposizione.

**Da mettere in "In breve" di A.1:** il divario dal compra e tieni è una scelta di quanto capitale tenere investito, non una taratura sbagliata delle soglie.

## Q5 — SOL: rientro dopo vendita totale

| Rientro | Prezzo | Ore dalla vendita | Passo d'acquisto (Sherpa) | Poi | Ore |
|---|---|---|---|---|---|
| 07-ago 10:55 | $73,48 | primo acquisto | 2,25% | rivenduto prima del 2° lotto | 27,7 |
| 08-ago 16:35 | $76,22 | 2,0 | 2,67% | rivenduto prima del 2° | 262,3 |
| 19-ago 15:50 | $81,94 | 1,0 | 1,68% | rivenduto prima del 2° | 5,2 |
| 19-ago 22:05 | $85,97 | 1,0 | 1,26% | **2° lotto** | 5,1 |
| 16-set 19:23 | $97,43 | 1,0 | 1,68% | rivenduto prima del 2° | 19,0 |
| 17-set 15:36 | $100,90 | 1,2 | 1,66% | rivenduto prima del 2° | 12,7 |
| 18-set 05:20 | $105,72 | 1,0 | 1,71% | rivenduto prima del 2° | 9,5 |
| 18-set 16:07 | $111,36 | 1,3 | 1,71% | **2° lotto** | 34,6 |
| 25-set 11:52 | $121,00 | 0,8 | 1,15% | **2° lotto** | 0,4 |

- **9 rientri con un solo lotto.** Il secondo lotto è arrivato 3 volte (dopo 5,1 ore di mediana). Nelle altre 6 SOL ha rivenduto l'unico lotto prima di comprare il secondo.
- Rientro tipico: 1 ora dopo la vendita, cioè il ricalcolo idle (0,75-1h in avidità e neutrale). Il passo d'acquisto in vigore andava da 1,15% a 2,67%.
- **Lettura per A.2:** in un rialzo SOL fa "un lotto, vendi, ricompra un'ora dopo". Per questo ha tenuto investito solo il 26% (Q4). Qualsiasi proposta A.2 cambia proprio questo numero, e con esso il comportamento nei crolli (A.1 §5, SOL novembre 2022).

## Q5b — Giorno per giorno su tutta la finestra

**Perché A.1 guardava solo gli ultimi 30 giorni:** non c'era un motivo di metodo. Il limite era fissato nel codice dell'analisi S130, senza una ragione scritta. Rifatto su tutta la finestra (BTC 69 giorni, SOL 53), prezzi Coinbase senza disturbi, variante contro la strategia attuale:

| Variante | BTC: giorni sopra / sotto / pari | SOL: giorni sopra / sotto / pari | A.1 (ultimi 30) |
|---|---|---|---|
| D (zona morta corretta e basta) | 0 / 41 / 28 | 16 / 23 / 14 | BTC 0/30, SOL 11/30 |
| R (regola S131a) | 11 / 0 / 58 | 13 / 2 / 38 | nuova |
| F' (commissione 0,25%) | 52 / 17 / 0 | 53 / 0 / 0 | nuova |

- **D:** confermata la conclusione di A.1. Su BTC non sta mai sopra, su SOL è rumore.
- **R:** non sta mai sotto su BTC e quasi mai su SOL. Nei giorni "pari" coincide con la strategia attuale.
- **F':** su SOL sopra tutti i giorni. Su BTC sopra 52 giorni su 69 e sotto 17, tra cui tutti quelli dal 18-set in poi (il percorso descritto in Q3).

## Cosa cambia rispetto al report A.1

- **"In breve" di A.1, punto 6:** alla voce "la commissione maker (X.1) vince in 6 finestre su 11" va aggiunto che, **isolata dalle soglie (F'), la commissione più bassa migliora tutte le 11 finestre.**
- **Da aggiungere a "In breve":** il divario dal compra e tieni è quasi tutto esposizione (Q4).
- **Nessuna nuova variante oltre F'.** Nessuna combinazione provata (lezione S115).
