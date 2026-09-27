"""
R.1 (S129, 2026-09-27) — Reconciliation Kraken ↔ DB for the real-money grids.

Three checks per symbol (BTC/USD, SOL/USD), all cycles (kraken_test + kraken_2b):

  1. Order by order — every DB trade must match its Kraken order
     (trades.exchange_order_id == Kraken ordertxid; fills of one order are
     summed). Real-money tolerances: qty ±1e-8, price ±0.1%, fee/cost ±$0.01.
  2. Orphans — Kraken order missing from DB (bot executed, DB write lost:
     the Supabase blocks of 17-18 Sep) and DB trade missing on Kraken.
  3. Balance — coin the DB believes it holds (Σbuy − Σsell) vs the Kraken
     balance. A small SOL surplus is staking rewards (OK with a note).

USD cash is NOT reconciled yet (shared by both grids + unallocated funds;
needs the deposits ledger) — declared gap, next phase.

Unlike reconcile_binance.py there is no fuzzy fallback match and no "DB-only
= pre-reset legacy" pass: on real money every DB row carries its Kraken order
id, and a DB row with no Kraken order is an alarm, not history.

Read-only: 1 public + ~3 private Kraken calls (TradesHistory pages + Balance),
same API key as the grids (0 "Invalid nonce" in 2 months of two grids
sharing it — revisit with a dedicated read-only key if one ever appears).

Usage (Mac Mini, repo root):
    venv/bin/python3.13 scripts/reconcile_kraken.py              # dry-run, stdout only
    venv/bin/python3.13 scripts/reconcile_kraken.py --verbose    # + every matched order
    venv/bin/python3.13 scripts/reconcile_kraken.py --write      # also INSERT into reconciliation_runs (venue='kraken')

Exit codes: 0 all OK · 1 at least one DRIFT* · 2 fatal (Kraken/DB unreachable)
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.exchanges.kraken_client import KrakenClient
from db.client import get_client

SYMBOLS = ["BTC/USD", "SOL/USD"]
HISTORY_START = datetime(2026, 7, 15, tzinfo=timezone.utc)  # before the 17-Jul test order

# === Tolerances (real money) ===
QTY_TOL_ABS = 1e-8          # Kraken base precision
PRICE_TOL_PCT = 0.1 / 100   # ±0.1%
MONEY_TOL_ABS = 0.01        # ±$0.01 on fee and cost
BAL_TOL_REL = 0.001         # balance gap within ±0.1% of DB holdings = OK
STAKING_MAX_REL = 0.02      # SOL surplus up to +2% = staking rewards, OK with note
STAKED_COINS = {"SOL"}

SEVERITY = ["DRIFT_EXCHANGE_ORPHAN", "DRIFT_DB_ORPHAN", "DRIFT", "DRIFT_BALANCE", "OK"]


def _ts(sec: float) -> str:
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# Kraken side
# ============================================================

def fetch_kraken_fills(raw) -> list[dict]:
    """All account fills since HISTORY_START (TradesHistory, 50 per page)."""
    fills, ofs, count = [], 0, None
    start = int(HISTORY_START.timestamp())
    while count is None or ofs < count:
        res = raw.privatePostTradesHistory({"start": start, "ofs": ofs})["result"]
        count = int(res.get("count", 0))
        page = res.get("trades", {})
        if not page:
            break
        for txid, t in page.items():
            fills.append({"txid": txid, **t})
        ofs += len(page)
    return fills


def aggregate_orders(fills: list[dict], pair_ids: set[str]) -> list[dict]:
    """Group fills of our pair by ordertxid → one logical order each."""
    by_order = defaultdict(list)
    for f in fills:
        if f.get("pair") in pair_ids:
            by_order[f["ordertxid"]].append(f)
    orders = []
    for oid, group in by_order.items():
        qty = sum(float(g["vol"]) for g in group)
        cost = sum(float(g["cost"]) for g in group)
        orders.append({
            "order_id": oid,
            "side": group[0]["type"],
            "qty": qty,
            "cost": cost,
            "price": cost / qty if qty else 0.0,
            "fee": sum(float(g["fee"]) for g in group),
            "ts": max(float(g["time"]) for g in group),
            "fills": len(group),
        })
    return sorted(orders, key=lambda o: o["ts"])


# ============================================================
# DB side
# ============================================================

def fetch_db_trades(client, symbol: str) -> list[dict]:
    rows = (
        client.table("trades")
        .select("id,created_at,side,amount,price,cost,fee,exchange_order_id,cycle")
        .eq("symbol", symbol)
        .order("created_at")
        .execute()
    ).data or []
    return [{
        "db_id": r["id"],
        "created_at": r["created_at"][:19].replace("T", " "),
        "side": r["side"],
        "qty": float(r["amount"]),
        "price": float(r["price"]),
        "cost": float(r.get("cost") or 0),
        "fee": float(r.get("fee") or 0),
        "order_id": r.get("exchange_order_id"),
        "cycle": r.get("cycle"),
    } for r in rows]


# ============================================================
# Checks
# ============================================================

def check_pair(db: dict, kr: dict) -> list[dict]:
    """Field-level drift for a matched DB row / Kraken order (empty = OK)."""
    out = []
    if db["side"] != kr["side"]:
        out.append({"field": "side", "db": db["side"], "kraken": kr["side"]})
    if abs(db["qty"] - kr["qty"]) > QTY_TOL_ABS:
        out.append({"field": "qty", "db": db["qty"], "kraken": kr["qty"]})
    if kr["price"] and abs(db["price"] - kr["price"]) / kr["price"] > PRICE_TOL_PCT:
        out.append({"field": "price", "db": db["price"], "kraken": round(kr["price"], 6)})
    if abs(db["cost"] - kr["cost"]) > MONEY_TOL_ABS:
        out.append({"field": "cost", "db": db["cost"], "kraken": round(kr["cost"], 6)})
    if abs(db["fee"] - kr["fee"]) > MONEY_TOL_ABS:
        out.append({"field": "fee", "db": db["fee"], "kraken": round(kr["fee"], 6)})
    return out


def check_balance(coin: str, db_holdings: float, kraken_bal: float) -> tuple[str, str]:
    gap = kraken_bal - db_holdings
    tol = max(abs(db_holdings) * BAL_TOL_REL, QTY_TOL_ABS)
    if abs(gap) <= tol:
        return "OK", f"gap {gap:+.8f} {coin} within tolerance"
    if coin in STAKED_COINS and gap > 0 and db_holdings > 0 and gap / db_holdings <= STAKING_MAX_REL:
        return "OK", f"surplus {gap:+.8f} {coin} ({gap / db_holdings:+.2%}) = staking rewards"
    return "DRIFT_BALANCE", f"gap {gap:+.8f} {coin} ({gap / db_holdings:+.2%} of DB holdings)" if db_holdings else f"gap {gap:+.8f} {coin}"


def reconcile_symbol(symbol: str, raw, client, fills: list[dict], balance: dict, verbose: bool) -> dict:
    market = raw.market(symbol)
    pair_ids = {market["id"], market.get("info", {}).get("altname"), market.get("info", {}).get("wsname")} - {None}
    coin = market["base"]  # ccxt unified: BTC, SOL

    kr_orders = aggregate_orders(fills, pair_ids)
    db_rows = fetch_db_trades(client, symbol)
    kr_by_id = {o["order_id"]: o for o in kr_orders}

    matched, drift, db_orphans = [], [], []
    for d in db_rows:
        k = kr_by_id.get(d["order_id"]) if d["order_id"] else None
        if k is None:
            db_orphans.append(d)
            continue
        matched.append((d, k))
        findings = check_pair(d, k)
        if findings:
            drift.append({"order_id": d["order_id"], "db_id": d["db_id"], "at": d["created_at"], "findings": findings})
    used = {d["order_id"] for d, _ in matched}
    kr_orphans = [o for o in kr_orders if o["order_id"] not in used]

    db_holdings = sum(d["qty"] if d["side"] == "buy" else -d["qty"] for d in db_rows)
    kraken_bal = float(balance.get("total", {}).get(coin) or 0)
    bal_status, bal_note = check_balance(coin, db_holdings, kraken_bal)

    issues = []
    if kr_orphans:
        issues.append("DRIFT_EXCHANGE_ORPHAN")
    if db_orphans:
        issues.append("DRIFT_DB_ORPHAN")
    if drift:
        issues.append("DRIFT")
    if bal_status != "OK":
        issues.append(bal_status)
    status = min(issues, key=SEVERITY.index) if issues else "OK"

    print(f"\n=== {symbol} (Kraken pair {market['id']}) ===")
    print(f"  DB trades: {len(db_rows)}   Kraken orders: {len(kr_orders)} "
          f"({sum(o['fills'] for o in kr_orders)} fills)   matched: {len(matched)}")
    if verbose:
        for d, k in matched:
            print(f"    ✓ {d['created_at']} {d['side']:4s} {d['qty']:.8f} @ {d['price']:.2f}  "
                  f"fee db {d['fee']:.5f} / kr {k['fee']:.5f}  [{k['fills']} fill]  {d['order_id']}")
    for x in drift:
        print(f"  ⚠ DRIFT {x['at']} {x['order_id']}: {x['findings']}")
    for d in db_orphans:
        print(f"  ⚠ IN DB, NOT ON KRAKEN: {d['created_at']} {d['side']} {d['qty']:.8f} @ {d['price']:.2f} "
              f"order={d['order_id']} cycle={d['cycle']}")
    for o in kr_orphans:
        print(f"  ⚠ ON KRAKEN, NOT IN DB: {_ts(o['ts'])} {o['side']} {o['qty']:.8f} @ {o['price']:.2f} "
              f"fee {o['fee']:.5f} order={o['order_id']}")
    variants = {k: v for k, v in balance.get("total", {}).items() if k.startswith(coin) and k != coin and v}
    print(f"  Balance {coin}: DB {db_holdings:.8f} vs Kraken {kraken_bal:.8f} → {bal_status} ({bal_note})"
          + (f"  [other {coin} balances, not counted: {variants}]" if variants else ""))
    print(f"  → {status}")

    return {
        "symbol": symbol, "status": status, "db_count": len(db_rows),
        "exchange_count": len(kr_orders), "matched_count": len(matched),
        "unmatched_db_count": len(db_orphans), "unmatched_exchange_count": len(kr_orphans),
        "drift_count": len(drift), "db_holdings": db_holdings, "exchange_holdings": kraken_bal,
        "balance_status": bal_status, "balance_note": bal_note,
        "drift_details": {
            "drift": drift,
            "in_db_not_on_kraken": [{k: d[k] for k in ("created_at", "side", "qty", "price", "fee", "order_id", "cycle")} for d in db_orphans],
            "on_kraken_not_in_db": [{"at": _ts(o["ts"]), **{k: o[k] for k in ("side", "qty", "price", "fee", "order_id")}} for o in kr_orphans],
        } if issues else None,
        "matched_details": [{
            "at": d["created_at"], "side": d["side"], "order_id": d["order_id"], "fills": k["fills"],
            "qty_db": d["qty"], "qty_kr": k["qty"], "price_db": d["price"], "price_kr": round(k["price"], 6),
            "fee_db": d["fee"], "fee_kr": round(k["fee"], 6),
        } for d, k in matched],
    }


def write_results(client, results: list[dict], notes: str) -> None:
    rows = [{
        "venue": "kraken", "symbol": r["symbol"], "status": r["status"],
        "db_count": r["db_count"], "exchange_count": r["exchange_count"],
        "matched_count": r["matched_count"], "unmatched_db_count": r["unmatched_db_count"],
        "unmatched_exchange_count": r["unmatched_exchange_count"], "drift_count": r["drift_count"],
        "db_holdings": r["db_holdings"], "exchange_holdings": r["exchange_holdings"],
        "balance_status": r["balance_status"], "balance_note": r["balance_note"],
        "drift_details": r["drift_details"], "matched_details": r["matched_details"], "notes": notes,
    } for r in results]
    res = client.table("reconciliation_runs").insert(rows).execute()
    print(f"\n✓ wrote {len(res.data or [])} rows to reconciliation_runs (venue=kraken)")


def main() -> int:
    ap = argparse.ArgumentParser(description="R.1 — Kraken ↔ DB reconciliation (read-only)")
    ap.add_argument("--verbose", action="store_true", help="print every matched order")
    ap.add_argument("--write", action="store_true", help="INSERT results into reconciliation_runs")
    args = ap.parse_args()

    mode = "WRITE" if args.write else "dry-run (nothing written)"
    print(f"[reconcile_kraken] {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC — {mode}")
    try:
        raw = KrakenClient().raw
        raw.load_markets()
        fills = fetch_kraken_fills(raw)
        balance = raw.fetch_balance()
        client = get_client()
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}")
        return 2

    pairs = sorted({f.get("pair") for f in fills})
    print(f"Kraken fills since {HISTORY_START:%Y-%m-%d}: {len(fills)} on pairs {pairs}")

    results = [reconcile_symbol(s, raw, client, fills, balance, args.verbose) for s in SYMBOLS]

    ours = set()
    for s in SYMBOLS:
        m = raw.market(s)
        ours |= {m["id"], m.get("info", {}).get("altname"), m.get("info", {}).get("wsname")}
    other = [f for f in fills if f.get("pair") not in ours]
    notes = "USD cash not reconciled yet (shared by both grids + unallocated funds)."
    if other:
        other_pairs = sorted({f.get("pair") for f in other})
        print(f"\nℹ {len(other)} fill(s) on other pairs (not bot trades, e.g. EUR→USD conversions): {other_pairs}")
        notes += f" Ignored {len(other)} non-bot fill(s) on {', '.join(other_pairs)}."
    print(f"\n{notes}")

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  {r['symbol']:8s} {r['status']:22s} matched {r['matched_count']}/{r['db_count']} DB, "
              f"{r['exchange_count']} Kraken · orphans DB {r['unmatched_db_count']} / Kraken "
              f"{r['unmatched_exchange_count']} · drift {r['drift_count']} · balance {r['balance_status']}")
    if args.write:
        try:
            write_results(client, results, notes)
        except Exception as e:
            print(f"FATAL: write failed: {type(e).__name__}: {e}")
            return 2
    else:
        print("\n(dry-run: nothing written. Pass --write to persist into reconciliation_runs.)")
    return 1 if any(r["status"] != "OK" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
