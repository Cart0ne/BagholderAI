"""
BagHolderAI - Exchange Connection
Handles connection to Binance via ccxt.

Modes:
- Paper trading: connects to LIVE Binance (read-only) for real prices.
  Fills are simulated internally. No API keys needed.
- Live + TESTNET: connects to testnet.binance.vision with testnet API keys.
  Real fills, fake money, realistic slippage/latency. The "no soldi a
  rischio" path used for accounting verification before mainnet.
- Live + MAINNET: connects to api.binance.com with mainnet API keys.
  Real money, real fills.

66a Step 3 (Operation Clean Slate): testnet path reactivated. Pre-S67
the bot bypassed testnet because the v3 paper era simulated everything
internally. Now we want Binance to write its own realized_pnl on each
sell so we can compare it to ours and certify the accounting convention.
"""

import ccxt
from config.settings import ExchangeConfig, TradingMode


def create_exchange() -> ccxt.binance:
    """
    Create and return a configured Binance exchange instance.

    - Paper mode: live API, no auth, sandbox=False (read-only prices).
    - Live + TESTNET=true: testnet API + testnet keys, sandbox=True.
    - Live + TESTNET=false: live API + mainnet keys, sandbox=False.
    """
    use_testnet = TradingMode.is_live() and ExchangeConfig.TESTNET
    config = {
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "adjustForTimeDifference": True,
            # Brief 73c (S73 2026-05-12): ccxt default for Binance MARKET
            # BUY converts `amount` (base) into `quoteOrderQty=amount*lastPrice`
            # under the hood. This breaks `place_market_buy_base` whose
            # entire purpose is to submit a deterministic, lot-step-rounded
            # base amount. Setting this to False makes ccxt pass through
            # the base quantity to Binance's `quantity` field, exactly what
            # we want for the thin-book LOT_SIZE-safe path. Quote-order
            # call site (place_market_buy) is unaffected because it
            # explicitly sets `params['quoteOrderQty']` which always wins.
            "createMarketBuyOrderRequiresPrice": False,
        },
    }

    # Only include API keys in live mode (mainnet OR testnet)
    if TradingMode.is_live():
        config["apiKey"] = ExchangeConfig.API_KEY
        config["secret"] = ExchangeConfig.SECRET

    exchange = ccxt.binance(config)

    # ccxt v3+: sandbox is set via the dedicated method, NOT via the
    # config dict (the "sandbox" config key is silently ignored for
    # Binance and the URLs stay on api.binance.com).
    if use_testnet:
        exchange.set_sandbox_mode(True)

    return exchange


def test_connection(exchange: ccxt.binance) -> dict:
    """
    Test the exchange connection. Returns account info or error.
    Paper mode: just fetches a price (no auth needed).
    Live mode (testnet or mainnet): also checks balance (needs auth).
    """
    try:
        # Fetch a real price — proves connection works
        ticker = exchange.fetch_ticker("BTC/USDT")

        if TradingMode.is_paper():
            mode_label = "PAPER (live prices)"
        elif ExchangeConfig.TESTNET:
            mode_label = "LIVE TESTNET"
        else:
            mode_label = "LIVE MAINNET"

        result = {
            "status": "connected",
            "mode": mode_label,
            "btc_price": ticker["last"],
        }

        # In live mode (testnet or mainnet), also check balance
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
