# Equity P&L vs FIFO Realized — il numero "vero" sul wallet Binance

**Data:** 2026-05-05
**From:** CC (Claude Code, Intern)
**To:** CEO (Claude, Projects) + Max (Board)
**Origine:** sessione di verifica spot della home Astro — Max chiede di estrarre la formula del TODAY P&L (`+$0.99`), poi nota che "su Binance l'ultima vendita di BONK sarebbe in perdita".

---

## In una riga

Il `+$52.69` di TOTAL P&L che mostriamo sulla home **non è quello che vedremmo sul wallet Binance se chiudessimo tutto adesso**. Il numero vero è **+$48.16**. Il delta non è un bug della home — è una limitazione strutturale del FIFO realized: ignora il valore mark-to-market dei lotti ancora aperti, che oggi vale $213 distribuiti su 6 symbol.

Non è urgente patchare ma è urgente che il CEO sappia che il numero che usa per le decisioni ha un margine di errore noto e direzionalmente prevedibile.

---

## Cosa è successo nella sessione

Max ha aperto la home Astro e ha chiesto di estrarre la formula del TODAY P&L (`+$0.99`). Estratto il codice, fatto verifica SQL: i conti tornano al centesimo, formula corretta.

Poi però:

> "questo non torna: su Binance l'ultima vendita di BONK sarebbe in perdita."

Il sospetto era giusto. Investigando, sono saltati fuori tre piani sovrapposti che vanno separati con cura.

---

## I tre numeri che chiamiamo tutti "P&L"

Ho ricalcolato tutto da DB live + prezzi spot Binance live:

| Metrica | Valore | Cos'è | Bias direzionale |
|---|---:|---|---|
| **DB `realized_pnl` sommato** | **+$78.88** | il bot scrive con avg_buy_price come basis | sovrastima ~$30 |
| **FIFO globale (home)** | **+$52.69** | la home ricalcola FIFO da zero ogni page-load | sovrastima ~$5 |
| **Equity P&L (Binance vero)** | **+$48.16** | cash_delta + valore MtM posizioni aperte | la verità |

Tutti e tre i numeri esistono **nello stesso istante**, sullo stesso DB, sullo stesso wallet ipotetico. Sono solo formule diverse.

---

## Perché esistono tre numeri diversi

### 1. DB `realized_pnl` (+$78.88)
Già diagnosticato e parzialmente fixato nel report del 03/05 (`session 55`). Il bot calcola il PnL ad ogni sell come `revenue − holdings × avg_buy_price`. L'`avg_buy_price` è una media mobile che si rinfresca ad ogni buy/sell — su mercati laterali con tanti trade, scivola verso il prezzo di mercato corrente, gonfiando i sell "in profitto" e mascherando i sell "in perdita". I 458 trade pre-53a hanno bias accumulato; i nuovi sono FIFO interni del bot ma comunque diversi dal FIFO globale che fa la home.

### 2. FIFO globale (+$52.69)
La home (e ora anche `commentary.get_grid_state` dal 03/05) ricostruisce la coda FIFO per symbol da zero, somma tutti i `revenue − basis_FIFO` dei sell. È **molto** più onesto del DB. Ma ha un buco: ignora che alcuni symbol hanno **lotti ancora aperti**. Quei lotti hanno un costo storico (in coda) ma anche un valore di mercato corrente, che il FIFO realized non vede.

### 3. Equity P&L (+$48.16)
La formula completa che un broker farebbe sul tuo wallet:
```
P&L = (USDT entrati - USDT usciti) + Σ(holdings × prezzo_spot_corrente)
    = cash_delta_totale + valore_MtM
    = −$165.23 + $213.39
    = +$48.16
```

Questo è l'**unico** numero direttamente confrontabile con quello che vedremmo su Binance se liquidassimo tutto al market.

---

## Snapshot per symbol (oggi, 2026-05-05)

Cash flow finora + valore di mercato dei residui:

| Symbol | Cash flow | Holdings residui | Valore MtM | P&L equity |
|---|---:|---:|---:|---:|
| BONK (Grid) | +$26.69 | 0.99 BONK (polvere) | $0.00 | **+$26.69** |
| SOL (Grid) | −$146.91 | 1.7636 SOL @ $84.69 | +$149.36 | **+$2.45** |
| BTC (Grid) | −$21.36 | 0.000627 BTC @ $80.7k | +$50.61 | **+$29.25** |
| TRX (TF tf_grid) | −$7.35 | 22.20 TRX @ $0.34 | +$7.55 | +$0.20 |
| ZEC (TF tf_grid) | −$5.75 | 0.014 ZEC @ $418.6 | +$5.86 | +$0.11 |
| PHB (TF) | +$1.28 | 0.10 PHB @ $0.107 | +$0.01 | +$1.29 |
| Altri ~45 TF chiusi | −$11.83 | $0 | $0 | −$11.83 |
| **Totale** | **−$165.23** | | **+$213.39** | **+$48.16** |

Notare:
- **SOL e BTC sono il caso più estremo**: cash delta negativo ($−168 combinati) compensato da $200 di MtM. È esattamente l'effetto che il FIFO realized non cattura. Su mainnet il P&L si materializzerebbe solo quando i lotti aperti vengono effettivamente venduti.
- **BONK è il caso opposto**: posizione completamente flat, cash delta = P&L vero al centesimo. Qui il FIFO realized e l'equity P&L coincidono.

---

## L'esempio specifico che ha fatto sospettare a Max

Sell BONK delle 05:11 di oggi:

| Vista | P&L singolo trade |
|---|---:|
| DB `realized_pnl` | **+$0.52** (il bot dice "ho guadagnato") |
| FIFO globale | **−$0.07** (la home dice "ho perso") |

Il bot aveva fatto un buy di 4.012.841 BONK ieri sera a $6.23/M. Stamattina vende lo stesso identico amount a $6.36/M. Il bot pensa: "ho guadagnato $0.52 sul lotto di ieri". Il FIFO globale però vede che la coda BONK aveva ancora lotti residui dal 30 aprile / 1 maggio (comprati a prezzi più alti) non completamente svuotati. Vendere 4M BONK significa contabilmente svuotare quei lotti vecchi a costo $25.59, non quello di ieri a $25.00. Risultato: −$0.07.

Né l'uno né l'altro è "il P&L vero su Binance" — perché su Binance BONK è praticamente flat (0.99 token residui = polvere). Il P&L vero su BONK lo conosciamo solo a posizione chiusa: **+$26.69 cumulativi**, ed è coerente sia col cash delta sia col FIFO globale (perché quando chiudi tutto i due numeri convergono).

---

## Implicazioni operative

### Cosa NON è in pericolo
- **Non perdiamo soldi reali**, siamo paper. L'errore di reporting è cosmetico finché non andiamo mainnet.
- **La dashboard e i report Telegram dal 03/05 sono già allineati** alla stessa formula FIFO. Non c'è discrepanza tra superfici.
- **Il bot decide di vendere usando la sua logica interna** (`avg_buy_price` + soglia), non i numeri della home. Quindi i numeri della home non influenzano il trading.

### Cosa è in pericolo
- **Il go-live mainnet** porta con sé un rischio nascosto: il bot decide di vendere quando `current_price > avg_buy_price × (1 + min_profit_pct/100)`. Su mercati laterali con tanti buy ravvicinati, l'avg si avvicina al prezzo di mercato e il bot finisce per vendere lotti FIFO che sono **realmente** in perdita rispetto al loro costo storico. Sul singolo trade è rumore, sui mesi si compone.
- **Il TOTAL P&L della home (+$52.69) verrebbe smentito da Binance** del 9% (~$5) al momento di un audit. Non è drammatico, ma è il tipo di errore che, se cresce di scala, è la classica fonte di "ho aperto la dashboard pensando di aver guadagnato 40 e invece ho 5" che Max ha richiamato esplicitamente nel report del 03/05.

### Quanto può crescere il delta?
Dipende da quanto MtM accumuliamo in posizioni aperte. Oggi sono $213 su un capitale paper di ~$1k. Se andassimo mainnet con $10k, lo stesso pattern proporzionale darebbe $2.000 di posizioni aperte e un delta plausibile di $50–100 tra "FIFO realized" e "equity vera". Già visibile a occhio.

---

## Proposta — tre interventi, in ordine di priorità

### 1. Aggiungere "Equity P&L" alla home (priorità: alta, costo: 1–2 ore)
Un solo fetch a `https://api.binance.com/api/v3/ticker/price?symbols=[...]` per i symbol con holdings residui, moltiplicare per le quantità in coda FIFO, sommare al cash delta. Mostra:

- **TOTAL P&L (FIFO realized)**: $52.69 *— quanto abbiamo "incassato" finora*
- **TOTAL P&L (equity)**: $48.16 *— quanto vedremmo su Binance se chiudessimo tutto adesso*

Due numeri affiancati, niente magia, l'utente capisce la differenza dal label. Stessa logica anche per il TODAY P&L.

### 2. Allineare la decisione di vendita del bot a FIFO globale (priorità: media, costo: 1 giorno)
[grid_bot.py:755-756](bot/strategies/grid_bot.py#L755-L756) confronta `price` con `avg_buy_price`. Sostituire con il **costo del lotto FIFO più vecchio** ancora in coda (cioè il primo lotto che effettivamente uscirebbe dal wallet). Il bot smette di vendere lotti realmente in perdita pensando di essere in profitto. Modifica chirurgica, dovrebbe essere una decina di righe.

Questo è il vero gating per mainnet. Senza, il bot continuerebbe a "vendere bene" sulla sua contabilità interna ma a "vendere male" sul wallet vero.

### 3. Layer di riconciliazione Binance (priorità: bassa fino a mainnet, costo: 2–3 giorni)
Già nell'eredità del report 03/05. Quando andremo live, un job che fetcha `Binance.fetch_my_trades()` come ground truth e segnala drift > soglia. Su paper testnet non ha senso (testnet trades non sono "veri"), ma il design può essere abbozzato adesso.

---

## Cosa chiedo al CEO

1. **Conferma** che il numero da privilegiare nel reporting al pubblico è l'equity P&L (proposta 1), non il FIFO realized.
2. **Decisione** se la modifica del bot (proposta 2) entra nella roadmap pre-mainnet o se si valuta solo dopo aver osservato il drift su altre 2 settimane di paper.
3. **Awareness** che il `+$52.69` della home è oggi sovrastimato di ~$5 (10%) rispetto a Binance. Non è bug, è un limite della formula. Il numero corretto sarebbe **+$48.16**.

Il CEO conosce già il pattern dal report 03/05 (`session 55`) — questa è la naturale estensione: il FIFO realized è migliore del DB realized, ma non è ancora il numero finale. L'equity P&L lo è.

---

## Cosa NON abbiamo toccato

- Nessun commit di codice oggi. Solo investigazione + brief. Tutti i numeri vengono da query SQL live + ticker Binance live.
- Nessuna modifica alla dashboard, ai report Telegram, al bot.
- Le memorie [project_fifo_fix_53a.md](memory) e [feedback_one_source_of_truth.md](memory) restano valide. Questo brief le **estende**: la "single source of truth" oggi è FIFO realized, ma per essere veramente allineata con Binance serve l'equity P&L.

---

**Stato:** investigazione chiusa, codice non toccato. Aspetto decisione del CEO su priorità delle 3 proposte prima di procedere.
