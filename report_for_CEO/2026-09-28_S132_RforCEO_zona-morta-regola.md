# S131a Parte A — Zona morta come regola esplicita

**Per:** CEO e Board · **Da:** CC (S132, 2026-09-28)
**Brief sorgente:** [`config/2026-09-28_S131a_brief_zona-morta-regola.md`](../config/2026-09-28_S131a_brief_zona-morta-regola.md) (Board S131)
**Commit:** `a2a8028` (codice + test + modifica DB) · `9949fca` (variante F' negli script, per la Parte B)
**Parte B (verifiche Q2-Q5b):** report separato [`2026-09-28_S132_RforCEO_a1-addendum.md`](2026-09-28_S132_RforCEO_a1-addendum.md)
**Stato:** codice pronto e testato, **non ancora attivo**. Diventa attivo al prossimo riavvio dei bot, che decide Max, con la sequenza del §5.

---

## In breve

1. **La regola D2 è nel codice.** In neutrale, avidità e avidità estrema la zona morta è spenta per scelta (`dead_zone_hours = 0`). In paura (1h) e paura estrema (2h) resta com'era. Quando scatta, azzera la scala delle vendite ma **non sposta più il riferimento d'acquisto**. Non dipende più dai riavvii.
2. **Il gate Q1 non era un sì pulito, quindi la regola è stata provata come variante esplicita (R).** Contro la strategia attuale vince nei 2 mesi reali (BTC +$2,6/+3,5, SOL +$9,5/+9,8). Nello storico è identica in 8 finestre su 11, guadagna +$11,6 nel crollo BTC del 2022 e perde al massimo $0,41 (metà dei disturbi, un mese laterale). Il criterio del brief è rispettato: non perde mai nel 90% dei disturbi.
3. **Il brief prevedeva qualche dollaro in meno nei 2 mesi reali, invece il risultato è più alto.** Il motivo è verificato: la strategia attuale non scatta solo ai riavvii del 26 e 27-set, ma anche alle ripartenze del 14 e 16-set, all'inizio del rialzo. Lì vende presto lotti che la scala avrebbe venduto più in alto (§3).
4. **Tre scostamenti dal brief, due approvati da Max:** una riga di modifica al database (il vincolo rifiutava lo zero, ok Max), e la guardia "zona morta inerte", la cui condizione nel brief era rovesciata (corretta da me, fix meccanico). Il terzo è la scelta D2 "non toccare" invece di "stesso limite dell'idle": sono equivalenti (§2).
5. **Il riavvio va fatto in un ordine preciso.** Se lo zero venisse scritto mentre gira il codice vecchio, BTC venderebbe subito un lotto, perché il codice vecchio legge 0 come "scatta adesso" (§5).

---

## 1. Cosa succedeva prima (verificato, non assunto)

| Regime | Attesa ricalcolo (idle) | Zona morta prima | Zona morta adesso | La zona morta scattava a bot acceso? |
|---|---|---|---|---|
| Paura estrema | 4h | 2h | **2h** (invariata) | Sì: arriva prima del ricalcolo |
| Paura | 2h | 1h | **1h** (invariata) | Sì |
| Neutrale | 1h | 2h | **0 = spenta** | No: il ricalcolo azzerava prima il cronometro condiviso |
| Avidità | 0,75h | 2h | **0 = spenta** | No |
| Avidità estrema | 0,5h | 3h | **0 = spenta** | No |

Valori dalla tabella di Sherpa (`bot/sherpa/parameter_rules.py:35-39` per l'idle, `bot/sherpa/board_parameter_rules.py` per la zona morta, uguali per i tre livelli di volatilità). In neutrale e avidità la zona morta scattava **solo al riavvio**, quando il cronometro viene ripreso dal database all'ultimo trade vero. È così che BTC ha venduto il 26 e il 27-set.

## 2. Cosa è cambiato nel codice (`a2a8028`)

- **Tabella Sherpa** (`board_parameter_rules.py`): zona morta 0 in neutrale, avidità e avidità estrema. Paura e paura estrema invariate.
- **Bot** (`grid_bot.py`, blocco DEAD ZONE): con zona morta ≤ 0 il blocco viene saltato, anche al riavvio. Senza questa guardia lo 0 sarebbe stato letto come "scatta subito".
- **D2** (stesso blocco): quando la zona morta scatta, azzera la scala delle vendite e lascia il riferimento d'acquisto dov'era. **Scelta "non toccare" e non "stesso limite dell'idle":** sono la stessa cosa. La zona morta scatta solo col prezzo sopra la media, e lì il limite S70 dell'idle lascia già fermo il riferimento. Nessun motivo tecnico per preferire il limite.
- **Guardia anti-ricaduta** (`config_sync.py`): avviso `dead_zone_inert` nel registro eventi (`bot_events_log`, non Telegram), scritto una volta per cambio di valori e non a ogni minuto. **Condizione corretta rispetto al brief:** il brief chiedeva di avvisare quando `0 < zona morta ≤ idle`, che è proprio il caso che funziona (paura: 1h contro 2h). La condizione giusta è `0 < idle < zona morta`, cioè quando il ricalcolo azzera il cronometro prima che la zona morta arrivi.
- **Messaggio Telegram** della zona morta (`idle_alerts.py`): dice che il riferimento resta invariato.
- **Database:** il vincolo su `dead_zone_hours` passa da "maggiore di 0" a "maggiore o uguale a 0" (migration `db/migration_20260928_s132_dead_zone_allow_zero.sql`, **già applicata**, approvata da Max). Serve perché altrimenti Sherpa non potrebbe scrivere lo zero.
- **Pannello `/grid`:** la spiegazione del campo dice "0 = spenta".
- **Test:** 366 su 366, di cui 6 nuovi: i 5 regimi, lo zero che non scatta nemmeno al riavvio in avidità con cronometro vecchio, il riferimento che non si muove dopo il reset, la guardia.

**Cosa non è cambiato:** margini di acquisto e vendita, logica della scala, ricalcolo idle, blocco perdita, valori in paura, X.1, TF, Sentinel, NewsKeeper.

## 3. Gate Q1: la regola provata contro la strategia attuale

**Risposta a Q1:** nello storico (11 finestre, senza fermi né riavvii) la strategia attuale **non fa mai scattare** la zona morta in neutrale o avidità: 0 reset, contro 9 in paura e 7 in paura estrema. Il ragionamento del CEO è quindi giusto per quei regimi. Però in paura il reset attuale **sposta il riferimento d'acquisto**, e la regola D2 no: le due strategie non coincidono. Come chiede il brief, la regola è stata provata come variante esplicita R, con gli stessi script e gli stessi disturbi di A.1.

**2 mesi reali** (20 disturbi di prezzo, confronto appaiato):

| | Fonte | Strategia attuale | Regola R | Differenza (mediana) | R vince / perde |
|---|---|---|---|---|---|
| BTC | Coinbase | +$27,2 | +$30,8 | **+$3,5** | 20 / 0 |
| BTC | Binance | +$26,2 | +$28,2 | **+$2,6** | 19 / 1 |
| SOL | Coinbase | +$20,4 | +$31,3 | **+$9,8** | 18 / 1 |
| SOL | Binance | +$21,5 | +$31,1 | **+$9,5** | 18 / 2 |

**Perché R guadagna invece di perdere qualche dollaro, come si aspettava il brief.** Nella simulazione dei 2 mesi reali (prezzi Coinbase, senza disturbi) la strategia attuale fa scattare la zona morta 3 volte su BTC e 4 su SOL, tutte in avidità e tutte alla ripartenza dopo un fermo:
- **14-set**, fine del blackout di 9 giorni (BTC e SOL);
- **16-set**, riavvio (solo SOL);
- **26 e 27-set**, i due riavvii del Mini (BTC e SOL).

Quelli del 14 e 16-set arrivano all'inizio del rialzo e vendono presto: BTC a $79.057 e $80.907 il 18-set, SOL a $101,39, $98,91 e $102,29. Con la regola gli stessi lotti restano in mano e la scala li vende più in alto: BTC a $84.429 e $86.838 il 21-set, SOL a $112,12, $116,72 e $121,35. Le vendite da riavvio del 26-27 set, che il brief considerava buone, pesano meno di quelle anticipate di metà settembre. È lo stesso effetto trovato in A.1: in un rialzo la scala conviene.

**Storico** (10 disturbi per finestra):

| Finestra | Differenza R − attuale (mediana) | R vince / perde |
|---|---|---|
| BTC crollo giugno 2022 | **+$11,6** | 9 / 1 |
| BTC settembre 2023 (laterale) | −$0,41 | 0 / 5 |
| BTC settembre 2024 | −$0,28 | 3 / 5 |
| Altre 8 finestre (BTC e SOL, rialzi, cali e laterali) | $0,00 | identica |

**Criterio del brief** ("non peggio della strategia attuale: nessuna finestra in cui perde nel 90% o più dei disturbi"): **rispettato**. Le due finestre negative perdono meno di mezzo dollaro nella metà dei disturbi. Numeri grezzi: `audits/backtest/a1/s131a_rule_real.csv` e `s131a_rule_history.csv`.

## 4. Conseguenza da sapere (già accettata dal Board)

In avidità e neutrale una scala bloccata non ha più uscita: se il prezzo si ferma tra la soglia di vendita e il costo medio, il bot resta fermo finché il prezzo non sale abbastanza da vendere, scende fino alla media per comprare, o il regime passa a paura. **Oggi su BTC:** vende solo sopra circa $87.127 e compra solo sotto circa $77.363 (costo medio). In mezzo non fa nulla, e sulla dashboard si vedrà come una lunga pausa. È la terza auto-obiezione del brief: le vendite da riavvio erano casuali, e il Board ha scelto di rinunciarci.

## 5. Riavvio: cosa va live e in che ordine

**Va live con lo stesso riavvio:**
- `a2a8028`: la regola della zona morta;
- `354586a` (S130): il blocco acquisti per "prezzo sopra la media" scritto una volta per episodio invece che ogni minuto (circa 1.440 righe al giorno in meno nel database).

T.2 e T.3 (S120), che il brief chiedeva di verificare, sono già attivi da molti riavvii. I bot girano col codice `4ba8928` dal 27-set 18:48 UTC. Il repo sul Mini è già aggiornato a `a2a8028`.

**Sequenza obbligata** (lo zero va scritto a bot spenti, perché il codice vecchio lo legge come "scatta adesso"):
1. spegnimento ordinato dell'orchestrator (che spegne anche i bot);
2. `dead_zone_hours = 0` su BTC/USD e SOL/USD, con la riga corrispondente in `config_changes_log`. Oggi il regime è avidità ed entrambi sono ancora a 2;
3. avvio con `scripts/start_bots.py`;
4. controlli: nessuna vendita all'avvio; Sherpa non riscrive 2; nessun avviso `dead_zone_inert` nel registro eventi.

**Dopo il riavvio:** la voce "zona morta inerte" di PROJECT_STATE §5 passa a chiusa con rimando a questo brief, e la roadmap riceve la voce della regola esplicita. **Vincolo noto, non bug:** idle e zona morta condividono ancora un solo cronometro. Oggi funziona perché in paura la zona morta (1h, 2h) arriva prima dell'idle (2h, 4h). Se un domani Sherpa cambiasse quei valori, lo segnala la guardia.

## 6. Decisions

DECISIONE: "zona morta spenta" = `dead_zone_hours = 0`, con modifica al vincolo del database (≥ 0).
RAZIONALE: è esplicita, si legge in dashboard, e la gestisce Sherpa come gli altri parametri.
ALTERNATIVE CONSIDERATE: 168h senza modifica al DB, scartata perché non esplicita e perché scatterebbe comunque dopo 7 giorni di silenzio o a un riavvio; NULL, scartata perché il bot tratta NULL come "tieni il valore precedente".
FALLBACK SE SBAGLIATA: rimettere 2 dove c'è 0, poi ripristinare il vincolo "> 0" (istruzioni nella migration).

DECISIONE: D2 = "non toccare il riferimento d'acquisto", senza replicare il limite S70 dell'idle.
RAZIONALE: la zona morta scatta solo col prezzo sopra la media, dove il limite S70 terrebbe comunque fermo il riferimento: le due opzioni danno lo stesso risultato, e "non toccare" è più semplice.
ALTERNATIVE CONSIDERATE: stesso limite dell'idle (equivalente), comportamento attuale (sposta il riferimento sopra la media, dove la Strategia A blocca gli acquisti).
FALLBACK SE SBAGLIATA: ripristinare la riga `_pct_last_buy_price = current_price` nel blocco DEAD ZONE (1 riga), poi riavvio.

DECISIONE: guardia `dead_zone_inert` con condizione `0 < idle < zona morta`, invece di quella del brief (`0 < zona morta ≤ idle`).
RAZIONALE: la condizione del brief avviserebbe proprio nel caso che funziona (paura) e tacerebbe nel caso rotto.
ALTERNATIVE CONSIDERATE: condizione del brief, scartata perché rovesciata.
FALLBACK SE SBAGLIATA: è solo un avviso nel registro eventi, senza effetti sul trading.

DECISIONE: avviso nel registro eventi, una volta per cambio, non su Telegram.
RAZIONALE: Telegram è saturo (regola Board: il monitoraggio va in `/admin`), e la sincronizzazione gira ogni minuto.
ALTERNATIVE CONSIDERATE: avviso su Telegram; log a ogni minuto.
FALLBACK SE SBAGLIATA: nessuno necessario.
