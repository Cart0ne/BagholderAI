# Nota per il CEO — Abilitare Sherpa su Kraken (dipendenza nascosta di Opzione B)

**Da:** CC (Intern) · **Per:** CEO (via Max) · **Data:** 2026-07-22 (S122)
**Tipo:** proposta di lavoro / gate pre-Fase-2b (SCOPE proposto per il brief: `sherpa-on-kraken`)
**Contesto:** chiusura bundle nodo-5 (`kraken-2b-bundle`, commit `ed1933d`) + config 2b decisa da Max.

---

## TL;DR

La decisione Board **Opzione B (Fase 2b = $100 Sherpa-driven su BTC)** presuppone che Sherpa possa **guidare la riga Kraken**. Oggi il codice **lo impedisce di proposito**: la Fase 1 rese Sherpa *hands-off* su Kraken e rimandò l'accensione a "post-collaudo". Il bundle di oggi ha sistemato la matematica delle fee (che era il pezzo di *sicurezza*), **non** ha acceso Sherpa su Kraken. Quindi "Sherpa guida" **non è pronta**: serve un piccolo ma reale intervento (togliere il filtro + far leggere la volatilità), con test e restart, **prima** della finestra 2b. Questa nota surfacea il gap e propone il lavoro (Strada 1).

## Config 2b già decisa da Max (parte "soldi", Board-only)
- Riga **BTC/USD**, venue=kraken · **allocazione $100** · **$/trade $33,33** (3 lotti tondi) · **skim 30%** (test: verificare che venga contato) · cassa reale sul conto ~$112,10.
- **Sherpa guida, niente freeze** (scelta di Max) → è ciò che richiede il lavoro sotto.

---

## Stato del codice (con prove)

**1. Filtro hands-off esplicito** — [bot/sherpa/main.py:408](../bot/sherpa/main.py#L408):
```python
return [r for r in rows if (r.get("venue") or "binance") != "kraken"]
```
Il commento sopra ([:397-408](../bot/sherpa/main.py#L397)) documenta **due** ragioni dell'hands-off:
- **(a) il floor si azzererebbe** (BOARD_TABLE ha `profit_target=0` in ogni cella). → **RISOLTO dal fee-fix di oggi**: `profit_target=0` ora significa "floor a break-even" (recupera entrambe le fee), non "floor spento". Quindi togliere il filtro **ora è sicuro**. ✅
- **(b) la volatilità è rotta su Kraken.** → **ANCORA APERTA.** ❌

**2. Volatilità rotta su /USD** — [bot/sherpa/volatility.py:51](../bot/sherpa/volatility.py#L51) e [main.py:447](../bot/sherpa/main.py#L447) fanno `symbol.replace("/","")` → `BTC/USD` diventa **`BTCUSD`**, che su Binance **non esiste** (è `BTCUSDT`). Con la riga Kraken, `_fetch_stdev` cadrebbe su 0.0/fallback → Sherpa calcolerebbe i parametri su volatilità degradata = **parametri sbagliati**. È l'item aperto **S117** ("fix sorgente volatilità Sherpa su Kraken").

---

## Proposta — Strada 1 (scope del lavoro)

**a) Rimuovere il filtro venue=kraken** ([main.py:408](../bot/sherpa/main.py#L408)) — ora sicuro grazie al fee-fix di oggi.

**b) Fix mapping binance-symbol per /USD in TUTTO il path Sherpa** (sweep, non una riga sola): volatilità ([volatility.py](../bot/sherpa/volatility.py)) + price fetch ([main.py:447](../bot/sherpa/main.py#L447)). Proposta: mappare **/USD → /USDT** per klines e prezzo (la volatilità di BTC/USDT ≈ BTC/USD; riusa l'infra Binance esistente, **coerente con la decisione S112 "funding-rate resta su Binance, dato pubblico read-only EU-ok"**). Additivo: applicato **solo** ai simboli /USD → il path /USDT resta byte-identico (invariante Binance da inchiodare con test).
- *Alternativa scartata (per ora):* leggere l'OHLC nativo di Kraken — più fedele ma più lavoro e nuova superficie API; il proxy /USDT basta e avanza a questa scala.

**c) Seed della riga** coi valori correnti fear/LOW (buy 1,8 / sell 1,2 / floor 0) così Sherpa ha un punto di partenza finché non riscrive al primo tick.

**Test** (invariante Binance + Sherpa vede la riga Kraken + mapping /USD) + **va live allo stesso restart** della finestra 2b.

---

## Questione strategica da decidere (Board)

La calibrazione di Sherpa è **tarata su fee Binance 0,1%**. Su Kraken (0,8%/lato = 1,6% a giro) tenderebbe a proporre **sell_pct piccoli** in bassa volatilità = **molti trade con tanta fee** (fee-drag). ⚠️ Ogni singolo trade resta **in utile netto** (il trigger fee-buffered di oggi lo garantisce), ma è inefficiente. Opzioni:
- **(A)** accettare per il collaudo e **osservare il dato** prima di aggiungere logica (mia raccomandazione: è un collaudo, il punto è misurare).
- **(B)** aggiungere un **minimo sell_pct Kraken-aware** nella calibrazione Sherpa (più codice, tara da decidere).

Raccomando **(A)** per la 2b, con rivalutazione (B) coi numeri veri se il fee-drag si vede.

---

## Anti-assenso / rischi

- **Invariante Binance**: il fix (b) è additivo (mapping solo su /USD). Ma tocca un file del path Sherpa **live sui 4 grid**: va provato che /USDT resta byte-identico (test dedicato).
- **La riga Kraken entra nel loop Sherpa**: verificare che nessun'altra superficie "binance-only" (report/reconcile/aggregati) la peschi indebitamente — stessa famiglia dei bug cycle-fetch già incontrati (S118/S119).
- **Non è un parto** ma non è nemmeno un flip: è un mini-brief vero (2 fix + sweep + test). L'alternativa (statico-first) evita il codice ma contraddice "Sherpa guida, niente freeze".

## Roadmap impact
Chiude l'item **S117** "fix sorgente volatilità Sherpa su Kraken"; sblocca operativamente **Opzione B**. Nessuna Phase pubblica nuova (è plumbing interno) → probabile nota, non version bump, su `roadmap.ts`.

---

## Decisioni chieste al CEO
1. **OK a Strada 1** come gate pre-2b (Sherpa guida davvero), o si ripiega su **statico-first** (2b parte prima, Sherpa fast-follow)?
2. **Sorgente volatilità** = proxy Binance /USDT (mia proposta) o Kraken OHLC nativo?
3. **Fee-drag**: opzione **(A)** osservare o **(B)** minimo sell_pct Kraken-aware subito?

*Se approvi, il lavoro diventa il brief `sherpa-on-kraken` e lo shippo (codice+test, no restart) come il bundle di oggi. Cita: bundle `kraken-2b-bundle` (`ed1933d`), item S117, decisione Opzione B (BUSINESS_STATE §4 2026-07-21).*
