"""
S66 Operation Clean Slate — Step 0d: verify accounting formulas.

Now that all positions are closed (Unrealized = $0), the accounting
identity simplifies to:

    SUM(realized_pnl) == cash_post − budget        (per bot, per cluster)

If it doesn't close, the bug is in the bot's per-sell formula or in the
queue state it used at sell time.

This script does TWO checks:

(1) Per-trade verification:
    For every SELL in trades, we replay the symbol's history using strict
    FIFO (oldest lot first), compute the expected cost_basis at that
    point in time, derive expected_realized = revenue − expected_cost_basis,
    and compare with the DB realized_pnl. Any mismatch is a bug in the
    bot's runtime queue (60c desync, dust pop, etc.) — the formula itself
    is fine, but the state it used was wrong.

(2) Global identity:
    SUM(realized_pnl across all v3 sells) vs (sum of revenue − sum of
    cost_basis_strict_FIFO). The delta is the cumulative bias the bot
    introduced over its lifetime.

Output: prints a structured report to stdout. Pipe to a file to capture.

Run:
    python -m scripts.verify_formulas_s66 > /tmp/verify.log
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from db.client import get_client

logger = logging.getLogger("verify_formulas_s66")
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Tolerance for matching realized_pnl (1 cent — anything bigger is suspect)
TOL = 0.01


def fetch_all_trades_for_symbol(client, symbol: str) -> list[dict]:
    """Fetch all v3 trades for a symbol, paginated, chronological."""
    all_trades: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("trades")
            .select("id,side,amount,price,cost,fee,realized_pnl,created_at,reason,managed_by")
            .eq("symbol", symbol)
            .eq("config_version", "v3")
            .order("created_at", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        chunk = result.data or []
        all_trades.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return all_trades


def list_v3_symbols(client) -> list[str]:
    """All symbols with at least one v3 trade."""
    seen: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("trades")
            .select("symbol")
            .eq("config_version", "v3")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        chunk = result.data or []
        for r in chunk:
            seen.add(r["symbol"])
        if len(chunk) < page_size:
            break
        offset += page_size
    return sorted(seen)


def verify_symbol(client, symbol: str) -> dict:
    """
    Replay strict FIFO and compare expected_realized_pnl with DB.
    Returns aggregated metrics + mismatches.
    """
    trades = fetch_all_trades_for_symbol(client, symbol)
    open_positions: list[dict] = []  # FIFO queue: [{amount, price}]
    total_db_realized = 0.0
    total_expected_realized = 0.0
    n_sells = 0
    mismatches: list[dict] = []

    for t in trades:
        side = t["side"]
        amount = float(t["amount"] or 0)
        price = float(t["price"] or 0)

        if side == "buy":
            open_positions.append({"amount": amount, "price": price})
            continue

        if side != "sell":
            continue

        n_sells += 1
        # Compute expected_cost_basis with strict FIFO walk
        cost_basis = 0.0
        remaining = amount
        consumed_idx = 0
        # Make a snapshot of queue state *before* this sell (for diagnostics)
        queue_before = [(lot["amount"], lot["price"]) for lot in open_positions]
        while remaining > 1e-12 and consumed_idx < len(open_positions):
            lot = open_positions[consumed_idx]
            if lot["amount"] <= remaining + 1e-12:
                cost_basis += lot["amount"] * lot["price"]
                remaining -= lot["amount"]
                consumed_idx += 1
            else:
                cost_basis += remaining * lot["price"]
                remaining = 0
                break

        revenue = amount * price
        expected_realized = revenue - cost_basis

        # If queue was insufficient (sell exceeds queue), the strict-FIFO
        # ricalcolo is incomplete — flag it
        insufficient_queue = remaining > 1e-9

        db_realized = float(t["realized_pnl"] or 0)
        total_db_realized += db_realized
        total_expected_realized += expected_realized

        delta = db_realized - expected_realized
        if abs(delta) > TOL or insufficient_queue:
            mismatches.append({
                "trade_id": t["id"],
                "created_at": t["created_at"],
                "amount": amount,
                "price": price,
                "revenue": revenue,
                "db_realized": db_realized,
                "expected_realized": expected_realized,
                "delta": delta,
                "insufficient_queue": insufficient_queue,
                "queue_depth_before": len(queue_before),
                "queue_unsold_amount": remaining if insufficient_queue else 0,
                "reason": t.get("reason", "")[:60],
            })

        # Now actually consume the queue (mutate)
        remaining = amount
        while remaining > 1e-12 and open_positions:
            lot = open_positions[0]
            if lot["amount"] <= remaining + 1e-12:
                remaining -= lot["amount"]
                open_positions.pop(0)
            else:
                lot["amount"] -= remaining
                remaining = 0
                break

    final_holdings = sum(lot["amount"] for lot in open_positions)
    return {
        "symbol": symbol,
        "n_sells": n_sells,
        "n_mismatches": len(mismatches),
        "total_db_realized": total_db_realized,
        "total_expected_realized": total_expected_realized,
        "bias": total_db_realized - total_expected_realized,
        "final_holdings": final_holdings,
        "queue_remainder_lots": len(open_positions),
        "mismatches": mismatches,
    }


def main() -> int:
    client = get_client()

    print("=" * 76)
    print("  S66 — Step 0d — Formula Verification (strict-FIFO vs DB realized_pnl)")
    print(f"  Run: {datetime.utcnow().isoformat()}Z")
    print("=" * 76)

    symbols = list_v3_symbols(client)
    print(f"\nFound {len(symbols)} symbols with v3 trades.\n")

    per_symbol_results = []
    for sym in symbols:
        res = verify_symbol(client, sym)
        per_symbol_results.append(res)

    # Per-symbol summary
    print(f"{'Symbol':<14}  {'n_sells':>7}  {'n_mismatch':>10}  "
          f"{'DB_realized':>13}  {'expected':>13}  {'bias':>11}  {'fin_holdings':>14}")
    print("-" * 76)
    for r in per_symbol_results:
        print(f"{r['symbol']:<14}  {r['n_sells']:>7}  {r['n_mismatches']:>10}  "
              f"{r['total_db_realized']:>13.4f}  {r['total_expected_realized']:>13.4f}  "
              f"{r['bias']:>+11.4f}  {r['final_holdings']:>14.6f}")

    # Global aggregate
    g_db_realized = sum(r['total_db_realized'] for r in per_symbol_results)
    g_expected_realized = sum(r['total_expected_realized'] for r in per_symbol_results)
    g_bias = g_db_realized - g_expected_realized
    g_n_sells = sum(r['n_sells'] for r in per_symbol_results)
    g_n_mismatches = sum(r['n_mismatches'] for r in per_symbol_results)
    print("-" * 76)
    print(f"{'TOTAL':<14}  {g_n_sells:>7}  {g_n_mismatches:>10}  "
          f"{g_db_realized:>13.4f}  {g_expected_realized:>13.4f}  "
          f"{g_bias:>+11.4f}")

    # Per-symbol mismatch detail (for symbols with at least one)
    print("\n" + "=" * 76)
    print("  MISMATCH DETAIL (delta > $0.01 or queue insufficient)")
    print("=" * 76)
    for r in per_symbol_results:
        if not r['mismatches']:
            continue
        print(f"\n[{r['symbol']}] — {r['n_mismatches']} mismatch(es)")
        # Show worst 5 by absolute delta
        worst = sorted(r['mismatches'], key=lambda m: abs(m['delta']), reverse=True)[:5]
        for m in worst:
            flag = " ⚠ INSUFFICIENT_QUEUE" if m['insufficient_queue'] else ""
            print(f"  {m['created_at'][:19]}  amt={m['amount']:.6f}  "
                  f"px={m['price']:.6f}  db={m['db_realized']:+.4f}  "
                  f"exp={m['expected_realized']:+.4f}  Δ={m['delta']:+.4f}"
                  f"{flag}")
            print(f"    reason: {m['reason']}")
        if len(r['mismatches']) > 5:
            print(f"  ... and {len(r['mismatches']) - 5} more")

    # Final summary
    print("\n" + "=" * 76)
    print("  GLOBAL ACCOUNTING IDENTITY")
    print("=" * 76)
    print(f"DB realized total:       ${g_db_realized:>12.4f}")
    print(f"Expected (strict-FIFO):  ${g_expected_realized:>12.4f}")
    print(f"Cumulative bias:         ${g_bias:>+12.4f}")
    print(f"  (positive bias = bot OVERSTATED realized P&L vs strict-FIFO replay)")
    print(f"  (negative bias = bot UNDERSTATED)")
    print(f"\nSells with mismatch > $0.01: {g_n_mismatches} / {g_n_sells} "
          f"({100*g_n_mismatches/g_n_sells:.1f}%)" if g_n_sells else "")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
