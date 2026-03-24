"""
BagHolderAI - Database Client
Handles all Supabase interactions: logging trades, updating portfolio, etc.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from config.settings import DatabaseConfig


def get_client():
    """
    Create and return a Supabase client.
    Lazy import to avoid errors when supabase isn't installed yet.
    """
    from supabase import create_client
    return create_client(DatabaseConfig.SUPABASE_URL, DatabaseConfig.SUPABASE_KEY)


class TradeLogger:
    """Logs every trade the bot makes."""
    
    def __init__(self):
        self.client = get_client()
    
    def log_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        fee: float,
        strategy: str,
        brain: str,
        reason: str,
        mode: str = "paper",
        exchange_order_id: Optional[str] = None,
        realized_pnl: Optional[float] = None,
        buy_trade_id: Optional[str] = None,
        cost: Optional[float] = None,
    ) -> dict:
        """Log a trade to the database."""
        data = {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "cost": round(cost, 8) if cost is not None else round(amount * price, 8),
            "fee": fee,
            "strategy": strategy,
            "brain": brain,
            "reason": reason,
            "mode": mode,
            "exchange_order_id": exchange_order_id,
            "realized_pnl": realized_pnl,
            "buy_trade_id": buy_trade_id,
        }
        
        result = self.client.table("trades").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """Fetch recent trades with optional filters."""
        query = self.client.table("trades").select("*").order("created_at", desc=True).limit(limit)
        
        if symbol:
            query = query.eq("symbol", symbol)
        if strategy:
            query = query.eq("strategy", strategy)
        
        result = query.execute()
        return result.data or []
    
    def get_daily_trade_count(self) -> int:
        """Count today's trades (for daily limit check)."""
        today = date.today().isoformat()
        result = (
            self.client.table("trades")
            .select("id", count="exact")
            .gte("created_at", f"{today}T00:00:00")
            .execute()
        )
        return result.count or 0

    def get_today_trades(self) -> list:
        """Fetch all of today's trades."""
        today = date.today().isoformat()
        result = (
            self.client.table("trades")
            .select("*")
            .gte("created_at", f"{today}T00:00:00")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

class PortfolioManager:
    """Manages current holdings."""
    
    def __init__(self):
        self.client = get_client()
    
    def get_portfolio(self) -> list:
        """Get all current holdings."""
        result = self.client.table("portfolio").select("*").gt("amount", 0).execute()
        return result.data or []
    
    def update_position(
        self,
        symbol: str,
        strategy: str,
        amount: float,
        avg_buy_price: float,
        current_price: Optional[float] = None,
    ) -> dict:
        """Update or create a portfolio position."""
        unrealized_pnl = None
        if current_price and avg_buy_price > 0:
            unrealized_pnl = round((current_price - avg_buy_price) * amount, 8)
        
        data = {
            "symbol": symbol,
            "strategy": strategy,
            "amount": amount,
            "avg_buy_price": avg_buy_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        result = (
            self.client.table("portfolio")
            .upsert(data, on_conflict="symbol")
            .execute()
        )
        return result.data[0] if result.data else {}
    
    def get_total_allocation(self) -> float:
        """Get total capital currently allocated (for limit checks)."""
        portfolio = self.get_portfolio()
        return sum(p.get("amount", 0) * p.get("avg_buy_price", 0) for p in portfolio)


class DailyPnLTracker:
    """Tracks daily performance."""
    
    def __init__(self):
        self.client = get_client()
    
    def record_daily(
        self,
        total_value: float,
        daily_pnl: float,
        cumulative_pnl: float,
        strategy_a_pnl: float = 0,
        strategy_b_pnl: float = 0,
        total_fees: float = 0,
        trades_count: int = 0,
        pool_a: float = 0,
        pool_b: float = 0,
        reserve: float = 0,
    ) -> dict:
        """Record end-of-day summary."""
        data = {
            "date": date.today().isoformat(),
            "total_value": total_value,
            "daily_pnl": daily_pnl,
            "cumulative_pnl": cumulative_pnl,
            "strategy_a_pnl": strategy_a_pnl,
            "strategy_b_pnl": strategy_b_pnl,
            "total_fees": total_fees,
            "trades_count": trades_count,
            "pool_a": pool_a,
            "pool_b": pool_b,
            "reserve": reserve,
        }
        
        result = (
            self.client.table("daily_pnl")
            .upsert(data, on_conflict="date")
            .execute()
        )
        return result.data[0] if result.data else {}
    
    def get_daily_pnl_today(self) -> float:
        """Get today's P&L (for daily loss limit check)."""
        today = date.today().isoformat()
        result = (
            self.client.table("daily_pnl")
            .select("daily_pnl")
            .eq("date", today)
            .execute()
        )
        if result.data:
            return float(result.data[0].get("daily_pnl", 0))
        return 0.0


class SentinelLogger:
    """Logs AI Sentinel analyses."""
    
    def __init__(self):
        self.client = get_client()
    
    def log_analysis(
        self,
        risk_score: int,
        opportunity_score: int,
        summary: str,
        action_taken: Optional[str] = None,
        news_sources: Optional[dict] = None,
        llm_model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0,
    ) -> dict:
        """Log a Sentinel analysis."""
        data = {
            "risk_score": risk_score,
            "opportunity_score": opportunity_score,
            "summary": summary,
            "action_taken": action_taken,
            "news_sources": news_sources,
            "llm_model": llm_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
        
        result = self.client.table("sentinel_logs").insert(data).execute()
        return result.data[0] if result.data else {}
