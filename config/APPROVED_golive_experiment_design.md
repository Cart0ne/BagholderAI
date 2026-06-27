# GO-LIVE EXPERIMENT DESIGN — APPROVED

**Origine:** sessione estemporanea 2026-06-10 (bozza parcheggiata)
**Approvato:** sessione S110, 2026-06-27 (CEO + Board)
**Stato:** TUTTE LE 9 DOMANDE CHIUSE. Pronto per Board approval finale post-annuncio exchange.
**Sostituisce:** `PARKED_golive_experiment_design.md`

---

## 0. Distinzione madre — i due tipi di ritardo (Max)

- **CASO 1 = veleno.** Tutto ciò che si infila TRA noi e il mainnet con un "prima però". Il CEO lo blocca SEMPRE.
- **CASO 2 = libero.** Side-quest che girano ACCANTO al go-live. Nessun problema.
- **Domanda-filtro:** "è un prerequisito del go-live, o gira in parallelo?"

---

## 1. Capitale — premessa corretta

- €100 NON è il test. È il collaudo della macchina.
- **Capitale operativo target = €600.**
- "Lavora bene" = rispetta le regole, niente slippage/drift/errori di esecuzione. NON significa guadagnare.

---

## 2. FASE COLLAUDO — €100 sequenziali (DECISIONE S110)

Il collaudo NON è il primo gradino di una rampa incrementale. È un test rotativo su tutti e 3 i tier con lo stesso €100.

### Sequenza:
1. **BTC** (Tier 1) — grid puro con €100. Almeno un ciclo buy→sell completo. Validare: fill, fee, slippage, riconciliazione.
2. Quando soddisfatto → vendi tutto, **SOL** (Tier 2) — stesso €100, stessa validazione.
3. Quando soddisfatto → vendi tutto, **BONK** (Tier 3) — stesso €100, stessa validazione.

### Criteri di uscita per coin:
- Grid ha completato almeno un ciclo buy→sell
- Fill reale, fee, slippage coerenti con Supabase (riconciliazione pulita)
- Nessun errore di esecuzione
- Uscita a **giudizio di Max** (target positivo, ma se una coin non rimbalza e Max vuole passare oltre, decide lui)

### Cancello collaudo → deployment:
**A intuito di Max, messo a verbale.** Nessun criterio formale — Max ha visto 3 tier funzionare con soldi veri ed è soddisfatto.

---

## 3. FASE DEPLOYMENT — €600 (DECISIONE S110)

Superato il collaudo, Max versa i restanti €500 e configura l'allocazione definitiva.

### Allocazione:

| Slot | Capitale | Tipo | Gestione |
|---|---|---|---|
| BTC | €250 | Grid fisso | Sempre attivo |
| SOL | €150 | Grid fisso | Sempre attivo |
| TF slot 1 | €100 | tf_grid | TF sceglie e ruota (Tier 1-2) |
| TF slot 2 | €100 | tf_grid | TF sceglie e ruota (Tier 1-2) |
| **Totale** | **€600** | | |

### TF = grid-selector, NON fondo shitcoin
TF seleziona coin Tier 1-2 e le passa a grid. Nessun trading diretto TF. Nessun fondo shitcoin separato.

**Post-mainnet (CASO 2):** clone TF in paper/testnet su Tier 3. Promozione a live solo con track record. Binario indipendente dal go-live.

### Exit thresholds per coin tf_grid (Brief S110d):

| P&L posizione | Segnale trend | Azione |
|---|---|---|
| > +5% | qualsiasi | RUOTA: vendi, TF sceglie la migliore |
| > +0.1% e ≤ +5% | negativo | ESCI: blocca il profitto |
| > +0.1% e ≤ +5% | positivo | TIENI |
| ≤ +0.1% | qualsiasi | TIENI (mai uscire in perdita) |

---

## 4. RESET e PUNTO-ZERO

Dopo il deployment:
- Se in positivo → togli l'eccedenza dal flusso
- Se in negativo → rabbocchi fino a €600 (MA solo per bug, vedi §5)
- **€600 netti = punto-zero.** Il cronometro del verdetto parte da qui.
- Da lì in poi: mani off il trading. "Adesso sono cazzi del CEO."

---

## 5. RABBOCCO — regola pulita (DECISIONE S110)

### Criterio (deciso a freddo):
- **"Comportamento divergente dalla spec scritta" = BUG → rabbocco.**
- **"Regola eseguita correttamente con esito negativo" = PERDITA → resta.**

### Chi giudica: Max.
La telemetria su Supabase (`reason`, `config_version`, `managed_by`, `fill_price` vs `check_price`) rende la classificazione verificabile. Niente "me lo ricordo".

### Tetto all'esborso: nessuno formale.
I bug tendono a zero col procedere → il rabbocco si auto-esaurisce. Max tiene traccia del totale versato.

### Spina:
Max può staccare la spina quando vuole.

---

## 6. NIENTE deadline / NIENTE X-mesi

- Sistema automatizzato + capitale a fondo perduto + attenzione quasi zero = NON è procrastinazione.
- Un deadline taglierebbe fuori il dato che conta: validare l'edge richiede CONDIZIONI (bear + bull + laterale), non calendario.
- Kill-switch CADUTO (importato male da Reddit, non si applica a sistema automatizzato senza emozioni nel loop).

---

## 7. VERDETTO = contenuto, non spegnimento (DECISIONE S110)

### Verdetto negativo:
**-50% dal punto-zero** (da €600 a €300) = trigger per scrivere un capitolo (post-mortem o analisi). NON necessariamente un verdetto di fallimento — se il mercato è sceso del 50% e le regole funzionano, è un unrealized, non un errore. Il verdetto vero viene dal ciclo completo. **Soglia indicativa, rivediamo se ci arriviamo.**

### Verdetto positivo:
Almeno un **ciclo di mercato completo** (bear + bull + laterale) con il sistema in positivo o stabile. Anche tra 3 anni. Nessuna deadline temporale.

### Dopo il verdetto:
I bot possono continuare. Il verdetto produce il CAPITOLO, non la fine della corsa.

---

## 8. VICTORY LAP (DECISIONE S110)

### Percorso progressivo: C → B → A

**Fase C (ora):** niente Victory Lap. Go-live, vedi come va, accumula dati.

**Fase B (quando i dati lo giustificano):** mani off il trading, mani on il racconto. Annuncio: "il trading è autonomo". Max continua a postare, commentare, fare community.

**Fase A (quando i tempi sono maturi):** mani off totale. "Il mio lavoro è finito, seguite il CEO." Prerequisito: pipeline contenuti automatici funzionante. La Victory Lap è la mossa più forte ma anche la più irreversibile — va fatta con dati veri, non con speranza.

---

## 9. SEQUENZA PRE-LIVE (STATO S110)

| Step | Stato |
|---|---|
| NewsKeeper v2 | ✅ PASS |
| Sherpa LIVE testnet | ✅ PASS |
| Osservazione Board-only | ✅ |
| Bug backlog | ✅ azzerato |
| Infra pre-mainnet | ✅ |
| USDT→USDC migration | ⬜ Brief S110c pronto per CC |
| Exchange decision | ⬜ Attesa annuncio Binance MiCA (entro 30 giugno). Kraken = Plan B |
| Board approval finale | ⬜ Dopo exchange + USDC |

---

## 10. CASO 2 — side-quest (binario indipendente)

- **TF clone Tier 3** in paper/testnet — accumula track record post-mainnet
- **Marketplace** — barometro NewsKeeper come candidato più pulito, imbuto non cassa
- **Portfolio Guardian** — tiered drawdown post-mainnet
- **Bottone "esci"** su admin dashboard — nice-to-have, force-liquidate da terminale funziona uguale
- **Book depth telemetria** — micro-brief CC post-collaudo

Nessuno di questi è gate del go-live.

---

## Auto-obiezioni permanenti

1. Il rischio n.1 NON è il mercato, è il LIMBO. Se un punto genera sotto-task a cascata → tagliare.
2. Il CEO difende il progetto perché è il suo. Il test pulito è andare live e guardare i dati.
3. Il CEO tende a importare struttura e dare per acquisite cose da decidere. Max corregge. CEO propone, Max decide.
