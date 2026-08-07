# Report di sessione — S120 · Discussione architettura cervelli (brainstorming)

**Data:** 2026-07-20 · **Tipo:** brainstorming (no diary, no Supabase write) · **Presenti:** Max (Board) + CEO (Claude) · **CC:** assente
**Scope:** come si interfacciano Sentinel, NewsKeeper, Sherpa e TF, in vista del collaudo Grid ($100 → $500) e del successivo collaudo TF.
**Stato deliverable:** questo report + brief ricognizione `2026-07-20_S120_brief_brains_recon.md` (read-only, per CC nei prossimi giorni).

---

## 0. Perché questa discussione, ora

Il collaudo reale parte su **Grid puro** (BTC → SOL, $100). TF **non** entra nel collaudo iniziale;
si collauderà solo dopo il passaggio a $500. Quindi TF **non è bloccante**: c'è tempo per fare
ricognizione + design con calma, prima che tocchi denaro reale. Questa sessione serve a inquadrare
il ragionamento e produrre un brief di sola ricognizione — **non** a decidere l'architettura finale
(non abbiamo ancora lo stato reale del codice).

Innesco: un thread Reddit (r/CryptoTradingBot, "bot che deliberatamente non può fare trade") passato
da Max. Vedi §5 per le lezioni rubate.

---

## 1. Il principio-guida: niente voti sommati

Lezione centrale del thread Reddit, confermata empiricamente da un commentatore (Rare_Explorer) che
ha addestrato un meta-modello su 20 "voti" di indicatori e ha ottenuto **peggio del lancio di una moneta**:

> RSI, MACD, EMA, VWAP, pattern… sono **tutti derivati della stessa serie di prezzo**. Sommarli come
> "voti indipendenti" = contare lo stesso segnale N volte. Non è confluenza, è **un segnale travestito**.

**Test di ortogonalità** (Rushapoil, stesso thread): un input si guadagna il titolo di "conferma" solo
se **può essere in disaccordo col prezzo ed avere comunque ragione qualche volta**. Se è sempre d'accordo
col prezzo, è solo consistenza interna, non informazione nuova.

Applicato a noi:
- **Sentinel (Fear & Greed Index)** → sentiment/posizionamento, NON serie di prezzo. **Ortogonale.** ✅ (da validare, vedi §4)
- **NewsKeeper (RSS/eventi)** → event-driven, zero prezzo. **Ortogonale.** ✅
- **TF (EMA cross + RSI su 50 coin)** → **derivato dal prezzo.** NON ortogonale. È momentum travestito. ⚠️

**Conseguenza di principio:** i cervelli **non si votano tra loro**. Ognuno ha un mestiere diverso e
non sovrapponibile.

---

## 2. L'architettura logica su cui abbiamo convergiato

Non una media pesata, ma una **catena di autorità** con poteri diversi:

- **Un cervello:** Sentinel (legge F&G / regime).
- **Un traduttore:** Sherpa (traduce il regime in parametri operativi). Riuso di ciò che già esiste per il Grid.
- **Due esecutori:** Grid e TF, che ricevono lo stesso *tipo* di regolazione da Sherpa.
- **Un veto:** NewsKeeper, sopra tutto, fuori dalla logica d'ingresso.

Ruoli:

| Componente | Potere | Cosa fa | Cosa NON fa |
|---|---|---|---|
| NewsKeeper | **Veto / freno d'emergenza** | Sospende operatività su evento raro (hack, delisting, crollo esogeno) | Non predice il prezzo (è INCONCLUSIVE — verdetto barometro), non genera trade |
| Sentinel | **Regime** | Legge F&G, dichiara il clima | Non decide il singolo ingresso (F&G è in ritardo) |
| Sherpa | **Traduttore / arbitro** | Converte regime → parametri per Grid **e** TF | — |
| Grid | **Esecutore (airbag)** | Compra cali / vende rimbalzi, mercato laterale | Non insegue il trend |
| TF | **Esecutore (inseguitore) + selettore** | Sceglie i coin bullish e li scaglona | Non è un input di confluenza |

### 2.1 Il ritardo di F&G non è un bug, se usato bene
- **Come contrarian su asset consolidati (Tier 1-2):** F&G "extreme fear" arriva tardi = sei già nella
  zona bassa; su roba con floor storico, "vale poco ora" ≈ "rimbalza". Comprare lì è coerente col grid.
- **Come modulatore di cadenza, non di trigger:** un segnale lento è pessimo per "compra ORA", ma va bene
  per "in questo clima, dai più respiro tra un lotto e l'altro". Il ritardo non morde se regola il *ritmo*.

### 2.2 La modulazione è sulla CADENZA dei lotti, non sull'ingresso
Modello di Max (da validare contro il codice, vedi §4):
- **In FEAR, dopo il 1° BUY:** allarga la distanza prima del 2° lotto (più pazienza, il coltello può ancora cadere).
- **In GREED, dopo il 1° SELL:** allarga la distanza prima del 2° sell (lascia correre il profitto).

Sono gli stessi *tipi* di leva che Sherpa già gira sul Grid (spacing buy/sell, size lotto).

### 2.3 Polarità invertita per tier
- **Tier 1-2 (consolidate):** F&G **contrarian** (aggressivo in fear, prudente in greed).
- **Tier 3 (small-cap):** F&G **momentum** — spente di default, riaccese da Sherpa **solo in greed/extreme greed**
  (non hanno floor: l'unica finestra in cui pagano è l'euforia diffusa).

### 2.4 Due filtri distinti, da non confondere
- **Filtro-universo statico** (`> X`): *quali monete esistono* per TF. Applicato **una volta**, all'ingresso
  della scansione. Taglia le vere shitcoin a prescindere dal regime.
- **Tier (1/2/3):** *come tratti ciò che resta*. Dinamico, gestito da Sherpa per regime.
- ⚠️ **Anti-invention:** la soglia `X` e la sua metrica (**market cap** o **volume**?) non sono confermate.
  Lo screenshot TREND SCAN mostra tier tagliati per **volume** ($100M / $20M). "Tagliare le shitcoin" di
  solito si ragiona in **market cap**. Non sono la stessa cosa. **Numero + metrica da recuperare da CC/file.**

---

## 3. Il dato reale che ha aggiustato il ragionamento (ETH tf_grid)

Durante la sessione abbiamo letto da Supabase la posizione **ETH/USDT `managed_by='tf_grid'`** (cycle
`testnet_2`): è l'**hand-off TF→Grid già live**, non teorico. Osservazioni:

- TF ha solo **selezionato** ETH. La gestione è **grid puro** (buy −2%, sell +2,5% "greed decay").
  → l'hand-off, in pratica, rende ETH una **posizione-airbag**, non un motore di trend.
- Realized ≈ **+$4,23** in ~5 settimane (15/06 → 20/07); posizione ora ~chiusa (0,0001 ETH di polvere).
- `capital_allocation` verificato = **$46,67** (NON $100; il "$100 slot TF" del lineup go-live ≠ budget di test).
  `capital_per_trade` = $15,56 (3 lotti).
- **Excess vs hold:** +$4,23 su $46,67 = **+9,1%** contro hold ETH **+4,8%** → **batte l'hold** (~2×) su questo campione.
- ⚠️ **Caveat pesante:** è **N=1** e nel regime **più favorevole al grid** (choppy + mildly bullish). Non dice
  nulla su bull dritto (hold stravince) o crollo. Il rendimento *vero* va calcolato **time-weighted**
  (capitale davvero a rischio nel tempo, non il budget fermo) → lavoro da brief separato per CC.

**Bandiera rossa operativa:** trade "LAST SHOT" del 20/07 con `check $1.585,50 → fill $1.829,47`
(**slippage +15,39%**). Su testnet è book vuoto; su mainnet a size grande, un tick sporco che innesca un
buy che fila 15% più su è denaro vero. Da mettere tra i rischi go-live, non tra i cosmetici.

---

## 4. I tre buchi aperti (→ oggetto del brief di ricognizione)

Tutti **"undetermined"** senza guardare il codice. Progettare l'architettura prima di chiuderli = costruire sulla sabbia.

1. **Sherpa tocca davvero le righe `tf_grid`?** I dati ETH mostrano parametri **statici** e "greed decay"
   apparentemente **tempo-based** (age in minuti), non regime-based. Non sappiamo se il canale
   Sentinel → Sherpa → TF **esiste già** o va costruito da zero.
2. **"Greed decay" è tempo o regime?** Determina se la modulazione-per-regime di §2.2 esiste già in altra forma.
3. **Sentinel e NewsKeeper scrivono da qualche parte che Grid/TF leggono, o sono isolati?** Oggi, per quanto
   sappiamo, i cervelli **non si parlano**. Va confermato dove.

Buchi di design (dopo la ricognizione, da fare Max+CEO, NON CC):
- **Tier 3-in-greed vs filtro entry-distance:** in greed le small-cap bullish sono **già scappate** (screenshot:
  HEMI +21,8%, BANK +58,7% sopra EMA20, bloccate dal filtro 12%). Riaccenderle in greed serve, o è teoria?
  Riaccensione ed entry-distance vanno progettate **insieme** o si sabotano.
- **Chi vince Sentinel vs TF in disaccordo** (es. TF vede ETH bullish, F&G a 85 dice risk-off): con la proposta
  Max si scioglie in "**Sherpa arbitra**" (TF propone la lista, Sherpa decide quanto/su quali tier) — ma va confermato dopo la ricognizione.
- **Filtri EMA/RSI di TF mai validati:** selezioniamo bene i coin, o è rumore? (`excess vs hold` per fattore/tier).

---

## 5. Gemme operative da adottare comunque (dal thread)

Indipendenti dall'architettura, da tenere a prescindente:

1. **"Excess vs BTC/hold, non win-rate."** Qualsiasi settimana bull fa sembrare geniale un sistema long-biased.
   Il metro del collaudo dev'essere *quanto batti l'hold*, non "abbiamo guadagnato". Coerente con "il grid è un
   airbag" e con "€100 non è il test".
2. **"Freeze pass/fail PRIMA del test, o negozi coi tuoi risultati."** Da fissare **ora**, prima che i $100
   girino, non dopo.

---

## 6. Sequenza confermata (Board)

1. **Collaudo $100 = solo Grid** (BTC → SOL). TF congelato.
2. **$500 su Grid** a regime.
3. **Solo dopo:** collaudo TF.
4. Scaling ulteriore (fino a 6 cifre) **non deve essere una discriminante di funzionamento** → l'architettura
   va disegnata per reggere a qualsiasi size, non ottimizzata per "pochi spicci".

**TF non bloccante** → ricognizione + design in parallelo, senza fretta.

---

## 7. Prossimi passi

- **[ORA]** Brief di **sola ricognizione** per CC: `2026-07-20_S120_brief_brains_recon.md` (read-only, 3 domande fattuali del §4).
- **[DOPO la ricognizione — Max+CEO]** Design della catena di autorità con lo stato reale in mano.
- **[BRIEF SEPARATO — CC]** `excess vs hold` time-weighted su ETH tf_grid (+ altri coin tf_grid se possibile),
  con criterio pass/fail deciso *prima* di guardare il risultato.
- **[PARCHEGGIATO]** Recuperare soglia + metrica del filtro-universo TF (`> X` mln, cap o volume?).
- **[GO-LIVE RISK]** Slippage da tick sporco (LAST SHOT +15,39%) tra i rischi mainnet.

---

*Report di sessione, non diary. Nessuna decisione operativa eseguita in questa sessione (brainstorming).
Le decisioni di design restano da prendere dopo la ricognizione.*
