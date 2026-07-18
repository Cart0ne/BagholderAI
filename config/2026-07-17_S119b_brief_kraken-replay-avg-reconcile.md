Brief S119b — kraken-replay-avg-reconcile — 2026-07-17

**Tipo:** indagine **read-only**. Nessun codice, nessun restart, nessun ordine.
**Base:** `PROJECT_STATE.md` corrente (`git pull` all'apertura).
**Sorgenti:** `config/2026-07-16_S119_RforCEO_kraken-fase2a.md`, `config/2026-07-16_S119_runbook_kraken-ordine-prova.md`, `bot/grid_runner.py`, `bot/exchanges/kraken_client.py`, moduli grid (replay avg-cost / boot reconcile).

---

## 0. Contesto

Il primo ordine reale su Kraken è passato il **17/07 alle 18:45** (`OCILGP-2GRMI-D3WSNK`, BUY 0,00039379 BTC @ $63.483,50, fee $0,19999 USD). Il fix critico ha funzionato: `fill confirmed via fetch_order after 3.1s`, un solo BUY, nessun loop.

**Il bot è tuttora acceso e sorvegliato**, in attesa del SELL a +2%. La riga `BTC/USD / kraken / cycle=kraken_test` è a `is_active=false`, gira a mano con `KRAKEN_TEST_MODE=1`.

Prima di autorizzare qualsiasi riavvio di quel processo, il CEO ha tre domande a cui **solo il codice** può rispondere. Sono tutte a costo zero: si leggono, non si eseguono.

**Perché non le testiamo e basta:** il riavvio col gate chiuso (`ALLOW_REAL_MONEY=false`) non è utilizzabile come test — il bot si rifiuta di partire (runbook §3) e il gate viene valutato ~6s **prima** che il replay stampi. Quindi l'unico riavvio possibile è con soldi veri abilitati. Se il replay è rotto, quel riavvio produce un **secondo BUY reale da $25** non voluto (il primo boot loggava `Buy trigger: immediate (no reference — first entry)` proprio perché `holdings=0`). Da qui: si legge il codice prima.

---

## 1. Domanda 1 — il replay ritrova il trade Kraken? 🔴

Il boot del 17/07 loggava `No v3 trades found — _last_trade_time stays None` e `Avg-cost state restored: holdings=0.000000`.

Ora a DB esiste questo trade:

- `id` = `07519506-b2ba-4b04-a544-85a57d578e0b`
- `symbol='BTC/USD'` · `cycle='kraken_test'` · `config_version='v3'` · `side='buy'`
- `amount=0.00039379` · `price=63483.50` · `cost=24.99916746` · `fee=0.19999` · `fee_asset='USD'`

**Rispondi:**
- a) Su quali colonne filtra esattamente il replay avg-cost al boot?
- b) Con la riga `bot_config` attuale (`BTC/USD` / `kraken` / `kraken_test`), il replay **trova** quel trade e ricostruisce `holdings=0.00039379` + `avg_buy` coerente? Sì / no / a quali condizioni.
- c) Se **non** lo trova: cosa succede al primo tick? Confermi lo scenario "first entry → buy immediato"?

## 2. Domanda 2 — `avg_buy` include la fee di acquisto? 🟠

Divergenza fra due tuoi documenti:

- **Report:** trigger SELL ≈ **$64.753**. Ricalcolo: 63.483,50 × 1,02 = **64.753,17** → implica `avg_buy` = **prezzo puro**, fee esclusa.
- **Runbook §4:** *"l'avg del bot deve riflettere prezzo **+ fee reale in USD**"* → implica `avg_buy` ≈ 63.991,36 → trigger ≈ **65.271**.

Delta ~$518 (0,8%). Non è cosmetico: determina il margine netto.

- avg = prezzo puro → SELL a +2% → netto **0,39%** (break-even reale post-fee = +1,61%)
- avg = prezzo + fee → netto **~1,19%**

**Rispondi:** qual è il comportamento **del codice** (non della documentazione)? Cita il punto in cui `avg_buy` viene calcolato e dove viene applicato `sell_pct`. Se i due documenti divergono, **quale dei due è sbagliato** e va corretto.

> Questa risposta è **input diretto del nodo 5** (margine floor `profit_target_pct`). La tua proposta di 0,4% ha senso solo se sappiamo su cosa si misura il 2%.

## 3. Domanda 3 — il boot reconcile su venue Kraken interroga chi? 🟠

Log del 17/07, con `Venue: kraken`:

```
Boot reconcile OK: replayed=0.000000 vs Binance=0.000000 (gap=+0.000000 BTC)
Holdings synced from Binance: BTC=0.0
```

L'hai classificato **cosmetico** ("etichetta hardcoded, holdings letti correttamente = 0").

**Obiezione del CEO:** quel test non è falsificabile. Al boot gli holdings erano `0` su Kraken **e** `0` su Binance testnet. `0 = 0 → OK` è compatibile sia con "etichetta sbagliata, sotto legge Kraken" (innocuo) sia con "interroga davvero Binance" (**il reconcile su Kraken è cieco**). Il test passa in entrambi i casi, quindi non prova nulla. E il pattern "codice che assume Binance implicitamente" ci ha già morso due volte: cycle-fetch (S118 🟠) e superfici sito (S119 🟠).

**Rispondi:** sul percorso `venue=kraken`, il reconcile chiama il client **della venue della riga** o un client Binance? Se è solo l'etichetta → dimostralo indicando il punto del codice. Se non lo è → è un **finding**, non un cosmetico, e va in PROJECT_STATE §5.

---

## 4. OFF-LIMITS (nessuna eccezione)

- ❌ **Nessuna modifica di codice.** Questo brief è diagnosi. Il fix, se serve, è un brief separato.
- ❌ **Nessun restart** del bot di test né della flotta testnet. Il processo Kraken è acceso e sorvegliato: **non toccarlo**.
- ❌ **Nessun ordine**, reale o validate.
- ❌ **Nessuna modifica a `bot_config` o `trades`.** Le migrazioni Supabase le applica il CEO via MCP.
- ❌ **Non cancellare la riga** `BTC/USD / kraken` (runbook §7.3 lo propone: **sospeso finché il ciclo è aperto** — con $25 di BTC in pancia la cancellazione orfaneggia la posizione).

## 5. Delega / escalation

- **Deleghi a te:** lettura codice, verdetto tecnico, indicazione dei punti esatti.
- **Escali a Max (via CEO):** qualsiasi risposta che implichi toccare il processo acceso o i soldi sul conto.
- **Se scopri un blocker** (replay rotto / reconcile cieco): fermati, riportalo, **non fixarlo qui**. Serve un brief con la decisione di Board sulla Fase 2b.

## 6. Output atteso

`config/2026-07-17_S119b_RforCEO_kraken-replay-avg-reconcile.md` — SCOPE **identico**, push diretto su main.

Contenuto: le 3 risposte, ciascuna con **verdetto + punto di codice**. Dove non sei certo scrivi **"indeterminato"** — è la risposta giusta quando è vera, e mi serve più di una certezza costruita. Chiudi con: **il riavvio del processo di test è sicuro sì/no**.

## 7. Auto-obiezione del CEO (anti-assenso)

Questo brief potrebbe essere **teatro della prudenza**. L'evidenza a DB è già buona: il trade è `v3`, sul `cycle` giusto, ben formato — cioè il replay ha esattamente ciò che il log diceva gli mancasse. Probabilità che la D1 sia un problema: bassa. Il rischio coperto sono $25 su un progetto che ne ha bruciati di più in token in questa sessione, e ti sto costando una lettura di codice per confermare quello che già sospetto.

**Perché lo mando lo stesso:** la D2 non è prudenza, è un **numero che non torna** fra due tuoi documenti e che decide il nodo 5 — quella va risolta comunque. La D3 è un finding che hai chiuso come cosmetico su un test non falsificabile. La D1 viaggia gratis con le altre due.

**Ma se ritieni che la D1 sia banale, dillo e liquidala in due righe.** Non voglio pagine su un non-problema.

## 8. Obbligo di obiezione (CC)

Prima di rispondere: **almeno un'obiezione tecnica reale** a questo brief. Se pensi che il CEO stia inseguendo un fantasma su una delle tre, argomentalo. Se pensi che manchi una quarta domanda che conta di più, dilla. "Nessuna obiezione" è una risposta accettabile **solo** se motivata.
