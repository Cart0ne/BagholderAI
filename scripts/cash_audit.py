"""
BagHolderAI — Cash Audit Script
================================
Retroactive cash position audit per symbol.

Queries ALL v3 trades from Supabase, reconstructs true cash balances,
and compares against capital allocations (fetched live from bot_config).

Usage:
    python -m scripts.cash_audit

Read-only. Does NOT modify any data.
"""

import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client

# Fallback capital allocations (used if bot_config row is missing)
_DEFAULT_ALLOCATIONS = {
    "BTC/USDT":  200.0,
    "SOL/USDT":  150.0,
    "BONK/USDT": 150.0,
}
TOTAL_STARTING_CAPITAL = 500.0
CONFIG_VERSION = "v3"


def fetch_capital_allocations(client) -> dict:
    """Read live capital_allocation from bot_config in Supabase."""
    try:
        result = (
            client.table("bot_config")
            .select("symbol,capital_allocation")
            .execute()
        )
        rows = result.data or []
        return {r["symbol"]: float(r["capital_allocation"]) for r in rows if r.get("capital_allocation")}
    except Exception as e:
        print(f"  [warn] Could not fetch bot_config: {e} — using defaults")
        return {}


def fetch_trades(client, symbol: str) -> list:
    """Fetch all v3 trades for a symbol, chronologically."""
    result = (
        client.table("trades")
        .select("side,amount,price,cost,fee,created_at")
        .eq("symbol", symbol)
        .eq("config_version", CONFIG_VERSION)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def fetch_reserve_total(client, symbol: str) -> float:
    """Sum all reserve_ledger entries for a symbol (v3)."""
    try:
        result = (
            client.table("reserve_ledger")
            .select("amount")
            .eq("symbol", symbol)
            .eq("config_version", CONFIG_VERSION)
            .execute()
        )
        return sum(float(r["amount"]) for r in (result.data or []))
    except Exception:
        return 0.0


def fetch_holdings(client, symbol: str) -> float:
    """Read current holdings from portfolio table."""
    try:
        result = (
            client.table("portfolio")
            .select("amount")
            .eq("symbol", symbol)
            .execute()
        )
        rows = result.data or []
        return float(rows[0]["amount"]) if rows else 0.0
    except Exception:
        return 0.0


def audit_symbol(client, symbol: str, allocation: float) -> dict:
    """Full cash audit for one symbol. Returns result dict."""
    trades = fetch_trades(client, symbol)
    reserve = fetch_reserve_total(client, symbol)

    total_buy_cost = 0.0
    total_sell_revenue = 0.0
    total_fees = 0.0
    buy_count = 0
    sell_count = 0
    holdings = 0.0

    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount") or 0)
        price = float(t.get("price") or 0)
        fee = float(t.get("fee") or 0)
        cost = float(t.get("cost") or (amount * price))

        total_fees += fee

        if side == "buy":
            total_buy_cost += cost
            holdings += amount
            buy_count += 1
        elif side == "sell":
            revenue = amount * price
            total_sell_revenue += revenue
            holdings -= amount
            sell_count += 1

    if holdings < 0:
        holdings = 0.0

    net_invested = total_buy_cost - total_sell_revenue
    available_cash = allocation - net_invested - reserve

    return {
        "symbol": symbol,
        "allocation": allocation,
        "total_buy_cost": total_buy_cost,
        "total_sell_revenue": total_sell_revenue,
        "net_invested": net_invested,
        "reserve": reserve,
        "available_cash": available_cash,
        "total_fees": total_fees,
        "holdings": holdings,
        "trade_count": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
    }


def run_audit():
    client = get_client()
    symbols = list(_DEFAULT_ALLOCATIONS.keys())

    # Try to get live allocations from Supabase
    live_allocs = fetch_capital_allocations(client)

    print()
    print("=" * 55)
    print("  BAGHOLDER CASH AUDIT")
    print("=" * 55)

    results = []
    for symbol in symbols:
        allocation = live_allocs.get(symbol, _DEFAULT_ALLOCATIONS[symbol])
        r = audit_symbol(client, symbol, allocation)
        results.append(r)

        sign = lambda v: f"+${v:.2f}" if v >= 0 else f"-${abs(v):.2f}"

        print()
        print(f"  {symbol}  (allocation: ${allocation:.2f})")
        print(f"  {'─' * 45}")
        print(f"  Trades:             {r['trade_count']} total  ({r['buy_count']} buys / {r['sell_count']} sells)")
        print(f"  Total buy cost:     ${r['total_buy_cost']:.2f}")
        print(f"  Total sell revenue: ${r['total_sell_revenue']:.2f}")
        print(f"  Total fees:         ${r['total_fees']:.4f}")
        print(f"  Net invested:       ${r['net_invested']:.2f}")
        if r["reserve"] > 0:
            print(f"  Reserve (skimmed):  ${r['reserve']:.2f}")
        print(f"  Correct cash:       ${r['available_cash']:.2f}", end="")
        if r["available_cash"] < 0:
            print("  ⚠ NEGATIVE — over-invested", end="")
        print()
        print(f"  Holdings (est):     {r['holdings']:.6f} {symbol.split('/')[0]}")

    # Portfolio summary
    print()
    print("=" * 55)
    print("  PORTFOLIO SUMMARY")
    print("=" * 55)
    print()

    total_allocation = sum(r["allocation"] for r in results)
    total_net_invested = sum(r["net_invested"] for r in results)
    total_reserve = sum(r["reserve"] for r in results)
    total_correct_cash = sum(r["available_cash"] for r in results)
    total_fees = sum(r["total_fees"] for r in results)

    print(f"  Total allocation:   ${total_allocation:.2f}")
    print(f"  Total net invested: ${total_net_invested:.2f}")
    print(f"  Total reserve:      ${total_reserve:.2f}")
    print(f"  Total correct cash: ${total_correct_cash:.2f}")
    print(f"  Total fees paid:    ${total_fees:.4f}")
    print()

    # P&L estimate: cash + holdings value (holdings value requires current prices)
    print("  Note: holdings value requires current market prices.")
    print("  Cash P&L vs starting capital:")
    cash_pnl = total_correct_cash - TOTAL_STARTING_CAPITAL
    realized_pnl_total = total_correct_cash + total_net_invested - total_allocation
    print(f"    Starting capital:  ${TOTAL_STARTING_CAPITAL:.2f}")
    print(f"    Liquid cash now:   ${total_correct_cash:.2f}")
    print(f"    Diff (cash only):  ${cash_pnl:.2f}  (excludes holdings value)")
    print()

    # Warn if any coin is over-invested
    over = [r for r in results if r["available_cash"] < 0]
    if over:
        print("  ⚠ WARNING: The following coins are OVER-INVESTED:")
        for r in over:
            print(f"    {r['symbol']}: ${r['available_cash']:.2f} available (${abs(r['available_cash']):.2f} over limit)")
        print()
        print("  These are likely the result of phantom-cash buys after bot restarts.")
        print("  Brief 20c fix prevents this from happening again.")
    else:
        print("  ✓ All coins within allocation limits.")

    print()
    print("=" * 55)
    print()


if __name__ == "__main__":
    run_audit()
