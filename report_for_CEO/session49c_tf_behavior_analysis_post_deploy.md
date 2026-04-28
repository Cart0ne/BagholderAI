# Session 49c — TF Behavior Analysis post 49a/49b deploy

**From:** Intern (Claude Code) → CEO
**Date:** 2026-04-28
**Window analizzata:** 27/04 20:00 UTC → 28/04 16:00 UTC (~20 ore live post-deploy)
**Predecessori:** brief 49a + 49b, deployati 27/04 sera

---

## TL;DR (3 righe)

1. **45g sta funzionando** ma il campione è minuscolo: 3 trigger live in 20h, di cui 2/3 via `proactive_tick` (il fix di 49b era necessario).
2. **Non vale la pena alzare il default globale a 4 ora** — 4 closed periods post-deploy non bastano per replicare il backtest, e il singolo dato pulito (LUNC) suggerisce che il 45f potrebbe già fare il lavoro meglio.
3. **Ho trovato 2 problemi che meritano un brief 49d**: (a) doppio trigger 45g sullo stesso period dopo riallocazione, (b) stop_reason inconsistente tra post_sell e proactive_tick.

---

## 1. Stato attuale (snapshot 28/04 16:00)

**Default globale `trend_config`:**
- `tf_exit_after_n_enabled` = TRUE (kill-switch on)
- `tf_exit_after_n_positive_sells` = **0** (regola disattivata system-wide → solo coin con override esplicito sono protette)

**Coin TF attive in questo momento:**

| Symbol | Override N | Capital | Allocated_at |
|---|---|---|---|
| PENGU/USDT | **7** | $53.37 | 28/04 15:47 |
| LUMIA/USDT | **4** | $17.72 | 28/04 15:17 |

⚠️ Discrepanza con brief 49c: il brief diceva "PENGU=10, LUMIA=10". Ora trovo PENGU=7 e LUMIA=4. Probabilmente li ha calibrati Max via dashboard tra brief e deploy.

**Coin TF chiuse 28/04 con override esplicito:**
TURTLE (N=2), SPELL (N=2), LUNC (N=4), ALGO (N=4 — ma è uscita per liquidation, non per 45g).

---

## 2. Risposta alla Domanda A — La regola 45g sta funzionando?

### Eventi `tf_exit_saturated` totali: **3**

| # | UTC | Symbol | N | Override? | Trigger source | Pos sells | PnL period |
|---|---|---|---|---|---|---|---|
| 1 | 2026-04-27 20:07:14 | PENGU | 7 | ✅ | **post_sell** | 7 | +$0.13 |
| 2 | 2026-04-28 02:25:25 | LUNC | 4 | ✅ | **proactive_tick** | 4 | +$1.37 |
| 3 | 2026-04-28 15:17:42 | PENGU | 7 | ✅ | **proactive_tick** | 7 | $0.00 |

### Distribuzione `proactive_tick` vs `post_sell`

- **post_sell**: 1 / 3 (33%)
- **proactive_tick**: 2 / 3 (67%)

**Letta**: il proactive **non** è una safety net rara. È il trigger dominante. Il design originario di 49a (post-sell only) era effettivamente insufficiente — il fix di 49b è stato corretto.

Caveat: il trigger #3 (PENGU del 28/04 15:17) è "patologico" — riallocazione che richiude in 1 secondo (vedi §4 sotto). Se lo escludiamo, il rapporto reale è 1 post_sell + 1 proactive = 50/50.

### Errore fattuale nel brief 49c

Il brief 49c diceva: *"ALGO è uscita correttamente alle 20:59 via 45g `proactive_tick` — primo trigger live in assoluto"*.

**Falso.** Verificato in `bot_events_log`: ALGO il 27/04 sera è uscita via:
- 18:58:40 `bot_stopped` reason=manual
- 18:58:59 `bot_started`
- 18:59:01 `bot_stopped` reason=**liquidation** (TF deallocates, niente 45g)

Il **primo trigger 45g vero** è stato PENGU il 27/04 alle 20:07:14 (`post_sell`, N=7).

---

## 3. Risposta alla Domanda B — Coin protette vs non-protette

PnL realized post-deploy per le 6 coin TF attive nella window:

| Symbol | Override | Pos sells | PnL realized | Tagliata da 45g? |
|---|---|---|---|---|
| LUNC | 4 | 7 | **+$4.80** | ✅ a N=4 |
| PENGU | 7 | 1 | **+$0.13** | ✅ a N=7 |
| LUMIA | 4 | 2 | −$0.12 | ❌ non ha raggiunto N=4 |
| SPELL | 2 | 0 | −$1.13 | ❌ zero pos sells |
| TURTLE | 2 | 0 | −$1.35 | ❌ zero pos sells |
| VANA | NULL | 0 | −$0.68 | ❌ non protetta |

**PnL aggregato post-deploy: +$1.65** (dominato da LUNC +$4.80 da solo).

**Il confronto protette vs non-protette è sostanzialmente impossibile**: solo VANA è "non protetta" → campione di 1, niente statistica. E VANA ha perso $0.68, che è in linea con il pattern delle perdenti.

**Osservazione qualitativa importante**: gli override **molto bassi (N=2)** non sembrano fare nulla di utile. SPELL e TURTLE hanno fatto 0 positive sells: sono uscite in stop loss / lifecycle prima di accumulare 2 sell positive. Il N=2 è "non sparato mai" su coin che vanno male.

---

## 4. Risposta alla Domanda C — Backtest predittivo?

Replica del backtest counterfactual (`scripts/backtest_exit_after_n_post_deploy.py`) sui 4 closed periods post-deploy:

| N | totΔ pre-deploy (28 periods) | totΔ post-deploy (4 periods) | shift |
|---|---|---|---|
| 2 | +$26.73 | −$3.66 | −30.39 |
| 3 | +$31.71 | −$3.51 | −35.22 |
| **4** | **+$35.07** | **−$3.43** | **−38.50** |
| 5 | +$16.68 | −$0.79 | −17.47 |
| 6 | +$17.77 | +$1.54 | −16.23 |
| 7 | +$3.94 | +$1.68 | −2.26 |
| 8 | +$4.58 | $0.00 | −4.58 |

**Il backtest non si replica** su 4 periods. A N=4 (il valore raccomandato nel proposal originario) l'edge passa da **+$35.07 totale → −$3.43**. Segno invertito.

### Ma 4 periods sono troppo pochi

- Solo **1 period su 4** (LUNC) ha avuto positive sells sufficienti per triggerare la regola
- 3 periods (SPELL, VANA, TURTLE) hanno fatto 0 positive sells → la regola non poteva nemmeno simulare un'uscita
- Il backtest pre-deploy aveva 28 periods → 7× la numerosità

### Il problema metodologico su LUNC

Il counterfactual usa `GAP_HOURS=24` per separare i periods. LUNC il 28/04 ha avuto 3 cicli entry-exit-entry tutti dentro 16h, quindi il backtest li tratta come **un solo period sintetico** con 22 trades e 7 pos sells. Ma il period "vero" è stato:
- Ciclo 1: 45g taglia a +$1.37 (live, alle 02:25)
- Ciclo 2: 45f profit_lock a +$2.73 (alle 03:12)
- Ciclo 3: SL a −$1.63 (alle 12:18)

**Il counterfactual confronta cf vs un actual già "trattato" dal 45g + 45f insieme**. Il delta che ne esce non è interpretabile come "edge della regola pura".

### Conclusione

Aspettare almeno 2-3 settimane di dati prima di rifare il confronto. Sui 4 periods attuali, qualunque numero (positivo o negativo) è dominato da LUNC.

---

## 5. Il caso LUNC — quello che davvero conta

Il period LUNC del 27-28/04 è **l'episodio più informativo** della finestra. Va capito bene perché smonta in parte la tesi del 45g.

| Ora UTC | Evento | PnL incrementale |
|---|---|---|
| 27/04 20:29 | tf_allocate, entry @ 0.00006503 | — |
| **28/04 02:25** | **45g** proactive_tick, N=4 | **+$1.37** |
| 02:35 | TF rialloca, entry @ 0.00006686 | — |
| **03:12** | **45f** profit_lock, +5.06% net | **+$2.73** |
| 05:38 | TF rialloca di nuovo, entry @ 0.00006731 | — |
| **12:18** | **stop_loss** −3% | **−$1.63** |

PnL totale del soggiorno LUNC: **+$2.47** (sommando le 3 fasi, lordo).

**Tre safety hanno triggerato in cascata sulla stessa coin**. Tutte hanno fatto il loro lavoro. Ma:
- **45g (regola di 49a) ha preso $1.37** sulla 1° fase
- **Se il 45g non ci fosse stato**, la coin sarebbe rimasta sul ciclo originario, e con buona probabilità sarebbe arrivata fino al 45f (+$2.73) oppure SL (−$1.63), quindi tra +$2.73 e −$1.63
- **Il 45f ha pagato meglio del 45g** sul singolo trigger ($2.73 > $1.37)

**Implicazione**: 45g e 45f sono **redundant safeties** che possono interferire. Il 45g taglia "presto" (a N pos sells), il 45f tira "lungo" (al 5% net). Sul caso LUNC, tirare lungo ha pagato meglio.

⚠️ Questo NON significa che il 45g sia sbagliato — significa che l'edge atteso dipende dalla **distribuzione delle coin**: il backtest pre-deploy includeva coin "MOVR-like" che regalavano 4 pos sells e poi seppellivano (lì il 45g salva). LUNC non era così.

---

## 6. Raccomandazione operativa

### **Mantenere il default globale a 0** per ora

Motivi:
1. Il backtest pre-deploy non si replica sui dati live (campione minuscolo, ma il segno è almeno discordante)
2. L'unico caso pulito (LUNC) suggerisce che il 45f sarebbe stato più redditizio del 45g
3. Override "aggressivi" (N=2) sembrano inutili — nessuna coin con N=2 ha mai triggerato

### **Continuare con override per-coin** dove ha senso

PENGU N=7 e LUMIA N=4 sono override "mirati" su coin specifiche. Possono restare. Ma **eviterei N=2** d'ora in poi: troppo basso per essere utile.

### **Aspettare almeno 2 settimane** di dati prima di rifare il backtest

Target: ~20+ closed periods post-deploy. A quel punto la replica è statisticamente significativa.

---

## 7. Problemi trovati che meritano un brief 49d

### 7.1 Doppio trigger 45g sullo stesso period

**Cosa**: PENGU il 27/04 esce 20:07 via 45g (post_sell). Il 28/04 alle 15:17 il TF rialloca PENGU (`tf_allocate update=true`), `bot_started` alle 15:17:41, e **alle 15:17:42 (1 secondo dopo)** il proactive_tick rifire 45g.

**Perché**: il `period_started_at` è ancora **27/04 06:25** (non resettato dalla riallocazione). Il counter di pos sells è ancora 7 da 19h prima. Il proactive vede `counter >= override` al primo tick e spara.

**Effetto**: il TF rialloca → 45g chiude in 1 secondo → il TF ritenta tra 30 minuti → finalmente parte. Spreco di 1 ciclo allocate-deallocate, niente impatto P&L (residual_holdings=0).

**Decisione di policy** che il CEO deve prendere:
- (A) Lasciare così — il 45g blocca correttamente la coin "satura"
- (B) Reset del counter al `tf_allocate update=true` — la coin ottiene una "seconda chance" pulita
- (C) Cooldown post-45g sul TF — la coin esce dalla pool per N ore dopo un trigger

### 7.2 Stop reason inconsistente

- 45g via `post_sell` → `bot_stopped` reason=**`gain_saturation`**
- 45g via `proactive_tick` → `bot_stopped` reason=**`liquidation`**

Probabilmente i due flow non passano dallo stesso codepath di shutdown. Da uniformare per non sporcare reporting/dashboard.

### 7.3 Interazione 45g + 45f

LUNC ha mostrato che il 45g e il 45f possono triggerare in cascata sulla stessa coin in sequenza. Domanda di design: il 45g dovrebbe **deferire** al 45f quando il net_pnl è già vicino alla soglia profit_lock? Oppure restano due safety indipendenti?

---

## 8. Domande aperte per il CEO

1. **Approva l'attesa di 2 settimane** prima di valutare il default globale, o vuoi alzarlo a 4 lo stesso (decisione "per fede" sul backtest pre-deploy)?
2. **Vuoi un brief 49d** per i 3 punti del §7? (Doppio trigger + stop_reason + interazione 45g/45f)
3. **Override N=2 su SPELL/TURTLE**: li teniamo per altre coin future o smettiamo di usarli?
4. **PENGU N=7 troppo alto?** Dopo il deploy ha triggerato due volte ma sempre in territorio neutrale ($0.13 e $0). Vale la pena abbassarlo a 5? (Decisione tua, non implementabile dall'intern.)

---

## 9. Output di questa sessione

- Report: `report_for_CEO/session49c_tf_behavior_analysis_post_deploy.md` (questo file)
- Script di replica backtest: `scripts/backtest_exit_after_n_post_deploy.py`
- CSV dati: `scripts/output/exit_after_n_post_deploy_summary.csv`
- **Niente modifiche al codice di produzione** (rispettato il vincolo del brief).

🏳️ Bandiera bianca.
