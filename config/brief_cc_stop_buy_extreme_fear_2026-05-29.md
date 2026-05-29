# Brief CC — Fix stop_buy irraggiungibile (gap regime "extreme_fear") + verifica overlay admin

**Base**: PROJECT_STATE.md @ 2026-05-28 (runtime commit `673c941`, post S90). *Confermare con Max il numero di sessione corrente per il tracking/filename.*
**Origine**: Seconda Brain Analysis Sherpa (2026-05-29) — analisi dati DRY_RUN 22→29 mag + finestra crash 15→23 mag.
**Stima**: piccolo (mapping fix) + indagine (overlay). Probabile ~1h. Piano prima del codice (vedi sotto).

---

## Contesto / causa radice

Il loop **slow** di Sentinel calcola `regime` (salvato in `sentinel_scores.raw_signals->>'regime'`) dal Fear & Greed con soglie proprie, ma **non emette MAI "extreme_fear"**, nemmeno quando `fng_label = "Extreme Fear"` / `fng_value <= 25`.

Evidenza (query Supabase, finestra osservazione + crash):
- 19 mag: `fng_value` 25, `fng_label` "Extreme Fear" → `regime` = **"fear"**.
- 22→29 mag: **22 cicli slow su 43** erano "Extreme Fear" (fng 22–25); `regime` = "fear" nel **100%** dei casi. Mai "extreme_fear".

**Doppia conseguenza, stessa radice:**
- **(A)** Sherpa arma `proposed_stop_buy_active` solo se `regime == "extreme_fear"` (decisione S81). Risultato: stop_buy **mai scattato** (0 righe in `sherpa_proposals` su tutta la finestra) nonostante giorni di panico estremo → **freno di sicurezza morto**.
- **(B)** L'overlay regime sui grafici admin (S86b, `drawRegimeBands`) ha già il colore per extreme_fear in palette, ma non lo dipinge mai perché quel valore non arriva.

---

## Decisioni delegate a CC

1. **Fix alla radice in Sentinel** (preferito). Nel punto in cui il loop slow mappa F&G → regime (individuare il file: probabile `bot/sentinel/regime_analyzer.py` o `score_engine.py`), aggiungere il bucket **"extreme_fear"**.
   - Chiave consigliata: `fng_label == "Extreme Fear"` (classificazione autoritativa di alternative.me, già presente in `raw_signals` e `decision_log`), invece di una soglia numerica hardcoded. In subordine: `fng_value <= 25` (dati: extreme 22–25, fear 28–34 → gap netto).
   - Perché alla radice: sistema **sia (A) che (B)** in un colpo, senza toccare né la logica stop_buy né l'overlay.
2. **Verificare l'overlay admin**: confermare che `drawRegimeBands` (admin.html, raw Canvas 2D, le 3 render functions di S86b) legga lo **stesso** campo `regime` e gestisca il valore "extreme_fear" (colore già definito). Se legge un campo diverso o manca il `case`, allinearlo.
3. Aggiornare `PROJECT_STATE.md` §10 a fine sessione (regola di casa).

---

## Decisioni che CC DEVE chiedere a Max (non decidere da solo)

1. **Backfill storico sì/no.** Le righe storiche di `sentinel_scores` hanno `regime: "fear"` cristallizzato nel jsonb anche quando F&G era extreme. Il fix vale solo **in avanti**: l'overlay mostrerà extreme_fear solo sui dati nuovi.
   - **(a)** Solo fix-forward (zero migrazione dati). *Raccomandata dal CEO*: operativamente conta solo il futuro.
   - **(b)** UPDATE una-tantum sulle righe storiche dove `fng_label = "Extreme Fear"` → regime "extreme_fear", per grafici storici corretti. Più lavoro, tocca dati storici. Solo se Max vuole i grafici storici puliti.
2. **Restart per applicare il fix.** Sentinel è orchestrator-managed → il fix entra in vigore solo a restart sul Mac Mini. CC **non riavvia in autonomia**: push su main, poi il restart lo coordina Max (procedura revert+pull se crasha).

---

## Output atteso (a fine sessione)

- Sentinel emette `regime = "extreme_fear"` quando F&G è in extreme fear (verifica: primo ciclo slow utile dopo restart).
- Sherpa: `proposed_stop_buy_active` si arma quando `regime == "extreme_fear"` — **verificare che la condizione scatti davvero** (test mirato o primo ciclo extreme_fear utile), non darlo per scontato.
- Overlay admin: dipinge la banda extreme_fear.
- `PROJECT_STATE.md` §10 aggiornato.
- Decisione backfill posta a Max.

---

## Vincoli — cosa NON toccare

- **NON** toccare la logica di tuning parametri di Sherpa (scaling per-coin di buy/sell/idle): **è validata e funzionante** (i 3 fix dello Sprint 2 sono OK — coin-aware, oscillazione domata, cap).
- **NON** toccare il loop **fast** di Sentinel.
- **NON** modificare le soglie degli altri regimi (neutral/fear/greed): aggiungere **solo** il bucket extreme_fear in cima alla scala fear.
- **NON** riavviare l'orchestrator in autonomia (vedi sopra).

---

## Piano prima del codice

C'è una componente di indagine (individuare il file di mapping + verificare la fonte dati dell'overlay). Quindi: **prima un piano breve in italiano** per Max — file toccati, punto esatto della modifica, come verifichi (A) e (B) — da approvare, poi codice.

---

## Roadmap impact

Impatto diretto sulla roadmap pubblica (`web_astro/src/pages/roadmap.astro`): **minimo**, è un bug fix interno → non aggiornare la roadmap in questo brief. La decisione che muoverà la roadmap è quella **parcheggiata** sul timing di Sentinel (Phase B vs accelerare NewsKeeper), da valutare dopo la prima analisi NewsKeeper (lun 1 giugno).
