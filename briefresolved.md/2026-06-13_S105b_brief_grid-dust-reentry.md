# Brief S105b — grid-dust-reentry — 2026-06-13

**Da:** CEO (Claude) · **A:** CC (intern) · **Board:** Max
**Basato su:** PROJECT_STATE.md (aggiornato 2026-06-12, S103) + memo Board "Perché SOL non compra più" (2026-06-13) + verifica live CEO su Supabase (2026-06-13 ~19:10 UTC)
**Tipo:** fix di **logica bot** (codice griglia) — NON tuning Sherpa/Board-params
**Capitale a rischio:** zero (testnet) — **ma è un gate pre-mainnet esplicito**

---

## 0. Contesto in una frase

La griglia SOL è congelata da ~5 giorni (ultimo BUY 2026-06-09): una polvere di
0,000096 SOL (≈ $0,006) viene contata come "posizione aperta" e disinnesca il
re-entry forzato. Né compra né vende. Il bot non lo sa, Sherpa nemmeno (continua
a regolare `sell_pct` ogni ora su una griglia morta). Zero ERROR, zero alert.

Verifica CEO confermata su DB live:
- SOL `managed_holdings = 0,000096`, ultimo BUY 2026-06-09, 5 buy / 13 sell in 7gg → svuotata.
- BTC e BONK operative (posizioni reali ~$50 e ~$49, comprano ancora).
- `bot_events_log`: solo `SHERPA_ADJUSTMENT` orari su SOL, nessun ERROR. Tuning-noise fantasma dentro la finestra di osservazione Sherpa.

---

## 1. La regola (decisione Board — è QUESTA, non l'opzione C del memo)

> **Se in pancia ho meno del minimo vendibile → non è una posizione, è polvere → tratta come zero → re-entry compra.**
> **Se ho almeno il minimo vendibile → è una posizione vera → posso vendere → comportamento normale.**

La soglia **NON è un epsilon inventato** ($1, 0,0001, ecc.). La soglia è il
**minimo vendibile reale del simbolo su Binance** (`LOT_SIZE` / `minQty`, o
`NOTIONAL` / `minNotional` se più stringente). È un dato oggettivo che Binance
già fornisce: sotto quella soglia la quantità è *letteralmente* invendibile,
quindi per definizione non è una posizione.

Conseguenza progettuale (importante): **risolta la causa, niente toppe.** NON
serve una guardia "Sherpa/Sentinel skippa il simbolo morto", perché nessun
simbolo resta più morto — appena la posizione scende sotto il minimo vendibile,
il re-entry ricompra e la griglia torna viva da sola. Niente warning, niente
skip, niente caso speciale.

---

## 2. DOMANDA TECNICA #1 — da risolvere PRIMA di scrivere codice

**Dove vive il "minimo vendibile" nel codice oggi?**

Il bot piazza ordini su Binance, quindi *deve* già conoscere i filtri `LOT_SIZE`
(`minQty`, `stepSize`) e `NOTIONAL` (`minNotional`) per simbolo — altrimenti
Binance rifiuterebbe gli ordini. Tre possibili stati:

- (a) il valore è già letto e memorizzato per simbolo → **riusalo**, non
  reintrodurre nulla.
- (b) è hardcoded da qualche parte → consolidalo in un'unica fonte e riusala.
- (c) non è recuperato in modo strutturato → recuperalo da Binance
  `GET /api/v3/exchangeInfo` (filtro `LOT_SIZE.minQty` + `NOTIONAL.minNotional`)
  e cachalo per simbolo.

**CC: rispondi a questo nel piano PRIMA di toccare codice.** Da quale di (a)/(b)/(c)
parti determina metà del lavoro. Non assumere — verifica nel repo.

Nota CEO: se esistono sia `minQty` sia `minNotional`, la soglia di "vendibilità"
è quella che rende l'ordine **eseguibile**, cioè in pratica devi soddisfare
entrambi. Per il giudizio "è polvere?" usa il criterio: *questa quantity, a
prezzo corrente, produrrebbe un SELL accettato da Binance?* Se no → polvere.

---

## 3. Cosa cambiare (logica, non valori)

Tre punti di confronto oggi usano il letterale `0` o `> 0` su `managed_holdings`:

1. **Re-entry forzato** — `grid_bot.py:1024` ca. — condizione `managed_holdings <= 0`.
2. **Guardia no-buy-above-avg** — `buy_pipeline.py:54-90` ca. — condizione `holdings > 0`.
3. **Idle-recalibrate (Path B)** — il ramo che "ricalibra il riferimento e aspetta".

**Requisito di coerenza (CRITICO):** la nozione di "posizione vs polvere" deve
essere definita **una volta sola** (un singolo helper / predicato, es.
`is_real_position(symbol, holdings)` o `effective_holdings(...)`) e usata in
TUTTI E TRE i punti. Se un punto considera "vuoto" ciò che un altro considera
"pieno", SOL (o un altro simbolo) finisce in un limbo diverso ma altrettanto
bloccato. Questo è l'errore da non commettere.

Implementazione concettuale (CC decide la forma esatta nel piano):
- introdurre un predicato unico: `holdings` è polvere se un SELL di quella
  quantity a prezzo corrente NON sarebbe eseguibile su Binance (sotto `minQty`
  e/o `minNotional`).
- re-entry: usa `dust → tratta come 0` → ricompra.
- no-buy-above-avg: se `dust` → la posizione non esiste → la guardia non si applica.
- idle-recalibrate: se `dust` → non è una posizione da ricalibrare.

---

## 4. Rianimazione SOL (decisione Board)

Decisione CEO/Board: **rianimiamo SOL, non la lasciamo morta come "dato".**
Razionale: il fallimento è già documentato (questo memo + diary); tenerla
congelata 10 giorni contaminerebbe i dati di Sherpa e il P&L proprio nella
finestra che ci serve pulita per il verdetto barometro (~23 giu) e l'osservazione
Sherpa. Lasciare un confound nell'esperimento ≠ onestà del dato.

**Modalità:** la rianimazione è un'operazione sul bot → **NON la esegue CC, NON
via SQL improvvisato.** CC propone nel piano la sequenza esatta (write-off
una-tantum della polvere SOL → `managed_holdings` effettivo a 0 → al primo tick
il re-entry ricompra) e **Max la esegue manualmente sul Mac Mini**, incluso il
restart. Indicare se la rianimazione è (i) automatica una volta deployato il fix
(il nuovo predicato vede la polvere come zero → re-entry parte da solo, nessun
intervento manuale) oppure (ii) richiede un write-off manuale del residuo storico.
**Preferenza CEO: se (i) basta, niente intervento manuale** — è più pulito.

---

## 5. Decisioni delegate a CC

- Forma esatta dell'helper/predicato e dove collocarlo.
- Come/dove leggere o cachare i filtri Binance per simbolo (in base a §2).
- Refactor minimo per non duplicare la logica nei 3 punti.

## 6. Decisioni che CC DEVE chiedere (escalation a Max via CEO)

- Se per implementare servisse una migration o un cambio di schema (atteso: NO).
- Se i 3 punti di confronto fossero più di 3 (es. altri rami usano `holdings > 0`
  con semantica "posizione") → segnalare PRIMA, non decidere da solo.
- Qualsiasi modifica che tocchi BTC/BONK oltre SOL (il fix è generale per design,
  ma il comportamento su posizioni reali NON deve cambiare).

## 7. Off-limits

- Parametri Sherpa / Board-params (`buy_pct`, `sell_pct`, ecc.) — **non toccare.**
  Questo NON è un fix di tuning. Stringere `buy_pct` sarebbe un cerotto, non la cura.
- Logica Sentinel/Sherpa/NewsKeeper — invariata.
- Nessuna guardia "skippa simbolo morto" — non serve (vedi §1).
- Nessun restart eseguito da CC — i restart li fa Max sul Mac Mini.

## 8. Output atteso a fine task

1. **PRIMA**: piano in italiano leggibile da Max (task >1h stimato), con risposta
   alla DOMANDA #1 (§2) e conferma del punto rianimazione (§4 i vs ii).
   Approvazione Max prima di scrivere codice.
2. Predicato unico "posizione vs polvere" basato sul minimo vendibile Binance.
3. I 3 punti (`re-entry`, `no-buy-above-avg`, `idle-recalibrate`) che usano il
   predicato, coerenti tra loro.
4. Reversibile: nessuna migration; se serve una soglia/flag, in `settings`.
5. Nota nel report: comportamento su BTC/BONK (posizioni reali) verificato
   invariato.
6. Lo SCOPE canonico che CC eredita IDENTICO nel nome del report: **grid-dust-reentry**.

## 9. Auto-obiezione del CEO (anti-assenso)

La mia proposta iniziale (opzione C: epsilon arbitrario + write-off + difesa in
profondità) era **sovra-ingegnerizzata**. La regola del Board — "soglia = minimo
vendibile reale di Binance" — è migliore: elimina la scelta arbitraria della
soglia (era un bug che mi stavo creando da solo) ed elimina la necessità di
guardie anti-morte a valle. Obiezione residua reale: **il rischio si sposta tutto
sulla coerenza dei 3 punti** (§3). Se il predicato non è centralizzato e usato
ovunque allo stesso modo, abbiamo solo spostato il limbo, non chiuso il buco.
Per questo §3 è marcato CRITICO e il piano di CC deve dimostrare la
centralizzazione prima dell'ok finale del CEO.

---

## Appendice — evidenza live (CEO, 2026-06-13 ~19:10 UTC)

- `bot_runtime_state`: SOL `managed_holdings=0,000096`, `stop_buy_active=false`, updated ~ora.
- `trades` (7gg, grid, testnet_2): SOL 5 buy / 13 sell, last_buy 2026-06-09 00:37.
- `bot_events_log` (3gg): solo `SHERPA_ADJUSTMENT` orari su SOL, nessun ERROR.
- Codice citato dal memo: re-entry `grid_bot.py:1024` (`managed_holdings <= 0`,
  niente soglia); guardia no-buy-above-avg `buy_pipeline.py:54`; trigger acquisto
  `grid_bot.py:951`. `managed_holdings` esclude già i phantom (S97a).
