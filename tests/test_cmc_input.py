"""Unit tests for bot.sentinel.inputs.cmc_global.fetch().

Same NEVER-raise contract as F&G. Extra cases here: missing API key
(env var unset) and the nested CMC response shape (data.quote.USD).

Run:
    python -m pytest tests/test_cmc_input.py -v
"""

import os
import sys
from unittest.mock import patch, MagicMock

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sentinel.inputs import cmc_global


def _mock_response(status_code=200, json_data=None, raise_json=False):
    m = MagicMock()
    m.status_code = status_code
    if raise_json:
        m.json.side_effect = ValueError("malformed JSON")
    else:
        m.json.return_value = json_data
    return m


_VALID_PAYLOAD = {
    "data": {
        "btc_dominance": 57.34,
        "active_cryptocurrencies": 9712,
        "quote": {
            "USD": {
                "total_market_cap": 2_300_000_000_000.0,
                "total_volume_24h": 85_000_000_000.0,
            }
        },
    },
    "status": {"error_code": 0},
}


def test_fetch_valid_payload():
    with patch.dict(os.environ, {"CMC_API_KEY": "fake_key"}, clear=False):
        with patch.object(cmc_global.requests, "get", return_value=_mock_response(200, _VALID_PAYLOAD)):
            result = cmc_global.fetch()
    assert result == {
        "btc_dominance": 57.34,
        "total_market_cap_usd": 2_300_000_000_000.0,
        "total_volume_24h_usd": 85_000_000_000.0,
        "active_cryptocurrencies": 9712,
    }


def test_fetch_no_api_key_returns_none():
    # Ensure CMC_API_KEY is absent for this test.
    env = {k: v for k, v in os.environ.items() if k != "CMC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        # requests.get must NOT be called — assert via a sentinel mock.
        with patch.object(cmc_global.requests, "get") as mocked_get:
            assert cmc_global.fetch() is None
            mocked_get.assert_not_called()


def test_fetch_network_error_returns_none():
    with patch.dict(os.environ, {"CMC_API_KEY": "fake_key"}, clear=False):
        with patch.object(
            cmc_global.requests,
            "get",
            side_effect=requests.ConnectionError("network down"),
        ):
            assert cmc_global.fetch() is None


def test_fetch_http_401_returns_none():
    """Invalid CMC API key returns 401 — fetch must swallow it."""
    with patch.dict(os.environ, {"CMC_API_KEY": "bad_key"}, clear=False):
        with patch.object(cmc_global.requests, "get", return_value=_mock_response(401, {})):
            assert cmc_global.fetch() is None


def test_fetch_malformed_json_returns_none():
    with patch.dict(os.environ, {"CMC_API_KEY": "fake_key"}, clear=False):
        with patch.object(
            cmc_global.requests,
            "get",
            return_value=_mock_response(200, None, raise_json=True),
        ):
            assert cmc_global.fetch() is None


def test_fetch_missing_data_returns_none():
    with patch.dict(os.environ, {"CMC_API_KEY": "fake_key"}, clear=False):
        with patch.object(cmc_global.requests, "get", return_value=_mock_response(200, {"status": {}})):
            assert cmc_global.fetch() is None


def test_fetch_malformed_data_returns_none():
    """Missing nested fields in data → None, not exception."""
    bad = {"data": {"btc_dominance": 57.0}}  # missing quote.USD
    with patch.dict(os.environ, {"CMC_API_KEY": "fake_key"}, clear=False):
        with patch.object(cmc_global.requests, "get", return_value=_mock_response(200, bad)):
            assert cmc_global.fetch() is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
