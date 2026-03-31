"""
Test script for daily commentary generation.
Runs the commentary function in isolation with fake portfolio data.
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import DatabaseConfig
from db.client import get_client
from commentary import generate_daily_commentary

# Fake portfolio data (mirrors what grid_runner builds)
fake_portfolio_data = {
    "total_value": 499.60,
    "cash": 450.55,
    "holdings_value": 49.05,
    "initial_capital": 500.00,
    "total_pnl": -0.40,
    "positions": [
        {
            "symbol": "BTC/USDT",
            "holdings": 0.0003,
            "value": 24.85,
            "avg_buy_price": 83500.0,
            "unrealized_pnl": -0.12,
            "unrealized_pnl_pct": -0.49,
            "realized_pnl": 0.0,
            "live_price": 82833.0,
        },
        {
            "symbol": "SOL/USDT",
            "holdings": 0.095,
            "value": 12.32,
            "avg_buy_price": 131.0,
            "unrealized_pnl": -0.16,
            "unrealized_pnl_pct": -1.25,
            "realized_pnl": 0.0,
            "live_price": 129.7,
        },
        {
            "symbol": "BONK/USDT",
            "holdings": 700.0,
            "value": 11.87,
            "avg_buy_price": 0.0000172,
            "unrealized_pnl": -0.12,
            "unrealized_pnl_pct": -1.03,
            "realized_pnl": 0.0,
            "live_price": 0.00001696,
        },
    ],
    "day_number": 2,
    "today_trades_count": 4,
    "today_buys": 4,
    "today_sells": 0,
    "today_fees": 0.02,
    "today_realized": 0.00,
}


def main():
    print("=" * 60)
    print("BagHolderAI - Commentary Test")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment.")
        print("Make sure config/.env has the key set.")
        sys.exit(1)
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")

    # Init Supabase
    print("Connecting to Supabase...")
    supabase = get_client()
    print("Connected.")

    # Generate commentary
    print("\nCalling Haiku for daily commentary...")
    result = generate_daily_commentary(fake_portfolio_data, supabase)

    if result:
        print(f"\n--- Commentary ---\n{result}\n--- End ---")

        # Verify it was saved
        from datetime import date
        check = (
            supabase.table("daily_commentary")
            .select("*")
            .eq("date", str(date.today()))
            .execute()
        )
        if check.data:
            row = check.data[0]
            print(f"\nSaved to Supabase:")
            print(f"  date: {row['date']}")
            print(f"  model: {row.get('model_used')}")
            print(f"  created_at: {row.get('created_at')}")
            print(f"  commentary length: {len(row['commentary'])} chars")
        else:
            print("\nWARNING: Row not found in Supabase after upsert!")
    else:
        print("\nERROR: Commentary generation returned None.")
        sys.exit(1)

    print("\nTest completed successfully.")


if __name__ == "__main__":
    main()
