"""
BagHolderAI - Exchange Connection
Handles connection to Binance via ccxt.
Supports both testnet (paper trading) and live mode.
"""

import ccxt
from config.settings import ExchangeConfig, TradingMode


def create_exchange() -> ccxt.binance:
    """
    Create and return a configured Binance exchange instance.
    Automatically uses testnet if TRADING_MODE=paper.
    """
    config = {
        "apiKey": ExchangeConfig.API_KEY,
        "secret": ExchangeConfig.SECRET,
        "sandbox": ExchangeConfig.TESTNET,  # ccxt sandbox = testnet
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "adjustForTimeDifference": True,
        },
    }
    
    exchange = ccxt.binance(config)
    
    # Set testnet URLs if paper trading
    if TradingMode.is_paper():
        exchange.set_sandbox_mode(True)
    
    return exchange


def test_connection(exchange: ccxt.binance) -> dict:
    """
    Test the exchange connection. Returns account info or error.
    Safe to call — only reads, never trades.
    """
    try:
        # Fetch server time (no auth needed)
        server_time = exchange.fetch_time()
        
        # Try to fetch balance (needs auth)
        balance = exchange.fetch_balance()
        
        return {
            "status": "connected",
            "mode": "testnet" if TradingMode.is_paper() else "LIVE",
            "server_time": server_time,
            "total_usdt": balance.get("USDT", {}).get("total", 0),
        }
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
