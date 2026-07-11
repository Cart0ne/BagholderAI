"""
S118 (K.1 Fase 1) — Kraken cutover pre-lavori: unit tests.

Covers the five behavioural pillars of Fase 1, each venue-gated so the
binance path stays byte-identical (§3 invariant):

  1. fee_rate dinamico: instance rate defaults to the class constant on
     binance; KrakenClient.taker_fee_rate reads the live tier, caches it,
     and falls back to the conservative 0.80% on API failure.
  2. Floor min-profit FEE-AWARE (sell_pipeline): on kraken
     min_price = avg × (1 + margine/100 + 2×fee); binance formula unchanged;
     force_all (emergency exits) bypasses the floor.
  3. Fix contabile buy-fee-in-quote (buy_pipeline): Kraken's USD BUY fee
     folds into avg + total_invested; binance base-coin fee path unchanged.
  4. Sell proceeds net of USD fee (sell_pipeline → total_received) on kraken.
  5. Boot-replay mirror (state_manager): replaying kraken trades reproduces
     the same avg/invested/received as the runtime bookkeeping.

Plus: Sherpa hands-off filter on venue='kraken' rows, and the validate=true
passthrough used by the Fase 1 "prova generale".

Run:  venv/bin/python3.13 -m pytest tests/test_kraken_fase1_s118.py -q
"""

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Same telegram stub as test_sherpa_slow_loop_gate.py — the telegram lib is
# broken on Python 3.13 (pre-existing env issue); importing bot.sherpa.main
# would otherwise fail before reaching the code under test.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from config.settings import TradingMode
from bot.grid.grid_bot import GridBot
from bot.exchanges.kraken_client import KrakenClient


# ----------------------------------------------------------------------
# Scaffolding (mirrors tests/test_accounting_avg_cost.py)
# ----------------------------------------------------------------------

class MockTradeLogger:
    def __init__(self):
        self.trades = []

    def log_trade(self, **kwargs):
        self.trades.append(kwargs)
        return kwargs


FILTERS = {"lot_step_size": 0.000001, "min_qty": 0.000001, "min_notional": 1.0}


def make_bot(venue="binance", symbol="TEST/USD", fee_rate=None,
             min_profit_pct=0.0, managed_by="grid"):
    bot = GridBot(
        exchange=None,
        trade_logger=MockTradeLogger(),
        portfolio_manager=None,
        pnl_tracker=None,
        venue=venue,
        symbol=symbol,
        capital=1000.0,
        buy_pct=1.0,
        sell_pct=1.0,
        strategy="A",
        min_profit_pct=min_profit_pct,
    )
    if fee_rate is not None:
        bot.fee_rate = fee_rate
    bot._exchange_filters = dict(FILTERS)
    bot.managed_by = managed_by
    bot.tf_exit_after_n_enabled = False
    bot.setup_grid(current_price=100.0)
    bot.state.holdings = 0.0
    bot.state.avg_buy_price = 0.0
    bot.state.total_invested = 0.0
    bot.state.total_received = 0.0
    bot.state.total_fees = 0.0
    bot.state.realized_pnl = 0.0
    bot._pct_last_buy_price = 0.0
    bot.capital_per_trade = 50.0
    bot.min_profit_pct = min_profit_pct
    return bot


class _LiveMode:
    """Temporarily flip TradingMode to live (restored on exit)."""
    def __enter__(self):
        self._saved = TradingMode.MODE
        TradingMode.MODE = "live"
    def __exit__(self, *a):
        TradingMode.MODE = self._saved


def _mock_client_buy_base(*, filled, avg_price, cost, fee, fee_currency, fee_base):
    client = MagicMock()
    client.place_market_buy_base.return_value = {
        "order_id": "OB1", "filled_amount": filled, "avg_price": avg_price,
        "cost": cost, "fee_cost": fee, "fee_currency": fee_currency,
        "fee_native_amount": fee, "fee_base": fee_base, "status": "closed",
        "raw": {},
    }
    return client


def _mock_client_sell(*, filled, avg_price, revenue, fee, fee_currency):
    client = MagicMock()
    client.place_market_sell.return_value = {
        "order_id": "OS1", "filled_amount": filled, "avg_price": avg_price,
        "cost": revenue, "fee_cost": fee, "fee_currency": fee_currency,
        "fee_native_amount": fee, "fee_base": 0.0, "status": "closed",
        "raw": {},
    }
    return client


# ----------------------------------------------------------------------
# 1. fee_rate dinamico
# ----------------------------------------------------------------------

def test_default_fee_rate_is_class_constant():
    bot = make_bot(venue="binance", symbol="TEST/USDT")
    assert bot.fee_rate == GridBot.FEE_RATE == 0.001


def test_kraken_taker_fee_rate_live_and_cached():
    ex = MagicMock()
    ex.fetch_trading_fee.return_value = {"taker": 0.006, "maker": 0.003}
    kc = KrakenClient(exchange=ex)
    assert kc.taker_fee_rate("BTC/USD") == 0.006
    assert kc.taker_fee_rate("BTC/USD") == 0.006
    assert ex.fetch_trading_fee.call_count == 1  # second read served by cache


def test_kraken_taker_fee_rate_fallback_on_error():
    ex = MagicMock()
    ex.fetch_trading_fee.side_effect = RuntimeError("api down")
    kc = KrakenClient(exchange=ex)
    assert kc.taker_fee_rate("BTC/USD") == KrakenClient.FALLBACK_TAKER_FEE == 0.008


def test_kraken_taker_fee_rate_rejects_malformed_tier():
    ex = MagicMock()
    ex.fetch_trading_fee.return_value = {"taker": 80.0}  # unit-confused response
    kc = KrakenClient(exchange=ex)
    assert kc.taker_fee_rate("BTC/USD") == KrakenClient.FALLBACK_TAKER_FEE


# ----------------------------------------------------------------------
# 2. Floor min-profit fee-aware
# ----------------------------------------------------------------------

def test_floor_kraken_blocks_sell_inside_fee_band():
    """avg=100, fee 0.8%/side → floor 101.6 (margine 0). 101.0 must be blocked."""
    bot = make_bot(venue="kraken", fee_rate=0.008)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    out = bot._execute_percentage_sell(101.0, sell_amount=0.5)
    assert out is None
    assert bot.state.holdings == 1.0  # untouched


def test_floor_kraken_allows_sell_above_fee_band():
    bot = make_bot(venue="kraken", fee_rate=0.008)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    out = bot._execute_percentage_sell(102.0, sell_amount=0.5)
    assert out is not None


def test_floor_kraken_includes_margin_on_top_of_fees():
    """margine 0.4% + 1.6% fee → floor 102.0: 101.9 blocked, 102.1 ok."""
    bot = make_bot(venue="kraken", fee_rate=0.008, min_profit_pct=0.4)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    assert bot._execute_percentage_sell(101.9, sell_amount=0.5) is None
    assert bot._execute_percentage_sell(102.1, sell_amount=0.5) is not None


def test_floor_binance_formula_unchanged():
    """Invariante §3: su binance il fee floor è 0 — solo min_profit_pct conta."""
    bot = make_bot(venue="binance", symbol="TEST/USDT", min_profit_pct=1.0)
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    assert bot._execute_percentage_sell(100.5, sell_amount=0.5) is None       # sotto 101
    assert bot._execute_percentage_sell(101.5, sell_amount=0.5) is not None   # sopra 101


def test_floor_skipped_on_force_all():
    """Un'uscita d'emergenza (force_all) non va bloccata dal floor."""
    bot = make_bot(venue="kraken", fee_rate=0.008, managed_by="tf")
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    bot._stop_loss_triggered = True  # tf_override per la guardia no-sell-at-loss
    out = bot._execute_percentage_sell(95.0, force_all=True)
    assert out is not None  # floor e guardia Strategy A non bloccano l'emergenza


# ----------------------------------------------------------------------
# 3+4. Fix contabile fee-in-quote (runtime)
# ----------------------------------------------------------------------

def test_kraken_buy_fee_in_quote_enters_avg_and_invested():
    bot = make_bot(venue="kraken", fee_rate=0.008)
    bot.exchange = MagicMock()
    bot.exchange_client = _mock_client_buy_base(
        filled=0.5, avg_price=100.0, cost=50.0, fee=0.40,
        fee_currency="USD", fee_base=0.0)
    with _LiveMode():
        out = bot._execute_percentage_buy(100.0)
    assert out is not None
    assert abs(bot.state.avg_buy_price - (50.40 / 0.5)) < 1e-9   # fee nel cost basis
    assert abs(bot.state.total_invested - 50.40) < 1e-9          # fee = cash uscito
    assert abs(bot.state.holdings - 0.5) < 1e-12                 # fee NON in coin


def test_binance_buy_base_fee_path_unchanged():
    """Invariante: fee in base coin (72a) → avg da cost/qty_net, invested=cost."""
    bot = make_bot(venue="binance", symbol="TEST/USDT")
    bot.exchange = MagicMock()
    bot.exchange_client = _mock_client_buy_base(
        filled=0.5, avg_price=100.0, cost=50.0, fee=0.05,
        fee_currency="TEST", fee_base=0.0005)
    with _LiveMode():
        out = bot._execute_percentage_buy(100.0)
    assert out is not None
    qty_net = 0.5 - 0.0005
    assert abs(bot.state.avg_buy_price - (50.0 / qty_net)) < 1e-9  # solo cost (72a P2)
    assert abs(bot.state.total_invested - 50.0) < 1e-9             # gross legacy
    assert abs(bot.state.holdings - qty_net) < 1e-12


def test_kraken_sell_proceeds_net_of_fee():
    bot = make_bot(venue="kraken", fee_rate=0.008)
    bot.exchange = MagicMock()
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    bot.exchange_client = _mock_client_sell(
        filled=0.5, avg_price=103.0, revenue=51.5, fee=0.412, fee_currency="USD")
    with _LiveMode():
        out = bot._execute_percentage_sell(103.0, sell_amount=0.5)
    assert out is not None
    assert abs(bot.state.total_received - (51.5 - 0.412)) < 1e-9   # netto USD
    # realized = revenue − cost_basis − sell_fee (buy fee già dentro l'avg)
    assert abs(out["realized_pnl"] - (51.5 - 50.0 - 0.412)) < 1e-9


def test_binance_sell_proceeds_stay_gross():
    bot = make_bot(venue="binance", symbol="TEST/USDT")
    bot.exchange = MagicMock()
    bot.state.holdings = 1.0
    bot.state.avg_buy_price = 100.0
    bot.exchange_client = _mock_client_sell(
        filled=0.5, avg_price=103.0, revenue=51.5, fee=0.0515, fee_currency="USDT")
    with _LiveMode():
        out = bot._execute_percentage_sell(103.0, sell_amount=0.5)
    assert out is not None
    assert abs(bot.state.total_received - 51.5) < 1e-9             # gross legacy


# ----------------------------------------------------------------------
# 5. Boot-replay mirror (state_manager)
# ----------------------------------------------------------------------

class _Query:
    def __init__(self, data):
        self._data = data
    def execute(self):
        return SimpleNamespace(data=self._data)
    def __getattr__(self, name):          # select/eq/order/limit → chainable
        def _chain(*a, **k):
            return self
        return _chain


class _MockSupabase:
    def __init__(self, tables):
        self._tables = tables
    def table(self, name):
        return _Query(self._tables.get(name, []))


def test_replay_mirrors_kraken_runtime_bookkeeping():
    kraken_trades = [
        {"side": "buy", "amount": 1.0, "price": 100.0, "cost": 100.0,
         "fee": 0.80, "fee_asset": "USD", "managed_by": "grid",
         "created_at": "2026-07-11T10:00:00+00:00"},
        {"side": "sell", "amount": 0.5, "price": 105.0, "cost": 52.5,
         "fee": 0.42, "fee_asset": "USD", "managed_by": "grid",
         "created_at": "2026-07-11T11:00:00+00:00"},
    ]
    bot = make_bot(venue="kraken", symbol="BTC/USD", fee_rate=0.008)
    bot.trade_logger = SimpleNamespace(client=_MockSupabase({
        "bot_config": [{"cycle": "usd_live_1"}],
        "trades": kraken_trades,
    }))
    bot.init_avg_cost_state_from_db()
    # BUY: avg = (100 + 0.80) / 1.0 = 100.80 (fee USD nel cost basis)
    assert abs(bot.state.avg_buy_price - 100.80) < 1e-9
    assert abs(bot.state.total_invested - 100.80) < 1e-9
    # SELL: received netto = 0.5×105 − 0.42; realized = (105 − 100.8)×0.5 − 0.42
    assert abs(bot.state.total_received - (52.5 - 0.42)) < 1e-9
    assert abs(bot.state.realized_pnl - ((105.0 - 100.80) * 0.5 - 0.42)) < 1e-9
    assert abs(bot.state.holdings - 0.5) < 1e-12


def test_replay_binance_rows_unchanged():
    """Invariante: righe binance (synth fee USDT) replay identico a pre-S118."""
    binance_trades = [
        {"side": "buy", "amount": 1.0, "price": 100.0, "cost": 100.0,
         "fee": 0.10, "fee_asset": "USDT", "managed_by": "grid",
         "created_at": "2026-07-11T10:00:00+00:00"},
        {"side": "sell", "amount": 0.5, "price": 105.0, "cost": 52.5,
         "fee": 0.0525, "fee_asset": "USDT", "managed_by": "grid",
         "created_at": "2026-07-11T11:00:00+00:00"},
    ]
    bot = make_bot(venue="binance", symbol="BTC/USDT")
    bot.trade_logger = SimpleNamespace(client=_MockSupabase({
        "bot_config": [{"cycle": "testnet_2"}],
        "trades": binance_trades,
    }))
    bot.init_avg_cost_state_from_db()
    assert abs(bot.state.avg_buy_price - 100.0) < 1e-9      # fee NON nel basis
    assert abs(bot.state.total_invested - 100.0) < 1e-9
    assert abs(bot.state.total_received - 52.5) < 1e-9      # gross
    assert abs(bot.state.realized_pnl - ((105.0 - 100.0) * 0.5 - 0.0525)) < 1e-9


# ----------------------------------------------------------------------
# Sherpa hands-off su venue='kraken'
# ----------------------------------------------------------------------

def test_sherpa_skips_kraken_rows_null_safe():
    from bot.sherpa.main import _fetch_active_manual_bots
    rows = [
        {"symbol": "BTC/USDT", "venue": "binance"},
        {"symbol": "BTC/USD", "venue": "kraken"},
        {"symbol": "SOL/USDT", "venue": None},   # NULL-safe → treated as binance
    ]
    sb = _MockSupabase({"bot_config": rows})
    out = _fetch_active_manual_bots(sb)
    symbols = {r["symbol"] for r in out}
    assert symbols == {"BTC/USDT", "SOL/USDT"}


# ----------------------------------------------------------------------
# validate=true passthrough (prova generale Fase 1)
# ----------------------------------------------------------------------

def test_kraken_validate_passthrough_market_sell():
    ex = MagicMock()
    ex.create_order.return_value = {"descr": {"order": "sell 0.5 SOLUSD @ market"}}
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_sell("SOL/USD", 0.5, params={"validate": True})
    ex.create_order.assert_called_once_with(
        "SOL/USD", "market", "sell", 0.5, None, {"validate": True})
    assert out is not None and out["validated"] is True
    assert out["status"] == "validated" and out["filled_amount"] == 0.0


def test_kraken_validate_passthrough_cost_buy():
    ex = MagicMock()
    ex.create_market_buy_order_with_cost.return_value = {"descr": {}}
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_buy("BTC/USD", 25.0, params={"validate": True})
    ex.create_market_buy_order_with_cost.assert_called_once_with(
        "BTC/USD", 25.0, {"validate": True})
    assert out is not None and out["validated"] is True


def test_kraken_validate_failure_returns_none():
    ex = MagicMock()
    ex.create_order.side_effect = RuntimeError("EOrder:Insufficient funds")
    kc = KrakenClient(exchange=ex)
    out = kc.place_market_buy_base("BTC/USD", 0.00005, params={"validate": True})
    assert out is None
