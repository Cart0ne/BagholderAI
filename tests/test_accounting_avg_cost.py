"""
S66 Operation Clean Slate — Step 1.4 unit tests.

Validates the canonical avg-cost accounting:
    on buy:  avg = (avg_old × qty_old + price × qty_buy) / (qty_old + qty_buy)
    on sell: realized = (sell_price − avg) × sell_qty
             avg does NOT change (only resets to 0 when holdings → 0)

The accounting identity SUM(realized) == revenue_total − invested_total
must hold for ANY buy/sell sequence, by construction.

Pre-66a, the bot computed cost_basis with a walk-and-sum of the FIFO
queue (sell_pipeline.py:514-535), which silently desynced from DB and
introduced a +29% bias on the v3 dataset (594 sells, 80.6% mismatch).
Post-66a, cost_basis = bot.state.avg_buy_price × sell_qty — robust to
queue desync because avg_buy_price is two scalars, not a mutable list.

Run:
    python tests/test_accounting_avg_cost.py
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------------
# Test scaffolding (mirrors tests/test_pct_sell_fifo.py)
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


def make_bot(capital=1000.0, capital_per_trade=50.0):
    """Construct a fresh GridBot in percentage mode with mock collaborators."""
    from bot.strategies.grid_bot import GridBot
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=MockPortfolioManager(),
        pnl_tracker=MockPnLTracker(),
        symbol="TEST/USDT",
        capital=capital,
        num_levels=10,
        range_percent=0.04,
        grid_mode="percentage",
        buy_pct=1.0,
        sell_pct=1.0,
        strategy="A",
    )
    bot._exchange_filters = None
    bot.setup_grid(current_price=10.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.realized_pnl = 0.0
    bot.state.daily_realized_pnl = 0.0
    bot.state.total_invested = 0.0
    bot.state.total_received = 0.0
    bot.state.total_fees = 0.0
    bot._pct_open_positions = []
    bot._pct_last_buy_price = 0.0
    bot.capital_per_trade = capital_per_trade
    # Disable safety latches that would block buys/sells in tests
    bot._stop_buy_active = False
    bot._gain_saturation_triggered = False
    bot._trailing_stop_triggered = False
    bot._stop_loss_triggered = False
    bot._take_profit_triggered = False
    bot._profit_lock_triggered = False
    bot.pending_liquidation = False
    bot.min_profit_pct = 0  # disable min-profit gate
    return bot


def assert_close(actual, expected, tol=1e-6, label=""):
    if abs(actual - expected) > tol:
        raise AssertionError(
            f"{label}: expected {expected!r}, got {actual!r} (diff {actual-expected:+.10f})"
        )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_a_simple_buy_then_sell():
    """1 buy + 1 sell totale: avg = price del buy, realized = (sell-buy)*qty."""
    print("=" * 70)
    print("TEST A: simple buy → sell totale")
    print("=" * 70)
    bot = make_bot()

    bot._execute_percentage_buy(price=5.0)  # spends $50 → qty=10 @ avg=$5
    assert_close(bot.state.avg_buy_price, 5.0, label="avg after buy")
    assert_close(bot.state.holdings, 10.0, label="holdings after buy")

    trade = bot._execute_percentage_sell(price=6.0)
    assert trade is not None, "sell must execute"
    assert_close(trade["realized_pnl"], 10.0, label="realized = (6-5)*10 = $10")
    assert_close(bot.state.holdings, 0.0, label="holdings after full sell")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg resets to 0 on full sell")
    print(f"  realized = ${trade['realized_pnl']:.4f} (expected $10.0000) ✓")
    print(f"  avg post-sell = ${bot.state.avg_buy_price:.2f} (expected $0.00) ✓")


def test_b_multi_buy_partial_sell():
    """2 buy a prezzi diversi, sell parziale: avg ponderato, NON cambia su sell."""
    print("=" * 70)
    print("TEST B: multi-buy → partial sell (avg unchanged on sell)")
    print("=" * 70)
    bot = make_bot()

    bot._execute_percentage_buy(price=5.0)   # $50 / $5 = 10 qty
    bot._execute_percentage_buy(price=10.0)  # $50 / $10 = 5 qty
    # avg = (5*10 + 10*5) / 15 = 100 / 15 = 6.6667
    expected_avg = (5.0 * 10.0 + 10.0 * 5.0) / 15.0
    expected_qty = 15.0
    assert_close(bot.state.avg_buy_price, expected_avg, label="avg after 2 buys")
    assert_close(bot.state.holdings, expected_qty, label="holdings after 2 buys")
    print(f"  after 2 buys: avg=${bot.state.avg_buy_price:.4f}  qty={bot.state.holdings} ✓")

    # Manually trigger a sell of the first lot (10 qty) at $9
    # _execute_percentage_sell sells the first lot's amount
    avg_before_sell = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=9.0)
    expected_realized = (9.0 - avg_before_sell) * 10.0  # sell qty = lot1.amount = 10
    assert_close(trade["realized_pnl"], expected_realized,
                 label=f"realized = (9 - {avg_before_sell:.4f}) * 10")
    # CRITICAL: avg must NOT change on sell (still $6.67)
    assert_close(bot.state.avg_buy_price, avg_before_sell,
                 label="avg unchanged after partial sell")
    assert_close(bot.state.holdings, 5.0, label="holdings = 15 - 10 = 5")
    print(f"  after partial sell: avg=${bot.state.avg_buy_price:.4f} (UNCHANGED) ✓")
    print(f"  realized = ${trade['realized_pnl']:.4f} (expected ${expected_realized:.4f}) ✓")


def test_c_full_sell_then_buy_resets_avg():
    """Sell totale → avg=0 → nuovo buy → avg=prezzo del nuovo buy (non old avg)."""
    print("=" * 70)
    print("TEST C: full sell → new buy → avg resets to new buy price")
    print("=" * 70)
    bot = make_bot()

    bot._execute_percentage_buy(price=5.0)   # qty=10 @ avg=$5
    bot._execute_percentage_buy(price=10.0)  # qty=15 @ avg=$6.667
    # Need to sell BOTH lots to fully empty. Use last-lot logic by selling
    # lot1 first, then lot2.
    bot._execute_percentage_sell(price=12.0)  # sells lot1 (10 qty)
    assert bot.state.holdings == 5.0, "after sell1: 5 qty left"
    # avg STILL = 6.667 (unchanged) — this is the canonical avg-cost behaviour
    bot._execute_percentage_sell(price=12.0)  # sells last 5
    assert_close(bot.state.holdings, 0.0, label="holdings empty")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg resets to 0 on full empty")

    # Now a fresh buy must establish avg = new buy price (NOT inherit old)
    bot._execute_percentage_buy(price=20.0)
    assert_close(bot.state.avg_buy_price, 20.0, label="avg = $20 on fresh buy")
    assert_close(bot.state.holdings, 50.0/20.0, label="qty = $50 / $20 = 2.5")
    print(f"  after full sell + new buy: avg=${bot.state.avg_buy_price:.2f} ✓")
    print(f"  holdings={bot.state.holdings} ✓")


def test_d_alternating_buy_sell_sequence():
    """Stress: 5 buy + 5 sell alternati. Avg si aggiorna solo su buy."""
    print("=" * 70)
    print("TEST D: alternating buy-sell sequence (5+5)")
    print("=" * 70)
    bot = make_bot()
    sequence = [
        ("buy",  5.00),
        ("sell", 6.00),
        ("buy",  7.00),
        ("buy",  8.00),
        ("sell", 9.00),
        ("buy", 10.00),
        ("sell", 11.00),
        ("sell", 12.00),
        ("sell", 13.00),
    ]
    realized_track = []
    for op, price in sequence:
        if op == "buy":
            bot._execute_percentage_buy(price=price)
        else:
            t = bot._execute_percentage_sell(price=price)
            if t:
                realized_track.append(t["realized_pnl"])

    # After the sequence, verify accounting identity
    revenue_total = bot.state.total_received
    invested_total = bot.state.total_invested
    realized_db = sum(t["realized_pnl"] for t in bot.trade_logger.trades if t.get("side") == "sell")
    expected_realized = revenue_total - invested_total

    print(f"  invested total: ${invested_total:.4f}")
    print(f"  received total: ${revenue_total:.4f}")
    print(f"  realized expected (revenue−invested): ${expected_realized:.4f}")
    print(f"  realized DB (sum of trade.realized_pnl):  ${realized_db:.4f}")

    # NOTE: identity holds only when ALL positions are closed (Unrealized=0).
    # If holdings > 0, we add the unrealized at the last price to verify.
    last_price = sequence[-1][1]
    unrealized = bot.state.holdings * (last_price - bot.state.avg_buy_price) if bot.state.holdings > 0 else 0
    print(f"  holdings residue: {bot.state.holdings:.4f} × (${last_price} - ${bot.state.avg_buy_price:.4f}) = ${unrealized:.4f}")
    print(f"  total P&L (realized + unrealized): ${realized_db + unrealized:.4f}")
    print(f"  total expected (received - invested + holdings_value): "
          f"${revenue_total - invested_total + bot.state.holdings * last_price:.4f}")

    closed_identity = realized_db + unrealized
    open_identity = revenue_total - invested_total + bot.state.holdings * last_price
    assert_close(closed_identity, open_identity,
                 tol=1e-6, label="closed_identity == open_identity")
    print(f"  identity holds ✓")


def test_e_random_sequence_identity():
    """Random sequence: SUM(realized) == revenue−invested when fully closed."""
    print("=" * 70)
    print("TEST E: random sequence (50 ops) — identity must close")
    print("=" * 70)
    random.seed(66)  # reproducible
    bot = make_bot(capital=100000.0, capital_per_trade=100.0)
    n_ops = 50

    for i in range(n_ops):
        if bot.state.holdings <= 0 or random.random() < 0.55:
            # buy at random price
            price = round(random.uniform(50, 200), 2)
            bot._execute_percentage_buy(price=price)
        else:
            # sell at random price ABOVE current avg (Strategy A no-loss)
            min_sell = bot.state.avg_buy_price * 1.001
            price = round(random.uniform(min_sell, min_sell * 1.5), 4)
            bot._execute_percentage_sell(price=price)

    # Force-close any residual holdings to test pure identity
    while bot.state.holdings > 1e-9 and bot._pct_open_positions:
        # 68a: Strategy A guard now checks avg_buy_price, so sell_price must be > avg.
        # We keep the oldest_lot_price > sell_price safety as well, in case some
        # future code path re-introduces a lot-level check.
        sell_price = bot.state.avg_buy_price * 1.001 if bot.state.avg_buy_price > 0 else 1.0
        oldest_lot_price = bot._pct_open_positions[0]["price"]
        sell_price = max(sell_price, oldest_lot_price * 1.001)
        result = bot._execute_percentage_sell(price=sell_price)
        if result is None:
            break  # safety to avoid infinite loop

    revenue_total = bot.state.total_received
    invested_total = bot.state.total_invested
    realized_db = sum(t["realized_pnl"] for t in bot.trade_logger.trades if t.get("side") == "sell")
    holdings_residue = bot.state.holdings

    print(f"  ops executed: buys={sum(1 for t in bot.trade_logger.trades if t.get('side')=='buy')}, "
          f"sells={sum(1 for t in bot.trade_logger.trades if t.get('side')=='sell')}")
    print(f"  invested total: ${invested_total:.4f}")
    print(f"  received total: ${revenue_total:.4f}")
    print(f"  expected realized = revenue − invested = ${revenue_total - invested_total:.4f}")
    print(f"  DB realized (sum of trade.realized_pnl): ${realized_db:.4f}")
    print(f"  holdings residue: {holdings_residue:.6f}")

    # If holdings residue > 0, identity holds via realized + unrealized = total
    if holdings_residue > 1e-9:
        # Use last sell price as proxy for spot
        last_sell_price = bot.trade_logger.trades[-1]["price"]
        unrealized = holdings_residue * (last_sell_price - bot.state.avg_buy_price)
        print(f"  unrealized @ last sell price ${last_sell_price}: ${unrealized:.4f}")
        total_pnl_via_db = realized_db + unrealized
        total_pnl_via_id = revenue_total - invested_total + holdings_residue * last_sell_price
        assert_close(total_pnl_via_db, total_pnl_via_id, tol=1e-3,
                     label="realized+unrealized == revenue-invested+holdings_value")
        print(f"  identity holds (open positions): ${total_pnl_via_db:.4f} == ${total_pnl_via_id:.4f} ✓")
    else:
        # Fully closed: identity is direct
        assert_close(realized_db, revenue_total - invested_total, tol=1e-3,
                     label="SUM(realized) == revenue - invested")
        print(f"  identity holds (closed): SUM(realized) = ${realized_db:.4f} == "
              f"${revenue_total - invested_total:.4f} ✓")


def test_f_dust_prevention_residual_below_min_sellable():
    """66a Step 2: when a sell would leave a residual below 1.5x min_sellable,
    sell-all instead. Prevents the silent dust-pop queue desync (source #4a
    of the +29% bias certified in formula_verification_s66.md).

    Identity must still close: realized + unrealized = revenue − invested.
    """
    print("=" * 70)
    print("TEST F: 66a Step 2 — dust prevention sell-all when residual is dust")
    print("=" * 70)
    bot = make_bot()
    # Mock filters: step 0.001, min_qty=0, min_notional=$5
    bot._exchange_filters = {
        "lot_step_size": 0.001,
        "min_qty": 0.0,
        "min_notional": 5.0,
    }
    # Two lots simulating a state with a small residual lot:
    # lot1 = 10 @ $5, lot2 = 0.4 @ $9, holdings = 10.4
    bot._pct_open_positions = [
        {"amount": 10.0, "price": 5.0},
        {"amount": 0.4, "price": 9.0},
    ]
    bot.state.holdings = 10.4
    bot.state.avg_buy_price = (10.0 * 5.0 + 0.4 * 9.0) / 10.4
    bot.state.total_invested = 10.0 * 5.0 + 0.4 * 9.0  # 53.6

    # Sell at $10. Without dust prevention: amount=lot1.amount=10, residual=0.4.
    # min_sellable = max(0.001, 0, 5/10=0.5) = 0.5. residual=0.4 < 0.75 → trigger.
    # New amount = 10.4 (sell all). cost = 10.4 * avg ≈ 53.6, rev = 104, pnl ≈ +50.4.
    avg_before = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=10.0)
    assert trade is not None, "sell must execute"
    assert_close(trade["amount"], 10.4, label="amount sold = all holdings")
    assert len(bot._pct_open_positions) == 0, "queue must be empty post sell-all"
    assert_close(bot.state.holdings, 0.0, label="holdings empty")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg resets to 0")

    expected_pnl = (10.0 - avg_before) * 10.4
    assert_close(trade["realized_pnl"], expected_pnl, tol=1e-6, label="realized_pnl")
    print(f"  amount = {trade['amount']:.4f} (expected 10.4) ✓")
    print(f"  queue empty, holdings=0, avg=0 ✓")
    print(f"  realized = ${trade['realized_pnl']:+.4f} (expected ${expected_pnl:+.4f}) ✓")

    # Identity check: revenue − invested = realized (fully closed)
    assert_close(
        bot.state.total_received - bot.state.total_invested,
        bot.state.realized_pnl,
        tol=1e-6,
        label="closed identity",
    )
    print(f"  closed identity holds: rev − inv = realized ✓")


def test_h_guard_blocks_sell_below_avg_even_above_lot_buy():
    """68a: Strategy A guard must block a sell when price > oldest lot_buy_price
    but price < avg_buy_price. Pre-68a the guard checked lot_buy → such sells
    would pass and produce realized_pnl < 0 (canonical avg-cost). Post-68a the
    guard checks avg_buy_price → these sells are correctly blocked.

    Evidence motivating the fix: BONK sell 2026-05-08 22:56 UTC, realized −$0.152
    when price ($0.00000724) was above oldest lot ($0.00000722) but below avg.
    """
    print("=" * 70)
    print("TEST H: 68a — guard blocks sell when price > lot_buy but price < avg")
    print("=" * 70)
    bot = make_bot()

    # Two buys at very different prices to force avg > oldest_lot
    bot._execute_percentage_buy(price=5.0)    # $50 → 10 qty @ avg $5
    bot._execute_percentage_buy(price=15.0)   # $50 → 3.333 qty @ avg = ?
    expected_avg = (5.0 * 10.0 + 15.0 * (50.0 / 15.0)) / (10.0 + 50.0 / 15.0)
    expected_avg = round(expected_avg, 6)
    actual_avg = round(bot.state.avg_buy_price, 6)
    assert_close(actual_avg, expected_avg, label="avg after 2 mixed buys")
    print(f"  state: oldest lot=$5.00, avg=${bot.state.avg_buy_price:.4f}")

    # Pick a price that is strictly between lot_buy ($5) and avg
    sell_price = 7.0  # > $5 (oldest lot) but < avg (~$7.50)
    assert sell_price > 5.0, "sell_price must be above oldest lot_buy"
    assert sell_price < bot.state.avg_buy_price, (
        f"sell_price ${sell_price} must be below avg ${bot.state.avg_buy_price:.4f} "
        "for this test to be meaningful"
    )

    # Pre-68a behaviour would have executed and produced realized < 0.
    # Post-68a: guard must block, return None, no state mutation.
    holdings_before = bot.state.holdings
    realized_before = bot.state.realized_pnl
    trades_before = len(bot.trade_logger.trades)

    result = bot._execute_percentage_sell(price=sell_price)

    assert result is None, "guard must BLOCK the sell"
    assert_close(bot.state.holdings, holdings_before, label="holdings unchanged after blocked sell")
    assert_close(bot.state.realized_pnl, realized_before, label="realized_pnl unchanged after blocked sell")
    assert len(bot.trade_logger.trades) == trades_before, "no new trade logged"
    print(f"  sell at ${sell_price} blocked correctly (would have been loss vs avg ${bot.state.avg_buy_price:.4f}) ✓")
    print(f"  no state mutation ✓")

    # Sanity check: a sell ABOVE avg must still execute
    sell_price_ok = bot.state.avg_buy_price * 1.05  # +5% above avg
    avg_at_sell = bot.state.avg_buy_price
    result_ok = bot._execute_percentage_sell(price=sell_price_ok)
    assert result_ok is not None, "sell above avg must execute"
    expected_pnl = (sell_price_ok - avg_at_sell) * result_ok["amount"]
    assert_close(result_ok["realized_pnl"], expected_pnl, tol=1e-6,
                 label="realized = (sell_price - avg) * qty")
    print(f"  sell at ${sell_price_ok:.4f} executed (above avg) → realized ${result_ok['realized_pnl']:+.4f} ✓")


def test_g_dust_prevention_no_trigger_when_residual_healthy():
    """66a Step 2: if residual is well above 1.5x min_sellable, normal pct-sell
    runs unchanged (single-lot consumption). Guards against over-aggressive
    sell-all in healthy states."""
    print("=" * 70)
    print("TEST G: 66a Step 2 — no trigger when residual is healthy")
    print("=" * 70)
    bot = make_bot()
    bot._exchange_filters = {
        "lot_step_size": 0.001,
        "min_qty": 0.0,
        "min_notional": 5.0,
    }
    # Two lots: 10 @ $5, 5 @ $9. Holdings = 15. Residual after lot1 sell = 5 (healthy).
    bot._pct_open_positions = [
        {"amount": 10.0, "price": 5.0},
        {"amount": 5.0, "price": 9.0},
    ]
    bot.state.holdings = 15.0
    bot.state.avg_buy_price = (10.0 * 5.0 + 5.0 * 9.0) / 15.0
    bot.state.total_invested = 10.0 * 5.0 + 5.0 * 9.0  # 95.0

    # Sell at $10. amount = lot1.amount = 10. residual = 5 > 0.75 → no trigger.
    # cost_basis = 10 * avg ≈ 63.33. revenue = 100. pnl ≈ +36.67.
    avg_before = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=10.0)
    assert trade is not None, "sell must execute"
    assert_close(trade["amount"], 10.0, label="amount sold = lot1 only (no dust trigger)")
    assert len(bot._pct_open_positions) == 1, "lot2 must remain in queue"
    assert_close(bot._pct_open_positions[0]["amount"], 5.0, label="lot2 amount untouched")
    assert_close(bot.state.holdings, 5.0, label="holdings = 5 after partial sell")
    # avg unchanged on partial sell (canonical avg-cost)
    assert_close(bot.state.avg_buy_price, avg_before, label="avg unchanged on partial sell")

    expected_pnl = (10.0 - avg_before) * 10.0
    assert_close(trade["realized_pnl"], expected_pnl, tol=1e-6, label="realized_pnl")
    print(f"  amount = {trade['amount']:.4f} (expected 10.0) ✓")
    print(f"  lot2 untouched ({bot._pct_open_positions[0]['amount']}), holdings={bot.state.holdings} ✓")
    print(f"  avg unchanged = ${bot.state.avg_buy_price:.4f} ✓")
    print(f"  realized = ${trade['realized_pnl']:+.4f} (expected ${expected_pnl:+.4f}) ✓")


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def main():
    tests = [
        test_a_simple_buy_then_sell,
        test_b_multi_buy_partial_sell,
        test_c_full_sell_then_buy_resets_avg,
        test_d_alternating_buy_sell_sequence,
        test_e_random_sequence_identity,
        test_f_dust_prevention_residual_below_min_sellable,
        test_g_dust_prevention_no_trigger_when_residual_healthy,
        test_h_guard_blocks_sell_below_avg_even_above_lot_buy,
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
