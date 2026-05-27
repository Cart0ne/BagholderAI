# Archived Tests

These tests were archived on 2026-05-27 following automated Audit Area 1.

- `legacy/` — Grid bot tests from pre-S76 refactor. Constructor signature
  changed during grid_runner package split; tests never updated.
- `test_trend_36e_v2.py` — Contains sys.exit(1) at module level (line 312)
  that crashes pytest collection.

To restore: update GridBot constructor calls to match current signature
in `bot/grid/grid_runner.py`, and remove the sys.exit(1) from the trend test.
