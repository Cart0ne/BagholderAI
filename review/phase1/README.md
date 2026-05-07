# Grid Bot Refactoring — Phase 1 Review Package

## What this is

Refactoring of a monolithic trading bot ([bot/strategies/grid_bot.py](../../bot/strategies/grid_bot.py),
2242 lines) into focused modules. **ZERO behavior change intended** — pure
code reorganization.

This package was prepared on 2026-05-07 (session 62) as part of brief 62a
(Phase 1: split). It accompanies a single commit that splits `grid_bot.py`
into 6 files. Phase 2 (fix 60c + dust handling) and Phase 3 (clean run)
follow in separate briefs/sessions.

## Architecture

- **Grid bot for crypto trading** (BTC, SOL, BONK on Binance) — paper trading
  today, live trading imminent (€100 LIVE planned ~20 may).
- **FIFO queue** for position management (`_pct_open_positions` list of
  `{amount, price}` lots; oldest lot consumed first on sells).
- **Talks to Supabase (Postgres)** for trade logging (`trades` table) and
  config (`bot_config`). Audit trail in `bot_events_log`.
- **Two grid modes**:
  - `fixed`: pre-computed grid levels at startup, sell at fixed prices
    (legacy v1, kept for tests but not used in production).
  - `percentage`: dynamic, buy when price drops `buy_pct%` from last buy,
    sell when price rises `sell_pct%` from a lot's buy price. Hot path —
    all v3 production bots use this.

## What changed in Phase 1

| Module (new) | Lines | Extracted from `grid_bot.py` |
|---|---|---|
| `fifo_queue.py` | 173 | `verify_fifo_queue` + `replay_trades_to_queue` helper |
| `state_manager.py` | 176 | `init_percentage_state_from_db` + `restore_state_from_db` |
| `dust_handler.py` | 81 | dust pop helpers (split from `_execute_percentage_sell`) |
| `buy_pipeline.py` | 309 | `_execute_buy` + `_execute_percentage_buy` + `activate_sell_level` |
| `sell_pipeline.py` | 749 | `_execute_sell` + `_execute_percentage_sell` + `evaluate_gain_saturation` + `get_effective_tp` + `activate_buy_level` |
| `grid_bot.py` (residual) | 1022 | Coordinator: dataclasses, `__init__`, `setup_grid`, dispatcher `_check_percentage_and_execute`, public API wrappers, `get_status`, `should_reset_grid` |

Total: 2510 lines vs 2242 originally → +268 lines overhead from module
docstrings, cross-module imports, and explicit deviation/TODO markers.

### Convention used for the split

Module functions take `bot: GridBot` as first argument and access state
via `bot.state`, `bot._pct_open_positions`, etc. — same fields the original
methods used via `self`. This was an explicit architectural choice
discussed before the split:
- Pro: zero changes to `_pct_open_positions` access patterns (30+ read
  sites in the codebase).
- Pro: trivial to write thin wrapper methods on `GridBot` that grid_runner
  and tests keep calling.
- Con: not "pure functions" in the strict sense — they have side effects
  on `bot`. Acceptable for Phase 1; Phase 2+ can refine if needed.

## Phase 1 deviations from the brief

### `FIFOQueue` class deferred to Phase 2

Brief §3.1 proposed a `FIFOQueue` class wrapping `_pct_open_positions`.
We extracted only the verify/replay logic as functions and kept
`_pct_open_positions` as a plain list on `GridBot`. A class wrapper would
require touching 30+ read sites in the same commit, raising regression
risk beyond the Phase 1 mandate ("ZERO behaviour change"). The class
will land in Phase 2 alongside the dust + 60c fixes.

Marked in `fifo_queue.py` line 12 with `# TODO 62a (Phase 2)`.

### No other deviations

All other points of the brief (no logic change, no log format change,
no DB API change, no rename of `GridBot` class, no test additions, no
changes outside `bot/strategies/`) are honored.

## What to check

1. **Behavioral equivalence**: does the new code do exactly the same
   thing as the old code? Any logic change = bug. Recommended approach:
   diff each extracted function body against the corresponding lines in
   `before/grid_bot.py`. Comments and indentation should be preserved
   verbatim wherever they appeared.
2. **State management**: is in-memory state (`bot.state.holdings`,
   `bot.state.realized_pnl`, `bot._pct_open_positions`) handled
   identically? Any new code path that mutates state outside the
   existing flow = bug.
3. **Race conditions**: any new timing issues from the split? In
   particular, the wrapper methods on `GridBot` should be 1-line
   delegates — anything else is suspicious.
4. **Edge cases**: dust lots, self-heal (holdings>0 + queue empty),
   last-lot sell-all, empty queue, idle re-entry/recalibrate.
5. **Import/dependency**: are all cross-module calls wired correctly?
   The new module-level imports in `grid_bot.py` are
   `from bot.strategies import fifo_queue, state_manager, buy_pipeline, sell_pipeline`.
   Inside hot paths (e.g. `dust_handler` is imported lazily inside
   `execute_percentage_sell` to avoid circular import — the call site
   uses `from bot.strategies.dust_handler import handle_step_size_dust, handle_economic_dust`).

## Known bugs (intentionally NOT fixed in Phase 1)

These are the bugs the Phase 1 split surfaces but does not fix. They
will be addressed in Phase 2 (brief 62b).

### 60c — Double-call to `_execute_percentage_sell`
Diagnosed in session 62. The loop `for _ in lots_to_sell:` in
`_check_percentage_and_execute` (now in `grid_bot.py` ~line 758)
iterates once per "triggered lot", but on TF bots with Strategy A
"trigger first" reorder, it can call `_execute_percentage_sell` twice
in <1 second. The DB safety trigger `Duplicate trade rejected within 5s`
blocks the 2nd INSERT, but `state.holdings`, `state.realized_pnl`,
`_pct_open_positions` are already mutated for both calls.

Marked: `grid_bot.py` line 758, `sell_pipeline.py` lines 23, 544, 572.

### Dust pop writes audit but no trade (phantom audit)
`_execute_percentage_sell` writes the `sell_fifo_detail` audit BEFORE
calling `log_trade`. If `log_trade` fails (60c case, or any other),
the audit becomes orphaned (written, no matching trade in `trades`).

Marked: `sell_pipeline.py` line 544.

### `verify_fifo_queue` dust filter mismatch (spurious drift)
`verify_fifo_queue` filters `db_queue` for dust (lots below MIN_NOTIONAL)
but doesn't filter `mem_queue` symmetrically. When a real dust pop has
just happened in `_execute_percentage_sell`, mem and db differ by
exactly the dust lot, the verify reads it as drift, rebuilds, and the
loop repeats every cycle.

Marked: `fifo_queue.py` line 96.

### Dust pop is silent in `bot_events_log`
The two pop paths in `dust_handler.py` mutate state without writing any
event to `bot_events_log` nor any trade to `trades`. This is the root
of the queue desync that causes the spurious drift above and the
orphaned audits.

Marked: `dust_handler.py` lines 17-22.

## How to validate

### Diff the modules against the snapshot
```bash
diff before/grid_bot.py after/grid_bot.py | less
```
Every removed block of logic in `before/grid_bot.py` should reappear
verbatim (modulo `self` → `bot`) in one of the new modules
in `after/`.

### Spot-check the public API
```bash
python3.13 -c "
from bot.strategies.grid_bot import GridBot
methods = ['init_percentage_state_from_db', 'verify_fifo_queue',
           'restore_state_from_db', 'setup_grid', 'check_price_and_execute',
           'should_reset_grid', 'get_status', 'evaluate_gain_saturation',
           'set_exchange_filters', '_execute_percentage_buy',
           '_execute_percentage_sell', '_execute_buy', '_execute_sell',
           'get_effective_tp', '_activate_buy_level', '_activate_sell_level']
for m in methods:
    assert hasattr(GridBot, m), f'MISSING: {m}'
print('API surface intact')
"
```

### After deploy on Mac Mini
1. `git pull`
2. Sanity import: `python3.13 -c "from bot.strategies.grid_bot import GridBot; print('OK')"`
3. Restart orchestrator.
4. Monitor for 2h: trade execution normale, niente crash, drift count
   non aumenta in modo anomalo (~5-10/h baseline pre-refactor).
5. Monitor for 48h: la baseline trade count + cumulative realized_pnl
   per simbolo deve continuare a crescere coerentemente.

## Baseline (snapshot 2026-05-07, manual Grid v3)

For the post-deploy equivalence check.

| Symbol | Side | Count | Total Cost | Sum Realized PnL |
|---|---|---|---|---|
| BONK/USDT | buy | 126 | $2,988.17 | — |
| BONK/USDT | sell | 127 | $2,993.07 | $44.24 |
| BTC/USDT | buy | 49 | $2,375.20 | — |
| BTC/USDT | sell | 48 | $2,257.39 | $31.93 |
| SOL/USDT | buy | 52 | $964.44 | — |
| SOL/USDT | sell | 50 | $953.40 | $16.49 |

Drift events (last 7 days): BONK 21, BTC 12, SOL 37 (last seen
2026-05-07 07:33). Post-deploy these should keep growing at similar
cadence — a sudden spike means we introduced a regression.

## Files in this package

```
review/phase1/
├── README.md           # This file
├── before/
│   └── grid_bot.py     # 2242-line snapshot taken before any edits
└── after/
    ├── grid_bot.py     # 1022-line residual coordinator
    ├── fifo_queue.py   # 173 lines
    ├── state_manager.py # 176 lines
    ├── buy_pipeline.py # 309 lines
    ├── sell_pipeline.py # 749 lines
    └── dust_handler.py # 81 lines
```
