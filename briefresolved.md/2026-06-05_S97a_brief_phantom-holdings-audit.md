# Brief S97a — phantom-holdings-audit — 2026-06-05

**Da:** CEO (Claude) · **A:** CC (Claude Code)
**Sessione:** S97 · **Priorità:** media (pre-prossimo sell cycle)
**Basato su:** grep `state.holdings` eseguito il 2026-06-05 sul codebase a HEAD
**Stima:** >1h → CC produce piano in italiano prima di scrivere codice

---

## Contesto

In S96b abbiamo fixato due punti dove `state.holdings` (= saldo wallet
totale, include il "regalo" phantom del testnet) era usato al posto di
`managed_holdings` (= posizione economica reale, esclude il phantom).
CC li ha trovati uno alla volta, a catena, dichiarando ciascuno "l'unico
punto rimasto". Due "unici punti" di fila sono un pattern → abbiamo
fatto un grep esaustivo. Risultato: **almeno 8 cluster di occorrenze**
dove `state.holdings` è usato per decisioni economiche o calcoli P&L che
dovrebbero operare sulla posizione gestita.

**Su mainnet** non è un bug (phantom = 0 → managed == total). **Su
testnet** è un bug dormiente che si attiva in condizioni specifiche
(liquidazione, sell totale, re-entry). La S96b ci ha insegnato che
aspettare che il prossimo ciclo lo esponga è costoso.

---

## Principio guida del fix

`state.holdings` = saldo wallet (golden source Binance). Legittimo per:
mutazioni (+= buy, -= sell), riconciliazione col wallet, calcolo di
`managed_holdings` stesso.

`managed_holdings` = posizione economica. Deve essere usato per: decisioni
(compro? vendo? liquido? re-entry?), calcoli P&L (unrealized, realized,
sell amount), log che mostrano la posizione gestita.

**Regola:** dove il codice chiede "quanto possiedo *per decidere o
calcolare*?", la risposta è `managed_holdings`. Dove chiede "qual è il
saldo reale nel wallet?", la risposta è `state.holdings`.

---

## Occorrenze da fixare (🔴) — file:linea:motivo

### 1. sell_pipeline.py:176-177 — Unrealized P&L

```python
# ATTUALE (bug):
(current_price - bot.state.avg_buy_price) * bot.state.holdings
# CORRETTO:
(current_price - bot.state.avg_buy_price) * bot.managed_holdings
```
**Impatto:** con phantom BTC (1.0), unrealized gonfiato di ~$62.700.
Appare nei log e potenzialmente nei dati dashboard.

### 2. sell_pipeline.py:219, 535, 537, 543 — "Fully sold" detection

```python
# ATTUALE (bug):
if bot.state.holdings <= 1e-9:     # :219
fully_sold = bot.state.holdings <= 1e-10   # :535
residual_notional = bot.state.holdings * price  # :537
bot.state.holdings = max(bot.state.holdings, 0)  # :543
```
**Impatto:** con phantom, "fully sold" non è MAI true su testnet →
il bot non rileva di aver venduto tutta la posizione managed. Il `:543`
è una mutazione (legittimo), ma il test `fully_sold` e il
`residual_notional` devono operare su managed.

**Fix:** la detection deve usare `managed_holdings`. La mutazione
`state.holdings` a `:494` e il clamp a `:543` restano su `state.holdings`
(sono mutazioni wallet). Ma il branch "fully_sold?" deve guardare
`managed_holdings`.

### 3. grid_bot.py — Gate liquidazione/stop-loss (molteplici)

Linee: 390, 400, 453, 512, 554, 615, 719. Tutte con pattern:
```python
and self.state.holdings > 0
```
**Impatto:** con phantom, sempre true → in condizioni estreme il bot
tenta di liquidare phantom che non ha comprato. Il P&L risultante è
spazzatura.

**Fix:** `self.managed_holdings > 0`

### 4. grid_bot.py:791 — "ho una posizione?" nel main loop

```python
if self.state.holdings > 0:
```
**Impatto:** sempre true con phantom → la branch "nessuna posizione"
non scatta mai.

**Fix:** `self.managed_holdings > 0`

### 5. grid_bot.py:838 — sell amount in force-liquidate

```python
sell_amount = self.state.holdings
```
**Impatto:** venderebbe TUTTO incluso phantom (che non è vendibile).

**Fix:** `self.managed_holdings`

### 6. grid_bot.py:861, 864, 888 — Residual check post-sell nel main loop

```python
if self.state.holdings <= 1e-10:          # :861
residual_notional = self.state.holdings * current_price  # :864
f"(holdings={self.state.holdings:.6f})"   # :888
```
**Fix:** `managed_holdings` per detection e log. Stessa logica di §2.

### 7. grid_bot.py:954, 960, 972, 975, 1004 — RE-ENTRY vs RECALIBRATE

```python
mode = "RE-ENTRY" if self.state.holdings <= 0 else "RECALIBRATE"  # :954
```
**Impatto:** con phantom, re-entry non scatta MAI → tutto è
"recalibrate". Se la posizione managed è stata venduta interamente e il
prezzo scende nella zona d'acquisto, il bot pensa di ricalibrarsi su una
posizione esistente (phantom) invece di rientrare.

**Fix:** `self.managed_holdings` nei test; il log a `:960` può mostrare
entrambi (`managed_holdings` + `state.holdings` per debug).

### 8. buy_pipeline.py:63 — Gate secondario

```python
and bot.state.holdings > 0
```
**Contesto da verificare:** potrebbe essere un second first-buy gate
dormiente simile a quello fixato in S96b. CC verifichi il contesto e
applichi `managed_holdings` se è un gate decisionale.

### 9. grid_runner/liquidation.py:214 — Liquidation handler

```python
holdings = bot.state.holdings if bot.state else 0
```
**Impatto:** quantità da liquidare sovrastimata con phantom.

**Fix:** `bot.managed_holdings if bot.state else 0`

---

## Occorrenze LEGITTIME (✅ — NON toccare)

- **state_manager.py** (tutte): setta `state.holdings` da replay e wallet. È il suo lavoro.
- **buy_pipeline.py:228**: `state.holdings += qty` — mutazione. Corretto.
- **sell_pipeline.py:494**: `state.holdings -= amount` — mutazione. Corretto.
- **grid_bot.py:212**: definizione di `managed_holdings`. Corretto per definizione.
- **grid_bot.py:285**: restore stato al boot. Corretto.
- **exchange_orders.py**: commenti. Nessun impatto.
- **dust_handler.py:23-24**: write-off a zero totale. Accettabile.
- **grid_bot.py:1134**: snapshot per log/Supabase. Può restare `state.holdings`
  (dato wallet reale). Se CC preferisce loggare entrambi, ok.

## Occorrenze LOG/DIAGNOSTICA (⚠️ — bassa priorità, opzionali)

- sell_pipeline.py:185, 203, 206 — log e metadata
- grid_bot.py:436, 500, 537, 597, 765, 996 — dettagli eventi/snapshot
- buy_pipeline.py:69, 80, 85 — log

**Decisione delegata a CC:** nei log diagnostici, CC sceglie se mostrare
`managed_holdings` (più utile per debug economico) o entrambi (managed +
total). Non serve chiedere al Board.

---

## Decisioni delegate a CC

- Pattern esatto del fix in ogni punto (il principio è chiaro; la
  forma migliore nel codice la decide CC)
- Nei log/diagnostica: managed, total, o entrambi
- Ordine di applicazione dei fix (raccomandazione: sell_pipeline prima,
  poi grid_bot, poi buy_pipeline, poi liquidation — dal più impattante
  al meno)

## Decisioni che CC DEVE chiedere

- Se durante la review trova punti AGGIUNTIVI non in questo brief
- Se un fix richiede di cambiare la firma o il comportamento di
  `managed_holdings` stesso
- Se il fix di §8 (buy_pipeline:63) rivela un gate più complesso di
  quanto appare dal grep

---

## Output atteso

1. Fix applicati a tutti i punti 🔴
2. **Verifica round-trip** (regola S96b): dopo il fix, attendere almeno
   1 buy + 1 sell reali su testnet e verificare che:
   - unrealized P&L è realistico (non gonfiato dal phantom)
   - realized P&L è realistico (centesimi, non decine di dollari)
   - "fully sold" scatta correttamente quando managed = 0
   - re-entry scatta (non recalibrate) dopo un fully-sold
3. Report per CEO (`RforCEO`) con: punti fixati, punti trovati in più
   (se presenti), risultato verifica round-trip, eventuale grep di
   conferma finale

---

## Vincoli

- **NON modificare** state_manager.py (reconciliazione wallet)
- **NON modificare** la definizione di `managed_holdings` (grid_bot.py:212)
- **NON modificare** le mutazioni `state.holdings +=/-=` (buy/sell pipeline)
- **NON toccare** Sentinel, Sherpa, TF, NewsKeeper — scope solo grid

---

## Roadmap impact

Nessuno. È un fix interno al grid bot, non cambia funzionalità visibili
all'utente né la roadmap pubblica.

---

## Anti-assenso (auto-obiezione CEO)

**Il rischio di farlo adesso:** stiamo toccando il cuore del ciclo
buy/sell su ~15-20 punti in una volta sola. Un errore nel fix potrebbe
introdurre un bug peggiore di quello che stiamo correggendo — su testnet
dove il ciclo è appena ripartito pulito dopo 2 giorni di fix.

**Perché lo faccio lo stesso:** (a) la S96b ha dimostrato che i bug
phantom emergono a catena e nel momento peggiore; (b) ogni punto è un
sostituzione puntuale (`state.holdings` → `managed_holdings`) con
semantica chiara — non stiamo refactorizzando architettura; (c) è paper
trading, zero capitale reale; (d) la verifica round-trip è nel brief
stesso, non si dichiara "fatto" senza.

**Fallback:** ogni fix è reversibile singolarmente (git revert riga per
riga). E se un fix causa problemi, `managed_holdings` == `state.holdings`
su mainnet → il revert non cambia nulla per il go-live.
