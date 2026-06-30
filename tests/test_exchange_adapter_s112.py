"""
S112 — Exchange adapter (ExchangeClient + factory + Binance/Kraken).

All tests are mock-based / offline: no network, no API keys. The Kraken public
AssetPairs resolution (BTC/SOL/BONK in USD) was verified live during S112b and
is documented in the report; here we lock the behaviour that matters for the
§3 invariant and the Kraken fee model.
"""

from unittest.mock import MagicMock, patch

import pytest

from bot.exchanges import create_client, BinanceClient, ExchangeClient
from bot.exchanges.kraken_client import KrakenClient
from bot import exchange_orders


# ---------------------------------------------------------------------------
# Factory + invariant
# ---------------------------------------------------------------------------

def test_factory_default_is_binance():
    """EXCHANGE unset/default → BinanceClient (§3 invariant: nothing changes)."""
    c = create_client()
    assert isinstance(c, BinanceClient)
    assert c.name == "binance"
    assert c.quote_currency == "USDT"


def test_factory_explicit_kraken():
    c = create_client("kraken")
    assert isinstance(c, KrakenClient)
    assert c.name == "kraken"
    assert c.quote_currency == "USD"


def test_factory_unknown_raises():
    with pytest.raises(ValueError):
        create_client("bitstamp")


def test_both_clients_are_exchangeclients():
    assert isinstance(create_client("binance"), ExchangeClient)
    assert isinstance(create_client("kraken"), ExchangeClient)


# ---------------------------------------------------------------------------
# BinanceClient — delegates VERBATIM (the invariant proof)
# ---------------------------------------------------------------------------

def test_binance_delegates_market_buy():
    bc = BinanceClient(exchange=MagicMock())
    with patch.object(exchange_orders, "place_market_buy", return_value={"ok": 1}) as spy:
        out = bc.place_market_buy("BTC/USDT", 25.0)
    spy.assert_called_once_with(bc._exchange, "BTC/USDT", 25.0)
    assert out == {"ok": 1}


def test_binance_delegates_market_sell_and_buy_base():
    bc = BinanceClient(exchange=MagicMock())
    with patch.object(exchange_orders, "place_market_sell", return_value={"s": 1}) as s_spy, \
         patch.object(exchange_orders, "place_market_buy_base", return_value={"b": 1}) as b_spy:
        bc.place_market_sell("SOL/USDT", 1.0)
        bc.place_market_buy_base("SOL/USDT", 2.0)
    s_spy.assert_called_once_with(bc._exchange, "SOL/USDT", 1.0)
    b_spy.assert_called_once_with(bc._exchange, "SOL/USDT", 2.0)


def test_binance_advanced_primitives_raise():
    """Binance must NOT silently no-op the Kraken-only primitives."""
    bc = BinanceClient(exchange=MagicMock())
    for call in (
        lambda: bc.place_order_batch("BTC/USDT", []),
        lambda: bc.cancel_all_after(60),
        lambda: bc.fee_tier(),
        lambda: bc.edit_order("id"),
    ):
        with pytest.raises(NotImplementedError):
            call()


# ---------------------------------------------------------------------------
# KrakenClient — order routing + fee model (the §5 divergence)
# ---------------------------------------------------------------------------

def _kraken_with_mock():
    return KrakenClient(exchange=MagicMock())


def test_kraken_market_buy_uses_native_cost_order():
    kc = _kraken_with_mock()
    kc._exchange.create_market_buy_order_with_cost.return_value = {
        "id": "OABC", "status": "closed", "filled": 0.001, "average": 59000.0,
        "cost": 59.0, "fee": {"cost": 0.1475, "currency": "USD"},
    }
    out = kc.place_market_buy("BTC/USD", 59.0)
    kc._exchange.create_market_buy_order_with_cost.assert_called_once_with("BTC/USD", 59.0)
    assert out["order_id"] == "OABC"
    assert out["filled_amount"] == 0.001
    assert out["fee_cost"] == 0.1475
    assert out["fee_currency"] == "USD"
    assert out["fee_base"] == 0.0          # Kraken never deducts fee from base


def test_kraken_market_sell_uses_create_order():
    kc = _kraken_with_mock()
    kc._exchange.create_order.return_value = {
        "id": "OSELL", "status": "closed", "filled": 2.0, "average": 74.0,
        "cost": 148.0, "fee": {"cost": 0.37, "currency": "USD"},
    }
    out = kc.place_market_sell("SOL/USD", 2.0)
    kc._exchange.create_order.assert_called_once_with("SOL/USD", "market", "sell", 2.0)
    assert out["fee_cost"] == 0.37
    assert out["fee_base"] == 0.0


def test_kraken_fee_base_always_zero_even_if_fee_in_base():
    """Even if the broker ever reports a base-coin fee, Kraken normalize keeps
    fee_base=0.0 (its model is quote-fee); the value is still recorded as cost."""
    kc = _kraken_with_mock()
    kc._exchange.create_order.return_value = {
        "id": "OX", "status": "closed", "filled": 1.0, "average": 100.0,
        "cost": 100.0, "fee": {"cost": 0.004, "currency": "BTC"},
    }
    out = kc.place_market_buy_base("BTC/USD", 1.0)
    assert out["fee_base"] == 0.0
    assert out["fee_cost"] == 0.004        # native value preserved as cost


def test_kraken_unfilled_order_is_noop():
    kc = _kraken_with_mock()
    kc._exchange.create_order.return_value = {"id": "OZ", "status": "canceled", "filled": 0}
    assert kc.place_market_sell("BONK/USD", 1_000_000) is None


def test_kraken_no_synth_fee():
    """A zero-fee fill must NOT be back-filled with a synthetic FEE_RATE
    (that's a Binance-testnet behaviour; Kraken fees are real)."""
    kc = _kraken_with_mock()
    kc._exchange.create_order.return_value = {
        "id": "OF", "status": "closed", "filled": 1.0, "average": 100.0,
        "cost": 100.0, "fee": {"cost": 0.0, "currency": "USD"},
    }
    out = kc.place_market_sell("SOL/USD", 1.0)
    assert out["fee_cost"] == 0.0          # stays 0, no synth top-up


def test_kraken_advanced_primitives_route_to_ccxt():
    kc = _kraken_with_mock()
    kc.cancel_all_after(60)
    kc._exchange.cancel_all_orders_after.assert_called_once_with(60)
    kc.cancel_all("BTC/USD")
    kc._exchange.cancel_all_orders.assert_called_once_with("BTC/USD")
    kc.place_order_batch("BTC/USD", [{"type": "limit", "side": "buy", "amount": 1, "price": 100}])
    assert kc._exchange.create_orders.called


def test_kraken_get_all_symbols_filters_spot_and_quote():
    kc = _kraken_with_mock()
    kc._exchange.markets = {
        "BTC/USD": {"spot": True},
        "SOL/USD": {"spot": True},
        "BTC/EUR": {"spot": True},
        "WEIRD/USD": {"spot": False},   # synthetic/derivative → excluded
    }
    kc._exchange.load_markets.return_value = None
    out = kc.get_all_symbols("/USD")
    assert set(out) == {"BTC/USD", "SOL/USD"}
