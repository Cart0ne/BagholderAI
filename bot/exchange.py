"""
BagHolderAI - Exchange Connection
Handles connection to Binance via ccxt.

Paper trading: connects to LIVE Binance (read-only) for real prices.
Live trading: connects to LIVE Binance (read + trade).

We don't use Binance testnet because:
- Testnet requires separate API keys
- Testnet prices are fake and don't reflect real market
- Our paper trading simulates fills internally, it just needs real prices
"""

import ccxt
from config.settings import ExchangeConfig, TradingMode


def create_exchange() -> ccxt.binance:
    """
    Create and return a configured Binance exchange instance.
    Paper mode: no API keys needed, just reads public price data.
    Live mode: requires API keys for trading.
    """
    config = {
        "sandbox": False,  # Always use live API for real prices
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "adjustForTimeDifference": True,
        },
    }
    
    # Only include API keys in live mode
    if TradingMode.is_live():
        config["apiKey"] = ExchangeConfig.API_KEY
        config["secret"] = ExchangeConfig.SECRET
    
    exchange = ccxt.binance(config)
    
    return exchange


def test_connection(exchange: ccxt.binance) -> dict:
    """
    Test the exchange connection. Returns account info or error.
    Paper mode: just fetches a price (no auth needed).
    Live mode: also checks balance (needs auth).
    """
    try:
        # Fetch a real price — proves connection works
        ticker = exchange.fetch_ticker("BTC/USDT")
        
        result = {
            "status": "connected",
            "mode": "PAPER (live prices)" if TradingMode.is_paper() else "LIVE",
            "btc_price": ticker["last"],
        }
        
        # In live mode, also check balance
        if TradingMode.is_live():
            balance = exchange.fetch_balance()
            result["total_usdt"] = balance.get("USDT", {}).get("total", 0)
        
        return result
        
    except ccxt.AuthenticationError:
        return {
            "status": "auth_error",
            "message": "API key invalid or missing. Check .env file.",
        }
    except ccxt.NetworkError as e:
        return {
            "status": "network_error",
            "message": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


def fetch_ticker(exchange: ccxt.binance, symbol: str) -> dict:
    """
    Fetch current ticker for a symbol. No auth needed.
    Returns: {"last": price, "bid": bid, "ask": ask, "volume": vol}
    """
    return exchange.fetch_ticker(symbol)
