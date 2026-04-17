# BRIEF — Session 36j: MBOX phantom profit / skim desync

**Date:** 2026-04-17
**Priority:** LOW — impatto contabile $0.19, self-healing alla prossima riallocazione
**Status:** Audit documentato, **nessuna azione correttiva** intrapresa. Opzione 1 (lasciare stare) scelta.

---

## Anomalia osservata

Durante l'audit 36g, MBOX/USDT (deallocata da TF, netHoldings=0) presenta un gap
tra `realized_net` registrato dal bot e il cash flow effettivo:

| Metrica | Valore |
|---|---|
| `Σ trades.cost` buy (invested) | $187.49 |
| `Σ trades.cost` sell (received) | $188.23 |
| **Gross cash flow** (received − invested) | **$0.74** |
| `Σ trades.realized_pnl` (net di fees) | $3.09 |
| `Σ trades.fee` | $0.28 |
| Gross implied da realized_net + fees | $3.37 |
| **Phantom profit** = realized_gross_implied − gross_cash_flow | **$2.63** |
| Skim versata in reserve_ledger (30%) | $0.93 |
| Skim "giustificabile" (30% × $0.74) | $0.22 |
| **Phantom skim** = skim reale − skim giustificabile | **$0.71** |
| Cash flow reale residuo (0.74 − 0.93) | **−$0.19** |

Gli altri coin TF passano il check con gap trascurabile:
- ORDI: phantom = $0.00 (match esatto)
- AXL: phantom = $0.02
- BIO: phantom = $0.25
- TST: phantom = $0.001
- MOVR (attiva, ha holdings): il "phantom" apparente è in realtà il valore crypto bloccato in open lots — non è un bug.

## Diagnosi probabile

Il grid_bot, durante i 15 cicli buy-sell di MBOX (16-17 apr), ha bookato due-tre
sells contro lo **stesso lotto** (FIFO queue desync). Ricostruendo dalla formula
`cost_basis = (revenue − realized_pnl − sell_fee) / 1.00075` si vede che:

- Sell #13 e Sell #14 (entrambe 932.8 MBOX) → `implied_buy_price` = 0.0134,
  ma c'è **un solo buy** a quel prezzo in DB (B15, 932.8 @ 0.0134).
- Sell #15 (736.3 MBOX) → ancora implied 0.0134, consumando "ombra" dello stesso lotto.

Il lotto reale non ancora consumato era B13 (892.8 @ 0.014) ma il bot non l'ha mai
visto come aperto al momento di questi sell.

## Root cause ipotetica

Desincronizzazione `_pct_open_positions` (coda runtime del grid_bot) dai dati
storici DB. Possibili trigger:

1. Restart del grid_bot durante recovery — la ricostruzione da DB ha saltato
   o duplicato un lotto.
2. Race condition tra un sell in flight e l'append di un buy alla coda.
3. Sessione 36c/36e con molti restart ravvicinati → finestra di vulnerabilità.

Non riproducibile senza rilanciare MBOX in condizioni identiche.

## Impatto contabile

- **Net Worth dashboard**: CORRETTO (calcolato da cash + holdings + skim − initial,
  non dipende dal realized_pnl per-trade).
- **Sub-line "realized +$21.38"** nel Total P&L di /tf: sovrastimata del phantom profit.
  Non è fonte di verità autoritativa.
- **Skim Reserve**: contiene $0.19 "immateriali" dovuti al phantom skim MBOX.
  Visibile nel +$0.19 di surplus quando si fa `sum(skim) − 0.30 × sum(realized_net_corretto)`.
- **tf_floating per MBOX**: -$0.18 nel breakdown di Phase 1 (corretto riflesso
  del fatto che MBOX ha consumato più cash di quanto abbia generato).

## Decisione

**Opzione 1 — Lasciare stare**. Motivi:

- L'entità è pulviscolo ($0.19).
- Il sistema è self-healing: quando MBOX sarà nuovamente allocata dal TF, lo stato
  del nuovo grid_bot è ricostruito da zero via `recover_from_db`. Un eventuale
  desync sarebbe isolato alla nuova sessione, non eredita dalla precedente.
- Il `tf_floating` del 36g Phase 1 riflette il cash flow reale (−$0.18), non il
  phantom. Quindi il compound non è inquinato dal phantom skim.

Non si corregge `reserve_ledger` (scarterebbe la traccia audit) né si riapre il
bot recovery (servirebbe riproduzione, scope largo).

## Cosa fare se risuccede

Se un'altra coin mostra `phantom_profit >> 0` in audit futuri:

1. Rieseguire la query di [brief 36j](briefresolved.md/brief_36j_mbox_phantom_skim.md)
   (sezione "Gap analysis") contro i trades del symbol interessato.
2. Se il gap supera $1-2, aprire brief dedicato con log orchestrator del periodo
   in cui la coin era attiva — cercare restart/recovery anomali.
3. Prioritizzare il fix `recover_from_db` in grid_bot se il pattern ricorre.

## Query di verifica (riutilizzabile)

```sql
WITH tf_summary AS (
  SELECT symbol,
         SUM(cost) FILTER (WHERE side='sell')              AS received,
         SUM(cost) FILTER (WHERE side='buy')               AS invested,
         SUM(realized_pnl) FILTER (WHERE side='sell')      AS realized_net,
         SUM(fee)                                          AS fees_all,
         SUM(amount) FILTER (WHERE side='buy')
           - SUM(amount) FILTER (WHERE side='sell')        AS net_holdings
  FROM trades
  WHERE managed_by='trend_follower' AND config_version='v3'
  GROUP BY symbol
)
SELECT symbol,
       ROUND((received - invested)::numeric, 4) AS gross_cash_flow,
       ROUND(realized_net::numeric, 4)          AS realized_net,
       ROUND((realized_net + fees_all - (received - invested))::numeric, 4)
         AS phantom_profit,
       net_holdings
FROM tf_summary
ORDER BY phantom_profit DESC NULLS LAST;
```

## Files NON modificati in questo brief

Nessuno. Brief di sola documentazione.
