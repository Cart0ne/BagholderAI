Brief S102 — sherpa-coherence-audit — 2026-06-11

# Brief d'implementazione — Sherpa Coherence Audit + Write Guard

**SCOPE canonico:** `sherpa-coherence-audit`
**Basato su:** PROJECT_STATE.md al 2026-06-10; BUSINESS_STATE §6-§7; dati Supabase `sherpa_proposals` (50.303 righe al 2026-06-11); design spec `sentinel_sherpa_design_v1.md` (S61); report `2026-06-09_S100_RforCEO_newskeeper-t7-quality-review.md`.
**Stima:** > 1h → CC produce PRIMA un piano in italiano per Max, e attende approvazione prima di scrivere codice. Nessun time-box: la Parte B è un'indagine completa, prendi il tempo che serve.

---

## 0. Cosa stiamo facendo, in una riga

**Parte A:** fix meccanico write-on-change per `sherpa_proposals`. **Parte B:** audit completo del codice Sherpa per produrre una mappa esaustiva di cosa fa, cosa non fa, e se è pronto per essere attivato.

## 1. Contesto e motivazione

Sherpa è in DRY_RUN dal Sprint 2 (S81, coin-aware). Il Board vuole capire esattamente cosa Sherpa farebbe se venisse attivato, prima di decidere se e come accenderlo.

I dati che il CEO ha estratto da Supabase mostrano:

- **50.303 righe** in `sherpa_proposals` dal 6 maggio a oggi
- **~700 proposte/giorno/coin** — una ogni ~2 minuti, praticamente a ogni tick
- `would_have_changed = true` per il 100% delle righe — Sherpa non è MAI d'accordo con la config corrente
- Solo **3 regimi osservati** su 5 possibili: extreme_fear (dal 29 maggio), fear (14-28 maggio), neutral (6-13 maggio)
- **btc_price = null** per tutte le righe recenti (campo non popolato)
- Sherpa propone modifiche solo a **4 parametri su 12+** presenti in `bot_config`

Il Board ha 4 domande specifiche + 1 fix meccanico.

---

## 2. PARTE A — Write-on-change guard (task autonomo, implementabile)

### Problema

Sherpa scrive una riga per coin a ogni tick (~2 min), anche quando la proposta è identica alla precedente. Risultato: 50K+ righe di cui il 99%+ sono duplicati. Le altre brain (Sentinel, NewsKeeper) già fanno write-on-change.

### Specifica

- Sherpa scrive in `sherpa_proposals` SOLO quando la proposta per quel coin è **diversa** dall'ultima proposta scritta per lo stesso coin (confronto su: `proposed_regime`, `proposed_buy_pct`, `proposed_sell_pct`, `proposed_idle_reentry_hours`, `proposed_stop_buy_active`)
- Aggiungere un **heartbeat** periodico (es. ogni 4h come Sentinel slow loop) che scrive anche se non è cambiato nulla, per confermare "sono vivo, il regime non è cambiato"
- Loggare in console quando una proposta viene skippata per write-on-change ("Sherpa: proposal unchanged for BTC/USDT, skipping write")

### Test

- Verifica che dopo il fix, Sherpa scriva significativamente meno righe (atteso: <10 righe/giorno in mercato stabile, vs le attuali ~2100)
- Verifica che il heartbeat funzioni (una riga ogni 4h anche senza cambi)
- Regressione: Sherpa continua a proporre correttamente quando il regime cambia

### Note

- Le righe storiche NON vanno cancellate (servono per l'analisi Parte B)
- Nessun restart richiesto per questo fix se Sherpa standalone — verificare con Max

---

## 3. PARTE B — Indagine Sherpa completa (read-only, produce un documento)

Questa parte NON produce codice. CC legge il codice Sherpa attuale, lo confronta con il design spec originale (S61) e i dati Supabase, e produce un report con le seguenti 5 sezioni.

### B1 — Mappa completa regime → parametri (dal CODICE, non dal design spec)

Produrre una tabella che per OGNI regime (tutti e 5: extreme_fear, fear, neutral, greed, extreme_greed) e per OGNI coin (BTC, SOL, BONK) mostri:

| Regime | Coin | buy_pct proposto | sell_pct proposto | idle_hours proposto | stop_buy | note |
|---|---|---|---|---|---|---|

I valori devono venire dal codice (`parameter_rules.py` o dove risiede la logica), NON dal design spec S61 (che potrebbe essere divergente dopo Sprint 2).

Se i regimi greed e extreme_greed NON sono implementati nel codice (solo nel design), dichiararlo esplicitamente.

Includere anche la **logica del fast loop** — la tabella di aggiustamento che il design spec S61 prevedeva (BTC ±3%/5% in 1h → adjustments). Questa logica è implementata? Se sì, documentare la tabella completa. Se no, dichiararlo.

### B2 — Coin-agnostic check

**Domanda:** se domani Max aggiunge DOGE/USDT a `bot_config`, Sherpa lo gestisce automaticamente senza modificare il codice di Sherpa?

Verificare:
- Sherpa legge i coin da `bot_config` dinamicamente, o ha una lista hardcoded?
- La volatility scaling (Sprint 2, coin-aware) calcola la volatilità dal mercato per qualunque coin, o ha parametri per-coin hardcoded (es. "BONK ha volatilità X")?
- Cosa succede se un coin in `bot_config` non ha un corrispondente in Sherpa?

Risposta attesa: "sì, è coin-agnostic" oppure "no, serve [elenco modifiche] per ogni coin nuovo".

### B3 — Confronto Sherpa vs Dashboard

Produrre una tabella con TUTTI i parametri in `bot_config`, indicando per ciascuno:

| Parametro bot_config | Valore corrente (BTC / SOL / BONK) | Sherpa lo tocca? | Se sì, come? Se no, perché? |
|---|---|---|---|

Parametri noti in `bot_config`: `buy_pct`, `sell_pct`, `skim_pct`, `idle_reentry_hours`, `stop_buy_drawdown_pct`, `stop_buy_unlock_hours`, `dead_zone_hours`, `capital_allocation`, `capital_per_trade`, `profit_target_pct`, `initial_lots`, `managed_by`.

Per quelli che Sherpa NON tocca: è una scelta di design documentata, oppure è una lacuna? Il design spec S61 dice esplicitamente che `capital_per_trade` è "Board-only, Level B" — gli altri parametri non-toccati hanno un'analoga motivazione, o semplicemente non sono stati considerati?

In particolare: `skim_pct`, `dead_zone_hours`, `stop_buy_drawdown_pct` — ha senso che un brain li gestisca, o sono intrinsecamente statici?

### B4 — Volume di scrittura e campo btc_price

Due sotto-domande:
1. `btc_price` è null per tutte le righe recenti in `sherpa_proposals`. Il campo esiste nello schema. È un bug (dovrebbe essere popolato ma non lo è) o dead code (il campo non è mai stato cablato)?
2. Il flag `would_have_changed` è `true` per il 100% delle righe. Questo è perché in DRY_RUN la config non viene mai aggiornata (quindi il "current" è sempre il default statico e la proposta è sempre diversa), oppure c'è un bug nella logica di confronto?

### B5 — Design: input "regime_stickiness" dal barometro NewsKeeper

Questa è una domanda di design, non di codice attuale. Il Board sta valutando un concetto: usare il barometro NewsKeeper v2 (attualmente in shadow, non cablato) come modulatore della "sicurezza" con cui Sherpa applica i parametri.

L'idea: il barometro dice 🐻/⚖️/🐂 e Sentinel dice il regime attuale (extreme_fear/fear/neutral/greed/extreme_greed). Quando sono allineati (entrambi bear) → il regime è "sticky", Sherpa applica parametri conservativi pieni. Quando divergono (Sentinel dice fear, barometro dice ⚖️ Neutral o 🐂 Bullish) → il regime è "in esaurimento", Sherpa inizia a rilassare i parametri prima che Sentinel confirmi il cambio.

Domanda per CC: il codice attuale di Sherpa ha un punto di innesto dove un input aggiuntivo (es. un campo `regime_confidence` o `regime_stickiness`) potrebbe modulare la proposta? Quanto codice servirebbe per aggiungere questo concetto? NON implementare — solo valutare.

Nota: il barometro v2 è in shadow fino a ~23 giugno. Questo innesto NON va costruito ora. È una valutazione di fattibilità.

---

## 4. Output atteso

1. **Parte A shippata:** codice write-on-change + heartbeat in `sherpa_proposals`, test, commit su main
2. **Parte B in report:** `report_for_CEO/` con SCOPE identico `sherpa-coherence-audit`, che contenga le 5 sezioni B1-B5 con tabelle, codice citato per path, e verdetti chiari

Il report Parte B è il deliverable principale. Parte A è il fix meccanico che va a prescindere.

---

## 5. Vincoli e off-limits

- **NON restartare i bot.** Max fa partire/fermare i processi a mano. CC consegna i comandi, Max li esegue.
- **NON attivare Sherpa** (toglierlo da DRY_RUN). Questo brief è investigativo. L'attivazione è una decisione Board separata.
- **NON modificare** la logica di Sherpa (regime mapping, parametri, scaling). Parte A tocca solo la logica di scrittura. Parte B è read-only.
- **NON toccare** il runtime di trading (grid, tf, sentinel core, newskeeper).
- Push diretto su main per Parte A, come da workflow.
- `source venv/bin/activate` sempre prima di lanciare.

---

## 6. Roadmap impact

**Nessuno.** Parte A è housekeeping (write-on-change, come già fatto per le altre brain). Parte B è un documento informativo per il Board. Nessuna feature nuova, nessun aggiornamento roadmap pubblico.

---

## 7. Anti-assenso CEO

Mi preoccupo che la Parte B, senza time-box, possa allargarsi in un refactoring mentale ("già che ci sono, miglioro anche X"). Il guardrail è: **Parte B produce un REPORT, non codice.** Se CC durante l'indagine trova qualcosa che andrebbe cambiato, lo documenta nel report con una raccomandazione — non lo implementa. Le implementazioni verranno in brief separati dopo che il Board ha letto il report e deciso.

Seconda preoccupazione: la domanda B5 (regime_stickiness) potrebbe essere prematura — il barometro è in shadow e non validato. Ma il Board l'ha chiesta esplicitamente come valutazione di fattibilità, e una risposta "costa N ore e tocca M file" ha valore anche se poi decidiamo di non farlo. Non la taglio.
