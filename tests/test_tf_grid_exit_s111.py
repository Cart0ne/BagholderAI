"""
S111 — tf-grid exit logic: trailing stop replaces Profit Lock.

Board+Max decision (2026-06-28, estemporanea): for tf_grid coins the only
auto-exits are (1) a trailing stop (price-based, per-tick) and (2) SWAP
rotation. The +8% Profit Lock is removed for tf_grid; the bearish signal
exit is NOT implemented (too slow). "Never exit in loss" is absolute.

This pins the behaviours my change touches:
    A. config_sync routes tf_grid → tf_grid_trailing_* columns,
       pure-TF → tf_trailing_* columns.
    B. grid_bot: trailing arms at +activation% and exits −trailing% from the
       peak (in net green); Profit Lock is OFF for tf_grid but unchanged for
       pure-TF; a position in loss never trails out (activation gate).

Run:
    python tests/test_tf_grid_exit_s111.py
    # or: pytest tests/test_tf_grid_exit_s111.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.timeutils import utcnow
from bot.grid_runner.config_sync import _sync_config_to_bot


# ----------------------------------------------------------------------
# Scaffolding (mirrors test_accounting_avg_cost / test_config_sync_chain_s109)
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
    """Stand-in for SupabaseConfigReader (mirrors test_config_sync_chain_s109)."""
    def __init__(self, config=None, trend=None):
        self._config = config or {}
        self._trend = trend or {}
    def get_config(self, symbol):
        return dict(self._config)
    def get_trend_config_value(self, key):
        return self._trend.get(key)


SYMBOL = "TEST/USDT"


def _make_bot(managed_by):
    """GridBot with a real open position (avg 10, holdings 1.0), mocks only.

    sell_pct is set very high so the normal grid sell never fires in the
    test price range — this isolates the trailing/profit-lock exits.
    """
    from bot.grid.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol=SYMBOL,
        capital=100.0,
        buy_pct=1.0,
        sell_pct=100.0,           # huge → no normal grid sell in [9, 11]
        strategy="A",
    )
    bot._exchange_filters = None
    bot.managed_by = managed_by
    bot.tf_exit_after_n_enabled = False   # avoid DB query in gain-saturation
    bot.idle_reentry_hours = 0.0          # disable idle re-entry/recalibrate
    bot.setup_grid(current_price=10.0)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 10.0
    bot.state.realized_pnl = 0.0
    bot.state.total_invested = 10.0
    bot.state.total_received = 0.0
    bot._pct_last_buy_price = 10.0        # buy_trigger 9.9 → no buy at ≥10
    bot._last_sell_price = 0.0
    bot._last_trade_time = utcnow()
    bot._trailing_peak_price = 0.0
    # latches off
    bot._stop_buy_active = False
    bot._gain_saturation_triggered = False
    bot._trailing_stop_triggered = False
    bot._stop_loss_triggered = False
    bot._take_profit_triggered = False
    bot._profit_lock_triggered = False
    bot.pending_liquidation = False
    return bot


# ----------------------------------------------------------------------
# A. config_sync trailing-column routing
# ----------------------------------------------------------------------

def test_tf_grid_reads_tf_grid_trailing_columns():
    from bot.grid.grid_bot import GridBot
    bot = GridBot(None, MockTradeLogger(), MockPortfolioManager(),
                  MockPnLTracker(), symbol=SYMBOL, capital=100.0,
                  buy_pct=1.0, sell_pct=1.0, strategy="A")
    reader = FakeConfigReader(
        config={"managed_by": "tf_grid"},
        trend={
            "tf_trailing_stop_activation_pct": 1.5,
            "tf_trailing_stop_pct": 2.0,
            "tf_grid_trailing_activation_pct": 5.0,
            "tf_grid_trailing_stop_pct": 4.0,
        },
    )
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.managed_by == "tf_grid"
    # tf_grid bot must pick up the WIDE tf_grid_* values, not the tf_* ones
    assert bot.tf_trailing_stop_activation_pct == 5.0
    assert bot.tf_trailing_stop_pct == 4.0


def test_tf_pure_reads_tf_trailing_columns():
    from bot.grid.grid_bot import GridBot
    bot = GridBot(None, MockTradeLogger(), MockPortfolioManager(),
                  MockPnLTracker(), symbol=SYMBOL, capital=100.0,
                  buy_pct=1.0, sell_pct=1.0, strategy="A")
    reader = FakeConfigReader(
        config={"managed_by": "tf"},
        trend={
            "tf_trailing_stop_activation_pct": 1.5,
            "tf_trailing_stop_pct": 2.0,
            "tf_grid_trailing_activation_pct": 5.0,
            "tf_grid_trailing_stop_pct": 4.0,
        },
    )
    _sync_config_to_bot(reader, bot, SYMBOL)
    assert bot.managed_by == "tf"
    # pure-TF keeps the original tf_* columns
    assert bot.tf_trailing_stop_activation_pct == 1.5
    assert bot.tf_trailing_stop_pct == 2.0


# ----------------------------------------------------------------------
# B. grid_bot trailing + profit-lock gating
# ----------------------------------------------------------------------

def test_trailing_arms_and_exits_for_tf_grid():
    bot = _make_bot("tf_grid")
    bot.tf_trailing_stop_activation_pct = 5.0
    bot.tf_trailing_stop_pct = 4.0
    # Climb to +6% → peak 10.6, armed (≥ +5%), but no trigger yet (at the peak).
    t1 = bot.check_price_and_execute(10.6)
    assert bot._trailing_peak_price == 10.6
    assert not bot._trailing_stop_triggered
    assert t1 == []  # nothing sold while rising
    # Drop 4%+ from the peak (10.6 × 0.96 = 10.176) → trailing exit, in green.
    t2 = bot.check_price_and_execute(10.10)
    assert bot._trailing_stop_triggered
    assert any(tr.get("side") == "sell" for tr in t2)  # liquidated


def test_trailing_does_not_arm_below_activation():
    bot = _make_bot("tf_grid")
    bot.tf_trailing_stop_activation_pct = 5.0
    bot.tf_trailing_stop_pct = 4.0
    # Peak only +3% (< +5% activation) → never armed.
    bot.check_price_and_execute(10.3)
    assert bot._trailing_peak_price == 10.3
    assert not bot._trailing_stop_triggered
    # Even a drop afterwards must not fire (activation gate not crossed).
    bot.check_price_and_execute(10.0)
    assert not bot._trailing_stop_triggered


def test_never_exits_in_loss_for_tf_grid():
    bot = _make_bot("tf_grid")
    bot.tf_trailing_stop_activation_pct = 5.0
    bot.tf_trailing_stop_pct = 4.0
    bot._pct_last_buy_price = 5.0  # buy_trigger 4.95 → no buy in the 9.x range
    # Price stays below avg (in loss) → peak never reaches activation.
    bot.check_price_and_execute(9.8)
    bot.check_price_and_execute(9.0)
    assert not bot._trailing_stop_triggered
    assert bot.state.holdings == 1.0  # position untouched — never sold at a loss


def test_profit_lock_off_for_tf_grid():
    bot = _make_bot("tf_grid")
    bot.tf_profit_lock_enabled = True
    bot.tf_profit_lock_pct = 8.0
    bot.tf_trailing_stop_pct = 0.0   # isolate: trailing disabled
    bot.state.realized_pnl = 8.0     # net = 8.0 + 0.6 unrealized = 8.6% of 100
    bot.check_price_and_execute(10.6)
    # tf_grid must IGNORE Profit Lock now (S111) even above +8% net.
    assert not bot._profit_lock_triggered


def test_profit_lock_still_on_for_pure_tf():
    bot = _make_bot("tf")
    bot.tf_profit_lock_enabled = True
    bot.tf_profit_lock_pct = 8.0
    bot.tf_trailing_stop_pct = 0.0
    bot.tf_take_profit_pct = 0.0
    bot.tf_stop_loss_pct = 0.0
    bot.state.realized_pnl = 8.0     # net 8.6% ≥ 8%
    bot.check_price_and_execute(10.6)
    # pure-TF behaviour is unchanged: Profit Lock still fires.
    assert bot._profit_lock_triggered


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
