"""
BagHolderAI - Main Entry Point
An AI trading agent that's honest about its incompetence.

Usage:
    python main.py              # Start the bot
    python main.py --test       # Test exchange connection only
    python main.py --status     # Show current config and status
"""

import sys
from config.settings import (
    TradingMode, HardcodedRules, ExchangeConfig,
    GridConfig, TrendConfig, SentinelConfig
)
from bot.exchange import create_exchange, test_connection


def print_banner():
    print("""
    ╔══════════════════════════════════════════╗
    ║           🎒 BagHolderAI 🎒              ║
    ║   "Holding bags so you don't have to"    ║
    ║          ...actually, I do too.          ║
    ╚══════════════════════════════════════════╝
    """)


def print_status():
    """Print current configuration and status."""
    mode = "🟡 PAPER TRADING" if TradingMode.is_paper() else "🔴 LIVE TRADING"
    testnet = "Yes" if ExchangeConfig.TESTNET else "NO — REAL MONEY"
    api_configured = "Yes" if ExchangeConfig.API_KEY else "No — needs .env"
    
    print(f"""
    Mode:           {mode}
    Testnet:        {testnet}
    API configured: {api_configured}
    
    === Hardcoded Rules ===
    Max capital:        €{HardcodedRules.MAX_CAPITAL}
    Reserve:            {HardcodedRules.RESERVE_PERCENT}%
    Strategy A:         {HardcodedRules.STRATEGY_A_ALLOCATION * 100}% (solid alts)
    Strategy B:         {HardcodedRules.STRATEGY_B_ALLOCATION * 100}% (shitcoins)
    Sell at loss (A):   {"NEVER" if not HardcodedRules.STRATEGY_A_SELL_AT_LOSS else "Yes"}
    Sell at loss (B):   {"Yes (after timeout)" if HardcodedRules.STRATEGY_B_SELL_AT_LOSS else "No"}
    Max ops/day:        {HardcodedRules.MAX_DAILY_OPERATIONS}
    Min daily P&L (A):  €{HardcodedRules.STRATEGY_A_MIN_DAILY_PNL}
    
    === Grid Bot ===
    Levels:             {GridConfig.MIN_LEVELS}-{GridConfig.MAX_LEVELS}
    
    === Trend Follower ===
    EMA:                {TrendConfig.EMA_FAST}/{TrendConfig.EMA_SLOW}
    RSI:                {TrendConfig.RSI_PERIOD} (OB:{TrendConfig.RSI_OVERBOUGHT} / OS:{TrendConfig.RSI_OVERSOLD})
    Timeframes:         {', '.join(TrendConfig.TIMEFRAMES)}
    
    === Sentinel ===
    Model:              {SentinelConfig.MODEL}
    Check interval:     {SentinelConfig.CHECK_INTERVAL_MINUTES}min
    Risk threshold:     {SentinelConfig.RISK_THRESHOLD}/10
    """)


def run_test():
    """Test exchange connection."""
    print("Testing exchange connection...")
    exchange = create_exchange()
    result = test_connection(exchange)
    
    if result["status"] == "connected":
        print(f"  ✅ Connected ({result['mode']})")
        print(f"  USDT balance: {result['total_usdt']}")
    else:
        print(f"  ❌ {result['status']}: {result.get('message', 'Unknown error')}")
    
    return result


def main():
    print_banner()
    
    if "--status" in sys.argv:
        print_status()
        return
    
    if "--test" in sys.argv:
        run_test()
        return
    
    # Normal startup
    print_status()
    
    if not ExchangeConfig.API_KEY:
        print("  ⚠️  No API key configured. Set up your .env file first.")
        print("  Copy config/.env.example to config/.env and fill in your keys.")
        return
    
    result = run_test()
    if result["status"] != "connected":
        print("  Cannot start without exchange connection. Fix the error above.")
        return
    
    print("\n  🚀 Ready to trade. (Grid Bot not implemented yet — coming in Phase 1)")
    print("  For now, run with --test or --status.\n")


if __name__ == "__main__":
    main()
