"""
Backtest: would TF perform better if it forced an exit after the Nth
positive sell, instead of relying on % take-profit / greed decay / SL?

Definition of a "managed period":
  A continuous TF management of one coin. We approximate this from trade
  history: a managed period starts at the first TF trade and continues
  while consecutive TF trades on the same coin are within GAP_HOURS of
  each other. A gap > GAP_HOURS marks the end of one period and the start
  of the next (i.e. coin was deallocated and later re-allocated).

  Holdings can hit 0 and come back inside one managed period — we DON'T
  split on that, because that's just the grid breathing inside a TF hold.

For each managed period we compute:
  - actual realized PnL (sum of realized_pnl on every sell)
  - counterfactual PnL for N in {2..8}: walk trades in order, count
    positive sells. On the Nth positive sell, force-liquidate any remaining
    holdings at that sell's price and stop reading subsequent trades.

Output: scripts/output/exit_after_n_summary.csv + per-period CSV.
"""

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.client import get_client


OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# Gap > this many hours between two consecutive TF trades on the same coin
# is interpreted as "coin was deallocated and later re-allocated" — i.e. a
# new managed period. Below this, all activity is treated as one period
# (grid breathing inside a TF hold).
GAP_HOURS = 24
N_VALUES = (2, 3, 4, 5, 6, 7, 8)


def fetch_all_tf_trades():
    sb = get_client()
    rows = []
    step = 1000
    offset = 0
    while True:
        r = (
            sb.table("trades")
            .select("id, symbol, side, amount, price, cost, fee, realized_pnl, "
                    "buy_trade_id, created_at")
            .eq("managed_by", "tf")
            .order("created_at")
            .range(offset, offset + step - 1)
            .execute()
        )
        if not r.data:
            break
        rows.extend(r.data)
        if len(r.data) < step:
            break
        offset += step
    return rows


def build_managed_periods(trades, gap_hours=GAP_HOURS):
    """
    Group trades by symbol, walk chronologically, split into managed periods
    when the gap between two consecutive trades on that coin exceeds
    `gap_hours`. Each period collects all trades regardless of whether
    holdings hit 0 mid-period.

    A period is considered "closed" if its last trade ended with net
    holdings ≈ 0 (final sell completed). Otherwise it's still holding.
    """
    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"]].append(t)

    periods = []
    EPS = 1e-9
    gap_seconds = gap_hours * 3600

    for symbol, ts in by_symbol.items():
        ts.sort(key=lambda t: t["created_at"])
        groups = []
        current = []
        prev_dt = None
        for t in ts:
            dt = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            if prev_dt is not None and (dt - prev_dt).total_seconds() > gap_seconds:
                groups.append(current)
                current = []
            current.append(t)
            prev_dt = dt
        if current:
            groups.append(current)

        for idx, grp in enumerate(groups):
            holdings = 0.0
            for t in grp:
                amt = float(t.get("amount") or 0)
                if t["side"] == "buy":
                    holdings += amt
                elif t["side"] == "sell":
                    holdings -= amt
            closed = abs(holdings) <= EPS
            periods.append({
                "symbol": symbol,
                "period_idx": idx,
                "trades": grp,
                "opened_at": grp[0]["created_at"],
                "closed_at": grp[-1]["created_at"] if closed else None,
                "closed": closed,
                "final_holdings": holdings,
            })
    return periods


def actual_realized_pnl(period):
    return sum(float(t.get("realized_pnl") or 0) for t in period["trades"]
               if t.get("side") == "sell")


def counterfactual_pnl(period, N):
    """
    Simulate: process trades in order, count positive sells. As soon as the
    Nth positive sell fires, stop. Force-liquidate any remaining holdings at
    that sell's price (no fee modelled — same assumption as actual_realized_pnl
    which already excludes implicit liquidation costs).

    Returns dict with: realized, exited_early, pos_count, exit_price,
    residual_holdings (qty at the exit moment, BEFORE force-liquidation),
    residual_avg_buy, liq_pnl_usd (PnL contribution of the force-sell only),
    liq_value_usd (gross USD value of the residual block sold).
    """
    holdings = 0.0
    avg_buy = 0.0
    realized = 0.0
    pos_count = 0
    exited_early = False
    exit_price = None
    residual_holdings = 0.0
    residual_avg_buy = 0.0
    liq_pnl = 0.0
    liq_value = 0.0

    for t in period["trades"]:
        side = t.get("side")
        amt = float(t.get("amount") or 0)
        price = float(t.get("price") or 0)

        if side == "buy":
            new_h = holdings + amt
            if new_h > 0:
                avg_buy = (avg_buy * holdings + price * amt) / new_h
            holdings = new_h
        elif side == "sell":
            rpnl = float(t.get("realized_pnl") or 0)
            realized += rpnl
            holdings -= amt
            if holdings < 0:
                holdings = 0.0
            if rpnl > 0:
                pos_count += 1
                if pos_count >= N:
                    exit_price = price
                    residual_holdings = holdings
                    residual_avg_buy = avg_buy
                    if holdings > 0:
                        liq_pnl = (price - avg_buy) * holdings
                        liq_value = price * holdings
                        realized += liq_pnl
                        holdings = 0.0
                    exited_early = True
                    break

    return {
        "realized": realized,
        "exited_early": exited_early,
        "pos_count": pos_count,
        "exit_price": exit_price,
        "residual_holdings": residual_holdings,
        "residual_avg_buy": residual_avg_buy,
        "liq_pnl_usd": liq_pnl,
        "liq_value_usd": liq_value,
    }


def summarize(periods, n_values=N_VALUES):
    closed = [p for p in periods if p["closed"]]
    summary = []
    for N in n_values:
        deltas = []
        triggered = 0
        beat = tied = worse = 0
        total_actual = 0.0
        total_cf = 0.0
        for p in closed:
            actual = actual_realized_pnl(p)
            res = counterfactual_pnl(p, N)
            cf = res["realized"]
            exited = res["exited_early"]
            total_actual += actual
            total_cf += cf
            if exited:
                triggered += 1
                d = cf - actual
                deltas.append(d)
                if d > 0.01:
                    beat += 1
                elif d < -0.01:
                    worse += 1
                else:
                    tied += 1
        avg_delta = (sum(deltas) / len(deltas)) if deltas else 0.0
        summary.append({
            "N": N,
            "periods_closed": len(closed),
            "rule_triggered": triggered,
            "rule_beat_actual": beat,
            "rule_worse_than_actual": worse,
            "rule_tied": tied,
            "avg_delta_when_triggered_usd": round(avg_delta, 4),
            "total_actual_pnl_usd": round(total_actual, 4),
            "total_counterfactual_pnl_usd": round(total_cf, 4),
            "delta_total_usd": round(total_cf - total_actual, 4),
        })
    return summary


def write_per_period_csv(periods, n_values=N_VALUES, detail_n=4):
    """
    detail_n: extra columns about the residual liquidation are written for
    this single N (kept narrow to avoid an unreadably wide CSV).
    """
    import csv
    path = OUT_DIR / "exit_after_n_per_period.csv"
    fieldnames = ["symbol", "period_idx", "opened_at", "closed_at", "closed",
                  "n_trades", "n_positive_sells", "actual_pnl_usd"]
    for N in n_values:
        fieldnames += [f"cf_N{N}_pnl_usd", f"cf_N{N}_triggered", f"cf_N{N}_delta_usd"]
    fieldnames += [
        f"detail_N{detail_n}_residual_qty",
        f"detail_N{detail_n}_residual_avg_buy",
        f"detail_N{detail_n}_exit_price",
        f"detail_N{detail_n}_liq_value_usd",
        f"detail_N{detail_n}_liq_pnl_usd",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in periods:
            actual = actual_realized_pnl(p)
            n_pos = sum(1 for t in p["trades"]
                        if t.get("side") == "sell" and float(t.get("realized_pnl") or 0) > 0)
            row = {
                "symbol": p["symbol"],
                "period_idx": p["period_idx"],
                "opened_at": p["opened_at"],
                "closed_at": p["closed_at"] or "",
                "closed": p["closed"],
                "n_trades": len(p["trades"]),
                "n_positive_sells": n_pos,
                "actual_pnl_usd": round(actual, 4),
            }
            for N in n_values:
                if p["closed"]:
                    res = counterfactual_pnl(p, N)
                    row[f"cf_N{N}_pnl_usd"] = round(res["realized"], 4)
                    row[f"cf_N{N}_triggered"] = res["exited_early"]
                    row[f"cf_N{N}_delta_usd"] = round(res["realized"] - actual, 4)
                    if N == detail_n and res["exited_early"]:
                        row[f"detail_N{detail_n}_residual_qty"] = round(res["residual_holdings"], 8)
                        row[f"detail_N{detail_n}_residual_avg_buy"] = round(res["residual_avg_buy"], 8)
                        row[f"detail_N{detail_n}_exit_price"] = round(res["exit_price"], 8)
                        row[f"detail_N{detail_n}_liq_value_usd"] = round(res["liq_value_usd"], 4)
                        row[f"detail_N{detail_n}_liq_pnl_usd"] = round(res["liq_pnl_usd"], 4)
                else:
                    row[f"cf_N{N}_pnl_usd"] = ""
                    row[f"cf_N{N}_triggered"] = ""
                    row[f"cf_N{N}_delta_usd"] = ""
            w.writerow(row)
    return path


def main():
    print("Fetching TF trades from Supabase...")
    trades = fetch_all_tf_trades()
    print(f"  fetched {len(trades)} trades")

    periods = build_managed_periods(trades)
    closed = [p for p in periods if p["closed"]]
    open_ = [p for p in periods if not p["closed"]]
    print(f"Reconstructed managed periods (gap > {GAP_HOURS}h splits): "
          f"{len(periods)} total — {len(closed)} closed, {len(open_)} still holding")

    if not closed:
        print("No closed periods — nothing to backtest.")
        return

    summary = summarize(closed)
    import csv
    sum_path = OUT_DIR / "exit_after_n_summary.csv"
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    per_period_path = write_per_period_csv(periods)

    print("\n=== Summary ===")
    print(f"Closed managed periods: {len(closed)}")
    print(f"{'N':>3} {'trig':>5} {'beat':>5} {'worse':>6} {'tied':>5} "
          f"{'avgΔ$':>8} {'totΔ$':>9}")
    for row in summary:
        print(f"{row['N']:>3} {row['rule_triggered']:>5} {row['rule_beat_actual']:>5} "
              f"{row['rule_worse_than_actual']:>6} {row['rule_tied']:>5} "
              f"{row['avg_delta_when_triggered_usd']:>8.2f} "
              f"{row['delta_total_usd']:>9.2f}")
    print(f"\nWritten:\n  {sum_path}\n  {per_period_path}")


if __name__ == "__main__":
    main()
