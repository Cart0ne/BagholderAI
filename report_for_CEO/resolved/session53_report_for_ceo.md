# Session 53 — Report for CEO

**Data:** 2026-05-01
**Durata:** ~giornata intera (compactazione conversazione a metà)
**Esiti:** 7 commit deployati, fix bot critico in produzione, homepage rinnovata pre-HN

## Riepilogo executive

Sessione concentrata sul **rendere i numeri pubblici onesti prima del lancio HN** e sul **rinnovo della homepage** per renderla più impattante. Lungo la strada è emerso un bug FIFO nel bot che gonfiava il `realized_pnl` di +$17.74 cumulativo — fixato e in produzione.

## 1. Allineamento numeri (FIFO truth)

### 1.1 Discovery

Indagando il dubbio di Max ("se realizzato $63 e aperte −$10 dovrebbe fare $53, perché Total P&L è $39?") abbiamo scoperto che **`trades.realized_pnl` nel DB era sopra-stimato** di ~$17.74 cumulativi su 458 sell v3.

Catena di verifiche:
- Grid: DB raw $59.20, FIFO ground truth $41.46 (gap +$17.74)
- TF e Grid sommati identità: Realized FIFO $40.69 + Unrealized FIFO −$10.20 = +$30.49 ≈ Net Worth $630 − $600 ✓
- L'identità FIFO **chiude perfettamente** quando ricalcoli client-side; non chiudeva con i dati raw del DB

### 1.2 Root cause (fix 53a)

`_execute_percentage_sell` ([grid_bot.py:1747](bot/strategies/grid_bot.py#L1747)) computava:

```
cost_basis = amount × first_lot.price
self._pct_open_positions.pop(0)
```

Quando un singolo sell attraversava 2+ lotti (last-lot logic con `holdings > first_lot.amount`), il bot:
1. Caricava il prezzo del primo lotto su tutto l'`amount`, ignorando i lotti successivi
2. Faceva pop di un solo lotto, lasciando "fantasmi" in coda con quantità non venduta

I lotti fantasma poi entravano come "primo lotto" nei sell successivi, biasando ancora il cost basis. Effetto cumulativo: +$17.74.

Path "fixed-grid" (`_execute_sell` riga 833) aveva un bug simile (usa `avg_buy_price`) ma è **dead code**: tutti i bot v3 sono `grid_mode=percentage`. Lasciato intatto.

### 1.3 Fix deployato (commit `6b4b4d1`)

Sostituito con walk multi-lotto:
- `cost_basis = Σ (lot.amount × lot.price)` su tutti i lotti consumati
- Coda drenata in ordine, lotti parziali shrunk in place
- Invariante `sum(lot.amount) == state.holdings` ora reggono trade-by-trade

5 unit-test in `tests/test_pct_sell_fifo.py`:
- single-lot sanity, multi-lot full consume, sell crosses boundary
- queue/holdings invariant under sequential sells
- cumulative pnl drift zero vs ground truth indipendente

Tutti verdi. Test esistenti `test_grid_bot.py` 1-6 verdi (test 7 era già flaky pre-fix).

### 1.4 Backfill DB

Deliberatamente **NOT** fatto. I 458 sell storici restano biasati nel DB ma le 4 dashboard pubbliche (`/`, `/dashboard`, `/grid`, `/tf`) ricostruiscono FIFO client-side. Il bot da ora scrive corretto. Convergenza naturale.

## 2. Fix dashboard FIFO (commit serie `6bfb644` → `3fd5b08`)

Cinque file modificati prima del fix bot per rendere subito onesti i numeri pubblici:

| Commit | File | Cosa |
|---|---|---|
| `6bfb644` | dashboard.html, grid.html, tf.html | Stat cards: FIFO recalc per Realized totale |
| `e7860ba` | dashboard.html | Cumulative P&L chart + Daily P&L bars: FIFO daily breakdown |
| `3fd5b08` | index.html | Homepage stat "+$59 realized P&L" → FIFO ricalcolato (~$41) |

**Effetto netto**: chiunque visiti il sito ora vede numeri internamente coerenti tra loro e con la realtà cassa-flusso.

## 3. Homepage rinnovata (3 commit)

### 3.1 Sezione "The AI Bots" (commit `29b48d4`)

4 trading-card-style cards live sotto "The Team":
- **GRID BOT** (verde, attivo): mixer DJ animato (3 monete × buy/sell faders), mascotte seduto + tazza caffè
- **TREND FOLLOWER** (ambra, attivo): radar che ruota, mascotte con binocoli
- **SENTINEL** (blu, locked): silhouette + "monitors positions, halts on drawdown"
- **SHERPA** (rosso, locked): silhouette + "coordinates all active bots"

Stat per card: PATIENCE, SPEED, CAPITAL, WINS, LOSSES. W/L live da Supabase. Identifier "● live · supabase" / "◌ fallback data".

Mascot SVG generati client-side con `shade()` helper per gradient 3D. Animazioni CSS keyframes pure. Materiale design preso dal handoff bundle Claude Design (`/Users/max/Desktop/BagHolderAI/Design/design_handoff_team_cards`), portato a vanilla HTML/CSS/JS.

### 3.2 Compaction homepage (commit `854d6b8`)

Rimossi: TF banner, framing box verde. Hero text-align center. Headline su una riga. Desc su una riga. CTA spostati sotto AI Bots. Padding cross-page ridotti (40→24px su 11 pagine pubbliche). Team card più compatte.

Risultato: ~150-200px in meno di scroll prima delle bot cards.

### 3.3 Stats strip onesto (commit `3fd5b08`)

- "trades executed" → "orders executed" (937 = buy + sell, non solo sell)
- realized P&L → ricalcolato FIFO ($59 → $41)
- "LIVE / trading now" → "PAPER / trading now" (più onesto: paper Binance testnet, no live capital)

### 3.4 Rename /admin → /grid (commit `2bfab84`)

Ora che TF ha la sua dashboard separata, "Admin" non era più accurato. Rinominato a `/grid` (Grid control panel). Badge "GRID — private". Link aggiornato in tf.html. Nessun redirect (URL pulito senza eredità).

## 4. Effetti operativi

- **Bot sul Mac Mini**: restartato alle 09:34 dopo deploy `6b4b4d1`. Pid 80138, 6 grid bots + TF spawned, Telegram restart notification inviata. Reconciler 1 dust skip atteso.
- **Vercel**: tutti i deploy automatici, niente intervento manuale.
- **Stato sito pubblico**: pronto per HN. I 4 punti che HN poteva contestare ("ma realized non quadra con W/L", "trades executed include i buy", "LIVE è ambiguo", "Admin non è admin se TF è separato") risolti.

## 5. Memoria salvata

`project_fifo_fix_53a.md` aggiunta a `MEMORY.md`. Nota chiave per future investigazioni: trade pre-2026-05-01 hanno bias DB; dashboards correggono client-side.

## 6. Cosa NON è stato fatto (consapevolmente)

- **Backfill 458 sell storici**: troppo invasivo per ROI marginale, dashboards correggono già
- **Fix `_execute_sell`** (path fixed-grid): dead code, lasciato intatto
- **Centratura del badge "paper trading" colore verde** (brief diceva verde, in realtà CSS è giallo): non toccato, brief si concentrava sul centrare
- **Test Daily P&L Reset** in `test_grid_bot.py` (test 7 flaky): non era nello scope, lasciato per dopo

## 7. Domande aperte / da decidere

1. **Brief 36h "Haiku sees TF"**: ancora in `config/`, non implementato. Da schedulare?
2. **Homepage badge color**: il brief diceva "green badge", il CSS attuale lo rende giallo. Ricoloriamo o lasciamo? (Visivamente funziona così, ma se vogliamo onestà 1:1 col brief va corretto.)
3. **Roadmap.html**: aggiornare con v1.37 = sessione 53 (FIFO fix + homepage rifresh + AI Bots section)?

## Numeri attuali (2026-05-01 09:34 CET)

- Net Worth: $630.50 (su $600 base = +5.08% in ~32 giorni)
- Realized FIFO: +$40.69 (Grid +$49.15, TF −$8.46)
- Unrealized FIFO: −$10.20
- Identity check: +$40.69 − $10.20 = +$30.49 ≈ Net Worth − $600 ✓
- 937 orders eseguiti (476 buy + 461 sell)
- Bot attivi: 3 manual (BONK/BTC/SOL) + 3 TF (LUNC/DOGE/POL)
