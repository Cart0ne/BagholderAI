Brief S112 — kraken-adapter — 2026-06-29

> **Base documentale:** scouting S112 (questa sessione) + `APPROVED_golive_experiment_design.md` + `TESTNET_RESET_RUNBOOK.md` (caricato da Max).
> ⚠️ **Riferimento PROJECT_STATE.md: DA CONFERMARE** — il CEO non ha interrogato PROJECT_STATE all'inizio di questa chat (sessione partita come scouting). CC: prima di partire, allinea sull'ultima data di PROJECT_STATE e segnala se qualcosa qui contraddice lo stato reale del repo.

---

## 0. Contesto e perché questo brief esiste

Binance ha mancato la licenza MiCA (ritiro domanda Grecia 24/06) e **dal 1° luglio sospende nuovi ordini spot/depositi per i residenti UE**. Il bot non potrà più piazzare ordini su Binance. Decisione Board (S112): **si migra a Kraken** come venue di go-live.

Gate venue **CHIUSO** in questa sessione:
- Account Max registrato + validato (entità EU/MiCA — footer "MICAR").
- API accessibile: *Connessioni e API → Crea API key* (Kraken Pro).
- Coppie verificate **da Max nella UI del proprio conto EU**:
  - `BTC/USDC` — vol ~60.1M
  - `SOL/USDC` — vol ~3.12M (nota: `SOL/USD` ~35M, book più profondo; **resta USDC**, vedi §6 decisioni)
  - `BONK/USDC` — vol ~113K (sottile ma vivibile per €100 grid-only)

**Obiettivo strategico di Max:** front-load tutto il front-loadabile ADESSO, così che al prossimo reset del testnet Binance (stimato inizio luglio) il cutover sia *flip del flag + 1 ordine reale*, non una migrazione.

**Questo brief NON è il cutover.** È solo la costruzione dell'adapter Kraken **dormiente dietro flag**, mentre il bot continua a girare su Binance testnet. Il cutover (flip + collaudo) è un brief successivo.

---

## 1. Task >1h → PRIMA il piano, POI il codice

Task non banale. Come da CEO_WORKFLOW_RULES §2: **produci PRIMA un piano in italiano leggibile da Max e fattelo approvare prima di scrivere una riga di codice.** Non partire a codare.

Il piano deve includere l'output del **Passo 0** qui sotto (la mappatura), che è esso stesso il primo deliverable da approvare.

---

## 2. PASSO 0 (obbligatorio, prima di tutto) — Mappa dell'accoppiamento exchange

Prima di costruire qualsiasi cosa, **mappa dove il codice è accoppiato a "Binance"** e proponi il punto di taglio dell'astrazione. Niente codice finché Max/CEO non valida la mappa.

Touchpoint **noti** da cui partire (fonte: `TESTNET_RESET_RUNBOOK.md`, NON una mappa completa — la completi tu):
- `bot/grid/buy_pipeline.py` — contiene `synth_fee` / `FEE_RATE` (fee sintetiche, vedi §5 sotto: critico).
- `bot/grid/sell_pipeline.py`
- `bot/grid/grid_bot.py`
- `bot/grid/state_manager.py`
- `bot/orchestrator.py`
- `scripts/reconcile_binance.py` — **reconcile exchange-specifico**: è uno dei nodi di accoppiamento più probabili.

Output del Passo 0: un documento breve in italiano che elenca **tutti** i punti dove si decide/usa "Binance" (auth, naming coppie, place/cancel/amend ordini, parsing risposte, reconcile, fetch prezzi/candele, websocket) e **dove proponi di mettere il confine dell'astrazione** (es. interfaccia `ExchangeClient` con due implementazioni). 20 minuti di analisi per non spendere una giornata a capire perché il testnet si è impiantato.

---

## 3. VINCOLO INVARIANTE (il cuore del brief, non negoziabile)

L'adapter Kraken è **additivo e dietro flag** `EXCHANGE` (valori `binance` | `kraken`, **default `binance`**). Il flag si inserisce nel pattern env-flag già esistente dell'orchestrator (accanto a `ENABLE_TF`, `ENABLE_SENTINEL`, `ENABLE_SHERPA`, ecc.).

**Invariante:** con `EXCHANGE=binance`, il comportamento del bot deve essere **identico a prima del tuo commit** — stessi import, stesso path d'esecuzione, zero diff osservabile sul processo testnet vivo sul Mac Mini.

- NON rifattorizzare moduli condivisi dall'orchestrator se non dietro il flag.
- Il codice Binance esistente resta sostanzialmente intatto; aggiungi il ramo Kraken *accanto*, non al posto.
- **Prova richiesta:** un `git pull` su `main` con `EXCHANGE=binance` non deve cambiare nulla nel testnet in corso. Questo è importante perché il runbook reset (§6 del runbook) fa `git pull --ff-only` dentro la procedura di restart: se al prossimo reset Max segue il runbook, tirerà dentro il tuo codice — e DEVE essere innocuo a flag spento.

---

## 4. ADAPTER KRAKEN — cosa deve fare (spec funzionale)

Tre porte: REST + WebSocket (FIX non serve). Specifiche verificate sui doc Kraken in questa sessione:

**Auth**
- HMAC-SHA512 con gestione nonce. **Nonce window alto** (es. 10000) per evitare errori "Invalid nonce" in contesto multi-thread.
- Chiavi lette da env (`KRAKEN_API_KEY`, `KRAKEN_API_SECRET` o nomi che proponi tu) — **mai hardcoded, mai nel repo**. Verifica che `.env` sia in `.gitignore`.

**Naming asset/coppie**
- Kraken usa simboli non standard (`XBT` per BTC, `ZUSD`, ecc.). **Risolvi via endpoint pubblico `AssetPairs`** i nomi canonici + `pair_decimals`/`lot_decimals`/`ordermin` per `BTC/USDC`, `SOL/USDC`, `BONK/USDC`. Non hardcodare le stringhe a intuito.

**Order layer**
- `AddOrder` (limit, market).
- `AddOrderBatch` (max 15 ordini/coppia in una chiamata) — per piazzare le scale del grid in un colpo.
- `EditOrder`/amend — riposiziona livelli senza cancel+recreate.
- `CancelOrder` / `CancelAll`.
- `cancel_all_after_x` — **dead-man's switch**: se il bot smette di battere il cuore per X secondi, Kraken azzera gli ordini aperti. Rete di sicurezza per crash del Mac Mini.
- Feed WebSocket `executions` per i fill in tempo reale (auth via `GetWebSocketsToken`).
- Lettura fee-tier corrente + volume 30gg.

**Permessi chiave API** (da impostare quando Max genera la chiave, NON ora): Query Funds, Query Open/Closed Orders & Trades, Modify Orders, Cancel/Close Orders, Access WebSockets API. **Withdraw Funds → OFF.**

---

## 5. USDC NATIVO + FEE REALI (assorbe il vecchio S110c)

Il vecchio brief S110c (USDT→USDC) era concepito nell'era Binance: **è superato, non eseguirlo separatamente.** Lo strato core di USDC entra qui:

- Il bot tratta **USDC** come valuta-cassa/quote (non USDT) — config, state, label.
- ⚠️ **FEE REALI, non sintetiche.** Sul testnet Binance le fee erano 0 e il bot **sintetizzava** `FEE_RATE` 0,1% (`synth_fee` in `buy_pipeline.py`, opzione B). **Su Kraken le fee sono reali** (base tier ~0,25% maker / 0,40% taker). La logica `synth_fee` NON deve applicarsi al path Kraken: lì le fee vanno **lette dall'exchange**, non finte. Questo è un punto di divergenza comportamentale da gestire esplicitamente, non un dettaglio.
- **Ricalibrazione step grid + soglie di profitto** sul regime fee Kraken (0,25%/0,40%) invece di 0,10% di Binance: lo step minimo profittevole si allarga. Proponi i nuovi parametri nel piano, non deciderli silenziosamente.

---

## 6. Decisioni

**Delegate a CC (decidi tu):**
- Struttura interna dell'adapter (layout classi, nomi file), purché additiva + dietro flag + invariante rispettato.
- Implementazione del mapping simboli via `AssetPairs`.
- Nomi delle env var Kraken.

**Già decise (Board/CEO, S112) — documenta, non rimettere in discussione:**
- Venue = Kraken. Coppie su **USDC** per tutti e tre (BTC/SOL/BONK). SOL resta USDC nonostante il book USD più profondo (3,12M reggono €150 grid; rompere la coerenza USDC per un guadagno marginale = no).

**CC DEVE chiedere (NON decidere da solo → sale a Max via CEO):**
- **Exit nativi vs bot-side.** Kraken offre trailing-stop/take-profit nativi. Le soglie di uscita TF (trailing +5%/−4%, da S110d) sono già implementate **lato bot**. Spostarle su ordini nativi Kraken è un trade-off (nativo sopravvive a bot giù, ma lega la logica all'exchange e perde portabilità). **NON scegliere da solo:** proponi, motiva, ma è decisione di Max.
- Qualsiasi punto in cui l'invariante §3 risulti impossibile senza toccare il path Binance (vedi auto-obiezione CEO sotto).

---

## 7. OUTPUT ATTESO (cosa deve esistere a fine lavoro)

1. Documento Passo 0 (mappa accoppiamento) approvato da Max.
2. Piano in italiano approvato da Max.
3. Adapter Kraken funzionante **dietro flag**, con `EXCHANGE=binance` invariante verificato.
4. Risoluzione `AssetPairs` per le 3 coppie con precisioni/minimi.
5. Order layer completo (place/batch/amend/cancel/cancel-after-x/WS executions/fee-tier).
6. USDC nativo + fee reali sul path Kraken + parametri grid ricalibrati (proposti).
7. Report: `2026-06-29_S112_RforCEO_kraken-adapter.md` (SCOPE **identico**: `kraken-adapter`), con commit hash dentro.

**NON in questo brief (cutover, brief successivo):** flip del flag in produzione, ordine reale di validazione, collaudo €100, bump ciclo, dashboard pubbliche (§5 runbook).

---

## 8. OFF-LIMITS (cosa NON toccare)

- **Path Binance**: con flag a `binance`, zero diff comportamentale.
- **Processi standalone**: NewsKeeper v1/v2, Sentinel, Sherpa — non c'entrano, non toccarli.
- **NON rimuovere** l'adapter Binance: resta dietro flag.
- **NON riavviare il bot**: il restart è decisione di Max (pull/push sono autonomi tuoi; il restart no).
- **NON generare/maneggiare le API key**: le mette Max nel `.env` del Mac Mini. Tu definisci solo i *nomi* delle variabili.
- **NON toccare le dashboard pubbliche / il ciclo hardcoded** (è cutover, non questo brief).

---

## 9. AUTO-OBIEZIONE DEL CEO (regola anti-assenso)

L'obiezione vera a questo mio stesso brief: **l'invariante §3 ("additivo, non toccare il path Binance") potrebbe essere irrealistico se la scelta dell'exchange è intrecciata in profondità** (auth, naming, parsing, reconcile sparsi in più punti). Se l'accoppiamento è profondo, isolare Kraken senza toccare il codice condiviso potrebbe costringerti a un'astrazione invasiva — e *quella* rifattorizzazione è proprio dove si infila il rischio di rompere il testnet vivo. È esattamente perché il Passo 0 esiste: se la mappa rivela che l'invariante non è tenibile a costo ragionevole, **fermati e dillo a Max** — non forzare un'astrazione fragile né rompere l'invariante in silenzio. Meglio rivedere l'approccio (es. branch separato, o accettare un piccolo refactor condiviso ben isolato e testato) che scoprire al reset che il bot non riparte.

## 10. CONTRO-OBIEZIONE RICHIESTA A CC (regola anti-assenso)

Prima di scrivere codice: **produci ≥1 obiezione tecnica reale** a questo brief (fattibilità, rischio, assunzione fragile, effetto collaterale) — oppure dichiara in una riga perché non ce ne sono. Non partire su un brief non smontato. Se la tua obiezione e la posizione del CEO non convergono → sale a Max, non decidi tu.
