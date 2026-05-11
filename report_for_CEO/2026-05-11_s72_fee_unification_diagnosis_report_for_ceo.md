# Report S72 — Fee Unification Diagnosis

**Data:** 2026-05-11
**Sessione:** 72
**Sintesi:** Sessione di diagnosi. Niente codice committato. Smontata la teoria S71 "brief 71b isolato" e riformulata come brief unico 72a "fee unification" che chiude in un colpo BONK InsufficientFunds + Strada 2 + bug correlati. Brief pronto, **attende approval CEO** prima di codice.

---

## 1. Cosa è successo

Max ha aperto S72 chiedendo "fee brainstorming + fix BONK" come da BUSINESS_STATE. Dopo la mia prima proposta (fix isolato di `holdings += amount − fee_base` + replay retroattivo), Max ha risposto:

> "Voglio chiarire le fees in generale, non capisco la difficoltà ad avere i numeri uguali a quelli che avrei con binance mainnet al netto dello slippage sugli ordini... Stiamo inseguendo dei bug e non capisco perché"

Ha ragione. Abbiamo costruito a strati. Ho fatto un passo indietro e identificato che il bot ha **3 "memorie" delle fee non coerenti**:
1. `state.holdings` (somma lordo, dovrebbe essere netto)
2. `state.avg_buy_price` (basato su qty lorda, dovrebbe essere su qty netta)
3. `trades.realized_pnl` (gross di fee_sell, dovrebbe sottrarla)

Proposta: un brief **unico** che fissa 3 proprietà invariabili e chiude la radice.

Max ha approvato il principio: "fee unification, non voglio più avere problemi".

## 2. Diagnosi BONK (la svolta)

Mentre tentavo un dry-run del replay retroattivo per validare la teoria, ho scoperto che **i numeri non quadravano**:

- Replay retroattivo (lordo − fee_native − sell) → 1.638.312 BONK
- Binance reale → **1.656.758 BONK** (gap +18.446 inspiegato)
- DB lordo → 1.669.038 (drift osservato 12.280)

Per capire ho fatto girare uno script diagnostico sul Mac Mini (`/tmp/diag_bonk_drift2.py`) che chiama `fetch_my_trades()` di Binance. Risultato decisivo:

| Voce | Valore | Origine |
|---|---|---|
| Buy lordo cumulato | 30.726.196 BONK | sum executedQty |
| Fee BONK reale | **30.726,2 BONK** | sum commission per fill (0.1% esatto) |
| Sell cumulato | 29.057.158 BONK | fee in USDT |
| Net teorico (lordo − fee − sell) | 1.638.311,8 BONK | da zero |
| Binance reale | **1.656.757,8 BONK** | fetch_balance() oggi |
| **Initial balance fantasma** | **+18.446 BONK** | testnet pre-S67, non in fetch_my_trades |

L'equazione chiude: 1.656.757,8 = 1.638.311,8 + 18.446 ✓

**Implicazione critica**: il replay deterministico dal DB **non può** ricostruire holdings reali perché ignora:
- Saldi iniziali testnet (gift Binance all'apertura account)
- Eventuali reset testnet mensili
- Trasferimenti orfani

→ **Holdings deve venire da `fetch_balance()`, sempre. Il DB serve per altre cose (avg, realized), non per holdings.**

Questa è una svolta di design che cambia la struttura del fix.

## 3. Brief 72a "Fee Unification" — sintesi

Scritto in `config/brief_72a_fee_unification.md`. Sostituisce brief 71b + Strada 2.

### Le 3 proprietà invariabili (assiomi)

```
P1 — state.holdings = exchange.fetch_balance() (golden source)
     Boot: state.holdings = balance[base_coin]. Replay NON scrive holdings.
     Fill: state.holdings += filled − fee_base (incremento coerente)
     Soglie: warn >0.5%, fail-start >2%, no override.

P2 — state.avg_buy_price = USDT_speso / qty_realmente_acquisita
     Su BUY: cost_usdt = filled × price; qty_acquired = filled − fee_base
     Su replay: avg ricostruito sui SOLI trade DB (ignora initial fantasma testnet)

P3 — trade.realized_pnl = (price − avg) × qty − fee_sell_usdt
     Coincide col vero P&L wallet Binance per ogni sell.
```

### Cosa cambia rispetto alla prima bozza

- Niente più "replay retroattivo che sottrae fee_native" (overshoot 18K BONK)
- `fetch_balance()` è la fonte ultima di holdings — gestisce automaticamente initial fantasma, reset mensile testnet, drift orfani futuri
- BNB-discount integrato gratis (su mainnet con BNB, `fee_base=0`, holdings non drifta)
- Avg ricostruito sui SOLI trade DB (opzione A — initial fantasma ignorato, è "materia narrativa" non contabile)

### Punti di codice (5 file + tests)

`exchange_orders.py` — ritorna `fee_base`
`buy_pipeline.py` — holdings/avg netti
`sell_pipeline.py` — realized_pnl netto
`state_manager.py` — boot reconcile vs Binance, holdings = golden
`tests/test_accounting_avg_cost.py` — 3 casi nuovi (P/Q/R)

Niente migration DB. `trades.amount` resta lordo (audit). `realized_pnl` ricomputato in DB per trade testnet (UPDATE post-deploy, paper non toccato).

### Stima

4-6h codice + test + rollout. Pre-go-live €100 gate.

## 4. Decisioni di Max in S72

Confermate via AskUserQuestion in sessione:

- **BNB discount**: codice BNB-aware ora, attivazione BNB-discount post-mainnet stabile
- **Boot reconcile severity**: warn >0.5%, fail >2%, **no override env**
- **Backfill storia**: solo testnet (post-S67), paper resta as-is
- **Initial balance fantasma**: opzione A — ignorato nel calcolo avg, è narrativa
- **Restart scope post-fix**: tutti e 3 i grid (BTC + SOL + BONK)
- **Telegram noise ORDER_REJECTED**: nessuna azione, smetteranno da soli post-fix

## 5. Open questions per CEO

Tre punti dove serve la tua voce strategica prima di approvare:

1. **Soglia 0.5%/2% adeguata per mainnet?** Su mainnet (no initial fantasma, no reset) gap dovrebbe essere ~0. Su testnet, BONK resterà sempre con ~1.1% di gap (initial fantasma 18.446 non recuperabile). Il bot partirà sempre con warn. Accetto questo overhead o cambiamo soglia?

2. **Backfill paper trade conferma "no"?** Il diary post-fix dovrà raccontare che la cronologia paper ha P&L gross e quella testnet ha P&L netto. Storia divisa coscientemente. Memoria `feedback_story_is_process_not_numbers` supporta. OK?

3. **Sanity check post-trade `fetch_balance()` ogni fill: ON o OFF?** Default OFF. ON = 1 chiamata API extra ogni trade (rate limit ok ma cost non zero). Vantaggio: drift visibile immediato, non solo al boot. Preferenza?

## 6. Cosa NON si fa con questo brief

- Slippage_buffer parametrico per coin (brief separato pre-mainnet)
- Phase 2 split `grid_runner.py` (62b parcheggiato)
- BNB cross-rate runtime (Step 5 separato)
- Sherpa rule-aware sull'hotfix slippage (separato)

## 7. Roadmap impact

Phase 9 V&C — Pre-Live Gates: aggiunge ⬜ "Fee unification" come ultima gate. Chiude in un colpo brief 71b + Strada 2.

Target go-live €100:
- Brief 72a complete: 4-6h codice + 24h osservazione = **15-18 maggio**
- Go-live se osservazione clean: **18-21 maggio**
- vs target BUSINESS_STATE "fine maggio / inizio giugno": **possibile recupero 7-10 gg**

## 8. Stato repo fine S72

- Branch: `main`
- Ultimo commit: `0ae0610` (S71 chiusura)
- **Niente codice in questa sessione**. Solo 2 file nuovi pronti per commit:
  - `config/brief_72a_fee_unification.md` (brief tecnico)
  - `report_for_CEO/2026-05-11_s72_fee_unification_diagnosis_report_for_ceo.md` (questo)
  - `PROJECT_STATE.md` (update sessione 72)
- Mac Mini ancora a commit `441b0fc` (S70c). Pull S71 + S72 deferred al deploy del brief 72a.
- Bot live testnet invariato. Alert ORDER_REJECTED BONK continuano (stimati ~10-15/h finché non shippiamo 72a).

## 9. Richiesta esplicita

**Aspetto la tua approval del brief 72a** prima di scrivere codice. Se le 3 open questions in §5 hanno risposte, e tu approvi la struttura, posso aprire la sessione 73 con il deploy.

In alternativa, se la teoria ha falle che non ho visto, dimmi cosa correggere.

— CC, 2026-05-11
