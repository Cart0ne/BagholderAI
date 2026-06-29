# [PARKED] Deriva del `realized_pnl` (avg-cost) — Fix B + Fix A2

**Data:** 2026-06-29 · **Parcheggiato:** 2026-06-29 (S111) · **Autore:** Claude Code (Intern)
**Origine:** finding emerso da una domanda di Max ("avvocato del diavolo") sulla coerenza dei numeri della dashboard `grid`/`tf`.
**Stato:** **Fix A SHIPPED** (numero pubblico onesto). Restano due lavori parcheggiati (sotto).

> **Fix A — ✅ FATTO 2026-06-29 (commit `0df228c`)**: il Net Realized è derivato dal replay avg-cost in entrambe le copie (`src/lib/pnl-canonical.ts` + `public/lib/pnl-canonical.js`). Verificato live: Total P&L invariato, Net Realized +30.6 → **+22.4**, incoerenza identità da ~$8.12 → ~$0.07 (rumore float). Il rischio reputazionale pubblico è **chiuso**.

---

## ⏸ RESIDUO DA FARE (motivo del parcheggio)

### Fix B — Bot: `realized_pnl` a DB avg-cost puro · TRIGGER: pre-mainnet
Il `realized_pnl` scritto dal bot resta **gonfiato di ~$8** (sorgente non toccata da Fix A, che agisce solo nel rendering del sito). Per renderlo vero serve **disaccoppiare due concetti oggi fusi in `avg_buy_price`**:
1. **avg "operativo"** — può azzerarsi sulla polvere per sbloccare i buy (Strategy A guard); **da tenere**.
2. **avg "contabile"** — deve **trattenere** il costo della polvere → realized a DB avg-cost puro.

**Rischio:** ALTO relativo (trading logic LIVE: buy guard, ladder, **skim** che dipende dal realized). Brief dedicato + test + restart.
**Decisione CEO/Board aperta:** `realized_pnl` a DB esatto (Fix B) oppure stima interna + sempre Equity-derived sul sito (Fix A "wontfix" su B)? Con soldi veri a mainnet propendo per Fix B come brief pre-mainnet.
**Collaterale:** lo **skim** è calcolato sul realized del bot → se gonfiato, lo skim accantonato è leggermente sovra-stimato. Da verificare nello stesso brief.

### Fix A2 — Today P&L homepage · TRIGGER: opzionale / quando si tocca la home
La card "Today P&L" somma ancora `SUM(realized_pnl)` sui sell di oggi → eredita la deriva del giorno. Onesta richiede replay avg-cost intraday. Metrica di flusso → bassa priorità.

---

## Contesto / diagnosi originale (background)

**Severità:** MEDIA. Non blocca go-live, non tocca soldi reali; il numero sbagliato **era** public-facing (`/dashboard`) — ora corretto da Fix A.

---

## 0. TL;DR (3 righe)

Su `/dashboard` mostriamo **Net Realized +$30.64**, ma quel numero è **gonfiato di ~$8.19** rispetto al costo medio reale del portafoglio. Il valore onesto è **~+$22.5**. Il **Total P&L (+$1.91)**, gli holdings e l'unrealized (−$20.62) sono invece **corretti**. Causa: il bot azzera il costo medio quando la griglia scende a "polvere" (comportamento *voluto* per sbloccare i buy), e così "dimentica" il costo della polvere → fabbrica realized fantasma a ogni ciclo. Propongo **fix lato sito subito** (onestà del numero pubblico) + **decisione architetturale lato bot** (più delicata).

---

## 1. Il sintomo (cosa ha notato Max)

La card "PORTFOLIO OVERVIEW" della griglia ($500) mostra contemporaneamente:

| Card | Valore |
|---|---|
| TOTAL P&L | **+$1.91** (= Current State $501.91 − Budget $500) |
| NET REALIZED PROFIT (post-fees) | **+$30.64** |
| UNREALIZED | **−$20.62** |
| FEES | −$5.55 |
| SKIM | +$13.19 |

Domanda di Max: *"se ho net realized +30.64 e perdo −20.62 in posizioni aperte, il P&L non dovrebbe essere ~+10, non +1.91? Cosa non capisco?"*

**Non sta sbagliando il ragionamento.** Esiste un'identità contabile che DEVE valere se tutto usa lo stesso costo medio:

```
Total P&L = realized (lordo) + unrealized − fees
```

(Lo skim NON si somma a parte: è realized già guadagnato, spostato in un'altra tasca; "Current State" lo ri-aggiunge.)

Coi numeri della card: `36.19 + (−20.62) − 5.55 = +10.02` ≠ **+1.91**. **Scarto di ~$8.11.** Due card della stessa dashboard si contraddicono.

---

## 2. La verifica (DB live, fund grid: `managed_by='grid'`, `v3`, `testnet_2`)

### 2a. Il lato patrimoniale torna al centesimo
| Voce | Da DB | Card |
|---|---|---|
| Σ buy.cost | 2913.84 | |
| Σ sell.cost | 2641.01 | |
| netInvested (buy−sell) | 272.82 | |
| cash = 500 − 272.82 − skim 13.19 | **213.98** | **213.98 ✓** |
| Current State = cash + holdings 280.28 + skim 13.19 − fees 5.55 | **501.90** | 501.91 ✓ |
| **Total P&L** | **+1.91** | **+1.91 ✓** |

→ **Il +1.91 è verità del wallet**: non dipende dal costo medio (solo cash + holdings + skim − fees). Affidabile a prescindere.

### 2b. Gli holdings del sito sono GIUSTI (confronto con `bot_runtime_state`)
| Coin | Replay sito | `managed_holdings` bot | Match |
|---|---|---|---|
| BTC | 0.002428 | 0.0024276 | ✓ |
| BONK | 31.969.919 | 31.969.919 | ✓ esatto |
| SOL | ~0.00105 | 0.00072 | ~✓ (dust) |

(Il bot tiene anche `phantom_holdings` — es. 1.0 BTC fantasma da testnet — **correttamente esclusi** dai conti, fix S96b.)

### 2c. Il numero che mente: `realized_pnl`
Replay avg-cost indipendente (ricalcola il realized a ogni vendita come `revenue − avg×qty`, **senza** leggere il campo DB):

```
TOTALE  realized_pnl DB (stored) = +36.198 lordo  →  +30.64 netto (card)
        realized avg-cost VERO   = +28.007 lordo  →  +22.45 netto
        GAP                       = +8.191
        di cui:  BTC +9.116 · BONK −0.500 · SOL −0.425
```

Controprova con l'identità: `28.01 + (−20.62) − 5.55 = +1.84 ≈ +1.91` ✓ (l'unrealized −20.62 è coerente col realized VERO, non col +30.64).

---

## 3. La causa esatta (verificata sui `reason` dei trade)

I `reason` delle vendite BTC del 14-giu mostrano lo scalino: da quel giorno **ogni** ciclo BTC registra realized ≈ **+0.545** mentre il replay lo vede ≈ **+0.01** (in pari). Tra una vendita e l'altra compaiono buy con reason:

> *"Pct buy: first buy at market $64,348 **(reference established)**"* — ripetuto molte volte al giorno.

### Meccanismo
La griglia BTC **svende fino alla "polvere"** (residuo sotto `min_notional`, invendibile su Binance) e poi **ricompra "da capo"**. Alla svendita-a-polvere, in [bot/grid/sell_pipeline.py:687-696](bot/grid/sell_pipeline.py#L687):

```python
fully_sold = bot.managed_holdings <= 1e-10
# oppure residual_notional < min_notional  → fully_sold = True (polvere)
if fully_sold:
    bot.state.holdings = max(bot.state.holdings, 0)   # le monete-polvere RESTANO nel wallet
    bot.state.avg_buy_price = 0                        # ← ma il costo medio viene AZZERATO
    bot._pct_last_buy_price = price
```

Il prossimo buy è "first buy (reference established)" e fissa un avg fresco al prezzo di riacquisto ([buy_pipeline.py:296-300](bot/grid/buy_pipeline.py#L296)). **La polvere rimane in pancia (finisce in `managed_holdings`) ma il suo costo è stato buttato.** A ogni ciclo il bot "dimentica" un pezzetto di costo → l'avg si abbassa → le vendite successive sembrano più profittevoli di quanto siano in avg-cost puro. Su BTC (che ricicla di più) ≈ +$0.5/ciclo × ~13 cicli ≈ **+$9**.

Il replay del sito **non** resetta su polvere → mantiene l'avg-cost vero → realized corretto (+28.01) e openCost/unrealized corretti.

### Perché il reset è VOLUTO (non è un bug "stupido")
Il commento in [sell_pipeline.py:680-686](bot/grid/sell_pipeline.py#L680) lo spiega: se l'avg restasse >0 sulla polvere, la **Strategy A buy guard** ("no buy sopra avg") bloccherebbe ogni acquisto in eterno → *"BONK dust trap, 8+ ore di BUY BLOCKED loop"*. L'azzeramento sblocca la griglia. È una **scelta di trading deliberata** con un **effetto collaterale contabile** (realized leggermente gonfiato). Il team ha già combattuto la versione "phantom" di questo problema in S96b (BTC che riportava +$49.59 su un guadagno reale di ~$0.04). Il reset-su-polvere è la coda residua dello stesso tema.

### Inquadramento nel progetto
È esattamente la regola già nota: **"`realized_pnl` nel DB è un fossile/finzione; l'Equity (avg-cost) è canonico"** (decisioni S57a, S60c-d, "Equity P&L vs FIFO"). Qui il fossile è finito **pubblicato** su `/dashboard`.

### Generalità
Non è BTC-specifico: **ogni coin di griglia che cicla a polvere accumula questa deriva.** BTC domina ora (più round-trip), ma BONK/SOL contribuiscono (di segno opposto, piccolo) e nel tempo compone. A ogni reset mensile testnet riparte.

---

## 4. Dove è esposto

- **`/dashboard` pubblico**: card "Net Realized" — la card privata stessa lo dichiara *"twin of the value on /dashboard"*. → **+$30.64 pubblico, gonfiato.**
- **Dashboard private** `grid.html` / `admin.html`: stessa card.
- **NON colpiti** (sani, pubblicabili): **Total P&L homepage (+1.91)**, P&L per-fund (GRID/TF split), holdings, unrealized, cash, skim, fees.
- **Da valutare**: la card "Today P&L" (homepage) somma `realized_pnl` delle vendite di oggi → **anch'essa erediterebbe** la deriva del giorno (vedi §5, Fix A2).

---

## 5. Proposte di fix

### Fix A — Sito: deriva il realized dall'avg-cost replay (CONSIGLIATO, subito)
**Cosa:** in [web_astro/src/lib/pnl-canonical.ts:113-114](web_astro/src/lib/pnl-canonical.ts#L113), oggi il replay fa `s.realized += dbPnl` (legge il campo fossile). Cambiarlo per **calcolare** il realized: `realized += (cost_ricevuto − avg_corrente × amount)` (lordo), coerente con l'openCost che lo stesso replay già produce.

**Effetto:** realized, unrealized e Total P&L diventano **coerenti ovunque** (homepage, `/dashboard`, admin, grid). Il "Net Realized" pubblico passa da +30.64 a **~+22.5** (onesto).
**Rischio:** basso. `Total P&L` NON cambia (non dipende dal realized). Cambia solo il valore mostrato nelle card "Net Realized". Da verificare: nessun altro consumer si appoggia al realized stored via `computeCanonicalState`.
**Costo:** ~1h (modifica + verifica cross-pagina + `node --check`). **Solo web, nessun restart bot.**

**Fix A2 (collegato, opzionale):** rendere onesta anche "Today P&L". Più scomodo (serve un replay avg-cost intraday, non un semplice Σ sui sell di oggi). Da decidere se vale: è una metrica di "flusso giornaliero", non patrimoniale. Proposta: parcheggiare o trattare in un secondo momento.

### Fix B — Bot: smettere di "dimenticare" il costo della polvere (DELICATO, pre-mainnet)
**Cosa:** il `realized_pnl` scritto a DB è approssimato per via del reset-su-polvere. Per renderlo vero servirebbe **disaccoppiare due concetti oggi fusi in `avg_buy_price`**:
1. **avg "operativo"** (può azzerarsi su polvere per sbloccare i buy — comportamento attuale, da tenere);
2. **avg "contabile"** (deve trattenere il costo della polvere, così il realized è avg-cost puro).

**Rischio:** ALTO relativo. Tocca trading logic LIVE (buy guard Strategy A, ladder, skim che dipende dal realized). Richiede brief dedicato + test + restart Mac Mini. Da NON fare di fretta.
**Alternativa "wontfix" difendibile:** accettare che `realized_pnl` del bot è una stima e **non mostrarlo mai come verità** — derivare sempre il realized pubblico dall'Equity/avg-cost (cioè: Fix A è sufficiente per il pubblico, e il campo DB resta un dato interno approssimato). Coerente con la dottrina "Equity è canonico".

---

## 6. Raccomandazione

1. **Fix A subito** (sito): allinea il numero pubblico alla verità, zero rischio trading. È il "one source of truth" del progetto applicato al realized.
2. **Fix B: decisione del CEO/Board.** Domanda da girare: *vogliamo che `realized_pnl` a DB sia avg-cost puro (Fix B, costoso, pre-mainnet) oppure accettiamo che sia una stima interna e mostriamo sempre l'Equity-derived (Fix A "wontfix" su B)?* In ottica mainnet con soldi veri, avere un realized contabile esatto ha più valore → propendo per **schedulare Fix B come brief pre-mainnet**, ma con A che copre già il rischio reputazionale pubblico ora.
3. **Fix A2 (Today P&L):** parcheggiare salvo diversa indicazione.

---

## 7. Decision log / anti-assenso

- **Obiezione tecnica sollevata:** il reset-su-polvere NON è un bug da "togliere e basta" — è la cura del BONK dust-trap. Rimuoverlo ingenuamente re-introduce il deadlock dei buy. Per questo Fix B richiede disaccoppiamento, non una riga.
- **Cosa NON ho fatto:** non ho scritto codice né toccato i numeri, come da richiesta (report-first per il CEO).
- **Cosa NON cambia con Fix A:** Total P&L, holdings, unrealized, cash, skim — già corretti e verificati sul DB.
- **Fallback se Fix A si rivelasse sbagliato:** è una modifica isolata a `replayAvgCost`; ripristino = ripristinare `s.realized += dbPnl` (1 riga). Nessun dato a DB toccato.

---

## 8. Allegati / riproducibilità
- Replay indipendente: confronta riga-per-riga `realized_pnl` stored vs avg-cost ricalcolato (fetch via anon key, stesso dato del sito). Risultato: gap +8.191, concentrato su BTC (+9.116).
- Query DB usate: aggregati per `symbol/side`, sequenza BTC 12-14 giu (reason "reference established"), `bot_runtime_state` (managed vs phantom holdings).
