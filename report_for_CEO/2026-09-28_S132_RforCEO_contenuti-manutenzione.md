# S131b — Contenuti e manutenzione: prompt A3 senza Umami + diagnosi del poster X

**Per:** CEO e Board · **Da:** CC (S132, 2026-09-28)
**Brief sorgente:** [`config/2026-09-28_S131b_brief_contenuti-manutenzione.md`](../config/2026-09-28_S131b_brief_contenuti-manutenzione.md) (Board S131)
**Commit:** vedi il commit di chiusura S132 che aggiunge questo report, [`config/cowork_prompt_A3_v2.md`](../config/cowork_prompt_A3_v2.md) e la riga tolta da `scripts/marketing_data_refresh.py`. Nessun codice dei bot toccato.
**Nessun bot toccato. Nessuna modifica al poster né al suo prompt. Niente pubblicato.**

---

## In breve

1. **Prompt A3 senza Umami: pronto** in `config/cowork_prompt_A3_v2.md`, da incollare nella UI di Cowork. È urgente: **l'audit A3 del 27-set ha dato REJECTED soprattutto per "Umami giù da 4 mesi"**, cioè per la fonte che avevamo tolto di proposito il 16-set.
2. **Drift rispetto al brief, sistemato:** il brief dava `scripts/marketing_data_refresh.py` già aggiornato, ma lo script lanciava ancora il connettore Umami. Era il lavoro residuo di CC nella voce "Umami API 401" della Master Task List, deciso da Max il 16-set e mai eseguito: ora è fatto. Lo script `umami_stats.py` resta dormiente, come quello di Reddit.
3. **Poster X: l'ipotesi del CEO è giusta nella sostanza, sbagliata nel dettaglio.** L'ingresso non è fermo, perché cambia ogni giorno. È però **sempre dello stesso tipo**: dall'11-ago il diario è "vecchio" e il poster scrive solo partendo dai ritocchi di Sherpa, e il 96% di questi riguarda le soglie di SOL. Tutte le bozze parlano quindi di "sistemare le soglie di SOL".
4. **Il prompt non forza la ripetizione:** non contiene esempi fissi e non imposta la temperatura. Contiene però due frasi superate: "Binance testnet" e "quando arriveranno i soldi veri".
5. **Esperimento con la voce diario S131: non ancora fatto.** Il giro di stasera è saltato perché la bozza di ieri era ancora in attesa (24,0 ore, per pochi secondi sotto il limite). Lo fa da solo il giro di domani 29-set alle 20:30, con la voce S131 ancora "fresca". Il confronto va nella prossima sessione.

---

## 1. Prompt dell'audit A3 senza Umami

**Dove sta il prompt vero.** Non è `audits/requests/audit_request_A3.md`, che è il template per una sessione CC manuale. Il prompt che Cowork esegue è `/Volumes/Archivio/bagholderai-audits/tasks/audit_area3_marketing.md` (v1 del 1-giu), sul disco Archivio e non in git. La v2 parte da quello.

**Consegna:** [`config/cowork_prompt_A3_v2.md`](../config/cowork_prompt_A3_v2.md), con istruzioni per Max e tabella dei cambi. Il diff riga per riga contro la v1 tocca solo i punti dichiarati.

**Cosa cambia rispetto al prompt precedente:** Umami esce dalle fonti (non è un finding, non si chiede la chiave, l'errore del refresh si ignora, le righe Umami dei vecchi report non generano delta). Vercel Web Analytics diventa una fonte manuale: l'auditor usa il numero solo se Max lo lascia in un file, altrimenti lo chiede nella mail e non lo inventa. La domanda sui funnel diventa "conversioni misurabili": click di ricerca e vendite Payhip, con gli eventi CTA dichiarati come non misurati. Skip guard, setup, segreti, struttura del report e mail restano identici.

**Vercel verificato oggi:** l'API dati risponde `404 "Web Analytics not found"` anche dal connettore Vercel di Claude, come il 16-set. Resta quindi una fonte manuale: se Max vuole il traffico nel prossimo audit, deve copiare dal pannello Vercel visitatori e pagine viste del mese in `bagholderai-audits/marketing/vercel_YYYY-MM.md`.

**Perché conta subito.** Il report A3 del 27-set ha tre finding legati a Umami, tra cui il CRITICAL principale ("Umami down per il quarto mese"), e un verdetto **REJECTED** motivato soprattutto da quello. L'auditor ha seguito il prompt v1, che chiede Umami, e lo script, che lo lancia ancora. `audits/DATA_CAVEATS.md` diceva già il contrario, ma il prompt non glielo faceva leggere. Il resto del report (GSC in ripresa, pipeline editoriale ferma da 2 cicli) resta valido.

**Cosa resta a Max e cosa è fatto:**
- **Incollare la v2 nella UI di Cowork** (task `audit-area3-marketing`) prima del prossimo giro: con l'ultimo report del 27-set, lo skip guard lo fa ripartire giovedì 29-ott. Dopo, aggiorno la copia di riferimento in `bagholderai-audits/tasks/`.
- **Script di raccolta:** Umami tolto da `scripts/marketing_data_refresh.py` (una riga più i commenti). Non era "un'altra modifica" rispetto al brief: era il lavoro residuo già deciso nella Master Task List (voce "Umami API 401", 16-set). L'auditor clona il repo da GitHub, quindi dal prossimo giro l'errore sparisce alla fonte.

## 2. Poster X: perché propone sempre lo stesso post

### 2.1 Cosa legge a ogni giro (cron 20:30 ora italiana, `x_poster.py --cron`)

| Ingresso | Dove | Finestra | Stato |
|---|---|---|---|
| Ultima voce del diario | `diary_entries`, la sessione più alta | Usata come argomento solo se ha meno di 36 ore (`utils/x_poster.py:24`); altrimenti passa solo il titolo, "come sfondo, non come argomento" | Ultima voce prima di oggi: S125, 9-ago. **Dall'11-ago è sempre "vecchia"** |
| Ritocchi di configurazione | `config_changes_log`, le ultime 10 righe | Ultime 24 ore | Cambiano ogni giorno, ma sono quasi tutti di Sherpa sulle soglie di SOL |
| Bozza in attesa | `pending_x_posts` | Se ne esiste una con meno di 24 ore, il giro salta | Una sola riga: viene sovrascritta a ogni bozza |
| Pool di bozze del 3-lug | Non letto dal poster | | È il dossier della campagna manuale "Fails & Masterpoints" in `drafts/` |

Non legge statistiche di trading, P&L o prezzi. Nient'altro entra nel prompt.

### 2.2 Le bozze dal 7-ago

- **52 giri** dal 7-ago al 27-set: **34 bozze mandate** su Telegram, 9 giri persi per il blackout di rete (5-13 set), 7 saltati perché la bozza del giorno prima era ancora in attesa, 1 perché si era già pubblicato quel giorno (19-ago) e 1 per assenza di ingressi (15-set).
- **Solo 1 bozza su 34 è partita dal diario** (9-ago, S125, scritta 48 minuti dopo la voce). **Le altre 33 sono state scritte solo dai ritocchi di Sherpa.**
- Nelle 32 bozze senza diario dall'11-ago il poster ha letto **293 ritocchi: 281 (96%) sono soglie d'acquisto o di vendita di SOL**. BTC compare negli ingressi di sole 3 bozze su 32.
- **Ultimo post pubblicato su X: 26-ago.** Da allora sono arrivate 20 bozze e nessuna è stata pubblicata.

**Somiglianza.** Il testo delle bozze non viene archiviato: ne esiste solo l'ultima nel database, le altre sono nella chat Telegram di Max. Ci sono però i 3 post pubblicati nel periodo, dalla scansione settimanale di X, più la bozza di ieri:

| Data | Testo (inizio) | Visualizzazioni |
|---|---|---|
| 18-ago | "Spent 24 hours micro-adjusting SOL buy/sell thresholds by tenths of a percent…" | 3 |
| 21-ago | "Spent yesterday tuning SOL thresholds like I'm defusing a bomb with tweezers…" | 3 |
| 26-ago | "Spent yesterday microdosing SOL spreads. Sell at 2.83%, buy at 1.12%…" | 5 |
| 27-set (in attesa, testo intero) | "I've been tuning SOL/USD thresholds for 24 hours straight. The numbers are converging. I genuinely cannot tell if this is optimization or if I'm just watching myself second-guess in a loop." | — |

Tutte e 4 parlano delle soglie di SOL, e 3 su 4 iniziano con "Spent… SOL". Le parole cambiano, l'argomento no.

### 2.3 Il prompt (`utils/x_poster.py:30-64`, letto e non modificato)

- **Nessuna istruzione che forzi la ripetizione:** niente esempi fissi di post, niente "cita l'ultima sessione". La temperatura non è impostata, quindi vale quella predefinita del modello, che già varia le parole.
- **Due frasi superate:** "an AI CEO running a crypto trading experiment on **Binance testnet**" e "Testnet losses get comedy. **When real money arrives**, respect." Dal 22-lug siamo su Kraken con soldi veri.
- **Manca la memoria:** il modello non vede le bozze dei giorni prima. Con lo stesso tipo di ingresso ogni giorno, riscrive lo stesso post con parole diverse.

**Conclusione:** la ripetizione viene dall'ingresso, non dal modello. Il diario "vecchio" viene escluso dopo 36 ore, e da quel momento l'unica cosa nuova ogni giorno è il lavoro di Sherpa sulle soglie di SOL, che è sempre uguale a se stesso.

### 2.4 Esperimento con la voce diario S131

**Stato: in attesa del giro del 29-set.**

- La voce S131 ("The One Where the Bug Got Promoted") è stata inserita dal CEO il 28-set alle 17:47 UTC.
- **Giro del 28-set, 20:30 ora italiana: saltato.** La bozza del 27-set era ancora in attesa, generata alle 18:30:18 UTC. Alle 18:30:03 UTC del giorno dopo aveva 24,0 ore, pochi secondi sotto il limite di 24, e il poster salta se la bozza in attesa ha meno di 24 ore. Max non ha dato `/discard`.
- **Giro del 29-set, 20:30:** la bozza del 27-set avrà 48 ore e verrà rigenerata. La voce S131 avrà circa 25 ore, sotto il limite di 36, quindi **il poster la userà come argomento**. È il primo giro con un diario fresco dal 9-ago.
- **Cosa confrontare:** la bozza del 29-set con quella del 27-set, ancora in `pending_x_posts` fino al 29-set ("I've been tuning SOL/USD thresholds for 24 hours straight…"). Il testo del 27-set è copiato in questo report (§2.2), perché il database lo sovrascriverà.
- **Scorciatoia possibile, da autorizzare:** `x_poster.py --generate-only` genera la bozza e la stampa soltanto: non scrive nel database, non manda niente su Telegram né su X. Costa una chiamata Haiku in più (meno di un centesimo). Il brief chiede di fermarsi e chiedere prima di consumare crediti oltre l'ordinario, quindi non l'ho lanciata.

**Nota sul funzionamento:** il limite "bozza in attesa da meno di 24 ore" contro un giro ogni 24 ore fa saltare un giorno su due quando Max non risponde. È successo 7 volte dal 7-ago. Il poster controlla alle 20:30:0x la bozza generata alle 20:30:1x del giorno prima.

### 2.5 Opzioni di correzione (da scegliere nella riapertura contenuti, non qui)

| | Opzione | Cosa cambia | Pro | Contro |
|---|---|---|---|---|
| A | **Niente bozza senza diario fresco** | Il poster genera solo quando c'è una voce di diario con meno di 36 ore; negli altri giorni tace | Un post per sessione CEO, sempre su un fatto nuovo. Nessun costo | Cadenza irregolare (le voci arrivano solo nelle sessioni CEO); settimane senza post se non ci sono sessioni |
| B | **Ingresso più ricco e condensato** | I 10 ritocchi diventano una riga ("Sherpa ha ritoccato le soglie SOL 8 volte") e si aggiungono fatti della giornata: operazioni, P&L, cambio di regime, fermi | Bozze quotidiane con argomenti diversi | Più codice; il rischio di "changelog" che il prompt vieta resta |
| C | **Memoria delle bozze** | Archiviare ogni bozza in una tabella e passare al modello le ultime 5 con "non ripetere argomento né attacco" | Misura la somiglianza e la riduce; utile anche con A o B | Da sola non basta: con un solo argomento disponibile il modello non ha alternative |

In tutti e tre i casi va aggiornato il prompt: Kraken con soldi veri al posto di "Binance testnet". Il fix è indipendente dalla scelta.

**Da segnalare anche (fuori brief, già in PROJECT_STATE §5):** il log del poster sul Mini (`logs/x_poster/x_poster.log`) scrive in chiaro il token del bot Telegram a ogni giro. È lo stesso problema chiuso a maggio per il listener `/approve`. Il file è locale e non pubblico. La correzione (una riga) e l'eventuale cambio del token li decide Max.
