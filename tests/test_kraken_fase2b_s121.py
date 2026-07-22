"""
S121 (K.1 Fase 2b — kraken-2b-bundle) — sell-trigger/floor double-count fix.

Three things, all Strada A (fix on every venue) except where noted:

  1. grid_sell_trigger_price(): NET-margin trigger. The avg-cost basis already
     includes the buy fee (buy_pipeline cost_for_avg), so the trigger recovers
     ONLY the sell fee: reference×(1+m)/(1−fee). The pre-S121 formula added the
     buy fee a SECOND time (…+fee…) → sold ~1×fee too high. Numeric proof on the
     real 2a numbers (avg $63,991, sell_pct 2%, Kraken 0.8%): $65,796 not $66,313.

  2. current_sell_trigger(): ONE source shared by execution AND every display
     (get_status → terminal/daily_report/Telegram, site widget). Folds the sell
     ladder reference + Adaptive Sell Penalty, so the displayed target == where
     the bot actually sells (pre-S121 get_status showed the naive avg×(1+sell_pct)).

  3. Floor (sell_pipeline) shares the trigger's shape → trigger ≥ floor whenever
     sell_pct ≥ profit_target_pct (no silent stall). Verified behaviourally on
     kraken.

Run:  venv/bin/python3.13 -m pytest tests/test_kraken_fase2b_s121.py -q
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Telegram lib is broken on Python 3.13 (pre-existing env issue) — stub it so
# importing the grid stack doesn't blow up before reaching the code under test.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from bot.grid.grid_bot import GridBot, grid_sell_trigger_price


class MockTradeLogger:
    def __init__(self):
        self.trades = []

    def log_trade(self, **kwargs):
        self.trades.append(kwargs)
        return kwargs


FILTERS = {"lot_step_size": 0.000001, "min_qty": 0.000001, "min_notional": 1.0}


def make_bot(venue="binance", symbol="TEST/USD", fee_rate=None,
             sell_pct=2.0, min_profit_pct=0.0, managed_by="grid"):
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=None,
        pnl_tracker=None,
        venue=venue,
        symbol=symbol,
        capital=1000.0,
        buy_pct=99.0,        # disable buy path in these tests
        sell_pct=sell_pct,
        strategy="A",
        min_profit_pct=min_profit_pct,
    )
    if fee_rate is not None:
        bot.fee_rate = fee_rate
    bot._exchange_filters = dict(FILTERS)
    bot.managed_by = managed_by
    bot.tf_exit_after_n_enabled = False
    bot.idle_reentry_hours = 0.0
    bot.setup_grid(current_price=100.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.total_invested = 0.0
    bot.state.total_received = 0.0
    bot.state.total_fees = 0.0
    bot.state.realized_pnl = 0.0
    bot._pct_last_buy_price = 0.0
    bot._last_sell_price = 0.0
    bot._sell_pct_penalty = 0.0
    bot.capital_per_trade = 50.0
    bot.min_profit_pct = min_profit_pct
    return bot


# ----------------------------------------------------------------------
# 1. Pure function — no double-count, numeric proof
# ----------------------------------------------------------------------

def test_pure_no_double_count_vs_old_formula():
    ref, m, f = 100.0, 2.0, 0.008
    new = grid_sell_trigger_price(ref, m, f)
    old = ref * (1 + m / 100 + f) / (1 - f)          # the pre-S121 buggy formula
    assert new == ref * (1 + m / 100) / (1 - f)
    # The fix removes exactly one buy-fee's worth of over-shoot.
    assert new < old
    assert abs((old - new) - ref * f / (1 - f)) < 1e-9


def test_pure_numeric_proof_2a_lot():
    """Real 2a baseline: avg $63,991, sell_pct 2%, Kraken taker 0.8%."""
    trig = grid_sell_trigger_price(63991.0, 2.0, 0.008)
    assert abs(trig - 65796.2) < 1.0            # NOT $66,313 (old double-count)
    old = 63991.0 * (1 + 0.02 + 0.008) / (1 - 0.008)
    assert abs(old - 65796.2) > 400             # the bug was ~$517 too high


def test_pure_binance_strada_a_shift():
    """Strada A: on binance (fee 0.1%) the fix lowers the trigger ~0.1%."""
    new = grid_sell_trigger_price(100.0, 2.0, 0.001)
    old = 100.0 * (1 + 0.02 + 0.001) / (1 - 0.001)
    assert new < old
    assert (old - new) / old < 0.0015           # ~0.1%, tiny, on paper money


def test_pure_guards():
    assert grid_sell_trigger_price(0.0, 2.0, 0.008) == 0.0
    assert grid_sell_trigger_price(-5.0, 2.0, 0.008) == 0.0
    assert grid_sell_trigger_price(100.0, 2.0, 1.0) == 0.0   # degenerate fee


# ----------------------------------------------------------------------
# 2. current_sell_trigger() — grid fee-buffered, TF plain
# ----------------------------------------------------------------------

def test_grid_current_trigger_is_fee_buffered():
    bot = make_bot(venue="kraken", fee_rate=0.008, sell_pct=2.0)
    bot.state.avg_buy_price = 100.0
    assert abs(bot.current_sell_trigger()
               - grid_sell_trigger_price(100.0, 2.0, 0.008)) < 1e-9


def test_tf_current_trigger_is_plain_no_fee_buffer():
    bot = make_bot(symbol="TEST/USD", managed_by="tf", sell_pct=2.0)
    bot.state.avg_buy_price = 100.0
    # TF keeps the greed-decay TP (avg×(1+threshold)); get_effective_tp drives it.
    thr = bot.get_effective_tp()[0]
    assert abs(bot.current_sell_trigger() - 100.0 * (1 + thr / 100)) < 1e-9


def test_current_trigger_folds_penalty_and_ladder():
    bot = make_bot(venue="kraken", fee_rate=0.008, sell_pct=2.0)
    bot.state.avg_buy_price = 100.0
    bot._sell_pct_penalty = 1.0                 # S98a Adaptive Sell Penalty
    bot._last_sell_price = 110.0                # sell ladder anchor
    # reference = ladder (110), threshold = sell_pct+penalty = 3%
    assert abs(bot.current_sell_trigger()
               - grid_sell_trigger_price(110.0, 3.0, 0.008)) < 1e-9


# ----------------------------------------------------------------------
# 3. display == execution
# ----------------------------------------------------------------------

def test_get_status_matches_execution_trigger():
    bot = make_bot(venue="kraken", fee_rate=0.008, sell_pct=2.0)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    status = bot.get_status()
    trig = bot.current_sell_trigger()
    assert abs(status["sell_trigger"] - trig) < 1e-9
    # just below trigger → no sell; just above → sell (execution honours the
    # SAME number the display shows).
    before = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    bot.check_price_and_execute(current_price=trig * 0.999)
    assert sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell") == before
    bot.check_price_and_execute(current_price=trig * 1.001)
    assert sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell") == before + 1


def test_get_status_reflects_penalty_not_naive_avg():
    """Pre-S121 get_status showed the naive avg×(1+sell_pct); now it folds the
    penalty/ladder like execution — so display and the naive value diverge."""
    bot = make_bot(venue="kraken", fee_rate=0.008, sell_pct=2.0)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    bot._sell_pct_penalty = 2.0
    naive = 100.0 * (1 + bot.sell_pct / 100)
    assert abs(bot.get_status()["sell_trigger"] - bot.current_sell_trigger()) < 1e-9
    assert bot.get_status()["sell_trigger"] > naive     # penalty raises the real target


# ----------------------------------------------------------------------
# 4. trigger ≥ floor — no silent stall
# ----------------------------------------------------------------------

def test_no_stall_trigger_clears_floor_on_kraken():
    """sell_pct 1% > profit_target 0 → the trigger price passes the floor."""
    bot = make_bot(venue="kraken", fee_rate=0.008, sell_pct=1.0, min_profit_pct=0.0)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    trig = bot.current_sell_trigger()
    floor = bot.state.avg_buy_price * (1 + bot.min_profit_pct / 100) / (1 - bot.fee_rate)
    assert trig >= floor
    # a sell fired at the trigger is NOT blocked by the floor (executes)
    out = bot._execute_percentage_sell(trig, sell_amount=0.5)
    assert out is not None
