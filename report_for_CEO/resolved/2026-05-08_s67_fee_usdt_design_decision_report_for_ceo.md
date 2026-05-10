# S67 — Design Decision: come scriviamo le fee dei trade reali

**Sessione:** 67 · 2026-05-08 · ~21:00 UTC
**Stato bot:** fermo (killato dopo 1 minuto di vita su testnet, 3 buy fatti)
**Decisione richiesta al CEO:** semantica della colonna `trades.fee` post brief 67a
**Tempo stimato CEO:** 3-5 min lettura + 1 minuto verdetto

---

## TL;DR

Il bot è andato live su testnet per 1 minuto (3 buy reali, $94.68 totali). La dashboard privata grid mostra un P&L spaventoso di **−$3,419.97** che è un **bug di unità**, non una perdita vera. Devo decidere come correggere il design del campo `trades.fee` prima di rimettere il bot in moto. Tre opzioni. Mia raccomandazione: **(A) `fee` in USDT-equivalent + `fee_asset` per audit**.

---

## Cosa è successo (sintesi onesta)

Sequenza di stasera dopo l'approvazione del piano S67:

1. ✅ Backup Supabase completato (22 tabelle, 51,943 righe, 22.47 MB → `audits/2026-05-08_pre-reset-s67/` su Mac Mini)
2. ✅ Migration `trades.fee_asset` shipped (le altre 2 colonne del brief 67a erano già nello schema)
3. ✅ TRUNCATE 5 tabelle (`trades`, `reserve_ledger`, `bot_state_snapshots`, `bot_events_log`, `daily_pnl`) CASCADE
4. ✅ `.env` Mac Mini aggiornato con chiavi testnet, `TRADING_MODE=live`, `BINANCE_TESTNET=true`
5. ✅ Smoke test `test_connection` → "LIVE TESTNET", 10,000 USDT virtuali in account
6. ⚠️ Restart orchestrator con flag `ENABLE_TF=false ENABLE_SENTINEL=false ENABLE_SHERPA=false`
7. 🔴 **Errore di scope**: `bot_config` aveva 6 row con `is_active=true`, non 3. Sono partiti grid bot anche per OP/ZEC/TRX (TF allocation paper era + manual storiche), oltre BTC/SOL/BONK previsti.
8. 🔴 **3 buy reali su testnet** in 60 secondi:

| Symbol | amount | avg_price | cost (USDT) | fee | fee_asset | order_id Binance |
|---|---|---|---|---|---|---|
| BTC/USDT | 0.00062 | $80,179.71 | $49.71 | 6.2e-07 | BTC | 1257113 |
| SOL/USDT | 0.216 | $92.45 | $19.97 | 0.000216 | SOL | 129489 |
| BONK/USDT | 3,419,972 | $0.00000731 | $25.00 | 3,419.97 | BONK | 6964 |

9. 🔴 **Bug 1 (logging)**: `bot_events_log` rifiuta il mio INSERT `severity='warning'` perché il CHECK constraint accetta solo `info|warn|error|critical`. Telegram alert funzionano, log DB no.
10. 🔴 **Bug 2 (semantica)**: il valore `3,419.97` salvato in `trades.fee` per il buy BONK è in **BONK**, non in USDT. La dashboard privata grid lo legge come USDT → mostra **−$3,419.97 P&L**. P&L vero ≈ −$0.025 (la fee in USDT-equivalent).
11. ✅ Bot killato (TERM 90089 → propagato a 6 child grid_runner → tutti morti).

Il backup pre-TRUNCATE è intatto, i 3 trade live restano in `trades` (sono dati validi, primo "battesimo" del path live testnet — solo le unità sono sbagliate).

---

## Il design issue al cuore

### Cosa fa Binance

Binance market BUY scala la fee dal **coin che stai comprando**, non da USDT. Esempio: spendi 25 USDT per comprare BONK → ricevi N BONK − 0.1% (standard) = N × 0.999 BONK; quei "0.1% di BONK" sono la fee. La response API include:

```json
{
  "fee": { "cost": 3419.97, "currency": "BONK" }
}
```

Lo stesso per le sell market: scala la fee dal USDT che ricevi (fee in USDT). Quindi a seconda di buy/sell la `fee_currency` cambia.

Casi possibili (ordinati per probabilità in produzione):

1. **Market BUY su /USDT**: fee in coin di base (BTC, SOL, BONK, ETH, ...)
2. **Market SELL su /USDT**: fee in USDT
3. **Con BNB-discount on (utente ha BNB nel wallet)**: fee in BNB indipendentemente dal lato — sconto del 25% sui costi
4. **Limit orders**: fee dipende dal maker/taker e segue lo stesso pattern

### Cosa scrive il bot oggi (post brief 67a)

`trades.fee` = valore raw dalla response Binance (es. `3419.97`)
`trades.fee_asset` = currency dalla response (es. `'BONK'`)

### Perché è sbagliato per la dashboard / P&L

La dashboard mostra valori in dollari (`$X`), il foglio P&L è in USDT, il go-live €100 sarà in USDT. Avere `fee = 3419.97` dove "3419.97" non è dollari rompe ogni calcolo a valle:

- **P&L per trade** = `revenue − cost − fee` → impossibile se le 3 unità sono mischiate
- **Total fees per giorno** = `SUM(fee)` → mismatch unità (BTC + SOL + BONK + USDT sommati)
- **Reconciliation gate** (Step 5 brief 66a) → non chiude

E la dashboard ha già preso fuoco in vivo — Max ha visto -$3,419 dopo 60 secondi.

---

## Tre opzioni

### (A) `fee` in USDT-equivalent + `fee_asset` per audit  ← raccomandata

`trades.fee` = USDT-equivalent della fee (calcolato dal bot al momento del fill)
`trades.fee_asset` = currency raw da Binance (audit + reconciliation futura)

Conversione nel wrapper `bot/exchange_orders.py:_normalize_order_response`:

```python
base_coin = symbol.split("/")[0].upper()      # "BONK"
quote_coin = symbol.split("/")[1].upper()     # "USDT"

if fee_currency == quote_coin:
    fee_usdt = fee_cost                        # già in USDT
elif fee_currency == base_coin and avg_price > 0:
    fee_usdt = fee_cost * avg_price            # convert al fill price
else:
    # BNB o altro asset (caso edge, BNB-discount)
    fee_usdt = 0.0
    logger.warning(f"fee in {fee_currency}, USDT-equivalent left as 0")

return { "fee_cost": fee_usdt, "fee_currency": fee_currency, ... }
```

Esempi sui 3 buy fatti stasera:

| Symbol | fee raw | fee_currency | base_coin | avg_price | fee_usdt |
|---|---|---|---|---|---|
| BTC | 6.2e-07 | BTC | BTC | $80,179.71 | $0.0000497 |
| SOL | 0.000216 | SOL | SOL | $92.45 | $0.0200 |
| BONK | 3,419.97 | BONK | BONK | $0.00000731 | $0.0250 |

P&L dashboard tornerebbe a numeri sensati: −$0.025 BONK fee, non −$3,419.

**Pro:**
- Una sola sorgente di verità in USDT per tutto il sistema (P&L, dashboard, reconciliation, Telegram alerts)
- `fee_asset` preserva l'audit (sappiamo se Binance ha scalato in BNB invece che in USDT → futuro report risparmio BNB-discount)
- Compatibile retroattivamente con il fix dei 3 trade già fatti via `UPDATE trades SET fee = fee * price WHERE ...`
- Coerente con il pattern "una fonte di verità in USDT" già usato per `cost`, `realized_pnl`, etc.

**Contro:**
- Il caso BNB-discount richiede un cross-rate lookup (BNB→USDT al momento del fill). Per ora `fee_usdt = 0` quando fee è in BNB → underestimate del costo. Stima del gap: 0.1% × 25% sconto = 0.025% del cost, su $25 trade = $0.006 gap → trascurabile. Account testnet non ha BNB, quindi caso edge zero per questa fase.
- Se in futuro vogliamo report "quanto abbiamo risparmiato con BNB-discount", servirà aggiungere `fee_native_amount` come terza colonna (TODO post-mainnet).

### (B) `fee` raw + dashboard fa la conversione

`trades.fee` = valore raw (3419.97 BONK)
`trades.fee_asset` = currency (BONK)
Dashboard / P&L scripts leggono entrambi e convertono on-the-fly via JOIN su `exchange_filters` o cross-rate at trade time.

**Pro:** "fedeltà al broker" — il valore in DB è bit-exact a quello di Binance.

**Contro:**
- Ogni consumer (3+ dashboard, daily report, Telegram alert, reconciliation gate) deve duplicare la logica di conversione. Drift garantito.
- Per convertire a USDT al timestamp del trade serve sapere il prezzo allora, ma `trades.price` è il fill price del trade stesso (ok per buy del base coin, nullo per fee in BNB). Soluzione richiede tabella di prezzi storici aggiuntiva.
- "−$3,419 P&L" mostrato in dashboard pubblica = catastrofe narrativa in un progetto di radical transparency. Ogni regression test della dashboard deve duplicare la conversione.

### (C) `fee` in USDT-equivalent + nuova colonna `fee_native_amount`

Aggiungiamo una terza colonna `trades.fee_native_amount NUMERIC NULL` per il valore raw, e teniamo `fee` come USDT-equivalent. Gli audit Binance usano la nativa, le dashboard usano USDT.

**Pro:** completezza totale, audit perfetto con i numeri esatti del broker.

**Contro:**
- Migration in più (additiva, low risk)
- Il valore raw è già recuperabile via `fee × price` quando `fee_asset = base_coin`, quindi è ridondante per il 90% dei casi
- Complessità di schema aggiunta per uno use case (BNB-discount audit) che è post-mainnet

---

## Raccomandazione CC

**Opzione A.** Motivi:

1. **Frictionless per il sistema esistente**: dashboard, daily report, Telegram, P&L, reconciliation gate — tutti continuano a leggere `fee` in USDT senza modifiche.
2. **Risolve la regressione visiva**: dashboard privata grid torna a mostrare numeri credibili in 5 minuti.
3. **Il caso BNB-discount è 0% probabile su testnet** (account fresh senza BNB) e 0% probabile sul go-live €100 (Max non ha BNB nel wallet mainnet — verificare). Posso shippare l'opzione (A) ora e migrare a (C) prima del go-live mainnet se serve l'audit BNB-discount.
4. **Compatibilità retroattiva**: i 3 trade già fatti li sistemo con un UPDATE chirurgico (3 righe, calcolo manuale, già verificato sopra).

L'unico gap di (A) — fee BNB → 0 USDT — è risolvibile con una tabella `bnb_usdt_rate_at_trade` o un campo `fee_native_amount` aggiunto in futuro come opzione (C). Non gating per stasera né per il go-live.

---

## Cleanup operativo (dipendente dal verdetto CEO)

Se CEO approva (A):

1. Patch `bot/exchange_orders.py:_normalize_order_response` con la conversione (5 righe + 5 di logging) + fix bug severity `"warning"` → `"warn"`
2. UPDATE chirurgico per i 3 trade già fatti:
   ```sql
   UPDATE trades SET fee = 6.2e-07 * 80179.71 WHERE exchange_order_id = '1257113';  -- BTC
   UPDATE trades SET fee = 0.000216 * 92.45 WHERE exchange_order_id = '129489';     -- SOL
   UPDATE trades SET fee = 3419.97 * 0.00000731 WHERE exchange_order_id = '6964';   -- BONK
   ```
3. UPDATE `bot_config` per disattivare i 3 simboli fuori scope (OP/ZEC/TRX → `is_active=false`)
4. Test 7/7 verde no-regression
5. SCP `exchange_orders.py` al Mac Mini
6. Restart orchestrator (resta `ENABLE_TF=false ENABLE_SENTINEL=false ENABLE_SHERPA=false`)
7. Verifica startup → 3 grid bot solo (BTC/SOL/BONK), 3 buy esistenti restored, dashboard privata torna a mostrare P&L credibile

Tempo stimato: 30 minuti.

Se CEO approva (B) o (C):
- (B): non tocco il bot ma devo riscrivere 4-5 file di dashboard/report. Stima 2-3h. Sconsigliato.
- (C): tutto come (A) + migration `ALTER TABLE trades ADD COLUMN fee_native_amount NUMERIC NULL` + propagazione. Stima 45 minuti.

---

## Domande aperte secondarie (non gating per la decisione fee)

1. **Bot_config OP/ZEC/TRX**: stasera disattivo. Storicamente erano TF allocation (OP) e manual storiche (ZEC, TRX). Vogliamo cancellare le row da `bot_config` o mantenerle `is_active=false` come archivio?

2. **3 trade testnet già fatti**: dato di prova del path live → restano in DB come "battesimo" S67 oppure li TRUNCATE-iamo per ripartire da zero pulito? Mia preferenza: restano (cancellarli sarebbe fingere che non sia successo).

3. **Sito pubblico**: ancora in maintenance da 2026-05-08. Quando sblocchiamo? Mio piano originale era sbloccare home stasera, ma con il bot che ha avuto 1 minuto di scope creep + 2 bug shipped, forse meglio aspettare 12-24h di osservazione testnet pulita prima di rimettere up il sito.

---

## Stato finale per il CEO

- **Codice**: 8 file modificati su MBP, 7 di questi già SCP-ati al Mac Mini, working tree dirty (zero commit)
- **DB**: post-TRUNCATE 5 tabelle, post-migration `fee_asset`, 3 trade live in `trades`
- **Bot**: fermo
- **Sito**: in maintenance
- **Test**: 7/7 verde locale e Mac Mini

**Decisione richiesta:** A / B / C sul design `trades.fee` + risposte alle 3 domande secondarie.
