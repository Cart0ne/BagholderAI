# Brief 78b — SWEEP/LAST SHOT slippage buffer + banner fix

**Stato:** APPROVATO da Board (S78 fase 2, 2026-05-16). Pronto per esecuzione.
**Da:** Claude Code (Intern) — diagnosi 2026-05-16 (sessione 78 fase 2, post pubblicazione blog "The Day Our Bot Ran Out of Money")
**Per:** CEO (Claude, claude.ai) — comunicazione decisione tecnica
**Origine:** sessione 78 fase 2 diagnostica. Max (Board) ha notato sul `/grid`: (Q1) BONK non flaggato `tapped out` nonostante allocazione satura, (Q2) `cash to reinvest = -$0.39`.

---

## ⚠️ Storico del brief

**Versione 1 (rifiutata)**: ipotizzava che il bot capital guard ignorasse `skim_reserve` e proponeva un guard skim-aware + replay byte-identical. Premessa **errata**: verifica empirica ha mostrato che [grid_bot.py:210-224](bot/grid/grid_bot.py#L210-L224) `_available_cash()` **già** sottrae `reserve_ledger.get_reserve_total()`. Nessun replay necessario, nessuna formula da riallineare. La 1.0 è cestinata.

**Versione 2 (questa)**: root cause vera = path SWEEP/LAST SHOT manda ordini BASE che eseguono in slippage positivo → cost reale > cost_before atteso. Behavior accettato dal Board come "by design su testnet" ma necessita di buffer pre-mainnet per evitare `-2010 INSUFFICIENT_FUNDS` reject.

---

## 1. Diagnosi (verifica empirica 2026-05-16)

Cronologia BONK ricostruita da DB. Trade incriminato — **2026-05-15 05:39:17 UTC**:

| | valore |
|---|---:|
| cum_invested pre-trade | $335.11 |
| cum_received | $233.37 |
| cum_skim_reserve | $2.60 |
| **cash_before skim-aware** (formula `_available_cash()`) | **$45.66** |
| capital_per_trade BONK | $25 |
| path attivato | SWEEP (line 99: `0 < remaining_after $20.66 < standard_cost $25`) |
| cost richiesto al bot | $45.66 (= cash_before) |
| base_order inviato a Binance | base_rounded = $45.66 / 0.00000671 ≈ 6.8M BONK |
| fill_price Binance | 0.00000679 (slippage +1.19%) |
| **`res["cost"]` reale** | **$46.10** |
| **drift singolo trade** | **+$0.44 over cassa attesa** |

Reason DB: `"LAST SHOT: Pct buy: check $0.00000671 dropped 2.5% below last buy $0.00000691 → fill $0.00000679 (slippage +1.19%) — spent remaining $46.10"`.

Su totale 3 sweep-like BONK su 15 buy, drift cumulato osservato = $0.39 (somma con BTC/SOL sub-cent compensanti), coerente con cash to reinvest $-0.39 visto dal dashboard.

## 2. Decisione Board

> SWEEP/LAST SHOT è regola **by design**: "no cash morto non investibile". Il drift sub-dollar su testnet è prezzo accettabile per non lasciare cassa stranded.
>
> Pre-mainnet però Binance rifiuta con `-2010 INSUFFICIENT_FUNDS` qualsiasi base_order che ecceda USDT free (mainnet non è permissivo come testnet). Servono **buffer di slippage** sul cost SWEEP/LAST SHOT per non sforare.

## 3. Scope

### G1 — Slippage buffer fisso 3% in SWEEP/LAST SHOT

Costante hardcoded in `config/settings.py`:

```python
class HardcodedRules:
    # ... esistenti ...
    SLIPPAGE_BUFFER_PCT = 0.03  # 3% buffer su SWEEP/LAST SHOT cost
    # Scopo: non sforare USDT free su mainnet (Binance reject -2010 INSUFFICIENT_FUNDS).
    # Calibrato su testnet BONK ~2.46% slippage. Ricalibrare post-mainnet (slippage reale
    # tipicamente 10× più basso). NO per-coin tuning ora — ricalibrazione semplice in mainnet
    # quando avremo dati reali.
```

Applicato in [bot/grid/buy_pipeline.py](bot/grid/buy_pipeline.py):
- **SWEEP** (linea 100): `cost = cash_before * (1 - HardcodedRules.SLIPPAGE_BUFFER_PCT)`
- **LAST SHOT** (linea 110): `cost = cash_before * (1 - HardcodedRules.SLIPPAGE_BUFFER_PCT)`

Path normale (cost = standard_cost = capital_per_trade) NON cambia: ha già margine perché `cash_before >= standard_cost + ε`.

### G2 — Banner fix grid.html

[web_astro/public/grid.html:668](web_astro/public/grid.html#L668): `=== 0` → `<= 0`. Per `buysLeft < 0` (caso fisiologico post-SWEEP con slippage), testo informativo:

```js
if (analysis.buysLeft < 0) {
  alerts.push({ type: 'red', text: SHORT[sym] + ' is tapped out (swept) — $' + fmt(Math.abs(analysis.cashLeft)) + ' over by slippage' });
} else if (analysis.buysLeft === 0) {
  alerts.push({ type: 'red', text: SHORT[sym] + ' is tapped out — $' + fmt(analysis.cashLeft) + ' cash, needs $' + fmt(Number(cfg.capital_per_trade)) + '/buy' });
}
```

## 4. Punti di codice

| # | File | Cambio | Stima |
|---|---|---|---:|
| 1 | [config/settings.py:78-107](config/settings.py#L78) | Aggiungere `SLIPPAGE_BUFFER_PCT = 0.03` con commento. | 5 min |
| 2 | [bot/grid/buy_pipeline.py:100,110](bot/grid/buy_pipeline.py#L100) | Applicare buffer in SWEEP + LAST SHOT cost. Log riga aggiornata con sia `cash_before` sia `cost_with_buffer`. | 15 min |
| 3 | [web_astro/public/grid.html:668](web_astro/public/grid.html#L668) | Banner: branch `buysLeft < 0` con testo informativo "swept, $X over by slippage". | 10 min |
| 4 | `tests/test_sweep_slippage_buffer.py` (NEW) | 3 scenari: (a) normal buy `cash >= standard_cost` → cost=standard_cost invariato; (b) SWEEP `0 < remaining < standard` → cost = cash_before × 0.97; (c) LAST SHOT `5 ≤ cash < standard_cost` → cost = cash_before × 0.97. Mock exchange, no DB. | 25 min |

Totale stimato: ~55 min.

## 5. Cosa NON cambia

- Guard skim-aware in `_available_cash()` invariato (funziona già).
- `state.total_invested` registra `res["cost"]` reale post-buffer (NON il `cost` richiesto pre-buffer). Trasparenza contabile invariata.
- Path normale buy invariato.
- Banner per BTC/SOL (`buysLeft === 0`) invariato.

## 6. Rollout

1. Implementare punti 1-3.
2. Test punto 4 verde locale (richiede Archivio mount per import bot/* — vedi memoria `feedback_archivio_mount`).
3. Commit + push.
4. SSH Mac Mini: pull → graceful kill orchestrator → restart (memoria `reference_orchestrator_start`).
5. Verifica empirica 24-48h: prossimo SWEEP/LAST SHOT BONK genera cost ridotto del 3%, cassa residua ≥ 0.
6. Aggiornamento PROJECT_STATE §4 (decisione) + §10 (sessione shipped).

## 7. Open question (NON in scope)

- **Calibrazione mainnet**: lasciato a un brief separato quando ci avviciniamo a go-live €100. Slippage mainnet tipicamente 10× più basso del testnet, quindi 3% sarà sovradimensionato. Decideremo se tunare a 0.5-1% allora.
- **Banner badge "−1 buys left" arancione in card per BONK**: card mostra correttamente "−1 buys left" gialla; con questo fix il banner top mostra anche "swept" rosso. Coerenti, no ulteriori cambi.

## Decision log

- DECISIONE: slippage buffer 3% fisso uniforme su SWEEP/LAST SHOT, hardcoded in `HardcodedRules`.
- RAZIONALE: pre-mainnet REJECT `-2010` se base_order eccede USDT free. Buffer minimo per garantire mai sforare. 3% calibrato su slippage testnet BONK osservata (2.46%); BTC/SOL su testnet hanno slippage <0.5% ma il buffer è uniforme per semplicità ora. **Punto aggiuntivo Board S78 fase 2**: per-coin parametrizzato sarebbe overengineering anche perché in mainnet non sappiamo ancora con quali monete lavoreremo — calibrare per BTC/SOL/BONK ora rischia di buttare lavoro se il mix mainnet sarà diverso.
- ALTERNATIVE CONSIDERATE: (A') buffer per-coin parametrizzato in `bot_config` — scartata (premature optimization + non sappiamo nemmeno il mix coin mainnet); (B) quote-order in SWEEP — scartata perché riapre il rischio della memoria `project_last_shot_lot_size_bypass` (BONK -2010 LOT_SIZE su book sottile S73c).
- FALLBACK SE SBAGLIATA: revert dei 2 cambi in `buy_pipeline.py`. Stato torna a SWEEP "spendi tutto" senza buffer. Compatibile con testnet (permissivo), riapre il rischio mainnet REJECT.

## Roadmap impact

Nessuno. Brief locale di consistency + safety net pre-mainnet. Non muove timeline Sentinel-first, non muove go-live €100.
