"""
Brief S105b (S105 2026-06-13) — grid-dust-reentry.

Tests for the unified "position vs dust" predicate (is_dust) and the live/replay
gates that now route through it.

Background: a sub-min-sellable residual (e.g. 0.000096 SOL ≈ $0.006) used to count
as an open position. That kept `managed_holdings > 0`, which (1) disabled the idle
re-entry forced buy (gated on `managed_holdings <= 0`) and (2) kept the
no-buy-above-avg guard armed — so once SOL drained to dust it could neither buy
(price above avg) nor sell (below LOT_SIZE) and froze for ~5 days (2026-06-09→13).

is_dust() makes every position gate agree on what counts as a real, sellable
position: anything below Binance's smallest sellable size (LOT_SIZE / NOTIONAL) is
dust → treated as empty → idle re-entry fires.

Real Binance testnet filters used below were verified live (S105b GATE A2):
SOL/BTC minNotional $5, BONK $1 — all dominate the legacy $0.50 dust threshold.
"""

from datetime import datetime, timedelta

from tests.test_accounting_avg_cost import make_bot
from utils.exchange_filters import is_dust, min_sellable_amount
from utils.timeutils import utcnow

SOL_FILTERS = {"lot_step_size": 0.001, "min_qty": 0.001, "min_notional": 5.0}
BONK_FILTERS = {"lot_step_size": 1.0, "min_qty": 1.0, "min_notional": 1.0}


# ----------------------------------------------------------------------
# Unit — the predicate (single source of truth)
# ----------------------------------------------------------------------

def test_min_sellable_amount_notional_binds():
    # SOL @ $68: minNotional $5 dominates → 5/68 ≈ 0.0735 SOL
    assert abs(min_sellable_amount(68.0, SOL_FILTERS) - 5.0 / 68.0) < 1e-12
    # no filters / non-positive price → unknown → 0.0
    assert min_sellable_amount(68.0, None) == 0.0
    assert min_sellable_amount(0.0, SOL_FILTERS) == 0.0


def test_is_dust_empty_and_below_min_sellable():
    assert is_dust(0.0, 68.1, SOL_FILTERS) is True
    assert is_dust(-1.0, 68.1, SOL_FILTERS) is True
    # the exact SOL freeze residual ($0.0065)
    assert is_dust(0.000096, 68.1, SOL_FILTERS) is True
    # 0.07 SOL ≈ $4.77 < minNotional $5 → still unsellable → dust
    assert is_dust(0.07, 68.1, SOL_FILTERS) is True
    # a real ~$20 position is NOT dust
    assert is_dust(0.3, 68.1, SOL_FILTERS) is False


def test_is_dust_gate_a2_bonk_covers_the_050_band():
    """GATE A2: for BONK the predicate ($1) dominates the old $0.50, so it
    zeroes everything the $0.50 did and the [$0.50,$1) band on top."""
    price = 0.00000456
    # $0.70 residual: dust under the new rule, survived the old $0.50 threshold
    assert is_dust(0.70 / price, price, BONK_FILTERS) is True
    # a real ~$49 position is not dust
    assert is_dust(49.0 / price, price, BONK_FILTERS) is False


def test_is_dust_fallback_without_filters_preserves_050():
    # No usable filters → economic $0.50 proxy (keeps the S73 restart fix alive)
    assert is_dust(0.000096, 68.1, None) is True   # ~$0.0065 < $0.50
    assert is_dust(1.0, 68.1, None) is False        # $68 > $0.50
    assert is_dust(0.4, 1.0, {}) is True            # $0.40 < $0.50
    assert is_dust(0.6, 1.0, {}) is False           # $0.60 > $0.50


# ----------------------------------------------------------------------
# Behaviour — the live loop (the SOL freeze and its fix)
# ----------------------------------------------------------------------

def test_reentry_fires_on_dust_above_avg_the_sol_freeze():
    """The exact SOL freeze: dust residual, price stuck above avg AND above the
    buy trigger, ladder active. Pre-S105b the idle path took Path B (recalibrate)
    and skipped it (price > avg) → frozen. Post-S105b is_dust → Path A forces a
    re-entry buy that absorbs the dust into a real position."""
    bot = make_bot(capital=1000.0, capital_per_trade=20.0)
    bot.managed_by = "grid"
    bot.is_active = True
    bot._exchange_filters = dict(SOL_FILTERS)
    bot.idle_reentry_hours = 4.0
    bot.buy_pct = 3.0
    bot.sell_pct = 1.58
    bot.state.holdings = 0.000096       # dust, exactly like SOL on 2026-06-13
    bot._phantom_holdings = 0.0
    bot.state.avg_buy_price = 66.33
    bot._pct_last_buy_price = 68.1      # stale ref > 0 → idle check runs
    bot._last_sell_price = 67.9         # ladder active → dead-zone must still skip (dust)
    bot.state.total_invested = 0.0064
    bot.state.total_received = 0.0
    bot._last_trade_time = utcnow() - timedelta(hours=5)  # idle > 4h

    assert bot._position_is_dust(68.1) is True, "precondition: SOL position is dust"
    trades_before = len(bot.trade_logger.trades)

    # $68.1 is above avg ($66.33) and above buy trigger ($66.06) → the frozen point
    bot.check_price_and_execute(current_price=68.1)

    assert len(bot.trade_logger.trades) > trades_before, "idle re-entry buy must fire on dust"
    assert not bot._position_is_dust(68.1), "dust absorbed into a real position after re-entry"
    assert bot.managed_holdings > min_sellable_amount(68.1, SOL_FILTERS)


def test_real_position_above_avg_does_not_reenter():
    """Same frozen setup but a REAL position → unchanged behaviour: idle
    recalibrate is skipped above avg and NO re-entry buy fires (mirrors test_j).
    Guards the fix against touching healthy positions."""
    bot = make_bot(capital=1000.0, capital_per_trade=20.0)
    bot.managed_by = "grid"
    bot.is_active = True
    bot._exchange_filters = dict(SOL_FILTERS)
    bot.idle_reentry_hours = 4.0
    bot.buy_pct = 3.0
    bot.sell_pct = 99.0                 # disable sell so the real position is held
    bot.state.holdings = 0.3           # ~$20 real position
    bot._phantom_holdings = 0.0
    bot.state.avg_buy_price = 66.33
    bot._pct_last_buy_price = 68.1
    bot._last_sell_price = 0.0         # ladder inactive → dead-zone skipped, clean idle path
    bot.state.total_invested = 20.0
    bot._last_trade_time = utcnow() - timedelta(hours=5)

    assert bot._position_is_dust(68.1) is False, "precondition: real position"
    trades_before = len(bot.trade_logger.trades)
    ref_before = bot._pct_last_buy_price

    bot.check_price_and_execute(current_price=68.1)  # above avg → recalibrate skipped

    assert len(bot.trade_logger.trades) == trades_before, "real position must NOT re-enter"
    assert bot._pct_last_buy_price == ref_before, "buy reference unchanged (skipped above avg)"


def test_no_buy_above_avg_bypassed_for_dust_enforced_for_real():
    """The guard that would otherwise block the re-entry buy itself: it must NOT
    apply to dust (not a position) but MUST still block a real position above avg."""
    # Dust → guard bypassed → buy above avg allowed (this is what unsticks SOL)
    dusty = make_bot(capital=1000.0, capital_per_trade=20.0)
    dusty.managed_by = "grid"
    dusty._exchange_filters = dict(SOL_FILTERS)
    dusty.state.holdings = 0.000096
    dusty._phantom_holdings = 0.0
    dusty.state.avg_buy_price = 66.33
    dusty._pct_last_buy_price = 0.0
    assert dusty._execute_percentage_buy(price=68.1) is not None, \
        "dust → no-buy-above-avg guard bypassed"

    # Real position → guard enforced → buy above avg blocked (unchanged)
    real = make_bot(capital=1000.0, capital_per_trade=20.0)
    real.managed_by = "grid"
    real._exchange_filters = dict(SOL_FILTERS)
    real.state.holdings = 0.3
    real._phantom_holdings = 0.0
    real.state.avg_buy_price = 66.33
    assert real._execute_percentage_buy(price=68.1) is None, \
        "real position above avg → guard blocks (unchanged)"


# ----------------------------------------------------------------------
# Behaviour — the boot replay (state_manager), A1.2 unification
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
    def table(self, _):
        return _MockTable(self._data)


class _MockLogger:
    def __init__(self, data):
        self.client = _MockClient(data)
        self.trades = []
    def log_trade(self, **kw):
        self.trades.append(kw)
        return kw


def _replay_bot(history):
    bot = make_bot()
    bot.symbol = "TEST/USDT"
    bot.exchange = None                       # paper → replay sets holdings, no fetch_balance
    bot.trade_logger = _MockLogger(history)
    # min_notional $5, tiny step → "min sellable" ≈ $5 notional
    bot._exchange_filters = {"lot_step_size": 1e-8, "min_qty": 0.0, "min_notional": 5.0}
    return bot


def test_replay_keeps_dust_residual_at_true_cost_s113():
    """S113 churn-avg-fix: un residuo $3 (banda [$0.50,$5)) è ora TENUTO al costo
    vero sul replay (prima veniva azzerato avg+qty). Tenere l'avg onesto sulla
    polvere elimina la diluizione al re-entry → niente churn. La guard Strategy A
    esente-polvere (S105b) garantisce che NON si re-introduca il dust-trap (W1
    del CEO): dallo stato replayato un buy SOPRA avg scatta comunque e assorbe la
    polvere in una posizione vera. Mirror del live sell_pipeline:694."""
    from bot.grid.state_manager import init_avg_cost_state_from_db
    history = [
        {"side": "buy",  "amount": 4.0, "price": 1.0, "cost": 4.0, "fee": 0.0,
         "fee_asset": "USDT", "created_at": "2026-06-10T00:00:00+00:00"},
        {"side": "sell", "amount": 1.0, "price": 1.0, "cost": 1.0, "fee": 0.0,
         "fee_asset": "USDT", "created_at": "2026-06-10T01:00:00+00:00"},
    ]
    bot = _replay_bot(history)
    init_avg_cost_state_from_db(bot)

    # residual 3.0 @ $1 = $3 < min_sellable $5 → polvere → ora TENUTA al costo vero
    assert bot._pct_last_buy_price == 1.0, "replay ran (buy ref restored)"
    assert abs(bot.state.holdings - 3.0) < 1e-9, "S113: dust residual KEPT (was zeroed)"
    assert abs(bot.state.avg_buy_price - 1.0) < 1e-9, "S113: avg kept at true cost (was 0)"

    # W1 (CEO): nessun dust-trap. Un buy sopra avg deve scattare comunque per
    # l'esenzione is_dust della guard Strategy A (S105b), assorbendo la polvere.
    bot.managed_by = "grid"
    assert is_dust(bot.managed_holdings, 1.5, bot._exchange_filters), "precondition: still dust"
    trade = bot._execute_percentage_buy(price=1.5)  # above avg $1.0
    assert trade is not None, "re-entry above avg must fire on dust (no dust-trap)"
    assert not is_dust(bot.managed_holdings, 1.5, bot._exchange_filters), "dust absorbed into real position"
    assert 1.0 < bot.state.avg_buy_price < 1.5, "avg blended honestly (dust cost + new lot)"


def test_replay_keeps_healthy_residual():
    """Counter-test: a $9 residual (above min_sellable) is preserved on replay —
    real positions (BTC/BONK ~$50/$49) are untouched."""
    from bot.grid.state_manager import init_avg_cost_state_from_db
    history = [
        {"side": "buy",  "amount": 10.0, "price": 1.0, "cost": 10.0, "fee": 0.0,
         "fee_asset": "USDT", "created_at": "2026-06-10T00:00:00+00:00"},
        {"side": "sell", "amount": 1.0,  "price": 1.0, "cost": 1.0,  "fee": 0.0,
         "fee_asset": "USDT", "created_at": "2026-06-10T01:00:00+00:00"},
    ]
    bot = _replay_bot(history)
    init_avg_cost_state_from_db(bot)

    assert abs(bot.state.holdings - 9.0) < 1e-9, "healthy residual ($9 > $5) preserved"
    assert abs(bot.state.avg_buy_price - 1.0) < 1e-9
