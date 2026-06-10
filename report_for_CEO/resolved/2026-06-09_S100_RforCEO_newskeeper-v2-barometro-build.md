# Report per CEO — NewsKeeper v2 "Barometro" (BUILD) — 2026-06-09 — S100

**SCOPE canonico (ereditato identico):** `newskeeper-v2-barometro`
**Brief sorgente:** `config/2026-06-09_S100_brief_newskeeper-v2-barometro.md`
**Catena documentale:** review `2026-06-09_S100_RforCEO_newskeeper-t7-quality-review.md` → concept `…_CEOtoCC_newskeeper-v2-barometro-concept.md` → critica `config/…_RforCEO_newskeeper-v2-barometro.md` → brief → **questo report di build**.
**Nota naming:** `report_for_CEO/2026-06-09_S100_RforCEO_newskeeper-v2-barometro.md` contiene la *critica* al concept (file spostato qui da `config/`; il riferimento `config/…` nel brief §7 è ora stale, anti-drift §0). Per non sovrascriverla, questo report di build usa il suffisso `-build`.
**Esito:** ✅ CODICE SCRITTO + migration applicata + **test 185/185** + review avversariale multi-agente passata (1 finding trovato e fixato). **NON ancora lanciato in shadow** (lo fa Max) e **NON committato/pushato** (attendo OK).

---

## 0. In una riga

Il barometro è costruito come da sintesi S100: **architettura C** (Haiku decide la polarità, il lexicon non ha veto) **+ voto pesato per confidenza** (sotto soglia astiene) **+ dedup a livello-evento** (una storia = un voto). Gira **in shadow accanto a v1**, **non tocca Sentinel**, e logga tutto per il verdetto falsificabile a T+14 (validazione **sul prezzo a 24h**, non sul F&G). Una review avversariale ha trovato 1 bug reale nella dedup (sceglieva un rappresentante stale/fuori-finestra) — fixato e coperto da 2 test di regressione.

## 1. Cosa è stato costruito

Nuovo package `bot/newskeeper_v2/` (isolato da v1 e dal runtime di trading):
- **`aggregator.py`** — funzioni pure (no rete/DB): dedup per `event_key` → `raw_score` (decadimento + confidenza, normalizzato in [-1,+1]) → macchina a stati con isteresi. È il cuore unit-testato.
- **`classifier.py`** — **una** chiamata Haiku/articolo → `{relevance, polarity, event_key, confidence}`. Architettura C: la polarità è di Haiku; il lexicon Python sopravvive solo come sensore `direction_conflict` loggato. Fallback = **astensione** (polarità 0), mai una tirata a indovinare col regex.
- **`store.py`** — unico modulo che tocca Supabase: scrive il per-item arricchito, legge i voti 24h, scrive lo stato regime (write-on-change + heartbeat), snapshotta BTC/F&G al flip. Never-raise.
- **`main.py`** — loop 15 min in shadow. **Legge** `sentinel_scores` (solo per lo snapshot prezzo), non scrive mai a Sentinel, non spegne v1.
- **`tests/test_newskeeper_v2.py`** — 25 test sulle funzioni pure (incluso il test di regressione del bug S100: polarità di Haiku preservata contro il lexicon).

## 2. Schema finale (migration applicata al DB condiviso)

- **`newskeeper_signals`** arricchita (colonne nullable → righe v1 restano NULL, v1 intatto): `relevance` (text), `polarity` (smallint, CHECK -1/0/1 o NULL), `event_key` (text), `confidence` (real). Indice parziale su `event_key IS NOT NULL`. La vecchia `severity` (NOT NULL + CHECK) viene mappata da relevance (high/medium/discard → high/medium/low) solo per soddisfare il vincolo: **non è più un driver**. **I voti v2 = righe con `event_key IS NOT NULL`** (discriminatore pulito da v1).
- **`newskeeper_regime`** (nuova): `state` (CHECK bearish/neutral/bullish), `prev_state`, `net_score`, `abstain_frac`, `vote_count`, `btc_price_at_flip`, `fg_at_flip`, `raw_data{kind:flip|heartbeat}`. Write-on-change + heartbeat ≥6h. RLS on, nessuna policy pubblica (service-role only) → privato durante lo shadow.

## 3. Set `event_key` iniziale + parametri (da calibrare sui dati, NON definitivi)

- **Entità:** `BTC ETH SOL BONK MACRO FED REG EXCH MISC`. **Tipi:** `etf_flow price_move rate_signal inflation_print exploit_hack regulation adoption liquidation geopolitics misc`. Off-vocab → `MISC|misc`.
- **Parametri (congelati durante lo shadow** — anti-assenso B: non tarare su mercato monodirezionale): half-life decadimento **10h**; soglie isteresi **bull_enter +0.15 / bull_exit +0.05 / bear_enter −0.12 / bear_exit −0.04** (asimmetria recall-biased: si entra in 🐻 più facilmente e se ne esce più a fatica); persistenza **6h** (bull/neutral) / **4h** (bear). Tutti in `BarometerParams`, override-abili.

## 4. Come si legge il verdetto a T+14 (il gate falsificabile)

Metrica primaria = **anticipo sul prezzo, non sul F&G** (validarsi sul F&G è circolare). A T+14, per ogni riga di flip in `newskeeper_regime`:
1. ritorno forward = `(sentinel_scores.btc_price a created_at+24h − btc_price_at_flip) / btc_price_at_flip`.
2. **Il barometro si promuove** se i flip 🐻 precedono ritorni negativi e i flip 🐂 ritorni positivi, con anticipo utile **rispetto al prezzo** (e, secondariamente, se anticipa i cambi di F&G).
3. **Salute (anti-assenso A):** monitorare `abstain_frac` nelle righe regime. Se è alto e lo stato resta sempre ⚖️, il barometro **non è lento, è muto** → alzare le soglie di confidenza o rivedere il prompt.
4. **Lente di regime (auto-obiezione CEO §9 + anti-assenso B):** se i 14 giorni restano monodirezionali (solo-bear), il verdetto è **parziale** — estendere fino a vedere almeno un cambio di regime prima di fidarsi.

**Nessun cablaggio in Sentinel** prima di un verdetto positivo: è la sola condizione di principio del brief.

## 5. Qualità: review avversariale (processo §7)

Build sottoposto a review multi-agente su 5 dimensioni (matematica aggregatore, integrità architettura-C, correttezza SQL, isolamento shadow, aderenza alla sintesi), ogni finding verificato per refutazione. **1 finding confermato (medium), fixato:**
- `dedup_by_event_key` sceglieva il rappresentante di un evento per `(relevance, directional, confidence, recency)` con la recency ultima → una riga stale o appena-fuori-finestra poteva vincere e (a) far contare **zero** un evento con lettura fresca valida, o (b) sotto-pesare ~5× un catalizzatore fresco, **annullando il decadimento**. **Fix:** dedup ora window/decay-aware — rappresentante scelto per `(in_window, directional, peso_effettivo=relevance×confidence×decay)`. + 2 test di regressione (Modo 1 e Modo 2).
- 0 altri finding (matematica, architettura-C, SQL/constraint, isolamento shadow, aderenza: tutti puliti).

## 6. Baseline di confronto (dal report review S100)

Costo Haiku **~€6/mese** (stesso volume di chiamate di v1, +un campo in output → costo invariato); staleness misurata **219 titoli ripetuti su ≥2 giorni** (è ciò che la dedup event-level chiude); tabella lead/lag per-item (v1 coincidente-a-laggante) come termine di paragone per il verdetto del barometro.

## 7. Comandi per Max (NON eseguiti da me)

Migration: **già applicata** al DB condiviso (vale per entrambe le macchine). Restano due passi manuali, **dopo** che il codice è su `main` + pull sul Mac Mini:
- **Avvio shadow (v1 resta vivo):**
  ```
  cd /Volumes/Archivio/bagholderai && git pull --ff-only origin main
  source venv/bin/activate
  nohup caffeinate -i -s -- venv/bin/python3.13 -m bot.newskeeper_v2.main >> logs/newskeeper_v2.out 2>&1 < /dev/null & disown
  ```
- **Verifica T+1:** `newskeeper_signals` ha righe con `event_key IS NOT NULL` e `classifier_version='barometro_v1'` (0 `barometro_fallback`); `newskeeper_regime` ha almeno un heartbeat.
- **Spegnimento v2** (se serve): `kill -TERM <pid>`. v1 si spegne **solo** dopo verdetto, e lo decide il Board.

## 8. Cosa NON è stato fatto (e perché)

- **Non lanciato in shadow:** lo fa Max (brief §7, no restart da CC).
- **Non committato/pushato:** attendo OK (consegno il commit pronto).
- **Nessun cablaggio in Sentinel, nessun aggiornamento roadmap pubblico:** il barometro è un esperimento non validato (brief §3, §8).
- **F&G al flip = best-effort** (fonte alternative.me, never-raise): è conferma secondaria, non la metrica di validazione.
- **Parametri non tarati:** congelati ai valori iniziali fino a un cambio di regime (anti-assenso B).
- **Naming:** la critica al concept vive in `report_for_CEO/…_RforCEO_newskeeper-v2-barometro.md` (spostata da `config/`; il riferimento `config/…` nel brief §7 è ora stale). Questo build report coesiste col suffisso `-build`. Se preferisci, posso togliere `-build` (i due artefatti restano distinti: critica pre-brief vs report di build).

---

## Decisioni (per PROJECT_STATE §4)

- **DECISIONE:** dedup event-level **window/decay-aware** (non solo per relevance/confidenza). **RAZIONALE:** la review ha provato che ignorare finestra+decadimento nella scelta del rappresentante perde eventi freschi e annulla il half-life. **ALTERNATIVE:** rank originale (buggy); drop hard fuori-finestra prima del rank (equivalente, scelto come `in_window` top-key). **FALLBACK:** reversibile (la firma `_dedup_rank` è isolata).
- **DECISIONE:** v2 scrive nella *stessa* `newskeeper_signals` di v1, discriminata da `event_key IS NOT NULL`. **RAZIONALE:** brief §4 (per-item grezzo unico per audit/digest/retuning). **FALLBACK:** tabella separata se emerge contaminazione (nessuna riscontrata: v1 non setta event_key, la sua dedup filtra per source+signal_type).
