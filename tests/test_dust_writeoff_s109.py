"""
S109 — dust write-off as a persisted event + guarded dust-to-BNB converter
(brief DUST, scope "evento + stub", MASTER 1.4).

Part 1 (bot/grid/dust_handler.py): a write-off now emits a durable
DUST_WRITEOFF event (with written_off_at / amount / est_value) and zeroes the
state — not just a log line.

Part 2 (bot/dust_converter.py): convert_dust_to_bnb is mainnet-only and a
guarded no-op on testnet/paper (the endpoint is absent there). The real
conversion + wallet reconciliation is a go-live task; the stub makes that
explicit.

Run:
    python tests/test_dust_writeoff_s109.py
    # or: pytest tests/test_dust_writeoff_s109.py
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.grid.dust_handler as dh
import bot.dust_converter as dc


# ----------------------------------------------------------------------
# Lightweight bot stand-in (dust_handler only touches a few attributes)
# ----------------------------------------------------------------------

class _State:
    def __init__(self):
        self.holdings = 5.0
        self.avg_buy_price = 2.0


class _FakeBot:
    def __init__(self):
        self.symbol = "OP/USDT"
        self.managed_holdings = 0.1          # the managed dust to write off
        self.state = _State()
        self._exchange_filters = {"lot_step_size": 0.001}


# ----------------------------------------------------------------------
# Part 1 — write-off emits a durable event and zeroes state
# ----------------------------------------------------------------------

def test_economic_dust_emits_event_and_zeros():
    bot = _FakeBot()
    with patch.object(dh, "log_event") as mock_le:
        result = dh.handle_economic_dust(
            bot, price=1.5, reason_reject="MIN_NOTIONAL too small"
        )
    assert result is True
    assert bot.state.holdings == 0.0
    assert bot.state.avg_buy_price == 0.0
    mock_le.assert_called_once()
    kw = mock_le.call_args.kwargs
    assert kw["event"] == "DUST_WRITEOFF"
    assert kw["symbol"] == "OP/USDT"
    d = kw["details"]
    assert d["amount"] == 0.1
    assert d["price"] == 1.5
    assert d["est_value_usdt"] == round(0.1 * 1.5, 8)
    assert d["written_off_at"]  # non-empty timestamp


def test_step_size_dust_emits_event():
    bot = _FakeBot()
    with patch.object(dh, "log_event") as mock_le:
        result = dh.handle_step_size_dust(bot, amount=0.0, price=2.0)
    assert result is True
    assert bot.state.holdings == 0.0
    mock_le.assert_called_once()
    assert mock_le.call_args.kwargs["event"] == "DUST_WRITEOFF"


def test_step_size_no_writeoff_when_amount_positive():
    bot = _FakeBot()
    with patch.object(dh, "log_event") as mock_le:
        result = dh.handle_step_size_dust(bot, amount=5.0, price=2.0)
    assert result is False
    assert bot.state.holdings == 5.0  # untouched
    mock_le.assert_not_called()


def test_economic_dust_ignores_unrelated_rejection():
    bot = _FakeBot()
    with patch.object(dh, "log_event") as mock_le:
        result = dh.handle_economic_dust(
            bot, price=1.5, reason_reject="some other reason"
        )
    assert result is False
    assert bot.state.holdings == 5.0  # untouched
    mock_le.assert_not_called()


# ----------------------------------------------------------------------
# Part 2 — convert_dust_to_bnb guard (mainnet-only)
# ----------------------------------------------------------------------

def test_convert_skipped_on_testnet():
    # Default env is testnet -> no-op.
    res = dc.convert_dust_to_bnb(None)
    assert res == {"converted": False, "reason": "not-mainnet-live"}


def test_convert_stub_on_mainnet():
    with patch.object(dc.ExchangeConfig, "TESTNET", False), \
         patch.object(dc.TradingMode, "is_live", classmethod(lambda cls: True)), \
         patch.object(dc, "log_event") as mock_le:
        res = dc.convert_dust_to_bnb(None, assets=["OP"])
    assert res == {"converted": False, "reason": "mainnet-not-implemented"}
    mock_le.assert_called_once()
    assert mock_le.call_args.kwargs["event"] == "DUST_CONVERT_STUB"


def test_is_mainnet_live_false_on_testnet():
    assert dc.is_mainnet_live() is False


# ----------------------------------------------------------------------
# Standalone runner
# ----------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
