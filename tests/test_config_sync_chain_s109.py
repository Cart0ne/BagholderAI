"""
S109 — Integration test: Supabase config → live bot reader chain (gap S76).

`bot/grid_runner/config_sync.py::_sync_config_to_bot` is the single point
where values edited in the dashboard / written by Sherpa (Supabase
bot_config + trend_config) reach the running GridBot. Until now this chain
had NO end-to-end test: if a link breaks (a param changes in the DB but the
bot keeps the old value, or a rename desyncs the field), nothing catches it
before go-live.

This test pins the chain at the six places it can break silently:
    1. strategic params propagate (buy_pct / sell_pct / capital_per_trade)
    2. the rename gotcha: DB `profit_target_pct` → bot `min_profit_pct`
    3. None values are ignored (a missing DB field must NOT zero the bot)
    4. empty config is a no-op (bot unchanged, no crash)
    5. pending_liquidation is monotonic-sticky (a DB poll cannot clear a
       liquidation the bot already flagged)
    6. TF safety params are gated on managed_by ∈ {tf, tf_grid}

It does not re-test every one of the ~20 params (that would be a brittle
mirror of the implementation); it locks the behaviours that are non-obvious
and the ones a refactor is most likely to break.

Run:
    python tests/test_config_sync_chain_s109.py
    # or: pytest tests/test_config_sync_chain_s109.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.grid_runner.config_sync import _sync_config_to_bot


# ----------------------------------------------------------------------
# Test scaffolding (mirrors tests/test_accounting_avg_cost.py)
# ----------------------------------------------------------------------

class MockTradeLogger:
    def __init__(self):
        self.trades = []

    def log_trade(self, **kwargs):
        self.trades.append(kwargs)
        return kwargs


class MockPortfolioManager:
    def update_position(self, **kwargs):
        return kwargs

    def get_portfolio(self):
        return []

    def get_total_allocation(self):
        return 0


class MockPnLTracker:
    def record_daily(self, **kwargs):
        return kwargs

    def get_daily_pnl_today(self):
        return 0


class FakeConfigReader:
    """Stand-in for SupabaseConfigReader.

    `get_config` returns the bot_config dict for the symbol (empty dict =
    "not found", which the real reader does for unknown symbols).
    `get_trend_config_value` reads a single trend_config field or None.
    Mirrors config/supabase_config.py:121-135.
    """

    def __init__(self, config=None, trend=None):
        self._config = config or {}
        self._trend = trend or {}

    def get_config(self, symbol):
        return dict(self._config)

    def get_trend_config_value(self, key):
        return self._trend.get(key)


SYMBOL = "TEST/USDT"


def make_bot():
    """Fresh GridBot with mock collaborators (no exchange, no DB)."""
    from bot.grid.grid_bot import GridBot
    return GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol=SYMBOL,
        capital=500.0,
        buy_pct=1.0,
        sell_pct=1.0,
        strategy="A",
    )


# ----------------------------------------------------------------------
# 1. strategic params propagate end-to-end
# ----------------------------------------------------------------------

def test_strategic_params_propagate():
    bot = make_bot()
    reader = FakeConfigReader({
        "buy_pct": 0.7,
        "sell_pct": 1.3,
        "capital_per_trade": 42.0,
        "skim_pct": 25.0,
        "idle_reentry_hours": 5.5,
    })
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.buy_pct == 0.7
    assert bot.sell_pct == 1.3
    assert bot.capital_per_trade == 42.0
    assert bot.skim_pct == 25.0
    assert bot.idle_reentry_hours == 5.5


# ----------------------------------------------------------------------
# 2. the rename gotcha: DB profit_target_pct → bot.min_profit_pct
# ----------------------------------------------------------------------

def test_profit_target_maps_to_min_profit_pct():
    bot = make_bot()
    bot.min_profit_pct = 0.5
    reader = FakeConfigReader({"profit_target_pct": 2.5})
    _sync_config_to_bot(reader, bot, SYMBOL)
    # The DB column is named profit_target_pct; the bot field is
    # min_profit_pct. If this mapping ever drifts, the dashboard's
    # "min profit" control silently stops working.
    assert bot.min_profit_pct == 2.5


# ----------------------------------------------------------------------
# 3. None values must be ignored (missing field must not zero the bot)
# ----------------------------------------------------------------------

def test_none_values_are_ignored():
    bot = make_bot()
    bot.buy_pct = 0.9
    bot.sell_pct = 1.1
    bot.stop_buy_drawdown_pct = 30.0
    reader = FakeConfigReader({
        "buy_pct": None,
        "sell_pct": None,
        "stop_buy_drawdown_pct": None,
    })
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.buy_pct == 0.9
    assert bot.sell_pct == 1.1
    assert bot.stop_buy_drawdown_pct == 30.0


# ----------------------------------------------------------------------
# 4. empty config is a no-op (bot unchanged, no crash)
# ----------------------------------------------------------------------

def test_empty_config_is_noop():
    bot = make_bot()
    bot.buy_pct = 0.8
    bot.sell_pct = 1.2
    bot.min_profit_pct = 1.5
    snapshot = (bot.buy_pct, bot.sell_pct, bot.min_profit_pct)
    reader = FakeConfigReader({})  # get_config → {} → early return
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert (bot.buy_pct, bot.sell_pct, bot.min_profit_pct) == snapshot


# ----------------------------------------------------------------------
# 5. pending_liquidation is monotonic-sticky
# ----------------------------------------------------------------------

def test_pending_liquidation_sticky_true_wins():
    # bot already flagged itself for liquidation; a stale DB row saying
    # False must NOT clear it.
    bot = make_bot()
    bot.pending_liquidation = True
    reader = FakeConfigReader({"pending_liquidation": False})
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.pending_liquidation is True


def test_pending_liquidation_db_can_set_true():
    # DB can still raise the flag when the bot hasn't.
    bot = make_bot()
    assert bot.pending_liquidation is False
    reader = FakeConfigReader({"pending_liquidation": True})
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.pending_liquidation is True


# ----------------------------------------------------------------------
# 6. TF safety params are gated on managed_by
# ----------------------------------------------------------------------

def test_tf_params_ignored_for_grid_bot():
    bot = make_bot()  # managed_by defaults to "grid"
    default_slp = bot.tf_stop_loss_pct
    reader = FakeConfigReader(
        config={},  # no managed_by override → stays "grid"
        trend={"tf_stop_loss_pct": 99.0, "tf_take_profit_pct": 88.0},
    )
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.managed_by == "grid"
    assert bot.tf_stop_loss_pct == default_slp  # untouched


def test_tf_params_applied_for_tf_grid_bot():
    bot = make_bot()
    reader = FakeConfigReader(
        config={"managed_by": "tf_grid"},
        trend={"tf_stop_loss_pct": 15.0, "tf_take_profit_pct": 40.0},
    )
    _sync_config_to_bot(reader, bot, SYMBOL)
    # The DB flips managed_by → tf_grid, and the same tick must then pick
    # up the TF thresholds (the chain order matters: managed_by is read
    # before the TF block).
    assert bot.managed_by == "tf_grid"
    assert bot.tf_stop_loss_pct == 15.0
    assert bot.tf_take_profit_pct == 40.0


# ----------------------------------------------------------------------
# Standalone runner
# ----------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
