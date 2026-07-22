"""
S122 (sherpa-on-kraken) — Sherpa now DRIVES Kraken /USD rows.

Two code changes, both required by Opzione B (2b Sherpa-driven):
  a) the Fase-1 hands-off filter (main.py) is removed → Sherpa's active-bot
     fetch now RETURNS venue='kraken' rows (it excluded them before);
  b) the /USD symbol maps to its /USDT Binance twin (shared to_binance_symbol)
     so volatility + price fetch return real values instead of 0.0/fallback.

The load-bearing test is INVARIANT BINANCE: to_binance_symbol must be
byte-identical on /USDT symbols (the file runs on the 4 live grids).

Run:  venv/bin/python3.13 -m pytest tests/test_sherpa_on_kraken_s122.py -q
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Telegram lib is broken on Python 3.13 — stub before importing the sherpa stack.
_fake_telegram = types.ModuleType("telegram")
_fake_telegram.Bot = object  # type: ignore[attr-defined]
_fake_constants = types.ModuleType("telegram.constants")
_fake_constants.ParseMode = type("ParseMode", (), {"HTML": "HTML"})
sys.modules.setdefault("telegram", _fake_telegram)
sys.modules.setdefault("telegram.constants", _fake_constants)

from unittest.mock import MagicMock

from bot.sentinel.inputs.binance_btc import to_binance_symbol
import bot.sherpa.volatility as vol
import bot.sherpa.main as sherpa_main


# ----------------------------------------------------------------------
# (b) symbol mapping — INVARIANT BINANCE + /USD proxy
# ----------------------------------------------------------------------

def test_usdt_symbols_are_byte_identical():
    """The load-bearing invariant: /USDT path unchanged vs the old
    symbol.replace('/', '') on the 4 live grids."""
    for s in ("BTC/USDT", "SOL/USDT", "BONK/USDT", "ETH/USDT"):
        assert to_binance_symbol(s) == s.replace("/", "")


def test_usd_maps_to_usdt_twin():
    assert to_binance_symbol("BTC/USD") == "BTCUSDT"
    assert to_binance_symbol("SOL/USD") == "SOLUSDT"
    assert to_binance_symbol("BONK/USD") == "BONKUSDT"


def test_mapping_edge_cases():
    # only an exact '/USD' suffix is remapped — '/USDC' and '/USDT' are not
    assert to_binance_symbol("BTC/USDC") == "BTCUSDC"
    assert to_binance_symbol("BTC/USDT") == "BTCUSDT"
    assert to_binance_symbol("BTCUSDT") == "BTCUSDT"  # already concatenated


def test_volatility_wrapper_delegates_to_shared():
    assert vol._to_binance_symbol("BTC/USD") == "BTCUSDT"
    assert vol._to_binance_symbol("BTC/USDT") == "BTCUSDT"


def test_fetch_stdev_uses_usdt_twin_for_usd(monkeypatch):
    """A /USD row must fetch the /USDT twin's klines and return a REAL stdev,
    not 0.0/fallback (the whole reason Sherpa was hands-off on Kraken)."""
    called = {}

    def fake_klines(binance_symbol, limit=None):
        called["symbol"] = binance_symbol
        # rising then falling closes → non-zero log-return stdev
        return [(i, 100.0 + (i % 5)) for i in range(limit or 24)]

    monkeypatch.setattr(vol, "fetch_klines_1h", fake_klines)
    vol._stdev_cache.clear()
    stdev = vol._fetch_stdev("BTC/USD")
    assert called["symbol"] == "BTCUSDT"       # mapped, not the bogus 'BTCUSD'
    assert stdev > 0.0                          # real value, not fallback


def test_fetch_symbol_price_maps_usd(monkeypatch):
    seen = {}

    def fake_price(binance_symbol):
        seen["symbol"] = binance_symbol
        return 65000.0

    monkeypatch.setattr(sherpa_main, "fetch_price", fake_price)
    out = sherpa_main._fetch_symbol_price("BTC/USD")
    assert seen["symbol"] == "BTCUSDT"
    assert out == 65000.0


# ----------------------------------------------------------------------
# (a) filter removal — Sherpa now sees Kraken rows
# ----------------------------------------------------------------------

def _fake_supabase(rows):
    resp = MagicMock()
    resp.data = rows
    sb = MagicMock()
    (sb.table.return_value.select.return_value
       .eq.return_value.eq.return_value.execute.return_value) = resp
    return sb


def test_sherpa_now_sees_kraken_rows():
    rows = [
        {"symbol": "BTC/USDT", "venue": "binance"},
        {"symbol": "BTC/USD", "venue": "kraken"},
        {"symbol": "SOL/USDT", "venue": None},   # null venue → treated binance
    ]
    out = sherpa_main._fetch_active_manual_bots(_fake_supabase(rows))
    syms = {r["symbol"] for r in out}
    assert "BTC/USD" in syms          # was EXCLUDED pre-S122, now driven
    assert "BTC/USDT" in syms         # binance still present
    assert "SOL/USDT" in syms         # null-venue still present
    assert len(out) == 3


def test_sherpa_returns_empty_on_no_rows():
    out = sherpa_main._fetch_active_manual_bots(_fake_supabase([]))
    assert out == []
