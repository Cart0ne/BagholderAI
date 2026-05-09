"""
Quick test: fetch real prices for SOL/USDT and BONK/USDT,
setup grids, and show levels. No DB, no Telegram.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_grid_config, GRID_INSTANCES


def test_config_lookup():
    print("=" * 60)
    print("TEST: Config Lookup")
    print("=" * 60)
    for cfg in GRID_INSTANCES:
        print(f"  {cfg.symbol}: capital=${cfg.capital}, levels={cfg.num_levels}, "
              f"range={cfg.grid_range_pct*100}%, order=${cfg.order_amount}")

    sol = get_grid_config("SOL/USDT")
    assert sol.symbol == "SOL/USDT"
    assert sol.capital == 50.0
    assert sol.num_levels == 10
    assert sol.grid_range_pct == 0.06

    bonk = get_grid_config("BONK/USDT")
    assert bonk.symbol == "BONK/USDT"
    assert bonk.capital == 30.0
    assert bonk.num_levels == 12
    assert bonk.grid_range_pct == 0.08

    unknown = get_grid_config("DOGE/USDT")
    assert unknown.symbol == "BTC/USDT", "Unknown symbol should fallback to BTC"

    print("  ✅ Config lookup OK\n")


def test_grid_setup_sol():
    from bot.grid.grid_bot import GridBot

    cfg = get_grid_config("SOL/USDT")
    # Use a realistic SOL price for offline test
    test_price = 140.50

    print("=" * 60)
    print(f"TEST: Grid Setup — {cfg.symbol} @ ${test_price}")
    print("=" * 60)

    class MockLogger:
        trades = []
        def log_trade(self, **kw): self.trades.append(kw)

    class MockPM:
        def update_position(self, **kw): pass
        def get_portfolio(self): return []
        def get_total_allocation(self): return 0

    class MockPnL:
        def record_daily(self, **kw): pass
        def get_daily_pnl_today(self): return 0

    bot = GridBot(
        exchange=None, trade_logger=MockLogger(),
        portfolio_manager=MockPM(), pnl_tracker=MockPnL(),
        symbol=cfg.symbol, capital=cfg.capital,
        num_levels=cfg.num_levels, range_percent=cfg.grid_range_pct,
    )
    state = bot.setup_grid(test_price)

    base = cfg.symbol.split("/")[0]
    print(f"  Center: ${state.center_price:,.4f}")
    print(f"  Range:  ${state.lower_bound:,.4f} - ${state.upper_bound:,.4f}")
    for lv in state.levels:
        marker = "BUY ↓" if lv.side == "buy" else "SELL ↑"
        amt = f"({lv.order_amount:.6f} {base})" if lv.order_amount > 0 else "(waiting)"
        print(f"    ${lv.price:>10,.4f}  {marker}  {amt}")

    assert len(state.levels) == cfg.num_levels
    assert state.lower_bound < test_price < state.upper_bound
    print(f"  ✅ {cfg.symbol} grid OK\n")


def test_grid_setup_bonk():
    from bot.grid.grid_bot import GridBot

    cfg = get_grid_config("BONK/USDT")
    test_price = 0.00001234

    print("=" * 60)
    print(f"TEST: Grid Setup — {cfg.symbol} @ ${test_price:.8f}")
    print("=" * 60)

    class MockLogger:
        trades = []
        def log_trade(self, **kw): self.trades.append(kw)

    class MockPM:
        def update_position(self, **kw): pass
        def get_portfolio(self): return []
        def get_total_allocation(self): return 0

    class MockPnL:
        def record_daily(self, **kw): pass
        def get_daily_pnl_today(self): return 0

    bot = GridBot(
        exchange=None, trade_logger=MockLogger(),
        portfolio_manager=MockPM(), pnl_tracker=MockPnL(),
        symbol=cfg.symbol, capital=cfg.capital,
        num_levels=cfg.num_levels, range_percent=cfg.grid_range_pct,
    )
    state = bot.setup_grid(test_price)

    base = cfg.symbol.split("/")[0]
    print(f"  Center: ${state.center_price:.8f}")
    print(f"  Range:  ${state.lower_bound:.8f} - ${state.upper_bound:.8f}")
    for lv in state.levels:
        marker = "BUY ↓" if lv.side == "buy" else "SELL ↑"
        amt = f"({lv.order_amount:.2f} {base})" if lv.order_amount > 0 else "(waiting)"
        print(f"    ${lv.price:.8f}  {marker}  {amt}")

    assert len(state.levels) == cfg.num_levels
    assert state.lower_bound < test_price < state.upper_bound
    print(f"  ✅ {cfg.symbol} grid OK\n")


if __name__ == "__main__":
    print("\n🎒 BagHolderAI — Multi-Token Tests\n")
    test_config_lookup()
    test_grid_setup_sol()
    test_grid_setup_bonk()
    print("=" * 60)
    print("ALL MULTI-TOKEN TESTS PASSED ✅")
    print("=" * 60)
