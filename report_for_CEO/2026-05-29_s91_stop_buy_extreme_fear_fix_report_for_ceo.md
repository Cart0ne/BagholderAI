# Report CEO — S91 (pomeriggio): fix stop_buy irraggiungibile (gap regime "extreme_fear")

**Data:** 2026-05-29
**Sessione:** S91 (parte pomeriggio; la parte mattina era SEO/A11y. Numerazione confermata da Max: oggi è tutta S91)
**Brief:** `config/brief_cc_stop_buy_extreme_fear_2026-05-29.md` (origine: seconda Brain Analysis Sherpa 2026-05-29)
**Esito:** ✅ SHIPPED + RESTART Mac Mini eseguito + **fix verificato LIVE in produzione**
**Commit:** `ea4c7a8` (fix+test) · `51895f8`/`<docs>` (PROJECT_STATE)
**Restart:** Mac Mini 15:53 CET — PID parent **33218**, runtime `51895f8`

---

## 1. Il problema (in una riga)

Il freno di sicurezza "stop_buy in panico estremo" **non è mai scattato** durante il
crash di maggio, nonostante giorni di Extreme Fear. Causa: Sentinel non emetteva
mai il regime `extreme_fear`, quindi Sherpa non aveva nulla su cui armarsi.

## 2. Causa radice

Il mapping Fear&Greed → regime in Sentinel (`bot/sentinel/regime_analyzer.py`)
usava una soglia numerica hardcoded `F&G ≤ 20 → extreme_fear`. Ma alternative.me
(la fonte) etichetta "Extreme Fear" già da ~25 in giù. Risultato: i valori 21–25,
che la fonte chiama esplicitamente "Extreme Fear", venivano declassati a "fear".

Sui dati: nei **22 cicli slow su 43** in cui F&G era 22–25 (Extreme Fear), il regime
emesso è stato "fear" nel **100% dei casi**. Mai extreme_fear → freno morto.

## 3. Il fix (chirurgico, 1 file, ~8 righe)

Reso il mapping **label-aware**: la classificazione di alternative.me diventa
autoritativa.

```
extreme_fear  ⟸  fng_label == "Extreme Fear"   OPPURE   fng_value ≤ 25
```

- Le soglie degli altri regimi (fear / neutral / greed / extreme_greed) **non toccate**.
- Sherpa **non toccato**: la sua condizione `regime == "extreme_fear"` era già corretta,
  le mancava solo l'input. Tuning Sprint 2 (coin-aware) intatto.
- Overlay admin (bande regime sui chart): **zero codice** — legge già lo stesso campo
  e aveva già colore/alpha per extreme_fear; dipingerà la banda sui dati nuovi.

Un solo punto di modifica risolve sia (A) il freno morto sia (B) l'overlay cieco.

## 4. Verifica LIVE (non solo test)

Il restart è caduto in un momento fortunato: **F&G oggi = 23, "Extreme Fear"** —
esattamente il caso del gap. Prova before/after sulla stessa fonte:

**Sentinel** (`sentinel_scores`, slow loop):

| Ora (UTC) | F&G | Label | Regime emesso |
|---|---|---|---|
| 13:53:25 — **post-restart, codice nuovo** | 23 | Extreme Fear | **`extreme_fear`** (risk 20 / opp 80) |
| 11:28 / 07:26 / 03:24 — codice vecchio | 23 | Extreme Fear | `fear` (risk 30 / opp 65) |

**Sherpa** (`sherpa_proposals`):

| Ora (UTC) | Regime | `proposed_stop_buy_active` |
|---|---|---|
| 13:55:27 — **primo ciclo pieno post-restart** | extreme_fear | **TRUE** (BTC, SOL, BONK) |
| 13:48 e prima | fear | false |

A parità di mercato, il sistema ora vede l'estremo e arma il freno. Prima: 0 righe
con stop_buy su tutta la finestra di crash.

## 5. Caveat di design (importante)

Sherpa gira in **DRY_RUN**. Quindi `proposed_stop_buy_active = true` è una proposta
*would-have* loggata, **non un blocco applicato** al bot (lo stop-buy resta Board-only:
Sherpa propone, non scrive). Cosa cambia davvero da oggi:

1. Il **segnale** di panico estremo è finalmente vivo, corretto e tracciato in DB.
2. L'**overlay admin** mostrerà le bande extreme_fear (contesto visivo per la Brain Analysis).
3. Quando/se passeremo Sherpa a LIVE, il freno avrà la base corretta su cui agire.

Non è un cambio di comportamento di trading oggi — è il ripristino di un sensore rotto.

## 6. Decisioni

- **Backfill storico: NO** (decisione Max). Solo fix-forward, nessuna migrazione dati.
  Le righe storiche di `sentinel_scores` restano con regime="fear" cristallizzato;
  l'overlay mostrerà extreme_fear solo sui dati dal restart in avanti. Operativamente
  conta solo il futuro (raccomandazione CEO confermata).
- **Approccio: label-primary + rete numerica ≤25** (vs solo numerico). Segue la fonte
  autoritativa ed è robusto se alternative.me sposta le bande.

## 7. Stato sistema post-restart

- 7 brain orchestrator-managed up (orchestrator 33218 + 3 Grid + TF + Sentinel + Sherpa),
  caffeinate 33219, log pulito, 2 Telegram "spawned" inviati.
- NewsKeeper standalone (PID 78098) intatto, non toccato dal restart.
- Sherpa resta DRY_RUN, flag Telegram Sentinel/Sherpa silenziati (env invariato).
- Test suite 131/131 verde.

## 8. Roadmap impact

Nessuno sulla roadmap pubblica (bug fix interno) — coerente col brief. La decisione
che muove la roadmap (timing Sentinel Phase B vs accelerare NewsKeeper) resta
parcheggiata, da valutare dopo la prima analisi NewsKeeper (lun 1 giugno).

---

*In attesa del BUSINESS_STATE da modificare (CC non lo tocca di iniziativa).*
