# Brief S99b — sell-ladder-audit — 2026-06-08

**Riferimento:** PROJECT_STATE.md consultato via PK 2026-06-08.
**Contesto:** Analisi dal vivo della giornata di trading 8 giugno 2026. Il Board e il CEO hanno osservato comportamenti divergenti tra BONK e SOL che richiedono verifica e potenziali fix.

---

## Problema osservato

Oggi 8 giugno, nella stessa finestra temporale (13:00–17:00 UTC):

- **BONK** ha venduto 5 lotti in 4 minuti (13:01–13:05 UTC), liquidando l'intera posizione in un burst.
- **SOL** ha venduto 4 lotti spalmati su 15 ore (02:16–17:00 UTC), bloccata dalla sell ladder + dead zone 4h tra una vendita e l'altra, nonostante il prezzo fosse costantemente sopra avg_cost + sell_pct.

Il comportamento divergente non è un bug in sé — è una conseguenza meccanica del rapporto tra sell_pct e volatilità. Ma ha esposto domande aperte sulla coerenza tra codice, dashboard e regole.

---

## Domande che CC DEVE rispondere (investigazione, no codice)

### Q1 — Sell trigger: per-lotto o avg_cost?
Il dashboard dice testualmente: *"PER-LOT TRIGGER: SELLS WHEN PRICE RISES THIS % ABOVE THAT LOT'S BUY PRICE"*.
Ma il campo `reason` dei trade dice: *"1.5% above avg cost $65.05"*.
**Qual è la logica effettivamente implementata?** Se è avg_cost (come sembra dai log), il testo del dashboard è sbagliato e va corretto.

### Q2 — Come viene calcolato NEXT SELL IF nel dashboard?
Per SOL: avg_buy = $65.05, sell_pct = 1.5%, il dashboard mostra NEXT SELL IF ↑ = **$68.40**.
$65.05 × 1.015 = $66.02 — non torna.
**Ipotesi CEO:** il dashboard calcola il prossimo gradino della sell ladder, cioè `_last_sell_price × (1 + sell_pct + fee) / (1 − fee)`. Se l'ultimo sell era a $67.26, il conto torna: $67.26 × 1.015... ≈ $68.27 + fee ≈ $68.40. **Confermare o correggere.**

### Q3 — Config change SOL alle 11:24 UTC
L'evento `config_changed_bot_config` dice "1 field(s)" senza specificare quale.
Le prime 2 vendite SOL avevano reason "1.0% above avg cost", la terza "1.5%".
**Confermare:** è stato sell_pct da 1.0% a 1.5%? Chi/cosa lo ha modificato (Sherpa? Manuale? Hot-reload)?

### Q4 — Adaptive Sell Penalty: trigger su perdita o su slippage?
Dal codice `sell_pipeline.py`, il trigger è:
```
if price < avg → penalty = (avg − price) / avg × 100
if price >= avg → penalty = 0
```
Oggi BONK ha avuto slippage −3.45% / −4.08% su vendite PROFITTEVOLI (fill > avg) → penalty resettata ogni volta → nessuna protezione anti-slippage sulle sell 2–5.
**Confermare che questa è la logica intesa.** Vedi sezione "Proposta Board" sotto per l'evoluzione richiesta.

---

## Decisioni delegate a CC

Nessuna in questa fase. Questo brief è investigativo: CC risponde alle 4 domande sopra, poi il CEO e il Board decidono i prossimi passi.

## Decisioni che CC DEVE chiedere

- Qualsiasi modifica alla sell ladder, dead zone, o Adaptive Sell Penalty richiede Board approval prima del commit.
- Se Q1 rivela che il dashboard è sbagliato: CC propone la correzione testuale, non la applica.

---

## Proposta Board — Evoluzione anti-slippage (discussione, NON da implementare ora)

Il Board propone un'evoluzione della Adaptive Sell Penalty:

**Regola attuale:** penalty si attiva solo su vendita in perdita (fill < avg), si resetta su vendita in profitto.

**Regola proposta:** il reset su vendita in profitto resta corretto. MA se la vendita successiva ha di nuovo slippage significativo (fill profittevole ma slippage sopra una soglia), la penalty si riattiva basata sullo slippage osservato.

**Auto-obiezione CEO:** su testnet BONK lo slippage è strutturale (3–4% ogni volta, order book sottile). Se la penalty si riattiva su slippage anche in caso di profitto, BONK rischia di congelare di nuovo — lo stesso deadlock che il Board ha corretto in S98 passando da cumulativo a ultima perdita. Possibile mitigazione: soglia minima di slippage sotto la quale la penalty non si attiva (es. 1%), così su mainnet con slippage fisiologico 0.1–0.3% non scatta, ma su testnet col 3–4% sì. Questo però significherebbe che su testnet BONK sarebbe sempre penalizzato, il che potrebbe essere il comportamento desiderato ("se l'order book è sempre sottile, vendi meno aggressivamente") ma va validato.

**Status:** da discutere in sessione successiva con dati dalle risposte Q1–Q4.

---

## Roadmap impact

- Nessuno immediato — brief investigativo.
- Se Q1 conferma che il dashboard è incoerente, è un fix pre-mainnet (già tracciato in Phase 9 V&C: "dashboard coherence S74b ✅" — ma evidentemente non copriva questo aspetto).
- Se l'evoluzione anti-slippage viene approvata, diventa un nuovo brief operativo (S99b+1 o sessione successiva).

---

## Output atteso da CC

Un report in italiano leggibile da Max, con:
1. Risposta a Q1–Q4 con riferimenti precisi al codice (file + riga)
2. Se Q1 rivela incoerenza: testo corretto proposto per il dashboard
3. Dettaglio del config change Q3 (fonte: git log, Supabase audit, o Sherpa log)

**Naming del report:** `2026-06-08_S99b_report_sell-ladder-audit.md`
