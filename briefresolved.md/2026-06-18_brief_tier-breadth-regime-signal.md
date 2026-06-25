# Brief — Tier-breadth come segnale di regime (NewsKeeper → Sentinel)

**Tipo:** proposta CC (analisi-design), da eseguire **insieme al verdetto
barometro del ~23 giugno** — una sola sessione di sintesi con tutti i segnali
sul tavolo.
**Autore:** CC (Intern), 2026-06-18.
**Origine:** idea di Max, pitchata al CEO (nota Apple "BagHolderAI — Todo"):
> *"il fatto che dopo giorni e giorni di scan con 0 bullish, di colpo inizi a
> bloccare un botto di monete tier 3, non è un indice da tenere conto per
> newskeeper → sentinel?"*

**Stato attuale dell'idea:** registrata solo come riga generica e **congelata**
nella master list (`CONGELATO: "Sentinel market breadth da TF scanner — Phase
B/C"`). La framing specifica di Max (l'*anomalia* breadth) non è codificata da
nessuna parte. Questo brief la recupera e la rende falsificabile.

---

## 1. L'ipotesi (in chiaro)

Quando il mercato passa risk-on, l'appetito al rischio "trabocca" nelle
small-cap: un'ondata di coin **tier 3** diventa bullish anche se i blue-chip
(tier 1-2) sono ancora fermi. Questa **espansione di breadth nelle small-cap**
potrebbe essere un segnale di regime utile a Sentinel — **complementare** a:
- Fear & Greed (sentiment esterno, fonte unica),
- barometro NewsKeeper (clima news),
- prezzo BTC (già osservato).

Due sotto-ipotesi, **opposte**, entrambe da testare:
- **(H-conferma)** breadth T3 in salita = risk-on che *anticipa/conferma* il
  rialzo → input pro-ciclico.
- **(H-contrarian)** picco di breadth T3 = *froth tardiva* che precede il
  drawdown (la spazzatura pompa quando il rally è vecchio) → input di cautela.

Il quick pass del 18 giu (vedi §3) dà un accenno debole verso **H-contrarian**
(il picco T3 ha seguito il top BTC), ma su 1 episodio non si conclude nulla.

## 2. Perché NON è già testabile coi nostri dati

Lo scanner gira su **Binance testnet** → `trend_scans` ha:
- volumi finti → **tier 1 sempre vuoto**, **~94% delle coin in tier 3**: la
  separazione per tier è degenerata, "breadth T3" ≈ "breadth totale";
- universo testnet limitato e prezzi/klines potenzialmente sottili/stale per
  le small-cap → il segnale T3 è in buona parte rumore testnet.

**Conclusione:** la breadth va calcolata su **dati mainnet reali**.

## 3. Cosa ha già detto il quick pass (2026-06-18, read-only su testnet)

Finestra 11→18 giu, 327 scan. Dettaglio in
`report_for_CEO/assets/2026-06-18_breadth-scan/` (script + CSV + RESULTS.md).
- Tier 1-2 bullish-morti quasi sempre ("0 bullish per giorni" ✓).
- Tier 3 sempre attivo, con **espansione 15→17 giu (≈7 → picco 18 bullish/
  scan)** = il "botto di tier 3" che lo scanner segnala e che **blocchiamo**
  (`tf_tier3_weight=0`).
- Il picco T3 (16-17 giu) ha **seguito** il top BTC ($66k, 15 giu) → accenno
  contrarian. Aneddoto, non prova.

→ L'osservazione di Max è **reale**. La sua validità come segnale di mercato è
quello che il 23 dobbiamo misurare su dati veri.

## 4. Piano per la sessione del 23 (read-only, zero codice bot, zero DB write)

Stessa disciplina dell'analisi volume-PnL S103a (API pubblica Binance no-key,
asset riproducibili).

**A. Costruire la serie breadth MAINNET**
1. Universo: top ~150-300 USDT pair per volume **reale** (no stablecoin).
2. Per ogni coin, klines 4h → stessi indicatori del nostro classifier
   (EMA20/50, RSI14, ATR14) → stessa regola BULLISH/BEARISH/SIDEWAYS.
3. Tier per **volume reale** (soglie 100M / 20M) → tier 1/2/3 *veri*.
4. Serie giornaliera per tier: frazione bullish, conteggio, e **breadth
   thrust** (Δ giornaliera). Finestra: la più lunga ricostruibile (mesi).

**B. Tenere anche la serie testnet** (`trend_scans`) come "ciò che vede il
bot" — utile per capire quanto il bot è cieco rispetto al mercato vero.

**C. Incrocio con gli altri segnali** (è il punto della sessione unica):
- regime Sentinel (`sentinel_scores`) + Fear & Greed,
- barometro NewsKeeper (`newskeeper_regime`) — il cui verdetto T+14 cade lo
  stesso giorno,
- ritorni forward BTC a 24h / 3g / 7g.

**D. Domande a cui rispondere:**
1. La breadth T3 **anticipa, accompagna o segue** i movimenti di prezzo/regime?
2. È **contrarian** (picchi prima dei drawdown) o pro-ciclica?
3. Aggiunge **informazione oltre** F&G + barometro, o è solo un'eco ritardata
   (ridondante)? — test chiave: regressione/divergenze, non solo correlazione.
4. Esiste una **divergenza utile**? (es. T3 che si accende mentre il regime è
   ancora bear = early risk-on; o T3 al picco mentre BTC fa nuovi massimi =
   alert froth).

## 5. Output decisionale (Board)

Tre esiti possibili, da decidere con tutti i dati (breadth + barometro +
regime) davanti:
- **Promuovi**: la breadth T3 aggiunge segnale → design di come cablarla in
  Sentinel come 4ª lente (probabilmente Phase B). Brief separato.
- **Parcheggia**: segnale debole/ridondante → resta in backlog, ri-test con
  più dati.
- **Boccia**: nessun valore → si chiude (eventuale spunto blog "abbiamo testato
  un'idea, non funzionava").

## 6. Anti-assenso (obiezioni reali, messe in chiaro ora)

- **Ridondanza**: la breadth potrebbe essere solo il riflesso ritardato di
  prezzo/F&G → niente informazione nuova. È l'esito più probabile a priori; il
  test §4.3 deve escluderlo prima di qualunque cablaggio.
- **Overfitting su finestra corta**: anche mainnet, se ricostruiamo pochi mesi
  e il periodo è mono-regime (come il barometro), il verdetto è parziale.
  Dichiararlo, non forzare una conclusione.
- **Costo-beneficio**: Sentinel oggi è semplice e robusto; aggiungere una lente
  va giustificato. Se l'effetto è marginale, il rischio operativo non vale.
- **Doppio uso del classifier**: riusare la nostra regola BULLISH garantisce
  coerenza col bot ma eredita i suoi limiti (EMA20/50 4h); va bene per un test
  esplorativo, non è "la verità" sul regime.

## 7. Vincoli

Read-only assoluto (no scritture Supabase, no touch codice bot/scanner/Sentinel,
no restart). Riusa `breadth_analysis.py`. Asset riproducibili in
`report_for_CEO/assets/`. Nessuna decisione di cablaggio in questa sessione:
solo misura + sintesi → poi il Board decide.
