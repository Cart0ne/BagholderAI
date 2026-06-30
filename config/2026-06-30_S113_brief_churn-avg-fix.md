Brief S113 — churn-avg-fix — 2026-06-30

**Fonte:** report RforCEO `2026-06-30_S113_RforCEO_grid-regime-backtest.md` (CC) + verifica diretta CEO su Supabase `trades` (30/06, vedi §1). Allinearsi a PROJECT_STATE.md corrente per i path; questo brief NON ipotizza numeri di riga (vedi Passo 0).
**Decisione del Board:** Piano A approvato (Max, 30/06). Piano B (dust write-off) scartato consapevolmente — razionale in §7.
**Classificazione:** fix di trading-logic LIVE. Task > 1h → piano italiano obbligatorio PRIMA di qualunque commit (vedi §4).
**Gate:** questo fix è prerequisito per accendere i €100 reali su Kraken. NON blocca la cutover del codice/adapter; blocca il primo euro vero.

---

## 1. Il problema (verificato sui trade VERI, non sul simulatore)

Verifica CEO sulla tabella `trades` (BTC/USDT, strategy A, mode live), 30/06:

- Trade reale citato da CC, confermato identico: `2026-06-22 15:27 UTC` — buy 65017.60 → sell 65081.19, **gap 1.0 min**, prezzo mosso **+0.098%**, realized **+$0.545**, fee $0.0495.
- **Firma del bug (prova indipendente dalla teoria):** una serie di sell scatta dopo movimenti di prezzo di **~0.1%** mentre il trigger di sell nominale è **1.0%**. È impossibile senza un avg di riferimento più basso del buy reale. Inoltre il realized resta **piatto a ~$0.55** mentre il prezzo balla tra 0.098% e 0.138%: un profitto reale seguirebbe il prezzo, questo no → è contabile (avg diluito), non economico.
- **Due popolazioni distinte** nello stesso dataset: cicli "churn" (gap < 60 min, move < 0.5%, realized piatto ~$0.55) vs cicli grid veri (gap ore/giorni, move 1–3%, realized variabile, incluso un −$1.31).
- **Quantificazione:** 15 cicli churn, lotto medio ~$50. Fee round-trip Binance ~$0.10 (mascherato dal realized fantasma) vs **Kraken taker ~$0.40**. Guadagno reale catturato ~$0.05/ciclo → su Kraken **~−$0.35 netti per ciclo** → ~−$5 su $250 in ~8 giorni (14–22 giugno), peggio nei trend (re-entry idle ogni 4h).
- **Implicazione (non parte di questo brief, ma da tenere a mente):** ~58% del realized BTC analizzato ($8.27 / $14.28) è churn fantasma. Tema reporting pubblico, gestito separatamente.

Meccanica (per il piano): il bot svende fino alla polvere, azzera l'avg ma **tiene** le monetine (finding S111, `realized_pnl_avg_cost_fixB`). Al re-entry la polvere a basso costo **diluisce l'avg operativo** → il trigger di sell risulta già superato → vende ~1 min dopo aver comprato, pagando solo fee.

---

## 2. Approccio scelto (Piano A)

**L'avg OPERATIVO non si azzera sulla polvere: la trattiene al costo vero** → niente diluizione → niente trigger di sell spurio.

Differenza chiave dal Fix B parcheggiato: il Fix B sistemava solo il *numero* realized (reporting). Piano A sistema l'**avg che guida le decisioni di trading**. La guard Strategy A esente-polvere (S105b) **resta**: il fix non deve reintrodurre un dust-trap.

---

## 3. PASSO 0 — mappatura (OBBLIGATORIO, prima di tutto)

Non si tocca nulla finché non esiste questa mappa. Produci (in italiano, dentro il piano §4):

1. **Dove** e **come** l'avg si azzera sulla polvere nel loop reale (`grid_runner` / `grid_bot`): file + righe esatte.
2. **Chi legge l'avg** per prendere decisioni: trigger di sell, buy guard, ladder, e **skim 30%** (lo skim dipende dal realized → dipende dall'avg). File + righe.
3. **Dove vive** la guard Strategy A esente-polvere (S105b) e come interagisce col reset dell'avg.
4. Distinzione attuale (se esiste) tra "avg operativo" e "avg reporting", o se sono lo stesso campo.

---

## 4. Piano italiano prima del codice (regola task > 1h, logica viva)

Dopo il Passo 0, produci un piano in italiano leggibile da Max, da approvare PRIMA di scrivere codice. Deve contenere:

- I file/righe che intendi toccare e l'effetto su: trigger sell, buy guard, ladder, skim.
- Come separi/correggi l'avg operativo senza rompere la guard S105b.
- **≥ 1 obiezione tecnica reale** alla tua stessa implementazione (regola anti-assenso). In particolare rispondi a queste due, che sono le mie preoccupazioni:
  - L'avg-al-costo-vero introduce un nuovo dust-trap? La guard S105b lo previene? Dimostralo.
  - Lo skim 30%, leggendo ora un avg corretto invece del fantasma, cambia l'ammontare skimmato in modo non voluto?

---

## 5. Decisioni delegate / da chiedere

**Delegate a CC** (puoi decidere tu, nel piano):
- Strutture dati / implementazione tecnica del fix una volta approvato il piano.
- Come rappresentare l'avg operativo al costo vero (polvere inclusa al costo reale, non azzerata).

**CC DEVE chiedere a Max** (escalation):
- Qualunque modifica al comportamento di trading oltre l'eliminazione del churn (trigger, lot size, dead-zone, idle re-entry, skim%).
- Qualunque tocco a `bot_config`, DB, o file di config.
- Il momento del restart del bot. **CC non riavvia mai. Restart = Max, manuale, Mac Mini.**

---

## 6. Output atteso & validazione (il gate)

**Sessione piano:** Passo 0 + piano italiano approvato.
**Sessione implementazione (dopo OK Max):**
1. Codice del fix, push diretto su main (prassi), MA solo dopo OK Max sul piano.
2. Il counterfactual "riparato" del backtest deve ora girare sul **codice vero** (non più flag nel simulatore) e riprodurre la sparizione del churn.
3. **Replay sui trade veri BTC 14–22 giugno:** zero cicli churn (nessun buy→sell < 60 min con move < 0.5% e realized piatto ~$0.55).
4. **Invariante (critico):** sui cicli grid veri (move ≥ 1%) realized e numero trade restano **identici** a pre-fix. Il fix tocca solo il churn, non la strategia.
5. **Skim:** verifica che lo skim 30% legga l'avg corretto.

---

## 7. Vincoli / off-limits

- **NON toccare:** `bot_config`, DB, file di config (read/propose only).
- **NON cambiare:** trigger sell, lot size, dead-zone, idle re-entry, skim% — solo la meccanica dell'avg.
- **NON rompere** la guard Strategy A esente-polvere (S105b).
- Push su main come da prassi, ma piano italiano approvato da Max **prima** di qualunque commit (eccezione alla velocità abituale, giustificata dalla natura live).

---

## 8. Anti-assenso (CEO)

**Auto-obiezione mia:** Piano A è più invasivo di B — tocco la logica che guida le decisioni, non solo il numero, con rischio di regressione su buy guard/ladder/skim. Perché vale la spesa di rischio invece del B più sicuro? Perché B butta ~$2/mese di polvere E lascia l'avg di reporting fantasma → i numeri pubblici resterebbero gonfiati (e la trasparenza è il brand). A corregge decisioni + reporting in un colpo. Trade-off accettato dal Board consapevolmente.

**Decision log (da incollare in BUSINESS_STATE.md §4):**
`2026-06-30 — Board sceglie Piano A (avg operativo non azzerato sulla polvere) vs Piano B (dust write-off) per il fix churn — why: A elimina la causa radice e corregge sia decisioni sia reporting; B più sicuro ma butta polvere e lascia i numeri pubblici gonfiati. Fix promosso a gate pre-go-live-€100-Kraken, non blocca la cutover del codice.`
