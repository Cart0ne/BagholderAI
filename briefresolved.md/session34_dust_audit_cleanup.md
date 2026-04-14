# BRIEF — Audit Dust & Posizioni Stranded v1/v2

**Priorità:** BASSA (paper mode, zero impatto economico)
**Stato:** Da valutare con CEO prima di implementare
**Data audit:** 2026-04-14

---

## Domanda chiave

Ha senso fare pulizia contabile della dust residuale v3 e delle posizioni orfane nelle vecchie config v1/v2, oppure è irrilevante dato che prima o poi azzereremo il DB?

---

## Contesto

Durante l'analisi del display `Holdings: 0.990517 BONK` nel log del runner, è emerso che:

1. Il display del P&L realizzato è cosmeticamente sbagliato (bug minore in `init_percentage_state_from_db` — non restaura `realized_pnl` e `total_fees` dal DB al restart). **Da fixare a parte.**
2. La dust BONK di 0,99 unità è reale e corrisponde ad un residuo contabile tra `Σbuy` e `Σsell` v3.

Da lì abbiamo allargato l'indagine a tutte le coin e a tutte le config_version.

---

## Findings

### 1. La dust v3 è un'eredità congelata, non un processo attivo

La transizione da trade con amount frazionari a trade step-aligned è avvenuta **tra il 12 e il 13 aprile 2026** per tutte e tre le coin (attivazione di `round_to_step` sul buy, brief [session32e](session32e_dust_fix_round_buy.md)). Da quel momento in poi:

- Tutti i trade v3 hanno amount multipli esatti dello step_size dell'exchange
- Nuova dust frazionaria **non si genera più** in paper
- In live mode non si genererebbe in principio (Binance fa fill step-aligned)

I residui v3 attuali sono quindi tutti accumulati **prima** del 13 aprile.

### 2. Dust v3 residua (paper, congelata)

| Coin | step_size | Residuo | Valore USD |
|---|---|---|---|
| BONK/USDT | 1 | 0,99051683 BONK | ~$0,000006 |
| BTC/USDT  | 0,00001 | 0,00002706 BTC | ~$1,89 |
| SOL/USDT  | 0,001 | 0,00056888 SOL | ~$0,10 |

**Totale dust v3:** ~$2 paper. Tutti sub-`min_notional` → invendibili sull'exchange reale.

### 3. Posizioni stranded v1/v2 (paper, orfane)

Queste **non sono dust** — sono vere posizioni aperte nelle config superseded che non sono mai state chiuse al momento della migrazione:

| Coin | v1 residuo | v2 residuo | Totale USD (paper) |
|---|---|---|---|
| BONK | 4.302.683 BONK | 1.451.309 BONK | ~$34,76 |
| BTC  | 0,00525137 BTC | 0,00037889 BTC | **~$394,12** |
| SOL  | 0,82114097 SOL | 0,06116534 SOL | **~$158,82** |

**Totale stranded v1/v2:** ~$588 paper. BTC v1 e SOL v1 da soli valgono oltre $500.

In paper: zero impatto (sono numeri fittizi nel DB).
In live: **sarebbero coin reali** ferme sul wallet Binance senza nessuna config che le gestisca.

---

## Opzioni

### A) Zero intervento

Aspettiamo il reset completo del DB che è comunque previsto. Non tocchiamo niente.

- ✅ Zero sforzo, zero rischio
- ✅ Paper, quindi nessun valore reale in gioco
- ❌ La dashboard continua a mostrare numeri confusi finché non pulizia
- ❌ Se prima del reset si decide di provare il passaggio live, le posizioni v1/v2 diventano un problema concreto

### B) Pulizia chirurgica via pseudo-trade

Una sola migration SQL che inserisce `dust_writeoff` (o `position_retire`) come trade artificiali per azzerare in un colpo:

- i residui v3 (dust vera)
- le posizioni v1/v2 (stranded)

Formato: `side='sell'`, `amount=residuo`, `price=0`, `realized_pnl=0`, `brain='cleanup'`, `reason='paper write-off — pre-live cleanup'`.

- ✅ Contabilità pulita: `netHoldings = 0` per tutte le coin in tutte le versioni
- ✅ Dashboard torna leggibile
- ✅ Pronti per live senza "sorprese" da vecchie config
- ✅ Reversibile (basta eliminare i trade di cleanup)
- ❌ Crea una pseudo-realtà storica che non è davvero avvenuta
- ❌ Realized P&L cumulativo non cambia (le pseudo-sell sono a price=0) ma il `total_received` e `total_invested` storici restano "sbilanciati" visualmente

### C) Reset completo del DB

Cancellare `trades`, `portfolio_snapshots`, `reserve_ledger`, `config_changes_log`, ecc.
Ripartire da zero con config v3 pulita.

- ✅ Tabula rasa, nessuna ambiguità
- ✅ Coerente con il piano "prima o poi azzeriamo" già sul tavolo
- ❌ Si perde la storia di 3 settimane di paper trading
- ❌ Si perde la possibilità di fare retrospective sui trade passati
- ❌ Richiede coordinamento (bot fermi, backup, re-init)

### D) Opzione ibrida

Snapshot della `trades` attuale in `trades_archive` (o dump JSON), poi reset selettivo solo di v1/v2 (o solo dei trade pre-2026-04-13).

- ✅ Mantieni la storia recente (post-fix step_size) che è "sana"
- ✅ Elimini il rumore storico
- ❌ Leggermente più lavoro di B o C
- ❌ Alcune metriche portfolio potrebbero rompersi se referenziano trade archiviati

---

## Raccomandazione tecnica

Dato che:
- siamo in paper
- la dust v3 nuova non si genera più grazie al fix del 13 aprile
- il reset DB è comunque previsto
- le v1/v2 erano già candidate alla cancellazione

La strada più pulita è **C (reset completo)** quando si fa il passaggio a live, eventualmente preceduta da un **D-light** (dump JSON di backup) per salvare la storia come riferimento.

Se invece il reset è lontano nel tempo e nel frattempo vogliamo dashboard leggibili, **B (pulizia chirurgica)** risolve senza toccare lo storico dei trade "buoni".

**A (zero intervento)** è accettabile solo se il reset è imminente (settimane, non mesi) e nel frattempo siamo d'accordo a convivere con dashboard un po' sporche.

---

## Decisione richiesta

1. **Quando si fa il reset del DB?** (orizzonte temporale approssimativo)
2. **Se il reset è lontano:** facciamo la pulizia chirurgica B intanto, o lasciamo stare?
3. **Se il reset è vicino:** serve un backup/dump prima del drop delle tabelle?

---

## Side task già pianificato

Indipendentemente dalla decisione sopra, aggiungiamo alla dashboard admin un **contatore dust v3** sempre visibile — serve a monitorare che il sistema post-fix step_size continui a non accumulare nuova dust. Se il contatore torna a crescere, sappiamo che c'è una regressione.
