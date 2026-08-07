Brief S125 — kraken-fase3-execution — 2026-08-07

**Da:** CEO
**A:** CC
**Origine:** `20260806_krakenfase3piano_note_for_ceo.md` (S124), approvato dal Board con modifiche zero.
**Natura:** esecuzione operativa. **Nessuna modifica al comportamento dei bot.** Si cambia il venue su cui operano, non come operano.

---

## 0. Perimetro — leggere prima di toccare qualsiasi cosa

Questo brief NON contiene:

- modifiche a logica di trading, sell ladder, LAST SHOT, calcolo fee
- nuovi parametri (`profit_target_pct` resta **0** su tutte le righe, come oggi)
- ricalibrazioni di `buy_pct` / `sell_pct` (già netti-fee e per-venue, collaudati)
- rinomina del ciclo (`kraken_2b` resta `kraken_2b` — è Fase 3 solo nella narrazione, §5d della nota accolta)

Se durante l'esecuzione emerge la tentazione di "sistemare anche questo", **si ferma e si chiede**. Il valore di questa sessione è che l'unica variabile che cambia è l'exchange.

---

## 1. Precondizione bloccante

**Capitale su Kraken ≥ $400.** Max versa oggi.

I Passi 2 e 3 **non partono** finché il saldo non è confermato. Un `capital_allocation` a $250 con $100 sul conto produce ordini rifiutati dall'exchange su denaro reale.

Verifica del saldo: da fare **quando il grid non ha un ordine in volo** (l'ultimo trade è del 28 luglio, la posizione è ferma — la finestra è ampia, ma si guarda `bot_runtime_state.updated_at` prima di chiamare).

---

## 2. Stato di partenza rilevato (DB, 2026-08-07 ~09:00 UTC)

| riga | venue | ciclo | attiva | allocation | lotto | note |
|---|---|---|---|---|---|---|
| BTC/USDT | binance | testnet_2 | sì | $200 | $50 | da spegnere |
| SOL/USDT | binance | testnet_2 | sì | $150 | $20 | da spegnere |
| BONK/USDT | binance | testnet_2 | sì | $150 | $25 | da spegnere |
| ETH/USDT | binance | testnet_2 | sì | $46,67 | $15,56 | `managed_by='tf_grid'` — da spegnere |
| **BTC/USD** | **kraken** | **kraken_2b** | **sì** | **$100** | **$33,33** | **resta viva, si alza** |

Stato posizione Kraken: holdings `0.00152221` BTC, costo medio `$64.745,65`, cassa disponibile **$1,44**, realized di ciclo **$0,00**, ultimo trade **28 luglio**. Il grid è al 98,6% investito e senza munizioni — questo è il motivo operativo del Passo 2.

---

## 3. Passi

Tutto in **una finestra sola**: il Passo 4 richiede comunque il riavvio.

### Passo 1 — spegnere i grid Binance
*(nessun riavvio)*

```
UPDATE bot_config SET is_active = false
WHERE venue = 'binance'
  AND symbol IN ('BTC/USDT','SOL/USDT','BONK/USDT','ETH/USDT');
```

L'orchestratore rilegge `is_active` ogni 30 secondi; i processi si chiudono da soli.

**Verificato in S124:** il meccanismo che resuscita i bot spenti con posizioni residue filtra su `managed_by='tf'`; la riga ETH è `managed_by='tf_grid'` → non viene riaccesa. **Riconfermare questo filtro prima di procedere** — se il filtro è cambiato, ETH torna su e il Passo 1 è inutile.

### Passo 2 — portare BTC/USD a regime

```
UPDATE bot_config SET capital_allocation = 250
WHERE symbol = 'BTC/USD' AND venue = 'kraken';
```

Tutto il resto della riga **invariato**: `capital_per_trade` resta $33,33, `buy_pct` 1,80, `sell_pct` 1,20, `skim_pct` 30, `stop_buy_drawdown_pct` 3, `profit_target_pct` 0, ciclo `kraken_2b`.

Effetto atteso: la cassa disponibile passa da $1,44 a **~$152** ($250 − $97,77 già investiti). La scala passa da 3 a **7 livelli** nominali. La posizione aperta non viene toccata, il costo medio non cambia, la storia del denaro reale non si interrompe.

### Passo 3 — aprire SOL/USD

Nuova riga `bot_config`, **parametri copiati identici dalla riga SOL/USDT Binance**:

| campo | valore |
|---|---|
| symbol | `SOL/USD` |
| venue | `kraken` |
| cycle | `kraken_2b` |
| is_active | `true` |
| managed_by | `grid` |
| capital_allocation | `150` |
| capital_per_trade | `20` |
| buy_pct | `2.25` |
| sell_pct | `1.50` |
| skim_pct | `30` |
| stop_buy_drawdown_pct | `3` |
| profit_target_pct | `0` |

Gli altri campi seguono il default della riga Binance corrispondente. Se un campo non ha corrispondenza sensata su Kraken, **si segnala prima di inventare un valore**.

### Passo 4 — riavvio orchestratore con `ENABLE_TF=false`

Ferma il Trend Follower (flag d'ambiente, richiede riavvio) e porta in volo il fix del report P&L `f98afbc`, già in repo ma non nei processi attivi.

### Passo 5 — verifiche

- [ ] processi attivi = **2 grid Kraken + Sentinel + Sherpa**. Niente TF, niente grid Binance
- [ ] primo tick a buon fine di entrambi i grid Kraken
- [ ] BTC/USD: cassa disponibile ~$152, holdings e costo medio **invariati** rispetto al pre-intervento
- [ ] SOL/USD: riga letta correttamente, nessun ordine inatteso al primo tick
- [ ] nessun ordine su Binance dopo lo spegnimento
- [ ] report serale coerente su entrambe le righe
- [ ] **a T+24h**: verificare che Sherpa non abbia riscritto parametri sulle righe Kraken in modo inatteso

---

## 4. Rollback

- Passi 1-3 sono `UPDATE`/`INSERT` su `bot_config`: reversibili invertendo i valori. Annotare i valori pre-modifica **prima** di scrivere.
- Passo 4 è reversibile riavviando con `ENABLE_TF=true`.
- **Non reversibile:** eventuali ordini eseguiti su Kraken dopo il Passo 2/3. Se qualcosa non torna al Passo 5, si spengono le righe Kraken (`is_active=false`) prima di indagare — la posizione resta in pancia, non si liquida niente per fretta.

---

## 5. Auto-obiezione

**SOL/USD parte con parametri mai testati su questo venue.** `buy_pct` 2,25 e `sell_pct` 1,50 vengono da un book Binance con commissioni allo 0,1%; su Kraken lo spread SOL è 0,014% (contro 0,000% di BTC) e la commissione 0,80%. La copia identica è coerente con la decisione del Board — non si cambia niente oggi — e `sell_pct` è già netto-fee per venue, quindi la compensazione avviene da sola. Ma è il punto del piano con meno evidenza sotto: BTC su Kraken ha 16 giorni di storia, SOL su Kraken ne ha zero.

**Non chiedo di cambiarlo.** Chiedo che il primo ciclo completo di SOL venga guardato con attenzione e riportato, invece di essere dato per riuscito perché "erano i parametri di sempre".

**Seconda obiezione, minore:** l'allocazione $250/$150 non ha una derivazione scritta da nessuna parte — è una scelta del Board sul capitale che è disposto a mettere in campo. Va bene così, ma va scritto che è quello, non un risultato di calcolo, altrimenti fra tre mesi qualcuno cercherà la formula che non esiste.

---

## 6. Difetto noto da girare a CC (non bloccante, non in questo brief)

Negli snapshot `bot_state_snapshots`, il campo `last_trade_at` riporta il timestamp dell'ultimo *recalibrate*, non dell'ultimo trade: al 7 agosto segna `07:31` di stamattina, mentre l'ultimo trade reale è del **28 luglio**. Cosmetico, ma falsa ogni lettura di "da quanto tempo questo bot non opera" — inclusa la nostra di oggi, se non avessimo incrociato con `trades`.

Da mettere in coda, non da sistemare in questa finestra.
