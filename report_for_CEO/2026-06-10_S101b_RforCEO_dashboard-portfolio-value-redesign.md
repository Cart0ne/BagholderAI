# RforCEO — S101b · Dashboard §3 "Portfolio value" redesign + fix MTM −$100

**Data:** 2026-06-10 · **Sorgente:** sessione diretta con Max (nessun brief CEO) · **Commit:** `8ea0a23` (web-only, no bot, no restart, push → deploy Vercel) · **Suffisso b:** la sessione GSC mattutina era già S101; il commit message/commenti dicono "S101" per refuso di numerazione.

## 1. Perché

Max non capiva il grafico "Cumulative P&L · time series" della dashboard pubblica e dubitava della sua utilità. L'analisi ha dato ragione al dubbio due volte:

1. **Era confuso**: due linee che divergevano senza spiegazione (realized + MTM), sottotitolo gergale ("realized + mtm"), asse "+$0" dove zero significava in realtà "tornati ai $600 iniziali", nessun copy per un neofita.
2. **Era proprio sbagliato**: con il TF a 0 trade nel ciclo, `reconstructTFForDay` ritornava `0` invece del budget cash $100 → la linea MTM mostrava **−$102.71** quando il valore vero era **−$2.71** (l'hero, fixato in S97b, era corretto; il chart §3 era rimasto indietro — stessa famiglia di bug).

## 2. Cosa vede ora il pubblico

- **Una sola linea** ("Portfolio vs start", la MTM): la realized resta nelle barre weekly sotto, ognuno col suo mestiere. Razionale brand: la MTM mostra anche le bags aperte; la sola realized le nasconderebbe.
- **Fill semantico**: verde sopra il break-even, clay sotto ("underwater") — i periodi negativi si vedono da soli, in tema trasparenza.
- **Asse in valore di portafoglio**: $600 = break-even (decisione D1 Max), break-even tratteggiato con legenda "the $600 we started with".
- **Big number**: es. "−$2.71 · −0.45% · as of Jun 9" + frase "if we sold everything today · started with $600". Ancorato all'ultimo snapshot `daily_pnl` reale (D2), così numero e fine curva combaciano sempre; il valore live resta nell'hero.
- **Tooltip onesto**: "$597.29 · −$2.71 (−0.45%)", con suffisso "est." sui giorni senza snapshot (prima il fallback su realized era silenzioso).
- **Sticker "Fresh start · Jun 4"** replicato (prop `mirrored`, scala 0.8) sull'angolo alto-destro di entrambe le card §3: uno screenshot del singolo grafico si porta dietro il contesto testnet/reset.
- Fix minore: etichette settimane delle barre corrette ("May 31" → "Jun 1"; bug timezone in `weekKey`).

## 3. Scoperta — snapshot daily_pnl day-1 sottostimato (serve brief)

Verificato su DB: `total_value` 5-giu = **350.63** e 6-giu = **476.72**, ma a fine 5-giu il grid aveva net invested **$496.53** (18 trade) con realized **+$0.18** — nessuna perdita reale; e il 6-giu "recupera" +$126 con realized −$6.30, impossibile come mercato. La curva mostra quindi un dip day-1 in parte finto (≈ −$150 → ora ben visibile con la linea singola).

**Pista**: lo snapshot è scritto dal PRIMO grid bot che arriva al blocco delle 20:00 (`db/client.py:306`, `ignore_duplicates=True`, mai più aggiornato); al day-1 post-reset valutava un portafoglio parziale (sospetto: holdings di una coin a prezzo mancante, taglia compatibile con una board da ~$165). Ricorre a ogni reset mensile testnet.

**Raccomandazione**: brief bot-side per (a) hardening del calcolo snapshot day-1, (b) eventuale correzione delle righe 5-6 giu con valori ricostruiti dai trade, (c) valutare se spostare/aggiornare lo snapshot oltre le 20:00. Nessun dato DB è stato toccato in questa sessione.

## 4. Fase 2 (candidate, non urgenti)

- **Snapshot TF server-side in `daily_pnl`**: elimina la ricostruzione client (~5% di margine dichiarato) e il fallback silenzioso.
- **Benchmark BTC buy-and-hold** sulla card: rimandato finché la linea singola non si è dimostrata leggibile (evitare di rimettere 2 linee subito).

## 5. Note di chiusura

- Il commit `8ea0a23` include anche la **chiusura docs della S101-GSC** (header/§4/§10 di PROJECT_STATE + `SEO_RULES.md`) trovata in staging e mai committata da quella sessione. Contenuto verificato: nessun dato sensibile. S101-GSC resta **senza report RforCEO** (gap da sanare se ritenuto utile).
- **Niente pull a inizio sessione** (Mac Mini irraggiungibile, ok Max): nessuna divergenza emersa, push fast-forward pulito. Repo runtime Mac Mini da allineare al prossimo sync (irrilevante per il sito: deploy via GitHub → Vercel).
- Verifica: build Astro 19 pagine ok, preview locale con dati live Supabase (big number, asse, fill, sticker, range 1M/3M/ALL), console browser pulita.
