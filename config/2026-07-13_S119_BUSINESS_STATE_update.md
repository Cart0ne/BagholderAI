Aggiornamento BUSINESS_STATE.md — S119 — 2026-07-13
(incolla nelle sezioni indicate; §4 tiene solo le ultime 10-15 voci)

## §4 — Decisioni strategiche recenti (append)

- 2026-07-13 — Fase 2 del cutover Kraken spezzata in 2a (fix bug + ordine-prova reale sorvegliato) e 2b (switch reale sui $100 già sul conto) — perché Kraken non ha testnet: il codice che legge la risposta di un ordine reale non è esercitabile a costo zero, e il bug critico vive proprio lì. La sola certificazione onesta è un ordine reale minimo guardato a mano.
- 2026-07-13 — Sito pubblico resta su `binance` durante test interno e collaudo → venue canonico = binance. Why: rende invisibile il test da $25 e sblocca il fix cycle-fetch venue-aware (senza, il sito salterebbe sulla riga Kraken mostrando "Fresh start" al pubblico).
- 2026-07-13 — Floor (`profit_target_pct`) lasciato a 0 = "non vendere sotto il break-even dopo le fee" (già sicuro, non è "spento"). Trigger del test $25 = 2% manuale (copre il round-trip Kraken 1,6% + cuscino slippage). Sherpa spento sulle righe Kraken durante i test. Why: separare "quando vendere" (trigger) da "mai in perdita" (floor); per i test i parametri sono statici a mano.
- 2026-07-13 — Fix-fee Sherpa 0,1%→0,80% = prerequisito SOLO per il sistema pieno (fase €600), FUORI scope Fase 2a. Why: Sherpa oggi calcola i trigger sulle fee Binance; su Kraken produrrebbe sell_pct sotto il floor → stallo. Nei test manuali Sherpa è spento, quindi non serve subito.
- 2026-07-13 — Staging del collaudo confermato: $25 BTC (meccanica grid) → $100 sequenziale grid-only BTC→SOL→BONK (segnale pulito, una variabile alla volta) → sistema pieno (Sentinel + Sherpa fee-fixed + NewsKeeper wired) SOLO dopo. Why: "tutti i brain insieme" è il passo dopo il collaudo, non il collaudo; accenderli sul primo denaro reale perde il segnale pulito e impila integrazione non testata sul momento di rischio massimo.
- 2026-07-13 — Cuscino slippage dentro `sell_pct` per ora; colonna `slippage_buffer_pct` resta NULL (micro-decisione, rivedibile).

## §3 — Diary status (aggiorna)

- Vol 4 "From Eyes to Live" in corso. Diario S118 scritto (.docx, "The One Where 28 Out of 28 Wasn't Enough"). S119 su Supabase = BUILDING (coda domani: report CC post-implementazione brief + diario S119).

## §5 — Domande aperte per CC (già nel brief 2a, qui per tracciamento)

- Isolamento del processo di test da terminale vs orchestrator (chi "possiede" la riga BTC/USD-Kraken).
- Timeout/retry del poll `fetch_order` e comportamento se il fill non è confermato entro il timeout (ordine in volo).
- Dimensione del primo ordine-prova ($25 vs ~$5 ordermin) = decisione Board.

## Nota drift (correzione a memoria)

- `sell_pct` reale delle righe grid (testnet_2, binance): BTC 1,20% · SOL **1,61%** (memoria diceva 1,43%, errata) · BONK 2,53%. `profit_target_pct` = 0 su tutte le righe (confermato).
