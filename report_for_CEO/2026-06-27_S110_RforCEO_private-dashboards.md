# Report per il CEO — S110 (Private Dashboards)

**Data:** 2026-06-27
**Sessione:** S110 (110a + 110b), collaborativa Max + CC
**Scope:** sistemazione delle 3 dashboard private (`grid.html`, `tf.html`, `admin.html`)
**Basato su:** sessione guidata da Max in chat (nessun brief CEO sorgente)
**Natura:** **tutto front-end** — zero codice bot, zero DB/migration, zero restart. Le dashboard girano da Vercel/origin.

---

## Cosa è stato shippato

### 110a — grid + tf (commit `5407331`, `2cd3f5a`, `ff2e629`)

**grid.html (G1):**
- Risolto il bug cosmetico **"−1 buys left"**: con cassa < $5 (floor reale del bot) il badge ora dice **TAPPED OUT** invece di un conteggio negativo (drift da SWEEP/LAST SHOT).
- Il badge **conta anche il last-shot** e mostra la **taglia del prossimo buy** ("· $25/buy" o "· $18 last shot").
- Nuovo indicatore **"To next lot"**: quanta cassa manca per sbloccare il prossimo lotto pieno + l'equivalente lordo al netto dello skim. Rende **visibile** il compounding "grumoso" (vedi 4.14).
- **Verifiche richieste da Max — esito:** la formula dell'**avg-cost** (V1) e il giro **profitti − skim → cassa disponibile** (V3) sono **corretti, nessun bug**. Il bot fa benissimo a non comprare con cassa negativa; era solo l'etichetta a essere brutta.

**tf.html (T1, Path 1):**
- Card per-coin e Portfolio Overview **uniformate a grid**. Razionale: oggi **tutte** le coin sulla pagina TF sono `tf_grid` (TF le sceglie, **grid** le gestisce) → hanno i parametri/meccanismi di grid, quindi la card di grid è quella corretta.
- Aggiunto il fetch di `bot_runtime_state` per i **trigger live** ("Next buy/sell if", stop-buy con countdown).
- **Preservate** le sezioni TF-uniche (safety params, greed decay), il badge GRID e le coin deallocate.

**Audit "niente italiano visibile"** su tutti e 3 i file (7 stringhe tradotte; i commenti di codice restano in italiano per scelta).

### 110b — admin (commit `79d3594`, `ea8e7f5`, `3c464d9`)

- **A1** — snapshot aggregato **Grid + TF** in cima (Total P&L, Today P&L, n° trade, split per fondo), con la **stessa formula canonica della homepage** (`window.PnL`, nessuna 4ª copia del P&L). Verificato sui dati live (Total P&L −$1.65, Grid +$3.84 / TF −$5.49).
- **A3** — nuova sezione **"Market prices"**: un grafico per ogni coin attiva, prezzo **live da Binance** (klines pubbliche, no key). **Dinamico**: i grafici compaiono/spariscono in base a `bot_config.is_active` (ETH incluso). La finestra segue il range-selector (12h/24h/7g/1m).
- **A4** — **tooltip al mouseover** sul grafico Sentinel × BTC: giorno/ora, prezzo BTC, risk, opportunity del punto sotto il cursore.

---

## Decisioni da portare al Board / possibili update a BUSINESS_STATE

Due temi sono emersi **dall'analisi del codice** e sono stati **tracciati nella MASTER task list come decisioni CEO** (non implementati, scelta strategica):

- **4.12 — Floor di acquisto per-coin (BONK).** Il bot usa un floor fisso **$5** (`MIN_LAST_SHOT_USD`) per l'ultimo buy. Su Binance il minimo reale (`min_notional`) è $5 per BTC/SOL/ETH ma **$1 per BONK**. Quindi su BONK il bot lascia **$1–5 di cassa non spesi** che l'exchange accetterebbe. Decidere: convertire il floor a `max($5, min_notional)` per-coin, **oppure** tenere $5 come soglia anti-micro-buy (book BONK sottile, slippage 2-3%). *Il bot oggi è corretto: è una scelta di design.*

- **4.14 — Compounding policy (grid).** Col lotto **fisso** + skim, il profitto aumenta la capacità d'acquisto solo **a scatti interi** (~$36 lordi/coin, o ~$107 distribuiti su 3 coin, per **un solo lotto** in più). Il reinvestimento è **per-coin** (silos indipendenti, nessun pooling — verificato). Opzioni: **(A)** lotto fisso oggi, **(B)** lotto cresce col profitto (+rischio per trade), **(C)** allocazione cresce col profitto (+lotti). L'indicatore "To next lot" (110a) serve a **rendere visibile** il fenomeno.

Entrambe sono su **testnet paper**, quindi nessuna urgenza: decidibili coi dati, pre-mainnet.

---

## Roadmap impact

**Nessuno.** Le dashboard private sono tool interni (auth-gated, non indicizzati), non una Phase pubblica della roadmap. `web_astro/src/data/roadmap.ts` non toccato — corretto.

## Note operative

- Tutto front-end → **nessun restart bot**. Repo ufficiale del Mac Mini sincronizzato.
- Cadenza audit: nessuno scaduto; **A1** (ultimo 2026-06-01) e **A3** (ultimo 2026-05-31) si avvicinano alla cadenza di 30 giorni (~1-lug / ~30-giu) — da pianificare a breve.
- Commit S110: `5407331` `2cd3f5a` `ff2e629` (110a) · `79d3594` `ea8e7f5` `3c464d9` (110b) · `b7f590d` `67ad581` `1f8d8cf` (MASTER 4.12/4.13/4.14).
