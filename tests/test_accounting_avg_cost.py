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
    # Brief s70 FASE 2 buy guard: managed_by="tf" bypassa il guard
    # "no buy above avg" (TF rotator buys are signal-driven). Test_k
    # esplicitamente usa managed_by="grid" per verificare il guard.
    bot.managed_by = "tf"
    # Disable TF gain-saturation eval (would query DB via mock client).
    bot.tf_exit_after_n_enabled = False
    bot.setup_grid(current_price=10.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.realized_pnl = 0.0
    bot.state.daily_realized_pnl = 0.0
    bot.state.total_invested = 0.0
    bot.state.total_received = 0.0
    bot.state.total_fees = 0.0
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
    """1 buy + 1 sell totale: avg = price del buy, realized = (sell-buy)*qty.

    Brief s70 FASE 1: sell totale via force_all=True (TF override path).
    """
    print("=" * 70)
    print("TEST A: simple buy → sell totale (force_all=True)")
    print("=" * 70)
    bot = make_bot()

    bot._execute_percentage_buy(price=5.0)  # spends $50 → qty=10 @ avg=$5
    assert_close(bot.state.avg_buy_price, 5.0, label="avg after buy")
    assert_close(bot.state.holdings, 10.0, label="holdings after buy")

    trade = bot._execute_percentage_sell(price=6.0, force_all=True)
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

    # Brief s70 FASE 1: sell explicit amount=10 to replicate the legacy
    # FIFO lot1 sell. avg-cost mode: avg unchanged on partial sell.
    avg_before_sell = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=9.0, sell_amount=10.0)
    expected_realized = (9.0 - avg_before_sell) * 10.0
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
    # Brief s70 FASE 1: full liquidation in one call via force_all=True.
    bot._execute_percentage_sell(price=12.0, force_all=True)
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

    # Brief s70 FASE 1: force-close residual holdings via force_all=True.
    # Pure identity test (Realized + Unrealized = Revenue − Invested).
    if bot.state.holdings > 1e-9:
        sell_price = bot.state.avg_buy_price * 1.001 if bot.state.avg_buy_price > 0 else 1.0
        bot._execute_percentage_sell(price=sell_price, force_all=True)

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
    # State with a small residual: holdings=10.4, avg ≈ $5.154
    # (the FIFO queue is no longer consulted in avg-cost mode; only
    # state.holdings + state.avg_buy_price drive the dust prevention).
    bot.state.holdings = 10.4
    bot.state.avg_buy_price = (10.0 * 5.0 + 0.4 * 9.0) / 10.4
    bot.state.total_invested = 10.0 * 5.0 + 0.4 * 9.0  # 53.6

    # Sell at $10 with explicit sell_amount=10. residual = 10.4 - 10 = 0.4.
    # min_sellable = max(0.001, 0, 5/10=0.5) = 0.5. residual=0.4 < 0.75 → trigger.
    # New amount = 10.4 (sell all). cost = 10.4 * avg ≈ 53.6, rev = 104, pnl ≈ +50.4.
    avg_before = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=10.0, sell_amount=10.0)
    assert trade is not None, "sell must execute"
    assert_close(trade["amount"], 10.4, label="amount sold = all holdings")
    assert_close(bot.state.holdings, 0.0, label="holdings empty")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg resets to 0")

    expected_pnl = (10.0 - avg_before) * 10.4
    assert_close(trade["realized_pnl"], expected_pnl, tol=1e-6, label="realized_pnl")
    print(f"  amount = {trade['amount']:.4f} (expected 10.4) ✓")
    print(f"  holdings=0, avg=0 ✓")
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
    # State: holdings=15 with avg ≈ $6.333. Residual after sell of 10 = 5 (healthy).
    bot.state.holdings = 15.0
    bot.state.avg_buy_price = (10.0 * 5.0 + 5.0 * 9.0) / 15.0
    bot.state.total_invested = 10.0 * 5.0 + 5.0 * 9.0  # 95.0

    # Sell at $10 with explicit sell_amount=10. residual = 5 > 0.75 → no trigger.
    # cost_basis = 10 * avg ≈ 63.33. revenue = 100. pnl ≈ +36.67.
    avg_before = bot.state.avg_buy_price
    trade = bot._execute_percentage_sell(price=10.0, sell_amount=10.0)
    assert trade is not None, "sell must execute"
    assert_close(trade["amount"], 10.0, label="amount sold = sell_amount (no dust trigger)")
    assert_close(bot.state.holdings, 5.0, label="holdings = 5 after partial sell")
    # avg unchanged on partial sell (canonical avg-cost)
    assert_close(bot.state.avg_buy_price, avg_before, label="avg unchanged on partial sell")

    expected_pnl = (10.0 - avg_before) * 10.0
    assert_close(trade["realized_pnl"], expected_pnl, tol=1e-6, label="realized_pnl")
    print(f"  amount = {trade['amount']:.4f} (expected 10.0) ✓")
    print(f"  holdings={bot.state.holdings} ✓")
    print(f"  avg unchanged = ${bot.state.avg_buy_price:.4f} ✓")
    print(f"  realized = ${trade['realized_pnl']:+.4f} (expected ${expected_pnl:+.4f}) ✓")


def test_i_sell_trigger_uses_avg_buy_price():
    """Brief s70 FASE 1: sell trigger gates on state.avg_buy_price, not on
    individual lot prices. Two buys at very different prices give an avg
    between them. The trigger fires when current_price >= avg × (1 +
    sell_pct/100), irrespective of where each lot was bought.

    Pre-fix the trigger was per-lot: a price above the oldest lot.price ×
    (1 + sell_pct/100) (but below the avg-based threshold) would fire a
    sell. Post-fix only avg matters.
    """
    print("=" * 70)
    print("TEST I: avg-cost sell trigger fires on avg_buy_price (not per-lot)")
    print("=" * 70)
    bot = make_bot()
    bot.sell_pct = 5.0  # threshold = 5%

    # Two buys at different prices: $5 (qty=10) and $15 (qty=$50/$15≈3.333).
    # avg = ($50 + $50) / (10 + 3.333) = $100 / 13.333 = $7.50.
    bot._execute_percentage_buy(price=5.0)
    bot._execute_percentage_buy(price=15.0)
    avg = bot.state.avg_buy_price
    assert avg > 7.0, f"setup sanity: avg should be ~7.50, got {avg:.4f}"
    print(f"  setup: 2 buys → avg=${avg:.4f}, holdings={bot.state.holdings:.4f}")

    # Disable the buy path so check_price_and_execute exercises only the
    # sell trigger in isolation. buy_pct=99 makes the buy threshold so
    # low that no realistic price re-entry can fire.
    bot.buy_pct = 99.0
    bot.idle_reentry_hours = 0.0  # disable idle re-entry path too

    # Pre-fix: price=$5.30 (above oldest lot $5 × 1.05) would have FIRED sell.
    # Post-fix: $5.30 < avg × 1.05 = $7.875 → must NOT sell.
    sells_before = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    bot.check_price_and_execute(current_price=5.30)
    sells_after = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before, (
        f"Pre-fix would have fired (price > oldest lot × 1.05), post-fix must NOT sell. "
        f"Got {sells_after - sells_before} extra sells."
    )
    print(f"  $5.30 (above oldest lot+5% but below avg+5%): no sell ✓")

    # Now at $7.90 (above avg × 1.05 = $7.875) the trigger fires.
    avg_before_sell = bot.state.avg_buy_price
    bot.check_price_and_execute(current_price=7.90)
    sells_after_trigger = [t for t in bot.trade_logger.trades if t.get("side") == "sell"]
    assert len(sells_after_trigger) >= 1, "trigger must fire above avg × (1 + sell_pct/100)"
    sell_trade = sells_after_trigger[-1]
    print(
        f"  $7.90 (above avg+5%): sell fired, amount={sell_trade['amount']:.4f}, "
        f"realized=${sell_trade['realized_pnl']:+.4f} ✓"
    )

    # Sell amount must be capital_per_trade / current_price ≈ $50/$7.90 = 6.329
    expected_amount = bot.capital_per_trade / 7.90
    assert_close(
        sell_trade["amount"], expected_amount, tol=1e-3,
        label=f"sell amount = capital_per_trade / price = $50 / $7.90"
    )
    print(f"  sell amount = {sell_trade['amount']:.4f} (= ${bot.capital_per_trade}/$7.90) ✓")

    # Realized must use avg (snapshot at sell-time) as cost basis, not lot price.
    expected_pnl = (7.90 - avg_before_sell) * sell_trade["amount"]
    assert_close(
        sell_trade["realized_pnl"], expected_pnl, tol=1e-6,
        label="realized = (price − avg) × amount"
    )
    print(f"  realized identity uses avg (not lot price): ✓")


def test_k_buy_guard_above_avg_when_holdings():
    """Brief s70 FASE 2 (CEO + Max 2026-05-09): Strategy A symmetric guard.
    Buy above avg is BLOCKED when holdings > 0; first entry (holdings=0)
    is always permitted regardless of price.
    """
    print("=" * 70)
    print("TEST K: Strategy A buy guard above avg (holdings>0)")
    print("=" * 70)
    bot = make_bot()
    bot.managed_by = "grid"  # manual bot path

    # First buy: holdings=0 → guard does NOT apply, buy allowed at any price
    trade1 = bot._execute_percentage_buy(price=100.0)
    assert trade1 is not None, "first buy must execute (holdings=0, avg=0)"
    assert_close(bot.state.avg_buy_price, 100.0, label="avg = first buy price")
    print(f"  first buy at $100 (holdings=0 entry): executed ✓ avg=${bot.state.avg_buy_price:.2f}")

    # Now holdings>0, avg=$100. Buy at $105 (above avg) → must BLOCK
    holdings_before = bot.state.holdings
    avg_before = bot.state.avg_buy_price
    trades_before = len(bot.trade_logger.trades)

    blocked = bot._execute_percentage_buy(price=105.0)
    assert blocked is None, "guard must BLOCK buy above avg"
    assert_close(bot.state.holdings, holdings_before, label="holdings unchanged")
    assert_close(bot.state.avg_buy_price, avg_before, label="avg unchanged")
    assert len(bot.trade_logger.trades) == trades_before, "no new trade logged"
    print(f"  buy at $105 (above avg $100, holdings>0): BLOCKED ✓ no state mutation")

    # Buy at $95 (below avg) → must EXECUTE, mediating in basso
    trade2 = bot._execute_percentage_buy(price=95.0)
    assert trade2 is not None, "buy below avg must execute"
    # New avg < old avg (mediating down)
    assert bot.state.avg_buy_price < 100.0, (
        f"avg should drop after buy at $95, got {bot.state.avg_buy_price}"
    )
    print(f"  buy at $95 (below avg): executed ✓ new avg=${bot.state.avg_buy_price:.4f}")

    # Edge: TF managed_by override (managed_by='tf') → guard NOT applied
    bot2 = make_bot()
    bot2.managed_by = "tf"
    bot2._execute_percentage_buy(price=100.0)  # first entry
    trade_tf = bot2._execute_percentage_buy(price=110.0)  # above avg
    assert trade_tf is not None, "TF bot can buy above avg (signal-driven)"
    print(f"  TF bot (managed_by='tf'): buy above avg allowed ✓ (signal-driven path)")


def test_j_idle_recalibrate_skipped_above_avg():
    """Brief s70 FASE 2 (CEO + Max 2026-05-09): in IDLE RECALIBRATE path B
    (holdings > 0), skip the reset of _pct_last_buy_price if current_price
    is strictly above state.avg_buy_price. Prevents the Scenario 4 loop
    where the bot mediates up in lateral-up markets, gonfiando il cost
    basis e amplificando drawdown post-peak.

    Specular test: when current_price <= avg, recalibrate fires as before.
    """
    from datetime import datetime, timedelta
    print("=" * 70)
    print("TEST J: IDLE recalibrate skipped when current > avg")
    print("=" * 70)
    bot = make_bot()
    bot.is_active = True
    bot.idle_reentry_hours = 4.0
    bot.buy_pct = 99.0   # disable buy path
    bot.sell_pct = 99.0  # disable sell path

    # Establish a state with holdings, avg, and a stale buy reference.
    bot._execute_percentage_buy(price=100.0)  # avg=$100, holdings=0.5 ($50/$100)
    initial_ref = bot._pct_last_buy_price
    initial_avg = bot.state.avg_buy_price
    assert_close(initial_avg, 100.0, label="avg after first buy")
    print(f"  initial: ref=${initial_ref:.2f}, avg=${initial_avg:.2f}")

    # Set _last_trade_time to 5h ago → elapsed > idle_reentry_hours (4h)
    bot._last_trade_time = datetime.utcnow() - timedelta(hours=5)

    # --- CASE 1: current > avg ($105 vs avg $100) → recalibrate must SKIP
    bot.check_price_and_execute(current_price=105.0)
    assert bot._pct_last_buy_price == initial_ref, (
        f"recalibrate should be skipped (price > avg): "
        f"ref was {initial_ref}, now {bot._pct_last_buy_price}"
    )
    # Verify the skipped alert was recorded
    skipped_alerts = [
        a for a in bot.idle_reentry_alerts if a.get("skipped_above_avg")
    ]
    assert len(skipped_alerts) == 1, (
        f"expected 1 skipped alert, got {len(skipped_alerts)}: {bot.idle_reentry_alerts}"
    )
    print(f"  $105 (above avg $100): recalibrate SKIPPED ✓ ref unchanged @ ${bot._pct_last_buy_price:.2f}")

    # --- CASE 2: current <= avg ($95 vs avg $100) → recalibrate FIRES
    # Reset _last_trade_time to 5h ago again (advanced by previous skip path)
    bot._last_trade_time = datetime.utcnow() - timedelta(hours=5)
    bot.idle_reentry_alerts.clear()
    ref_before = bot._pct_last_buy_price
    bot.check_price_and_execute(current_price=95.0)
    assert_close(bot._pct_last_buy_price, 95.0, label="ref recalibrated to current")
    fired_alerts = [
        a for a in bot.idle_reentry_alerts if a.get("recalibrate") is True
    ]
    assert len(fired_alerts) == 1, (
        f"expected 1 recalibrate alert, got {len(fired_alerts)}: {bot.idle_reentry_alerts}"
    )
    print(f"  $95 (below avg $100): recalibrate FIRED ✓ ref={ref_before:.2f} → ${bot._pct_last_buy_price:.2f}")


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
        test_i_sell_trigger_uses_avg_buy_price,
        test_j_idle_recalibrate_skipped_above_avg,
        test_k_buy_guard_above_avg_when_holdings,
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
