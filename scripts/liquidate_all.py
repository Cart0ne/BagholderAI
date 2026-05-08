"""
S66 Operation Clean Slate — Step 0b: liquidate all open positions.

Purpose:
    Close every open lot via direct DB writes (no orchestrator, no bot).
    Replicates the bot's _execute_percentage_sell formula faithfully so
    the post-liquidation dataset will reveal accounting bugs in Step 0d.

What it writes:
    - One SELL row per open position (table `trades`)
    - One skim row per profitable sell with skim_pct > 0 (table `reserve_ledger`)
    - One final snapshot per liquidated symbol (table `bot_state_snapshots`)
    - One summary event (table `bot_events_log`)

What it does NOT write:
    - daily_pnl: stale by design (today is not a trading day)
    - Sentinel/Sherpa tables: out of scope (vincolo brief 66a)

Run:
    python -m scripts.liquidate_all              # default: dry-run, prints plan
    python -m scripts.liquidate_all --execute    # actually liquidates

Pre-req: orchestrator stopped on the runtime host.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from bot.exchange import create_exchange, fetch_ticker
from db.client import get_client

# Faithful replication of GridBot.FEE_RATE (sell_pipeline computes
# fee = revenue * FEE_RATE; paper-mode realized_pnl excludes fees per 52a).
FEE_RATE = 0.00075

LIQUIDATION_REASON = "liquidate_all_s66 (Operation Clean Slate Step 0b)"

logger = logging.getLogger("liquidate_all")
logging.basicConfig(level=logging.INFO, format="%(message)s")


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------

def find_open_positions(client) -> list[dict]:
    """
    Find symbols with non-zero net holdings using the same definition
    the bot uses (config_version='v3', sum buys minus sum sells).
    Returns: [{symbol, net_holdings, n_buys, n_sells, last_trade_at}]
    """
    # Cap-aware fetch via Range header if needed; trades table is ~1185 rows
    # which is above the default Supabase REST cap of 1000. We page in chunks.
    all_trades: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("trades")
            .select("symbol,side,amount,created_at")
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

    # Aggregate per symbol
    agg: dict[str, dict] = {}
    for t in all_trades:
        sym = t["symbol"]
        side = t["side"]
        amount = float(t.get("amount") or 0)
        if sym not in agg:
            agg[sym] = {"symbol": sym, "holdings": 0.0,
                        "n_buys": 0, "n_sells": 0, "last_trade_at": None}
        if side == "buy":
            agg[sym]["holdings"] += amount
            agg[sym]["n_buys"] += 1
        elif side == "sell":
            agg[sym]["holdings"] -= amount
            agg[sym]["n_sells"] += 1
        agg[sym]["last_trade_at"] = t.get("created_at")

    return [
        v for v in agg.values()
        if v["holdings"] > 1e-8
    ]


# ----------------------------------------------------------------------
# FIFO replay (replicates state_manager.init_percentage_state_from_db)
# ----------------------------------------------------------------------

def replay_fifo(client, symbol: str) -> dict:
    """
    Replay all v3 trades for a symbol chronologically and return:
      - open_positions: list of {amount, price} lots remaining (FIFO order)
      - total_invested: sum of buy costs
      - total_received: sum of sell revenues
      - total_fees: sum of buy+sell fees from DB rows
    """
    # Page through all trades for this symbol
    all_trades: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("trades")
            .select("side,amount,price,cost,fee,created_at")
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

    open_positions: list[dict] = []
    total_invested = 0.0
    total_received = 0.0
    total_fees = 0.0

    for t in all_trades:
        side = t.get("side")
        amount = float(t.get("amount") or 0)
        price = float(t.get("price") or 0)
        cost = float(t.get("cost") or (amount * price))
        fee = float(t.get("fee") or 0)
        total_fees += fee

        if side == "buy":
            total_invested += cost
            open_positions.append({"amount": amount, "price": price})
        elif side == "sell":
            total_received += amount * price
            remaining = amount
            while remaining > 1e-12 and open_positions:
                oldest = open_positions[0]
                if oldest["amount"] <= remaining + 1e-12:
                    remaining -= oldest["amount"]
                    open_positions.pop(0)
                else:
                    oldest["amount"] -= remaining
                    remaining = 0

    return {
        "open_positions": open_positions,
        "total_invested": total_invested,
        "total_received": total_received,
        "total_fees": total_fees,
    }


# ----------------------------------------------------------------------
# Bot config + reserves
# ----------------------------------------------------------------------

def get_bot_configs_for_symbol(client, symbol: str) -> list[dict]:
    """Return all bot_config rows for a symbol (Grid + TF can both have one)."""
    result = (
        client.table("bot_config")
        .select("*")
        .eq("symbol", symbol)
        .execute()
    )
    return result.data or []


def get_reserve_total(client, symbol: str) -> float:
    """Sum of reserve_ledger.amount for a symbol (config_version v3)."""
    result = (
        client.table("reserve_ledger")
        .select("amount")
        .eq("symbol", symbol)
        .eq("config_version", "v3")
        .execute()
    )
    return sum(float(r["amount"] or 0) for r in (result.data or []))


def get_realized_cumulative(client, symbol: str) -> float:
    """Sum of realized_pnl across all v3 trades for a symbol (pre-liquidation)."""
    # Page through, since trades table can exceed cap
    total = 0.0
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("trades")
            .select("realized_pnl")
            .eq("symbol", symbol)
            .eq("config_version", "v3")
            .eq("side", "sell")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        chunk = result.data or []
        for r in chunk:
            total += float(r.get("realized_pnl") or 0)
        if len(chunk) < page_size:
            break
        offset += page_size
    return total


# ----------------------------------------------------------------------
# Liquidate one symbol
# ----------------------------------------------------------------------

def liquidate_one(client, exchange, symbol: str, dry_run: bool) -> dict | None:
    """Liquidate all open lots for one symbol. Returns result dict or None."""
    state = replay_fifo(client, symbol)
    if not state["open_positions"]:
        logger.info(f"[{symbol}] no open lots after FIFO replay, skipping")
        return None

    # Sum the queue (= bot's holdings at this moment)
    holdings = sum(lot["amount"] for lot in state["open_positions"])
    queue_depth = len(state["open_positions"])

    # Fetch current spot price (live Binance public API, no auth)
    ticker = fetch_ticker(exchange, symbol)
    price = float(ticker["last"])

    # Faithful replication of sell_pipeline._execute_percentage_sell:
    revenue = holdings * price
    fee = revenue * FEE_RATE

    # Walk FIFO queue (53a) and sum cost_basis
    cost_basis = 0.0
    remaining = holdings
    for lot in state["open_positions"]:
        if lot["amount"] <= remaining + 1e-9:
            cost_basis += lot["amount"] * lot["price"]
            remaining -= lot["amount"]
        else:
            cost_basis += remaining * lot["price"]
            remaining = 0
            break

    # 52a paper-mode: realized_pnl excludes fees
    realized_pnl = revenue - cost_basis

    # Resolve managed_by + skim_pct from active bot_config (prefer is_active=true)
    cfgs = get_bot_configs_for_symbol(client, symbol)
    active_cfg = next((c for c in cfgs if c.get("is_active")), None) or (cfgs[0] if cfgs else {})
    managed_by = active_cfg.get("managed_by", "manual")
    skim_pct = float(active_cfg.get("skim_pct") or 0)
    capital_allocation = float(active_cfg.get("capital_allocation") or 0)

    # Brain mapping
    brain = "trend" if managed_by in ("trend_follower", "tf_grid") else "grid"

    trade_row = {
        "symbol": symbol,
        "side": "sell",
        "amount": float(holdings),
        "price": float(price),
        "cost": float(revenue),
        "fee": float(fee),
        "strategy": "A",  # all v3 bots run Strategy A
        "brain": brain,
        "reason": LIQUIDATION_REASON,
        "mode": "paper",
        "realized_pnl": float(realized_pnl),
        "config_version": "v3",
        "managed_by": managed_by,
    }

    logger.info(
        f"[{symbol}] holdings={holdings:.8f} @ ${price:.6f} "
        f"(queue depth: {queue_depth}, brain={brain}, managed_by={managed_by})"
    )
    logger.info(
        f"  revenue=${revenue:.4f}  cost_basis=${cost_basis:.4f}  "
        f"realized=${realized_pnl:+.4f}  fee=${fee:.4f}"
    )

    trade_id: str | None = None
    if not dry_run:
        result = client.table("trades").insert(trade_row).execute()
        if result.data:
            trade_id = result.data[0].get("id")
            logger.info(f"  → INSERTED trade {trade_id}")
        else:
            logger.error(f"  ✗ INSERT failed for {symbol}")
            return None
    else:
        logger.info(f"  → [dry-run] would INSERT sell trade")

    # Skim — replicates sell_pipeline lines 727-743
    skim_amount = 0.0
    if skim_pct > 0 and realized_pnl > 0:
        skim_amount = realized_pnl * (skim_pct / 100.0)
        if not dry_run:
            client.table("reserve_ledger").insert({
                "symbol": symbol,
                "amount": float(skim_amount),
                "trade_id": trade_id,
                "config_version": "v3",
                "managed_by": managed_by,
            }).execute()
            logger.info(f"  → SKIM ${skim_amount:.4f} ({skim_pct}% of realized)")
        else:
            logger.info(f"  → [dry-run] would SKIM ${skim_amount:.4f} ({skim_pct}% of realized)")

    return {
        "symbol": symbol,
        "amount": holdings,
        "price": price,
        "revenue": revenue,
        "cost_basis": cost_basis,
        "realized_pnl": realized_pnl,
        "fee": fee,
        "skim_amount": skim_amount,
        "trade_id": trade_id,
        "managed_by": managed_by,
        "capital_allocation": capital_allocation,
        "total_invested_pre": state["total_invested"],
        "total_received_pre": state["total_received"],
        "queue_depth": queue_depth,
    }


# ----------------------------------------------------------------------
# Final snapshots + summary event
# ----------------------------------------------------------------------

def write_final_snapshot(client, r: dict, dry_run: bool):
    """One final snapshot per symbol with holdings=0."""
    # Cash post-liquidation, replicating GridBot._available_cash:
    #   cash = capital - total_invested + total_received - reserve
    total_received_post = r["total_received_pre"] + r["revenue"]
    reserve = get_reserve_total(client, r["symbol"])
    cash_available = max(
        0.0,
        r["capital_allocation"] - r["total_invested_pre"] + total_received_post - reserve,
    )

    # Cumulative realized P&L now includes the liquidation sell
    realized_cumulative = get_realized_cumulative(client, r["symbol"])

    snapshot = {
        "symbol": r["symbol"],
        "managed_by": r["managed_by"],
        "holdings": 0.0,
        "avg_buy_price": 0.0,
        "cash_available": float(cash_available),
        "unrealized_pnl": 0.0,
        "realized_pnl_cumulative": float(realized_cumulative),
        "open_lots_count": 0,
        "stop_loss_active": False,
        "stop_buy_active": False,
        "last_trade_at": datetime.now(timezone.utc).isoformat(),
    }

    if not dry_run:
        client.table("bot_state_snapshots").insert(snapshot).execute()
        logger.info(
            f"  → snapshot [{r['symbol']}] cash_available=${cash_available:.4f} "
            f"realized_cum=${realized_cumulative:.4f}"
        )
    else:
        logger.info(
            f"  → [dry-run] would write snapshot [{r['symbol']}] "
            f"cash_available=${cash_available:.4f} realized_cum=${realized_cumulative:.4f}"
        )


def write_summary_event(client, results: list[dict], dry_run: bool):
    """One summary event in bot_events_log."""
    n = len(results)
    total_revenue = sum(r["revenue"] for r in results)
    total_realized = sum(r["realized_pnl"] for r in results)
    total_fee = sum(r["fee"] for r in results)
    total_skim = sum(r["skim_amount"] for r in results)

    details = {
        "n_positions": n,
        "total_revenue": round(total_revenue, 4),
        "total_realized_pnl": round(total_realized, 4),
        "total_fee": round(total_fee, 4),
        "total_skim": round(total_skim, 4),
        "symbols": [r["symbol"] for r in results],
        "by_symbol": [
            {
                "symbol": r["symbol"],
                "managed_by": r["managed_by"],
                "amount": float(r["amount"]),
                "price": float(r["price"]),
                "realized_pnl": round(r["realized_pnl"], 4),
                "queue_depth": r["queue_depth"],
            }
            for r in results
        ],
    }

    # `lifecycle` is the right category for "end of paper-trading era".
    # The whitelist (migration 57a) is: lifecycle, trade, safety, tf, config,
    # error, integrity, trade_audit. "liquidation" was rejected.
    event_row = {
        "severity": "info",
        "category": "lifecycle",
        "symbol": None,
        "event": "liquidate_all_completed",
        "message": (
            f"S66 Operation Clean Slate — liquidated {n} open positions "
            f"(realized total ${total_realized:+.4f})"
        ),
        "details": details,
    }

    if not dry_run:
        client.table("bot_events_log").insert(event_row).execute()
        logger.info(f"  → summary event written")
    else:
        logger.info(f"  → [dry-run] would write summary event")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="S66 Operation Clean Slate — liquidate all")
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to the DB. Default is dry-run (no writes).",
    )
    args = ap.parse_args()
    dry_run = not args.execute

    banner = "DRY-RUN MODE (no DB writes)" if dry_run else "EXECUTE MODE — WRITING TO DB"
    logger.info("=" * 70)
    logger.info(f"  S66 Operation Clean Slate — Step 0b — {banner}")
    logger.info("=" * 70)

    client = get_client()
    exchange = create_exchange()

    open_positions = find_open_positions(client)
    if not open_positions:
        logger.info("No open positions found. Nothing to do.")
        return 0
    logger.info(f"Found {len(open_positions)} open position(s):")
    for p in sorted(open_positions, key=lambda x: x["symbol"]):
        logger.info(
            f"  {p['symbol']:14s}  holdings={p['holdings']:>20.8f}  "
            f"buys={p['n_buys']}  sells={p['n_sells']}"
        )
    logger.info("")

    # Liquidate each
    results: list[dict] = []
    for p in sorted(open_positions, key=lambda x: x["symbol"]):
        res = liquidate_one(client, exchange, p["symbol"], dry_run)
        if res:
            results.append(res)
        logger.info("")

    if not results:
        logger.info("No symbols actually liquidated.")
        return 0

    # Final snapshots
    logger.info("-" * 70)
    logger.info("FINAL SNAPSHOTS")
    logger.info("-" * 70)
    for r in results:
        write_final_snapshot(client, r, dry_run)
    logger.info("")

    # Summary event
    logger.info("-" * 70)
    logger.info("SUMMARY EVENT")
    logger.info("-" * 70)
    write_summary_event(client, results, dry_run)
    logger.info("")

    # Final report
    total_realized = sum(r["realized_pnl"] for r in results)
    total_revenue = sum(r["revenue"] for r in results)
    total_skim = sum(r["skim_amount"] for r in results)
    logger.info("=" * 70)
    logger.info("LIQUIDATION REPORT")
    logger.info("=" * 70)
    logger.info(f"Symbols liquidated:  {len(results)}")
    logger.info(f"Total revenue:       ${total_revenue:>+12.4f}")
    logger.info(f"Total realized P&L:  ${total_realized:>+12.4f}")
    logger.info(f"Total skim:          ${total_skim:>+12.4f}")
    logger.info("")
    for r in sorted(results, key=lambda x: x["symbol"]):
        logger.info(
            f"  {r['symbol']:14s}  "
            f"amount={r['amount']:>20.8f}  "
            f"price=${r['price']:>12.6f}  "
            f"realized=${r['realized_pnl']:>+11.4f}"
        )
    logger.info("=" * 70)

    if dry_run:
        logger.info("\nThis was a DRY RUN. To actually execute, run with --execute.")
    else:
        logger.info("\nLiquidation complete. Proceed to Step 0c (snapshot) + 0d (verify formulas).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
