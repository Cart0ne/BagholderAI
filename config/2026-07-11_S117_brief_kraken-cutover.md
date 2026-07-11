Brief S117 — kraken-cutover — 2026-07-11

**Base:** PROJECT_STATE.md corrente (CC: `git pull` all'apertura — regola multi-macchina — e leggi la versione più recente).
**Sorgenti di contesto:** `config/APPROVED_golive_experiment_design.md` (§2 collaudo, §3 deployment), `config/2026-06-29_S112_brief_kraken-adapter.md` + `2026-06-29_S112_passo0_kraken-coupling-map.md` + `2026-06-29_S112_piano_kraken-adapter.md`, `config/settings.py` (`KrakenConfig`, flag `EXCHANGE`), `bot/exchanges/kraken_client.py` (adapter dormiente).
**Bot/Mac Mini:** il restart del cutover lo fa Max via runbook. NON riavviare tu.

---

## 0. Contesto e obiettivo

Le chiavi API Kraken sono state generate da Max e inserite in `config/.env` sul Mac Mini oggi (Withdraw **OFF**, WebSocket ON, nonce window 10000ms). L'adapter Kraken (`bot/exchanges/kraken_client.py`) è shippato ma **DORMIENTE** dietro flag `EXCHANGE` (default `binance`) da S112b.

Questo brief è il **CUTOVER** (task K.1 del MASTER_TASK_LIST): **cablare l'hot-path del grid al `KrakenClient`**, così che con `EXCHANGE=kraken` il grid tradi davvero su **Kraken USD** con soldi veri.

⚠️ **Questo è il momento in cui i soldi finti (Binance testnet) diventano soldi veri (Kraken live).** Massima cautela. **Nessun ordine reale prima che i dry-run `validate=true` siano tutti verdi** (§3).

**Task > 1h → PIANO PRIMA DEL CODICE.** Produci un piano in italiano leggibile da Max, che parte dalla coupling map di S112 (passo0) ed elenca esattamente quali call-site dell'hot-path grid vengono cablati e come. Approvazione di Max **prima** di scrivere codice.

---

## 1. Decisioni di Board già chiuse (NON riaprire)

- **Modello grid = A (ordini a mercato on-trigger)** — stesso comportamento del testnet validato 15gg. Fee taker 0,40%. [Board S117]. Il modello B (ladder a limiti maker 0,25%) è **rimandato a fase deployment come Caso 2** — non costruirlo qui.
- **Quote = USD**: `BTC/USD`, `SOL/USD`, `BONK/USD`. [S112b]
- **Collaudo €100 sequenziale**: BTC → SOL → BONK, **stesso €100 riciclato**, un ciclo buy→sell completo per moneta, uscita a giudizio di Max. [APPROVED §2]. Il collaudo è **grid puro** (niente TF).
- **Chiavi**: già in `.env`, nomi `KRAKEN_API_KEY` / `KRAKEN_API_SECRET`, Withdraw OFF.

---

## 2. Cosa deve fare il cutover (il COSA; il COME lo proponi tu nel piano)

**a) Cablaggio hot-path grid → `KrakenClient`.** Con `EXCHANGE=kraken`, il grid piazza/legge ordini via `KrakenClient` invece di Binance, usando la factory `ExchangeClient` già scaffoldata (S112 Fase 1). **Invariante S112 non negoziabile:** con `EXCHANGE=binance` il comportamento resta identico a oggi (testnet intatto, zero diff osservabile).

**b) Modello A (market) su Kraken.** Porta il market-order-on-trigger attuale sul path Kraken (`place_market_buy` / sell già in `kraken_client.py`). **NON** costruire il ladder a limiti.

**c) Risoluzione coppie via `AssetPairs` (no hardcode).** Risolvi `BTC/USD`, `SOL/USD`, `BONK/USD` → nome canonico Kraken (XBT/ZUSD ecc.) + `ordermin` + `pair_decimals`/`lot_decimals`. Serve per il floor (d) e per rispettare i minimi. **Non hardcodare i simboli a intuito.**

**d) Floor min-profit FEE-AWARE (il cuore trading-safety, Sherpa-managed).** Sul testnet la fee sintetica era 0,1%. Su Kraken con modello A è **0,40% taker per lato = 0,80% a giro tondo**. Il grid **non deve** vendere a un delta che non copra 2× la fee reale, o "vince" nominalmente e **perde in reale**. Il floor deve:
- leggere la fee **REALE** da Kraken (fee-tier + volume 30gg), **non** hardcodarla;
- essere un **parametro gestito da Sherpa** (come gli altri board params), non una costante nel codice;
- garantire `sell_price ≥ buy_price × (1 + 2×fee + margine minimo)`.

Questo probabilmente impone di **ricalibrare i passi della griglia** (oggi tarati per 0,1%: troppo stretti per 0,40%, perderebbero su ogni ciclo "vinto").

**e) Isolamento collaudo — UN grid alla volta.** Il collaudo gira **una moneta per volta** (€100 su BTC, poi SOL, poi BONK), **non** i 3 grid insieme. Serve un modo pulito per far girare SOLO il grid BTC su Kraken con €100, con SOL/BONK/TF fermi. **Proponi tu il meccanismo** (flag per-coin? config a singolo symbol?) e chiudilo nel piano con Max.

---

## 3. Scaletta test PRIMA di qualsiasi ordine reale (OBBLIGATORIA)

Kraken **non ha testnet spot** (verificato). La validazione pre-€100 è quindi solo sulla plumbing:

1. **Endpoint pubblici (no auth):** `Time` (clock sync — vitale per i nonce), `AssetPairs` (le 3 coppie esistono, risolvono, leggi `ordermin`).
2. **Auth read-only:** `fetch_balance` con la chiave. Su conto a saldo 0 può tornare risposta vuota ma **non deve** tornare `auth_error`. Se `auth_error` → chiave/permessi sbagliati, **STOP**.
3. **`validate=true` su `AddOrder`** per ognuna delle 3 coppie: valida l'ordine (permessi, simbolo, `ordermin`) **senza eseguirlo** — nessun order id, zero soldi. **Deve passare per tutte e 3.** Scova i bug di dimensione-minima e simbolo prima di rischiare un euro.

**Solo quando 1-2-3 sono verdi**, Max finanzia €100 in USD su Kraken e parte il primo ordine reale (BTC). Documenta l'esito dei 3 step nel report.

---

## 4. Decisioni delegate a CC

- Il COME del cablaggio (dove mettere il branch nella factory/call-site), purché rispetti l'invariante.
- Il meccanismo di isolamento single-grid per il collaudo (proponi, Max valida nel piano).
- La formula esatta di ricalibrazione passi griglia fee-aware (proponi; **fee non hardcodata**).

## 5. Decisioni che CC DEVE chiedere (non decidere da solo)

- Qualsiasi cosa cambi il comportamento del grid **oltre** al cambio venue (es. logica di trigger).
- Se emerge che il modello A market ha un problema strutturale su Kraken (es. `create_market_buy_order_with_cost` non si comporta come atteso sul "cost") → **fermati e segnala**, non ripiegare su B da solo.
- Se il floor fee-aware richiede toccare Sherpa in modo non banale → piano dedicato.

## 6. Vincoli (off-limits)

- **NON** toccare il path Binance/testnet se non dietro flag. Invariante S112: `EXCHANGE=binance` = zero diff.
- **NON** cablare TF in questo brief. **Solo grid.** TF è separato (post-collaudo).
- **NON** riavviare i bot / il Mac Mini: il restart del cutover lo fa Max via runbook.
- **NON** hardcodare la fee. **NON** hardcodare i simboli Kraken.
- Il bot non chiama **mai** funding (deposit/withdraw/earn): la chiave non ha quei permessi, e il codice non deve provarci.

## 7. Output atteso a fine sessione

1. **Piano in italiano approvato da Max** (PRIMA del codice).
2. Hot-path grid cablato dietro flag, **invariante `EXCHANGE=binance` verificato**.
3. Floor min-profit fee-aware Sherpa-managed + ricalibrazione passi.
4. Risoluzione `AssetPairs` per le 3 coppie con `ordermin`/decimals.
5. Scaletta test §3 eseguita e **documentata** (output `validate=true` per le 3 coppie).
6. Report `2026-07-11_S117_RforCEO_kraken-cutover.md` con commit hash. **SCOPE ereditato IDENTICO: `kraken-cutover`.**

## 8. Anti-assenso

**CC:** prima di codare, ≥1 obiezione tecnica reale (fattibilità/rischio/effetto collaterale/assunzione fragile) **o** riga "nessuna, motivo X". Non partire su brief non smontato. Se non converge con il CEO → sale a Max.

**CEO (auto-obiezioni, onestà):**
1. Il rischio n.1 è che **floor fee-aware + ricalibrazione griglia siano un buco più profondo del previsto**: se i passi giusti per coprire 0,80% rendono la griglia troppo rada per fare cicli con €100 su BTC (prezzo ~$100k, dato `ordermin` Kraken), potremmo scoprire che €100 su BTC costruisce una griglia con pochissimi livelli. Da **verificare nel piano** (via `ordermin` + prezzo attuale), non a €100 già versati. Se è così, opzioni: passi larghi/pochi livelli, o Max valuta l'ordine delle monete.
2. Sto assumendo che `create_market_buy_order_with_cost` su Kraken gestisca il quote-amount come su Binance. Se Kraken tratta diversamente il "cost" market order, il porting di A **non è 1:1**. Da verificare nella fase test (§3) prima del primo ordine reale.
