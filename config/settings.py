"""
BagHolderAI - Configuration
Loads environment variables and defines hardcoded trading rules.
Rules in HARDCODED_RULES cannot be modified by the AI agent.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from config directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


# === Exchange Configuration ===
class ExchangeConfig:
    API_KEY = os.getenv("BINANCE_API_KEY", "")
    SECRET = os.getenv("BINANCE_SECRET", "")
    TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    # Binance testnet URLs
    TESTNET_BASE_URL = "https://testnet.binance.vision"
    LIVE_BASE_URL = "https://api.binance.com"


# === Database Configuration ===
class DatabaseConfig:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


# === Telegram Configuration ===
class TelegramConfig:
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# === AI Sentinel Configuration ===
class SentinelConfig:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL = "claude-haiku-4-5-20251001"  # Start cheap, upgrade if needed
    CHECK_INTERVAL_MINUTES = 30  # Normal conditions
    CHECK_INTERVAL_HIGH_VOL = 15  # High volatility
    RISK_THRESHOLD = 7  # Risk > 7 = reduce exposure
    OPPORTUNITY_THRESHOLD = 8  # Opportunity > 8 = increase exposure


# === Trading Mode ===
class TradingMode:
    MODE = os.getenv("TRADING_MODE", "paper")  # "paper" or "live"
    
    @classmethod
    def is_paper(cls) -> bool:
        return cls.MODE == "paper"
    
    @classmethod
    def is_live(cls) -> bool:
        return cls.MODE == "live"


# ============================================================
# HARDCODED RULES - From Blueprint
# These are implemented in code and NOT modifiable by the AI.
# ============================================================
class HardcodedRules:
    """
    Immutable trading rules. Defined in Blueprint v1.0.
    The AI agent cannot override these. Period.
    """
    
    # Capital allocation
    MAX_CAPITAL = float(os.getenv("MAX_CAPITAL", "500"))
    RESERVE_PERCENT = 10  # 10% always in stablecoin reserve
    OPERATIONAL_CAPITAL_PERCENT = 90  # Max 90% can be traded
    
    # Strategy A - Solid Altcoins (80% of operational capital)
    STRATEGY_A_ALLOCATION = 0.80
    STRATEGY_A_MAX_PER_TOKEN = 0.30  # Max 30% on single token
    STRATEGY_A_SELL_AT_LOSS = False  # NEVER sell at loss. THE rule.
    STRATEGY_A_MIN_DAILY_PNL = -10  # Stop if daily P&L < -10€
    
    # Strategy B - Shitcoin Pump (20% of operational capital)
    STRATEGY_B_ALLOCATION = 0.20
    STRATEGY_B_MAX_PER_TRADE = 30  # Max 30€ per single trade
    STRATEGY_B_TRAILING_STOP = -0.10  # -10% from peak
    STRATEGY_B_TRAILING_ACTIVATION = 0.20  # Activate after +20%
    STRATEGY_B_TIMEOUT_HOURS = 2  # Force sell after 2h if no pump
    STRATEGY_B_SELL_AT_LOSS = True  # Accepted by design
    
    # Global limits
    MAX_DAILY_OPERATIONS = 50  # Prevent infinite loops
    
    # Take profit levels (Strategy A)
    TAKE_PROFIT_LEVELS = [
        {"threshold": 0.20, "sell_percent": 0.25},  # +20% → sell 25%
        {"threshold": 0.40, "sell_percent": 0.25},  # +40% → sell 25%
        {"threshold": 0.60, "sell_percent": 0.25},  # +60% → sell 25%
    ]
    TRAILING_STOP_AFTER_60 = -0.15  # After +60%, trail at -15%
    
    # Profit management
    PROFIT_REINVEST_RATIO = 0.50  # 50% reinvested
    PROFIT_RESERVE_RATIO = 0.50  # 50% to reserve


# === Grid Bot Configuration (adjustable by Trend Follower) ===
class GridConfig:
    DEFAULT_LEVELS = 10  # 8-12 per token
    MIN_LEVELS = 8
    MAX_LEVELS = 12


# === Trend Follower Configuration ===
class TrendConfig:
    EMA_FAST = 12
    EMA_SLOW = 26
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    TIMEFRAMES = ["1h", "4h"]
