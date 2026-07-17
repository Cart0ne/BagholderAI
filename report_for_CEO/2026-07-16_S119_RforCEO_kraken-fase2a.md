# Report per CEO — S119 Fase 2a cutover Kraken

> ## ⭐ AGGIORNAMENTO POST-TEST LIVE — 2026-07-17
>
> **Il primo ordine reale su Kraken è passato. Il fix critico è validato su denaro vero.**
>
> Max ha lanciato l'ordine-prova (BTC/USD, riga isolata `is_active=false` +
> `KRAKEN_TEST_MODE`, sorvegliato). Esito del **BUY**:
> - `[kraken] BUY BTC/USD: fill confirmed via fetch_order after 3.1s` → il fix
>   critico **in azione**: il bot ha chiesto a Kraken l'esito reale e l'ha letto.
>   **Un solo BUY, nessun loop.**
> - Fill reale: **0,00039379 BTC @ $63.483,50 · costo $24,999 · fee $0,19999 USD**
>   (= 0,80% taker, letta dal vivo). Fee uscita dai **dollari**, non dal BTC.
> - **Tripla conferma incrociata**: DB `trades` = API Kraken = interfaccia Kraken,
>   stessi numeri e stesso order-id (`OCILGP-2GRMI-D3WSNK`). Saldi tornano:
>   $111,40 → $86,20 USD + $25 di BTC.
>
> **Il SELL è ancora pendente**: parte da solo quando BTC sale +2% sopra l'avg
> (trigger ≈ **$65.271**; ora ~$63.470). Il bot resta acceso e sorvegliato; alla vendita
> arriva un Telegram `🔴 SELL BTC/USD`. **La 2b si sblocca solo dopo aver visto
> registrare bene ANCHE una vendita reale** (brief). Nessuna urgenza.
>
> **🟡 Finding operativo per il go-live (da valutare Board/BUSINESS_STATE):** i
> "$100" caricati erano in **EUR** (€97,80), non USD. Le coppie `/USD` si tradano
> solo con **USD reali** sul conto (il toggle EUR/USD dell'interfaccia è solo una
> vista, non converte l'asset). Max ha fatto una **conversione manuale EUR→USD**
> su Kraken (EUR/USD, ~$111). → Il flusso di funding per il go-live è
> **deposito EUR → conversione a USD → trading /USD**: va messo nel runbook 2b e,
> se il CEO vuole, loggato in BUSINESS_STATE.
>
> **Cosmetico (non blocca):** il log di boot scrive "vs Binance" nel reconcile
> anche su venue kraken (etichetta hardcoded; holdings letti correttamente = 0).
> Da ripulire in un micro-fix.
>
> **Prossimo passo:** aspettare il SELL (quando BTC supera avg × 1,02) → verifica
> finale → poi Board decide il **nodo 5** (margine floor `profit_target_pct`,
> proposta CC 0,4%, + parametri delle 3 monete) → runbook Fase 2b (switch reale $100).
>
> *Correzione 2026-07-17 (indagine S119b): il trigger SELL era erroneamente indicato
> a ~$64.753 (prezzo puro × 1,02). L'avg **include la fee** (`buy_pipeline.py:304`) →
> avg ≈ $63.991 → trigger reale ≈ **$65.271**. Margine netto a +2% ≈ **+1,19%** (non
> +0,39%). Il runbook era già corretto. Dettaglio: `..._S119b_RforCEO_kraken-replay-avg-reconcile.md`.*

**Data:** 2026-07-16 · **Brief sorgente:** `config/2026-07-13_S119_brief_kraken-fase2a.md`
**Commit:** `2c57fb0` (fix S119) · precede `2cb315b` (BUSINESS_STATE update S119)
**Esito:** SHIPPED — no restart, **NESSUN ordine reale** (Kraken resta dormiente, `ALLOW_REAL_MONEY=false`)
**Test:** 297/297 verdi (290 baseline + 7 nuovi `test_kraken_fase2a_s119.py`) — invariante binance intatto

---

## In una riga

Chiusi i 2 blocker + la medium della review avversaria S118. Il bot ora, su Kraken,
**conferma l'esito reale di ogni ordine** (invece di leggere una ricevuta cieca) e,
se non riesce a confermarlo, **si ferma invece di riprovare**. Il sistema è pronto
per l'ordine-prova reale da $25 che lanci tu; quel test è azione Board.

## Cosa è stato fatto

- **🔴 CRITICAL — fill reale (era: ogni ordine trattato come "non eseguito").**
  La risposta di piazzamento di Kraken porta solo un numero di pratica, non il
  fill. Il vecchio codice leggeva "0 eseguito" → tornava a vuoto → il bot
  ri-ordinava ad ogni tick (loop, soldi veri, niente registrato). Ora
  `KrakenClient` fa un **poll `fetch_order(txid)`** (budget ~15s, backoff) e
  normalizza la risposta di dettaglio (quantità/prezzo/fee reali). Un ordine
  genuinamente annullato/rifiutato resta un no-op (non lo confonde col caso da
  pollare). Test dedicato che mocka la **forma reale** della QueryOrders
  (fallisce sul vecchio codice, passa sul nuovo).

- **halt-on-unconfirmed (tua scelta: mai retry).** Se entro il budget il fill
  non è confermato (ordine in volo, illeggibile), il bot solleva
  `OrderFillUnconfirmed` → **HALT sticky**: porta la riga a `is_active=false`,
  manda l'alert, si ferma, **zero retry**. Agganciato nel loop del grid *prima*
  del gestore d'errore generico (che invece ritenta). Raggiungibile solo sul
  percorso Kraken → il testnet Binance è inalterato per costruzione.

- **🟠 HIGH — sito pinnato a Binance.** Le superfici che leggono il "ciclo
  corrente" (4 sul sito + la funzione lato bot per la vista pubblica) ora
  filtrano esplicitamente `venue=binance` (decisione Board S119: Binance è il
  venue canonico pubblico durante test e collaudo). Senza, accendere una riga
  Kraken avrebbe fatto saltare il sito sul suo ciclo quasi-vuoto mostrando
  "Fresh start". Verificato che lo sticker "Fresh start" non scatta più per una
  riga Kraken.

- **🟡 MEDIUM — niente falsi allarmi.** Le prove "a vuoto" (`validate=true`) non
  fanno più partire l'alert Telegram / la riga forense se falliscono; un
  fallimento reale invece la fa ancora partire.

- **Isolamento del test (§5 del brief).** La riga Kraken di prova vive a
  `is_active=false`: l'orchestrator spawna solo le righe attive → **non la vede**,
  nessun conflitto con la flotta testnet. Un flag `KRAKEN_TEST_MODE` ti permette
  di far girare a mano quella riga. Scoperta utile: siccome tutte le superfici
  filtrano già `is_active=true`, per il **solo** test da $25 il pin-a-Binance non
  era nemmeno necessario — ma l'ho tenuto perché è prerequisito della Fase 2b e
  a rischio ~zero.

## Decisioni (decision log)

- **DECISIONE:** fill non confermato → HALT, mai retry. **RAZIONALE:** la
  doppia-spesa reale è il rischio peggiore; il test è sorvegliato, un intervento
  manuale è accettabile. **ALTERNATIVE:** alert-only + retry (scartata da te).
  **FALLBACK:** su `venue=binance` il codice è identico (297 test); il flag di
  test non è mai settato in produzione.
- **DECISIONE:** isolamento via riga `is_active=false` + `KRAKEN_TEST_MODE`.
  **RAZIONALE:** è ciò che impedisce davvero a due processi di "possedere" la
  stessa riga; in Fase 2b la riga andrà `is_active=true` e l'orchestrator la
  gestirà normalmente (nessun special-case permanente). **ALTERNATIVE:**
  orchestrator hands-off sul venue Kraken (scartata: in 2b lo vogliamo attivo).

## Cosa NON ho fatto e perché (anti-assenso)

- **2a.4 `total_fees` — RINVIATO con motivo.** La review lo dava come
  "double-count" da togliere. Verificando: il replay al boot **non** ricostruisce
  `total_fees`, quindi il pezzo "sospetto" fa in realtà da **ricostruzione
  cross-restart** delle commissioni di acquisto (perse in memoria al riavvio).
  Toglierlo così com'è **sottostima** dopo ogni restart. Il fix corretto
  (ricostruire `total_fees` nel replay dai trade) cambierebbe i numeri fee del
  report giornaliero **anche su Binance** = differenza osservabile → rischio per
  l'invariante. È una metrica **solo di visualizzazione** (zero impatto su
  cash/avg/realized). → rinviato al brief del sistema-pieno Kraken. Stesso
  pattern anche in `liquidation.py` (annotato).
- La mia obiezione tecnica al brief (§9) era proprio il caso-limite del poll: è
  stata incorporata come la regola HALT sopra.

## Il prossimo passo è tuo

**Ordine-prova reale $25 BTC/USD, sorvegliato** — è il criterio di accettazione
della 2a (un buy **e** un sell reali, registrati bene, senza loop né Telegram
fuorvianti). *Il sell arriva quando BTC sale del 2%: nessuna vendita forzata.*
Sequenza completa (insert riga, comando esatto, cosa guardare, teardown, cosa
fare se scatta l'HALT) in:

**`config/2026-07-16_S119_runbook_kraken-ordine-prova.md`**

Non si passa ai $100 (Fase 2b) finché non si è vista registrare bene **anche**
una vendita reale.

## Nota operativa (tuo aggiornamento PC + restart)

I fix S119 sono un **no-op su Binance** (297 test). Non impongono un restart. Il
tuo spegnimento per l'aggiornamento del PC è l'occasione per fare `git pull` sul
Mac Mini prima di rilanciare la flotta (porta il Mini su S118+S119 senza cambi di
comportamento). Health-sweep e sequenza di rilancio nel runbook, §finale.
