# Report per CEO — ETH bad-tick / slippage sul buy — 2026-07-22 (S122)

**Tipo:** finding di analisi (APERTO — da analizzare con Max/CEO domani, NON risolto)
**Trigger:** Max, 2026-07-22 — "verifica gli ultimi movimenti di ETH, qualcosa non mi torna"
**Rilevanza:** ⚠️ ALTA per tempistica — emerso **poche ore dopo il go-live 2b a denaro reale su Kraken**.

---

## TL;DR

Il "profitto" recente di ETH (tf_grid, testnet Binance) è **gonfiato da due acquisti eseguiti su tick di prezzo fasulli** del book sottile del testnet. Il bot ha "visto" un prezzo ~$1.575 (mentre ETH stava a ~$1.940), ha fatto scattare il buy trigger, e il market order si è riempito ~$240 più in alto (**+15% di slippage**), accettato **senza rifiuto**. Quel lotto a sconto ha abbassato l'avg e i sell successivi hanno registrato utile — **profitto fabbricato da un glitch di dati**, non da un movimento vero.

Su testnet è innocuo (soldi finti). Ma **non esiste un rifiuto sullo slippage del fill**, e lo spike-guard non ha fermato un tick del −19%: la stessa classe di bug su un book Kraken sottile (**BONK/USD in Fase 3, ~$120K**) sarebbe una **perdita reale**.

---

## Le prove (tabella `trades`, ETH/USDT, cycle testnet_2)

| quando (UTC) | check price | fill | slippage | reason (verbatim, troncato) |
|---|---|---|---|---|
| **2026-07-22 16:40:38** | **$1.575,00** | $1.815,35 | **+15,26%** | "Pct buy: check $1.575,00 dropped 2.0% below last buy $1.938,16 → fill $1.815,35 (slippage +15,26%)" |
| **2026-07-20 17:40:38** (LAST SHOT) | **$1.585,50** | $1.829,47 | **+15,39%** | "LAST SHOT: Pct buy: check $1.585,50 dropped 2.0% below last buy $1.858,08 → fill $1.829,47 (slippage +15,39%) — spent remaining $20.86" |

Contesto prezzo attorno al 16:40: i trade del bot stesso quotavano ETH ~**$1.938** (buy 15:07) e ~**$1.951-1.952** (sell 16:41-16:42). Un "prezzo" di **$1.575** alle 16:40 è un **flash-crash fasullo del ~19%** su book sottile, non un livello reale.

## Meccanismo (catena completa)

1. Il price-check fetcha un tick spurio **~$1.575** (−19% sul riferimento ~$1.938).
2. Essendo sotto il buy trigger (2% sotto last buy = ~$1.899), il buy **scatta**.
3. Il market order si riempie al prezzo "vero" recuperato **~$1.815** → **+15,26% slippage** vs il check.
4. Il bot **accetta** il fill (solo un *warning* post-fill, nessun blocco) e registra il buy a $1.815.
5. Il lotto a sconto abbassa l'avg **$1.938 → $1.872**; i due greed-decay sell a $1.951/$1.952 scattano (prezzo ≥ avg×1,025 = $1.919) e registrano **+$0,61 e +$0,78**.

→ Gran parte dell'utile ETH del 22-lug è questo: **round-trip in profitto nato da un buy su prezzo-fantasma.**

## Perché conta ADESSO (non è solo testnet)

- **Nessun cap di rifiuto sullo slippage del fill.** Solo un warning post-fill (brief 70a Parte 4), non un blocco. Persino il path **LAST SHOT** — che ha `SLIPPAGE_BUFFER_PCT=0.03` — ha accettato **+15,39%**: quel buffer è una guardia sul *prezzo di buy* (non comprare troppo sopra avg), **non** un rifiuto sullo *slippage del fill*.
- **Lo spike-guard (soglia 4%) non ha fermato un tick −19%.** Ipotesi da verificare: (a) il tick basso persiste nel confirm-window → preso per reale; (b) il prezzo che alimenta il buy-trigger bypassa il guard; (c) guard mis-configurato sul path tf_grid.
- **Denaro reale appena acceso su Kraken.** Su **BTC/USD** (book profondo) il rischio è basso: un tick −19% non capita e un market buy non slitta 15%. **Su BONK/USD in Fase 3** (book Kraken sottile ~$120K, già il nostro punto interrogativo per lo scaling) questa è una **perdita reale possibile**.

## Domande aperte per domani

1. Perché lo spike-guard non ha filtrato il tick −19%? (leggere `fetch_price_with_spike_guard` + il path buy tf_grid).
2. Serve un **cap di rifiuto sullo slippage del fill** (reject/alert se |fill − check|/check > X%)? Con quale soglia per-venue (Binance testnet vs Kraken BTC vs Kraken BONK)?
3. È un gate **prima** di scalare su BONK Kraken (Fase 3)?
4. I due round-trip ETH gonfiati: si lasciano (testnet, "la storia è il processo") o si annota il caveat nei numeri pubblici?

## Cosa NON è stato fatto (di proposito)
Nessun fix, nessun tocco ai trade/ai numeri. Questo è un report di analisi — la decisione (indagare spike-guard + eventuale cap slippage, ed eventuale brief) è di domani con Max/Board.

---

*Fonti: `trades` ETH/USDT 07-20/07-22 (reason verbatim con slippage loggata), runtime_state ETH (managed 0.008, phantom 1.0). Collegato agli item aperti: "slippage_buffer parametrico per coin" (pre-mainnet) e "calibrazione spike guard" (BUSINESS_STATE §5). Sessione S122.*
