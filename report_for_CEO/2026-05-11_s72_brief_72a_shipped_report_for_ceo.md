# Report S72 — Brief 72a Fee Unification SHIPPED

**Data:** 2026-05-11
**Sessione:** 72 (chiusura tecnica)
**Sintesi:** Brief 72a shipped come da tua approval. Bot restart Mac Mini OK con holdings golden source. Zero ORDER_REJECTED post-restart. Cron reconciliation notturno installato. Frontend + commentary allineati alla nuova logica. **Resta un debito matematico residuo** che richiede tua decisione editoriale prima del go-live €100.

---

## 1. Output atteso vs delivered (dal tuo brief approval)

| Voce richiesta | Status | Dettaglio |
|---|---|---|
| Codice 5 file su main | ✅ | `116d0fb` (codice) + `1f9bba9` (patch reconcile asymmetric) |
| Test 18/18 verdi | ✅ | 15 esistenti + P/Q/R nuovi, verdi locale + Mac Mini |
| Bot restartato 3 grid | ✅ | 13:49 UTC, 6 processi vivi (BTC + SOL + BONK + Sentinel + Sherpa + caffeinate) |
| Backfill ~42 trade testnet | ✅ | Sanity check rivelato 18 SELL (non 42; il 42 includeva BUY). Cumulato $11.63 → $10.53 (Δ −$1.097) |
| 24h osservazione iniziata | ✅ | Counter parte dalle 13:49 UTC, scade 2026-05-12 13:49 UTC |
| Zero ORDER_REJECTED conferma | ✅ | `bot_events_log` post-restart: 0 eventi `ORDER_REJECTED`. Telegram dev-console silente dal restart |

---

## 2. Boot reconcile post-restart (output reale)

3 eventi `integrity` / `holdings_drift_warn` (severity=info) loggati al boot delle 13:49 UTC:

| Symbol | Replay DB | Binance reale | Gap signed | Gap % | Verdict |
|---|---|---|---|---|---|
| BTC | 0.000609 | **1.000606** | +0.999997 BTC | **+164098%** | wallet_surplus (initial fantasma) |
| SOL | 0.625374 | **5.624730** | +4.999356 SOL | **+799%** | wallet_surplus (initial fantasma) |
| BONK | 1.638.312 | 1.656.758 | +18.446 BONK | +1.13% | wallet_surplus (come previsto S72 diagnosi) |

**Tutti positivi** (drift POSITIVO = "il wallet ha più di quanto il replay si aspetta" = initial balance gift testnet). Su mainnet attesi tutti ~0%.

**Edge case scoperto al primo restart**: la soglia simmetrica 2% del tuo brief originale (no override) ha fatto FAIL_START su BTC/SOL (1 BTC e 5 SOL gratis dal testnet Binance — magnitudo non prevista pre-S72). Soluzione concordata con Max: **asymmetric threshold** — drift positivo sempre WARN (testnet gift = innocuo), drift negativo > 2% FAIL (phantom holdings = capital at risk, mainnet relevant). Su mainnet pulito (no initial gift, no reset mensile) il comportamento è funzionalmente identico al brief originale.

---

## 3. Cron reconciliation Step C — installato

```cron
# BagHolderAI - Nightly Binance reconciliation (brief 71a Task 2, S72)
0 3 * * * /Volumes/Archivio/bagholderai/scripts/cron_reconcile.sh
```

03:00 Europe/Rome = 01:00 UTC, BEFORE il bot daily retention (04:00 UTC). TCC Full Disk Access già concesso (memoria S70b conferma). Test run manuale eseguito 15:05 UTC: BTC 11 / SOL 9 / BONK 18 matched, 0 drift su tutti. Prima run automatica: stanotte 03:00.

---

## 4. Frontend + commentary aggiornati (commit `d93f38a`)

Aggiornati a posteriori per matchare le 3 invariants del bot:
- `web_astro/src/lib/pnl-canonical.ts` — Replay home/dashboard ora sottrae `fee_native = fee_usdt/price` quando `fee_asset == base_coin`
- `web_astro/src/scripts/dashboard-live.ts` — Stesso fix nel replay locale
- `commentary.py` (server-side Haiku) — Stesso fix in `_analyze_coin_avg_cost`
- SELECT queries (Supabase) ora includono `fee_asset` ovunque

Astro build green (10/10 pagine). Vercel auto-deploy in corso.

---

## 5. Il debito matematico residuo — l'onestà serve

Max ha sintetizzato bene durante la sessione: "tanto non torna nulla, non ce la facciamo con la matematica". È vero, e merita di essere documentato chiaramente prima del go-live:

### 5.1 Tre dataset eterogenei nello stesso DB

| Origine | Trade count | Formula realized_pnl | Holdings replay |
|---|---|---|---|
| Paper era (pre-S67) | 458 | (price − avg) × qty (**gross**) | Lordo |
| Testnet era backfill (post-S72) | 18 SELL | (price − avg) × qty **− fee_sell** | Netto fee_base |
| Testnet wallet reale | n/a | n/a | Include **initial fantasma** (1 BTC, 5 SOL, 18K BONK gift Binance) |

Nessuna formula unica li tratta in modo coerente. Risultato: nel **Net Realized Profit pubblico** (hero dashboard + grid.html), c'è un bias documentato di **−$0.22** (fee_sell contata due volte sui 18 testnet, una volta correttamente sui paper). Hard-coded nei commenti del codice per non perdere la memoria del debito.

### 5.2 Holdings: 2 sorgenti di verità

| Numero | Fonte | Include initial fantasma? |
|---|---|---|
| `state.holdings` (bot in memoria) | `fetch_balance()` Binance | **Sì** (1.000606 BTC, 5.624730 SOL, 1.656.757,8 BONK) |
| Holdings su dashboard/home | Replay DB dei `trades` | **No** (mostra solo il "lavoro" dei $500 testnet) |

Differenza pratica: BTC su dashboard mostra ~$49 di holdings_value, bot sa di averne $80.000 dal punto di vista wallet. Sia il bot che la dashboard sono "corretti" — semplicemente rispondono a domande diverse:
- **Bot**: "quanto puoi davvero vendere?" → wallet reale (golden source)
- **Dashboard pubblica**: "dove sono finiti i $500 di paper budget?" → replay del lavoro

Non è un bug, è una scelta editoriale implicita. Ma è una **divergenza che vale la pena rendere esplicita** al pubblico (o eliminarla).

### 5.3 Le 3 vie possibili per "far quadrare la matematica" — decisione Board/CEO

**Via A — Status quo + documentazione pubblica (0h lavoro)**
Lasciamo i numeri come sono. Aggiungiamo una nota piccola in /dashboard o /blueprint: "I numeri pubblici escludono l'initial balance fantasma del testnet ($Y di BTC/SOL/BONK assegnati gratuitamente da Binance all'apertura account). Eventuale bias residuo netRealized: −$0.22 documentato." Onesto, narrativamente coerente con "story is process, not numbers".

**Via B — Split visivo "Paper Era" + "Testnet Era" (~2-3h frontend)**
La dashboard pubblica diventa 2 sezioni: "Paper Era (Mar 30 → May 8): $X realized gross, $Y fees" + "Testnet Era (May 8 → today): $Z realized net". Ogni era usa la sua formula corretta. Niente bias. Più complicato editorialmente ma totalmente onesto.

**Via C — Backfill totale paper (~3-4h codice + decisione)**
Ricalcoliamo realized_pnl di tutti i 458 paper trade con la formula nuova. La storia "cambia" retroattivamente ma diventa coerente. Avevi detto NO a questo a S71 ("paper as-is, story is process"). Reversibile se cambi idea.

**Mio voto**: A per ora (chiudere S72 pulito, va in osservazione 24h), B post-go-live €100 (quando avremo dati real-money e il Paper/Testnet sarà tutta storia narrativa).

---

## 6. Pending pre-go-live €100

Phase 9 V&C — ✅ Fee Unification (S72), ⬜ 24h osservazione (in corso), ⬜ Decisione Via A/B/C sopra, ⬜ Mobile smoke test reale, ⬜ Sentinel/Sherpa analisi DRY_RUN, ⬜ Board approval finale.

Target go-live: **18-21 maggio** se osservazione clean + Via A approvata.

---

## 7. Cosa ho imparato in S72 (lezioni per le prossime sessioni)

1. **Memoria `feedback_check_constraints` violata**: ho usato `category='reconcile'` senza verificare il CHECK constraint pg → primo commit doveva essere `'integrity'`. Mea culpa, una patch 1f9bba9 in più. Niente perdite, ma ricordo.
2. **Diagnosi dati prima della teoria**: la prima bozza brief 72a si basava su "drift = 12.280 BONK = fee scalata". La diagnosi `fetch_my_trades` ha rivelato che era diluito da initial fantasma 18.446 BONK. Senza diagnosi avrei deployato un fix peggiorativo.
3. **CEO threshold simmetriche non scalano bene sul testnet**: l'asymmetric variant è il pattern corretto su un sandbox dove l'exchange assegna saldi iniziali. Su mainnet le due varianti coincidono.

---

## 8. Roadmap impact

Phase 9 V&C Pre-Live Gates: aggiunto **✅ Fee Unification (S72)**. Chiude in unico shipping i ticket pending 71b + Strada 2 + bug realized_pnl gross + bug avg gross + Open question 27 (reason bugiardo, chiusa S71). Resta Via A/B/C come decisione editoriale Board, non gate tecnica.

— CC, 2026-05-11
