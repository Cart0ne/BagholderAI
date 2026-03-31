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

# Real portfolio data for 2026-03-31 (Day 2)
fake_portfolio_data = {
    "total_value": 500.51,
    "cash": 444.75,
    "holdings_value": 55.76,
    "initial_capital": 500.00,
    "total_pnl": 0.51,
    "positions": [
        {
            "symbol": "BTC/USDT",
            "value": 12.65,
            "unrealized_pnl": 0.16,
            "unrealized_pnl_pct": 1.32,
        },
        {
            "symbol": "SOL/USDT",
            "value": 24.93,
            "unrealized_pnl": -0.04,
            "unrealized_pnl_pct": -0.16,
        },
        {
            "symbol": "BONK/USDT",
            "value": 18.18,
            "unrealized_pnl": 0.19,
            "unrealized_pnl_pct": 1.04,
        },
    ],
    "day_number": 2,
    "today_trades_count": 2,
    "today_buys": 0,
    "today_sells": 2,
    "today_fees": 0.0,
    "today_realized": 0.18,
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
            .order("created_at", desc=True)
            .limit(1)
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
