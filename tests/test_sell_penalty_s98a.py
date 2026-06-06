"""
Brief S98a (2026-06-06) — Adaptive Sell Penalty unit tests.

Riproduce l'incidente BONK del 2026-06-06 09:07-09:15 UTC: 7 sell consecutivi
in perdita (~−$5.31) perché il prezzo ticker (check) superava la soglia sell_pct
ma il FILL del market order su testnet atterrava 4-14% sotto il check a causa
del book vuoto. La guardia Strategy A controlla il prezzo PRE-esecuzione, non il
fill → non proteggeva dallo slippage post-fill.

La Adaptive Sell Penalty (S98a) alza la soglia di vendita effettiva del danno
subìto dopo ogni sell il cui fill è atterrato sotto avg_cost, e la azzera al
primo sell con fill >= avg.

Decisione Max/Board (2026-06-06): trigger PRICE-BASED (fill < avg), non
realized_pnl < 0 come nella lettera del brief — una perdita da sola fee
(fill > avg ma pnl < 0) darebbe loss_pct negativo, abbassando la soglia.

Run:
    python tests/test_sell_penalty_s98a.py
oppure: pytest tests/test_sell_penalty_s98a.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------------
# Scaffolding (mirrors tests/test_accounting_avg_cost.py)
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


def make_bot(capital=10000.0, capital_per_trade=50.0):
    from bot.grid.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="TEST/USDT",
        capital=capital,
        buy_pct=1.0,
        sell_pct=2.0,
        strategy="A",
    )
    bot._exchange_filters = None
    bot.managed_by = "grid"
    bot.tf_exit_after_n_enabled = False
    bot.setup_grid(current_price=100.0)
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


def _build_grid_position(avg_price=100.0, n_buys=8):
    """Build a grid Strategy-A position in PAPER mode (avg = avg_price)."""
    bot = make_bot()
    bot.exchange = None  # paper buys
    for _ in range(n_buys):
        bot._execute_percentage_buy(price=avg_price)
    assert_close(bot.state.avg_buy_price, avg_price, label="setup avg")
    assert bot.state.holdings > 0, "setup must hold"
    return bot


class _SellFill:
    """Mutable holder so a single mock can return a varying fill price."""
    def __init__(self, price):
        self.price = price
    def mock(self, exchange, symbol, amount):
        return {
            "order_id": "mock_s98a",
            "filled_amount": amount,
            "avg_price": self.price,
            "cost": amount * self.price,
            "fee_cost": 0.0,          # → synthesized FEE_RATE in pipeline
            "fee_currency": "USDT",
        }


def _live_sell(bot, fill, check_price, sell_amount=0.05):
    """Execute a sell where the exchange FILL = `fill` regardless of check_price.

    Reproduces the real incident: check_price passes the Strategy-A guard
    (>= avg), but the market fill lands at `fill` (possibly < avg).
    """
    from config.settings import TradingMode
    import bot.exchange_orders as eo
    holder = _SellFill(fill)
    original_mode = TradingMode.MODE
    original_sell = eo.place_market_sell
    TradingMode.MODE = "live"
    bot.exchange = object()
    eo.place_market_sell = holder.mock
    try:
        return bot._execute_percentage_sell(price=check_price, sell_amount=sell_amount)
    finally:
        TradingMode.MODE = original_mode
        eo.place_market_sell = original_sell
        bot.exchange = None


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_a_penalty_increases_on_fill_below_avg():
    """Un sell con fill < avg arma la penalty = loss_pct e logga l'evento."""
    print("=" * 70)
    print("TEST A: penalty +loss_pct quando il fill atterra sotto avg")
    print("=" * 70)
    import bot.grid.sell_pipeline as sp

    captured = []
    original = sp.log_event
    sp.log_event = lambda **kw: captured.append(kw)
    try:
        bot = _build_grid_position(avg_price=100.0, n_buys=4)
        assert bot._sell_pct_penalty == 0.0, "starts at 0"

        # check 105 (> avg, guard passes), fill 96 (4% below avg)
        trade = _live_sell(bot, fill=96.0, check_price=105.0, sell_amount=0.05)
        assert trade is not None, "sell must execute"
        assert_close(bot._sell_pct_penalty, 4.0, label="penalty = (100-96)/100*100")

        events = [c for c in captured if c.get("event") == "sell_penalty_increased"]
        assert len(events) == 1, f"expected 1 increase event, got {len(events)}"
        d = events[0]["details"]
        assert_close(d["loss_pct"], 4.0, label="logged loss_pct")
        assert_close(d["new_penalty"], 4.0, label="logged new_penalty")
        assert_close(d["effective_sell_pct"], 2.0 + 4.0, label="effective = base + penalty")
        print(f"  fill 96 < avg 100 → penalty {bot._sell_pct_penalty:.1f}%, "
              f"effective sell_pct {d['effective_sell_pct']:.1f}% ✓")
    finally:
        sp.log_event = original


def test_b_penalty_tracks_last_loss_then_resets():
    """DESIGN v2 (Max+CEO): la penalty = ULTIMA perdita osservata, NON la somma.
    Più sell in perdita la SOSTITUISCONO (non accumulano); 1 sell a fill>=avg azzera.
    Questo evita il deadlock del cumulativo (soglia che cresce all'infinito → freeze)."""
    print("=" * 70)
    print("TEST B: penalty = ultima perdita (sostituisce, non accumula) + reset")
    print("=" * 70)
    import bot.grid.sell_pipeline as sp

    captured = []
    original = sp.log_event
    sp.log_event = lambda **kw: captured.append(kw)
    try:
        bot = _build_grid_position(avg_price=100.0, n_buys=10)

        # Sequenza di perdite diverse: la penalty deve riflettere SEMPRE l'ultima.
        for fill, exp in [(96.0, 4.0), (97.0, 3.0), (95.0, 5.0), (96.0, 4.0)]:
            _live_sell(bot, fill=fill, check_price=105.0, sell_amount=0.05)
            assert_close(bot._sell_pct_penalty, exp, tol=1e-9,
                         label=f"penalty = ultima perdita (fill {fill})")
        # Anche dopo 4 sell in perdita NON accumula: resta = ultima (4%), non 16%.
        assert_close(bot._sell_pct_penalty, 4.0, label="penalty = ultima, NON somma")
        increases = [c for c in captured if c.get("event") == "sell_penalty_increased"]
        assert len(increases) == 4, f"4 increase events, got {len(increases)}"
        print(f"  4 sell (−4/−3/−5/−4%) → penalty {bot._sell_pct_penalty:.1f}% "
              f"(= ultima, NON 16%) ✓")

        # Sell profittevole: fill 110 >= avg 100 → reset a 0.
        captured.clear()
        _live_sell(bot, fill=110.0, check_price=110.0, sell_amount=0.05)
        assert_close(bot._sell_pct_penalty, 0.0, label="penalty azzerata")
        resets = [c for c in captured if c.get("event") == "sell_penalty_reset"]
        assert len(resets) == 1, f"1 reset event, got {len(resets)}"
        assert_close(resets[0]["details"]["previous_penalty"], 4.0,
                     label="reset event logs previous penalty")
        print(f"  sell @ fill 110 ≥ avg 100 → penalty reset a "
              f"{bot._sell_pct_penalty:.1f}% (was 4%) ✓")
    finally:
        sp.log_event = original


def test_c_penalty_raises_sell_trigger():
    """La penalty alza la soglia di vendita nel SELL CHECK (grid_bot.py)."""
    print("=" * 70)
    print("TEST C: penalty alza il sell_trigger in check_price_and_execute")
    print("=" * 70)
    from bot.grid.grid_bot import GridBot

    bot = make_bot()
    bot.sell_pct = 2.0
    bot.buy_pct = 99.0
    bot.idle_reentry_hours = 0.0
    bot.exchange = None
    bot._execute_percentage_buy(price=100.0)  # paper, avg=100

    # Senza penalty il trigger = 100×(1.02+FEE)/(1−FEE) ≈ 102.1
    base_trigger = 100.0 * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    # Con penalty=5% il trigger = 100×(1.07+FEE)/(1−FEE) ≈ 107.2
    bot._sell_pct_penalty = 5.0
    pen_trigger = 100.0 * (1 + 0.07 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    print(f"  base trigger ≈ {base_trigger:.3f}, penalty trigger ≈ {pen_trigger:.3f}")

    # Un prezzo che scatterebbe SENZA penalty (tra i due trigger) NON deve vendere.
    mid = (base_trigger + pen_trigger) / 2
    sells_before = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    bot.check_price_and_execute(current_price=mid)
    sells_after = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before, (
        f"prezzo {mid:.3f} sopra base ma sotto penalty trigger non deve vendere"
    )
    print(f"  @ {mid:.3f} (sopra base, sotto penalty): no sell ✓")

    # Sopra il penalty trigger vende.
    bot.check_price_and_execute(current_price=pen_trigger * 1.001)
    sells_after = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before + 1, "sopra penalty trigger deve vendere"
    print(f"  @ {pen_trigger*1.001:.3f} (sopra penalty trigger): sell ✓")


def test_d_tf_sells_do_not_accumulate_penalty():
    """I sell TF (force-liquidate sotto avg) NON armano la penalty."""
    print("=" * 70)
    print("TEST D: TF sell sotto avg non accumula penalty (by design)")
    print("=" * 70)
    bot = make_bot()
    bot.managed_by = "tf"
    bot.exchange = None
    bot._execute_percentage_buy(price=100.0)  # avg=100
    bot._stop_loss_triggered = True  # TF force path → guard override

    # Sell paper a 95 (sotto avg) via force path.
    trade = bot._execute_percentage_sell(price=95.0, force_all=True)
    assert trade is not None, "TF stop-loss deve eseguire (override)"
    assert_close(bot._sell_pct_penalty, 0.0, label="TF non arma penalty")
    print(f"  TF stop-loss @ 95 < avg 100: penalty resta {bot._sell_pct_penalty:.1f}% ✓")


# ----------------------------------------------------------------------
# Restart recalc (state_manager replay)
# ----------------------------------------------------------------------

class _MockResult:
    def __init__(self, data):
        self.data = data


class _MockTable:
    def __init__(self, data):
        self.data = data
    def select(self, *_):
        return self
    def eq(self, *_):
        return self
    def order(self, *_, **__):
        return self
    def execute(self):
        return _MockResult(self.data)


class _MockClient:
    def __init__(self, data):
        self._data = data
    def table(self, _name):
        return _MockTable(self._data)


def _replay(history, managed_by="grid"):
    from bot.grid.state_manager import init_avg_cost_state_from_db
    bot = make_bot()
    bot.symbol = "TEST/USDT"
    bot.managed_by = managed_by
    bot.exchange = None  # paper → replay sets holdings

    class _MockLogger:
        def __init__(self):
            self.client = _MockClient(history)
            self.trades = []
        def log_trade(self, **kw):
            self.trades.append(kw)
            return kw
    bot.trade_logger = _MockLogger()
    init_avg_cost_state_from_db(bot)
    return bot


def _buy(amount, price, ts):
    return {"side": "buy", "amount": amount, "price": price, "cost": amount * price,
            "fee": 0.0, "fee_asset": "USDT", "managed_by": "grid", "created_at": ts}


def _sell(amount, price, ts, managed_by="grid"):
    return {"side": "sell", "amount": amount, "price": price, "cost": amount * price,
            "fee": amount * price * 0.001, "fee_asset": "USDT",
            "managed_by": managed_by, "created_at": ts}


def test_e_restart_reconstructs_last_loss():
    """DESIGN v2: al restart il replay ricostruisce l'ULTIMA perdita osservata,
    non la somma. 3 sell sotto avg (−4/−3/−5%) → penalty = 5% (l'ultima), non 12%."""
    print("=" * 70)
    print("TEST E: restart recalc ricostruisce l'ULTIMA perdita (non l'accumulo)")
    print("=" * 70)
    history = [
        _buy(10.0, 100.0, "2026-06-06T09:00:00+00:00"),
        _sell(1.0, 96.0, "2026-06-06T09:07:00+00:00"),  # −4%
        _sell(1.0, 97.0, "2026-06-06T09:09:00+00:00"),  # −3%
        _sell(1.0, 95.0, "2026-06-06T09:11:00+00:00"),  # −5% (ultima)
    ]
    bot = _replay(history)
    # avg resta 100 (non cambia in vendita) → penalty = ultima perdita = 5% (NON 12%)
    assert_close(bot._sell_pct_penalty, 5.0, tol=1e-9,
                 label="penalty = ultima perdita, NON somma")
    print(f"  3 sell (−4/−3/−5%) → penalty ricostruita {bot._sell_pct_penalty:.1f}% "
          f"(= ultima, NON 12%) ✓")


def test_f_restart_reset_by_last_profitable_sell():
    """Un sell a fill>=avg nello storico azzera l'accumulo precedente."""
    print("=" * 70)
    print("TEST F: restart recalc — sell profittevole azzera l'accumulo")
    print("=" * 70)
    history = [
        _buy(10.0, 100.0, "2026-06-06T09:00:00+00:00"),
        _sell(1.0, 96.0, "2026-06-06T09:07:00+00:00"),   # −4% → penalty 4
        _sell(1.0, 110.0, "2026-06-06T09:20:00+00:00"),  # +10% → reset 0
    ]
    bot = _replay(history)
    assert_close(bot._sell_pct_penalty, 0.0, tol=1e-9,
                 label="penalty azzerata dal sell profittevole")
    print(f"  sell −4% poi +10% → penalty {bot._sell_pct_penalty:.1f}% (reset) ✓")


def test_g_restart_tf_history_no_penalty():
    """Storico di un bot TF non ricostruisce penalty (gate managed_by)."""
    print("=" * 70)
    print("TEST G: restart recalc — bot TF ignora la penalty")
    print("=" * 70)
    history = [
        _buy(10.0, 100.0, "2026-06-06T09:00:00+00:00"),
        _sell(1.0, 90.0, "2026-06-06T09:07:00+00:00", managed_by="tf"),
    ]
    bot = _replay(history, managed_by="tf")
    assert_close(bot._sell_pct_penalty, 0.0, label="TF bot non ricostruisce penalty")
    print(f"  bot TF, sell −10%: penalty {bot._sell_pct_penalty:.1f}% ✓")


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def main():
    tests = [
        test_a_penalty_increases_on_fill_below_avg,
        test_b_penalty_tracks_last_loss_then_resets,
        test_c_penalty_raises_sell_trigger,
        test_d_tf_sells_do_not_accumulate_penalty,
        test_e_restart_reconstructs_last_loss,
        test_f_restart_reset_by_last_profitable_sell,
        test_g_restart_tf_history_no_penalty,
    ]
    passed = 0
    failed = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS {t.__name__}\n")
        except Exception as e:
            failed.append((t.__name__, str(e)))
            print(f"  FAIL {t.__name__}: {e}\n")

    print("=" * 70)
    print(f"  RESULTS: {passed}/{len(tests)} passed")
    if failed:
        for name, err in failed:
            print(f"    ✗ {name}: {err}")
        return 1
    print("  All tests passed ✓")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
