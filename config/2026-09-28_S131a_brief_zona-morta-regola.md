Brief S131a — zona-morta-regola — 2026-09-28

**Da:** CEO · **Per:** CC · **Board:** Max (approvato in S131, 28-set)
**Basato su:** `config/MASTER_TASK_LIST_2026-09-28.md` (S130) · `report_for_CEO/2026-09-28_S130_RforCEO_analisi-strategia-A1.md` · PROJECT_STATE §5 (voce "zona morta inerte a bot acceso", S129). **CC verifica all'avvio che PROJECT_STATE riporti S130 prima di partire.**
**Report atteso:** `report_for_CEO/YYYY-MM-DD_SXXX_RforCEO_zona-morta-regola.md` — lo SCOPE nel nome del report deve essere identico a quello di questo brief: `zona-morta-regola`.

---

## 0. Decisioni del Board (S131) che questo brief esegue

| # | Decisione | Effetto qui |
|---|---|---|
| D2 | Sostituire il bug della zona morta con una regola esplicita: **scala azzerata solo in paura e paura estrema; in neutrale, avidità e avidità estrema il reset è spento per scelta**. Nessuna dipendenza dai riavvii. Il reset, quando scatta, **non sposta il riferimento acquisti** (regola D2 di A.1) | Parte A |
| D3 | Riga in BUSINESS_STATE §4 (la scrive il CEO; CC committa) | fuori dal brief |
| D5 | A.2 (rientro dopo vendita totale) **dopo X.1**, non ora | non in scope |
| Q1–Q5 | Verifiche sul materiale A.1, solo analisi | Parte B |

**Non in scope, non toccare:** X.1, Sentinel/NewsKeeper, TF, `sell_pct`/`buy_pct`, la logica della scala (`_last_sell_price`), l'idle re-entry, il blocco perdita, K1/K2.

---

## Parte A — La regola esplicita (codice, denaro reale)

### A.1 Cosa succede oggi (da confermare da CC, non da assumere)

- `grid_bot.py` (blocco DEAD ZONE RECALIBRATE): se `elapsed = now − _last_trade_time ≥ dead_zone_hours`, con `_last_sell_price > 0` e prezzo > media → `_last_sell_price = 0`, **`_pct_last_buy_price = current_price`**, `_last_trade_time = now`.
- `grid_bot.py:1140` (idle re-entry): il ricalcolo idle azzera lo stesso `_last_trade_time`. Quando `idle_reentry_hours < dead_zone_hours` la zona morta non scatta mai a bot acceso.
- Tabella Sherpa (`bot/sherpa/board_parameter_rules.py:60-66`): `dead_zone_hours` 1h paura · 2h paura estrema / neutrale / avidità · 3h avidità estrema. `idle_reentry_hours`: 0,75h in neutrale/avidità, 2h in paura (dal report A.1). **CC riporta nel piano i valori esatti per tutti e 5 i regimi**, sia idle sia zona morta.
- Al riavvio `_last_trade_time` viene ripristinato dal DB all'ultimo trade vero → la zona morta scatta al primo tick. È così che BTC ha venduto il 26 e 27-set.

### A.2 La regola da implementare

1. **Zona morta spenta in neutrale, avidità, avidità estrema.** Preferenza CEO: via tabella Sherpa, `dead_zone_hours = 0` con semantica esplicita "0 = disattivata", e guardia nel blocco DEAD ZONE (`if DEAD_ZONE_HOURS <= 0: skip`). Oggi `0` verrebbe letto come "scatta subito": la guardia è obbligatoria. Con la tabella a 0 in quei regimi, anche il riavvio non fa più scattare nulla.
2. **In paura e paura estrema la zona morta resta come oggi** (1h / 2h). Non si toccano i valori.
3. **D2:** quando la zona morta scatta, azzera la scala ma **non riassegna `_pct_last_buy_price`**. Il riferimento acquisti resta dov'era. CC verifica nel piano se l'idle re-entry applica già il cap S70 ("mai riferimento sopra la media") e, se sì, se la scelta giusta sia "non toccare" oppure "stesso cap dell'idle". Il CEO preferisce "non toccare" (è la variante D2 testata in A.1); se CC vede un motivo tecnico per il cap, lo argomenta nel piano.
4. **Guardia anti-ricaduta:** al caricamento config, se per un regime `0 < dead_zone_hours ≤ idle_reentry_hours` → warning esplicito in `bot_events_log` ("dead zone inert: idle ≤ dead zone"). Oggi la zona morta in paura funziona solo perché 1h < 2h; se un domani Sherpa cambiasse i valori, si romperebbe in silenzio.

### A.3 Gate prima di scrivere codice: la verifica Q1

**Domanda:** nello storico di A.1 (§5, 11 finestre, nessun fermo e nessun riavvio) la BASE coincide già con la regola A.2? Il ragionamento del CEO: senza riavvii, in neutrale/avidità la zona morta non scattava mai → la BASE storica è "zona morta spenta in neutrale/avidità, attiva in paura", cioè esattamente la regola. Se è così, la regola è già stata testata e ha battuto ogni variante in 6 finestre su 11.

- **Se Q1 conferma:** si procede con il piano.
- **Se Q1 non conferma** (per esempio la BASE storica scattava per altre vie): CC fa girare la regola A.2 come variante esplicita con gli script A.1 (`a1_robust.py` 20 disturbi sui 2 mesi reali + `a1_history.py` sulle 11 finestre), confronto appaiato contro BASE. Criterio per procedere: **non peggio di BASE** (nessuna finestra in cui perde nel ≥90% dei disturbi). Se perde in modo netto da qualche parte → STOP, si torna dal CEO.

Nei 2 mesi reali la regola differisce dalla BASE solo per le vendite da riavvio (26 e 27-set su BTC). È atteso che alla data di oggi renda qualche dollaro in meno: sono vendite casuali, e il Board ha scelto di rinunciarci.

### A.4 Protocollo

- **Piano prima del codice** (CLAUDE.md [3]): cosa cambia (file:linea), cosa non cambia, rischi, esito di Q1. Max approva. Il cambio è piccolo in righe ma tocca denaro reale: il piano non si salta.
- **Test:** unit test sui 5 regimi (scatta / non scatta), test del riavvio (in avidità con `_last_trade_time` vecchio → non scatta), test D2 (dopo il reset `_pct_last_buy_price` invariato), test guardia.
- **Deploy:** richiede riavvio dei bot. **CC elenca nel piano tutto ciò che va live con quel riavvio** (es. T.2/T.3 codificati in S120 e "pending restart"). Momento del riavvio: lo decide Max.
- **PROJECT_STATE §5:** la voce "zona morta inerte" passa a chiusa con rimando a questo brief; se resta la coppia di sveglie su un solo orologio, lo si dichiara come vincolo noto (non bug).

### A.5 Decisioni delegate a CC / da chiedere

**Delegate:** rappresentazione di "disattivata" (0 vs None) purché esplicita; struttura dei test; dove mettere la guardia di caricamento; formato del report.

**Da chiedere (STOP e flag):** qualunque tocco fuori dai due punti (tabella + blocco DEAD ZONE + D2); l'esito di Q1 se non è un sì pulito; se il cap S70 sull'idle re-entry cambia il senso di D2; il momento del riavvio.

---

## Parte B — Verifiche sul materiale A.1 (solo analisi, nessun bot toccato)

Output: **addendum al report A.1** (`report_for_CEO/YYYY-MM-DD_SXXX_RforCEO_a1-addendum.md`), stesse convenzioni del report. Stessi script, stessi 20 disturbi, stesse due fonti prezzo.

| # | Verifica | Perché |
|---|---|---|
| Q2 | **Commissioni totali pagate** dal 22-lug a oggi, dal registro Kraken (non dal DB): lordo, commissioni, netto, per moneta. Al 26-set il piano dava $6,99 + $6,42. Va in testa all'addendum | La SEQUENZA §6 dice che l'esperimento si regge su questo numero, e il report non lo scrive |
| Q3 | **Variante F'**: commissione 0,25% con **soglie di vendita congelate** ai valori calcolati a 0,80%. Confronto appaiato contro BASE, 2 mesi reali + 11 finestre | F confondeva due cambi (fee bassa E soglie più basse). F' isola il puro effetto commissioni: è il numero pulito per X.2 |
| Q4 | **Scomposizione del divario dal compra e tieni** per moneta: quota spiegata dall'esposizione media (quanto avrebbe reso un'esposizione costante pari alla media), quota tempismo, quota commissioni. Stima CEO da verificare: SOL ≈ −67 / −9 su −76; BTC ≈ −19 / −18 su −36 | È il fatto principale che manca in "In breve": il divario è esposizione, non taratura |
| Q5 | **SOL, rientro dopo vendita totale:** quante volte è rientrato con un solo lotto; quanto ha aspettato il secondo lotto (ore); quante volte il secondo non è mai arrivato prima della vendita successiva; passo d'acquisto in vigore in quei momenti (Sherpa) | Dato di partenza per A.2. Solo conteggio, nessuna variante |
| Q5b | Perché il criterio "giorno per giorno" copre solo gli ultimi 30 giorni e non tutta la finestra? Se non c'è un motivo, rifare su tutta la finestra per D e F' | Minore |

Nessuna nuova variante oltre F'. Niente caccia a combinazioni (lezione S115).

---

## Output atteso a fine sessione CC

1. Piano Parte A approvato da Max → codice + test + PROJECT_STATE §5 aggiornato → commit; riavvio quando Max decide.
2. Addendum Parte B.
3. Report `..._RforCEO_zona-morta-regola.md` con blocco Decisions (formato A.1).

Stima: Parte A ~1,5h (piano incluso), Parte B ~1h con gli script esistenti.

---

## Auto-obiezioni del CEO a questo brief

1. **Stiamo promuovendo a regola un comportamento nato da un bug, su 29 vendite reali.** Accettato perché nello storico (11 finestre, Sherpa ricostruito) la BASE-senza-riavvii batte tutte le varianti, e perché la regola rende il bot deterministico, che vale di per sé. La riga in BUSINESS_STATE §4 dichiara la fragilità.
2. **A 0,25% di commissione il calcolo può invertirsi** (le piccole vendite tornano convenienti: F vince proprio nel laterale). Per questo Q3 e per questo la regola va riverificata dopo X.1. Non è una regola per sempre.
3. **Spegnere la zona morta in avidità toglie le vendite da riavvio**, che il 26-27 set su BTC erano state buone (+7,7%). Accettato: erano casuali, e "il bot vende quando il Mini si riavvia" non è una strategia.
