# Proposta esplorativa — Exit-after-N-positive-sells (TF)

**From:** Claude Code (Intern) → CEO (Claude, Projects)
**Via:** Max (board)
**Date:** 2026-04-27
**Tipo:** Proposta esplorativa con backtest sui dati reali — *no codice scritto, no brief ancora aperto*
**Origine:** brainstorming Max ↔ Intern, 27/04/2026

---

## TL;DR

Max ha proposto un meccanismo di exit aggiuntivo per il TF: **dopo la 4ª vendita in profitto sulla stessa coin gestita da TF, chiudere la posizione (vendere il residuo) e impedire al TF di ricomprarla nello stesso "soggiorno"**. Un take-profit contato in *eventi*, non in *percentuali*.

Ho ricostruito i 449 trade TF storici (15-27 aprile 2026, 12 giorni, 29 coin TF — BTC/SOL/BONK esclusi automaticamente perché manuali) e simulato la regola su **27 gestioni TF chiuse**.

**Risultato N=4: edge totale +$35.30 sul portfolio (12 giorni). 14/27 periodi triggered. 10 vincite, 4 sconfitte, 0 pareggi.**

Sorpresa metodologica importante (sezione "Cosa fa davvero la regola"): **l'edge non viene dal vendere meglio il residuo, ma dall'evitare i trade futuri di quelle coin.**

---

## Definizione operativa della regola

> Su una coin gestita TF, mantieni un counter di *sell con `realized_pnl > 0`* dall'ALLOCATE (o, in approssimazione, dalla prima trade TF su quella coin nel soggiorno corrente). Quando il counter raggiunge **N**:
> 1. Vendi il residuo di posizione (se >0) al mercato.
> 2. Tagga la coin come "saturated" per il resto del soggiorno → il grid TF non rientra. Solo un nuovo ALLOCATE TF (su scan successivo) può riattivarla.
> 3. Reset del counter al prossimo ALLOCATE.

**Non sostituisce** stop-loss / take-profit % / greed decay. Si aggiunge come *layer di safety lato gain-saturation*.

---

## Metodologia del backtest

**Universo dati:** tabella `trades` su Supabase, filtro `managed_by = 'trend_follower'`, ordine cronologico. 449 trade su 29 coin distinte, 15→27 aprile 2026.

**Definizione di "soggiorno gestito":** sequenza continua di trade TF sulla stessa coin. Due trade della stessa coin a >24h di distanza = due soggiorni distinti (perché in mezzo c'è stata dealloc + ri-alloc; verificato sui dati: 412/420 gap intra-coin sono <12h, solo 1 supera 48h). 30 soggiorni totali, 27 chiusi (holdings finali = 0), 3 ancora aperti (esclusi).

**Counter "sell positiva":** trade con `side='sell'` e `realized_pnl > 0`. Niente filtri su soglia minima di profitto.

**Liquidazione forzata simulata:** al raggiungimento di N, le holdings residue vengono vendute al prezzo dell'Nesima sell (no fee, no slippage modellati — stesso assunto del realized_pnl reale che non li include). Tutti i trade TF successivi nello stesso soggiorno vengono ignorati nel counterfactual.

**Limite metodologico onesto:** lo script non ha accesso a serie di prezzi minute-by-minute post-uscita. Quindi l'assunzione "vendiamo il residuo al prezzo di quella sell" è **una stima centrale**: ottimistica nei casi in cui la coin sia continuata a salire dopo l'uscita (la regola perderebbe edge), pessimistica nei casi di ritraccio (la regola guadagnerebbe edge — ed è esattamente lo scenario che vuole coprire).

---

## Risultati — sweep su N

| N | Trigger | Beat | Worse | Tied | Avg Δ$ quando trigger | **Δ totale portfolio (USD)** |
|---|---|---|---|---|---|---|
| 2 | 19 | 11 | 7 | 1 | +1.43 | **+27.25** |
| 3 | 15 | 9 | 6 | 0 | +2.14 | **+32.10** |
| **4** | **14** | **10** | **4** | **0** | **+2.52** | **+35.30** ← picco |
| 5 | 12 | 6 | 4 | 2 | +1.40 | +16.78 |
| 6 | 11 | 7 | 2 | 2 | +1.62 | +17.77 |
| 7 | 6 | 3 | 2 | 1 | +0.66 | +3.94 |
| 8 | 5 | 3 | 2 | 0 | +0.92 | +4.58 |

Picco netto a **N=4**. Il segnale è coerente N=2/3/4 (sempre positivo, beat ≥ worse), poi declina rapidamente da N=5 in su (la regola si attiva troppo tardi e perde efficacia).

---

## Cosa fa davvero la regola — la trovata sorprendente

Approfondendo il caso N=4 (Max ha chiesto: *"hai calcolato anche con tutto l'allocato, non solo 1 lotto?"*), ho aggiunto al CSV 5 colonne diagnostiche per capire **da dove arriva l'edge dei +$35**: residual_qty, residual_avg_buy, exit_price, liq_value_usd (USD del blocco residuo venduto), liq_pnl_usd (PnL contribuito dalla sola vendita-forzata).

**Risultato per le 14 coin in cui N=4 si attiva:**

| Symbol | sells | +sells | actual$ | cf$ | delta$ | residual qty | liq value$ | liq PnL$ |
|---|---|---|---|---|---|---|---|---|
| BIO/USDT | 12 | 6 | +5.80 | +5.68 | -0.12 | 159.5 | 5.87 | +0.02 |
| AXL/USDT | 27 | 12 | +1.80 | +0.99 | -0.81 | 206.27 | 12.46 | +0.21 |
| MBOX/USDT | 30 | 15 | +3.10 | +1.30 | -1.80 | 771.6 | 12.58 | +0.19 |
| **MOVR/USDT** | **19** | **4** | **-13.39** | **+4.70** | **+18.09** | **0** | **0** | **0** |
| TST/USDT | 23 | 7 | -2.36 | +0.88 | +3.24 | 2904.1 | 34.97 | -1.69 |
| HIGH/USDT | 21 | 6 | +0.46 | +3.74 | +3.27 | 0 | 0 | 0 |
| API3/USDT | 13 | 5 | +3.40 | +4.16 | +0.75 | 75.18 | 31.38 | +0.94 |
| BLUR/USDT | 20 | 6 | -1.17 | +4.00 | +5.17 | 769.5 | 26.30 | +0.85 |
| SPK/USDT | 50 | 14 | +1.68 | +5.97 | +4.28 | 0 | 0 | 0 |
| GUN/USDT | 16 | 4 | +0.30 | +2.91 | +2.61 | 0 | 0 | 0 |
| CHZ/USDT | 14 | 6 | +2.30 | +2.58 | +0.28 | 206.0 | 10.10 | +0.32 |
| MET/USDT | 32 | 12 | -4.47 | -3.99 | +0.48 | 0 | 0 | 0 |
| RUNE/USDT | 14 | 6 | +1.06 | +1.12 | +0.06 | 0 | 0 | 0 |
| KAT/USDT | 26 | 9 | +0.84 | +0.62 | -0.21 | 0 | 0 | 0 |
| **TOTALE** | | | **-0.64** | **+34.66** | **+35.30** | | **133.65** | **+0.85** |

**Tre osservazioni che cambiano la lettura del backtest:**

1. **In 7 casi su 14, al momento della 4ª sell positiva la coin era già flat** (residual_qty = 0). In questi casi la "uscita forzata" non vende niente — semplicemente *impedisce ai buy successivi di rientrare*. L'edge viene dall'aver evitato cicli buy-sell futuri. Vedi MOVR (+$18.09), HIGH (+$3.27), SPK (+$4.28), GUN (+$2.61), MET (+$0.48), RUNE (+$0.06), KAT (-$0.21).

2. **Negli altri 7 casi** la liquidazione vende un blocco residuo (mediamente $9.55, totale $133.65 di valore venduto), ma il PnL contribuito da quella vendita è praticamente zero: **+$0.85 totali**. Il blocco residuo si vende quasi al pari del prezzo medio di carico — non c'è alfa nella vendita-blocco in sé.

3. **Il PnL "actual" totale delle 14 coin è -$0.64**, in pratica zero/leggermente negativo. Le **stesse coin** sotto la regola N=4 farebbero **+$34.66**. Tradotto: **le coin che riescono a fare 4 sell positive sono proprio quelle che oggi finiscono per costarci**. La regola taglia il rumore di rotazione ulteriore su coin "già spremute".

**Conclusione operativa:** la feature non è un "take-profit smart" come l'avevamo concettualizzata (vendere il residuo a un prezzo migliore di quello che otterremmo aspettando). È un **circuit breaker che dice "questa coin ha già dato, fermiamoci"** — proteggendoci dai cicli successivi che statisticamente vanno male.

---

## Caso emblematico — MOVR/USDT

Il singolo contributo più grande all'edge totale (+$18.09 su +$35.30, il 51%).

- 19 trade complessivi, 4 sell positive, P&L reale finale: **-$13.39**.
- Sotto N=4, la regola sarebbe scattata alla 4ª sell positiva mentre la coin era già flat (residual=0).
- Avrebbe impedito i buy/sell successivi → P&L contraffattuale: **+$4.70**.
- Quindi 15 trade post-4ª-sell-positiva su MOVR sono andati in negativo, presumibilmente con uno stop-loss finale o una serie di sell-loss che ha mangiato tutto il profitto accumulato + altro.

Questo è il pattern che la regola intercetta: **una coin che ti regala 4 sell positive e poi ti seppellisce**.

---

## Quello che la regola NON risolve

- **Coin che non fanno mai 4 sell positive nello stesso soggiorno.** 13/27 periodi (48%) hanno <4 sell positive — escono per stop-loss, dealloc bearish, swap, o budget exhaustion prima. La regola è invisibile su questi. Trailing stop (brief 36f) attaccherà invece quel mezzo del campione.
- **Continuazioni vere.** Se una coin fa 4 sell positive e poi continua a pumpare per ore, la regola ci fa uscire e perdere il rialzo. Sui dati storici questo non emerge come contributore negativo significativo (0 tied = mai esattamente uguale, ma 4 worse vs 10 beat su N=4), ma su un altro regime di mercato potrebbe essere diverso. **Difesa naturale:** TF al prossimo scan può ri-allocare la coin se è ancora bullish, perdendo solo le fee dell'uscita.

---

## Limiti del campione

- **27 soggiorni chiusi, 12 giorni di storico.** Campione modesto. Il segnale è coerente nello sweep N=2..6, ma non possiamo escludere che un campione più ampio (target: 100+ soggiorni, ~6-8 settimane) modifichi il picco da N=4 a N=3 o N=5.
- **Regime di mercato unico.** I 12 giorni coprono un periodo specifico di trend-following su coin scelte dal TF corrente. Cambio di volatilità o di mix tier potrebbe spostare il numero ottimale.
- **Costi non modellati.** No fee sulla liquidazione forzata, no slippage. Su trade da $5-30 le fee 0.1% incidono per pochi cent — trascurabili rispetto al delta totale, ma per onestà va detto.

---

## Raccomandazione

**Proposta:** aprire un brief leggero per implementare la regola con N=4 default (configurabile da `trend_config`, off-by-default fino a primo periodo di osservazione live).

**Costo implementazione stimato:** basso. Un counter per bot TF in `bot_state_snapshots` (o `bot_config`), un check in `grid_bot.py` accanto a 39a/39c/45f, una flag "saturated" che blocca rientro per il soggiorno corrente. Nessun cambio architetturale.

**Priorità relativa:** **dopo** trailing stop (36f, già in roadmap a 2 settimane). Trailing stop attacca il problema dello stop-loss (campione più ampio, ~50% dei soggiorni), exit-after-N attacca il problema dell'over-rotation (campione 14/27). Insieme coprono complementi diversi del fallimento TF.

**In subordine:** se il CEO vuole più solidità statistica prima di muoversi, si può ri-girare lo stesso script tra 30 giorni (target ~80-100 soggiorni chiusi) e confermare/rivedere il picco a N=4.

---

## Allegati

- Script: [scripts/backtest_exit_after_n_positive_sells.py](../scripts/backtest_exit_after_n_positive_sells.py) — riproducibile, ~280 LOC, gira in <5s.
- CSV summary: [scripts/output/exit_after_n_summary.csv](../scripts/output/exit_after_n_summary.csv) — N=2..8 con beat/worse/tied/delta totale.
- CSV per-period: [scripts/output/exit_after_n_per_period.csv](../scripts/output/exit_after_n_per_period.csv) — 30 soggiorni con tutti i contraffattuali e le 5 colonne diagnostiche per N=4.

---

**Domande aperte per il CEO:**

1. **N=4 conferma o vuoi un valore diverso?** N=3 ha edge simile (+$32 vs +$35), trigger più frequente (15 vs 14), ma rapporto beat/worse leggermente peggiore (9/6 vs 10/4). N=4 sembra il punto migliore ma è una micro-decisione.
2. **Cooldown post-trigger:** dopo che la regola scatta, la coin resta "saturated" solo per il soggiorno corrente (TF può ri-allocarla al prossimo scan), oppure introduciamo un cooldown ore tipo `tf_saturated_cooldown_hours` come abbiamo per SL?
3. **Aspettiamo più dati prima di implementare** o partiamo subito con un brief "tarato a N=4 di default, off-by-default, accendiamo dopo 2 settimane di osservazione"?
