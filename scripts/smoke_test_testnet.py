"""
S67 — smoke test for the LIVE TESTNET path.

Read-only: fetches BTC/USDT ticker + USDT balance from
testnet.binance.vision via the new ccxt sandbox=True path. No order
placement, no DB write. Use after .env has been updated with testnet
API keys to verify the credentials + path work end-to-end.

Usage (Mac Mini):
    cd /Volumes/Archivio/bagholderai
    source venv/bin/activate
    python3.13 scripts/smoke_test_testnet.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.exchange import create_exchange, test_connection
from config.settings import TradingMode, ExchangeConfig


def main() -> int:
    print(f"TRADING_MODE: {TradingMode.MODE}")
    print(f"BINANCE_TESTNET: {ExchangeConfig.TESTNET}")
    print(f"is_live(): {TradingMode.is_live()}")
    print(f"is_paper(): {TradingMode.is_paper()}")
    print()

    print("Creating exchange instance...")
    ex = create_exchange()
    api_url = ex.urls.get("api", "unknown")
    print(f"ccxt urls.api: {api_url}")
    print()

    print("Calling test_connection() (fetch_ticker + fetch_balance if live)...")
    result = test_connection(ex)
    print("=== Result ===")
    print(json.dumps(result, indent=2, default=str))

    if result.get("status") == "connected":
        print()
        print("Path is healthy. NO orders were placed.")
        return 0
    else:
        print()
        print("Path FAILED. Check the error above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
