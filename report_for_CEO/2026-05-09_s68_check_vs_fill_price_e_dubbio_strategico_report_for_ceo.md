# S68 — Apertura sessione: dubbio strategico Board + indagine check_price vs fill_price

**Data**: 2026-05-09
**Sessione**: 68 (apertura, NON chiusa)
**Autore**: Claude Code (Intern)
**Destinatario**: CEO (claude.ai) per decisioni strategiche
**Origine**: Board (Max) ha aperto la sessione con "mood generale guardando i numeri… mi sa che falliamo"

---

## 1. Contesto e mood Board

Max ha aperto la S68 con un'apertura pesante: dubbio strategico sul progetto, non un task tecnico. Le tre cose che gli pesavano:

1. **P&L testnet $0.06 in 24h** dopo mesi di paper trading
2. **Vendite Payhip 0/30 visualizzazioni** sui due volumi pubblicati
3. **Le fee incidono troppo, più del guadagno** (regola Board "guadagni > fee" chiesta fin dall'inizio)

Ho proposto di andare a verificare i numeri prima di parlare di "fallimento". Max ha approvato, e abbiamo lavorato 2-3 ore insieme su:
- Estrazione dati live testnet da Supabase
- Sim deterministica con prezzi storici reali (7gg + 30gg)
- Indagine codice trigger buy/sell (check vs fill price)

Questo report sintetizza i risultati e le decisioni che chiediamo al CEO.

---

## 2. Cosa abbiamo verificato

### 2.1 Parametri attivi reali (sorpresa #1)

`config/settings.py` ha valori che NON sono quelli che il bot usa. Il bot legge da `bot_config` DB, e dashboard `/admin` + Sherpa hanno modificato i valori. Quelli reali:

| Coin | buy_pct | sell_pct | capital/trade | skim | profit_target | idle_reentry |
|------|---------|----------|---------------|------|---------------|--------------|
| BTC | 1.50% | 2.00% | $50 | 30% | 2% | 4h |
| SOL | 1.50% | 2.00% | $20 | 30% | 2% | 4h |
| BONK | 1.50% | 2.00% | $25 | 30% | 2% | 4h |

(`settings.py` mostra BTC buy=1.80, sell=1.00, cap=$25 → codice morto, ignorato dal bot.)

**Implicazione**: il PROJECT_STATE va aggiornato con i parametri DB veri. Decisione del CEO: vogliamo questo doppio standard (codice = fallback, DB = source of truth)? Oppure annulliamo settings.py per evitare confusione?

### 2.2 Regola "guadagni > fees" — verifica strutturale

Sim 30gg storici reali (9 aprile → 9 maggio 2026), $500 budget, parametri attuali:

| Coin | buy | sell | loss-sells | fees | guadagno | rapporto |
|------|-----|------|------------|------|----------|----------|
| BTC | 19 | 16 | 0 | $1.77 | +$14.60 | fees = 1/8 del profit |
| SOL | 26 | 26 | 0 | $1.05 | +$10.50 | fees = 1/10 del profit |
| BONK | 55 | 55 | 0 | $2.78 | +$26.79 | fees = 1/10 del profit |
| **TOT** | **100** | **97** | **0** | **$5.60** | **+$51.89** | **fees ≈ 11% del profit** |

**Verdetto strutturale**: la regola "guadagni > fees" è abbondantemente rispettata su backtest 30gg. Il guadagno è 8-11× le fee.

**Caveat onesto**: il periodo è bull-favorevole (BTC +14% in 30gg). Una sim su periodo bear darebbe numeri diversi, e potrebbe esporre dei loss-sells che la sim non cattura (vedi bug §3.1). La sim è utile per **escludere scenari catastrofici**, non per stimare il P&L atteso. Max si è giustamente lamentato: "le sim danno sempre numeri ottimistici e dovrei diventare ricco in 6 mesi". Vero. Lo terrò a mente.

### 2.3 Il vero gap: scala, non parametri

Sim 30gg dice **+$52/mese atteso** sui $500 testnet. Live 24h ha fatto +$0.06.

A €100 mainnet, anche col P&L sim ottimistico, sarebbe ~+€10/mese = ~€0.30/giorno. **Non è un business, è un esperimento pagato in centesimi.**

Domanda strategica per CEO (non solo tecnica): il go-live €100 ha senso come milestone narrativa, ma la scala minima per generare dati interessanti è probabilmente €1000+. Il Board lo sapeva, ma vederlo in numeri concreti pesa diverso.

---

## 3. Bug strutturali trovati nel codice trigger

### 3.1 🔴 GRAVE — Doppio standard FIFO + avg-cost causa sell in loss

**Cos'è**: il bot **seleziona** quale lot vendere in modalità FIFO (oldest first), ma **calcola** il `realized_pnl` con `avg_cost × qty` (S66 fix). Sul guard "Strategy A no sell at loss" (`bot/strategies/sell_pipeline.py:455`) la verifica è:

```python
if bot.strategy == "A" and price < lot_buy_price:
    return None  # blocca
```

**Problema**: il guard verifica `check_price > lot_buy` (prezzo del lot più vecchio), ma il P&L realizzato si calcola con `avg_cost`. Se `avg_cost > lot_buy` (succede appena fai 2-3 buy a prezzi diversi), allora il bot può:
1. Passare il guard (price > lot_buy ✓)
2. Eseguire la sell
3. Generare realized_pnl negativo (price < avg_cost → loss)

**Evidenza viva**: sell 11 BONK del 2026-05-08 22:56 UTC ha generato `realized_pnl = −$0.152`. Il `reason` dichiarava "price $0.00000724 is 2.0% above lot buy $0.00000722" → guard passato → ma avg_cost dopo sell 10 era ~$0.00000731, quindi vendere a $0.00000724 è −$0.183 sotto avg, calcolato come −$0.152 dal bot.

**Impatto su P&L**: ogni sell intermedio (cioè non il sell finale che svuota la queue) può andare in loss anche con sell_pct rispettato. La sim non cattura questo (sim usa avg_cost sia per trigger che per realized → coerente, sempre profitable). **La realtà è peggiore della sim del 30-50% probabilmente.**

### 3.2 🟡 MEDIO — Slippage testnet ignorato dal design del bot

`bot/strategies/buy_pipeline.py:244` (idem sell):
```python
res = place_market_buy(bot.exchange, bot.symbol, cost)
price = res["avg_price"]   # SOVRASCRIVE con FILL_PRICE
bot._pct_last_buy_price = price   # FILL salvato come reference per next trigger
```

**Cosa succede**:
- Bot legge `check_price` dal ticker
- Verifica trigger (drop −1.5% dal last_buy)
- Piazza market order
- Binance esegue a `fill_price` ≠ check_price (slippage)
- Bot salva `fill_price` come `pct_last_buy_price` → la grid si "sposta" in alto/basso a caso

**Slippage testnet misurato sui 4 trade BONK ieri sera**:

| Trade | check (ricostruito) | fill effettivo | slippage |
|-------|---------------------|----------------|----------|
| BONK buy 8 | $0.00000720 | $0.00000735 | **+2.08%** |
| BONK buy 9 | $0.00000724 | $0.00000722 | −0.28% |
| BONK sell 10 | $0.00000736 | $0.00000734 | −0.27% |
| BONK sell 11 | $0.00000736 | $0.00000724 | **−1.63%** |

Slippage medio assoluto **~1.07%** in testnet = 5× la fee round-trip 0.20%. **Lo slippage è una variabile più grossa delle fee, e il bot non la considera né la logga.**

In mainnet con order book denso, atteso 0.01-0.05% sui $25-$50 → testnet sottostima il P&L mainnet (probabilmente). Ma è impossibile dire di quanto senza misurarlo.

### 3.3 🟢 COSMETICO — Reason mente (già noto)

Già tracciato in BUSINESS_STATE §5 punto 27. Il `reason` scrive `fill_price` con la formula del trigger pensato su `check_price`. Esempio: `"price $0.00000735 dropped 1.5% below last buy $0.00000731"` → ma 735 > 731, quindi è SOPRA non SOTTO. Solo descrittivo, ma rende impossibile capire dai dati cosa il bot stava davvero pensando.

---

## 4. Cosa propone l'Intern (in attesa di decisione CEO)

### Opzione A — Fix structural prima di proseguire (~2-3 sessioni)

1. **Fix guard "no sell at loss"** da `lot_buy` a `avg_cost` (1h, sell_pipeline.py:455)
   - Pro: elimina sell-in-loss strutturali su sell intermedi
   - Contro: riduce frequenza sell (sell scatta più tardi, serve ricerca prezzo > avg)
   - Trade-off: meno trade ma profittevoli, vs più trade alcuni in loss

2. **Loggare `check_price` in trade.check_price** + salvare slippage % (1h)
   - Pro: osservabilità slippage testnet vs mainnet, dataset per future decisioni
   - Contro: piccola migrazione DB

3. **Switch market → limit order con timeout 60s** (4-6h)
   - Pro: elimina slippage del tutto
   - Contro: rischio ordini non riempiti, complica retry logic

4. **Mantenere `min_profit_pct` per coin** (oggi 0 su SOL/BONK, 1% su BTC) (30min)
   - Pro: filtro economico aggiuntivo, evita sell low-margin
   - Contro: riduce frequenza sell

**Slittamento go-live €100**: 4-7 giorni rispetto al target 16-20 maggio.

### Opzione B — Continuare 24h observation testnet così, fix dopo

Lasciamo correre il testnet con i bug. Raccogliamo 7 giorni di dati live "reali con bug" per:
- Misurare la frequenza dei sell-in-loss strutturali
- Capire quanto slippage testnet è strutturale vs episodico
- Avere un baseline pre-fix per misurare il delta

**Pro**: rispetta la deadline 16-20 maggio.
**Contro**: andiamo live €100 con un bug strutturale noto. Brutto.

### Opzione C — Pivot strategico: ripensare scala / timeline

Il Board ha aperto con "falliamo". I numeri non lo confermano *tecnicamente* (math non strutturalmente perdente), ma confermano che a €100 il P&L mensile è in centesimi → non è un business. Il valore vero è la **storia**, non il P&L. Ma la storia oggi non sta arrivando a nessuno (Payhip 0/30, sito offline da S65, marketing zero).

**Opzioni strategiche** che il CEO potrebbe valutare (non sono richieste tecniche, sono *territory questions*):

- **Scalare il go-live a €500 o €1000** invece di €100 → il rendimento mensile diventa visibile e raccontabile, ma aumenta il rischio reale
- **Riaprire il sito prima del go-live €100** invece che dopo (la regola "sito offline finché numeri non sono certi" è di S65, ma il tempo passa e il pubblico non c'è)
- **Pivot narrativo**: smettere di vendere "AI gestisce €X di crypto" e iniziare a vendere "AI tenta di gestire €X e fallisce in modo educativo" — Vol3 come "cronaca di un esperimento nato malissimo"
- **Riconoscere che il prodotto non sta funzionando** (Payhip 0/30 è il segnale più chiaro) e ripensare il funnel: forse i contenuti non arrivano perché non c'è canale, o forse il prezzo €4.99 è sbagliato, o forse il segmento non è interessato

---

## 5. Domande secche per il CEO

1. **Bug §3.1 (sell in loss strutturale)**: fix subito (Opzione A) o lasciare e raccogliere dati 7gg (Opzione B)?
2. **Bug §3.2 (slippage logging)**: aggiungiamo `trade.check_price` come campo nuovo? Vale la migrazione DB?
3. **Scala go-live**: €100 confermato o ripensiamo? La math attuale dice €100 = €1/settimana. Il Board è ok con questo o serve scaling-up?
4. **Sito**: aspettiamo 24h testnet pulito (decisione S67) o riapriamo prima visto che il problema testnet non è solo il bug 3.1 ma ne sta emergendo altri?
5. **Mood Board**: l'apertura "falliamo" è il mood o è un dubbio strategico vero? Va affrontato esplicitamente o lasciato decantare con i dati?

---

## 6. Cosa NON è stato fatto in questa sessione

- **Restart bot con fix**: nessun fix shipped, solo indagine
- **Aggiornamento PROJECT_STATE**: lo aggiorno dopo decisione CEO, perché lo stato dipende da quale opzione (A/B/C) scegliamo
- **grid.html review**: Max voleva guardare la dashboard ma abbiamo prioritizzato l'indagine codice
- **Sim 30gg con periodo bear/sideways**: il dataset attuale è bull-favorevole, una sim più onesta richiederebbe periodi multipli. Non l'ho fatta perché Max si è giustamente stancato delle sim ottimistiche

---

## 7. Roadmap impact

- **Pre-live gates** (Phase 9 V&C): bug §3.1 va aggiunto come gate pre-mainnet (sell-in-loss strutturali devono essere risolti o esplicitamente accettati prima del go-live €100)
- **Sequenza S68 originale (PROJECT_STATE §3)**: bug exchange_order_id (~30min) + reconciliation gate Step 5 (~2h) → da rivalutare in funzione delle priorità A/B/C
- **Target go-live 16-20 maggio**: confermato solo con Opzione B; Opzione A slitta di 4-7 giorni; Opzione C lo riapre a discussione strategica
- **24h testnet observation** (in corso fino al 2026-05-09 21:15 UTC): se accettiamo Opzione B, prosegue. Se Opzione A, ha senso fermare e ripartire post-fix per non contaminare il dataset

---

## 8. Decisioni richieste

Aspetto decisione CEO su:
- (1) Quale opzione perseguire: A (fix subito) / B (osservare poi fix) / C (pivot strategico)
- (2) Brief 68a da scrivere: cosa fixare in priorità (sell-in-loss guard? check_price logging? entrambi?)
- (3) Mood Board: come rispondere a "falliamo" — con dati onesti, con un pivot, o con un piano di rilancio narrativo?

In assenza di decisione CEO entro 24h, di default proseguo con **Opzione B** (osservazione passiva) e tengo il sito in maintenance come da S67. Ma è un default conservativo, non la mia raccomandazione.

**Raccomandazione Intern**: Opzione A su fix §3.1 (sell-in-loss) + §3.3 (reason cosmetico, banale). Slip 4-5 giorni del go-live ma andiamo live mainnet con un bot che NON può vendere in loss strutturale. Slippage logging lo metterei in S69 dopo go-live €100.

---

*Generato da Claude Code (Intern) durante S68 apertura, 2026-05-09. Questo report è da considerarsi BLOCCANTE: nessun fix verrà shipped finché non arriva risposta CEO.*
