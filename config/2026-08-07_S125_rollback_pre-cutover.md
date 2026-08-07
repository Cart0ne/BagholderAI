# Rollback S125 — stato `bot_config` PRIMA del cutover Kraken Fase 3

**Sessione:** S125 · 2026-08-07
**Brief:** `config/2026-08-07_S125_brief_kraken-fase3-execution.md`
**Snapshot preso:** 2026-08-07 ~10:20 UTC, prima di qualunque scrittura.
**Perché:** brief §4 — "Annotare i valori pre-modifica **prima** di scrivere."

Saldo Kraken verificato allo stesso momento (lettura sola dal Mac Mini):
USD liberi **$452,47** · BTC **0,00152221** (≈ $98,68 @ $64.825) · equity **$551,15**.

---

## Stato `bot_config` pre-intervento (5 righe)

| symbol | venue | cycle | active | managed_by | alloc | per_trade | buy_pct | sell_pct | skim | idle_h | sb_dd | sb_unlock | dead_h | profit_tgt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BONK/USDT | binance | testnet_2 | true | grid | 150 | 25 | 3.00 | 4.00 | 30 | 2 | 5 | 12 | 2 | 0 |
| BTC/USDT | binance | testnet_2 | true | grid | 200 | 50 | 1.80 | 1.20 | 30 | 2 | 3 | 12 | 2 | 0 |
| ETH/USDT | binance | testnet_2 | true | **tf_grid** | 46.666666666666664 | 15.56 | 2.00 | 2.50 | 0 | 1 | 15 | 0 | 4 | 0 |
| SOL/USDT | binance | testnet_2 | true | grid | 150 | 20 | 2.27 | 1.51 | 30 | 2 | 3 | 12 | 2 | 0 |
| BTC/USD | **kraken** | kraken_2b | true | grid | **100** | 33.33 | 1.80 | 1.20 | 30 | 2 | 3 | 12 | 2 | 0 |

`slippage_buffer_pct` = NULL e `initial_lots` = 0 su tutte le righe. `pending_liquidation` = false su tutte.

> Nota: `SOL/USDT` risulta 2.27/1.51 e non 2.25/1.50 come nel brief §3 Passo 3 — Sherpa
> ha riscritto la riga alle 10:13 UTC, mentre preparavamo la finestra. Differenza
> irrilevante (0,02 punti) e comunque effimera: `buy_pct`/`sell_pct` sono nella
> whitelist Sherpa (`bot/sherpa/main.py:79`) e vengono riscritti in continuazione.
> La riga SOL/USD nasce con i valori del brief (2.25 / 1.50).

## Altro stato pre-intervento

- `site_flags.disclaimer_mode` = **false** (id=1, testo già a DB, invariato)
- Nessuna riga `reserve_ledger` per BTC/USD → nessuno skim accantonato sul venue Kraken
- `bot_runtime_state` BTC/USD: managed_holdings `0.00152221`, phantom `0.0`,
  buy_reference_price `63497.9`, last_sell_price NULL, stop_buy_active false
- Orchestrator pid **16865**, avviato 2026-07-22, codice `4c6f191`, flag:
  `caffeinate -i env ENABLE_TF=true ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=live SHERPA_TELEGRAM_ENABLED=true ALLOW_REAL_MONEY=true`

---

## Come si torna indietro

**Passi 1-3 (scritture su `bot_config`) — reversibili:**

```sql
-- Passo 1 inverso: riaccendere i grid Binance
UPDATE bot_config SET is_active = true
WHERE venue = 'binance'
  AND symbol IN ('BTC/USDT','SOL/USDT','BONK/USDT','ETH/USDT');

-- Passo 2 inverso: BTC/USD torna a $100
UPDATE bot_config SET capital_allocation = 100
WHERE symbol = 'BTC/USD' AND venue = 'kraken';

-- Passo 3 inverso: spegnere SOL/USD (NON cancellare la riga se ha gia' tradato)
UPDATE bot_config SET is_active = false
WHERE symbol = 'SOL/USD' AND venue = 'kraken';
```

L'orchestrator rilegge `is_active` ogni 30s (`orchestrator.py:376/382`): accendere e
spegnere righe **non richiede riavvio**.

**Passo 4 (restart con `ENABLE_TF=false`) — reversibile** riavviando con `ENABLE_TF=true`.

**NON reversibile:** gli ordini eventualmente eseguiti su Kraken dopo i Passi 2-3.
Se al Passo 5 qualcosa non torna: si spengono le righe Kraken (`is_active=false`)
e si indaga. **La posizione resta in pancia — non si liquida niente per fretta.**

**Sito:** `UPDATE site_flags SET disclaimer_mode = false WHERE id = 1;` toglie la
pagina d'attesa (zero deploy).
