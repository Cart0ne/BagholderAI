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
    # Brief 72a P3 (S72): realized = (sell - avg) × qty − fee_sell
    expected_realized = (6.0 - 5.0) * 10.0 - (6.0 * 10.0) * bot.FEE_RATE
    assert_close(trade["realized_pnl"], expected_realized,
                 label=f"realized = (6-5)*10 − fee_sell = ${expected_realized:.4f}")
    assert_close(bot.state.holdings, 0.0, label="holdings after full sell")
    assert_close(bot.state.avg_buy_price, 0.0, label="avg resets to 0 on full sell")
    print(f"  realized = ${trade['realized_pnl']:.4f} (expected ${expected_realized:.4f}) ✓")
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
    # Brief 72a P3 (S72): realized = (sell - avg) × qty − fee_sell
    expected_fee_sell = (9.0 * 10.0) * bot.FEE_RATE
    expected_realized = (9.0 - avg_before_sell) * 10.0 - expected_fee_sell
    assert_close(trade["realized_pnl"], expected_realized,
                 label=f"realized = (9 - {avg_before_sell:.4f}) * 10 − fee_sell")
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

    # After the sequence, verify accounting identity.
    # Brief 72a (S72): realized_pnl now includes -fee_sell. Identity becomes:
    #   realized + unrealized + sum(fee_sell) = revenue − invested + holdings_value
    # i.e. the "P&L view" matches the "cash view" only after adding back
    # the sell-side fees that realized has already absorbed.
    revenue_total = bot.state.total_received
    invested_total = bot.state.total_invested
    realized_db = sum(t["realized_pnl"] for t in bot.trade_logger.trades if t.get("side") == "sell")
    total_fee_sell = sum(t.get("fee", 0) for t in bot.trade_logger.trades if t.get("side") == "sell")
    expected_realized = revenue_total - invested_total - total_fee_sell

    print(f"  invested total: ${invested_total:.4f}")
    print(f"  received total: ${revenue_total:.4f}")
    print(f"  sum fee_sell: ${total_fee_sell:.6f}")
    print(f"  realized expected (revenue−invested−fee_sell): ${expected_realized:.4f}")
    print(f"  realized DB (sum of trade.realized_pnl):  ${realized_db:.4f}")

    # NOTE: identity holds only when ALL positions are closed (Unrealized=0).
    # If holdings > 0, we add the unrealized at the last price to verify.
    last_price = sequence[-1][1]
    unrealized = bot.state.holdings * (last_price - bot.state.avg_buy_price) if bot.state.holdings > 0 else 0
    print(f"  holdings residue: {bot.state.holdings:.4f} × (${last_price} - ${bot.state.avg_buy_price:.4f}) = ${unrealized:.4f}")
    print(f"  total P&L (realized + unrealized): ${realized_db + unrealized:.4f}")
    print(f"  total expected (received - invested + holdings_value): "
          f"${revenue_total - invested_total + bot.state.holdings * last_price:.4f}")

    # 72a: realized already has fee_sell baked in, so add it back to compare.
    closed_identity = realized_db + unrealized + total_fee_sell
    open_identity = revenue_total - invested_total + bot.state.holdings * last_price
    assert_close(closed_identity, open_identity,
                 tol=1e-6, label="closed_identity (+fee_sell) == open_identity")
    print(f"  identity holds (72a: +sum(fee_sell)) ✓")


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
    total_fee_sell = sum(t.get("fee", 0) for t in bot.trade_logger.trades if t.get("side") == "sell")
    holdings_residue = bot.state.holdings

    print(f"  ops executed: buys={sum(1 for t in bot.trade_logger.trades if t.get('side')=='buy')}, "
          f"sells={sum(1 for t in bot.trade_logger.trades if t.get('side')=='sell')}")
    print(f"  invested total: ${invested_total:.4f}")
    print(f"  received total: ${revenue_total:.4f}")
    print(f"  sum fee_sell: ${total_fee_sell:.6f}")
    print(f"  expected realized (revenue − invested − fee_sell): "
          f"${revenue_total - invested_total - total_fee_sell:.4f}")
    print(f"  DB realized (sum of trade.realized_pnl): ${realized_db:.4f}")
    print(f"  holdings residue: {holdings_residue:.6f}")

    # Brief 72a (S72): identity now includes sum(fee_sell), since realized
    # bakes in -fee_sell per row.
    if holdings_residue > 1e-9:
        # Use last sell price as proxy for spot
        last_sell_price = bot.trade_logger.trades[-1]["price"]
        unrealized = holdings_residue * (last_sell_price - bot.state.avg_buy_price)
        print(f"  unrealized @ last sell price ${last_sell_price}: ${unrealized:.4f}")
        total_pnl_via_db = realized_db + unrealized + total_fee_sell
        total_pnl_via_id = revenue_total - invested_total + holdings_residue * last_sell_price
        assert_close(total_pnl_via_db, total_pnl_via_id, tol=1e-3,
                     label="realized+unrealized+fee_sell == revenue-invested+holdings_value")
        print(f"  identity holds (open, 72a): ${total_pnl_via_db:.4f} == ${total_pnl_via_id:.4f} ✓")
    else:
        # Fully closed: realized + sum(fee_sell) == revenue - invested
        assert_close(realized_db + total_fee_sell, revenue_total - invested_total, tol=1e-3,
                     label="SUM(realized) + sum(fee_sell) == revenue - invested")
        print(f"  identity holds (closed, 72a): "
              f"SUM(realized)+fee_sell = ${realized_db + total_fee_sell:.4f} "
              f"== ${revenue_total - invested_total:.4f} ✓")


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

    # Brief 72a P3 (S72): realized = (sell - avg) × qty − fee_sell
    expected_fee_sell = (10.0 * 10.4) * bot.FEE_RATE
    expected_pnl = (10.0 - avg_before) * 10.4 - expected_fee_sell
    assert_close(trade["realized_pnl"], expected_pnl, tol=1e-6, label="realized_pnl")
    print(f"  amount = {trade['amount']:.4f} (expected 10.4) ✓")
    print(f"  holdings=0, avg=0 ✓")
    print(f"  realized = ${trade['realized_pnl']:+.4f} (expected ${expected_pnl:+.4f}) ✓")

    # Identity check (72a): rev − inv = realized + fee_sell when fully closed
    assert_close(
        bot.state.total_received - bot.state.total_invested,
        bot.state.realized_pnl + expected_fee_sell,
        tol=1e-6,
        label="closed identity (72a: realized + fee_sell == rev - inv)",
    )
    print(f"  closed identity holds (72a): rev − inv = realized + fee_sell ✓")


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
    # Brief 72a P3: realized = (sell - avg) × qty − fee_sell
    revenue_ok = sell_price_ok * result_ok["amount"]
    expected_pnl = (sell_price_ok - avg_at_sell) * result_ok["amount"] - revenue_ok * bot.FEE_RATE
    assert_close(result_ok["realized_pnl"], expected_pnl, tol=1e-6,
                 label="realized = (sell_price - avg) * qty − fee_sell")
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

    # Brief 72a P3: realized = (sell - avg) × qty − fee_sell
    expected_fee_sell = (10.0 * 10.0) * bot.FEE_RATE
    expected_pnl = (10.0 - avg_before) * 10.0 - expected_fee_sell
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
    # Brief 72a P3 (S72): realized = (price − avg) × qty − fee_sell
    revenue_trade = 7.90 * sell_trade["amount"]
    expected_pnl = (7.90 - avg_before_sell) * sell_trade["amount"] - revenue_trade * bot.FEE_RATE
    assert_close(
        sell_trade["realized_pnl"], expected_pnl, tol=1e-6,
        label="realized = (price − avg) × amount − fee_sell"
    )
    print(f"  realized identity uses avg (not lot price), netto fees: ✓")


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
# Brief 70a tests (S70 2026-05-10)
# ----------------------------------------------------------------------

def test_l_sell_trigger_includes_fee_buffer_grid_only():
    """Brief 70a Parte 2: Grid manual sell trigger include fee buffer.
    Formula: avg × (1 + sell_pct/100 + FEE) / (1 - FEE) (uniforme).
    TF/tf_grid mantengono formula vecchia: avg × (1 + threshold/100).
    """
    print("=" * 70)
    print("TEST L: brief 70a — Grid sell trigger include fee buffer; TF no")
    print("=" * 70)
    from bot.grid.grid_bot import GridBot

    # --- Grid manual: trigger = avg × (1.02 + 0.001) / 0.999
    bot = make_bot()
    bot.managed_by = "grid"
    bot.sell_pct = 2.0
    bot.buy_pct = 99.0  # disable buy path
    bot.idle_reentry_hours = 0.0
    bot._execute_percentage_buy(price=100.0)
    avg = bot.state.avg_buy_price
    expected_trigger = avg * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    print(f"  Grid: avg={avg:.4f}, expected trigger ≈ {expected_trigger:.4f}")

    # Below trigger: must NOT sell
    sells_before = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    bot.check_price_and_execute(current_price=expected_trigger * 0.999)
    sells_after = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before, (
        f"Grid: price below trigger should not sell"
    )
    print(f"  Grid @ {expected_trigger*0.999:.4f} (below trigger): no sell ✓")

    # Above trigger: must sell
    bot.check_price_and_execute(current_price=expected_trigger * 1.001)
    sells_after = sum(1 for t in bot.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before + 1, "Grid: price above trigger must sell"
    print(f"  Grid @ {expected_trigger*1.001:.4f} (above trigger): sell ✓")

    # --- TF: trigger = avg × 1.02 (no fee buffer)
    bot2 = make_bot()
    bot2.managed_by = "tf"
    bot2.sell_pct = 2.0
    bot2.buy_pct = 99.0
    bot2.idle_reentry_hours = 0.0
    bot2._execute_percentage_buy(price=100.0)
    avg2 = bot2.state.avg_buy_price
    expected_trigger_tf = avg2 * 1.02
    expected_trigger_grid = avg2 * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)

    # Price right between TF trigger and Grid trigger: TF must sell, Grid wouldn't
    mid_price = (expected_trigger_tf + expected_trigger_grid) / 2
    sells_before = sum(1 for t in bot2.trade_logger.trades if t.get("side") == "sell")
    bot2.check_price_and_execute(current_price=mid_price)
    sells_after = sum(1 for t in bot2.trade_logger.trades if t.get("side") == "sell")
    assert sells_after == sells_before + 1, (
        f"TF: must sell at {mid_price} > avg×1.02 ({expected_trigger_tf:.4f}). "
        f"Got {sells_after - sells_before} sells."
    )
    print(f"  TF @ {mid_price:.4f} (TF sells but Grid wouldn't @ same price): sell ✓")


def test_m_sell_ladder_three_steps():
    """Brief 70a Parte 3: sell graduale — 3 lotti venduti a 3 prezzi crescenti.
    Step N+1 trigger usa _last_sell_price come reference (non avg).
    Formula uniforme (decisione Max iii): reference × (1+sell_pct/100+FEE)/(1-FEE).
    """
    print("=" * 70)
    print("TEST M: brief 70a — sell ladder 3 step crescenti")
    print("=" * 70)
    from bot.grid.grid_bot import GridBot

    bot = make_bot(capital=1000.0, capital_per_trade=20.0)
    bot.managed_by = "grid"
    bot.sell_pct = 2.0
    bot.buy_pct = 99.0
    bot.idle_reentry_hours = 0.0

    # 3 buy: total $60 → avg=$100, holdings=0.6
    for _ in range(3):
        bot._execute_percentage_buy(price=100.0)
    assert bot.state.holdings > 0
    assert bot._last_sell_price == 0.0, "ladder reset at start"
    avg = bot.state.avg_buy_price

    # Step 1 trigger: avg × 1.021 / 0.999
    s1_trigger = avg * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    bot.check_price_and_execute(current_price=s1_trigger * 1.0001)
    sells = [t for t in bot.trade_logger.trades if t.get("side") == "sell"]
    assert len(sells) == 1, f"step 1 should fire 1 sell, got {len(sells)}"
    assert bot._last_sell_price > 0, "ladder should be set after partial sell"
    s1_price = bot._last_sell_price
    print(f"  Step 1: trigger @ {s1_trigger:.4f}, fill {s1_price:.4f}, ladder set ✓")

    # Step 2 trigger: last_sell × 1.021 / 0.999 (NOT avg-based)
    s2_trigger = s1_price * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    # Price between s1_trigger and s2_trigger should NOT fire (ladder up)
    bot.check_price_and_execute(current_price=s1_trigger * 1.001)
    sells = [t for t in bot.trade_logger.trades if t.get("side") == "sell"]
    assert len(sells) == 1, "ladder must wait for s2_trigger, not re-fire at s1"
    print(f"  Step 2 wait: price near s1 doesn't fire (ladder up) ✓")

    # Above s2_trigger fires
    bot.check_price_and_execute(current_price=s2_trigger * 1.0001)
    sells = [t for t in bot.trade_logger.trades if t.get("side") == "sell"]
    assert len(sells) == 2, f"step 2 should fire, got {len(sells)} sells"
    s2_price = bot._last_sell_price
    assert s2_price > s1_price, "ladder must climb"
    print(f"  Step 2: trigger @ {s2_trigger:.4f}, fill {s2_price:.4f}, ladder climbed ✓")

    # Step 3
    s3_trigger = s2_price * (1 + 0.02 + GridBot.FEE_RATE) / (1 - GridBot.FEE_RATE)
    bot.check_price_and_execute(current_price=s3_trigger * 1.0001)
    sells = [t for t in bot.trade_logger.trades if t.get("side") == "sell"]
    assert len(sells) == 3, f"step 3 should fire, got {len(sells)} sells"
    print(f"  Step 3: trigger @ {s3_trigger:.4f}, ladder = {bot._last_sell_price:.4f} ✓")
    assert bot._last_sell_price > s2_price, "ladder must climb again"


def test_n_ladder_resets_on_full_selloff():
    """Brief 70a Parte 3: _last_sell_price reset a 0 quando holdings → 0.
    Nuovo ciclo (buy successivo) parte di nuovo dal trigger basato su avg.
    """
    print("=" * 70)
    print("TEST N: brief 70a — ladder reset on full sell-out")
    print("=" * 70)
    bot = make_bot(capital=1000.0, capital_per_trade=20.0)
    bot.managed_by = "grid"
    bot.sell_pct = 2.0

    # 1 buy + force_all sell (vende tutto)
    bot._execute_percentage_buy(price=100.0)
    assert bot._last_sell_price == 0.0, "fresh state"
    bot._execute_percentage_sell(price=110.0, force_all=True)
    assert bot.state.holdings == 0, "must be fully sold out"
    assert bot._last_sell_price == 0.0, (
        f"ladder must reset on full exit, got {bot._last_sell_price}"
    )
    print(f"  Sell-out: holdings=0, _last_sell_price=0 ✓")

    # Partial sell deve INVECE settare last_sell
    bot._execute_percentage_buy(price=100.0)
    bot._execute_percentage_buy(price=100.0)
    bot._execute_percentage_buy(price=100.0)
    assert bot.state.holdings > 0
    bot._execute_percentage_sell(price=110.0)  # partial
    assert bot.state.holdings > 0, "must still hold after partial sell"
    assert bot._last_sell_price == 110.0, (
        f"partial sell must set ladder = {110.0}, got {bot._last_sell_price}"
    )
    print(f"  Partial sell: _last_sell_price set to {bot._last_sell_price} ✓")


def test_o_post_fill_warning_slippage_below_avg():
    """Brief 70a Parte 4: warning loggato quando fill_price < avg_buy_price.
    NON loggato per TF force-liquidate path. Trade NON bloccato (è già eseguito).
    """
    print("=" * 70)
    print("TEST O: brief 70a — post-fill warning slippage_below_avg")
    print("=" * 70)
    import bot.grid.sell_pipeline as sp

    captured = []
    original_log_event = sp.log_event

    def mock_log_event(severity=None, category=None, event=None, **kwargs):
        captured.append({"severity": severity, "category": category, "event": event, **kwargs})

    sp.log_event = mock_log_event
    try:
        # --- CASE 1: Grid manual con fill < avg → warning loggato
        bot = make_bot(capital=1000.0, capital_per_trade=50.0)
        bot.managed_by = "grid"
        bot.strategy = "B"  # bypass guard 282 per testare specificamente Parte 4
        bot._execute_percentage_buy(price=100.0)
        captured.clear()
        # Force a sell at price < avg via _execute_percentage_sell.
        # Strategy "B" bypassa la guard 282 (Strategy A only).
        result = bot._execute_percentage_sell(price=99.0, sell_amount=0.1)
        assert result is not None, "sell must execute (Strategy B, no guard)"
        warnings = [c for c in captured if c.get("event") == "slippage_below_avg"]
        assert len(warnings) == 1, (
            f"expected 1 slippage_below_avg warning, got {len(warnings)}: "
            f"{[c.get('event') for c in captured]}"
        )
        w = warnings[0]
        assert w["severity"] == "warn", f"severity should be warn, got {w['severity']}"
        details = w.get("details", {})
        assert details.get("gap_pct") < 0, f"gap_pct should be negative, got {details.get('gap_pct')}"
        print(f"  Grid fill 99 < avg 100: warning logged (gap {details.get('gap_pct'):.2f}%) ✓")

        # --- CASE 2: TF force-liquidate path → NO warning
        bot2 = make_bot()
        bot2.managed_by = "tf"
        bot2.strategy = "B"  # bypass guard 282
        bot2._stop_loss_triggered = True  # TF force path
        bot2._execute_percentage_buy(price=100.0)
        captured.clear()
        bot2._execute_percentage_sell(price=99.0, sell_amount=0.1, force_all=False)
        warnings = [c for c in captured if c.get("event") == "slippage_below_avg"]
        assert len(warnings) == 0, (
            f"TF force-liquidate must NOT log warning, got {len(warnings)}"
        )
        print(f"  TF stop-loss: no warning (force-liquidate path) ✓")

        # --- CASE 3: fill >= avg → no warning
        bot3 = make_bot()
        bot3.managed_by = "grid"
        bot3._execute_percentage_buy(price=100.0)
        captured.clear()
        bot3._execute_percentage_sell(price=110.0, sell_amount=0.1)
        warnings = [c for c in captured if c.get("event") == "slippage_below_avg"]
        assert len(warnings) == 0, "fill above avg must not log warning"
        print(f"  Grid fill 110 > avg 100: no warning ✓")
    finally:
        sp.log_event = original_log_event


# ----------------------------------------------------------------------
# Brief 72a tests — Fee Unification (S72 2026-05-11)
# ----------------------------------------------------------------------


def test_p_live_buy_scales_holdings_net_of_fee_base():
    """Brief 72a P1+P2 (S72): live mode BUY with fee_currency==base_coin must
    add `filled − fee_base` to holdings (not `filled` lordo). And avg_buy_price
    must use `cost USDT / qty_acquired_net`, so the true USDT-per-coin held
    is reflected.

    Reproduces BONK testnet bug: pre-72a `state.holdings += filled` accumulated
    phantom qty (12.280 BONK drift on 9 BUYs). Post-72a state matches wallet.
    """
    print("=" * 70)
    print("TEST P: 72a — live BUY holdings = filled − fee_base, avg P2")
    print("=" * 70)
    from config.settings import TradingMode
    import bot.exchange_orders as eo

    bot = make_bot()
    bot.managed_by = "tf"  # bypass Strategy A guard (TF path)
    bot.exchange = object()  # non-None to enter live branch

    # Mock: Binance fills 1000 TEST coins, charges 1 TEST as fee
    # (= 0.1%, exactly like real BONK testnet). USDT cost = 50.
    def mock_place_market_buy(exchange, symbol, cost):
        return {
            "order_id": "mock_p1",
            "filled_amount": 1000.0,
            "avg_price": 0.05,
            "cost": 50.0,
            "fee_cost": 0.05,           # USDT-equivalent
            "fee_currency": "TEST",     # base coin → fee scaled from base
            "fee_native_amount": 1.0,
            "fee_base": 1.0,            # 72a: subtracted from holdings
            "status": "closed",
            "raw": {},
        }

    original_mode = TradingMode.MODE
    original_buy = eo.place_market_buy
    TradingMode.MODE = "live"
    eo.place_market_buy = mock_place_market_buy

    try:
        bot._execute_percentage_buy(price=0.05)
    finally:
        TradingMode.MODE = original_mode
        eo.place_market_buy = original_buy

    # P1: holdings = filled - fee_base = 1000 - 1 = 999
    assert_close(bot.state.holdings, 999.0, tol=1e-6,
                 label="holdings net of fee_base")
    # P2: avg = cost / qty_acquired = 50 / 999 ≈ 0.05005005
    expected_avg = 50.0 / 999.0
    assert_close(bot.state.avg_buy_price, expected_avg, tol=1e-9,
                 label="avg = cost_usdt / qty_acquired")
    # total_invested still tracks USDT lordo (cash actually paid)
    assert_close(bot.state.total_invested, 50.0, label="total_invested USDT")
    print(f"  filled=1000, fee_base=1 → holdings={bot.state.holdings} (expected 999) ✓")
    print(f"  avg={bot.state.avg_buy_price:.8f} (expected {expected_avg:.8f}) ✓")


def test_q_sell_realized_pnl_includes_fee_sell():
    """Brief 72a P3 (S72): realized_pnl = (price - avg) × qty − fee_sell_usdt.
    Pre-72a was just (price - avg) × qty → gonfiato di ~0.1% per sell.

    Paper mode is sufficient to test this — paper simulates fee = revenue × FEE_RATE,
    and the formula change applies in both paper and live paths uniformly.
    """
    print("=" * 70)
    print("TEST Q: 72a — sell realized_pnl includes fee_sell_usdt")
    print("=" * 70)
    bot = make_bot()
    bot.strategy = "B"  # bypass S68a guard so we can sell at any price

    # Setup: 1 buy @ $10 → avg=10, qty=5
    bot._execute_percentage_buy(price=10.0)
    avg_before_sell = bot.state.avg_buy_price
    assert_close(avg_before_sell, 10.0, label="avg after buy")

    # Sell 5 units @ $12. fee_paper = revenue × FEE_RATE = 60 × 0.001 = 0.06.
    # Expected realized P&L = (12 - 10) × 5 − 0.06 = 10 - 0.06 = 9.94
    trade = bot._execute_percentage_sell(price=12.0, sell_amount=5.0)
    assert trade is not None, "sell must execute (strategy B, no guard)"

    expected_fee = 60.0 * bot.FEE_RATE  # paper sim
    expected_realized = (12.0 - 10.0) * 5.0 - expected_fee
    assert_close(trade["realized_pnl"], expected_realized, tol=1e-6,
                 label="realized = (sell - avg) × qty − fee_sell")
    print(f"  fee_paper = ${expected_fee:.6f}")
    print(f"  realized = ${trade['realized_pnl']:.6f} "
          f"(expected ${expected_realized:.6f}) ✓")
    print(f"  Pre-72a would have been ${(12.0 - 10.0) * 5.0:.4f} "
          f"(overstated by fee = ${expected_fee:.6f}) ✓")


def test_r_replay_with_fee_in_base_coin():
    """Brief 72a (S72): replay applies the 3 invariants — BUYs with
    fee_asset == base_coin reduce qty_acquired, avg uses cost USDT
    over net qty, sells subtract fee_sell. Paper trades (fee_asset='USDT')
    preserve legacy behaviour because fee_native_est = 0.

    Ground-truth scenario: 2 BUYs on TEST/USDT with fee in TEST + 1 SELL
    with fee in USDT. Verify final avg/realized match the closed-form
    expectation, and the BUY-side fee correctly shaves qty.
    """
    print("=" * 70)
    print("TEST R: 72a — replay subtracts fee_native on BUY, fee_sell on SELL")
    print("=" * 70)
    from bot.grid.state_manager import init_avg_cost_state_from_db
    from bot.grid.grid_bot import GridBot

    # Mock client that returns synthetic trade history
    class MockSupabaseResult:
        def __init__(self, data):
            self.data = data

    class MockTable:
        def __init__(self, data):
            self.data = data
        def select(self, _): return self
        def eq(self, *_): return self
        def order(self, *_, **__): return self
        def execute(self): return MockSupabaseResult(self.data)

    class MockClient:
        def __init__(self, data):
            self._data = data
        def table(self, _): return MockTable(self._data)

    # Trade history:
    # BUY1: 1000 TEST @ $0.05, cost $50, fee_usdt $0.05, fee_asset=TEST
    # BUY2: 500 TEST @ $0.04, cost $20, fee_usdt $0.02, fee_asset=TEST
    # SELL1: 300 TEST @ $0.06, fee_usdt $0.018, fee_asset=USDT
    trade_history = [
        {"side": "buy",  "amount": 1000.0, "price": 0.05, "cost": 50.0,
         "fee": 0.05, "fee_asset": "TEST", "created_at": "2026-05-10T00:00:00+00:00"},
        {"side": "buy",  "amount": 500.0,  "price": 0.04, "cost": 20.0,
         "fee": 0.02, "fee_asset": "TEST", "created_at": "2026-05-10T01:00:00+00:00"},
        {"side": "sell", "amount": 300.0,  "price": 0.06, "cost": 18.0,
         "fee": 0.018, "fee_asset": "USDT", "created_at": "2026-05-10T02:00:00+00:00"},
    ]

    bot = make_bot()
    bot.symbol = "TEST/USDT"
    # Replace trade_logger with one whose client returns the synthetic history
    class MockLogger:
        def __init__(self):
            self.client = MockClient(trade_history)
            self.trades = []
        def log_trade(self, **kw):
            self.trades.append(kw)
            return kw
    bot.trade_logger = MockLogger()
    bot.exchange = None  # paper mode → no fetch_balance, replay sets holdings

    init_avg_cost_state_from_db(bot)

    # Expected calculations:
    # BUY1: fee_native_est = 0.05 / 0.05 = 1.0 TEST → qty_acq1 = 999
    #       avg1 = 50.0 / 999.0
    # BUY2: fee_native_est = 0.02 / 0.04 = 0.5 TEST → qty_acq2 = 499.5
    #       cumulative qty = 999 + 499.5 = 1498.5
    #       avg2 = (avg1 × 999 + 20.0) / 1498.5 = (50.0 + 20.0) / 1498.5 = 70.0 / 1498.5
    # SELL1: realized = (0.06 - avg2) × 300 − 0.018
    expected_qty_after_buys = 999.0 + 499.5
    expected_avg_after_buys = 70.0 / 1498.5
    expected_realized = (0.06 - expected_avg_after_buys) * 300.0 - 0.018
    expected_qty_after_sell = 1498.5 - 300.0

    assert_close(bot.state.holdings, expected_qty_after_sell, tol=1e-6,
                 label="qty after replay (paper, no fetch_balance)")
    assert_close(bot.state.avg_buy_price, expected_avg_after_buys, tol=1e-9,
                 label="avg after 2 BUYs with fee in base coin")
    assert_close(bot.state.realized_pnl, expected_realized, tol=1e-6,
                 label="realized = (sell - avg) × qty − fee_sell")
    print(f"  BUY1 (1000 @ $0.05, fee=1 TEST) → qty_acq=999, avg={50.0/999.0:.8f}")
    print(f"  BUY2 (500 @ $0.04, fee=0.5 TEST) → qty_acq=499.5, "
          f"avg={expected_avg_after_buys:.8f}")
    print(f"  SELL1 (300 @ $0.06, fee=$0.018) → realized=${expected_realized:.6f}")
    print(f"  Final state: holdings={bot.state.holdings:.4f}, "
          f"avg={bot.state.avg_buy_price:.8f}, "
          f"realized=${bot.state.realized_pnl:.6f} ✓")


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
        test_l_sell_trigger_includes_fee_buffer_grid_only,
        test_m_sell_ladder_three_steps,
        test_n_ladder_resets_on_full_selloff,
        test_o_post_fill_warning_slippage_below_avg,
        test_p_live_buy_scales_holdings_net_of_fee_base,
        test_q_sell_realized_pnl_includes_fee_sell,
        test_r_replay_with_fee_in_base_coin,
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
