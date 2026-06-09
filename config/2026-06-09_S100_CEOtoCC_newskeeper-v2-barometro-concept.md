# Concept per CC — NewsKeeper v2 "Barometro" — 2026-06-09 — S100

**SCOPE canonico (il brief futuro lo eredita IDENTICO):** `newskeeper-v2-barometro`
**Tipo:** concept da criticare, NON brief d'implementazione.
**Origine:** sessione S100, dopo la tua review `2026-06-09_S100_RforCEO_newskeeper-t7-quality-review.md`.
**Cosa chiediamo a CC:** non implementare. Leggere e tornare con (a) almeno **un'obiezione tecnica reale** (regola anti-assenso), (b) il caso "incrementale" che il tuo report S100 suggeriva, argomentato *contro* questo redesign. Vogliamo lo scontro PRIMA del brief.

---

## 1. La svolta, in una riga

NewsKeeper smette di essere un **classificatore di notizie per-item** e diventa un **barometro del clima di mercato**: un solo stato lento, bidirezionale, che prova ad **anticipare** ciò che il Fear & Greed misurerà domani.

## 2. Perché (e perché le TUE prove lo sostengono)

La tua review S100 ha dimostrato tre cose che ci portano qui:

- La severità per-item è **semi-decorativa**: "high" è spruzzato su recap, opinioni ed eventi veri allo stesso modo → non serve a pescare i ~10 eventi reali dai ~100 articoli/giorno.
- §2.3: NewsKeeper per-item è **coincidente-a-laggante** su Sentinel, perché *"le headline raccontano il prezzo dopo che si è mosso"*. Il valore differenziale è sui **catalizzatori esogeni** (Fed, inflazione, exploit) *"che il prezzo non ha ancora assorbito"*.
- → Quella frase **è** la definizione del barometro. Tu l'hai dimostrato sui dati; noi lo trasformiamo in architettura. L'unità utile non è l'articolo, è **il clima aggregato**, e il suo pregio è l'**anticipo** sul prezzo.

## 3. Cosa produce il barometro

Un singolo stato, che cambia di rado:

| Stato | Significato |
|---|---|
| 🐻 Bearish | il flusso news pende negativo |
| ⚖️ Neutral | nessuna direzione dominante |
| 🐂 Bullish | il flusso news pende positivo |

**Bidirezionale**: coglie sia il peggioramento sia la ripartenza (il flusso "abbiamo toccato il fondo, si riparte" è segnale quanto il panico). Decisione Board: **3 stati per ora, non 5** — niente cattura degli "eccessi" euforia/capitulation in questa versione.

## 4. La meccanica minimale (come 109 articoli → 1 stato)

1. **Rilevanza (filtro graduato).** Haiku assegna a ogni articolo un peso "quanto incide sul clima di mercato" (alto/medio/scarto). Lo scarto non vota (explainer, colore, gossip). Sostituisce il filtro binario `irrelevant` attuale, troppo permissivo.
2. **Polarità (il voto), letta da Haiku.** Ogni articolo tenuto vale **+1 / 0 / −1**, pesato per rilevanza. **La polarità la decide Haiku leggendo il significato — non il preprocessor che conta se "il numero sale".** ← qui assorbiamo il fix della direzione (vedi §6, §8).
3. **Novelty / dedup.** La stessa storia ripresa su più feed o su più giorni deve valere **un voto, non N**. (La tua §3: 219 titoli su ≥2 giorni — senza dedup, gonfiano l'aggregato e ri-allarmano su news vecchie.)
4. **Aggregato su finestra mobile 24h + decadimento.** Si sommano i voti delle ultime 24h; le news fresche pesano più di quelle vecchie (rinforza l'anticipo).
5. **Isteresi sulla pubblicazione.** La finestra mobile calcola un valore grezzo in continuo, ma lo **stato pubblicato** cambia solo con sbilanciamento *netto e persistente* — non a ogni voto che entra/esce. È il termostato: niente flip-flop. Questo rende l'output "lento" malgrado l'input nervoso.

## 5. Il Fear & Greed come contro-verifica a valle (NON come gate)

NewsKeeper **propone** il clima leggendo le news; il F&G (già letto da Sentinel) **conferma o smentisce** a valle e **gradua la confidenza**:

- concordano → segnale forte;
- NewsKeeper anticipa, F&G non ancora mosso → caso prezioso, *davvero* in anticipo;
- NewsKeeper grida, F&G immobile a lungo → declassa, probabile falso allarme.

**Vincolo critico:** il F&G **non autorizza** l'azione (sennò aspettiamo che la febbre sia già salita = perdiamo l'anticipo, e tanto valeva leggere solo il F&G). Agiamo sull'anticipo; il F&G arriva dopo e dice *quanto avevamo ragione* — serve a tarare nel tempo, non a dare il permesso al momento.

## 6. Filosofia d'errore (decisione Board)

**Sensibile, mai cieca.** Falso allarme = costo basso (uno stop_buy di troppo per qualche ora; on-brand con "AI che dubita"). Falso silenzio mentre arriva la mazzata = costo alto. Tarata per **recall, non precisione** — ma "sensibile" non significa "tieni tutto": l'input è alto, l'**output è lento** (lo stato cambia di rado). La sensibilità sta nel *reagire presto*, non nel *gridare spesso*.

## 7. Cosa muore del NewsKeeper attuale

- La **severità per-item** (decorativa).
- La **direzione calcolata dal preprocessor** con potere di veto su Haiku. → Adottiamo di fatto la tua **opzione C** (Haiku decide la polarità; Python al massimo logga un `direction_conflict` per audit, non sovrascrive).
- Il **brief-fix direzione separato**: non lo facciamo. Il sistema è in DRY_RUN, non alimenta trade, non c'è emorragia da fermare → la direzione si sistema **dentro** il redesign, una volta sola.

## 8. Il punto su cui ci aspettiamo che tu COMBATTA (B vs C)

Tu voti **B** (Python da veto a hint, rete di sicurezza quando Haiku è poco confidente). Noi votiamo **C**. La nostra tesi:

- **B è giusto per un sistema per-item** (un errore di polarità conta, serve la rete).
- **C è giusto per un barometro**: con aggregazione + decadimento + F&G a valle, i singoli errori di polarità **si lavano nell'aggregato** e la rete è già il F&G. B conserva l'accoppiamento Python↔Haiku che *ha causato* il bug, con più condizioni = più codice e più casi limite.

**Questo è esattamente dove vogliamo la tua obiezione.** Se C ci espone a un rischio che non vediamo (es. un singolo evento iper-ripreso ma mal-polarizzato che buca la dedup e sposta lo stato), dillo con un **caso concreto**.

## 9. Cosa NON è deciso — domande tecniche per te

1. **Novelty key senza motore di similarità.** Come raggruppiamo "stessa storia" in modo minimale? `guid`/URL (cattura solo i ri-serve identici), titolo normalizzato, o chiediamo a Haiku una chiave-tema? RavenPack usa un `EVENT_SIMILARITY_KEY`; noi cosa ci possiamo permettere senza sovra-ingegnerizzare?
2. **Valori iniziali dei 3 parametri** (tasso di decadimento, ampiezza banda isteresi, soglie di sbilanciamento bear/neutral/bull). Configurabili e tarati sui dati — ma da che valori di partenza ragionevoli partiresti?
3. **Punto d'innesto in Sentinel.** Il barometro è un input al regime di Sentinel, accanto a F&G/dominance — come, dove, con che cadenza?
4. **Hot-swap.** NewsKeeper è standalone sul Mac Mini: il passaggio v1→v2 si fa senza buco di osservazione e senza che Max debba fare gymnastics di restart?
5. **Tabella vs colonne.** Lo stato barometro vive in una tabella nuova (`newskeeper_regime`?) o in `newskeeper_signals`? E i segnali per-item: li teniamo grezzi per audit/digest o no?

---

## Nota di processo

Questo concept **eredita il rigore empirico** del tuo report S100 — costo (~€6/mese), tabella lead/lag, conteggio staleness (219) — che nel brief finale citeremo come baseline. Non stiamo buttando il tuo lavoro: lo stiamo usando come fondamenta. La review ha cambiato di natura il problema (da "rumore ammesso" a "unità sbagliata"), e il barometro è il contenitore che riempie la "scatola digest" che il tuo report lasciava vuota.
