# SEQUENZA POST-GO-LIVE — v1

**Decisa:** 2026-08-09 (S125), Board + CEO.
**Contesto:** sistema live su Kraken con denaro reale dal 7 agosto. Volume 4 chiuso come prodotto.
**Cosa è questo file:** l'ordine dei lavori e il criterio per dire "fatto". Da leggere a inizio sessione insieme a PROJECT_STATE e BUSINESS_STATE.

> **⚖️ Emendamento Board — 2026-09-16 (S127), deciso da Max, annotato da CC.** Davanti al punto 1 entra **R.7 "Mac Mini autonomo"** (avvio automatico dei bot dopo il login + watchdog Wi-Fi): dal 5 al 16 settembre il denaro reale è rimasto **11 giorni** senza operare (Mini staccato dal Wi-Fi, poi riavviato da un aggiornamento senza rilancio dei bot). **Ordine vigente: R.7 → 1 riconciliazione → 2 commissioni (XRP) → 3 Sentinel/NewsKeeper.** Il resto del file è invariato. Dettaglio: `config/MASTER_TASK_LIST_2026-09-16.md` R.7. *(Una v2 del file, se serve, la scrive il CEO.)*

---

## 1. I tre lavori, in quest'ordine

### 1 — Riconciliazione su Kraken
**Perché prima:** è il controllo che verifica che i numeri a database corrispondano agli ordini che l'exchange ha davvero eseguito. Non esiste. Sul testnet era una formalità; con denaro reale è l'unica cosa fra *"i conti tornano"* e *"crediamo che tornino"*. Il progetto ha una storia documentata di numeri che mentivano senza che nessuno lo vedesse — e il reset di Binance è stato scoperto 24 ore dopo, per caso, da uno script che l'aveva rilevato e scritto in un log che nessuno legge.

**Fatto quando:** esiste un confronto automatico fra `trades` e i fill reali di Kraken, gira con una cadenza, e **il suo esito arriva dove un umano lo guarda già** — non in un log. Un avviso che nessuno riceve non è un avviso: è la lezione di S124 e non va ripetuta nel lavoro che la corregge.

**Dipendenza scoperta strada facendo:** il database non sa distinguere il denaro reale. Nessuna colonna `venue` su `trades`, e `mode` vale `live` su tutte e 319 le operazioni, testnet incluse. L'unico appiglio è la stringa del ciclo — una convenzione sui nomi, non un dato. Probabilmente va sistemato **dentro** questo lavoro, non dopo.

### 2 — XRP: misurare la commissione degli ordini a prezzo fissato
**Perché subito dopo:** quel numero decide se il resto ha senso. Oggi paghiamo **0,8001%** per lato, verificato due volte su due monete diverse. Il listino dichiara 0,25% per gli ordini che aspettano nel mercato, ma lo stesso listino dichiarava 0,40% dove abbiamo pagato 0,7999% — **quindi il listino non è una fonte**. Il ciclo di SOL ha reso $0,36 su $0,69 lordi: l'exchange si è preso il 47%.

**Fatto quando:** un ordine limite è stato eseguito e **l'addebito reale è stato letto e scritto da qualche parte**. Mezz'ora, non settimane.

**Esplicitamente FUORI da questo lavoro:** la macchina completa di gestione degli ordini in attesa — tracciamento, cancellazioni alla scadenza, fill parziali, ricalcolo a ogni mossa di Sherpa. Sono settimane, e si valutano **dopo** aver visto il numero, non prima.

### 3 — Sentinel / NewsKeeper
Il lavoro sui cervelli, con il tempo che serve.

**Nota di dissenso messa a verbale:** il CEO ha sostenuto che questo lavoro migliora *quando* il sistema decide, mentre il collo di bottiglia è *quanto costa muoversi* — e che ottimizzare le decisioni di una macchina che lascia il 47% al casello è ottimizzare la parte sbagliata. **Il Board ha confermato la sequenza comunque**, e ha un argomento che il CEO non ha: i cervelli sono il contenuto pubblico migliore del progetto, e il valore del progetto non è mai stato il P&L. I punti 1 e 2 restano prima, quindi il dissenso è rientrato nell'ordine, non nella priorità.

---

## 2. Il diario: cosa si ferma, cosa continua

| | stato |
|---|---|
| **Diario .docx** (il volume, il prodotto Payhip) | ⛔ **si ferma.** Volume 4 chiuso, nessun Volume 5 |
| **Diary entry su Supabase** (per il sito) | ✅ **continua**, sessione per sessione, regole §3 di `CEO_WORKFLOW_RULES` invariate |
| **Capitolo di chiusura del Volume 4** | 📌 da scrivere a due mani in sessione dedicata |

**Verificato che questo non rompe niente.** La macchina di contenuti attinge alle **entry Supabase**, non al .docx: il poster X legge `diary_entries` (ed era per questo che si era fermato — *"Latest diary: Session 122 (384.6h old) — STALE"*), e il canale Telegram pubblica su nuova sessione completa. Finché le entry si scrivono, il canale respira.

**Rischio residuo, da tenere d'occhio.** Il .docx era il posto dove la narrazione veniva messa in forma lunga, e da quella forma lunga nascevano i blog post. Le entry Supabase sono due o tre frasi: sono un teaser, non una storia. Se sparisse anche la fonte lunga, i post nascerebbero dal nulla.

**Non sparisce**, e va detto perché è la ragione per cui la decisione è sicura: i **report di CC** sono già materiale narrativo pieno — quello del 9 agosto contiene più storia utilizzabile del .docx che ha alimentato. La fonte lunga cambia autore, non esiste più come prodotto.

---

## 3. Marketing: da residuo ad attività

Cambia lo status, non il metodo. Il metodo è già scritto in `MARKETING_RUNBOOK_v1`.

**Cosa significa "seriamente", in concreto:**

- **Il marketing non è più quello che si fa se resta tempo.** È un blocco come gli altri, dentro il conto dei due blocchi per sessione.
- **Tre gesti a settimana, venti minuti l'uno**, dal runbook: due o tre reply in thread altrui · un post su un fatto vero · una risposta a chi ci ha scritto. Nessuno dei tre deve saltare due settimane di fila.
- **Le 69 bozze si consumano.** Sono pronte dal 3 luglio con il campo "pubblicato" vuoto su tutte e 69. Due o tre a settimana e la coda si smaltisce; zero a settimana e restano un archivio.
- **L'unica soglia numerica reale è ~50 di karma Reddit** per sbloccare r/ClaudeAI (siamo a 35, e solo i commenti fanno karma). Il "karma >100" che gira nel tracker da giugno è un numero tondo senza derivazione: si ignora.

**Il vincolo strutturale, dichiarato.** La regola di autenticità — Max scrive in italiano, il CEO traduce — mette Max nel percorso critico di ogni singolo post. È il prezzo dell'unico vantaggio competitivo reale del progetto, quindi si paga. Ma è anche **la ragione tecnica per cui la macchina si è fermata cinque settimane**, e va saputo quando si pianifica: una settimana pesante di Max è una settimana di silenzio, per costruzione.

**Fuori dalla regola** (non richiedono la voce di Max, si possono muovere sempre): l'audit con Mike, i DM ai contatti tecnici, il carosello visivo, le risposte brevi di cortesia.

---

## 4. Non nella sequenza, ma da fare subito perché costa dieci minuti

**Il messaggio a Mike Czerwinski.** Ha accettato di auditare il sistema ponendo lui la condizione — walk-forward su regimi non scelti da noi, *"bring me the part you can't tune"* — noi abbiamo detto sì e promesso il repo col codice congelato **quando andiamo live**. Siamo live da due giorni e la palla è nostra dal 29 giugno.

Non è un blocco di lavoro, è un messaggio. Ma è il gesto col miglior rapporto valore/fatica di tutto questo file, e un audit esterno indipendente è ciò che il progetto rivendica in ogni post che pubblica.

---

## 5. Parcheggiati, con l'etichetta

- **Trend Follower** — da riprendere dopo i cervelli
- **Macchina completa degli ordini a prezzo fissato** — dopo il punto 2, se il numero la giustifica
- **Backtest pubblico girato a commissione dimezzata** (0,40% contro 0,80%) — decisione editoriale, più urgente ora che c'è denaro reale
- **Difetto del prezzo fasullo** — non più un gate, resta manutenzione
- **Script ricorrente spread + volume** per la selezione asset
- **`COLLAUDO_COMMS_GUIDELINES_v1` da emendare** — contraddetta su tre punti dalla Fase 3
- **`last_trade_at` negli snapshot** riporta il recalibrate, non il trade
- **Sherpa allarga SOL senza sosta** — 39 riscritture in 48h, sempre nella stessa direzione. Se fra una settimana `sell_pct` è a 2,2 senza cicli, verificare se il clamp sia tarato per un venue allo 0,80%

---

## 6. La domanda che questa sequenza serve a rispondere

Se il punto 2 dice che le commissioni non si possono ridurre, allora un grid da quattrocento dollari su un exchange europeo **non può essere profittevole e non lo sarà mai**.

Non sarebbe una brutta notizia: sarebbe il risultato dell'esperimento, misurato invece che supposto. E vale più di un bot che guadagna.
