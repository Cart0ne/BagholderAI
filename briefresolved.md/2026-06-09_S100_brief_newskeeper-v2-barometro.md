Brief S100 — newskeeper-v2-barometro — 2026-06-09

# Brief d'implementazione — NewsKeeper v2 "Barometro"

**SCOPE canonico:** `newskeeper-v2-barometro` (eredita identico da concept + critica; il report di CC deve riportarlo invariato).
**Basato su:** PROJECT_STATE.md al 2026-06-08; BUSINESS_STATE §5-§6.
**Catena documentale:** review `2026-06-09_S100_RforCEO_newskeeper-t7-quality-review.md` → concept `2026-06-09_S100_CEOtoCC_newskeeper-v2-barometro-concept.md` → critica `2026-06-09_S100_RforCEO_newskeeper-v2-barometro.md` → **questo brief**.
**Stima:** > 1h → **CC produce PRIMA un piano in italiano per Max, e attende approvazione prima di scrivere codice.**

---

## 0. Cosa stiamo costruendo, in una riga

NewsKeeper diventa un **barometro del clima di mercato** a 3 stati (🐻 Bearish / ⚖️ Neutral / 🐂 Bullish), che gira **in shadow mode accanto a v1**, **non alimenta Sentinel**, e si guadagna il posto **solo se** 2 settimane di dati provano che i suoi flip anticipano il prezzo. È un **esperimento con clausola di morte falsificabile** — e va bene così (fallback: pagina /news).

## 1. Decisioni già prese (Board, NON da rinegoziare)

Queste tre sono approvate dal Board in S100. CC le implementa, non le ridiscute:

1. **Architettura "C" + voto pesato per confidenza + dedup a livello-evento**, come terna unica:
   - **C**: la **polarità** la decide Haiku leggendo il significato. Il preprocessor Python NON ha più potere di veto sulla direzione.
   - **Voto pesato per confidenza**: confidenza Haiku bassa → il voto pesa 0 (astensione), non pieno. È la rete di sicurezza, senza riaccoppiare Python↔Haiku.
   - **Dedup event-level**: stessa storia (cross-feed/cross-day) = **un voto**, non N. È la chiave di volta che rende C sicuro.
2. **Gate falsificabile (punto di principio):** v2 in **shadow** ~2 settimane, validazione contro il **ritorno di prezzo BTC a 24h** — **NON contro il Fear & Greed** (validarsi sul F&G è circolare: il F&G è costruito in parte sulle stesse news). Il barometro **non guida Sentinel** finché lo shadow non mostra che anticipa il prezzo.
3. **Per-item grezzo conservato** in `newskeeper_signals` (serve a /news, digest futuro, audit, e ricalcolo parametri).

## 2. Decisioni delegate a CC (decidi tu, sei il tecnico)

- Struttura dei moduli del nuovo package (`bot/newskeeper_v2/` o nome che preferisci) — multifile, una concern per modulo.
- Schema SQL preciso delle due tabelle, **entro la forma concordata** (sotto §4).
- Tassonomia concreta delle `event_key` di Haiku (es. `BTC|etf_outflow`, `FED|rate_signal`) — proponi il set iniziale.
- Meccanica di query/aggregazione della finestra mobile, implementazione del decadimento e dell'isteresi.
- Layer di dedup: hai proposto L1 `guid`/URL + L2 `event_key`. Confermalo o miglioralo.
- Dove loggare `(stato_barometro, F&G, ritorno_BTC_forward_24h)` per la validazione shadow.

## 3. Decisioni che CC DEVE chiedere (escalation a Board, NON decidere da solo)

- **Qualsiasi cablaggio del barometro dentro lo score di Sentinel** prima del verdetto shadow → VIETATO senza OK Board. In shadow è solo loggato in parallelo.
- Qualunque cosa tocchi i **3 punti del §1** o cambi la metrica di validazione (prezzo BTC 24h).
- Qualunque modifica al **runtime di trading** (grid/tf/sherpa/sentinel) → fuori scope, off-limits.
- Se durante il piano emerge che lo shadow di 2 settimane non basta (vedi auto-obiezione CEO §8) → portalo a Max, non allungare in autonomia.

## 4. Forma delle tabelle (concordata — dettagli a te)

- **`newskeeper_signals`** (esistente): si **arricchisce** dei nuovi campi per-item → `relevance`, `polarity`, `event_key`, più la `confidence` già presente. Il per-item resta grezzo e ricalcolabile (essenziale per tarare i parametri senza ri-chiamare Haiku). La vecchia `severity` per-item **non è più un driver** del barometro; resta come campo grezzo/audit, non la si usa per decidere lo stato.
- **`newskeeper_regime`** (nuova): lo stato del barometro, **write-on-change** (scrivi solo al flip dello stato pubblicato + heartbeat periodico). La lentezza del barometro deve essere visibile nella tabella stessa.
- Preprocessor Python: la direzione calcolata da lexicon **perde il veto**; sopravvive solo come **sensore `direction_conflict`** loggato per audit (rileva se Haiku sviluppa un bias sistematico), senza potere di sovrascrittura.

## 5. Parametri (configurabili, NON hardcoded — si tarano sui dati shadow)

Valori di **partenza** proposti da CC, da NON trattare come definitivi:
- decadimento esponenziale, half-life ~10h;
- banda isteresi simmetrica ±0,15 di voto netto;
- persistenza ≥6h prima di flippare lo stato;
- **asimmetria** (coerente con la filosofia recall-biased): entra in 🐻 più in fretta di quanto ne esca.
Vivono in config, taratura sui dati dello shadow. Nel report, dichiararli come "valori iniziali, da calibrare".

## 6. Output atteso (cosa deve esistere a fine lavoro)

1. Package v2 che gira **accanto** a v1 (v1 NON spento da CC — vedi §7), scrive per-item arricchito + stato `newskeeper_regime`.
2. Le due tabelle (migration via Supabase).
3. Logging della tripla di validazione `(stato, F&G, ritorno_BTC_24h)`.
4. Test sulle funzioni pure (aggregazione, decadimento, isteresi, dedup) — devono essere unit-testabili senza rete/DB.
5. Report `report_for_CEO/` con SCOPE **identico** `newskeeper-v2-barometro`, che includa: schema finale, set `event_key`, parametri iniziali, e come leggere i dati shadow per il verdetto a T+14.
6. Baseline citata dalla review S100 (costo ~€6/mese, staleness 219 titoli, tabella lead/lag) come riferimento di confronto.

## 7. Vincoli e off-limits

- **NON restartare i bot.** Max fa partire/fermare i processi a mano. CC consegna i comandi (`nohup … venv/bin/python3.13 -m …`, `kill -TERM …`), Max li esegue.
- **NON spegnere v1.** v1 continua a girare in parallelo, zero buco di osservazione. v1 si spegne solo dopo il verdetto shadow, e lo decide il Board.
- **NON toccare** `bot/` trading runtime (grid, tf, sherpa, sentinel core). Il barometro è isolato.
- **NON cablare** nulla in Sentinel in questa fase.
- **Push diretto su main**, come da workflow (mai PR). Se qualcosa crasha → git revert + git pull sul Mac Mini.
- `source venv/bin/activate` sempre prima di lanciare.

## 8. Roadmap impact

**Nessun aggiornamento pubblico della roadmap in questa fase.** Il barometro è un esperimento non validato: non lo annunciamo su `roadmap.astro` finché lo shadow non dà un verdetto. Post-T+14: se promosso → phase NewsKeeper aggiornata (Sprint 3 = barometro live); se bocciato → narrativa onesta "esperimento fallito → /news" (candidato blog post, on-brand). Decisione di comunicazione → Board, a verdetto avvenuto.

## 9. Auto-obiezione CEO (anti-assenso, reale)

Il gate shadow di 2 settimane ha una falla che né io né CC abbiamo sollevato: **il mercato attuale è solo-bear.** La nostra stessa regola go-live richiede di osservare bear+bull+laterale prima di fidarsi di un componente. Un barometro che in 2 settimane di solo-discesa sembra "anticipare bene" potrebbe aver solo imparato a dire 🐻 in un mercato che scende e basta — e fallire al primo rimbalzo. Viceversa, un "fallimento" in 2 settimane piatte potrebbe non essere conclusivo. → **Non blocca il brief**, ma il verdetto T+14 va letto con questa lente: "ha anticipato *in che regime?*". Se i 14 giorni restano monodirezionali, il verdetto è **parziale**, non definitivo, e la validazione va estesa fino a vedere almeno un cambio di regime. CC tenga questo esplicito nel report di validazione.

---

**Prossimo passo:** CC produce il **piano in italiano** per approvazione Max (task > 1h), poi implementa.
