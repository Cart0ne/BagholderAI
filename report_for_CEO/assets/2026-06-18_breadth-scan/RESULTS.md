# Breadth analysis — quick pass (2026-06-18)

**Fonte:** `trend_scans` (TF scanner su Binance **testnet**), 16.350 righe,
327 scan, finestra **2026-06-11 → 2026-06-18** (~7 giorni, retention 14gg).
**Metodo:** conteggio segnali `BULLISH` per volume-tier (A=T1 blue, B=T2 mid,
C=T3 small) per scan, aggregato per giorno. Script: `breadth_analysis.py`.
**Read-only**: zero scritture DB, zero modifiche bot.

## Tabella giornaliera (media bullish / media coin per scan)

| Giorno | Scan | T1 (blue) | T2 (mid) | T3 (small) | BTC~ | Note T3 |
|--------|-----:|----------:|---------:|-----------:|-----:|---------|
| 06-11 | 16 | 0.0/0.0 | 0.0/3.0 | 6.9/47.0 | 63194 | max 7 |
| 06-12 | 47 | 0.0/0.0 | 0.0/3.0 | 6.6/47.0 | 63570 | max 9 |
| 06-13 | 48 | 0.0/0.0 | 0.0/2.1 | 7.3/47.9 | 63956 | max 9 |
| 06-14 | 46 | 0.0/0.0 | 0.1/1.4 | 6.2/48.6 | 64408 | max 9 |
| 06-15 | 47 | 0.0/0.0 | 0.6/3.3 | **8.8**/46.7 | 66198 | max 13 |
| 06-16 | 43 | 0.0/0.0 | 1.0/3.5 | **10.7**/46.5 | 66104 | max 15 |
| 06-17 | 47 | 0.0/0.0 | 0.4/2.1 | **11.1**/47.9 | 65237 | max **18** |
| 06-18 | 33 | 0.0/0.0 | 0.0/2.7 | 8.4/47.3 | 64091 | max 12 |

## Findings

1. **Tier 1 (A) è sempre VUOTO** (0 coin ogni scan). Su testnet nessuna coin
   raggiunge la soglia volume tier1 (100M): i volumi testnet sono finti.
   → la classificazione per volume è degenerata su testnet.

2. **~47 coin su ~50 cadono in T3 (C)**, T2 ha 0-3 coin. Quindi su testnet
   "breadth T3" ≈ "breadth complessiva", non un segnale small-cap isolato.

3. **Il pattern di Max è confermato, ma il meccanismo è preciso:** i tier
   *operabili* (T1-T2) sono bullish-morti quasi sempre (lo "0 bullish per
   giorni"), mentre **T3 porta tutta la breadth e ha avuto un'espansione
   15→17 giu (da ~7 a un picco di 18 bullish/scan)** = il "botto di tier 3"
   che lo scanner segnala e che noi **blocchiamo** (tf_tier3_weight=0).

4. **Tempistica vs BTC:** l'espansione T3 ha accompagnato il pop BTC a $66k
   (15 giu) e ha **toccato il picco (16-17 giu) mentre BTC stava già
   ripiegando** (66.2k→65.2k), poi si è sgonfiata il 18 con BTC a 64k. Un
   accenno coerente con l'ipotesi "froth tardiva / contrarian" — ma è **un
   solo episodio su 7 giorni = aneddoto, non prova**.

## Conseguenza per il 23

Il dato testnet **non può** validare l'idea (tier degenerati, universo finto).
Serve calcolare la breadth da **dati mainnet reali** (API pubblica Binance
no-key, stesso metodo dell'analisi volume-PnL S103a) su una finestra più
lunga, e incrociarla con regime Sentinel + barometro. Vedi brief
`config/2026-06-18_brief_tier-breadth-regime-signal.md`.
