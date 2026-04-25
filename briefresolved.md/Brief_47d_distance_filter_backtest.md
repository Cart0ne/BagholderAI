# Brief 47d — Historical Backtest: Distance Filter Threshold Optimization

## Context

The TF uses a "distance filter" that blocks entry when a coin's price is more than
`tf_entry_max_distance_pct` above its EMA20. We've been tuning the threshold by feel
(12% → 20% → 17%) with mixed results:

- At 12%: nothing entered. Zero profit, zero risk.
- At 20%: GALA (+$0.80), D (+$0.84), APE (-$0.94 stop-loss). Net: +$0.70.
- At 17%: current setting, no data yet.

We have a counterfactual tracker (47a) collecting forward data, but that takes weeks.
This script answers the same question in hours using historical data from Binance.

## What to Build

A standalone Python script: `scripts/backtest_distance_filter.py`

### Input

- Coin list: all T3 altcoins the scanner currently evaluates
  (pull from the scanner's existing coin list, or hardcode the current set)
- Timeframe: 1h candles, last 90 days (adjustable via CLI arg)
- Thresholds to test: 10%, 12%, 15%, 17%, 20%, 25% (adjustable)

### Logic

For each coin, for each threshold:

1. **Fetch OHLCV** via `exchange.fetch_ohlcv(symbol, '1h', limit=2160)` (90 days × 24h).
   Rate-limit between calls to avoid Binance throttling.
   Cache results locally (JSON or CSV) so re-runs don't re-fetch.

2. **Compute EMA20** on close prices, rolling.

3. **Simulate entries.** Walk through each candle:
   - Compute `distance_pct = ((close - ema20) / ema20) * 100`
   - If `distance_pct > 0` AND `distance_pct <= threshold` AND signal is BULLISH
     (simplification: price > ema20 = bullish, good enough for this test):
     → simulate BUY at close price, allocation = $30 (our typical lot size)
   - If already in position:
     - If unrealized PnL >= +5% → SELL (Profit Lock)
     - If unrealized PnL <= -3% → SELL (stop-loss)
     - Track holding duration in hours
   - Only 1 position per coin at a time (simplification)
   - Apply 0.075% fee on each buy and sell

4. **Record each simulated trade:**
   ```
   symbol, threshold, entry_price, entry_time, entry_distance_pct,
   exit_price, exit_time, exit_reason (profit_lock | stop_loss | end_of_data),
   gross_pnl, net_pnl (after fees), holding_hours
   ```

### Output

**Per-threshold summary table** (print to console + save as CSV):

```
Threshold | Trades | Win Rate | Avg PnL | Total PnL | Avg Hold (h) | Max Drawdown
----------|--------|----------|---------|-----------|--------------|-------------
10%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
12%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
15%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
17%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
20%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
25%       |   ...  |   ...    |   ...   |    ...    |     ...      |    ...
```

**Per-threshold + per-coin breakdown** (CSV only):
Same columns but grouped by coin. This tells us if some coins behave
differently at different thresholds (e.g., memecoins might need tighter
filters than DeFi tokens).

**Win/loss by distance band** (bonus, very useful):
For ALL trades regardless of threshold, bucket by actual entry distance:
```
Distance Band | Trades | Win Rate | Avg PnL
0-5%          |   ...  |   ...    |   ...
5-10%         |   ...  |   ...    |   ...
10-15%        |   ...  |   ...    |   ...
15-20%        |   ...  |   ...    |   ...
20-25%        |   ...  |   ...    |   ...
25%+          |   ...  |   ...    |   ...
```
This is the killer table — it tells us empirically where the sweet spot is.

### Simplifications (acceptable for v1)

- Single position per coin (no multi-lot averaging)
- No cooldown simulation after stop-loss
- "Bullish" = price > EMA20 (skip the full scanner signal logic)
- No skim deduction (we're testing the filter, not the full P&L model)
- Use close prices for entry/exit (no slippage simulation)
- If a position is still open at end of data, mark as `end_of_data` and
  calculate unrealized PnL at last close

### Simplifications NOT acceptable

- DO apply the 0.075% fee per trade — fees matter on small lots
- DO respect 1-position-per-coin — no overlapping entries
- DO use proper EMA calculation (not SMA)

## What NOT to Build

- No dashboard / UI. Console output + CSV files.
- No database writes. This is a standalone analysis script.
- No changes to the live bot.

## Dependencies

- `ccxt` (already installed)
- `pandas` (already installed)
- `numpy` (already installed)
- No new packages needed

## Execution

```bash
cd ~/BagholderAI
source venv/bin/activate
python scripts/backtest_distance_filter.py --days 90 --lot-size 30
```

Optional args:
- `--days 90` (default 90, can do 30 for quick test)
- `--lot-size 30` (default $30)
- `--thresholds 10,12,15,17,20,25` (customizable)
- `--cache` (reuse cached OHLCV data if available)

Output files saved to `scripts/output/`:
- `backtest_summary.csv`
- `backtest_by_coin.csv`
- `backtest_by_distance_band.csv`

## Test Checklist

1. Run with `--days 7` first as a smoke test. Verify output makes sense.
2. Check that EMA20 calculation matches a known source
   (compare first 100 values of BTC EMA20 with TradingView).
3. Verify fee math: $30 buy + $30 sell = $0.045 total fees per round trip.
4. Verify that win = Profit Lock (>=5%) and loss = stop-loss (<=-3%).
5. Run full 90 days. Check that total trade count is plausible
   (order of magnitude: hundreds to low thousands across all coins and thresholds).

## After the Backtest

Share the 3 CSV outputs. The CEO and Board will use the results to:
1. Set the distance filter threshold with empirical backing
2. Decide if different coin categories need different thresholds
3. Compare with forward data from the counterfactual tracker (47a) as it accumulates

This does NOT replace the counterfactual tracker — the tracker validates in real-time
market conditions, the backtest validates on historical data. Together they give us
confidence that the threshold is right.

## Git

```bash
git add -A && git commit -m "47d: distance filter backtest script" && git push
```

No deploy needed — this is a standalone analysis tool, not production code.
