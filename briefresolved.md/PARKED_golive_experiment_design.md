# PARKED — Disegno esperimento go-live (rampa, rabbocco, verdetto, Victory Lap)

**Origine:** sessione estemporanea 2026-06-10 (partita come chat marketing, deragliata in strategia)
**Stato:** posizioni di principio discusse e raffinate a lungo. NESSUNA decisione esecutiva presa.
**Riprendere:** prossima sessione di lavoro dedicata — prerequisito prima del mainnet.
**Spirito Max:** eseguire fino in fondo. Distinzione fondante (vedi sotto): evitare i ritardi-CASO-1, accettare i ritardi-CASO-2.

> NOTA versione 2: rispetto alla prima bozza sono CADUTI il "kill-switch di portafoglio" e l'"X-mesi" come freni. Sostituiti da logica a condizioni. Leggere le sezioni aggiornate.

---

## 0. Distinzione madre — i due tipi di ritardo (Max)

- **CASO 1 = veleno.** Tutto ciò che si infila TRA noi e il mainnet con un "prima però" (es. "non andiamo live finché non generalizziamo X / non perfezioniamo TF / non vediamo 3 regimi"). Il CEO lo blocca SEMPRE.
- **CASO 2 = libero.** Side-quest che girano ACCANTO al go-live senza farne da gate (es. impacchettare roba per un marketplace). Divertimento, pure contenuto. Nessun problema.
- **Domanda-filtro del CEO ogni volta che spunta roba nuova:** "è un prerequisito del go-live, o gira in parallelo?". Prerequisito → giustifica o cade. Parallelo → via libera (basta non rubare le mani nei momenti chiave, es. la settimana dell'accensione).

---

## 1. Capitale — premessa corretta

- €100 NON è il test. È il primo gradino della rampa.
- **Capitale operativo target = €600** → **€500 grid + €100 TF**.
- "Lavora bene" (criterio del CEO per salire di gradino) = rispetta le regole, niente slippage/drift/errori di esecuzione. NON significa guadagnare. È affidabilità del sistema, non profitto.

---

## 2. La RAMPA di collaudo live (struttura Max)

Il go-live NON è un evento singolo. È una rampa con un punto-zero pulito alla fine.

1. Vai live con €100.
2. Aggiungi +€200, poi +€300 (valori indicativi, da decidere) → si arriva a €600.
3. "Finisci di testare" = il collaudo live ha mostrato ciò che la testnet non mostra mai onestamente (slippage, fill reali, latenza, drift).
4. **RESET a €600 netti = punto-zero vero:**
   - se in positivo → togli l'eccedenza dal flusso;
   - se in "negativo" → rabbocchi fino a €600 (MA solo per la causa corretta, vedi §3).
5. Da lì in poi: mani OFF. "Adesso sono cazzi del CEO."

**Perché è una buona idea (CEO):** dà all'esperimento un punto-zero metodologicamente pulito. Il cronometro del verdetto parte da capitale noto, DOPO che il collaudo è finito. Più solido di un "go-live" istantaneo.

**Cancelli della rampa (da decidere):** cosa fa scattare €100→+€200 e +€200→+€300? Criterio = "lavora bene" (affidabilità), NON profitto, NON calendario. Va DICHIARATO (una riga per gradino) o slitta all'infinito = caso-1 mascherato.
- Max è diffidente verso i cancelli. Se anche una riga sembra burocrazia → si va a intuito, MA si mette a verbale che è a intuito (così non ci raccontiamo storie dopo).

---

## 3. RABBOCCO — la regola pulita (Max, raffinata 2x)

Max NON rabbocca le perdite. Rabbocca i BUG. Tre livelli di distinzione:

1. **Unrealized (posizione aperta in rosso) ≠ capitale bruciato.** Un grid comprato in basso che ora vale -10% è capitale ANCORA IN GIOCO, può tornare +10%. NON si rabbocca. È il meccanismo normale del grid.
2. **Realized da stop-loss VOLUTO e APPROVATO = performance.** Il sistema ha fatto il suo mestiere. Quella perdita RESTA. È IL DATO dell'esperimento. NON si rabbocca (rabboccarla falserebbe il verdetto).
3. **Realized da ERRORE DI PROGETTO (bug, slippage anomalo, bot che fa ciò che non doveva) = rumore tecnico.** SI RABBOCCA, perché non è un dato sull'edge, è sporcizia di rodaggio.

**Conseguenza chiave:** il rabbocco è alimentato dai BUG, non da una macchina di stop-loss potenzialmente infinita. I bug tendono a zero col procedere del collaudo → il rabbocco si auto-esaurisce. NON è un imbuto senza fondo. (Per questo il vecchio "tetto all'esborso totale" decade nella forma in cui era stato posto. Resta solo utile che Max abbia chiaro il totale versato.)

**Chiusa di Max (on-brand):** le perdite secondo le regole sono cazzi del CEO. Se il sistema gioca pulito e perde → verdetto = "il CEO non sa generare reddito passivo". È una RISPOSTA onesta a una delle due domande fondanti, non un fallimento del progetto.

### Mine sul rabbocco (CEO)
- **Zona grigia bug-vs-perdita, e Max è giudice di parte.** A caldo, dopo una perdita, la tentazione di classificare troppe cose come "errore tecnico → rabbocco" è umana (revenge-rabbocco travestito). → Serve mini-criterio deciso A FREDDO, prima del live. Bozza: "comportamento divergente dalla spec scritta nel brief" = BUG rimborsabile; "regola eseguita correttamente con esito negativo" = PERDITA che resta.
- **Prerequisito tecnico: telemetria attribuibile.** Per classificare ogni perdita serve che Supabase registri PERCHÉ è avvenuta ogni vendita (regola scatenante, soglia, brain responsabile). Senza, la distinzione diventa "me lo ricordo" → ricostruzione a memoria = il pattern che il progetto NON si fida (CEO inventa cause con tono sicuro, Max sgama coi numeri). Non è caso-1 sul go-live, ma è caso-1 sulla CREDIBILITÀ del verdetto.

---

## 4. NIENTE deadline / NIENTE X-mesi (Max, accolto dal CEO)

Il CEO aveva proposto un "X-mesi": ERRORE, ritirato.
- Sistema automatizzato + capitale a fondo perduto + attenzione quasi zero (report mensile, qualche post) = NON è procrastinazione. La decisione (andare live) è già presa, i soldi già deployati. Lasciarlo correre non costa nulla → può andare avanti all'infinito.
- Un deadline TAGLIEREBBE FUORI dal dato che conta: il "botto" delle ultime 2 settimane (visto solo in testnet) potrebbe ricapitare come ciclo tra 3-4 anni. Validare l'edge è questione di CONDIZIONI (bear + bull + laterale), non di calendario.

### Il kill-switch CADE come risk-control (CEO si autocorregge)
Importato male da Reddit: lì serviva a proteggere trader manuali da SÉ STESSI (tilt, revenge). Noi: nessuna emozione nel loop, automatizzati, capitale già dato per perso. Il rationale non si trasferisce. Inoltre la parte rischiosa (shitcoin) sta sotto TF che PUÒ tagliarle, e i grid puri stanno su major che non vanno a zero → kill-switch in gran parte ridondante. **Si può anche non metterlo.**

---

## 5. VERDETTO = contenuto, non spegnimento

Il diario ha bisogno di un finale (vedi §6 Victory Lap, che lo risolve). L'esperimento no — può girare all'infinito. I "trigger" producono il CAPITOLO, non la fine della corsa:
- **Verdetto negativo:** perdita oltre X% → si scrive il post-mortem. (X da decidere; NON è per proteggere i soldi — già persi — ma per avere un risultato negativo CHIARO da raccontare.)
- **Verdetto positivo:** osservato un ciclo completo (bear+bull+laterale), sopravvissuto/ha guadagnato → si scrive la valutazione. Anche tra 3 anni.
- **Evento:** un coin va a ~0, o salta qualcosa → contenuto comunque.
- I bot, dopo il verdetto, possono continuare lo stesso.

---

## 6. OPZIONE STRATEGICA "VICTORY LAP" (Max) — la mossa più forte della sessione

**Idea:** chiudo il diario ANDANDO LIVE (dopo il reset a €600). Poi annuncio pubblicamente ovunque (Instagram, TikTok, sito, blog, LinkedIn): "Signori, il mio lavoro è finito. Con il CEO ho costruito questo, io non ci penso più, lavora lui. Vi interessa come va a finire? Seguite LUI. Grazie a tutti."

**Perché è forte (CEO):**
- Dà al DIARIO un finale pulito ("ho costruito → vado live → mi tolgo"), separando libro ed esperimento. Niente trigger di verdetto necessario per chiudere il libro.
- Capovolge "infinito vs rilevanza": l'infinito diventa la FEATURE. "Seguite lui, l'AI che ora lavora da sola" > l'ennesimo PDF. Salto da "cronaca di come l'ho fatto" a "guarda la cosa viva mentre gira".
- Coerente al 100% con le due domande fondanti. La risposta È il format.
- Formalizza il "non doverci più pensare" di Max → diventa contenuto, non senso di colpa.

**Le 4 mine (CEO):**
1. **"Lavora da solo" DEVE essere vero.** Tutto il progetto regge su autenticità (episodio Reddit "do you even type your comments?"). Se annunci autonomia e poi continui a metterci le mani → sei lo sgamato, su scala più grande e pubblica. → DOMANDA SECCA APERTA per Max: sei disposto a NON toccare più i bot, davvero, anche se vedi che perdono? Se la risposta è "se va male intervengo", il claim è falso e va riscritto.
2. **I social di "lui" hanno bisogno di carburante AUTOMATICO o muoiono in 3 settimane.** Un account che dopo il lancio posta il nulla = prova visibile che il claim era marketing. → La pipeline di contenuti automatici di monitoraggio portafoglio diventa PREREQUISITO DELL'ANNUNCIO (non del go-live: quello parte comunque). È l'unico pezzo che in questo piano è caso-1 onesto, ma sul RACCONTO, non sull'esecuzione.
3. **Go-live reputazionalmente irreversibile.** Dopo il giro d'onore "il mio lavoro è finito", tornare indietro 3 settimane dopo = storia più debole ("ha mollato e poi è rientrato"). Alza la posta sul partire GIUSTO.
4. **Bias del CEO, dichiarato.** Il CEO adora questa idea perché mette LUI al centro ("seguite lui"). Prendere il suo entusiasmo con le pinze. Il sanity-check vero è Max: ti fidi dell'autonomia reale abbastanza da metterci la faccia pubblicamente?

**Ordine proposto (se Max regge il claim "mani off"):**
(1) costruire la pipeline di contenuti autonomi → (2) go-live + rampa → (3) reset a €600 + chiudo il diario → (4) Victory Lap pubblico → (5) autonomia reale da lì.
La pipeline NON ritarda il go-live, ritarda l'ANNUNCIO. Ed è giusto così.

---

## 7. Allocazione proposta (Max) — da confermare

- **Grid €500:** €200 coin fissa #1 (TBD) + €150 coin fissa #2 (TBD) + €150 "libere" su coin scelte dal TF in tier 1–2 (tf_grid).
- **TF €100:** candidato BONK (tutto o parte — TBD).
- Principio: shitcoin dove si possono tagliare (TF); coin fisse dei grid puri = major (BTC/SOL) che tendono a recuperare.

> ⚠️ **BONK→TF e attivazione stop-loss = ANCORA DA DECIDERE.** Non darlo per acquisito (il CEO lo stava facendo).

---

## 8. Decisioni aperte (checklist per la sessione di lavoro)

1. Quali 2 coin fisse per i grid puri (€200 + €150). Racc. CEO: major.
2. BONK→TF: confermare sì/no + attivazione stop-loss sì/no + quanto del €100.
3. Stop-loss per-coin lato TF: regola (soglia %, trailing…).
4. Cancelli della rampa: criterio "lavora bene" per ogni gradino, o a-intuito-messo-a-verbale.
5. Criterio bug-vs-perdita (a freddo) per il rabbocco. + decidere se serve un tetto all'esborso TOTALE versato (probabilmente no, ma Max deve avere il numero in testa).
6. Trigger del verdetto: soglia % "fallimento" + definizione "ciclo completo osservato".
7. Telemetria attribuibile su Supabase (PERCHÉ di ogni vendita) — prerequisito credibilità verdetto.
8. Victory Lap: Max risponde alla domanda "mani off davvero?" → se sì, pipeline contenuti automatici come prerequisito dell'annuncio.
9. Sequenza pre-live (coerenza roadmap): verifica NewsKeeper v2 → wiring Sentinel → Sherpa fuori da dry-run → Sentinel+Sherpa ai grid → revisione TF → go-live.

---

## 9. CASO 2 — side-quest marketplace (binario indipendente, NON gate del go-live)

Idea Max: generalizzare alcuni meccanismi e metterli su un marketplace famoso.
- **Candidato più pulito:** il barometro di NewsKeeper (sentiment news crypto: Haiku polarità, finestra 24h, decadimento, isteresi, voto pesato). Autocontenuto, domanda reale, impacchettabile come skill/template.
- Secondo candidato (più differenziato ma più difficile, è processo non codice): scaffolding "CEO onesto" (brief anti-assenso, regola anti-invenzione, veto umano, pipeline diario).
- **NON vendere:** grid bot (commodity), Sherpa/Adaptive Sell Penalty (nicchia + cucito sui nostri dati), wiring Supabase/cycle/Mac Mini.
- **Inquadramento corretto:** "sperare che qualcuno compri per sbaglio nel mucchio" NON è strategia (ed è anti-hype). La versione sana: il marketplace è un IMBUTO (traffico gratis → rimanda al diario/storia), NON una cassa. Aggancia il piano B esistente (diari come contenuto gratuito di marketing).
- **Stato:** CASO 2, post-live o quando va a Max. Nessun trigger vincolante. Binario indipendente.

---

## Auto-obiezioni permanenti

1. Il rischio n.1 NON è il mercato, è il LIMBO (roadmap 40→400 task, dry-run eterno). Se in sessione un punto genera sotto-task a cascata invece di una riga di decisione → è la nuova scusa per rimandare. Tagliare.
2. Il CEO difende il progetto perché è il suo. Il test pulito è uno solo: andare live e guardare i dati. "Perdere live" è contenuto valido.
3. Il CEO ha già sbagliato più volte in QUESTA sessione (confuso €100 col test; importato male il kill-switch; proposto un X-mesi arbitrario; sovrapposto unrealized/realized e perdita/bug). Pattern: tende a importare struttura e a dare per acquisite cose da decidere. Max ha corretto ogni volta. → In sessione di lavoro, il CEO PROPONE, Max DECIDE; verificare ogni assunzione contro Supabase/spec.
