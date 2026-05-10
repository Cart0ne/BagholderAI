"""
S70 — Reconciliation Binance ↔ DB trades.

For each active symbol (GRID_INSTANCES), compares the bot's DB trades
(config_version='v3', managed_by='grid') against Binance fetch_my_trades.

Detects:
  - DRIFT                 — matched orders with qty/price/fee outside tolerance
  - DRIFT_BINANCE_ORPHAN  — order on Binance not in DB (serious: bot executed
                            but failed to write to DB)
  - WARN_BINANCE_EMPTY    — Binance returned 0 trades (probable testnet reset,
                            informational, NOT a drift)
  - OK                    — everything matches within tolerance

DB-only orders (in DB but not on Binance) are reported as informational
"pre-reset legacy", NOT as drift. Expected after a Binance testnet reset.

Match strategy:
  1. exchange_order_id (DB) == order (Binance)  — preferred
  2. fallback: same side + ts ±1s + qty within ±1% (covers S67 debt where
     a few sells have exchange_order_id=NULL)

Tolerances (testnet — see top of file):
  qty   ±0.00001 absolute
  price ±0.5%    relative  (testnet book is thin; tighten to 0.1% for mainnet)
  fee   ±$0.01   absolute  (USDT-equivalent)

Usage (Mac Mini):
    cd /Volumes/Archivio/bagholderai
    source venv/bin/activate
    python3.13 scripts/reconcile_binance.py            # dry-run, stdout only
    python3.13 scripts/reconcile_binance.py --write    # also INSERT into reconciliation_runs
    python3.13 scripts/reconcile_binance.py --symbols BTC/USDT SOL/USDT

Exit codes:
    0 — all OK or only WARN/legacy
    1 — at least one DRIFT or DRIFT_BINANCE_ORPHAN
    2 — fatal error (bad mode, exchange unreachable, etc.)
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.exchange import create_exchange
from config.settings import GRID_INSTANCES, TradingMode, ExchangeConfig
from db.client import get_client


# === Tolerances (testnet) ===
QTY_TOL_ABS = 1e-5          # ±0.00001 (BTC sub-satoshi level)
PRICE_TOL_PCT = 0.5 / 100   # ±0.5% — testnet book sottile
FEE_TOL_ABS = 0.01          # ±$0.01 (USDT)

# How many trades to look back
DB_LOOKBACK = 1000
BINANCE_LIMIT = 1000

# Fallback match window (ms)
TS_FALLBACK_MS = 1000
QTY_FALLBACK_TOL_PCT = 0.01  # ±1%


# ============================================================
# Binance side
# ============================================================

def aggregate_binance_fills(fills):
    """Group ccxt fills by orderId → 1 logical order per group.

    Returns a list of dicts sorted by ts DESC. fee_usdt is computed by
    converting fee.cost to USDT-equivalent (base coin × fill price for
    BUY fees; SELL fees already in USDT). Mirrors the canonical fee
    handling done by exchange_orders.py post-S67.
    """
    by_order = defaultdict(list)
    for f in fills:
        oid = f.get("order")
        if oid is None:
            continue
        by_order[str(oid)].append(f)

    orders = []
    for order_id, group in by_order.items():
        total_qty = sum(float(g["amount"]) for g in group)
        total_cost = sum(float(g["cost"]) for g in group)
        avg_price = total_cost / total_qty if total_qty > 0 else 0.0

        fee_usdt = 0.0
        for g in group:
            fee = g.get("fee") or {}
            fcost = float(fee.get("cost", 0) or 0)
            fcurr = (fee.get("currency") or "").upper()
            if fcurr in ("USDT", "", None):
                fee_usdt += fcost
            else:
                # Base coin (e.g. BTC for a BUY) → convert at fill price
                fee_usdt += fcost * float(g["price"])

        last_ts = max(int(g["timestamp"]) for g in group)
        side = group[0]["side"].lower()

        orders.append({
            "order_id": order_id,
            "side": side,
            "qty": total_qty,
            "price": avg_price,
            "cost": total_cost,
            "fee_usdt": fee_usdt,
            "ts_ms": last_ts,
        })

    orders.sort(key=lambda o: o["ts_ms"], reverse=True)
    return orders


# ============================================================
# DB side
# ============================================================

def fetch_db_trades(client, symbol, limit=DB_LOOKBACK):
    """Recent v3 grid trades for a symbol, sorted DESC by created_at."""
    res = (
        client.table("trades")
        .select("id,created_at,symbol,side,amount,price,cost,fee,exchange_order_id,managed_by,config_version")
        .eq("symbol", symbol)
        .eq("config_version", "v3")
        .eq("managed_by", "grid")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    out = []
    for r in rows:
        ts = r["created_at"]
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ts_ms = int(dt.astimezone(timezone.utc).timestamp() * 1000)
        out.append({
            "db_id": r["id"],
            "side": r["side"],
            "qty": float(r["amount"]),
            "price": float(r["price"]),
            "cost": float(r.get("cost") or 0),
            "fee_usdt": float(r.get("fee") or 0),
            "exchange_order_id": r.get("exchange_order_id"),
            "ts_ms": ts_ms,
        })
    return out


# ============================================================
# Matching
# ============================================================

def match_orders(db_orders, binance_orders):
    """Match DB rows to Binance orders.

    Returns (matched, unmatched_db, unmatched_binance):
      matched              — list of (db_row, binance_order) pairs
      unmatched_db         — DB rows with no Binance match (likely pre-reset)
      unmatched_binance    — Binance orders with no DB match (BAD: bot executed
                             on exchange but failed to log to DB)
    """
    bn_by_id = {o["order_id"]: o for o in binance_orders}
    bn_used = set()

    matched = []
    unmatched_db = []

    for d in db_orders:
        eid = d["exchange_order_id"]
        if eid is not None:
            key = str(eid)
            if key in bn_by_id and key not in bn_used:
                matched.append((d, bn_by_id[key]))
                bn_used.add(key)
                continue

        # Fallback: ts ±1s + side + qty ±1%
        cand = None
        for b in binance_orders:
            if b["order_id"] in bn_used:
                continue
            if b["side"] != d["side"]:
                continue
            if abs(b["ts_ms"] - d["ts_ms"]) > TS_FALLBACK_MS:
                continue
            if d["qty"] > 0 and abs(b["qty"] - d["qty"]) / d["qty"] > QTY_FALLBACK_TOL_PCT:
                continue
            cand = b
            break

        if cand is not None:
            matched.append((d, cand))
            bn_used.add(cand["order_id"])
        else:
            unmatched_db.append(d)

    unmatched_binance = [b for b in binance_orders if b["order_id"] not in bn_used]
    return matched, unmatched_db, unmatched_binance


def check_drift(db, bn):
    """Return list of drift findings for a matched pair (empty = OK)."""
    findings = []

    delta_qty = abs(db["qty"] - bn["qty"])
    if delta_qty > QTY_TOL_ABS:
        findings.append({
            "field": "qty",
            "db_val": db["qty"],
            "binance_val": bn["qty"],
            "delta_abs": delta_qty,
            "tol_abs": QTY_TOL_ABS,
        })

    if db["price"] > 0:
        delta_price_pct = abs(db["price"] - bn["price"]) / db["price"]
        if delta_price_pct > PRICE_TOL_PCT:
            findings.append({
                "field": "price",
                "db_val": db["price"],
                "binance_val": bn["price"],
                "delta_pct": round(delta_price_pct * 100, 4),
                "tol_pct": round(PRICE_TOL_PCT * 100, 4),
            })

    delta_fee = abs(db["fee_usdt"] - bn["fee_usdt"])
    if delta_fee > FEE_TOL_ABS:
        findings.append({
            "field": "fee_usdt",
            "db_val": db["fee_usdt"],
            "binance_val": bn["fee_usdt"],
            "delta_abs": round(delta_fee, 4),
            "tol_abs": FEE_TOL_ABS,
        })

    return findings


# ============================================================
# Per-symbol orchestration
# ============================================================

def reconcile_symbol(exchange, client, symbol):
    print(f"\n=== {symbol} ===")

    fills = exchange.fetch_my_trades(symbol, limit=BINANCE_LIMIT)
    bn_orders = aggregate_binance_fills(fills)
    db_orders = fetch_db_trades(client, symbol)

    print(f"  Binance: {len(fills)} fills → {len(bn_orders)} orders")
    print(f"  DB:      {len(db_orders)} trades (v3, managed_by=grid)")

    if len(bn_orders) == 0:
        status = "WARN_BINANCE_EMPTY"
        print(f"  → {status}: probable testnet reset, awaiting new data")
        return {
            "symbol": symbol,
            "status": status,
            "binance_count": 0,
            "db_count": len(db_orders),
            "matched_count": 0,
            "unmatched_db_count": len(db_orders),
            "unmatched_binance_count": 0,
            "drift_count": 0,
            "drift_details": None,
            "notes": "Binance returned 0 trades; DB unchanged.",
        }

    matched, un_db, un_bn = match_orders(db_orders, bn_orders)

    drift_rows = []
    for d, b in matched:
        f = check_drift(d, b)
        if f:
            drift_rows.append({
                "db_id": d["db_id"],
                "binance_order": b["order_id"],
                "side": d["side"],
                "fields": f,
            })

    if un_bn:
        status = "DRIFT_BINANCE_ORPHAN"
    elif drift_rows:
        status = "DRIFT"
    else:
        status = "OK"

    print(f"  matched={len(matched)} drift={len(drift_rows)} db_only={len(un_db)} binance_only={len(un_bn)} → {status}")

    for dr in drift_rows[:5]:
        print(f"    DRIFT  db={str(dr['db_id'])[:8]} bn={dr['binance_order']} {dr['side']}")
        for f in dr["fields"]:
            print(f"      {f}")
    if len(drift_rows) > 5:
        print(f"    ... +{len(drift_rows) - 5} more drifts")

    for b in un_bn[:5]:
        print(f"    BINANCE_ONLY order={b['order_id']} side={b['side']} qty={b['qty']} ts_ms={b['ts_ms']}")
    if len(un_bn) > 5:
        print(f"    ... +{len(un_bn) - 5} more binance_orphans")

    if un_db:
        print(f"  (DB-only / pre-reset legacy: {len(un_db)} rows — informational, not drift)")

    drift_details = None
    if drift_rows or un_bn:
        drift_details = {
            "drift": drift_rows,
            "binance_orphans": [
                {"order_id": b["order_id"], "side": b["side"],
                 "qty": b["qty"], "price": b["price"], "ts_ms": b["ts_ms"]}
                for b in un_bn
            ],
            "db_only_count": len(un_db),
        }

    return {
        "symbol": symbol,
        "status": status,
        "binance_count": len(bn_orders),
        "db_count": len(db_orders),
        "matched_count": len(matched),
        "unmatched_db_count": len(un_db),
        "unmatched_binance_count": len(un_bn),
        "drift_count": len(drift_rows),
        "drift_details": drift_details,
        "notes": None,
    }


# ============================================================
# DB write
# ============================================================

def write_results(client, results):
    rows = [{
        "symbol": r["symbol"],
        "status": r["status"],
        "binance_count": r["binance_count"],
        "db_count": r["db_count"],
        "matched_count": r["matched_count"],
        "unmatched_db_count": r["unmatched_db_count"],
        "unmatched_binance_count": r["unmatched_binance_count"],
        "drift_count": r["drift_count"],
        "drift_details": r["drift_details"],
        "notes": r["notes"],
    } for r in results]

    if not rows:
        return
    res = client.table("reconciliation_runs").insert(rows).execute()
    print(f"\n✓ wrote {len(res.data or [])} rows to reconciliation_runs")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Reconcile bot DB trades vs Binance fetch_my_trades")
    parser.add_argument("--write", action="store_true",
                        help="Insert results into reconciliation_runs (default: stdout-only)")
    parser.add_argument("--symbols", nargs="*",
                        help="Override symbols (default: all from GRID_INSTANCES)")
    args = parser.parse_args()

    if not TradingMode.is_live():
        print("ERROR: TRADING_MODE must be 'live' (TESTNET=true is fine).", file=sys.stderr)
        sys.exit(2)

    print(f"Mode: LIVE {'TESTNET' if ExchangeConfig.TESTNET else 'MAINNET'}")
    print(f"Tolerances: qty ±{QTY_TOL_ABS}, price ±{PRICE_TOL_PCT * 100}%, fee ±${FEE_TOL_ABS}")

    try:
        exchange = create_exchange()
    except Exception as e:
        print(f"ERROR: failed to create exchange: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        client = get_client()
    except Exception as e:
        print(f"ERROR: failed to create Supabase client: {e}", file=sys.stderr)
        sys.exit(2)

    symbols = args.symbols or [g.symbol for g in GRID_INSTANCES]

    results = []
    for sym in symbols:
        try:
            r = reconcile_symbol(exchange, client, sym)
            results.append(r)
        except Exception as e:
            print(f"  ! ERROR on {sym}: {e}", file=sys.stderr)

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  {r['symbol']:12s}  {r['status']:24s}  "
              f"matched={r['matched_count']:3d}  drift={r['drift_count']:2d}  "
              f"binance_orphan={r['unmatched_binance_count']:2d}  "
              f"db_legacy={r['unmatched_db_count']:3d}")

    if args.write and results:
        write_results(client, results)
    elif results:
        print("\n(dry-run: nothing written. Pass --write to persist into reconciliation_runs.)")

    has_drift = any(r["status"] in ("DRIFT", "DRIFT_BINANCE_ORPHAN") for r in results)
    sys.exit(1 if has_drift else 0)


if __name__ == "__main__":
    main()
