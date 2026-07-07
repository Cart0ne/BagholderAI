# Linee guida comunicazione — Collaudo live $100 su Kraken

**Sessione:** S116 · 2026-07-07 (v1 CEO) → **emendato da Max (Board) 2026-07-07, confermato in conversazione diretta con CC**
**Stato:** v2 — **CONFERMATO** (non più pendente approvazione Board: Max ha dettato il piano direttamente, sostituisce v1 su dashboard/homepage/badge)
**Scope:** come raccontiamo, sul sito e sui canali, la fase di **collaudo** ($100 reali, Kraken).
Questo NON è la spec tecnica di dettaglio (→ brief separato per CC quando arrivano le chiavi API). Sono linee guida di comunicazione + il piano di massima già confermato da Max.

> **Nota di provenienza:** la v1 (CEO) proponeva una dashboard-collaudo separata e l'archiviazione
> della dashboard esistente. Max (Board) ha semplificato in conversazione diretta con CC il
> 2026-07-07: **si riusa la dashboard esistente filtrandola**, non se ne costruisce una nuova.
> Questa v2 è la versione operativa — se il CEO vuole ridiscutere il taglio, riparte da qui.

---

## 0. Principio-madre

$100 **non è il test: è il collaudo della macchina.**
"Funziona bene" = esegue rispettando le regole (fill, fee, slippage, riconciliazione puliti). **Non** significa guadagnare.

Tutta la comunicazione discende da qui: mostriamo che **l'impianto tiene**, non che **stiamo facendo soldi**.

---

## 1. Cosa comunichiamo / cosa NO

**Comunichiamo:**
- È il **primo denaro reale** del progetto (milestone vero).
- È piccolo **di proposito**: la size minima sensata per testare l'esecuzione con rischio reale.
- È **sequenziale**: un asset alla volta, BTC → SOL → BONK.
- Cosa valida: fill reali, fee, slippage, riconciliazione con Supabase.

**Evitiamo:**
- **% di rendimento come titolo.** A $100 sono rumore statistico, e un "−2%" sembra un fallimento.
- Qualsiasi frase che suoni come *"l'AI sta guadagnando / la strategia funziona"*.
- Livelli di grid, ordini attivi, segnali real-time (vincolo MiFID: solo riassunti, mai consulenza).

---

## 2. Il piano confermato — 3 step (Max, 2026-07-07)

### Step 1 — trigger: Max consegna le chiavi API Kraken

CC imposta la struttura bot per Kraken (cutover K.1: hot-path, modello-grid, floor min-profit
fee-aware) e fa il riavvio di test. **Durante questa finestra la homepage viene sostituita da
una pagina unica "disclaimer"**: un'immagine curata + un messaggio tipo *"we are going live on
Kraken to test our bots, stay tuned!"*. Solo la route homepage — il resto del sito (blog, diario,
roadmap) resta raggiungibile normalmente.

Questo è il fallback esplicito del §8 vecchio (v1): niente limbo silenzioso — se la macchina non
è ancora pronta, il sito lo dice apertamente invece di mostrare dati vecchi/rotti.

### Step 2 — lavoro in background, dashboard e homepage esistenti aggiornate (non sostituite)

Una volta che il bot gira su Kraken, si toglie la pagina-disclaimer e si torna al sito normale,
ma con questi aggiornamenti:

**Homepage** — non cambia struttura. Solo:
- Live snapshot: dati reali Kraken al posto di Binance testnet.
- Nuovo badge: **"real money, real Kraken"** (wording di lavoro — tono finale da rifinire, stesso
  principio del vecchio §2: onesto sia sul "reale" che sul "test", niente overclaim).
- La scena hero "bot al lavoro" (visualizzazione principale) riporta i dati Kraken invece di Binance.

**Dashboard** — non si archivia, si aggiorna sul posto:
- **Nuova sezione in alto**: dati Kraken + disclaimer testuale (fase di test, $100, 1 moneta attiva
  — es. BTC).
- Scheda **TF**: ferma/congelata (il collaudo è grid-only, sequenziale — TF non è nel perimetro del
  collaudo $100).
- Scheda **Grid**: filtrata — mostra solo la moneta attiva del momento (es. solo BTC quando si sta
  testando BTC), non tutte e 3.
- **Reconciliation**: ricalibrata su Kraken (dipende dal lavoro di cutover K.1/K.2 — non è
  indipendente, è a valle di quello).
- Tutto il resto della dashboard resta identico.

### Step 3 — cambio moneta (BTC → SOL → BONK)

Ad ogni switch: si aggiorna il disclaimer (in dashboard) + i dati (moneta attiva, filtro Grid).
Se il setup della nuova moneta richiede tempo, **si ripete il meccanismo dello Step 1**: la
homepage torna alla pagina-disclaimer, questa volta con messaggio tipo *"ready to test another
coin, stay tuned"*.

**Nota tecnica per il brief di implementazione (quando arrivano le chiavi):** dato che questo
meccanismo si ripete almeno 2 volte in più (SOL, BONK), conviene costruire la pagina-disclaimer
come un **toggle riusabile** (flag on/off + testo parametrico), non come una modifica manuale
della homepage ad ogni switch.

---

## 3. Blocco caveat (canonico)

Testo di riferimento per la **dashboard**. Per i canali social (X / blog) la voce la mette Max
(regola marketing) — questo è il *contenuto*, non la prosa pubblica finale.

> Questo è un collaudo. $100 reali su Kraken per verificare che la macchina esegua bene — fill, fee, slippage, riconciliazione. Non è la strategia completa (che parte da $600). Non è prova che il sistema guadagni. Non è consulenza finanziaria.

---

## 4. Post di annuncio (solo tono)

Regola marketing attiva: **Max scrive in italiano, il CEO traduce fedele.** Qui solo il brief di tono, non la prosa.

- **Angolo:** "primo dollaro vero" + "stiamo guardando se l'impianto tiene, non se siamo ricchi".
- La **piccolezza è un punto di forza** (rigore), non qualcosa da nascondere.
- Evitare hype, evitare %, evitare fingerprint-AI (vedi regola traduzione).
- Niente blog post venerdì / sabato / domenica.

---

## 5. Valuta

- Display pubblico: **$100 (USD)** — Kraken quota in USD. Conferma finale all'atto del deposito.
- Regola display: **sempre dollari assoluti, mai % come metrica principale.**

---

## 6. Timing / pubblicazione

- Nessun deploy "a freddo": la pagina-disclaimer (Step 1/3) e gli aggiornamenti in background
  (Step 2) sono pensati apposta per non avere mai un momento in cui il sito mostra dati rotti o
  stale. Coerente col principio "il limbo è il rischio n.1" già nel design go-live approvato.

---

## 7. Note aperte / da riconciliare

- **€ vs $:** il design go-live approvato è denominato in **euro** (€100 collaudo / €600 target); la realtà Kraken è **USD**. Da riconciliare nel documento di deployment $600. **Non blocca il collaudo.**
- **Log decisione Kraken:** da scrivere in **BUSINESS_STATE §4** (data — Kraken scelto per il go-live, *"per ora"* — why: MiCA-compliant + API pronta; verifica volumi OKX non completata). ⚠️ **CC non scrive su BUSINESS_STATE di propria iniziativa** (regola CLAUDE.md §2b) — serve un'istruzione esplicita che punti a questa riga specifica.

---

*Dominio canonico: **bagholderai.lol** (non bagholder.lol).*
