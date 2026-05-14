"""Unit tests for bot.sentinel.inputs.alternative_fng.fetch().

The fetcher must NEVER raise — every failure mode returns None and logs
a warning. These tests cover the four documented failure modes plus the
happy path.

Run:
    python -m pytest tests/test_fng_input.py -v
"""

import os
import sys
from unittest.mock import patch, MagicMock

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sentinel.inputs import alternative_fng


def _mock_response(status_code=200, json_data=None, raise_json=False):
    m = MagicMock()
    m.status_code = status_code
    if raise_json:
        m.json.side_effect = ValueError("malformed JSON")
    else:
        m.json.return_value = json_data
    return m


def test_fetch_valid_payload():
    payload = {
        "name": "Fear and Greed Index",
        "data": [
            {
                "value": "32",
                "value_classification": "Fear",
                "timestamp": "1715692800",
                "time_until_update": "12345",
            }
        ],
    }
    with patch.object(alternative_fng.requests, "get", return_value=_mock_response(200, payload)):
        result = alternative_fng.fetch()
    assert result == {
        "fng_value": 32,
        "fng_label": "Fear",
        "fng_timestamp": 1715692800,
    }


def test_fetch_network_error_returns_none():
    with patch.object(
        alternative_fng.requests,
        "get",
        side_effect=requests.ConnectionError("network down"),
    ):
        assert alternative_fng.fetch() is None


def test_fetch_timeout_returns_none():
    with patch.object(
        alternative_fng.requests,
        "get",
        side_effect=requests.Timeout("timed out"),
    ):
        assert alternative_fng.fetch() is None


def test_fetch_http_500_returns_none():
    with patch.object(alternative_fng.requests, "get", return_value=_mock_response(500, {})):
        assert alternative_fng.fetch() is None


def test_fetch_malformed_json_returns_none():
    with patch.object(
        alternative_fng.requests,
        "get",
        return_value=_mock_response(200, None, raise_json=True),
    ):
        assert alternative_fng.fetch() is None


def test_fetch_missing_data_field_returns_none():
    with patch.object(
        alternative_fng.requests,
        "get",
        return_value=_mock_response(200, {"name": "F&G"}),
    ):
        assert alternative_fng.fetch() is None


def test_fetch_malformed_row_returns_none():
    payload = {"data": [{"value": "not_a_number", "value_classification": "Fear"}]}
    with patch.object(alternative_fng.requests, "get", return_value=_mock_response(200, payload)):
        assert alternative_fng.fetch() is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
