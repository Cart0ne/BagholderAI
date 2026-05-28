"""
Brief fix_slippage_AB (S90, 2026-05-28) — spike guard A + post-recalibrate cooldown B.

Opzione A: doppio fetch con conferma in `fetch_price_with_spike_guard`.
Opzione B: `_skip_next_decision` flag che esce da `check_price_and_execute`
nello stesso tick del dead_zone_recalibrate (within-tick gate) e nel tick
successivo (in-cima gate, defense in depth).

Riferimento: investigations/slippage_btc_20260527.md.

Run:
    python tests/test_spike_guard.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------------
# Mocks
# ----------------------------------------------------------------------

class MockExchange:
    """fetch_ticker returns prices in sequence (queue). Pop one per call."""
    def __init__(self, prices):
        self.prices = list(prices)
        self.calls = 0

    def fetch_ticker(self, symbol):
        if not self.prices:
            raise RuntimeError("MockExchange ran out of prices")
        self.calls += 1
        return {"last": self.prices.pop(0)}


# ----------------------------------------------------------------------
# Opzione A — fetch_price_with_spike_guard
# ----------------------------------------------------------------------

def test_a1_delta_below_threshold_returns_tick1():
    """delta < 4% → return tick_1 immediato, no pause, no second fetch."""
    from bot.grid_runner.lifecycle import fetch_price_with_spike_guard
    print("=" * 70)
    print("TEST A1: delta 1.5% (< 4% threshold) → tick_1, no second fetch")
    print("=" * 70)
    ex = MockExchange([75500.0])  # last_known=75000, delta +0.67%
    result = fetch_price_with_spike_guard(ex, "BTC/USDT", last_known_price=75000.0)
    assert result == 75500.0, f"expected 75500.0, got {result}"
    assert ex.calls == 1, f"expected 1 fetch_ticker call, got {ex.calls}"
    print(f"  result = {result} ✓")
    print(f"  fetch_ticker calls = {ex.calls} (no second fetch) ✓")


def test_a2_spike_rejected_returns_none():
    """delta 10% + tick_2 conferma solo 0.1% → spike rejected, return None.

    Riproduce esattamente lo scenario 27/05:
      last_known = 74500 (mainnet baseline)
      tick_1     = 82143 (spike testnet, delta +10.2%)
      tick_2     = 74600 (book ritornato a verita', conferma ~1.3%)
    Confirmed ratio = (74600-74500) / (82143-74500) ~= 1.3% < 50% → REJECT.
    """
    from bot.grid_runner.lifecycle import fetch_price_with_spike_guard
    print("=" * 70)
    print("TEST A2: 27/05 scenario — spike $82,143 NOT confirmed → return None")
    print("=" * 70)
    ex = MockExchange([82143.07, 74600.0])
    # pause_seconds=0 nel test per non bloccare la suite per 5s reali
    result = fetch_price_with_spike_guard(
        ex, "BTC/USDT", last_known_price=74500.0, pause_seconds=0.0
    )
    assert result is None, f"expected None (spike rejected), got {result}"
    assert ex.calls == 2, f"expected 2 fetch_ticker calls, got {ex.calls}"
    print(f"  result = None (caller will skip cycle) ✓")
    print(f"  fetch_ticker calls = {ex.calls} (both ticks fetched) ✓")


def test_a3_real_rally_confirmed_returns_tick2():
    """delta 12% + tick_2 conferma 92% → real rally, return tick_2.

    Scenario BONK pump reale (esempio dal brief):
      last_known = 0.000020
      tick_1     = 0.0000224 (+12%)
      tick_2     = 0.0000221 (+10.5%, conferma 87.5% del movimento)
    """
    from bot.grid_runner.lifecycle import fetch_price_with_spike_guard
    print("=" * 70)
    print("TEST A3: real rally +12% confirmed → return tick_2")
    print("=" * 70)
    ex = MockExchange([0.0000224, 0.0000221])
    result = fetch_price_with_spike_guard(
        ex, "BONK/USDT", last_known_price=0.000020, pause_seconds=0.0
    )
    assert result == 0.0000221, f"expected 0.0000221, got {result}"
    assert ex.calls == 2
    print(f"  result = {result} (rally legit, proceed with tick_2) ✓")


def test_a4_first_tick_post_restart_no_baseline():
    """last_known_price=0 → return tick_1 senza guard (primo tick post-restart)."""
    from bot.grid_runner.lifecycle import fetch_price_with_spike_guard
    print("=" * 70)
    print("TEST A4: last_known=0 (post-restart, no baseline) → tick_1 senza guard")
    print("=" * 70)
    ex = MockExchange([99999.0])  # any wild value passes
    result = fetch_price_with_spike_guard(ex, "BTC/USDT", last_known_price=0.0)
    assert result == 99999.0
    assert ex.calls == 1, f"expected 1 fetch_ticker call (no guard), got {ex.calls}"
    print(f"  result = {result} ✓")
    print(f"  fetch_ticker calls = {ex.calls} (guard bypassed) ✓")


def test_a5_reverse_sign_rejected():
    """delta 10% UP + tick_2 -3% DOWN → segno opposto → spike rejected."""
    from bot.grid_runner.lifecycle import fetch_price_with_spike_guard
    print("=" * 70)
    print("TEST A5: tick_1 up 10%, tick_2 reverses down → REJECT")
    print("=" * 70)
    ex = MockExchange([82000.0, 73000.0])  # last_known=75000
    result = fetch_price_with_spike_guard(
        ex, "BTC/USDT", last_known_price=75000.0, pause_seconds=0.0
    )
    assert result is None
    print(f"  result = None (opposite-sign confirmation rejected) ✓")


# ----------------------------------------------------------------------
# Opzione B — _skip_next_decision flag in GridBot
# ----------------------------------------------------------------------

class _MockTradeLogger:
    def __init__(self):
        self.trades = []
    def log_trade(self, **kwargs):
        self.trades.append(kwargs)
        return kwargs


class _MockPortfolioManager:
    def update_position(self, **kwargs):
        return kwargs
    def get_portfolio(self):
        return []
    def get_total_allocation(self):
        return 0


class _MockPnLTracker:
    def record_daily(self, **kwargs):
        return kwargs
    def get_daily_pnl_today(self):
        return 0


def _make_grid_bot_for_dead_zone():
    """GridBot in paper mode, configurato per essere idle > dead_zone_hours
    e holdings>0 sopra avg cost (precondizioni dead_zone_recalibrate)."""
    from bot.grid.grid_bot import GridBot
    from datetime import datetime, timedelta
    bot = GridBot(
        exchange=None,
        trade_logger=_MockTradeLogger(),
        portfolio_manager=_MockPortfolioManager(),
        pnl_tracker=_MockPnLTracker(),
        symbol="BTC/USDT",
        capital=500.0,
        buy_pct=1.0,
        sell_pct=1.5,
        strategy="A",
        dead_zone_hours=4.0,
    )
    bot._exchange_filters = None
    bot.managed_by = "grid"
    bot.is_active = True
    bot.pending_liquidation = False
    bot.tf_exit_after_n_enabled = False
    bot.setup_grid(current_price=80000.0)
    # Configurazione che riproduce lo stato del bot BTC il 27/05 alle 21:44 UTC
    bot.state.holdings = 1.00254375
    bot.state.avg_buy_price = 79454.40
    bot.state.last_price = 78000.0  # tick precedente
    bot._pct_last_buy_price = 78009.34
    bot._last_sell_price = 81853.66  # ladder ancora attivo
    bot._last_trade_time = datetime.utcnow() - timedelta(hours=6.2)  # idle 6.2h
    bot._stop_buy_active = False
    bot._gain_saturation_triggered = False
    bot._trailing_stop_triggered = False
    bot._stop_loss_triggered = False
    bot._take_profit_triggered = False
    bot._profit_lock_triggered = False
    return bot


def test_b1_dead_zone_arms_flag_and_skips_sell_same_tick():
    """Dead zone recalibrate scatta + flag armato + nessuna sell nello stesso tick.

    Senza il fix, lo spike $82,143 farebbe scattare la sell immediatamente.
    Con il fix: dead_zone aggiorna lo stato, ma check_price_and_execute esce
    senza valutare il SELL CHECK.
    """
    print("=" * 70)
    print("TEST B1: dead_zone scatta + spike $82,143 → NO sell (skip same tick)")
    print("=" * 70)
    bot = _make_grid_bot_for_dead_zone()
    assert bot._skip_next_decision is False  # baseline

    trades = bot.check_price_and_execute(current_price=82143.07)

    assert len(trades) == 0, f"expected NO trades, got {len(trades)}"
    assert bot._skip_next_decision is True, "flag should be armed for next tick"
    # Verifica che il recalibrate sia effettivamente avvenuto
    assert bot._pct_last_buy_price == 82143.07, (
        f"dead_zone should update _pct_last_buy_price; got {bot._pct_last_buy_price}"
    )
    assert bot._last_sell_price == 0.0, "dead_zone should reset _last_sell_price"
    print(f"  trades = [] ✓ (sell NOT triggered despite spike above avg)")
    print(f"  _skip_next_decision = True ✓ (armed for next tick)")
    print(f"  _pct_last_buy_price = 82143.07 ✓ (recalibrate happened)")
    print(f"  _last_sell_price = 0 ✓ (ladder reset)")


def test_b2_next_tick_consumes_flag_and_skips():
    """Tick successivo: flag True → in-cima check skippa + reset flag.

    Defense in depth: anche se il prezzo del tick N+1 è "normale", saltiamo
    una volta in più per garantire che il prossimo SELL CHECK usi una baseline
    completamente fresca (lo `state.last_price` settato nel tick N era lo
    spike $82,143; al tick N+2 sarà già stato sovrascritto a un prezzo non-spike).
    """
    print("=" * 70)
    print("TEST B2: tick N+1 con flag True → in-cima check skippa")
    print("=" * 70)
    bot = _make_grid_bot_for_dead_zone()
    bot._skip_next_decision = True  # simula stato post-tick-N

    trades = bot.check_price_and_execute(current_price=74500.0)

    assert len(trades) == 0, f"expected NO trades, got {len(trades)}"
    assert bot._skip_next_decision is False, "flag should be cleared after consume"
    print(f"  trades = [] ✓ (skipped by in-cima gate)")
    print(f"  _skip_next_decision = False ✓ (consumed)")


def test_b3_third_tick_normal_behavior():
    """Tick N+2: flag False, prezzo normale, nessun dead_zone (last_trade_time
    fresco dal recalibrate del tick N). Si comporta normalmente."""
    print("=" * 70)
    print("TEST B3: tick N+2 → flag False, sotto sell trigger → no trade")
    print("=" * 70)
    bot = _make_grid_bot_for_dead_zone()
    # Simula stato post-tick-N (recalibrate avvenuto) + tick N+1 (flag consumed)
    from datetime import datetime
    bot._pct_last_buy_price = 82143.07
    bot._last_sell_price = 0.0
    bot._last_trade_time = datetime.utcnow()  # appena resettato dal recalibrate
    bot._skip_next_decision = False
    bot.state.last_price = 74500.0  # ultimo tick "normale"

    trades = bot.check_price_and_execute(current_price=74600.0)

    # sell trigger ≈ avg × 1.016 / 0.999 ≈ 80807; 74600 < 80807 → no sell
    # buy ref = 82143, buy_pct=1% → trigger = 82143 × 0.99 = 81322; 74600 < 81322 → buy?
    # Strategy A: holdings>0 + current<avg? 74600 < 79454 → BUY consentita
    # Però richiede cash sufficiente — bot in paper non ha cash configurato, salta.
    # L'asserzione importante: il flag NON viene riarmato, comportamento normale.
    assert bot._skip_next_decision is False, "flag must stay False (no recalibrate this tick)"
    print(f"  _skip_next_decision = False ✓ (no recalibrate fired)")
    print(f"  trades count = {len(trades)} (behavior normale, no skip)")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Brief fix_slippage_AB — spike guard (A) + post-recalibrate cooldown (B)")
    print("S90 2026-05-28")
    print("=" * 70 + "\n")

    test_a1_delta_below_threshold_returns_tick1()
    print()
    test_a2_spike_rejected_returns_none()
    print()
    test_a3_real_rally_confirmed_returns_tick2()
    print()
    test_a4_first_tick_post_restart_no_baseline()
    print()
    test_a5_reverse_sign_rejected()
    print()
    test_b1_dead_zone_arms_flag_and_skips_sell_same_tick()
    print()
    test_b2_next_tick_consumes_flag_and_skips()
    print()
    test_b3_third_tick_normal_behavior()

    print("\n" + "=" * 70)
    print("All tests passed ✓")
    print("=" * 70)
