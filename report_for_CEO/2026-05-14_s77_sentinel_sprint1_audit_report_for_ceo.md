# S77 — Sentinel Sprint 1 Audit Empirico (post-fix 70b)

**Da:** Claude Code (Intern)
**Per:** CEO + Board (Max)
**Data:** 2026-05-14
**Brief di riferimento:** `config/brief_77a_sentinel_sprint1_audit.md`
**Window analizzata:** `created_at > 2026-05-10T09:51:00Z` AND `score_type = 'fast'`
**Sample size:** **6.081 scan** (~4 giorni e mezzo di dati DRY_RUN continuo)
**Codice toccato:** **zero**. Nessun commit, nessun restart bot.

---

## 0. TL;DR

| Bug 70b | Criterio brief | Osservato | Verdetto |
|---|---|---|---|
| 1. `speed_of_fall_accelerating` scattava ~30% | firing < 10% | **2.32%** | ✅ PASS netto |
| 2. `opportunity_score` inchiodato a 20 | ≥ 1 valore > 20 | 3 valori distinti (20/25/30) | ✅ PASS (debole) |
| 3. `risk_score` binario 20/40 | ≥ 3 valori distinti | **5 valori distinti** (20/26/32/46/52) | ✅ PASS |

**Tutti e 3 i fix 70b funzionano sui criteri stabiliti dal brief 77a.** Nessun codice da toccare per chiudere Sprint 1.

**Però** l'audit ha portato in superficie 2 issue strutturali NON previste dal brief, entrambe domande da portare al Board (vedi §5):

- **A.** Asimmetria visiva risk vs opportunity sul grafico /admin: confermata empiricamente. Driver unico = SoF (alza solo risk, mai opp). Con SoF acceso il gap medio è +26; senza SoF il sistema è simmetrico.
- **B.** Il signal funding è **completamente morto** su testnet: 0 firing su 6.081 scan, su nessuna delle 8 soglie. Le soglie 70b sono ancora ~10× sopra il range reale, e su testnet il funding sta praticamente sempre intorno a +0.00004 (poco mosso, raramente negativo).

---

## 1. Metodologia

### 1.1 Window e filtro

- Filtro temporale: `created_at > '2026-05-10T09:51:00Z'` (restart S70, primo tick post-fix 70b)
- Filtro tipo: `score_type = 'fast'` (Sprint 1 fast loop; Sprint 2 slow loop sarà un brief separato)
- Schema verificato: colonne top-level `risk_score`, `opportunity_score`, `btc_change_1h`, `funding_rate`; JSONB `raw_signals` contiene `speed_of_fall_accelerating` (bool), `breakdown` (dict regole+delta), e cambi multi-timeframe (5m/15m/1h/4h)
- Note brief 1.4: la breakdown vive in `raw_signals->'breakdown'`, NON al livello top di `raw_signals`. Query adattata.

### 1.2 Query eseguite

Tutte via Supabase MCP `execute_sql` su progetto `pxdhtmqfwjwjhtcoacsn`. Nessun dato inventato. 6 query del brief + 3 query custom asimmetria.

### 1.3 Sample size adeguato?

6.081 scan ÷ ~60s tick interval ≈ 101 ore di Sentinel attivo nel periodo. Buona base per inferenza su firing rate e distribuzioni; meno solida per coda estrema (eventi rari come BTC −5% o funding squeeze, mai osservati nel periodo).

---

## 2. Verdetti dettagliati sui 3 bug

### 2.1 Bug 1 — SoF firing rate

| Metric | Valore |
|---|---|
| Total scans (fast, post-70b) | 6.081 |
| SoF = true | 141 |
| **SoF firing %** | **2.32%** |

**Verdetto: ✅ PASS netto** (criterio brief: < 10%).

Pre-70b stimato ~30% (dataset 6-8 maggio nel commento `price_monitor.py:39-42`); post-70b 2.32% → riduzione di ~13×. Il floor `_SOF_MIN_DROP_1H_PCT = -0.5` filtra correttamente il rumore di mercato laterale.

**Nota architetturale**: il fix è strutturale (non un tuning di soglia delicato). SoF ora richiede 3 condizioni AND: (a) ora intera in calo ≥ 0.5%, (b) ultimi 20m negativi, (c) accelerazione ≥ 1.5× rispetto alla media. Il floor a) è la condizione che mancava pre-70b ed eliminava praticamente tutti i falsi positivi.

### 2.2 Bug 2 — `opportunity_score` morto a 20

| opportunity_score | count | % |
|---|---|---|
| 20 (base) | 5.591 | **91.94%** |
| 25 | 391 | 6.43% |
| 30 | 99 | 1.63% |
| > 30 | 0 | 0% |

**Verdetto: ✅ PASS tecnico** (criterio brief: ≥ 1 valore > 20). 3 valori distinti osservati, ma **vita debole**:
- 92% del tempo opp = 20 (base)
- Solo 8.06% del tempo opp si muove
- Max osservato = 30 (mai 35/40/45+)

**Cosa muove opp nel dataset attuale**: 100% via `btc_pump_0_5pct_1h` (+5 → 25) e `btc_pump_1pct_1h` (+10 → 30). **Nessuna delle 4 soglie funding short squeeze ha mai contribuito** (vedi §3).

### 2.3 Bug 3 — `risk_score` binario 20/40

| risk_score | count | % | Composizione |
|---|---|---|---|
| 20 (base) | 5.695 | **93.65%** | nessuna regola fired |
| 26 | 229 | 3.77% | `btc_drop_0_5pct_1h` (+6) |
| 32 | 16 | 0.26% | `btc_drop_1pct_1h` (+12) |
| 46 | 133 | 2.19% | `btc_drop_0_5pct_1h` + SoF (+6 + 20) |
| 52 | 8 | 0.13% | `btc_drop_1pct_1h` + SoF (+12 + 20) |

**Verdetto: ✅ PASS netto** (criterio brief: ≥ 3 valori). **5 valori distinti** osservati. Pre-70b risk era solo 20 o 40 (binario). Post-70b la ladder granulare aggiunge gli step 26 e 32; il salto 40→46/52 conferma anche che SoF compone correttamente con i drop ladder.

**Stesso pattern di opp**: 94% del tempo risk = 20 (base). I valori intermedi 26/32 sono dominati dai mini-drop 0.5–1%; i valori "alti" 46/52 sono sempre SoF + un drop.

---

## 3. Breakdown completo delle regole scattate

| Regola | Times fired | % su 6.081 | Lato |
|---|---|---|---|
| `btc_pump_0_5pct_1h` | 391 | 6.43% | opp +5 |
| `btc_drop_0_5pct_1h` | 362 | 5.95% | risk +6 |
| `speed_of_fall_accelerating` | 141 | 2.32% | risk +20 |
| `btc_pump_1pct_1h` | 99 | 1.63% | opp +10 |
| `btc_drop_1pct_1h` | 24 | 0.39% | risk +12 |
| `btc_drop_2pct_1h` | 0 | 0% | — |
| `btc_drop_3pct_1h` | 0 | 0% | — |
| `btc_drop_5pct_1h` | 0 | 0% | — |
| `btc_drop_10pct_1h` | 0 | 0% | — |
| `btc_pump_2pct_1h` | 0 | 0% | — |
| `btc_pump_3pct_1h` | 0 | 0% | — |
| `btc_pump_5pct_1h` | 0 | 0% | — |
| `funding_long_weak` (+4 risk) | 0 | 0% | — |
| `funding_long_mild` (+8 risk) | 0 | 0% | — |
| `funding_over_leveraged_long` (+15 risk) | 0 | 0% | — |
| `funding_over_leveraged_long_strong` (+25 risk) | 0 | 0% | — |
| `funding_short_weak` (+4 opp) | 0 | 0% | — |
| `funding_short_mild` (+8 opp) | 0 | 0% | — |
| `funding_short_squeeze` (+15 opp) | 0 | 0% | — |
| `funding_short_squeeze_strong` (+25 opp) | 0 | 0% | — |

**Osservazioni chiave**:

1. **Solo 5 delle 17 regole hanno mai scattato** nel periodo.
2. **Drop_2pct e oltre: zero firing**. Mercato testnet troppo calmo per i 4 step alti del ladder risk.
3. **Pump_2pct e oltre: zero firing**. Stessa cosa lato opp.
4. **Tutte le 8 regole funding: zero firing**. Vedi §4 per il perché — il signal funding è strutturalmente dead nel range testnet osservato.
5. **Simmetria del primo step**: 362 drop_0.5 vs 391 pump_0.5, 24 drop_1 vs 99 pump_1. Mercato leggermente bullish nel periodo, ma il primo step funziona simmetricamente. Il bias osservato non viene dalla ladder BTC.

---

## 4. Issue strutturale A — Asimmetria risk vs opportunity

### 4.1 Osservazione di partenza (Board)

Max ha notato sul grafico /admin che **risk si alza molto più di quanto opportunity faccia**. Audit empirico: l'osservazione è corretta, l'asimmetria è quasi interamente attribuibile a SoF.

### 4.2 Distribuzione del gap (`risk - opp`)

| gap | count | % | Significato |
|---|---|---|---|
| −10 | 99 | 1.63% | opp = 30 (pump_1pct), risk = 20 → opp avanti |
| −5 | 391 | 6.43% | opp = 25 (pump_0.5pct), risk = 20 → opp avanti |
| 0 | **5.206** | **85.60%** | base 20 = 20 → simmetrico |
| +6 | 229 | 3.77% | risk = 26 (drop_0.5pct), opp = 20 |
| +12 | 16 | 0.26% | risk = 32 (drop_1pct), opp = 20 |
| **+26** | **133** | **2.19%** | risk = 46 (drop_0.5pct + SoF), opp = 20 |
| **+32** | **8** | **0.13%** | risk = 52 (drop_1pct + SoF), opp = 20 |

**Lettura**: il gap è bilanciato per i mini-mov (−5/−10 lato opp = 8%, +6/+12 lato risk = 4%, ratio ~2:1 dovuto al mercato leggermente bullish). I gap **alti** sono tutti spiegati da SoF acceso (+26 / +32). Nessun gap "alto" è dovuto al solo ladder asimmetrico del brief originale.

### 4.3 SoF on vs off — il vero driver

| Stato | n | avg risk | avg opp | avg gap | max risk | max opp |
|---|---|---|---|---|---|---|
| SoF = **false** | 5.941 | 20.26 | 20.50 | **−0.23** | 32 | 30 |
| SoF = **true** | 141 | **46.34** | 20.00 | **+26.34** | 52 | 20 |

Quando SoF è false, il sistema è **quasi perfettamente simmetrico** (avg gap −0.23, addirittura leggermente sbilanciato a favore di opp per via dei pump_0.5/1pct più frequenti dei drop nel periodo).

Quando SoF è true, opp resta **inchiodata a 20** (max 20) mentre risk salta a 46 o 52. **SoF è l'unico signal asimmetrico per design**: +20 a risk, 0 a opp.

### 4.4 Implicazioni

Tutta l'asimmetria visiva osservata sul grafico /admin viene dal 2.32% di firing SoF. È matematicamente by design del brief 70b originale.

**Due interpretazioni possibili**:

1. **"È giusto così"**: panico bearish ≠ euforia bullish. Le capitolazioni crypto sono fenomeni asimmetrici (ripide, accelerate); i pump tendono ad essere a gradini, meno cascade. Mantenere SoF mono-laterale è coerente con la natura del mercato.

2. **"Serve simmetria"**: aggiungere uno `speed_of_rise_accelerating` (specchio di SoF) per catturare FOMO/short squeeze cascading. Costo: ~50 righe in `price_monitor.py` + ~10 in `score_engine.py` + test.

**Questa è una decisione di design, non delegata a CC.** Vedi §6 domande aperte.

---

## 5. Issue strutturale B — Funding signal completamente morto

### 5.1 Range osservato vs soglie 70b

| Soglia | Direzione | Trigger | Mai raggiunto perché |
|---|---|---|---|
| `funding > 0.0005` → risk +25 | long strong | mai | max osservato 0.0000582 (~10× sotto) |
| `funding > 0.0003` → risk +15 | long mild | mai | max osservato 0.0000582 (~5× sotto) |
| `funding > 0.0002` → risk +8 | long weak+ | mai | max osservato 0.0000582 (~3× sotto) |
| `funding > 0.0001` → risk +4 | long weak | mai | max osservato 0.0000582 (~2× sotto) |
| `funding < -0.00002` → opp +4 | short weak | mai | min osservato −0.00000115 (17× sopra la soglia, lato sbagliato) |
| `funding < -0.00005` → opp +8 | short mild | mai | idem |
| `funding < -0.0001` → opp +15 | short mid | mai | idem |
| `funding < -0.0003` → opp +25 | short strong | mai | idem |

**Statistiche funding nel periodo**:

| Metric | Valore |
|---|---|
| min | −0.00000115 |
| p5 | −0.00000115 |
| p50 (mediana) | +0.00004555 |
| avg | +0.00004137 |
| p95 | +0.00005822 |
| max | +0.00005822 |
| n | 6.081 |

### 5.2 Diagnosi

Il funding testnet Binance sembra **strutturalmente vicino a +0.00004** (≈ 0.004% per finestra di funding), praticamente mai negativo, mai sopra 0.00006. Range totale: ~6e-5 di ampiezza, tutto schiacciato sopra zero.

**Probabili cause** (interpretazione, da confermare con Binance docs):
- Volume perpetual testnet basso → calcolo funding poco stressato dal market
- Binance potrebbe applicare un floor/ceiling artificiale sul testnet
- Mercato spot↔perpetual su testnet poco speculativo → nessun premium di leva

In ogni caso: **le soglie 70b funding sono ancora 1 ordine di grandezza fuori dal range testnet**. Era già stata la diagnosi 70b ma evidentemente l'abbassamento non è stato sufficiente.

### 5.3 Opzioni

| Opzione | Descrizione | Costo | Rischio |
|---|---|---|---|
| **A. Ri-abbassare le soglie** ulteriormente (es. risk weak > 0.00005, opp weak < 0) | ~20 righe in `score_engine.py` + test | basso codice | rischio overfit testnet, soglie inutili su mainnet |
| **B. Accettare funding dead-by-design su testnet**, lasciare le soglie come sono | zero codice | zero | accettiamo che funding contribuisca solo su mainnet |
| **C. Sostituire funding con un indicatore alternativo** (es. open interest, basis spot↔perp) | redesign Sprint 1.5 o Sprint 2 | alto (input source, infrastructure) | strategicamente più solido |
| **D. Branch testnet vs mainnet** delle soglie | ~30 righe + env flag | medio | duplicazione, rischio drift |

**Raccomandazione CC** (delegata al Board): **opzione B per ora**, perché:
- Le soglie 70b sono già pensate per essere mainnet-realistic (funding tipico mainnet 0.01–0.03%).
- Abbassare di nuovo sarebbe overfitting al testnet di maggio 2026, non a comportamento reale.
- Sprint 2 introdurrà signal alternativi (F&G, CMC dominance) che possono compensare il funding dead.

**Ma questa è una decisione strategica, non delegabile a CC.** Vedi §6.

---

## 6. Domande aperte per Board / CEO

### 6.1 SoF asimmetrico — decisione di design

**Domanda**: SoF deve restare mono-laterale (+20 solo a risk) o serve simmetrizzarlo con `speed_of_rise_accelerating` (+X a opp su pump accelerati)?

**Implicazioni**:
- Mono-laterale = system è "cauto su drop ma neutro su pump". Coerente con bias di sopravvivenza del bot Grid (entry conservative).
- Simmetrico = system pesa anche le opportunità accelerate (FOMO/squeeze). Più aggressivo, potenzialmente più Sherpa-actionable.

**Costo stimato se simmetrico**: ~1-2h CC (price_monitor.py + score_engine.py + 2-3 test).

### 6.2 Funding signal su testnet — decisione strategica

**Domanda**: come gestire il funding signal totalmente dead su testnet?

**Opzioni in §5.3.** Raccomandazione CC: opzione B (accetta dead-by-design, rimpiazza in Sprint 2). Ma Board può decidere altrimenti.

### 6.3 Opportunity score debole (max 30, 92% del tempo a base 20)

**Osservazione**: anche se "PASS tecnico", opp è morta il 92% del tempo. Il fix 70b ha sbloccato 25/30 ma non più alti. In un mercato testnet calmo è coerente, ma se Sherpa dovrà reagire a "opp alta" potrebbe non vederla mai.

**Domanda**: serve un fix ad hoc (es. abbassare ulteriormente le soglie pump_0.5pct → +8 invece di +5, e pump_1pct → +15 invece di +10) **oppure** è giusto che opp resti bassa fino a Sprint 2 (F&G + dominance compongano)?

**Raccomandazione CC**: attendere Sprint 2. Toccare ora le soglie pump rischia di overcorreggere.

---

## 7. Cosa è stato fatto e cosa NO

### Fatto

- Schema sentinel_scores ispezionato (tutte le colonne mappate, JSONB confermato)
- 6 query brief + 3 query custom asimmetria eseguite
- Tutti i 6 criteri brief verificati con verdetto PASS/FAIL
- Issue strutturali emerse documentate
- Report scritto (questo file)

### NON fatto (per scelta)

- **Nessun codice toccato.** Brief 77a richiede di "scrivere fix" solo se uno o più bug fallisce. Tutti i 3 hanno passato → nessun fix obbligatorio.
- **Nessun commit di codice.** Solo questo report.
- **Nessun restart bot.** Mac Mini resta su `b2ae5f7` come previsto dal brief.
- **Nessuna modifica a Sherpa.** Off-limits per brief 77a.
- **Nessuna decisione strategica unilaterale su 6.1, 6.2, 6.3.** Tutte parcheggiate al Board.

---

## 8. Roadmap impact

**Sprint 1 audit (questo brief)**: ✅ CHIUSO. I 3 fix 70b funzionano.

**Sblocca Sprint 2?** Tecnicamente sì (criterio brief 77a soddisfatto). Ma 3 questions aperte richiedono input prima di partire con Sprint 2:

- 6.1 SoF simmetria → impatta design score_engine
- 6.2 Funding dead → impatta sequenza Sprint 2 (priorità F&G come rimpiazzo?)
- 6.3 Opp debole → impatta calibrazione di partenza Sprint 2

**Suggerimento CC**: sessione CEO breve per discutere 6.1/6.2/6.3, poi brief 78a "Sentinel Sprint 2 build" con scelte già fatte.

---

## 9. Allegato — Query SQL eseguite (riproducibilità)

Tutte su Supabase progetto `pxdhtmqfwjwjhtcoacsn` via MCP `execute_sql`.

```sql
-- 1.1 SoF firing rate
SELECT COUNT(*) AS total_scans,
       COUNT(*) FILTER (WHERE raw_signals->>'speed_of_fall_accelerating' = 'true') AS sof_true,
       ROUND(100.0 * COUNT(*) FILTER (WHERE raw_signals->>'speed_of_fall_accelerating' = 'true') / COUNT(*), 2) AS sof_pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast';

-- 1.2 risk distribution
SELECT risk_score, COUNT(*) AS cnt,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast'
GROUP BY risk_score ORDER BY risk_score;

-- 1.3 opp distribution (idem con opportunity_score)

-- 1.4 breakdown rules fired (nota: raw_signals->'breakdown', non root)
SELECT key AS rule_name, COUNT(*) AS times_fired
FROM sentinel_scores, jsonb_each(raw_signals->'breakdown') AS kv(key, value)
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast' AND key != 'base'
GROUP BY key ORDER BY times_fired DESC;

-- 1.5 funding range (colonna top-level, non in raw_signals)
SELECT MIN(funding_rate), MAX(funding_rate), AVG(funding_rate),
       PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY funding_rate) AS p5,
       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY funding_rate) AS p50,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY funding_rate) AS p95
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast' AND funding_rate IS NOT NULL;

-- 1.6 BTC change_1h range (colonna top-level)
SELECT MIN(btc_change_1h), MAX(btc_change_1h), AVG(btc_change_1h),
       PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY btc_change_1h) AS p5,
       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY btc_change_1h) AS p50,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY btc_change_1h) AS p95
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast' AND btc_change_1h IS NOT NULL;

-- Asym 1: distribuzione gap (risk - opp)
SELECT (risk_score - opportunity_score) AS gap, COUNT(*) AS cnt,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast'
GROUP BY gap ORDER BY gap;

-- Asym 2: SoF impact su avg risk / opp / gap
SELECT
  CASE WHEN raw_signals->>'speed_of_fall_accelerating' = 'true' THEN 'SoF=true' ELSE 'SoF=false' END AS sof,
  COUNT(*) AS n, AVG(risk_score) AS avg_risk, AVG(opportunity_score) AS avg_opp,
  AVG(risk_score - opportunity_score) AS avg_gap, MAX(risk_score) AS max_risk, MAX(opportunity_score) AS max_opp
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast'
GROUP BY sof;

-- Asym 3: ladder firing symmetry
SELECT
  SUM(CASE WHEN btc_change_1h <= -1 THEN 1 ELSE 0 END) AS drop_1pct_plus,
  SUM(CASE WHEN btc_change_1h <= -0.5 AND btc_change_1h > -1 THEN 1 ELSE 0 END) AS drop_0_5pct,
  SUM(CASE WHEN btc_change_1h >= 1 THEN 1 ELSE 0 END) AS pump_1pct_plus,
  SUM(CASE WHEN btc_change_1h >= 0.5 AND btc_change_1h < 1 THEN 1 ELSE 0 END) AS pump_0_5pct,
  SUM(CASE WHEN btc_change_1h > -0.5 AND btc_change_1h < 0.5 THEN 1 ELSE 0 END) AS dead_zone,
  SUM(CASE WHEN btc_change_1h <= -2 THEN 1 ELSE 0 END) AS drop_2pct_plus,
  SUM(CASE WHEN btc_change_1h >= 2 THEN 1 ELSE 0 END) AS pump_2pct_plus,
  COUNT(*) AS total
FROM sentinel_scores
WHERE created_at > '2026-05-10T09:51:00Z' AND score_type = 'fast' AND btc_change_1h IS NOT NULL;
```

---

## 10. Addendum 2026-05-14 — Decisioni Board sulle 3 questions

CEO/Board ha risposto a §6.1/6.2/6.3 lo stesso giorno. Riassunto delle decisioni e razionali:

### 10.1 Risposta a §6.1 — SoF asimmetrico: NO `speed_of_rise`

**Decisione**: lasciare SoF mono-laterale. Niente signal simmetrico lato opp.

**Razionale CEO**: "le capitolazioni crypto sono asimmetriche per natura — scendono a picco, salgono a gradini. Un `speed_of_rise` su un pump del 2% in 20 minuti non è un segnale di pericolo o opportunità chiara — è rumore. Il Grid bot poi non ha un'azione sensata da prendere su 'prezzo che sale velocemente' (non vende di più — la sell ladder già copre quello). Il costo è basso (~2h) ma il valore aggiunto è quasi zero."

**Parking condition**: "Se Sprint 2 con Fear & Greed mostra che ci serve, lo rivalutiamo." → riapribile in Sprint 2 se F&G indica FOMO/squeeze sistematici non catturati.

### 10.2 Risposta a §6.2 — Funding signal dead: opzione B

**Decisione**: accettare funding dead-by-design su testnet. Soglie 70b restano come sono.

**Razionale CEO**: "Le soglie 70b sono già calibrate per mainnet (funding tipico 0.01–0.03%). Ri-abbassarle per il testnet sarebbe overfitting a un ambiente artificiale. Sprint 2 aggiungerà Fear & Greed e CMC dominance che compenseranno. Quando andremo su mainnet, il funding si sveglierà da solo."

**Implicazione**: il signal funding contribuirà alla scoring solo da mainnet. Su testnet Sentinel opera effettivamente su 4 signal anziché 5 (price ladder + SoF + base; no funding).

### 10.3 Risposta a §6.3 — Opp debole (max 30): aspettare Sprint 2

**Decisione**: non toccare i delta pump_X. Aspettare Sprint 2.

**Razionale CEO**: "Opp a 30 con un mercato laterale ±1.8% è coerente. Toccare i delta ora (pump +8 invece di +5) sarebbe un tuning cosmetico. Sprint 2 porterà F&G e regime detection che sono il vero moltiplicatore di opp — è lì che il punteggio prenderà vita."

**Implicazione**: opp resterà 92% del tempo a base 20 fino all'arrivo di Sprint 2. Accettabile perché Sherpa è in DRY_RUN e non agirà su opp bassa.

### 10.4 Verdetto complessivo Sprint 1

**Sprint 1 è CHIUSO con tutti PASS.** Le 3 questions di design hanno tutte la stessa risposta strategica: "va bene così per ora, Sprint 2 risolverà".

**Prossima mossa nella sequenza Sentinel-first (CEO S76)**: Brief 78a — Sentinel Sprint 2 (slow loop: Fear & Greed + CMC dominance + regime detection).

---

*Fine report. Sprint 1 audit chiuso. CC in attesa del brief 78a Sprint 2.*
