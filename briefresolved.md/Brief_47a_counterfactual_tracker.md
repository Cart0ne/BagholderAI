# Brief 47a — Counterfactual Tracker for Distance Filter Skips

## Context

The distance filter (deployed in 45e v2) blocks TF entries when a coin's price is
more than `tf_entry_max_distance_pct` above its EMA20. The filter works — it blocked
MOVR-type entries overnight and GALA (entered at ~12%) did two Profit Locks.

**Problem:** we don't know if the blocked coins would have been profitable or not.
We need the counterfactual data to tune the threshold intelligently.

## What to Build

### Step 1 — Add `skip_price` to existing skip events

**File:** wherever `entry_distance_skip` events are logged (likely in the scanner or allocator).

Currently the event details contain:
```json
{"path": "ALLOCATE", "distance_pct": 14.53, "max_distance_pct": 12}
```

Add the current price at time of skip:
```json
{"path": "ALLOCATE", "distance_pct": 14.53, "max_distance_pct": 12, "skip_price": 0.01234}
```

The price is already available in the scanner context (it's used to compute distance_pct).
No new API calls needed.

### Step 2 — Add `skip_ema20` to the same event

Also log the EMA20 value at skip time for completeness:
```json
{"path": "ALLOCATE", "distance_pct": 14.53, "max_distance_pct": 12, "skip_price": 0.01234, "skip_ema20": 0.01078}
```

### Step 3 — Counterfactual check job

Create a lightweight function (can live in the scanner or as a standalone utility called
after each scan) that:

1. Queries `bot_events_log` for `entry_distance_skip` events older than 24h
   that have a `skip_price` in details but no matching `counterfactual_checked` flag.
2. For each unique (symbol, date) pair, fetches the **current price** via ccxt
   (the scanner already has the exchange connection open).
3. Inserts a row in a new table `counterfactual_log`:

```sql
CREATE TABLE counterfactual_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    skip_timestamp TIMESTAMPTZ NOT NULL,
    skip_price NUMERIC NOT NULL,
    skip_ema20 NUMERIC NOT NULL,
    skip_distance_pct NUMERIC NOT NULL,
    check_price NUMERIC NOT NULL,
    hours_elapsed NUMERIC NOT NULL,
    delta_pct NUMERIC NOT NULL  -- ((check_price - skip_price) / skip_price) * 100
);
ALTER TABLE counterfactual_log DISABLE ROW LEVEL SECURITY;
```

4. To avoid checking the same skip multiple times, after writing to
   `counterfactual_log`, update the original event's details to add
   `"counterfactual_checked": true`, OR simply filter by:
   `WHERE NOT EXISTS (SELECT 1 FROM counterfactual_log WHERE symbol = e.symbol AND skip_timestamp = e.created_at)`

### Step 4 — Run frequency

Run the counterfactual check **once per scan cycle** (currently every hour).
Only process skips that are between 24h and 48h old (so we get a consistent
24h window, and don't re-check older ones).

## What NOT to Build

- No dashboard UI. We query this via SQL for now.
- No alerts. Pure data collection.
- No changes to the filter logic itself — threshold stays human-controlled.

## Test Checklist

1. Trigger a scan with a coin above the distance threshold.
   Verify the event details now include `skip_price` and `skip_ema20`.
2. Manually backdate a test event to 25h ago.
   Run the counterfactual check. Verify a row appears in `counterfactual_log`
   with correct `delta_pct`.
3. Run the check again. Verify the same skip is NOT processed twice.
4. Check that the scanner's normal flow is unaffected (no extra latency,
   no crashes if ccxt returns an error for a delisted coin).

## Execution

```bash
cd ~/BagholderAI
source venv/bin/activate
# implement changes, test, then:
git add -A && git commit -m "47a: counterfactual tracker for distance filter skips" && git push
```

On Mac Mini after push:
```bash
cd ~/BagholderAI && git pull
# restart orchestrator
```
