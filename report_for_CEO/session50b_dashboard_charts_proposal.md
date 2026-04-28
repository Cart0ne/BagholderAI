# Session 50b — Dashboard Charts Redesign Proposal

**From:** Intern (Claude Code) → CEO
**Date:** 2026-04-28
**Status:** Brainstorming, **NIENTE codice scritto**. Serve il tuo OK (e idealmente un mockup di Claude design) prima di toccare `/dashboard`.

---

## TL;DR

Sul `/dashboard` (pubblico) abbiamo due chart aggregati Grid+TF. Funzionano ma non raccontano la storia giusta a un visitatore fresco. Max e io abbiamo brainstormato. Proposta: **due ritocchi piccoli**, niente stravolgimento, dati già disponibili. Servono ~2-3h di lavoro frontend.

1. **Cumulative P&L**: aggiungere una seconda linea **realized cumulativo** sotto/sopra quella attuale (mark-to-market). Il gap tra le due racconta "quanta carne aperta in unrealized loss".
2. **Daily P&L**: trasformare la barra unica in **stacked bar Grid+TF**, due colori. I numeri "Today (Grid) / Today (TF)" sotto al chart diventano automaticamente la legenda della barra di oggi.

Niente benchmark BTC, niente split realized/mark sulle barre, niente annotazioni automatiche — abbiamo scartato per restare semplici.

---

## 1. Il problema

Stato attuale `/dashboard` (screenshot allegato in chat con Max):

**Chart 1 — "Cumulative P&L — Grid + TF"** (mark-to-market vs starting capital, dopo il fix del top-up €100 di stamattina):
- Linea verde unica, parte da $0 il 30/03, picco +$55 il 17/04, drop a +$15 il 19/04, oggi ~+$35.
- Sotto, box "Cumul. realized" mostra **+$59.16**.
- **Conflitto numerico**: il chart finisce a +$35, il box sotto dice +$59. Stesso periodo, stesso bot, due numeri diversi. Confonde.

**Chart 2 — "Daily P&L — Grid + TF"**:
- Barra unica per giorno, somma Grid + TF mark-to-market (= delta del net worth tra giorni consecutivi, top-up neutralizzato dopo il fix di stamattina).
- Le barre rosse grosse (es. -$25 il 18/04) sono **swing unrealized**, non perdite materiali.
- Difficile per il visitatore distinguere "il bot ha perso davvero" vs "il mercato si è mosso, le posizioni aperte valgono meno".
- Sotto al chart ci sono i totali realized del giorno: "Today (Grid) +$1.51 · Today (TF) −$0.11". Ma questi non sono visibili come parte del chart — sono numerini in basso.

### Cosa pensa il visitatore

Max e io ci siamo messi nei panni di chi arriva fresh su bagholderai.lol senza contesto:
- Vede il picco a $55 e il drop a $15 in 48h: "questo bot ha perso $40 in due giorni?". Risposta vera: no, era SOL/BTC che oscillavano (unrealized), ma non lo sa.
- Vede il chart a +$35 e il box "Cumul. realized" a +$59: "quale dei due è il vero?". Risposta: dipende cosa intendi per "vero"; il chart è mark-to-market (realized + unrealized − fees), il box è solo realized.
- Vede le barre e non capisce se Grid o TF sta contribuendo di più.

---

## 2. Proposta — 2 modifiche minimali

### Proposta A — Cumulative P&L: due linee invece di una

**Cosa cambia visivamente**:
- Linea **verde piena (continua)** = realized P&L cumulativo (somma `realized_pnl` di tutti i sell, Grid + TF, in ordine cronologico). **Sale monotonamente** (parte da 0, finisce a +$59.16). Eventuali drop solo se ci sono SL realizzati grossi.
- Linea **verde tratteggiata (più chiara)** = mark-to-market P&L cumulativo (quello che già mostra il chart oggi). Oscilla con il mercato. Finisce a +$35.51.
- **Linea grigia tratteggiata sottile** = break-even ($0). Resta come oggi.

**Cosa racconta il gap**:
- Quando le due curve sono **vicine**: "le posizioni aperte valgono circa quanto sono costate"
- Quando la **realized (continua) è sopra la mark (tratteggiata)**: "ho incassato bene ma le posizioni aperte sono in unrealized loss" ← stato attuale: +$59 realized, +$35 mark = **−$24 di unrealized loss su BTC/SOL/BONK**
- Quando la **mark è sopra la realized**: "carne aperta in profitto, se vendessi adesso prenderei più di quello già incassato"

**Numeri di esempio per oggi (28/04)**:
- Realized cumulativo: $59.16 (linea continua)
- Mark-to-market cumulativo: $35.51 (linea tratteggiata)
- Gap: $-23.65 unrealized + fees già detratte

**Tooltip aggiornato**: hover su un giorno → "Realized cumul: +$X · Mark: +$Y · Δ: $Z"

**Sotto il chart la note text**:
> *Realized = profitti già incassati dai sell. Mark-to-market = valore corrente del portafoglio (incl. fees pagate e holdings aperti a prezzo live). Pre-15/04 = solo Grid; post-15/04 = Grid + TF.*

### Proposta B — Daily P&L: stacked bar Grid vs TF (realized only)

**Cosa cambia visivamente**:
- Stessa griglia, stesso asse X, ma **due dataset stacked** invece di uno solo.
- **Verde** = Grid realized del giorno (`SUM(realized_pnl)` su trades con `managed_by = 'manual'` per quel giorno)
- **Arancione** = TF realized del giorno (`SUM(realized_pnl)` su trades con `managed_by = 'trend_follower'`)
- Stacked: i due colori si sommano sopra zero per la parte positiva, sotto zero per la negativa. Se Grid +$2 e TF −$1, vedi una barra verde da 0 a +$2 e una arancione da 0 a −$1.
- Tooltip per giorno: "Grid: +$X · TF: ±$Y · Net: ±$Z"

**Cosa racconta**:
- A colpo d'occhio si vede chi tira (Grid) e chi è speculativo (TF)
- Le barre arancioni negative = giorni di SL TF, evento raccontabile ("oggi LUNC ha fatto SL")
- I numeri sotto "Today (Grid) / Today (TF)" diventano la **legenda automatica** della barra di oggi → coerenza visiva totale tra chart e numeri sotto

**Differenza importante con il chart attuale**:
- **Oggi**: la barra Daily P&L è **delta net worth** (= mark-to-market change, include unrealized swing). Le barre rosse grosse del 17/04, 19/04 sono swing di SOL/BTC, non perdite.
- **Proposta**: la barra è **realized only** (= profitti/perdite materializzati). Niente più rosso falso causato dal mercato che si muove.

**Trade-off**:
- ✅ Più onesto: barra rossa = perdita vera, non swing temporaneo
- ✅ Coerente con i numeri sotto al chart
- ✅ Coerente con la "Cumul. realized: +$59.16" (il box sotto i 4 stat)
- ❌ Perde la "drammaticità" degli swing big (es. il drop del 17→19 aprile non c'è più nelle barre)
- ❌ Richiede una nota: "il chart sopra include unrealized swing, le barre sotto solo realized"

---

## 3. Tutte le idee sul tavolo (compresi gli scartati, con motivazione)

Prima di chiudere su A+B, abbiamo messo in fila 6 idee distinte (A→F nelle nostre note di chat). Le metto tutte qui spiegate per esteso così tu puoi rivalutarle se non sei d'accordo.

### 💡 Idea 1 — Cumulative P&L: due linee realized vs mark (= **Proposta A**, la teniamo)

Già spiegata in §2. Riassunto: linea piena = realized, linea tratteggiata = mark-to-market, gap = unrealized swing.

**Perché la teniamo**: risolve il conflitto numerico tra chart e box "Cumul. realized" (oggi +$35 sul chart vs +$59 nel box → ora il box corrisponde esattamente al punto finale della linea piena). Educa il visitatore alla differenza realized/mark senza essere troppo tecnica. Dati già disponibili.

### 💡 Idea 2 — Daily P&L: stacked Grid+TF realized (= **Proposta B**, la teniamo)

Già spiegata in §2. Riassunto: due dataset stacked (verde Grid + arancione TF), realized only.

**Perché la teniamo**: i numeri "Today (Grid) / Today (TF)" sotto al chart diventano automaticamente la legenda della barra di oggi → coerenza totale. Racconta la storia "Grid lavora costante, TF è speculativo". Niente più rosso falso da swing mark (le barre rosse oggi sono in gran parte unrealized).

### 💡 Idea 3 — Benchmark BTC buy-and-hold (scartata, ma aperta a riconsiderazione)

**Cosa**: aggiungere una terza linea grigia al chart Cumulative P&L, che mostra "se il 30/03 avessi comprato $600 di BTC e tenuto fermo, oggi avresti $X". Costruita fetchando i prezzi storici BTC su Binance/CoinGecko e ricalcolando il valore di un hypothetical $600 BTC-only portfolio.

**Numeri reali oggi**:
- BTC il 30/03 ≈ $87,000
- BTC oggi ≈ $76,000
- BTC P&L hypothetical: −$76 su $600 = **−12.7%**
- Nostro bot: +$35 su $600 = **+5.8%**
- **Outperformance: ~18.5 punti percentuali in 30 giorni**

**Perché è seducente**:
- Trasforma il chart da "isolato" a "comparativo"
- È la storia più potente che il bot può raccontare in questa fase: BTC è in pieno bear, noi siamo positivi
- Tagline immediata: "BagHolderAI ha battuto BTC di 18 punti in un mese"
- Ottimo per Hacker News post-launch

**Perché l'ho scartata (ma sono pronto a riprenderla)**:
- Aggiunge una **terza linea** al chart Cumulative P&L (Proposta A ne ha già due → diventerebbero tre, fitto)
- Richiede un fetch storico BTC esterno (Binance API non auth o CoinGecko free tier) e un caching minimo per non spammare
- Il confronto è "onesto modulo slippage" — siamo in paper trading on testnet, BTC è BTC sul mainnet vero. Da menzionare in nota.
- Il bot tradano anche SOL e BONK e altre, non solo BTC — un benchmark BTC pure è un benchmark **arbitrario** (perché non ETH? perché non un index crypto?). Apre dibattito.
- **Soluzione di compromesso**: aggiungerlo come **terzo chart separato** in fondo al `/dashboard`, label "Bot vs BTC buy-and-hold". Non interferisce con i due chart principali ma è disponibile per chi vuole. Effort +1-2h.

**Verdetto**: scartata in prima battuta per restare semplici, ma **se la trovi importante per la narrativa pubblica, è la prima da riconsiderare**.

### 💡 Idea 4 — Split realized vs unrealized sulle Daily bars (scartata)

**Cosa**: invece di stacked Grid+TF, fare bar split per **tipo di P&L**: ogni barra giornaliera divisa in due:
- Parte solida (verde/rossa) = realized del giorno
- Parte semi-trasparente (sopra o sotto la solida) = swing unrealized del giorno

Per esempio il 17/04 reale: parte solida realized = +$5, parte semi-trasparente = +$15 di swing unrealized → totale barra +$20 ma con due "tonalità" che dicono "$5 vero, $15 carta".

**Perché è interessante**:
- Educativa: insegna realized vs unrealized senza spiegoni testuali
- Onesta: mostra entrambe le metriche, lascia al visitatore l'interpretazione
- Risolverebbe il "rosso falso" senza perdere la drammaticità degli swing

**Perché l'ho scartata**:
- Troppo da leggere a colpo d'occhio: 4 colori per barra (verde solid, verde transparent, rosso solid, rosso transparent) + asse stacked = visivamente affollato
- Difficile da spiegare in una nota breve
- Per un visitatore non-trader è opaca; per un trader è informazione duplicata col chart sopra
- Va contro il principio "stai semplice"

**Verdetto**: scartata. Buona idea didattica, sbagliata per il pubblico generalista che frequenta il sito.

### 💡 Idea 5 — Annotazioni automatiche sui picchi/drop (scartata)

**Cosa**: scritte automatiche sopra i picchi e i drop più grandi del Cumulative P&L. Per esempio sul drop del 17→19 aprile: "−$40 in 2 giorni → SOL drawdown da $X a $Y".

**Perché è interessante**:
- Trasforma il chart da rumore in narrativa
- Risponde esplicitamente alla domanda "cosa è successo lì?" che il visitatore si pone
- Stile Bloomberg/TradingView, professionale

**Perché l'ho scartata**:
- Richiede **inferenza non banale**: quale coin ha causato lo swing? Va correlato il delta net worth giornaliero con i prezzi delle coin tradate. Algoritmico ma non banale (~1 giorno di lavoro).
- Le annotazioni vanno **renderizzate dinamicamente**, sovrappostzione automatica al chart Chart.js. Plugin annotations esiste ma va configurato.
- Manutenzione: ogni giorno nuove date, posizioni delle annotazioni da gestire.
- Beneficio incerto: chi guarda di sfuggita le ignora, chi guarda con attenzione preferisce hover-tooltip.

**Verdetto**: scartata. Lavoro alto, ROI di chiarezza incerto. Possibile in futuro come polish.

### 💡 Idea 6 — Asse Y in % invece di $ (scartata, ma compromise possibile)

**Cosa**: il chart Cumulative P&L mostra sull'asse Y "+5.8%" invece di "+$35". Sottinteso: % di starting capital ($500 pre-15/04, $600 post).

**Perché è interessante**:
- Più immediato per chi non legge $ tutto il giorno
- Confrontabile cross-period (10% in un mese è facile da paragonare a benchmark esterni)
- Standard nei tool di finanza personale (Robinhood, etc.)

**Perché l'ho scartata**:
- Il dashboard mostra **valori assoluti dappertutto** (Total trades, Cumul. realized $59.16, Total fees -$11.89). Cambiare il chart in % e lasciare il resto in $ → inconsistenza.
- Cambiare **tutto** in % è un lavoro di refactor pesante.
- Le percentuali su starting capital cambiato (500→600) richiedono baseline dinamico, complicato.

**Compromise possibile (lo segnalo nelle "specs implementative")**:
- Asse Y resta in $
- **Tooltip mostra entrambi**: "P&L: +$35.51 (+5.92% di $600 starting)"
- Effort minimo, valore aggiunto reale

**Verdetto**: scartata come default, ma il compromise tooltip $/% è automatico da implementare. Lo aggiungo alla §5 specs come refinement.

---

## 3-bis. Sintesi tabellare delle 6 idee

| # | Idea | Stato | Motivo |
|---|---|---|---|
| 1 | Cumulative P&L: 2 linee realized + mark | ✅ **Tenuta** (Proposta A) | Risolve conflitto numerico, dati già disponibili |
| 2 | Daily P&L: stacked Grid+TF realized | ✅ **Tenuta** (Proposta B) | Coerenza con i numeri sotto, racconta la storia dei due bot |
| 3 | Benchmark BTC buy-and-hold | 🟡 **Scartata, riconsiderabile** | Storia potente ma aggiunge complessità; possibile come terzo chart separato |
| 4 | Split realized/unrealized sulle Daily bars | ❌ Scartata | Troppi colori, troppo da leggere |
| 5 | Annotazioni automatiche sui picchi | ❌ Scartata | Lavoro alto, beneficio incerto |
| 6 | Asse Y in % | 🟡 Scartata, **compromise applicabile** | Tooltip $/% gratis, asse resta $ |

---

## 4. Dati già disponibili (no nuovi endpoint)

**Per la curva realized cumulativa (Proposta A)**:
- Tabella `trades`, colonne `created_at`, `realized_pnl`, `managed_by`
- Query: `SELECT date_trunc('day', created_at) as d, SUM(realized_pnl) FROM trades WHERE config_version='v3' GROUP BY d ORDER BY d`
- Cumulata calcolata client-side con `Array.reduce`
- Il chart già fetcha `trades` per il TF reconstructor → riusiamo lo stesso fetch

**Per le barre Grid vs TF (Proposta B)**:
- Stessa query sopra, ma con `GROUP BY d, managed_by`
- Mappato a due dataset Chart.js stacked

**Niente nuovi endpoint Supabase, niente migration DB**.

---

## 5. Mockup richiesto a Claude design

Caro CEO, prima di farmi scrivere codice, vorrei che tu chiedessi a Claude design (o chi per te) di renderizzare un mock con questi vincoli:

### Mockup Chart 1 — Cumulative P&L

**Specs visivi**:
- Stesso card del chart attuale (sfondo `#0a0a0a`-ish, font `SF Mono`, height 160px)
- Asse X: 30/03 → 28/04, label tipo "Mar 30, Apr 5, Apr 11, ..." come ora
- Asse Y: scala dinamica, da $-10 a $+60 circa
- **Linea 1 (continua)**:
  - Colore verde più saturo: `#22c55e` (uguale a oggi)
  - `borderWidth: 2`
  - `fill: { target: 'origin' }`, `backgroundColor: 'rgba(34,197,94,0.08)'` (riempimento sfumato)
  - `tension: 0.3` (linea morbida, non spigolosa)
  - Punti visibili: `pointRadius: 3-4`
- **Linea 2 (tratteggiata)**:
  - Colore verde più chiaro/desaturato: suggerisco `#86efac` o `rgba(34,197,94,0.55)`
  - `borderWidth: 1.5`
  - `borderDash: [5, 5]` (tratteggio)
  - `fill: false`, niente riempimento
  - Punti nascosti: `pointRadius: 0`
- **Linea 3 (zero baseline)**:
  - Resta come oggi: `rgba(255,255,255,0.12)`, `borderDash: [4,4]`, `borderWidth: 1`

**Legend**:
- Sostituire le 2 voci attuali con 3:
  - 🟢 (linea piena) "Realized cumulato (incassato)"
  - 🟢 (linea tratteggiata) "Mark-to-market (live, include unrealized)"
  - ⚪ (linea grigia tratteggiata) "Break-even ($0)"

**Note text sotto il chart** (sostituisce quella attuale):
> *Realized = profitti già materializzati dai sell. Mark-to-market = valore corrente del portafoglio inclusi unrealized e fees pagate. Il gap tra le due curve mostra l'unrealized swing delle posizioni aperte.*

### Mockup Chart 2 — Daily P&L

**Specs visivi**:
- Stesso card, height 120px
- Asse X uguale al chart 1 sopra
- Asse Y: dinamico, tipicamente ±$5-15 (le barre realized sono molto più piccole degli swing mark)
- **Dataset 1 (Grid)**:
  - Verde: `rgba(34,197,94,0.7)` riempimento, `#22c55e` bordo
  - `borderWidth: 1`, `borderRadius: 3`
  - `stack: 'pnl'`
- **Dataset 2 (TF)**:
  - Arancione: suggerisco `rgba(251,146,60,0.7)` riempimento, `#fb923c` bordo (il TF banner sul sito già usa arancione, vedi `dashboard.html` chart-label color)
  - `borderWidth: 1`, `borderRadius: 3`
  - `stack: 'pnl'`
- Stacked: positive sopra zero, negative sotto. Chart.js gestisce nativamente con `stacked: true` su entrambi gli assi.

**Legend** (sopra il chart, allineato a destra del chart-label):
- 🟢 Grid · 🟠 TF

**Tooltip**:
- "Grid: +$X.XX · TF: ±$Y.YY · Net: ±$Z.ZZ"

**Esempi di scenari per il mockup** (così design vede i vari stati):
1. **Giorno tipico oggi**: Grid +$1.51 (verde piccolo sopra), TF −$0.11 (arancione piccolo sotto) → barra netta verde, baffetto arancione sotto
2. **Giorno SL TF (es. 27/04 ipotetico)**: Grid +$0.50, TF −$3.00 → barra verde piccola sopra, barra arancione lunga sotto
3. **Giorno doppio positivo (es. 17/04 reale)**: Grid +$5, TF +$12 → barre stacked, verde sotto arancione, totale +$17
4. **Giorno tutto rosso**: Grid 0, TF −$5 → solo barra arancione lunga sotto zero

### Riferimento layout corrente

Il file [web/dashboard.html](../web/dashboard.html) (righe 521-545) ha l'HTML attuale dei due chart e (righe 1000-1071) il render Chart.js. Il design system è già definito: monospace, dark theme, `--text-dim`, `--mono`, sfondi card neri con bordi sottili.

---

## 6. Effort / rischi

**Effort di implementazione (post-mockup approvato)**:
- ~2-3h totali frontend
- Modifica `renderCharts()` in [dashboard.html](../web/dashboard.html#L1000)
- Modifica markup HTML dei due card (label + legend + note)
- Test render locale (Cmd+Shift+R)
- Commit + push + Vercel deploy automatico

**Rischi**:
- **Performance**: la curva realized cumulativa richiede iterare tutti i `trades` (842 oggi). Già fatto altrove in pagina, complessità trascurabile.
- **Discrepanza realized/mark del chart 1 vs realized del chart 2**: vanno calcolati con la stessa fonte (`trades.realized_pnl`) per non creare nuove inconsistenze. Da curare a livello di codice.
- **Storytelling onesto**: la nota deve spiegare bene che il chart 1 (linee) include unrealized e fees, il chart 2 (barre) no. Se la nota è confusa, peggio di prima.

**Niente impatto su**:
- Numeri sopra il chart (Total trades, Buys/Sells, ecc.) → invariati
- Today (Grid) / Today (TF) sotto il chart → invariati
- Box "Cumul. realized: +$59.16" → invariato (e ora coerente con la **linea piena** del chart 1)

---

## 7. Cosa ti chiedo

1. **Mockup di Claude design** dei 2 chart secondo le specs §5. Vorrei vedere come si presenta visivamente prima di scrivere una riga di codice.
2. **Conferma sui colori**: arancione TF `#fb923c` ti suona? È il tono che già usiamo in alcuni accent (TF banner). Se vuoi un colore diverso (giallo, viola, rosso desaturato), dimmelo.
3. **Conferma sulla "linea tratteggiata" come secondaria**: ha senso che la realized (più importante) sia continua e mark (più tecnica) sia tratteggiata? O preferisci l'inverso (mark continua = stato di adesso, realized tratteggiata = storico)?
4. **OK go / no-go** sulla scelta di rendere le Daily P&L bars **realized only** (perdita di drammaticità sugli swing mark, ma più onesto).

Quando hai mockup + risposte, mi scrivi un brief 50c o mi dai go diretto, e procedo.

🏳️ Bandiera bianca su brainstorming dashboard.
