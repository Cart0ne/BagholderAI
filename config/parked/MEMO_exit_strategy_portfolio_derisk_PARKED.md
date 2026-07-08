# MEMO — Exit Strategy (de-risking di portafoglio) — PARCHEGGIATO

**Data memo:** 2026-07-07
**Stato:** PARCHEGGIATO / DA VALIDARE — **non costruito**
**Fonte:** chat "Exit strategy" del 2026-06-18 (https://claude.ai/chat/fb8392d6-57b2-42dd-bdf4-9a8a6fd79c02)
**Provenienza:** architettura **proposta dal CEO**; Max l'ha ritenuta *necessaria* ma "qualcosa non mi suona"; lasciata **da validare con Sentinel + NewsKeeper**. Non è una decisione chiusa.

---

## Cos'è

Una coperta anti-bear a livello di **PORTAFOGLIO** (non un micro-stop della singola posizione). De-risking graduale guidato da:
- **Drawdown dal massimo storico** (HWM — High Water Mark)
- **Regime Sentinel + NewsKeeper**

Riduce l'esposizione netta **a tranche** quando il portafoglio affonda, uscendo prima dalle posizioni più rischiose; rientra gradualmente quando il regime torna bullish.

> NB: NON è lo stop-loss a scaglioni per-posizione (−3/−6/−10) che si aveva vagamente in memoria. Quella cosa non esiste. Questo è un overlay di portafoglio.

## Soglie (da backtestare, NON definitive)

| Drawdown da HWM | Stato | Azione |
|---|---|---|
| −15% | **Giallo** | Liquida ~30% del portafoglio; escono le posizioni più rischiose (es. DOGE, TF tier 3) |
| −30% | **Arancione** | Liquida un altro ~30%; escono es. ADA, TF tier 1-2; resta il core (ETH) + cash |
| −45% | **Rosso** | Ulteriore riduzione (livello da definire) |

## Rientro (graduale)

- Man mano che Sentinel torna bullish: neutral → rinforzo il core; bullish confermato per 48-72h → esposizione piena.
- **Cooling period** 24-48h tra un rientro e il successivo (anti ping-pong). Riusare il debounce Sentinel già esistente.

## HWM (High Water Mark)

- **Non si resetta** al rientro (stile hedge fund): il drawdown si misura sempre dal picco storico.
- **DUBBIO APERTO:** se l'HWM non si resetta mai, dopo un bear profondo si rischia di restare in regime protettivo per mesi anche mentre il mercato risale chiaramente → da validare col backtest.

## Scope / cosa NON è

- **NON** sostituisce i micro-exit del singolo trade (stop-loss, trailing, take-profit).
- **NON** è un prerequisito del go-live.
- Può partire come regola **MANUALE** (Max legge i numeri, decide) e diventare automatica dopo.
- Skim a scaglioni del 5% e i floor sono parametri da validare.

## Concern di Max (18/06)

> "Qualcosa non mi suona, ma non riesco a identificarlo… è una strategia che ritengo necessaria, ma va verificata anche con Sentinel e NewsKeeper."

## Perché conta ora (collegamento esterno)

È esattamente la **"condizione di deploy / airbag vero"** che Mike Czerwinski ha chiesto nel thread Dev.to del post #13:
> *"What is your deploy condition when the drawdown is real and the regime is not coming back?"*

Questo memo è il **punto di partenza** per la futura sessione di lavoro *"Sentinel/NewsKeeper come trigger di uscita sul grid"*. Da riaprire da qui, non da zero.
