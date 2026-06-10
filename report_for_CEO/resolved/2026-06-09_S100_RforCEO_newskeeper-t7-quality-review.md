# Report per CEO — S100 — NewsKeeper T+7 Quality Review — 2026-06-09

**Attività sorgente:** quality review promessa nel report S94a §6 (`report_for_CEO/resolved/2026-06-01_S94a_RforCEO_newskeeper-haiku-classifier.md`) e tracciata in BUSINESS_STATE §6 ("NewsKeeper T+7 quality review ~8 giugno") + §5 ("[S83] NewsKeeper S2 → T+7 quality review → S100").
**Tipo:** review investigativa read-only (nessun codice modificato, nessun restart).
**Finestra dati:** 2026-06-01 → 2026-06-09 (Supabase `newskeeper_signals`, 989 righe `haiku_s2`).
**Sblocca:** decisione *timing Sentinel: Phase B vs accelerare NewsKeeper S3-S4*.

---

## 0. In una riga

Il classifier Haiku S2 ha **risolto il problema vero del regex** (ammetteva ~65% rumore: ora il rumore viene scartato a monte), ma ha introdotto **un difetto strutturale più piccolo e più insidioso**: sui segnali più forti (high/critical) sbaglia la *direzione* circa 1 volta su 4, perché il guardrail "direction Python autoritativa" **sovrascrive Haiku anche quando Haiku ha ragione**. Costo trascurabile (~€6-7/mese). Come *indicatore di timing* NewsKeeper oggi è coincidente-o-laggante rispetto a Sentinel; il suo valore differenziale (catalizzatori macro esogeni) non emerge finché non c'è il digest aggregato S3.

---

## 1. Contesto: la settimana era un crash vero

Prima dei numeri, una premessa che cambia la lettura: **2026-06-01 → 09 è stata una settimana oggettivamente brutta** per il mercato. BTC da ~$71K a sotto $60K, ETF outflow $1.7B in 4 settimane, report inflazione "hot" (>4%, massimo da 2023), timori di rialzo Fed, guerra Iran-Israele, crash Zcash. Quindi quando vediamo "33% dei segnali è high severity", **non è automaticamente gonfiaggio**: parecchie di quelle news erano genuinamente gravi.

---

## 2. I 4 criteri della review (dal report S94a §6)

### 2.1 — Tasso di falsi positivi (FP) → **MIGLIORATO, ma cambiato di natura**

Il regex aveva ~65% FP nel senso di **ammettere rumore come segnale**. Haiku S2 chiude questo buco: `theme='irrelevant'` viene filtrato *prima* della scrittura → **0 righe irrilevanti scritte** in 9 giorni. Il campione di segnali high/critical è quasi tutto genuinamente market-relevant. Bene.

Il FP che resta **non è più rumore ammesso, è mis-calibrazione**:
- **Severità**: distribuzione su 989 righe = low 27% / medium 40% / **high 33% / critical 0.6%**. Un terzo "high" è alto; parte è giustificato dal crash, parte è gonfiato su macro CNBC tangenziale al crypto ("Iran war cost: household paying $450 more on gas" → high, ma irrilevante per il bot).
- **Theme**: 183 righe `market_crash` in 9gg, di cui **22% non-negative** (positive/neutral) — un tema "crash" che è positivo è un mis-labeling (es. *"Bitcoin price eyes $90K as bullish divergence flashes"* etichettato `market_crash`).

### 2.2 — Direzioni corrette → **IL problema. La 4ª obiezione CEO è confermata**

Distribuzione direzione (Python pre-computa, è "autoritativa" per Haiku):
- **mixed 74%** (Haiku decide), down 19%, up 6.5%, flat 0.2%.

Il bias conservativo a "mixed" **funziona**: nel 74% dei casi il lexicon Python si tira indietro e lascia decidere Haiku (che legge bene). Il problema vive nel ~26% con direzione "hard", dove il **guardrail forza l'impact di Haiku a combaciare con la direzione Python**. Quando il lexicon Python sbaglia, il guardrail **inverte attivamente** la lettura corretta di Haiku.

**45 righe (4.6%)** sono `macro`/`market_crash` marcate `positive`+`up`. Sul campione distinto, ~1 su 4 sono **inversioni vere** su news market-relevant, e si addensano su HIGH/critical (i segnali più consequenziali):

| Titolo | Classificato | Realtà | Causa tecnica |
|---|---|---|---|
| *"Bitcoin Has Dumped All of Its Gains... And Then Some"* | **critical, positive, up** (conf 0.95, ×4 giorni) | massimamente ribassista | `"gains"` ∈ lexicon up, `"dumped"` assente dal lexicon down |
| *"Wholesale inflation jumps 6%, biggest since 2022"* | **high, positive, up** | inflazione che sale = bearish | `"jumps"` = up word |
| *"Traders now see next Fed move as a hike"* | **high, positive, up** | rialzo Fed = bearish | `"surge"` = up word |
| *"Bitmine's ETH bet nears $9B loss as ether falls below $1,800"* | **high, positive, up** | massimamente ribassista | euristica inversione `loss`+`falls`→up sparata a vuoto |
| *"Bitcoin fell 21%... doom loop next?"* | **high, positive** | ribassista | lexicon gap |

In sintesi: ~1% di **tutti** i segnali sono inversioni *rumorose*, ma sono proprio dove NewsKeeper "grida" più forte.

**Causa-radice di design (non un bug puntuale):** il principio S94a "Python fa i conti, l'LLM legge" (lezione 81b) è corretto per la *matematica*, ma la direzione di una headline **non è matematica — è reading comprehension**, ed è esattamente ciò in cui Haiku batte un dizionario di parole-chiave. Per il campo `direction`, l'architettura ha invertito i ruoli: ha messo a fare il lavoro di lettura un lexicon, e ha dato a quel lexicon potere di veto su Haiku. Il guardrail, pensato come rete di sicurezza, è la **fonte primaria** degli errori rumorosi.

### 2.3 — Lead/lag vs Sentinel → **coincidente-a-laggante; non c'è ancora un aggregato da confrontare**

Sentinel produce uno *score di rischio price-based* (`sentinel_scores`); NewsKeeper produce *segnali per-item*. **Non esiste un "regime NewsKeeper" aggregato** da confrontare con Sentinel → il lead/lag pulito a livello-sistema non è cablato (lo fornirebbe proprio il digest S3 "calmo/alert/tempesta").

Allineamento giornaliero come proxy (NK = % segnali negativi e conteggio high; Sentinel = risk score + BTC):

| Giorno | NK neg% | NK high | Sentinel risk(avg/max) | BTC 24h | BTC low |
|---|---|---|---|---|---|
| 06-01 | 36% | 35 | 22.9 / 46 | -3.1 | 70.8K |
| 06-02 | **43%** | 37 | 27.2 / 52 | -4.8 | 66.3K |
| 06-04 | 43% | **49** | 26.1 / 60 | -4.4 | 62.0K |
| 06-05 | 43% | 43 | 28.4 / **70** | -2.7 | **59.3K** |
| 06-07 | 42% | 36 | 22.4 / 52 | **+2.0** | 60.8K |
| 06-08 | **36%** | 30 | 23.4 / 52 | +2.3 | 62.4K |
| 06-09 | 35% | **21** | 26.5 / 52 | -1.6 | 60.9K |

NK e Sentinel si muovono **insieme**: neg% sale al primo giorno di selloff e cala appena BTC gira positivo (06-07). Conclusione: **NewsKeeper è coincidente-a-laggante** sui movimenti price-driven — è inevitabile, perché le headline crypto *raccontano* il prezzo dopo che si è mosso ("Bitcoin dives below $60K" esce *dopo* il tonfo, mentre Sentinel legge il prezzo ogni minuto). Il valore differenziale di NewsKeeper è sui **catalizzatori esogeni** (Fed, inflazione, exploit) che il prezzo non ha ancora assorbito — ma quel valore emerge come *timing* solo se aggregato in un segnale di regime confrontabile con Sentinel. Cioè: di nuovo, il digest S3.

### 2.4 — Costo Haiku → **trascurabile (~€6-7/mese)**

- **~275 chiamate Haiku/giorno** (misurato dal log Mac Mini: 1019 candidati su 355 tick loggati / ~3.7 giorni; i candidati = le chiamate, dedup per `guid` con TTL 24h evita la riclassificazione a ogni tick).
- ~460 token input/call (system prompt ~260 + payload ~200) + ~70 output/call.
- Haiku 4.5 = $1/MTok input, $5/MTok output → **~$0.22/giorno ≈ $6.7/mese ≈ €6.2/mese**. Anche raddoppiando per sicurezza, ~€12/mese.
- **0 fallback regex** in tutta la finestra (conferma: gira davvero Haiku, non degradato in silenzio).
- Nota tecnica: nessun prompt caching → il system prompt è ri-fatturato a ogni call. A questo volume l'ottimizzazione (cache read 0.1×) farebbe risparmiare ~€2-3/mese: non vale la complessità ora.

---

## 3. Un quinto reperto non richiesto: staleness/duplicazione

**219 titoli distinti** (su ~989 righe) compaiono su **≥2 giorni diversi**. Il feed RSS ri-serve item vecchi e il pattern heartbeat (30 min) li riscrive. Esempio: *"Dumped all its gains"* riemesso critical 4 giorni di fila. Per i segnali per-item attuali è poco più che cosmetico; **per il digest S3 diventa importante** — contare item riemessi gonfia il volume e fa ri-allarmare su news vecchie. Da tenere a mente nel design di S3.

---

## 4. Verdetto e raccomandazione

**Verdetto: NewsKeeper S2 è un miglioramento netto sul regex e operativamente sano (feed stabile, 0 fallback, costo trascurabile), ma ha un difetto di correttezza sulla direzione che va chiuso prima che NewsKeeper alimenti qualcosa che decide.**

Sulla decisione che la review sblocca (*Phase B vs accelerare NewsKeeper S3*), i dati dicono:

1. **NewsKeeper oggi non aggiunge valore di timing sopra Sentinel** sui movimenti price-driven (è coincidente/laggante). Il suo edge (macro esogeno) richiede il digest aggregato S3 per emergere ed essere confrontabile con Sentinel.
2. **Prima del digest va sistemata la direzione.** Un digest costruito su segnali che a volte invertono il segno propagherebbe l'errore in forma aggregata (peggio: meno ispezionabile).
3. **Phase B (Sentinel coin-aware) è ortogonale** e copre il lato-prezzo, che Sentinel già fa meglio di NewsKeeper.

Raccomandazione operativa (decisione finale Board/CEO): **(a) fix direzione → (b) digest S3 → poi (c) confronto lead/lag vero vs Sentinel**, in quest'ordine. Phase B può procedere in parallelo perché indipendente.

---

## 5. Anti-assenso §[7] — il punto su cui NON decido io

C'è un **disaccordo tecnico reale con una scelta di design del brief S94a** (il guardrail "direction Python autoritativa"). Avere ragione sui dati non mi dà l'ultima parola sulla decisione → sale a Max/Board (regola §7). Tre opzioni per il fix direzione, in ordine di invasività crescente:

- **A — Patch del lexicon** (`"dumped"`, fix euristica `loss`+`falls`, declassare `"jumps/surge"` su soggetti-inflazione). Minimo sforzo, ma è whack-a-mole: il prossimo titolo fuori-dizionario re-inverte.
- **B — Declassare la direzione Python da "veto" a "hint"**: Haiku setta l'impact; il guardrail interviene solo quando Haiku ha bassa confidenza *oppure* la direzione Python è "hard" e *non* deriva dall'euristica fragile. Risolve la causa-radice mantenendo una rete per i casi ambigui.
- **C — Direzione Python solo come flag di disaccordo** (logga `direction_conflict` per audit, non sovrascrive). Massima fiducia in Haiku; perde la rete di sicurezza sui casi in cui Haiku davvero sbaglia.

Voto CC: **B**. Tiene il principio "Python fa la matematica" dove serve davvero (i `numbers`), ma restituisce a Haiku la lettura della direzione, che è il suo mestiere. Brief separato, ~stima media (tocca `haiku_classifier.py` + `preprocessor.py` + test), nessun restart bloccante (NewsKeeper standalone, hot-swap del processo).

---

## 6. Cosa NON ho fatto e perché

- **Nessun codice modificato**: il fix direzione è una decisione di design che richiede input Board (§7). Pronto a produrre il brief su conferma.
- **Lead/lag quantitativo fine** (correlazione oraria sui singoli eventi): non costruito perché manca l'aggregato NewsKeeper — sarebbe misurare timing su una grandezza che non esiste ancora. Il digest S3 è il prerequisito.
- **Backfill/pulizia delle inversioni storiche**: testnet, soldi finti, NewsKeeper in DRY_RUN (non alimenta trade) → conta il fix-forward, non lo storico.

---

## 7. Dati a supporto (riproducibili)

Tutte le query su Supabase progetto `BagHolderAI` (`pxdhtmqfwjwjhtcoacsn`), tabella `newskeeper_signals`, filtro `raw_data->>'classifier_version'='haiku_s2'`, finestra `now() - interval '8 days'`. Conteggio chiamate Haiku da `logs/newskeeper.out` sul Mac Mini (PID 10899). Codice: `bot/newskeeper/{preprocessor,haiku_classifier,signal_writer,main}.py` + `readers/rss_feeds.py`.
