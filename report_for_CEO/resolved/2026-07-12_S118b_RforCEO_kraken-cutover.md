# Report for CEO — kraken-cutover (S118b: review avversaria + gate Fase 2) — 2026-07-12

**Brief sorgente:** `config/2026-07-11_S117_brief_kraken-cutover.md` (SCOPE `kraken-cutover`), Fasi 0-4 (report S117b).
**Report Fase 1 (as-built):** `report_for_CEO/2026-07-12_S118_RforCEO_kraken-cutover.md`. **Piano:** `config/2026-07-11_S118_piano_kraken-fase1.md`.
**Dettaglio tecnico grezzo:** `config/2026-07-12_S118_review-findings.md` (6 confermati + 4 respinti, testo integrale).
**Review:** workflow avversario `wf_0ca1c13f-278`, 24 agenti su modello **Sonnet**, 3,38M token, 960 tool-call, ~48 min.
**Commit sessione:** 9 commit `6a3c8ac..d6a778b`. **Restart bot:** nessuno. **Ordini reali:** nessuno.
**Decisione Max (2026-07-12):** tutti i fix rinviati, e **Fase 2 spezzata in due**: **Fase 2a** = risoluzione dei bug + nuovi test (nessun soldo si muove); **Fase 2b** = lo switch reale su Kraken con i **$100 GIÀ CARICATI da Max sul conto Kraken**. Kraken resta dormiente e gated (`ALLOW_REAL_MONEY=false`) finché la 2a non è verde: i blocker non sono raggiungibili prima. **Nota operativa:** i $100 sono già sul conto ma **fermi** — nessun ordine parte finché il gate 2a non è chiuso.

---

## 0. Executive summary per il Board (go/no-go)

**La Fase 1 è shippata ed è sana.** Il cablaggio del cutover è a posto, l'invariante "con `venue='binance'` il testnet è identico a prima" **regge** — verificato dai 290 test, a mano sui punti a rischio, e ora **confermato in modo indipendente** da una review avversaria (i candidati che avrebbero potuto romperlo sono finiti tutti tra i respinti). Nulla di ciò che è in produzione oggi è a rischio.

**Ma la Fase 2 (soldi veri su Kraken) NON è ancora go.** La stessa review ha trovato **un difetto critico e uno grave** sul percorso Kraken — oggi dormiente, quindi innocuo, ma che colpirebbe al primo ordine reale. Il critico, se non corretto, farebbe **spendere denaro vero senza registrare i trade, in loop**. Sono ora prerequisiti espliciti (§8): **prima di flippare `ALLOW_REAL_MONEY` questi due vanno chiusi.**

**Il punto strategico per il Board:** Kraken **non ha un ambiente di test**. Questo significa che la nostra "prova generale" pre-go-live ha un **punto cieco strutturale** — può validare che un ordine *sarebbe* accettato, ma non può eseguirne uno finto per vedere cosa il bot *fa con la risposta*. Il critico vive esattamente in quel punto cieco. La lezione (§3) cambia come certifichiamo: poiché i $100 sono **già sul conto Kraken**, la vera prova del fix critico sarà un **singolo ordine reale minimo (~$3-5), sorvegliato a mano**, come criterio di accettazione della Fase 2a — prima di aprire il collaudo pieno in Fase 2b.

---

## 1. Cosa è stata la review, e perché

Dopo aver shippato la Fase 1 ho sottoposto l'intero diff a una **review avversaria multi-agente**: invece di rileggere il codice da solo, ho lanciato un panel di revisori indipendenti, ciascuno con una lente diversa (invariante binance, matematica delle fee, ciclo di vita/runtime, sito+DB), e per **ogni** bug candidato ho fatto girare due verificatori il cui compito era **demolirlo**. Un difetto sopravvive solo se entrambi i verificatori non riescono a smontarlo, leggendo il codice reale (non solo il diff). È una rete pensata per catturare i bug che un singolo revisore — me — non vede perché ha già in testa il modello di come "dovrebbe" funzionare.

**Onestà sul costo:** è costata 3,38M token e ~48 minuti. È una spesa importante e la dichiaro. Due mitigazioni: (a) è girata interamente su **Sonnet**, quindi non ha toccato i limiti di sessione di Fable (che si erano esauriti nei tentativi precedenti); (b) ha trovato un bug che avrebbe bruciato denaro reale e fiducia al go-live. Il rapporto costo/beneficio, stavolta, è nettamente a favore. Non è però un rituale da ripetere su ogni diff: ha senso davanti a una soglia irreversibile come "i soldi diventano veri".

---

## 2. Esito in una tabella

| # | Sev | Area | Blocca Fase 1? | Blocca Fase 2? |
|---|-----|------|:---:|:---:|
| 1 | 🔴 CRITICAL | KrakenClient: ogni ordine reale letto come "non eseguito" | No | **Sì** |
| 2 | 🟠 HIGH | Cycle-fetch sito non venue-robusto (falso "Fresh start" al go-live) | No | **Sì** |
| 3 | 🟡 MEDIUM | `_alert_rejection` scatta sui probe `validate=true` falliti | No | Sì (igiene) |
| 4 | 🟡 MEDIUM | Fallback cycle asimmetrico sito vs `get_current_cycle` | No | Consigliato |
| 5 | 🟡 LOW | `state.total_fees` conta due volte la fee di buy | No | Consigliato |
| 6 | 🟡 LOW | `get_current_cycle` path globale: selezione per updated_at | No | Opzionale |
| — | ✅ | 4 candidati **respinti** dai verificatori (incl. i 2 sull'invariante) | — | — |

**Nessuno tocca la Fase 1 shippata.** Tutti e 6 vivono sul percorso `venue='kraken'`, che è dormiente e gated.

---

## 3. La lezione di processo (la parte che conta per il CEO/Board)

Kraken, a differenza di Binance, **non offre un ambiente di test**. Tutta la nostra validazione pre-go-live si è quindi appoggiata su `validate=true`: un ordine che l'exchange controlla (permessi, simbolo, minimi) **senza eseguirlo**. La "prova generale" della Fase 1 — 28 check, 0 FAIL — usa esattamente questo.

Il problema è che `validate=true` risponde con "ok, sarebbe accettato" e **niente altro**: nessun fill, nessun prezzo, nessuna fee. Il mio codice, correttamente, riconosce la risposta-validate e la scavalca. Ma questo significa che **la prova generale non esegue mai il codice che interpreta una risposta di ordine reale** — ed è proprio lì che vive il difetto critico. Detto brutalmente: **il "28/28" era vero ma parziale**. Certificava la metà del percorso; l'altra metà — cosa fa il bot quando Kraken dice "eseguito" — non è mai stata esercitata nemmeno una volta.

**Implicazione operativa per la Fase 2:** non possiamo trattare i test verdi + la prova validate come "pronti a versare $100". La vera certificazione è graduale e sorvegliata:
1. Fixare i due blocker (§8).
2. **Un singolo ordine reale minimo** (l'`ordermin` di Kraken, ~$3-5) su una coppia, guardato a mano: l'exchange lo esegue, e il bot **lo registra correttamente** (riga in `trades`, avg/cash aggiornati, nessun loop, nessun Telegram fuorviante).
3. Solo allora il collaudo $100 (Fase 3).

Questo aggiunge uno scalino al runbook, ma è l'unico modo onesto di chiudere il punto cieco strutturale che Kraken ci impone.

---

## 4. 🔴 CRITICAL — KrakenClient tratta ogni ordine reale come "non eseguito"

**File:** `bot/exchanges/kraken_client.py:320` (`_normalize_order_response`), raggiunto dall'hot-path via `buy_pipeline.py:177/192` e `sell_pipeline.py:407`.

**Il difetto.** Quando il grid piazza un ordine, `_normalize_order_response` legge la quantità eseguita con `filled = float(order.get("filled") or 0)` e, se `filled <= 0`, conclude "non eseguito" e ritorna `None`. Ma la risposta di **creazione ordine** di Kraken (`AddOrder` / `create_market_buy_order_with_cost`) **non contiene affatto il campo di fill**: è solo `{descr, txid}`. L'ho verificato nel sorgente ccxt effettivamente installato (versione 4.5.50): il parser legge `filled` dal campo `vol_exec`, che compare **solo** nelle risposte di *interrogazione* ordini (open/closed/my-trades), **mai** in quella di creazione. Quindi, per qualunque ordine reale, `filled` è sempre vuoto → 0 → la funzione ritorna sempre `None`.

**Cosa succederebbe in Fase 2 (scenario concreto).** Riga BTC/USD flippata a Kraken, `ALLOW_REAL_MONEY=true`. Il trigger di acquisto scatta → il bot manda l'ordine → **Kraken lo esegue davvero, spende USD reali** → la risposta torna senza fill → il bot legge `None` → conclude "ordine fallito, riprovo al prossimo tick", **senza scrivere nulla** (nessuna riga in `trades`, avg/holdings/cash invariati). Al tick successivo la condizione di trigger è ancora vera (lo stato non è cambiato) → **il bot ripiazza lo stesso ordine reale**, di nuovo senza registrarlo. Il loop si ripete a ogni intervallo (20-60s) finché il saldo Kraken non si svuota o qualcuno se ne accorge — con **zero righe a DB a spiegare dove sono finiti i soldi**, e per di più un Telegram "⚠️ ordine rejected" fuorviante a ogni giro mentre in realtà gli ordini passano. È lo scenario peggiore: perdita di capitale + perdita di tracciabilità + segnale di allarme che dice il contrario di ciò che accade.

**Perché nessuno l'ha visto (e non è una scusa, è la lezione §3).** Tre reti indipendenti l'hanno mancato per la stessa ragione: (1) i test dell'adapter mockano una risposta con `"filled": 0.001` già valorizzato — una forma che il vero Kraken non restituisce mai; (2) i 19 test nuovi della Fase 1 mockano il client a monte, o passano `validate=true`, saltando la normalizzazione; (3) la prova generale usa solo `validate=true`. Tutti girano attorno al codice rotto.

**Il fix (per il brief Fase 2).** Dopo l'ordine, Kraken restituisce il `txid`; serve un **follow-up `fetch_order(txid)`** (o `fetch_my_trades`) — che *sì* contiene `vol_exec`/prezzo/fee — e normalizzare **quella** risposta. I market order Kraken eseguono quasi istantaneamente, quindi un breve poll basta. Nessun punto del codice lo fa oggi (verificato con grep sull'intero repo). Va accompagnato da un test che mocki la risposta *reale* di QueryOrders, non quella idealizzata di oggi.

**Rischio residuo fino ad allora: nullo, purché il gate resti chiuso.** Il difetto è raggiungibile solo con una riga `venue='kraken'` attiva **e** `ALLOW_REAL_MONEY=true`. Entrambe sono passi deliberati della Fase 2. Oggi non esiste alcuna riga Kraken e il flag è `false`.

---

## 5. 🟠 HIGH — Il cycle-fetch del sito non è davvero venue-robusto

**File:** `web_astro/src/scripts/live-stats.ts:57` + le altre 6 superfici bonificate + `db/client.py:57-65`.

**Il contesto.** In Fase 1 ho "bonificato" il modo in cui il sito legge il ciclo corrente: dove prima c'era il letterale `BTC/USDT` (che al cutover, diventando `BTC/USD`, avrebbe fatto congelare il sito), ho messo la regola "la riga grid **attiva** aggiornata più di recente". Ho dichiarato questa mossa "resa venue-robusta".

**Il difetto.** La review ha verificato (interrogando il DB reale) che `bot_config` ha un trigger che aggiorna il timestamp `updated_at` a **ogni** modifica di **qualunque** colonna, non solo del ciclo; e che Sherpa scrive sporadicamente. Quindi "la riga aggiornata più di recente" **non è** un indicatore affidabile di "la riga che porta il ciclo corrente della flotta". Oggi il risultato coincide col comportamento vecchio, ma **solo per coincidenza** — perché tutte le righe hanno lo stesso ciclo. La mia frase "venue-robusta" era troppo ottimista: è *identica oggi*, non *robusta*.

**Cosa succederebbe in Fase 2 (scenario concreto).** Si inseriscono le righe Kraken con un ciclo **nuovo**, poi si fa `UPDATE is_active=true` sulla riga BTC/USD Kraken. Quell'UPDATE è, per costruzione, l'**ultima scrittura** sulla tabella → la riga Kraken "vince" → tutte e 7 le superfici del sito saltano silenziosamente sul ciclo Kraken (quasi vuoto, 0-1 trade, P&L ~$0), smettendo di mostrare i trade binance ancora in corso. In particolare la **CleanSlateSticker mostrerebbe il badge pubblico "✨ Fresh start"** proprio nel momento del go-live reale — il messaggio più fuorviante possibile nel momento di massima visibilità.

**Il fix (per il brief Fase 2).** Rendere il cycle-fetch **esplicitamente venue-aware**: decidere quale venue è "canonico" per la vista pubblica durante la finestra di collaudo e filtrare su quello. Questa è anche una **domanda di comunicazione** (§10), non solo tecnica: durante il collaudo il sito pubblico deve raccontare Kraken, binance, o entrambi?

---

## 6. Gli altri quattro (MEDIUM + LOW)

- **🟡 MEDIUM — `_alert_rejection` scatta sui probe `validate=true` falliti** (`kraken_client.py:134/154/174`). Nel ramo `except`, l'alert Telegram (+ riga a `bot_events_log`) parte **prima** del controllo "è un validate?". Rilanciare la prova generale su una coppia vicina ai minimi (es. BONK) produrrebbe **falsi allarmi in produzione** e sporcherebbe il log forense. È in codice che ho scritto io in questa sessione. Fix banale: controllare "è un validate?" prima di allarmare. *Nota: nella prova del 12-lug non è scattato perché i probe validate sono passati; è un rischio se la si rilancia.*
- **🟡 MEDIUM — Fallback cycle asimmetrico** (`db/client.py:63` vs le 7 query sito). La versione Python del cycle-fetch ha guadagnato un fallback a due livelli; le query del sito no — su risposta vuota (es. flotta ferma per incident-response) ricadono su un letterale invece dei dati DB veri. Edge stretto, ma è la stessa classe di problema che la bonifica doveva eliminare.
- **🟡 LOW — `state.total_fees` conta due volte la fee di acquisto** (`sell_pipeline.py:685`). Pre-esistente (non introdotto dalla Fase 1): al momento del sell la fee di buy viene ri-stimata e ri-sommata a una fee di buy già contata al momento del buy. Con la fee Binance 0,1% era trascurabile; con la fee Kraken 0,8% l'errore diventa 8× più grande (~+50% su questa metrica). **Non tocca** cash, avg, realized P&L né il daily P&L (che somma le fee direttamente dal DB). Tocca solo il contatore `total_fees` in memoria, che **oggi non è esposto** in nessun report/dashboard — ma sarebbe sbagliato se un domani mostrassimo "fee pagate su Kraken" per giudicare la sostenibilità.
- **🟡 LOW — `get_current_cycle` path globale** (`db/client.py:65`). Variante Python del Finding HIGH, usata da commentary/daily-report/snapshot. Il path critico (il logging dei trade) **non è a rischio** (usa la ricerca per-simbolo, invariata). Richiede una precondizione non banale; segnalato per completezza.

---

## 7. Cosa la review ha SMONTATO (rassicurazione sull'invariante)

Il valore di una review avversaria è anche in ciò che uccide. Quattro candidati sono stati **respinti** dai verificatori dopo lettura del codice reale — e tra questi i due che avrebbero potuto minare l'invariante binance, i più importanti da escludere:

- **"Il floor `not force_all` cambia il comportamento su binance"** → respinto: su binance il termine-fee è 0 e `force_all` arriva solo dai path TF, che hanno il target-profitto a 0 → la guardia era già inerte. (Coincide con la mia verifica manuale.)
- **"Il cycle-fetch fa scattare il fallback anche senza errori di rete"** → respinto: comportamento accettabile, non un difetto.
- **"Il trigger di vendita può scendere sotto il floor → stallo"** → respinto: i verificatori non hanno confermato uno scenario raggiungibile (uno ha notato un possibile caso-limite dopo slippage avverso, ma non ha superato la soglia di conferma — lo annoto come da tenere d'occhio, non come bug).
- **"`sb_cfg` può restare unbound se Supabase è giù al boot → venue forzato a binance"** → la meccanica è corretta, ma l'esito è **sicuro**: se il DB è irraggiungibile il bot ripiega su binance (e se fosse una riga Kraken, tenterebbe un simbolo inesistente su binance → fallimento rumoroso, non silenzioso). Respinto come non-difetto.

In altre parole: l'invariante che avevo promesso — "Fase 1 non cambia nulla su binance" — è uscito **rafforzato** da questo esercizio, non indebolito.

---

## 8. Il gate di prontezza — spezzato in Fase 2a e Fase 2b (decisione Max)

### Fase 2a — risoluzione bug + nuovi test (nessun soldo si muove, salvo l'ordine-prova finale)
- [ ] **[2a.1] FIX CRITICAL** — follow-up `fetch_order(txid)` in KrakenClient + test con risposta QueryOrders **reale** (non quella idealizzata di oggi).
- [ ] **[2a.2] FIX HIGH** — cycle-fetch sito venue-aware (dipende dalla decisione comms §10).
- [ ] **[2a.3] FIX MEDIUM** — `_alert_rejection` gated su `is_validate` prima di allarmare.
- [ ] **[2a.4]** (consigliati) fallback cycle sito + double-count `total_fees`.
- [ ] **[2a.5] Ordine reale minimo sorvegliato** (~$3-5, l'`ordermin`, dai $100 già sul conto) su una coppia, `ALLOW_REAL_MONEY=true` temporaneo, verifica **a mano** che il bot registri il trade (riga in `trades`, avg/cash aggiornati, nessun loop, nessun Telegram fuorviante). **È il criterio di accettazione della 2a** — la vera prova del fix critico, che i test verdi non possono dare. Poi `ALLOW_REAL_MONEY=false` di nuovo fino alla 2b.

### Fase 2b — lo switch reale (i $100 già caricati su Kraken)
- [ ] **[2b.1] Nodo 5** — parametri collaudo righe Kraken (margine floor: proposta 0,4%; passi buy/sell) — da chiudere con Max.
- [ ] **[2b.2]** Runbook finestra coordinata: insert righe Kraken → is_active flip (solo la moneta in collaudo) → TF off → disclaimer on → `ALLOW_REAL_MONEY=true` → restart → il grid lavora sui **$100 già sul conto**.
- [ ] **[2b.3]** Collaudo BTC→SOL→BONK (Fase 3), verdetto, poi deployment (Fase 4).

**Il gate resta:** la 2b non parte finché la 2a non è verde, ordine-prova [2a.5] incluso.

---

## 9. Correzioni oneste ai claim del report Fase 1

Due frasi del report `..._S118_RforCEO_kraken-cutover.md` vanno lette alla luce di questa review:

- **"Prova generale validate via client: 28 check, 0 FAIL"** — vero, ma copre **solo** il percorso `validate=true`. Il percorso dell'ordine reale (la sua risposta) non è mai stato esercitato → il critico §4 era invisibile a quel test. Non era falso, era **parziale**, e l'ho presentato con più sicurezza di quanta ne meritasse.
- **"Bonifica resa venue-robusta"** (nodo 2) — sovra-ottimista: identica *oggi*, non *robusta* al multi-venue (§5).

Le ho corrette in PROJECT_STATE §4/§5 e nel Master Task List. Lo segnalo qui perché è esattamente il tipo di ottimismo che un CEO deve poter scontare quando pesa un go/no-go.

---

## 10. Domande aperte per CEO / Board

1. **Comunicazione durante il collaudo (blocca il fix HIGH):** durante la finestra Kraken, il sito pubblico deve mostrare i dati **Kraken** (la moneta in collaudo), **binance** (la flotta ancora viva), o **entrambi con etichette**? La risposta decide come rendere venue-aware il cycle-fetch. Il piano comms attuale (`COLLAUDO_COMMS_GUIDELINES_v1`) dice "dashboard filtrata alla moneta attiva" → suggerisce Kraken, ma con la CleanSlateSticker da domare per non gridare "Fresh start" al pubblico.
2. **Modello B (ladder maker 0,40%):** con la fee taker reale allo 0,80%, il maker dimezza il costo per giro. Resta da ri-esaminare in Board **prima** del deployment $600, coi numeri veri.
3. **Soglia di ri-review:** confermate che l'investimento in una review avversaria completa vada riservato alle soglie irreversibili (pre-real-money, pre-deployment) e non a ogni diff? È la mia proposta operativa dopo questa sessione.

## Decisions (log di sessione)

- **DECISIONE (Max):** tutti i fix al brief Fase 2, nessuno stasera. **RAZIONALE:** Kraken dormiente + gate chiuso = zero urgenza; il fix critico merita attenzione fresca e un test fedele, non fretta di fine sessione. **ALTERNATIVE:** fixare subito il medium banale (offerto, declinato). **FALLBACK:** i blocker sono registrati come prerequisiti #0 in MTL + PROJECT_STATE §5 → non si perdono.
- **DECISIONE:** review avversaria eseguita su **Sonnet** invece di Fable. **RAZIONALE:** i limiti di sessione Fable erano esauriti (avevano ucciso i due tentativi precedenti); Sonnet è pienamente capace per review di diff e non tocca quel monte-ore. **ALTERNATIVE:** Opus (più caro), o saltare la review (avrebbe lasciato il critico invisibile fino al primo ordine reale). **FALLBACK:** nessuno necessario — findings registrati e versionati.
