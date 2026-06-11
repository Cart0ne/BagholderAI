# Report S102 — Sherpa Coherence Audit + Write Guard

**Data**: 2026-06-11 · **Sessione**: S102
**Brief sorgente**: `config/2026-06-11_S102_brief_sherpa-coherence-audit.md` (SCOPE `sherpa-coherence-audit`)
**Commit Parte A**: `a867179` (bot/sherpa/main.py + tests/test_sherpa_write_gate.py)
**Metodo Parte B**: indagine multi-agente (6 investigatori + verifica avversariale per claim + completeness critic, 25 agenti totali); ogni claim load-bearing è stato sottoposto a refutazione indipendente; le correzioni dei refuter sono integrate nel testo. Dati: `sherpa_proposals` 50.303 righe (6 mag–11 giu), `sentinel_scores`, `bot_config`, `config_changes_log`, codice a commit `0ad599b` (pre-fix).

---

## 0. Executive summary

| Domanda | Verdetto |
|---|---|
| **Parte A** write-on-change | ⚠️ **Il brief partiva da una premessa superata**: il filtro esisteva già (79c, 18 mag). Il volume ~2.100/gg era causato dal pass-through *a livello* di `stop_buy` (extreme_fear persistente dal 29 mag). **Fix shippato** (`a867179`): gate flip-based + heartbeat 4h. Volume atteso: **~18 righe/gg** (−99%). Restart Mac Mini **rimandato** (decisione Max: restart unico post-review Board). |
| **B1** mappa regimi | Tutti e 5 i regimi implementati, valori base **identici al design S61**. Greed/extreme_greed mai esercitati (mercato solo-bear). Fast loop S61 **rimosso deliberatamente** nello Sprint 2 — oggi NON esiste. Le proposte nei dati NON sono i target di Sherpa: il cap ±30% su config statica le schiaccia (BTC extreme_fear: propone 0.65, vorrebbe 2.5). |
| **B2** coin-agnostic | **SÌ, senza modifiche al codice.** DOGE/USDT = 1 riga in bot_config. Verificato empiricamente contro Binance (multiplier DOGE 1.3519 calcolato live). |
| **B3** copertura parametri | Sherpa scrive **3/12** parametri (= Level A del design), osserva 1 (stop_buy flag), ignora 8. Solo `capital_per_trade` ha esclusione documentata. ⚠️ Gate pre-LIVE: `idle_reentry_hours=8` in bot_config è **fuori dal range di design** (0.5–6). |
| **B4** btc_price / would_have_changed | Nessun bug di Sherpa. `btc_price` null = gap di integrazione Sprint 2 (lo slow writer di Sentinel non ha mai scritto il campo). `would_have_changed`=100% = artefatto strutturale del DRY_RUN (cap ±30% su current statico). |
| **B5** regime_stickiness | **Fattibile, basso rischio**: ~5-7 ore / 4 file con l'opzione raccomandata (confidence che modula la velocità del cap). NON costruire prima del verdetto barometro (~23 giu) e di almeno un regime non-bear osservato. |

---

## A. Parte A — Write guard (SHIPPED `a867179`, deploy pending)

### A.1 La premessa del brief era superata (segnalato a Max pre-implementazione)

Il brief assumeva "Sherpa scrive a ogni tick, senza filtro". In realtà il filtro write-on-change + heartbeat esiste dal 18 maggio (brief 79c + fix S79.1). La timeline del volume lo dimostra:

| Fase | Periodo | Righe/gg | Causa |
|---|---|---|---|
| 1 — pre-79c | 6–18 mag | ~2.100 | nessun filtro: 720 tick/gg × 3 coin |
| 2 — post-79c | 19–28 mag | **~440** | filtro attivo: quasi solo heartbeat 600s (432/gg teorici) |
| 3 — bypass | 29 mag–oggi | ~2.100 | regime extreme_fear persistente → `proposed_stop_buy_active` true a ogni tick **bypassava il filtro a livello** ([main.py:411](../bot/sherpa/main.py) pre-fix); `stop_buy_true` ≈ 100% delle righe nei giorni incriminati |

Contributo secondario: `cooldown_active` (stesso difetto a livello) — 373/334 righe extra l'8-9 giu durante l'override manuale SOL.

### A.2 Fix implementato

1. **Gate flip-based**: stop_buy e cooldown scrivono solo alla **transizione** di stato, non finché lo stato persiste. La variabile `stop_buy_flipped` esisteva già ma era usata solo per gli alert Telegram.
2. **Identità completa della proposta**: il confronto on-change copre i 5 campi del brief (3 numerici + `proposed_regime` + `proposed_stop_buy_active`) + il flip di `cooldown_active`. Il regime è nel confronto perché il cap ±30% può saturare due regimi sugli stessi numeri (es. BTC buy 0.65 sia in fear sia in extreme_fear).
3. **Heartbeat 600s → 4h** (decisione Max D1), allineato alla cadenza slow-loop di Sentinel — il regime non può muoversi più in fretta di così.
4. **Bootstrap esteso** (regime/stop_buy/cooldown, finestra 8h): nessuna riga/alert spuria al restart in regime persistente (test dedicato).
5. **Log skip** (decisione Max D2): contatore nella riga heartbeat ("proposal unchanged (118 skips since last write)") invece del log-per-skip letterale del brief, che avrebbe prodotto ~2.000 righe/gg.

**Ramo LIVE invariato** (il gate vive solo nel ramo dry_run; alert gate sui soli numerici, come prima). **Nessuna migration**, nessun file nuovo, storico DB intatto.

### A.3 Volume atteso e nota sul "<10"

Mercato stabile: 3 coin × 6 heartbeat/gg = **18 righe/gg** (−99% vs 2.100). Cambio regime: +1 riga/coin. Override Board: +2 righe/coin (apertura+chiusura finestra). Il "<10 righe/gg" del brief non è raggiungibile con heartbeat 4h e 3 coin (floor matematico 18); Max ha scelto 4h — il monitoraggio liveness vale più del numero tondo.

### A.4 Test e deploy

- `tests/test_sherpa_write_gate.py`: 10 test nuovi (livello-persistente non scrive; flip scrive una volta; cambio regime a numerici identici scrive; cooldown apre/chiude = 2 righe; heartbeat; bootstrap anti-spurio al restart). **Suite completa 195/195.**
- **Deploy PENDING**: il processo Sherpa sul Mac Mini gira ancora col codice pre-fix (quindi `sherpa_proposals` continua a ~2.100 righe/gg finché non si riavvia). Decisione Max: restart unico dopo la review Board di questo report, cumulando eventuali altri interventi. Comandi di restart consegnati a Max in sessione.
- Verifica live post-restart (da fare al deploy): conteggio righe/gg ≤ ~20 in mercato stabile + heartbeat presente ogni 4h.

---

## B1 — Mappa completa regime → parametri (dal CODICE)

### Come leggere i numeri: TARGET vs PRIMA PROPOSTA

Il calcolo reale ([parameter_rules.py:56-125](../bot/sherpa/parameter_rules.py)) è: `base(regime) × volatility_multiplier` → clamp assoluti → **cap ±30% vs current di bot_config** (`MAX_DELTA_PCT=0.30`, `config/settings.py`). Due livelli:

- **TARGET** = dove Sherpa convergerebbe in LIVE dopo N tick (cap escluso).
- **PRIMA PROPOSTA** = quello che si vede in `sherpa_proposals` oggi: il primo passo cappato dal config corrente. **In DRY_RUN il current non si muove mai → la prima proposta è anche la proposta permanente.** Le 50K righe NON mostrano cosa Sherpa "vuole": mostrano il cap.

Moltiplicatori volatilità **live all'11 giugno** (calcolati con la funzione di produzione, no fallback): BTC 1.0 · SOL 1.5315 · BONK 1.7527. NB: il multiplier varia nel tempo (stdev 7gg, cache 1h) — i valori storici in DB usavano multiplier dell'epoca (es. BONK ~2.13 il 29 mag). La verifica avversariale ha confermato che il modello riproduce i dati DB **carattere-per-carattere** quando alimentato con multiplier e current storicamente corretti (es. BTC extreme_fear 0.65/1.05/5.6 = identico al DB; SOL sell 1.3 pre-8-giu si spiega col current 1.0 di allora, 1.53 dopo l'override Board a 1.5).

### Tabella 5 regimi × 3 coin (config corrente: BTC 0.50/1.50/8 · SOL 0.50/1.50/8 · BONK 2.50/2.50/8)

**BTC/USDT (mult 1.0)** — TARGET = base

| Regime | TARGET buy/sell/idle | PRIMA PROPOSTA | stop_buy | Note |
|---|---|---|---|---|
| extreme_fear | 2.50 / 1.00 / 4.0 | **0.65 / 1.05 / 5.6** | **ON** | regime attuale dal 29 mag; cap domina tutto |
| fear | 1.80 / 1.20 / 2.0 | 0.65 / 1.20 / 5.6 | off | |
| neutral | 1.00 / 1.50 / 1.0 | 0.65 / 1.50 / 5.6 | off | sell = target |
| greed | 0.80 / 2.00 / 0.75 | 0.65 / 1.95 / 5.6 | off | **mai osservato** |
| extreme_greed | 0.50 / 3.00 / 0.50 | 0.50 / 1.95 / 5.6 | off | **mai osservato** |

**SOL/USDT (mult 1.5315)**

| Regime | TARGET | PRIMA PROPOSTA | stop_buy | Note |
|---|---|---|---|---|
| extreme_fear | 3.00 / 1.53 / 4.0 | 0.65 / 1.53 / 5.6 | ON | TARGET buy clampato (3.83→3.0) |
| fear | 2.76 / 1.84 / 2.0 | 0.65 / 1.84 / 5.6 | off | |
| neutral | 1.53 / 2.30 / 1.0 | 0.65 / 1.95 / 5.6 | off | |
| greed | 1.23 / 3.06 / 0.75 | 0.65 / 1.95 / 5.6 | off | mai osservato |
| extreme_greed | 0.77 / 4.00 / 0.50 | 0.65 / 1.95 / 5.6 | off | sell satura il clamp 4.0; mai osservato |

**BONK/USDT (mult 1.7527)**

| Regime | TARGET | PRIMA PROPOSTA | stop_buy | Note |
|---|---|---|---|---|
| extreme_fear | 3.00 / 1.75 / 4.0 | 3.00 / 1.75 / 5.6 | ON | buy satura il clamp 3.0 |
| fear | 3.00 / 2.10 / 2.0 | 3.00 / 2.10 / 5.6 | off | |
| neutral | 1.75 / 2.63 / 1.0 | 1.75 / 2.63 / 5.6 | off | |
| greed | 1.40 / 3.51 / 0.75 | 1.75 / 3.25 / 5.6 | off | mai osservato |
| extreme_greed | 0.88 / 4.00 / 0.50 | 1.75 / 3.25 / 5.6 | off | mai osservato |

(idle = 5.6 ovunque nella colonna PRIMA PROPOSTA perché current=8 → floor del cap 8×0.7=5.6 domina ogni base; vedi B3.)

### Greed / extreme_greed: implementati, mai esercitati

Sono in `BASE_TABLE` e Sentinel li emette con F&G≥61 fresco (`regime_analyzer.py`). Il path completo funzionerebbe; semplicemente il mercato non l'ha mai attivato (regimi osservati: neutral 6-13 mag → fear 14 mag-2 giu → extreme_fear 29 mag-oggi). Non è dead code: è un ramo non testato dal mercato — e quindi **senza alcuna validazione live** a oggi.

### Fast loop: previsto da S61, rimosso nello Sprint 2, oggi NON implementato

La tabella S61 (BTC ±3%/±5% in 1h → tighten/loosen) fu implementata nello Sprint 1 (commit `83b253c`) e **rimossa** nello Sprint 2 (commit `3ba1132`, brief 81a) dopo che la Brain Analysis documentò 449 flip in 16 giorni → flicker delle proposte ogni ~6 minuti. Nel codice attuale non esiste alcun ladder fast; ne restano solo i riferimenti nei docstring (incluso uno stale in `bot/sherpa/__init__.py:10`, da allineare).

### Divergenze codice vs design S61

- **Valori base dei 5 regimi: NESSUNA divergenza** (identici riga per riga).
- **Boundary F&G dei regimi: riviste** (es. fear 26-40 nel codice vs 25-45 in S61; neutral 41-60 vs 45-55). S61 le dichiarava "proposals, need backtesting" — la revisione è legittima ma non documentata formalmente.
- Volatility scaling e amplitude cap: **additivi post-S61** (Sprint 2), non previsti dal design originale.

---

## B2 — Coin-agnostic check: SÌ

**Se domani Max aggiunge DOGE/USDT a `bot_config` (is_active=true, managed_by='grid'), Sherpa lo gestisce al tick successivo senza toccare codice.**

- **Discovery dinamica**: i coin arrivano sempre da `_fetch_active_manual_bots` ([main.py](../bot/sherpa/main.py)) con filtri `is_active=true` + `managed_by='grid'`. Zero liste hardcoded (grep verificato: BTC/SOL/BONK compaiono solo in commenti).
- **`ANCHOR_SYMBOL='BTC/USDT'`** ([volatility.py:39](../bot/sherpa/volatility.py)) è il *denominatore statistico*, fetchato direttamente dall'API pubblica Binance, **indipendente da bot_config**: se BTC uscisse dal config, i multiplier si calcolano comunque.
- **Prova empirica live**: DOGE/USDT → multiplier **1.3519** calcolato contro Binance reale; simbolo inesistente (FOOBAR/USDT) → fallback 1.0 con warning, nessun crash.
- **Failure mode**: fetch volatilità fallito → multiplier 1.0 ("si comporta come BTC") + `logger.warning`; prezzo mancante → `symbol_price=None`, la riga si scrive comunque. Degradazione sicura ma **silenziosa**: per un coin esotico atteso-volatile vale controllare i log al primo deploy.
- **Parametri NULL** per il coin nuovo: il cap viene saltato by design → prima proposta = base×mult piena (clampata). Coin `managed_by='tf'`: invisibili a Sherpa per costruzione.
- Vincolo brief 81a "NO hardcoded coin list": **rispettato**.

---

## B3 — Sherpa vs bot_config: 3 manopole su 12

Legenda: **(a)** propone e in LIVE scriverebbe (whitelist `config_writer.py:21`) · **(b)** osserva/segnala, mai scrive · **(c)** ignora.

| Parametro | BTC / SOL / BONK | Sherpa? | Come / perché no |
|---|---|---|---|
| `buy_pct` | 0.50 / 0.50 / 2.50 | **(a)** | base(regime) × mult, clamp [0.3,3.0], cap ±30% |
| `sell_pct` | 1.50 / 1.50 / 2.50 | **(a)** | idem, clamp [0.8,4.0] |
| `idle_reentry_hours` | 8 / 8 / 8 | **(a)** | non scalato (è un tempo), clamp [0.5,**6.0**] ⚠️ vedi sotto |
| `stop_buy_drawdown_pct` | 2 / 2 / 2 | **(b)** | flag `proposed_stop_buy_active=(regime==extreme_fear)`; "Board-only in Sprint 1" documentato in `config_writer.py:8-10` |
| `skim_pct` | 30 / 30 / 30 | (c) | mai considerato come manopola — vedi giudizio sotto |
| `stop_buy_unlock_hours` | 2 / 0 / 1 | (c) | nato in S75b, *dopo* il design S61 — mai rivisitato lo scope Sherpa |
| `dead_zone_hours` | 4 / 2 / 4 | (c) | nato in S74b, idem |
| `capital_allocation` | 200 / 150 / 150 | (c) | vicino al "Level B capital rebalancing" (S61 open item #2), mai assegnato |
| `capital_per_trade` | 50 / 20 / 25 | (c) | **unica esclusione documentata**: S61 "Board-only, Level B dopo 3 manopole proven" |
| `profit_target_pct` | 0 / 0 / 0 | (c) | mai considerato (parametro TF-side) |
| `initial_lots` | 0 / 0 / 0 | (c) | bootstrap one-shot, non tuning |
| `managed_by` | grid ×3 | (c) | è il filtro di selezione, non una manopola |
| *~17 campi infrastrutturali* (id, is_active, cycle, lock, lifecycle…) | — | (c) | stato contabile/lifecycle, fuori scope per qualunque brain |

### Giudizio di merito sui 3 parametri chiesti dal brief

- **`skim_pct` — intrinsecamente statico, non darlo a un brain.** È policy di tesoreria del Board ("no cash morto", 30% a reserve): decide *quanto trattenere*, non *quando vendere*. Modularlo per regime confonderebbe due assi ortogonali. Da formalizzare come Board-only (oggi è solo implicito).
- **`dead_zone_hours` — intrinsecamente statico.** È un anti-rumore di basso livello (soglia anti-flip-flop della ladder): renderlo dinamico introdurrebbe proprio il flip-flop che esiste per sopprimere. L'asimmetria attuale (SOL=2, BTC/BONK=4) è gestione manuale caso-per-caso, coerente col tenerlo fuori.
- **`stop_buy_drawdown_pct` — sensato per un brain, ma il dominio è frammentato.** Modulare il circuit breaker per regime ha una tesi trading valida, ed è ciò che Sherpa abbozza col flag. Ma il flag è binario mentre il parametro è un numero, e soprattutto **tre owner non coordinati** agiscono sullo stesso meccanismo: Board (soglia 2%), Sherpa (flag would-have su regime), grid (`stop_buy_unlock_hours` che auto-spegne il blocco: BTC dopo 2h, BONK 1h, SOL mai). Se Sherpa "accendesse" il breaker in extreme_fear, su BTC si auto-spegnerebbe dopo 2h a sua insaputa. Serve un owner unico del dominio circuit-breaker prima di dare la manopola a un brain.
- **Nota collegata — Adaptive Sell Penalty (S98/S99b)**: la penalty anti-slippage è una **costante di codice** (`SLIPPAGE_PENALTY_THRESHOLD_PCT=1.0` in sell_pipeline.py), non in bot_config — confermato. Modula `effective_sell_pct` a runtime partendo dalla base: quando Sherpa scriverà `sell_pct` in LIVE, saranno due modulatori dello stesso campo non coordinati (non in conflitto diretto, ma il design Sherpa non ne è consapevole). Da tenere presente al gate pre-LIVE.

### ⚠️ Gate pre-LIVE: `idle_reentry_hours` 8 vs range di design 0.5–6

Il design S61 prevede idle 0.5–6h (extreme_fear base = 4h); il clamp nel codice rispecchia il design; ma il valore operativo in bot_config è **8**, fuori range. Effetto oggi (DRY_RUN): proposta cronica 5.6 (=8×0.7, il floor del cap domina ogni base) su ogni riga — innocua ma garantisce da sola gran parte del `would_have_changed`=100%. **Effetto in LIVE** (precisato dalla verifica avversariale): al primo tick idle scenderebbe a 5.6, poi a gradini di cap fino alla base del regime in ~2-7 tick (extreme_fear→4.0, neutral→1.0…). Nota: 5.6h>4h è *più* cauto della base extreme_fear, non più aggressivo — il punto non è il segno, è che **Sherpa riporterebbe sistematicamente idle dentro il range di design, annullando la scelta operativa del Board (8)**. Domanda per il Board: l'8 è una scelta consapevole post-S61? Opzioni: (A) alzare il clamp a ≥8; (B) togliere idle dalla whitelist finché non riconciliato; (C) accettare che LIVE riporti idle ai valori di design. Da decidere **prima** di `SHERPA_MODE=live`.

---

## B4 — btc_price null e would_have_changed 100%: nessun bug di Sherpa

### B4.1 `btc_price` — gap di integrazione Sprint 2 (né bug né dead code)

Catena causale verificata: lo slow writer di Sentinel non ha **mai** incluso `btc_price` nell'INSERT ([slow_loop.py:128-133](../bot/sentinel/slow_loop.py); confermato su tutta la git history del file); il fast writer invece lo scrive (`sentinel/main.py:162`). Lo Sprint 2 (commit `3ba1132`, 22 mag 20:26) ha cambiato la sorgente di Sherpa da fast a slow → da quel momento Sherpa copia un null. Conferma DB chirurgica: 22 mag = 342/441 righe null (switch a metà giornata), dal 23 mag 100% null; le 173 righe slow di Sentinel sono null da sempre.

**Impatto basso**: `symbol_price` è popolato al 100% (fetch diretto Binance) e per BTC/USDT coincide con btc_price; per SOL/BONK il replay può ricostruire il prezzo BTC al timestamp dai klines. Coerenza di design: senza fast loop, Sherpa non usa più il prezzo BTC intra-ora — il campo è solo forensics.

**Fix raccomandato (brief separato, ~3 righe)**: fetch diretto del prezzo BTC in Sherpa quando la riga slow non lo porta (stesso pattern di symbol_price) — zero impatto su Sentinel. L'alternativa (fix nello slow writer) tocca Sentinel, off-limits per questo brief.

### B4.2 `would_have_changed`=100% — artefatto DRY_RUN, il comparatore funziona

`is_changed` (tol 0.01) è corretto. Il 100% (50.405/50.405 righe alla data dell'analisi) è **divergenza cronica indotta dal cap in DRY_RUN**: la config non viene mai scritta, quindi current resta statico e il cap ±30% non gli lascia mai raggiungere il target. Decomposizione (verifica avversariale): **buy_pct è il driver dominante (~98% delle righe)** — current 0.5 non raggiunge mai il target di regime in un tick; idle 8 vs floor 5.6 contribuisce (~84%); sell varia per regime. Non è un bug: è la fotografia di un sistema in cui il "current" è congelato per definizione del DRY_RUN. Il flag diventerà informativo solo in LIVE (dove current insegue proposed) — oppure ridefinendolo rispetto alla proposta precedente, che è esattamente ciò che il gate S102 ora traccia.

Raccomandazione collaterale: persistere QUALI parametri risultano changed (`changed_params` è già calcolato ma non salvato) per distinguere un cambio reale buy/sell da un artefatto idle.

### B4.3 Volume — vedi sezione A (timeline 3 fasi + fix shippato)

Nota schema: `sherpa_proposals` non ha una colonna `raw_signals` — il breakdown auditabile (regime/base/mult/clamp/cap) che il docstring di `parameter_rules.py` promette **non viene persistito**. Senza, dai dati grezzi non si distingue TARGET da PRIMA PROPOSTA. Raccomandazione: 1 colonna jsonb (migration piccola) in un brief futuro, oppure accettare la ricostruzione via codice come fatto qui.

---

## B5 — Regime stickiness dal barometro NewsKeeper v2: fattibile, non ora

**Punto di innesto ideale già esistente**: `calculate_parameters` è una funzione pura `(regime, current, mult) → (final, breakdown)` — lo stesso pattern con cui Sprint 2 ha aggiunto il volatility multiplier. Un 4° parametro keyword `regime_confidence: float = 1.0` con default neutro lascia l'output bit-identico: verificati tutti e 10 i call-site nei test (8 in test_sherpa_amplitude_cap + 2 in test_sherpa_slow_loop_gate), tutti keyword-only. Vincoli: non chiamarlo `fast_signals` (un test asserisce la sua assenza) e default che non altera l'output.

**Dati già pronti**: `newskeeper_regime` (S100) espone `state` (bear/neutral/bull), `net_score` ∈ [−1,+1] (proxy naturale di confidence), `abstain_frac` (salute), `btc_price_at_flip`. **Nessuna colonna nuova necessaria**: lo scalar confidence si deriva on-read.

**Tre opzioni valutate** (dettaglio nei file di sessione):
- **(a)** `stickiness_reader.py` nuovo (clone strutturale di regime_reader, contratto never-raise → fallback confidence=1.0) — fornisce lo scalar, da solo non fa nulla;
- **(b)** interpolazione BASE_TABLE tra regimi pesata per confidence — la più espressiva ma introduce **doppia fonte di verità sul regime** (~12-16 ore, 5-6 file);
- **(c)** confidence modula solo `MAX_DELTA_PCT` (sticky=cap pieno 0.30, divergente=cap ridotto) — Sentinel resta l'unico a decidere la *destinazione*, il barometro modula la *velocità* di marcia.

**Raccomandazione: (a)+(c), ~5-7 ore, 4 file, zero migration, zero rotture test.** L'opzione (b) eventualmente come fase 2.

**Strawman matrice 5×3** (policy da ratificare in Board, NON derivabile dai dati):

| Sentinel ↓ \ Barometro → | 🐻 bear | ⚖️ neutral | 🐂 bull |
|---|---|---|---|
| extreme_fear | sticky 1.0 | tiepido 0.6 | divergente 0.3 |
| fear | sticky 1.0 | tiepido 0.7 | divergente 0.4 |
| neutral | tiepido 0.7 | sticky 1.0 | tiepido 0.7 |
| greed | divergente 0.4 | tiepido 0.7 | sticky 1.0 |
| extreme_greed | divergente 0.3 | tiepido 0.6 | sticky 1.0 |

**Paletti (condivisi dal CEO nel brief §7)**: (1) non costruire prima del verdetto barometro T+14 (~23 giu) **e** di almeno un regime non-bear osservato — oggi il segnale di divergenza, che è l'intero valore dell'innesto, non è mai esistito nei dati; (2) definire `STALE_REGIME_S` (barometro heartbeat 6h vs Sherpa 120s; proposta 12-18h → oltre, confidence=1.0); (3) **anti-circolarità**: se in Phase C il barometro entrasse anche in Sentinel, l'innesto diretto in Sherpa creerebbe un loop — va deciso a priori che il barometro entra in UNO dei due.

---

## Decisions (decision log di sessione)

1. **DECISIONE**: Parte A come correzione del filtro esistente (flip-based), non filtro nuovo. **RAZIONALE**: il brief partiva da premessa superata (filtro 79c esistente); root cause = pass-through a livello. **ALTERNATIVE**: implementare letteralmente il brief (avrebbe duplicato il filtro). **FALLBACK**: revert `a867179`, nessuna migration.
2. **DECISIONE** (Max, D1): heartbeat 4h → 18 righe/gg, accettando di non rispettare il "<10" letterale. **RAZIONALE**: allineato alla cadenza slow-loop; 8h dimezzerebbe il liveness monitoring per un numero tondo. **FALLBACK**: costante `SHERPA_HEARTBEAT_S`, 1 riga.
3. **DECISIONE** (Max, D2): log skip come contatore nell'heartbeat, non per-skip. **RAZIONALE**: stessa informazione, 18 righe log/gg invece di ~2.000.
4. **DECISIONE** (Max, D3): cooldown nel gate come flip (il brief non lo citava). **RAZIONALE**: traccia apertura/chiusura delle finestre override Board a costo 2 righe.
5. **DECISIONE** (Max): restart Mac Mini rimandato → restart unico post-review Board. **CONSEGUENZA**: il volume resta ~2.100/gg fino al deploy.

## Raccomandazioni consolidate per il Board (nessuna implementata, come da brief §7)

1. **Pre-LIVE gate — idle 8 vs clamp 6** (B3): decidere A/B/C prima di `SHERPA_MODE=live`. È anche il modo per rendere di nuovo informativo `would_have_changed`.
2. **btc_price** (B4): brief micro (~3 righe) fetch diretto in Sherpa — o accettare il fallback klines.
3. **Owner unico del circuit breaker** (B3): soglia (Board) + flag regime (Sherpa) + auto-unlock (grid) oggi non si parlano.
4. **Persistere il breakdown** (B1/B4): colonna `raw_signals` su sherpa_proposals per audit TARGET-vs-PROPOSTA, oppure accettare la ricostruzione via codice.
5. **Formalizzare skim/dead_zone come Board-only** (B3) e rivisitare lo scope Sherpa ogni volta che nasce un parametro grid nuovo (dead_zone S74b e stop_buy_unlock S75b sono entrati senza assegnazione di owner).
6. **B5**: tenere la firma estendibile (gratis), costruire l'innesto solo post-verdetto barometro + primo regime non-bear; ratificare la matrice 5×3 come policy.
7. **Cosmetico**: docstring stale `bot/sherpa/__init__.py:10` (`delta(fast_signals)`) da allineare allo Sprint 2.

## Limiti dell'indagine

- Greed/extreme_greed e l'intera colonna bull della matrice B5 non hanno **alcun dato live**: mercato solo-bear dall'inizio di Sherpa. Le righe relative sono ricalcolo dal codice, non osservazione.
- I multiplier nelle tabelle B1 sono lo snapshot dell'11 giugno; i valori storici in DB usavano multiplier dell'epoca (la riconciliazione empirica è stata fatta dove possibile: BTC carattere-per-carattere; SOL/BONK spiegati con current/multiplier storici).
- Parte A verificata da 10 unit test + suite 195/195; la verifica del volume live (≤ ~20 righe/gg) richiede il restart, rimandato per decisione Max.
