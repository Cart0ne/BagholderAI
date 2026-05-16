"""
Brief 79a (S79 2026-05-16) — SWEEP / LAST SHOT slippage buffer test.

When the bot enters SWEEP or LAST SHOT path (`cost = cash_before * (1 - SLIPPAGE_BUFFER_PCT)`),
the cost spent must be reduced by HardcodedRules.SLIPPAGE_BUFFER_PCT (3% default), so
Binance fill_price slippage cannot push the actual cost above USDT free and trigger
-2010 INSUFFICIENT_FUNDS on mainnet.

3 scenarios:
  (a) normal buy: cash >= standard_cost AND remaining_after >= standard_cost → cost = standard_cost (no buffer)
  (b) SWEEP: cash >= standard_cost AND 0 < remaining_after < standard_cost → cost = cash_before * (1 - 0.03)
  (c) LAST SHOT: MIN_LAST_SHOT_USD <= cash < standard_cost → cost = cash_before * (1 - 0.03)

Run:
    python tests/test_sweep_slippage_buffer.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def make_bot(capital=150.0, capital_per_trade=25.0):
    """GridBot in paper mode (no exchange) — matches test_accounting_avg_cost.py pattern."""
    from bot.grid.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="TEST/USDT",
        capital=capital,
        buy_pct=1.0,
        sell_pct=1.0,
        strategy="A",
    )
    bot._exchange_filters = None
    bot.managed_by = "tf"  # bypass strategy-A buy-above-avg guard
    bot.tf_exit_after_n_enabled = False
    bot.setup_grid(current_price=1.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.realized_pnl = 0.0
    bot.state.daily_realized_pnl = 0.0
    bot.state.total_invested = 0.0
    bot.state.total_received = 0.0
    bot.state.total_fees = 0.0
    bot._pct_last_buy_price = 0.0
    bot.capital_per_trade = capital_per_trade
    bot._stop_buy_active = False
    bot._gain_saturation_triggered = False
    bot._trailing_stop_triggered = False
    bot._stop_loss_triggered = False
    bot._take_profit_triggered = False
    bot._profit_lock_triggered = False
    bot.pending_liquidation = False
    bot.min_profit_pct = 0
    return bot


def assert_close(actual, expected, tol=1e-6, label=""):
    if abs(actual - expected) > tol:
        raise AssertionError(
            f"{label}: expected {expected!r}, got {actual!r} (diff {actual-expected:+.10f})"
        )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_a_normal_buy_no_buffer():
    """cash >> standard_cost → path normale, cost = standard_cost intero."""
    from config.settings import HardcodedRules
    print("=" * 70)
    print("TEST A: normal buy (cash $150, standard $25) → cost=$25, NO buffer")
    print("=" * 70)
    bot = make_bot(capital=150.0, capital_per_trade=25.0)
    # cash_before = 150 - 0 + 0 = 150 → remaining_after = 125 >= 25 → path normale
    bot._execute_percentage_buy(price=1.0)
    last_trade = bot.trade_logger.trades[-1]
    cost_spent = last_trade["cost"]
    assert_close(cost_spent, 25.0, label="normal buy spends standard_cost")
    print(f"  cost spent = ${cost_spent:.4f} (expected $25.00) ✓")
    print(f"  buffer NOT applied — path normale ✓")


def test_b_sweep_with_buffer():
    """0 < remaining_after < standard_cost → SWEEP con buffer 3%."""
    from config.settings import HardcodedRules
    print("=" * 70)
    print("TEST B: SWEEP path (cash $40, standard $25) → cost = $40 × 0.97 = $38.80")
    print("=" * 70)
    bot = make_bot(capital=150.0, capital_per_trade=25.0)
    # Pre-loadiamo total_invested per simulare cassa residua di $40
    # cash_before = 150 - 110 + 0 = 40 → remaining_after = 40-25 = 15 → 0 < 15 < 25 → SWEEP
    bot.state.total_invested = 110.0
    bot.state.holdings = 110.0  # phantom holdings, irrilevante per il buy guard
    bot.state.avg_buy_price = 1.0

    expected_cost = 40.0 * (1 - HardcodedRules.SLIPPAGE_BUFFER_PCT)

    bot._execute_percentage_buy(price=1.0)
    last_trade = bot.trade_logger.trades[-1]
    cost_spent = last_trade["cost"]
    assert_close(cost_spent, expected_cost, label="SWEEP applies buffer")
    print(f"  cash_before = $40.00")
    print(f"  cost spent  = ${cost_spent:.4f} (expected ${expected_cost:.4f}) ✓")
    print(f"  buffer = {HardcodedRules.SLIPPAGE_BUFFER_PCT*100:.1f}% applied ✓")


def test_c_last_shot_with_buffer():
    """MIN_LAST_SHOT_USD <= cash < standard_cost → LAST SHOT con buffer 3%."""
    from config.settings import HardcodedRules
    print("=" * 70)
    print("TEST C: LAST SHOT path (cash $10, standard $25) → cost = $10 × 0.97 = $9.70")
    print("=" * 70)
    bot = make_bot(capital=150.0, capital_per_trade=25.0)
    # cash_before = 150 - 140 = 10 → 10 < 25 (standard) e 10 >= 5 (MIN_LAST_SHOT) → LAST SHOT
    bot.state.total_invested = 140.0
    bot.state.holdings = 140.0
    bot.state.avg_buy_price = 1.0

    expected_cost = 10.0 * (1 - HardcodedRules.SLIPPAGE_BUFFER_PCT)

    bot._execute_percentage_buy(price=1.0)
    last_trade = bot.trade_logger.trades[-1]
    cost_spent = last_trade["cost"]
    assert_close(cost_spent, expected_cost, label="LAST SHOT applies buffer")
    print(f"  cash_before = $10.00 (between MIN_LAST_SHOT $5 and standard $25)")
    print(f"  cost spent  = ${cost_spent:.4f} (expected ${expected_cost:.4f}) ✓")
    print(f"  buffer = {HardcodedRules.SLIPPAGE_BUFFER_PCT*100:.1f}% applied ✓")


def test_d_below_min_last_shot_skip():
    """cash < MIN_LAST_SHOT_USD → buy skippato, no trade."""
    print("=" * 70)
    print("TEST D: cash $3 < MIN_LAST_SHOT $5 → no buy (skip)")
    print("=" * 70)
    bot = make_bot(capital=150.0, capital_per_trade=25.0)
    # cash_before = 150 - 147 = 3 → < MIN_LAST_SHOT $5 → skip
    bot.state.total_invested = 147.0
    bot.state.holdings = 147.0
    bot.state.avg_buy_price = 1.0

    trades_before = len(bot.trade_logger.trades)
    result = bot._execute_percentage_buy(price=1.0)
    trades_after = len(bot.trade_logger.trades)

    assert result is None, "buy should return None when below MIN_LAST_SHOT_USD"
    assert trades_after == trades_before, "no trade should be logged"
    print(f"  cash_before = $3.00 < $5 → buy skipped ✓")
    print(f"  trades logged: unchanged ({trades_before}) ✓")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Brief 79a — SWEEP/LAST SHOT slippage buffer (S79 2026-05-16)")
    print("=" * 70 + "\n")

    test_a_normal_buy_no_buffer()
    print()
    test_b_sweep_with_buffer()
    print()
    test_c_last_shot_with_buffer()
    print()
    test_d_below_min_last_shot_skip()

    print("\n" + "=" * 70)
    print("All tests passed ✓")
    print("=" * 70)
