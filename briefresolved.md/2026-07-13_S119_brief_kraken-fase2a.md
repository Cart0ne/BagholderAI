Brief S119 — kraken-fase2a — 2026-07-13

# Fase 2a — fix blocker + igiene, pronti per l'ordine-prova

## 0. Contesto e base

- **Sorgente decisioni:** sessione CEO S119 (oggi) + i tuoi report `report_for_CEO/2026-07-12_S118_RforCEO_kraken-cutover.md` e `...S118b...`.
- **Dettaglio tecnico bug (autorevole):** `config/2026-07-12_S118_review-findings.md` (6 confermati). I numeri di riga qui sotto vengono dai report: **verificali sul codice corrente**, potrebbero essersi spostati.
- **PROJECT_STATE:** a inizio sessione `git pull`, poi leggi la versione corrente. Se flaggi drift/incoerenze → STOP, si risolve prima.
- **Gate invariato:** Kraken resta dormiente, `ALLOW_REAL_MONEY=false`. **Nessun ordine reale parte da te.** **Nessun restart bot** (li fa Max sul Mac Mini). Tu prepari; Max esegue le azioni sul mondo reale.

## 1. Obiettivo della Fase 2a

Chiudere i due blocker (critico + grave) e l'igiene, così che l'**unico** passo mancante per validare il fix critico sia l'ordine-prova reale minimo che **lancia Max** da terminale (non tu). Alla fine della 2a, il sistema è pronto per quel test; il test stesso è azione Board.

## 2. PRIMA di scrivere codice (stima > 1h)

Produci un **piano in italiano** leggibile da Max e attendi il suo ok prima di toccare codice (regola CLAUDE.md §3). Nel piano affronta esplicitamente il **punto di isolamento** del §5 — è il pezzo che potrebbe cambiare il design.

## 3. Task

### [2a.1] FIX CRITICAL — KrakenClient tratta ogni ordine eseguito come "non eseguito"
- **File:** `bot/exchanges/kraken_client.py:~320` (`_normalize_order_response`), raggiunto da `buy_pipeline.py:~177/192` e `sell_pipeline.py:~407`.
- **Fix:** dopo l'invio ordine Kraken restituisce solo `{descr, txid}` (niente fill). Aggiungi un **follow-up `fetch_order(txid)`** (o `fetch_my_trades`) — che contiene `vol_exec`/prezzo/fee — e normalizza **quella** risposta. I market order Kraken eseguono quasi subito, basta un poll breve con timeout.
- **Test:** obbligatorio un test che **mocki la risposta reale di QueryOrders** (con `vol_exec` valorizzato), NON la forma idealizzata `{"filled": 0.001}` che il vero Kraken non restituisce mai. Il test deve fallire sul codice attuale e passare col fix.

### [2a.2] FIX HIGH — cycle-fetch del sito venue-aware
- **File:** `web_astro/src/scripts/live-stats.ts:~57` + le altre 6 superfici bonificate + `db/client.py:~57-65`.
- **Decisione Board (chiusa oggi):** durante test interno e collaudo il **sito pubblico resta su `binance`**. Quindi il venue canonico per la vista pubblica = **binance**, e il cycle-fetch deve **filtrare esplicitamente su venue='binance'**, non su "ultima riga attiva aggiornata".
- **Verifica CleanSlateSticker:** confermare che col filtro non scatti il badge "Fresh start" quando esiste una riga Kraken attiva.
- **Perché in 2a e non 2b:** è ciò che rende invisibile il test da $25 (vedi §5). Senza, accendere una riga Kraken fa saltare il sito su di essa.

### [2a.3] FIX MEDIUM — `_alert_rejection` scatta sui probe validate falliti
- **File:** `kraken_client.py:~134/154/174`.
- **Fix:** nel ramo `except`, controllare **"è un validate?"** PRIMA di far partire l'alert Telegram + la riga in `bot_events_log`. Evita falsi allarmi in produzione se si rilancia la prova generale vicino ai minimi (es. BONK).

### [2a.4] (consigliati — includi se rientri, altrimenti flagga come rimandati)
- **`db/client.py:~63`** — fallback cycle sito asimmetrico rispetto a `get_current_cycle`. Allineare così che su risposta vuota non ricada su un letterale.
- **`sell_pipeline.py:~685`** — `state.total_fees` conta due volte la fee di buy (pre-esistente). Non tocca cash/avg/P&L, solo il contatore in memoria; ma con fee Kraken 0,80% l'errore diventa 8×. Fix pulito.

### [2a.5] Runbook ordine-prova (TU prepari, MAX esegue)
- Prepara e **documenta** la sequenza esatta che Max digiterà per lanciare **da terminale** un singolo ordine reale minimo su **BTC/USD Kraken**, sorvegliato, con `ALLOW_REAL_MONEY=true` temporaneo. Include: come inserire la riga Kraken di test, `sell_pct=2.0` (trigger deciso da Max), `profit_target_pct=0` (floor invariato), come isolarla (§5), come verificare a mano il risultato, come rimettere `ALLOW_REAL_MONEY=false` dopo.
- **Criterio di accettazione 2a:** dopo un **ciclo completo** (un buy **e** un sell) si deve vedere in `trades` le righe giuste, avg/cash aggiornati, nessun loop, nessun Telegram fuorviante. *Il sell arriva quando il mercato sale — nessuna vendita forzata.* Non si passa ai $100 finché non si è visto registrare bene **anche** una vendita reale.

## 4. Decisioni Board chiuse oggi (rispettale, non ri-aprire)

- Sito pubblico **resta su binance** durante test e collaudo → venue canonico = binance (guida [2a.2]).
- **Floor invariato a 0** = "non vendere sotto il break-even fee". Non si tocca.
- Test da $25: **trigger manuale 2%** (copre 1,6% fee round-trip + cuscino slippage), Sherpa **spento** sulla riga Kraken.
- **Cuscino slippage dentro `sell_pct`** per ora; `slippage_buffer_pct` resta NULL (micro-decisione, non implementarla adesso).
- Dimensione del **primo** ordine-prova ($25 vs ~$5 ordermin): **scelta di Max**, non tua. Chiedila (§Decisioni che CC DEVE chiedere).

## 5. Punto di isolamento — da sciogliere nel piano italiano

Max lancerà il bot Kraken di test **da terminale, mentre l'orchestrator gestisce la flotta testnet sul Mini**. I due processi **non devono** credere entrambi di "possedere" la riga BTC/USD-Kraken. Proponi come garantirlo, scegliendo tra (o combinando):
- (a) riga Kraken di test `is_active=false` + script terminale che la targetta esplicitamente (l'orchestrator non la vede);
- (b) `is_active=true` + sito filtrato su binance (fix [2a.2]) così il pubblico non la vede comunque.
Dì quale preferisci e perché. È la parte con più rischio di design.

## 6. FUORI SCOPE 2a (NON toccare in questa sessione)

- **Fix-fee Sherpa 0,1%→0,80%.** Sherpa oggi calcola i trigger sulle fee Binance; su Kraken produrrebbe `sell_pct` sotto il floor → stallo. Serve **prima** di riaccendere Sherpa sul sistema pieno (fase €600), **non** per i test manuali dove Sherpa è spento. → brief separato, più avanti.
- **Righe Kraken di produzione, insert collaudo, restart, andata live.** Sono Fase 2b.
- **Modello B (ladder maker 0,40%).** Ri-esame Board pre-deployment.
- **BUSINESS_STATE.md** (territorio CEO).

## 7. Vincoli / file off-limits

- Non toccare il percorso `venue='binance'`: l'invariante S112 (testnet byte-identico) deve restare verde. I 290 test devono continuare a passare.
- Non modificare BUSINESS_STATE.md, i diari, la logica del floor.
- Push diretto su main, mai PR. Se crasha → git revert + git pull sul Mini (lo fa Max).

## 8. Auto-obiezione (CEO)

Metto il fix GRAVE [2a.2] in 2a, e tocca 7 superfici frontend + astro: superficie ampia per una fase che "doveva solo fixare il critico". **Contro-argomento per cui lo tengo comunque:** senza [2a.2], il test da $25 non è invisibile — accendere una riga Kraken fa saltare il sito su di essa e mostrare "Fresh start" al pubblico. Quindi [2a.2] non è extra: è il prerequisito dell'invisibilità che Max ha chiesto. Se in fase di piano trovi che l'isolamento via (a) `is_active=false` rende [2a.2] non necessario per il *solo* test da $25, **dillo**: potremmo spezzare [2a.2] fuori dal test e tenerlo come prerequisito 2b. Non ho una posizione rigida qui — dipende dal design di §5.

## 9. Obiezione richiesta a te (CC) prima di implementare

Produci **almeno una obiezione tecnica reale** al brief prima di scrivere codice (o una riga che dichiara perché non ce ne sono, se è tutto meccanico). In particolare voglio il tuo parere sul poll `fetch_order`: timeout, retry, e cosa fa il bot se il follow-up **non** conferma il fill entro il timeout (ordine in volo ma non ancora leggibile) — è il caso limite più pericoloso del fix critico.

## 10. Output atteso a fine sessione

1. `[2a.1]` fix critico + test su risposta reale, verde.
2. `[2a.2]` cycle-fetch venue-aware (canonico binance), CleanSlateSticker verificata.
3. `[2a.3]` alert_rejection gated.
4. `[2a.4]` inclusi o flaggati come rimandati con motivo.
5. `[2a.5]` runbook ordine-prova documentato per Max, con la scelta di isolamento del §5 motivata.
6. 290 test ancora verdi (invariante binance).
7. PROJECT_STATE.md rigenerato; commit + push su `origin/main`.
